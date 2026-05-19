#!/usr/bin/env python3
"""
bucket_s2_citations.py — Time-bucket the S2 reference cache into per-row
yearly cumulative inbound-citation trajectories for the `citation-trajectory`
column (issue #51 / SCHEMA.md §2.5.5).

This is a pure offline transform: it does NOT call the network. It reads
the committed `extraction/s2-cache/*.json` files (which contain each
research-paper row's S2 references-OUT list, populated by
`scripts/fetch_citations.py`) and inverts the relation to produce a
within-catalog inbound-citation trajectory for each target row.

Algorithm
---------

1. Build a CatalogIndex mapping arxiv-id, S2-paper-hash, and DOI to
   record ids — same logic as `scripts/fetch_citations.py`.
2. For each record R with a cache file:
   - Read the cache file's `data` array of `{citedPaper, isInfluential}`.
   - Resolve each `citedPaper` to a target record T in the catalog.
   - Extract R's publication year from its arxiv id-suffix (preferred)
     or from a parseable arxiv URL in its cells.
   - For each (T, R-year, isInfluential) triple, record a contribution
     to T's trajectory bucket for that year.
3. For each target T, fold the per-year contributions into a
   non-decreasing cumulative series `[{year, cum, infl}, ...]` and
   write it back as the value of T's `citation-trajectory` cell in
   landscape.html (and, transitively, in landscape.json when the next
   `make build` runs `extract.py`).

Cell shape
----------

  Status              | Value                                          | Citation
  --------------------|------------------------------------------------|---------------------------------------
  real-data           | JSON array `[{"year":N,"cum":M,"infl":K},...]` | S2 paper URL (the paper itself)
  real-data (empty)   | `[]` (paper in cache, no inbound from catalog) | S2 paper URL
  depth-floor-reached | `""`                                           | S2 paper URL (or attempted URL)
  not-applicable      | `"not applicable — non-paper row"`             | null

Determinism contract
--------------------

- Iterates records in catalog order, citations in cache order.
- Year-buckets sorted ascending in output.
- JSON serialised with `separators=(",", ":")` for byte-stability.
- Run idempotently: re-running over the same cache + landscape produces
  byte-identical output.

Usage
-----

  python3 scripts/bucket_s2_citations.py            # patches landscape.html in place
  python3 scripts/bucket_s2_citations.py --check    # writes to /tmp and diffs
  python3 scripts/bucket_s2_citations.py --quiet    # suppress per-row progress
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from _cell_writer import load_landscape, save_landscape, update_cell

ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
LANDSCAPE_HTML = ROOT / "landscape.html"
CACHE_DIR = ROOT / "extraction" / "s2-cache"


# ---------------------------------------------------------------------------
# Identifier regexes — kept in sync with scripts/fetch_citations.py
# ---------------------------------------------------------------------------

ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,6})(?:v\d+)?", re.IGNORECASE)
ARXIV_TOKEN_RE = re.compile(r"\barxiv:\s*(\d{4}\.\d{4,6})", re.IGNORECASE)
ARXIV_API_RE = re.compile(r"api\.semanticscholar\.org/graph/v1/paper/arXiv:(\d{4}\.\d{4,6})", re.IGNORECASE)
S2_HASH_RE = re.compile(r"semanticscholar\.org/paper/(?:[A-Za-z0-9_:%\.-]+/)?([a-f0-9]{40})")
ID_ARXIV_SUFFIX_RE = re.compile(r"--arxiv-(\d{4}-\d{4,6})$")
ID_ARXIV_YYMM_RE = re.compile(r"--arxiv-(\d{4})-\d{4,6}$")
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>)]+)")


# ---------------------------------------------------------------------------
# Identifier extraction (same as fetch_citations.py for cache filename)
# ---------------------------------------------------------------------------


def extract_paper_identifier(record: dict) -> str | None:
    """Pick the best S2 paperId for a catalog record — mirrors
    fetch_citations.py.extract_paper_identifier(). Returns the paperId
    string used as the cache filename stem, or None."""
    m = ID_ARXIV_SUFFIX_RE.search(record["id"])
    if m:
        aid = m.group(1).replace("-", ".", 1)
        return f"arXiv:{aid}"

    url = record.get("url") or ""
    m = ARXIV_URL_RE.search(url)
    if m:
        return f"arXiv:{m.group(1)}"

    cit_cell = record.get("cells", {}).get("citations") or {}
    cit_url = cit_cell.get("citation") or ""
    cit_val = cit_cell.get("value") or ""
    for src in (cit_url, cit_val):
        if not src:
            continue
        m = (ARXIV_URL_RE.search(src)
             or ARXIV_API_RE.search(src)
             or ARXIV_TOKEN_RE.search(src))
        if m:
            return f"arXiv:{m.group(1)}"

    for src in (cit_url, cit_val, url):
        if not src:
            continue
        m = S2_HASH_RE.search(src)
        if m:
            return m.group(1)

    for cell_key in ("links", "desc", "claims"):
        cell = record.get("cells", {}).get(cell_key) or {}
        for src in (cell.get("citation") or "", cell.get("value") or ""):
            if not src:
                continue
            m = ARXIV_URL_RE.search(src) or ARXIV_API_RE.search(src) or ARXIV_TOKEN_RE.search(src)
            if m:
                return f"arXiv:{m.group(1)}"

    return None


def cache_filename(paper_id: str) -> str:
    return paper_id.replace(":", "_").replace("/", "_") + ".json"


# ---------------------------------------------------------------------------
# CatalogIndex — mirror fetch_citations.py.CatalogIndex
# ---------------------------------------------------------------------------


def slugify_arxiv(arxiv_id: str) -> str:
    return arxiv_id.replace(".", "-")


class CatalogIndex:
    """Map every external identifier to a catalog record id."""

    def __init__(self, records: list[dict]):
        self.by_arxiv: dict[str, str] = {}
        self.by_s2_hash: dict[str, str] = {}
        self.by_doi: dict[str, str] = {}

        for r in records:
            m = ID_ARXIV_SUFFIX_RE.search(r["id"])
            if m:
                self.by_arxiv.setdefault(m.group(1), r["id"])

            urls = [r.get("url") or ""]
            for cell in (r.get("cells") or {}).values():
                if isinstance(cell, dict):
                    if cell.get("citation"):
                        urls.append(cell["citation"])
                    if cell.get("value"):
                        urls.append(cell["value"])

            for src in urls:
                if not src:
                    continue
                m = ARXIV_URL_RE.search(src) or ARXIV_API_RE.search(src) or ARXIV_TOKEN_RE.search(src)
                if m:
                    slug = slugify_arxiv(m.group(1))
                    self.by_arxiv.setdefault(slug, r["id"])
                m = S2_HASH_RE.search(src)
                if m:
                    self.by_s2_hash.setdefault(m.group(1), r["id"])
                for dm in DOI_RE.finditer(src):
                    doi = dm.group(1).rstrip(".,;:)\"'").lower()
                    self.by_doi.setdefault(doi, r["id"])

    def resolve_cited(self, cited: dict) -> str | None:
        ext = (cited or {}).get("externalIds") or {}

        arxiv = ext.get("ArXiv") or ext.get("arXiv") or ext.get("arxiv")
        if arxiv:
            slug = slugify_arxiv(arxiv)
            if slug in self.by_arxiv:
                return self.by_arxiv[slug]

        paper_id = (cited or {}).get("paperId")
        if paper_id and paper_id in self.by_s2_hash:
            return self.by_s2_hash[paper_id]

        doi = ext.get("DOI") or ext.get("doi")
        if doi and doi.lower() in self.by_doi:
            return self.by_doi[doi.lower()]

        return None


# ---------------------------------------------------------------------------
# Year extraction for the citing record
# ---------------------------------------------------------------------------


def extract_record_year(record: dict) -> int | None:
    """Pull the publication year (YYYY) from a record. Strategy:
      1. arxiv id-suffix `--arxiv-YYMM-NNNNN` → 20YY (or 19YY for YY ≥ 90).
      2. arxiv URL anywhere in cells → same YYMM trick.
      3. `created` cell → first 4-digit year in 1990..2099 range.
    """
    m = ID_ARXIV_YYMM_RE.search(record["id"])
    if m:
        yy = int(m.group(1)[:2])
        return 2000 + yy if yy < 90 else 1900 + yy

    # Try arxiv URL anywhere in the record
    candidates = [record.get("url") or ""]
    for cell in (record.get("cells") or {}).values():
        if isinstance(cell, dict):
            if cell.get("citation"):
                candidates.append(cell["citation"])
            if cell.get("value"):
                candidates.append(cell["value"])

    for src in candidates:
        if not src:
            continue
        m = ARXIV_URL_RE.search(src) or ARXIV_API_RE.search(src) or ARXIV_TOKEN_RE.search(src)
        if m:
            yy = int(m.group(1)[:2])
            return 2000 + yy if yy < 90 else 1900 + yy

    # Fall back: scan `created` cell for first YYYY
    created = (record.get("cells") or {}).get("created") or {}
    created_val = created.get("value") or ""
    m = re.search(r"\b(19\d{2}|20\d{2})\b", created_val)
    if m:
        return int(m.group(1))

    return None


# ---------------------------------------------------------------------------
# Bucket: walk every cache file and build inbound trajectories
# ---------------------------------------------------------------------------


def build_trajectories(
    records: list[dict], index: CatalogIndex
) -> tuple[dict[str, list[dict]], dict[str, str], dict[str, Any]]:
    """Return (trajectories_by_target, paperid_by_record, stats).

    trajectories_by_target maps target-record-id → sorted list of
      {"year": int, "cum": int, "infl": int}.

    paperid_by_record maps record-id → paperId string (for citation URLs)
    for every record that has a usable cache file.
    """
    stats = {
        "records_total": len(records),
        "records_with_paperid": 0,
        "records_with_cache_file": 0,
        "records_with_year": 0,
        "cache_entries_total": 0,
        "cache_entries_resolved": 0,
        "cache_entries_self": 0,
        "cache_entries_unresolved": 0,
        "cache_parse_errors": 0,
        "targets_with_trajectory": 0,
        "targets_with_empty_trajectory": 0,
    }

    # per-target: {year: [cum_delta, infl_delta]} accumulated raw
    # We aggregate per (target, citing_record) to dedupe within run —
    # if the same citing paper appears twice in its own ref list (S2
    # has occasionally been observed to do this), we only count once.
    raw: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    seen_pairs: set[tuple[str, str]] = set()  # (citing_id, target_id)

    paperid_by_record: dict[str, str] = {}

    for rec in records:
        paper_id = extract_paper_identifier(rec)
        if not paper_id:
            continue
        stats["records_with_paperid"] += 1

        cache_file = CACHE_DIR / cache_filename(paper_id)
        if not cache_file.exists():
            continue
        stats["records_with_cache_file"] += 1
        paperid_by_record[rec["id"]] = paper_id

        year = extract_record_year(rec)
        if year is None:
            continue
        stats["records_with_year"] += 1

        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            stats["cache_parse_errors"] += 1
            continue

        data = cache.get("data") or []
        for entry in data:
            stats["cache_entries_total"] += 1
            cited = entry.get("citedPaper") or {}
            target_id = index.resolve_cited(cited)
            if target_id is None:
                stats["cache_entries_unresolved"] += 1
                continue
            if target_id == rec["id"]:
                stats["cache_entries_self"] += 1
                continue
            pair = (rec["id"], target_id)
            if pair in seen_pairs:
                # Already counted this citing→target relation for this run
                continue
            seen_pairs.add(pair)
            stats["cache_entries_resolved"] += 1

            is_infl = bool(entry.get("isInfluential"))
            raw[target_id][year][0] += 1
            if is_infl:
                raw[target_id][year][1] += 1

    # Fold per-year deltas into cumulative trajectories.
    trajectories: dict[str, list[dict]] = {}
    for target_id, year_map in raw.items():
        years_sorted = sorted(year_map.keys())
        cum, infl_cum = 0, 0
        traj: list[dict] = []
        for y in years_sorted:
            delta, infl_delta = year_map[y]
            cum += delta
            infl_cum += infl_delta
            traj.append({"year": y, "cum": cum, "infl": infl_cum})
        trajectories[target_id] = traj
        if traj:
            stats["targets_with_trajectory"] += 1

    # Also record records that have a cache file but ZERO inbound citations —
    # they get an empty trajectory `[]`. These appear in paperid_by_record
    # but NOT in trajectories. Mark them so the writer treats them as
    # real-data (empty array) rather than no-data.
    for rec_id in paperid_by_record:
        if rec_id not in trajectories:
            trajectories[rec_id] = []
            stats["targets_with_empty_trajectory"] += 1

    return trajectories, paperid_by_record, stats


# ---------------------------------------------------------------------------
# HTML patching — adapted from fetch_commit_trajectories.py
# ---------------------------------------------------------------------------


# Capture both the empty placeholder shape and any prior-real-data shape so the
# script is idempotent (re-running over already-bucketed HTML reproduces same
# output). The `.*?` plus DOTALL is bounded by the cell's `</td>`.
CELL_RE = re.compile(
    r'<td class="citation-trajectory">.*?</td>',
    re.DOTALL,
)


def s2_paper_url(paper_id: str) -> str:
    """`arXiv:2304.03442` -> `https://www.semanticscholar.org/paper/arXiv:2304.03442`.
    For raw 40-char hashes, same convention works."""
    # S2 accepts /paper/arXiv:NNNN or /paper/<hash> directly.
    return f"https://www.semanticscholar.org/paper/{paper_id}"


def render_real_cell(trajectory: list[dict], paper_id: str) -> str:
    val = json.dumps(trajectory, separators=(",", ":"))
    cite_url = s2_paper_url(paper_id)
    return (
        f'<td class="citation-trajectory">'
        f'<span class="trajectory-data">{val}</span> '
        f'<a class="cite" href="{cite_url}" title="source">↗</a>'
        f'</td>'
    )


def render_depth_floor_cell(paper_id: str) -> str:
    cite_url = s2_paper_url(paper_id)
    return (
        f'<td class="citation-trajectory">'
        f'<span class="no-data">searched not found</span> '
        f'<a class="cite" href="{cite_url}" title="searched">↗</a>'
        f'</td>'
    )


def render_not_applicable_cell() -> str:
    return (
        '<td class="citation-trajectory">'
        '<span class="no-data" style="font-style:italic;color:#555;">'
        'not applicable — non-paper row</span>'
        '</td>'
    )


def patch_html_for_row(
    html: str,
    row_name: str,
    row_url: str | None,
    new_cell_html: str,
    occurrence: int = 0,
) -> tuple[str, bool]:
    """Patch the citation-trajectory cell for the row whose name+url match.
    Mirrors fetch_commit_trajectories.patch_html_for_row exactly."""
    from html import escape

    name_escaped = escape(row_name)

    if row_url:
        url_escaped = escape(row_url, quote=True)
        anchor_pat = re.compile(
            re.escape(f'<td class="name"><a href="{url_escaped}">')
            + re.escape(name_escaped)
            + re.escape('</a></td>')
        )
    else:
        anchor_pat = re.compile(
            re.escape(f'<td class="name">{name_escaped}</td>')
        )

    matches = list(anchor_pat.finditer(html))
    if not matches or occurrence >= len(matches):
        return html, False
    m = matches[occurrence]

    end_tr = html.find('</tr>', m.end())
    if end_tr < 0:
        return html, False
    row_chunk = html[m.start():end_tr]
    cell_m = CELL_RE.search(row_chunk)
    if cell_m is None:
        return html, False
    abs_start = m.start() + cell_m.start()
    abs_end = m.start() + cell_m.end()
    new_html = html[:abs_start] + new_cell_html + html[abs_end:]
    return new_html, True


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    target_json = args.target == "landscape.json"
    if not target_json:
        print(
            "warning: --target landscape.html is deprecated under Path A; "
            "writes will go to landscape.html for legacy compatibility only.",
            file=sys.stderr,
        )

    if not LANDSCAPE_JSON.exists():
        print(f"error: {LANDSCAPE_JSON} not found", file=sys.stderr)
        return 1
    if not target_json and not LANDSCAPE_HTML.exists():
        print(f"error: {LANDSCAPE_HTML} not found", file=sys.stderr)
        return 1
    if not CACHE_DIR.exists():
        print(f"error: {CACHE_DIR} not found", file=sys.stderr)
        return 1

    landscape = load_landscape(LANDSCAPE_JSON)
    data = landscape
    records = landscape["records"]
    if not args.quiet:
        print(f"bucket_s2_citations: loaded {len(records)} records", file=sys.stderr)

    index = CatalogIndex(records)
    if not args.quiet:
        print(
            f"  index: {len(index.by_arxiv)} arxiv, "
            f"{len(index.by_s2_hash)} s2-hash, {len(index.by_doi)} doi",
            file=sys.stderr,
        )

    trajectories, paperid_by_record, stats = build_trajectories(records, index)

    if not args.quiet:
        print(file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print("Bucket statistics", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        for k, v in stats.items():
            print(f"  {k:35s} {v}", file=sys.stderr)
        print(file=sys.stderr)

    # Year-span report
    all_years = []
    for traj in trajectories.values():
        for p in traj:
            all_years.append(p["year"])
    if all_years and not args.quiet:
        print(
            f"  trajectory year span: {min(all_years)} - {max(all_years)}",
            file=sys.stderr,
        )

    # Per-row writes — either update landscape.json cells or patch HTML.
    html = LANDSCAPE_HTML.read_text(encoding="utf-8") if not target_json and LANDSCAPE_HTML.exists() else ""
    occurrence_counter: dict[tuple[str, str | None], int] = {}

    counts = Counter()
    failed: list[tuple[str, str]] = []

    for rec in records:
        name = rec.get("name") or ""
        url = rec.get("url")
        key = (name, url)
        occ = occurrence_counter.get(key, 0)
        occurrence_counter[key] = occ + 1
        rec_id = rec["id"]

        paper_id = paperid_by_record.get(rec_id)
        traj = trajectories.get(rec_id)

        if paper_id is not None:
            # Real-data: has cache → has a trajectory (possibly [])
            kind = "real-data"
            value = json.dumps(traj or [], separators=(",", ":"))
            citation = s2_paper_url(paper_id)
            status = "real-data"
        else:
            # No usable paperId means no S2 cache for this row.
            kind = "not-applicable"
            value = "not applicable — non-paper row"
            citation = None
            status = "not-applicable"

        if target_json:
            update_cell(
                rec,
                "citation-trajectory",
                value=value,
                status=status,
                citation=citation,
            )
            counts[kind] += 1
        else:
            if paper_id is not None:
                cell_html = render_real_cell(traj or [], paper_id)
            else:
                cell_html = render_not_applicable_cell()
            new_html, ok = patch_html_for_row(html, name, url, cell_html, occurrence=occ)
            if not ok:
                failed.append((rec_id, name))
                counts["skip-row-not-found"] += 1
                continue
            html = new_html
            counts[kind] += 1

    if not args.quiet:
        print("Patched HTML row totals:", file=sys.stderr)
        for kind, n in counts.most_common():
            print(f"  {kind:25s} {n}", file=sys.stderr)
        if failed:
            print(f"  failed-to-locate-row: {len(failed)}", file=sys.stderr)
            for rid, nm in failed[:10]:
                print(f"    {rid}  {nm}", file=sys.stderr)

    # Top-5 most-cited within catalog (by raw count)
    if not args.quiet:
        ranked = sorted(
            trajectories.items(),
            key=lambda kv: -(kv[1][-1]["cum"] if kv[1] else 0),
        )
        records_by_id = {r["id"]: r for r in records}
        print(file=sys.stderr)
        print("Top 5 trajectories by cumulative count:", file=sys.stderr)
        for tid, traj in ranked[:5]:
            if not traj:
                continue
            name = records_by_id[tid]["name"]
            tail = traj[-1]
            print(
                f"  {name[:45]:45s}  {tail['cum']:3d} cum / {tail['infl']:3d} infl  "
                f"({len(traj)} years)",
                file=sys.stderr,
            )

    # Write out
    if args.check:
        if target_json:
            import tempfile
            tmp = Path(tempfile.mktemp(suffix=".json", prefix="landscape.bucketed."))
            save_landscape(landscape, tmp)
            existing = LANDSCAPE_JSON.read_bytes()
            new = tmp.read_bytes()
            tmp.unlink(missing_ok=True)
        else:
            out_path = Path("/tmp/landscape.html.bucketed")
            out_path.write_text(html, encoding="utf-8")
            existing = LANDSCAPE_HTML.read_bytes()
            new = out_path.read_bytes()
        if existing == new:
            print("CHECK: byte-identical to existing output.", file=sys.stderr)
            return 0
        else:
            print(
                f"CHECK: differs from existing output ({len(new) - len(existing):+d} bytes).",
                file=sys.stderr,
            )
            return 1

    if target_json:
        save_landscape(landscape, LANDSCAPE_JSON)
        if not args.quiet:
            print(f"wrote {LANDSCAPE_JSON}", file=sys.stderr)
    else:
        LANDSCAPE_HTML.write_text(html, encoding="utf-8")
        if not args.quiet:
            print(f"wrote {LANDSCAPE_HTML}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="Write to /tmp and diff against existing output (do not modify).",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress progress output (errors still go to stderr).",
    )
    parser.add_argument(
        "--target",
        choices=["landscape.json", "landscape.html"],
        default="landscape.json",
        help=(
            "Where to write citation-trajectory cells. Default (Path A) is "
            "landscape.json; landscape.html remains as a deprecated legacy "
            "path during the #68 transition window."
        ),
    )
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
