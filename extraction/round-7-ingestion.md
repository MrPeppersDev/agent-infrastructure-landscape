# Round 7 — Scope expansion ingestion (2026-05-12)

The "broader AI-infrastructure sphere" sweep authorized by the
2026-05-12 scope expansion entry in `docs/DECISIONS.md`.

## Mandate

> "we want everything we can get our hands on in this sphere — dont even
> bother to calculate the rough size, that just puts soft limitations on
> the number of things you pull in"

Three previously-excluded categories are now in scope: training
infrastructure, generic (non-memory) vector/search infrastructure, and
agent frameworks without first-party memory layers. Plus continued
expansion of memory-shaped systems.

## Result

**Total catalog: 699 records (was 523, +176 net).**

176 new rows landed across 8 existing sections + 6 newly-created
sections.

## New sections created

Six new top-level sections, all reachable via the section-explainers
sidecar and recognised by the canonical-sections set in `extract.py`:

1. **Training infrastructure** (51 rows) — fine-tuning platforms,
   RLHF stacks, dataset stores, label tools, data versioning,
   distributed training systems, synthetic data.
2. **Search platforms (non-memory)** (15 rows) — pure vector DBs and
   managed-cloud SKUs, hybrid search engines, search-as-a-service
   APIs. Distinct from "Vector-database infrastructure" which is
   scoped to substrates known to underlie memory products.
3. **Agent frameworks (no first-party memory layer)** (39 rows) —
   agent orchestration / tool-calling frameworks whose primary value
   is not memory. Some are cross-listings of existing
   Framework-embedded-memory rows (LangChain, LlamaIndex, AutoGen,
   CrewAI, LangGraph).
4. **Inference platforms & gateways** (15 rows) — inference-as-a-
   service clouds (Together, Modal, Baseten, Fireworks, Replicate,
   Anyscale) and LLM gateways (LiteLLM, OpenRouter, Portkey).
5. **Embedding & reranker services** (11 rows) — hosted embedding /
   reranker APIs (Cohere Embed, Voyage AI, OpenAI Embeddings, Mistral
   Embed, Jina, Nomic, BGE, GTE, Sentence Transformers).
6. **Evaluation & observability platforms** (15 rows) — LLM/agent
   eval/tracing/observability (LangSmith, LangFuse, Helicone, Arize
   Phoenix, Galileo, Patronus, Confident AI, TruEra/TruLens,
   Braintrust, Humanloop, Vellum, Ragas, OpenInference, OpenLLMetry,
   PromptLayer, Arize). Distinct from the memory-specific "Memory
   observability & monitoring" section.

## Per-category counts of new rows

| Category | Section | New rows |
|---|---|---:|
| Memory-shaped (expanded sweep) | Dedicated memory layers | 4 |
| Memory-shaped (expanded sweep) | Framework-embedded memory | 1 |
| Memory-shaped (expanded sweep) | Retrieval-as-memory hybrids | 5 |
| Memory-shaped (expanded sweep) | Recent method papers (subsections) | 20 |
| Training infrastructure | Training infrastructure | 51 |
| Generic search | Search platforms (non-memory) | 15 |
| Generic search | Embedding & reranker services | 11 |
| Agent frameworks | Agent frameworks (no first-party memory layer) | 39 |
| Inference / gateway | Inference platforms & gateways | 15 |
| Evaluation / observability | Evaluation & observability platforms | 15 |
| **Total** | | **176** |

## Skipped (already in catalog)

Eleven candidates were already present in the catalog and were not
re-added. These will become re-tagging candidates if the cross-scope
re-framing makes the existing row insufficient:

- Supermemory (already in Dedicated memory layers)
- MemoryBank (already in Recent method papers)
- ChunkRAG (already in Retrieval-as-memory hybrids)
- Marqo (already in Vector-database infrastructure)
- MongoDB Atlas Vector Search (already in Vector-database infrastructure)
- Coveo (already in Enterprise-search adjacencies)
- Aider (already in File-backed / editor paradigms — re-tagged as framework)
- LangSmith (covered as part of existing Langfuse / observability landscape)
- LangFuse (already in Memory observability & monitoring)
- EM-LLM (already in Recent method papers)
- Reflexion (already in Recent method papers)

## Cross-listings created

Four major frameworks that span memory + non-memory roles are
intentionally listed in two sections. They are tracked in
`extraction/cross-listings.json` (preserved across the pipeline run):

- Mem0 — Dedicated memory layers (primary) + Memory observability
  (secondary, via AgentOps)
- Zep & Graphiti — Dedicated memory layers (primary) + Memory
  observability (secondary)
- Memobase — Dedicated memory layers (primary) + Claude Code memory
  mechanisms (secondary)
- MemoryBench — Recent method papers (primary) + Memory benchmarks
  (secondary)

Round 7's strategy: where a framework had an existing row in
Framework-embedded memory (LangChain, LangGraph, LlamaIndex, AutoGen,
CrewAI, Inngest), we added a separate new row in "Agent frameworks
(no first-party memory layer)" rather than registering it as a
cross-listing. The two rows characterise the system through different
lenses:
- The Framework-embedded-memory row covers the framework's memory
  subsystem (e.g. LangChain Memory primitives).
- The Agent-frameworks row covers the framework as an orchestration /
  agent-abstraction product (e.g. LangChain's Runnables, tool calls,
  routers).

This is a different convention from the original four cross-listings,
which point at *the same product, two framings*. Round 7's choice to
keep them as two records reflects that the new rows characterise
genuinely-separate aspects of the same framework, not the same
product from a different angle. The two rows can be merged into a
cross-listing later if the duplication becomes more confusing than
useful — recorded as `keep-separate-link-via-edge` recommendation in
ambiguous.csv for any case that surfaces.

## Categories where we hit content limits / made scope calls

- **Inference platforms.** Hit the "everything in this sphere" target
  in 15 rows. There are easily 50+ niche GPU clouds (Lambda Labs,
  Coreweave, Crusoe, Vast.ai, Massed Compute, …) and per-provider
  inference SKUs (Cloudflare Workers AI, Cerebras Inference, Groq,
  SambaNova, …). Added the dominant ones; deferred the rest.
- **Search platforms.** Vector DB landscape has 30+ entries between
  Elasticsearch derivatives, Postgres extensions, niche cloud DBs.
  Coverage included the highest-traffic OSS and managed offerings.
- **Agent frameworks.** Listed all major frameworks plus a long tail
  of niche/community ones (Eliza, Phidata/Agno, Burr, Agency Swarm).
  Many micro-frameworks have only marketing-site existence and
  weren't added.
- **Training papers.** Added foundational papers (LoRA, QLoRA, DPO,
  GRPO, LongLoRA, YaRN, PoSE) and 12 memory-shaped 2024-2026 papers.
  Did not attempt to populate the long tail of fine-tuning method
  papers — out of scope per the "in this sphere" framing.
- **Memory observability**: Cross-listed LangFuse instead of adding
  separately under the new Evaluation section.

## Surprises

- **Scale AI / Surge AI / Labelbox**: didn't realise the labelling
  industry's revenue concentration. Scale's $14B Meta investment, Surge
  AI's reportedly-$1B 2024 revenue *bootstrapped*, and Labelbox's
  $300M ARR claim all surface here.
- **Voyage AI acquisition**: Voyage was acquired by MongoDB for $220M
  in Feb 2025 — relevant because MongoDB Atlas Vector + Voyage =
  vertically-integrated memory stack story.
- **OctoAI**: NVIDIA acquired OctoML's inference offering in Oct 2024
  — quieter than the Together/Fireworks fundraises.
- **Pieces for Developers**: a 2022-founded local-LTM product for
  developers that I'd missed previously. On-device memory engine
  worth noting alongside the cloud-first dedicated memory layers.
- **AGNTCY (Internet of Agents)** & **A2A (Agent2Agent)** protocols:
  added as agent-framework entries because they're emerging
  protocols, not products. Worth tracking as substrates.
- **Mamba/Mamba-2/Jamba** and the SSM line — added as papers because
  they're directly relevant to "working memory & context management"
  even though they're often discussed under model-architecture.
- **GPT Engineer / Lovable lineage**: confirmed the same-team-as edge
  from Anton Osika's GPT Engineer (OSS) to Lovable.dev (commercial).
  Added as descent lineage candidate.

## What's locked in for Track A re-refresh

Track A's "20 sections" framing is now obsolete:
- **Section count is now 26**, not 20. Re-running section-vs-section
  stats needs to handle the new 6.
- **Mem0 inbound recount**: the new agent-framework rows (LangChain,
  LangGraph, CrewAI, LlamaIndex, AutoGen, n8n) may pick up
  built-on/integrates-with edges to Mem0 that the previous edge build
  missed when these were absent.
- **New lineages possible**:
  - "Stanford agents lineage": Generative Agents (Park et al.) →
    Voyager → Reflexion → ExpeL → Self-Refine → ChunkRAG → RAPTOR.
  - "SSM lineage": Hyena → Mamba → Mamba-2 → Jamba; potential
    pattern lineage with RWKV-7.
  - "RLHF lineage": LoRA → QLoRA → DPO → GRPO → TRL/OpenRLHF
    implementations.
  - "Embedding model lineage": Sentence Transformers → BGE → GTE → 
    Nomic Embed → Mixedbread.
  - "Agent-protocol lineage": MCP (Anthropic Nov 2024) → A2A (Google
    Apr 2025) → AGNTCY (Cisco-LangChain Mar 2025).
- **Population-median quadrant cutoffs (influence-vs-adoption matrix)**:
  the non-zero medians on each axis may move with the new 176 records,
  even though most of them sit at the origin. Re-compute.
- **Tier population recount**: now T1=213, T2=192, T3=141, T4=145,
  T5=13. The about-page coverage claim ("~88-92% for the memory core,
  lower-and-growing for the adjacent categories") needs the rate
  re-stated against the 699-record denominator.
- **Sections-page totals** and the leaderboard top-N may shift,
  especially in the Training-infrastructure and Agent-frameworks
  sections where new T1 entries (LangChain, LlamaIndex, AutoGen,
  CrewAI, TRL, vLLM, Unsloth, etc.) will dominate inbound/integration
  counts when the cell-miner re-runs.
- **Cross-references graph**: build_edges discarded ~57 cell-mining
  edges as "no-match" or "known-unresolvable". Many of these target
  the new training/agent rows — re-running build_edges after the new
  HTML is committed will pick those up.

## Pipeline state

- Extract → Reconcile → Build_edges → Validate: all pass after the
  insertion + fetch_citations --offline refresh.
- Render NOT re-run for this round. The current render.py loses
  cross-listings on round-trip (pre-existing limitation) — running
  it now would drop the 4 cross-listings. Keeping the hand-inserted
  HTML as canonical for this round.
- New IDs follow the canonical slug algorithm (host-slug for products,
  gh-owner-repo for OSS, arxiv-id for papers). No collisions surfaced
  except the 2 pre-existing duplicate-row records (MemoryBench, Zep).

## Files modified

- `landscape.html` — 176 new rows inserted; 6 new section headers;
  6 new section explainer rows.
- `web/landscape.json` — regenerated, 699 records.
- `web/landscape.edges.json` — regenerated, 278 edges.
- `extraction/cross-listings.json` — preserved, 4 entries.
- `extraction/merges.json` — preserved, 1 entry.
- `extraction/section-explainers.json` — extended with 6 new sections.
- `scripts/extract.py` — CANONICAL_SECTIONS extended with 6 new sections.
- `docs/DECISIONS.md` — new entry below.
- `extraction/round-7-ingestion.md` — this file.
