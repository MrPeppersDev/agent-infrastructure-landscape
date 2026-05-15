#!/usr/bin/env python3
"""
apply_intake_pr.py — open a draft PR for an auto-researched intake row.

Reads a record JSON (output of scripts/research_intake.py) and:
  1. Inserts a new <tr> block into landscape.html at the target section
     (using scripts/render.py's row template so the row markup matches
     the rest of the catalog).
  2. Runs `make build` to regenerate data/landscape.json + landscape.edges.json.
  3. Runs `make validate` — aborts if any of the 5 gates fail.
  4. Emits the run-trail markdown to intake-pr-bodies/<issue-number>.md.
  5. Stages specific files (landscape.html + data/ + docs/), commits to a
     new branch, and opens a draft PR via `gh pr create`.
  6. Comments on the originating Issue with the PR link.

The caller is the auto-intake GHA workflow. Local invocations are
supported for development; pass --no-push and --no-comment to skip the
remote side effects.

CLI:
  python3 scripts/apply_intake_pr.py --record /tmp/record.json \\
      --issue-number 999
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_HTML = ROOT / "landscape.html"
INTAKE_FAILURES = ROOT / "intake-failures"
INTAKE_PR_BODIES = ROOT / "intake-pr-bodies"
REPO = "MrPeppersDev/memory-analysis-program"

# Import render.py's row rendering. We add `scripts/` to sys.path so the
# import works regardless of where the script is invoked from.
sys.path.insert(0, str(ROOT / "scripts"))
from render import render_row  # noqa: E402


def html_escape_for_group_label(section: str) -> str:
    """Group-row labels embed `&amp;` for `&` (matches process_intake.py)."""
    return section.replace("&", "&amp;")


# ---------------------------------------------------------------------------
# Row insertion (same algorithm as process_intake.py.insert_row)
# ---------------------------------------------------------------------------


def insert_row(html_text: str, section: str, row_html: str) -> str:
    """Append `row_html` to the section's tbody before the next section."""
    group_pattern = re.compile(
        r'<tr class="group-row"><td colspan="93"[^>]*>'
        + re.escape(html_escape_for_group_label(section))
        + r'</td></tr>'
    )
    m = group_pattern.search(html_text)
    if m is None:
        raise ValueError(f"section group-row not found for: {section!r}")
    start_after = m.end()

    # Find the next group-row (any non-matching section) or </tbody>.
    next_group = re.search(
        r'<tr class="group-row"><td colspan="93"[^>]*>(?!' +
        re.escape(html_escape_for_group_label(section)) + r')',
        html_text[start_after:],
    )
    tbody_close = html_text.find("</tbody>", start_after)
    if next_group is not None:
        end_before = start_after + next_group.start()
    else:
        end_before = tbody_close
    if end_before < 0:
        raise ValueError("</tbody> not found after section header")

    section_chunk = html_text[start_after:end_before]
    last_tr_close = section_chunk.rfind("</tr>")
    if last_tr_close < 0:
        insertion_point = start_after
    else:
        insertion_point = start_after + last_tr_close + len("</tr>")

    inserted = "\n\n" + row_html
    return html_text[:insertion_point] + inserted + html_text[insertion_point:]


# ---------------------------------------------------------------------------
# Build + validate
# ---------------------------------------------------------------------------


def run_cmd(cmd: list[str], *, label: str) -> tuple[bool, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    output = f"$ {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}\n"
    return proc.returncode == 0, output


def run_build() -> tuple[bool, str]:
    return run_cmd(["make", "build"], label="make build")


def run_validate() -> tuple[bool, str]:
    return run_cmd(["make", "validate"], label="make validate")


# ---------------------------------------------------------------------------
# Run-trail markdown
# ---------------------------------------------------------------------------


def render_run_trail(
    record: dict,
    source_map: dict,
    issue_number: int,
) -> str:
    """Generate the PR body markdown."""
    lines: list[str] = []
    name = record["name"]
    section = record["sections"][0]["section"]
    subsection = record["sections"][0].get("subsection") or ""

    lines.append(f"# Auto-researched intake from #{issue_number}: {name}")
    lines.append("")
    lines.append(f"**Section:** {section}")
    if subsection:
        lines.append(f"**Subsection:** {subsection}")
    lines.append(f"**Row tier (1-5):** {record['tier']}")
    lines.append(f"**Record id:** `{record['id']}`")
    if record.get("url"):
        lines.append(f"**Primary URL:** {record['url']}")
    lines.append("")
    lines.append("## Run trail")
    lines.append("")
    lines.append("| Column | Status | Tier | Source |")
    lines.append("|--------|--------|------|--------|")

    cells = record.get("cells", {})
    for slug, cell in cells.items():
        status = cell.get("status", "")
        tier = cell.get("tier", "")
        source = source_map.get(slug, "")
        # Trim long source URLs for the table.
        if isinstance(source, str) and len(source) > 80:
            source_display = source[:77] + "..."
        else:
            source_display = source
        lines.append(f"| `{slug}` | {status} | {tier} | {source_display} |")

    lines.append("")
    lines.append("## Maintainer checklist")
    lines.append("")
    lines.append("- [ ] Tier assignment is correct (T1 fields auto-verifiable; T2 fields cited; T3 fields flagged estimate)")
    lines.append("- [ ] Section assignment is correct")
    lines.append("- [ ] No factual errors in claim cells (desc, claims)")
    lines.append("- [ ] No duplicate of an existing row")
    lines.append("- [ ] All citation URLs resolve")
    lines.append("- [ ] `make validate` passes (5/5 gates)")
    lines.append("- [ ] Taxonomy axes filled (auto-research left them as `n/a`)")
    lines.append("")
    lines.append(f"Closes #{issue_number}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Branch / commit / PR
# ---------------------------------------------------------------------------


def slugify_for_branch(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:40] or "intake"


def current_branch() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return proc.stdout.strip()


def branch_exists(name: str) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", name],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return proc.returncode == 0


def comment_on_issue(number: int, body: str) -> None:
    subprocess.run(
        ["gh", "issue", "comment", str(number), "--repo", REPO, "--body", body],
        check=False, cwd=str(ROOT),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--record", required=True,
                    help="JSON record file from research_intake.py")
    ap.add_argument("--issue-number", type=int, required=True,
                    help="originating intake Issue number")
    ap.add_argument("--source-map", default=None,
                    help="JSON source map (default: <record>.sources.json)")
    ap.add_argument("--branch-name", default=None,
                    help="explicit branch name (default: intake/N-slug)")
    ap.add_argument("--no-push", action="store_true",
                    help="skip git push and PR creation (useful for local tests)")
    ap.add_argument("--no-comment", action="store_true",
                    help="skip the Issue comment with the PR link")
    ap.add_argument("--no-commit", action="store_true",
                    help="skip the branch/commit; just patch landscape.html and validate")
    args = ap.parse_args()

    record_path = Path(args.record)
    if not record_path.exists():
        print(f"error: record file not found: {record_path}", file=sys.stderr)
        return 1
    record = json.loads(record_path.read_text())

    source_map_path = Path(args.source_map) if args.source_map else \
        record_path.with_suffix(record_path.suffix + ".sources.json")
    if source_map_path.exists():
        source_map = json.loads(source_map_path.read_text())
    else:
        print(f"warn: source map not found at {source_map_path}; "
              "run trail will be sparse", file=sys.stderr)
        source_map = {}

    # 1. Insert row into landscape.html.
    section = record["sections"][0]["section"]
    row_html = render_row(record)

    INTAKE_FAILURES.mkdir(parents=True, exist_ok=True)
    INTAKE_PR_BODIES.mkdir(parents=True, exist_ok=True)

    html_text = LANDSCAPE_HTML.read_text()
    try:
        new_html = insert_row(html_text, section, row_html)
    except ValueError as exc:
        msg = f"row insertion failed: {exc}"
        print(f"error: {msg}", file=sys.stderr)
        (INTAKE_FAILURES / f"{args.issue_number}-insert.log").write_text(msg)
        return 3
    LANDSCAPE_HTML.write_text(new_html)
    print(f"inserted row into section `{section}`")

    # 2. Run build.
    build_ok, build_out = run_build()
    if not build_ok:
        log_path = INTAKE_FAILURES / f"{args.issue_number}-build.log"
        log_path.write_text(build_out)
        print(f"error: `make build` failed — see {log_path}", file=sys.stderr)
        subprocess.run(
            ["git", "checkout", "--",
             str(LANDSCAPE_HTML), "data/landscape.json", "data/landscape.edges.json"],
            cwd=str(ROOT),
        )
        return 4

    # 3. Run validate.
    validate_ok, validate_out = run_validate()
    if not validate_ok:
        log_path = INTAKE_FAILURES / f"{args.issue_number}-validate.log"
        log_path.write_text(validate_out)
        print(f"error: `make validate` failed — see {log_path}", file=sys.stderr)
        # Don't revert here — leave the diff for the developer to inspect.
        return 5
    print("validate: 5/5 gates pass")

    # 4. Emit run-trail markdown.
    body = render_run_trail(record, source_map, args.issue_number)
    body_path = INTAKE_PR_BODIES / f"{args.issue_number}.md"
    body_path.write_text(body)
    print(f"wrote run trail to {body_path}")

    if args.no_commit:
        print("--no-commit set; stopping after build + validate.")
        return 0

    # 5. Branch + commit.
    branch = args.branch_name or \
        f"intake/{args.issue_number}-{slugify_for_branch(record['name'])}"

    # If we're on the target branch already, skip create.
    if current_branch() != branch:
        if branch_exists(branch):
            subprocess.run(["git", "checkout", branch], check=True, cwd=str(ROOT))
        else:
            subprocess.run(
                ["git", "checkout", "-b", branch], check=True, cwd=str(ROOT),
            )

    # Stage specific files. NEVER `git add .`.
    stage_files = [
        str(LANDSCAPE_HTML),
        "data/landscape.json",
        "data/landscape.edges.json",
    ]
    for sf in stage_files:
        subprocess.run(["git", "add", sf], check=True, cwd=str(ROOT))

    # Commit (only if there are staged changes — empty commit would noise the log).
    diff_check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=str(ROOT),
    )
    if diff_check.returncode == 0:
        print("no staged changes; nothing to commit")
        return 0

    commit_msg = (
        f"Auto-research intake: {record['name']} (refs #{args.issue_number})"
    )
    subprocess.run(
        ["git", "commit", "-m", commit_msg], check=True, cwd=str(ROOT),
    )
    commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=str(ROOT),
    ).stdout.strip()
    print(f"committed: {commit_sha} on branch {branch}")

    if args.no_push:
        print("--no-push set; stopping before push/PR.")
        return 0

    # 6. Push + open draft PR.
    push_proc = subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=str(ROOT),
    )
    if push_proc.returncode != 0:
        print(f"warn: push failed (code {push_proc.returncode}); PR not opened.",
              file=sys.stderr)
        return 6

    pr_proc = subprocess.run(
        ["gh", "pr", "create",
         "--draft",
         "--base", "main",
         "--head", branch,
         "--title", f"Auto-research intake: {record['name']} (refs #{args.issue_number})",
         "--body-file", str(body_path)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if pr_proc.returncode != 0:
        print(f"warn: `gh pr create` failed:\n{pr_proc.stderr}",
              file=sys.stderr)
        return 7
    pr_url = pr_proc.stdout.strip()
    print(f"opened draft PR: {pr_url}")

    # 7. Comment on the originating Issue.
    if not args.no_comment:
        comment_on_issue(
            args.issue_number,
            f"Auto-research complete — draft PR opened: {pr_url}\n\n"
            f"Maintainer review pending. The run-trail markdown is in the "
            f"PR body; checklist items track per-cell tier/source assignments.",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
