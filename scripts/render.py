#!/usr/bin/env python3
"""
render.py — data/landscape.json → landscape.html

The reverse of scripts/extract.py. Reads the structured records from
data/landscape.json and writes a no-JS-readable landscape.html that
mirrors the existing hand-edited landscape.html structure (head, styles,
column key, cross-cutting analyses, table layout).

Determinism contract:
  - Records are grouped by primary section (and primary subsection where
    applicable). Group ordering is taken from extraction/section-explainers.json
    (a sidecar extracted from the current landscape.html — issue #6).
  - Within each group, records are sorted by tier ASC then id ASC. This
    matches the post-JS view of the existing landscape.html (which has the
    same tier-sort applied client-side).
  - All cell rendering is deterministic: status enum drives the wrapper,
    citation hrefs are emitted verbatim, taxonomy axes emit one .tax-pill
    span per entry in the array.

Usage:
  python3 scripts/render.py            # writes landscape.html (default)
  python3 scripts/render.py --output /tmp/foo.html

For round-trip validation against the current landscape.html, run
  python3 scripts/extract.py
  python3 scripts/render.py --output /tmp/landscape.rendered.html
  diff landscape.html /tmp/landscape.rendered.html

Expected diff: row reordering (extract.py loses source order; we tier-sort
to match the post-JS view), per-cell HTML markup (signal-num spans, <br>,
<sub class="sub">, pill anchors inside <td.links>) that extract.py
collapsed into plain text, and cross-listing markers we add for records
with secondary section memberships. Otherwise the structural skeleton is
identical.
"""

from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Schema constants — kept in sync with docs/SCHEMA.md / scripts/extract.py.
# ---------------------------------------------------------------------------

CELL_COLUMN_SLUGS: list[str] = [
    "type",
    "desc",
    "claims",
    "modalities",
    "created",
    "latest-release",
    "license",
    "gh",
    "mindshare",
    "citations",
    "funding",
    "customers",
    "pricing",
    "compliance",
    "data-handling",
    "deployment",
    "hq",
    "founders",
    "volume",
    "perf",
    "repro",
    "code-release",
    "api-surface",
    "latency",
    "throughput",
    "backend-storage",
    "multi-tenancy",
    "encryption",
    "sso-rbac",
    "embedding-model",
    "consistency",
    "versioning",
    "tombstoning",
    "schema-evolution",
    "namespace",
    "contradiction",
    "forgetting",
    "mcp-support",
    "a2a-support",
    "otel",
    "webhooks",
    "import-export",
    "integration-count",
    "orchestration",
    "programmatic-control",
    "vendor-benchmarks",
    "pricing-specifics",
    "agent-abstraction",
    "memory-primitives",
    "llm-lock",
    "runtimes",
    "session-handling",
    "validated-verticals",
    "time-to-running",
    "anti-fit",
    "optimised-for",
    "adjacent-infrastructure",
    "pros",
    "cons",
    "links",
    # T1-1 observability columns (issue #39). See docs/SCHEMA.md §2.5.1.
    "obs-langsmith",
    "obs-opentelemetry",
    "obs-datadog",
    "obs-helicone",
    "obs-weave",
    "obs-langfuse",
    "obs-arize",
    "obs-custom",
    # T1-3 cost-control columns (issue #41). See docs/SCHEMA.md §2.5.2.
    "cost-token-budget",
    "cost-prompt-caching",
    "cost-semantic-caching",
    "cost-batching",
    "cost-model-routing",
    "cost-streaming-only",
    "cost-observability-cost-attribution",
    # T1-2 eval-tooling columns (issue #40). See docs/SCHEMA.md §2.5.3.
    "eval-langsmith-evals",
    "eval-braintrust",
    "eval-weights-and-biases-agent",
    "eval-helicone-evals",
    "eval-custom-test-harness",
    "eval-human-loop",
    "eval-production-traffic-replay",
    # T3-prep-1 commit-trajectory column (issue #50). See docs/SCHEMA.md §2.5.4.
    "commit-trajectory",
    # T3-prep-2 citation-trajectory column (issue #51). See docs/SCHEMA.md §2.5.5.
    "citation-trajectory",
    # T3-prep-3 download-trajectory column (issue #52). See docs/SCHEMA.md §2.5.6.
    "download-trajectory",
]
assert len(CELL_COLUMN_SLUGS) == 85

TAXONOMY_AXES: list[str] = [
    "storage",
    "retrieval",
    "persistence",
    "update",
    "unit",
    "governance",
    "conflict",
]

# Trajectory cells wrap their JSON payload in a <span class="trajectory-data">
# so the sparkline JS can find it. Source-HTML invariant; round-tripped by
# extract.py via the data-as-text capture.
TRAJECTORY_CELL_SLUGS = {
    "commit-trajectory",
    "citation-trajectory",
    "download-trajectory",
}

# Volatile slugs that may carry per-cell data-last-verified attributes
# (SCHEMA.md §3b). Mirrors scripts/extract.py / backfill_verified_at.py.
VOLATILE_CELL_SLUGS = {
    "created",
    "latest-release",
    "gh",
    "mindshare",
    "citations",
    "funding",
    "vendor-benchmarks",
    "commit-trajectory",
    "citation-trajectory",
    "download-trajectory",
    "obs-langsmith",
    "obs-opentelemetry",
    "obs-datadog",
    "obs-helicone",
    "obs-weave",
    "obs-langfuse",
    "obs-arize",
    "obs-custom",
    "cost-token-budget",
    "cost-prompt-caching",
    "cost-semantic-caching",
    "cost-batching",
    "cost-model-routing",
    "cost-streaming-only",
    "cost-observability-cost-attribution",
    "eval-langsmith-evals",
    "eval-braintrust",
    "eval-weights-and-biases-agent",
    "eval-helicone-evals",
    "eval-custom-test-harness",
    "eval-human-loop",
    "eval-production-traffic-replay",
}

# Style attribute reused on every level-2 group-row td (subsection header).
SUB_GROUP_STYLE = (
    "padding-left: 28px; text-transform: none; "
    "letter-spacing: 0.04em; color: #b8b8b8;"
)

# Style attribute reused on most "no-data" spans that wrap not-applicable text.
NA_SPAN_STYLE = "font-style:italic;color:#555;"


# ---------------------------------------------------------------------------
# Templates extracted from the current landscape.html.
#
# We treat the current landscape.html as the source of truth for the
# scaffold — head, styles, thead, the column-key block, the cross-cutting
# analyses block, and the closing tags. render.py only regenerates the
# tbody body. To avoid embedding ~330 lines of CSS/HTML inline in this
# script, we read it from landscape.html at runtime and slice out the
# stable HEAD (everything up through `<tbody>\n`) and TAIL (everything
# from `  </tbody>\n` onwards). The tbody itself is rewritten from the
# JSON; only the surrounding markup is reused verbatim.
#
# This is the structurally-honest behaviour for an HTML-as-build-artifact
# during the transitional period (issue #7 will activate JSON-as-canonical):
# the JSON drives the data, the existing HTML drives the chrome, and the
# diff stays bounded to data rows.
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATE_HTML = ROOT / "landscape.html"
DEFAULT_INPUT = ROOT / "data" / "landscape.json"
DEFAULT_OUTPUT = ROOT / "landscape.html"
DEFAULT_SECTION_SIDECAR = ROOT / "extraction" / "section-explainers.json"


def slice_template(html: str) -> tuple[str, str]:
    """Return (head, tail) so that render output is `head + body + tail`."""
    open_marker = "\n  <tbody>\n"
    close_marker = "\n  </tbody>\n"
    open_at = html.find(open_marker)
    close_at = html.find(close_marker)
    if open_at < 0 or close_at < 0:
        raise RuntimeError(
            "template landscape.html missing the tbody markers used to slice "
            "head / tail; check that the file still has `\\n  <tbody>\\n` and "
            "`\\n  </tbody>\\n` exactly once each."
        )
    head_end = open_at + len(open_marker)
    # tail starts at the leading newline that precedes `</tbody>` so the
    # rendered output keeps the same blank-line spacing.
    tail_start = close_at + 1  # skip the leading '\n' so head/body/tail join cleanly
    head = html[:head_end]
    tail = html[tail_start:]
    return head, tail


# ---------------------------------------------------------------------------
# Cell rendering.
# ---------------------------------------------------------------------------


def _value_passthrough(value: str) -> str:
    """Render a cell's `value` for the HTML output.

    The issue spec describes a future state where `value` may already
    contain HTML markup (e.g. `<span class="signal-num">…</span>`,
    `<br>`, `<span class="sub">…</span>`) and asks render.py to pass
    that markup through verbatim. In the current build of landscape.json
    extract.py is lossy in the other direction — it calls
    BeautifulSoup's `get_text()` and decodes `&lt;` / `&amp;` into the
    literal characters `<` / `&`. So the JSON we have today is plain
    text with no embedded markup, and passing the raw string through
    would emit invalid HTML for ~310 cells whose values contain a
    literal `<` (e.g. `<10min (hosted)`).

    To square the two contracts, we escape conservatively: `<`, `>`, and
    `&` always become entities. Quotes are left alone since values are
    only ever rendered as element children, never as attribute values.
    A future producer that wants to preserve markup verbatim will need
    a companion `valueHtml` field on the cell (or a producer-side flag);
    this decision is documented in `docs/DECISIONS.md`.
    """
    return escape(value, quote=False)


def render_citation(href: str | None, title: str = "source") -> str:
    """Render the `<a class="cite" href="..." title="...">↗</a>` link.

    Returns "" if href is None / empty / non-http.
    """
    if not href:
        return ""
    if not (href.startswith("http://") or href.startswith("https://")):
        return ""
    return (
        f'<a class="cite" href="{escape(href, quote=True)}" '
        f'title="{escape(title, quote=True)}">↗</a>'
    )


def render_cell(td_class: str, cell: dict[str, Any]) -> str:
    """Render one cell <td> for a non-name, non-taxonomy column.

    `td_class` is the css class (e.g. "type", "desc", "perf"). `cell` is
    the JSON record's cell dict.

    Volatile cells (SCHEMA.md §3b) emit a `data-last-verified="YYYY-MM-DD"`
    attribute on the <td> when the cell carries one. Non-volatile cells
    never emit the attribute (they inherit the row-level date).
    """
    status = cell.get("status")
    value = cell.get("value", "") or ""
    citation = cell.get("citation")
    last_verified = cell.get("last_verified_at")

    if status == "real-data":
        body = _value_passthrough(value)
        if td_class in TRAJECTORY_CELL_SLUGS:
            body = f'<span class="trajectory-data">{body}</span>'
        cite = render_citation(citation, "source")
        # If there's a citation, separate the value from the link with a
        # space — this matches the existing HTML's pattern.
        if cite:
            inner = f"{body} {cite}".strip()
        else:
            inner = body
    elif status == "not-applicable":
        # Two render shapes coexist in the source HTML: the wrong-section
        # rows ("N/A — wrong section <a href=N/A>↗</a>") and the inline
        # italic-grey not-applicable span. We collapse to the latter
        # since the JSON's `value` already includes the annotation text
        # and the JSON has dropped non-http citation hrefs.
        v_lower = value.strip().lower()
        if v_lower.startswith("n/a") and "wrong section" in v_lower:
            # Preserve the original "N/A — wrong section" plain rendering
            # so the diff against the current landscape.html is minimal
            # for these very common cells. The href="N/A" placeholder
            # cannot be reproduced (extract.py drops it), so the cite
            # link is omitted.
            inner = _value_passthrough(value)
        else:
            inner = (
                f'<span class="no-data" style="{NA_SPAN_STYLE}">'
                f"{_value_passthrough(value)}</span>"
            )
            cite = render_citation(citation, "source")
            if cite:
                inner = f"{inner} {cite}"
    elif status == "depth-floor-reached":
        # depth-floor-reached cells use the un-styled .no-data span (the
        # CSS rule at .no-data already makes them italic-grey via the
        # ::before "no data " prefix).
        inner = f'<span class="no-data">{_value_passthrough(value)}</span>'
        cite = render_citation(citation, "searched")
        if cite:
            inner = f"{inner} {cite}"
    elif status == "no-data":
        inner = '<span class="no-data"></span>'
    elif status == "estimate":
        # Maintainer-judgement (T3 claim tier — see SCHEMA.md §3a).
        # Render with an explicit "estimate" marker span so the round-trip
        # extract picks the status back up.
        body = _value_passthrough(value)
        cite = render_citation(citation, "source")
        marker = '<span class="no-data">estimate</span>'
        inner = f"{marker} {body}".strip()
        if cite:
            inner = f"{inner} {cite}"
    else:
        raise RuntimeError(f"unknown cell status {status!r}")

    attrs = f'class="{escape(td_class, quote=True)}"'
    if (
        td_class in VOLATILE_CELL_SLUGS
        and isinstance(last_verified, str)
        and last_verified
    ):
        attrs += f' data-last-verified="{escape(last_verified, quote=True)}"'
    return f"    <td {attrs}>{inner}</td>"


def render_taxonomy_cell(axis: str, axis_values: list[dict[str, Any]]) -> str:
    """Render one tax-* cell from the array of {value, primary, reason}.

    Pills are emitted in array order. The schema specifies "exactly one
    primary"; primary is mostly informational at render time — every pill
    renders the same way. When a non-primary value carries a `reason`, we
    drop it as a `title=` attribute so the pill remains hoverable for the
    rationale.

    For axes whose JSON entry is `[{value: "n/a", primary: true, reason:
    "<text>"}]` (free-text taxonomy fallback), we render the reason as a
    no-data span — same shape extract.py was reading.
    """
    td_class = f"tax-{axis}"
    if not axis_values:
        return f'    <td class="{td_class}"></td>'
    # Special-case the n/a-with-reason fallback used for free-text
    # taxonomy cells (e.g. tax-conflict free-text descriptions, or
    # not-applicable annotations).
    # Free-text taxonomy fallback: extract.py records `reason` only when the
    # cell was free text (not pills). A single-entry axis whose lone value
    # has a `reason` therefore round-trips back to the prose form, not a pill.
    # This matches the source HTML where some axes (notably tax-conflict for
    # papers, plus older NVIDIA-style rows) use bare prose instead of pills.
    if len(axis_values) == 1 and axis_values[0].get("reason"):
        reason = axis_values[0]["reason"]
        rl = reason.lower()
        if rl.startswith("not applicable") or rl.startswith("n/a"):
            return (
                f'    <td class="{td_class}"><span class="no-data" '
                f'style="{NA_SPAN_STYLE}">{_value_passthrough(reason)}</span></td>'
            )
        if (
            "searched not found" in rl
            or rl.startswith("not specified")
            or rl.startswith("position paper")
            or rl.startswith("no public")
            or rl.startswith("no releases")
            or rl.startswith("no quantitative")
            or rl.startswith("no headline")
        ):
            return (
                f'    <td class="{td_class}"><span class="no-data">'
                f"{_value_passthrough(reason)}</span></td>"
            )
        # Generic free-text taxonomy fallback (e.g. tax-conflict prose).
        return f'    <td class="{td_class}">{_value_passthrough(reason)}</td>'

    pills: list[str] = []
    for entry in axis_values:
        v = entry.get("value", "") or ""
        title_attr = ""
        reason = entry.get("reason")
        if reason and not entry.get("primary"):
            title_attr = f' title="{escape(reason, quote=True)}"'
        pills.append(
            f'<span class="tax-pill tax-{escape(v, quote=True)}"{title_attr}>'
            f"{escape(v)}</span>"
        )
    return f'    <td class="{td_class}">{"".join(pills)}</td>'


def render_name_cell(record: dict[str, Any]) -> str:
    """Render `<td class="name"><a href="...">Name</a></td>` (or no <a> if
    url is null)."""
    name = record["name"]
    url = record.get("url")
    if url:
        body = (
            f'<a href="{escape(url, quote=True)}">{_value_passthrough(name)}</a>'
        )
    else:
        body = _value_passthrough(name)
    return f'    <td class="name">{body}</td>'


def render_cross_listing_marker(record: dict[str, Any]) -> str:
    """Return an inline marker fragment for records that appear in more
    than one section. Empty string for records with a single section.

    Rendered choice (see DECISIONS.md): emit `<span class="cross-listed">…
    </span>` immediately after the name <a>, listing the secondary section
    names. The class isn't styled today; it sits inert in the no-JS view
    but is queryable by future consumers (table app, CSS, search).
    """
    secondary = [s for s in record.get("sections", []) if not s.get("primary")]
    if not secondary:
        return ""
    parts = []
    for s in secondary:
        target = s["section"]
        if s.get("subsection"):
            target = f"{target} / {s['subsection']}"
        parts.append(target)
    label = "; ".join(parts)
    return (
        f' <span class="cross-listed" title="Also listed under: '
        f'{escape(label, quote=True)}">also in §{escape(label)}</span>'
    )


# ---------------------------------------------------------------------------
# Row + section rendering.
# ---------------------------------------------------------------------------


def render_row(record: dict[str, Any]) -> str:
    tier = record["tier"]
    lines: list[str] = []
    # Row-level data-last-verified (SCHEMA.md §3b). Always present for
    # post-backfill records; older serialisations without one render the
    # row without the attribute (the cycle gate would then catch a
    # round-trip drift, which is the correct signal to re-run backfill).
    lva = record.get("last_verified_at")
    tr_attrs = f'class="row-t{tier}"'
    if isinstance(lva, str) and lva:
        tr_attrs += f' data-last-verified="{escape(lva, quote=True)}"'
    # Row-level decay forensics (SCHEMA.md §3c, issue #56). Three
    # optional attrs — emit each when present, omit when absent. The
    # extract.py side reads these back into record-level fields; the
    # cycle gate (gate 3) enforces round-trip stability.
    decay_cause = record.get("decay_cause")
    if isinstance(decay_cause, str) and decay_cause:
        tr_attrs += f' data-decay-cause="{escape(decay_cause, quote=True)}"'
    decay_date = record.get("decay_date")
    if isinstance(decay_date, str) and decay_date:
        tr_attrs += f' data-decay-date="{escape(decay_date, quote=True)}"'
    decay_evidence = record.get("decay_evidence")
    if isinstance(decay_evidence, str) and decay_evidence:
        tr_attrs += (
            f' data-decay-evidence="{escape(decay_evidence, quote=True)}"'
        )
    lines.append(f"  <tr {tr_attrs}>")
    # Name with optional cross-listing marker injected after the closing </a>.
    name_cell = render_name_cell(record)
    marker = render_cross_listing_marker(record)
    if marker:
        # Inject the marker before the closing </td>.
        name_cell = name_cell[:-len("</td>")] + marker + "</td>"
    lines.append(name_cell)
    # type cell (the first cell column).
    lines.append(render_cell("type", record["cells"]["type"]))
    # 7 taxonomy axes.
    for axis in TAXONOMY_AXES:
        lines.append(render_taxonomy_cell(axis, record["taxonomy"].get(axis, [])))
    # Remaining 59 cells (skip "type" — already emitted).
    for slug in CELL_COLUMN_SLUGS[1:]:
        cell = record["cells"].get(slug)
        if cell is None:
            raise RuntimeError(f"record {record['id']!r} missing cell {slug!r}")
        lines.append(render_cell(slug, cell))
    lines.append("  </tr>")
    return "\n".join(lines)


def render_group_header(label: str, is_subsection: bool) -> str:
    if is_subsection:
        return (
            f'  <tr class="group-row"><td colspan="93" '
            f'style="{SUB_GROUP_STYLE}">{_value_passthrough(label)}</td></tr>'
        )
    return (
        f'  <tr class="group-row"><td colspan="93">'
        f"{_value_passthrough(label)}</td></tr>"
    )


def render_section_explainer(explainer_html: str | None) -> str | None:
    if not explainer_html:
        return None
    return (
        '  <tr class="section-explainer"><td colspan="93">'
        f'<div class="explainer-text">{explainer_html}</div></td></tr>'
    )


# ---------------------------------------------------------------------------
# Body assembly.
# ---------------------------------------------------------------------------


def primary_section(record: dict[str, Any]) -> tuple[str, str | None]:
    for s in record.get("sections", []):
        if s.get("primary"):
            return s["section"], s.get("subsection")
    raise RuntimeError(f"record {record['id']!r} has no primary section")


def render_body(records: list[dict[str, Any]], sections_meta: list[dict]) -> str:
    """Render the inside-of-tbody portion."""
    # Group records by (section, subsection).
    groups: dict[tuple[str, str | None], list[dict]] = {}
    for r in records:
        key = primary_section(r)
        groups.setdefault(key, []).append(r)
    # Within each group, sort by (tier ASC, id ASC). This matches the
    # post-JS view of the existing landscape.html (the inline <script>
    # at the bottom of the file does the same client-side sort).
    for k in groups:
        groups[k].sort(key=lambda r: (r["tier"], r["id"]))

    # Walk sections_meta in declared order.
    out_parts: list[str] = []
    for entry in sections_meta:
        section = entry["section"]
        subsection = entry.get("subsection")
        is_sub = subsection is not None
        label = subsection if is_sub else section

        # Group header
        out_parts.append("")  # blank line before each group-row
        out_parts.append(render_group_header(label, is_sub))

        # Section explainer (if any)
        explainer = render_section_explainer(entry.get("explainer"))
        if explainer is not None:
            out_parts.append("")
            out_parts.append(explainer)

        # Records in this group
        group_records = groups.get((section, subsection), [])
        for rec in group_records:
            out_parts.append("")
            out_parts.append(render_row(rec))

    out_parts.append("")  # trailing blank line (matches existing layout)
    # Strip a leading blank line so we sit cleanly after `<tbody>\n`.
    body = "\n".join(out_parts)
    if body.startswith("\n"):
        body = body[1:]
    return body


# ---------------------------------------------------------------------------
# Main pipeline.
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="path to landscape.json (default: data/landscape.json)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="path to write landscape.html (default: ./landscape.html)",
    )
    parser.add_argument(
        "--template",
        default=str(DEFAULT_TEMPLATE_HTML),
        help="HTML template providing head/tail scaffold (default: ./landscape.html)",
    )
    parser.add_argument(
        "--sections",
        default=str(DEFAULT_SECTION_SIDECAR),
        help="JSON sidecar of section ordering + explainers "
        "(default: extraction/section-explainers.json)",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    template_path = Path(args.template)
    sections_path = Path(args.sections)

    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2
    if not template_path.exists():
        print(f"error: template not found: {template_path}", file=sys.stderr)
        return 2
    if not sections_path.exists():
        print(f"error: sections sidecar not found: {sections_path}", file=sys.stderr)
        return 2

    # Load input data.
    payload = json.loads(in_path.read_text(encoding="utf-8"))
    records = payload["records"]

    # Load sections sidecar (declared section ordering + explainer copy).
    sections_meta = json.loads(sections_path.read_text(encoding="utf-8"))["sections"]

    # Slice the head/tail off the existing HTML.
    template = template_path.read_text(encoding="utf-8")
    head, tail = slice_template(template)

    body = render_body(records, sections_meta)

    out = head + body + tail
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")

    # Summary.
    by_tier: dict[int, int] = {}
    n_cross = 0
    for r in records:
        by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
        if len(r.get("sections", [])) > 1:
            n_cross += 1
    print(f"wrote {out_path} ({len(records)} records)")
    print(
        "  by tier: "
        + ", ".join(f"T{t}={by_tier.get(t, 0)}" for t in (1, 2, 3, 4, 5))
    )
    print(f"  cross-listed records: {n_cross}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
