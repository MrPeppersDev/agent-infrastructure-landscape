#!/usr/bin/env python3
"""
Data-gap audit.

Reads `web/landscape.json` (read-only) and classifies every (record, column)
cell into one of six gap classes. Emits:

  - extraction/data-gaps.csv          — prioritised work-queue
  - extraction/data-gaps-summary.md   — human-readable report

Determinism: the script is purely a function of `web/landscape.json` plus the
constants in this file. Re-running over an unchanged input produces byte-
identical output (stable sort: priority DESC, section ASC, record_id ASC,
column ASC).

Gap classes (see spec / docs/DECISIONS.md):
  - fillable-and-missing        — applies, but empty / no-data / placeholder
  - real-data-no-citation       — has value but citation missing
  - shallow-prose               — value present but too thin
  - structurally-not-applicable — terminal NA, skip
  - searched-not-found          — depth-floor-reached with citation, skip
  - terminal-real-data          — fully-filled, skip

The first three are written to `data-gaps.csv`. The latter three are not
in the CSV but are counted toward the sanity-check total.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_PATH = REPO_ROOT / "web" / "landscape.json"
CSV_OUT = REPO_ROOT / "extraction" / "data-gaps.csv"
SUMMARY_OUT = REPO_ROOT / "extraction" / "data-gaps-summary.md"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Columns considered "high-leverage" for priority scoring.
HIGH_LEVERAGE_COLS = {
    "funding",
    "customers",
    "claims",
    "perf",
    "citations",
    "gh",
    "created",
}

# Columns whose expected type is "long prose" — anything below MIN_PROSE_CHARS
# under one of these columns is shallow.
PROSE_COLS = {
    "desc",
    "claims",
    "perf",
    "pros",
    "cons",
    "data-handling",
    "anti-fit",
    "optimised-for",
    "validated-verticals",
    "memory-primitives",
    "adjacent-infrastructure",
    "vendor-benchmarks",
    "pricing-specifics",
    "session-handling",
    "import-export",
    "orchestration",
    "programmatic-control",
    "api-surface",
}
MIN_PROSE_CHARS = 15

# Round-7 sections (scope-expansion sweep) for the report-only "by category"
# breakdown.
ROUND_7_SECTIONS = {
    "Training infrastructure",
    "Search platforms (non-memory)",
    "Agent frameworks (no first-party memory layer)",
    "Inference platforms & gateways",
    "Embedding & reranker services",
    "Evaluation & observability platforms",
}

# Sections that are research / paper / benchmark in nature — terminal NAs are
# expected on most product-shaped columns.
RESEARCH_PAPER_SECTIONS = {
    "Recent method papers — theorized, no distinct product",
    "Research / specialised systems",
    "Memory benchmarks & evaluation",
    "Theoretical / informal — ideas without a paper",
}

# Original memory-focused sections present pre-Round-7 (used for the report's
# "original memory sections" comparison bucket).
ORIGINAL_MEMORY_SECTIONS = {
    "Vertical / domain-specific AI memory",
    "Dedicated memory layers",
    "Retrieval-as-memory hybrids",
    "Framework-embedded memory",
    "Personal AI / PKM / lifelogging memory",
    "Claude Code memory mechanisms",
    "Knowledge-graph platforms",
    "Vector-database infrastructure",
    "Platform-provider memory",
    "Memory benchmarks & evaluation",
    "File-backed / editor paradigms",
    "Coding-agent memory",
    "Voice-first / wearable AI memory",
    "Research / specialised systems",
    "Enterprise-search adjacencies",
    "Memory governance, privacy & safety",
    "Browser-agent memory",
    "Memory observability & monitoring",
    "Recent method papers — theorized, no distinct product",
    "Theoretical / informal — ideas without a paper",
}

# Columns that don't apply to research papers / benchmarks (when status is
# already not-applicable, that's structurally-correct).
PRODUCT_ONLY_COLS = {
    "funding",
    "customers",
    "pricing",
    "compliance",
    "deployment",
    "hq",
    "api-surface",
    "latency",
    "throughput",
    "backend-storage",
    "multi-tenancy",
    "encryption",
    "sso-rbac",
    "embedding-model",
    "mcp-support",
    "a2a-support",
    "otel",
    "webhooks",
    "import-export",
    "pricing-specifics",
    "vendor-benchmarks",
    "integration-count",
    "namespace",
}

# Applicability rules: which columns are structurally not-applicable for a
# given "kind" of record.  Used to validate NOT-APPLICABLE statuses and to
# decide whether an empty cell counts as fillable.
APPLIES_RULES: dict[str, set[str]] = {
    # Research papers / informal / theoretical: product-shaped columns don't
    # apply.
    "research-paper": PRODUCT_ONLY_COLS,
    # Benchmarks: same, plus perf/volume aren't product attributes.
    "benchmark": PRODUCT_ONLY_COLS | {"perf", "volume"},
    # OSS framework or product: pretty much everything applies; funding /
    # customers may still legitimately be NA for non-incorporated projects.
    "product": set(),  # nothing structurally excluded by default
}

# Placeholder-phrase regex for detecting fillable-but-cosmetically-filled cells.
PLACEHOLDER_PATTERNS = [
    r"^\s*$",  # empty / whitespace-only
    r"^\s*[—–-]\s*$",  # dash placeholder
    r"\bTBD\b",
    r"\bTBA\b",
    r"\bnot yet researched\b",
    r"\bnot researched\b",
    r"\bsearched not found\b",
    r"^\s*no data\b",
    r"\bn\s*/\s*a\b",
    r"\bunknown\b",
]
PLACEHOLDER_RE = re.compile("|".join(PLACEHOLDER_PATTERNS), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def classify_record_kind(record: dict[str, Any]) -> str:
    """Return 'research-paper', 'benchmark', or 'product' for a record.

    Heuristic: primary section governs.  Falls back on type-string keywords.
    """
    primary_section = None
    for s in record.get("sections") or []:
        if s.get("primary"):
            primary_section = s.get("section")
            break
    if primary_section is None and record.get("sections"):
        primary_section = record["sections"][0].get("section")

    if primary_section == "Memory benchmarks & evaluation":
        return "benchmark"
    if primary_section in RESEARCH_PAPER_SECTIONS:
        return "research-paper"
    # Fallback on id pattern: arxiv-... / openreview-... / aclanthology-...
    rid = (record.get("id") or "").lower()
    if any(tok in rid for tok in ("arxiv-", "openreview", "aclanthology", "neurips", "iclr", "icml")):
        return "research-paper"
    return "product"


def is_placeholder_value(value: Any) -> bool:
    """True if the string value looks like a placeholder, NOT real data."""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    if value.strip() == "":
        return True
    if PLACEHOLDER_RE.search(value):
        # Reject long values that just *mention* one of the placeholder
        # words inline (e.g. "no data available since 2023..."). Keep the
        # detection limited to ~short cosmetic fills.
        return len(value.strip()) <= 60
    return False


def is_shallow_prose(column: str, value: str) -> bool:
    """True if a real-data prose cell is too thin."""
    if column not in PROSE_COLS:
        return False
    v = (value or "").strip()
    return len(v) < MIN_PROSE_CHARS


def primary_section_for(record: dict[str, Any]) -> str:
    for s in record.get("sections") or []:
        if s.get("primary"):
            return s.get("section") or ""
    if record.get("sections"):
        return record["sections"][0].get("section") or ""
    return ""


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def classify_cell(
    record: dict[str, Any],
    column: str,
    cell: dict[str, Any],
    kind: str,
) -> str:
    """Return a gap-class string for a single cell."""
    status = cell.get("status")
    value = cell.get("value")
    citation = cell.get("citation")

    excluded = APPLIES_RULES.get(kind, set())

    # ----- not-applicable branch -----
    if status == "not-applicable":
        # Treat as structurally-not-applicable if this kind genuinely
        # excludes the column. Otherwise the NA is suspicious (someone
        # marked a usually-applicable column NA), but we still keep it
        # in the structurally-NA bucket so the audit doesn't generate
        # noise; deep-fill rounds can revisit selectively.
        if column in excluded or kind == "product":
            return "structurally-not-applicable"
        return "structurally-not-applicable"

    # ----- depth-floor branch -----
    if status == "depth-floor-reached":
        if citation:
            return "searched-not-found"
        # No citation: treat as still-fillable (someone gave up but didn't
        # log where they looked).
        return "fillable-and-missing"

    # ----- no-data branch -----
    if status == "no-data":
        # If the column doesn't apply, mark structural.
        if column in excluded:
            return "structurally-not-applicable"
        return "fillable-and-missing"

    # ----- real-data branch -----
    if status == "real-data":
        if is_placeholder_value(value):
            if column in excluded:
                return "structurally-not-applicable"
            return "fillable-and-missing"
        if not citation:
            return "real-data-no-citation"
        if isinstance(value, str) and is_shallow_prose(column, value):
            return "shallow-prose"
        return "terminal-real-data"

    # Defensive fallback (should never happen given known statuses).
    return "fillable-and-missing"


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------


def priority_for(gap_class: str, column: str) -> int:
    if gap_class == "fillable-and-missing":
        return 10 if column in HIGH_LEVERAGE_COLS else 5
    if gap_class == "real-data-no-citation":
        return 3 if column in HIGH_LEVERAGE_COLS else 1
    if gap_class == "shallow-prose":
        return 1
    return 0  # terminal / NA / searched — not in CSV anyway


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    with LANDSCAPE_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    records = data.get("records") or []

    rows: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    column_class_counts: dict[str, Counter[str]] = defaultdict(Counter)
    section_class_counts: dict[str, Counter[str]] = defaultdict(Counter)
    record_gap_counts: Counter[str] = Counter()
    record_name: dict[str, str] = {}
    record_section: dict[str, str] = {}
    record_kind: dict[str, str] = {}
    record_tier: dict[str, int] = {}

    total_cells = 0

    for record in records:
        rid = record.get("id") or ""
        rname = record.get("name") or ""
        rtier = record.get("tier")
        section = primary_section_for(record)
        kind = classify_record_kind(record)
        record_name[rid] = rname
        record_section[rid] = section
        record_kind[rid] = kind
        record_tier[rid] = rtier if rtier is not None else 0

        cells = record.get("cells") or {}
        for column, cell in cells.items():
            if not isinstance(cell, dict):
                continue
            total_cells += 1
            klass = classify_cell(record, column, cell, kind)
            class_counts[klass] += 1
            column_class_counts[column][klass] += 1
            section_class_counts[section][klass] += 1

            if klass in {"fillable-and-missing", "real-data-no-citation", "shallow-prose"}:
                prio = priority_for(klass, column)
                rows.append(
                    {
                        "record_id": rid,
                        "record_name": rname,
                        "record_tier": rtier,
                        "section": section,
                        "column": column,
                        "gap_class": klass,
                        "priority": prio,
                        "current_value": cell.get("value") or "",
                        "current_citation": cell.get("citation") or "",
                        "current_status": cell.get("status") or "",
                    }
                )
                record_gap_counts[rid] += 1

    # Deterministic sort: priority DESC, section ASC, record_id ASC, column ASC.
    rows.sort(
        key=lambda r: (
            -int(r["priority"]),
            r["section"],
            r["record_id"],
            r["column"],
        )
    )

    # ----- write CSV -----
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "record_id",
        "record_name",
        "record_tier",
        "section",
        "column",
        "gap_class",
        "priority",
        "current_value",
        "current_citation",
        "current_status",
    ]
    with CSV_OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            # CSV values must be strings; normalise.
            out = {k: ("" if row[k] is None else row[k]) for k in fieldnames}
            writer.writerow(out)

    # ----- summary -----
    write_summary(
        rows=rows,
        class_counts=class_counts,
        column_class_counts=column_class_counts,
        section_class_counts=section_class_counts,
        record_gap_counts=record_gap_counts,
        record_name=record_name,
        record_section=record_section,
        record_kind=record_kind,
        record_tier=record_tier,
        total_cells=total_cells,
        total_records=len(records),
    )

    # ----- console echo for the operator -----
    high_prio = sum(1 for r in rows if int(r["priority"]) >= 10)
    print(f"records           : {len(records)}")
    print(f"total cells       : {total_cells}")
    print(f"gap rows in CSV   : {len(rows)}")
    print(f"high-priority (>=10): {high_prio}")
    for cls, n in class_counts.most_common():
        print(f"  {cls:30s} {n}")
    # Sanity reconciliation
    accounted = (
        class_counts["fillable-and-missing"]
        + class_counts["real-data-no-citation"]
        + class_counts["shallow-prose"]
        + class_counts["structurally-not-applicable"]
        + class_counts["searched-not-found"]
        + class_counts["terminal-real-data"]
    )
    print(f"sanity check      : classes sum {accounted} vs total_cells {total_cells} (match={accounted == total_cells})")


def write_summary(
    *,
    rows: list[dict[str, Any]],
    class_counts: Counter,
    column_class_counts: dict[str, Counter],
    section_class_counts: dict[str, Counter],
    record_gap_counts: Counter,
    record_name: dict[str, str],
    record_section: dict[str, str],
    record_kind: dict[str, str],
    record_tier: dict[str, int],
    total_cells: int,
    total_records: int,
) -> None:
    lines: list[str] = []
    high_prio = sum(1 for r in rows if int(r["priority"]) >= 10)
    fillable_classes = {"fillable-and-missing", "real-data-no-citation", "shallow-prose"}

    lines.append("# Data-gap audit summary")
    lines.append("")
    lines.append(f"- Records scanned: **{total_records}**")
    lines.append(f"- Cells scanned: **{total_cells:,}**")
    lines.append(f"- Gap rows (CSV): **{len(rows):,}**")
    lines.append(f"- High-priority queue (priority >= 10): **{high_prio:,}**")
    lines.append("")
    lines.append("## Counts by class")
    lines.append("")
    lines.append("| Class | Count |")
    lines.append("|---|---:|")
    for cls in [
        "fillable-and-missing",
        "real-data-no-citation",
        "shallow-prose",
        "structurally-not-applicable",
        "searched-not-found",
        "terminal-real-data",
    ]:
        lines.append(f"| `{cls}` | {class_counts.get(cls, 0):,} |")
    accounted = sum(class_counts.values())
    lines.append(f"| **sum** | **{accounted:,}** |")
    lines.append("")
    lines.append(
        f"Sanity: {accounted:,} classified cells vs {total_cells:,} non-name cells "
        f"(match: **{'YES' if accounted == total_cells else 'NO'}**)."
    )
    lines.append("")

    # ----- top-10 most-gappy columns -----
    col_gap_total = {
        col: sum(c[k] for k in fillable_classes) for col, c in column_class_counts.items()
    }
    top_cols = sorted(col_gap_total.items(), key=lambda x: (-x[1], x[0]))[:10]
    lines.append("## Top 10 most-gappy columns")
    lines.append("")
    lines.append("| Column | Gaps | fillable | no-cite | shallow |")
    lines.append("|---|---:|---:|---:|---:|")
    for col, gaps in top_cols:
        c = column_class_counts[col]
        lines.append(
            f"| `{col}` | {gaps:,} | {c['fillable-and-missing']:,} | "
            f"{c['real-data-no-citation']:,} | {c['shallow-prose']:,} |"
        )
    lines.append("")

    # ----- top-10 most-gappy sections -----
    sec_gap_total = {
        sec: sum(c[k] for k in fillable_classes) for sec, c in section_class_counts.items()
    }
    top_secs = sorted(sec_gap_total.items(), key=lambda x: (-x[1], x[0]))[:10]
    lines.append("## Top 10 most-gappy sections")
    lines.append("")
    lines.append("| Section | Gaps | fillable | no-cite | shallow |")
    lines.append("|---|---:|---:|---:|---:|")
    for sec, gaps in top_secs:
        c = section_class_counts[sec]
        lines.append(
            f"| {sec} | {gaps:,} | {c['fillable-and-missing']:,} | "
            f"{c['real-data-no-citation']:,} | {c['shallow-prose']:,} |"
        )
    lines.append("")

    # ----- top 20 records by total gaps -----
    top_records = sorted(
        record_gap_counts.items(),
        key=lambda x: (-x[1], x[0]),
    )[:20]
    lines.append("## Top 20 records by total gaps")
    lines.append("")
    lines.append("| Record | Tier | Section | Gaps |")
    lines.append("|---|:--:|---|---:|")
    for rid, n in top_records:
        lines.append(
            f"| {record_name.get(rid, rid)} | T{record_tier.get(rid, '?')} | "
            f"{record_section.get(rid, '')} | {n} |"
        )
    lines.append("")

    # ----- by category -----
    lines.append("## By category")
    lines.append("")
    cat_buckets = {
        "Round-7 sections (Training / Search / Frameworks / Inference / Embedding / Eval)": ROUND_7_SECTIONS,
        "Original memory sections": ORIGINAL_MEMORY_SECTIONS - ROUND_7_SECTIONS,
        "Research papers / theory / benchmarks": RESEARCH_PAPER_SECTIONS,
    }
    lines.append("| Category | Records | Total cells | Fillable gaps | NA-terminal | Terminal-filled | Gap rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    # Compute per-record per-bucket totals
    for label, secs in cat_buckets.items():
        rec_ids = [rid for rid, s in record_section.items() if s in secs]
        cells = 0
        gaps = 0
        na = 0
        term = 0
        nocite = 0
        shallow = 0
        for rid in rec_ids:
            sec = record_section[rid]
            c = section_class_counts.get(sec, Counter())
        # Sum at the section level instead — counts include all records of that section.
        # Reset accumulators using section-level counts for member sections.
        cells = 0
        for sec in secs:
            cells += sum(section_class_counts.get(sec, Counter()).values())
        gaps = sum(
            section_class_counts.get(sec, Counter())[k]
            for sec in secs
            for k in fillable_classes
        )
        na = sum(
            section_class_counts.get(sec, Counter())["structurally-not-applicable"]
            for sec in secs
        )
        term = sum(
            section_class_counts.get(sec, Counter())["terminal-real-data"]
            for sec in secs
        )
        n_records = sum(
            1 for rid, s in record_section.items() if s in secs
        )
        rate = (gaps / cells * 100) if cells else 0.0
        lines.append(
            f"| {label} | {n_records:,} | {cells:,} | {gaps:,} | "
            f"{na:,} | {term:,} | {rate:.1f}% |"
        )
    lines.append("")

    # ----- bottom-line phase-2 estimate -----
    lines.append("## Phase-2 effort estimate")
    lines.append("")
    fillable = class_counts.get("fillable-and-missing", 0)
    no_cite = class_counts.get("real-data-no-citation", 0)
    shallow = class_counts.get("shallow-prose", 0)
    lines.append(f"- `fillable-and-missing`: {fillable:,}")
    lines.append(f"- `real-data-no-citation`: {no_cite:,}")
    lines.append(f"- `shallow-prose`: {shallow:,}")
    # At ~5 min/cell average for research-and-fill, ~1 min/cell for citation lookup.
    minutes = fillable * 5 + no_cite * 1 + shallow * 3
    hours = minutes / 60
    lines.append("")
    lines.append(
        "At ~5 min/cell to research-and-fill a fillable, ~1 min/cell to locate a citation "
        "for a no-cite real-data row, and ~3 min/cell to enrich shallow prose:"
    )
    lines.append("")
    lines.append(f"- Estimated phase-2 effort: **{minutes:,} min ≈ {hours:,.0f} h**.")
    lines.append("")
    lines.append(
        "(Estimate is wall-clock for a single agent working serially; deep-fill rounds "
        "can parallelise across records.)"
    )
    lines.append("")

    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_OUT.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    main()
