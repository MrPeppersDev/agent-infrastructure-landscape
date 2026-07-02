"""
test_composite.py — parity test for scripts/_composite.py.

Mirrors the assertions in mcp/src/test-composite.ts so both
implementations of the composite formula are known to agree on a
golden fixture. If this file drifts from that one, they've drifted
out of sync — treat that as a build failure, not a "just fix the
Python side" nudge.

Run:  python3 scripts/test_composite.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _composite import (  # noqa: E402
    BAND_CUTOFFS,
    BenchmarkAnchor,
    BenchmarkObservation,
    TASK_FAMILIES,
    compute_composite,
    compute_family_score,
    compute_row,
    derive_band,
    normalize,
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


def close(actual, expected: float, label: str, eps: float = 1e-6) -> None:
    global tests_run
    tests_run += 1
    if actual is None:
        _fail(label, f"expected ≈{expected}, got None")
        return
    if abs(actual - expected) < eps:
        return
    _fail(label, f"expected ≈{expected}, got {actual}")


def is_none(actual, label: str) -> None:
    global tests_run
    tests_run += 1
    if actual is None:
        return
    _fail(label, f"expected None, got {actual!r}")


# ---- normalize ----
eq(normalize(50, BenchmarkAnchor(max=100)), 50, "normalize: midpoint")
eq(normalize(0, BenchmarkAnchor(max=100)), 0, "normalize: floor")
eq(normalize(100, BenchmarkAnchor(max=100)), 100, "normalize: ceiling")
eq(normalize(150, BenchmarkAnchor(max=100)), 100, "normalize: above ceiling clamps")
eq(normalize(-10, BenchmarkAnchor(max=100)), 0, "normalize: below floor clamps")
eq(normalize(75, BenchmarkAnchor(min=50, max=100)), 50, "normalize: with min")
eq(normalize(50, BenchmarkAnchor(max=0)), 0, "normalize: degenerate max ≤ min")
eq(normalize(float("nan"), BenchmarkAnchor(max=100)), 0, "normalize: NaN → 0")

# ---- compute_family_score ----
anchors = {
    "bench-a": BenchmarkAnchor(max=100),
    "bench-b": BenchmarkAnchor(max=100),
    "bench-c": BenchmarkAnchor(max=50),
}

close(
    compute_family_score(
        [
            BenchmarkObservation("bench-a", 80, 1.0, "code"),
            BenchmarkObservation("bench-b", 60, 1.0, "code"),
        ],
        anchors,
    ),
    70,
    "family: equal trust → mean",
)

close(
    compute_family_score(
        [
            BenchmarkObservation("bench-a", 80, 1.0, "code"),
            BenchmarkObservation("bench-b", 60, 0.5, "code"),
        ],
        anchors,
    ),
    (1.0 * 80 + 0.5 * 60) / 1.5,
    "family: unequal trust → weighted mean",
)

close(
    compute_family_score(
        [BenchmarkObservation("bench-c", 25, 1.0, "code")],
        anchors,
    ),
    50,
    "family: normalised per anchor max",
)

is_none(compute_family_score([], anchors), "family: empty → None")

is_none(
    compute_family_score(
        [BenchmarkObservation("bench-a", 80, 0, "code")],
        anchors,
    ),
    "family: zero trust → None",
)

is_none(
    compute_family_score(
        [BenchmarkObservation("unknown", 80, 1.0, "code")],
        anchors,
    ),
    "family: unknown anchor → None",
)

# ---- compute_composite ----
close(
    compute_composite({"code": 80, "agentic": 80, "longcontext": 80}),
    80,
    "composite: all equal",
)

close(
    compute_composite({"code": 100, "agentic": 25, "longcontext": 25}),
    (100 * 25 * 25) ** (1 / 3),
    "composite: geometric mean formula",
)

one_axis = compute_composite({"code": 100, "agentic": 25, "longcontext": 25})
tests_run += 1
if one_axis is None or one_axis >= 50:
    _fail(
        "composite: one-axis strength must be penalised below arithmetic mean",
        f"got {one_axis}",
    )

close(
    compute_composite({"code": 60, "agentic": None, "longcontext": None}),
    60,
    "composite: single present family",
)

close(
    compute_composite({"code": 80, "agentic": 50, "longcontext": None}),
    math.sqrt(80 * 50),
    "composite: two present families",
)

is_none(
    compute_composite({"code": None, "agentic": None, "longcontext": None}),
    "composite: all None → None",
)

eq(
    compute_composite({"code": 0, "agentic": 80, "longcontext": 80}),
    0,
    "composite: any zero collapses to 0",
)

# ---- derive_band ----
eq(derive_band(None), None, "band: None → None")
eq(derive_band(0), "entry", "band: 0 → entry")
eq(derive_band(BAND_CUTOFFS["competent"] - 0.1), "entry", "band: below competent")
eq(derive_band(BAND_CUTOFFS["competent"]), "competent", "band: at competent")
eq(derive_band(BAND_CUTOFFS["frontier"] - 0.1), "competent", "band: below frontier")
eq(derive_band(BAND_CUTOFFS["frontier"]), "frontier", "band: at frontier")
eq(derive_band(100), "frontier", "band: 100 → frontier")

# ---- compute_row ----
row_anchors = {
    "aider-polyglot": BenchmarkAnchor(max=100),
    "swe-bench-verified": BenchmarkAnchor(max=70),
    "gaia": BenchmarkAnchor(max=80),
    "ruler-128k": BenchmarkAnchor(max=95),
}
row_obs = [
    BenchmarkObservation("aider-polyglot", 70, 0.9, "code"),
    BenchmarkObservation("swe-bench-verified", 49, 0.85, "code"),
    BenchmarkObservation("gaia", 40, 0.8, "agentic"),
    BenchmarkObservation("ruler-128k", 76, 0.85, "longcontext"),
]
row = compute_row(row_obs, row_anchors)

eq(row.benchmark_count["code"], 2, "row: code count")
eq(row.benchmark_count["agentic"], 1, "row: agentic count")
eq(row.benchmark_count["longcontext"], 1, "row: longcontext count")
close(row.by_family["code"], 70, "row: code sub-score")
close(row.by_family["agentic"], 50, "row: agentic sub-score")
close(row.by_family["longcontext"], 80, "row: longcontext sub-score")
close(row.composite, (70 * 50 * 80) ** (1 / 3), "row: composite")
eq(row.band, "competent", "row: band")

# ---- TASK_FAMILIES ----
eq(len(TASK_FAMILIES), 3, "task families: count")
eq("code" in TASK_FAMILIES, True, "task families: code")
eq("agentic" in TASK_FAMILIES, True, "task families: agentic")
eq("longcontext" in TASK_FAMILIES, True, "task families: longcontext")

print(f"\n_composite tests: {tests_run - tests_failed}/{tests_run} passed")
if tests_failed > 0:
    sys.exit(1)
