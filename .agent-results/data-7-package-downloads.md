# Package Manager Download Counts — AI Memory Landscape

**Data collected:** 2026-05-06  
**Source APIs:** pypistats.org/api, api.npmjs.org, crates.io/api/v1, pypi.org/pypi (version data)  
**Coverage:** 96 GitHub rows checked; 43 package records collected across 33 distinct systems.  
All download figures are for the 30-day period ending ~2026-05-05 unless noted.

---

## Top 20 by Downloads Last Month

Ranked by `downloads_last_month` across all package managers. Where a project ships multiple packages (e.g. both Python and npm), the largest figure is used for ranking; all packages are listed.

| Rank | System | Package Manager | Package Name | Downloads / Month | Downloads / Week |
|------|--------|----------------|--------------|-------------------|-----------------|
| 1 | weaviate/weaviate | PyPI | weaviate-client | 109,040,750 | 26,349,639 |
| 2 | modelcontextprotocol/servers | npm | @modelcontextprotocol/sdk | 138,884,739 | 33,359,614 |
| 3 | qdrant/qdrant | PyPI | qdrant-client | 22,986,680 | 6,406,861 |
| 4 | pgvector/pgvector | PyPI | pgvector | 20,667,000 | 4,965,498 |
| 5 | chroma-core/chroma | PyPI | chromadb | 13,650,783 | 2,989,183 |
| 6 | run-llama/llama_index | PyPI | llama-index | 10,371,161 | 2,430,517 |
| 7 | crewAIInc/crewAI | PyPI | crewai | 7,305,228 | 1,850,454 |
| 8 | milvus-io/milvus | PyPI | pymilvus | 6,593,585 | 1,313,404 |
| 9 | lancedb/lancedb | PyPI | lancedb | 6,970,138 | 1,628,202 |
| 10 | microsoft/semantic-kernel | PyPI | semantic-kernel | 2,701,100 | 620,664 |
| 11 | mem0ai/mem0 | PyPI | mem0ai | 2,813,995 | 675,372 |
| 12 | microsoft/autogen | PyPI | autogen-agentchat | 1,405,278 | 325,519 |
| 13 | agno-agi/agno | PyPI | agno | 1,790,748 | 424,542 |
| 14 | milvus-io/milvus | PyPI | milvus-lite | 1,793,421 | 384,648 |
| 15 | qdrant/qdrant | npm | @qdrant/js-client-rest | 1,912,822 | 447,960 |
| 16 | weaviate/weaviate | npm | weaviate-client | 1,705,121 | 324,180 |
| 17 | lancedb/lancedb | npm | @lancedb/lancedb | 4,009,113 | 591,562 |
| 18 | chroma-core/chroma | npm | chromadb | 782,275 | 170,867 |
| 19 | huggingface/smolagents | PyPI | smolagents | 582,984 | 119,965 |
| 20 | langchain-ai/langmem | PyPI | langmem | 647,917 | 141,301 |

**Note on weaviate-client:** The 109M/month figure is abnormally high for a vector database client and warrants verification — it may include CI/CD pipeline pulls, mirror resync, or automated test infrastructure. The npm client (1.7M/month) is in a more expected range for actual developer usage.

**Note on @modelcontextprotocol/sdk:** The MCP SDK (138M/month) is infrastructure — it underpins every MCP server and client. This is not the servers repo itself but the transport/protocol SDK. Placed in row 2 because it is the load-bearing package for the `modelcontextprotocol/servers` repo entry.

---

## Fastest-Growing: Last-Week vs Last-Month Velocity Ratio

A high week/month ratio (above ~0.27, which is the flat-traffic baseline) suggests accelerating downloads. Ratio = `(last_week * 4.3) / last_month` — values >1.0 indicate the last week was above monthly average pace.

| System | Package | Week | Month | Week×4.3/Month | Signal |
|--------|---------|------|-------|----------------|--------|
| qdrant/qdrant | qdrant-client (PyPI) | 6,406,861 | 22,986,680 | 1.20 | Accelerating |
| weaviate/weaviate | weaviate-client (PyPI) | 26,349,639 | 109,040,750 | 1.04 | Flat/slightly up |
| letta-ai/letta | letta | 52,951 | 138,101 | 1.65 | Strongly accelerating |
| topoteretes/cognee | cognee | 30,307 | 109,500 | 1.19 | Accelerating |
| doobidoo/mcp-memory-service | mcp-memory-service | 8,730 | 28,183 | 1.33 | Accelerating |
| getzep/graphiti | graphiti-core | 109,614 | 488,265 | 0.97 | Flat |
| crewAIInc/crewAI | crewai | 1,850,454 | 7,305,228 | 1.09 | Slightly accelerating |
| pgvector/pgvector | pgvector | 4,965,498 | 20,667,000 | 1.03 | Flat |
| mem0ai/mem0 | mem0ai | 675,372 | 2,813,995 | 1.03 | Flat |

Top accelerators by this measure: **letta** (1.65x), **mcp-memory-service** (1.33x), **qdrant-client** (1.20x), **cognee** (1.19x). Letta's spike is notable given the repo has only ~22K stars — strong developer adoption relative to GitHub visibility.

---

## Package Velocity vs GitHub Stars — Mismatch Cases

These cases are notable because download volumes don't match star counts in the expected direction:

**Overperforming (high downloads, relatively fewer stars):**
- `weaviate-client` / `qdrant-client` / `pgvector` — infrastructure libraries used as dependencies; downloads far exceed what star counts predict because they are pulled transitively by higher-level frameworks.
- `semantic-kernel` (2.7M/mo) with only ~28K stars — indicates enterprise/Microsoft internal adoption.
- `letta` (138K/mo, 52K+/week velocity) with only ~22K stars — strong adoption momentum.

**Underperforming (many stars, low or no package):**
- `MemPalace/mempalace` (51K stars) — **no public package found** on PyPI or npm.
- `joonspk-research/generative_agents` (21K stars) — no package; research-only codebase.
- `gkamradt/LLMTest_NeedleInAHaystack` (2.3K stars) — no package.
- `SakanaAI/continuous-thought-machines` — no package.
- `zai-org/Open-AutoGLM` (25K stars) — no package found on PyPI or npm.
- `obra/superpowers` (179K stars) — no package found; appears to be a Shell-based tool.
- `thedotmack/claude-mem` (72K stars) — no package found on npm.
- `BasedHardware/omi` (12K stars, Dart) — no pub.dev check performed (outside npm/PyPI/crates scope).

---

## OSS Libraries with No Public Package

These systems were checked and no matching package was found on PyPI, npm, or crates.io:

| System | Stars | Primary Language | Reason / Notes |
|--------|-------|----------------|----------------|
| obra/superpowers | 179,810 | Shell | Shell-based; no package ecosystem |
| thedotmack/claude-mem | 72,661 | TypeScript | No npm package found |
| MemPalace/mempalace | 51,262 | Python | No PyPI package found — research/private? |
| zai-org/Open-AutoGLM | 25,196 | Python | No PyPI package found |
| joonspk-research/generative_agents | 21,250 | (none) | Research codebase; no package |
| stackblitz/bolt.new | 16,356 | TypeScript | Web app; no npm package |
| memvid/memvid | 15,349 | Rust | No crates.io crate found under memvid |
| MemoriLabs/Memori | 14,075 | Python | No PyPI package found |
| BasedHardware/omi | 12,404 | Dart | pub.dev not checked |
| vectorize-io/hindsight | 12,321 | Python | No PyPI package found |
| MemTensor/MemOS | 8,913 | TypeScript | No npm package found |
| NVIDIA/Isaac-GR00T | 6,933 | Python | No PyPI package found |
| brianpetro/obsidian-smart-connections | 4,944 | JavaScript | Obsidian plugin; no npm package |
| deepseek-ai/Engram | 4,371 | Python | No PyPI package found |
| CaviraOSS/OpenMemory | 4,065 | TypeScript | No npm package found |
| facebookresearch/jepa | 3,787 | Python | Research-only |
| OSU-NLP-Group/HippoRAG | 3,484 | Python | hipporag exists but very low traffic (4,734/mo) |
| facebookresearch/ijepa | 3,358 | Python | Research-only |
| noahshinn/reflexion | 3,139 | Python | Research-only |
| MemMachine/MemMachine | 3,081 | Python | No PyPI package found |
| qhjqhj00/MemoRAG | 2,241 | Python | No PyPI package found |
| SakanaAI/continuous-thought-machines | 1,844 | Python | Research-only |
| BAI-LAB/MemoryOS | 1,362 | Python | memoryos exists but very low (2,460/mo) |
| ByteDance-Seed/m3-agent | 1,330 | Python | No PyPI package found |
| THUDM/LongBench | 1,165 | Python | Benchmark; no package |
| neo4j-contrib/mcp-neo4j | 944 | Python | No PyPI package found |
| lucidrains/RETRO-pytorch | 880 | Python | retro-pytorch exists; 831/mo (research/archived) |
| WujiangXu/A-mem | 871 | Python | No PyPI package found |
| shaneholloman/mcp-knowledge-graph | 849 | JavaScript | No npm package found |
| zjunlp/LightMem | 820 | Python | No PyPI package found |
| booydar/recurrent-memory-transformer | 779 | Jupyter Notebook | Research-only |
| Various benchmarks/evals | varies | various | Benchmark repos (RULER, LongMemEval, etc.) — research code, not packages |

---

## Raw Data Notes

- **graphiti vs graphiti-core:** The PyPI package `graphiti` (14 versions, last published 2018) is an unrelated older project. The correct package for `getzep/graphiti` is `graphiti-core` (189 versions, 488K/mo downloads).
- **autogen dual packages:** Microsoft AutoGen ships both `autogen-agentchat` (1.4M/mo, v0.7) and the legacy `pyautogen` (1.2M/mo, v0.10). Combined ~2.65M/mo.
- **milvus dual packages:** `pymilvus` (6.6M/mo) is the standard client; `milvus-lite` (1.8M/mo) is the embedded variant. Combined ~8.4M/mo.
- **weaviate dual npm:** `weaviate-client` (v3 TS client, 1.7M/mo) has superseded `weaviate-ts-client` (v2 legacy, 134K/mo).
- **lancedb cross-language:** Ships Python (6.97M/mo), npm (4M/mo), and Rust crates (339K total downloads, recent_downloads=168K). Genuinely polyglot distribution.
- **shadowkv (bytedance/ShadowKV):** A `shadowkv` package exists on PyPI with only 8 downloads/month — almost certainly the research authors' personal upload with no real adoption.
- **mcp-memory-service:** 255 versions published at 10.49.4 is suspicious — this appears to be a package that auto-publishes versions. High version count is not a meaningful signal here.
- **PyPI rate limiting:** pypistats.org enforces rate limits (~1 req/sec). Several packages required retry with backoff. All high-priority packages were successfully fetched.
- **crates.io:** Only `qdrant-client` (Rust, 2.33M total / 713K recent) and `lancedb` (Rust, 339K total / 168K recent) were found as significant Rust crates from this dataset. Chroma's backend is Rust but it ships Python/npm clients only; no public chroma crate was found.

