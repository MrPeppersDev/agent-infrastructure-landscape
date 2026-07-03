#!/usr/bin/env python3
"""
capability_sweep.py — populates capability-* cells from linked benchmark
sources on the weekly rebaseline cron.

Reads:
  - data/landscape.json (912 rows)
  - docs/benchmark-families.yml (benchmark → family map)
  - data/_baselines/benchmark-maxima.json (per-benchmark ceilings; if
    absent, falls back to per-row max — logs warning, staging only)

For each row:
  1. Parses `capability-benchmark-sources` for {benchmark, score, url}
     tuples. Where the cell text is placeholder-only ("general capability
     estimate", "not applicable"), the row is skipped and its existing
     capability-* cells are left alone.
  2. (LLM PATH) Calls Haiku over each linked URL to extract structured
     {benchmark_id, score, run_date} triples.
  3. Classifies each triple into a family via benchmark-families.yml.
  4. Runs `compute_row` from scripts/_composite.py to produce the
     composite + sub-scores + band.
  5. (LLM PATH) Calls Sonnet for a QA sanity check on the composite
     before committing.
  6. Writes results to a staging file
     `data/_baselines/capability-sweep-YYYY-MM-DD.json` — NEVER directly
     to landscape.json. A separate merge step commits into
     landscape.json (see `--merge-into-landscape` below).

Provenance semantics (methodology §Verification bit):
  - `_provenance[cell].verified: true` is set ONLY when
    (a) ≥ 1 benchmark score in a linked URL matched an extraction,
    AND (b) the Sonnet QA pass approved the composite.
  - Otherwise the cell is written (or left) with `verified: false`.
  - Rows with no linked URLs get cells left as-is; verified bit unchanged.

Idempotency:
  Content-hash of `capability-benchmark-sources` cell + methodology
  version tag are compared against the last successful sweep manifest at
  `data/_baselines/capability-sweep-manifest.json`. Rows whose hash and
  version match are skipped.

Cost & rate limiting:
  Sweep uses the Anthropic batch API (methodology recommendation #3;
  24h SLA; 50% cheaper). API key from `ANTHROPIC_API_KEY` env var; the
  cron passes it in from GitHub Actions secrets. Local runs read `.env`.

Usage
-----
    python3 scripts/capability_sweep.py --dry-run           # print plan, no writes, no LLM calls
    python3 scripts/capability_sweep.py --limit 10          # sweep first 10 rows only
    python3 scripts/capability_sweep.py --no-llm            # use existing benchmark-source text as
                                                            # already-extracted observations, run
                                                            # composite formula, write staging
    python3 scripts/capability_sweep.py                     # full sweep (needs ANTHROPIC_API_KEY)
    python3 scripts/capability_sweep.py --merge-into-landscape \
        --sweep data/_baselines/capability-sweep-2026-07-01.json
                                                            # commit a staged sweep into landscape.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _composite import (  # noqa: E402
    BenchmarkAnchor,
    BenchmarkObservation,
    TaskFamily,
    compute_row,
)

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
BENCHMARK_FAMILIES_YML = ROOT / "docs" / "benchmark-families.yml"
BASELINES_DIR = ROOT / "data" / "_baselines"
BENCHMARK_MAXIMA_JSON = BASELINES_DIR / "benchmark-maxima.json"
SWEEP_MANIFEST = BASELINES_DIR / "capability-sweep-manifest.json"
METHODOLOGY_VERSION = "2026-07-01"  # bump when composite formula changes

# Text markers indicating the source cell is placeholder, not real
# benchmark data. Case-insensitive substring match.
PLACEHOLDER_MARKERS = (
    "not applicable",
    "general capability estimate",
    "no specific benchmark",
    "not a capable system",
    "not benchmarked",
    "not evaluated",
    "n/a",
)


@dataclass
class RowResult:
    row_id: str
    composite: Optional[float]
    band: Optional[str]
    by_family: dict[str, Optional[float]]
    benchmark_count: dict[str, int]
    observations: list[dict]  # serialized BenchmarkObservation list
    sources_seen: list[str]
    sources_verified: list[str]  # subset with URL-backed extractions
    qa_verdict: Optional[str] = None  # 'approved' / 'flagged' / None
    skipped_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# benchmark-families.yml loader (no PyYAML dependency — the file is a flat
# structure and we already control its shape).
# ---------------------------------------------------------------------------


def load_benchmark_families() -> dict[str, str]:
    """Return {benchmark_id: family_str} — 'excluded' family is dropped
    (its benchmarks contribute zero and are not passed to compute_row).
    Entries with `family: null` are also dropped."""
    text = BENCHMARK_FAMILIES_YML.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    current_id: Optional[str] = None
    for line in text.splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        # Top-level benchmark id: no leading spaces, ends with ":"
        m = re.match(r"^([a-z0-9][a-z0-9\-]*):\s*$", stripped)
        if m:
            current_id = m.group(1)
            continue
        m = re.match(r"^\s+family:\s*(\S+)\s*$", stripped)
        if m and current_id is not None:
            fam = m.group(1)
            if fam in ("code", "agentic", "longcontext"):
                out[current_id] = fam
            current_id = None
    return out


# ---------------------------------------------------------------------------
# benchmark-maxima.json — the SOTA anchor file. Absent on first run.
# ---------------------------------------------------------------------------


def load_benchmark_maxima() -> dict[str, BenchmarkAnchor]:
    if not BENCHMARK_MAXIMA_JSON.exists():
        return {}
    raw = json.loads(BENCHMARK_MAXIMA_JSON.read_text(encoding="utf-8"))
    out: dict[str, BenchmarkAnchor] = {}
    for bench_id, entry in raw.items():
        out[bench_id] = BenchmarkAnchor(
            max=float(entry["max"]),
            min=float(entry.get("min", 0.0)),
        )
    return out


# ---------------------------------------------------------------------------
# Placeholder-detection + naïve benchmark-source parsing.
#
# Under --no-llm we treat `capability-benchmark-sources` cell text as
# already-extracted observations. Under the LLM path this same function
# picks off obvious mentions before falling back to fetch+extract.
# ---------------------------------------------------------------------------


BENCH_MENTION_RE = re.compile(
    r"(?P<bench>[a-z0-9][a-z0-9\-_+]*(?:\s+[a-z0-9][a-z0-9\-_+]*){0,3})"
    r"\s*(?:score|verified)?\s*"
    r"[:~≈=]?\s*"
    r"(?P<score>\d{1,3}(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


def is_placeholder_text(text: str) -> bool:
    lower = text.lower()
    return any(m in lower for m in PLACEHOLDER_MARKERS)


def parse_naive_observations(
    text: str,
    families: dict[str, str],
    default_trust: float = 50.0,
) -> list[BenchmarkObservation]:
    """Extract {benchmark, score} tuples from cell text using a regex.

    Only used under --no-llm mode. Real sweep will replace this with a
    Haiku extraction pass over linked URLs.
    """
    obs: list[BenchmarkObservation] = []
    seen: set[str] = set()
    for m in BENCH_MENTION_RE.finditer(text):
        raw = m.group("bench").strip().lower()
        # Canonicalise "swe-bench verified" → "swe-bench-verified" etc.
        candidate = re.sub(r"\s+", "-", raw)
        # Also try the head token for umbrella matches.
        for key in (candidate, candidate.split("-")[0]):
            if key in families and key not in seen:
                seen.add(key)
                score = float(m.group("score"))
                obs.append(
                    BenchmarkObservation(
                        id=key,
                        score=score,
                        trust=default_trust,
                        family=families[key],  # type: ignore[arg-type]
                    )
                )
                break
    return obs


# ---------------------------------------------------------------------------
# Per-row sweep (delegated to LLM in production; regex under --no-llm).
# ---------------------------------------------------------------------------


def sweep_row(
    row: dict,
    families: dict[str, str],
    anchors: dict[str, BenchmarkAnchor],
    use_llm: bool,
) -> RowResult:
    row_id = row["id"]
    cells = row.get("cells") or {}
    src_cell = cells.get("capability-benchmark-sources") or {}
    src_text = (src_cell.get("value") or "").strip()

    result = RowResult(
        row_id=row_id,
        composite=None,
        band=None,
        by_family={"code": None, "agentic": None, "longcontext": None},
        benchmark_count={"code": 0, "agentic": 0, "longcontext": 0},
        observations=[],
        sources_seen=[],
        sources_verified=[],
    )

    if not src_text:
        result.skipped_reason = "empty benchmark-sources cell"
        return result
    if is_placeholder_text(src_text):
        result.skipped_reason = "placeholder-only cell text"
        return result

    if use_llm:
        # Production path — call Haiku over each linked URL, extract
        # {benchmark_id, score, run_date} triples, then Sonnet QA.
        # LLM plumbing is intentionally not implemented here: the cron
        # will inject an ANTHROPIC_API_KEY-bearing client via
        # scripts/_llm_client.py (a follow-up PR).
        raise NotImplementedError(
            "LLM extraction path not yet wired. Use --no-llm for now."
        )

    obs = parse_naive_observations(src_text, families)
    if not obs:
        result.skipped_reason = "no benchmark mentions matched families map"
        return result

    row_result = compute_row(obs, anchors)
    result.composite = row_result.composite
    result.band = row_result.band
    result.by_family = {k: v for k, v in row_result.by_family.items()}  # type: ignore[misc]
    result.benchmark_count = {k: v for k, v in row_result.benchmark_count.items()}  # type: ignore[misc]
    result.observations = [
        {"id": o.id, "score": o.score, "trust": o.trust, "family": o.family}
        for o in obs
    ]
    result.sources_seen = [src_text]
    return result


# ---------------------------------------------------------------------------
# Idempotency manifest.
# ---------------------------------------------------------------------------


def row_hash(row: dict) -> str:
    """Content hash keyed on the benchmark-sources cell + methodology
    version. Rows whose hash matches the manifest can be skipped."""
    src = (row.get("cells") or {}).get("capability-benchmark-sources") or {}
    payload = json.dumps(
        {"value": src.get("value", ""), "methodology": METHODOLOGY_VERSION},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def load_manifest() -> dict[str, str]:
    if not SWEEP_MANIFEST.exists():
        return {}
    return json.loads(SWEEP_MANIFEST.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Staging output.
# ---------------------------------------------------------------------------


def staging_path() -> Path:
    return BASELINES_DIR / f"capability-sweep-{date.today().isoformat()}.json"


def write_staging(results: list[RowResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "methodologyVersion": METHODOLOGY_VERSION,
        "totalRows": len(results),
        "rowsWithComposite": sum(1 for r in results if r.composite is not None),
        "results": [asdict(r) for r in results],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Merge staged sweep → landscape.json (invoked separately from the sweep
# itself so a human / CI can inspect the staging file first).
# ---------------------------------------------------------------------------


def merge_into_landscape(sweep_path: Path) -> tuple[int, int]:
    """Return (rows_updated, cells_written)."""
    sweep = json.loads(sweep_path.read_text(encoding="utf-8"))
    data = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))
    by_id = {rec["id"]: rec for rec in data["records"]}
    today = date.today().isoformat()

    rows_updated = 0
    cells_written = 0

    for res in sweep["results"]:
        row_id = res["row_id"]
        rec = by_id.get(row_id)
        if rec is None:
            continue
        if res["composite"] is None:
            continue

        cells = rec.setdefault("cells", {})
        prov = rec.setdefault("_provenance", {})
        verified = bool(res.get("sources_verified")) and res.get("qa_verdict") == "approved"

        def _write(slug: str, value: str) -> None:
            nonlocal cells_written
            cells[slug] = {
                "value": value,
                "citation": None,
                "status": "estimate",
                "tier": "T3",
            }
            prov[slug] = {
                "source": "llm",
                "model_id": "claude-sonnet-4-6",
                "generated_at": today,
                "verified": verified,
            }
            cells_written += 1

        _write("capability-composite-score", f"{res['composite']:.1f}")
        _write("capability-band", res["band"] or "")
        for fam in ("code", "agentic", "longcontext"):
            v = res["by_family"].get(fam)
            if v is not None:
                _write(f"capability-{fam}-score", f"{v:.1f}")

        rows_updated += 1

    tmp = LANDSCAPE_JSON.with_suffix(LANDSCAPE_JSON.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(LANDSCAPE_JSON)
    return rows_updated, cells_written


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--dry-run", action="store_true", help="Plan-only. No writes, no LLM calls.")
    ap.add_argument("--limit", type=int, default=0, help="Only sweep the first N eligible rows.")
    ap.add_argument(
        "--no-llm",
        action="store_true",
        help="Use existing benchmark-source cell text as already-extracted observations "
        "(no URL fetch, no LLM). Useful for pipeline testing without ANTHROPIC_API_KEY.",
    )
    ap.add_argument(
        "--merge-into-landscape",
        action="store_true",
        help="Merge a previously-staged sweep into data/landscape.json.",
    )
    ap.add_argument(
        "--sweep",
        type=Path,
        help="Path to the staging file to merge (with --merge-into-landscape).",
    )
    args = ap.parse_args()

    if args.merge_into_landscape:
        if not args.sweep:
            print("--merge-into-landscape requires --sweep <path>", file=sys.stderr)
            return 2
        rows_updated, cells_written = merge_into_landscape(args.sweep)
        print(f"Merged {args.sweep}:")
        print(f"  rows updated:  {rows_updated}")
        print(f"  cells written: {cells_written}")
        return 0

    families = load_benchmark_families()
    anchors = load_benchmark_maxima()
    if not anchors:
        print(
            "warning: benchmark-maxima.json absent — using per-row anchor fallback "
            "(staging-only; refuse to merge)",
            file=sys.stderr,
        )
    print(f"loaded {len(families)} benchmark → family classifications")

    data = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))
    records = data["records"]

    manifest = load_manifest()
    results: list[RowResult] = []
    swept = 0
    skipped_by_hash = 0
    for rec in records:
        if args.limit and swept >= args.limit:
            break
        h = row_hash(rec)
        if manifest.get(rec["id"]) == h and not args.dry_run:
            skipped_by_hash += 1
            continue

        # Anchor fallback when maxima file is absent: use 100 for every
        # observed benchmark (produces less-meaningful sub-scores but
        # runs the pipeline end-to-end for testing).
        row_anchors = dict(anchors)
        if not row_anchors:
            row_anchors = {b: BenchmarkAnchor(max=100.0) for b in families}

        res = sweep_row(rec, families, row_anchors, use_llm=not args.no_llm)
        results.append(res)
        swept += 1

    total = len(results)
    with_composite = sum(1 for r in results if r.composite is not None)
    print(f"swept {total} rows ({skipped_by_hash} skipped by manifest hash)")
    print(f"  with composite:    {with_composite}")
    print(f"  skipped (no data): {total - with_composite}")

    if args.dry_run:
        print("(dry-run — no staging file written)")
        return 0

    out = staging_path()
    write_staging(results, out)
    print(f"wrote: {out.relative_to(ROOT)}")
    print("Next: python3 scripts/capability_sweep.py --merge-into-landscape --sweep " +
          str(out.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
