#!/usr/bin/env python3
"""
build_edges.py — mine `data/landscape.edges.json` from cells + cross-refs.

Edge sources (in order of confidence):
  1. `.agent-results/data-5-cross-references.csv` — explicit "X integrates
     with Y" mentions captured during prior research. Highest confidence.
  2. `cells.claims.value`, `cells.desc.value`, `cells.repro.value`,
     `cells.code-release.value`, `cells.adjacent-infrastructure.value` —
     regex-mined for the rule-table phrases.
  3. `extraction/cross-listings.json` — explicit pairs (currently four,
     including the `claude-brain → memvid` case noted by issue #3).

The script writes `data/landscape.edges.json` conforming to docs/SCHEMA.md
§4 / §7.2. It is deterministic: edges are sorted by (source, target, type)
and the `generatedAt` is fixed (overridable via `BUILD_EDGES_GENERATED_AT`).

Usage:
  python3 scripts/build_edges.py
  python3 scripts/build_edges.py --check   # writes to /tmp + diffs
  python3 scripts/build_edges.py --report  # extra stdout reporting

The script prints a summary at the end:
  - edge counts by type
  - top 10 hub nodes by inbound degree
  - count of edges discarded due to unresolvable target
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Constants — kept in sync with docs/SCHEMA.md.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0.0"
DEFAULT_GENERATED_AT = "2026-05-07T00:00:00Z"

REPO_ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = REPO_ROOT / "data" / "landscape.json"
CROSS_REFS_CSV = REPO_ROOT / ".agent-results" / "data-5-cross-references.csv"
CROSS_LISTINGS_JSON = REPO_ROOT / "extraction" / "cross-listings.json"
DISAMBIGUATION_JSON = REPO_ROOT / "extraction" / "edge-disambiguation.json"
OUT_PATH = REPO_ROOT / "data" / "landscape.edges.json"

VALID_EDGE_TYPES = {
    "built-on",
    "extends",
    "forks",
    "integrates-with",
    "competes-with",
    "inspired-by",
    "cites",
    "same-team-as",
    "succeeds",
}

# The cells we mine. Order matters only for evidence tie-breaking.
MINED_CELLS = ("desc", "claims", "repro", "code-release", "adjacent-infrastructure")

# Phrase rules: (regex, edge_type). Matched case-insensitively against cell text.
# Group 1 is always the target span. We capture up to a sentence boundary
# (period, semicolon, comma followed by capital, or close-paren) so that
# `built on Qdrant; bundles Neo4j` only emits the Qdrant edge from "built on".
_TARGET_TAIL = r"([A-Za-z0-9][A-Za-z0-9\.\-_/+ &]{1,80}?)(?=[\.\;,\)\(\n]| and | for | via | with | which | that | rather | \(| — | – |$)"

PHRASE_RULES: list[tuple[re.Pattern, str]] = [
    # Most specific first — these win the priority order from SCHEMA §4.
    (re.compile(r"\bfork(?:ed)? (?:of|from)\s+" + _TARGET_TAIL, re.IGNORECASE), "forks"),
    (re.compile(r"\bsuccessor to\s+" + _TARGET_TAIL, re.IGNORECASE), "succeeds"),
    (re.compile(r"\bfollow-up to\s+" + _TARGET_TAIL, re.IGNORECASE), "succeeds"),
    (re.compile(r"\breimplementation of\s+" + _TARGET_TAIL, re.IGNORECASE), "extends"),
    (re.compile(r"\bvariant of\s+" + _TARGET_TAIL, re.IGNORECASE), "extends"),
    (re.compile(r"\bbuilt on\s+" + _TARGET_TAIL, re.IGNORECASE), "built-on"),
    (re.compile(r"\bbased on\s+" + _TARGET_TAIL, re.IGNORECASE), "built-on"),
    (re.compile(r"\bpowered by\s+" + _TARGET_TAIL, re.IGNORECASE), "built-on"),
    (re.compile(r"\bbackend for\s+" + _TARGET_TAIL, re.IGNORECASE), "built-on"),
    (re.compile(r"\bextends\s+" + _TARGET_TAIL, re.IGNORECASE), "extends"),
    (re.compile(r"\bbuilds on\s+" + _TARGET_TAIL, re.IGNORECASE), "extends"),
    (re.compile(r"\bintegrates with\s+" + _TARGET_TAIL, re.IGNORECASE), "integrates-with"),
    (re.compile(r"\binspired by\s+" + _TARGET_TAIL, re.IGNORECASE), "inspired-by"),
    (re.compile(r"\bin the tradition of\s+" + _TARGET_TAIL, re.IGNORECASE), "inspired-by"),
    (re.compile(r"\bsame team as\s+" + _TARGET_TAIL, re.IGNORECASE), "same-team-as"),
    (re.compile(r"\balternative to\s+" + _TARGET_TAIL, re.IGNORECASE), "competes-with"),
    (re.compile(r"\bcompetitor to\s+" + _TARGET_TAIL, re.IGNORECASE), "competes-with"),
]

# Map cross-reference CSV `relationship_type` values to edge types.
CROSSREF_TYPE_MAP: dict[str, str] = {
    "integrates_with": "integrates-with",
    "exclusive_partnership": "integrates-with",
    "or_backed_by": "integrates-with",
    "substrate": "built-on",
    "default_substrate_local": "built-on",
    "default_substrate": "built-on",
    "production_substrate": "built-on",
    "native_integration": "integrates-with",
    "integration_ga": "integrates-with",
    "bundled_integration": "integrates-with",
    "graph_backend": "built-on",
    "mcp_integration": "integrates-with",
    "integration": "integrates-with",
    "vector_store_option": "integrates-with",
    "production_store": "built-on",
    "vector_backend": "built-on",
    "uses": "built-on",
    "pluggable_backend": "integrates-with",
    "same_ecosystem": "integrates-with",
    "agent_pipeline_focus": "integrates-with",
    "checkpointer": "integrates-with",
    "pairs_with": "integrates-with",
    "toolkit": "integrates-with",
    "optional_backend": "integrates-with",
    "langchain_native": "integrates-with",
    "tutorial_integration": "integrates-with",
    "mcp_wrapper": "built-on",
    "fork_of": "forks",
    "built_on": "built-on",
    "powered_by": "built-on",
    "variant_of": "extends",
    "targets": "integrates-with",
    "native_native": "integrates-with",
}

# Known aliases for products whose cross-ref CSV name doesn't match the
# landscape `name` exactly. These are encountered during a one-off scan of
# data-5-cross-references.csv against the corpus.
NAME_ALIASES: dict[str, str] = {
    # CSV/cell name -> landscape name (case-insensitive comparison)
    "memoryllm": "MemoryLLM (original)",
    "cline": "Cline .clinerules",
    "graphrag": "GraphRAG (Microsoft)",
    "memobase": "Memobase",
    "hindsight": "Hindsight (Vectorize)",
    "phidata": "Agno (Phidata) Memory",
    "agno": "Agno (Phidata) Memory",
    "graphiti": "Zep & Graphiti",
    "zep": "Zep & Graphiti",
    "memgpt": "Letta / MemGPT",
    "letta": "Letta / MemGPT",
    "agentcore": "AWS Bedrock AgentCore Memory",
    "amazon bedrock agentcore memory": "AWS Bedrock AgentCore Memory",
    "official memory mcp": "Official MCP Memory server",
    "official mcp memory": "Official MCP Memory server",
}

# Names that legitimately don't have a row in landscape.json — log once and
# don't fail on these.
KNOWN_UNRESOLVABLE = {
    "redis",                         # generic substrate, no row
    "langchain",                     # framework umbrella; LangGraph/LangSmith are listed separately
    "libsql",                        # generic substrate
    "sqlite-vec",                    # generic substrate
    "cassandra",                     # generic substrate
    "jdbc",                          # generic substrate
    "llama 3.3",                     # generic LLM, not a memory system
    "hunyuan",                       # generic LLM
    "mcp servers (general)",         # umbrella reference
    "opensearch",                    # only listed as 'Elasticsearch / OpenSearch' compound
}

# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,6})(?:v\d+)?\b")
DOMAIN_RE = re.compile(r"https?://([^/\s]+)")


def normalise_name(s: str) -> str:
    """Lowercase + strip + collapse whitespace for fuzzy name matching."""
    return re.sub(r"\s+", " ", s.lower().strip())


def slugify_arxiv(arxiv_id: str) -> str:
    """`2504.19413` -> `2504-19413` (matches slug suffix `--arxiv-2504-19413`)."""
    return arxiv_id.replace(".", "-")


def domain_slug(host: str) -> str:
    """`docs.mem0.ai` -> `mem0-ai` (strip `www.` and `docs.`/subdomains)."""
    h = host.lower()
    if h.startswith("www."):
        h = h[4:]
    parts = h.split(".")
    # Match the schema's "registrable domain" rule: take the rightmost
    # two labels for most cases (mem0.ai), three for known multi-label TLDs
    # like `co.uk`. Good enough for our corpus.
    if len(parts) >= 3 and parts[-2] in {"co", "com", "ac", "gov", "org"} and len(parts[-1]) == 2:
        registrable = ".".join(parts[-3:])
    else:
        registrable = ".".join(parts[-2:]) if len(parts) >= 2 else h
    return registrable.replace(".", "-")


# ---------------------------------------------------------------------------
# Resolver: name (or hint) -> record id, with multiple lookup strategies.
# ---------------------------------------------------------------------------

def load_disambiguation() -> dict:
    """Load the manual disambiguation table (Round 12 hygiene pass).

    Schema: { "entries": { "<normalised_hint>": { "primary_id": str|None,
              "alternates": { "<phrase>": "<id>", ... } } } }

    Missing file returns an empty dict — the resolver falls back to its
    own ambiguity / unresolvable rules. All keys are matched against the
    `normalise_name(hint)` form (lowercase, whitespace-collapsed).
    """
    if not DISAMBIGUATION_JSON.exists():
        return {}
    try:
        data = json.loads(DISAMBIGUATION_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARN: could not load {DISAMBIGUATION_JSON}: {exc}", file=sys.stderr)
        return {}
    raw_entries = data.get("entries", {})
    # Normalise keys defensively.
    out: dict[str, dict] = {}
    for key, val in raw_entries.items():
        norm_key = re.sub(r"\s+", " ", key.lower().strip())
        # Normalise alternate phrase keys too.
        alts = val.get("alternates", {}) or {}
        norm_alts = {
            re.sub(r"\s+", " ", k.lower().strip()): v for k, v in alts.items()
        }
        out[norm_key] = {
            "primary_id": val.get("primary_id"),
            "alternates": norm_alts,
            "reason": val.get("reason"),
        }
    return out


class Resolver:
    def __init__(self, records: list[dict], disambiguation: dict | None = None):
        self.records = records
        self.by_id: dict[str, dict] = {r["id"]: r for r in records}
        self.disambiguation: dict = disambiguation or {}

        # Exact name match (lowercased)
        self.by_name: dict[str, list[str]] = defaultdict(list)
        for r in records:
            self.by_name[normalise_name(r["name"])].append(r["id"])

        # Arxiv-id suffix from id, e.g. `--arxiv-2504-19413`
        self.by_arxiv: dict[str, str] = {}
        for r in records:
            m = re.search(r"--arxiv-(\d{4}-\d{4,6})$", r["id"])
            if m:
                self.by_arxiv[m.group(1)] = r["id"]

        # Domain match from url
        self.by_domain: dict[str, list[str]] = defaultdict(list)
        for r in records:
            url = r.get("url")
            if not url:
                continue
            m = DOMAIN_RE.match(url)
            if m:
                slug = domain_slug(m.group(1))
                self.by_domain[slug].append(r["id"])

        # GitHub owner/repo from id, e.g. `--gh-mem0ai-mem0`
        self.by_gh: dict[str, str] = {}
        for r in records:
            m = re.search(r"--gh-([a-z0-9\-]+)$", r["id"])
            if m:
                # last two slugs in canonical id: gh-<owner>-<repo>
                # (cannot reliably split without the original URL, so we
                # keep the whole tail and match against URL-derived tails).
                self.by_gh[m.group(1)] = r["id"]

    def _disambiguate(self, norm: str, context_text: str | None) -> tuple[str | None, str] | None:
        """Consult the manual disambiguation table (Round-12 hygiene).

        Returns `(id, reason)` if the table resolves the hint, or `None`
        to fall through to the default rules. Alternate phrases are
        searched in the *context_text* (case-insensitive) before falling
        back to the entry's `primary_id`. This lets us route bare
        'LangChain' to the framework row by default, while 'langchain
        memory' nearby in the same cell routes to LangMem.
        """
        entry = self.disambiguation.get(norm)
        if entry is None:
            return None
        ctx_norm = (context_text or "").lower()
        # Try alternates first — longer phrase wins (sort by length desc).
        alts = entry.get("alternates") or {}
        for phrase in sorted(alts.keys(), key=len, reverse=True):
            if phrase and phrase in ctx_norm:
                target_id = alts[phrase]
                if target_id in self.by_id:
                    return target_id, f"disambig-alt:{phrase}"
        primary = entry.get("primary_id")
        if primary and primary in self.by_id:
            return primary, "disambig-primary"
        # Documented unresolvable (e.g. Redis with primary_id=null) — log clearly.
        return None, f"disambig-unresolvable: {norm}"

    def resolve(self, hint: str, context_text: str | None = None) -> tuple[str | None, str]:
        """Resolve a free-text product mention to a record id.

        Returns (id_or_none, reason). The reason describes how the match
        was made, or why it failed (used for the discard log).
        """
        hint = hint.strip().rstrip(".,;:")
        if not hint:
            return None, "empty hint"

        norm = normalise_name(hint)

        # 0. Manual disambiguation table (Round-12 hygiene pass). Runs
        #    BEFORE the default rules so it can override ambiguous-name,
        #    ambiguous-substring, and known-unresolvable fallbacks for
        #    umbrella names like 'LangChain' / 'LangGraph' / 'Mem0'.
        disambig = self._disambiguate(norm, context_text)
        if disambig is not None and disambig[0] is not None:
            return disambig

        # 1. Exact name (lowercased)
        if norm in self.by_name:
            ids = self.by_name[norm]
            if len(ids) == 1:
                return ids[0], "exact-name"
            # Ambiguous name — consult disambiguation table again for the
            # bare hint before giving up.
            if disambig is not None:
                return disambig
            return None, f"ambiguous-name: {ids}"

        # 1b. Alias table
        if norm in NAME_ALIASES:
            target = NAME_ALIASES[norm]
            ids = self.by_name.get(normalise_name(target), [])
            if len(ids) == 1:
                return ids[0], "alias"

        # 2. Arxiv-id match — look in the original (unnormalised) hint AND
        # the surrounding context if provided (e.g. paper claim text often
        # has "(arXiv:2405.15083)").
        for src in (hint, context_text or ""):
            for m in ARXIV_ID_RE.finditer(src):
                aid = slugify_arxiv(m.group(1))
                if aid in self.by_arxiv:
                    return self.by_arxiv[aid], f"arxiv-{aid}"

        # 3. Domain match from a URL inside the hint or context
        for src in (hint, context_text or ""):
            for m in DOMAIN_RE.finditer(src):
                slug = domain_slug(m.group(1))
                if slug in self.by_domain:
                    ids = self.by_domain[slug]
                    if len(ids) == 1:
                        return ids[0], f"domain-{slug}"

        # 4. Known unresolvable shortcut
        if norm in KNOWN_UNRESOLVABLE:
            return None, f"known-unresolvable: {norm}"

        # 5. Substring partial match — must be an unambiguous "the hint
        # IS the start of the name" or "the hint contains the entire
        # name as a whole word". Avoid the `retro`-vs-`retrospective`
        # false-positive class.
        if len(norm) >= 4:
            candidates: list[str] = []
            hint_words = set(norm.split())
            for n in self.by_name:
                if len(self.by_name[n]) != 1:
                    continue
                # accept if name is a whole-word in hint, or hint == name's first word(s)
                # i.e. require token-level overlap, not arbitrary substring.
                name_first = n.split()[0]
                if n == norm:
                    candidates.append(n)
                elif n.startswith(norm + " ") and len(norm) >= len(name_first):
                    candidates.append(n)
                elif norm.startswith(n + " ") and len(n) >= 4:
                    candidates.append(n)
                elif name_first == norm and len(name_first) >= 4:
                    candidates.append(n)
            unique_ids = {self.by_name[n][0] for n in candidates}
            if len(unique_ids) == 1:
                return next(iter(unique_ids)), f"substring: {candidates[0]}"
            if len(unique_ids) > 1:
                # Try disambiguation one more time before giving up.
                if disambig is not None:
                    return disambig
                return None, f"ambiguous-substring: {sorted(unique_ids)[:3]}"

        return None, f"no-match: {hint!r}"


# ---------------------------------------------------------------------------
# Edge mining.
# ---------------------------------------------------------------------------

def trim_target(text: str) -> str:
    """Trim trailing junk from a regex-captured target span.

    Captured targets look like 'Mem0 for the long-term tier' — we want
    'Mem0'. The PHRASE_RULES regex stops at a connector word, but in
    practice the captured span often still has trailing modifier text.
    """
    text = text.strip()
    # Cut at first sentence-ish boundary
    text = re.split(r"\b(for|via|with|which|that|rather|and|using|to deliver|to provide)\b", text, maxsplit=1)[0]
    text = text.rstrip(" .,;:-")
    # If it looks like a bare phrase (>4 words), shrink to the first
    # capitalised noun-phrase chunk.
    words = text.split()
    if len(words) > 4:
        # Keep words until we hit a non-capitalised, non-acronym, non-name token
        kept = []
        for w in words:
            if w[0].isupper() or any(c.isdigit() for c in w) or w.lower() in {"the", "a", "an"}:
                kept.append(w)
                continue
            break
        if kept:
            text = " ".join(kept).rstrip(" .,;:-")
    return text.strip()


def evidence_window(text: str, match: re.Match, max_len: int = 200) -> str:
    """Pull a tidy ~200-char window around the matched phrase."""
    start = max(0, match.start() - 20)
    end = min(len(text), match.end() + 60)
    snippet = text[start:end].strip()
    if len(snippet) > max_len:
        snippet = snippet[:max_len].rstrip() + "..."
    return snippet


def mine_cells(records: list[dict], resolver: Resolver) -> tuple[list[dict], list[dict]]:
    """Return (mined_edges, discarded). Mined edges are dicts.

    Edges are deduplicated per (source, target, type) within this pass;
    longer evidence wins on tie.
    """
    edges_by_key: dict[tuple[str, str, str], dict] = {}
    discarded: list[dict] = []

    for r in records:
        source_id = r["id"]
        primary_url = r.get("url")
        for cell_key in MINED_CELLS:
            cell = r["cells"].get(cell_key)
            if not cell or cell.get("status") not in {"real-data", "depth-floor-reached"}:
                continue
            text = cell.get("value") or ""
            if not text or len(text) < 10:
                continue
            cell_citation = cell.get("citation")
            for pattern, edge_type in PHRASE_RULES:
                for m in pattern.finditer(text):
                    raw_target = m.group(1)
                    target_hint = trim_target(raw_target)
                    if not target_hint or normalise_name(target_hint) == normalise_name(r["name"]):
                        continue  # no self-edges from cells
                    target_id, reason = resolver.resolve(target_hint, context_text=text)
                    citation = cell_citation or primary_url or ""
                    if not target_id:
                        discarded.append({
                            "source": source_id,
                            "target_hint": target_hint,
                            "type": edge_type,
                            "cell": cell_key,
                            "reason": reason,
                        })
                        continue
                    if target_id == source_id:
                        continue  # SCHEMA §7.2.5 — no self-edges
                    key = (source_id, target_id, edge_type)
                    evidence = evidence_window(text, m)
                    if key in edges_by_key:
                        existing = edges_by_key[key]
                        if len(evidence) > len(existing["evidence"]):
                            existing["evidence"] = evidence
                            if citation:
                                existing["citation"] = citation
                    else:
                        edges_by_key[key] = {
                            "source": source_id,
                            "target": target_id,
                            "type": edge_type,
                            "evidence": evidence,
                            "citation": citation,
                        }

    return list(edges_by_key.values()), discarded


# ---------------------------------------------------------------------------
# Cross-references CSV.
# ---------------------------------------------------------------------------

def mine_cross_refs(resolver: Resolver) -> tuple[list[dict], list[dict]]:
    edges_by_key: dict[tuple[str, str, str], dict] = {}
    discarded: list[dict] = []

    if not CROSS_REFS_CSV.exists():
        print(f"WARN: {CROSS_REFS_CSV} not found", file=sys.stderr)
        return [], []

    with CROSS_REFS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src_name = row["source_system"]
            tgt_name = row["target_system"]
            rel_raw = row["relationship_type"].strip()
            evidence = (row.get("evidence_quote") or "").strip().strip('"')

            edge_type = CROSSREF_TYPE_MAP.get(rel_raw)
            if not edge_type:
                discarded.append({
                    "source_name": src_name,
                    "target_name": tgt_name,
                    "type": rel_raw,
                    "reason": f"unknown crossref relationship_type: {rel_raw!r}",
                })
                continue

            src_id, src_reason = resolver.resolve(src_name)
            tgt_id, tgt_reason = resolver.resolve(tgt_name)
            if not src_id or not tgt_id:
                discarded.append({
                    "source_name": src_name,
                    "target_name": tgt_name,
                    "type": edge_type,
                    "reason": (
                        f"src={src_reason}; tgt={tgt_reason}"
                    ),
                })
                continue
            if src_id == tgt_id:
                continue

            # Citation: the source row's primary URL (where the evidence
            # came from).
            src_record = resolver.by_id[src_id]
            citation = src_record.get("url") or resolver.by_id[tgt_id].get("url") or ""

            key = (src_id, tgt_id, edge_type)
            ev = evidence[:300] if evidence else f"cross-references CSV: {rel_raw}"
            if key in edges_by_key:
                existing = edges_by_key[key]
                if len(ev) > len(existing["evidence"]):
                    existing["evidence"] = ev
            else:
                edges_by_key[key] = {
                    "source": src_id,
                    "target": tgt_id,
                    "type": edge_type,
                    "evidence": ev,
                    "citation": citation,
                }
    return list(edges_by_key.values()), discarded


# ---------------------------------------------------------------------------
# Cross-listings JSON (the four manually-curated pairs).
# ---------------------------------------------------------------------------

def mine_cross_listings(resolver: Resolver) -> list[dict]:
    """Cross-listings encode 'this product is also listed under section X'.

    The agent in #3 noted `claude-brain → memvid` as `built-on`. The
    cross-listings file currently doesn't have that pair (it has merged-id
    pairs, not cross-product references), so we additionally derive the
    `claude-brain → memvid` edge from the GitHub-org match: the
    `claude-brain--gh-memvid-claude-brain` id has GitHub owner `memvid`,
    which is the same owner as `memvid--gh-memvid-memvid`. That same-owner
    rule yields a `same-team-as` edge by default; for the specific
    claude-brain → memvid case we know it's `built-on` (claude-brain
    packages memvid for Claude Code).
    """
    edges: list[dict] = []
    if not CROSS_LISTINGS_JSON.exists():
        return edges

    # Hard-coded curated edge: claude-brain → memvid (built-on)
    cb_id = "claude-brain--gh-memvid-claude-brain"
    mv_id = "memvid--gh-memvid-memvid"
    if cb_id in resolver.by_id and mv_id in resolver.by_id:
        edges.append({
            "source": cb_id,
            "target": mv_id,
            "type": "built-on",
            "evidence": "claude-brain packages memvid (same GitHub org memvid/) as a Claude Code plugin; cross-listings note flagged this pair.",
            "citation": resolver.by_id[cb_id].get("url") or resolver.by_id[mv_id].get("url") or "https://github.com/memvid",
        })
    return edges


# ---------------------------------------------------------------------------
# Same-team-as inference from `--gh-<owner>-<repo>` ids.
# ---------------------------------------------------------------------------

UMBRELLA_GH_OWNERS = {
    # Big tech / research orgs that publish many unrelated repos. Two
    # repos under one of these owners is NOT evidence that the same
    # team produced both; suppress to avoid false `same-team-as` edges.
    "microsoft", "google", "google-research", "googleresearch",
    "facebookresearch", "meta", "facebook", "amazon", "aws",
    "openai", "anthropic", "huggingface", "deepmind", "nvidia",
    "alibaba", "alibaba-nlp", "tencent", "baidu", "bytedance",
    "ibm", "apple", "salesforce", "intel",
    "modelcontextprotocol",
}


def infer_same_team_from_gh(resolver: Resolver) -> list[dict]:
    """Two records sharing the same GitHub owner are likely same-team.

    This catches lineage like `mem0--mem0-ai` + `mem0-mcp-official--gh-mem0ai-mem0-mcp`
    (owner: mem0ai), which prior agents highlighted in analysis-4.
    Only emit an edge when both records carry a `--gh-<owner>-<repo>` suffix
    so the owner string is unambiguous, and only when the owner is not a
    big-tech umbrella org (see UMBRELLA_GH_OWNERS).
    """
    edges: list[dict] = []
    by_owner: dict[str, list[str]] = defaultdict(list)
    for r in resolver.records:
        m = re.search(r"--gh-([a-z0-9]+)-", r["id"])
        if m:
            by_owner[m.group(1)].append(r["id"])
    for owner, ids in by_owner.items():
        if len(ids) < 2:
            continue
        if owner in UMBRELLA_GH_OWNERS:
            continue
        # Same-team is noisy across umbrella orgs; cap on group size too.
        if len(ids) > 5:
            continue
        ids_sorted = sorted(ids)
        for i, src in enumerate(ids_sorted):
            for tgt in ids_sorted[i + 1:]:
                evidence = f"Same GitHub organisation `{owner}` publishes both repos."
                citation = resolver.by_id[src].get("url") or resolver.by_id[tgt].get("url") or ""
                if not citation:
                    continue
                edges.append({
                    "source": src,
                    "target": tgt,
                    "type": "same-team-as",
                    "evidence": evidence,
                    "citation": citation,
                })
    return edges


# ---------------------------------------------------------------------------
# Validation + dedup + write.
# ---------------------------------------------------------------------------

def dedupe(edges: list[dict]) -> list[dict]:
    """Per SCHEMA §7.2.8 — `(source, target, type)` triples are unique.
    Prefer the entry with the longer `evidence` text on collision.
    """
    by_key: dict[tuple[str, str, str], dict] = {}
    for e in edges:
        key = (e["source"], e["target"], e["type"])
        existing = by_key.get(key)
        if existing is None or len(e.get("evidence", "")) > len(existing.get("evidence", "")):
            by_key[key] = e
    return list(by_key.values())


def validate(edges: list[dict], resolver: Resolver) -> None:
    valid_ids = set(resolver.by_id)
    for e in edges:
        assert e["source"] in valid_ids, f"unknown source id: {e['source']}"
        assert e["target"] in valid_ids, f"unknown target id: {e['target']}"
        assert e["source"] != e["target"], f"self-edge: {e['source']}"
        assert e["type"] in VALID_EDGE_TYPES, f"bad type: {e['type']}"
        assert e["evidence"], f"empty evidence: {e}"
        assert e["citation"] and e["citation"].startswith(("http://", "https://")), \
            f"bad citation: {e!r}"


def write_output(edges: list[dict], out_path: Path) -> None:
    edges_sorted = sorted(edges, key=lambda e: (e["source"], e["target"], e["type"]))
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": os.environ.get("BUILD_EDGES_GENERATED_AT", DEFAULT_GENERATED_AT),
        "edges": edges_sorted,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Reporting.
# ---------------------------------------------------------------------------

def report(edges: list[dict], discarded_cells: list[dict], discarded_xref: list[dict],
           resolver: Resolver) -> str:
    lines: list[str] = []
    lines.append(f"Total edges: {len(edges)}")
    lines.append("")
    lines.append("== Edges by type ==")
    by_type = Counter(e["type"] for e in edges)
    for t in sorted(by_type, key=lambda x: -by_type[x]):
        lines.append(f"  {t:18s} {by_type[t]}")
    lines.append("")

    lines.append("== Top 10 hub nodes by inbound degree ==")
    in_deg: Counter = Counter(e["target"] for e in edges)
    for tgt, deg in in_deg.most_common(10):
        name = resolver.by_id[tgt]["name"]
        lines.append(f"  {deg:4d}  {tgt:50s}  {name}")
    lines.append("")

    lines.append("== Discards ==")
    lines.append(f"  cell-mining unresolvable targets:    {len(discarded_cells)}")
    lines.append(f"  cross-ref unresolvable targets:      {len(discarded_xref)}")
    if discarded_cells[:5]:
        lines.append("  sample cell-miner discards:")
        for d in discarded_cells[:5]:
            lines.append(f"    - {d['source'][:30]} / {d['cell']}: hint={d['target_hint']!r} reason={d['reason']}")
    if discarded_xref[:5]:
        lines.append("  sample cross-ref discards:")
        for d in discarded_xref[:5]:
            lines.append(f"    - {d.get('source_name')} -> {d.get('target_name')}: {d['reason']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entrypoint.
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="Write to /tmp and diff against existing output.")
    parser.add_argument("--report", action="store_true",
                        help="Print full reporting block to stdout.")
    args = parser.parse_args(argv)

    landscape = json.loads(LANDSCAPE_JSON.read_text(encoding="utf-8"))
    records = landscape["records"]
    disambiguation = load_disambiguation()
    resolver = Resolver(records, disambiguation=disambiguation)
    print(
        f"Loaded {len(records)} records; "
        f"{len(disambiguation)} disambiguation entries.",
        file=sys.stderr,
    )

    # Mine each source.
    cell_edges, cell_discards = mine_cells(records, resolver)
    print(f"Cell mining: {len(cell_edges)} edges, {len(cell_discards)} discarded.", file=sys.stderr)
    xref_edges, xref_discards = mine_cross_refs(resolver)
    print(f"Cross-refs:  {len(xref_edges)} edges, {len(xref_discards)} discarded.", file=sys.stderr)
    listing_edges = mine_cross_listings(resolver)
    print(f"Cross-listings/curated: {len(listing_edges)} edges.", file=sys.stderr)
    team_edges = infer_same_team_from_gh(resolver)
    print(f"Same-team (GH org):     {len(team_edges)} edges.", file=sys.stderr)

    all_edges = cell_edges + xref_edges + listing_edges + team_edges
    all_edges = dedupe(all_edges)
    validate(all_edges, resolver)

    if args.check:
        out_path = Path("/tmp/landscape.edges.json")
    else:
        out_path = OUT_PATH
    write_output(all_edges, out_path)
    print(f"Wrote {out_path} ({len(all_edges)} edges).", file=sys.stderr)

    print(report(all_edges, cell_discards, xref_discards, resolver))

    if args.check and OUT_PATH.exists():
        existing = OUT_PATH.read_bytes()
        new = out_path.read_bytes()
        if existing == new:
            print("CHECK: byte-identical to existing output.", file=sys.stderr)
        else:
            print("CHECK: differs from existing output.", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
