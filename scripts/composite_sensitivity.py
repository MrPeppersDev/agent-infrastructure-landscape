#!/usr/bin/env python3
"""
composite_sensitivity.py — Dirichlet weight-perturbation sensitivity
analysis for the capability composite (methodology §8.1, issue #130).

What it does
------------

The composite (docs/composite-methodology.md §7.2) is an equally-weighted
geometric mean over the three family sub-scores. §8.1 requires a
robustness check: perturb the inter-family weight vector with Dirichlet
samples around (1/3, 1/3, 1/3) and measure how stable each canonical
question's top-5 recommendation set is under the perturbed weights.

Procedure (per §8.1, with defaults documented where the spec is open):

1. Load rows and their family sub-scores (`capability-code-score`,
   `capability-agentic-score`, `capability-longcontext-score`) from
   data/landscape.json. Rows whose sub-score cells are all `no-data`
   are excluded — until the first real sweep (#128) lands this is every
   row, and the script exits cleanly reporting "0 rows with composite
   data".
2. Draw N Dirichlet weight samples. §8.1 says "Dirichlet samples around
   (1/3, 1/3, 1/3) with concentration parameter α = 10"; we read that
   as the symmetric Dirichlet(α, α, α) with α = 10 per component (mean
   (1/3, 1/3, 1/3), sd ≈ 0.085 per weight). Sampling is stdlib-only:
   three `random.gammavariate(α, 1)` draws, normalised to sum 1.
3. For each canonical question in docs/canonical-questions.yml (55 at
   time of writing; the script uses whatever the file contains) and
   each weight sample, rank the question's candidate pool by the
   weighted composite `exp(Σ wᵢ·ln sᵢ / Σ wᵢ)` over the row's present
   families (weights renormalised over present families, mirroring
   §7.2's present-families rule; any present sub-score ≤ 0 → 0) and
   take the top-5 (ties broken by row id for determinism).
4. Stability per question = per-sample overlap of the perturbed top-5
   with the unperturbed (equal-weights) baseline top-5. A question is
   flagged as "churning" when fewer than 90% of samples keep ≥ 4/5
   overlap (§8.1 target: ≥ 90% of questions show ≥ 4/5 overlap across
   100 samples).

Candidate pools (stdlib approximation of the TS recommender, documented
here because the full ranking math lives in mcp/ and issue #130 scopes
this script to the composite sort key):

- `surface: between` — pool is every scored row whose (perturbed)
  composite lies strictly between the two anchor rows' (perturbed)
  composites, anchors excluded. Anchors missing sub-score data →
  question reported with status `no-anchor-data` and skipped from the
  pass/fail tally.
- `surface: by-constraints` — pool is every scored row. The recommender
  also applies weight-INDEPENDENT filters (cost ceilings, use-case
  tags); those shrink the pool identically for baseline and perturbed
  rankings, so omitting them makes this a conservative (pessimistic)
  stability estimate over the widest pool.

Defaults chosen where §8.1 is open, per module contract:
  --samples 100   (stated in §8.1)
  --alpha   10.0  (stated in §8.1; interpreted as symmetric per-component)
  --seed    130   (issue number; any fixed seed makes runs reproducible)

Output
------

JSON artifact at data/_baselines/composite-sensitivity-YYYY-MM-DD.json
(matching the capability-sweep / rebaseline staging convention: JSON
under data/_baselines/, human-readable summaries belong in
docs/FINDINGS-YYYY-MM-DD.md per methodology §8). Contains parameters,
per-question stability scores, churn flags, and the §8.1 pass/fail
verdict. Never writes data/landscape.json.

Usage
-----

    python3 scripts/composite_sensitivity.py                 # real landscape.json
    python3 scripts/composite_sensitivity.py --fixture f.json  # synthetic rows (tests)
    python3 scripts/composite_sensitivity.py --samples 100 --alpha 10 --seed 130
    python3 scripts/composite_sensitivity.py --dry-run       # compute, no artifact write

Fixture format: either the full landscape.json shape ({"records": [...]})
or simplified records carrying a "subscores" object directly, e.g.
{"records": [{"id": "row-a", "subscores": {"code": 80, "agentic": 70}}]}.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _composite import TASK_FAMILIES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
QUESTIONS_YML = ROOT / "docs" / "canonical-questions.yml"
BASELINES_DIR = ROOT / "data" / "_baselines"

METHODOLOGY_SECTION = "8.1"
DEFAULT_SAMPLES = 100
DEFAULT_ALPHA = 10.0
DEFAULT_SEED = 130  # issue number; fixed for reproducibility
TOP_K = 5
OVERLAP_BAR = 4 / 5  # §8.1: ≥ 4/5 overlap ...
SAMPLE_PASS_RATE = 0.90  # ... in ≥ 90% of samples (per-question flag)
QUESTION_PASS_RATE = 0.90  # §8.1 target: ≥ 90% of questions unflagged

SUBSCORE_CELLS = {f: f"capability-{f}-score" for f in TASK_FAMILIES}


# ---------------------------------------------------------------------------
# Row loading — landscape.json cells or simplified fixture records.
# ---------------------------------------------------------------------------


def _parse_score(cell: Any) -> Optional[float]:
    """A sub-score cell counts only when its status isn't no-data and its
    value parses as a finite number."""
    if not isinstance(cell, dict):
        return None
    if (cell.get("status") or "").lower() == "no-data":
        return None
    raw = str(cell.get("value") or "").strip()
    if not raw:
        return None
    try:
        v = float(raw)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def load_rows(path: Path) -> dict[str, dict[str, float]]:
    """Return {row_id: {family: sub_score}} for rows with ≥ 1 sub-score."""
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data["records"] if isinstance(data, dict) else data
    out: dict[str, dict[str, float]] = {}
    for rec in records:
        row_id = rec.get("id")
        if not row_id:
            continue
        subs: dict[str, float] = {}
        if isinstance(rec.get("subscores"), dict):  # simplified fixture shape
            for fam in TASK_FAMILIES:
                v = rec["subscores"].get(fam)
                if isinstance(v, (int, float)) and math.isfinite(float(v)):
                    subs[fam] = float(v)
        else:
            cells = rec.get("cells") or {}
            for fam, slug in SUBSCORE_CELLS.items():
                v = _parse_score(cells.get(slug))
                if v is not None:
                    subs[fam] = v
        if subs:
            out[row_id] = subs
    return out


# ---------------------------------------------------------------------------
# canonical-questions.yml — minimal stdlib parser. We only need id,
# surface, and the two anchor ids; the file's shape is under our control
# (docs/SCHEMA.md §8) and the drift cron re-validates it with real YAML.
# ---------------------------------------------------------------------------

_ENTRY_RE = re.compile(r"^- id:\s*(\S+)\s*$")
_FIELD_RE = re.compile(r"^\s+(surface|anchor_low_id|anchor_high_id):\s*(\S+)\s*$")
_BLOCK_SCALAR_RE = re.compile(r"^(\s*)\S[^:]*:\s*[|>][+-]?\s*$")


def load_questions(path: Path) -> list[dict[str, Optional[str]]]:
    questions: list[dict[str, Optional[str]]] = []
    cur: Optional[dict[str, Optional[str]]] = None
    block_indent: Optional[int] = None  # inside a `notes: |` block scalar
    for line in path.read_text(encoding="utf-8").splitlines():
        if block_indent is not None:
            # Block-scalar bodies (e.g. `notes: |`) may contain lines that
            # look like fields; skip until dedent.
            if not line.strip() or len(line) - len(line.lstrip()) > block_indent:
                continue
            block_indent = None
        if line.lstrip().startswith("#"):
            continue
        m = _BLOCK_SCALAR_RE.match(line)
        if m:
            block_indent = len(m.group(1))
            continue
        m = _ENTRY_RE.match(line)
        if m:
            cur = {"id": m.group(1), "surface": None,
                   "anchor_low_id": None, "anchor_high_id": None}
            questions.append(cur)
            continue
        if cur is None:
            continue
        m = _FIELD_RE.match(line)
        if m:
            cur[m.group(1)] = m.group(2)
    return questions


# ---------------------------------------------------------------------------
# Dirichlet sampling (stdlib) + weighted composite.
# ---------------------------------------------------------------------------


def sample_dirichlet(rng: random.Random, alpha: float, k: int = 3) -> tuple[float, ...]:
    """Symmetric Dirichlet(α, ..., α) via normalised Gamma(α, 1) draws."""
    draws = [rng.gammavariate(alpha, 1.0) for _ in range(k)]
    total = sum(draws)
    if total <= 0:  # theoretically impossible for α > 0; belt-and-braces
        return tuple(1.0 / k for _ in range(k))
    return tuple(d / total for d in draws)


def weighted_composite(
    subs: dict[str, float], weights: dict[str, float]
) -> Optional[float]:
    """Weighted geometric mean over the row's PRESENT families, weights
    renormalised over those families — the weighted generalisation of
    §7.2 (equal weights reproduce compute_composite exactly). Any
    present sub-score ≤ 0 collapses the composite to 0, same as §7.2."""
    present = [(f, subs[f]) for f in TASK_FAMILIES if f in subs]
    if not present:
        return None
    if any(s <= 0 for _, s in present):
        return 0.0
    w_sum = sum(weights[f] for f, _ in present)
    if w_sum <= 0:
        return None
    log_sum = sum(weights[f] * math.log(s) for f, s in present)
    return math.exp(log_sum / w_sum)


EQUAL_WEIGHTS = {f: 1.0 / len(TASK_FAMILIES) for f in TASK_FAMILIES}


def composites_for(
    rows: dict[str, dict[str, float]], weights: dict[str, float]
) -> dict[str, float]:
    out: dict[str, float] = {}
    for row_id, subs in rows.items():
        c = weighted_composite(subs, weights)
        if c is not None:
            out[row_id] = c
    return out


# ---------------------------------------------------------------------------
# Per-question pool + top-k ranking.
# ---------------------------------------------------------------------------


def question_top_k(
    q: dict[str, Optional[str]],
    composites: dict[str, float],
    k: int = TOP_K,
) -> Optional[list[str]]:
    """Top-k row ids for a question under the given composite map.
    Returns None when the question can't be scored (missing anchors)."""
    surface = (q.get("surface") or "").lower()
    if surface == "between":
        low_id, high_id = q.get("anchor_low_id"), q.get("anchor_high_id")
        if not low_id or not high_id:
            return None
        lo, hi = composites.get(low_id), composites.get(high_id)
        if lo is None or hi is None:
            return None
        if lo > hi:
            lo, hi = hi, lo
        pool = [
            (c, rid) for rid, c in composites.items()
            if lo < c < hi and rid not in (low_id, high_id)
        ]
    else:  # by-constraints (and any future surface): widest pool
        pool = list((c, rid) for rid, c in composites.items())
    pool.sort(key=lambda t: (-t[0], t[1]))  # score desc, id asc (deterministic)
    return [rid for _, rid in pool[:k]]


# ---------------------------------------------------------------------------
# The analysis.
# ---------------------------------------------------------------------------


def run_analysis(
    rows: dict[str, dict[str, float]],
    questions: list[dict[str, Optional[str]]],
    samples: int,
    alpha: float,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    weight_samples = [sample_dirichlet(rng, alpha, len(TASK_FAMILIES))
                      for _ in range(samples)]
    weight_maps = [dict(zip(TASK_FAMILIES, w)) for w in weight_samples]

    baseline = composites_for(rows, EQUAL_WEIGHTS)
    perturbed = [composites_for(rows, wm) for wm in weight_maps]

    per_question: list[dict[str, Any]] = []
    scored = flagged = 0
    for q in questions:
        qid = q["id"]
        base_top = question_top_k(q, baseline)
        if base_top is None:
            per_question.append({
                "id": qid, "surface": q.get("surface"),
                "status": "no-anchor-data", "stability": None,
                "pct_samples_ge_4_of_5": None, "flagged": None,
            })
            continue
        if not base_top:
            per_question.append({
                "id": qid, "surface": q.get("surface"),
                "status": "empty-pool", "stability": None,
                "pct_samples_ge_4_of_5": None, "flagged": None,
            })
            continue
        base_set = set(base_top)
        denom = len(base_top)  # ≤ TOP_K when the pool is small
        overlaps: list[float] = []
        for comp in perturbed:
            top = question_top_k(q, comp) or []
            overlaps.append(len(base_set & set(top)) / denom)
        stability = sum(overlaps) / len(overlaps)
        pass_rate = sum(1 for o in overlaps if o >= OVERLAP_BAR) / len(overlaps)
        is_flagged = pass_rate < SAMPLE_PASS_RATE
        scored += 1
        flagged += int(is_flagged)
        per_question.append({
            "id": qid, "surface": q.get("surface"),
            "status": "scored",
            "baseline_top5": base_top,
            "stability": round(stability, 4),
            "pct_samples_ge_4_of_5": round(pass_rate, 4),
            "flagged": is_flagged,
        })

    question_pass_rate = ((scored - flagged) / scored) if scored else None
    return {
        "generatedAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "methodologySection": METHODOLOGY_SECTION,
        "parameters": {
            "samples": samples,
            "alpha": alpha,
            "alphaInterpretation": "symmetric per-component Dirichlet(α, α, α)",
            "seed": seed,
            "topK": TOP_K,
            "overlapBar": OVERLAP_BAR,
            "samplePassRate": SAMPLE_PASS_RATE,
            "questionPassRate": QUESTION_PASS_RATE,
        },
        "rowsWithSubScores": len(rows),
        "questionsTotal": len(questions),
        "questionsScored": scored,
        "questionsFlagged": flagged,
        "questionPassRateObserved": (
            round(question_pass_rate, 4) if question_pass_rate is not None else None
        ),
        "passes81Target": (
            question_pass_rate >= QUESTION_PASS_RATE
            if question_pass_rate is not None else None
        ),
        "perQuestion": per_question,
    }


# ---------------------------------------------------------------------------
# Artifact + main.
# ---------------------------------------------------------------------------


def artifact_path() -> Path:
    return BASELINES_DIR / f"composite-sensitivity-{date.today().isoformat()}.json"


def write_artifact(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Dirichlet weight-perturbation sensitivity analysis "
                    "(composite-methodology §8.1, issue #130).")
    ap.add_argument("--fixture", type=Path, default=None,
                    help="Row source instead of data/landscape.json "
                         "(landscape shape or simplified 'subscores' records).")
    ap.add_argument("--questions", type=Path, default=QUESTIONS_YML,
                    help="Path to canonical-questions.yml.")
    ap.add_argument("--samples", type=int, default=DEFAULT_SAMPLES,
                    help=f"Dirichlet samples (default {DEFAULT_SAMPLES}, per §8.1).")
    ap.add_argument("--alpha", type=float, default=DEFAULT_ALPHA,
                    help=f"Per-component concentration (default {DEFAULT_ALPHA}, per §8.1).")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help=f"RNG seed (default {DEFAULT_SEED}).")
    ap.add_argument("--out", type=Path, default=None,
                    help="Artifact path (default data/_baselines/"
                         "composite-sensitivity-YYYY-MM-DD.json).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Compute and print the summary; write no artifact.")
    args = ap.parse_args(argv)

    rows_path = args.fixture or LANDSCAPE_JSON
    rows = load_rows(rows_path)
    if not args.questions.exists():
        print(f"error: {args.questions} not found", file=sys.stderr)
        return 2
    questions = load_questions(args.questions)
    print(f"loaded {len(rows)} rows with composite data from {rows_path.name}, "
          f"{len(questions)} canonical questions")

    if not rows:
        # Expected until the first real sweep (#128) populates sub-score
        # cells. Exit cleanly, but still record the no-data state in the
        # artifact so the run leaves an operational trace.
        print("0 rows with composite data — sub-score cells are all no-data "
              "(first sweep #128 not merged yet). Nothing to perturb.")
        report = run_analysis({}, questions, args.samples, args.alpha, args.seed)
        if not args.dry_run:
            out = args.out or artifact_path()
            write_artifact(report, out)
            print(f"wrote: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
        return 0

    report = run_analysis(rows, questions, args.samples, args.alpha, args.seed)

    print(f"questions scored:  {report['questionsScored']}/{report['questionsTotal']}")
    print(f"questions flagged: {report['questionsFlagged']} "
          f"(top-5 churns in >{(1 - SAMPLE_PASS_RATE) * 100:.0f}% of samples)")
    if report["questionPassRateObserved"] is not None:
        verdict = "PASS" if report["passes81Target"] else "FAIL"
        print(f"§8.1 target (≥{QUESTION_PASS_RATE * 100:.0f}% of questions "
              f"with ≥4/5 overlap): {verdict} "
              f"({report['questionPassRateObserved'] * 100:.1f}%)")
    for pq in report["perQuestion"]:
        if pq.get("flagged"):
            print(f"  CHURN {pq['id']}: stability {pq['stability']:.2f}, "
                  f"≥4/5 overlap in {pq['pct_samples_ge_4_of_5'] * 100:.0f}% of samples")

    if args.dry_run:
        print("(dry-run — no artifact written)")
        return 0
    out = args.out or artifact_path()
    write_artifact(report, out)
    print(f"wrote: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
