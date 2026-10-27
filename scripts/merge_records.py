#!/usr/bin/env python3
"""
merge_records.py — fold duplicate catalog records into one (HANDOFF item 2).

Input: a rules file (see extraction/merges-2026-10/rules.json):

    {"date": "YYYY-MM-DD",
     "rules": [{"keep": "<id>", "drop": ["<id>", ...], "name": "...",
                "aliases": ["..."], "cells": {"<slug>": "<value>"},
                "packages": ["pypi:...", ...], "reason": "..."}]}

For each rule:
  * Cells: the kept record's real-data cells win; a dropped record's
    real-data cell fills a kept cell that is missing or not real-data
    (its citation and _provenance come along). Taxonomy axes the kept
    record lacks are filled the same way.
  * `cells` overwrites kept cells' values in place, keeping each cell's
    citation (used for subtractive edits such as splitting a combined row).
  * `name` renames the kept record; the id never changes.
  * Dropped records are removed. Their ids are written to
    taxonomy/system-aliases.json `redirects` (old id → kept id) so the site,
    the MCP server and the API keep resolving them, and `aliases` plus the
    dropped names are added as compat aliases of the kept record.
  * taxonomy/package-aliases.json entries of dropped / renamed records move
    to the kept record's (new) name; `packages` replaces the entry outright.

Then canonicalizes (render → extract → reconcile). Run `make build validate`
afterwards. Writes a merge log to extraction/merges-<date>/log.json.

Usage:
    python3 scripts/merge_records.py extraction/merges-2026-10/rules.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cell_writer import find_record, load_landscape, save_landscape  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE = ROOT / "data" / "landscape.json"
SYSTEM_ALIASES = ROOT / "taxonomy" / "system-aliases.json"
PACKAGE_ALIASES = ROOT / "taxonomy" / "package-aliases.json"


def write_json(path: Path, data: dict, indent: int) -> None:
    path.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8")


def fold(keep: dict, drop: dict) -> list[str]:
    """Fill the kept record's gaps from a dropped record; return filled slugs."""
    filled = []
    for slug, cell in (drop.get("cells") or {}).items():
        mine = keep["cells"].get(slug)
        if cell.get("status") == "real-data" and (not mine or mine.get("status") != "real-data"):
            keep["cells"][slug] = dict(cell)
            prov = (drop.get("_provenance") or {}).get(slug)
            if prov:
                keep.setdefault("_provenance", {})[slug] = prov
            elif slug in (keep.get("_provenance") or {}):
                del keep["_provenance"][slug]
            filled.append(slug)
    for axis, vals in (drop.get("taxonomy") or {}).items():
        if vals and not (keep.get("taxonomy") or {}).get(axis):
            keep.setdefault("taxonomy", {})[axis] = vals
    return filled


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rules")
    ap.add_argument("--no-canonicalize", action="store_true")
    args = ap.parse_args()

    spec = json.loads(Path(args.rules).read_text())
    landscape = load_landscape(LANDSCAPE)
    sys_aliases = json.loads(SYSTEM_ALIASES.read_text())
    pkg_aliases = json.loads(PACKAGE_ALIASES.read_text())
    aliases = sys_aliases.setdefault("aliases", {})
    redirects = sys_aliases.setdefault("redirects", {})
    packages = pkg_aliases["records"]
    log = []

    for rule in spec["rules"]:
        keep = find_record(landscape, rule["keep"])
        if keep is None:
            sys.exit(f"merge_records: kept id {rule['keep']!r} not found")
        old_name = keep["name"]
        drops = []
        for did in rule.get("drop", []):
            d = find_record(landscape, did)
            if d is None:
                sys.exit(f"merge_records: dropped id {did!r} not found")
            drops.append(d)

        filled = {d["id"]: fold(keep, d) for d in drops}
        for slug, value in (rule.get("cells") or {}).items():
            keep["cells"][slug]["value"] = value
        new_name = rule.get("name") or old_name
        keep["name"] = new_name

        # Compat aliases: keyed by name, so move the old key on a rename.
        names = list(aliases.pop(old_name, [])) if old_name != new_name else list(aliases.get(new_name, []))
        for d in drops:
            names += aliases.pop(d["name"], [])
        names += rule.get("aliases", []) + [d["name"] for d in drops]
        names = [n for n in dict.fromkeys(names) if n != new_name and n.split(" (")[0] != new_name]
        if names:
            aliases[new_name] = names
        else:
            aliases.pop(new_name, None)

        # Package aliases.
        pk = list(packages.pop(old_name, [])) if old_name != new_name else list(packages.get(new_name, []))
        for d in drops:
            pk += packages.pop(d["name"], [])
        if "packages" in rule:
            pk = rule["packages"]
        if pk:
            packages[new_name] = list(dict.fromkeys(pk))

        for d in drops:
            redirects[d["id"]] = keep["id"]
        # A kept id that was itself redirected earlier must not stay redirected.
        redirects.pop(keep["id"], None)
        for old, new in list(redirects.items()):
            if new in {d["id"] for d in drops}:
                redirects[old] = keep["id"]

        drop_ids = {d["id"] for d in drops}
        landscape["records"] = [r for r in landscape["records"] if r["id"] not in drop_ids]
        log.append({"kept_id": keep["id"], "name": new_name, "renamed_from": old_name if old_name != new_name else None,
                    "dropped": [{"id": d["id"], "name": d["name"], "cells_filled": filled[d["id"]]} for d in drops],
                    "cells_edited": sorted(rule.get("cells") or {}), "reason": rule["reason"]})

    # An alias that is now another record's own name (e.g. "OpenSearch" once
    # a combined row is split) would attribute that record's mentions here.
    names_now = {r["name"] for r in landscape["records"]}
    for key in list(aliases):
        aliases[key] = [a for a in aliases[key] if a not in names_now or a == key]
        if not aliases[key]:
            del aliases[key]
    sys_aliases["redirects"] = dict(sorted(redirects.items()))
    save_landscape(landscape, LANDSCAPE)
    write_json(SYSTEM_ALIASES, sys_aliases, 2)
    write_json(PACKAGE_ALIASES, pkg_aliases, 2)
    out = Path(args.rules).parent / "log.json"
    write_json(out, {"date": spec.get("date"), "merges": log}, 1)
    if not args.no_canonicalize:
        import apply_reverify
        apply_reverify.canonicalize()
    print(f"merge_records: {len(log)} rules, {sum(len(m['dropped']) for m in log)} records removed; log → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
