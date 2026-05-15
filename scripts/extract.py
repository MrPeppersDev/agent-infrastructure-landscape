#!/usr/bin/env python3
"""
extract.py — landscape.html → data/landscape.json

Parses every data row from landscape.html into the structured per-record schema
defined in docs/SCHEMA.md, validates each record against the §7 rules, and
writes the result to data/landscape.json.

Determinism contract:
  - Records are sorted by id ASC.
  - Inside each record, taxonomy axes and sections preserve document order.
  - Inside each cell, the citation is the first <a class="cite"> href.
  - generatedAt is fixed (read from env EXTRACT_GENERATED_AT, else default
    constant) so that round-tripping the script twice yields byte-identical
    output. The spec calls this out as a hard requirement.

Usage:
  python3 scripts/extract.py            # writes data/landscape.json
  python3 scripts/extract.py --check    # writes to a temp file and diffs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

# ---------------------------------------------------------------------------
# Schema constants — kept in sync with docs/SCHEMA.md.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0.0"
# Fixed timestamp so the extractor is byte-stable across runs.
# Override with env EXTRACT_GENERATED_AT (ISO-8601 Zulu) when re-stamping
# is intentional.
DEFAULT_GENERATED_AT = "2026-05-07T00:00:00Z"

# In document order, the 85 cell column slugs (everything except `name`,
# the 7 `tax-*` axes, and the implicit `name` column).
#
# Columns 61-68 (the `obs-*` family) were appended in T1-1 (issue #39)
# to record which third-party observability integrations each product
# supports. See docs/SCHEMA.md §2.5.1 for semantics.
#
# Columns 69-75 (the `cost-*` family) were appended in T1-3 (issue #41)
# to record cost-control / token-economics governance features. See
# docs/SCHEMA.md §2.5.2 for semantics.
#
# Columns 76-82 (the `eval-*` family) were appended in T1-2 (issue #40)
# to record eval-tooling integrations. The catalog frames this as the
# observability-vs-eval gap (89% obs adoption vs 52% eval per LangChain
# State of Agent Engineering 2025). See docs/SCHEMA.md §2.5.3 for
# semantics.
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
    # T1-1 observability columns (issue #39).
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

# Sections that legitimately have subsections (per §2.3 of the schema).
SECTIONS_WITH_SUBS = {
    "Recent method papers — theorized, no distinct product",
    "Vertical / domain-specific AI memory",
    "Use-case-specific agent harnesses",
    # New subsection added in Round 16 (2026-05-13 game/interactive-env sweep)
    "Memory benchmarks & evaluation",
}

# Canonical section names — taken from §2.3 in document order. Used by
# validation only; producer reads them straight from the HTML so no
# reconciliation is needed.
CANONICAL_SECTIONS = {
    "Dedicated memory layers",
    "Framework-embedded memory",
    "Platform-provider memory",
    "Coding-agent memory",
    "Browser-agent memory",
    "Personal AI / PKM / lifelogging memory",
    "Voice-first / wearable AI memory",
    "Research / specialised systems",
    "Recent method papers — theorized, no distinct product",
    "Retrieval-as-memory hybrids",
    "File-backed / editor paradigms",
    "Claude Code memory mechanisms",
    "Knowledge-graph platforms",
    "Vector-database infrastructure",
    "Enterprise-search adjacencies",
    "Vertical / domain-specific AI memory",
    "Memory benchmarks & evaluation",
    "Memory observability & monitoring",
    "Memory governance, privacy & safety",
    "Theoretical / informal — ideas without a paper",
    # New sections added in Round 7 (2026-05-12 scope expansion)
    "Training infrastructure",
    "Search platforms (non-memory)",
    "Agent frameworks (no first-party memory layer)",
    "Inference platforms & gateways",
    "Embedding & reranker services",
    "Evaluation & observability platforms",
    # New section added in Round 11 (2026-05-13 agentic-harness sweep)
    "Agent IDEs & coding harnesses",
    # New sections added in Round 12 (2026-05-13 agentic-expansion sweep)
    "Computer-use & desktop agents",
    "Voice agent platforms",
    "Robotics foundation models & agent stacks",
    # New section added in Round 13 (2026-05-13 use-case-vertical agent harness sweep)
    "Use-case-specific agent harnesses",
    # New sections added in Round 15 (2026-05-13 substrate / orchestration / sandbox sweep)
    "Foundation models (substrate reference)",
    "Multi-agent orchestration platforms",
    "AI sandbox & runtime environments",
}

# Status enum values.
STATUS_VALUES = {"real-data", "not-applicable", "depth-floor-reached", "no-data", "estimate"}

# Claim-tier values — see SCHEMA.md §3a.
CLAIM_TIERS = {"T1", "T2", "T3"}

# GitHub URL pattern used by the tier heuristic — anchored at the start so
# only cells whose citation IS a github.com link get the T1 tier.
TIER_GITHUB_URL_RE = re.compile(r"^https?://github\.com/", re.IGNORECASE)

# ISO date used by data-last-verified attributes (SCHEMA.md §3b).
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Decay-cause enum (SCHEMA.md §3c, issue #56). When `data-decay-cause` is
# present on a <tr>, it MUST be one of these seven values.
DECAY_CAUSE_VALUES = {
    "acquired",
    "pivoted",
    "unfunded",
    "lost-benchmark-race",
    "superseded",
    "archived",
    "unknown",
}

# Volatile cell slugs (SCHEMA.md §3b). The same set is repeated in
# scripts/render.py and scripts/backfill_verified_at.py. Cells outside
# this set inherit the row-level last_verified_at — they don't carry
# their own attribute and extract.py drops any per-cell last_verified_at
# field for non-volatile slugs to keep the JSON canonical.
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

# id regex from §7.1.6.
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*(--[a-z0-9]+(-[a-z0-9]+)*)?$")

ARXIV_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(?P<id>\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)
GITHUB_RE = re.compile(
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/?#]+)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Slug helpers (§2.1)
# ---------------------------------------------------------------------------


def name_slug(name: str) -> str:
    """Lowercase, alnum-only with `-` separators, max-64 on `-` boundary."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    s = re.sub(r"-+", "-", s)
    if len(s) > 64:
        cut = s[:64]
        # trim back to the last `-` boundary if we'd cut a token
        if "-" in cut and not s[64:65] == "-":
            cut = cut.rsplit("-", 1)[0]
        s = cut.strip("-")
    return s


def host_slug(url: str) -> str:
    """URL's host minus leading `www.`, dots → `-`."""
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host.replace(".", "-")


def source_suffix(url: str | None) -> str | None:
    """Compute the `--<source-suffix>` portion of an id, sans the leading `--`."""
    if not url:
        return None
    m = ARXIV_RE.search(url)
    if m:
        arxiv_id = m.group("id").replace(".", "-")
        return f"arxiv-{arxiv_id}"
    m = GITHUB_RE.search(url)
    if m:
        owner = name_slug(m.group("owner"))
        repo = name_slug(m.group("repo"))
        return f"gh-{owner}-{repo}"
    h = host_slug(url)
    return h or None


def make_id(name: str, url: str | None) -> str:
    """Slug + optional source suffix, joined by `--`."""
    base = name_slug(name)
    suffix = source_suffix(url)
    return f"{base}--{suffix}" if suffix else base


# ---------------------------------------------------------------------------
# HTML cell decomposition.
# ---------------------------------------------------------------------------


def first_citation_href(td: Tag) -> str | None:
    """Return the href of the first <a class="cite"> when it is a real URL.

    The HTML occasionally uses non-URL citation hrefs as inline annotations
    (e.g. href="taxonomy/tags.json", href="inferred from primary tags ..."),
    plus the literal href="N/A" placeholders for "wrong section" cells. The
    schema (§7.1.11) requires `citation` to be either null or http(s); we
    silently drop the non-URL placeholders here. The reconciliation pass
    (#3) is the right place to recover any signal those placeholders carry.
    """
    for a in td.find_all("a", class_="cite"):
        href = (a.get("href") or "").strip()
        if href.startswith("http://") or href.startswith("https://"):
            return href
    return None


def cell_text_value(td: Tag) -> str:
    """Visible text with citation arrows removed and whitespace normalised.

    Strips:
      - all <a class="cite">↗</a> citation markers
      - the lone "↗" character if it leaks through
      - signal-num / sub / signal-warn wrappers (kept as text)
    Preserves the rendered text for everything else.
    """
    # Work on a clone so we don't mutate the caller's tree.
    clone = BeautifulSoup(str(td), "html.parser").find("td")
    if clone is None:
        return ""
    for a in clone.find_all("a", class_="cite"):
        a.decompose()
    text = clone.get_text(" ", strip=True)
    # Some cells embed a literal ↗ character outside an <a class="cite">.
    text = text.replace("↗", "").strip()
    # Collapse whitespace.
    text = re.sub(r"\s+", " ", text)
    return text


def detect_status(td: Tag) -> tuple[str, str]:
    """Return (status, override_value).

    The `value` may be replaced when a no-data span gives a more specific
    annotation than the surrounding cell text.
    """
    no_data = td.find("span", class_="no-data")
    if no_data is None:
        # No status span — check for fully empty cell.
        text = cell_text_value(td)
        if not text:
            return "no-data", ""
        return "real-data", text

    inner = (no_data.get_text(" ", strip=True) or "").strip()
    inner_lower = inner.lower()

    # The N/A — wrong section pattern: <td>...N/A — wrong section <a class="cite" href="N/A">↗</a></td>
    # has no <span class="no-data"> — handled elsewhere.

    if "not applicable" in inner_lower or inner_lower.startswith("n/a"):
        return "not-applicable", inner
    # Estimate marker (SCHEMA.md §3a): "<span class='no-data'>estimate</span>"
    # signals a maintainer-judgement T3 cell.
    if inner_lower == "estimate":
        text = cell_text_value(td)
        text = re.sub(r"\bestimate\b", "", text, count=1).strip()
        return "estimate", text
    if (
        "searched not found" in inner_lower
        or "depth-floor reached" in inner_lower
        or "depth floor reached" in inner_lower
        or inner_lower.startswith("not specified")
        or inner_lower.startswith("position paper")
        or inner_lower.startswith("no public")
        or inner_lower.startswith("no releases")
        or inner_lower.startswith("no quantitative")
        or inner_lower.startswith("no headline")
        or inner_lower.startswith("parent is public")
    ):
        return "depth-floor-reached", inner
    if inner_lower in ("", "no data"):
        return "no-data", inner

    # Unknown wording inside <span class="no-data"> — treat as a depth-floor
    # annotation; this is the most defensible default for cells the
    # researchers explicitly marked.
    return "depth-floor-reached", inner


def is_n_a_wrong_section(td: Tag) -> bool:
    """True for cells like:
        <td>...N/A — wrong section <a class="cite" href="N/A">↗</a></td>
    that lack a no-data span but still mean not-applicable."""
    for a in td.find_all("a", class_="cite"):
        if (a.get("href") or "").strip().upper() == "N/A":
            return True
    text = cell_text_value(td).strip().lower()
    if text.startswith("n/a") and "wrong section" in text:
        return True
    return False


def classify_tier(citation, status):
    """Apply the SCHEMA.md §3a auto-detection heuristic.

    Returns (tier, missing_url_warning). The heuristic is top-down (first
    match wins):

      1. status == "estimate" → T3 (explicit maintainer judgement)
      2. status == "no-data"  → T3 (transitional placeholder)
      3. citation matches GitHub URL → T1 (auto-verifiable)
      4. citation is any other http(s) URL → T2 (resolvable source)
      5. status == "not-applicable" and citation absent → T3
         (an N/A annotation is the maintainer's "no claim applies"
         decision; demanding a citation defeats the purpose)
      6. citation empty AND status in {real-data, depth-floor-reached}
         → T2 + warning (we have a claim but lost the URL)
      7. fallback → T2 (conservative)
    """
    if status == "estimate":
        return "T3", False
    if status == "no-data":
        return "T3", False
    if citation and TIER_GITHUB_URL_RE.match(citation):
        return "T1", False
    if citation and (citation.startswith("http://") or citation.startswith("https://")):
        return "T2", False
    if status == "not-applicable":
        return "T3", False
    if status in {"real-data", "depth-floor-reached"}:
        return "T2", True
    return "T2", True


def parse_cell(
    td: Tag, *, warnings=None, where=None, slug: str | None = None
) -> dict[str, Any]:
    """Decompose one cell <td> into {value, citation, status, tier[, last_verified_at]}.

    The tier is computed by classify_tier() from the (citation, status)
    pair. When the heuristic returns missing_url_warning=True the caller's
    `warnings` list (if provided) receives a one-line summary.

    When the cell carries a `data-last-verified="YYYY-MM-DD"` HTML
    attribute AND the cell's slug is in VOLATILE_CELL_SLUGS (SCHEMA.md
    §3b), the parsed date is added to the cell dict as
    `last_verified_at`. Non-volatile cells inherit the row-level date
    and drop the per-cell field even if the HTML carries one — keeps
    the JSON canonical.
    """
    if is_n_a_wrong_section(td):
        cell = {
            "value": cell_text_value(td) or "N/A — wrong section",
            "citation": None,
            "status": "not-applicable",
        }
    else:
        status, override = detect_status(td)
        if status == "real-data":
            value = cell_text_value(td)
        elif status == "estimate":
            value = override
        elif status in {"not-applicable", "depth-floor-reached"}:
            value = override
        else:  # no-data
            value = override or ""
        citation = first_citation_href(td)
        cell = {"value": value, "citation": citation, "status": status}
    tier, missing_url = classify_tier(cell["citation"], cell["status"])
    cell["tier"] = tier
    # Read per-cell last_verified_at — but only retain it for volatile
    # slugs per SCHEMA.md §3b.
    if slug in VOLATILE_CELL_SLUGS:
        attr = td.get("data-last-verified")
        if isinstance(attr, str) and ISO_DATE_RE.match(attr.strip()):
            cell["last_verified_at"] = attr.strip()
    if missing_url and warnings is not None and where is not None:
        warnings.append(where)
    return cell


# ---------------------------------------------------------------------------
# Taxonomy parsing (§2.4).
# ---------------------------------------------------------------------------


def first_token(text: str) -> str:
    """Return a lowercase canonical-looking first token from free text."""
    text = text.strip().lower()
    # Strip a leading parenthetical entirely.
    text = re.sub(r"\([^)]*\)", "", text).strip()
    # Take the first dash-separated token cluster up to a space or punctuation.
    m = re.match(r"[a-z0-9][a-z0-9\-]*", text)
    return m.group(0) if m else "n/a"


def parse_taxonomy_axis(td: Tag) -> list[dict[str, Any]]:
    """Return a non-empty list of {value, primary, reason} per axis cell."""
    pills = td.find_all("span", class_="tax-pill")
    if pills:
        out = []
        for i, pill in enumerate(pills):
            classes = pill.get("class") or []
            value = None
            for cls in classes:
                if cls.startswith("tax-") and cls != "tax-pill":
                    value = cls[len("tax-") :]
                    break
            if value is None:
                value = pill.get_text(strip=True).lower()
            out.append({
                "value": value,
                "primary": (i == 0),
                "reason": None,
            })
        return out

    no_data = td.find("span", class_="no-data")
    if no_data is not None:
        text = no_data.get_text(" ", strip=True)
        return [{
            "value": "n/a",
            "primary": True,
            "reason": text or "n/a",
        }]

    # Free-text fallback: <td class="tax-X">long-term <a class="cite">↗</a></td>
    # Strip the citation, take the first token as the canonical value, retain
    # the full string as `reason` if it's not just the value itself.
    text = cell_text_value(td)
    if not text:
        return [{"value": "n/a", "primary": True, "reason": "empty"}]
    value = first_token(text)
    reason = None if text.lower() == value else text
    return [{"value": value, "primary": True, "reason": reason}]


# ---------------------------------------------------------------------------
# Section walker.
# ---------------------------------------------------------------------------


SUB_PREFIX_RE = re.compile(r"^—\s*")


def section_label(group_row_td_text: str) -> tuple[str, bool]:
    """Return (label, is_subsection) for a group-row's first <td> text.

    Subsections in the HTML start with the literal "— " (em-dash + space)
    inside a `<td colspan="93" style="padding-left: 28px; ...">`. We
    preserve the prefix exactly per §2.3.
    """
    txt = group_row_td_text.strip()
    is_sub = txt.startswith("—")
    return txt, is_sub


def iter_records(soup: BeautifulSoup):
    """Yield (tier_int, name, url, td_list, primary_section, subsection)
    in document order, walking the tbody and tracking the current section
    based on intervening `<tr class="group-row">` rows."""
    tbody = soup.find("tbody")
    current_section: str | None = None
    current_subsection: str | None = None
    for tr in tbody.find_all("tr", recursive=False):
        cls = tr.get("class") or []
        if "group-row" in cls:
            td = tr.find("td")
            label = td.get_text(" ", strip=True) if td else ""
            if not label:
                continue
            txt, is_sub = section_label(label)
            if is_sub:
                # Per §2.3 we preserve the leading "— " exactly. Use the raw
                # label text, which includes the dash.
                current_subsection = txt
            else:
                current_section = txt
                current_subsection = None
            continue
        if "section-explainer" in cls:
            continue
        # Tier rows.
        tier = None
        for c in cls:
            if c.startswith("row-t") and len(c) == 6 and c[5].isdigit():
                tier = int(c[5])
                break
        if tier is None:
            continue
        name_td = tr.find("td", class_="name")
        if name_td is None:
            continue
        a = name_td.find("a")
        if a is not None and a.get("href"):
            url = a["href"].strip()
            name = a.get_text(" ", strip=True)
        else:
            url = None
            name = name_td.get_text(" ", strip=True)
        # The 67 trailing <td>s for the row.
        tds = tr.find_all("td", recursive=False)
        # Row-level last_verified_at: HTML attribute data-last-verified
        # on the <tr> itself. See SCHEMA.md §3b.
        row_verified = tr.get("data-last-verified")
        if isinstance(row_verified, str) and ISO_DATE_RE.match(
            row_verified.strip()
        ):
            row_verified = row_verified.strip()
        else:
            row_verified = None
        # Row-level decay forensics (SCHEMA.md §3c, issue #56). Three
        # optional HTML attributes on the <tr>: data-decay-cause,
        # data-decay-date, data-decay-evidence. Validated against the
        # enum in DECAY_CAUSE_VALUES; the date must be ISO YYYY-MM-DD;
        # evidence is free-text. Absent attributes mean "active row, no
        # decay cause recorded."
        decay_cause_raw = tr.get("data-decay-cause")
        decay_cause = (
            decay_cause_raw.strip()
            if isinstance(decay_cause_raw, str) and decay_cause_raw.strip()
            else None
        )
        decay_date_raw = tr.get("data-decay-date")
        decay_date = None
        if isinstance(decay_date_raw, str) and decay_date_raw.strip():
            if ISO_DATE_RE.match(decay_date_raw.strip()):
                decay_date = decay_date_raw.strip()
        decay_evidence_raw = tr.get("data-decay-evidence")
        decay_evidence = (
            decay_evidence_raw.strip()
            if isinstance(decay_evidence_raw, str) and decay_evidence_raw.strip()
            else None
        )
        # First is name; next 7 are tax-*; rest are cells.
        yield {
            "tier": tier,
            "name": name,
            "url": url,
            "tds": tds,
            "section": current_section,
            "subsection": current_subsection,
            "last_verified_at": row_verified,
            "decay_cause": decay_cause,
            "decay_date": decay_date,
            "decay_evidence": decay_evidence,
        }


# ---------------------------------------------------------------------------
# Validator (§7.1)
# ---------------------------------------------------------------------------


def is_http_url(s: str) -> bool:
    return isinstance(s, str) and (s.startswith("http://") or s.startswith("https://"))


def validate_record(rec: dict[str, Any]) -> list[str]:
    """Return a list of validation errors. Empty list = valid."""
    errs: list[str] = []
    rid = rec.get("id", "<missing>")

    # 7.1.4 required keys
    for key in (
        "id",
        "name",
        "tier",
        "url",
        "last_verified_at",
        "sections",
        "taxonomy",
        "cells",
    ):
        if key not in rec:
            errs.append(f"{rid}: missing key {key!r}")
    # Row-level last_verified_at — SCHEMA.md §3b.
    lva = rec.get("last_verified_at")
    if not isinstance(lva, str) or not ISO_DATE_RE.match(lva or ""):
        errs.append(
            f"{rid}: last_verified_at must match YYYY-MM-DD (got {lva!r})"
        )
    # 7.1.6 id regex
    if not isinstance(rec.get("id"), str) or not ID_RE.match(rec["id"] or ""):
        errs.append(f"{rid}: id failed regex {ID_RE.pattern}")
    # Decay-cause forensics (SCHEMA.md §3c, issue #56). When present
    # the fields must match the documented enum / date / string shape.
    # Presence/absence semantics (active vs stale/abandoned) are
    # enforced by scripts/validate.py gate 5 — here we only validate
    # the value shape.
    dc = rec.get("decay_cause")
    if dc is not None:
        if not isinstance(dc, str) or dc not in DECAY_CAUSE_VALUES:
            errs.append(
                f"{rid}: decay_cause {dc!r} not in "
                f"{sorted(DECAY_CAUSE_VALUES)}"
            )
    dd = rec.get("decay_date")
    if dd is not None:
        if not isinstance(dd, str) or not ISO_DATE_RE.match(dd):
            errs.append(
                f"{rid}: decay_date must match YYYY-MM-DD (got {dd!r})"
            )
    de = rec.get("decay_evidence")
    if de is not None:
        if not isinstance(de, str) or not de:
            errs.append(
                f"{rid}: decay_evidence must be non-empty string (got {de!r})"
            )
    # 7.1.7 tier
    if rec.get("tier") not in (1, 2, 3, 4, 5):
        errs.append(f"{rid}: tier not in 1..5")
    # 7.1.8 url
    url = rec.get("url")
    if not (url is None or is_http_url(url)):
        errs.append(f"{rid}: url must be null or http(s) ({url!r})")
    # 7.1.9 sections
    secs = rec.get("sections") or []
    if not isinstance(secs, list) or not secs:
        errs.append(f"{rid}: sections must be non-empty array")
    else:
        primaries = sum(1 for s in secs if s.get("primary"))
        if primaries != 1:
            errs.append(f"{rid}: sections must have exactly one primary (got {primaries})")
        for s in secs:
            if s.get("section") not in CANONICAL_SECTIONS:
                errs.append(f"{rid}: unknown section {s.get('section')!r}")
            sub = s.get("subsection")
            if sub is not None and s.get("section") not in SECTIONS_WITH_SUBS:
                errs.append(f"{rid}: section {s.get('section')!r} has no subsections in spec but got {sub!r}")
    # 7.1.10 taxonomy
    tax = rec.get("taxonomy") or {}
    if set(tax.keys()) != set(TAXONOMY_AXES):
        errs.append(f"{rid}: taxonomy keys {sorted(tax.keys())} != {sorted(TAXONOMY_AXES)}")
    else:
        for axis, vals in tax.items():
            if not isinstance(vals, list) or not vals:
                errs.append(f"{rid}: taxonomy.{axis} must be non-empty array")
                continue
            primaries = sum(1 for v in vals if v.get("primary"))
            if primaries != 1:
                errs.append(f"{rid}: taxonomy.{axis} must have exactly one primary (got {primaries})")
    # 7.1.11 cells
    cells = rec.get("cells") or {}
    if set(cells.keys()) != set(CELL_COLUMN_SLUGS):
        missing = sorted(set(CELL_COLUMN_SLUGS) - set(cells.keys()))
        extra = sorted(set(cells.keys()) - set(CELL_COLUMN_SLUGS))
        errs.append(f"{rid}: cells key mismatch (missing={missing} extra={extra})")
    else:
        for slug, cell in cells.items():
            if cell.get("status") not in STATUS_VALUES:
                errs.append(f"{rid}: cells[{slug}].status invalid: {cell.get('status')!r}")
            if not isinstance(cell.get("value"), str):
                errs.append(f"{rid}: cells[{slug}].value must be string")
            cit = cell.get("citation")
            if cit is not None and not is_http_url(cit):
                errs.append(f"{rid}: cells[{slug}].citation must be null or http(s) ({cit!r})")
            tier = cell.get("tier")
            if tier not in CLAIM_TIERS:
                errs.append(f"{rid}: cells[{slug}].tier invalid: {tier!r}")
            # Per-cell last_verified_at (SCHEMA.md §3b) — optional but
            # if present MUST match YYYY-MM-DD and slug MUST be volatile.
            cell_lva = cell.get("last_verified_at")
            if cell_lva is not None:
                if not isinstance(cell_lva, str) or not ISO_DATE_RE.match(
                    cell_lva
                ):
                    errs.append(
                        f"{rid}: cells[{slug}].last_verified_at must match "
                        f"YYYY-MM-DD (got {cell_lva!r})"
                    )
                elif slug not in VOLATILE_CELL_SLUGS:
                    errs.append(
                        f"{rid}: cells[{slug}].last_verified_at present "
                        f"but slug {slug!r} is not in the volatile set "
                        "(SCHEMA.md §3b)"
                    )
    return errs


# ---------------------------------------------------------------------------
# Main pipeline.
# ---------------------------------------------------------------------------


def build_record(
    parsed: dict,
    used_ids: dict[str, int],
    tier_warnings: list[str] | None = None,
) -> dict[str, Any]:
    name = parsed["name"]
    url = parsed["url"]

    # id with collision suffix per §2.1.4
    base_id = make_id(name, url)
    count = used_ids.get(base_id, 0)
    used_ids[base_id] = count + 1
    rec_id = base_id if count == 0 else f"{base_id}-{count + 1}"
    if count > 0:
        print(
            f"warn: id collision on {base_id!r}; using {rec_id!r} for occurrence #{count + 1}",
            file=sys.stderr,
        )

    tds = parsed["tds"]
    # HTML layout (left-to-right):
    #   tds[0]    = name
    #   tds[1]    = type (the "Memory model" cell — first cell column)
    #   tds[2..8] = tax-storage .. tax-conflict (7 taxonomy axes)
    #   tds[9..92] = desc .. download-trajectory (84 remaining cell columns)
    # Total: 1 + 1 + 7 + 84 = 93 tds per row.
    if len(tds) != 93:
        raise RuntimeError(
            f"row {rec_id!r}: expected 93 tds, got {len(tds)}"
        )
    type_td = tds[1]
    tax_tds = tds[2:9]
    rest_cell_tds = tds[9:]
    assert len(tax_tds) == 7
    assert len(rest_cell_tds) == 84

    taxonomy = OrderedDict()
    for axis, td in zip(TAXONOMY_AXES, tax_tds):
        taxonomy[axis] = parse_taxonomy_axis(td)

    cells = OrderedDict()
    cells[CELL_COLUMN_SLUGS[0]] = parse_cell(
        type_td,
        warnings=tier_warnings,
        where=f"{rec_id}.{CELL_COLUMN_SLUGS[0]}",
        slug=CELL_COLUMN_SLUGS[0],
    )  # "type"
    for slug, td in zip(CELL_COLUMN_SLUGS[1:], rest_cell_tds):
        cells[slug] = parse_cell(
            td, warnings=tier_warnings, where=f"{rec_id}.{slug}", slug=slug
        )

    sections = [{
        "section": parsed["section"],
        "subsection": parsed["subsection"],
        "primary": True,
        "reason": None,
    }]

    # Row-level last_verified_at — required per SCHEMA.md §3b. Falls
    # back to the schema's documented default ("2026-05-06", the first
    # commit touching landscape.html) if the HTML lacks an attribute,
    # so older / unrenderable rows still pass gate-5 validation.
    last_verified_at = parsed.get("last_verified_at") or "2026-05-06"

    rec = OrderedDict([
        ("id", rec_id),
        ("name", name),
        ("tier", parsed["tier"]),
        ("url", url),
        ("last_verified_at", last_verified_at),
    ])
    # Decay-cause forensics (SCHEMA.md §3c, issue #56) — only emit the
    # three keys when at least one is populated. Omitting the keys for
    # active rows keeps the JSON canonical (no empty-string clutter) and
    # makes the gate-5 "active row must not carry a decay_cause" check
    # trivially correct: presence of any decay_* key in the record dict
    # is the signal.
    decay_cause = parsed.get("decay_cause")
    decay_date = parsed.get("decay_date")
    decay_evidence = parsed.get("decay_evidence")
    if decay_cause:
        rec["decay_cause"] = decay_cause
    if decay_date:
        rec["decay_date"] = decay_date
    if decay_evidence:
        rec["decay_evidence"] = decay_evidence
    rec["sections"] = sections
    rec["taxonomy"] = taxonomy
    rec["cells"] = cells
    return rec


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(Path(__file__).resolve().parent.parent / "landscape.html"),
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent.parent / "data" / "landscape.json"),
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 2

    html = in_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    used_ids: dict[str, int] = {}
    records: list[dict[str, Any]] = []
    # Cells claiming data but lacking a citation are classified T2 with
    # a soft warning so the population can be tracked and researched.
    tier_warnings: list[str] = []
    for parsed in iter_records(soup):
        if parsed["section"] is None:
            print(
                f"warn: row {parsed['name']!r} has no current section — skipping",
                file=sys.stderr,
            )
            continue
        rec = build_record(parsed, used_ids, tier_warnings=tier_warnings)
        records.append(rec)

    # Stable order: sort by id ASC.
    records.sort(key=lambda r: r["id"])

    # Validate.
    errors: list[str] = []
    seen = set()
    for r in records:
        if r["id"] in seen:
            errors.append(f"duplicate id after sort: {r['id']!r}")
        seen.add(r["id"])
        errors.extend(validate_record(r))
    if errors:
        for e in errors[:50]:
            print(f"validation error: {e}", file=sys.stderr)
        if len(errors) > 50:
            print(f"... and {len(errors) - 50} more errors", file=sys.stderr)
        print(f"\n{len(errors)} validation errors total", file=sys.stderr)
        return 1

    generated_at = os.environ.get("EXTRACT_GENERATED_AT", DEFAULT_GENERATED_AT)
    payload = OrderedDict([
        ("schemaVersion", SCHEMA_VERSION),
        ("generatedAt", generated_at),
        ("sourceHtml", in_path.name),
        ("records", records),
    ])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if not text.endswith("\n"):
        text += "\n"
    out_path.write_text(text, encoding="utf-8")

    # Summary.
    by_tier: dict[int, int] = {}
    by_status: dict[str, int] = {s: 0 for s in STATUS_VALUES}
    by_claim_tier: dict[str, int] = {ct: 0 for ct in CLAIM_TIERS}
    for r in records:
        by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
        for c in r["cells"].values():
            by_status[c["status"]] += 1
            by_claim_tier[c["tier"]] = by_claim_tier.get(c["tier"], 0) + 1
    print(f"wrote {out_path} ({len(records)} records)")
    print(f"  by tier: " + ", ".join(f"T{t}={by_tier.get(t, 0)}" for t in (1, 2, 3, 4, 5)))
    print(f"  by status: " + ", ".join(f"{k}={v}" for k, v in by_status.items()))
    print(f"  by claim-tier: " + ", ".join(f"{ct}={by_claim_tier.get(ct, 0)}" for ct in ("T1", "T2", "T3")))
    if tier_warnings:
        print(
            f"  soft-warning: {len(tier_warnings)} cells claim data but have no citation URL "
            f"(classified T2 — they will fail gate 5 unless researched)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
