#!/usr/bin/env python3
"""
audit_tiers.py — claim-tier provenance audit over data/landscape.json

Reads the canonical dataset and prints a compact distribution report:

  - Total cells per tier (T1 / T2 / T3)
  - For T1 cells: count with valid github-URL citations vs missing/bad
  - For T2 cells: count with resolvable URL citations vs missing
  - For T3 cells: count with status="estimate", "no-data", or other
  - Status distribution across all cells

The output is plain-text and stable across runs against the same
dataset, so commit messages can quote it verbatim.

Usage:
  python3 scripts/audit_tiers.py
  python3 scripts/audit_tiers.py --input /tmp/foo.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"

GITHUB_URL_RE = re.compile(r"^https?://github\.com/", re.IGNORECASE)
HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Claim-tier audit over data/landscape.json"
    )
    ap.add_argument("--input", default=str(LANDSCAPE_JSON))
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    records = payload.get("records") or []

    total = 0
    counts = {"T1": 0, "T2": 0, "T3": 0}
    t1_github_ok = 0
    t1_missing_or_bad = 0
    t2_with_url = 0
    t2_missing_url = 0
    t3_estimate = 0
    t3_no_data = 0
    t3_other = 0
    by_status: dict[str, int] = {}

    for rec in records:
        for slug, cell in (rec.get("cells") or {}).items():
            total += 1
            tier = cell.get("tier")
            status = cell.get("status") or "<missing>"
            citation = cell.get("citation")
            by_status[status] = by_status.get(status, 0) + 1
            if tier not in counts:
                print(
                    f"warn: {rec.get('id')!r}.cells[{slug}] has tier {tier!r}",
                    file=sys.stderr,
                )
                continue
            counts[tier] += 1
            if tier == "T1":
                if citation and GITHUB_URL_RE.match(citation):
                    t1_github_ok += 1
                else:
                    t1_missing_or_bad += 1
            elif tier == "T2":
                if citation and HTTP_URL_RE.match(citation):
                    t2_with_url += 1
                else:
                    t2_missing_url += 1
            else:  # T3
                if status == "estimate":
                    t3_estimate += 1
                elif status == "no-data":
                    t3_no_data += 1
                else:
                    t3_other += 1

    print(f"audit_tiers.py — {in_path.name}")
    print(f"records:     {len(records):,}")
    print(f"total cells: {total:,}")
    print()
    print("tier distribution:")
    for t in ("T1", "T2", "T3"):
        pct = (counts[t] / total * 100) if total else 0.0
        print(f"  {t}: {counts[t]:>6,}  ({pct:5.1f}%)")
    print()
    print("T1 detail (must cite a github.com URL):")
    print(f"  github-URL OK:        {t1_github_ok:>6,}")
    print(f"  missing/bad citation: {t1_missing_or_bad:>6,}")
    print()
    print("T2 detail (must cite a resolvable http(s) URL):")
    print(f"  citation present:     {t2_with_url:>6,}")
    print(f"  citation missing:     {t2_missing_url:>6,}")
    print()
    print("T3 detail (no citation required):")
    print(f"  status=estimate (explicit flag):       {t3_estimate:>6,}")
    print(f"  status=no-data  (placeholder):         {t3_no_data:>6,}")
    print(f"  status=other    (uncited n/a / other): {t3_other:>6,}")
    print()
    print("status distribution (all cells):")
    for s, n in sorted(by_status.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {s:<22} {n:>6,}")

    # Compact summary suitable for commit message / gh issue close.
    print()
    print("summary:", end=" ")
    print(
        f"T1={counts['T1']:,} ({t1_github_ok:,} ok / {t1_missing_or_bad:,} bad); "
        f"T2={counts['T2']:,} ({t2_with_url:,} cited / {t2_missing_url:,} missing); "
        f"T3={counts['T3']:,} ({t3_estimate:,} estimate / {t3_no_data:,} no-data / "
        f"{t3_other:,} other)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
