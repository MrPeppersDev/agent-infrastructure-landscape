# AI Memory Landscape — Cross-Cutting Synthesis

**Date:** 2026-05-06
**Source:** 9 parallel analyses against the 520-row landscape catalog + 6-axis taxonomy + adoption/funding/activity data passes.

---

## The single biggest finding

**The field is converging at the paradigm level, diverging at the fingerprint level, and bifurcating at the deployment level — and the academy is not feeding the market.**

- 8 architectural paradigms cover 83% of 520 rows; vector-similarity alone is 33.5%, spanning 27 of ~33 sections.
- But at strict 6-axis taxonomy granularity, 364 distinct fingerprints exist with 288 singletons. Same paradigm, many local recipes.
- And T1 (production) and T4 (preprints) share *exactly one* dominant axis value (`retrieval=similarity`). Every other axis splits.

The story is not "RAG → KG → world-model." It is: **vector-RAG was already universal in 2023; graph and parametric layered onto it concurrently, not sequentially; and the late-2025 inflection (hybrid storage + episode unit + agentic retrieval) is the dedicated-memory-layer cohort bundling multi-store backends behind LLM-controlled retrieval over episodes** — *not* world-models.

---

## What the market is rewarding

From the architecture × adoption pass: the composite winning architecture is **inspectable + append-only + kv-or-file-backed + injection-retrieved + cross-session**. This is the **agent-framework / MCP-server pattern, not the purpose-built "memory layer" pattern.**

Per-axis median lifts (n ≥ 12 each):

| Axis value | Median ★ | Median funding | Notes |
|---|---:|---:|---|
| `governance: inspectable` | 16,600 | $65M | Most consistent winner |
| `update: append-only` | 11,300 | — | Also leads citations |
| `storage: kv` (open-vocab, NOT kv-cache) | 12,800 | $105M | Letta-style core/recall |
| `persistence: cross-session` | 33,850 | — | MCP pattern signature |
| `retrieval: injection` | 19,450 | $100M | Beats similarity ~10× |
| `storage: vector + retrieval: similarity` (baseline) | 2,300 | $45M | Below field median |

Anything-plus-injection beats anything-plus-similarity by ~10×. Vector + similarity is table-stakes baseline, not a winning bet.

**The starkest mismatch: graph-backed systems are community darlings without commercial backing.** Zep 25.7k★ on $3M, Supermemory 22.4k★ on $6M, Agno 39.9k★ on $5M.

---

## The dependency graph (who is in whose stack)

Power-law, not mesh. 80 explicit integration edges across the catalog; ~485 rows have zero edges. Top three hubs absorb 38% of inbound integrations:

| Rank | Hub | In-degree |
|---|---|---:|
| 1 | Mem0 | 14 |
| 2 | LangChain ecosystem | 11 |
| 3 | LangGraph Persistence | 5 |

Pure substrate sinks (depended on, depend on nothing): Pinecone, Qdrant, Redis, pgvector, Neo4j, FAISS, OpenSearch, LibSQL, Milvus, Chroma, LanceDB, Weaviate.

**Practical takeaway: to be in someone else's stack today, a product becomes (a) a Mem0 plug-in, (b) a LangChain-native node, or (c) a vector-DB substrate. No fourth shape exists with comparable in-degree.**

---

## Academy vs. market divergence

Top T1↔T4 divergences (Δ percentage points on coverage-normalised share):

**Production-only patterns:** `unit=fact` +45.7, `update=append-only` +36.1, `retrieval=injection` +34.0, `governance=inspectable` +30.7, `storage=relational` +16.8 (zero in T3/T4).

**Academy-only patterns:** `storage=hybrid` −25.4 (37 research / 0 production rows), `storage=parametric` −16.6, `update=parametric-edit` −14.8, `unit=skill` −12.0, `unit=trajectory` (11 research / 1 production).

**Strict translation gaps** (research has, production doesn't): hybrid storage, trajectory unit, and the entire parametric-memory family (knowledge editing, model-as-memory).

**Strict pragmatic gaps** (production has, research ignores): `governance=opaque`, `storage=relational`, `storage=column`. Postgres + S3 + a vector index + a markdown file with provenance is the production stack — almost none of those primitives appear in research papers.

Diversity paradox: research is more diverse by Shannon entropy (more values explored per axis) but **less** diverse by unique 6-tuple signatures (T1 0.84 vs T3 0.69). Papers cluster into archetypes; production mixes a smaller vocabulary into more distinct architectures.

---

## Governance is a genuine structural gap (not a tagging artifact)

- **Genuine governance** (`auditable` or `deterministic`): **57/520 = 11.0%**.
- Within agent frameworks (30/30 tagged): 0 auditable, 0 deterministic. Conflict resolution is LLM-arbitrate (6), overwrite/last-write-wins (8), append (6), or none (5). **Zero use bi-temporal versioning, deterministic rules, or human-in-the-loop conflict resolution.**
- Within dedicated memory layers (36 rows): only Zep/Graphiti has structured governance + bi-temporal versioning. All 35 others are LLM-arbitrate, overwrite, append, or none.
- Where governance does exist, it's **inherited from KG / enterprise-search / regulated-vertical traditions** — not invented for AI agents.

The single AI-native system combining provenance audit + structured conflict resolution: **Zep / Graphiti**. Everything else trusts the LLM, overwrites, appends, or punts.

---

## Capital is concentrated where the product isn't

| Section | Total disclosed funding |
|---|---:|
| Platform-provider memory | $156.1B |
| Coding-agent memory | $59.9B |
| Framework-embedded | $41.6B |
| Vector-DB infrastructure | $22.8B |
| Robotics / embodied | $5.3B |
| Browser-agent | $3.4B |
| ... | |
| **Dedicated memory layers** | **$1.87B (12th)** |

93% of disclosed capital sits outside dedicated memory. The 60× valuation gap (Devin $10.2B vs Mem0 $150M peak) is **confirmed and tightened to 68×** when restricted to priced-equity rounds.

Capital efficiency by section ($/★, lower = more efficient):

| Section | Median $/★ |
|---|---:|
| Memory observability | $272 |
| **Dedicated memory layers** | **$435** |
| Memory governance & safety | $436 |
| Framework-embedded | $793 |
| Claude Code memory | $2,154 |
| Vector-DB infrastructure | $2,562 |

Dedicated memory layers are the **most efficient capital users** — 6× cheaper than vector-DB infra, 19× cheaper than coding-agent products per disclosed dollar.

---

## Activity / abandonment

- 75.3% of rows with a maintenance signal are active (within 6 months).
- **T3 research repos: 24% active, 59% stalled.** Citation gravity is real.
- Most-stalled section: "Recent method papers" — 57% stalled among scored rows.
- T2 OSS zombie rate (high-star + stalled): ~7% (excluding Aider as a release-rare artefact).
- Real zombies: Generative Agents (21k★, dead Aug 2024), Bolt.new (16k★, dead Dec 2024), RAFT (13k★), KAG (8.7k★), V-JEPA family.
- Rising stars all in T2 and cluster in three sections: **Claude Code memory mechanisms** (5/10), **Dedicated memory layers** (3/10), **Framework-embedded memory** (1/10).

---

## Modality + deployment together

- **83% text-only.** Truly fully-multimodal: 7 rows out of 520.
- Multimodal is **bimodally concentrated**: voice-wearable (100% non-text) and vertical/domain-specific (47%, splitting cleanly into clinical-voice scribes and robotics/AV vision+sensor).
- **Dedicated memory layers — the architectural core — are 94% text-only.** Mem0, Letta, Zep, Cognee, MemMachine all assume tokens.
- Multimodal is *not* a post-2025 phenomenon. Pre-2020 (24% non-text) and 2026-to-date (0%) bracket the trend; the recent boom is *all* text agents.
- Deployment is **bifurcated, not converging**: 15.6% self-only / 45.5% SaaS-only / 39% both. Splits cleanly by section.
- Substrate-ownership cluster (≥70% offer self-host): frameworks, KGs, dedicated memory layers, Claude Code, vector DBs, governance, observability, coding-agent.
- Hosted-only cluster: Personal/PKM (80% SaaS), vertical (82.5%), voice/wearable (89%), platform-provider (93%), **browser-agents (100%)**.
- T1 maturity correlates with hosted-only (52.9% SaaS-only) vs T2 substrate-friendly (60% offer self-host). Successful products get pulled toward lock-in by market gravity.

**The combined finding: text-only memory is where substrate ownership is winnable; multimodal memory is where vendor lock-in has already won.**

---

## Where this is heading (10-finding consolidated read)

1. **Convergence at paradigm level (8 paradigms cover 83%), divergence at recipe level (288 singleton fingerprints).** Vector RAG never gave way; graph and parametric layered onto it.
2. **The market rewards inspectable + append-only + kv/file + injection + cross-session.** Agent-framework / MCP pattern, not purpose-built memory layer. Vector+similarity is below median.
3. **Late-2025 inflection: hybrid storage + episode unit + agentic retrieval move together.** This is the dedicated-memory-layer cohort (Mem0, Letta, Zep, MIRIX, ~20 others), not world-models.
4. **The dependency graph is power-law: Mem0, LangChain, LangGraph dominate.** Path to being adopted = Mem0 plug-in / LangChain node / vector-DB substrate.
5. **Academy and market are diverging.** They share only `retrieval=similarity`. Translation gap (research-only): hybrid storage, parametric memory family, trajectory unit. Pragmatic gap (production-only): relational/column storage, opaque governance.
6. **Governance gap is real, not artifact.** 11% have genuine governance. Zep/Graphiti is the only AI-native combination of provenance + structured conflict resolution. Everything else trusts the LLM.
7. **Capital concentration is extreme (93% outside dedicated memory).** 68× valuation gap (coding agents vs memory layers). Dedicated memory layers are the most efficient capital users — under-funded relative to coding agents but not under-valued relative to revenue.
8. **Research repos rot (T3: 59% stalled).** Live edge is in T2 Claude Code mechanisms, dedicated memory, and framework-embedded — every rising-star repo is in those three sections.
9. **83% text-only. Multimodal is forced by use case, not chosen.** Voice-wearable and vertical (clinical/robotics) carry 55% of all non-text rows. Dedicated memory tier is 94% text-only.
10. **Deployment is bifurcated. Browser-agents are 100% SaaS-only.** Substrate ownership wins in frameworks/KGs/memory-layers; vendor lock-in wins in vertical/PKM/voice/platform/browser.

---

## What this all says about "where it's heading"

Three strong directional signals from the substrate:

**(A) The agent-framework / MCP pattern has won the developer mindshare and the GitHub stargazing.** It's also where the 2025H2 dedicated-memory-layer cohort is plugging in. If you're building a memory product today and want adoption, you ship as a Mem0 / LangChain / Claude Code integration before you ship a standalone product.

**(B) Capital is betting that memory becomes a vertical-product feature, not horizontal infrastructure.** Coding-agent memory ($59.9B), platform-provider memory ($156B), browser-agent memory ($3.4B all SaaS-only) — all bigger than dedicated memory layers ($1.87B). The market isn't paying for "memory as substrate"; it's paying for "memory inside an applied product."

**(C) Three white-spaces are real and quantified.** (1) Genuine governance / conflict resolution at the agent-write interface (only Zep/Graphiti). (2) Multimodal substrate (94% of dedicated memory tier is text-only; multimodal exists only inside vertical lock-in). (3) Cross-session, cross-vendor portability of memory state (no row in the catalog provides this; even self-hostable memory layers are not portable across the four hub types).

If a memory-substrate program wanted to differentiate against the field as captured here, those three are the defensible white-space — not "another vector-graph hybrid."
