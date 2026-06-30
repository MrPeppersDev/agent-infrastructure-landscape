#!/usr/bin/env python3
"""
phase_2_llm_fill_apply.py — Phase 2 Gate 1 / Phase 4 of 4.

Applies LLM-generated cell fills (capability-*, use-case-*, residual
cost-*) to data/landscape.json from a JSONL input file produced by
parallel sub-agents (PHASE_2_SPEC.html §3.5).

Input JSONL — one line per cell:

  {"record_id": "...", "slug": "capability-band",
   "value": "frontier", "citation": "https://...", "status": "real-data"}

Optional fields:
  - "citation": null or absent → no citation (tier auto-classifier
    will pick T3).
  - "status": one of {real-data, not-applicable, depth-floor-reached};
    default "real-data". A missing or "no-data" status is rejected —
    LLM-judgment fills must commit to a status.

Provenance — every cell touched here gets:
  { "generated_at": <run date>,
    "model_id": <--model-id>,
    "source": "llm",
    "verified": false }

Round-trip invariants (same traps that bit Phase 3):
  - Tier is auto-derived via extract.classify_tier(citation, status) so
    the committed JSON matches what extract.py would compute on the
    rendered HTML round-trip (gate 2).
  - Provenance entries are alphabetized; the `_provenance` dict is
    re-sorted to match cells iteration order after all writes.
  - Values intended as not-applicable must begin with "not applicable —"
    (extract.py:detect_status() reclassifies otherwise) — the script
    enforces this at apply time.

Idempotent: skips any cell whose current status is not "no-data".
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
SCRIPT_REL_PATH = "scripts/phase_2_llm_fill_apply.py"

sys.path.insert(0, str(ROOT / "scripts"))
from extract import classify_tier  # noqa: E402

# Slugs Phase 4 is allowed to write. Anything outside this set is
# rejected — Phase 4 is scoped to the new cells only.
ALLOWED_SLUGS = {
    "cost-input-usd-per-mtok",
    "cost-output-usd-per-mtok",
    "cost-tier",
    "cost-pricing-model",
    "cost-last-verified",
    "capability-composite-score",
    "capability-band",
    "capability-benchmark-sources",
    "capability-last-verified",
    "use-case-tags",
    "use-case-anti-tags",
}

ALLOWED_STATUSES = {"real-data", "not-applicable", "depth-floor-reached", "estimate"}

NA_PREFIX_RE = re.compile(r"^\s*(not\s+applicable|n/a)\b", re.IGNORECASE)


def make_cell(value: str, citation: str | None, status: str) -> dict[str, Any]:
    """Build a cell with auto-derived tier so the round-trip stays byte-stable."""
    tier, _ = classify_tier(citation, status)
    out = OrderedDict()
    out["value"] = value
    out["citation"] = citation
    out["status"] = status
    out["tier"] = tier
    return out


def provenance_entry(*, generated_at: str, model_id: str) -> OrderedDict[str, Any]:
    entry = {
        "generated_at": generated_at,
        "model_id": model_id,
        "source": "llm",
        "verified": False,
    }
    return OrderedDict(sorted(entry.items()))


def validate_row(row: dict[str, Any], lineno: int) -> tuple[str, str, str, str | None, str]:
    """Return (record_id, slug, value, citation, status). Raises on bad input."""
    if not isinstance(row, dict):
        raise ValueError(f"line {lineno}: expected object, got {type(row).__name__}")
    record_id = row.get("record_id")
    slug = row.get("slug")
    value = row.get("value")
    citation = row.get("citation")
    status = row.get("status", "real-data")

    if not isinstance(record_id, str) or not record_id:
        raise ValueError(f"line {lineno}: missing/invalid record_id")
    if slug not in ALLOWED_SLUGS:
        raise ValueError(
            f"line {lineno}: slug {slug!r} not in Phase 4 scope. "
            f"Allowed: {sorted(ALLOWED_SLUGS)}"
        )
    if not isinstance(value, str):
        raise ValueError(f"line {lineno}: value must be string, got {type(value).__name__}")
    if citation is not None and not isinstance(citation, str):
        raise ValueError(f"line {lineno}: citation must be string or null")
    if status not in ALLOWED_STATUSES:
        raise ValueError(
            f"line {lineno}: status {status!r} not allowed. "
            f"Must be one of {sorted(ALLOWED_STATUSES)}"
        )

    # Round-trip trap from Phase 3: extract.py:detect_status() looks at
    # the value text. If we claim "not-applicable" but the prose doesn't
    # match, the round-trip will reclassify and break gate 3.
    if status == "not-applicable" and not NA_PREFIX_RE.match(value):
        raise ValueError(
            f"line {lineno}: status=not-applicable requires value to start "
            f"with 'not applicable —' (got {value[:50]!r})"
        )

    return record_id, slug, value, citation, status


def reorder_provenance(landscape: dict[str, Any]) -> None:
    """Re-sort each `_provenance` to match cells iteration order — required
    by gate 2. Same convention as phase_2_provenance_backfill.py."""
    for rec in landscape.get("records") or []:
        prov = rec.get("_provenance")
        if not isinstance(prov, dict) or not prov:
            continue
        cell_order = list((rec.get("cells") or {}).keys())
        rank = {slug: i for i, slug in enumerate(cell_order)}
        rec["_provenance"] = OrderedDict(
            sorted(prov.items(), key=lambda kv: rank.get(kv[0], 1_000_000))
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True,
                    help="Path to JSONL of LLM-generated cell fills.")
    ap.add_argument("--landscape", type=Path, default=LANDSCAPE_JSON)
    ap.add_argument("--model-id", required=True,
                    help="Model identifier recorded in provenance (e.g. claude-opus-4-7).")
    ap.add_argument("--today", default=None,
                    help="Override run date (YYYY-MM-DD). Default: today UTC.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Validate + print counts; do not write.")
    args = ap.parse_args()

    today = args.today or dt.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", today):
        print(f"--today must be YYYY-MM-DD, got {today!r}", file=sys.stderr)
        return 2

    rows: list[tuple[str, str, str, str | None, str]] = []
    with args.input.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw or raw.startswith("//"):
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"line {lineno}: bad JSON: {e}", file=sys.stderr)
                return 2
            try:
                rows.append(validate_row(obj, lineno))
            except ValueError as e:
                print(str(e), file=sys.stderr)
                return 2

    print(f"loaded {len(rows)} cell-fills from {args.input}")

    with args.landscape.open("r", encoding="utf-8") as f:
        landscape = json.load(f)

    by_id = {r["id"]: r for r in landscape.get("records") or []}

    slug_counter: Counter[str] = Counter()
    skipped_already_filled = 0
    skipped_unknown_record = 0
    records_touched: set[str] = set()
    total_cells_filled = 0

    for record_id, slug, value, citation, status in rows:
        rec = by_id.get(record_id)
        if rec is None:
            skipped_unknown_record += 1
            continue
        cells = rec.setdefault("cells", OrderedDict())
        existing = cells.get(slug) or {}
        if existing.get("status") != "no-data":
            skipped_already_filled += 1
            continue
        cells[slug] = make_cell(value, citation, status)
        prov = rec.setdefault("_provenance", OrderedDict())
        if not isinstance(prov, dict):
            prov = OrderedDict()
            rec["_provenance"] = prov
        prov[slug] = provenance_entry(generated_at=today, model_id=args.model_id)
        slug_counter[slug] += 1
        records_touched.add(record_id)
        total_cells_filled += 1

    print("cells filled by slug:")
    for s, n in slug_counter.most_common():
        print(f"  {s}: {n}")
    print(f"records_touched={len(records_touched)}  "
          f"cells_filled={total_cells_filled}  "
          f"skipped_already_filled={skipped_already_filled}  "
          f"skipped_unknown_record={skipped_unknown_record}")

    if args.dry_run:
        return 0

    reorder_provenance(landscape)
    with args.landscape.open("w", encoding="utf-8") as f:
        json.dump(landscape, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {args.landscape}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
