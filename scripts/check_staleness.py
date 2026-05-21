#!/usr/bin/env python3
"""
check_staleness.py — flag catalog rows whose upstream repo has gone quiet.

Issue #38 (T0-4). Reads ``data/landscape.json``, finds records with a GitHub
``repo-url`` signal, and emits a list of rows whose latest commit is older
than the freshness SLA threshold defined in MAINTAINER.md §2 (active <12mo,
stale 12-24mo, abandoned >24mo).

This is the testable core. The CI wrapper at .github/workflows/staleness.yml
calls this script and then opens (or updates) a GitHub Issue per flagged
row with the ``stale-row`` label.

Modes
-----

  --offline (default when no token available)
      Don't hit the network. Parse ``latest-release`` and ``code-release``
      cells in landscape.json — they typically encode the most recent
      release / last-commit date already, written by the curator at row
      ingestion time. This is the mode ``make stale-check`` uses; it's
      reproducible and zero-cost.

  --online (requires GITHUB_TOKEN env var or --github-token)
      Hit the GitHub commits API once per row with a github.com URL to
      fetch the actual latest commit date. The CI workflow uses this mode
      so the freshness check is grounded in real-time GitHub state, not
      catalog drift.

Output
------

Stdout (and ``--output`` JSON file): a sorted JSON array of stale-row
records, most severe first:

  [
    {
      "id": "...",                 // record id
      "name": "...",
      "repo": "https://github.com/owner/repo",
      "last_commit": "2023-11-04", // ISO date or "unknown" if not parseable
      "days_since": 547,
      "severity": "abandoned",     // or "stale"
      "signal": "latest-release 2023-11"  // brief origin-of-date string
    }
  ]

Defaults
--------

  --threshold-days 365        — anything older than this is "stale".
  --threshold-abandoned 730   — anything older than this is "abandoned".

These match MAINTAINER.md §2's 12 / 24 month wall-clock thresholds. The
script uses today's UTC date as the reference.

Sanity cap
----------

``--max-emit N`` (default 20) trims the emitted list to at most N rows,
sorted by descending days_since. This is the soft fuse against opening
hundreds of issues on the first scheduled run. The CI workflow consumes
the output of this cap; the full summary still lands in the
``--reports-dir`` JSON if requested.

Exit codes
----------

  0 — script ran (may still emit stale rows, and partial fetches are
      reported via `partial: true` in the summary artifact; non-empty
      output ≠ failure).
  1 — usage / IO error (bad path, malformed JSON, unauthorised API).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


# --- Defaults -------------------------------------------------------------

DEFAULT_LANDSCAPE = Path(__file__).resolve().parent.parent / "data" / "landscape.json"

DEFAULT_THRESHOLD_STALE = 365
DEFAULT_THRESHOLD_ABANDONED = 730
DEFAULT_MAX_EMIT = 20

GITHUB_URL_RE = re.compile(
    r"https?://(?:www\.)?github\.com/([A-Za-z0-9._\-]+)/([A-Za-z0-9._\-]+?)(?:/|\.git|$|#|\?)",
    re.IGNORECASE,
)

# Common cell substrings indicating "no data" — see docs/SCHEMA.md §3.
SKIP_VALUES = {
    "",
    "no data",
    "no-data",
    "searched not found",
    "not applicable",
}


# --- Date parsing (mirror of web/src/lib/analyses/survivorship.ts) --------

DATE_RE = re.compile(r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?")
LAST_COMMIT_RE = re.compile(r"last[- ]commit\s+(\d{4})-(\d{1,2})", re.IGNORECASE)


def parse_date_latest(raw: str | None) -> dt.date | None:
    """Pull the LATEST YYYY-MM(-DD) date out of a free-text cell value.

    The catalog encodes dates as "v1.5.9 2026-05-05" or "Neo (consumer
    humanoid, 2025-2026 launch)" etc. We grab every match and return the
    chronologically latest one. Months without days are pinned to the
    15th, matching the TypeScript helper used by the survivorship view —
    this keeps offline mode aligned with what the UI shows.
    """
    if not raw:
        return None
    v = raw.strip()
    if not v:
        return None
    lower = v.lower()
    if any(
        lower == s or lower.startswith(s)
        for s in (
            "no-release no-release",
            "no-release",
            "no data",
            "no releases",
            "searched not found",
            "not applicable",
        )
    ):
        return None
    if "pre-existing" in lower:
        return None
    latest: dt.date | None = None
    for m in DATE_RE.finditer(v):
        try:
            year = int(m.group(1))
            month = int(m.group(2))
            day = int(m.group(3)) if m.group(3) else 15
            if year < 1900 or year > 2099 or month < 1 or month > 12 or day < 1 or day > 31:
                continue
            d = dt.date(year, month, day)
        except ValueError:
            continue
        if latest is None or d > latest:
            latest = d
    return latest


def parse_last_commit(raw: str | None) -> dt.date | None:
    """Pull "last commit YYYY-MM" from a code-release cell."""
    if not raw:
        return None
    m = LAST_COMMIT_RE.search(raw)
    if not m:
        return None
    try:
        year = int(m.group(1))
        month = int(m.group(2))
        if year < 1900 or year > 2099 or month < 1 or month > 12:
            return None
        return dt.date(year, month, 15)
    except ValueError:
        return None


def extract_repo(record: dict[str, Any]) -> tuple[str, str, str] | None:
    """Return (owner, repo, full_url) for the record's primary GitHub repo, or None.

    Priority: ``cells.gh.citation`` (the explicit GitHub-summary cell),
    then ``url`` (the row's primary link). Both are documented in
    docs/SCHEMA.md §2.5 / §2 respectively.
    """
    gh = (record.get("cells") or {}).get("gh") or {}
    candidates = [gh.get("citation"), record.get("url"), gh.get("value")]
    for cand in candidates:
        if not cand:
            continue
        m = GITHUB_URL_RE.search(cand)
        if not m:
            continue
        owner = m.group(1)
        repo = m.group(2).rstrip(".").removesuffix(".git")
        # github.com/owner/repo/blob/... — strip anything after the second segment.
        return owner, repo, f"https://github.com/{owner}/{repo}"
    return None


# --- Offline classification ----------------------------------------------


def offline_signal(record: dict[str, Any]) -> tuple[dt.date, str] | None:
    """Best-effort latest date for this record from the catalog cells.

    Mirrors the JS survivorship classifier's priority order:
      1. cells['latest-release'].value
      2. cells['code-release'] "last commit YYYY-MM" parse
    """
    cells = record.get("cells") or {}
    lr = cells.get("latest-release") or {}
    if lr.get("status") == "real-data":
        d = parse_date_latest(lr.get("value"))
        if d:
            return d, f"latest-release {d.strftime('%Y-%m')}"
    cr = cells.get("code-release") or {}
    val = cr.get("value")
    if val:
        d = parse_last_commit(val)
        if d:
            return d, f"code-release last commit {d.strftime('%Y-%m')}"
    return None


# --- Online classification (GitHub API) ----------------------------------


class GitHubAPIError(Exception):
    pass


def fetch_latest_commit(
    owner: str,
    repo: str,
    token: str | None,
    timeout: float = 15.0,
) -> dt.date:
    """GET /repos/{owner}/{repo}/commits?per_page=1 → ISO date.

    Raises GitHubAPIError on 4xx/5xx other than 404. 404 raises with a
    distinct message so the caller can decide whether to treat the row as
    "repo deleted" (a strong abandonment signal in itself).
    """
    url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/commits?per_page=1"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "agent-infrastructure-landscape-staleness-check")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise GitHubAPIError(f"repo-not-found: {owner}/{repo}") from e
        # Rate limit: GitHub returns 403 with X-RateLimit-Remaining: 0.
        remaining = e.headers.get("X-RateLimit-Remaining") if e.headers else None
        if e.code == 403 and remaining == "0":
            raise GitHubAPIError(f"rate-limited (reset epoch={e.headers.get('X-RateLimit-Reset', '?')})") from e
        raise GitHubAPIError(f"http-{e.code}: {owner}/{repo}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise GitHubAPIError(f"network-error: {owner}/{repo}: {e.reason}") from e
    if not data:
        raise GitHubAPIError(f"empty-repo: {owner}/{repo}")
    commit = data[0].get("commit") or {}
    committer = commit.get("committer") or commit.get("author") or {}
    iso = committer.get("date")
    if not iso:
        raise GitHubAPIError(f"no-date: {owner}/{repo}")
    # ISO 8601: 2026-05-01T12:34:56Z
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).date()


# --- Driver ---------------------------------------------------------------


def classify(
    last_commit: dt.date,
    today: dt.date,
    thr_stale: int,
    thr_abandoned: int,
) -> tuple[str | None, int]:
    """Return (severity, days_since) — severity None means "active"."""
    days = (today - last_commit).days
    if days >= thr_abandoned:
        return "abandoned", days
    if days >= thr_stale:
        return "stale", days
    return None, days


def run(args: argparse.Namespace) -> int:
    landscape_path: Path = args.landscape
    if not landscape_path.exists():
        print(f"error: landscape file not found: {landscape_path}", file=sys.stderr)
        return 1
    try:
        with landscape_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        print(f"error: landscape file is not valid JSON: {e}", file=sys.stderr)
        return 1
    records = data.get("records") or []

    today = dt.date.today()
    token = args.github_token or os.environ.get("GITHUB_TOKEN")
    offline = args.offline or args.dry_run or not token

    # Round-friendly mode banner to stderr (so --output stays clean).
    print(
        f"check_staleness: mode={'offline' if offline else 'online'} "
        f"records={len(records)} threshold-stale={args.threshold_days}d "
        f"threshold-abandoned={args.threshold_abandoned}d today={today.isoformat()}",
        file=sys.stderr,
    )

    flagged: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen_repo_count = 0
    partial = False

    for rec in records:
        repo_info = extract_repo(rec)
        if not repo_info:
            continue
        if rec.get("decay_cause"):
            # Row's lifecycle is already classified (SCHEMA.md §3c). The
            # catalog is a museum, not an active-only registry — once a
            # decay_cause is recorded the staleness signal is no longer a
            # question that needs an issue, just a fact in the schema.
            continue
        seen_repo_count += 1
        owner, repo, repo_url = repo_info

        last_commit: dt.date | None = None
        signal = ""

        if offline:
            sig = offline_signal(rec)
            if not sig:
                continue
            last_commit, signal = sig
        else:
            try:
                last_commit = fetch_latest_commit(owner, repo, token)
                signal = f"github-api {last_commit.isoformat()}"
            except GitHubAPIError as e:
                msg = str(e)
                errors.append({"id": rec.get("id"), "repo": repo_url, "error": msg})
                partial = True
                # "repo-not-found" is itself a strong abandonment signal —
                # treat as max-severity so it surfaces.
                if msg.startswith("repo-not-found"):
                    flagged.append(
                        {
                            "id": rec.get("id"),
                            "name": rec.get("name"),
                            "repo": repo_url,
                            "last_commit": "unknown",
                            "days_since": args.threshold_abandoned * 2,
                            "severity": "abandoned",
                            "signal": "repo-not-found (404 from GitHub API)",
                        }
                    )
                continue

        if last_commit is None:
            continue

        severity, days = classify(
            last_commit, today, args.threshold_days, args.threshold_abandoned
        )
        if severity is None:
            continue
        flagged.append(
            {
                "id": rec.get("id"),
                "name": rec.get("name"),
                "repo": repo_url,
                "last_commit": last_commit.isoformat(),
                "days_since": days,
                "severity": severity,
                "signal": signal,
            }
        )

        if not offline and args.sleep > 0:
            # Politeness pacing — even at 5000/hr authenticated we sleep
            # a tick between calls to be a good neighbour.
            time.sleep(args.sleep)

    # Sort: most-stale-first, with abandoned bubbling above stale.
    severity_rank = {"abandoned": 0, "stale": 1}
    flagged.sort(
        key=lambda r: (severity_rank.get(r["severity"], 9), -r["days_since"])
    )

    capped = flagged[: args.max_emit] if args.max_emit and args.max_emit > 0 else flagged

    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "offline" if offline else "online",
        "threshold_stale_days": args.threshold_days,
        "threshold_abandoned_days": args.threshold_abandoned,
        "records_total": len(records),
        "records_with_github_repo": seen_repo_count,
        "flagged_total": len(flagged),
        "flagged_stale": sum(1 for r in flagged if r["severity"] == "stale"),
        "flagged_abandoned": sum(1 for r in flagged if r["severity"] == "abandoned"),
        "emitted_count": len(capped),
        "max_emit": args.max_emit,
        "errors": errors,
        "partial": partial,
        "flagged": capped,
    }

    # The primary contract — caller (CI) consumes this:
    payload = json.dumps(capped, indent=2, sort_keys=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
        print(f"check_staleness: wrote {len(capped)} entries to {args.output}", file=sys.stderr)
    else:
        print(payload)

    if args.reports_dir:
        args.reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = args.reports_dir / "staleness-summary.json"
        report_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"check_staleness: wrote full summary to {report_path}", file=sys.stderr)

    # Human-readable counts to stderr so `make stale-check` is informative.
    print(
        f"check_staleness: {len(flagged)} flagged "
        f"(stale={summary['flagged_stale']} abandoned={summary['flagged_abandoned']}) "
        f"out of {seen_repo_count} github-bearing rows; emitting {len(capped)}.",
        file=sys.stderr,
    )

    if partial:
        # Surface partiality without failing CI — the dedupe + issue-opening
        # step depends on this exit code being 0 to run at all. Consumers
        # that care can read `partial: true` from the summary artifact.
        print(
            f"check_staleness: partial run — {len(errors)} row(s) errored "
            "(see summary.errors); continuing.",
            file=sys.stderr,
        )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--landscape",
        type=Path,
        default=DEFAULT_LANDSCAPE,
        help="Path to landscape.json (default: data/landscape.json).",
    )
    p.add_argument(
        "--threshold-days",
        type=int,
        default=DEFAULT_THRESHOLD_STALE,
        help=f"Stale threshold in days (default: {DEFAULT_THRESHOLD_STALE} = 12 months).",
    )
    p.add_argument(
        "--threshold-abandoned",
        type=int,
        default=DEFAULT_THRESHOLD_ABANDONED,
        help=f"Abandoned threshold in days (default: {DEFAULT_THRESHOLD_ABANDONED} = 24 months).",
    )
    p.add_argument(
        "--github-token",
        default=None,
        help="GitHub API token; if absent, falls back to env GITHUB_TOKEN.",
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help="Don't hit the GitHub API; parse dates from catalog cells.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Alias for --offline; emphasises 'no side effects'.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write JSON list of flagged rows to PATH (default: stdout).",
    )
    p.add_argument(
        "--reports-dir",
        type=Path,
        default=None,
        help="Write a fuller summary (counts, errors, flagged) under this dir.",
    )
    p.add_argument(
        "--max-emit",
        type=int,
        default=DEFAULT_MAX_EMIT,
        help=f"Hard cap on emitted-list size (default: {DEFAULT_MAX_EMIT}). "
        "Sorted by severity then days-since-commit, so the most urgent rows survive. "
        "Set to 0 to disable.",
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0.1,
        help="Seconds to sleep between GitHub API calls (default: 0.1).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except KeyboardInterrupt:
        print("check_staleness: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
