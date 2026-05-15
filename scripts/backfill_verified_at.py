#!/usr/bin/env python3
"""
backfill_verified_at.py — initial backfill of last_verified_at attributes
for every record (row-level) and high-volatility cells (per-cell) on
landscape.html.

Strategy
--------
  - Build a {line_number: ISO-date} map from a single `git blame -p
    landscape.html` pass. This is the only git invocation we need —
    blame reports per-line author-time, which we use as the
    last-modification timestamp for that line.
  - Parse landscape.html with the same line-level granularity. For each
    data-row <tr> block, the row's `last_verified_at` is the *latest*
    blame-date across every line that belongs to the block.
  - For each volatile <td> cell, the cell's `last_verified_at` is the
    blame-date of that cell's line (one line per <td> in the rendered
    layout).
  - Edge case — if a line's blame falls under the bootstrap "Initial
    commit" we still use it; if any record has zero parseable lines
    (shouldn't happen but defensive), fall back to the first commit
    that touched landscape.html.
  - Output is written back into landscape.html as HTML attributes:
      <tr class="row-t1" data-last-verified="YYYY-MM-DD">
      <td class="vendor-benchmarks" data-last-verified="YYYY-MM-DD">…</td>
    Only volatile cells receive the per-cell attribute. Low-volatility
    cells inherit the row-level attribute.

High-volatility cells (per docs/SCHEMA.md §3b)
----------------------------------------------
  - vendor-benchmarks                    (benchmark scores)
  - obs-* (8 columns)                    (observability integrations)
  - cost-* (7 columns)                   (cost-control features)
  - eval-* (7 columns)                   (eval-tooling integrations)
  - funding                              (funding stage / state)
  - created, latest-release              (release / lifecycle dates)
  - gh                                   (star count, last-commit date)
  - mindshare, citations                 (inbound counts)
  - commit-trajectory, citation-trajectory, download-trajectory
                                         (trajectory data)

Usage
-----
  python3 scripts/backfill_verified_at.py                # in-place rewrite
  python3 scripts/backfill_verified_at.py --dry-run      # print summary only
  python3 scripts/backfill_verified_at.py --check        # exit 1 if any row
                                                         # lacks data-last-verified
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_HTML = ROOT / "landscape.html"

# High-volatility cell classes. Anything else inherits the row-level date.
VOLATILE_CELL_CLASSES = {
    # Lifecycle & release dates
    "created",
    "latest-release",
    # Mindshare / inbound counts / star + last-commit date
    "gh",
    "mindshare",
    "citations",
    # Funding state
    "funding",
    # Benchmarks
    "vendor-benchmarks",
    # Trajectory series
    "commit-trajectory",
    "citation-trajectory",
    "download-trajectory",
    # T1-1 observability columns (issue #39)
    "obs-langsmith",
    "obs-opentelemetry",
    "obs-datadog",
    "obs-helicone",
    "obs-weave",
    "obs-langfuse",
    "obs-arize",
    "obs-custom",
    # T1-3 cost-control columns (issue #41)
    "cost-token-budget",
    "cost-prompt-caching",
    "cost-semantic-caching",
    "cost-batching",
    "cost-model-routing",
    "cost-streaming-only",
    "cost-observability-cost-attribution",
    # T1-2 eval-tooling columns (issue #40)
    "eval-langsmith-evals",
    "eval-braintrust",
    "eval-weights-and-biases-agent",
    "eval-helicone-evals",
    "eval-custom-test-harness",
    "eval-human-loop",
    "eval-production-traffic-replay",
}

# Detect a data row's opening <tr>. Matches both the normal form
# (`<tr class="row-tN">`) and a form that already carries
# data-last-verified (so reruns are idempotent).
TR_OPEN_RE = re.compile(r'^(\s*)<tr class="row-t(\d)"([^>]*)>')
TR_CLOSE_RE = re.compile(r'^\s*</tr>\s*$')

# Detect a single-line <td class="…">…</td>. The landscape.html layout
# emits exactly one <td> per line inside a row, which is what makes
# per-cell blame attribution tractable.
TD_OPEN_RE = re.compile(r'^(\s*)<td class="([^"]+)"([^>]*)>(.*)$', re.DOTALL)

DATA_ATTR_RE = re.compile(r' data-last-verified="\d{4}-\d{2}-\d{2}"')


def git_blame_dates(path: Path) -> list[str | None]:
    """Return a list of `YYYY-MM-DD` strings, one per line of `path`.

    Index 0 of the list corresponds to line 1 (git's 1-indexed line
    numbers). Lines without a blame entry (shouldn't happen for a
    tracked file) are None.
    """
    cmd = [
        "git",
        "blame",
        "-p",
        "--",
        str(path.relative_to(ROOT)),
    ]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)

    # Blame porcelain output: header lines like
    #   <sha> <orig-line> <final-line> [<num-lines>]
    #   author …
    #   author-mail …
    #   author-time <unix-ts>
    #   author-tz <+/-HHMM>
    #   …
    #   \t<file content of that line>
    # The final-line tells us which line we're on; author-time +
    # author-tz give the timezone-local timestamp we'll format as
    # ISO date. We use *local* (not UTC) date because git log --format=%cs
    # — the documented backfill source in the issue — uses local
    # committer date, and we want to match that intuition.
    dates: dict[int, str] = {}
    current_line: int | None = None
    current_author_time: int | None = None
    current_author_tz: str | None = None
    sha_to_info: dict[str, tuple[int, str]] = {}
    current_sha: str | None = None
    SHA_RE = re.compile(r"^([0-9a-f]{40}) \d+ (\d+)(?: \d+)?$")
    AUTHOR_TIME_RE = re.compile(r"^author-time (\d+)$")
    AUTHOR_TZ_RE = re.compile(r"^author-tz ([+-]\d{4})$")

    def _local_date(ts: int, tz: str | None) -> str:
        offset_seconds = 0
        if tz and len(tz) == 5:
            sign = 1 if tz[0] == "+" else -1
            offset_seconds = sign * (int(tz[1:3]) * 3600 + int(tz[3:5]) * 60)
        return _dt.datetime.utcfromtimestamp(ts + offset_seconds).date().isoformat()

    for raw_line in res.stdout.splitlines():
        m = SHA_RE.match(raw_line)
        if m:
            current_sha = m.group(1)
            current_line = int(m.group(2))
            cached = sha_to_info.get(current_sha)
            if cached is not None:
                current_author_time, current_author_tz = cached
            else:
                current_author_time = None
                current_author_tz = None
            continue
        m = AUTHOR_TIME_RE.match(raw_line)
        if m:
            current_author_time = int(m.group(1))
            continue
        m = AUTHOR_TZ_RE.match(raw_line)
        if m:
            current_author_tz = m.group(1)
            if current_sha is not None and current_author_time is not None:
                sha_to_info[current_sha] = (current_author_time, current_author_tz)
            continue
        # Lines starting with \t are the literal file content; commit
        # the (line, date) mapping there.
        if raw_line.startswith("\t"):
            if current_line is not None and current_author_time is not None:
                dates[current_line] = _local_date(
                    current_author_time, current_author_tz
                )

    if not dates:
        return []
    max_line = max(dates)
    return [dates.get(i + 1) for i in range(max_line)]


def html_first_commit_date(path: Path) -> str:
    """Fall back date for rows with no blameable lines (shouldn't happen)."""
    res = subprocess.run(
        ["git", "log", "--reverse", "--format=%cs", "--", str(path.relative_to(ROOT))],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = res.stdout.splitlines()
    return lines[0] if lines else "2026-05-06"


def latest_date(dates: list[str]) -> str:
    """Return the lexicographically-greatest ISO date (ISO-8601 sorts correctly)."""
    return max(d for d in dates if d)


def strip_existing_attr(line: str) -> str:
    """Remove any pre-existing data-last-verified attr so backfill is idempotent."""
    return DATA_ATTR_RE.sub("", line)


def inject_attr(line: str, date: str) -> str:
    """Insert `data-last-verified="YYYY-MM-DD"` into the opening tag.

    For a <tr> line: insert right after `class="row-tN"`.
    For a <td> line: insert right after `class="…"`.
    Idempotent: pre-existing attr is stripped first.
    """
    line = strip_existing_attr(line)
    # Find the first `>` that closes the opening tag and inject before it.
    # The class="…" attribute always comes first on these lines, so we
    # inject after its closing quote — keeping ordering: class, data-last-verified, rest.
    m = re.match(r'^(\s*<\w+\s+class="[^"]+")(\s*)([^>]*)>(.*)$', line, re.DOTALL)
    if not m:
        return line
    indent_open, ws, rest_attrs, after = m.group(1), m.group(2), m.group(3), m.group(4)
    rest_attrs = rest_attrs.strip()
    if rest_attrs:
        new = f'{indent_open} data-last-verified="{date}" {rest_attrs}>{after}'
    else:
        new = f'{indent_open} data-last-verified="{date}">{after}'
    return new


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        default=str(LANDSCAPE_HTML),
        help="path to landscape.html (default: ./landscape.html)",
    )
    ap.add_argument(
        "--output",
        default=None,
        help="path to write output (default: in-place rewrite of --input)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="don't write; print summary only",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any data row lacks data-last-verified",
    )
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output) if args.output else in_path

    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2

    print(f"reading {in_path}")
    html_text = in_path.read_text(encoding="utf-8")
    lines = html_text.split("\n")

    print(f"running git blame on {in_path.relative_to(ROOT)}…")
    blame_dates = git_blame_dates(in_path)
    if not blame_dates:
        print("error: git blame returned no data", file=sys.stderr)
        return 2

    fallback_date = html_first_commit_date(in_path)
    print(f"  blame coverage: {sum(1 for d in blame_dates if d)}/{len(lines)} lines")
    print(f"  fallback date: {fallback_date}")

    out_lines: list[str] = []
    n_rows = 0
    n_cells_tagged = 0
    bucket_counts = {"fresh": 0, "aging": 0, "stale": 0, "very_stale": 0}
    today = _dt.date.fromisoformat("2026-05-14")

    i = 0
    while i < len(lines):
        line = lines[i]
        tr_m = TR_OPEN_RE.match(line)
        if not tr_m:
            out_lines.append(line)
            i += 1
            continue

        # Found a row. Walk to its closing </tr>, collecting per-line dates.
        row_start = i
        row_lines: list[int] = []
        j = i
        while j < len(lines):
            row_lines.append(j)
            if TR_CLOSE_RE.match(lines[j]):
                break
            j += 1
        else:
            # Unterminated row — pass through unchanged.
            out_lines.append(line)
            i += 1
            continue

        # Compute row-level date = latest blame date across all row lines.
        # blame_dates is 0-indexed (line 1 → index 0).
        row_dates = [
            blame_dates[k]
            for k in row_lines
            if k < len(blame_dates) and blame_dates[k]
        ]
        row_date = latest_date(row_dates) if row_dates else fallback_date

        # Bucket the row by freshness.
        try:
            row_dt = _dt.date.fromisoformat(row_date)
            age_days = (today - row_dt).days
            if age_days < 183:
                bucket_counts["fresh"] += 1
            elif age_days < 365:
                bucket_counts["aging"] += 1
            elif age_days < 730:
                bucket_counts["stale"] += 1
            else:
                bucket_counts["very_stale"] += 1
        except ValueError:
            pass

        # Walk row lines, rewriting <tr> and volatile <td>s.
        for k in row_lines:
            ln = lines[k]
            if k == row_start:
                # Opening <tr> — inject row-level attr.
                ln = inject_attr(ln, row_date)
            else:
                td_m = TD_OPEN_RE.match(ln)
                if td_m:
                    classes = td_m.group(2).split()
                    # Only inject for high-volatility classes.
                    if any(c in VOLATILE_CELL_CLASSES for c in classes):
                        cell_date = (
                            blame_dates[k]
                            if k < len(blame_dates) and blame_dates[k]
                            else row_date
                        )
                        ln = inject_attr(ln, cell_date)
                        n_cells_tagged += 1
            out_lines.append(ln)

        n_rows += 1
        i = j + 1

    new_html = "\n".join(out_lines)

    if args.check:
        # Idempotency check: every data row must carry data-last-verified.
        missing = 0
        for ln in new_html.split("\n"):
            tr_m = TR_OPEN_RE.match(ln)
            if tr_m and "data-last-verified=" not in ln:
                missing += 1
        if missing:
            print(f"check: FAIL — {missing} data rows lack data-last-verified", file=sys.stderr)
            return 1
        print(f"check: PASS — all {n_rows} data rows carry data-last-verified")
        return 0

    print(f"  rows tagged: {n_rows}")
    print(f"  cells tagged: {n_cells_tagged}")
    print(
        "  freshness: "
        f"fresh={bucket_counts['fresh']} "
        f"aging={bucket_counts['aging']} "
        f"stale={bucket_counts['stale']} "
        f"very_stale={bucket_counts['very_stale']}"
    )

    if args.dry_run:
        print("dry-run: not writing output")
        return 0

    out_path.write_text(new_html, encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
