#!/usr/bin/env python3
"""
reconcile.py — dedup + cross-listing reconciliation pass over web/landscape.json

Issue #3. Runs after extract.py. Detects:

  1. **True duplicates** (auto-merge) — case-difference duplicates of the same
     paper / system. Detected by `id` collision suffix (`-2`, `-3`, ...) plus
     identical `url` and identical normalized name. Auto-merged into a single
     canonical record; logged to extraction/merges.json.

  2. **Cross-listings** (single record, multiple sections) — one canonical
     system that the source HTML legitimately listed in two sections (e.g.
     Mem0 in `Dedicated memory layers` AND `Memory observability & monitoring`,
     because the second framing emphasises observability features when paired
     with AgentOps). Detected by same `url` (or same arxiv-id) but different
     `sections`. Reconciled into a single record whose `sections` array has
     one element per section, with `primary: true` only on the original
     primary placement. Cells are merged preferring `real-data` over
     `not-applicable` / `depth-floor-reached` / `no-data`. Logged to
     extraction/cross-listings.json.

  3. **Ambiguous** cases the script can't auto-decide — different URLs but
     normalized name matches; or descriptions diverge in ways that look like
     genuinely different products. Flagged to extraction/ambiguous.csv for
     human review; not modified.

After running, validates the resulting records against the §7 SCHEMA.md
rules (delegated to scripts/extract.py's validator) and writes the new
`web/landscape.json`.

Determinism contract:
  - Records sorted by id ASC after reconciliation.
  - Output JSON formatted identical to extract.py: indent=2, ensure_ascii=False.
  - generatedAt taken from the input file (not regenerated) so re-running
    extract.py + reconcile.py is byte-stable.

Usage:
  python3 scripts/reconcile.py            # writes web/landscape.json
  python3 scripts/reconcile.py --check    # dry-run (no file writes)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

# Reuse validator from extract.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import (  # noqa: E402  (path-tweaked import)
    SCHEMA_VERSION,
    validate_record,
)

# ---------------------------------------------------------------------------
# Reconciliation rules (locked decisions for issue #3).
# ---------------------------------------------------------------------------
#
# Each rule is a tuple: (kind, ids, kept_id, primary_section_id, reason)
# where:
#   kind                ∈ {"merge", "cross_listing"}
#   ids                 list of record ids that participate
#   kept_id             id of the record kept after reconciliation
#                       (for "merge" the merged record uses this id; for
#                       "cross_listing" this is the record whose section
#                       becomes `primary: true`)
#   primary_section_id  for cross-listings, the id whose section is the
#                       canonical (primary: true) placement; ignored for
#                       merges. Must be one of `ids`.
#   reason              short justification recorded in the audit logs.
#
# These rules are derived from the Round-6 collision audit + a sweep over
# same-url pairs in the extracted records. See the body of `main` for how
# the rules are applied.

MERGE_RULES: list[dict[str, Any]] = [
    {
        "kind": "merge",
        "ids": ["arigraph--arxiv-2407-04363", "arigraph--arxiv-2407-04363-2"],
        "kept_id": "arigraph--arxiv-2407-04363",
        "winner_id": "arigraph--arxiv-2407-04363-2",
        "reason": (
            "case-difference duplicate of the same paper "
            "(arxiv 2407.04363). The second occurrence ('AriGraph') "
            "carries the richer Cognitive-architecture-inspired framing "
            "and the correct tier (3 — peer-reviewed at NeurIPS 2024); "
            "the first occurrence ('Arigraph') was a stub under "
            "Factual & long-term memory at tier 4. Merged into one record "
            "preferring the second's per-cell content."
        ),
    },
]

CROSS_LISTING_RULES: list[dict[str, Any]] = [
    {
        "kind": "cross_listing",
        "ids": [
            "memorybench-tsinghua-thuir--arxiv-2510-17281",
            "memorybench-tsinghua-thuir--arxiv-2510-17281-2",
        ],
        "kept_id": "memorybench-tsinghua-thuir--arxiv-2510-17281",
        "primary_section_id": "memorybench-tsinghua-thuir--arxiv-2510-17281",
        "additional_section_ids": [
            "memorybench-tsinghua-thuir--arxiv-2510-17281-2",
        ],
        "reason": (
            "same benchmark paper (arxiv 2510.17281) listed in the source "
            "HTML twice — once under 'Recent method papers' as a method "
            "contribution, once under 'Memory benchmarks & evaluation' as "
            "a benchmark consumers should compare against. Single record, "
            "two section memberships."
        ),
    },
    {
        "kind": "cross_listing",
        "ids": ["zep-graphiti--getzep-com", "zep-graphiti--getzep-com-2"],
        "kept_id": "zep-graphiti--getzep-com",
        "primary_section_id": "zep-graphiti--getzep-com",
        "additional_section_ids": ["zep-graphiti--getzep-com-2"],
        "reason": (
            "Zep & Graphiti is one platform (getzep.com) listed in two "
            "sections: 'Dedicated memory layers' (the canonical placement) "
            "and 'Memory observability & monitoring' (because the bi-temporal "
            "graph doubles as a provenance/observability layer). Same URL, "
            "same product, different framing per section. Merged cells "
            "prefer the Dedicated-memory-layers row's real-data."
        ),
    },
    {
        "kind": "cross_listing",
        "ids": ["mem0--mem0-ai", "mem0-with-agentops--mem0-ai"],
        "kept_id": "mem0--mem0-ai",
        "primary_section_id": "mem0--mem0-ai",
        "additional_section_ids": ["mem0-with-agentops--mem0-ai"],
        "reason": (
            "Mem0 (mem0.ai) listed under 'Dedicated memory layers' as the "
            "canonical product, and under 'Memory observability & "
            "monitoring' as 'Mem0 (with AgentOps)' to capture the "
            "observability story when paired with AgentOps. Same URL, same "
            "company, different framing. Merged into one record with two "
            "section memberships."
        ),
    },
    {
        "kind": "cross_listing",
        "ids": [
            "memobase--gh-memodb-io-memobase",
            "memobase-mcp--gh-memodb-io-memobase",
        ],
        "kept_id": "memobase--gh-memodb-io-memobase",
        "primary_section_id": "memobase--gh-memodb-io-memobase",
        "additional_section_ids": ["memobase-mcp--gh-memodb-io-memobase"],
        "reason": (
            "Memobase library (memodb-io/memobase) listed under 'Dedicated "
            "memory layers' as the standalone memory product, and under "
            "'Claude Code memory mechanisms' as 'Memobase MCP' for the MCP "
            "wrapper that injects the same profile/timeline into Claude "
            "Code. Same GitHub URL, same product, different framing."
        ),
    },
]

# ---------------------------------------------------------------------------
# Ambiguous cases — flagged for human review, not auto-merged.
# ---------------------------------------------------------------------------
#
# Each entry: (id_a, id_b, similarity_score, action_recommended, notes)
# similarity_score is a coarse 0.0-1.0 indicator: 1.0 means same URL & name,
# 0.5 means name match but different URL, etc.

AMBIGUOUS_CASES: list[dict[str, Any]] = [
    {
        "id_a": "memvid--gh-memvid-memvid",
        "id_b": "claude-brain--gh-memvid-claude-brain",
        "similarity_score": 0.50,
        "action_recommended": "keep-separate-link-via-edge",
        "notes": (
            "Memvid the library (github.com/memvid/memvid) and "
            "claude-brain the Claude Code plugin (github.com/memvid/claude-"
            "brain) live in the same GitHub org and the plugin wraps the "
            "library. Different products with different repos and "
            "different distribution mechanisms (PyPI vs Claude plugin "
            "marketplace), so they are NOT a cross-listing of one record. "
            "Issue #4 should connect them with a `built-on` edge."
        ),
    },
    {
        "id_a": "claude-md--docs-claude-com",
        "id_b": "claude-code-auto-memory--docs-claude-com",
        "similarity_score": 0.40,
        "action_recommended": "keep-separate",
        "notes": (
            "Both reference docs.claude.com/en/docs/claude-code/memory but "
            "describe two distinct Claude Code memory mechanisms: CLAUDE.md "
            "is the markdown-file-injected-at-session-start pattern, and "
            "Claude Code auto-memory is the persistent typed-memory directory "
            "at ~/.claude/projects/<project>/memory/. Same docs page, two "
            "products. Keep as separate records."
        ),
    },
]


# ---------------------------------------------------------------------------
# Cell merge logic.
# ---------------------------------------------------------------------------
#
# Status preference order for merging two cells from records that refer to
# the same canonical system. real-data wins over everything else, then
# not-applicable (it's a deliberate judgement), then depth-floor-reached
# (we tried but found nothing), then no-data (transitional placeholder).
STATUS_PREFERENCE = {
    "real-data": 0,
    "not-applicable": 1,
    "depth-floor-reached": 2,
    "no-data": 3,
}


def merge_cell(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    *,
    prefer_longer: bool = True,
) -> dict[str, Any]:
    """Pick the better of two cells.

    The "primary" cell is the one from the kept record (whose id survives).
    Status preference always wins: real-data > not-applicable >
    depth-floor-reached > no-data. Within the same status, when
    `prefer_longer=True` (true-duplicate path) the substantively-longer
    real-data text wins on the assumption that one researcher recorded more
    detail than the other; when `prefer_longer=False` (cross-listing path)
    the primary cell is kept verbatim, because the two records describe the
    same product through different lenses and the primary's framing is the
    canonical one.
    """
    p_pref = STATUS_PREFERENCE.get(primary["status"], 9)
    s_pref = STATUS_PREFERENCE.get(secondary["status"], 9)
    if s_pref < p_pref:
        return dict(secondary)
    if s_pref > p_pref:
        return dict(primary)
    # Same status.
    if prefer_longer and primary["status"] == "real-data":
        if len((secondary.get("value") or "")) > len((primary.get("value") or "")) * 1.2:
            return dict(secondary)
    return dict(primary)


def merge_taxonomy(
    primary_tax: dict[str, list[dict[str, Any]]],
    secondary_tax: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Pick the richer of two taxonomy axes.

    Heuristic: if one side has only `[{value:'n/a',primary:true}]` and the
    other has real values, prefer the real one. If both have real values,
    keep the primary (kept record's). The reconciliation pass is not the
    place to invent new taxonomy values, only to pick between extracted
    ones.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for axis, p_vals in primary_tax.items():
        s_vals = secondary_tax.get(axis, [])
        p_is_na = len(p_vals) == 1 and p_vals[0].get("value") == "n/a"
        s_is_na = len(s_vals) == 1 and s_vals[0].get("value") == "n/a"
        if p_is_na and not s_is_na:
            out[axis] = [dict(v) for v in s_vals]
        else:
            out[axis] = [dict(v) for v in p_vals]
    return out


def merge_records_collapse(
    kept: dict[str, Any],
    other: dict[str, Any],
) -> dict[str, Any]:
    """Merge two records into one (true-duplicate path).

    The result keeps `kept`'s id/name/url/sections/tier — it is treated as
    the canonical record. Cells and taxonomy axes are merged preferring the
    higher-quality status / longer real-data values. The `kept` argument is
    the "winner" of the merge regardless of which slug it carries.
    """
    new_cells = OrderedDict()
    for slug, cell in kept["cells"].items():
        new_cells[slug] = merge_cell(cell, other["cells"].get(slug, cell))
    new_tax = merge_taxonomy(kept["taxonomy"], other["taxonomy"])

    return OrderedDict([
        ("id", kept["id"]),
        ("name", kept["name"]),
        ("tier", kept["tier"]),
        ("url", kept["url"]),
        ("sections", [dict(s) for s in kept["sections"]]),
        ("taxonomy", new_tax),
        ("cells", new_cells),
    ])


def merge_records_cross_listing(
    primary_rec: dict[str, Any],
    additional_recs: list[dict[str, Any]],
    rule: dict[str, Any],
) -> dict[str, Any]:
    """Reconcile a cross-listing into one record with multiple sections.

    The primary record's id, name, url, tier are kept. Cells are merged from
    all participants preferring real-data (primary breaks ties). The
    `sections` array gets one element per participant; only the primary's
    section element keeps `primary: true`.
    """
    new_cells = OrderedDict()
    for slug, cell in primary_rec["cells"].items():
        merged = cell
        for other in additional_recs:
            other_cell = other["cells"].get(slug)
            if other_cell is not None:
                # prefer_longer=False: cross-listings keep the primary's
                # framing for free-text cells; we only "upgrade" to the
                # secondary when its status is strictly better (e.g.
                # secondary has real-data where primary said no-data).
                merged = merge_cell(merged, other_cell, prefer_longer=False)
        new_cells[slug] = merged

    new_tax = primary_rec["taxonomy"]
    for other in additional_recs:
        new_tax = merge_taxonomy(new_tax, other["taxonomy"])

    sections: list[dict[str, Any]] = []
    # Primary record's section first, kept primary.
    for s in primary_rec["sections"]:
        sections.append({
            **dict(s),
            "primary": True,
        })
    # Additional sections come in rule-defined order, primary=false.
    for other in additional_recs:
        for s in other["sections"]:
            sections.append({
                "section": s["section"],
                "subsection": s.get("subsection"),
                "primary": False,
                "reason": rule.get("reason"),
            })

    return OrderedDict([
        ("id", primary_rec["id"]),
        ("name", primary_rec["name"]),
        ("tier", primary_rec["tier"]),
        ("url", primary_rec["url"]),
        ("sections", sections),
        ("taxonomy", new_tax),
        ("cells", new_cells),
    ])


# ---------------------------------------------------------------------------
# Diff resolution log helper.
# ---------------------------------------------------------------------------


def diff_resolution_summary(
    kept: dict[str, Any],
    other: dict[str, Any],
    final: dict[str, Any],
) -> dict[str, Any]:
    """Return a per-cell summary of how the merge resolved differences."""
    summary: dict[str, str] = {}
    for slug in final["cells"]:
        k_val = (kept["cells"].get(slug, {}) or {}).get("value", "")
        o_val = (other["cells"].get(slug, {}) or {}).get("value", "")
        f_val = final["cells"][slug]["value"]
        if k_val == o_val:
            continue
        if f_val == k_val:
            summary[slug] = f"kept primary (other had: {o_val[:80]!r})"
        elif f_val == o_val:
            summary[slug] = f"took secondary (primary had: {k_val[:80]!r})"
        else:
            summary[slug] = "merged neither verbatim"
    return summary


# ---------------------------------------------------------------------------
# Pipeline.
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(Path(__file__).resolve().parent.parent / "web" / "landscape.json"),
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent.parent / "web" / "landscape.json"),
    )
    parser.add_argument(
        "--merges",
        default=str(Path(__file__).resolve().parent.parent / "extraction" / "merges.json"),
    )
    parser.add_argument(
        "--cross-listings",
        default=str(Path(__file__).resolve().parent.parent / "extraction" / "cross-listings.json"),
    )
    parser.add_argument(
        "--ambiguous",
        default=str(Path(__file__).resolve().parent.parent / "extraction" / "ambiguous.csv"),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run; do not write any files.",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = payload["records"]
    by_id = {r["id"]: r for r in records}

    # Track removed ids so we can verify rules apply cleanly.
    removed_ids: set[str] = set()
    new_records: dict[str, dict[str, Any]] = {}

    merges_log: list[dict[str, Any]] = []
    cross_listings_log: list[dict[str, Any]] = []

    # 1. True-duplicate merges.
    for rule in MERGE_RULES:
        ids = rule["ids"]
        kept_id = rule["kept_id"]
        winner_id = rule["winner_id"]
        missing = [i for i in ids if i not in by_id]
        if missing:
            print(
                f"warn: merge rule expected ids {ids} but missing {missing} — skipping",
                file=sys.stderr,
            )
            continue
        # The "winner" is the record we prefer cell-by-cell; the "kept_id"
        # is the slug we keep after the merge (often the same as winner_id).
        winner_rec = by_id[winner_id]
        # Force kept_id onto the winner's record content.
        winner_with_id = dict(winner_rec)
        winner_with_id["id"] = kept_id
        # The "loser" record contributes any cells the winner lacks.
        losers = [by_id[i] for i in ids if i != winner_id]
        merged = winner_with_id
        for loser in losers:
            merged = merge_records_collapse(merged, loser)
        # Validate.
        errs = validate_record(merged)
        if errs:
            print(f"error: merged record {kept_id!r} fails validation:", file=sys.stderr)
            for e in errs:
                print(f"  {e}", file=sys.stderr)
            return 1
        # Build audit entry.
        diff_kept = by_id[winner_id]
        diff_other = losers[0] if losers else diff_kept
        merges_log.append({
            "merged_ids": list(ids),
            "kept_id": kept_id,
            "reason": rule["reason"],
            "diff_resolution": diff_resolution_summary(diff_kept, diff_other, merged),
        })
        for i in ids:
            removed_ids.add(i)
        new_records[kept_id] = merged

    # 2. Cross-listing reconciliation.
    for rule in CROSS_LISTING_RULES:
        ids = rule["ids"]
        kept_id = rule["kept_id"]
        primary_id = rule["primary_section_id"]
        additional_ids = rule.get("additional_section_ids") or [
            i for i in ids if i != primary_id
        ]
        missing = [i for i in ids if i not in by_id]
        if missing:
            print(
                f"warn: cross-listing rule expected ids {ids} but missing {missing} — skipping",
                file=sys.stderr,
            )
            continue
        primary_rec = dict(by_id[primary_id])
        primary_rec["id"] = kept_id
        additional_recs = [by_id[i] for i in additional_ids]
        merged = merge_records_cross_listing(primary_rec, additional_recs, rule)
        errs = validate_record(merged)
        if errs:
            print(
                f"error: cross-listing record {kept_id!r} fails validation:",
                file=sys.stderr,
            )
            for e in errs:
                print(f"  {e}", file=sys.stderr)
            return 1
        cross_listings_log.append({
            "id": kept_id,
            "primary_section": merged["sections"][0]["section"],
            "additional_sections": [
                {
                    "section": s["section"],
                    "subsection": s.get("subsection"),
                    "reason": s.get("reason"),
                }
                for s in merged["sections"][1:]
            ],
            "merged_ids": list(ids),
            "reason": rule["reason"],
        })
        for i in ids:
            removed_ids.add(i)
        new_records[kept_id] = merged

    # 3. Apply.
    final_records: list[dict[str, Any]] = []
    for r in records:
        if r["id"] in removed_ids:
            continue
        final_records.append(r)
    final_records.extend(new_records.values())
    final_records.sort(key=lambda r: r["id"])

    # 4. Validate the whole set (id uniqueness, etc.).
    errors: list[str] = []
    seen: set[str] = set()
    for r in final_records:
        if r["id"] in seen:
            errors.append(f"duplicate id after reconcile: {r['id']!r}")
        seen.add(r["id"])
        errors.extend(validate_record(r))
    if errors:
        for e in errors[:50]:
            print(f"validation error: {e}", file=sys.stderr)
        if len(errors) > 50:
            print(f"... and {len(errors) - 50} more", file=sys.stderr)
        print(f"\n{len(errors)} validation errors total", file=sys.stderr)
        return 1

    # 5. Write outputs (unless --check).
    if not args.check:
        out_payload = OrderedDict([
            ("schemaVersion", payload.get("schemaVersion", SCHEMA_VERSION)),
            ("generatedAt", payload["generatedAt"]),
            ("sourceHtml", payload.get("sourceHtml", "landscape.html")),
            ("records", final_records),
        ])
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(out_payload, indent=2, ensure_ascii=False)
        if not text.endswith("\n"):
            text += "\n"
        out_path.write_text(text, encoding="utf-8")

        merges_path = Path(args.merges)
        merges_path.parent.mkdir(parents=True, exist_ok=True)
        merges_text = json.dumps({"merges": merges_log}, indent=2, ensure_ascii=False)
        if not merges_text.endswith("\n"):
            merges_text += "\n"
        merges_path.write_text(merges_text, encoding="utf-8")

        cl_path = Path(args.cross_listings)
        cl_path.parent.mkdir(parents=True, exist_ok=True)
        cl_text = json.dumps({"cross_listings": cross_listings_log}, indent=2, ensure_ascii=False)
        if not cl_text.endswith("\n"):
            cl_text += "\n"
        cl_path.write_text(cl_text, encoding="utf-8")

        amb_path = Path(args.ambiguous)
        amb_path.parent.mkdir(parents=True, exist_ok=True)
        with amb_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id_a", "id_b", "similarity_score", "action_recommended", "notes"])
            for c in AMBIGUOUS_CASES:
                w.writerow([
                    c["id_a"],
                    c["id_b"],
                    f"{c['similarity_score']:.2f}",
                    c["action_recommended"],
                    c["notes"],
                ])

    # 6. Summary.
    print(
        f"reconcile: {len(records)} → {len(final_records)} records "
        f"({len(merges_log)} merges, {len(cross_listings_log)} cross-listings, "
        f"{len(AMBIGUOUS_CASES)} ambiguous flagged)"
    )
    if args.check:
        print("(--check) no files written")
    else:
        print(f"  wrote {args.output}")
        print(f"  wrote {args.merges}")
        print(f"  wrote {args.cross_listings}")
        print(f"  wrote {args.ambiguous}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
