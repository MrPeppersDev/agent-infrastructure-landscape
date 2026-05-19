#!/usr/bin/env python3
"""
research_decay_causes.py — backfill decay-cause forensics (SCHEMA.md §3c).

Issue #56. Three phases (this script currently implements Phase C only;
Phases A and B follow in #56b / #56c):

  Phase C — archive-flag sweep (this run; cheapest, most mechanical):
    For every record with a github.com URL, GET /repos/{owner}/{repo}
    and inspect `archived`. If true: write
      decay_cause = "archived"
      decay_date  = updated_at as YYYY-MM-DD
      decay_evidence = <github URL>
    onto the row's <tr> in landscape.html as data-decay-* attributes.

  Phase A — commercial products (research-heavy, separate run):
    Stale / abandoned commercial rows → TechCrunch / VBeat / HN Algolia
    / Wayback Machine in priority order. Hard 2-minute budget per row.

  Phase B — academic papers (separate run):
    Stale / abandoned research-tier rows → S2 cache for follow-up
    papers by overlapping authors → typically `superseded`.

Cache
-----
Per-repo responses cached under extraction/decay-cause-cache/<owner>__<repo>.json
so reruns are deterministic and skip already-resolved rows. The cache
shape mirrors the existing extraction/gh-cache/ shape (full_name,
pushed_at, updated_at, stargazers_count, archived, ...).

Usage
-----
  python3 scripts/research_decay_causes.py archive-sweep
      Phase C run; writes decay_cause / decay_date / decay_evidence /
      last_verified_at onto each archived record in data/landscape.json
      (Path A, default since #68 Stream C). The legacy landscape.html
      writer is still available via --target landscape.html.

  python3 scripts/research_decay_causes.py archive-sweep --dry-run
      Phase C; reports what WOULD be written without modifying anything.

  python3 scripts/research_decay_causes.py archive-sweep --rate-limit 30
      Limit to 30 API calls (testing).

  python3 scripts/research_decay_causes.py archive-sweep --target landscape.html
      Legacy Path B: patch landscape.html instead of data/landscape.json
      (emits a deprecation warning).

Environment
-----------
  GITHUB_TOKEN  Optional. Lifts unauthenticated 60/hr rate limit to
                5000/hr — needed to cover ~230 repos cleanly.
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

# Path A helper for landscape.json writes (issue #68 Stream C).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cell_writer import load_landscape, save_landscape  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_LANDSCAPE = ROOT / "data" / "landscape.json"
HTML_LANDSCAPE = ROOT / "landscape.html"
CACHE_DIR = ROOT / "extraction" / "decay-cause-cache"

# Today's date used for last_verified_at refresh on touched rows.
TODAY = dt.date(2026, 5, 15)

# GitHub URL pattern (mirrors check_staleness.py).
GITHUB_URL_RE = re.compile(
    r"https?://(?:www\.)?github\.com/([A-Za-z0-9._\-]+)/([A-Za-z0-9._\-]+?)(?:/|\.git|$|#|\?)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Repo extraction (mirrors check_staleness.py).
# ---------------------------------------------------------------------------


def extract_repo(record: dict[str, Any]) -> tuple[str, str, str] | None:
    """Return (owner, repo, full_url) for the record's primary GitHub
    repo, or None. Priority: cells.gh.citation → record.url → cells.gh.value.
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
        return owner, repo, f"https://github.com/{owner}/{repo}"
    return None


# ---------------------------------------------------------------------------
# GitHub API.
# ---------------------------------------------------------------------------


class GitHubError(Exception):
    pass


def fetch_repo(
    owner: str,
    repo: str,
    token: str | None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """GET /repos/{owner}/{repo} → dict.

    Returns a slim dict (full_name, archived, updated_at, pushed_at,
    created_at, stargazers_count) — the subset we cache for the
    decay-cause workflow.

    Raises GitHubError on 4xx/5xx; the caller is expected to log and
    continue.
    """
    url = (
        f"https://api.github.com/repos/{urllib.parse.quote(owner)}"
        f"/{urllib.parse.quote(repo)}"
    )
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "agent-infrastructure-landscape-decay-sweep")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise GitHubError(f"repo-not-found: {owner}/{repo}") from e
        remaining = e.headers.get("X-RateLimit-Remaining") if e.headers else None
        if e.code == 403 and remaining == "0":
            reset = e.headers.get("X-RateLimit-Reset", "?") if e.headers else "?"
            raise GitHubError(f"rate-limited (reset epoch={reset})") from e
        raise GitHubError(
            f"http-{e.code}: {owner}/{repo}: {e.reason}"
        ) from e
    except urllib.error.URLError as e:
        raise GitHubError(f"network-error: {owner}/{repo}: {e.reason}") from e
    except (TimeoutError, OSError) as e:
        # Socket-level timeout (e.g. SSL read timeout). Treat as transient
        # network error so the caller can log + skip rather than crash the
        # whole sweep on a single slow request.
        raise GitHubError(f"network-error: {owner}/{repo}: {e}") from e
    # Slim cache shape.
    return {
        "full_name": data.get("full_name"),
        "pushed_at": data.get("pushed_at"),
        "updated_at": data.get("updated_at"),
        "created_at": data.get("created_at"),
        "stargazers_count": data.get("stargazers_count"),
        "archived": bool(data.get("archived")),
        "disabled": bool(data.get("disabled")),
        "fork": bool(data.get("fork")),
        "default_branch": data.get("default_branch"),
        "description": data.get("description"),
    }


# ---------------------------------------------------------------------------
# Cache I/O.
# ---------------------------------------------------------------------------


def cache_path(owner: str, repo: str) -> Path:
    safe_owner = owner.replace("/", "_")
    safe_repo = repo.replace("/", "_")
    return CACHE_DIR / f"{safe_owner}__{safe_repo}.json"


def load_cached(owner: str, repo: str) -> dict[str, Any] | None:
    p = cache_path(owner, repo)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_cached(owner: str, repo: str, data: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = cache_path(owner, repo)
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
    if not text.endswith("\n"):
        text += "\n"
    p.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML patching.
# ---------------------------------------------------------------------------


def html_escape_attr(s: str) -> str:
    """Escape a value for use inside a double-quoted HTML attribute.

    Mirrors the conservative escape policy in scripts/render.py
    (escape `&`, `<`, `>`, and `"`).
    """
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# Match a <tr ...> opening tag and capture (full_tag, attrs_inner).
# Anchored against `class="row-tN"` to limit hits to data rows only;
# the source HTML uses this class on every data row. We process one row
# at a time so each replacement is a clean string op.
TR_OPEN_RE = re.compile(
    r'<tr\s+([^>]*class="row-t[1-5]"[^>]*)>',
    re.IGNORECASE,
)

# Match data-* attrs we add or refresh. Used to detect existing values
# so the patch is idempotent across reruns.
DATA_LAST_VERIFIED_RE = re.compile(
    r'\s+data-last-verified="[^"]*"', re.IGNORECASE
)
DATA_DECAY_CAUSE_RE = re.compile(
    r'\s+data-decay-cause="[^"]*"', re.IGNORECASE
)
DATA_DECAY_DATE_RE = re.compile(
    r'\s+data-decay-date="[^"]*"', re.IGNORECASE
)
DATA_DECAY_EVIDENCE_RE = re.compile(
    r'\s+data-decay-evidence="[^"]*"', re.IGNORECASE
)


def patch_row_attrs(
    tr_open_tag: str,
    *,
    new_decay_cause: str,
    new_decay_date: str,
    new_decay_evidence: str,
    new_last_verified: str,
) -> str:
    """Return the rewritten `<tr ...>` open tag with the four data-*
    attrs set/replaced to the given values.

    Existing data-* attrs are stripped first so the patch is idempotent
    (a rerun produces byte-identical output). The four attrs are
    appended in canonical order:
        data-last-verified, data-decay-cause, data-decay-date,
        data-decay-evidence
    matching the render.py output and the §3c HTML example.
    """
    # Strip existing copies of the attrs we manage.
    inner = tr_open_tag
    for r in (
        DATA_LAST_VERIFIED_RE,
        DATA_DECAY_CAUSE_RE,
        DATA_DECAY_DATE_RE,
        DATA_DECAY_EVIDENCE_RE,
    ):
        inner = r.sub("", inner)
    # Tag is `<tr <attrs>>`. Insert the new attrs before the closing `>`.
    assert inner.endswith(">"), f"expected `>`-terminated <tr> tag, got: {inner!r}"
    head = inner[:-1]  # drop the closing `>`
    head = head.rstrip()
    new_attrs = (
        f' data-last-verified="{html_escape_attr(new_last_verified)}"'
        f' data-decay-cause="{html_escape_attr(new_decay_cause)}"'
        f' data-decay-date="{html_escape_attr(new_decay_date)}"'
        f' data-decay-evidence="{html_escape_attr(new_decay_evidence)}"'
    )
    return head + new_attrs + ">"


def find_tr_for_url(html: str, url: str) -> tuple[int, int, str] | None:
    """Locate the <tr> whose name-cell `<a href="...">` matches `url`.

    Returns (start_index_of_<tr_open, end_index_of_<tr_open, full_tag)
    or None if not found. The match is on the full URL so we don't
    accidentally hit a different row whose link contains the substring.
    """
    # The opening <tr is at some offset; the matching name <a href> is
    # within the next ~few KB. We use a forward scan: walk tr matches,
    # for each one look ahead for the first <a href="..."> that exactly
    # matches the target URL (URL-encoded escapes inside HTML attrs are
    # rare for our hrefs; we trust the literal match here).
    pos = 0
    while pos < len(html):
        m = TR_OPEN_RE.search(html, pos)
        if m is None:
            return None
        tr_start = m.start()
        tr_end = m.end()
        # Look ahead within the next ~6000 chars for the name <a href>.
        # 6000 chars comfortably exceeds the largest row in landscape.html.
        window = html[tr_end : tr_end + 6000]
        # The name cell is `<td class="name"><a href="URL">`.
        name_href = f'<td class="name"><a href="{url}">'
        # The HTML may double-quote-encode some hrefs; also try with
        # quote-escaped ampersands.
        url_esc = url.replace("&", "&amp;")
        name_href_esc = f'<td class="name"><a href="{url_esc}">'
        if name_href in window or name_href_esc in window:
            return tr_start, tr_end, m.group(0)
        pos = tr_end


def find_tr_by_repo_url(html: str, repo_full_url: str) -> tuple[int, int, str] | None:
    """Locate the <tr> whose name cell's `<a href="...">` value EQUALS
    repo_full_url (a github.com URL).

    Some catalog rows point their primary URL at the repo (so the
    `<a>` href is the github.com URL directly). For rows whose primary
    URL is something else (e.g. the company landing page) but whose
    `cells.gh.citation` is github.com, we fall back to scanning every
    <tr> for any `<a class="cite" href="<repo>">` substring within
    the row.
    """
    # Try fast path: direct href match.
    hit = find_tr_for_url(html, repo_full_url)
    if hit is not None:
        return hit
    # Fall back: walk every <tr> and look for the repo URL anywhere in
    # the row body.
    pos = 0
    repo_esc = repo_full_url.replace("&", "&amp;")
    while pos < len(html):
        m = TR_OPEN_RE.search(html, pos)
        if m is None:
            return None
        tr_start = m.start()
        tr_end = m.end()
        # Look for the row's `</tr>` to bound the row body.
        close_at = html.find("</tr>", tr_end)
        if close_at < 0:
            return None
        body = html[tr_end:close_at]
        if repo_full_url in body or repo_esc in body:
            return tr_start, tr_end, m.group(0)
        pos = close_at + len("</tr>")


# ---------------------------------------------------------------------------
# Phase C driver.
# ---------------------------------------------------------------------------


def phase_c_archive_sweep(args: argparse.Namespace) -> int:
    """Sweep every GitHub-bearing row's archived flag and label archived
    rows. Writes either data/landscape.json (Path A, default) or
    landscape.html (legacy) depending on --target."""
    target_json = args.target == "landscape.json"
    if not target_json:
        import warnings
        warnings.warn(
            "--target landscape.html is deprecated under Path A; "
            "writes will go to landscape.html for legacy compatibility only.",
            DeprecationWarning,
            stacklevel=2,
        )
        print(
            "warning: --target landscape.html is deprecated under Path A; "
            "writes will go to landscape.html for legacy compatibility only.",
            file=sys.stderr,
        )

    if not DATA_LANDSCAPE.exists():
        print(f"error: {DATA_LANDSCAPE} not found", file=sys.stderr)
        return 1
    if not target_json and not HTML_LANDSCAPE.exists():
        print(f"error: {HTML_LANDSCAPE} not found", file=sys.stderr)
        return 1

    landscape = load_landscape(DATA_LANDSCAPE)
    records = landscape.get("records") or []

    # Resolve GitHub repos per record (id → (owner, repo, repo_url)).
    repo_targets: list[tuple[str, str, str, str, dict[str, Any]]] = []
    for rec in records:
        info = extract_repo(rec)
        if info is None:
            continue
        owner, repo, repo_url = info
        repo_targets.append((rec["id"], owner, repo, repo_url, rec))

    token = args.github_token or os.environ.get("GITHUB_TOKEN")
    if token:
        print(
            f"  GITHUB_TOKEN provided — 5000/hr rate limit",
            file=sys.stderr,
        )
    else:
        print(
            f"  no GITHUB_TOKEN — falling back to 60/hr unauthenticated limit",
            file=sys.stderr,
        )

    print(
        f"  found {len(repo_targets)} github-bearing rows in landscape.json",
        file=sys.stderr,
    )
    if args.rate_limit:
        print(
            f"  --rate-limit={args.rate_limit} — capping API calls this run",
            file=sys.stderr,
        )

    # Walk repos, fetch with caching.
    archived_results: list[dict[str, Any]] = []
    api_calls = 0
    skipped_cached = 0
    failures: list[tuple[str, str]] = []  # (id, message)
    for rec_id, owner, repo, repo_url, rec in repo_targets:
        cached = load_cached(owner, repo)
        if cached is not None:
            skipped_cached += 1
            data = cached
        else:
            if args.rate_limit and api_calls >= args.rate_limit:
                print(
                    f"  --rate-limit reached ({api_calls}); stopping early",
                    file=sys.stderr,
                )
                break
            try:
                data = fetch_repo(owner, repo, token=token)
            except GitHubError as e:
                msg = str(e)
                failures.append((rec_id, msg))
                # Cache the failure marker so we don't re-hit. Use a
                # distinct shape so future passes can distinguish.
                save_cached(
                    owner,
                    repo,
                    {
                        "full_name": f"{owner}/{repo}",
                        "error": msg,
                        "fetched_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    },
                )
                api_calls += 1
                # Politeness sleep.
                if not args.no_sleep:
                    time.sleep(args.sleep_seconds)
                continue
            save_cached(owner, repo, data)
            api_calls += 1
            # Politeness sleep so we don't hammer the API.
            if not args.no_sleep:
                time.sleep(args.sleep_seconds)
        # Skip entries that cached a prior failure.
        if "error" in data and not data.get("archived"):
            continue
        if data.get("archived"):
            # `updated_at` is the timestamp the repo was archived (it
            # changes when archived flag flips). pushed_at is the date
            # of the last push before archiving. The spec asks for the
            # archived date — use updated_at and slice the date portion.
            updated_at = data.get("updated_at") or ""
            iso_date = updated_at[:10] if isinstance(updated_at, str) else ""
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", iso_date or ""):
                # Best-effort fallback: use pushed_at, then today.
                pushed_at = data.get("pushed_at") or ""
                iso_date = (
                    pushed_at[:10]
                    if isinstance(pushed_at, str)
                    and re.match(r"^\d{4}-\d{2}-\d{2}$", pushed_at[:10] or "")
                    else TODAY.isoformat()
                )
            archived_results.append({
                "id": rec_id,
                "owner": owner,
                "repo": repo,
                "repo_url": repo_url,
                "decay_date": iso_date,
                "stargazers_count": data.get("stargazers_count", 0),
            })

    # Summary print.
    print(
        f"  api calls this run: {api_calls}; cached hits: {skipped_cached}; "
        f"failures: {len(failures)}",
        file=sys.stderr,
    )
    print(f"  archived rows found: {len(archived_results)}", file=sys.stderr)
    for r in archived_results:
        print(
            f"    {r['id']} ({r['owner']}/{r['repo']}) archived on {r['decay_date']}",
            file=sys.stderr,
        )
    if failures:
        print(
            f"  failed lookups (first 10):",
            file=sys.stderr,
        )
        for rec_id, msg in failures[:10]:
            print(f"    {rec_id}: {msg}", file=sys.stderr)

    if args.dry_run:
        print(
            f"  --dry-run: not patching {'landscape.json' if target_json else 'landscape.html'}",
            file=sys.stderr,
        )
        return 0

    patched = 0
    not_found: list[str] = []

    if target_json:
        # Path A: stamp top-level decay_* fields onto each archived record
        # in landscape.json. extract.py also writes these as top-level
        # fields, so render.py picks them up directly.
        for r in archived_results:
            rec_id = r["id"]
            rec = next((x for x in records if x["id"] == rec_id), None)
            if rec is None:
                not_found.append(rec_id)
                continue
            rec["decay_cause"] = "archived"
            rec["decay_date"] = r["decay_date"]
            rec["decay_evidence"] = r["repo_url"]
            rec["last_verified_at"] = TODAY.isoformat()
            patched += 1
        if patched:
            save_landscape(landscape, DATA_LANDSCAPE)
        print(
            f"  patched {patched} records in {DATA_LANDSCAPE.name} "
            f"({len(not_found)} records not located)",
            file=sys.stderr,
        )
    else:
        # Legacy Path B: patch landscape.html as before.
        html_text = HTML_LANDSCAPE.read_text(encoding="utf-8")
        for r in archived_results:
            rec_id = r["id"]
            rec = next((x for x in records if x["id"] == rec_id), None)
            if rec is None:
                not_found.append(rec_id)
                continue
            hit = None
            if rec.get("url"):
                hit = find_tr_for_url(html_text, rec["url"])
            if hit is None:
                hit = find_tr_by_repo_url(html_text, r["repo_url"])
            if hit is None:
                not_found.append(rec_id)
                continue
            tr_start, tr_end, full_tag = hit
            new_tag = patch_row_attrs(
                full_tag,
                new_decay_cause="archived",
                new_decay_date=r["decay_date"],
                new_decay_evidence=r["repo_url"],
                new_last_verified=TODAY.isoformat(),
            )
            html_text = html_text[:tr_start] + new_tag + html_text[tr_end:]
            patched += 1

        if patched:
            HTML_LANDSCAPE.write_text(html_text, encoding="utf-8")
        print(
            f"  patched {patched} rows in landscape.html "
            f"({len(not_found)} rows not located in HTML)",
            file=sys.stderr,
        )

    if not_found:
        for rid in not_found[:10]:
            print(f"    not located: {rid}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = parser.add_subparsers(dest="phase", required=True)

    p_arch = sub.add_parser(
        "archive-sweep",
        help="Phase C: GitHub archive-flag sweep.",
    )
    p_arch.add_argument(
        "--dry-run",
        action="store_true",
        help="Report results without modifying landscape.html.",
    )
    p_arch.add_argument(
        "--rate-limit",
        type=int,
        default=0,
        help="Cap API calls this run (0 = uncapped).",
    )
    p_arch.add_argument(
        "--github-token",
        default=None,
        help="GitHub token (else read from GITHUB_TOKEN env).",
    )
    p_arch.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.4,
        help="Politeness sleep between API calls (default 0.4s).",
    )
    p_arch.add_argument(
        "--no-sleep",
        action="store_true",
        help="Disable politeness sleep (use only with a token).",
    )
    p_arch.add_argument(
        "--target",
        choices=["landscape.json", "landscape.html"],
        default="landscape.json",
        help=(
            "Where to write decay-cause fields. Default (Path A, refs #68) "
            "is landscape.json; landscape.html remains as a deprecated "
            "legacy path during the transition window."
        ),
    )

    args = parser.parse_args()

    if args.phase == "archive-sweep":
        return phase_c_archive_sweep(args)
    parser.print_help(file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
