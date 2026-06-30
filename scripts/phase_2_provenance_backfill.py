#!/usr/bin/env python3
"""
phase_2_provenance_backfill.py — Phase 2 Gate 1 / Phase 2 of 4.

Populates `_provenance` entries for the 85 pre-Phase-2 cells in every
record of `data/landscape.json`. See PHASE_2_SPEC.html §3.4 / §3.5
and docs/SCHEMA.md §3d for the provenance model.

Assignment policy
-----------------

Default for every claim-bearing cell:
  { "source": "legacy", "verified": true }

Upgraded to `scrape` when the writing script is identifiable from
the cell's slug AND the cell carries a usable http(s) citation:
  - commit-trajectory     → scripts/fetch_commit_trajectories.py
  - citation-trajectory   → scripts/bucket_s2_citations.py
  - download-trajectory   → scripts/fetch_download_trajectories.py

  { "source": "scrape", "verified": true,
    "scraped_at": <cell.last_verified_at or row.last_verified_at>,
    "scrape_url": <cell.citation>,
    "script":     <mapped script path> }

Cells with `status == "no-data"` carry no claim and get no provenance
entry. The other three statuses (`real-data`, `not-applicable`,
`depth-floor-reached`, `estimate`) all represent maintainer-curated
claims and receive an entry.

The 11 Phase 2 cells (cost-*, capability-*, use-case-*) are skipped
here — they're populated by Phase 3 (mechanical fill) and Phase 4
(LLM-judgment fill) of Gate 1.

Idempotent: re-running over an already-backfilled file is a no-op
(existing entries are preserved; only missing entries are added).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"

# Slugs introduced by Phase 1 of Gate 1 — skip these during legacy
# backfill (they'll be filled by Phases 3 & 4).
PHASE_2_CELL_SLUGS = {
    "cost-input-usd-per-mtok",
    "cost-output-usd-per-mtok",
    "cost-tier",
    "cost-pricing-model",
    "cost-last-verified",
    "capability-composite-score",
    "capability-band",
    "capability-benchmark-sources",
    "capability-last-verified",
    "use-case-tags",
    "use-case-anti-tags",
}

# Slug → script path. Where the writing script is unambiguous from
# the cell's role, we upgrade `legacy` → `scrape` so future audits
# know exactly where the value came from.
SCRAPE_SCRIPT_MAP = {
    "commit-trajectory": "scripts/fetch_commit_trajectories.py",
    "citation-trajectory": "scripts/bucket_s2_citations.py",
    "download-trajectory": "scripts/fetch_download_trajectories.py",
}

# Statuses that carry no claim — get no provenance entry.
NO_CLAIM_STATUSES = {"no-data"}


def is_http_url(s: Any) -> bool:
    if not isinstance(s, str) or not s.strip():
        return False
    try:
        p = urlparse(s.strip())
    except ValueError:
        return False
    return p.scheme in {"http", "https"} and bool(p.netloc)


def build_entry(
    slug: str,
    cell: dict[str, Any],
    row_last_verified: str,
) -> dict[str, Any] | None:
    """Return a new provenance entry for this cell, or None to skip."""
    status = cell.get("status")
    if status in NO_CLAIM_STATUSES:
        return None
    script = SCRAPE_SCRIPT_MAP.get(slug)
    citation = cell.get("citation")
    # Entry fields are emitted alphabetically because render.py serializes
    # the provenance JSON with `sort_keys=True`, and the round-trip dict
    # therefore comes back alphabetized — gate 2 requires the committed
    # JSON to match that ordering byte-for-byte.
    if (
        script is not None
        and status == "real-data"
        and is_http_url(citation)
    ):
        scraped_at = cell.get("last_verified_at") or row_last_verified
        entry = {
            "source": "scrape",
            "verified": True,
            "scraped_at": scraped_at,
            "scrape_url": citation,
            "script": script,
        }
    else:
        entry = {"source": "legacy", "verified": True}
    return OrderedDict(sorted(entry.items()))


def backfill(
    landscape: dict[str, Any],
    overwrite: bool,
) -> tuple[int, int, int]:
    """Walk records and populate `_provenance`. Returns
    (records_touched, entries_added, entries_skipped_existing)."""
    records_touched = 0
    entries_added = 0
    entries_skipped = 0

    records = landscape.get("records") or []
    for rec in records:
        cells = rec.get("cells") or {}
        prov = rec.get("_provenance")
        if not isinstance(prov, dict):
            prov = OrderedDict()
            rec["_provenance"] = prov

        row_last_verified = rec.get("last_verified_at") or ""
        touched_this_record = False
        for slug, cell in cells.items():
            if slug in PHASE_2_CELL_SLUGS:
                continue
            if slug in prov and not overwrite:
                entries_skipped += 1
                continue
            entry = build_entry(slug, cell, row_last_verified)
            if entry is None:
                if slug in prov and overwrite:
                    del prov[slug]
                    touched_this_record = True
                continue
            prov[slug] = entry
            entries_added += 1
            touched_this_record = True

        if touched_this_record:
            records_touched += 1

    return records_touched, entries_added, entries_skipped


def reorder_provenance(landscape: dict[str, Any]) -> None:
    """Reorder each `_provenance` dict to match the cell-iteration order
    used by extract.py / render.py — i.e. the order of `cells` in the
    record. This is what the round-trip cycle (gate 2) expects."""
    for rec in landscape.get("records") or []:
        prov = rec.get("_provenance")
        if not isinstance(prov, dict) or not prov:
            continue
        cell_order = list((rec.get("cells") or {}).keys())
        rank = {slug: i for i, slug in enumerate(cell_order)}
        rec["_provenance"] = OrderedDict(
            sorted(prov.items(), key=lambda kv: rank.get(kv[0], 1_000_000))
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input",
        type=Path,
        default=LANDSCAPE_JSON,
        help="Path to landscape.json (default: data/landscape.json).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the count of entries that would be added; do not write.",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help=(
            "Exit 0 if every claim-bearing pre-Phase-2 cell already has a "
            "_provenance entry; exit 1 otherwise. Implies --dry-run."
        ),
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Overwrite existing _provenance entries. Default is "
            "idempotent: existing entries are preserved."
        ),
    )
    args = ap.parse_args()

    with args.input.open("r", encoding="utf-8") as f:
        landscape = json.load(f)

    records_touched, entries_added, entries_skipped = backfill(
        landscape, overwrite=args.overwrite
    )

    if args.check:
        if entries_added > 0:
            print(
                f"FAIL: {entries_added} cell(s) across "
                f"{records_touched} record(s) lack a _provenance entry.",
                file=sys.stderr,
            )
            return 1
        print(
            f"OK: every claim-bearing pre-Phase-2 cell has a _provenance "
            f"entry ({entries_skipped} entries already present)."
        )
        return 0

    print(
        f"records_touched={records_touched} "
        f"entries_added={entries_added} "
        f"entries_skipped_existing={entries_skipped}"
    )

    if args.dry_run:
        return 0

    reorder_provenance(landscape)
    with args.input.open("w", encoding="utf-8") as f:
        json.dump(landscape, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {args.input}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
