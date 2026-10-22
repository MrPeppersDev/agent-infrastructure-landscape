#!/usr/bin/env python3
"""
apply_reverify.py — merge research-agent re-verification results into
data/landscape.json.

Input: one or more JSON files, each a list of rows shaped like

    {"id": "...", "lifecycle": "active|maintenance|archived|deprecated|
      acquired|renamed|dead|unknown", "lifecycle_note": "...",
     "lifecycle_citation": "https://...", "verified": true,
     "updates": [{"cell": "latest-release", "old": "...", "new": "...",
                  "citation": "https://...", "confidence": "high|medium"}]}

Policy (deliberately conservative — this is published data):
  * Rows with verified != true are skipped entirely; their updates rest
    on secondary sources only.
  * Every applied cell gets status real-data, the agent's citation, and
    last_verified_at = --date. Provenance is recorded as source "scrape"
    with the citation URL; `verified` is true only for high-confidence
    updates, so medium-confidence values stay visibly unconfirmed.
  * Verified rows get their row-level last_verified_at bumped to --date.
  * lifecycle archived/deprecated/dead → decay_cause (archived/superseded/
    archived) with the lifecycle citation as decay_evidence. Acquired and
    renamed rows usually still ship, so they are reported, not decayed.

Usage:
    python3 scripts/apply_reverify.py --date 2026-10-22 extraction/reverify-2026-10/result-*.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cell_writer import find_record, load_landscape, save_landscape, update_cell  # noqa: E402
from extract import VOLATILE_CELL_SLUGS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE = ROOT / "data" / "landscape.json"
DECAY_MAP = {"archived": "archived", "deprecated": "superseded", "dead": "archived"}
_URL = re.compile(r"^https?://\S+$")


def clean(value: str) -> str:
    # Values round-trip through landscape.html; keep them plain text.
    return re.sub(r"\s+", " ", value.replace("<", "‹").replace(">", "›")).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--date", required=True)
    ap.add_argument("--report", default=None, help="write a markdown summary here")
    args = ap.parse_args()

    landscape = load_landscape(LANDSCAPE)
    stats = {"rows_seen": 0, "rows_verified": 0, "cells_applied": 0,
             "cells_skipped": 0, "decayed": 0}
    lifecycle_notes: list[str] = []

    for f in args.files:
        for row in json.loads(Path(f).read_text()):
            stats["rows_seen"] += 1
            rec = find_record(landscape, row["id"])
            if rec is None or row.get("verified") is not True:
                stats["cells_skipped"] += len(row.get("updates") or [])
                continue
            stats["rows_verified"] += 1
            rec["last_verified_at"] = args.date
            for u in row.get("updates") or []:
                cit = (u.get("citation") or "").strip()
                new = clean(str(u.get("new") or ""))
                if u["cell"] not in rec["cells"] or not new or not _URL.match(cit):
                    stats["cells_skipped"] += 1
                    continue
                # Per-cell dates are only legal on volatile slugs (SCHEMA §3b);
                # the row-level date covers the rest.
                lva = args.date if u["cell"] in VOLATILE_CELL_SLUGS else None
                update_cell(rec, u["cell"], value=new, status="real-data",
                            citation=cit, last_verified_at=lva)
                # Tier (T1 GitHub-verifiable vs T2 URL) is derived from the
                # citation by the render/extract round-trip; drop any stale
                # tier so the pipeline recomputes it.
                rec["cells"][u["cell"]].pop("tier", None)
                rec.setdefault("_provenance", {})[u["cell"]] = dict(sorted({
                    "source": "scrape",
                    "scrape_url": cit,
                    "scraped_at": args.date,
                    "script": "scripts/apply_reverify.py",
                    "verified": u.get("confidence") == "high",
                }.items()))
                stats["cells_applied"] += 1
            lc = (row.get("lifecycle") or "").lower()
            lc_cit = (row.get("lifecycle_citation") or "").strip()
            if lc in DECAY_MAP and _URL.match(lc_cit) and not rec.get("decay_cause"):
                rec["decay_cause"] = DECAY_MAP[lc]
                rec["decay_evidence"] = lc_cit
                stats["decayed"] += 1
            if lc in {"acquired", "renamed", "archived", "deprecated", "dead", "maintenance"}:
                note = clean(row.get("lifecycle_note") or "")
                lifecycle_notes.append(f"- **{rec['name']}** — {lc}" + (f": {note}" if note else "")
                                       + (f" ([source]({lc_cit}))" if _URL.match(lc_cit) else ""))

    save_landscape(landscape, LANDSCAPE)
    print(json.dumps(stats))
    if args.report:
        Path(args.report).write_text(
            f"# Re-verification {args.date}\n\n"
            + "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in stats.items())
            + "\n\n## Lifecycle changes found\n\n" + "\n".join(sorted(lifecycle_notes)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
