#!/usr/bin/env python3
"""
Path A: Quintet citation backfill.

Backfills citations for the desc/type/pros/cons/links quintet across every
record in web/landscape.json that currently has status=real-data but
citation=null.

Rules (per the Round 9 brief):
  1. If status != real-data, skip.
  2. If citation is non-null, skip (already cited).
  3. If record.url is non-null and starts with "http", use it as the citation.
  4. Else if record.cells.gh.citation exists, use that.
  5. Else if record.cells.created.citation exists, use that.
  6. Else: log as unresolvable; skip.

Emits extraction/round-9-quintet-citations.csv containing every targeted
cell, sorted by (record_id, column). The CSV is prefixed by a commented
summary block (lines beginning with `#`).
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_PATH = REPO_ROOT / "web" / "landscape.json"
OUT_PATH = REPO_ROOT / "extraction" / "round-9-quintet-citations.csv"

QUINTET = ("desc", "type", "pros", "cons", "links")
# Stable sort order for the CSV (within a record_id).
COLUMN_ORDER = {col: i for i, col in enumerate(QUINTET)}


def resolve_citation(record: dict) -> tuple[str | None, str]:
    """Return (citation_url, source) for a record per the fallback rules."""
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

    records = landscape.get("records", [])

    rows: list[dict] = []
    per_column_counts: Counter = Counter()
    per_source_counts: Counter = Counter()
    unresolvable_rows: list[dict] = []

    # Diagnostic: how many quintet cells currently match the target predicate
    # (status == real-data && citation == null). The audit said 2,575.
    matched_total = 0

    for record in records:
        rec_id = record.get("id", "")
        rec_name = record.get("name", "")
        cells = record.get("cells") or {}

        for column in QUINTET:
            cell = cells.get(column)
            if not isinstance(cell, dict):
                continue
            status = cell.get("status")
            citation = cell.get("citation")
            if status != "real-data":
                continue
            if citation is not None:
                continue

            matched_total += 1

            citation_url, source = resolve_citation(record)
            row = {
                "record_id": rec_id,
                "record_name": rec_name,
                "column": column,
                "new_value": cell.get("value", ""),
                "citation_url": citation_url if citation_url else "",
                "status": "real-data",
                "_source": source,
            }
            rows.append(row)
            if citation_url is None:
                unresolvable_rows.append(row)
            else:
                per_column_counts[column] += 1
                per_source_counts[source] += 1

    # Sort: record_id then column-order.
    rows.sort(key=lambda r: (r["record_id"], COLUMN_ORDER[r["column"]]))

    total_resolved = sum(per_column_counts.values())
    total_unresolvable = len(unresolvable_rows)

    summary_lines = [
        "# Round 9 — Path A quintet citation backfill",
        f"# generated_by: scripts/path_a_quintet.py",
        f"# source: web/landscape.json",
        f"# total_rows: {len(rows)}",
        f"# matched_cells (status=real-data, citation=null): {matched_total}",
        f"# resolved: {total_resolved}",
        f"# unresolvable: {total_unresolvable}",
        "# per_column_resolved:",
    ]
    for col in QUINTET:
        summary_lines.append(f"#   {col}: {per_column_counts.get(col, 0)}")
    summary_lines.append("# per_source_resolved:")
    for src in ("record.url", "cells.gh.citation", "cells.created.citation"):
        summary_lines.append(f"#   {src}: {per_source_counts.get(src, 0)}")
    summary_lines.append("# fallback_chain: record.url -> cells.gh.citation -> cells.created.citation -> unresolvable")
    summary_lines.append("# columns: record_id,record_name,column,new_value,citation_url,status")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        for line in summary_lines:
            fh.write(line + "\n")
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "record_id",
            "record_name",
            "column",
            "new_value",
            "citation_url",
            "status",
        ])
        for row in rows:
            writer.writerow([
                row["record_id"],
                row["record_name"],
                row["column"],
                row["new_value"],
                row["citation_url"],
                row["status"],
            ])

    # Console summary (also useful for the commit message).
    print(f"matched_cells={matched_total}", file=sys.stderr)
    print(f"resolved={total_resolved}", file=sys.stderr)
    print(f"unresolvable={total_unresolvable}", file=sys.stderr)
    for col in QUINTET:
        print(f"  {col}: {per_column_counts.get(col, 0)}", file=sys.stderr)
    for src in ("record.url", "cells.gh.citation", "cells.created.citation"):
        print(f"  via {src}: {per_source_counts.get(src, 0)}", file=sys.stderr)
    if unresolvable_rows:
        print("\nFirst 10 unresolvable rows:", file=sys.stderr)
        for r in unresolvable_rows[:10]:
            print(
                f"  {r['record_id']} :: {r['column']}",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
