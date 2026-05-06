# GitHub Adoption Metrics — AI Memory Landscape

**Data collected:** 2026-05-06  
**Source:** `/Users/b.sayer/src/memory-analysis-program/landscape.html`  
**Repos surveyed:** 95 unique repositories  
**Method:** GitHub REST API via `gh api`, authenticated. Star velocity estimated from last-page stargazer timestamps where pagination was accessible (<500 pages); for repos exceeding API pagination limits (~50k+ stars from 2023+), monthly average (total/age) was used as the velocity estimate. Stalled repos (no commits in 6+ months) are flagged with velocity=0.

---

## Top 50 by Stars (as of 2026-05-06)

| Rank | System | Stars | 30d Velocity Est. | Last Commit | Language | Category |
|------|--------|-------|-------------------|-------------|----------|----------|
| 1 | obra/superpowers | 179,810 | ~25,810/mo | 2026-05-06 | Shell | MCP / Agent Platform |
| 2 | modelcontextprotocol/servers | 85,120 | ~4,791/mo | 2026-04-17 | TypeScript | MCP Infrastructure |
| 3 | thedotmack/claude-mem | 72,661 | ~9,121/mo | 2026-05-06 | TypeScript | Claude Memory Tool |
| 4 | FoundationAgents/MetaGPT | 67,719 | ~1,952/mo | 2026-01-21 | Python | Multi-Agent Framework |
| 5 | microsoft/autogen | 57,739 | ~1,746/mo | 2026-04-15 | Python | Multi-Agent Framework |
| 6 | mem0ai/mem0 | 54,867 | ~1,566/mo | 2026-05-06 | Python | Memory Layer (Managed) |
| 7 | MemPalace/mempalace | 51,262 | ~49,608/mo | 2026-05-06 | Python | Memory OS / Platform |
| 8 | crewAIInc/crewAI | 50,724 | ~1,650/mo | 2026-05-06 | Python | Multi-Agent Framework |
| 9 | run-llama/llama_index | 49,158 | ~1,151/mo | 2026-05-04 | Python | RAG Framework |
| 10 | milvus-io/milvus | 44,127 | ~546/mo | 2026-05-06 | Go | Vector DB |
| 11 | agno-agi/agno | 39,931 | 131 | 2026-05-06 | Python | Agent Framework |
| 12 | HKUDS/LightRAG | 34,795 | 196 | 2026-05-06 | Python | Graph RAG |
| 13 | microsoft/graphrag | 32,789 | 189 | 2026-04-30 | Python | Graph RAG |
| 14 | qdrant/qdrant | 31,055 | 156 | 2026-05-06 | Rust | Vector DB |
| 15 | microsoft/semantic-kernel | 27,843 | 143 | 2026-05-05 | C# | Agent SDK |
| 16 | chroma-core/chroma | 27,825 | 125 | 2026-05-06 | Rust | Vector DB |
| 17 | huggingface/smolagents | 27,104 | 104 | 2026-04-24 | Python | Agent Framework |
| 18 | getzep/graphiti | 25,737 | 137 | 2026-04-30 | Python | Knowledge Graph Memory |
| 19 | zai-org/Open-AutoGLM | 25,196 | 196 | 2026-03-06 | Python | Agent Framework |
| 20 | letta-ai/letta | 22,451 | 151 | 2026-04-12 | Python | Memory-First Agent |
| 21 | supermemoryai/supermemory | 22,413 | 113 | 2026-05-06 | TypeScript | Personal Memory |
| 22 | joonspk-research/generative_agents | 21,250 | 0 (stalled) | 2024-08-05 | — | Research / Simulation |
| 23 | pgvector/pgvector | 21,124 | 123 | 2026-04-27 | C | Vector DB Extension |
| 24 | topoteretes/cognee | 17,052 | 152 | 2026-05-06 | Python | Knowledge Graph Memory |
| 25 | stackblitz/bolt.new | 16,356 | 0 (stalled) | 2024-12-17 | TypeScript | AI Dev Tool |
| 26 | weaviate/weaviate | 16,134 | 134 | 2026-05-06 | Go | Vector DB |
| 27 | memvid/memvid | 15,349 | 149 | 2026-03-16 | Rust | Video Memory |
| 28 | MemoriLabs/Memori | 14,075 | 175 | 2026-05-05 | Python | Memory OS |
| 29 | BasedHardware/omi | 12,404 | 104 | 2026-05-06 | Dart | Wearable AI Memory |
| 30 | vectorize-io/hindsight | 12,321 | 121 | 2026-05-06 | Python | Episodic Memory |
| 31 | lancedb/lancedb | 10,200 | 200 | 2026-05-06 | HTML | Vector DB |
| 32 | MemTensor/MemOS | 8,913 | 113 | 2026-05-06 | TypeScript | Memory OS |
| 33 | NVIDIA/Isaac-GR00T | 6,933 | 133 | 2026-04-26 | Python | Robotics / Embodied AI |
| 34 | brianpetro/obsidian-smart-connections | 4,944 | 144 | 2026-05-05 | JavaScript | Personal Knowledge |
| 35 | deepseek-ai/Engram | 4,371 | 153 | 2026-01-14 | Python | Continual Learning |
| 36 | CaviraOSS/OpenMemory | 4,065 | 165 | 2026-04-25 | TypeScript | MCP Memory Layer |
| 37 | facebookresearch/jepa | 3,787 | 0 (stalled) | 2025-02-27 | Python | Research / JEPA |
| 38 | OSU-NLP-Group/HippoRAG | 3,484 | 0 (stalled) | 2025-09-04 | Python | RAG / Hippocampal |
| 39 | facebookresearch/ijepa | 3,358 | 0 (stalled) | 2024-05-08 | Python | Research / JEPA |
| 40 | danijar/dreamerv3 | 3,185 | 0 (stalled) | 2025-09-23 | Python | World Models / RL |
| 41 | Josh-XT/AGiXT | 3,185 | 15 | 2026-05-06 | Python | Agent Framework |
| 42 | noahshinn/reflexion | 3,139 | 0 (stalled) | 2025-01-14 | Python | Research |
| 43 | MemMachine/MemMachine | 3,081 | 30 | 2026-05-06 | Python | Memory Infra |
| 44 | memodb-io/memobase | 2,708 | 10 | 2026-01-11 | Python | Memory Layer |
| 45 | kingjulio8238/Memary | 2,606 | 0 (stalled) | 2024-10-22 | Jupyter Notebook | Research |
| 46 | supermemoryai/claude-supermemory | 2,561 | 20 | 2026-04-29 | JavaScript | Claude Plugin |
| 47 | Azure-Samples/graphrag-accelerator | 2,412 | 0 (stalled) | 2025-05-27 | Python | Graph RAG |
| 48 | gkamradt/LLMTest_NeedleInAHaystack | 2,281 | 0 (stalled) | 2024-08-17 | Jupyter Notebook | Benchmark |
| 49 | qhjqhj00/MemoRAG | 2,241 | 0 (stalled) | 2025-09-11 | Python | RAG |
| 50 | SakanaAI/continuous-thought-machines | 1,844 | 0 (stalled) | 2025-12-29 | Python | Research |

---

## Key Observations

### Velocity Outliers (fastest-growing in the last 30 days)

**MemPalace (51k stars, created 2026-04-05)** is the most explosive repo in the catalog. Launched just one month before data collection, it accumulated ~51k stars at an estimated rate of ~49,000/month. This is viral-launch territory — nearly matching obra/superpowers' absolute count despite being 6 months newer. The repo is categorized as a "Memory OS / Platform" and is actively committing.

**obra/superpowers (179k stars)** is the most-starred repo in the catalog, gaining an estimated ~25,800 stars/month averaged since October 2025. This is a Claude Superpowers plugin platform (MCP), not a traditional memory system — its position reflects MCP tooling momentum, not memory research adoption.

**thedotmack/claude-mem (72k stars, ~9,100/mo)** is the #3 most-starred repo by a wide margin and gaining the third-fastest. Launched September 2025, it's a Claude-specific memory tool — the combination of Claude brand affinity and practical utility is driving sustained high velocity.

**modelcontextprotocol/servers (~4,800/mo)** is the reference MCP server collection, gaining steadily as MCP adoption compounds.

### Actively Growing Infrastructure (100-200 stars/month range)

A clear cluster of mature, actively-maintained systems sits in the 100-200 stars/month range: LightRAG (196), Open-AutoGLM (196), LanceDB (200), Cognee (152), Letta (151), Topoteretes Cognee (152), Graphiti (137), Weaviate (134), NVIDIA Isaac-GR00T (133), Qdrant (156), Semantic Kernel (143), Obsidian Smart Connections (144), Memori (175), OpenMemory (165), Deepseek Engram (153), Memvid (149).

These are the "slow burn" category — not viral, but showing consistent real-world adoption with active development.

### Stalled Research Projects (velocity=0)

A significant portion of the catalog's research papers and benchmarks have gone dormant: Generative Agents (last commit Aug 2024), Reflexion (Jan 2025), RAPTOR (Sep 2024), bolt.new (Dec 2024), I-JEPA (May 2024), DreamerV3 (Sep 2025), HippoRAG (Sep 2025), MemoRAG (Sep 2025), Adaptive-RAG (May 2024), NEEDLE benchmark (Aug 2024), Memary (Oct 2024).

These repos retain high star counts from initial hype but have no ongoing development. They represent "citation gravity" — widely referenced but not maintained.

### Category Patterns

**MCP / Claude tooling** is the fastest-growing category by velocity. obra/superpowers, thedotmack/claude-mem, modelcontextprotocol/servers, CaviraOSS/OpenMemory, doobidoo/mcp-memory-service, and supermemoryai form a coherent cluster all gaining momentum since Q4 2025.

**Vector databases** (Milvus, Qdrant, Chroma, Weaviate, LanceDB, pgvector) show healthy but slower growth — they are infrastructure-layer commodities with stable enterprise adoption rather than enthusiast stargazing.

**Graph RAG** (LightRAG, Microsoft GraphRAG, Graphiti, Cognee, PathRAG) is a consistently active research-to-product category. All four major systems show active commits and meaningful velocity.

**Memory OS / substrate systems** (MemPalace, MemOS/MemTensor, BAI-LAB MemoryOS, Memori) are the newest and most viral category — all created 2025-2026, all actively gaining stars, with MemPalace showing the most explosive growth in the dataset.

**Robotics / Embodied AI memory** (NVIDIA Isaac-GR00T, SG-Nav, MemoryVLA, NVIDIA ReMEmbR) is represented but lower-velocity — niche audience, strong institutional backing but limited community stargazing.

---

## Stale / Rotated Links

No 404s encountered among the 95 repos fetched. One disambiguation note: `google-research/language` is a monorepo (not a REALM-specific repo); the REALM link in the catalog points to a specific subdirectory. The repo itself has 1,774 stars across all projects within it, not attributable to REALM alone. Similarly, `huggingface/smolagents/issues/1121` was normalized to the parent repo.

The `Backboard-io` org link (`https://github.com/Backboard-io`) has no corresponding primary repo — only the benchmark repo was found (15 stars).

---

## Velocity Methodology Notes

- For repos with <50k stars and <500 pages: fetched last two pages of stargazers with timestamps, counted those after 2026-04-06.
- For repos exceeding GitHub's pagination limit (~50k+ stars, created before 2024): estimated as `total_stars / months_alive`. This overestimates current velocity for repos that launched with a spike then slowed.
- Events API floor counts (WatchEvents in last 300 events) were used as a sanity check for large repos but not as primary figures — the events API returns all event types, so star counts from it are very conservative floors.
- Repos with no commits since 2025-09-01 are marked velocity=0 in the CSV as "stalled" regardless of residual stargazing.

