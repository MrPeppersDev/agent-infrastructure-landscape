#!/usr/bin/env python3
"""
phase_2_cost_mechanical_fill.py — Phase 2 Gate 1 / Phase 3 of 4.

Mechanically populates the five new cost-* cells (PHASE_2_SPEC.html §3.1
/ docs/SCHEMA.md §2.5.7) wherever the existing `pricing` cell makes the
answer obvious. Records that need real text parsing of vendor prose are
left empty — Phase 4 (LLM-judgment fill) picks them up.

Three deterministic buckets:

  Bucket A — Mass N/A propagation
    Records with `pricing.status` in {not-applicable, depth-floor-reached}
    have no commercial offering (research papers, OSS-only projects,
    "searched and found nothing"). All 5 cost cells are marked
    not-applicable mirroring the existing reason.

  Bucket B — Free / OSS detection on real-data pricing text
    Pattern match for "free", "open source", "OSS", "no charge", etc.
    Sets cost-tier=free, cost-pricing-model=free-tier (or self-hosted),
    cost-input/output to 0 USD.

  Bucket C — Subscription / enterprise pricing model
    Pattern match for "per-seat", "subscription", "per-agent",
    "enterprise only", "contact sales". Sets cost-pricing-model to
    "subscription"; cost-input/output to N/A since per-token cost
    cannot be expressed.

Everything else (numeric "$X per Mtok" prose, hybrid pricing,
unparseable strings) is left at `status: "no-data"` for Phase 4.

Provenance: every cell touched here gets a `source: "scrape"` entry
with `script: "scripts/phase_2_cost_mechanical_fill.py"`, `scrape_url`
mirroring the existing pricing cell's citation when present (else the
row's url). `scraped_at` is the run date. The N/A and free/OSS calls
are conservative enough that `verified: true` is appropriate; gates 5+8
catch staleness later.

Idempotent: re-running over an already-filled file is a no-op
(skips cells whose status is no longer `no-data`).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
SCRIPT_REL_PATH = "scripts/phase_2_cost_mechanical_fill.py"

sys.path.insert(0, str(ROOT / "scripts"))
from extract import classify_tier  # noqa: E402  — share the tier heuristic

COST_CELL_SLUGS = [
    "cost-input-usd-per-mtok",
    "cost-output-usd-per-mtok",
    "cost-tier",
    "cost-pricing-model",
    "cost-last-verified",
]

# Pattern matchers on the lower-cased value of the existing `pricing`
# cell. Order matters: enterprise/subscription is checked before free,
# so "free tier; enterprise pricing for production" classifies as
# subscription (the load-bearing claim).

ENTERPRISE_RE = re.compile(
    r"\b(enterprise(?:\s+only|\s+pricing|\s+quote)?|contact\s+sales|"
    r"per[- ]seat|per[- ]agent|per[- ]user|subscription)\b"
)
FREE_OSS_RE = re.compile(
    r"\b(free(?:\s+(?:tier|forever|/\s*open))?|open[- ]?source|"
    r"\boss\b|no\s+charge|community\s+edition|byo[a-z]*\s+only)\b"
)
SELF_HOSTED_RE = re.compile(
    r"\bself[- ]?hosted(?:\s+only)?\b"
)
# Any explicit dollar-numeric pattern means the prose contains real
# per-token / per-request pricing that needs a smarter parser. Defer
# to Phase 4 even if free/OSS keywords also appear (e.g. "$0.14 per
# 1M tokens; OSS weights also free" — the load-bearing claim is the
# numeric tier, not the OSS freebie).
DOLLAR_NUMERIC_RE = re.compile(r"\$\s?\d")


def make_cell(
    value: str,
    citation: str | None,
    status: str,
) -> dict[str, Any]:
    """Build a cell with auto-derived tier — matches the heuristic used
    by `scripts/extract.py:classify_tier()` so the round-trip stays
    byte-stable (gate 2)."""
    tier, _ = classify_tier(citation, status)
    out = OrderedDict()
    out["value"] = value
    out["citation"] = citation
    out["status"] = status
    out["tier"] = tier
    return out


def provenance_entry(
    *,
    scraped_at: str,
    scrape_url: str | None,
    source: str = "scrape",
) -> OrderedDict[str, Any]:
    """Alphabetized entry — matches the round-trip ordering required by
    gate 2 (see phase_2_provenance_backfill.py for the same convention)."""
    if source == "scrape":
        entry = {
            "source": "scrape",
            "verified": True,
            "scraped_at": scraped_at,
            "scrape_url": scrape_url or "",
            "script": SCRIPT_REL_PATH,
        }
    else:
        entry = {"source": "legacy", "verified": True}
    return OrderedDict(sorted(entry.items()))


def classify(pricing_cell: dict[str, Any]) -> str:
    """Return the bucket name for this row.

    Returns one of: "na-propagate", "free", "self-hosted",
    "subscription", "leave-for-phase-4".
    """
    status = pricing_cell.get("status")
    if status in {"not-applicable", "depth-floor-reached"}:
        return "na-propagate"
    if status != "real-data":
        return "leave-for-phase-4"

    value = (pricing_cell.get("value") or "").lower()
    if not value:
        return "leave-for-phase-4"

    # If the prose contains explicit numeric pricing, the load-bearing
    # claim is the per-token tier — defer to Phase 4 even if "free" or
    # "OSS" appears alongside (a mixed-pricing row).
    if DOLLAR_NUMERIC_RE.search(value):
        return "leave-for-phase-4"

    # Order matters per the docstring.
    if ENTERPRISE_RE.search(value):
        return "subscription"
    if SELF_HOSTED_RE.search(value):
        return "self-hosted"
    if FREE_OSS_RE.search(value):
        return "free"
    return "leave-for-phase-4"


def apply_bucket(
    record: dict[str, Any],
    bucket: str,
    today: str,
) -> int:
    """Mutate record's cells + _provenance for this bucket. Return the
    number of cells touched. Skips any cost cell that already has
    non-no-data status (idempotency)."""
    pricing = record.get("cells", {}).get("pricing", {}) or {}
    pricing_citation = pricing.get("citation")
    scrape_url = pricing_citation or record.get("url") or ""

    if bucket == "leave-for-phase-4":
        return 0

    # Pre-derive the desired values per bucket.
    if bucket == "na-propagate":
        # Mirror the pricing cell's status AND value verbatim. Mixing
        # status "not-applicable" with value "searched not found" would
        # break the round-trip — extract.py reclassifies cells with that
        # text to depth-floor-reached based on the value text alone
        # (see extract.py: detect_status()).
        reason = (pricing.get("value") or "").strip() or "not applicable — no commercial offering"
        src_status = pricing.get("status")
        propagated_status = src_status if src_status in {"not-applicable", "depth-floor-reached"} else "not-applicable"
        values = {
            "cost-input-usd-per-mtok": make_cell(reason, pricing_citation, propagated_status),
            "cost-output-usd-per-mtok": make_cell(reason, pricing_citation, propagated_status),
            "cost-tier": make_cell(reason, pricing_citation, propagated_status),
            "cost-pricing-model": make_cell(reason, pricing_citation, propagated_status),
            "cost-last-verified": make_cell(reason, pricing_citation, propagated_status),
        }
        prov_source = "legacy"  # transitive from existing N/A annotation
    elif bucket == "free":
        values = {
            "cost-input-usd-per-mtok": make_cell("0", pricing_citation, "real-data"),
            "cost-output-usd-per-mtok": make_cell("0", pricing_citation, "real-data"),
            "cost-tier": make_cell("free", pricing_citation, "real-data"),
            "cost-pricing-model": make_cell("free-tier", pricing_citation, "real-data"),
            "cost-last-verified": make_cell(today, pricing_citation, "real-data"),
        }
        prov_source = "scrape"
    elif bucket == "self-hosted":
        values = {
            "cost-input-usd-per-mtok": make_cell("not applicable — self-hosted, no per-token cost", pricing_citation, "not-applicable"),
            "cost-output-usd-per-mtok": make_cell("not applicable — self-hosted, no per-token cost", pricing_citation, "not-applicable"),
            "cost-tier": make_cell("free", pricing_citation, "real-data"),
            "cost-pricing-model": make_cell("self-hosted", pricing_citation, "real-data"),
            "cost-last-verified": make_cell(today, pricing_citation, "real-data"),
        }
        prov_source = "scrape"
    elif bucket == "subscription":
        values = {
            "cost-input-usd-per-mtok": make_cell("not applicable — subscription pricing, no per-token cost", pricing_citation, "not-applicable"),
            "cost-output-usd-per-mtok": make_cell("not applicable — subscription pricing, no per-token cost", pricing_citation, "not-applicable"),
            "cost-tier": make_cell("not applicable — subscription pricing, no per-token cost", pricing_citation, "not-applicable"),
            "cost-pricing-model": make_cell("subscription", pricing_citation, "real-data"),
            "cost-last-verified": make_cell(today, pricing_citation, "real-data"),
        }
        prov_source = "scrape"
    else:
        raise ValueError(f"unknown bucket: {bucket!r}")

    touched = 0
    cells = record["cells"]
    prov = record.setdefault("_provenance", OrderedDict())
    if not isinstance(prov, dict):
        prov = OrderedDict()
        record["_provenance"] = prov

    for slug, new_cell in values.items():
        existing = cells.get(slug) or {}
        if existing.get("status") != "no-data":
            # Already filled; honor idempotency.
            continue
        cells[slug] = new_cell
        prov[slug] = provenance_entry(
            scraped_at=today,
            scrape_url=scrape_url if prov_source == "scrape" else None,
            source=prov_source,
        )
        touched += 1

    return touched


def reorder_provenance(landscape: dict[str, Any]) -> None:
    """Re-sort each `_provenance` to match cells iteration order — same
    convention as phase_2_provenance_backfill.py. Required for gate 2."""
    for rec in landscape.get("records") or []:
        prov = rec.get("_provenance")
        if not isinstance(prov, dict) or not prov:
            continue
        cell_order = list((rec.get("cells") or {}).keys())
        rank = {slug: i for i, slug in enumerate(cell_order)}
        rec["_provenance"] = OrderedDict(
            sorted(prov.items(), key=lambda kv: rank.get(kv[0], 1_000_000))
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=LANDSCAPE_JSON)
    ap.add_argument("--dry-run", action="store_true",
                    help="Print bucket counts; do not write.")
    ap.add_argument("--today", default=None,
                    help="Override today's date (YYYY-MM-DD). Default: today UTC.")
    args = ap.parse_args()

    today = args.today or dt.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", today):
        print(f"--today must be YYYY-MM-DD, got {today!r}", file=sys.stderr)
        return 2

    with args.input.open("r", encoding="utf-8") as f:
        landscape = json.load(f)

    bucket_counts: Counter[str] = Counter()
    total_cells_touched = 0
    records_touched = 0

    for rec in landscape.get("records") or []:
        pricing = rec.get("cells", {}).get("pricing", {}) or {}
        bucket = classify(pricing)
        bucket_counts[bucket] += 1
        touched = apply_bucket(rec, bucket, today)
        if touched:
            records_touched += 1
            total_cells_touched += touched

    print("bucket distribution (across all records):")
    for b, n in bucket_counts.most_common():
        print(f"  {b}: {n}")
    print(f"records_touched={records_touched}  "
          f"cost_cells_filled={total_cells_touched}")

    if args.dry_run:
        return 0

    reorder_provenance(landscape)
    with args.input.open("w", encoding="utf-8") as f:
        json.dump(landscape, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {args.input}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
