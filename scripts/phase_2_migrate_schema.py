#!/usr/bin/env python3
"""
phase_2_migrate_schema.py — Phase 2 Gate 1 / Phase 1 of 4.

Adds the 11 new Phase 2 cell slugs to every record in
`data/landscape.json` with empty defaults, and adds an empty
`_provenance` object to each record. Idempotent: re-running is a no-op.

Phase 2 cell slugs (kebab-case to match the existing 85, see
docs/SCHEMA.md §2.5 — the source-of-truth schema uses kebab-case
throughout; the Gate 1 issue body wrote them snake_case as spec
shorthand only):

  Column family A — Normalized cost (PHASE_2_SPEC.html §3.1)
    cost-input-usd-per-mtok, cost-output-usd-per-mtok,
    cost-tier, cost-pricing-model, cost-last-verified

  Column family B — Capability tier (§3.2)
    capability-composite-score, capability-band,
    capability-benchmark-sources, capability-last-verified

  Column family C — Use-case suitability (§3.3)
    use-case-tags, use-case-anti-tags

The empty-cell shape matches the existing 85-cell schema
(`{value, citation, status, tier}`) so `scripts/validate.py` Gate 1
passes immediately after this migration. Status is `no-data` and tier
is `T3` — the lowest claim tier — so any consumer that filters by
claim strength correctly treats these as "not yet sourced."

The `_provenance` object is a per-record dict keyed by cell slug. Phase
1 leaves it empty; Phase 2 of Gate 1 (a separate script /
PR — `phase_2_backfill_legacy_provenance.py`) populates legacy entries
for all 85 pre-Phase-2 cells.

Usage
-----
    python3 scripts/phase_2_migrate_schema.py            # in-place rewrite
    python3 scripts/phase_2_migrate_schema.py --dry-run  # print summary, no write
    python3 scripts/phase_2_migrate_schema.py --check    # exit 1 if any row
                                                         # is missing Phase 2 cells
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"

PHASE_2_CELL_SLUGS: list[str] = [
    # Column family A — Normalized cost (§3.1)
    "cost-input-usd-per-mtok",
    "cost-output-usd-per-mtok",
    "cost-tier",
    "cost-pricing-model",
    "cost-last-verified",
    # Column family B — Capability tier (§3.2)
    "capability-composite-score",
    "capability-band",
    "capability-benchmark-sources",
    "capability-last-verified",
    # Column family C — Use-case suitability (§3.3)
    "use-case-tags",
    "use-case-anti-tags",
]

assert len(PHASE_2_CELL_SLUGS) == 11


def empty_cell() -> dict:
    return {"value": "", "citation": None, "status": "no-data", "tier": "T3"}


def migrate(data: dict) -> tuple[int, int, int]:
    """Return (rows_touched, cells_added, provenance_added)."""
    rows_touched = 0
    cells_added = 0
    provenance_added = 0

    for rec in data["records"]:
        touched = False
        cells = rec.setdefault("cells", {})
        for slug in PHASE_2_CELL_SLUGS:
            if slug not in cells:
                cells[slug] = empty_cell()
                cells_added += 1
                touched = True

        if "_provenance" not in rec:
            rec["_provenance"] = {}
            provenance_added += 1
            touched = True

        if touched:
            rows_touched += 1

    return rows_touched, cells_added, provenance_added


def write_json(data: dict, path: Path) -> None:
    """Match the existing formatter (2-space indent, trailing newline)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def check_mode(data: dict) -> int:
    """Exit-1 if any row is missing any Phase 2 cell or _provenance."""
    bad = []
    for rec in data["records"]:
        rid = rec.get("id", "<unknown>")
        cells = rec.get("cells", {})
        missing = [s for s in PHASE_2_CELL_SLUGS if s not in cells]
        if missing:
            bad.append(f"  {rid}: missing cells {missing}")
        if "_provenance" not in rec:
            bad.append(f"  {rid}: missing _provenance object")
    if bad:
        print("Phase 2 schema check FAILED:", file=sys.stderr)
        for line in bad[:20]:
            print(line, file=sys.stderr)
        if len(bad) > 20:
            print(f"  ... and {len(bad) - 20} more", file=sys.stderr)
        return 1
    print(f"OK: all {len(data['records'])} rows carry the 11 Phase 2 cells + _provenance.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="Print summary, no write.")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any row lacks Phase 2 cells or _provenance.",
    )
    args = ap.parse_args()

    data = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))

    if args.check:
        return check_mode(data)

    rows_touched, cells_added, provenance_added = migrate(data)

    total_rows = len(data["records"])
    print(f"Phase 2 schema migration summary:")
    print(f"  records total:       {total_rows}")
    print(f"  rows touched:        {rows_touched}")
    print(f"  Phase-2 cells added: {cells_added} (expected: {total_rows * 11} on first run)")
    print(f"  _provenance objects added: {provenance_added}")

    if args.dry_run:
        print("  (dry-run — no write)")
        return 0

    write_json(data, LANDSCAPE_JSON)
    print(f"  wrote: {LANDSCAPE_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
