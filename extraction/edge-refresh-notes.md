# Edge-graph refresh notes — 2026-05-12

Post-Round-7 catalog (699 records). Two coordinated passes against the
already-committed edge graph:

1. Re-run `scripts/build_edges.py` over the regenerated `web/landscape.json`.
2. Re-run `scripts/fetch_citations.py` to refresh S2 `cites` edges,
   including four candidate lineages (SSM, RLHF, Embedding,
   Agent-protocol) surfaced by analysis.md v2.

Cache-hit dominated: 207 cache / 24 network calls; runtime 72.2s.

## Headline delta

| metric                | before | after | delta |
|-----------------------|-------:|------:|------:|
| total edges           |   278  |  298  |   +20 |
| `cites`               |   217  |  237  |   +20 |
| `built-on`            |    22  |   22  |    0  |
| `extends`             |     3  |    3  |    0  |
| `forks`               |     2  |    2  |    0  |
| `integrates-with`     |    31  |   31  |    0  |
| `same-team-as`        |     2  |    2  |    0  |
| `succeeds`            |     1  |    1  |    0  |

All 20 new edges are `cites` from S2 — no new cell-mined edges from
the Round-7 rows. The cell-miner returned only the same 9 edges as
before. The Round-7 framework rows (Mem0/LangGraph/Zep neighbourhood)
*do* mention Mem0, LangGraph, Zep in their `desc`/`integrates`/
`adjacent-infrastructure` cells, but those mentions are landing in
the `cross-references CSV` discard pile or the cell-miner discard
pile (see "Persistent gaps" below) rather than in the edge graph.

## Top 10 hubs (inbound degree) — before → after

| rank | before                            | n  | after                             | n  | Δ   |
|-----:|-----------------------------------|---:|-----------------------------------|---:|----:|
| 1    | mem0--mem0-ai                     | 12 | mem0--mem0-ai                     | 12 |  0  |
| 2    | locomo--arxiv-2402-17753          |  9 | graphrag-microsoft--microsoft-com | 12 | +3  |
| 3    | memgpt-v2-agent-tools             |  9 | memgpt-v2-agent-tools             | 10 | +1  |
| 4    | a-mem--gh-wujiangxu-a-mem         |  9 | compressive-transformer           | 10 | +2  |
| 5    | graphrag-microsoft                |  9 | locomo--arxiv-2402-17753          |  9 |  0  |
| 6    | compressive-transformer           |  8 | a-mem--gh-wujiangxu-a-mem         |  9 |  0  |
| 7    | transformer-xl                    |  8 | transformer-xl                    |  8 |  0  |
| 8    | zep-graphiti--getzep-com          |  7 | zep-graphiti--getzep-com          |  7 |  0  |
| 9    | generative-agents--arxiv-2304-...|  6 | generative-agents                 |  7 | +1  |
| 10   | memorybank--arxiv-2305-10250      |  5 | retro--arxiv-2112-04426           |  6 | +1  |

**Mem0 did NOT grow past 12.** All 12 inbound Mem0 edges are
`integrates-with` / `built-on` from the cross-references CSV, not
from cell-mined Round-7 rows. The new 176 records did not surface
fresh edges into Mem0 because the cross-references CSV hasn't been
re-mined for the Round-7 sections.

Largest hub jump: **GraphRAG (Microsoft) +3** (now tied #1 with Mem0
at 12 inbound). All three new edges are influential `cites` from
newly-fetched research papers in Round 7.

## Per-candidate-lineage verdict (descent edges = strong types + influential `cites`)

| Family            | members in catalog | inter-member descent edges | component status                                          | Verdict           |
|-------------------|-------------------:|---------------------------:|-----------------------------------------------------------|-------------------|
| Stanford agents   | 2 (one duplicate)  |  0                         | 1 in the 148-node mega-component, 1 isolated singleton    | **dissolved**     |
| SSM               | 6                  |  0                         | Hyena/Mamba/Mamba-2 in mega-component (no inter-edges); Jamba×2 + RWKV-7 isolated | **still candidate (sparse)** |
| RLHF              | 6                  |  2 (LoRA→QLoRA, DPO→GRPO)  | LoRA/QLoRA in mega-component; DPO/GRPO+MPO+SeAgent form a 4-node component | **still candidate** |
| Embedding         | 6                  |  0                         | BGE-M3 in mega-component (cites LoRA); rest are isolated singletons (Sentence-Transformers / BGE / GTE / Nomic / Mixedbread are products with no S2 paper or no inbound cites) | **sparse — promotion blocked by 5 isolated singletons** |
| Agent-protocol    | 3                  |  0                         | MCP-spec, A2A, AGNTCY all isolated singletons             | **sparse, as expected** |

Auto-discovered components (size ≥ 3) currently:

| size | sample anchor                                | character                                |
|-----:|----------------------------------------------|------------------------------------------|
|  148 | a-mem--gh-wujiangxu-a-mem                    | Research-paper mega-component (RAG/agent/memory papers, all linked by influential `cites`) |
|   10 | agno-phidata-memory--docs-phidata-com        | Agent-framework integration cluster (Agno/AgentCore/Neptune/FalkorDB/…) |
|    4 | dpo--arxiv-2305-18290                        | DPO/GRPO/MPO/SeAgent — the RLHF preference-optimisation sub-cluster |
|    3 | continue-dev-memory-mcp                      | MCP-memory implementations               |
|    3 | hindsight-mcp                                | Hindsight (Vectorize) family — same GH org |
|    3 | i-jepa--arxiv-2301-08243                     | JEPA family (I-JEPA / V-JEPA / V-JEPA-2) |
|    3 | meta-memory--arxiv-2509-20754                | Mixed: Meta-Memory + Milvus + NVIDIA ReMembR |

## Stanford agents — recap of the prior "partial 3-node" finding

Two records in the catalog match "Generative Agents":
- `generative-agents--arxiv-2304-03442`
- `generative-agents-park-et-al--arxiv-2304-03442`

These are duplicates (same arxiv suffix). The first one is heavily
connected (7 inbound influential cites from FinCon / G-Memory /
LoCoMo / Lyfe-Agents / MemTree / Retroformer / S-paper) and is
absorbed into the 148-node mega-component. The second has no inbound
edges and sits isolated. The "partial 3-node Stanford agents lineage"
described in analysis.md v2 dissolves once the duplicate is
deduplicated and the connected one is rolled into the mega-component.

**Verdict:** Stanford agents no longer reads as a discrete lineage. It
is one of many ancestor nodes inside the research-paper mega-component.
If we want it as a curated seed it needs depth-limited BFS (like the
RSSM / Graph-RAG curated seeds) and an explicit anchor.

## Persistent gaps in `build_edges.py` (what's still discarded)

After this refresh, the cell-miner still discards 40 cell-text
candidates and the cross-ref miner discards 17 CSV rows. Top patterns:

**Cell-miner discards (no-match by hint):**
- `'Ray'` (2×) — generic name, not in catalog
- `'LangGraph'` — ambiguous: matches two records
  (`langgraph-orchestration--langchain-com` and
  `langgraph-persistence--docs-langchain-com`) so resolver returns
  `ambiguous-substring`
- `'Mem0/Zep'` — combined hint, not a single product name
- `'OpenAI Assistants API'`, `'AutoGen v0'`, `'open-source Llama 3'`,
  `'DAPO'`, `'RAG-Anything'` — not in catalog
- `'proprietary 1'`, `'attention'`, `'hippocampal mechanisms'`,
  `'human feedback'`, `'the Ebbinghaus forgetting curve'`,
  `'20 bAbI reasoning tasks'`, `'retrospective consolidation'`,
  `'Workers'`, `'Hub'` — false-positive captures from the rule-table
  regex (cells use the trigger phrases in non-product ways)

**Cross-ref CSV discards (target name):**
- `'LangChain'` (7×) — flagged `known-unresolvable` (umbrella name;
  LangGraph / LangSmith are the real records)
- `'Redis'` (3×) — `known-unresolvable` (generic substrate)
- `'FAISS'`, `'OpenSearch'`, `'SQLite-Vec'`, `'LibSQL'`,
  `'Hunyuan'`, `'Llama 3.3'`, `'MCP servers (general)'`

The biggest fix-able item is the **LangGraph ambiguity**: when an
adjacent cell mentions "LangGraph" we want to land it on
`langgraph-persistence--docs-langchain-com` if the source row is
clearly memory-focused (and on `langgraph-orchestration` otherwise).
The cleanest mechanical fix is an alias rule: `"langgraph" →
"LangGraph Persistence"` for cells coming from any record whose
section is in `{Dedicated memory layers, Framework-embedded memory,
Agent frameworks (no first-party memory layer)}`. Left for a future
pass — out of scope for this 30-min refresh.

## What is NOT changing

- `web/landscape.json` is read-only here (the sibling-agent OSS
  enrichment may regenerate it; if so this edge refresh re-runs
  against the new corpus and the cache hit rate stays ≈100%).
- No new alias rules, no new schema fields, no `NAME_ALIASES` table
  additions.
- The 4 candidate lineages remain candidates — no curated seeds
  added. Promoting them to descent lineages would require either
  curated-seed entries in `web/src/lib/lineages.ts` (with
  depth-limited BFS) or fresh cell-mined `succeeds` / `extends` edges
  between members. Both are out of scope here; deferred to a future
  Track A iteration.

## Reproduction

```
python3 scripts/build_edges.py           # 61 edges (cell-mine only)
python3 scripts/fetch_citations.py       # restores 237 cites edges → 298 total
```

Determinism: with cache warm and `BUILD_EDGES_GENERATED_AT` /
`FETCH_CITATIONS_GENERATED_AT` defaulted to `2026-05-07T00:00:00Z`,
re-runs produce byte-identical output (`--check` verifies).
