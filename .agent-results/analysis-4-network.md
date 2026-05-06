# Network Analysis — AI Memory Systems Dependency Graph

**Source:** `landscape.html` (591 catalog rows) plus pre-computed edge list in
`.agent-results/data-5-cross-references.csv` (73 explicit edges), augmented
during this pass with five additional edges harvested from a second sweep
(Marqo→LangChain, Microsoft Agent Governance Toolkit → LangChain / CrewAI /
Google ADK / Microsoft Agent Framework, Inngest AgentKit→Mem0 cookbook,
Pydantic-AI MemoryTool→Mem0/Hindsight). Final edge count: ~80.

**Method.** Edges of the form `source → target` where `source` is a catalog row
whose description / claims / pros / cons cell mentions `target` as something it
integrates with, is built on, is powered by, is backed by, wraps, forks, or whose
MCP it exposes. Trivial co-mentions (comparison anchors, "smaller community
than X", competitive benchmark references) are excluded. Self-published vendor
partnership claims (e.g. "exclusive partnership") are kept — they describe real
production wiring. Names normalised: `mem0ai/Mem0AI/Mem0 → Mem0`;
`Zep/Graphiti` collapsed (same company); `LangChain` and `LangGraph` kept
distinct where a row names only one. Edges where the target was not a catalog
row (generic terms, model providers without rows) were dropped.

---

## Headline

The graph is **strongly power-law, not mesh**. ~80 edges across ~520 catalog
rows means average degree under 0.2; the vast majority of rows have zero edges.
A small set of substrate hubs (Mem0, LangChain ecosystem, Qdrant / Pinecone /
pgvector, Neptune Analytics) absorbs almost all inbound references; the
framework / MCP / observability layer above them is where outbound edges
originate.

---

## Top Hubs by In-Degree

| Rank | Target | In-degree | Role |
|------|--------|-----------|------|
| 1 | **Mem0** | 14 | T1 memory layer; named integration target for CrewAI, AutoGen, Haystack, DSPy, Langflow, AgentOps, Ratine, Strands (AWS), FalkorDB, Mem0 MCP, OpenMemory MCP, Mem0 Security, Inngest AgentKit, Pydantic-AI |
| 2 | **LangChain** (incl. LangGraph) | 11 | Framework ecosystem hub; named by LangMem (1st-party), Flowise, Memgraph, ArangoDB, Dgraph, Marqo, AWS AgentCore, LangSmith, pgvector, Microsoft Agent Governance Toolkit |
| 3 | **LangGraph Persistence** | 5 | Stateful graph checkpointing; named by AWS AgentCore, mcp-memory-service, LangSmith, MongoDB Atlas, LangMem |
| 4 | **Qdrant** | 4 | Self-hosted vector DB; named by Agno, n8n, Mem0 Security/OpenMemory, OpenMemory MCP |
| 5 | **Pinecone** | 3 | Managed vector DB; named by Agno, n8n, OpenAI Agents SDK |
| 6 | **pgvector** | 3 | Vector-in-Postgres; named by Agno, Mem0 Security/OpenMemory, Apache AGE |
| 7 | **Zep & Graphiti** | 3 | KG memory layer; named by AutoGen, FalkorDB (MCP integration), Graphiti MCP wrapper |
| 8 | **Redis** | 3 | Production cache/store; named by LangGraph Persistence, n8n, Langflow |
| 9 | **Amazon Neptune Analytics** | 3 | AWS graph+vector; named by Strands, Mem0, Cognee |
| 10 | **CrewAI** (incl. CrewAI Memory) | 3 | Orchestration framework; named by mcp-memory-service, Microsoft Agent Governance Toolkit, ecosystem comparators |

Tier-2 hubs (in-degree 2): Official MCP Memory server, MongoDB Atlas Vector
Search, Hindsight (Vectorize), Cognee, Chroma.

Tier-3 sinks (in-degree 1): Weaviate, Supermemory, SQLite-Vec, OpenSearch,
Neo4j, Milvus, Memobase, Llama 3.3, LibSQL, LanceDB, Hunyuan, GraphRAG
(Microsoft), FAISS, DreamerV3, Cline .clinerules, AWS Bedrock AgentCore Memory,
AutoGen Memory, Google ADK, Microsoft Agent Framework.

---

## In-Degree Distribution (shape)

| In-degree | Node count | Cumulative share of edges |
|-----------|-----------|--------------------------|
| 14 (Mem0) | 1 | 17% |
| 11 (LangChain) | 1 | 31% |
| 5 (LangGraph Persistence) | 1 | 38% |
| 3–4 | 7 | 65% |
| 2 | 5 | 78% |
| 1 | 18 | 100% |

Textbook long-tail. Two nodes account for one-third of all inbound edges; the
top ten account for two-thirds. There is no second-tier thicket of
mid-degree nodes — the curve drops cleanly from ~14 to ~3. The remaining
~485 rows have **zero inbound edges** as integration targets.

---

## Sinks (high in-degree, near-zero out-degree)

Pure substrate sinks — depended on by many, depend on nothing in the catalog:

- **Pinecone** (in 3, out 0)
- **Qdrant** (in 4, out 0)
- **Redis** (in 3, out 0)
- **pgvector** (in 3, out 1 — only "used as agent memory via LangChain")
- **Neo4j**, **FAISS**, **OpenSearch**, **LibSQL**, **Milvus**, **SQLite-Vec**,
  **Chroma**, **LanceDB**, **Weaviate** — all in ≥1, out 0
- **Llama 3.3 / DreamerV3 / Hunyuan** — model substrates referenced by exactly
  one downstream system each; no outbound edges (correctly out of scope as
  fine-tuning bases, not integrations)

The substrate layer is structurally pure: vector DBs, graph DBs, foundation
models. None name another catalog row as a dependency.

## Relays (high in-degree, also non-trivial out-degree)

- **Mem0** — in 14 / out 2 (depends on Qdrant, pgvector, Neptune Analytics
  for its self-hosted Security variant)
- **LangGraph Persistence** — in 5 / out 2 (depends on Redis, MongoDB Atlas)
- **Amazon Neptune Analytics** — in 3 / out 2 (depends on Mem0, Cognee via
  reverse partnership)
- **AWS Bedrock AgentCore Memory** — in 1 / out 2 (depends on LangChain,
  LangGraph Persistence)

These are the load-bearing relays. A failure at Mem0 propagates to 14
products; a failure at the substrate beneath Mem0 propagates further.

## Pure Sources (no inbound, ≥1 outbound)

Consumers only — they integrate but are not themselves integrated into
anything else in the catalog. The list is dominated by the
"framework with delegated memory" pattern:

- Strands Agents (AWS) — out 5
- Agno (Phidata) — out 5
- n8n AI Agent Memory — out 4
- mcp-memory-service (doobidoo) — out 4
- OpenMemory MCP, Mem0 Security/OpenMemory, Langflow Memory, FalkorDB,
  AutoGen Memory, LangSmith, AWS Bedrock AgentCore Memory — out 2 each
- ~30 systems (Tencent ima.copilot, Spring AI ChatMemory, Roo Code, Ratine,
  R2I, Pydantic-AI + Hindsight, OWASP Agent Memory Guard, OpenAI Agents SDK,
  NVIDIA ReMEmbR, MemPalace, Memobase MCP, Memgraph, Mem0 MCP,
  mcp-knowledge-graph, Mastra Memory, LazyGraphRAG, LangMem, Hindsight MCP,
  Haystack, Graphiti MCP, Flowise, DSPy History, Diffbot, Dgraph, CrewAI
  Memory, Continue.dev Memory MCP, Cognee MCP, claude-supermemory, ArangoDB,
  Apache AGE, AgentOps, Microsoft Agent Governance Toolkit, Marqo, Inngest
  AgentKit, Pydantic-AI MemoryTool) — out 1 each

---

## Integration Chains (length ≥3)

Chains spanning three or more layers — visible "stack shapes":

1. **Strands Agents → Mem0 → Neptune Analytics** (AWS-published architecture).
2. **Strands Agents → Mem0 → Qdrant** (alternate path via Mem0 Security /
   OpenMemory variant).
3. **CrewAI Memory → Mem0 → Qdrant / pgvector / Neptune Analytics**
   (canonical framework → memory layer → DB pattern).
4. **mcp-memory-service → CrewAI / LangGraph / AutoGen → Mem0 / Zep**
   (MCP wrapper above framework above memory layer — four layers if you count
   the Mem0 substrate beneath).
5. **Continue.dev Memory MCP → Official MCP Memory server → knowledge-graph
   backend** (MCP wrapper of reference impl; stable fork
   `mcp-knowledge-graph` joins at layer 2).
6. **OpenMemory MCP → Mem0 → Qdrant / pgvector** (MCP wrapper re-exposing
   Mem0's local variant).
7. **AWS AgentCore Memory → LangGraph Persistence → Redis / Mongo Atlas**
   (managed memory delegates to checkpointer delegates to backing store).
8. **FalkorDB → (Mem0 as graph backend) → Mem0 consumers** (FalkorDB
   advertises itself as "graph-memory backend for Mem0" — inverts the usual
   direction; sells to anyone using Mem0).
9. **DSPy History → Mem0 → substrate** (tutorial-driven integration in
   DSPy's docs).
10. **Spring AI ChatMemory → Neo4j** (and JDBC / Cassandra / in-memory as
    alternate pluggable backends).

Notably, **no chain extends across four distinct logical layers without going
through Mem0 or the LangChain ecosystem** — those two clusters are the
structural waypoints.

## Fork / Variant Edges

Three short fork chains, all single-generation:

- **mcp-knowledge-graph** ← fork of ← **Official MCP Memory server**
- **LazyGraphRAG** ← variant of ← **GraphRAG (Microsoft)**
- **Roo Code .roorules** ← fork of ← **Cline .clinerules**

No multi-generational fork trees observed.

---

## Isolated Nodes

Of 591 rows scanned, ~485 have no inbound *and* no outbound integration
edges. Structurally expected sub-populations:

- Section explainers / header rows (~20)
- Research papers and benchmarks (LoCoMo, LongMemEval, NIAH, RULER, MAE,
  Implicit-Memory bench, etc.) — referenced *as* benchmarks but not as
  integrations
- Foundation-model first-party memory features (ChatGPT Memory, Claude Memory,
  Gemini Memory, Microsoft Recall, Notion AI) — closed, vendor-internal; no
  integration surface
- Vertical / consumer products (Harvey Memory, Thomson Reuters, Duolingo
  Roleplay, Tencent ima.copilot) — terminal consumers
- Architecture / theory entries (ACT-R-on-vector-store, ReAct, Karpathy memory
  tweet) — citations, not edges
- Wave-4 newer entries with no public integration story documented

The "real" isolated nodes — products that *should* have integrations but don't
surface them in their description — are roughly two dozen out of ~150 dedicated
memory layers and frameworks. This is the population most likely to be either
too new to have wiring documented or too closed to disclose it.

---

## Structural Takeaway

The graph confirms a **two-cluster gravity model**, not a mesh:

- **Cluster A (memory-layer gravity):** Mem0 at the centre, with Zep / Graphiti,
  Cognee, Hindsight, Memobase, Supermemory, Letta as satellites. Substrate
  beneath: Qdrant, pgvector, Neptune Analytics, Chroma. Fourteen products
  explicitly route memory through Mem0; no other memory layer is named more
  than three times.

- **Cluster B (framework-ecosystem gravity):** LangChain + LangGraph + LangSmith
  + LangMem + LangGraph Persistence form a tight internally-coupled cluster.
  Eleven outside rows name LangChain or LangGraph as an integration target. No
  competing framework cluster achieves comparable in-degree (CrewAI, AutoGen,
  Mastra, Pydantic-AI, Strands all sit on the consumer side).

The MCP layer is **cross-cutting transport, not a hub** — it adds wrappers
around existing memory layers without forming its own gravity centre.

The "what's actually getting used" signal points cleanly: if you ship a memory
product or framework today and want to be in someone else's stack, you either
(a) become a Mem0 plug-in, (b) become a LangChain-native node, or (c) become a
vector-DB substrate. The catalog has no fourth shape with comparable in-degree.
