#!/usr/bin/env python3
"""
lint_contradictions.py — flag records whose own cells disagree with each
other, plus mechanical defects that make a published row look wrong.

Checks (each finding names the record, the cells involved and why):
  oss-conflict      license cell is an OSI licence (or gh names a repo with
                    stars) while another cell says the code is closed / not
                    OSS / paper-only / has no repo.
  acquired-year     two cells give different years for the same "acquired
                    by X" event.
  truncated         a value cut off mid-word with a trailing ellipsis.
  bare-citation     a citation that is only the root of a multi-tenant host
                    (https://github.com/, https://news.ycombinator.com/), so
                    it points at nothing about this record. A vendor's own
                    homepage is a fine citation and is not flagged.
  bad-citation      a citation whose first token is not a URL with a dotted
                    host ("https://no data - no public code found"), so it
                    links nowhere. A note after a real URL is fine.
  blank-taxonomy    an Agent Memory / Memory Research record whose seven
                    taxonomy axes are all n/a.
  edge-midword      an edge whose evidence excerpt starts in the middle of a
                    word of the cell it was cut from (#327).
  edge-verification-old
                    an integration edge whose verified_at stamp is more than
                    a year old, so its page should be re-checked (#360).
  stars-in-prose    a claims / desc / pros cell quoting a GitHub star count
                    while the gh cell carries the live one, so the page shows
                    two different numbers (#326).

Visibility only: exits 0 unless --fail-on is given. `make lint` runs it;
CI prints the summary on every PR.

Usage:
    python3 scripts/lint_contradictions.py [--json out.json] [--family memory] [--fail-on oss-conflict,...]
"""

from __future__ import annotations

import argparse
import datetime
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE = ROOT / "data" / "landscape.json"
EDGES = ROOT / "data" / "landscape.edges.json"
FAMILIES = ROOT / "taxonomy" / "families.json"

OSI = re.compile(r"\b(MIT|Apache[- ]?2(\.0)?|BSD|MPL|LGPL|AGPL|GPL|ISC|Unlicense|CC-BY)\b", re.I)
CLOSED = re.compile(
    r"\b(not OSS|not open[- ]source|closed[- ]source|code closed|proprietary only|"
    r"no (public )?(github )?repo|paper only|no code (release|released)|weights closed)\b", re.I)
ACQ = re.compile(r"acquired by ([A-Z][\w&.\- ]{1,30}?)[ ,(]+(?:in |on )?(?:\w+ )?(20\d\d)", re.I)
GOOD_URL = re.compile(r"^https?://[^\s/]+\.[^\s/]+")
BARE = re.compile(r"^https?://(www\.)?(github\.com|news\.ycombinator\.com|arxiv\.org|huggingface\.co|"
                  r"x\.com|twitter\.com|linkedin\.com|reddit\.com|medium\.com|pypi\.org|npmjs\.com|"
                  r"youtube\.com|crunchbase\.com|techcrunch\.com|google\.com)/?$", re.I)
SKIP_STATUS = {"not-applicable"}


# A star count in prose: "~51k★", "871 stars", "~2.3k GitHub stars".
STARS = re.compile(r"\d[\d.,]*\s*[kKmM]?\+?\s*(?:★|GitHub stars|GH stars|stars\b)", re.I)

def families() -> dict[str, str]:
    data = json.loads(FAMILIES.read_text())
    return {s: f["id"] for f in data["families"] for s in f["sections"]}


def primary_section(rec: dict) -> str:
    for s in rec.get("sections", []):
        if s.get("primary"):
            return s["section"]
    return rec["sections"][0]["section"]


def lint(rec: dict, fam: str) -> list[dict]:
    out: list[dict] = []
    cells = rec["cells"]

    def val(k: str) -> str:
        c = cells.get(k) or {}
        return "" if c.get("status") in SKIP_STATUS else str(c.get("value") or "")

    lic = val("license")
    # A licence cell that leads with "proprietary" / "not applicable" and
    # only mentions an OSI licence for an older or unofficial artefact
    # ("Grok 4 proprietary; Grok-1 weights Apache-2.0") is not an OSS claim.
    if re.match(r"\s*(proprietary|not applicable|n/a|closed)", lic, re.I):
        lic = ""
    gh = val("gh")
    gh_has_repo = (bool(re.search(r"[\w.-]+/[\w.-]+", gh))
                   and bool(re.search(r"\d[\d.,]*\s*k?\s*(★|stars)", gh, re.I))
                   # a repo marked unofficial / older-version-only doesn't
                   # make the record itself open source
                   and not re.search(r"unofficial|third-party|older|only\)", gh, re.I))
    if OSI.search(lic) or gh_has_repo:
        for k, c in cells.items():
            if k in ("license",) or c.get("status") in SKIP_STATUS:
                continue
            v = str(c.get("value") or "")
            m = CLOSED.search(v)
            # "Code public + weights closed" is a normal shape for code
            # projects (there are no weights to release), not a conflict.
            if m and m.group(0).lower() == "weights closed" and re.search(r"code (public|open)", v, re.I):
                m = None
            # One cell saying "the SDK repo is open, the service is closed
            # source" is a precise statement, not a contradiction.
            if m and k == "gh" and not OSI.search(lic) and re.search(r"\b(SDK|examples?|client|agents? repo)\b", v, re.I):
                m = None
            if m:
                out.append({"check": "oss-conflict", "cells": ["license" if OSI.search(lic) else "gh", k],
                            "why": f"{'license=' + lic[:40] if OSI.search(lic) else 'gh=' + gh[:50]} but {k} says '{m.group(0)}'"})

    years: dict[str, set] = collections.defaultdict(set)
    where: dict[str, list] = collections.defaultdict(list)
    for k, c in cells.items():
        for m in ACQ.finditer(str(c.get("value") or "")):
            who = m.group(1).strip().lower().split()[0]
            years[who].add(m.group(2))
            where[who].append(k)
    for who, ys in years.items():
        if len(ys) > 1:
            out.append({"check": "acquired-year", "cells": sorted(set(where[who])),
                        "why": f"acquired by {who}: years {sorted(ys)}"})

    for k, c in cells.items():
        v = str(c.get("value") or "")
        if k.endswith("trajectory") or c.get("status") in SKIP_STATUS:
            continue
        if v.endswith("…"):
            out.append({"check": "truncated", "cells": [k], "why": v[-60:]})
        cit = c.get("citation") or ""
        if cit and BARE.match(cit):
            out.append({"check": "bare-citation", "cells": [k], "why": cit})
        if cit and not GOOD_URL.match(cit.split()[0]):
            out.append({"check": "bad-citation", "cells": [k], "why": cit[:80]})

    gh_cell = cells.get("gh") or {}
    if gh_cell.get("status") == "real-data" and gh_cell.get("value"):
        for k in ("claims", "desc", "pros"):
            m = STARS.search(str((cells.get(k) or {}).get("value") or ""))
            if m:
                out.append({"check": "stars-in-prose", "cells": ["gh", k], "why": f"{k} says '{m.group(0)}'; gh={str(gh_cell['value'])[:30]}"})

    if fam in ("memory", "memory-research"):
        tax = rec.get("taxonomy") or {}
        if tax and all(all(v.get("value") == "n/a" for v in vals) for vals in tax.values()):
            out.append({"check": "blank-taxonomy", "cells": [], "why": "all seven taxonomy axes are n/a"})
    return out


def lint_edges(recs: list[dict]) -> list[dict]:
    """edge-midword: an excerpt found inside one of its endpoints' cells
    right after a letter or digit was cut mid-word.
    edge-verification-old: an integration edge whose verified_at stamp is
    more than a year old, so the integration page should be re-checked
    (#360)."""
    if not EDGES.exists():
        return []
    by_id = {r["id"]: r for r in recs}
    out = []
    today = datetime.date.today()
    for e in json.loads(EDGES.read_text()).get("edges", []):
        va = e.get("verified_at")
        if va:
            try:
                age = (today - datetime.date.fromisoformat(va)).days
            except ValueError:
                age = None
            if age is not None and age > 365:
                out.append({"id": e["source"], "name": by_id.get(e["source"], {}).get("name", e["source"]), "family": "edges",
                            "check": "edge-verification-old", "cells": [],
                            "why": f"{e['type']} -> {e['target']}: verified {va}, {age} days ago"})
        ev = re.sub(r"^[\w-]+ cell: ", "", e.get("evidence") or "").lstrip("…").rstrip(".…").strip()[:40]
        if len(ev) < 8:
            continue
        for rid in (e["source"], e["target"]):
            r = by_id.get(rid)
            hit = r and any(
                (i := str(c.get("value") or "").find(ev)) > 0 and str(c.get("value") or "")[i - 1].isalnum()
                for c in r.get("cells", {}).values()
            )
            if hit:
                out.append({"id": e["source"], "name": by_id.get(e["source"], {}).get("name", e["source"]), "family": "edges",
                            "check": "edge-midword", "cells": [], "why": f"{e['type']} -> {e['target']}: '{ev[:30]}'"})
                break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--family", default=None, help="only this product family id")
    ap.add_argument("--fail-on", default="", help="comma-separated checks that should fail the run")
    args = ap.parse_args()

    s2f = families()
    recs = json.loads(LANDSCAPE.read_text())["records"]
    findings = []
    for r in recs:
        fam = s2f.get(primary_section(r), "other")
        if args.family and fam != args.family:
            continue
        for f in lint(r, fam):
            findings.append({"id": r["id"], "name": r["name"], "family": fam, **f})

    findings += lint_edges(recs)

    by = collections.Counter(f["check"] for f in findings)
    print(f"lint_contradictions: {len(findings)} findings across "
          f"{len({f['id'] for f in findings})} records")
    for k, n in by.most_common():
        print(f"  {k:18} {n}")
    if args.json:
        Path(args.json).write_text(json.dumps(findings, indent=1, ensure_ascii=False))
    fail = {c.strip() for c in args.fail_on.split(",") if c.strip()}
    return 1 if fail & set(by) else 0


if __name__ == "__main__":
    sys.exit(main())
