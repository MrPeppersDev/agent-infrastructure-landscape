#!/usr/bin/env python3
"""
fetch_commit_trajectories.py — pull monthly cumulative commit counts for
every row with a parseable GitHub repo URL.

Issue #50 (T3-prep-1). Feeds the S-curve maturity fit (T2-4 / issue #47)
real per-row temporal data so the fitter can move beyond the 15.7% of
rows that previously had enough signal for a 3-parameter logistic.

Outputs:
- Writes the `commit-trajectory` cell into landscape.html for each
  GitHub-bearing row.
- Caches every raw GitHub commits-page response under
  ``extraction/commit-cache/<owner>__<repo>.json`` so subsequent
  ``make build`` runs are deterministic (and offline-safe).
- Persists in-progress state to
  ``extraction/commit-trajectory-progress.json`` so a SIGINT or rate-limit
  abort resumes cleanly on the next run.

Cell shape on write (real-data):

    <td class="commit-trajectory" data-status="real-data"
        data-citation="https://github.com/owner/repo"
        data-tier="T1">[{"ym":"2023-01","cum":4},...]</td>

The cell value is the JSON-stringified compact array (no spaces). For
status=depth-floor-reached / not-applicable the cell uses the canonical
``<span class="no-data">`` patterns documented in SCHEMA.md §3 so the
existing parser in extract.py picks them up unchanged.

Auth:
  GITHUB_TOKEN env var (or --github-token) is strongly recommended.
  Without auth the API is 60 req/hr which will exhaust within ~10 rows.
  With auth it's 5000 req/hr.

Usage:
  python3 scripts/fetch_commit_trajectories.py
  python3 scripts/fetch_commit_trajectories.py --offline       # cache-only
  python3 scripts/fetch_commit_trajectories.py --limit 50      # cap rows attempted
  python3 scripts/fetch_commit_trajectories.py --force         # ignore progress file
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

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LANDSCAPE = ROOT / "data" / "landscape.json"
DEFAULT_HTML = ROOT / "landscape.html"
CACHE_DIR = ROOT / "extraction" / "commit-cache"
PROGRESS_FILE = ROOT / "extraction" / "commit-trajectory-progress.json"

# Shared with check_staleness.py — keep the regex in sync if either drifts.
GITHUB_URL_RE = re.compile(
    r"https?://(?:www\.)?github\.com/([A-Za-z0-9._\-]+)/([A-Za-z0-9._\-]+?)(?:/|\.git|$|#|\?)",
    re.IGNORECASE,
)

PER_PAGE = 100
USER_AGENT = "agent-infrastructure-landscape-commit-trajectories"
RATE_LIMIT_SLEEP_MARGIN = 5  # seconds of slack to add after a rate-limit reset
RATE_LIMIT_FLOOR = 10        # if remaining drops at-or-below this, sleep until reset
# Hard cap on pages per repo. At 100 commits/page that's 1000 commits which
# is well past the granularity the S-curve fitter cares about (it just
# needs ~5-100 distinct month-anchors to fit a 3-parameter logistic). The
# alternative would be walking 100+ pages for monorepos like
# huggingface/transformers, which is wasteful both in API budget and
# wall-clock time (each page is a separate HTTPS round-trip).
# When truncated we anchor the cumulative count to (total - observed)
# from the probe — see fetch_full_history.
MAX_PAGES_PER_REPO = 10


# ---------------------------------------------------------------------------
# GitHub API client
# ---------------------------------------------------------------------------


class GitHubAPIError(Exception):
    """Per-repo failure. Caller marks the row as depth-floor."""


class RateLimited(Exception):
    """The API's hard rate-limit fired. Caller should sleep until reset."""

    def __init__(self, reset_epoch: int):
        super().__init__(f"rate-limited until {reset_epoch}")
        self.reset_epoch = reset_epoch


def _request(url: str, token: str | None, timeout: float = 30.0):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", USER_AGENT)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(req, timeout=timeout)


def _maybe_sleep_for_rate_limit(remaining: int | None, reset_epoch: int | None) -> None:
    """Politely sleep if we're nearing the 5000/hr ceiling."""
    if remaining is None or reset_epoch is None:
        return
    if remaining > RATE_LIMIT_FLOOR:
        return
    now = int(time.time())
    sleep_secs = max(0, reset_epoch - now) + RATE_LIMIT_SLEEP_MARGIN
    print(
        f"  rate-limit nearing exhaustion (remaining={remaining}); "
        f"sleeping {sleep_secs}s until reset",
        file=sys.stderr,
    )
    time.sleep(sleep_secs)


def probe_total_pages(
    owner: str,
    repo: str,
    token: str | None,
) -> tuple[int, int | None, int | None]:
    """Probe the repo with per_page=1 to read the Link rel=\"last\" page count.

    Returns (total_commits, remaining, reset). For a healthy repo this is
    a fast single-request way to discover the project-wide commit count
    without walking the whole history. Used as the cumulative-baseline
    when MAX_PAGES_PER_REPO truncates the live pagination.

    On 404 raises GitHubAPIError; on 409 (empty repo) returns 0.
    """
    url = (
        f"https://api.github.com/repos/{urllib.parse.quote(owner)}/"
        f"{urllib.parse.quote(repo)}/commits?per_page=1"
    )
    try:
        resp = _request(url, token)
    except urllib.error.HTTPError as e:
        remaining = e.headers.get("X-RateLimit-Remaining") if e.headers else None
        reset = e.headers.get("X-RateLimit-Reset") if e.headers else None
        if e.code == 403 and remaining == "0":
            raise RateLimited(int(reset) if reset else int(time.time()) + 60) from e
        if e.code == 404:
            raise GitHubAPIError(f"repo-not-found: {owner}/{repo}") from e
        if e.code == 409:
            # Empty repo
            return 0, None, None
        raise GitHubAPIError(f"http-{e.code}: {owner}/{repo}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise GitHubAPIError(f"network-error: {owner}/{repo}: {e.reason}") from e

    with resp:
        body = resp.read().decode("utf-8", errors="replace")
        link = resp.headers.get("Link", "") or ""
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = []
    if not data:
        return 0, None, None

    # The Link header on a per_page=1 query contains rel="last" whose URL
    # has the total page count as its `page=N` parameter.
    total = len(data) if data else 0
    for piece in link.split(","):
        piece = piece.strip()
        m = re.match(r'<([^>]+)>\s*;\s*rel="last"', piece)
        if m:
            last_url = m.group(1)
            mp = re.search(r"[?&]page=(\d+)", last_url)
            if mp:
                total = int(mp.group(1))
            break

    remaining_int = int(remaining) if remaining and remaining.isdigit() else None
    reset_int = int(reset) if reset and reset.isdigit() else None
    return total, remaining_int, reset_int


def fetch_commits_page(
    owner: str,
    repo: str,
    page_url: str | None,
    token: str | None,
) -> tuple[list[dict[str, Any]], str | None, int | None, int | None]:
    """Fetch one commits page. Returns (commits, next_url, remaining, reset).

    The first call uses owner/repo. Subsequent calls pass the URL from
    the Link header's rel="next". The GitHub Commits API paginates in
    REVERSE chronological order, but we don't care about order here —
    we collect every commit's date then bucket.

    Raises:
      - GitHubAPIError(404) on repo-not-found / private repo.
      - RateLimited on 403 with X-RateLimit-Remaining=0.
      - GitHubAPIError on any other 4xx/5xx.
    """
    url = page_url or (
        f"https://api.github.com/repos/{urllib.parse.quote(owner)}/"
        f"{urllib.parse.quote(repo)}/commits?per_page={PER_PAGE}"
    )
    try:
        resp = _request(url, token)
    except urllib.error.HTTPError as e:
        remaining = e.headers.get("X-RateLimit-Remaining") if e.headers else None
        reset = e.headers.get("X-RateLimit-Reset") if e.headers else None
        if e.code == 403 and remaining == "0":
            raise RateLimited(int(reset) if reset else int(time.time()) + 60) from e
        if e.code == 404:
            raise GitHubAPIError(f"repo-not-found: {owner}/{repo}") from e
        if e.code == 409:
            # 409 = empty repo
            raise GitHubAPIError(f"empty-repo: {owner}/{repo}") from e
        raise GitHubAPIError(f"http-{e.code}: {owner}/{repo}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise GitHubAPIError(f"network-error: {owner}/{repo}: {e.reason}") from e

    with resp:
        body = resp.read().decode("utf-8", errors="replace")
        link = resp.headers.get("Link", "") or ""
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise GitHubAPIError(f"bad-json: {owner}/{repo}: {e}") from e

    if not isinstance(data, list):
        # GitHub returned an error object even though status was 200 (rare).
        msg = data.get("message") if isinstance(data, dict) else "non-array"
        raise GitHubAPIError(f"bad-shape: {owner}/{repo}: {msg}")

    # Parse rel="next" out of the Link header.
    next_url: str | None = None
    for piece in link.split(","):
        piece = piece.strip()
        if not piece:
            continue
        m = re.match(r"<([^>]+)>\s*;\s*rel=\"next\"", piece)
        if m:
            next_url = m.group(1)
            break

    remaining_int = int(remaining) if remaining is not None and remaining.isdigit() else None
    reset_int = int(reset) if reset is not None and reset.isdigit() else None
    return data, next_url, remaining_int, reset_int


# ---------------------------------------------------------------------------
# Cache + trajectory construction
# ---------------------------------------------------------------------------


def cache_path(owner: str, repo: str) -> Path:
    """Cache filename — collapse owner/repo to a single safe string."""
    safe_owner = re.sub(r"[^A-Za-z0-9_.-]+", "-", owner)
    safe_repo = re.sub(r"[^A-Za-z0-9_.-]+", "-", repo)
    return CACHE_DIR / f"{safe_owner}__{safe_repo}.json"


def load_cache(owner: str, repo: str) -> dict[str, Any] | None:
    p = cache_path(owner, repo)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_cache(owner: str, repo: str, payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = cache_path(owner, repo)
    # Stable JSON formatting for diff-friendliness.
    p.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def build_trajectory(
    commit_dates: list[str],
    *,
    baseline: int = 0,
) -> list[dict[str, Any]]:
    """Reduce a list of ISO commit dates into [{ym, cum}, ...] ascending.

    Months without any commits are omitted; consumers should treat the
    series as a sparse cumulative growth curve.

    `baseline` is the project-wide commit count that PRECEDES the first
    observed commit in `commit_dates`. For a non-truncated walk this is
    0; for a truncated walk it's (project_total - len(commit_dates)) so
    the cumulative count at the first observed month already reflects
    all the pre-window history.
    """
    if not commit_dates:
        return []
    months: dict[str, int] = {}
    for iso in commit_dates:
        # Take YYYY-MM only.
        if not iso or len(iso) < 7:
            continue
        ym = iso[:7]
        # Validate roughly.
        if not re.match(r"^\d{4}-\d{2}$", ym):
            continue
        months[ym] = months.get(ym, 0) + 1
    if not months:
        return []
    cum = baseline
    out: list[dict[str, Any]] = []
    for ym in sorted(months):
        cum += months[ym]
        out.append({"ym": ym, "cum": cum})
    return out


def fetch_full_history(
    owner: str,
    repo: str,
    token: str | None,
    sleep_between: float = 0.3,
) -> dict[str, Any]:
    """Pull the repo's commit trajectory.

    Strategy:
      1. Probe the total commit count via /commits?per_page=1 (1 request,
         reads Link rel="last" → total pages = total commits).
      2. Walk /commits?per_page=100, capped at MAX_PAGES_PER_REPO pages.
         For repos with ≤ MAX_PAGES_PER_REPO*100 commits this gives full
         history. For larger repos we truncate to the most-recent
         MAX_PAGES_PER_REPO*100 commits.
      3. When truncated, anchor the cumulative count to (total_commits -
         observed) so the trajectory shape stays honest (the cumulative
         count at the oldest observed month is the project's pre-window
         commit count, not 0).

    The GitHub Commits API returns commits in REVERSE chronological order,
    so a truncated walk gives us the most-recent slice, which is the
    half of the curve the S-curve fitter cares about most for current-phase
    classification.

    Returns a dict with:
      - trajectory: [{ym, cum}, ...] cumulative monthly counts (ascending)
      - total_commits: int (project-wide, from probe)
      - fetched_at: ISO timestamp
      - pages_fetched: int
      - truncated: bool
      - observed_commits: int (count in the trajectory; may be < total)
    """
    # Probe project-wide commit count.
    try:
        total_commits, remaining, reset = probe_total_pages(owner, repo, token)
        _maybe_sleep_for_rate_limit(remaining, reset)
    except GitHubAPIError:
        total_commits = 0

    commit_dates: list[str] = []
    page_url: str | None = None
    pages = 0
    truncated = False
    while True:
        commits, next_url, remaining, reset = fetch_commits_page(
            owner, repo, page_url, token
        )
        pages += 1
        if not commits and pages == 1:
            break
        for c in commits:
            commit = c.get("commit") or {}
            committer = commit.get("committer") or commit.get("author") or {}
            iso = committer.get("date")
            if iso:
                commit_dates.append(iso[:10])
        _maybe_sleep_for_rate_limit(remaining, reset)
        if not next_url:
            break
        if pages >= MAX_PAGES_PER_REPO:
            truncated = True
            break
        page_url = next_url
        if sleep_between > 0:
            time.sleep(sleep_between)

    observed = len(commit_dates)
    commit_dates.sort()

    # Build trajectory with anchored cumulative count when truncated.
    baseline = 0
    if truncated and total_commits > observed:
        baseline = total_commits - observed
    trajectory = build_trajectory(commit_dates, baseline=baseline)

    return {
        "trajectory": trajectory,
        "total_commits": total_commits if total_commits > 0 else observed,
        "observed_commits": observed,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pages_fetched": pages,
        "truncated": truncated,
    }


# ---------------------------------------------------------------------------
# Repo extraction (mirrors check_staleness.py)
# ---------------------------------------------------------------------------


def extract_repo(record: dict[str, Any]) -> tuple[str, str, str] | None:
    """Return (owner, repo, full_url) for the row's primary GitHub repo, or None."""
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
        return owner, repo, f"https://github.com/{owner}/{repo}"
    return None


# ---------------------------------------------------------------------------
# HTML rewrite — replace each row's commit-trajectory <td>
# ---------------------------------------------------------------------------


# We match by the row's <a href="...">NAME</a> in the name cell. To survive
# the HTML structure exactly, we replace the empty placeholder `<td
# class="commit-trajectory"><span class="no-data"></span></td>` with the
# real cell, scoped to a window that ends at the next `</tr>`. The pipeline
# guarantees one such placeholder per row.

CELL_RE = re.compile(
    r'<td class="commit-trajectory">[^<]*(?:<[^>]+>[^<]*</[^>]+>)?[^<]*</td>',
    re.DOTALL,
)


def render_real_cell(trajectory: list[dict[str, Any]], repo_url: str) -> str:
    """Real-data cell — JSON value + GitHub citation."""
    val = json.dumps(trajectory, separators=(",", ":"))
    return (
        f'<td class="commit-trajectory">'
        f'<span class="trajectory-data">{val}</span> '
        f'<a class="cite" href="{repo_url}" title="source">↗</a>'
        f'</td>'
    )


def render_depth_floor_cell(repo_url: str) -> str:
    """Depth-floor cell — preserves the attempted URL in the citation."""
    return (
        f'<td class="commit-trajectory">'
        f'<span class="no-data">searched not found</span> '
        f'<a class="cite" href="{repo_url}" title="searched">↗</a>'
        f'</td>'
    )


def render_not_applicable_cell() -> str:
    """No GitHub repo → not-applicable, no citation needed."""
    return (
        '<td class="commit-trajectory">'
        '<span class="no-data" style="font-style:italic;color:#555;">'
        'not applicable — no GitHub repo</span>'
        '</td>'
    )


def patch_html_for_row(
    html: str,
    row_name: str,
    row_url: str | None,
    new_cell_html: str,
    occurrence: int = 0,
) -> tuple[str, bool]:
    """Patch the commit-trajectory cell for the row whose name+url match.

    Returns (new_html, did_replace). did_replace=False means we couldn't
    locate the row (caller should log a warning but keep going).

    `occurrence` is the 0-indexed match to take when (name, url) is not
    unique across the catalog. The caller tracks per-key counters to make
    sure repeated keys hit distinct rows in document order.

    Match strategy: requires the FULL name cell to match — both the href
    AND the link text, since some rows share a URL but differ by name
    suffix (e.g. "Generative Agents" and "Generative Agents (Park et al.)"
    both link to arxiv.org/abs/2304.03442). For url-null rows the name
    cell has no anchor, so we match the bare "<td class="name">NAME</td>"
    form.
    """
    from html import escape

    name_escaped = escape(row_name)

    if row_url:
        url_escaped = escape(row_url, quote=True)
        # Exact full <td class="name"> match — href AND text must align.
        anchor_pat = re.compile(
            re.escape(f'<td class="name"><a href="{url_escaped}">')
            + re.escape(name_escaped)
            + re.escape('</a></td>')
        )
    else:
        # No-URL row: name cell is "<td class="name">NAME</td>".
        anchor_pat = re.compile(
            re.escape(f'<td class="name">{name_escaped}</td>')
        )

    matches = list(anchor_pat.finditer(html))
    if not matches or occurrence >= len(matches):
        return html, False
    m = matches[occurrence]

    end_tr = html.find('</tr>', m.end())
    if end_tr < 0:
        return html, False
    row_chunk = html[m.start():end_tr]
    cell_m = CELL_RE.search(row_chunk)
    if cell_m is None:
        return html, False
    abs_start = m.start() + cell_m.start()
    abs_end = m.start() + cell_m.end()
    new_html = html[:abs_start] + new_cell_html + html[abs_end:]
    return new_html, True


# ---------------------------------------------------------------------------
# Progress file
# ---------------------------------------------------------------------------


def load_progress() -> dict[str, Any]:
    if not PROGRESS_FILE.exists():
        return {"done": {}}
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"done": {}}


def save_progress(progress: dict[str, Any]) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(
        json.dumps(progress, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    landscape_path: Path = args.landscape
    html_path: Path = args.html
    token = args.github_token or os.environ.get("GITHUB_TOKEN")

    if not landscape_path.exists():
        print(f"error: landscape not found: {landscape_path}", file=sys.stderr)
        return 1
    if not html_path.exists():
        print(f"error: landscape.html not found: {html_path}", file=sys.stderr)
        return 1

    data = json.loads(landscape_path.read_text(encoding="utf-8"))
    records = data.get("records") or []

    progress = {"done": {}} if args.force else load_progress()
    done: dict[str, Any] = progress.setdefault("done", {})

    print(
        f"fetch_commit_trajectories: records={len(records)} "
        f"offline={args.offline} have-token={bool(token)} "
        f"resume-from-progress={'no' if args.force else 'yes'} "
        f"already-done={len(done)}",
        file=sys.stderr,
    )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    html = html_path.read_text(encoding="utf-8")

    counts = {
        "real-data": 0,
        "depth-floor": 0,
        "not-applicable": 0,
        "skipped-row-not-found": 0,
        "cache-hit": 0,
        "live-fetch": 0,
        "errors": 0,
    }
    failed: list[dict[str, Any]] = []

    # Per-(name, url) occurrence counters so duplicate (name, url) rows
    # map onto the correct HTML row in document order.
    occurrence_counter: dict[tuple[str, str | None], int] = {}

    attempted = 0
    for rec in records:
        rec_id = rec.get("id") or "?"
        rec_name = rec.get("name") or ""
        rec_url = rec.get("url")
        key = (rec_name, rec_url)
        occ = occurrence_counter.get(key, 0)
        occurrence_counter[key] = occ + 1

        if args.limit and attempted >= args.limit:
            break

        repo_info = extract_repo(rec)
        if repo_info is None:
            # No GitHub repo for this row.
            new_cell = render_not_applicable_cell()
            html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
            if ok:
                counts["not-applicable"] += 1
                done[rec_id] = {"status": "not-applicable"}
            else:
                counts["skipped-row-not-found"] += 1
            continue

        owner, repo, repo_url = repo_info
        existing = done.get(rec_id)
        if existing and existing.get("status") in {"real-data", "depth-floor"}:
            # Re-render from cache (HTML may be regenerated). Don't recount.
            cached = load_cache(owner, repo)
            if existing["status"] == "real-data" and cached is not None:
                new_cell = render_real_cell(cached.get("trajectory") or [], repo_url)
                html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
                if ok:
                    counts["real-data"] += 1
                    counts["cache-hit"] += 1
                else:
                    counts["skipped-row-not-found"] += 1
            elif existing["status"] == "depth-floor":
                new_cell = render_depth_floor_cell(repo_url)
                html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
                if ok:
                    counts["depth-floor"] += 1
                    counts["cache-hit"] += 1
                else:
                    counts["skipped-row-not-found"] += 1
            continue

        # New row: cache → network → cache miss.
        cached = load_cache(owner, repo)
        trajectory: list[dict[str, Any]] | None = None
        fetched: bool = False

        if cached is not None and cached.get("trajectory") is not None:
            trajectory = cached["trajectory"]
            counts["cache-hit"] += 1
        elif args.offline:
            # Offline mode + cache-miss → depth-floor.
            pass
        else:
            attempted += 1
            try:
                payload = fetch_full_history(
                    owner, repo, token, sleep_between=args.sleep
                )
                save_cache(owner, repo, payload)
                trajectory = payload["trajectory"]
                counts["live-fetch"] += 1
                fetched = True
            except RateLimited as rl:
                # Sleep until reset and retry once.
                now = int(time.time())
                sleep_secs = max(0, rl.reset_epoch - now) + RATE_LIMIT_SLEEP_MARGIN
                print(
                    f"  hit hard rate limit fetching {owner}/{repo}; "
                    f"sleeping {sleep_secs}s",
                    file=sys.stderr,
                )
                time.sleep(sleep_secs)
                try:
                    payload = fetch_full_history(
                        owner, repo, token, sleep_between=args.sleep
                    )
                    save_cache(owner, repo, payload)
                    trajectory = payload["trajectory"]
                    counts["live-fetch"] += 1
                    fetched = True
                except (RateLimited, GitHubAPIError) as e:
                    failed.append({"id": rec_id, "repo": repo_url, "error": str(e)})
                    counts["errors"] += 1
            except GitHubAPIError as e:
                failed.append({"id": rec_id, "repo": repo_url, "error": str(e)})
                counts["errors"] += 1

        if trajectory:
            new_cell = render_real_cell(trajectory, repo_url)
            html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
            if ok:
                counts["real-data"] += 1
                done[rec_id] = {"status": "real-data", "repo": repo_url}
            else:
                counts["skipped-row-not-found"] += 1
        else:
            # No trajectory available — depth-floor.
            new_cell = render_depth_floor_cell(repo_url)
            html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
            if ok:
                counts["depth-floor"] += 1
                done[rec_id] = {"status": "depth-floor", "repo": repo_url}
            else:
                counts["skipped-row-not-found"] += 1

        # Periodically flush progress + html (every 25 fetched).
        if fetched and counts["live-fetch"] % 25 == 0:
            save_progress(progress)
            html_path.write_text(html, encoding="utf-8")
            print(
                f"  checkpoint: real-data={counts['real-data']} "
                f"depth-floor={counts['depth-floor']} "
                f"not-applicable={counts['not-applicable']} "
                f"live-fetch={counts['live-fetch']} "
                f"cache-hit={counts['cache-hit']}",
                file=sys.stderr,
            )

    # Final write.
    save_progress(progress)
    html_path.write_text(html, encoding="utf-8")

    print(
        "\nfetch_commit_trajectories: summary\n"
        f"  real-data:        {counts['real-data']}\n"
        f"  depth-floor:      {counts['depth-floor']}\n"
        f"  not-applicable:   {counts['not-applicable']}\n"
        f"  cache-hits:       {counts['cache-hit']}\n"
        f"  live-fetches:     {counts['live-fetch']}\n"
        f"  errors:           {counts['errors']}\n"
        f"  rows-not-found:   {counts['skipped-row-not-found']}",
        file=sys.stderr,
    )
    if failed:
        print(f"  sample errors (up to 10):", file=sys.stderr)
        for e in failed[:10]:
            print(f"    - {e['id']}  {e['repo']}  {e['error']}", file=sys.stderr)

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
        help="Path to landscape.json (default: data/landscape.json)",
    )
    p.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML,
        help="Path to landscape.html (default: landscape.html)",
    )
    p.add_argument(
        "--github-token",
        default=None,
        help="GitHub API token; falls back to env GITHUB_TOKEN.",
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help="Don't hit the network. Cache-only fills, otherwise depth-floor.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Cap the number of NEW live fetches (0 = unlimited).",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Ignore progress file; re-fetch / re-write every row.",
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Pause (s) between successive API calls (default 0.2).",
    )
    return p.parse_args(argv)


def main() -> int:
    args = parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
