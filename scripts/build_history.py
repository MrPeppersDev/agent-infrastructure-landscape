#!/usr/bin/env python3
"""
build_history.py — per-system change history from git → data/history.json.

Walks every first-parent commit on the current branch that touched
data/landscape.json, oldest first, and diffs each version of every record
against the previous one. The output feeds:

  * the "What changed" section on each /systems/<id> page,
  * per-system Atom feeds (/feeds/<id>.xml) and the catalog-wide
    /changes.xml, which "watch my stack" bundles into an OPML file,
  * the MCP `recent_changes` / `system_history` tools.

Only facts a builder would act on are tracked: lifecycle (decay_cause,
name, url, tier) and a curated set of cells (license, latest release,
pricing, deployment, MCP/A2A support…). Cosmetic churn in long prose cells
and GitHub star counts is ignored.

Needs full git history (actions/checkout `fetch-depth: 0`). With a shallow
clone it keeps the committed data/history.json rather than truncating it.

Usage: python3 scripts/build_history.py [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "history.json"
PATH = "data/landscape.json"

RECORD_FIELDS = ["name", "url", "tier", "decay_cause"]
CELL_FIELDS = {
    "license": "License",
    "latest-release": "Latest release",
    "pricing": "Pricing",
    "funding": "Funding / ownership",
    "deployment": "Deployment",
    "mcp-support": "MCP support",
    "a2a-support": "A2A support",
    "type": "Type",
    "backend-storage": "Backend storage",
    "llm-lock": "Model lock-in",
    "multi-tenancy": "Multi-tenancy",
    "compliance": "Compliance",
}
LABEL = {"name": "Name", "url": "Homepage", "tier": "Tier", "decay_cause": "Lifecycle"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def norm(v) -> str:
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip()


def snapshot(sha: str) -> dict[str, dict]:
    raw = git("show", f"{sha}:{PATH}")
    data = json.loads(raw)
    out = {}
    for r in data.get("records", []):
        cells = r.get("cells") or {}
        snap = {f: norm(r.get(f)) for f in RECORD_FIELDS}
        for k in CELL_FIELDS:
            c = cells.get(k) or {}
            snap[k] = norm(c.get("value")) if c.get("status") not in ("no-data", "depth-floor-reached") else ""
            snap[k + "@cite"] = c.get("citation") or ""
        out[r["id"]] = snap
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the output would change")
    args = ap.parse_args()

    if git("rev-parse", "--is-shallow-repository").strip() == "true":
        print("shallow clone: keeping committed data/history.json", file=sys.stderr)
        return 0

    log = git("log", "--first-parent", "--reverse", "--format=%H%x09%cs%x09%s", "--", PATH).strip().splitlines()
    if not log:
        print("no history for data/landscape.json", file=sys.stderr)
        return 0

    events: dict[str, list[dict]] = {}
    prev: dict[str, dict] | None = None
    for line in log:
        sha, date, subject = line.split("\t", 2)
        try:
            cur = snapshot(sha)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        m = re.search(r"#(\d+)", subject)
        ref = {"date": date, "commit": sha[:10], "pr": int(m.group(1)) if m else None}
        if prev is not None:
            for rid, snap in cur.items():
                old = prev.get(rid)
                if old is None:
                    events.setdefault(rid, []).append({**ref, "kind": "added", "changes": []})
                    continue
                changes = []
                for f in RECORD_FIELDS + list(CELL_FIELDS):
                    if snap[f] != old[f]:
                        ch = {"field": f, "label": LABEL.get(f) or CELL_FIELDS[f],
                              "from": old[f][:300], "to": snap[f][:300]}
                        if not old[f]:
                            ch["first"] = True  # first time the catalog recorded this field
                        cite = snap.get(f + "@cite")
                        if cite:
                            ch["source"] = cite
                        changes.append(ch)
                if changes:
                    kind = "lifecycle" if any(c["field"] in ("decay_cause", "name") for c in changes) else "update"
                    events.setdefault(rid, []).append({**ref, "kind": kind, "changes": changes})
            for rid in prev.keys() - cur.keys():
                events.setdefault(rid, []).append({**ref, "kind": "removed", "changes": []})
        prev = cur

    for v in events.values():
        v.reverse()  # newest first
    out = {"baseline": log[0].split("\t")[1], "records": dict(sorted(events.items()))}
    text = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    if args.check:
        same = OUT.exists() and OUT.read_text() == text
        print("history up to date" if same else "history would change")
        return 0 if same else 1
    OUT.write_text(text)
    n = sum(len(v) for v in events.values())
    print(f"wrote {OUT.relative_to(ROOT)}: {n} events across {len(events)} records (baseline {out['baseline']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
