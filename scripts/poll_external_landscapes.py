#!/usr/bin/env python3
"""Phase 5 — standing external-landscape poller (issue #151).

Runs monthly via .github/workflows/external-landscape-diff.yml. For each
enabled source in data/_external-landscapes.yml:

  1. Query GitHub for the latest commit SHA touching the source's data path.
  2. If the SHA is unchanged since the previous poll, skip the fetch.
  3. Otherwise fetch the raw file, record SHA-256 in a `_snapshot.json`
     manifest next to it, and write it under
     extraction/external/<source-id>/<YYYYMMDD>/ where YYYYMMDD is the
     target date (defaults to today UTC).

Then re-runs scripts/import_external_landscapes.py against the freshest
per-source snapshot (env var LANDSCAPE_SNAPSHOT_DATE pins the date the
import script reads from). Diffs the resulting candidates.csv and
cross-listing.csv against their pre-run contents and decides which
GitHub issues to open:

  - **intake-batch** — one issue if any new candidates appeared, listing
    them in Phase-1 priority order with links to the updated
    gap-report.md. Phase 3 (issue-per-candidate autoresearch) is not
    triggered from here — that policy has its own throttling.
  - **divergence** — one issue per source, if any matched row's
    source_categories changed since the previous cross-listing.

No-op runs are silent (no issues, no state changes committed).

Antgroup rule (Phase 0 licence audit, docs/DECISIONS.md 2026-07-09):
`enabled: false` sources are skipped entirely. Flip to true only after
the upstream licence audit is re-verified.

--dry-run: prints the issue titles + summaries that would be opened,
touches no snapshot files, opens no issues, exits 0.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "_external-landscapes.yml"
EXT_DIR = ROOT / "extraction" / "external"
IMPORT_SCRIPT = ROOT / "scripts" / "import_external_landscapes.py"

CANDIDATES_CSV = EXT_DIR / "candidates.csv"
CROSS_LISTING_CSV = EXT_DIR / "cross-listing.csv"
GAP_REPORT_MD = EXT_DIR / "gap-report.md"

DIVERGENCE_LABEL = "divergence"
INTAKE_BATCH_LABEL = "intake-batch"
WORKSTREAM_LABEL = "external-landscapes"


# --- manifest -------------------------------------------------------------

def load_manifest() -> list[dict[str, Any]]:
    if not MANIFEST.exists():
        print(f"poll_external_landscapes: {MANIFEST.relative_to(ROOT)} missing",
              file=sys.stderr)
        return []
    doc = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    sources = doc.get("sources") or []
    return [s for s in sources
            if isinstance(s, dict) and s.get("id") and s.get("enabled", True)]


# --- snapshot state -------------------------------------------------------

def latest_snapshot_dir(source_id: str) -> Path | None:
    src = EXT_DIR / source_id
    if not src.is_dir():
        return None
    dated = sorted(
        (d for d in src.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 8),
        key=lambda d: d.name,
    )
    return dated[-1] if dated else None


def previous_commit_sha(source_id: str) -> str | None:
    prev = latest_snapshot_dir(source_id)
    if not prev:
        return None
    manifest = prev / "_snapshot.json"
    if manifest.exists():
        try:
            return json.loads(manifest.read_text()).get("commit_sha")
        except json.JSONDecodeError:
            return None
    return None


# --- github fetch ---------------------------------------------------------

def gh_latest_commit_sha(repo: str, path: str) -> str | None:
    """Latest commit SHA touching `path` on `repo`'s default branch."""
    # `gh api` treats -f/-F as POST fields — for GET, put params in the URL.
    from urllib.parse import quote
    endpoint = f"repos/{repo}/commits?path={quote(path, safe='/')}&per_page=1"
    try:
        res = subprocess.run(
            ["gh", "api", endpoint],
            check=True, capture_output=True, text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"poll_external_landscapes: gh api commits failed for {repo} {path}: {e}",
              file=sys.stderr)
        return None
    try:
        commits = json.loads(res.stdout)
        if isinstance(commits, list) and commits:
            return commits[0].get("sha")
    except json.JSONDecodeError:
        pass
    return None


def gh_fetch_raw(repo: str, sha: str, path: str) -> bytes | None:
    """Fetch raw file at (repo, sha, path)."""
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"
    try:
        res = subprocess.run(
            ["curl", "-sSfL", url],
            check=True, capture_output=True,
        )
        return res.stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"poll_external_landscapes: curl failed for {url}: {e}", file=sys.stderr)
        return None


# --- refresh --------------------------------------------------------------

def refresh_source(source: dict[str, Any], target_date: str, dry_run: bool) -> dict[str, Any]:
    """Refresh one source. Returns a summary dict.

    summary["status"] is one of:
      "unchanged"  — upstream SHA unchanged since last poll.
      "refreshed"  — new snapshot written under target_date.
      "skipped"    — SHA lookup or fetch failed; existing snapshot untouched.
    """
    sid = source["id"]
    repo = source["repo"]
    path = source["data_path"]

    prev_sha = previous_commit_sha(sid)
    latest_sha = gh_latest_commit_sha(repo, path)
    summary = {
        "id": sid, "repo": repo, "path": path,
        "previous_sha": prev_sha, "latest_sha": latest_sha,
        "target_date": target_date, "status": "skipped",
    }
    if latest_sha is None:
        return summary
    if latest_sha == prev_sha:
        summary["status"] = "unchanged"
        return summary
    if dry_run:
        summary["status"] = "refreshed"
        return summary
    content = gh_fetch_raw(repo, latest_sha, path)
    if content is None:
        return summary
    filename = Path(path).name
    new_dir = EXT_DIR / sid / target_date
    new_dir.mkdir(parents=True, exist_ok=True)
    (new_dir / filename).write_bytes(content)
    sha256 = hashlib.sha256(content).hexdigest()
    (new_dir / "_snapshot.json").write_text(
        json.dumps({
            "source_id": sid, "repo": repo, "data_path": path,
            "commit_sha": latest_sha, "sha256": sha256,
            "snapshot_date": target_date,
        }, indent=2, sort_keys=True) + "\n",
    )
    summary["status"] = "refreshed"
    summary["sha256"] = sha256
    return summary


# --- diff -----------------------------------------------------------------

def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def diff_candidates(before: list[dict[str, str]], after: list[dict[str, str]]) -> list[dict[str, str]]:
    """New candidates: (source_id, name) pairs in `after` not present in `before`."""
    seen = {(r["source_id"], r["name"]) for r in before}
    return [r for r in after if (r["source_id"], r["name"]) not in seen]


def diff_divergences(before: list[dict[str, str]], after: list[dict[str, str]]) -> list[dict[str, str]]:
    """Matched rows whose source_categories changed."""
    by_key_before = {(r["landscape_id"], r["source_id"]): r for r in before}
    diverged: list[dict[str, str]] = []
    for r in after:
        key = (r["landscape_id"], r["source_id"])
        if key not in by_key_before:
            continue
        old_cats = by_key_before[key].get("source_categories", "")
        new_cats = r.get("source_categories", "")
        if old_cats != new_cats:
            diverged.append({
                "landscape_id": r["landscape_id"],
                "source_id": r["source_id"],
                "before": old_cats,
                "after": new_cats,
            })
    return diverged


# --- issue open ----------------------------------------------------------

def gh_issue_create(title: str, body: str, labels: list[str], dry_run: bool) -> bool:
    if dry_run:
        print(f"[dry-run] would open issue: {title}", file=sys.stderr)
        print(f"[dry-run] labels: {', '.join(labels)}", file=sys.stderr)
        return True
    args = ["gh", "issue", "create", "--title", title, "--body", body]
    for lab in labels:
        args += ["--label", lab]
    try:
        subprocess.run(args, check=True, cwd=str(ROOT))
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"poll_external_landscapes: gh issue create failed: {e}", file=sys.stderr)
        return False


def render_intake_batch_body(new_candidates: list[dict[str, str]], target_date: str) -> str:
    ordered = sorted(new_candidates, key=lambda r: (
        int(r.get("phase1_priority", "5")), r["source_id"], r["name"]))
    lines = [
        f"## New external-landscape candidates ({target_date})",
        "",
        f"The monthly external-landscape poll found **{len(ordered)}** new "
        f"unmatched upstream row(s) since the previous run. Full report: "
        f"`extraction/external/gap-report.md`.",
        "",
        "Phase 3 owns the per-candidate autoresearch policy — this issue is "
        "the batch signal, not a trigger.",
        "",
        "| Priority | Source | Name | Categories | Upstream URL |",
        "|---:|---|---|---|---|",
    ]
    for c in ordered[:200]:
        url = c.get("repo_url") or c.get("homepage_url") or ""
        cats = c.get("source_categories") or "—"
        lines.append(
            f"| {c.get('phase1_priority', '?')} | `{c['source_id']}` | "
            f"{c['name']} | {cats} | {url} |"
        )
    if len(ordered) > 200:
        lines.append("")
        lines.append(f"…and {len(ordered) - 200} more (see gap-report.md).")
    lines.extend([
        "",
        "---",
        "_Auto-opened by `scripts/poll_external_landscapes.py` (Phase 5, "
        "issue #151)._",
    ])
    return "\n".join(lines) + "\n"


def render_divergence_body(source_id: str, diverged: list[dict[str, str]], target_date: str) -> str:
    lines = [
        f"## Category divergence: `{source_id}` ({target_date})",
        "",
        f"The monthly external-landscape poll observed **{len(diverged)}** "
        f"matched row(s) whose upstream `source_categories` string changed "
        f"since the previous cross-listing. This is either upstream "
        f"re-taxonomy (harmless, update our cite) or a genuine "
        f"reclassification worth reflecting in the catalog.",
        "",
        "| Landscape ID | Before | After |",
        "|---|---|---|",
    ]
    for d in sorted(diverged, key=lambda r: r["landscape_id"]):
        before = d["before"] or "—"
        after = d["after"] or "—"
        lines.append(f"| `{d['landscape_id']}` | {before} | {after} |")
    lines.extend([
        "",
        "---",
        "_Auto-opened by `scripts/poll_external_landscapes.py` (Phase 5, "
        "issue #151)._",
    ])
    return "\n".join(lines) + "\n"


# --- driver ---------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    if not IMPORT_SCRIPT.exists():
        print(f"poll_external_landscapes: {IMPORT_SCRIPT} missing", file=sys.stderr)
        return 2

    sources = load_manifest()
    if not sources:
        print("poll_external_landscapes: no enabled sources in manifest", file=sys.stderr)
        return 0

    target_date = args.target_date or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    if not (len(target_date) == 8 and target_date.isdigit()):
        print(f"poll_external_landscapes: --target-date must be YYYYMMDD, got {target_date!r}",
              file=sys.stderr)
        return 2

    # Refresh snapshots.
    refresh_summaries = [refresh_source(s, target_date, args.dry_run) for s in sources]
    changed = [r for r in refresh_summaries if r["status"] == "refreshed"]

    # Snapshot the CSVs before re-running import so we can diff.
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        for src in (CANDIDATES_CSV, CROSS_LISTING_CSV):
            if src.exists():
                shutil.copy2(src, tdp / src.name)
        before_candidates = read_csv(tdp / CANDIDATES_CSV.name)
        before_cross = read_csv(tdp / CROSS_LISTING_CSV.name)

    # Re-run import (skip on dry-run — the source dirs weren't updated).
    if args.dry_run:
        after_candidates = before_candidates
        after_cross = before_cross
    else:
        env = os.environ.copy()
        env["LANDSCAPE_SNAPSHOT_DATE"] = target_date
        try:
            subprocess.run(
                [sys.executable, str(IMPORT_SCRIPT), "--out-dir", str(EXT_DIR)],
                check=True, cwd=str(ROOT), env=env,
            )
        except subprocess.CalledProcessError as e:
            print(f"poll_external_landscapes: import_external_landscapes.py failed: {e}",
                  file=sys.stderr)
            return 2
        after_candidates = read_csv(CANDIDATES_CSV)
        after_cross = read_csv(CROSS_LISTING_CSV)

    new_candidates = diff_candidates(before_candidates, after_candidates)
    divergences = diff_divergences(before_cross, after_cross)

    # Emit issues.
    opened = 0
    if new_candidates:
        title = f"External landscapes — new candidates ({target_date}, {len(new_candidates)})"
        body = render_intake_batch_body(new_candidates, target_date)
        if gh_issue_create(title, body,
                           [INTAKE_BATCH_LABEL, WORKSTREAM_LABEL], args.dry_run):
            opened += 1

    divergences_by_src: dict[str, list[dict[str, str]]] = {}
    for d in divergences:
        divergences_by_src.setdefault(d["source_id"], []).append(d)
    for sid, rows in sorted(divergences_by_src.items()):
        title = f"External landscapes — {sid} category divergence ({target_date}, {len(rows)})"
        body = render_divergence_body(sid, rows, target_date)
        if gh_issue_create(title, body,
                           [DIVERGENCE_LABEL, WORKSTREAM_LABEL], args.dry_run):
            opened += 1

    print(
        f"poll_external_landscapes: refresh={len(changed)}/{len(sources)} "
        f"new_candidates={len(new_candidates)} divergences={len(divergences)} "
        f"issues_opened={opened} target_date={target_date}",
        file=sys.stderr,
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true",
                   help="Don't touch snapshot files or open issues.")
    p.add_argument("--target-date", default=None,
                   help="YYYYMMDD (default: today UTC).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
