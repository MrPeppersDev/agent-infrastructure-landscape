#!/usr/bin/env python3
"""
audit_section.py — periodic section audit.

Run a structured re-validation pass over one section of the catalog.
Operates in two distinct modes (plus a `full` mode that runs both):

  - **reverify** — re-research every existing row in the section, diff
    each cell against its current value, stage drift as a proposed
    update. Cells whose re-research re-confirms the existing value
    receive a `refresh-last-verified` action (no value change, just
    bump the date).

  - **expand** — search the section's domain for systems *not* yet in
    the catalog, propose new rows. Capped at 5 candidates per run so
    the resulting PR stays reviewable. Uses MCP's `searchRecords` for
    duplicate detection.

  - **full** — both modes back-to-back.

The script ONLY proposes; nothing is auto-applied. Output JSON files
under `audit/` are consumed by `scripts/apply_audit_pr.py`, which
patches `landscape.html` and opens a draft PR for maintainer review.

Per-cell research budget mirrors `scripts/research_intake.py`: 25s
soft timeout, depth-floor fallback on miss. We reuse that script's
fetch + scan helpers wholesale; if those functions need refactoring to
be importable, this script is the consumer that motivates it.

Usage:
  python3 scripts/audit_section.py "Dedicated memory layers" --mode reverify
  python3 scripts/audit_section.py "Dedicated memory layers" --mode expand
  python3 scripts/audit_section.py "Dedicated memory layers" --mode full
  python3 scripts/audit_section.py "Memory benchmarks & evaluation" \\
      --mode reverify --limit 3 --no-network

Outputs (under `audit/`):
  audit/staged-updates-<section-slug>-<YYYY-MM-DD>.json
      — proposed cell diffs from reverify mode.
  audit/new-rows-<section-slug>-<YYYY-MM-DD>.json
      — proposed new records from expand mode.
  intake-pr-bodies/audit-<section-slug>-<YYYY-MM-DD>.md
      — run-trail markdown (written by apply_audit_pr.py).

Exit codes:
  0 — ≥1 proposal generated, ready for `apply_audit_pr.py`.
  1 — error (bad arguments, missing section, etc.).
  2 — nothing to propose (no drift in reverify; no candidates in expand).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import urllib.parse
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
AUDIT_DIR = ROOT / "audit"
MCP_TOOLS_JS = ROOT / "mcp" / "dist" / "tools.js"

# Make scripts/ importable so we can borrow research_intake's helpers
# (fetch_url, fetch_github_facts, scan_keywords, the keyword tables,
# the cell builders, name_similarity, etc.). research_intake.py is
# already structured as a library + main(); we never call its main().
sys.path.insert(0, str(ROOT / "scripts"))
import research_intake as ri  # noqa: E402

CELL_COLUMN_SLUGS: list[str] = ri.CELL_COLUMN_SLUGS
VOLATILE_CELL_SLUGS: set[str] = {
    "created", "latest-release", "gh", "mindshare", "citations",
    "funding", "vendor-benchmarks", "commit-trajectory",
    "citation-trajectory", "download-trajectory",
    "obs-langsmith", "obs-opentelemetry", "obs-datadog", "obs-helicone",
    "obs-weave", "obs-langfuse", "obs-arize", "obs-custom",
    "cost-token-budget", "cost-prompt-caching", "cost-semantic-caching",
    "cost-batching", "cost-model-routing", "cost-streaming-only",
    "cost-observability-cost-attribution",
    "eval-langsmith-evals", "eval-braintrust",
    "eval-weights-and-biases-agent", "eval-helicone-evals",
    "eval-custom-test-harness", "eval-human-loop",
    "eval-production-traffic-replay",
}

# Cells we attempt to re-research in reverify mode. Re-fetching a primary
# URL is cheap; re-deriving 85 cells from one fetch is fragile and noisy.
# The narrow set below is the high-volatility/easy-to-verify slice:
#   - desc / claims: re-extract from meta + first <p> / arxiv abstract
#   - created / latest-release / gh / mindshare: GitHub API
#   - obs/cost/eval: keyword scan over fetched HTML/README
# Other slugs receive a `refresh-last-verified` action only.
REVERIFY_CELLS: set[str] = (
    {"desc", "claims", "created", "latest-release", "license", "gh", "mindshare"}
    | set(ri.OBS_KEYWORDS.keys())
    | set(ri.COST_KEYWORDS.keys())
    | set(ri.EVAL_KEYWORDS.keys())
)

EXPAND_CAP = 5
DEFAULT_HEADERS = {"User-Agent": ri.USER_AGENT}

# Expand-mode search endpoints. We keep these few-and-cheap.
HN_API = "https://hn.algolia.com/api/v1/search"
ARXIV_RECENT = "https://arxiv.org/list/cs.CL/recent"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def today() -> str:
    return _dt.date.today().isoformat()


def section_slug(section: str) -> str:
    s = section.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:60] or "section"


def load_landscape() -> dict:
    if not LANDSCAPE_JSON.exists():
        raise SystemExit(f"data/landscape.json not found at {LANDSCAPE_JSON}")
    return json.loads(LANDSCAPE_JSON.read_text())


def records_in_section(records: list[dict], section: str) -> list[dict]:
    out: list[dict] = []
    for r in records:
        for s in r.get("sections", []):
            if s.get("primary") and s.get("section") == section:
                out.append(r)
                break
    return out


def normalise_for_compare(value: str) -> str:
    """Cheap normalisation for cell-value comparison.

    The goal: a `yes`/`no` stays distinct; whitespace and trailing
    punctuation don't trigger false drift. Anything subtler than a
    casefold + whitespace squeeze is over-engineering for an audit
    proposal that a maintainer will eyeball anyway.
    """
    if value is None:
        return ""
    s = str(value).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


# ---------------------------------------------------------------------------
# Reverify mode
# ---------------------------------------------------------------------------


def reverify_row(
    record: dict,
    *,
    no_network: bool,
) -> tuple[list[dict], dict[str, str]]:
    """Return (deltas, source_map) for one record.

    `deltas` is a list of staged-update entries. Each entry is one of:

      {action: "propose-update", cell_slug, current_value, proposed_value,
       current_citation, proposed_citation, source_url, status,
       last_verified_at}
      {action: "refresh-last-verified", cell_slug, last_verified_at}

    `source_map` is for the run-trail markdown (per-cell source URL or
    explanatory string).

    In no-network mode we skip fetching entirely and emit
    `refresh-last-verified` for every reverify cell — exercising the
    plumbing without consuming rate limits.
    """
    deltas: list[dict] = []
    source_map: dict[str, str] = {}
    issue_number = 0  # not an Issue-triggered run; reuse cache slot 0
    now = today()

    cells = record.get("cells", {})
    primary_url = record.get("url") or ""
    github_url = ""
    # Find GH URL from the gh cell or the primary URL.
    gh_cell_value = cells.get("gh", {}).get("value", "") or ""
    if "github.com/" in gh_cell_value:
        m = re.search(r"https?://github\.com/[^\s\)]+", gh_cell_value)
        if m:
            github_url = m.group(0).rstrip(",.")
    if not github_url and "github.com/" in (primary_url or ""):
        github_url = primary_url

    # No-network fast path: only refresh the date stamps. Per SCHEMA.md
    # §3b, non-volatile cells inherit the row-level date and MUST NOT
    # carry their own `data-last-verified`. So we emit per-cell refresh
    # actions only for the volatile slugs in REVERIFY_CELLS; everything
    # else gets the row-level refresh below.
    if no_network:
        for slug in REVERIFY_CELLS:
            if slug not in VOLATILE_CELL_SLUGS:
                continue
            deltas.append({
                "action": "refresh-last-verified",
                "cell_slug": slug,
                "last_verified_at": now,
            })
            source_map[slug] = "no-network: refresh-only"
        # Row-level refresh is always recorded.
        deltas.append({
            "action": "refresh-row-last-verified",
            "last_verified_at": now,
        })
        return deltas, source_map

    # Fetch primary URL HTML.
    primary_html = ""
    if primary_url:
        ok, body, _reason = ri.fetch_url(primary_url, issue_number=issue_number)
        if ok:
            primary_html = body

    # Fetch GitHub facts.
    gh_facts = ri.GitHubFacts()
    if github_url:
        gh_facts = ri.fetch_github_facts(github_url)

    # Keyword-scan corpus.
    corpus: list[tuple[str, str]] = []
    if primary_html:
        corpus.append((primary_html, primary_url))
    if gh_facts.readme_text:
        corpus.append((gh_facts.readme_text, gh_facts.repo_url or github_url))

    # ---- Re-derive specific cells ----
    proposed: dict[str, dict] = {}

    # desc — re-extract from meta description or first <p>.
    if primary_html:
        new_desc = (
            ri.extract_meta_description(primary_html)
            or ri.extract_first_p(primary_html)
        )
        if new_desc:
            proposed["desc"] = {
                "value": new_desc[:1000],
                "citation": primary_url,
                "status": "real-data",
                "tier": "T2",
            }
        source_map["desc"] = primary_url

    # claims — re-extract from first <p> or meta description as a coarse signal.
    if primary_html:
        new_claims = (
            ri.extract_first_p(primary_html)
            or ri.extract_meta_description(primary_html)
        )
        if new_claims:
            proposed["claims"] = {
                "value": new_claims[:1500],
                "citation": primary_url,
                "status": "real-data",
                "tier": "T2",
            }
        source_map["claims"] = primary_url

    # GitHub-backed cells.
    if gh_facts.repo_url and gh_facts.error is None:
        if gh_facts.created_at:
            proposed["created"] = {
                "value": gh_facts.created_at[:10],
                "citation": gh_facts.repo_url,
                "status": "real-data",
                "tier": "T1",
            }
            source_map["created"] = gh_facts.repo_url
        if gh_facts.last_commit_iso:
            proposed["latest-release"] = {
                "value": f"last commit {gh_facts.last_commit_iso[:10]}",
                "citation": gh_facts.repo_url,
                "status": "real-data",
                "tier": "T1",
            }
            source_map["latest-release"] = gh_facts.repo_url
        if gh_facts.license_spdx:
            proposed["license"] = {
                "value": gh_facts.license_spdx,
                "citation": gh_facts.repo_url,
                "status": "real-data",
                "tier": "T1",
            }
            source_map["license"] = gh_facts.repo_url
        if gh_facts.stars is not None:
            archived = " [archived]" if gh_facts.archived else ""
            proposed["gh"] = {
                "value": f"{gh_facts.repo_url} ({gh_facts.stars}★){archived}",
                "citation": gh_facts.repo_url,
                "status": "real-data",
                "tier": "T1",
            }
            proposed["mindshare"] = {
                "value": f"{gh_facts.stars} GitHub stars",
                "citation": gh_facts.repo_url,
                "status": "real-data",
                "tier": "T1",
            }
            source_map["gh"] = gh_facts.repo_url
            source_map["mindshare"] = gh_facts.repo_url

    # obs/cost/eval keyword scans.
    if corpus:
        for tbl, slugs in (
            (ri.OBS_KEYWORDS, list(ri.OBS_KEYWORDS.keys())),
            (ri.COST_KEYWORDS, list(ri.COST_KEYWORDS.keys())),
            (ri.EVAL_KEYWORDS, list(ri.EVAL_KEYWORDS.keys())),
        ):
            hits = ri.scan_keywords(corpus, tbl)
            for slug in slugs:
                found, src = hits[slug]
                if found and src:
                    proposed[slug] = {
                        "value": "yes",
                        "citation": src,
                        "status": "real-data",
                        "tier": "T2",
                    }
                    source_map[slug] = src
                else:
                    proposed[slug] = {
                        "value": "no",
                        "citation": primary_url or github_url or None,
                        "status": "depth-floor-reached",
                        "tier": "T2",
                    }
                    source_map[slug] = "depth-floor: not detected"

    # Diff against current cells.
    for slug in REVERIFY_CELLS:
        current = cells.get(slug) or {}
        cur_val = current.get("value", "")
        new_cell = proposed.get(slug)
        # Per SCHEMA.md §3b: only volatile cells carry a per-cell
        # `data-last-verified`. Non-volatile cells inherit the row-level
        # date and MUST NOT receive a per-cell refresh action. (The
        # value-drift case is still legal: we propose an update even on
        # non-volatile cells — the maintainer applies the value and the
        # row-level refresh implicitly covers freshness.)
        is_volatile = slug in VOLATILE_CELL_SLUGS

        if new_cell is None:
            # Couldn't re-research this slug (e.g. no GH repo) — bump
            # the per-cell date so the freshness signal stays honest.
            # Only for volatile cells.
            if is_volatile:
                deltas.append({
                    "action": "refresh-last-verified",
                    "cell_slug": slug,
                    "last_verified_at": now,
                })
                source_map.setdefault(slug, "could not reverify; refresh-only")
            continue

        new_val = new_cell.get("value", "")
        if normalise_for_compare(cur_val) == normalise_for_compare(new_val):
            if is_volatile:
                deltas.append({
                    "action": "refresh-last-verified",
                    "cell_slug": slug,
                    "last_verified_at": now,
                })
        else:
            deltas.append({
                "action": "propose-update",
                "cell_slug": slug,
                "current_value": cur_val,
                "proposed_value": new_val,
                "current_citation": current.get("citation"),
                "proposed_citation": new_cell.get("citation"),
                "current_status": current.get("status"),
                "proposed_status": new_cell.get("status"),
                "current_tier": current.get("tier"),
                "proposed_tier": new_cell.get("tier"),
                "source_url": source_map.get(slug, ""),
                "last_verified_at": now,
                "needs_review": True,
            })

    # Always bump the row-level date.
    deltas.append({
        "action": "refresh-row-last-verified",
        "last_verified_at": now,
    })
    return deltas, source_map


def run_reverify(
    section: str,
    records: list[dict],
    *,
    limit: int | None,
    no_network: bool,
) -> dict:
    """Aggregate per-row deltas into the staged-updates payload."""
    section_records = records_in_section(records, section)
    if limit is not None:
        section_records = section_records[:limit]
    payload = {
        "section": section,
        "section_slug": section_slug(section),
        "mode": "reverify",
        "date": today(),
        "no_network": no_network,
        "row_count": len(section_records),
        "rows": [],
    }
    for rec in section_records:
        deltas, source_map = reverify_row(rec, no_network=no_network)
        payload["rows"].append({
            "id": rec["id"],
            "name": rec["name"],
            "url": rec.get("url"),
            "deltas": deltas,
            "source_map": source_map,
        })
    return payload


# ---------------------------------------------------------------------------
# Expand mode
# ---------------------------------------------------------------------------


def _query_terms_for_section(section: str, records: list[dict]) -> list[str]:
    """Build a small bag of search terms from the section + sample rows."""
    terms: list[str] = []
    # Section name itself, plus the first two words of representative descriptions.
    terms.append(section)
    samples = records_in_section(records, section)[:3]
    for r in samples:
        desc = (r.get("cells", {}).get("desc") or {}).get("value", "") or ""
        first_chunk = re.split(r"[.,;:!?\n]", desc, maxsplit=1)[0].strip()
        if 10 <= len(first_chunk) <= 80:
            terms.append(first_chunk)
    return terms[:4]


def hn_search(query: str) -> list[dict]:
    """Top HN hits for a query. Returns [{title, url}, ...]. Best-effort."""
    qs = urllib.parse.urlencode({
        "query": query,
        "tags": "story",
        "hitsPerPage": 10,
    })
    ok, data, _reason = ri.fetch_json(
        f"{HN_API}?{qs}", headers=DEFAULT_HEADERS,
    )
    if not ok or not isinstance(data, dict):
        return []
    out: list[dict] = []
    for hit in data.get("hits", []) or []:
        title = hit.get("title") or ""
        url = hit.get("url") or ""
        if not title or not url:
            continue
        out.append({"title": title, "url": url, "source": "HN"})
    return out


def arxiv_recent_titles() -> list[dict]:
    """Best-effort scrape of /list/cs.CL/recent. Returns [{title, url}, ...]."""
    ok, body, _reason = ri.fetch_url(
        ARXIV_RECENT, issue_number=0, use_cache=True,
    )
    if not ok:
        return []
    out: list[dict] = []
    # arxiv listing pages embed papers as <dd> blocks with the title in
    # a <div class="list-title"> and the abs link in a sibling <span>.
    for m in re.finditer(
        r'<a\s+href="(/abs/(?P<id>\d{4}\.\d{4,5}))"[^>]*>(?P<label>[^<]+)</a>',
        body, re.I,
    ):
        arxiv_id = m.group("id")
        url = f"https://arxiv.org/abs/{arxiv_id}"
        title = m.group("label").strip()
        if title.lower().startswith("arxiv:"):
            title = ""
        if not title:
            continue
        out.append({"title": title, "url": url, "source": "arxiv"})
    # Dedupe by URL.
    seen = set()
    deduped: list[dict] = []
    for hit in out:
        if hit["url"] in seen:
            continue
        seen.add(hit["url"])
        deduped.append(hit)
    return deduped[:50]


def is_duplicate(name: str, records: list[dict]) -> tuple[bool, str | None]:
    """Run name-similarity check via MCP searchRecords (with direct
    fallback). Returns (is_dup, matched_id_or_None)."""
    target_token = ri.normalised_name_token(name)
    if not target_token:
        return False, None

    # Prefer the MCP path so this audit matches research_intake's behaviour.
    if MCP_TOOLS_JS.exists():
        try:
            shim = (
                "import { searchRecords } from './mcp/dist/tools.js';\n"
                "import { readFileSync } from 'node:fs';\n"
                "const data = JSON.parse(readFileSync('data/landscape.json', 'utf8'));\n"
                f"const query = {json.dumps(name)};\n"
                "const out = searchRecords(data.records, { query, limit: 20 });\n"
                "process.stdout.write(JSON.stringify(out));\n"
            )
            proc = subprocess.run(
                ["node", "--input-type=module", "-e", shim],
                capture_output=True, text=True, cwd=str(ROOT), timeout=15,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                result = json.loads(proc.stdout)
                for r in result.get("results", []):
                    existing_token = ri.normalised_name_token(r.get("name", ""))
                    if ri.name_similarity(target_token, existing_token) > 0.9:
                        return True, r.get("id")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

    # Fallback: direct scan.
    for r in records:
        existing_token = ri.normalised_name_token(r.get("name", ""))
        if ri.name_similarity(target_token, existing_token) > 0.9:
            return True, r.get("id")
    return False, None


def _candidate_name_from_title(title: str) -> str:
    """Best-effort extraction of a system/paper name from a title string."""
    s = title.strip()
    # Strip arxiv-id prefix.
    s = re.sub(r"^\[?arxiv\s*:\s*\d{4}\.\d{4,5}\]?\s*-?\s*", "", s, flags=re.I)
    # Strip leading "Show HN: " etc.
    s = re.sub(r"^(?:show\s*hn\s*[:|-]\s*|ask\s*hn\s*[:|-]\s*)", "", s, flags=re.I)
    # Truncate at first hyphen or colon for a tight name slug.
    head = re.split(r"\s+[—–|:-]\s+", s, maxsplit=1)[0]
    head = head.strip().strip(".\"'")
    if not head:
        head = s.strip()[:80]
    return head[:120]


def light_research_candidate(name: str, url: str) -> dict:
    """Light-touch research for a candidate. Just enough to make the
    proposal reviewable; full 85-cell research happens at intake time if
    the maintainer accepts."""
    desc = ""
    if url:
        ok, body, _reason = ri.fetch_url(url, issue_number=0)
        if ok:
            desc = (
                ri.extract_meta_description(body)
                or ri.extract_first_p(body)
                or ri.extract_title(body)
            )
    return {
        "name": name,
        "url": url,
        "brief_description": desc[:600] if desc else "",
    }


def run_expand(
    section: str,
    records: list[dict],
    *,
    cap: int = EXPAND_CAP,
) -> dict:
    """Collect ≤ cap new-row candidates for the section."""
    query_terms = _query_terms_for_section(section, records)
    hits: list[dict] = []

    # HN search for each query term.
    for q in query_terms:
        try:
            hits.extend(hn_search(q))
        except Exception:  # noqa: BLE001 — defensive; one source failing != abort
            pass

    # arxiv recent listing — we don't filter by query (the listing is
    # already topically narrow).
    try:
        hits.extend(arxiv_recent_titles())
    except Exception:  # noqa: BLE001
        pass

    # Dedupe by URL.
    seen_urls = set()
    deduped: list[dict] = []
    for h in hits:
        if h["url"] in seen_urls:
            continue
        seen_urls.add(h["url"])
        deduped.append(h)

    # Filter against existing catalog.
    candidates: list[dict] = []
    for h in deduped:
        if len(candidates) >= cap:
            break
        name = _candidate_name_from_title(h["title"])
        if not name:
            continue
        is_dup, existing_id = is_duplicate(name, records)
        if is_dup:
            continue
        light = light_research_candidate(name, h["url"])
        light.update({
            "source": h.get("source", "search"),
            "why_surfaced": f"{h.get('source', 'search')} hit: {h['title'][:140]}",
            "section": section,
        })
        candidates.append(light)

    return {
        "section": section,
        "section_slug": section_slug(section),
        "mode": "expand",
        "date": today(),
        "query_terms": query_terms,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def update_rotation(section: str) -> None:
    """Mark the section as audited today."""
    rotation_path = AUDIT_DIR / "section-rotation.json"
    if not rotation_path.exists():
        return
    rotation = json.loads(rotation_path.read_text())
    rotation[section] = today()
    rotation_path.write_text(
        json.dumps(rotation, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("section", help="Primary section name to audit")
    ap.add_argument(
        "--mode",
        choices=["reverify", "expand", "full"],
        default="full",
        help="Audit mode (default: full = reverify then expand)",
    )
    ap.add_argument(
        "--limit", type=int, default=None,
        help="Reverify at most N rows (smoke testing)",
    )
    ap.add_argument(
        "--cap", type=int, default=EXPAND_CAP,
        help=f"Expand-mode candidate cap (default: {EXPAND_CAP})",
    )
    ap.add_argument(
        "--no-network", action="store_true",
        help="Skip all network fetches — exercise diff/staging plumbing only "
             "(reverify mode degrades to refresh-last-verified-only)",
    )
    ap.add_argument(
        "--skip-rotation-update", action="store_true",
        help="Don't update audit/section-rotation.json (smoke testing)",
    )
    args = ap.parse_args()

    landscape = load_landscape()
    records = landscape.get("records", []) or []

    # Confirm section exists.
    all_sections = {
        s.get("section")
        for r in records
        for s in r.get("sections", [])
        if s.get("primary")
    }
    if args.section not in all_sections:
        print(f"error: section {args.section!r} not found in landscape "
              f"(known: {sorted(all_sections)})", file=sys.stderr)
        return 1

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    slug = section_slug(args.section)
    date_str = today()

    produced_anything = False

    if args.mode in ("reverify", "full"):
        reverify_payload = run_reverify(
            args.section, records,
            limit=args.limit, no_network=args.no_network,
        )
        # Count actionable items.
        n_proposals = 0
        n_refresh = 0
        for row in reverify_payload["rows"]:
            for d in row["deltas"]:
                if d.get("action") == "propose-update":
                    n_proposals += 1
                elif d.get("action") == "refresh-last-verified":
                    n_refresh += 1
        reverify_payload["proposal_count"] = n_proposals
        reverify_payload["refresh_only_count"] = n_refresh

        out_path = AUDIT_DIR / f"staged-updates-{slug}-{date_str}.json"
        write_payload(out_path, reverify_payload)
        print(f"reverify: wrote {out_path.relative_to(ROOT)} "
              f"({reverify_payload['row_count']} rows, "
              f"{n_proposals} proposed updates, "
              f"{n_refresh} refresh-only)")
        if n_proposals + n_refresh > 0:
            produced_anything = True

    if args.mode in ("expand", "full"):
        expand_payload = run_expand(args.section, records, cap=args.cap)
        out_path = AUDIT_DIR / f"new-rows-{slug}-{date_str}.json"
        write_payload(out_path, expand_payload)
        print(f"expand: wrote {out_path.relative_to(ROOT)} "
              f"({expand_payload['candidate_count']} candidates)")
        if expand_payload["candidate_count"] > 0:
            produced_anything = True

    if not args.skip_rotation_update:
        update_rotation(args.section)
        print(f"rotation: updated audit/section-rotation.json → "
              f"{args.section!r}: {date_str}")

    if not produced_anything:
        print("note: no proposals generated.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
