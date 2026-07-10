"""
test_composite_sensitivity.py — unit / fixture tests for
scripts/composite_sensitivity.py (issue #130).

Sub-score cells in the real landscape.json are all `no-data` until the
first sweep (#128) merges, so correctness is proven here on a synthetic
fixture with a seeded RNG. Same plain-assert style as test_composite.py.

Run:  python3 scripts/test_composite_sensitivity.py
"""

from __future__ import annotations

import json
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _composite import compute_composite  # noqa: E402
from composite_sensitivity import (  # noqa: E402
    EQUAL_WEIGHTS,
    load_questions,
    load_rows,
    main,
    question_top_k,
    run_analysis,
    sample_dirichlet,
    weighted_composite,
)

tests_run = 0
tests_failed = 0


def _fail(label: str, msg: str) -> None:
    global tests_failed
    tests_failed += 1
    print(f"FAIL  {label}\n  {msg}", file=sys.stderr)


def eq(actual, expected, label: str) -> None:
    global tests_run
    tests_run += 1
    if actual == expected:
        return
    _fail(label, f"expected {expected!r}, got {actual!r}")


def close(actual, expected: float, label: str, eps: float = 1e-9) -> None:
    global tests_run
    tests_run += 1
    if actual is None:
        _fail(label, f"expected ≈{expected}, got None")
        return
    if abs(actual - expected) < eps:
        return
    _fail(label, f"expected ≈{expected}, got {actual}")


def ok(cond: bool, label: str, msg: str = "") -> None:
    global tests_run
    tests_run += 1
    if not cond:
        _fail(label, msg or "condition false")


# ---- sample_dirichlet ----
rng = random.Random(42)
w = sample_dirichlet(rng, 10.0)
eq(len(w), 3, "dirichlet: 3 components")
close(sum(w), 1.0, "dirichlet: sums to 1")
ok(all(0 < x < 1 for x in w), "dirichlet: components in (0,1)")

rng_a, rng_b = random.Random(7), random.Random(7)
eq(
    [sample_dirichlet(rng_a, 10.0) for _ in range(5)],
    [sample_dirichlet(rng_b, 10.0) for _ in range(5)],
    "dirichlet: deterministic under a fixed seed",
)

rng = random.Random(0)
draws = [sample_dirichlet(rng, 10.0) for _ in range(3000)]
mean0 = sum(d[0] for d in draws) / len(draws)
ok(abs(mean0 - 1 / 3) < 0.01, "dirichlet: mean ≈ 1/3 for α=10",
   f"mean {mean0}")
sd0 = (sum((d[0] - mean0) ** 2 for d in draws) / len(draws)) ** 0.5
# Dirichlet(10,10,10): sd = sqrt((1/3)(2/3)/31) ≈ 0.0846
ok(abs(sd0 - 0.0846) < 0.01, "dirichlet: sd ≈ 0.085 for α=10", f"sd {sd0}")

# ---- weighted_composite ----
subs = {"code": 70.0, "agentic": 50.0, "longcontext": 80.0}
close(
    weighted_composite(subs, EQUAL_WEIGHTS),
    compute_composite({"code": 70.0, "agentic": 50.0, "longcontext": 80.0}),
    "weighted: equal weights reproduce §7.2 compute_composite",
)
close(
    weighted_composite({"code": 70.0}, EQUAL_WEIGHTS), 70.0,
    "weighted: single family renormalises to that family",
)
close(
    weighted_composite({"code": 64.0, "agentic": 4.0},
                       {"code": 0.75, "agentic": 0.25, "longcontext": 0.0}),
    (64.0 ** 0.75 * 4.0 ** 0.25),
    "weighted: renormalised weighted geometric mean",
)
eq(weighted_composite({"code": 0.0, "agentic": 90.0}, EQUAL_WEIGHTS), 0.0,
   "weighted: zero sub-score collapses to 0 (§7.2 rule)")
eq(weighted_composite({}, EQUAL_WEIGHTS), None, "weighted: no families → None")

# skew toward code should pull the composite toward the code sub-score
skew = weighted_composite(subs, {"code": 0.8, "agentic": 0.1, "longcontext": 0.1})
base = weighted_composite(subs, EQUAL_WEIGHTS)
ok(abs(skew - 70.0) < abs(base - 70.0), "weighted: skew moves toward code score")

# ---- load_questions (mini YAML parser) ----
yaml_snippet = """\
# header comment
- id: q-between
  text: "what sits between A and B?"
  category: positioning
  surface: between
  inputs:
    anchor_low_id: row-low
    anchor_high_id: row-high
    use_case: scoped-agentic
  notes: |
    anchor_low_id: decoy-inside-block-scalar
- id: q-constraints
  surface: by-constraints
  inputs:
    structured:
      project_shape: multi-agent
"""
with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as fh:
    fh.write(yaml_snippet)
    yml_path = Path(fh.name)
qs = load_questions(yml_path)
eq(len(qs), 2, "questions: two entries parsed")
eq(qs[0]["id"], "q-between", "questions: first id")
eq(qs[0]["surface"], "between", "questions: surface")
eq(qs[0]["anchor_low_id"], "row-low", "questions: anchor low")
eq(qs[0]["anchor_high_id"], "row-high", "questions: anchor high")
eq(qs[1]["id"], "q-constraints", "questions: second id")
eq(qs[1]["anchor_low_id"], None, "questions: constraints entry has no anchors")
yml_path.unlink()

# real file: 55 canonical questions, all with a surface
real_qs = load_questions(Path(__file__).resolve().parent.parent
                         / "docs" / "canonical-questions.yml")
eq(len(real_qs), 55, "questions: real canonical-questions.yml has 55 entries")
eq(sum(1 for q in real_qs if q["surface"] is None), 0,
   "questions: every real entry has a surface")

# ---- load_rows: landscape cell shape + simplified fixture shape ----
landscape_shape = {
    "records": [
        {
            "id": "cell-row",
            "cells": {
                "capability-code-score": {"value": "72.5", "status": "estimate"},
                "capability-agentic-score": {"value": "", "status": "no-data"},
                "capability-longcontext-score": {"value": "61", "status": "estimate"},
            },
        },
        {  # all no-data → excluded
            "id": "empty-row",
            "cells": {
                "capability-code-score": {"value": "", "status": "no-data"},
            },
        },
        {"id": "simple-row", "subscores": {"code": 80, "agentic": 75}},
    ]
}
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
    json.dump(landscape_shape, fh)
    rows_path = Path(fh.name)
rows = load_rows(rows_path)
eq(set(rows), {"cell-row", "simple-row"}, "rows: no-data rows excluded")
eq(rows["cell-row"], {"code": 72.5, "longcontext": 61.0}, "rows: cell parse")
eq(rows["simple-row"], {"code": 80.0, "agentic": 75.0}, "rows: fixture parse")
rows_path.unlink()

# ---- question_top_k ----
composites = {"a": 90.0, "b": 80.0, "c": 70.0, "d": 60.0, "e": 50.0,
              "f": 40.0, "lo": 45.0, "hi": 85.0}
q_between = {"id": "qb", "surface": "between",
             "anchor_low_id": "lo", "anchor_high_id": "hi"}
eq(question_top_k(q_between, composites), ["b", "c", "d", "e"],
   "top-k: between pool is strict interior, anchors excluded")
q_all = {"id": "qa", "surface": "by-constraints",
         "anchor_low_id": None, "anchor_high_id": None}
eq(question_top_k(q_all, composites), ["a", "hi", "b", "c", "d"],
   "top-k: by-constraints ranks the full pool")
q_missing = {"id": "qm", "surface": "between",
             "anchor_low_id": "lo", "anchor_high_id": "nonexistent"}
eq(question_top_k(q_missing, composites), None,
   "top-k: missing anchor data → None")
eq(question_top_k(q_all, {"x": 50.0, "y": 50.0, "z": 50.0}), ["x", "y", "z"],
   "top-k: ties broken by id (deterministic)")

# ---- run_analysis: end-to-end on a synthetic fixture ----
# STABLE regime: sub-scores balanced across families and top-5 separated
# by wide gaps — no plausible Dirichlet(10) draw reorders across a gap.
stable_rows = {
    f"s{i}": {"code": v, "agentic": v, "longcontext": v}
    for i, v in enumerate([95.0, 85.0, 75.0, 65.0, 55.0, 45.0, 35.0, 25.0])
}
# CHURN regime: baseline top-5 is five balanced rows at ~53; two
# code-skewed challengers sit just below at ~52 with composite
# 42·(80/42)^w_code — any draw with w_code ≳ 0.373 (≈ a third of
# Dirichlet(10) samples) promotes BOTH, dropping overlap to 3/5.
churn_rows = {
    "b1": {"code": 53.4, "agentic": 53.4, "longcontext": 53.4},
    "b2": {"code": 53.3, "agentic": 53.3, "longcontext": 53.3},
    "b3": {"code": 53.2, "agentic": 53.2, "longcontext": 53.2},
    "b4": {"code": 53.1, "agentic": 53.1, "longcontext": 53.1},
    "b5": {"code": 53.0, "agentic": 53.0, "longcontext": 53.0},
    "k1": {"code": 80.0, "agentic": 42.0, "longcontext": 42.0},  # ≈ 52.06
    "k2": {"code": 81.0, "agentic": 42.0, "longcontext": 42.0},  # ≈ 52.28
}
q_stable = {"id": "q-stable", "surface": "by-constraints",
            "anchor_low_id": None, "anchor_high_id": None}
q_churn = {"id": "q-churn", "surface": "by-constraints",
           "anchor_low_id": None, "anchor_high_id": None}

rep = run_analysis(stable_rows, [q_stable], samples=100, alpha=10.0, seed=130)
eq(rep["questionsScored"], 1, "e2e stable: scored")
eq(rep["questionsFlagged"], 0, "e2e stable: not flagged")
pq = rep["perQuestion"][0]
eq(pq["baseline_top5"], ["s0", "s1", "s2", "s3", "s4"], "e2e stable: baseline top-5")
close(pq["stability"], 1.0, "e2e stable: stability 1.0")
eq(rep["passes81Target"], True, "e2e stable: §8.1 target passes")

rep2 = run_analysis(churn_rows, [q_churn], samples=100, alpha=10.0, seed=130)
pq2 = rep2["perQuestion"][0]
ok(pq2["stability"] < 1.0, "e2e churn: stability below 1.0",
   f"stability {pq2['stability']}")
eq(pq2["flagged"], True, "e2e churn: flagged")
eq(rep2["questionsFlagged"], 1, "e2e churn: flag counted")
eq(rep2["passes81Target"], False, "e2e churn: §8.1 target fails")

# determinism: same seed → identical report bodies (minus timestamp)
rep3 = run_analysis(churn_rows, [q_churn], samples=100, alpha=10.0, seed=130)
rep2b, rep3b = dict(rep2), dict(rep3)
rep2b.pop("generatedAt"), rep3b.pop("generatedAt")
eq(rep2b, rep3b, "e2e: deterministic under fixed seed")

# between-question with anchors that lack sub-score data → no-anchor-data
q_bad = {"id": "q-bad", "surface": "between",
         "anchor_low_id": "ghost-a", "anchor_high_id": "ghost-b"}
rep4 = run_analysis(stable_rows, [q_bad], samples=10, alpha=10.0, seed=1)
eq(rep4["perQuestion"][0]["status"], "no-anchor-data",
   "e2e: missing anchors reported, not crashed")
eq(rep4["questionsScored"], 0, "e2e: no-anchor question not counted as scored")

# empty rows → clean zero report
rep5 = run_analysis({}, [q_stable, q_churn], samples=10, alpha=10.0, seed=1)
eq(rep5["rowsWithSubScores"], 0, "e2e empty: 0 rows")
eq(rep5["questionsScored"], 0, "e2e empty: nothing scored")
eq(rep5["passes81Target"], None, "e2e empty: verdict is None")

# ---- CLI: --fixture end-to-end, --dry-run, exit code 0 ----
fixture = {"records": [
    {"id": rid, "subscores": subs} for rid, subs in stable_rows.items()
]}
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
    json.dump(fixture, fh)
    fixture_path = Path(fh.name)
rc = main(["--fixture", str(fixture_path), "--samples", "20",
           "--seed", "130", "--dry-run"])
eq(rc, 0, "cli: fixture dry-run exits 0")
fixture_path.unlink()

print(f"\ncomposite_sensitivity tests: {tests_run - tests_failed}/{tests_run} passed")
if tests_failed > 0:
    sys.exit(1)
