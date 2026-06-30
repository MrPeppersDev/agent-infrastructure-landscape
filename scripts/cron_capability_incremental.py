#!/usr/bin/env python3
"""
cron_capability_incremental.py — re-score `capability_composite_score` for
rows whose `capability_benchmark_sources` cell changed in the past 24h.

Phase 2 / Gate 6 (issue #100). Companion workflow:
`.github/workflows/capability-incremental.yml`.

What "changed in the past 24h" means
------------------------------------

For each row with a populated `capability-benchmark-sources` cell, the
script asks three questions in priority order:

1. Does `_provenance[capability-benchmark-sources].scraped_at` (or
   `edited_at` / `generated_at`) fall in the past 24h? If yes — affected.
2. Otherwise, does the row's `last_verified_at` fall in the past 24h?
   If yes — affected (coarse fallback; the cell might have been touched
   without an explicit per-cell timestamp).
3. Otherwise, does `git log --since=24h -p data/landscape.json` show
   the row id in a diff hunk that also touches `capability-benchmark-sources`?
   If yes — affected.

Step 3 is the cheap-but-imprecise fallback. The Python implementation
greps the diff for the row id and the cell slug appearing within the
same hunk. False positives are tolerable — they just cause a no-op
auto-PR that the reviewer closes.

Scoring
-------

The recommender consumes the existing `capability-composite-score` cell
value verbatim — there is **no** in-script formula for "what should the
score be?" Phase 2 / Gate 1 backfilled scores from benchmarks via LLM
prompts, but live re-scoring requires a benchmark-data pipeline that
doesn't exist yet. So this script's job for now is to **detect** affected
rows and open an auto-PR that records *which* benchmark-source field
changed and parks the score question for human review.

Per spec §5: "Every daily run produces auto-PRs or auto-issues — never
direct writes to data/landscape.json." This script writes nothing to the
catalog. It opens a draft PR with a placeholder JSON diff (no-op) and a
PR body that includes the benchmark-sources delta.

Usage
-----

    python3 scripts/cron_capability_incremental.py [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE = ROOT / "data" / "landscape.json"
CELL_SLUG = "capability-benchmark-sources"
SCORE_SLUG = "capability-composite-score"


def load_landscape() -> dict[str, Any]:
    return json.loads(LANDSCAPE.read_text(encoding="utf-8"))


def iso_within_24h(iso: str | None, today: dt.datetime) -> bool:
    if not iso:
        return False
    try:
        # Accept date-only or full ISO.
        if "T" in iso:
            t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        else:
            t = dt.datetime.fromisoformat(iso + "T00:00:00+00:00")
    except ValueError:
        return False
    delta = today - t
    return delta.total_seconds() < 86400 and delta.total_seconds() >= 0


def per_cell_changed_at(record: dict[str, Any]) -> str | None:
    prov = (record.get("_provenance") or {}).get(CELL_SLUG)
    if not prov:
        return None
    # CellProvenance variants — try each timestamp key.
    for key in ("scraped_at", "edited_at", "generated_at"):
        ts = prov.get(key)
        if ts:
            return ts
    return None


def affected_via_git(today: dt.datetime) -> set[str]:
    """Run `git log --since=24h -p data/landscape.json` and find row ids
    whose hunks also touched the capability-benchmark-sources cell.
    """
    since = (today - dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        proc = subprocess.run(
            ["git", "log", f"--since={since}", "-p", "--", "data/landscape.json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
    except Exception as e:  # noqa: BLE001
        print(f"cron_capability_incremental: git log failed: {e}", file=sys.stderr)
        return set()
    if proc.returncode != 0 or not proc.stdout:
        return set()

    affected: set[str] = set()
    current_id: str | None = None
    seen_cell_in_record = False
    for line in proc.stdout.splitlines():
        # rough heuristic: track the most-recently-seen "id" line; flag if a
        # capability-benchmark-sources line appears within ~200 lines of it.
        stripped = line.strip()
        if (stripped.startswith('"id":') or stripped.startswith('+"id":') or
                stripped.startswith('-"id":')):
            # parse the JSON-string value
            try:
                _, val = stripped.lstrip("+-").split(":", 1)
                val = val.strip().rstrip(",").strip('"')
                current_id = val
                seen_cell_in_record = False
            except ValueError:
                current_id = None
        elif CELL_SLUG in stripped and current_id and not seen_cell_in_record:
            affected.add(current_id)
            seen_cell_in_record = True
    return affected


def find_affected(today: dt.datetime) -> list[dict[str, Any]]:
    """Return list of records whose capability-benchmark-sources changed
    in the past 24h. Each entry is the raw record (used by the PR body).
    """
    data = load_landscape()
    records = data.get("records") or []

    affected_ids: set[str] = set()
    for rec in records:
        cells = rec.get("cells") or {}
        bs = cells.get(CELL_SLUG) or {}
        if not bs.get("value"):
            continue
        # 1. per-cell timestamp
        ts = per_cell_changed_at(rec)
        if iso_within_24h(ts, today):
            affected_ids.add(rec["id"])
            continue
        # 2. row-level last_verified_at
        if iso_within_24h(rec.get("last_verified_at"), today):
            affected_ids.add(rec["id"])

    # 3. git fallback
    affected_ids.update(affected_via_git(today))

    return [r for r in records if r.get("id") in affected_ids]


# ---------------------------------------------------------------------------
# PR rendering
# ---------------------------------------------------------------------------


def render_pr_body(record: dict[str, Any]) -> str:
    cells = record.get("cells") or {}
    bs = cells.get(CELL_SLUG, {})
    score_cell = cells.get(SCORE_SLUG, {})
    prov = (record.get("_provenance") or {}).get(CELL_SLUG, {})

    lines = [
        f"## Auto-PR — capability re-score request for `{record['id']}`",
        "",
        f"Row **{record.get('name','?')}** had its `{CELL_SLUG}` cell change in the past 24h. "
        "Phase 2 / Gate 6 (issue #100) requires a re-score review — the recommender "
        f"reads `{SCORE_SLUG}` verbatim, so a sources change should be reflected in the "
        "score (or explicitly noted as not).",
        "",
        "### Current state",
        "",
        f"- `{CELL_SLUG}`:",
        "  ```",
        f"  {bs.get('value','(empty)')[:500]}",
        "  ```",
        f"- `{SCORE_SLUG}`: `{score_cell.get('value','(empty)')}`",
        f"- provenance: source=`{prov.get('source','?')}` verified=`{prov.get('verified','?')}`",
        "",
        "### Proposed change",
        "",
        "_No automatic numeric change applied — this PR is a **review pin**. "
        "Live benchmark re-scoring is Gate 8's responsibility; for now the maintainer "
        "should either:_",
        "",
        "- update the score manually if the new sources warrant it, or",
        "- close this PR with a comment if the sources change is cosmetic.",
        "",
        "_Auto-opened by `scripts/cron_capability_incremental.py` "
        "(Phase 2 / Gate 6). Daily runs move signal, not state._",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Branch + PR side-effects
# ---------------------------------------------------------------------------


def open_pr_for(record: dict[str, Any], today: dt.date, dry_run: bool) -> None:
    rec_id = record["id"]
    branch = f"capability-incremental/{today.isoformat()}/{rec_id}"
    title = f"capability-incremental: review {rec_id} ({today.isoformat()})"
    body = render_pr_body(record)

    if dry_run:
        print(f"[dry-run] would open PR: {title}")
        return

    # Dedupe — if an open PR with this exact title already exists, skip.
    existing = subprocess.run(
        ["gh", "pr", "list", "--state", "open",
         "--search", f"\"{title}\" in:title", "--json", "number", "--jq", "length"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if existing.returncode == 0 and existing.stdout.strip() not in ("", "0"):
        print(f"skip: already-open PR for {rec_id}")
        return

    # Create branch + empty commit + PR. Empty commit keeps the PR as a
    # review-pin without touching landscape.json (signal not state).
    subprocess.run(["git", "checkout", "-b", branch], capture_output=True, text=True, cwd=str(ROOT))
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m",
         f"capability-incremental: review pin for {rec_id}\n\n{title}"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    subprocess.run(["git", "push", "-u", "origin", branch], capture_output=True, text=True, cwd=str(ROOT))
    subprocess.run(
        ["gh", "pr", "create", "--title", title, "--body", body, "--draft"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    # Return to whatever branch we were on before; CI runs detached anyway.
    subprocess.run(["git", "checkout", "-"], capture_output=True, text=True, cwd=str(ROOT))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    if args.today:
        today_dt = dt.datetime.fromisoformat(args.today + "T00:00:00+00:00")
    else:
        today_dt = dt.datetime.now(dt.timezone.utc)
    today = today_dt.date()

    affected = find_affected(today_dt)
    print(
        f"cron_capability_incremental: {len(affected)} row(s) affected "
        f"(window=24h, today={today.isoformat()}).",
        file=sys.stderr,
    )
    if args.output:
        args.output.write_text(
            json.dumps([{"id": r["id"], "name": r.get("name")} for r in affected], indent=2) + "\n",
            encoding="utf-8",
        )
    if not affected:
        return 0
    for rec in affected[: args.max_emit]:
        open_pr_for(rec, today, args.dry_run)
    if len(affected) > args.max_emit:
        print(
            f"cron_capability_incremental: capped at {args.max_emit}; "
            f"{len(affected) - args.max_emit} more queued for next run.",
            file=sys.stderr,
        )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--today", default=None,
                   help="Override today (ISO date). Default: actual UTC today.")
    p.add_argument("--max-emit", type=int, default=20,
                   help="Cap on PRs opened per run (default: 20).")
    p.add_argument("--output", type=Path, default=None,
                   help="Optional: write JSON list of affected rows to PATH.")
    p.add_argument("--dry-run", action="store_true",
                   help="Do full compute, but skip every git/gh side-effect.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
