#!/usr/bin/env python3
"""
dataset_release_notes.py — Markdown notes for a monthly dataset release
(.github/workflows/dataset-release.yml): catalog size, and the recorded
changes of the previous calendar month from data/history.json, grouped
by kind, each linking its system page.

Usage:
    python3 scripts/dataset_release_notes.py --tag dataset-2026-11 [--month 2026-10]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://mrpeppersdev.github.io/agent-infrastructure-landscape"
REPO = "https://github.com/MrPeppersDev/agent-infrastructure-landscape"


def previous_month(today: dt.date) -> str:
    first = today.replace(day=1)
    return (first - dt.timedelta(days=1)).strftime("%Y-%m")


def notes(tag: str, month: str) -> str:
    land = json.loads((ROOT / "data" / "landscape.json").read_text())
    edges = json.loads((ROOT / "data" / "landscape.edges.json").read_text())
    hist = json.loads((ROOT / "data" / "history.json").read_text())
    names = {r["id"]: r["name"] for r in land["records"]}
    kinds: dict[str, list[str]] = {"added": [], "lifecycle": [], "update": [], "removed": []}
    for rid, events in hist.get("records", {}).items():
        for e in events:
            if not e["date"].startswith(month):
                continue
            label = names.get(rid, rid)
            fields = ", ".join(sorted({c["label"] for c in e.get("changes", [])})) or ("added to the catalog" if e["kind"] == "added" else "record")
            kinds.setdefault(e["kind"], []).append(f"- {e['date']} [{label}]({SITE}/systems/{rid}): {fields}")
    out = [
        f"# {tag}",
        "",
        f"The AI Agent Infrastructure Landscape catalog as of {dt.date.today().isoformat()}: "
        f"{len(land['records']):,} systems and {len(edges['edges']):,} typed edges, every value with its source. "
        f"Licence: CC-BY-4.0. Cite this release by its tag; the files are attached.",
        "",
        f"## Changes recorded in {month}",
        "",
    ]
    titles = {"added": "New systems", "lifecycle": "Lifecycle (acquisitions, archivals, renames, shutdowns)", "update": "Fact updates (licence, release, pricing, hosting, funding)", "removed": "Removed or merged"}
    total = 0
    for k, title in titles.items():
        rows = sorted(kinds.get(k, []), reverse=True)
        total += len(rows)
        if not rows:
            continue
        out += [f"### {title} ({len(rows)})", "", *rows[:200]]
        if len(rows) > 200:
            out.append(f"- … and {len(rows) - 200} more: {SITE}/changes")
        out.append("")
    if not total:
        out += ["No recorded changes that month.", ""]
    out += [f"All changes, by week: {SITE}/changes · Data and API: {SITE}/data · Source: {REPO}"]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--month", help="YYYY-MM (default: the previous calendar month)")
    a = ap.parse_args()
    print(notes(a.tag, a.month or previous_month(dt.date.today())), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
