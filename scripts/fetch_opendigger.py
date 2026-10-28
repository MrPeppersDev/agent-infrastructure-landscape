#!/usr/bin/env python3
"""
fetch_opendigger.py — fill the `developer-activity-opendigger` cell (schema
v1.1.0, issue #150) from the OpenDigger API (X-lab2017/open-digger).

For every record with a GitHub repo (the record `url`, else the `gh` cell's
citation) it reads three monthly series from OpenDigger:

    https://oss.open-digger.cn/github/<owner>/<repo>/openrank.json
    https://oss.open-digger.cn/github/<owner>/<repo>/activity.json
    https://oss.open-digger.cn/github/<owner>/<repo>/participants.json

and writes the cell value as compact, key-sorted JSON:

    {"activity":…,"as_of":"YYYY-MM","openrank_12mo":…,"openrank_current":…,"participants":…}

  as_of             latest month present in the openrank series
  openrank_current  OpenRank for that month
  openrank_12mo     mean monthly OpenRank over the 12 months ending at as_of
  activity          OpenDigger activity score for as_of (null if absent)
  participants      participants for as_of (null if absent)

Repos OpenDigger doesn't index (404) get `depth-floor-reached` / "searched
not found". OpenRank is fetched from OpenDigger directly, never from the
antgroup CSV snapshot (licence not cleared; see DECISIONS.md 2026-10-28).

Raw responses are cached in extraction/opendigger-cache/<owner>__<repo>.json
so `--offline` reruns are deterministic. The cache doubles as the
checkpoint: a rerun skips repos already cached unless --refresh is given.
Requests are sequential with retries, because the session proxy drops
parallel connections.

Usage:
  python3 scripts/fetch_opendigger.py                       # fetch missing, write cells
  python3 scripts/fetch_opendigger.py --offline             # cache only, no network
  python3 scripts/fetch_opendigger.py --refresh             # re-fetch every repo
  python3 scripts/fetch_opendigger.py --repos a/b,c/d --no-write   # fill the cache only
  python3 scripts/fetch_opendigger.py --limit 20 --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from _cell_writer import load_landscape, save_landscape, update_cell

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LANDSCAPE = ROOT / "data" / "landscape.json"
CACHE_DIR = ROOT / "extraction" / "opendigger-cache"
SLUG = "developer-activity-opendigger"
BASE = "https://oss.open-digger.cn/github"
METRICS = ("openrank", "activity", "participants")
USER_AGENT = "agent-infrastructure-landscape-opendigger"
SCRIPT = "scripts/fetch_opendigger.py"

# Same pattern as fetch_commit_trajectories.py / check_staleness.py.
GITHUB_URL_RE = re.compile(
    r"https?://(?:www\.)?github\.com/([A-Za-z0-9._\-]+)/([A-Za-z0-9._\-]+?)(?:/|\.git|$|#|\?)",
    re.IGNORECASE,
)
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
NOT_REPOS = {"orgs", "topics", "sponsors", "features", "marketplace", "apps", "collections"}


def repo_for(record: dict[str, Any]) -> str | None:
    """owner/repo for a record, from its url or its gh cell's citation."""
    gh = (record.get("cells") or {}).get("gh") or {}
    for url in (record.get("url"), gh.get("citation")):
        m = GITHUB_URL_RE.match((url or "").strip() + "/")
        if m and m.group(1).lower() not in NOT_REPOS:
            return f"{m.group(1)}/{m.group(2)}"
    return None


def cache_path(repo: str) -> Path:
    return CACHE_DIR / (repo.replace("/", "__").lower() + ".json")


def http_json(url: str, attempts: int = 4) -> Any:
    """GET JSON; None on 404. Retries other failures with backoff."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err: Exception = e
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            err = e
        time.sleep(2 ** (i + 1))
    raise RuntimeError(f"{url}: {err}")


def fetch(repo: str) -> dict[str, Any]:
    """Raw series for one repo; {"missing": true} when OpenDigger has none."""
    out: dict[str, Any] = {"repo": repo}
    for metric in METRICS:
        data = http_json(f"{BASE}/{repo}/{metric}.json")
        if data is None and metric == "openrank":
            return {"repo": repo, "missing": True}
        out[metric] = {k: v for k, v in sorted((data or {}).items()) if MONTH_RE.match(k)}
        time.sleep(0.3)
    return out


def summarize(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Cell object from cached series, or None if there is no OpenRank data."""
    openrank = raw.get("openrank") or {}
    if raw.get("missing") or not openrank:
        return None
    months = sorted(openrank)
    as_of = months[-1]
    window = [openrank[m] for m in months[-12:]]
    return {
        "activity": (raw.get("activity") or {}).get(as_of),
        "as_of": as_of,
        "openrank_12mo": round(sum(window) / len(window), 2),
        "openrank_current": openrank[as_of],
        "participants": (raw.get("participants") or {}).get(as_of),
    }


def cell_value(summary: dict[str, Any]) -> str:
    return json.dumps(summary, sort_keys=True, separators=(",", ":"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--landscape", type=Path, default=DEFAULT_LANDSCAPE)
    ap.add_argument("--offline", action="store_true", help="use the cache only; never touch the network")
    ap.add_argument("--refresh", action="store_true", help="re-fetch repos that are already cached")
    ap.add_argument("--repos", help="comma-separated owner/repo list instead of walking the catalog")
    ap.add_argument("--no-write", action="store_true", help="fill the cache only; leave landscape.json alone")
    ap.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    ap.add_argument("--limit", type=int, default=0, help="stop after N repos (0 = all)")
    ap.add_argument("--date", default=dt.date.today().isoformat(), help="scraped_at / last_verified_at date")
    args = ap.parse_args()

    landscape = load_landscape(args.landscape)
    if args.repos:
        targets = {r.strip(): [] for r in args.repos.split(",") if r.strip()}
    else:
        targets = {}
        for rec in landscape["records"]:
            repo = repo_for(rec)
            if repo:
                targets.setdefault(repo, []).append(rec)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stats = {"repos": 0, "fetched": 0, "cached": 0, "missing": 0, "failed": 0, "cells_changed": 0}
    for repo, recs in sorted(targets.items(), key=lambda kv: kv[0].lower()):
        if args.limit and stats["repos"] >= args.limit:
            break
        stats["repos"] += 1
        path = cache_path(repo)
        if path.exists() and not args.refresh:
            raw = json.loads(path.read_text(encoding="utf-8"))
            stats["cached"] += 1
        elif args.offline:
            continue
        else:
            try:
                raw = fetch(repo)
            except RuntimeError as e:
                print(f"warn: {e}", file=sys.stderr)
                stats["failed"] += 1
                continue
            if not args.dry_run:
                path.write_text(json.dumps(raw, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            stats["fetched"] += 1

        summary = summarize(raw)
        stats["missing"] += summary is None
        if args.no_write:
            continue
        citation = f"{BASE}/{repo}/openrank.json"
        for rec in recs:
            if summary is None:
                changed = update_cell(rec, SLUG, value="searched not found",
                                      status="depth-floor-reached", citation=citation)
            else:
                changed = update_cell(rec, SLUG, value=cell_value(summary), status="real-data",
                                      citation=citation, last_verified_at=args.date)
            if changed:
                rec["cells"][SLUG].pop("tier", None)  # recomputed from the citation on round-trip
                rec.setdefault("_provenance", {})[SLUG] = {
                    "scrape_url": citation,
                    "scraped_at": args.date,
                    "script": SCRIPT,
                    "source": "scrape",
                    "verified": True,
                }
                stats["cells_changed"] += 1

    if stats["cells_changed"] and not (args.dry_run or args.no_write):
        save_landscape(landscape, args.landscape)
    print(json.dumps(stats))
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
