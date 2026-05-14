#!/usr/bin/env python3
"""
Round-10 cleanup pass 2:
Resolve `real-data-no-citation` cells by applying a citation fallback chain
against the row's primary source in data/landscape.json.

Fallback chain (Path A):
  1. record.url (if http://...)
  2. record.cells.gh.citation
  3. record.cells.created.citation
  4. record.cells.claims.citation
  5. record.cells.desc.citation
  6. unresolvable

Output: extraction/round-10-cleanup-taxonomy-citations.csv
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAPS = ROOT / "extraction" / "data-gaps.csv"
LANDSCAPE = ROOT / "data" / "landscape.json"
OUT = ROOT / "extraction" / "round-10-cleanup-taxonomy-citations.csv"


def is_http(v):
    return isinstance(v, str) and v.startswith("http")


def resolve_citation(record):
    """Returns (citation_url, source_method)."""
    if not record:
        return (None, "unresolvable")

    url = record.get("url")
    if is_http(url):
        return (url, "record-url")

    cells = record.get("cells") or {}

    for cell_name, method in (
        ("gh", "gh-cite"),
        ("created", "created-cite"),
        ("claims", "claims-cite"),
        ("desc", "desc-cite"),
    ):
        cell = cells.get(cell_name) or {}
        cite = cell.get("citation")
        if is_http(cite):
            return (cite, method)

    return (None, "unresolvable")


def main():
    with open(LANDSCAPE) as f:
        landscape = json.load(f)
    records = {r["id"]: r for r in landscape["records"]}

    with open(GAPS) as f:
        reader = csv.DictReader(f)
        gap_rows = [r for r in reader if r["gap_class"] == "real-data-no-citation"]

    out_rows = []
    method_counts = {}
    unresolvable = []
    for row in gap_rows:
        rid = row["record_id"]
        record = records.get(rid)
        cite, method = resolve_citation(record)
        method_counts[method] = method_counts.get(method, 0) + 1
        status = "real-data" if method != "unresolvable" else "unresolvable"
        if method == "unresolvable":
            unresolvable.append((rid, row["record_name"], row["column"]))
        out_rows.append({
            "record_id": rid,
            "record_name": row["record_name"],
            "column": row["column"],
            "new_value": row["current_value"],
            "citation_url": cite or "",
            "status": status,
            "source_method": method,
        })

    with open(OUT, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "record_id",
                "record_name",
                "column",
                "new_value",
                "citation_url",
                "status",
                "source_method",
            ],
        )
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows to {OUT}")
    print("Per source_method:")
    for k in sorted(method_counts, key=lambda x: -method_counts[x]):
        print(f"  {k}: {method_counts[k]}")
    if unresolvable:
        print(f"\nUnresolvable ({len(unresolvable)}):")
        for rid, name, col in unresolvable:
            print(f"  - {rid} :: {name} :: {col}")


if __name__ == "__main__":
    main()
