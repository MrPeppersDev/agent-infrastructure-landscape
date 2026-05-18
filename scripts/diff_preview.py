#!/usr/bin/env python3
"""
diff_preview.py — render a markdown PR-comment preview of a JSON cell diff.

Reads two `data/landscape.json` snapshots (base and head) and emits a
markdown file describing what cells/records changed, with the full row
rendered for each touched record via `render.py`'s `render_row()`.
Changed cells are highlighted inside each rendered row.

Optionally compares `data/landscape.edges.json` and emits a table
section of added/removed/changed edges.

CLI (per docs/design-rendered-diff-preview.md §Implementation):

  diff_preview.py --base PATH --head PATH \
      [--edges-base PATH --edges-head PATH] --output FILE

Failure modes (per design doc §Failure modes):
  - per-cell render errors degrade to `<error rendering cell: {exc}>`
  - top-level JSON-parse errors write an error comment and exit 0

Open questions still open (per design doc):
  - Q2: should edge-endpoint records get full row renders? Default no.
  - Q3: bot-vs-human styling. Not surfaced here.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

# Make `render` importable when invoked from anywhere.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from render import (  # noqa: E402
    CELL_COLUMN_SLUGS,
    TAXONOMY_AXES,
    render_cell,
    render_row,
    render_taxonomy_cell,
)

MARKER = "<!-- diff-preview-bot -->"

# Truncation caps per design doc §Truncation.
MAX_RECORDS = 20
MAX_CELLS = 40
PER_CELL_CHAR_CAP = 2000
PER_CELL_HEAD_TAIL = 500

# Cell-level diff fields we treat as "real" changes.
CELL_DIFF_FIELDS = ("value", "status", "citation")
REFRESH_FIELD = "last_verified_at"


# ---------------------------------------------------------------------------
# Loading.
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    with open(path) as fh:
        return json.load(fh)


def _records_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in payload.get("records", [])}


# ---------------------------------------------------------------------------
# Per-record / per-cell diff.
# ---------------------------------------------------------------------------


def _cell_changes(
    base_cells: dict[str, Any], head_cells: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (substantive_changes, refresh_only_changes)."""
    substantive: list[dict[str, Any]] = []
    refresh_only: list[dict[str, Any]] = []
    slugs = set(base_cells) | set(head_cells)
    for slug in slugs:
        b = base_cells.get(slug)
        h = head_cells.get(slug)
        if b == h:
            continue
        b = b or {}
        h = h or {}
        substantive_delta = any(b.get(f) != h.get(f) for f in CELL_DIFF_FIELDS)
        refresh_delta = b.get(REFRESH_FIELD) != h.get(REFRESH_FIELD)
        if substantive_delta:
            substantive.append(
                {"slug": slug, "kind": "changed", "before": b, "after": h}
            )
        elif refresh_delta:
            refresh_only.append(
                {"slug": slug, "kind": "refreshed", "before": b, "after": h}
            )
    order = {s: i for i, s in enumerate(CELL_COLUMN_SLUGS)}
    substantive.sort(key=lambda c: (order.get(c["slug"], 10_000), c["slug"]))
    refresh_only.sort(key=lambda c: (order.get(c["slug"], 10_000), c["slug"]))
    return substantive, refresh_only


def _taxonomy_changes(
    base_tax: dict[str, Any], head_tax: dict[str, Any]
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for axis in TAXONOMY_AXES:
        b = base_tax.get(axis) or []
        h = head_tax.get(axis) or []
        if b != h:
            b_vals = {e.get("value") for e in b}
            h_vals = {e.get("value") for e in h}
            changes.append(
                {
                    "axis": axis,
                    "added": sorted(v for v in (h_vals - b_vals) if v is not None),
                    "removed": sorted(v for v in (b_vals - h_vals) if v is not None),
                    "before": b,
                    "after": h,
                }
            )
    return changes


def _record_section_changed(
    base_rec: dict[str, Any], head_rec: dict[str, Any]
) -> bool:
    return base_rec.get("sections") != head_rec.get("sections")


def _diff_records(
    base: dict[str, dict[str, Any]], head: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    added_ids = sorted(set(head) - set(base))
    removed_ids = sorted(set(base) - set(head))
    common = sorted(set(base) & set(head))

    changed: list[dict[str, Any]] = []
    refreshed_only: list[dict[str, Any]] = []
    for rid in common:
        b = base[rid]
        h = head[rid]
        cell_changes, refresh_changes = _cell_changes(
            b.get("cells", {}), h.get("cells", {})
        )
        tax_changes = _taxonomy_changes(
            b.get("taxonomy", {}), h.get("taxonomy", {})
        )
        section_changed = _record_section_changed(b, h)
        substantive = bool(cell_changes) or bool(tax_changes) or section_changed
        if substantive:
            changed.append(
                {
                    "id": rid,
                    "base": b,
                    "head": h,
                    "cell_changes": cell_changes,
                    "refresh_changes": refresh_changes,
                    "tax_changes": tax_changes,
                    "section_changed": section_changed,
                }
            )
        elif refresh_changes:
            refreshed_only.append(
                {
                    "id": rid,
                    "base": b,
                    "head": h,
                    "refresh_changes": refresh_changes,
                }
            )
    return {
        "added": added_ids,
        "removed": removed_ids,
        "changed": changed,
        "refreshed_only": refreshed_only,
        "base": base,
        "head": head,
    }


# ---------------------------------------------------------------------------
# Markdown rendering.
# ---------------------------------------------------------------------------


def _section_label(record: dict[str, Any]) -> str:
    for s in record.get("sections", []):
        if s.get("primary"):
            sub = s.get("subsection")
            sec = s.get("section", "")
            return f"{sec} / {sub}" if sub else sec
    return "(no section)"


def _truncate_rendered(html: str) -> str:
    if len(html) <= PER_CELL_CHAR_CAP:
        return html
    return (
        html[:PER_CELL_HEAD_TAIL]
        + f"\n… [truncated {len(html) - 2 * PER_CELL_HEAD_TAIL} chars] …\n"
        + html[-PER_CELL_HEAD_TAIL:]
    )


# Per-row cap is higher than per-cell because a full row legitimately has
# 85+ cells. We use a line-aware truncation that always preserves lines
# tagged with the visible 🔸 marker (per the highlight scheme), plus the
# <tr> header and </tr> footer.
PER_ROW_CHAR_CAP = 8000
HIGHLIGHT_MARK = "🔸"


def _truncate_row(rendered: str) -> str:
    if len(rendered) <= PER_ROW_CHAR_CAP:
        return rendered
    lines = rendered.split("\n")
    kept: list[str] = []
    skipped = 0
    n = len(lines)
    for i, line in enumerate(lines):
        keep = i == 0 or i == n - 1 or HIGHLIGHT_MARK in line
        if keep:
            if skipped:
                kept.append(
                    f"    <!-- … {skipped} unchanged cells elided … -->"
                )
                skipped = 0
            kept.append(line)
        else:
            skipped += 1
    if skipped:
        kept.insert(-1, f"    <!-- … {skipped} unchanged cells elided … -->")
    return "\n".join(kept)


def _safe_render_row(record: dict[str, Any]) -> str:
    try:
        return render_row(record)
    except Exception as exc:  # noqa: BLE001
        return f"<!-- error rendering row {record.get('id')}: {exc} -->"


def _highlight_row(
    rendered: str, changed_slugs: set[str], changed_tax_axes: set[str]
) -> str:
    """Prefix changed <td> lines with a 🔸 visible marker.

    We picked 🔸 (visible inside the fenced ```html block where the row
    HTML is shown) over `<mark>` because the row is shown inside a code
    fence — GitHub renders the code fence verbatim, so <mark> would just
    appear as literal text rather than highlighting. The emoji prefix is
    visible without forcing the reader to scan for an HTML tag.
    """
    if not changed_slugs and not changed_tax_axes:
        return rendered
    target_classes: set[str] = set(changed_slugs)
    for axis in changed_tax_axes:
        target_classes.add(f"tax-{axis}")
    out_lines: list[str] = []
    for line in rendered.split("\n"):
        marked = False
        for cls in target_classes:
            needle = f'class="{cls}"'
            needle_data = f'class="{cls} '
            if needle in line or needle_data in line:
                # Prepend the marker before the leading whitespace.
                leading = line[: len(line) - len(line.lstrip())]
                body = line[len(leading):]
                out_lines.append(f"{leading}🔸 {body}")
                marked = True
                break
        if not marked:
            out_lines.append(line)
    return "\n".join(out_lines)


def _safe_render_one_cell(
    slug: str, record: dict[str, Any], cell_payload: dict[str, Any]
) -> str:
    try:
        if slug.startswith("tax-"):
            axis = slug[len("tax-"):]
            return render_taxonomy_cell(axis, record.get("taxonomy", {}).get(axis, []))
        return render_cell(slug, cell_payload or {})
    except Exception as exc:  # noqa: BLE001
        return f"<error rendering cell: {exc}>"


def _render_record_block(rec: dict[str, Any]) -> tuple[str, int]:
    head = rec["head"]
    base = rec["base"]
    rid = rec["id"]
    section = _section_label(head)
    cell_changes = rec["cell_changes"]
    tax_changes = rec["tax_changes"]
    refresh_changes = rec["refresh_changes"]
    section_changed = rec["section_changed"]

    out: list[str] = []
    out.append(f"### `{rid}` ({section})")
    out.append("")

    summary_bits: list[str] = []
    if cell_changes:
        summary_bits.append(
            f"{len(cell_changes)} cell"
            + ("s" if len(cell_changes) != 1 else "")
            + ": "
            + ", ".join(f"`{c['slug']}`" for c in cell_changes)
        )
    if tax_changes:
        summary_bits.append(
            f"{len(tax_changes)} taxonomy axis: "
            + ", ".join(f"`tax-{c['axis']}`" for c in tax_changes)
        )
    if section_changed:
        summary_bits.append("section membership")
    if refresh_changes:
        summary_bits.append(
            f"{len(refresh_changes)} refreshed (last_verified_at only)"
        )
    if summary_bits:
        out.append("Changed: " + "; ".join(summary_bits))
        out.append("")

    if cell_changes:
        out.append("**Cell-level deltas:**")
        for c in cell_changes:
            b = c["before"]
            h = c["after"]
            bits = []
            if b.get("status") != h.get("status"):
                bits.append(f"status `{b.get('status')}` → `{h.get('status')}`")
            if b.get("citation") != h.get("citation"):
                bits.append(
                    f"citation `{b.get('citation') or '—'}` → "
                    f"`{h.get('citation') or '—'}`"
                )
            if b.get("value") != h.get("value"):
                bits.append("value changed")
            out.append(f"- 🔸 **{c['slug']}** — " + "; ".join(bits))
        out.append("")

    if tax_changes:
        out.append("**Taxonomy deltas:**")
        for t in tax_changes:
            adds = ", ".join(f"`+{v}`" for v in t["added"]) or "—"
            rems = ", ".join(f"`-{v}`" for v in t["removed"]) or "—"
            out.append(f"- 🔸 **tax-{t['axis']}** — added: {adds}; removed: {rems}")
        out.append("")

    if section_changed:
        out.append(
            f"**Section move:** `{_section_label(base)}` → `{_section_label(head)}`"
        )
        out.append("")

    if refresh_changes:
        out.append("**Refreshed (last_verified_at only):**")
        for r in refresh_changes:
            out.append(
                f"- `{r['slug']}`: "
                f"`{r['before'].get(REFRESH_FIELD) or '—'}` → "
                f"`{r['after'].get(REFRESH_FIELD) or '—'}`"
            )
        out.append("")

    # Full-row render with highlights.
    changed_slugs = {c["slug"] for c in cell_changes}
    changed_axes = {t["axis"] for t in tax_changes}
    rendered = _safe_render_row(head)
    rendered = _highlight_row(rendered, changed_slugs, changed_axes)
    rendered = _truncate_row(rendered)

    out.append("<details><summary>Full row render (HTML source)</summary>")
    out.append("")
    out.append("```html")
    out.append(rendered)
    out.append("```")
    out.append("")
    out.append("</details>")
    out.append("")

    if cell_changes:
        out.append("<details><summary>Per-cell before/after HTML</summary>")
        out.append("")
        for c in cell_changes:
            slug = c["slug"]
            before_html = _safe_render_one_cell(slug, base, c["before"])
            after_html = _safe_render_one_cell(slug, head, c["after"])
            before_html = _truncate_rendered(before_html)
            after_html = _truncate_rendered(after_html)
            out.append(f"**🔸 {slug}**")
            out.append("")
            out.append("- before:")
            out.append("")
            out.append("  ```html")
            for ln in before_html.split("\n"):
                out.append(f"  {ln}")
            out.append("  ```")
            out.append("- after:")
            out.append("")
            out.append("  ```html")
            for ln in after_html.split("\n"):
                out.append(f"  {ln}")
            out.append("  ```")
            out.append("")
        out.append("</details>")
        out.append("")

    cells_used = len(cell_changes) + len(tax_changes)
    return "\n".join(out), cells_used


# ---------------------------------------------------------------------------
# Top-level rendering (records + edges + truncation).
# ---------------------------------------------------------------------------


def _render_added_removed(diff: dict[str, Any]) -> str:
    out: list[str] = []
    if diff["added"]:
        out.append("### 🆕 New records")
        out.append("")
        for rid in diff["added"][:MAX_RECORDS]:
            rec = diff["head"][rid]
            out.append(f"#### `{rid}` ({_section_label(rec)})")
            out.append("")
            out.append("```html")
            out.append(_truncate_row(_safe_render_row(rec)))
            out.append("```")
            out.append("")
        if len(diff["added"]) > MAX_RECORDS:
            out.append(
                f"… and {len(diff['added']) - MAX_RECORDS} more new records "
                "(see the JSON diff)."
            )
            out.append("")
    if diff["removed"]:
        out.append("### ❌ Removed records")
        out.append("")
        for rid in diff["removed"]:
            base_rec = diff["base"][rid]
            out.append(f"- `{rid}` — {base_rec.get('name', '(no name)')}")
        out.append("")
    return "\n".join(out)


def _render_changed(diff: dict[str, Any]) -> tuple[str, dict[str, int]]:
    counts = {
        "records_shown": 0,
        "records_total": len(diff["changed"]),
        "cells_shown": 0,
        "cells_total": sum(
            len(r["cell_changes"]) + len(r["tax_changes"])
            for r in diff["changed"]
        ),
    }
    out: list[str] = []
    if not diff["changed"]:
        return "", counts
    out.append("### ✏️ Changed records")
    out.append("")
    cell_budget = MAX_CELLS
    for rec in diff["changed"]:
        if counts["records_shown"] >= MAX_RECORDS or cell_budget <= 0:
            break
        block, cells_used = _render_record_block(rec)
        out.append(block)
        counts["records_shown"] += 1
        counts["cells_shown"] += cells_used
        cell_budget -= max(cells_used, 1)
    remaining_records = counts["records_total"] - counts["records_shown"]
    remaining_cells = counts["cells_total"] - counts["cells_shown"]
    if remaining_records > 0 or remaining_cells > 0:
        out.append(
            f"… and {remaining_records} more records / "
            f"{remaining_cells} more cells changed, see the JSON diff."
        )
        out.append("")
    return "\n".join(out), counts


def _render_refreshed_only(diff: dict[str, Any]) -> str:
    if not diff["refreshed_only"]:
        return ""
    out: list[str] = ["### 🔄 Refreshed (last_verified_at only)", ""]
    out.append("| record | cell | before | after |")
    out.append("|---|---|---|---|")
    for r in diff["refreshed_only"]:
        for rc in r["refresh_changes"]:
            out.append(
                f"| `{r['id']}` | `{rc['slug']}` | "
                f"{rc['before'].get(REFRESH_FIELD) or '—'} | "
                f"{rc['after'].get(REFRESH_FIELD) or '—'} |"
            )
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Edges.
# ---------------------------------------------------------------------------


def _edge_key(edge: dict[str, Any]) -> tuple[str, str, str]:
    return (
        edge.get("source", ""),
        edge.get("target", ""),
        edge.get("type", ""),
    )


def _diff_edges(
    base_edges: list[dict[str, Any]], head_edges: list[dict[str, Any]]
) -> tuple[list[dict], list[dict], list[tuple[dict, dict]]]:
    base_by_key = {_edge_key(e): e for e in base_edges}
    head_by_key = {_edge_key(e): e for e in head_edges}
    added = [head_by_key[k] for k in head_by_key if k not in base_by_key]
    removed = [base_by_key[k] for k in base_by_key if k not in head_by_key]
    changed: list[tuple[dict, dict]] = []
    for k in set(base_by_key) & set(head_by_key):
        if base_by_key[k] != head_by_key[k]:
            changed.append((base_by_key[k], head_by_key[k]))
    return added, removed, changed


def _render_edges_section(
    edges_base_path: Path | None, edges_head_path: Path | None
) -> str:
    if not edges_base_path or not edges_head_path:
        return ""
    try:
        base_payload = _load_json(edges_base_path)
        head_payload = _load_json(edges_head_path)
    except Exception as exc:  # noqa: BLE001
        return f"### 🕸 Edges\n\n_error loading edges files: {exc}_\n"
    base_edges = (
        base_payload.get("edges", [])
        if isinstance(base_payload, dict)
        else base_payload
    )
    head_edges = (
        head_payload.get("edges", [])
        if isinstance(head_payload, dict)
        else head_payload
    )
    added, removed, changed = _diff_edges(base_edges, head_edges)
    if not (added or removed or changed):
        return ""
    out: list[str] = ["### 🕸 Edges", ""]
    out.append("| from | to | type | direction |")
    out.append("|---|---|---|---|")
    for e in added:
        out.append(
            f"| `{e.get('source', '')}` | `{e.get('target', '')}` | "
            f"`{e.get('type', '')}` | added |"
        )
    for e in removed:
        out.append(
            f"| `{e.get('source', '')}` | `{e.get('target', '')}` | "
            f"`{e.get('type', '')}` | removed |"
        )
    for _b, h in changed:
        out.append(
            f"| `{h.get('source', '')}` | `{h.get('target', '')}` | "
            f"`{h.get('type', '')}` | changed |"
        )
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Comment assembly.
# ---------------------------------------------------------------------------


def _summary_line(diff: dict[str, Any], counts: dict[str, int]) -> str:
    if not (
        diff["added"]
        or diff["removed"]
        or counts["records_total"]
        or diff["refreshed_only"]
    ):
        return "This PR makes no record-level content changes."
    parts = []
    if counts["records_total"]:
        parts.append(
            f"**{counts['records_total']} changed records** "
            f"({counts['cells_total']} cells)"
        )
    if diff["added"]:
        parts.append(f"**{len(diff['added'])} new**")
    if diff["removed"]:
        parts.append(f"**{len(diff['removed'])} removed**")
    if diff["refreshed_only"]:
        parts.append(f"**{len(diff['refreshed_only'])} refresh-only**")
    return "This PR changes " + ", ".join(parts) + "."


def build_comment(
    base_path: Path,
    head_path: Path,
    edges_base_path: Path | None,
    edges_head_path: Path | None,
) -> str:
    try:
        base_payload = _load_json(base_path)
        head_payload = _load_json(head_path)
    except Exception as exc:  # noqa: BLE001
        return (
            f"{MARKER}\n## 🪞 Rendered cell preview\n\n"
            f"❌ rendered preview failed: {exc}\n\n"
            f"```\n{traceback.format_exc()}\n```\n"
        )

    diff = _diff_records(
        _records_by_id(base_payload), _records_by_id(head_payload)
    )

    parts: list[str] = [MARKER, "## 🪞 Rendered cell preview", ""]

    changed_md, counts = _render_changed(diff)

    parts.append(_summary_line(diff, counts))
    parts.append("")
    parts.append(
        "Each touched record below is rendered as it will appear in "
        "`landscape.html` after merge. Changed cells are flagged with 🔸."
    )
    parts.append("")

    added_removed = _render_added_removed(diff)
    if added_removed:
        parts.append(added_removed)
    if changed_md:
        parts.append(changed_md)
    refreshed = _render_refreshed_only(diff)
    if refreshed:
        parts.append(refreshed)
    edges_md = _render_edges_section(edges_base_path, edges_head_path)
    if edges_md:
        parts.append(edges_md)

    return "\n".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Render a markdown PR comment for a landscape.json diff."
    )
    p.add_argument("--base", required=True, type=Path)
    p.add_argument("--head", required=True, type=Path)
    p.add_argument("--edges-base", type=Path, default=None)
    p.add_argument("--edges-head", type=Path, default=None)
    p.add_argument("--output", required=True, type=Path)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    body = build_comment(
        base_path=args.base,
        head_path=args.head,
        edges_base_path=args.edges_base,
        edges_head_path=args.edges_head,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
