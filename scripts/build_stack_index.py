#!/usr/bin/env python3
"""
build_stack_index.py — compile data/stack-index.json for the stack checker.

The stack checker ("check my stack": web /check, MCP tool `check_stack`,
CLI `landscape check`) takes a project's dependency manifest and reports
which dependencies are catalogued systems that are archived, deprecated,
acquired, renamed, stale, or tied to one model vendor. This script does
the heavy part once, at build time, so the three surfaces only need a
small JSON file:

  packages: { "npm:flowise": "<record id>", "pypi:mem0ai": "<id>", ... }
  repos:    { "flowiseai/flowise": "<id>", ... }        (git / GitHub deps)
  records:  { "<id>": {name, family, status, severity, note, evidence,
                       last_commit, license, llm_lock, url} }

Package names come from (1) taxonomy/package-aliases.json (curated),
(2) pypi.org/project/<x> and npmjs.com/package/<x> citations in any cell,
and (3) the record's GitHub repo. Status is derived only from catalogued
facts: decay_cause, "(now X)" names, dated lifecycle text in desc/funding/
gh cells, and the gh cell's last-commit month.

Usage: python3 scripts/build_stack_index.py [--today YYYY-MM-DD]   (default: latest last_verified_at)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE = ROOT / "data" / "landscape.json"
ALIASES = ROOT / "taxonomy" / "package-aliases.json"
FAMILIES = ROOT / "taxonomy" / "families.json"
OUT = ROOT / "data" / "stack-index.json"

PYPI = re.compile(r"pypi\.org/project/([A-Za-z0-9._-]+)")
NPM = re.compile(r"npmjs\.com/package/((?:@[\w.-]+/)?[\w.-]+)")
GH = re.compile(r"github\.com/([\w.-]+)/([\w.-]+)", re.I)
GH_VALUE = re.compile(r"^\s*(?:github\.com/)?([\w.-]+)/([\w.-]+)")
COMMIT = re.compile(r"last (?:commit|push|update)[^0-9]{0,12}(20\d\d)-(\d\d)", re.I)
ARCHIVED = re.compile(r"(?<!not )(?<!un)\barchived\b(?![^.]*\bnot archived)", re.I)
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b"
# "acquired by" in any case; the acquirer: up to four Capitalised words,
# stopping before a month, a year or a lower-case word.
ACQUIRED = re.compile(r"(?i:\bacquired by) ((?!" + MONTH + r")[A-Z][\w&.\-]*(?: (?!" + MONTH + r")[A-Z][\w&.\-]*){0,3})")
# Context that means the acquisition is about someone else (a founder's
# previous company, a parent of a parent…), not this system.
NOT_SELF = re.compile(r"\b(ex-|former|previously|founded by|founders?|co-?founder|team from)\b", re.I)
SHUT = re.compile(r"\b(shut down|sunset|discontinued|end of life|end-of-life|receivership|liquidation|wound down|went offline)\b", re.I)
DEPRECATED = re.compile(r"\b(deprecated|superseded by|no longer (?:actively )?maintained|read-only)\b", re.I)
MAINT = re.compile(r"\b(maintenance mode|maintenance only|bug ?fixes (?:and|/) security only|successor (?:is|product)|now Microsoft Agent Framework)\b", re.I)
# Context meaning a lifecycle word is about a different product ("distinct
# from the older Codex API (deprecated 2023)", "unlike X, which was
# archived"), not this system.
OTHER = re.compile(r"\b(distinct from|unlike|not to be confused|older|predecessor|the old|legacy|formerly|replaces|replaced the|successor to|instead of|vs\.?)\b", re.I)


def self_match(rx: re.Pattern, *texts: str):
    """First match of `rx` in any text whose preceding clause doesn't point
    at another product (OTHER within the same sentence, up to 80 chars)."""
    for t in texts:
        for m in rx.finditer(t):
            pre = re.split(r"[.;]\s", t[max(0, m.start() - 80):m.start()])[-1]
            if OTHER.search(pre):
                continue
            return m
    return None


NOW = re.compile(r"\(now ([^)]+)\)\s*$")

# Repos that are not one product (orgs' docs/monorepos) — never index.
SKIP_REPO_NAMES = {"docs", "core", "sdk", "python", "js", "api", "cli", "server",
                   "examples", "awesome", "paper", "code", "main", "app"}

SEVERITY = {"dead": 3, "archived": 3, "deprecated": 3, "maintenance": 2, "acquired": 2, "renamed": 1,
            "stale": 2, "research-code": 1, "inactive": 2, "active": 0}


def norm_pkg(eco: str, name: str) -> str:
    name = name.strip().lower()
    if eco == "pypi":
        name = re.sub(r"[-_.]+", "-", name)  # PEP 503
    return f"{eco}:{name}"


def cell(rec: dict, k: str) -> str:
    c = rec["cells"].get(k) or {}
    if c.get("status") in ("not-applicable",):
        return ""
    return str(c.get("value") or "")


def lifecycle(rec: dict, today: dt.date) -> dict:
    """Derive one status for a record from catalogued facts only."""
    name, desc, fund, gh = rec["name"], cell(rec, "desc"), cell(rec, "funding"), cell(rec, "gh")
    text = " ".join([desc, fund, gh, cell(rec, "latest-release")])
    decay = rec.get("decay_cause")
    status, note, evidence = "active", "", rec.get("decay_evidence") or rec.get("url")

    m = COMMIT.search(gh)
    last_commit = f"{m.group(1)}-{m.group(2)}" if m else None

    if decay == "archived" or ARCHIVED.search(gh):
        status, note = "archived", "repository archived (read-only)"
    elif decay == "superseded":
        status, note = "deprecated", "superseded by a successor product"
    elif decay in ("pivoted", "unfunded", "lost-benchmark-race"):
        status, note = "inactive", f"no longer developed ({decay})"
    elif decay == "acquired":
        status, note = "acquired", "acquired"
    elif decay == "research-complete":
        status, note = "research-code", "research code; not maintained as a product"
    elif decay == "unknown":
        status, note = "inactive", "development has stopped"

    sm = self_match(SHUT, desc, fund)
    if status == "active" and sm:
        status, note = "dead", f"{sm.group(0)}"
    dm = self_match(DEPRECATED, desc, gh)
    if status == "active" and dm:
        status, note = "deprecated", dm.group(0)
    mm = self_match(MAINT, desc, gh)
    if status == "active" and mm:
        status, note = "maintenance", "maintenance mode (bug and security fixes only)"
    am = None
    for txt in (desc, fund):
        for m in ACQUIRED.finditer(txt):
            pre = txt[max(0, m.start() - 45):m.start()]
            if NOT_SELF.search(pre):
                continue
            am = m
            break
        if am:
            break
    nm = NOW.search(name)
    if status == "active" and am:
        status, note = "acquired", f"acquired by {am.group(1)}"
    if status == "active" and nm:
        status, note = "renamed", f"now {nm.group(1)}"
    elif nm and note and "now " not in note:
        note = f"{note}; now {nm.group(1)}"

    if status == "active" and last_commit:
        y, mo = map(int, last_commit.split("-"))
        months = (today.year - y) * 12 + (today.month - mo)
        if months >= 12:
            status, note = "stale", f"no commits since {last_commit}"

    # a sentence of context from desc when it names the event
    ctx = ""
    for sent in re.split(r"(?<=[.;])\s+", desc):
        if re.search(r"acquir|archiv|sunset|shut|deprecat|renam|discontinu|receivership|liquidat|now ", sent, re.I):
            ctx = sent.strip()
            break
    return {"status": status, "severity": SEVERITY[status], "note": note,
            "context": ctx[:240], "evidence": evidence, "last_commit": last_commit}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=None)
    args = ap.parse_args()
    data = json.loads(LANDSCAPE.read_text())
    recs = data["records"]
    # Age staleness against the data's own latest verification date, not
    # the wall clock, so the index is a pure function of the dataset and
    # rebuilding it doesn't churn.
    latest = max((r.get("last_verified_at") or "") for r in recs) or dt.date.today().isoformat()
    today = dt.date.fromisoformat(args.today or latest)
    by_name = {r["name"]: r for r in recs}
    fam = {s: f["id"] for f in json.loads(FAMILIES.read_text())["families"] for s in f["sections"]}

    packages: dict[str, str] = {}
    repos: dict[str, str] = {}
    sources: dict[str, str] = {}

    def add_pkg(key: str, rid: str, src: str) -> None:
        if key not in packages:
            packages[key] = rid
            sources[key] = src

    aliases = json.loads(ALIASES.read_text())["records"]
    missing = []
    for rname, pkgs in aliases.items():
        rec = by_name.get(rname)
        if rec is None:
            missing.append(rname)
            continue
        for p in pkgs:
            eco, _, nm = p.partition(":")
            add_pkg(norm_pkg(eco, nm), rec["id"], "curated")

    for r in recs:
        blob = json.dumps(r["cells"])
        for m in PYPI.finditer(blob):
            add_pkg(norm_pkg("pypi", m.group(1)), r["id"], "pypi-citation")
        for m in NPM.finditer(blob):
            add_pkg(norm_pkg("npm", m.group(1)), r["id"], "npm-citation")
        gh_cell = r["cells"].get("gh") or {}
        cands = [gh_cell.get("citation") or "", r.get("url") or ""]
        m = GH_VALUE.match(str(gh_cell.get("value") or ""))
        if m and gh_cell.get("status") == "real-data":
            cands.append(f"github.com/{m.group(1)}/{m.group(2)}")
        for c in cands:
            gm = GH.search(c)
            if not gm:
                continue
            owner, repo = gm.group(1).lower(), gm.group(2).lower().removesuffix(".git")
            key = f"{owner}/{repo}"
            repos.setdefault(key, r["id"])
            # repo-name guesses: only distinctive names
            if len(repo) >= 5 and repo not in SKIP_REPO_NAMES:
                for eco in ("pypi", "npm"):
                    k = norm_pkg(eco, repo)
                    if k not in packages:
                        packages[k] = r["id"]
                        sources[k] = "repo-name"
            break

    used = set(packages.values()) | set(repos.values())
    records = {}
    for r in recs:
        if r["id"] not in used:
            continue
        sec = next((s["section"] for s in r["sections"] if s.get("primary")), r["sections"][0]["section"])
        lc = lifecycle(r, today)
        lock = cell(r, "llm-lock")
        records[r["id"]] = {
            "name": r["name"], "family": fam.get(sec, "other"), "section": sec,
            "url": r.get("url"), "license": cell(r, "license")[:80],
            "llm_lock": lock[:120] if lock and not re.match(r"(none|no\b|model-agnostic|any)", lock, re.I) else "",
            **lc,
        }

    out = {"generatedAt": today.isoformat(), "sourceGeneratedAt": data.get("generatedAt"),
           "packages": dict(sorted(packages.items())), "packageSource": dict(sorted(sources.items())),
           "repos": dict(sorted(repos.items())), "records": records}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=False) + "\n")
    flagged = sum(1 for v in records.values() if v["severity"] >= 2)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(packages)} packages, {len(repos)} repos, "
          f"{len(records)} records ({flagged} with severity >= 2)")
    if missing:
        print(f"warn: package-aliases.json names unknown records: {missing}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
