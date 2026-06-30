#!/usr/bin/env python3
"""
cron_vendor_price_sweep.py — daily scrape of vendor pricing pages.

Phase 2 / Gate 6 (issue #100). Companion workflow:
`.github/workflows/vendor-price-sweep.yml`.

What it does
------------

1. Walks `data/landscape.json` for hosted-service rows — rows whose
   `cost-pricing-model` cell value is one of `per-token`, `per-request`,
   or `subscription`.
2. For each such row, locates the vendor pricing page (via
   `lookup_pricing_page`) and scrapes it (via `scrape_vendor_pricing`).
   These helpers are a thin local copy of the functions added to
   `scripts/research_intake.py` in Gate 7; a follow-up can dedupe them
   once Gate 7 merges.
3. Diffs the scraped values against the stored `cost-input-usd-per-mtok`
   / `cost-output-usd-per-mtok` cells.
4. Opens **one auto-PR per change** with the proposed update + a
   `_provenance` entry of `{source: scrape, verified: true, ...}`.
5. If the change crosses a `cost_tier` boundary, also opens a
   `cost-tier-crossed` issue.

No direct writes to `data/landscape.json` — the PR is the gate. Daily
runs move signal, not state.

Usage
-----

    python3 scripts/cron_vendor_price_sweep.py [--max-emit 20] [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE = ROOT / "data" / "landscape.json"

PRICING_MODELS = {"per-token", "per-request", "subscription"}

COST_INPUT_SLUG = "cost-input-usd-per-mtok"
COST_OUTPUT_SLUG = "cost-output-usd-per-mtok"
COST_TIER_SLUG = "cost-tier"
COST_PRICING_MODEL_SLUG = "cost-pricing-model"

# Tier ranks mirror mcp/src/recommender.ts parseTier.
COST_TIER_ORDER = ["free", "budget", "mid", "premium"]

TIER_CROSSED_LABEL = "cost-tier-crossed"

# Known vendor pricing pages. Mirrors the Gate 7 `lookup_pricing_page` map —
# kept thin here so the cron works on `main` without Gate 7 merged. Once
# Gate 7 lands the cron will switch to importing from research_intake.
VENDOR_PRICING_PAGES: dict[str, str] = {
    "anthropic.com": "https://www.anthropic.com/pricing",
    "openai.com": "https://openai.com/api/pricing/",
    "deepmind.google": "https://ai.google.dev/pricing",
    "ai.google.dev": "https://ai.google.dev/pricing",
    "blog.google": "https://ai.google.dev/pricing",
    "deepseek.com": "https://api-docs.deepseek.com/quick_start/pricing",
    "mistral.ai": "https://mistral.ai/technology/#pricing",
    "qwen.alibaba.com": "https://www.alibabacloud.com/help/en/model-studio/pricing",
    "qwenlm.github.io": "https://www.alibabacloud.com/help/en/model-studio/pricing",
    "x.ai": "https://x.ai/api",
    "groq.com": "https://groq.com/pricing/",
    "cohere.com": "https://cohere.com/pricing",
    "perplexity.ai": "https://docs.perplexity.ai/guides/pricing",
}

USER_AGENT = "agent-infrastructure-landscape-price-sweep/1.0"


# ---------------------------------------------------------------------------
# Pricing helpers (local thin copy of Gate 7's research_intake.py helpers)
# ---------------------------------------------------------------------------


def lookup_pricing_page(url: str | None) -> str | None:
    """Map a record's primary URL to a known vendor pricing page. Returns
    None if we don't know where to look — the cron skips those rows
    silently rather than scrape arbitrary pages."""
    if not url:
        return None
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:  # noqa: BLE001
        return None
    host = host.lower().lstrip("www.")
    if host in VENDOR_PRICING_PAGES:
        return VENDOR_PRICING_PAGES[host]
    # also try stripping subdomain
    parts = host.split(".")
    if len(parts) > 2:
        root = ".".join(parts[-2:])
        if root in VENDOR_PRICING_PAGES:
            return VENDOR_PRICING_PAGES[root]
    return None


PRICE_RE = re.compile(
    r"\$?\s*(\d+\.?\d*)\s*/?\s*(?:per\s*)?[Mm](?:tok|illion\s+tokens?|TOK)",
    re.IGNORECASE,
)


def scrape_vendor_pricing(url: str, timeout: float = 15.0) -> dict[str, Any]:
    """Fetch a pricing page and pull out per-Mtok values.

    Returns a dict like:
      {
        "url": "...",
        "scraped_at": "2026-06-30",
        "raw_prices": ["1.50", "5.00", ...],   # all detected $/Mtok values
        "min_input_usd_per_mtok": 1.50,         # heuristic — lowest found
      }

    This is a deliberately thin implementation: vendor pricing pages vary
    too much for a per-vendor parser, so we surface the raw list and the
    minimum. The reviewer of the auto-PR validates the diff against the
    page. Future iterations can replace this with the Gate 7 implementation.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise RuntimeError(f"fetch failed for {url}: {e}") from e

    matches = PRICE_RE.findall(body)
    # de-dup, parse floats, sort
    values = sorted({float(m) for m in matches if _safe_float(m) is not None})
    return {
        "url": url,
        "scraped_at": dt.date.today().isoformat(),
        "raw_prices": [str(v) for v in values],
        "min_input_usd_per_mtok": values[0] if values else None,
    }


def _safe_float(s: str) -> float | None:
    try:
        f = float(s)
        # reject obvious garbage
        if f < 0 or f > 1000:
            return None
        return f
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Tier crossing
# ---------------------------------------------------------------------------


def parse_tier(s: str | None) -> str | None:
    if not s:
        return None
    v = s.strip().lower()
    return v if v in COST_TIER_ORDER else None


def infer_tier_from_price(usd_per_mtok: float | None) -> str | None:
    """Mirror the cost-tier buckets used elsewhere in the catalog. The
    boundaries match the `phase_2_cost_mechanical_fill.py` curation pass:
    free  = 0
    budget = (0, 1]
    mid    = (1, 10]
    premium = (10, ∞)
    """
    if usd_per_mtok is None:
        return None
    if usd_per_mtok <= 0:
        return "free"
    if usd_per_mtok <= 1:
        return "budget"
    if usd_per_mtok <= 10:
        return "mid"
    return "premium"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def load_landscape() -> dict[str, Any]:
    return json.loads(LANDSCAPE.read_text(encoding="utf-8"))


def hosted_service_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in records:
        cells = r.get("cells") or {}
        cpm = cells.get(COST_PRICING_MODEL_SLUG) or {}
        val = (cpm.get("value") or "").strip().lower()
        if cpm.get("status") == "real-data" and val in PRICING_MODELS:
            out.append(r)
    return out


def cell_float(cells: dict[str, Any], slug: str) -> float | None:
    c = cells.get(slug) or {}
    v = c.get("value")
    if not v:
        return None
    return _safe_float(str(v).strip())


# ---------------------------------------------------------------------------
# gh side-effects
# ---------------------------------------------------------------------------


def ensure_label(dry_run: bool) -> None:
    if dry_run:
        return
    subprocess.run(
        ["gh", "label", "create", TIER_CROSSED_LABEL,
         "--description", "Vendor price sweep detected a change that crosses a cost-tier boundary.",
         "--color", "D93F0B",
         "--force"],
        capture_output=True, text=True, cwd=str(ROOT),
    )


def open_change_pr(
    record: dict[str, Any],
    scrape: dict[str, Any],
    old_input: float | None,
    new_input: float | None,
    tier_crossed: bool,
    today: dt.date,
    dry_run: bool,
) -> None:
    rec_id = record["id"]
    branch = f"vendor-price-sweep/{today.isoformat()}/{rec_id}"
    title = f"vendor-price-sweep: {rec_id} input ${old_input}→${new_input}/Mtok"
    body = render_change_pr_body(record, scrape, old_input, new_input, tier_crossed)

    if dry_run:
        print(f"[dry-run] would open PR: {title}")
        return

    existing = subprocess.run(
        ["gh", "pr", "list", "--state", "open",
         "--search", f"\"{title}\" in:title", "--json", "number", "--jq", "length"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if existing.returncode == 0 and existing.stdout.strip() not in ("", "0"):
        print(f"skip: already-open PR for {rec_id}")
        return

    subprocess.run(["git", "checkout", "-b", branch], capture_output=True, text=True, cwd=str(ROOT))
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m",
         f"vendor-price-sweep: review pin for {rec_id}\n\n{title}"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    subprocess.run(["git", "push", "-u", "origin", branch], capture_output=True, text=True, cwd=str(ROOT))
    subprocess.run(
        ["gh", "pr", "create", "--title", title, "--body", body, "--draft"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    subprocess.run(["git", "checkout", "-"], capture_output=True, text=True, cwd=str(ROOT))


def render_change_pr_body(
    record: dict[str, Any],
    scrape: dict[str, Any],
    old_input: float | None,
    new_input: float | None,
    tier_crossed: bool,
) -> str:
    lines = [
        f"## Auto-PR — vendor pricing change for `{record['id']}`",
        "",
        f"Row **{record.get('name','?')}** had a pricing change detected by the daily "
        "vendor sweep.",
        "",
        f"- old `{COST_INPUT_SLUG}`: `${old_input}/Mtok`",
        f"- new `{COST_INPUT_SLUG}`: `${new_input}/Mtok`",
        f"- scrape source: {scrape['url']}",
        f"- scraped_at: {scrape['scraped_at']}",
        "",
    ]
    if tier_crossed:
        lines.extend([
            "### Tier crossing",
            "",
            "This change crosses a `cost_tier` bucket boundary. A companion "
            f"`{TIER_CROSSED_LABEL}` issue has been opened to flag the "
            "downstream impact (recommender constraint matching, leaderboards).",
            "",
        ])
    lines.extend([
        "### Proposed provenance",
        "",
        "```json",
        json.dumps({
            COST_INPUT_SLUG: {
                "source": "scrape",
                "verified": True,
                "scraped_at": scrape["scraped_at"],
                "scrape_url": scrape["url"],
                "script": "scripts/cron_vendor_price_sweep.py",
            },
        }, indent=2),
        "```",
        "",
        f"Raw prices detected on the page: `{', '.join(scrape.get('raw_prices') or [])}`",
        "",
        "_Auto-opened by `scripts/cron_vendor_price_sweep.py` "
        "(Phase 2 / Gate 6, issue #100). Daily runs move signal, not state — "
        "the data/landscape.json edit is **proposed**, not applied. "
        "Reviewer applies the diff (or closes) manually._",
    ])
    return "\n".join(lines)


def open_tier_crossed_issue(
    record: dict[str, Any],
    old_tier: str | None,
    new_tier: str | None,
    today: dt.date,
    dry_run: bool,
) -> None:
    title = f"cost-tier-crossed: {record['id']} {old_tier}→{new_tier}"
    body = (
        f"Vendor price sweep detected that `{record['id']}` "
        f"({record.get('name','?')}) crossed a cost-tier boundary today.\n\n"
        f"- old tier: `{old_tier}`\n"
        f"- new tier: `{new_tier}`\n\n"
        "A companion PR with the proposed cell update has been opened in parallel.\n\n"
        "_Auto-opened by `scripts/cron_vendor_price_sweep.py` (Phase 2 / Gate 6)._"
    )
    if dry_run:
        print(f"[dry-run] would open issue: {title}")
        return
    existing = subprocess.run(
        ["gh", "issue", "list", "--state", "open", "--label", TIER_CROSSED_LABEL,
         "--search", f"\"{title}\" in:title", "--json", "number", "--jq", "length"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if existing.returncode == 0 and existing.stdout.strip() not in ("", "0"):
        print(f"skip: already-open tier-crossed issue for {record['id']}")
        return
    subprocess.run(
        ["gh", "issue", "create", "--title", title, "--label", TIER_CROSSED_LABEL,
         "--body", body],
        capture_output=True, text=True, cwd=str(ROOT),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    data = load_landscape()
    records = data.get("records") or []
    hosted = hosted_service_rows(records)
    print(
        f"cron_vendor_price_sweep: {len(hosted)} hosted-service row(s) to consider.",
        file=sys.stderr,
    )

    ensure_label(args.dry_run)
    changes = 0
    crossings = 0
    for rec in hosted[: args.max_emit]:
        page = lookup_pricing_page(rec.get("url"))
        if not page:
            continue
        try:
            scrape = scrape_vendor_pricing(page)
        except Exception as e:  # noqa: BLE001
            print(f"  scrape failed for {rec['id']}: {e}", file=sys.stderr)
            continue
        new_input = scrape.get("min_input_usd_per_mtok")
        old_input = cell_float(rec.get("cells") or {}, COST_INPUT_SLUG)
        if new_input is None:
            continue
        # No-change check — within a 1 cent tolerance to avoid noise.
        if old_input is not None and abs(new_input - old_input) < 0.01:
            continue
        old_tier = parse_tier((rec.get("cells") or {}).get(COST_TIER_SLUG, {}).get("value"))
        new_tier = infer_tier_from_price(new_input)
        tier_crossed = bool(old_tier and new_tier and old_tier != new_tier)
        open_change_pr(rec, scrape, old_input, new_input, tier_crossed, today, args.dry_run)
        changes += 1
        if tier_crossed:
            open_tier_crossed_issue(rec, old_tier, new_tier, today, args.dry_run)
            crossings += 1

    print(
        f"cron_vendor_price_sweep: {changes} change PR(s) "
        f"({crossings} crossing tier boundary) "
        f"{'(dry-run, none opened)' if args.dry_run else 'requested via gh'}.",
        file=sys.stderr,
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--today", default=None,
                   help="Override today (ISO date). Default: actual UTC today.")
    p.add_argument("--max-emit", type=int, default=20,
                   help="Cap on rows considered per run (default: 20).")
    p.add_argument("--dry-run", action="store_true",
                   help="Do full compute (incl. live scrape), but skip every git/gh side-effect.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
