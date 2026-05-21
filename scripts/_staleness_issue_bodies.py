#!/usr/bin/env python3
"""
_staleness_issue_bodies.py — render one markdown body file per flagged row.

Internal helper for .github/workflows/staleness.yml. Reads the JSON list
produced by ``scripts/check_staleness.py`` and writes one ``<i>.md`` plus
one ``<i>.json`` (title + id sidecar) per entry into the output dir. The
workflow's bash loop then dedups by id and calls ``gh issue create``
with ``--body-file``.

Kept in its own file rather than inline-heredoc'd into the YAML because
heredocs inside YAML ``run: |`` blocks introduce indentation surprises
that are easier to dodge than debug. The leading-underscore in the
filename keeps it sorted near other "support" scripts.

Usage:
    python scripts/_staleness_issue_bodies.py <report.json> <output-dir>
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: _staleness_issue_bodies.py <report.json> <output-dir>",
            file=sys.stderr,
        )
        return 2
    report_path = argv[1]
    body_dir = pathlib.Path(argv[2])
    body_dir.mkdir(parents=True, exist_ok=True)
    with open(report_path, "r", encoding="utf-8") as fh:
        entries = json.load(fh)
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i, e in enumerate(entries):
        body = (
            "This catalog is a **museum**, not an active-only registry. An\n"
            "abandoned 2018 project is just as valid a catalog entry as a\n"
            "live 2026 one — the longitudinal record is the value. This row\n"
            "hasn't been classified yet: the ask is to **fill in its\n"
            "`decay_cause`**, NOT to remove the row.\n"
            "\n"
            f"**Row id:** `{e['id']}`\n"
            f"**Name:** {e.get('name', '?')}\n"
            f"**Repo:** {e['repo']}\n"
            f"**Last commit:** {e['last_commit']}\n"
            f"**Days since last commit:** {e['days_since']}\n"
            f"**Severity:** **{e['severity']}** (per MAINTAINER.md §2 freshness SLA)\n"
            f"**Detection signal:** {e['signal']}\n"
            "\n"
            "Opened automatically by the weekly staleness check\n"
            "(`.github/workflows/staleness.yml`, issue #38). The detection\n"
            "windows are `stale` = 12-24 months quiet, `abandoned` = 24+\n"
            "months quiet. That signal is mechanical — it tells us the row\n"
            "went quiet, not *why*. The `decay_cause` field (see\n"
            "`docs/SCHEMA.md` §3c) is where the *why* lives.\n"
            "\n"
            "### Pick a decay-cause\n"
            "\n"
            "One of the eight enum values:\n"
            "\n"
            "- `acquired` — bought by another vendor.\n"
            "- `pivoted` — team moved to a different product.\n"
            "- `unfunded` — funding ran out, no acquisition.\n"
            "- `lost-benchmark-race` — outpaced by a better system in the same niche.\n"
            "- `superseded` — academic paper replaced by a follow-up paper by the same / overlapping authors.\n"
            "- `research-complete` — academic paper with no maintained codebase intended (one-shot research artefact).\n"
            "- `archived` — GitHub repo has `archived: true` set.\n"
            "- `unknown` — researched but no clear cause found.\n"
            "\n"
            "### Evidence\n"
            "\n"
            "Provide a URL (resolvable `http(s)://` — TechCrunch / Crunchbase\n"
            "/ founder blog post / GitHub repo / S2 follow-up paper / etc.)\n"
            "**or** an `[unverifiable] <free-text>` string describing what\n"
            "you searched. Example:\n"
            "`[unverifiable] researched: techcrunch, vbeat, hn algolia,\n"
            "wayback; no clear cause found`.\n"
            "\n"
            "### Applying the classification\n"
            "\n"
            "1. Open `data/landscape.json` and find the record with\n"
            f"   `id == \"{e['id']}\"`.\n"
            "2. Set the three record-level fields:\n"
            "   - `decay_cause` — one of the eight values above.\n"
            "   - `decay_date` — ISO `YYYY-MM-DD` (best estimate of when\n"
            "     the project went quiet; the last-commit date is a fine\n"
            "     default if you don't have something better).\n"
            "   - `decay_evidence` — URL or `[unverifiable] …` string.\n"
            "3. Run `make build` to refresh edges + re-render `landscape.html`.\n"
            "4. Run `make validate` to confirm the row passes gate 5\n"
            "   (decay-field enum + format checks).\n"
            "5. Commit (`data/landscape.json` + `landscape.html`) and close\n"
            "   this issue.\n"
            "\n"
            "The row stays in the catalog regardless of decay-cause — we\n"
            "want the historical entry. Auto-reopen is not implemented; if\n"
            "upstream resumes activity, this issue stays open until a\n"
            "maintainer closes it manually.\n"
            "\n"
            "---\n"
            "\n"
            f"_Generated by `scripts/check_staleness.py` on {generated_at}._\n"
        )
        (body_dir / f"{i}.md").write_text(body, encoding="utf-8")
        meta = {
            "id": e["id"],
            "title": (
                f"stale-row: {e['id']} ({e['severity']}, "
                f"{e['days_since']}d since last commit)"
            ),
        }
        (body_dir / f"{i}.json").write_text(json.dumps(meta), encoding="utf-8")
    print(
        f"prepared {len(entries)} body files in {body_dir}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
