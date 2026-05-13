#!/usr/bin/env python3
"""
extract.py — landscape.html → web/landscape.json

Parses every data row from landscape.html into the structured per-record schema
defined in docs/SCHEMA.md, validates each record against the §7 rules, and
writes the result to web/landscape.json.

Determinism contract:
  - Records are sorted by id ASC.
  - Inside each record, taxonomy axes and sections preserve document order.
  - Inside each cell, the citation is the first <a class="cite"> href.
  - generatedAt is fixed (read from env EXTRACT_GENERATED_AT, else default
    constant) so that round-tripping the script twice yields byte-identical
    output. The spec calls this out as a hard requirement.

Usage:
  python3 scripts/extract.py            # writes web/landscape.json
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

# In document order, the 60 cell column slugs (everything except `name`,
# the 7 `tax-*` axes, and the implicit `name` column).
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
]
assert len(CELL_COLUMN_SLUGS) == 60

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
}

# Status enum values.
STATUS_VALUES = {"real-data", "not-applicable", "depth-floor-reached", "no-data"}

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


def parse_cell(td: Tag) -> dict[str, Any]:
    """Decompose one cell <td> into {value, citation, status}."""
    if is_n_a_wrong_section(td):
        return {
            "value": cell_text_value(td) or "N/A — wrong section",
            "citation": None,
            "status": "not-applicable",
        }
    status, override = detect_status(td)
    if status == "real-data":
        value = cell_text_value(td)
    elif status in {"not-applicable", "depth-floor-reached"}:
        # Use the no-data span text rather than the surrounding cell text,
        # since the surrounding text is just "↗" or empty.
        value = override
    else:  # no-data
        value = override or ""
    citation = first_citation_href(td)
    return {"value": value, "citation": citation, "status": status}


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
    inside a `<td colspan="68" style="padding-left: 28px; ...">`. We
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
        # First is name; next 7 are tax-*; rest are cells.
        yield {
            "tier": tier,
            "name": name,
            "url": url,
            "tds": tds,
            "section": current_section,
            "subsection": current_subsection,
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
    for key in ("id", "name", "tier", "url", "sections", "taxonomy", "cells"):
        if key not in rec:
            errs.append(f"{rid}: missing key {key!r}")
    # 7.1.6 id regex
    if not isinstance(rec.get("id"), str) or not ID_RE.match(rec["id"] or ""):
        errs.append(f"{rid}: id failed regex {ID_RE.pattern}")
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
    return errs


# ---------------------------------------------------------------------------
# Main pipeline.
# ---------------------------------------------------------------------------


def build_record(parsed: dict, used_ids: dict[str, int]) -> dict[str, Any]:
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
    #   tds[0]   = name
    #   tds[1]   = type (the "Memory model" cell — first cell column)
    #   tds[2..8] = tax-storage .. tax-conflict (7 taxonomy axes)
    #   tds[9..67] = desc .. links (59 remaining cell columns)
    # Total: 1 + 1 + 7 + 59 = 68 tds per row.
    if len(tds) != 68:
        raise RuntimeError(
            f"row {rec_id!r}: expected 68 tds, got {len(tds)}"
        )
    type_td = tds[1]
    tax_tds = tds[2:9]
    rest_cell_tds = tds[9:]
    assert len(tax_tds) == 7
    assert len(rest_cell_tds) == 59

    taxonomy = OrderedDict()
    for axis, td in zip(TAXONOMY_AXES, tax_tds):
        taxonomy[axis] = parse_taxonomy_axis(td)

    cells = OrderedDict()
    cells[CELL_COLUMN_SLUGS[0]] = parse_cell(type_td)  # "type"
    for slug, td in zip(CELL_COLUMN_SLUGS[1:], rest_cell_tds):
        cells[slug] = parse_cell(td)

    sections = [{
        "section": parsed["section"],
        "subsection": parsed["subsection"],
        "primary": True,
        "reason": None,
    }]

    return OrderedDict([
        ("id", rec_id),
        ("name", name),
        ("tier", parsed["tier"]),
        ("url", url),
        ("sections", sections),
        ("taxonomy", taxonomy),
        ("cells", cells),
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(Path(__file__).resolve().parent.parent / "landscape.html"),
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent.parent / "web" / "landscape.json"),
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
    for parsed in iter_records(soup):
        if parsed["section"] is None:
            print(
                f"warn: row {parsed['name']!r} has no current section — skipping",
                file=sys.stderr,
            )
            continue
        rec = build_record(parsed, used_ids)
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
    for r in records:
        by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
        for c in r["cells"].values():
            by_status[c["status"]] += 1
    print(f"wrote {out_path} ({len(records)} records)")
    print(f"  by tier: " + ", ".join(f"T{t}={by_tier.get(t, 0)}" for t in (1, 2, 3, 4, 5)))
    print(f"  by status: " + ", ".join(f"{k}={v}" for k, v in by_status.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
