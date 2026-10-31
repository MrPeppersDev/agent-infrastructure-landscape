#!/usr/bin/env python3
"""
fetch_repo_health.py — maintainer-health signals per GitHub repo (#365).

For every repo in data/stack-index.json (`repos`: owner/repo → record id)
it asks the GitHub REST API for four things and reduces them to a few
numbers a buyer can read:

    GET /repos/{o}/{r}                               archived, stars, pushed_at
    GET /repos/{o}/{r}/issues?state=all&per_page=100 the 100 most recent issues
         &sort=created&direction=desc                (pull requests dropped)
    GET /repos/{o}/{r}/releases?per_page=100         releases in the last year
    GET /repos/{o}/{r}/contributors?per_page=100     commit shares (bus factor)

  issues_90d                 issues opened in the last 90 days (of the sample)
  responded_share            share of those that are closed or have a comment;
                             null when fewer than 3 issues were opened
  open_issue_median_age_days median age of the open issues in the sample
  releases_12mo              releases published in the last 365 days
  latest_release_at          date of the newest release
  bus_factor                 contributors needed to reach half of the sampled
                             commits (1 = one person wrote most of it)
  top_contributor_share      share of sampled commits by the top contributor

Output: data/repo-health.json — {"generatedAt", "windowDays", "repos":
{"owner/repo": {...}}}. The run is rolling: --max-repos (default 120) repos
per run, oldest `as_of` first, so the whole catalog refreshes about weekly
within the GITHUB_TOKEN rate limit. A repo that fails keeps its previous
entry plus an `error`. The daily workflow (.github/workflows/repo-health.yml)
commits the file; build_stack_index.py copies the numbers into
data/stack-index.json, where the system page, the stack check and the
leaderboards read them.

Usage:
  GITHUB_TOKEN=… python3 scripts/fetch_repo_health.py [--max-repos 120] [--min-age-days 6]
  python3 scripts/fetch_repo_health.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STACK_INDEX = ROOT / "data" / "stack-index.json"
OUT = ROOT / "data" / "repo-health.json"
WINDOW_DAYS = 90
API = "https://api.github.com"


class GitHubError(Exception):
    pass


def _date(iso: str | None) -> dt.date | None:
    if not iso:
        return None
    try:
        return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def summarize(repo: dict[str, Any], issues: list[dict[str, Any]], releases: list[dict[str, Any]],
              contributors: list[dict[str, Any]], today: dt.date) -> dict[str, Any]:
    """Pure reduction of the four API payloads to the health numbers."""
    only_issues = [i for i in issues if "pull_request" not in i]
    cutoff = today - dt.timedelta(days=WINDOW_DAYS)
    recent = [i for i in only_issues if (_date(i.get("created_at")) or dt.date.min) >= cutoff]
    responded = [i for i in recent if (i.get("comments") or 0) > 0 or i.get("state") == "closed"]
    open_ages = sorted((today - (_date(i.get("created_at")) or today)).days for i in only_issues if i.get("state") == "open")
    median_age = open_ages[len(open_ages) // 2] if open_ages else None
    year = today - dt.timedelta(days=365)
    published = [d for d in (_date(r.get("published_at")) for r in releases if not r.get("draft")) if d]
    rel12 = [d for d in published if d >= year]
    shares = sorted((int(c.get("contributions") or 0) for c in contributors), reverse=True)
    total = sum(shares)
    bus = None
    if total:
        acc = 0
        for n, s in enumerate(shares, start=1):
            acc += s
            if acc * 2 >= total:
                bus = n
                break
    return {
        "as_of": today.isoformat(),
        "archived": bool(repo.get("archived")),
        "stars": repo.get("stargazers_count"),
        "pushed_at": (_date(repo.get("pushed_at")) or today).isoformat() if repo.get("pushed_at") else None,
        "issues_90d": len(recent),
        "responded_share": round(len(responded) / len(recent), 2) if len(recent) >= 3 else None,
        "open_issues_sampled": len(open_ages),
        "open_issue_median_age_days": median_age,
        "issues_sampled": len(only_issues),
        "sample_truncated": len(issues) >= 100,
        "releases_12mo": len(rel12),
        "latest_release_at": max(published).isoformat() if published else None,
        "bus_factor": bus,
        "top_contributor_share": round(shares[0] / total, 2) if total else None,
        "contributors_sampled": len(shares),
    }


def _get(url: str, token: str | None, timeout: float = 20.0) -> tuple[Any, dict[str, str]]:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "agent-infrastructure-landscape-repo-health")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        headers = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        if e.code == 404:
            raise GitHubError("not-found") from e
        if e.code in (403, 429) and headers.get("x-ratelimit-remaining") == "0":
            raise GitHubError(f"rate-limited:{headers.get('x-ratelimit-reset', '')}") from e
        if e.code == 409:  # empty repository
            return [], headers
        raise GitHubError(f"http-{e.code}") from e
    except urllib.error.URLError as e:
        raise GitHubError(f"network:{e.reason}") from e


def fetch_repo(owner: str, repo: str, token: str | None, today: dt.date) -> dict[str, Any]:
    q = f"{API}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
    meta, _ = _get(q, token)
    issues, _ = _get(f"{q}/issues?state=all&per_page=100&sort=created&direction=desc", token)
    releases, _ = _get(f"{q}/releases?per_page=100", token)
    try:
        contributors, _ = _get(f"{q}/contributors?per_page=100&anon=false", token)
    except GitHubError as e:  # 204 / huge repos → GitHub may refuse; keep the rest
        contributors = []
        if not str(e).startswith("http-"):
            raise
    return summarize(meta, issues if isinstance(issues, list) else [], releases if isinstance(releases, list) else [],
                     contributors if isinstance(contributors, list) else [], today)


def load_out() -> dict[str, Any]:
    if OUT.exists():
        try:
            return json.loads(OUT.read_text())
        except json.JSONDecodeError:
            pass
    return {"generatedAt": None, "windowDays": WINDOW_DAYS, "repos": {}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-repos", type=int, default=120, help="repos to refresh this run (rolling, oldest first)")
    ap.add_argument("--min-age-days", type=int, default=6, help="skip repos refreshed more recently than this")
    ap.add_argument("--repos", default="", help="comma-separated owner/repo list instead of the index")
    ap.add_argument("--github-token", default=None)
    ap.add_argument("--dry-run", action="store_true", help="list what would be fetched; no network, no write")
    ap.add_argument("--today", default=None, help="YYYY-MM-DD (tests)")
    args = ap.parse_args(argv)
    token = args.github_token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    out = load_out()
    repos_all = [r.strip().lower() for r in args.repos.split(",") if r.strip()] if args.repos else \
        sorted((json.loads(STACK_INDEX.read_text()).get("repos") or {}).keys())

    def age(key: str) -> int:
        d = _date(((out["repos"].get(key) or {}).get("as_of") or "") + "T00:00:00Z")
        return (today - d).days if d else 10_000

    due = [k for k in repos_all if age(k) >= args.min_age_days]
    due.sort(key=lambda k: -age(k))
    batch = due[: args.max_repos]
    print(f"{len(repos_all)} repos in the index, {len(due)} due, fetching {len(batch)}", file=sys.stderr)
    if args.dry_run:
        for k in batch:
            print(k)
        return 0
    if not token:
        print("GITHUB_TOKEN is required (or --dry-run)", file=sys.stderr)
        return 2

    done = failed = 0
    for key in batch:
        owner, _, repo = key.partition("/")
        if not owner or not repo:
            continue
        try:
            out["repos"][key] = fetch_repo(owner, repo, token, today)
            out["repos"][key].pop("error", None)
            done += 1
        except GitHubError as e:
            msg = str(e)
            if msg.startswith("rate-limited:"):
                reset = msg.split(":", 1)[1]
                wait = max(0, int(float(reset or 0)) - int(time.time())) if reset else 60
                print(f"rate limited; waiting {min(wait, 900)}s", file=sys.stderr)
                time.sleep(min(wait, 900))
                try:
                    out["repos"][key] = fetch_repo(owner, repo, token, today)
                    done += 1
                    continue
                except GitHubError as e2:
                    msg = str(e2)
            prev = out["repos"].get(key) or {}
            out["repos"][key] = {**prev, "as_of": today.isoformat(), "error": msg}
            failed += 1
        time.sleep(0.3)

    out["generatedAt"] = today.isoformat()
    out["windowDays"] = WINDOW_DAYS
    out["repos"] = dict(sorted(out["repos"].items()))
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {done} refreshed, {failed} failed, {len(out['repos'])} repos total", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
