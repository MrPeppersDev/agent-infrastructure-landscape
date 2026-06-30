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
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
INTAKE_FAILURES = ROOT / "intake-failures"
INTAKE_PR_BODIES = ROOT / "intake-pr-bodies"
REPO = "MrPeppersDev/agent-infrastructure-landscape"

# Phase 2 / Gate 1 cell slugs (issues #95 / #101). Mirrored from
# scripts/research_intake.py PHASE_2_CELL_SLUGS; duplicated here so
# apply_intake_pr.py has no cross-module dependency for a runtime path.
PHASE_2_CELL_SLUGS: tuple[str, ...] = (
    "cost-input-usd-per-mtok",
    "cost-output-usd-per-mtok",
    "cost-tier",
    "cost-pricing-model",
    "cost-last-verified",
    "capability-composite-score",
    "capability-band",
    "capability-benchmark-sources",
    "capability-last-verified",
    "use-case-tags",
    "use-case-anti-tags",
)

# Label applied to PRs that have any Phase 2 cell at
# `source: llm, verified: false`. Created (if missing) before the PR is
# opened so `gh pr create --label` succeeds.
PENDING_REVIEW_LABEL = "phase-2-cells-pending-review"


def _write_failure_log(name: str, msg: str) -> None:
    """Write a failure log under INTAKE_FAILURES, creating the dir if needed.

    Defensive against early-return paths that fire before the upfront
    mkdir in main(): each write ensures the parent directory exists, so
    no caller can hit FileNotFoundError regardless of control flow.
    """
    INTAKE_FAILURES.mkdir(parents=True, exist_ok=True)
    (INTAKE_FAILURES / name).write_text(msg)

# Import render.py's row rendering. We add `scripts/` to sys.path so the
# import works regardless of where the script is invoked from.
sys.path.insert(0, str(ROOT / "scripts"))
from render import render_row  # noqa: E402
from _cell_writer import load_landscape, save_landscape  # noqa: E402


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
# JSON record insert (Path A, issue #68 Stream C)
# ---------------------------------------------------------------------------


def insert_record_json(landscape: dict, record: dict) -> dict:
    """Append `record` to `landscape['records']`, replacing any existing
    record with the same id (idempotent re-run safety).

    Path A equivalent of insert_row(): instead of stitching HTML into
    landscape.html, we mutate the JSON record list. render.py's next
    `make build` regenerates landscape.html from this list, so row
    placement within a section is governed by render.py's section/
    subsection grouping rather than by HTML insertion order.

    Phase 2 / Gate 1 (issues #95 / #101): if the record carries a
    `_provenance` dict from research_intake.py, it is splice-written
    onto the row alongside `cells`. Pre-Phase-2 cells the bot did not
    touch are filled in with the canonical `legacy` source — preserving
    the on-disk shape established by the Gate 1 backfill.
    """
    records = landscape.setdefault("records", [])
    rid = record["id"]
    # Ensure record["_provenance"] is set for every populated cell:
    # cells the bot wrote already have an entry (from research_intake.py),
    # and we backfill `legacy` for anything else with a value.
    incoming_prov = dict(record.get("_provenance") or {})
    for slug, cell in (record.get("cells") or {}).items():
        if slug in incoming_prov:
            continue
        value = (cell or {}).get("value")
        if value:
            incoming_prov[slug] = {"source": "legacy", "verified": True}
    record["_provenance"] = incoming_prov

    for i, existing in enumerate(records):
        if existing.get("id") == rid:
            records[i] = record
            return landscape
    records.append(record)
    return landscape


def has_pending_phase_2_review(record: dict) -> bool:
    """Return True iff any Phase 2 cell on `record` is
    `source: llm, verified: false`. Used to decide whether to apply
    the `phase-2-cells-pending-review` PR label.
    """
    prov = record.get("_provenance") or {}
    for slug in PHASE_2_CELL_SLUGS:
        entry = prov.get(slug) or {}
        if entry.get("source") == "llm" and entry.get("verified") is False:
            return True
    return False


def summarise_phase_2_provenance(record: dict) -> list[tuple[str, str, bool]]:
    """Return a list of (slug, source, verified) tuples for every
    populated Phase 2 cell on `record`. Drives the "Provenance summary"
    table in the PR body.
    """
    out: list[tuple[str, str, bool]] = []
    prov = record.get("_provenance") or {}
    cells = record.get("cells") or {}
    for slug in PHASE_2_CELL_SLUGS:
        cell = cells.get(slug) or {}
        if not cell.get("value"):
            continue
        entry = prov.get(slug) or {}
        out.append((
            slug,
            entry.get("source", "?"),
            bool(entry.get("verified", False)),
        ))
    return out


def ensure_phase_2_pending_label() -> None:
    """Create the `phase-2-cells-pending-review` label if missing.
    `gh label create` is idempotent enough — it returns non-zero when
    the label already exists, which we tolerate.
    """
    subprocess.run(
        ["gh", "label", "create", PENDING_REVIEW_LABEL,
         "--repo", REPO,
         "--description",
         "Intake PR with at least one Phase 2 cell at source=llm verified=false. Review those before merge.",
         "--color", "C5DEF5",
         "--force"],
        capture_output=True, text=True, cwd=str(ROOT),
    )


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

    # Phase 2 / Gate 1 (issues #95 / #101) — provenance summary.
    # Primes the maintainer to focus on the LLM-unverified cells.
    phase_2 = summarise_phase_2_provenance(record)
    if phase_2:
        lines.append("")
        lines.append("## Provenance summary (Phase 2)")
        lines.append("")
        lines.append(
            "Every populated Phase 2 cell with its provenance source / "
            "verification status. **Focus review on the rows where "
            "`source = llm` and `verified = false`** — those are the "
            "bot's guesses awaiting curator confirmation."
        )
        lines.append("")
        lines.append("| Cell | Source | Verified |")
        lines.append("|------|--------|----------|")
        unverified_llm: list[str] = []
        for slug, source, verified in phase_2:
            mark = "yes" if verified else "**NO**"
            lines.append(f"| `{slug}` | `{source}` | {mark} |")
            if source == "llm" and not verified:
                unverified_llm.append(slug)
        lines.append("")
        if unverified_llm:
            lines.append(
                f"_{len(unverified_llm)} cell(s) flagged "
                f"`source: llm, verified: false` — PR carries label "
                f"`{PENDING_REVIEW_LABEL}`._"
            )
            lines.append("")

    lines.append("## Maintainer checklist")
    lines.append("")
    lines.append("- [ ] Tier assignment is correct (T1 fields auto-verifiable; T2 fields cited; T3 fields flagged estimate)")
    lines.append("- [ ] Section assignment is correct")
    lines.append("- [ ] No factual errors in claim cells (desc, claims)")
    lines.append("- [ ] No duplicate of an existing row")
    lines.append("- [ ] All citation URLs resolve")
    lines.append("- [ ] `make validate` passes (6/6 gates)")
    lines.append("- [ ] Taxonomy axes filled (auto-research left them as `n/a`)")
    if phase_2:
        lines.append("- [ ] Phase 2 cells: scrape/human-sourced rows are accurate; LLM-unverified cells either confirmed (flip provenance to `verified: true`) or corrected")
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
                    help="skip the branch/commit; just patch landscape and validate")
    ap.add_argument(
        "--target",
        choices=["landscape.json", "landscape.html"],
        default="landscape.json",
        help=(
            "Where to write the new row. Default (Path A, refs #68) is "
            "data/landscape.json; landscape.html remains as a deprecated "
            "legacy path during the transition window."
        ),
    )
    args = ap.parse_args()

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

    # 1. Insert row. Path A writes the record dict into landscape.json;
    # the legacy HTML path renders a <tr> and stitches it into the
    # section's tbody.
    section = record["sections"][0]["section"]

    INTAKE_FAILURES.mkdir(parents=True, exist_ok=True)
    INTAKE_PR_BODIES.mkdir(parents=True, exist_ok=True)

    if target_json:
        if not LANDSCAPE_JSON.exists():
            msg = f"landscape.json not found at {LANDSCAPE_JSON}"
            print(f"error: {msg}", file=sys.stderr)
            _write_failure_log(f"{args.issue_number}-insert.log", msg)
            return 3
        landscape = load_landscape(LANDSCAPE_JSON)
        try:
            insert_record_json(landscape, record)
        except (KeyError, ValueError) as exc:
            msg = f"record insertion failed: {exc}"
            print(f"error: {msg}", file=sys.stderr)
            _write_failure_log(f"{args.issue_number}-insert.log", msg)
            return 3
        save_landscape(landscape, LANDSCAPE_JSON)
        print(f"inserted record id=`{record['id']}` into section `{section}` "
              f"(target: {LANDSCAPE_JSON.name})")
    else:
        row_html = render_row(record)
        html_text = LANDSCAPE_HTML.read_text()
        try:
            new_html = insert_row(html_text, section, row_html)
        except ValueError as exc:
            msg = f"row insertion failed: {exc}"
            print(f"error: {msg}", file=sys.stderr)
            _write_failure_log(f"{args.issue_number}-insert.log", msg)
            return 3
        LANDSCAPE_HTML.write_text(new_html)
        print(f"inserted row into section `{section}` (target: landscape.html)")

    # 2. Run build.
    build_ok, build_out = run_build()
    if not build_ok:
        log_path = INTAKE_FAILURES / f"{args.issue_number}-build.log"
        _write_failure_log(log_path.name, build_out)
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
        _write_failure_log(log_path.name, validate_out)
        print(f"error: `make validate` failed — see {log_path}", file=sys.stderr)
        # Don't revert here — leave the diff for the developer to inspect.
        return 5
    print("validate: 6/6 gates pass")

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

    # Phase 2: if any Phase 2 cell is `source: llm, verified: false`,
    # apply the `phase-2-cells-pending-review` label. Ensure the label
    # exists first — `gh pr create --label` fails hard if the label is
    # missing.
    pr_labels: list[str] = []
    if has_pending_phase_2_review(record):
        ensure_phase_2_pending_label()
        pr_labels.append(PENDING_REVIEW_LABEL)

    pr_cmd = [
        "gh", "pr", "create",
        "--draft",
        "--base", "main",
        "--head", branch,
        "--title", f"Auto-research intake: {record['name']} (refs #{args.issue_number})",
        "--body-file", str(body_path),
    ]
    for label in pr_labels:
        pr_cmd.extend(["--label", label])
    pr_proc = subprocess.run(
        pr_cmd, capture_output=True, text=True, cwd=str(ROOT),
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
