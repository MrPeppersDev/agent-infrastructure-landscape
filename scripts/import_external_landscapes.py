#!/usr/bin/env python3
"""
Import + diff four external agent-landscape sources against data/landscape.json.

Inputs (read-only):
  extraction/external/agentic-community/20260701/data.yml
  extraction/external/antgroup/20260701/agentic-ai-projects.csv
  extraction/external/yc-sylph/20260701/yc_agent_companies_ai.csv
  extraction/external/ombharatiya/20260701/01-tool-use-landscape.md
  data/landscape.json

Outputs (deterministic; stable-sorted; no timestamps in content):
  extraction/external/candidates.csv     — unmatched upstream rows (intake queue)
  extraction/external/cross-listing.csv  — matched rows with upstream cite
  extraction/external/fuzzy-review.csv   — fuzzy-name candidates for maintainer eye
  extraction/external/gap-report.md      — narrative summary

Per-source parsers normalise to a common shape:
  {source_id, name, repo_url, homepage_url,
   source_categories: list[str], source_tags: list[str], source_url}

Antgroup licensing rule (per Phase 0 licence audit, issue #118 and
extraction/external/LICENCES.md): antgroup rows carry name / repo_url /
homepage_url ONLY. source_categories and source_tags are stripped at
parse time. Their curated categorisation is not republishable under the
current (undeclared) upstream licence.

Matching, in priority order:
  1. Exact normalised-URL match. Both repo_url and homepage_url are tried
     against records[*].url. GitHub URLs are canonicalised to the
     `github.com/owner/repo` form so trailing paths/slashes don't split
     equal repos.
  2. Fuzzy name >= 0.9 (difflib.SequenceMatcher) — never auto-imported;
     goes to fuzzy-review.csv for maintainer eyeball. Matches the
     >0.9 threshold used by the MCP searchRecords duplicate check in
     docs/INTAKE.md.
  3. Otherwise: candidate.

Phase-1 priority column (integer 1-5, 1 = highest), per plan agreed
2026-06-30 / 2026-07-01:
  1. Memory-adjacent (name matches 'memor'/'recall'/'context'/'state').
  2. agentic-community Memory + Knowledge Graphs + Vector DBs categories.
  3. yc-sylph 'Agent Memory & State' + 'Agent API/SDK' tech-strength.
  4. antgroup Agent Infra rows (fact-only extraction per licence audit).
  5. Everything else.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator

import yaml

# --- constants ------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DATE = "20260701"
EXT = REPO_ROOT / "extraction" / "external"

SOURCE_PATHS = {
    "agentic-community": EXT / "agentic-community" / SNAPSHOT_DATE / "data.yml",
    "antgroup": EXT / "antgroup" / SNAPSHOT_DATE / "agentic-ai-projects.csv",
    "yc-sylph": EXT / "yc-sylph" / SNAPSHOT_DATE / "yc_agent_companies_ai.csv",
    "ombharatiya": EXT / "ombharatiya" / SNAPSHOT_DATE / "01-tool-use-landscape.md",
}

SOURCE_URLS = {
    "agentic-community": "https://github.com/agentic-community/agentic-landscape",
    "antgroup": "https://github.com/antgroup/agentic-ai-landscape",
    "yc-sylph": "https://github.com/SylphAI-Inc/yc-agent-landscape",
    "ombharatiya": (
        "https://github.com/ombharatiya/ai-system-design-guide/blob/main/"
        "17-tool-use-and-computer-agents/01-tool-use-landscape.md"
    ),
}

LANDSCAPE_JSON = REPO_ROOT / "data" / "landscape.json"

FUZZY_THRESHOLD = 0.9
MEMORY_KEYWORDS = re.compile(r"\b(memor|recall|context|state)", re.IGNORECASE)

# For prose parsing of the ombharatiya chapter — systems that get their
# own H2 section header. Verified against the 20260701 snapshot.
OMBHARATIYA_SYSTEMS = [
    "OpenClaw",
    "OpenHands",
    "Open Interpreter",
    "Claude Computer Use",
    "Claude Code",
    "Cursor",
    "Windsurf",
    "Cline",
    "GitHub Copilot",
]


# --- URL normalisation ----------------------------------------------------

_GH_RE = re.compile(r"^github\.com/([^/]+)/([^/]+)")


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.rstrip("/")
    m = _GH_RE.match(u)
    if m:
        owner = m.group(1)
        repo = m.group(2).removesuffix(".git")
        return f"github.com/{owner}/{repo}"
    return u


# --- per-source parsers ---------------------------------------------------

def parse_agentic_community(path: Path) -> Iterator[dict]:
    doc = yaml.safe_load(path.read_text())
    for cat in doc.get("categories", []) or []:
        cat_name = cat.get("name", "")
        for sub in cat.get("subcategories", []) or []:
            sub_name = sub.get("name", "")
            for item in sub.get("items", []) or []:
                extra = item.get("extra") or {}
                yield {
                    "source_id": "agentic-community",
                    "name": (item.get("name") or "").strip(),
                    "repo_url": (item.get("repo_url") or "").strip(),
                    "homepage_url": (item.get("homepage_url") or "").strip(),
                    "source_categories": [f"{cat_name}/{sub_name}"],
                    "source_tags": [(extra.get("summary_tags") or "").strip()],
                    "source_url": SOURCE_URLS["agentic-community"],
                }


def parse_antgroup(path: Path) -> Iterator[dict]:
    """Fact-only extraction per licence audit: only name / repo_url are carried."""
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            repo_name = (row.get("repo_name") or "").strip()
            repo_url = f"https://github.com/{repo_name}" if repo_name else ""
            display = repo_name.split("/")[-1] if "/" in repo_name else repo_name
            yield {
                "source_id": "antgroup",
                "name": display,
                "repo_url": repo_url,
                "homepage_url": "",
                "source_categories": [],  # stripped by licence rule
                "source_tags": [],        # stripped by licence rule
                "source_url": SOURCE_URLS["antgroup"],
            }


def parse_yc_sylph(path: Path) -> Iterator[dict]:
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh):
            yield {
                "source_id": "yc-sylph",
                "name": (row.get("name") or "").strip(),
                "repo_url": "",
                "homepage_url": (row.get("website") or "").strip(),
                "source_categories": [(row.get("ai_tech_strength") or "").strip()],
                "source_tags": [
                    (row.get("batch") or "").strip(),
                    (row.get("agent_type") or "").strip(),
                    (row.get("ai_vertical") or "").strip(),
                ],
                "source_url": SOURCE_URLS["yc-sylph"],
            }


def parse_ombharatiya(path: Path) -> Iterator[dict]:
    text = path.read_text()
    for name in OMBHARATIYA_SYSTEMS:
        pattern = re.compile(rf"^##\s+.*\b{re.escape(name)}\b", re.MULTILINE)
        if pattern.search(text):
            yield {
                "source_id": "ombharatiya",
                "name": name,
                "repo_url": "",
                "homepage_url": "",
                "source_categories": ["Tool-Use / Computer Agents"],
                "source_tags": [],
                "source_url": SOURCE_URLS["ombharatiya"],
            }


# --- matching -------------------------------------------------------------

def index_landscape(records: list[dict]) -> dict:
    by_url: dict[str, str] = {}
    names: list[tuple[str, str]] = []
    for r in records:
        url = normalize_url(r.get("url"))
        if url and url not in by_url:
            by_url[url] = r["id"]
        names.append((r["id"], (r.get("name") or "").strip()))
    return {"by_url": by_url, "names": names}


def try_url_match(row: dict, idx: dict) -> tuple[str, str] | None:
    for kind, candidate in (("repo_url", row.get("repo_url")),
                            ("homepage_url", row.get("homepage_url"))):
        norm = normalize_url(candidate)
        if norm and norm in idx["by_url"]:
            return idx["by_url"][norm], kind
    return None


def try_fuzzy_match(row: dict, idx: dict) -> tuple[str, str, float] | None:
    name = (row.get("name") or "").lower()
    if not name:
        return None
    best: tuple[str, str, float] | None = None
    for lid, lname in idx["names"]:
        score = difflib.SequenceMatcher(None, name, lname.lower()).ratio()
        if score >= FUZZY_THRESHOLD and (best is None or score > best[2]):
            best = (lid, lname, score)
    return best


# --- prioritisation -------------------------------------------------------

AC_MEMORY_KEYS = ("Memory", "Knowledge Graphs", "Vector DB", "Vector Databases", "RAG")
YC_MEMORY_STRENGTHS = {"Agent Memory & State", "Agent API/SDK"}


def phase1_priority(row: dict) -> int:
    name = row.get("name", "")
    if MEMORY_KEYWORDS.search(name):
        return 1
    src = row["source_id"]
    cats = row.get("source_categories", [])
    if src == "agentic-community":
        for cat in cats:
            for key in AC_MEMORY_KEYS:
                if key in cat:
                    return 2
    if src == "yc-sylph":
        if any(cat in YC_MEMORY_STRENGTHS for cat in cats):
            return 3
    if src == "antgroup":
        return 4
    return 5


# --- output writers -------------------------------------------------------

def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_gap_report(
    path: Path,
    records: list[dict],
    candidates: list[dict],
    cross_listing: list[dict],
    fuzzy_review: list[dict],
    per_source_totals: Counter,
) -> None:
    matched_by = Counter(r["source_id"] for r in cross_listing)
    fuzzy_by = Counter(r["source_id"] for r in fuzzy_review)
    cand_by = Counter(r["source_id"] for r in candidates)

    lines = [
        "# External-landscape gap report",
        "",
        f"Generated by `scripts/import_external_landscapes.py` from the "
        f"`{SNAPSHOT_DATE}` vendored snapshots under "
        f"`extraction/external/`. Snapshot commit SHAs and licences: "
        f"`extraction/external/LICENCES.md`.",
        "",
        "## Per-source contribution",
        "",
        "| Source | Upstream rows | Matched | Fuzzy (review) | New candidates |",
        "|---|---:|---:|---:|---:|",
    ]
    for src in sorted(per_source_totals):
        lines.append(
            f"| `{src}` | {per_source_totals[src]} | "
            f"{matched_by[src]} | {fuzzy_by[src]} | {cand_by[src]} |"
        )

    lines += ["", "## Candidate priority distribution", "",
              "| Priority | Rule | Count |",
              "|---:|---|---:|"]
    prio_counts = Counter(r["phase1_priority"] for r in candidates)
    labels = {
        1: "Memory-adjacent (name keyword match)",
        2: "agentic-community Memory / KG / Vector DB / RAG",
        3: "yc-sylph Agent Memory & State / Agent API-SDK",
        4: "antgroup Agent Infra (fact-only extraction)",
        5: "Other",
    }
    for p in sorted(labels):
        lines.append(f"| {p} | {labels[p]} | {prio_counts.get(p, 0)} |")

    top = sorted(
        candidates,
        key=lambda r: (r["phase1_priority"], r["source_id"], r["name"]),
    )[:25]
    lines += ["", "## Top 25 highest-priority candidates", "",
              "| Priority | Source | Name | Upstream categories |",
              "|---:|---|---|---|"]
    for c in top:
        cats = c["source_categories"] or "—"
        lines.append(
            f"| {c['phase1_priority']} | `{c['source_id']}` | "
            f"{c['name']} | {cats} |"
        )

    # Licence-bucket distribution from agentic-community summary_tags
    lic_counts: Counter = Counter()
    doc = yaml.safe_load(SOURCE_PATHS["agentic-community"].read_text())
    for cat in doc.get("categories", []) or []:
        for sub in cat.get("subcategories", []) or []:
            for item in sub.get("items", []) or []:
                tag = ((item.get("extra") or {}).get("summary_tags") or "Unknown").strip()
                lic_counts[tag or "Unknown"] += 1
    lines += ["", "## Licence-bucket distribution (agentic-community summary_tags)", "",
              "| Bucket | Count |",
              "|---|---:|"]
    for bucket, cnt in sorted(lic_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {bucket} | {cnt} |")

    section_counts: Counter = Counter()
    for r in records:
        for s in r.get("sections", []) or []:
            if s.get("primary"):
                section_counts[s.get("section", "")] += 1
    lines += ["", "## Existing catalogue: primary-section coverage",
              "",
              f"Total catalogued records: **{len(records)}** across "
              f"**{len(section_counts)}** primary sections.",
              "",
              "| Section | Records |",
              "|---|---:|"]
    for section, cnt in sorted(section_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {section} | {cnt} |")

    path.write_text("\n".join(lines) + "\n")


# --- driver ---------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Import and diff four external agent-landscape sources "
                     "against data/landscape.json. Emits four deterministic "
                     "artefacts under extraction/external/. See module docstring.")
    )
    parser.add_argument(
        "--out-dir",
        default=str(EXT),
        help=f"Output directory (default: {EXT})",
    )
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    d = json.loads(LANDSCAPE_JSON.read_text())
    idx = index_landscape(d["records"])

    all_rows: list[dict] = []
    all_rows.extend(parse_agentic_community(SOURCE_PATHS["agentic-community"]))
    all_rows.extend(parse_antgroup(SOURCE_PATHS["antgroup"]))
    all_rows.extend(parse_yc_sylph(SOURCE_PATHS["yc-sylph"]))
    all_rows.extend(parse_ombharatiya(SOURCE_PATHS["ombharatiya"]))

    candidates: list[dict] = []
    cross_listing: list[dict] = []
    fuzzy_review: list[dict] = []
    per_source_totals: Counter = Counter()
    per_source_bucketed: Counter = Counter()

    for row in all_rows:
        per_source_totals[row["source_id"]] += 1
        m = try_url_match(row, idx)
        if m:
            landscape_id, method = m
            cross_listing.append({
                "landscape_id": landscape_id,
                "name": row["name"],
                "source_id": row["source_id"],
                "source_categories": "|".join(row.get("source_categories", [])),
                "source_url": row["source_url"],
                "match_method": method,
            })
            per_source_bucketed[row["source_id"]] += 1
            continue
        fm = try_fuzzy_match(row, idx)
        if fm:
            lid, lname, score = fm
            fuzzy_review.append({
                "source_id": row["source_id"],
                "upstream_name": row["name"],
                "upstream_url": row.get("repo_url") or row.get("homepage_url", ""),
                "candidate_landscape_id": lid,
                "candidate_name": lname,
                "similarity_score": f"{score:.4f}",
            })
            per_source_bucketed[row["source_id"]] += 1
            continue
        candidates.append({
            "source_id": row["source_id"],
            "name": row["name"],
            "repo_url": row["repo_url"],
            "homepage_url": row["homepage_url"],
            "source_categories": "|".join(row.get("source_categories", [])),
            "source_url": row["source_url"],
            "phase1_priority": phase1_priority(row),
        })
        per_source_bucketed[row["source_id"]] += 1

    candidates.sort(key=lambda r: (r["source_id"], r["name"]))
    cross_listing.sort(key=lambda r: (r["landscape_id"], r["source_id"]))
    fuzzy_review.sort(key=lambda r: (r["source_id"], r["upstream_name"]))

    write_csv(
        out / "candidates.csv",
        ["source_id", "name", "repo_url", "homepage_url",
         "source_categories", "source_url", "phase1_priority"],
        candidates,
    )
    write_csv(
        out / "cross-listing.csv",
        ["landscape_id", "name", "source_id", "source_categories",
         "source_url", "match_method"],
        cross_listing,
    )
    write_csv(
        out / "fuzzy-review.csv",
        ["source_id", "upstream_name", "upstream_url",
         "candidate_landscape_id", "candidate_name", "similarity_score"],
        fuzzy_review,
    )
    write_gap_report(
        out / "gap-report.md",
        d["records"], candidates, cross_listing, fuzzy_review,
        per_source_totals,
    )

    for src, total in per_source_totals.items():
        if per_source_bucketed[src] != total:
            print(f"SANITY FAIL: {src} bucketed={per_source_bucketed[src]} "
                  f"!= total={total}", file=sys.stderr)
            return 2

    print(f"candidates={len(candidates)} "
          f"cross-listing={len(cross_listing)} "
          f"fuzzy-review={len(fuzzy_review)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
