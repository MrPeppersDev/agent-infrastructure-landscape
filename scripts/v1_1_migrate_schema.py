#!/usr/bin/env python3
"""
v1_1_migrate_schema.py — schema v1.1.0 (issues #150 / #166).

Adds the seven v1.1.0 cell slugs to every record in `data/landscape.json`
with empty defaults and bumps `schemaVersion` to 1.1.0. Idempotent:
re-running is a no-op. Mirrors scripts/phase_2_migrate_schema.py (#95).

  adoption-accelerator              enum: yc-<batch> | none
  architecture-deployment-locus     enum: local | cloud | ide | computer-use | hybrid
  licensing-bucket                  enum: open-source | open-core | commercial
  positioning-platform-vs-product   enum: platform | product | both
  taxonomy-three-layer-rollup       enum: agent-infra | model-infra | large-models
  developer-activity-opendigger     JSON struct from the OpenDigger API
  freshness-date                    YYYY-MM-DD = max(upstream last commit, last audit)

Enum domains live in docs/schema/*.json; see docs/SCHEMA.md §2.5.10.
No values are filled here — the derived and research backfills do that.

Usage
-----
    python3 scripts/v1_1_migrate_schema.py            # in-place rewrite
    python3 scripts/v1_1_migrate_schema.py --dry-run  # print summary, no write
    python3 scripts/v1_1_migrate_schema.py --check    # exit 1 if any row lacks a v1.1.0 cell
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
SCHEMA_VERSION = "1.1.0"

V1_1_CELL_SLUGS: list[str] = [
    "adoption-accelerator",
    "architecture-deployment-locus",
    "licensing-bucket",
    "positioning-platform-vs-product",
    "taxonomy-three-layer-rollup",
    "developer-activity-opendigger",
    "freshness-date",
]


def empty_cell() -> dict:
    return {"value": "", "citation": None, "status": "no-data", "tier": "T3"}


def migrate(data: dict) -> tuple[int, int]:
    """Return (rows_touched, cells_added)."""
    rows_touched = cells_added = 0
    for rec in data["records"]:
        cells = rec.setdefault("cells", {})
        missing = [s for s in V1_1_CELL_SLUGS if s not in cells]
        for slug in missing:
            cells[slug] = empty_cell()
        cells_added += len(missing)
        rows_touched += bool(missing)
    data["schemaVersion"] = SCHEMA_VERSION
    return rows_touched, cells_added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    data = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))
    if args.check:
        bad = [r["id"] for r in data["records"] if any(s not in r.get("cells", {}) for s in V1_1_CELL_SLUGS)]
        if bad or data.get("schemaVersion") != SCHEMA_VERSION:
            print(f"{len(bad)} records missing v1.1.0 cells; schemaVersion={data.get('schemaVersion')}", file=sys.stderr)
            return 1
        print("all records carry the v1.1.0 cells")
        return 0

    rows, cells = migrate(data)
    print(f"rows touched: {rows}; cells added: {cells}; schemaVersion -> {SCHEMA_VERSION}")
    if not args.dry_run:
        tmp = LANDSCAPE_JSON.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(LANDSCAPE_JSON)
    return 0


if __name__ == "__main__":
    sys.exit(main())
