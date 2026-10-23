#!/usr/bin/env python3
"""
apply_reverify.py — merge research-agent re-verification results into
data/landscape.json.

Input: one or more JSON files, each a list of rows shaped like
(optional keys: "record": {"name", "url"} and "taxonomy": {axis: [...]})

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


AXES = ("storage", "retrieval", "persistence", "update", "unit", "governance", "conflict")


def taxonomy_vocab(landscape: dict) -> dict[str, set[str]]:
    """Values each taxonomy axis already uses — the controlled vocabulary."""
    voc: dict[str, set[str]] = {a: {"n/a"} for a in AXES}
    for r in landscape["records"]:
        for a in AXES:
            for v in (r.get("taxonomy") or {}).get(a, []):
                voc[a].add(v["value"])
    return voc


def apply_taxonomy(rec: dict, tax: dict, vocab: dict[str, set[str]]) -> bool:
    """Replace a record's taxonomy with curated values. Rejects the whole
    proposal if any axis is missing, uses a value outside the vocabulary,
    or doesn't have exactly one primary — partial taxonomy is worse than
    the honest n/a it replaces."""
    new: dict[str, list] = {}
    for a in AXES:
        vals = tax.get(a)
        if not isinstance(vals, list) or not vals:
            return False
        if sum(1 for v in vals if v.get("primary")) != 1:
            return False
        out = []
        for v in vals:
            if v.get("value") not in vocab[a]:
                return False
            out.append({"value": v["value"], "primary": bool(v.get("primary")), "reason": None})
        out.sort(key=lambda v: not v["primary"])  # primary first
        # Only a single-value axis can carry a reason through the HTML
        # round-trip: it renders as prose whose first token is re-read as
        # the value, so the prose must start with the value. Multi-value
        # axes render as pills, which drop reasons.
        if len(out) == 1:
            reason = clean(str(vals[0].get("reason") or "")).replace(":", " —")
            if reason and reason.lower() not in ("none", "null", out[0]["value"]):
                if not reason.lower().startswith(out[0]["value"]):
                    reason = f"{out[0]['value']} — {reason}"
                out[0]["reason"] = reason
        new[a] = out
    rec["taxonomy"] = new
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--date", required=True)
    ap.add_argument("--report", default=None, help="write a markdown summary here")
    args = ap.parse_args()

    landscape = load_landscape(LANDSCAPE)
    stats = {"rows_seen": 0, "rows_verified": 0, "cells_applied": 0,
             "cells_skipped": 0, "decayed": 0, "renamed": 0, "url_changed": 0,
             "taxonomy_set": 0}
    vocab = taxonomy_vocab(landscape)
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
            # Record-level changes: display name (renames/acquisitions keep
            # the old name first, "Old (now New)", so search still finds it)
            # and primary url (when the old one redirects or died). The id
            # stays stable.
            recd = row.get("record") or {}
            new_name = clean(str(recd.get("name") or ""))
            if new_name and new_name != rec["name"]:
                rec["name"] = new_name
                stats["renamed"] += 1
            new_url = (recd.get("url") or "").strip()
            if new_url and _URL.match(new_url) and new_url != rec.get("url"):
                rec["url"] = new_url
                stats["url_changed"] += 1
            if row.get("taxonomy"):
                if apply_taxonomy(rec, row["taxonomy"], vocab):
                    stats["taxonomy_set"] += 1
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
