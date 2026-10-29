#!/usr/bin/env python3
"""
v1_2_migrate_schema.py — schema v1.2.0: four buyer cells.

Adds the v1.2.0 cell slugs to every record in `data/landscape.json` with
empty defaults and bumps `schemaVersion` to 1.2.0. Idempotent. Mirrors
scripts/v1_1_migrate_schema.py.

  compliance-certifications   set of codes (soc2-type2, iso27001, hipaa, …) | none-published
  sdk-languages               set of languages (python, typescript, go, …)
  protocol-support            set (mcp-server, mcp-client, a2a, openai-compatible, ag-ui, opentelemetry) | none
  maturity                    enum: ga | beta | preview | alpha

Enum domains live in docs/schema/*.json; see docs/SCHEMA.md §2.5.11.
No values are filled here — the research backfill does that.

Usage
-----
    python3 scripts/v1_2_migrate_schema.py            # in-place rewrite
    python3 scripts/v1_2_migrate_schema.py --check    # exit 1 if any row lacks a v1.2.0 cell
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
SCHEMA_VERSION = "1.2.0"

V1_2_CELL_SLUGS: list[str] = [
    "compliance-certifications",
    "sdk-languages",
    "protocol-support",
    "maturity",
]


def empty_cell() -> dict:
    return {"value": "", "citation": None, "status": "no-data", "tier": "T3"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))
    if args.check:
        bad = [r["id"] for r in data["records"] if any(s not in r.get("cells", {}) for s in V1_2_CELL_SLUGS)]
        if bad or data.get("schemaVersion") != SCHEMA_VERSION:
            print(f"{len(bad)} records missing v1.2.0 cells; schemaVersion={data.get('schemaVersion')}", file=sys.stderr)
            return 1
        print("all records carry the v1.2.0 cells")
        return 0
    added = 0
    for rec in data["records"]:
        cells = rec.setdefault("cells", {})
        for slug in V1_2_CELL_SLUGS:
            if slug not in cells:
                cells[slug] = empty_cell()
                added += 1
    data["schemaVersion"] = SCHEMA_VERSION
    print(f"cells added: {added}; schemaVersion -> {SCHEMA_VERSION}")
    tmp = LANDSCAPE_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(LANDSCAPE_JSON)
    return 0


if __name__ == "__main__":
    sys.exit(main())
