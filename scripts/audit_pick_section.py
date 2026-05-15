#!/usr/bin/env python3
"""
audit_pick_section.py — pick the section with the oldest last-audited date.

Reads `audit/section-rotation.json` (map: section-name → ISO date string)
and prints the section name with the lexicographically-smallest date to
stdout. Lexicographic comparison works because the dates are zero-padded
ISO-8601 (`YYYY-MM-DD`).

Ties (same date — typical on the very first run when every section is
initialised to today) are broken by section name (alphabetical) so the
picker is deterministic.

Used by `.github/workflows/audit-section.yml` to rotate fairly through
sections under the weekly cron. Manual workflow runs supply a section
explicitly via workflow_dispatch input; this picker only fires on the
scheduled branch.

CLI:
  python3 scripts/audit_pick_section.py
  python3 scripts/audit_pick_section.py --rotation audit/section-rotation.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROTATION = ROOT / "audit" / "section-rotation.json"


def pick(rotation: dict[str, str]) -> str:
    """Return the section name with the oldest last-audited date.

    Ties broken alphabetically. Raises ValueError on empty input.
    """
    if not rotation:
        raise ValueError("rotation map is empty")
    # Sort by (date ASC, section ASC). The first item is the oldest.
    items = sorted(rotation.items(), key=lambda kv: (kv[1], kv[0]))
    return items[0][0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument(
        "--rotation",
        default=str(DEFAULT_ROTATION),
        help="Path to section-rotation.json "
        f"(default: {DEFAULT_ROTATION.relative_to(ROOT)})",
    )
    args = ap.parse_args()

    rotation_path = Path(args.rotation)
    if not rotation_path.exists():
        print(f"error: rotation file not found: {rotation_path}", file=sys.stderr)
        return 1

    try:
        rotation = json.loads(rotation_path.read_text())
    except json.JSONDecodeError as exc:
        print(f"error: malformed JSON in {rotation_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(rotation, dict):
        print(f"error: rotation file must be a JSON object, got {type(rotation).__name__}",
              file=sys.stderr)
        return 1

    try:
        section = pick(rotation)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(section)
    return 0


if __name__ == "__main__":
    sys.exit(main())
