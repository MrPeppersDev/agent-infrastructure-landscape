#!/usr/bin/env python3
"""
bot_status.py — last run and last success of every GitHub Actions workflow,
for the public /status page (product review, 2026-10-30: "a public
bot-health status page").

Writes data/bot-status.json. Run by the Pages deploy (pages.yml) with the
workflow's GITHUB_TOKEN (actions: read); without a token or network it
writes {"available": false} and the page says so. Not committed.

Usage:
    GH_TOKEN=... python3 scripts/bot_status.py [--repo owner/name] [--out data/bot-status.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def status(repo: str, token: str) -> dict:
    api = f"https://api.github.com/repos/{repo}/actions"
    wfs = get(f"{api}/workflows?per_page=100", token)["workflows"]
    out = []
    for w in sorted(wfs, key=lambda w: w["name"].lower()):
        if w.get("state") != "active":
            continue
        runs = get(f"{api}/workflows/{w['id']}/runs?per_page=20&exclude_pull_requests=true", token).get("workflow_runs", [])
        last = runs[0] if runs else None
        ok = next((r for r in runs if r.get("conclusion") == "success"), None)
        out.append({
            "name": w["name"],
            "file": w["path"].rsplit("/", 1)[-1],
            "url": w["html_url"],
            "lastRun": last and {"at": last["created_at"], "event": last["event"], "status": last["status"], "conclusion": last.get("conclusion"), "url": last["html_url"]},
            "lastSuccess": ok and {"at": ok["created_at"], "url": ok["html_url"]},
            "recentRuns": len(runs),
            "recentFailures": sum(1 for r in runs if r.get("conclusion") == "failure"),
        })
    return {"available": True, "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "repo": repo, "workflows": out}


def _get(url: str, token: str = "") -> dict | None:
    req = urllib.request.Request(url, headers={"Accept": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception:
        return None


def usage(repo: str, token: str) -> dict:
    """Public counts for /status: npm downloads of the MCP server and the
    repo's stars and forks. Each is null when its API doesn't answer."""
    week = _get("https://api.npmjs.org/downloads/point/last-week/landscape-mcp") or {}
    month = _get("https://api.npmjs.org/downloads/point/last-month/landscape-mcp") or {}
    gh = _get(f"https://api.github.com/repos/{repo}", token) or {}
    return {
        "npmPackage": "landscape-mcp",
        "npmLastWeek": week.get("downloads"),
        "npmLastMonth": month.get("downloads"),
        "stars": gh.get("stargazers_count"),
        "forks": gh.get("forks_count"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "MrPeppersDev/agent-infrastructure-landscape"))
    ap.add_argument("--out", default=str(ROOT / "data" / "bot-status.json"))
    a = ap.parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    try:
        if not token:
            raise RuntimeError("no GH_TOKEN")
        data = status(a.repo, token)
    except Exception as e:  # the page says "not available" rather than failing the deploy
        data = {"available": False, "reason": str(e)[:200]}
    data["usage"] = usage(a.repo, token)
    Path(a.out).write_text(json.dumps(data, indent=1) + "\n")
    print(f"bot_status: {'%d workflows' % len(data['workflows']) if data.get('available') else 'not available (' + data['reason'] + ')'} → {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
