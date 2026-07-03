#!/usr/bin/env python3
"""
phase_2_add_subscores.py — Phase 2 follow-up migration.

Adds the three per-family capability sub-score cells specified in
`docs/composite-methodology.md` §11 to every record in
`data/landscape.json`. Idempotent: re-running is a no-op.

Cells added (all kebab-case per §2.5 schema convention):

  capability-code-score
  capability-agentic-score
  capability-longcontext-score

Each is added with the standard empty-cell shape used by
`phase_2_migrate_schema.py`:

    {"value": "", "citation": null, "status": "no-data", "tier": "T3"}

The `capability_sweep.py` job (referenced in composite-methodology.md
§8 and PHASE_2_SPEC.html §9.3) populates these cells from the linked
benchmark sources on the weekly rebaseline cron. Populated cells will
carry a `_provenance[slug]` entry with `source: llm` (or `human` if a
maintainer edits by hand); empty cells do not require provenance per
the tolerance rule in `validate.py::gate_phase_2_provenance`.

Sister files that maintain their own `PHASE_2_CELL_SLUGS` list must be
updated in the same PR (see FILES_TO_UPDATE below).

Usage
-----
    python3 scripts/phase_2_add_subscores.py            # in-place rewrite
    python3 scripts/phase_2_add_subscores.py --dry-run  # print summary, no write
    python3 scripts/phase_2_add_subscores.py --check    # exit 1 if any row
                                                        # is missing sub-score cells
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"

SUBSCORE_CELL_SLUGS: list[str] = [
    "capability-code-score",
    "capability-agentic-score",
    "capability-longcontext-score",
]

# Reference only — kept in sync manually since scripts avoid cross-imports.
FILES_TO_UPDATE: list[str] = [
    "scripts/validate.py",
    "scripts/research_intake.py",
    "scripts/apply_intake_pr.py",
]


def empty_cell() -> dict:
    return {"value": "", "citation": None, "status": "no-data", "tier": "T3"}


def migrate(data: dict) -> tuple[int, int]:
    """Return (rows_touched, cells_added)."""
    rows_touched = 0
    cells_added = 0

    for rec in data["records"]:
        touched = False
        cells = rec.setdefault("cells", {})
        for slug in SUBSCORE_CELL_SLUGS:
            if slug not in cells:
                cells[slug] = empty_cell()
                cells_added += 1
                touched = True
        if touched:
            rows_touched += 1

    return rows_touched, cells_added


def write_json(data: dict, path: Path) -> None:
    """Match the existing formatter (2-space indent, trailing newline)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def check_mode(data: dict) -> int:
    bad = []
    for rec in data["records"]:
        rid = rec.get("id", "<unknown>")
        cells = rec.get("cells", {})
        missing = [s for s in SUBSCORE_CELL_SLUGS if s not in cells]
        if missing:
            bad.append(f"  {rid}: missing cells {missing}")
    if bad:
        print("Sub-score schema check FAILED:", file=sys.stderr)
        for line in bad[:20]:
            print(line, file=sys.stderr)
        if len(bad) > 20:
            print(f"  ... and {len(bad) - 20} more", file=sys.stderr)
        return 1
    print(f"OK: all {len(data['records'])} rows carry the 3 sub-score cells.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--dry-run", action="store_true", help="Print summary, no write.")
    ap.add_argument("--check", action="store_true", help="Exit 1 if any row lacks sub-score cells.")
    args = ap.parse_args()

    data = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))

    if args.check:
        return check_mode(data)

    rows_touched, cells_added = migrate(data)
    total_rows = len(data["records"])
    print("Sub-score schema migration summary:")
    print(f"  records total:         {total_rows}")
    print(f"  rows touched:          {rows_touched}")
    print(f"  sub-score cells added: {cells_added} (expected on first run: {total_rows * 3})")

    if args.dry_run:
        print("  (dry-run — no write)")
        return 0

    write_json(data, LANDSCAPE_JSON)
    print(f"  wrote: {LANDSCAPE_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
