#!/usr/bin/env python3
"""
derive_v1_1_cells.py — compute the three derived v1.1.0 cells (issues #150,
#166) from data already in each record. Runs inside `make build`, after
reconcile and before render, so the values follow the facts they come from.

  taxonomy-three-layer-rollup  primary section → docs/schema/
                               section-to-three-layer-rollup.json. Always
                               recomputed; never hand-set.
  freshness-date               max(upstream last-commit month from the `gh`
                               cell, row `last_verified_at`). The commit month
                               counts as its first day, so it never overstates.
                               Always recomputed.
  licensing-bucket             from the `license` cell, plus `pricing` to tell
                               open-source from open-core. Only written while
                               the cell is empty or was last written by this
                               script, so a reviewed value is never overwritten.

Rules for licensing-bucket (docs/schema/licensing-bucket.json):
  - research papers (memory-research family) with no OSI licence → not-applicable
  - "not applicable — not OSS", "proprietary…", or a source-available licence
    (BSL, FSL, SSPL, Elastic, CC-BY-NC, Polyform, Custom) → commercial
  - an OSI licence plus a closed tier in the same cell ("…; proprietary Premium",
    "(Core)") → open-core, status estimate
  - an OSI licence alone → open-source, or open-core (estimate) when the
    pricing cell shows a paid plan (paying a model provider for tokens doesn't count)
  - anything else (unknown, unlicensed, searched not found) → left empty

Provenance is only rewritten when a value changes, so rebuilding on a later
day doesn't churn the file.

Usage:
  python3 scripts/derive_v1_1_cells.py            # in place
  python3 scripts/derive_v1_1_cells.py --check    # exit 1 if anything would change
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

from _cell_writer import load_landscape, save_landscape
from build_stack_index import COMMIT
from extract import classify_tier

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE = ROOT / "data" / "landscape.json"
ROLLUP = json.loads((ROOT / "docs" / "schema" / "section-to-three-layer-rollup.json").read_text())["mapping"]
FAMILIES = json.loads((ROOT / "taxonomy" / "families.json").read_text())["families"]
SCRIPT = "scripts/derive_v1_1_cells.py"
REPO_BLOB = "https://github.com/MrPeppersDev/agent-infrastructure-landscape/blob/main"
SITE = "https://mrpeppersdev.github.io/agent-infrastructure-landscape"

OSI = re.compile(r"\b(MIT|Apache[- ]?2(?:\.0)?|BSD|GPL|AGPL|LGPL|MPL|ISC|EPL|Unlicense|0BSD|Zlib|Artistic)\b", re.I)
SOURCE_AVAILABLE = re.compile(r"\b(BSL|FSL|SSPL|Elastic[- ]2|ELv2|CC[- ]BY[- ]NC|Polyform|Custom|source-available)\b", re.I)
CLOSED_TIER = re.compile(r"\bproprietary\b|\(core\)|\bcommercial\b|\benterprise edition\b", re.I)
PAID = re.compile(r"\$\s?\d|\bper (?:seat|user|month)\b|/mo\b|\bpaid\b|\benterprise\b|\bpro plan\b", re.I)
# Paying a model provider for tokens is not a paid tier of the product itself.
USAGE_ONLY = re.compile(r"\b(?:api|model|token|inference)\b[^;]{0,30}\b(?:usage|tokens?|rates?)\b", re.I)
PLAN = re.compile(r"\b(?:cloud|enterprise|pro|teams?|business|premium|hosted|managed|platform|plan|tier|seat)\b", re.I)


def section_family() -> dict[str, str]:
    out = {}
    items = FAMILIES if isinstance(FAMILIES, list) else [dict(v, key=k) for k, v in FAMILIES.items()]
    for fam in items:
        for sec in fam.get("sections", []):
            out[sec] = fam.get("key") or fam.get("id") or fam.get("slug")
    return out


SECTION_FAMILY = section_family()


def value(rec: dict, slug: str) -> str:
    return str(((rec.get("cells") or {}).get(slug) or {}).get("value") or "")


def primary_section(rec: dict) -> str | None:
    return next((s["section"] for s in rec.get("sections", []) if s.get("primary")),
                (rec.get("sections") or [{}])[0].get("section"))


def licensing(rec: dict) -> tuple[str, str, str] | None:
    """(value, status, citation slug) or None to leave the cell empty."""
    lic = value(rec, "license").strip()
    low = lic.lower()
    paper = SECTION_FAMILY.get(primary_section(rec) or "") == "memory-research"
    osi = OSI.search(lic) is not None
    if paper and not osi:
        return ("not applicable — research paper", "not-applicable", "license")
    if low.startswith("not applicable — not oss") or low.startswith("proprietary"):
        # A closed core with open SDKs or helpers is still a commercial product.
        return ("commercial", "real-data", "license")
    if SOURCE_AVAILABLE.search(lic) and not osi:
        return ("commercial", "real-data", "license")
    if osi and (CLOSED_TIER.search(lic) or SOURCE_AVAILABLE.search(lic)):
        return ("open-core", "estimate", "license")
    if osi:
        pricing = value(rec, "pricing")
        if PAID.search(pricing) and not (USAGE_ONLY.search(pricing) and not PLAN.search(pricing)):
            return ("open-core", "estimate", "pricing")
        return ("open-source", "real-data", "license")
    return None


def set_cell(rec: dict, slug: str, new_value: str, status: str, citation: str | None, today: str) -> bool:
    cells = rec.setdefault("cells", {})
    tier, _ = classify_tier(citation, status)
    new = {"value": new_value, "citation": citation, "status": status, "tier": tier}
    if cells.get(slug) == new:
        return False
    cells[slug] = new
    rec.setdefault("_provenance", {})[slug] = {
        "scrape_url": citation,
        "scraped_at": today,
        "script": SCRIPT,
        "source": "scrape",
        "verified": status == "real-data",
    }
    return True


def derive(landscape: dict[str, Any], today: str) -> dict[str, int]:
    stats = {"rollup": 0, "freshness": 0, "licensing": 0}
    for rec in landscape["records"]:
        sec = primary_section(rec)
        layer = ROLLUP.get(sec or "")
        if layer:
            stats["rollup"] += set_cell(rec, "taxonomy-three-layer-rollup", layer, "real-data",
                                        f"{REPO_BLOB}/docs/schema/section-to-three-layer-rollup.json", today)

        audit = rec.get("last_verified_at") or ""
        m = COMMIT.search(value(rec, "gh"))
        commit = f"{m.group(1)}-{m.group(2)}-01" if m else ""
        if audit or commit:
            if commit > audit:
                fresh, cite = commit, ((rec["cells"].get("gh") or {}).get("citation") or f"{SITE}/systems/{rec['id']}")
            else:
                fresh, cite = audit, f"{SITE}/systems/{rec['id']}"
            stats["freshness"] += set_cell(rec, "freshness-date", fresh, "real-data", cite, today)

        cell = (rec.get("cells") or {}).get("licensing-bucket") or {}
        mine = ((rec.get("_provenance") or {}).get("licensing-bucket") or {}).get("script") == SCRIPT
        if cell.get("status") in (None, "no-data") or mine:
            got = licensing(rec)
            if got:
                val, status, src = got
                # Closed products' license cells are "not applicable — not OSS"
                # with no citation; the vendor's own pricing page or site is
                # then the source for "commercial".
                cite = next((c for c in (
                    (rec["cells"].get(src) or {}).get("citation"),
                    (rec["cells"].get("license") or {}).get("citation"),
                    (rec["cells"].get("pricing") or {}).get("citation"),
                    rec.get("url"),
                ) if c and str(c).startswith("http")), None)
                if cite is None and status != "not-applicable":
                    continue
                stats["licensing"] += set_cell(rec, "licensing-bucket", val, status, cite, today)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--landscape", type=Path, default=LANDSCAPE)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    landscape = load_landscape(args.landscape)
    stats = derive(landscape, args.date)
    changed = sum(stats.values())
    print(json.dumps(stats))
    if args.check:
        return 1 if changed else 0
    if changed:
        save_landscape(landscape, args.landscape)
    return 0


if __name__ == "__main__":
    sys.exit(main())
