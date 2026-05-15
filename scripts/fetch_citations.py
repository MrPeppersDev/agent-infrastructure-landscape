#!/usr/bin/env python3
"""
fetch_citations.py — pull Semantic Scholar `isInfluential` citations for every
research-paper row (T3 + T4) in `data/landscape.json` and append `cites` edges
to `data/landscape.edges.json`.

This script is the third edge-source for the catalog (after cross-references
CSV mining and cell-text mining done in `scripts/build_edges.py`). It does
NOT rebuild the cell-mined / cross-ref edges — it APPENDS new `cites` edges
on top of whatever `data/landscape.edges.json` already contains, deduplicating
by `(source, target, type)` with cell-mined edges winning on collision.

Determinism contract:
  - Edges sorted by `(source, target, type)` on output.
  - `generatedAt` is fixed (override via `FETCH_CITATIONS_GENERATED_AT`).
  - Cache populated under `extraction/s2-cache/<paperId>.json`; subsequent
    runs hit the cache and produce byte-identical output.

Rate limiting:
  - S2 free tier is 100 requests / 5 minutes (~3 sec spacing).
  - Default `--rate-delay` is 3.0 seconds. Backoff on 429 with up to 5 retries.
  - Hard cap on total runtime (~30 min) via `--max-seconds`.

Failure handling:
  - 5xx / network errors: retry with backoff, then skip with warning.
  - Paper without references list: skip cleanly.
  - 404 (e.g. arxiv-id is actually a date string): skip cleanly.
  - Rate-limit hit: exponential backoff and continue.

Usage:
  python3 scripts/fetch_citations.py
  python3 scripts/fetch_citations.py --check     # write to /tmp + diff
  python3 scripts/fetch_citations.py --offline   # cache-only (no network)
  python3 scripts/fetch_citations.py --no-cache  # force network even if cached
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Constants — kept in sync with docs/SCHEMA.md and scripts/build_edges.py.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0.0"
DEFAULT_GENERATED_AT = "2026-05-07T00:00:00Z"

REPO_ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = REPO_ROOT / "data" / "landscape.json"
EDGES_JSON = REPO_ROOT / "data" / "landscape.edges.json"
CACHE_DIR = REPO_ROOT / "extraction" / "s2-cache"

S2_API_BASE = "https://api.semanticscholar.org/graph/v1/paper"
S2_FIELDS = "isInfluential,citedPaper.externalIds,citedPaper.title"
S2_LIMIT = 1000

VALID_EDGE_TYPES = {
    "built-on", "runtime-dependency", "extends", "forks", "integrates-with",
    "competes-with", "inspired-by", "cites", "same-team-as", "succeeds",
}

# Same arxiv extraction regex as build_edges.py / extract.py.
ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,6})(?:v\d+)?", re.IGNORECASE)
ARXIV_TOKEN_RE = re.compile(r"\barxiv:\s*(\d{4}\.\d{4,6})", re.IGNORECASE)
ARXIV_BARE_RE = re.compile(r"\b(\d{4}\.\d{4,6})(?:v\d+)?\b")
ARXIV_API_RE = re.compile(r"api\.semanticscholar\.org/graph/v1/paper/arXiv:(\d{4}\.\d{4,6})", re.IGNORECASE)
S2_HASH_RE = re.compile(r"semanticscholar\.org/paper/(?:[A-Za-z0-9_:%\.-]+/)?([a-f0-9]{40})")
ID_ARXIV_SUFFIX_RE = re.compile(r"--arxiv-(\d{4}-\d{4,6})$")


# ---------------------------------------------------------------------------
# Identifier extraction.
# ---------------------------------------------------------------------------

def extract_paper_identifier(record: dict) -> tuple[str | None, str]:
    """Pick the best Semantic Scholar paperId for a catalog record.

    Returns (paperId, source) where source explains where it was found.
    paperId is a string in one of the forms S2 accepts on its
    `/paper/{id}` endpoint:
      - `arXiv:NNNN.NNNNN` (preferred — most catalogs key here)
      - the 40-char S2 hash (fallback for OpenReview / NeurIPS-only papers)

    Returns (None, reason) if no usable identifier exists.
    """
    # Priority 1: id suffix `--arxiv-XXXX-YYYYY` (extracted at extract.py time)
    m = ID_ARXIV_SUFFIX_RE.search(record["id"])
    if m:
        aid = m.group(1).replace("-", ".", 1)
        return f"arXiv:{aid}", "id-suffix"

    # Priority 2: arxiv URL in `url`
    url = record.get("url") or ""
    m = ARXIV_URL_RE.search(url)
    if m:
        return f"arXiv:{m.group(1)}", "url-arxiv"

    # Priority 3: arxiv URL or token in `cells.citations`
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
            return f"arXiv:{m.group(1)}", "citations-cell-arxiv"

    # Priority 4: S2 hash anywhere
    for src in (cit_url, cit_val, url):
        if not src:
            continue
        m = S2_HASH_RE.search(src)
        if m:
            return m.group(1), "s2-hash"

    # Priority 5: arxiv URL inside other free-text cells (links, desc)
    for cell_key in ("links", "desc", "claims"):
        cell = record.get("cells", {}).get(cell_key) or {}
        for src in (cell.get("citation") or "", cell.get("value") or ""):
            if not src:
                continue
            m = ARXIV_URL_RE.search(src) or ARXIV_API_RE.search(src) or ARXIV_TOKEN_RE.search(src)
            if m:
                return f"arXiv:{m.group(1)}", f"{cell_key}-cell-arxiv"

    return None, "no-identifier"


def slugify_arxiv(arxiv_id: str) -> str:
    """`2504.19413` -> `2504-19413` (matches slug suffix `--arxiv-2504-19413`)."""
    return arxiv_id.replace(".", "-")


def cache_path(paper_id: str) -> Path:
    """Filesystem-safe cache filename for an S2 paperId."""
    safe = paper_id.replace(":", "_").replace("/", "_")
    return CACHE_DIR / f"{safe}.json"


# ---------------------------------------------------------------------------
# Resolver: map S2-cited-paper externalIds to landscape record ids.
# ---------------------------------------------------------------------------

class CatalogIndex:
    """Index landscape records by every identifier that an S2 citedPaper
    might carry: arxiv-id slug (matches against record id suffix), and
    explicit arxiv URLs / S2 hashes anywhere in the record's cells."""

    def __init__(self, records: list[dict]):
        self.records = records
        self.by_id: dict[str, dict] = {r["id"]: r for r in records}

        # arxiv slug -> id (slug == "2504-19413")
        self.by_arxiv: dict[str, str] = {}
        # S2 paper hash -> id
        self.by_s2_hash: dict[str, str] = {}
        # DOI -> id
        self.by_doi: dict[str, str] = {}

        for r in records:
            # Arxiv from id-suffix
            m = ID_ARXIV_SUFFIX_RE.search(r["id"])
            if m:
                self.by_arxiv.setdefault(m.group(1), r["id"])

            # Walk every URL-bearing field for additional arxiv / S2 hooks
            urls = [r.get("url") or ""]
            cells = r.get("cells", {})
            for cell_key, cell in cells.items():
                if not isinstance(cell, dict):
                    continue
                if cell.get("citation"):
                    urls.append(cell["citation"])
                if cell.get("value"):
                    urls.append(cell["value"])

            for src in urls:
                if not src:
                    continue
                # Arxiv url
                m = ARXIV_URL_RE.search(src) or ARXIV_API_RE.search(src) or ARXIV_TOKEN_RE.search(src)
                if m:
                    slug = slugify_arxiv(m.group(1))
                    self.by_arxiv.setdefault(slug, r["id"])
                # S2 hash
                m = S2_HASH_RE.search(src)
                if m:
                    self.by_s2_hash.setdefault(m.group(1), r["id"])
                # DOI: 10.xxxx/something
                for dm in re.finditer(r"\b(10\.\d{4,9}/[^\s\"'<>)]+)", src):
                    doi = dm.group(1).rstrip(".,;:)\"'").lower()
                    self.by_doi.setdefault(doi, r["id"])

    def resolve_cited(self, cited: dict) -> tuple[str | None, str]:
        """cited has shape {externalIds: {ArXiv, DOI, CorpusId, ...}, paperId, title, ...}.
        Returns (record_id, reason) or (None, reason)."""
        ext = (cited or {}).get("externalIds") or {}

        # Arxiv first
        arxiv = ext.get("ArXiv") or ext.get("arXiv") or ext.get("arxiv")
        if arxiv:
            slug = slugify_arxiv(arxiv)
            if slug in self.by_arxiv:
                return self.by_arxiv[slug], f"arxiv:{arxiv}"

        # S2 paperId
        paper_id = (cited or {}).get("paperId")
        if paper_id and paper_id in self.by_s2_hash:
            return self.by_s2_hash[paper_id], f"s2-hash:{paper_id}"

        # DOI
        doi = ext.get("DOI") or ext.get("doi")
        if doi and doi.lower() in self.by_doi:
            return self.by_doi[doi.lower()], f"doi:{doi}"

        return None, "no-catalog-match"


# ---------------------------------------------------------------------------
# S2 API fetch with caching and rate-limit handling.
# ---------------------------------------------------------------------------

class S2Client:
    def __init__(self, rate_delay: float, max_retries: int, offline: bool, no_cache: bool,
                 deadline: float | None):
        self.rate_delay = rate_delay
        self.max_retries = max_retries
        self.offline = offline
        self.no_cache = no_cache
        self.deadline = deadline
        self.last_request_at = 0.0
        self.api_calls = 0
        self.cache_hits = 0
        self.errors: list[tuple[str, str]] = []

    def _wait_rate_limit(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_request_at
        if elapsed < self.rate_delay:
            time.sleep(self.rate_delay - elapsed)
        self.last_request_at = time.monotonic()

    def get_references(self, paper_id: str) -> dict | None:
        """Fetch references for `paper_id`. Returns the raw S2 response dict
        (with `data` array of citation entries) or None on a clean skip
        (404, no-references, terminal error)."""
        cache_file = cache_path(paper_id)

        # Cache hit
        if not self.no_cache and cache_file.exists():
            try:
                payload = json.loads(cache_file.read_text(encoding="utf-8"))
                self.cache_hits += 1
                return payload
            except json.JSONDecodeError:
                # corrupted cache — refetch
                pass

        if self.offline:
            self.errors.append((paper_id, "offline-and-no-cache"))
            return None

        if self.deadline is not None and time.monotonic() >= self.deadline:
            self.errors.append((paper_id, "runtime-cap-reached"))
            return None

        url = f"{S2_API_BASE}/{paper_id}/references?fields={S2_FIELDS}&limit={S2_LIMIT}"
        backoff = self.rate_delay
        for attempt in range(self.max_retries):
            self._wait_rate_limit()
            self.api_calls += 1
            req = Request(url, headers={"User-Agent": "memory-analysis-program/1.0 (issue #5)"})
            try:
                with urlopen(req, timeout=30) as resp:
                    body = resp.read().decode("utf-8")
                payload = json.loads(body)
                # Cache
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                return payload
            except HTTPError as e:
                if e.code == 404:
                    # paperId not found — cache empty payload so we don't refetch
                    empty = {"data": [], "_status": "not-found", "_paperId": paper_id}
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(
                        json.dumps(empty, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    self.errors.append((paper_id, f"404"))
                    return empty
                if e.code == 429:
                    # Rate-limited — exponential backoff
                    sleep_for = max(backoff, 5.0)
                    print(f"  [429] rate-limited on {paper_id}; sleeping {sleep_for:.1f}s",
                          file=sys.stderr, flush=True)
                    time.sleep(sleep_for)
                    backoff *= 2
                    continue
                if 500 <= e.code < 600:
                    sleep_for = backoff
                    print(f"  [{e.code}] server error on {paper_id}; sleeping {sleep_for:.1f}s",
                          file=sys.stderr, flush=True)
                    time.sleep(sleep_for)
                    backoff *= 2
                    continue
                self.errors.append((paper_id, f"http-{e.code}"))
                return None
            except (URLError, json.JSONDecodeError, TimeoutError, ConnectionResetError,
                    OSError) as e:
                sleep_for = backoff
                print(f"  [{type(e).__name__}] on {paper_id}; sleeping {sleep_for:.1f}s",
                      file=sys.stderr, flush=True)
                time.sleep(sleep_for)
                backoff = min(backoff * 2, 120.0)
                continue
            except Exception as e:  # pragma: no cover - last-resort guard
                print(f"  [unexpected:{type(e).__name__}] on {paper_id}: {e}",
                      file=sys.stderr, flush=True)
                self.errors.append((paper_id, f"unexpected:{type(e).__name__}"))
                return None
        self.errors.append((paper_id, f"max-retries-exceeded"))
        return None


# ---------------------------------------------------------------------------
# Edge generation.
# ---------------------------------------------------------------------------

def make_cite_edge(source_id: str, target_id: str, paper_id: str) -> dict:
    return {
        "source": source_id,
        "target": target_id,
        "type": "cites",
        "evidence": "S2 isInfluential citation",
        "citation": f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}",
        "isInfluential": True,
    }


def fetch_all_citations(records: list[dict], index: CatalogIndex,
                        client: S2Client) -> tuple[list[dict], dict]:
    """Walk every T3+T4 record, fetch its references, filter influential,
    resolve to catalog ids, return (new_edges, stats)."""
    stats = {
        "papers_total": 0,
        "papers_with_id": 0,
        "papers_skipped_no_id": 0,
        "papers_fetched": 0,
        "papers_fetch_failed": 0,
        "papers_no_references": 0,
        "raw_references": 0,
        "influential_references": 0,
        "resolved_in_catalog": 0,
        "discarded_unresolved": 0,
        "self_edges_skipped": 0,
        "duplicates_within_run": 0,
        "discard_reasons": Counter(),
    }
    new_edges: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()

    t34 = [r for r in records if r.get("tier") in (3, 4)]
    stats["papers_total"] = len(t34)
    for i, r in enumerate(t34, start=1):
        paper_id, src_reason = extract_paper_identifier(r)
        if not paper_id:
            stats["papers_skipped_no_id"] += 1
            continue
        stats["papers_with_id"] += 1

        if i % 25 == 0 or i == 1:
            print(
                f"  [{i}/{len(t34)}] {r['id'][:50]:50s}  paperId={paper_id}  "
                f"(api_calls={client.api_calls}, cache_hits={client.cache_hits})",
                file=sys.stderr, flush=True,
            )

        payload = client.get_references(paper_id)
        if payload is None:
            stats["papers_fetch_failed"] += 1
            continue

        if payload.get("_status") == "not-found":
            stats["papers_fetch_failed"] += 1
            continue

        stats["papers_fetched"] += 1
        data = payload.get("data") or []
        if not data:
            stats["papers_no_references"] += 1
            continue
        stats["raw_references"] += len(data)

        for entry in data:
            if not entry.get("isInfluential"):
                continue
            stats["influential_references"] += 1
            cited = entry.get("citedPaper") or {}
            target_id, reason = index.resolve_cited(cited)
            if not target_id:
                stats["discarded_unresolved"] += 1
                # Bucket discards by externalId-shape for the report
                ext = cited.get("externalIds") or {}
                key = "has-arxiv" if (ext.get("ArXiv") or ext.get("arXiv")) else (
                    "has-doi" if (ext.get("DOI") or ext.get("doi")) else (
                        "has-s2-only" if cited.get("paperId") else "no-ids"))
                stats["discard_reasons"][key] += 1
                continue
            if target_id == r["id"]:
                stats["self_edges_skipped"] += 1
                continue
            stats["resolved_in_catalog"] += 1
            edge_key = (r["id"], target_id, "cites")
            if edge_key in seen_keys:
                stats["duplicates_within_run"] += 1
                continue
            seen_keys.add(edge_key)
            new_edges.append(make_cite_edge(r["id"], target_id, paper_id))

    return new_edges, stats


# ---------------------------------------------------------------------------
# Merge with existing edges (cell-mined edges win on `(source,target,type)`).
# ---------------------------------------------------------------------------

def merge_edges(existing: list[dict], new_cites: list[dict]) -> list[dict]:
    by_key: dict[tuple[str, str, str], dict] = {}
    # First, install all existing edges (these win — cell-mined > cites).
    for e in existing:
        key = (e["source"], e["target"], e["type"])
        by_key.setdefault(key, e)
    # Then, install new cites only if the key is unclaimed.
    for e in new_cites:
        key = (e["source"], e["target"], e["type"])
        by_key.setdefault(key, e)
    return list(by_key.values())


# ---------------------------------------------------------------------------
# Validate against SCHEMA §7.2.
# ---------------------------------------------------------------------------

def validate(edges: list[dict], records_by_id: dict[str, dict]) -> None:
    seen: set[tuple[str, str, str]] = set()
    for e in edges:
        assert e["source"] in records_by_id, f"unknown source: {e['source']!r}"
        assert e["target"] in records_by_id, f"unknown target: {e['target']!r}"
        assert e["source"] != e["target"], f"self-edge: {e['source']}"
        assert e["type"] in VALID_EDGE_TYPES, f"bad type: {e['type']!r}"
        assert e["evidence"], f"empty evidence: {e!r}"
        assert e["citation"] and e["citation"].startswith(("http://", "https://")), \
            f"bad citation: {e!r}"
        if e["type"] == "cites":
            assert "isInfluential" in e and isinstance(e["isInfluential"], bool), \
                f"cites edge missing isInfluential: {e!r}"
        else:
            assert "isInfluential" not in e, \
                f"non-cites edge has isInfluential: {e!r}"
        key = (e["source"], e["target"], e["type"])
        assert key not in seen, f"duplicate edge key: {key}"
        seen.add(key)


# ---------------------------------------------------------------------------
# Reporting.
# ---------------------------------------------------------------------------

def report(stats: dict, all_edges: list[dict], existing_count: int,
           new_cites: list[dict], records_by_id: dict[str, dict],
           client: S2Client, runtime_s: float) -> str:
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("Semantic Scholar citation pull report")
    lines.append("=" * 70)
    lines.append(f"T3+T4 papers total:                {stats['papers_total']}")
    lines.append(f"  with usable paperId (arxiv/S2):  {stats['papers_with_id']}")
    lines.append(f"  skipped (no identifier):         {stats['papers_skipped_no_id']}")
    lines.append(f"  fetched successfully:            {stats['papers_fetched']}")
    lines.append(f"  fetch failed (404/5xx/timeout):  {stats['papers_fetch_failed']}")
    lines.append(f"  no references in S2:             {stats['papers_no_references']}")
    lines.append("")
    lines.append(f"References discovered (raw):       {stats['raw_references']}")
    lines.append(f"  isInfluential=true:              {stats['influential_references']}")
    lines.append(f"  resolved to catalog records:     {stats['resolved_in_catalog']}")
    lines.append(f"  discarded (target not in cat.):  {stats['discarded_unresolved']}")
    lines.append(f"  discarded self-edges:            {stats['self_edges_skipped']}")
    lines.append(f"  duplicates within run:           {stats['duplicates_within_run']}")
    if stats['discard_reasons']:
        lines.append("  discard breakdown by externalId shape:")
        for k, v in stats['discard_reasons'].most_common():
            lines.append(f"    {k:20s} {v}")
    lines.append("")
    lines.append(f"Network calls (S2 API):            {client.api_calls}")
    lines.append(f"Cache hits:                        {client.cache_hits}")
    lines.append(f"Errors logged:                     {len(client.errors)}")
    lines.append(f"Runtime:                           {runtime_s:.1f}s")
    lines.append("")
    lines.append(f"Existing edges before merge:       {existing_count}")
    lines.append(f"New `cites` edges added:           {len(new_cites)}")
    lines.append(f"Total edges after merge:           {len(all_edges)}")

    # Top 10 most-cited within catalog
    inbound_cites = Counter(
        e["target"] for e in all_edges if e["type"] == "cites"
    )
    lines.append("")
    lines.append("== Top 10 most-cited papers within catalog (inbound `cites`) ==")
    for tgt, n in inbound_cites.most_common(10):
        name = records_by_id[tgt]["name"]
        lines.append(f"  {n:4d}  {tgt:55s}  {name}")

    if client.errors[:10]:
        lines.append("")
        lines.append("== Sample errors ==")
        for pid, why in client.errors[:10]:
            lines.append(f"  {pid:30s}  {why}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entrypoint.
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="Write to /tmp and diff against existing output.")
    parser.add_argument("--offline", action="store_true",
                        help="Use cache only; do not call the network.")
    parser.add_argument("--no-cache", action="store_true",
                        help="Force network even if a cached response exists.")
    parser.add_argument("--rate-delay", type=float, default=3.0,
                        help="Seconds between S2 API requests (default: 3.0).")
    parser.add_argument("--max-retries", type=int, default=5,
                        help="Max retries on 429/5xx (default: 5).")
    parser.add_argument("--max-seconds", type=float, default=1800.0,
                        help="Soft runtime cap in seconds (default: 1800 = 30min).")
    args = parser.parse_args(argv)

    started_at = time.monotonic()
    deadline = started_at + args.max_seconds

    landscape = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))
    records: list[dict] = landscape["records"]
    records_by_id = {r["id"]: r for r in records}
    print(f"Loaded {len(records)} records.", file=sys.stderr)

    edges_payload = json.loads(EDGES_JSON.read_text(encoding="utf-8"))
    existing_edges: list[dict] = edges_payload["edges"]
    existing_count = len(existing_edges)
    print(f"Loaded {existing_count} existing edges.", file=sys.stderr)

    index = CatalogIndex(records)
    print(
        f"Catalog index: {len(index.by_arxiv)} arxiv, "
        f"{len(index.by_s2_hash)} s2-hash, {len(index.by_doi)} doi.",
        file=sys.stderr,
    )

    client = S2Client(
        rate_delay=args.rate_delay,
        max_retries=args.max_retries,
        offline=args.offline,
        no_cache=args.no_cache,
        deadline=deadline,
    )

    new_cites, stats = fetch_all_citations(records, index, client)
    print(f"Generated {len(new_cites)} new `cites` edges.", file=sys.stderr)

    merged = merge_edges(existing_edges, new_cites)
    # Re-sort deterministically
    merged.sort(key=lambda e: (e["source"], e["target"], e["type"]))

    # Validate every edge against SCHEMA §7.2
    validate(merged, records_by_id)

    # Verify that the original 58 edges are still present unchanged
    original_keys = {(e["source"], e["target"], e["type"]) for e in existing_edges}
    merged_keys = {(e["source"], e["target"], e["type"]) for e in merged}
    missing = original_keys - merged_keys
    assert not missing, f"existing edges dropped during merge: {missing}"

    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": os.environ.get("FETCH_CITATIONS_GENERATED_AT", DEFAULT_GENERATED_AT),
        "edges": merged,
    }

    out_path = Path("/tmp/landscape.edges.json") if args.check else EDGES_JSON
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    runtime_s = time.monotonic() - started_at
    print(report(stats, merged, existing_count, new_cites, records_by_id, client, runtime_s))

    if args.check and EDGES_JSON.exists():
        existing = EDGES_JSON.read_bytes()
        new = out_path.read_bytes()
        if existing == new:
            print("CHECK: byte-identical to existing output.", file=sys.stderr)
        else:
            print("CHECK: differs from existing output.", file=sys.stderr)
            return 1

    print(f"Wrote {out_path} ({len(merged)} edges).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
