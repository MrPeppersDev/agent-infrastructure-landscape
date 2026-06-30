#!/usr/bin/env python3
"""
cron_catalog_pulse.py — daily aggregate catalog snapshot.

Phase 2 / Gate 6 (issue #100). Companion workflow:
`.github/workflows/catalog-pulse.yml`.

Produces a daily markdown card at `docs/pulse-YYYY-MM-DD.md` summarising:

  - New rows (rows added in the past 24h)
  - Retirements (decay_cause newly set in the past 24h)
  - Stale-cell count (rows whose row-level last_verified_at is > 55 days)
  - Drift hot-spots (read from yesterday's `docs/drift-*.md`, if any)
  - Top-N most-queried surfaces (placeholder — we don't yet have query
    telemetry; surfaced with a TODO note per spec)

The web `/findings` route can enumerate `docs/pulse-*.md` to render a
timeline of daily cards.

Usage
-----

    python3 scripts/cron_catalog_pulse.py [--output PATH] [--today YYYY-MM-DD] [--dry-run]

`--output` defaults to `docs/pulse-YYYY-MM-DD.md`. `--dry-run` has no
side-effect distinction from the default — there are no gh calls in the
pulse — but it's accepted for symmetry with the other Gate 6 crons.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE = ROOT / "data" / "landscape.json"
DEFAULT_DRIFT_DIR = ROOT / "docs"

STALE_DAYS = 55  # gate-6 cell-level staleness threshold from scripts/validate.py


def load_landscape() -> dict[str, Any]:
    return json.loads(LANDSCAPE.read_text(encoding="utf-8"))


def days_since_iso(today: dt.date, iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        d = dt.date.fromisoformat(iso[:10])
    except ValueError:
        return None
    return (today - d).days


def new_rows_in_24h(records: list[dict[str, Any]], today: dt.date) -> list[dict[str, Any]]:
    """A "new row" is one whose last_verified_at is within the past 24h AND
    that did not exist in yesterday's git snapshot.

    Practical implementation: we trust git for the new-row signal — anything
    added to `data/landscape.json` in the past 24h is a candidate, and the
    record's `id` not being present in the prior snapshot means "new".
    """
    cutoff = today - dt.timedelta(days=1)
    # Try git: list ids that newly appeared in landscape.json over the last
    # 24 hours. We do this by reading the file as it was 24h ago and diffing
    # the id sets.
    prior_ids = git_ids_at(cutoff_iso=(today - dt.timedelta(days=1)).isoformat())
    if prior_ids is None:
        return []
    current_ids = {r["id"] for r in records}
    new_ids = current_ids - prior_ids
    return [r for r in records if r.get("id") in new_ids]


def git_ids_at(cutoff_iso: str) -> set[str] | None:
    """Return the set of record ids present in data/landscape.json as of the
    most recent commit at-or-before `cutoff_iso`. Returns None if git
    archaeology fails (e.g., file didn't exist yet)."""
    try:
        proc = subprocess.run(
            ["git", "log", "-1", f"--before={cutoff_iso}", "--format=%H", "--", "data/landscape.json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        sha = proc.stdout.strip()
        show = subprocess.run(
            ["git", "show", f"{sha}:data/landscape.json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        if show.returncode != 0:
            return None
        data = json.loads(show.stdout)
        return {r["id"] for r in data.get("records", []) if "id" in r}
    except Exception:  # noqa: BLE001
        return None


def newly_retired_in_24h(records: list[dict[str, Any]], today: dt.date) -> list[dict[str, Any]]:
    """A retirement is a row whose decay_date falls in the past 24h."""
    out = []
    for r in records:
        if not r.get("decay_cause"):
            continue
        delta = days_since_iso(today, r.get("decay_date"))
        if delta is not None and 0 <= delta <= 1:
            out.append(r)
    return out


def stale_row_count(records: list[dict[str, Any]], today: dt.date) -> int:
    n = 0
    for r in records:
        delta = days_since_iso(today, r.get("last_verified_at"))
        if delta is not None and delta > STALE_DAYS:
            n += 1
    return n


def drift_hotspots(drift_dir: Path, today: dt.date) -> list[str]:
    """Read yesterday's `docs/drift-*.md` if present and pull out question
    ids that were flagged as material drift."""
    # try yesterday first, fall back to most-recent-prior
    candidates = sorted(drift_dir.glob("drift-*.md"))
    target: Path | None = None
    for p in reversed(candidates):
        try:
            d = dt.date.fromisoformat(p.stem.removeprefix("drift-"))
        except ValueError:
            continue
        if d < today:
            target = p
            break
    if target is None:
        return []
    text = target.read_text(encoding="utf-8")
    # Match the bullet line we emit: `- **drift**: top-1 was `X`, now `Y``
    # The question id is the preceding `### ` header.
    hotspots: list[str] = []
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
        elif current and "**drift**" in line:
            hotspots.append(current)
    return hotspots


def render_pulse_markdown(
    today: dt.date,
    new_rows: list[dict[str, Any]],
    retired: list[dict[str, Any]],
    stale_count: int,
    hotspots: list[str],
) -> str:
    lines = [
        f"# Catalog pulse — {today.isoformat()}",
        "",
        "Daily aggregate snapshot of catalog activity. Generated by "
        "`scripts/cron_catalog_pulse.py` (Phase 2 / Gate 6, issue #100).",
        "",
        "## New rows (past 24h)",
        "",
    ]
    if not new_rows:
        lines.append("_None._")
    else:
        for r in new_rows[:50]:
            lines.append(f"- `{r['id']}` — {r.get('name','?')}")
        if len(new_rows) > 50:
            lines.append(f"- _… {len(new_rows)-50} more._")
    lines.extend(["", "## Retirements (past 24h)", ""])
    if not retired:
        lines.append("_None._")
    else:
        for r in retired:
            cause = r.get("decay_cause", "?")
            lines.append(f"- `{r['id']}` — {r.get('name','?')} (cause: `{cause}`)")
    lines.extend([
        "",
        f"## Stale-row count",
        "",
        f"- {stale_count} row(s) with row-level `last_verified_at` > {STALE_DAYS} days old.",
        "",
        "## Drift hot-spots (from yesterday's recommendation-drift run)",
        "",
    ])
    if not hotspots:
        lines.append("_None._")
    else:
        for qid in hotspots:
            lines.append(f"- `{qid}`")
    lines.extend([
        "",
        "## Top-N most-queried surfaces",
        "",
        "<!-- TODO(telemetry): we don't yet have query telemetry; this is a "
        "placeholder. When MCP/CLI query logging lands, populate this list "
        "from the past-24h aggregate. See issue #100 for context. -->",
        "",
        "_Placeholder — query telemetry not yet wired._",
        "",
        "---",
        "",
        f"_Generated {dt.datetime.now(dt.timezone.utc).isoformat()} by "
        "`scripts/cron_catalog_pulse.py`._",
    ])
    return "\n".join(lines).rstrip() + "\n"


def run(args: argparse.Namespace) -> int:
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    data = load_landscape()
    records = data.get("records") or []

    new_rows = new_rows_in_24h(records, today)
    retired = newly_retired_in_24h(records, today)
    stale_count = stale_row_count(records, today)
    hotspots = drift_hotspots(args.drift_dir, today)

    md = render_pulse_markdown(today, new_rows, retired, stale_count, hotspots)
    out_path: Path = args.output or (ROOT / "docs" / f"pulse-{today.isoformat()}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(
        f"cron_catalog_pulse: wrote {out_path} "
        f"(new={len(new_rows)} retired={len(retired)} stale={stale_count} hotspots={len(hotspots)})",
        file=sys.stderr,
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--today", default=None,
                   help="Override today (ISO date). Default: actual UTC today.")
    p.add_argument("--output", type=Path, default=None,
                   help="Output path (default: docs/pulse-YYYY-MM-DD.md).")
    p.add_argument("--drift-dir", type=Path, default=DEFAULT_DRIFT_DIR,
                   help="Directory holding drift-*.md snapshots (default: docs/).")
    p.add_argument("--dry-run", action="store_true",
                   help="Accepted for symmetry with other Gate 6 crons (this script has no "
                        "remote side-effects regardless).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
