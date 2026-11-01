#!/usr/bin/env python3
"""
prune_snapshots.py — retention for the daily bot snapshots in docs/.

The recommendation-drift and catalog-pulse bots write one markdown file a
day (docs/drift-YYYY-MM-DD.md, docs/pulse-YYYY-MM-DD.md). Each run only
reads the newest earlier file, so older ones are history, and git keeps
history. This keeps the last KEEP_DAYS days of each kind and deletes the
rest (product review, 2026-10-30: "a retention rule for the generated
files in docs/").

Usage:
    python3 scripts/prune_snapshots.py [--keep-days 30] [--dir docs] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

PATTERN = re.compile(r"^(drift|pulse)-(\d{4}-\d{2}-\d{2})\.md$")


def prune(directory: Path, keep_days: int, today: dt.date, dry_run: bool = False) -> list[Path]:
    cutoff = today - dt.timedelta(days=keep_days)
    removed = []
    for p in sorted(directory.iterdir()):
        m = PATTERN.match(p.name)
        if not m:
            continue
        if dt.date.fromisoformat(m.group(2)) < cutoff:
            removed.append(p)
            if not dry_run:
                p.unlink()
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep-days", type=int, default=30)
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parent.parent / "docs"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    removed = prune(Path(a.dir), a.keep_days, dt.date.today(), a.dry_run)
    print(f"prune_snapshots: {'would remove' if a.dry_run else 'removed'} {len(removed)} snapshot(s) older than {a.keep_days} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
