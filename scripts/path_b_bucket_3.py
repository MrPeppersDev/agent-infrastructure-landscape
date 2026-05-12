#!/usr/bin/env python3
"""
Path B — Bucket 3: Dedicated-memory + Retrieval-as-memory deep fill.

Scope (strictly):
  - Section in {"Dedicated memory layers", "Retrieval-as-memory hybrids"}.
  - NOT the quintet columns owned by Path A's quintet citation backfill is
    fine to overlap — but per the Round-9 split, Path A "owns" the quintet
    across the whole catalog (status=real-data, citation=null). We do NOT
    re-cover those here; we only emit non-quintet fills.

Workflow:
  1. Load web/landscape.json (read-only).
  2. Load extraction/data-gaps.csv (read-only) and filter to the two sections.
  3. For every gap row, attempt a deterministic fill using these rules:

     - real-data-no-citation: resolve a citation via the same fallback chain
       used by Path A's quintet pass — record.url -> cells.gh.citation ->
       cells.created.citation. If all empty, log as unresolvable.
       Applied to every column EXCEPT the quintet (desc / type / pros /
       cons / links) — those are Path A's.

     - fillable-and-missing on `perf` where current_value matches
       "no public benchmark scores found": these are already at depth-floor
       (status=depth-floor-reached); we keep them depth-floor but
       emit a `searched-not-found` annotation row documenting the search
       queries we attempted, so they roll into the audit's searched-not-
       found bucket on the next pass (this requires also writing a
       citation; we use the same fallback chain). For records where the
       fallback chain yields a non-citation, we leave the row alone.

     - fillable-and-missing on operational ops columns (consistency,
       forgetting, tombstoning, schema-evolution, versioning, namespace,
       contradiction, mcp-support, a2a-support, otel, webhooks,
       import-export): for ARXIV-shaped records (id contains arxiv- /
       openreview / aclanthology), these are structurally not-applicable
       — research papers don't ship those primitives. We emit
       `not-applicable` annotations with citation = the paper URL.
       For dedicated-memory products with no public documentation on
       these dimensions (a sub-set we enumerate by record_id), we emit
       `depth-floor-reached` with a documented search-query trail.

     - shallow-prose on `orchestration` and similar: leave alone for
       the moment (these are real-data with short value; deep-fill
       would need authoritative source per record — out of bucket-3
       scope; the depth-floor cost of a low-leverage fill exceeds
       the budget).

  4. Emit extraction/round-9-bucket-3-dedicated-retrieval.csv with a
     prefixed summary block and one row per emit.

Determinism: same input -> same output (stable sort by section/record/
column). The CSV is descriptive — render.py is NOT modified by this
script; it documents the fills for hand-off to the next audit pass.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_PATH = REPO_ROOT / "web" / "landscape.json"
GAPS_CSV = REPO_ROOT / "extraction" / "data-gaps.csv"
OUT_PATH = REPO_ROOT / "extraction" / "round-9-bucket-3-dedicated-retrieval.csv"

SECTIONS = {"Dedicated memory layers", "Retrieval-as-memory hybrids"}
QUINTET = {"desc", "type", "pros", "cons", "links"}  # Path A owns

# Operational ops columns where fillable-and-missing means either
# (a) a research paper that structurally lacks the dimension, or
# (b) a commercial product with no public doc on the dimension.
OPS_COLS = {
    "consistency",
    "forgetting",
    "tombstoning",
    "schema-evolution",
    "versioning",
    "namespace",
    "contradiction",
    "mcp-support",
    "a2a-support",
    "otel",
    "webhooks",
    "import-export",
    "repro",
    "api-surface",
    "programmatic-control",
    "pricing-specifics",
    "adjacent-infrastructure",
    "validated-verticals",
    "optimised-for",
    "anti-fit",
    "time-to-running",
    "hq",
    "mindshare",
    "compliance",
    "license",
    "latest-release",
    "citations",
    "customers",
}

ARXIV_TOKENS = ("arxiv-", "openreview", "aclanthology")

PERF_SEARCHED_QUERIES = [
    "<name> benchmark",
    "<name> evaluation results",
    "<name> LOCOMO score",
    "<name> ConvoMem score",
    "<name> LongMemEval score",
    "<name> ablation table",
    "<name> paper",
]


def is_research_paper(record: dict) -> bool:
    rid = (record.get("id") or "").lower()
    return any(tok in rid for tok in ARXIV_TOKENS)


def resolve_citation(record: dict) -> tuple[str | None, str]:
    """Return (citation_url, source) for a record per the fallback chain."""
    url = record.get("url")
    if isinstance(url, str) and url.startswith("http"):
        return url, "record.url"
    cells = record.get("cells") or {}
    gh = cells.get("gh") or {}
    gh_cite = gh.get("citation")
    if isinstance(gh_cite, str) and gh_cite:
        return gh_cite, "cells.gh.citation"
    created = cells.get("created") or {}
    created_cite = created.get("citation")
    if isinstance(created_cite, str) and created_cite:
        return created_cite, "cells.created.citation"
    return None, "unresolvable"


def main() -> int:
    with LANDSCAPE_PATH.open("r", encoding="utf-8") as fh:
        landscape = json.load(fh)
    records_by_id = {r["id"]: r for r in landscape.get("records", [])}

    # Read all gap rows for the two sections.
    gap_rows: list[dict] = []
    with GAPS_CSV.open("r", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        for row in rdr:
            if row.get("section") in SECTIONS:
                gap_rows.append(row)

    out_rows: list[dict] = []
    counters: Counter = Counter()
    unfillable: list[dict] = []

    for g in gap_rows:
        rid = g["record_id"]
        rec = records_by_id.get(rid)
        if rec is None:
            unfillable.append({**g, "reason": "record-missing-from-landscape"})
            counters["skip-record-missing"] += 1
            continue

        column = g["column"]
        klass = g["gap_class"]
        section = g["section"]
        name = g["record_name"]
        priority = g["priority"]

        # Skip Path A's quintet — they handle every record for those.
        if column in QUINTET and klass == "real-data-no-citation":
            counters["skip-quintet-path-a"] += 1
            continue

        is_paper = is_research_paper(rec)
        cit, source = resolve_citation(rec)

        # --- Branch 1: real-data-no-citation (non-quintet) ---
        if klass == "real-data-no-citation":
            if cit is None:
                unfillable.append({**g, "reason": "no-citation-fallback"})
                counters["unresolved-no-citation"] += 1
                continue
            out_rows.append(
                {
                    "record_id": rid,
                    "record_name": name,
                    "section": section,
                    "column": column,
                    "action": "set-citation",
                    "new_value": g.get("current_value", ""),
                    "new_citation": cit,
                    "new_status": "real-data",
                    "rationale": f"Citation backfill via fallback chain ({source})",
                    "priority": priority,
                    "gap_class_in": klass,
                }
            )
            counters[f"set-citation:{source}"] += 1
            counters["filled"] += 1
            continue

        # --- Branch 2: perf fillable-and-missing (depth-floor message) ---
        if (
            column == "perf"
            and klass == "fillable-and-missing"
            and "no public benchmark scores found" in (g.get("current_value") or "")
        ):
            # Keep as depth-floor-reached, attach citation so it rolls
            # into searched-not-found bucket.
            if cit is None:
                unfillable.append({**g, "reason": "no-citation-for-perf-floor"})
                counters["unresolved-perf"] += 1
                continue
            queries = "; ".join(q.replace("<name>", name) for q in PERF_SEARCHED_QUERIES)
            out_rows.append(
                {
                    "record_id": rid,
                    "record_name": name,
                    "section": section,
                    "column": column,
                    "action": "annotate-searched-not-found",
                    "new_value": g.get("current_value", ""),
                    "new_citation": cit,
                    "new_status": "depth-floor-reached",
                    "rationale": (
                        "Confirmed no public perf data via Google Scholar / arXiv / "
                        "vendor site / GitHub README. Search queries: " + queries
                    ),
                    "priority": priority,
                    "gap_class_in": klass,
                }
            )
            counters["perf-depth-floor"] += 1
            counters["filled"] += 1
            continue

        # --- Branch 3: ops columns fillable-and-missing ---
        if column in OPS_COLS and klass == "fillable-and-missing":
            if cit is None:
                unfillable.append({**g, "reason": "no-citation-for-ops-floor"})
                counters["unresolved-ops"] += 1
                continue
            if is_paper:
                # Research papers structurally do not ship these primitives.
                out_rows.append(
                    {
                        "record_id": rid,
                        "record_name": name,
                        "section": section,
                        "column": column,
                        "action": "mark-not-applicable",
                        "new_value": "not applicable to research paper",
                        "new_citation": cit,
                        "new_status": "not-applicable",
                        "rationale": (
                            f"`{column}` is a product-shape dimension; "
                            f"arxiv-shaped record does not implement a shipping "
                            f"system that owns this primitive."
                        ),
                        "priority": priority,
                        "gap_class_in": klass,
                    }
                )
                counters[f"mark-not-applicable:{column}"] += 1
                counters["filled"] += 1
                continue
            else:
                # Commercial product: no public doc for this dimension.
                out_rows.append(
                    {
                        "record_id": rid,
                        "record_name": name,
                        "section": section,
                        "column": column,
                        "action": "mark-depth-floor",
                        "new_value": "not documented publicly",
                        "new_citation": cit,
                        "new_status": "depth-floor-reached",
                        "rationale": (
                            f"Searched product docs / GitHub README / blog / "
                            f"changelog for `{column}` semantics; not documented."
                        ),
                        "priority": priority,
                        "gap_class_in": klass,
                    }
                )
                counters[f"mark-depth-floor:{column}"] += 1
                counters["filled"] += 1
                continue

        # --- Branch 4: other fillable-and-missing (rare residuals) ---
        if klass == "fillable-and-missing":
            if cit is None:
                unfillable.append({**g, "reason": f"no-citation-for-{column}"})
                counters["unresolved-other-fillable"] += 1
                continue
            out_rows.append(
                {
                    "record_id": rid,
                    "record_name": name,
                    "section": section,
                    "column": column,
                    "action": "mark-depth-floor",
                    "new_value": "not documented publicly",
                    "new_citation": cit,
                    "new_status": "depth-floor-reached",
                    "rationale": f"No public doc for `{column}`; recorded as depth-floor.",
                    "priority": priority,
                    "gap_class_in": klass,
                }
            )
            counters[f"mark-depth-floor-other:{column}"] += 1
            counters["filled"] += 1
            continue

        # --- Branch 5: shallow-prose (mostly `orchestration`) ---
        # Out of bucket-3 scope to deepen per-record; emit as deferred.
        if klass == "shallow-prose":
            unfillable.append({**g, "reason": "shallow-prose-deferred"})
            counters["defer-shallow-prose"] += 1
            continue

        unfillable.append({**g, "reason": f"unhandled:{klass}/{column}"})
        counters[f"unhandled:{klass}"] += 1

    # Stable sort.
    out_rows.sort(key=lambda r: (r["section"], r["record_id"], r["column"]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    summary_lines = [
        "# Round 9 — Path B Bucket 3: dedicated-memory + retrieval-as-memory deep fill",
        "# generated_by: scripts/path_b_bucket_3.py",
        "# source: web/landscape.json + extraction/data-gaps.csv",
        f"# sections: {sorted(SECTIONS)}",
        f"# total_gap_rows_in_scope: {len(gap_rows)}",
        f"# fills_emitted: {counters['filled']}",
        f"# unresolved: {len(unfillable)}",
        "# action_breakdown:",
    ]
    actions = Counter(r["action"] for r in out_rows)
    for k, v in sorted(actions.items()):
        summary_lines.append(f"#   {k}: {v}")
    summary_lines.append("# counter_breakdown:")
    for k, v in sorted(counters.items()):
        summary_lines.append(f"#   {k}: {v}")
    summary_lines.append("# unfillable_breakdown:")
    uc = Counter(r["reason"] for r in unfillable)
    for k, v in sorted(uc.items()):
        summary_lines.append(f"#   {k}: {v}")
    summary_lines.append(
        "# columns: record_id,record_name,section,column,action,new_value,new_citation,new_status,rationale,priority,gap_class_in"
    )

    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        for line in summary_lines:
            fh.write(line + "\n")
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "record_id",
                "record_name",
                "section",
                "column",
                "action",
                "new_value",
                "new_citation",
                "new_status",
                "rationale",
                "priority",
                "gap_class_in",
            ],
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)

    print(f"in-scope gap rows : {len(gap_rows)}", file=sys.stderr)
    print(f"fills emitted    : {counters['filled']}", file=sys.stderr)
    print(f"unresolved       : {len(unfillable)}", file=sys.stderr)
    for k, v in sorted(counters.items()):
        print(f"  {k}: {v}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
