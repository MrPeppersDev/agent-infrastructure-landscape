#!/usr/bin/env python3
"""
apply_v1_1_research.py — write researched v1.1.0 cells (issue #150) into
data/landscape.json.

Input: one or more JSON files, each a list of

    {"id": "...", "cell": "adoption-accelerator", "value": "yc-s24",
     "status": "real-data", "citation": "https://...",
     "confidence": "high|medium", "note": "..."}

Only the named cell changes, plus its `_provenance` entry (source "scrape",
verified when confidence is high). Unlike apply_reverify.py, the row-level
`last_verified_at` is left alone: checking one cell is not a re-verification
of the row. Values are checked against docs/schema/<cell>.json before
anything is written; a bad value aborts the whole run. A reviewed cell
(written by a human, or real-data from another script) is not overwritten
unless --force.

Run render → extract → reconcile afterwards (apply_reverify.canonicalize),
then `make build && make validate`. --canonicalize does the first step.

Usage:
  python3 scripts/apply_v1_1_research.py --date YYYY-MM-DD results.json [...]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from _cell_writer import find_record, load_landscape, save_landscape, update_cell

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE = ROOT / "data" / "landscape.json"
SCHEMA_DIR = ROOT / "docs" / "schema"
SCRIPT = "scripts/apply_v1_1_research.py"
CELLS = {"adoption-accelerator", "architecture-deployment-locus", "positioning-platform-vs-product", "licensing-bucket"}
STATUSES = {"real-data", "estimate", "not-applicable"}


def check(row: dict, specs: dict) -> str | None:
    cell, value, status = row.get("cell"), str(row.get("value") or ""), row.get("status", "real-data")
    if cell not in CELLS:
        return f"cell {cell!r} is not a researched v1.1.0 cell"
    if status not in STATUSES:
        return f"status {status!r} not in {sorted(STATUSES)}"
    if status == "not-applicable":
        return None if value.startswith("not applicable") else "not-applicable values start with 'not applicable'"
    if not str(row.get("citation") or "").startswith("http"):
        return "a filled cell needs an http(s) citation"
    spec = specs[cell]
    if value in spec.get("values", []) or ("pattern" in spec and re.match(spec["pattern"], value)):
        return None
    return f"{cell}={value!r} outside docs/schema/{cell}.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--date", required=True)
    ap.add_argument("--landscape", type=Path, default=LANDSCAPE)
    ap.add_argument("--force", action="store_true", help="overwrite cells another source already filled")
    ap.add_argument("--canonicalize", action="store_true", help="run render → extract → reconcile after writing")
    args = ap.parse_args()

    specs = {c: json.loads((SCHEMA_DIR / f"{c}.json").read_text()) for c in CELLS}
    rows = [r for f in args.files for r in json.loads(f.read_text(encoding="utf-8"))]
    landscape = load_landscape(args.landscape)
    errors = []
    for i, row in enumerate(rows):
        err = check(row, specs)
        if not err and find_record(landscape, row.get("id", "")) is None:
            err = "unknown record id"
        if err:
            errors.append(f"row {i} ({row.get('id')}): {err}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    stats = {"applied": 0, "unchanged": 0, "kept_existing": 0}
    for row in rows:
        rec = find_record(landscape, row["id"])
        cell = row["cell"]
        existing = rec["cells"].get(cell) or {}
        prov = (rec.get("_provenance") or {}).get(cell) or {}
        filled_elsewhere = existing.get("status") in ("real-data", "estimate") and prov.get("script") != SCRIPT
        if filled_elsewhere and not args.force:
            stats["kept_existing"] += 1
            continue
        status = row.get("status", "real-data")
        changed = update_cell(rec, cell, value=row["value"], status=status, citation=row.get("citation"))
        if not changed:
            stats["unchanged"] += 1
            continue
        rec["cells"][cell].pop("tier", None)  # recomputed from status + citation on round-trip
        rec.setdefault("_provenance", {})[cell] = {
            "scrape_url": row.get("citation"),
            "scraped_at": args.date,
            "script": SCRIPT,
            "source": "scrape",
            "verified": row.get("confidence", "high") == "high",
        }
        stats["applied"] += 1

    save_landscape(landscape, args.landscape)
    if args.canonicalize:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import apply_reverify
        apply_reverify.canonicalize()
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
