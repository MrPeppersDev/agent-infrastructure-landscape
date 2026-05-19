#!/usr/bin/env python3
"""
apply_audit_pr.py — open a draft PR for an audit run's proposals.

Mirrors `scripts/apply_intake_pr.py`. Reads the staged-updates +
new-rows JSON produced by `scripts/audit_section.py` and:

  1. Applies refresh-last-verified actions in place (the row-level
     `data-last-verified` attribute on the matching <tr>, or the
     per-cell attribute on a volatile <td>).
  2. Stages propose-update deltas as `<!-- audit needs-review -->`
     HTML comments inside the affected <td>. The maintainer reviews
     each one in the PR and either accepts (un-commenting and
     applying the proposed value) or rejects (deleting the comment).
     We never auto-apply a value change — every delta is gated on
     the checkbox in the PR body.
  3. Inserts new-row candidates from expand mode as a stub <tr> in
     the section's tbody, also flagged with an HTML comment.
  4. Runs `make build` + `make validate`, aborts on any failure.
  5. Emits the run-trail markdown to
     `intake-pr-bodies/audit-<section-slug>-<YYYY-MM-DD>.md`.
  6. Branches, commits, optionally pushes + opens a draft PR.

CLI:
  python3 scripts/apply_audit_pr.py --section "Dedicated memory layers" \\
      --mode reverify
  python3 scripts/apply_audit_pr.py --section "Memory benchmarks & evaluation" \\
      --date 2026-05-14 --no-push --no-commit
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_HTML = ROOT / "landscape.html"
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
AUDIT_DIR = ROOT / "audit"
INTAKE_PR_BODIES = ROOT / "intake-pr-bodies"
REPO = "MrPeppersDev/agent-infrastructure-landscape"

# Reuse render.py's row renderer for new-row stubs.
sys.path.insert(0, str(ROOT / "scripts"))
from render import render_row  # noqa: E402
import research_intake as ri  # noqa: E402
from _cell_writer import (  # noqa: E402
    find_record,
    load_landscape,
    save_landscape,
)


def today() -> str:
    return _dt.date.today().isoformat()


def section_slug(section: str) -> str:
    s = section.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:60] or "section"


def html_escape_for_group_label(section: str) -> str:
    """Group-row labels embed `&amp;` for `&`."""
    return section.replace("&", "&amp;")


# ---------------------------------------------------------------------------
# Run helpers
# ---------------------------------------------------------------------------


def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    output = f"$ {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}\n"
    return proc.returncode == 0, output


def run_build() -> tuple[bool, str]:
    return run_cmd(["make", "build"])


def run_validate() -> tuple[bool, str]:
    return run_cmd(["make", "validate"])


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


# ---------------------------------------------------------------------------
# HTML patchers
# ---------------------------------------------------------------------------


def _find_tr_for_record(html: str, record_id: str, name: str) -> tuple[int, int] | None:
    """Locate `<tr ...>...</tr>` containing the record's name cell.

    We use the name cell's value as the anchor because landscape.html
    doesn't carry the record id as an attribute. Returns (start, end)
    or None.

    For records whose name appears in multiple rows (unlikely but
    possible — e.g. cross-listings render once each), the FIRST match
    is returned; the audit script operates per-record-id and the row
    insertion is deterministic, so this is fine for our use.
    """
    # Match name cell. Anchor by `<td class="name">`. Escape regex
    # specials in the name.
    name_for_search = re.escape(name)
    # The <a href="...">{name}</a> shape OR the bare {name} shape.
    name_cell_pattern = re.compile(
        rf'<td class="name">(?:<a[^>]*>)?{name_for_search}(?:</a>)?'
        rf'(?:<span class="cross-listed"[^>]*>[^<]*</span>)?</td>',
    )
    m = name_cell_pattern.search(html)
    if m is None:
        # Try a more permissive variant: name embedded with HTML escapes.
        name_escaped = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if name_escaped != name:
            pattern2 = re.compile(
                rf'<td class="name">(?:<a[^>]*>)?{re.escape(name_escaped)}(?:</a>)?'
                rf'(?:<span class="cross-listed"[^>]*>[^<]*</span>)?</td>',
            )
            m = pattern2.search(html)
        if m is None:
            return None
    # Walk backward to the `<tr ` that contains this match.
    tr_open = html.rfind("<tr ", 0, m.start())
    if tr_open < 0:
        return None
    tr_close = html.find("</tr>", m.end())
    if tr_close < 0:
        return None
    return tr_open, tr_close + len("</tr>")


def patch_row_last_verified(html: str, tr_start: int, tr_end: int, new_date: str) -> str:
    """Set or replace the row-level `data-last-verified="..."` attribute
    on the `<tr ...>` open tag at tr_start."""
    open_close = html.find(">", tr_start)
    if open_close < 0 or open_close > tr_end:
        return html
    open_tag = html[tr_start:open_close + 1]  # includes the closing '>'
    # If the attribute already exists, replace; else append before `>`.
    if 'data-last-verified="' in open_tag:
        new_open = re.sub(
            r'data-last-verified="\d{4}-\d{2}-\d{2}"',
            f'data-last-verified="{new_date}"',
            open_tag, count=1,
        )
    else:
        # Insert before the closing `>`.
        new_open = open_tag[:-1].rstrip() + f' data-last-verified="{new_date}">'
    return html[:tr_start] + new_open + html[open_close + 1:]


def patch_cell_last_verified(
    html: str, tr_start: int, tr_end: int, cell_slug: str, new_date: str,
) -> str:
    """Set or replace `data-last-verified` on the <td class="{cell_slug}">
    inside this row. If the cell is non-volatile the attribute is added
    anyway — the validator only enforces the regex shape when present."""
    tr_chunk = html[tr_start:tr_end]
    # Find <td class="{slug}" ...>  (slug is a token, no spaces).
    td_open_re = re.compile(
        rf'<td class="{re.escape(cell_slug)}"([^>]*)>',
    )
    m = td_open_re.search(tr_chunk)
    if m is None:
        return html
    attr_blob = m.group(1)
    if 'data-last-verified="' in attr_blob:
        new_attr = re.sub(
            r'data-last-verified="\d{4}-\d{2}-\d{2}"',
            f'data-last-verified="{new_date}"',
            attr_blob, count=1,
        )
    else:
        # Append the attribute.
        new_attr = f'{attr_blob} data-last-verified="{new_date}"'
    new_td_open = f'<td class="{cell_slug}"{new_attr}>'
    new_tr_chunk = tr_chunk[:m.start()] + new_td_open + tr_chunk[m.end():]
    return html[:tr_start] + new_tr_chunk + html[tr_end:]


def annotate_cell_needs_review(
    html: str, tr_start: int, tr_end: int, delta: dict,
) -> str:
    """Insert an HTML comment inside the <td class="{slug}"> marking the
    proposed-but-not-applied value for maintainer review. The maintainer
    edits this cell directly in the PR; we don't mutate the value.

    Idempotent: re-running the audit replaces an existing audit comment.
    """
    tr_chunk = html[tr_start:tr_end]
    cell_slug = delta["cell_slug"]
    td_re = re.compile(
        rf'(<td class="{re.escape(cell_slug)}"[^>]*>)(.*?)(</td>)',
        re.DOTALL,
    )
    m = td_re.search(tr_chunk)
    if m is None:
        return html
    open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)
    # Drop a previous audit comment for the same slug.
    body_no_prev = re.sub(
        r'<!-- audit proposal needs-review[^>]*?-->\n?',
        "",
        body,
    )
    proposed_value = (delta.get("proposed_value") or "").replace("-->", "--&gt;")
    source = (delta.get("source_url") or "").replace("-->", "--&gt;")
    comment = (
        f"<!-- audit proposal needs-review "
        f'proposed="{proposed_value[:160]}" '
        f'source="{source[:120]}" -->'
    )
    new_body = f"{comment}\n      {body_no_prev}"
    new_td = f"{open_tag}{new_body}{close_tag}"
    new_tr_chunk = tr_chunk[:m.start()] + new_td + tr_chunk[m.end():]
    return html[:tr_start] + new_tr_chunk + html[tr_end:]


def insert_new_row(html: str, section: str, row_html: str, comment: str) -> str:
    """Append a stub row at the end of the section's tbody chunk."""
    group_pattern = re.compile(
        r'<tr class="group-row"><td colspan="93"[^>]*>'
        + re.escape(html_escape_for_group_label(section))
        + r'</td></tr>'
    )
    m = group_pattern.search(html)
    if m is None:
        raise ValueError(f"section group-row not found for: {section!r}")
    start_after = m.end()
    next_group = re.search(
        r'<tr class="group-row"><td colspan="93"[^>]*>(?!' +
        re.escape(html_escape_for_group_label(section)) + r')',
        html[start_after:],
    )
    tbody_close = html.find("</tbody>", start_after)
    if next_group is not None:
        end_before = start_after + next_group.start()
    else:
        end_before = tbody_close
    if end_before < 0:
        raise ValueError("</tbody> not found after section header")
    section_chunk = html[start_after:end_before]
    last_tr_close = section_chunk.rfind("</tr>")
    if last_tr_close < 0:
        insertion_point = start_after
    else:
        insertion_point = start_after + last_tr_close + len("</tr>")
    inserted = f"\n\n  <!-- {comment} -->\n{row_html}"
    return html[:insertion_point] + inserted + html[insertion_point:]


# ---------------------------------------------------------------------------
# JSON patchers (Path A, issue #68 Stream C)
# ---------------------------------------------------------------------------


def json_set_row_last_verified(record: dict, new_date: str) -> None:
    """Path A equivalent of patch_row_last_verified — set the top-level
    last_verified_at on the record dict."""
    record["last_verified_at"] = new_date


def json_set_cell_last_verified(
    record: dict, cell_slug: str, new_date: str,
) -> None:
    """Path A equivalent of patch_cell_last_verified — stamp
    last_verified_at on the cell, leaving value/status/citation alone."""
    cells = record.setdefault("cells", {})
    cell = cells.get(cell_slug)
    if cell is None:
        # The cell may not have been extracted yet; create a minimal stub
        # so the date doesn't get lost. Subsequent extract.py round-trips
        # will replace this with the rendered cell.
        cells[cell_slug] = {
            "value": None,
            "status": "no-data",
            "last_verified_at": new_date,
        }
        return
    cell["last_verified_at"] = new_date


def json_annotate_cell_needs_review(record: dict, delta: dict) -> None:
    """Path A equivalent of annotate_cell_needs_review.

    Under Path B the audit script writes an HTML comment inside the
    affected <td> so the maintainer reviews/approves the proposal in
    the rendered diff. Under Path A there's no <td> to annotate; we
    encode the same maintainer-gating intent as a per-cell `needs_review`
    object on the JSON cell:

        cell["needs_review"] = {
            "proposed_value": "...",
            "source_url": "...",
        }

    Re-running the audit replaces any prior needs_review block for the
    same cell (idempotent). The actual value/status/citation are NOT
    mutated — the maintainer still has to accept the proposal manually
    by editing the cell. render.py's HTML output is unaffected by the
    needs_review key (it's stripped at render-time).
    """
    cell_slug = delta["cell_slug"]
    cells = record.setdefault("cells", {})
    cell = cells.get(cell_slug)
    if cell is None:
        cell = {"value": None, "status": "no-data"}
        cells[cell_slug] = cell
    cell["needs_review"] = {
        "proposed_value": delta.get("proposed_value", ""),
        "source_url": delta.get("source_url", ""),
    }


def json_insert_new_record(landscape: dict, record: dict) -> None:
    """Append the candidate stub record to landscape['records'].

    Idempotent on `id`: replaces an existing record with the same id
    rather than duplicating. Section/subsection placement is governed
    by render.py's grouping logic, not by JSON insertion order.
    """
    records = landscape.setdefault("records", [])
    rid = record["id"]
    for i, existing in enumerate(records):
        if existing.get("id") == rid:
            records[i] = record
            return
    records.append(record)


# ---------------------------------------------------------------------------
# Stub-record builder (shared between Path A and Path B)
# ---------------------------------------------------------------------------


def candidate_to_stub_record(cand: dict) -> dict:
    """Build a minimum-viable record dict that render.py can serialise.

    The cells are all depth-floor stubs except `desc` (filled from the
    candidate's brief_description if any). This is intentional: the
    full 85-cell research happens at intake time IF the maintainer
    accepts the candidate. Until then the row is clearly a placeholder.
    """
    name = cand["name"]
    url = cand.get("url") or ""
    desc = (cand.get("brief_description") or "").strip()
    # tier=4 below already encodes "candidate / unverified" — no need for an
    # id suffix, which would violate the schema regex (one `--` separator max).
    record_id = ri.make_id(name, url)

    cells: dict[str, dict] = {}
    if desc and url:
        cells["desc"] = ri.cell_real(desc[:1000], url, tier="T2")
    elif desc:
        cells["desc"] = ri.cell_estimate(desc[:1000])
    else:
        cells["desc"] = ri.cell_depth_floor("searched not found", url or "")
    cells["type"] = ri.cell_estimate("Product")

    # Trajectory cells get pre-populated as not-applicable (T3). Otherwise
    # cell_depth_floor would emit T2 (because url is truthy) and the
    # downstream bucket / fetch passes would overwrite the citation to None
    # while update_cell preserves the existing T2 tier — violating gate 5
    # ("T2 requires non-empty http(s) citation").
    for traj_slug in ("citation-trajectory", "commit-trajectory", "download-trajectory"):
        if traj_slug in ri.CELL_COLUMN_SLUGS:
            cells[traj_slug] = ri.cell_not_applicable(
                "candidate row — not yet processed by trajectory pipeline"
            )

    for slug in ri.CELL_COLUMN_SLUGS:
        if slug in cells:
            continue
        cells[slug] = ri.cell_depth_floor("searched not found", url or "")

    record = {
        "id": record_id,
        "name": name,
        "tier": 4,  # candidate / unverified
        "url": url or None,
        "last_verified_at": today(),
        "sections": [{
            "section": cand["section"],
            "subsection": None,
            "primary": True,
            "reason": None,
        }],
        "taxonomy": {
            axis: [{
                "value": "n/a",
                "primary": True,
                # Must start with "n/a" or "not applicable" so render.py picks
                # the no-data-span branch; otherwise extract.py's free-text
                # path reads the first word ("candidate") as the value and
                # gate 2 (determinism) fails on the round-trip.
                "reason": "n/a — candidate row, not yet researched",
            }]
            for axis in ("storage", "retrieval", "persistence", "update",
                         "unit", "governance", "conflict")
        },
        "cells": cells,
    }
    return record


# ---------------------------------------------------------------------------
# Run-trail markdown
# ---------------------------------------------------------------------------


def render_run_trail(
    *,
    section: str,
    mode: str,
    date: str,
    staged_updates: dict | None,
    new_rows: dict | None,
) -> str:
    lines: list[str] = []
    lines.append(f"# Section audit: {section} ({mode}) — {date}")
    lines.append("")
    lines.append(
        f"**Section:** {section}  \n"
        f"**Mode:** {mode}  \n"
        f"**Date:** {date}"
    )
    lines.append("")

    # ---------------- Reverify ----------------
    if staged_updates is not None:
        row_count = staged_updates.get("row_count", 0)
        n_proposals = staged_updates.get("proposal_count", 0)
        n_refresh = staged_updates.get("refresh_only_count", 0)
        lines.append("## Reverify summary")
        lines.append("")
        lines.append(
            f"- Rows audited: **{row_count}**\n"
            f"- Proposed cell updates: **{n_proposals}** (each marked "
            f"`needs-review` — un-checked deltas are NOT applied)\n"
            f"- Refresh-only date bumps: **{n_refresh}**"
        )
        lines.append("")
        if staged_updates.get("no_network"):
            lines.append(
                "_Run in `--no-network` mode: no actual re-research was "
                "performed; every reverify cell received a refresh-only entry._"
            )
            lines.append("")

        # Per-row proposed-update table.
        proposals: list[tuple[str, str, dict]] = []
        for row in staged_updates.get("rows", []):
            for d in row.get("deltas", []):
                if d.get("action") == "propose-update":
                    proposals.append((row["id"], row["name"], d))

        if proposals:
            lines.append("### Proposed cell updates (maintainer-gated)")
            lines.append("")
            lines.append(
                "| Approve | Row | Cell | Current | Proposed | Source |"
            )
            lines.append(
                "|---------|-----|------|---------|----------|--------|"
            )
            for rid, rname, d in proposals:
                cur = _truncate(d.get("current_value", ""), 60)
                prop = _truncate(d.get("proposed_value", ""), 60)
                src = _truncate(d.get("source_url", ""), 50)
                lines.append(
                    f"| [ ] | `{rid}` ({_truncate(rname, 30)}) | "
                    f"`{d['cell_slug']}` | {cur} | {prop} | {src} |"
                )
            lines.append("")
        else:
            lines.append("_No proposed cell updates — every reverified cell "
                         "round-tripped to its existing value._")
            lines.append("")

    # ---------------- Expand ----------------
    if new_rows is not None:
        n = new_rows.get("candidate_count", 0)
        lines.append("## Expand summary")
        lines.append("")
        lines.append(f"- Candidates surfaced: **{n}** (cap: 5)")
        if new_rows.get("query_terms"):
            lines.append(
                "- Search terms: "
                + ", ".join(f"`{q}`" for q in new_rows["query_terms"])
            )
        lines.append("")
        cands = new_rows.get("candidates", [])
        if cands:
            lines.append("### New-row candidates (maintainer-gated)")
            lines.append("")
            lines.append("| Include | Name | URL | Why surfaced |")
            lines.append("|---------|------|-----|--------------|")
            for c in cands:
                lines.append(
                    f"| [ ] | {_truncate(c['name'], 40)} | "
                    f"{_truncate(c.get('url', ''), 60)} | "
                    f"{_truncate(c.get('why_surfaced', ''), 80)} |"
                )
            lines.append("")
        else:
            lines.append("_No candidates surfaced — section appears saturated "
                         "or the search sources returned nothing new._")
            lines.append("")

    # ---------------- Footer ----------------
    lines.append("---")
    lines.append("")
    lines.append(
        "**All delta proposals are marked `needs-review`. Approve each in "
        "this PR by checking the box, then make the corresponding edit in "
        "`landscape.html` (the HTML comments mark each location), and merge. "
        "Unchecked deltas are NOT applied.**"
    )
    lines.append("")
    lines.append(
        "New-row candidates are inserted as stub `<tr>` blocks flagged with "
        "an HTML comment. If you accept a candidate, edit the row to fill in "
        "the cells (or close the PR and let the auto-intake workflow do the "
        "full research pass on a re-submission)."
    )
    lines.append("")
    return "\n".join(lines)


def _truncate(s: str | None, n: int) -> str:
    if not s:
        return ""
    s = str(s).replace("|", "\\|").replace("\n", " ")
    return s if len(s) <= n else s[:n - 1] + "…"


# ---------------------------------------------------------------------------
# Apply staged updates to landscape.html
# ---------------------------------------------------------------------------


def apply_staged_updates_json(
    landscape: dict, staged: dict,
) -> dict:
    """Path A: apply refresh-last-verified actions in place; encode
    propose-update actions as cell-level `needs_review` blocks. Returns
    a stats dict matching the HTML variant's keys for symmetric logging.
    """
    stats = {
        "rows_touched": 0,
        "row_dates_set": 0,
        "cell_dates_set": 0,
        "needs_review_comments": 0,
        "missing_rows": [],
    }
    for row in staged.get("rows", []):
        rid = row["id"]
        rec = find_record(landscape, rid)
        if rec is None:
            stats["missing_rows"].append(rid)
            continue
        stats["rows_touched"] += 1
        for d in row.get("deltas", []):
            action = d.get("action")
            if action == "refresh-row-last-verified":
                json_set_row_last_verified(rec, d["last_verified_at"])
                stats["row_dates_set"] += 1
            elif action == "refresh-last-verified":
                json_set_cell_last_verified(
                    rec, d["cell_slug"], d["last_verified_at"],
                )
                stats["cell_dates_set"] += 1
            elif action == "propose-update":
                json_annotate_cell_needs_review(rec, d)
                stats["needs_review_comments"] += 1
    return stats


def apply_new_rows_json(landscape: dict, payload: dict) -> dict:
    """Path A: insert candidate stub records into landscape['records']."""
    stats: dict = {"inserted": 0, "skipped": []}
    for cand in payload.get("candidates", []):
        try:
            record = candidate_to_stub_record(cand)
        except Exception as exc:  # noqa: BLE001
            stats["skipped"].append(
                f"{cand.get('name')}: candidate_to_stub_record failed: {exc}"
            )
            continue
        try:
            json_insert_new_record(landscape, record)
            stats["inserted"] += 1
        except Exception as exc:  # noqa: BLE001
            stats["skipped"].append(f"{cand.get('name')}: {exc}")
    return stats


def apply_staged_updates(html: str, staged: dict) -> tuple[str, dict]:
    """Apply refresh-last-verified actions in place; insert needs-review
    HTML comments for propose-update actions. Return (new_html, stats)."""
    stats = {
        "rows_touched": 0,
        "row_dates_set": 0,
        "cell_dates_set": 0,
        "needs_review_comments": 0,
        "missing_rows": [],
    }
    for row in staged.get("rows", []):
        rid = row["id"]
        rname = row["name"]
        loc = _find_tr_for_record(html, rid, rname)
        if loc is None:
            stats["missing_rows"].append(rid)
            continue
        tr_start, tr_end = loc
        stats["rows_touched"] += 1
        for d in row.get("deltas", []):
            action = d.get("action")
            if action == "refresh-row-last-verified":
                html = patch_row_last_verified(
                    html, tr_start, tr_end, d["last_verified_at"],
                )
                stats["row_dates_set"] += 1
                # Recompute tr_end because we may have grown the row open tag.
                loc2 = _find_tr_for_record(html, rid, rname)
                if loc2:
                    tr_start, tr_end = loc2
            elif action == "refresh-last-verified":
                html = patch_cell_last_verified(
                    html, tr_start, tr_end, d["cell_slug"], d["last_verified_at"],
                )
                stats["cell_dates_set"] += 1
                loc2 = _find_tr_for_record(html, rid, rname)
                if loc2:
                    tr_start, tr_end = loc2
            elif action == "propose-update":
                html = annotate_cell_needs_review(
                    html, tr_start, tr_end, d,
                )
                stats["needs_review_comments"] += 1
                loc2 = _find_tr_for_record(html, rid, rname)
                if loc2:
                    tr_start, tr_end = loc2
    return html, stats


def apply_new_rows(html: str, payload: dict) -> tuple[str, dict]:
    """Insert candidate stubs as new <tr> rows."""
    stats = {"inserted": 0, "skipped": []}
    section = payload["section"]
    audit_date = payload.get("date", today())
    for cand in payload.get("candidates", []):
        record = candidate_to_stub_record(cand)
        try:
            row_html = render_row(record)
        except Exception as exc:  # noqa: BLE001
            stats["skipped"].append(f"{cand.get('name')}: render failed: {exc}")
            continue
        comment = (
            f"candidate row from audit {audit_date} — "
            f"needs-review; full research happens at intake if accepted"
        )
        try:
            html = insert_new_row(html, section, row_html, comment)
            stats["inserted"] += 1
        except ValueError as exc:
            stats["skipped"].append(f"{cand.get('name')}: {exc}")
    return html, stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--section", required=True)
    ap.add_argument(
        "--mode",
        choices=["reverify", "expand", "full"],
        default="full",
    )
    ap.add_argument("--date", default=None,
                    help="Audit date (default: today)")
    ap.add_argument("--no-push", action="store_true",
                    help="Skip git push and PR creation")
    ap.add_argument("--no-commit", action="store_true",
                    help="Skip branch/commit; only patch + validate")
    ap.add_argument(
        "--target",
        choices=["landscape.json", "landscape.html"],
        default="landscape.json",
        help=(
            "Where to apply audit actions. Default (Path A, refs #68) is "
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

    date_str = args.date or today()
    slug = section_slug(args.section)

    staged_path = AUDIT_DIR / f"staged-updates-{slug}-{date_str}.json"
    new_rows_path = AUDIT_DIR / f"new-rows-{slug}-{date_str}.json"

    staged_updates: dict | None = None
    new_rows: dict | None = None

    if args.mode in ("reverify", "full"):
        if not staged_path.exists():
            print(f"error: {staged_path} not found — "
                  f"run audit_section.py first", file=sys.stderr)
            return 1
        staged_updates = json.loads(staged_path.read_text())

    if args.mode in ("expand", "full"):
        if not new_rows_path.exists():
            print(f"error: {new_rows_path} not found — "
                  f"run audit_section.py first", file=sys.stderr)
            return 1
        new_rows = json.loads(new_rows_path.read_text())

    # ---- Apply audit actions to landscape.{json,html} ----
    stats_reverify: dict = {}
    stats_expand: dict = {}

    if target_json:
        if not LANDSCAPE_JSON.exists():
            print(f"error: {LANDSCAPE_JSON} not found", file=sys.stderr)
            return 2
        landscape = load_landscape(LANDSCAPE_JSON)
        # Snapshot for change-detection so we don't rewrite the file when
        # nothing changed (keeps `git diff` clean on no-op runs).
        original_dump = json.dumps(landscape, sort_keys=True)
        if staged_updates is not None:
            stats_reverify = apply_staged_updates_json(landscape, staged_updates)
        if new_rows is not None:
            stats_expand = apply_new_rows_json(landscape, new_rows)
        new_dump = json.dumps(landscape, sort_keys=True)
        if new_dump != original_dump:
            save_landscape(landscape, LANDSCAPE_JSON)
            print(f"patched {LANDSCAPE_JSON.name}")
        else:
            print(f"note: no {LANDSCAPE_JSON.name} patches applied (nothing actionable to write)")
    else:
        html_text = LANDSCAPE_HTML.read_text()
        original = html_text
        if staged_updates is not None:
            html_text, stats_reverify = apply_staged_updates(html_text, staged_updates)
        if new_rows is not None:
            html_text, stats_expand = apply_new_rows(html_text, new_rows)
        if html_text != original:
            LANDSCAPE_HTML.write_text(html_text)
            print(f"patched landscape.html")
        else:
            print("note: no HTML patches applied (nothing actionable to write)")

    if stats_reverify:
        print(f"  reverify: rows_touched={stats_reverify['rows_touched']}, "
              f"row_dates_set={stats_reverify['row_dates_set']}, "
              f"cell_dates_set={stats_reverify['cell_dates_set']}, "
              f"needs_review_comments={stats_reverify['needs_review_comments']}")
        if stats_reverify.get("missing_rows"):
            print(f"  reverify: WARNING missing_rows={stats_reverify['missing_rows']}")
    if stats_expand:
        print(f"  expand: inserted={stats_expand['inserted']}, "
              f"skipped={len(stats_expand.get('skipped', []))}")
        for sk in stats_expand.get("skipped", []):
            print(f"    - {sk}")

    # ---- build + validate ----
    build_ok, build_out = run_build()
    if not build_ok:
        log_path = AUDIT_DIR / f"build-fail-{slug}-{date_str}.log"
        log_path.write_text(build_out)
        print(f"error: `make build` failed — see {log_path}", file=sys.stderr)
        # Revert HTML so the working tree is clean.
        subprocess.run(
            ["git", "checkout", "--",
             str(LANDSCAPE_HTML), "data/landscape.json", "data/landscape.edges.json"],
            cwd=str(ROOT),
        )
        return 4

    validate_ok, validate_out = run_validate()
    if not validate_ok:
        log_path = AUDIT_DIR / f"validate-fail-{slug}-{date_str}.log"
        log_path.write_text(validate_out)
        print(f"error: `make validate` failed — see {log_path}", file=sys.stderr)
        return 5
    print("validate: 5/5 gates pass")

    # ---- Run-trail markdown ----
    INTAKE_PR_BODIES.mkdir(parents=True, exist_ok=True)
    body = render_run_trail(
        section=args.section,
        mode=args.mode,
        date=date_str,
        staged_updates=staged_updates,
        new_rows=new_rows,
    )
    body_path = INTAKE_PR_BODIES / f"audit-{slug}-{date_str}.md"
    body_path.write_text(body)
    print(f"wrote run trail to {body_path}")

    if args.no_commit:
        print("--no-commit set; stopping after build + validate + run trail.")
        return 0

    # ---- Branch + commit ----
    branch = f"audit/{slug}-{date_str}"
    if current_branch() != branch:
        if branch_exists(branch):
            subprocess.run(["git", "checkout", branch], check=True, cwd=str(ROOT))
        else:
            subprocess.run(
                ["git", "checkout", "-b", branch], check=True, cwd=str(ROOT),
            )

    stage_files = [
        str(LANDSCAPE_HTML),
        "data/landscape.json",
        "data/landscape.edges.json",
        str(staged_path) if staged_path.exists() else "",
        str(new_rows_path) if new_rows_path.exists() else "",
        str(AUDIT_DIR / "section-rotation.json"),
        str(body_path),
    ]
    for sf in stage_files:
        if not sf:
            continue
        subprocess.run(["git", "add", sf], cwd=str(ROOT))

    diff_check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=str(ROOT),
    )
    if diff_check.returncode == 0:
        print("no staged changes; nothing to commit")
        return 0

    commit_msg = f"Section audit: {args.section} ({args.mode}) (audit {date_str})"
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
         "--title", f"Section audit: {args.section} ({args.mode}) — {date_str}",
         "--body-file", str(body_path)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if pr_proc.returncode != 0:
        print(f"warn: `gh pr create` failed:\n{pr_proc.stderr}",
              file=sys.stderr)
        return 7
    print(f"opened draft PR: {pr_proc.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
