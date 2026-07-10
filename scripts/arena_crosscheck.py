#!/usr/bin/env python3
"""
arena_crosscheck.py — Arena external-validity cross-check (issue #131).

Per docs/composite-methodology.md §8.2: for the subset of catalog rows
that also appear on Chatbot Arena's leaderboard (foundation models,
identified via the curated data/arena-mapping.json), compute Spearman ρ
between our capability composite and Arena's Elo. Target ρ ≥ 0.7 on
the overlapping set.

REPORT-ONLY: strong disagreement flags either a methodology problem or
an interesting finding. This script never adjusts composites, weights,
or the mapping — it only reports. It also always exits 0 on a clean
run; low ρ is a finding, not a failure.

NETWORK-FREE: Arena Elo values are a point-in-time snapshot frozen in
data/arena-mapping.json (see its `_meta.elo_snapshot` for retrieval
date and sources). The script never fetches the network at runtime —
repo convention is network-free CI. Refreshing Elo = editing the file.

Composite eligibility
---------------------
A mapped row contributes a data point only when its composite is
sweep-backed: `capability-composite-score` parses as a number AND at
least one of the three sub-score cells (`capability-code-score`,
`capability-agentic-score`, `capability-longcontext-score`) is
non-`no-data` with a numeric value. Rationale: the geometric-mean
composite (scripts/_composite.py) is only defined over present family
scores, so a composite with zero sub-scores cannot have come from the
sweep pipeline — it is a pre-sweep hand estimate. Until the first
sweep (#128) lands, this yields "0 mapped rows with composite data",
which is the expected clean result. Pass --include-estimates to
preview ρ against the unverified pre-sweep estimates (clearly labeled;
never the default).

Spearman ρ is implemented stdlib-only: rank transform with average
ranks for ties, then Pearson correlation on the ranks.

Usage
-----
    python3 scripts/arena_crosscheck.py                     # real-data run
    python3 scripts/arena_crosscheck.py --include-estimates # preview vs pre-sweep estimates
    python3 scripts/arena_crosscheck.py --top 10            # show 10 largest divergences
    python3 scripts/arena_crosscheck.py --self-test         # synthetic-fixture tests only
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = REPO_ROOT / "data" / "landscape.json"
ARENA_MAPPING_JSON = REPO_ROOT / "data" / "arena-mapping.json"

SUBSCORE_SLUGS = (
    "capability-code-score",
    "capability-agentic-score",
    "capability-longcontext-score",
)
COMPOSITE_SLUG = "capability-composite-score"

RHO_TARGET = 0.7  # methodology §8.2


# ---------------------------------------------------------------------------
# Spearman ρ (stdlib-only)
# ---------------------------------------------------------------------------

def average_ranks(values: Sequence[float]) -> list[float]:
    """1-based ranks; ties receive the average of the ranks they span."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # average of 1-based ranks i+1 .. j+1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = sum((x - mx) ** 2 for x in xs)
    sy = sum((y - my) ** 2 for y in ys)
    if sx == 0 or sy == 0:
        return None  # a constant series has no defined correlation
    return cov / math.sqrt(sx * sy)


def spearman_rho(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Spearman ρ via average-rank transform + Pearson on ranks."""
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    return pearson(average_ranks(xs), average_ranks(ys))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_number(raw: object) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def row_composite(rec: dict, include_estimates: bool) -> Optional[float]:
    """Return the row's composite score if eligible, else None.

    Default eligibility = sweep-backed (see module docstring). With
    include_estimates, any numeric composite counts.
    """
    cells = rec.get("cells", {})
    comp_cell = cells.get(COMPOSITE_SLUG) or {}
    comp = parse_number(comp_cell.get("value"))
    if comp is None or comp_cell.get("status") == "no-data":
        return None
    if include_estimates:
        return comp
    for slug in SUBSCORE_SLUGS:
        sub = cells.get(slug) or {}
        if sub.get("status") != "no-data" and parse_number(sub.get("value")) is not None:
            return comp
    return None


def run_crosscheck(include_estimates: bool, top: int) -> int:
    landscape = json.loads(LANDSCAPE_JSON.read_text())
    mapping = json.loads(ARENA_MAPPING_JSON.read_text())
    mappings: dict = mapping["mappings"]
    unmapped: dict = mapping["unmapped"]
    snapshot = mapping.get("_meta", {}).get("elo_snapshot", {})

    by_id = {rec["id"]: rec for rec in landscape["records"]}
    missing = [rid for rid in mappings if rid not in by_id]
    if missing:
        print(f"WARNING: {len(missing)} mapped row id(s) not found in landscape.json: {missing}")

    points: list[tuple[str, str, float, float]] = []  # (row_id, arena_model, composite, elo)
    mapped_without_data: list[str] = []
    for rid, m in mappings.items():
        rec = by_id.get(rid)
        if rec is None:
            continue
        comp = row_composite(rec, include_estimates)
        if comp is None:
            mapped_without_data.append(rid)
        else:
            points.append((rid, m["arena_model"], comp, float(m["arena_elo"])))

    mode = "estimates preview (--include-estimates; UNVERIFIED pre-sweep values)" \
        if include_estimates else "sweep-backed composites only"
    print("Arena external-validity cross-check (methodology §8.2, issue #131)")
    print(f"  Elo snapshot: retrieved {snapshot.get('retrieved', '?')} "
          f"({snapshot.get('precision', 'precision unknown').split('.')[0]})")
    print(f"  Mode: {mode}")
    print(f"  Foundation-model rows mapped to Arena: {len(mappings)}; "
          f"unmapped (with rationale in data/arena-mapping.json): {len(unmapped)}")

    if not points:
        print(f"  Result: 0 mapped rows with composite data — nothing to correlate yet "
              f"(first capability sweep, #128, pending). Exiting cleanly.")
        return 0

    if len(points) < 2:
        print(f"  Result: only {len(points)} mapped row(s) with composite data; "
              f"ρ requires n ≥ 2. Exiting cleanly.")
        return 0

    comps = [p[2] for p in points]
    elos = [p[3] for p in points]
    rho = spearman_rho(comps, elos)
    n = len(points)
    if rho is None:
        print(f"  Result: ρ undefined on n={n} (constant series). Exiting cleanly.")
        return 0

    print(f"  Spearman ρ = {rho:.3f} (n = {n})")
    if mapped_without_data:
        print(f"  Mapped rows excluded for lack of composite data: {len(mapped_without_data)}")

    # Largest per-row divergences: |rank(composite) - rank(elo)|.
    comp_ranks = average_ranks(comps)
    elo_ranks = average_ranks(elos)
    divergences = sorted(
        (
            (abs(cr - er), rid, model, comp, elo, cr, er)
            for (rid, model, comp, elo), cr, er in zip(points, comp_ranks, elo_ranks)
        ),
        reverse=True,
    )
    print(f"  Largest per-row divergences (rank gap; composite rank vs Elo rank):")
    for gap, rid, model, comp, elo, cr, er in divergences[:top]:
        print(f"    {gap:4.1f}  {rid}  ({model})  "
              f"composite {comp:.1f} [rank {cr:.1f}]  vs  Elo {elo:.0f} [rank {er:.1f}]")

    if rho < RHO_TARGET:
        print(f"  FLAG: ρ = {rho:.3f} < target {RHO_TARGET} (methodology §8.2). "
              f"This flags a methodology re-review or an interesting finding to report — "
              f"it does NOT auto-adjust the composite, weights, or mapping.")
    else:
        print(f"  ρ meets the §8.2 target (≥ {RHO_TARGET}).")
    return 0


# ---------------------------------------------------------------------------
# Synthetic-fixture self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    failures = 0

    def check(name: str, got, want, tol=1e-9):
        nonlocal failures
        ok = (got is None and want is None) or (
            got is not None and want is not None and abs(got - want) <= tol
        )
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r}, want {want!r}")
        if not ok:
            failures += 1

    # 1. Perfect monotone agreement / disagreement.
    check("perfect positive", spearman_rho([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
    check("perfect negative", spearman_rho([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)

    # 2. Hand-computed example WITH ties.
    #    x = [1,2,3,4,5] -> ranks [1,2,3,4,5]
    #    y = [5,6,7,8,7] -> ranks [1,2,3.5,5,3.5]  (two 7s share (3+4)/2)
    #    Pearson on ranks: means are both 3;
    #    cov·n = (-2)(-2)+(-1)(-1)+0(0.5)+1(2)+2(0.5) = 8
    #    Σdx² = 10, Σdy² = 4+1+0.25+4+0.25 = 9.5
    #    ρ = 8 / sqrt(10·9.5) = 8 / sqrt(95)
    check("hand-computed with ties", spearman_rho([1, 2, 3, 4, 5], [5, 6, 7, 8, 7]),
          8.0 / math.sqrt(95.0))

    # 3. Classic textbook example without ties (Spearman via d²:
    #    ρ = 1 - 6Σd²/(n(n²-1)) = 1 - 6·193/990 = -29/165).
    x3 = [106, 100, 86, 101, 99, 103, 97, 113, 112, 110]
    y3 = [7, 27, 2, 50, 28, 29, 20, 12, 6, 17]
    check("textbook n=10 no ties", spearman_rho(x3, y3), -29.0 / 165.0)

    # 4. Tie handling in average_ranks itself.
    got_ranks = average_ranks([10, 20, 20, 30])
    want_ranks = [1.0, 2.5, 2.5, 4.0]
    ok = got_ranks == want_ranks
    print(f"  {'PASS' if ok else 'FAIL'}  average ranks with ties: got {got_ranks}, want {want_ranks}")
    failures += 0 if ok else 1

    # 5. Degenerate inputs return None (never crash).
    check("n=1 undefined", spearman_rho([1], [2]), None)
    check("constant series undefined", spearman_rho([5, 5, 5], [1, 2, 3]), None)

    # 6. End-to-end on a synthetic fixture shaped like the real inputs:
    #    5 mapped rows, one with a no-data composite, one estimate-only.
    fixture_rows = {
        "records": [
            {"id": "row-a", "cells": {
                COMPOSITE_SLUG: {"value": "90", "status": "estimate"},
                "capability-code-score": {"value": "88", "status": "estimate"}}},
            {"id": "row-b", "cells": {
                COMPOSITE_SLUG: {"value": "80", "status": "estimate"},
                "capability-code-score": {"value": "79", "status": "estimate"}}},
            {"id": "row-c", "cells": {
                COMPOSITE_SLUG: {"value": "70", "status": "estimate"},
                "capability-agentic-score": {"value": "70", "status": "estimate"}}},
            {"id": "row-d", "cells": {  # no-data composite -> excluded
                COMPOSITE_SLUG: {"value": "", "status": "no-data"}}},
            {"id": "row-e", "cells": {  # pre-sweep estimate, no sub-scores -> excluded by default
                COMPOSITE_SLUG: {"value": "60", "status": "estimate"},
                "capability-code-score": {"value": "", "status": "no-data"}}},
        ]
    }
    by_id = {r["id"]: r for r in fixture_rows["records"]}
    elos = {"row-a": 1500, "row-b": 1400, "row-c": 1450, "row-d": 1300, "row-e": 1200}
    pts = []
    for rid, elo in elos.items():
        comp = row_composite(by_id[rid], include_estimates=False)
        if comp is not None:
            pts.append((comp, float(elo)))
    ok = len(pts) == 3
    print(f"  {'PASS' if ok else 'FAIL'}  fixture eligibility: {len(pts)}/5 rows eligible, want 3")
    failures += 0 if ok else 1
    # composites [90,80,70] vs elos [1500,1400,1450]: ranks [3,2,1] vs [3,1,2] -> ρ = 0.5
    check("fixture end-to-end ρ", spearman_rho([p[0] for p in pts], [p[1] for p in pts]), 0.5)

    total = 9
    print(f"self-test: {total - failures}/{total} passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--self-test", action="store_true",
                    help="run synthetic-fixture tests for the ρ computation and exit")
    ap.add_argument("--include-estimates", action="store_true",
                    help="preview: include unverified pre-sweep estimate composites")
    ap.add_argument("--top", type=int, default=5,
                    help="number of largest per-row divergences to show (default 5)")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    return run_crosscheck(args.include_estimates, args.top)


if __name__ == "__main__":
    sys.exit(main())
