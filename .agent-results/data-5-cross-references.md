# Dependency Graph: AI Memory Systems Cross-References

Source: `/Users/b.sayer/src/memory-analysis-program/landscape.html`
Method: Grep-driven extraction of connector phrases and system-name cross-mentions in `<td class="desc">` and `<td class="claims">` cells.

---

## The Network in Brief

The catalog contains roughly 500+ named systems. Cross-reference extraction found 65+ explicit dependency edges. The graph is highly asymmetric: a small cluster of substrate systems (Mem0, Pinecone, Neo4j, pgvector, Qdrant, LangChain/LangGraph) appear as targets in the descriptions of many others, while most systems have zero outbound edges — they are leaves that depend on these hubs.

---

## Top-20 Hubs (by inbound reference count)

| Rank | System | Inbound references | Role |
|------|--------|--------------------|------|
| 1 | **Mem0** | 14 | Memory layer substrate; integrated into CrewAI, Haystack, AutoGen, AgentOps, Ratine, Langflow, Strands (AWS), FalkorDB, AgentOps, DSPy, OpenMemory MCP, Mem0 MCP, Mem0 Security, Haystack |
| 2 | **LangChain / LangGraph** | 10 | Framework ecosystem hub; named by Memgraph, ArangoDB, Dgraph, Flowise, LangMem, LangSmith, LangGraph Persistence, Flowise, AWS AgentCore, pgvector |
| 3 | **Pinecone** | 6 | Vector DB substrate; named by Agno, n8n, OpenAI Agents SDK, Flowise/n8n vector nodes, Databricks (comparison) |
| 4 | **Qdrant** | 6 | Vector DB substrate; named by Agno, n8n, OpenMemory MCP, Mem0 Security/OpenMemory, Spring AI (indirectly) |
| 5 | **pgvector** | 5 | Vector-in-Postgres substrate; named by Agno, Apache AGE, Mem0 Security/OpenMemory, Claude-CursorMemoryMCP, Spring AI |
| 6 | **Zep & Graphiti** | 5 | KG memory layer; named by AutoGen, FalkorDB (MCP integration), observability section, governance section, and comparison anchors |
| 7 | **Neo4j** | 4 | Graph DB substrate; named by Spring AI ChatMemory (pluggable backend), Official MCP Memory server description, FalkorDB comparisons, section explainer |
| 8 | **Redis** | 4 | Production cache/store; named by LangGraph Persistence, n8n, Langflow, Memobase MCP |
| 9 | **Chroma** | 3 | Local vector store; named by MemPalace (substrate for its benchmark score), Superpowers plugin (optional backend), and tutorial comparisons |
| 10 | **Milvus** | 2 | Large-scale vector DB; named by NVIDIA ReMEmbR (substrate), size-comparison anchor for others |
| 11 | **Amazon Neptune Analytics** | 3 | Graph+vector AWS service; named by Strands Agents, Mem0 architecture, Cognee integration |
| 12 | **LangGraph Persistence** | 4 | Stateful graph checkpointing; named by AWS AgentCore, mcp-memory-service, LangSmith, MongoDB Atlas |
| 13 | **Hindsight (Vectorize)** | 3 | Memory layer; named by Pydantic-AI integration entry, Hindsight MCP, comparisons |
| 14 | **Cognee** | 2 | ECL memory layer; named by Amazon Neptune Analytics integration, Cognee MCP |
| 15 | **Official MCP Memory server** | 2 | Reference KG MCP impl; named by mcp-knowledge-graph fork, Continue.dev Memory MCP |
| 16 | **LanceDB** | 2 | Columnar vector DB; named by Agno integrations list, LanceDB entry comparisons |
| 17 | **Weaviate** | 2 | Vector DB; named by Agno integrations list, comparison anchors |
| 18 | **FAISS** | 1 | Local vector index; named by Strands Agents (local default) |
| 19 | **OpenSearch** | 1 | Enterprise search/vector; named by Strands Agents (production default) |
| 20 | **LibSQL** | 1 | Embedded relational DB; named by Mastra Memory (default substrate) |

---

## Structural Patterns

### Pattern 1 — The Mem0 Gravitational Field

Mem0 is the single most-referenced memory layer in the catalog. It appears as a named integration target in: CrewAI, AutoGen, Haystack, DSPy, Langflow, AgentOps, Ratine, and the dedicated Mem0 MCP and OpenMemory MCP entries. AWS selected it as the exclusive long-term memory partner for Strands Agents with a named partnership announcement. FalkorDB advertises itself as "graph-memory backend for Mem0." The Mem0 Security / OpenMemory entry describes its own self-hosted variant using Postgres + Qdrant as underlying substrate — meaning Mem0 is both a hub that others depend on, and itself depends on Qdrant and pgvector downstream.

### Pattern 2 — The LangChain/LangGraph Ecosystem Cluster

LangChain and its graph-execution sibling LangGraph form a tightly coupled cluster. LangMem is explicitly "first-party LangChain integration." LangGraph Persistence is described as distinct from LangMem but most idiomatic when paired with LangChain. LangSmith is the de-facto trace tool for "that ecosystem." Flowise is "LangChain-native." AWS AgentCore lists LangChain/LangGraph as native integrations. Memgraph, ArangoDB, and Dgraph each list LangChain as an integration in their descriptions. This is a second gravitational center, operating at the framework layer rather than the memory-layer substrate.

### Pattern 3 — MCP as a Cross-Cutting Transport

Seven entries in the catalog are explicitly MCP server wrappers for other systems: Mem0 MCP, Graphiti MCP (Zep), Cognee MCP, Hindsight MCP, Memobase MCP, OpenMemory MCP, and the Official MCP Memory server. Each has exactly one outbound edge (to its parent memory system). Two additional entries — mcp-knowledge-graph (a community fork of the Official MCP Memory server) and Continue.dev Memory MCP (which uses the Official MCP server as its backend) — extend the pattern. The OWASP Agent Memory Guard entry calls out "visibility/control over MCP servers" as the primary attack surface for memory. MCP functions as a transport layer that any T1 memory product can plug into without coupling.

### Pattern 4 — Vector DB as Commodity Substrate

The section explainer for vector databases states the pattern explicitly: "Most dedicated memory layers are built on one or more of these." This is confirmed by the edges: Mem0's self-hosted variant uses Qdrant, Agno supports Pinecone/Weaviate/Qdrant/LanceDB interchangeably, n8n offers Qdrant/Pinecone/MongoDB as swappable nodes, and OpenAI Agents SDK names Pinecone as the implied long-term backend. Pinecone occupies the premium/managed end; Qdrant and pgvector split the self-hosted segment. Chroma is the dominant prototyping-only choice (MemPalace's benchmark score is attributed to Chroma defaults, not to the palace algorithm itself — a notable finding about how substrate choice inflates leaderboard numbers).

### Pattern 5 — Graph DB as Specialized Substrate

Separate from vector DBs, graph databases appear as the substrate for knowledge-graph memory products. The section explainer names "Zep/Graphiti, Cognee, and Neo4j-backed agents" as the canonical consumers. FalkorDB names itself as graph backend for Mem0 and integrates with Graphiti for its MCP server. Amazon Neptune Analytics lists both Mem0 (GA integration) and Cognee (agentic RAG integration). Apache AGE pairs with pgvector for hybrid graph+vector in Postgres. Neo4j is the comparison anchor for every other graph DB in the catalog.

### Pattern 6 — Fork and Variant Chains

Three fork chains appear. (1) LazyGraphRAG is an explicit variant of GraphRAG (Microsoft), described as being integrated back into the parent repo. (2) mcp-knowledge-graph (shaneholloman) is a stable local fork of `@modelcontextprotocol/server-memory`, the Official MCP Memory server. (3) Roo Code .roorules is described as "VS Code extension (fork of Cline)." These are shallow chains — one level deep — not multi-generational trees.

### Pattern 7 — Framework-Embedded Memory Delegating Down

Several framework-embedded memory systems have no native persistent storage and explicitly delegate to a named external layer. Pydantic-AI ships no persistent memory and names Hindsight as the canonical integration. OpenAI Agents SDK names external vector DBs (Pinecone) as the long-term tier. AutoGen integrates Mem0 or Zep rather than building natively. This delegation pattern means the framework entries are pass-through nodes: they inherit all the characteristics (and risks) of whatever substrate sits beneath them.

---

## Notable Findings

- **Chroma substrate effect on benchmarks.** MemPalace's high LoCoMo/LongMemEval score is attributed by an independent analysis to "verbatim storage + ChromaDB defaults rather than the palace structure." This is the only case in the catalog where a substrate choice is explicitly identified as distorting a benchmark result.

- **Strands/AWS as exclusive integration.** Mem0's integration with Strands Agents is labeled "exclusive provider" in the catalog's type cell, the only instance of that phrase in the file. Every other framework offers pluggable backends.

- **Mem0's dual role.** Mem0 appears both as an inbound hub (others depend on it) and as an outbound node: it depends on Qdrant, pgvector, and Amazon Neptune Analytics for its own storage. This makes it a relay node, not a pure substrate — a distinction relevant when assessing single-point-of-failure risk.

- **LangSmith as observability lock-in.** LangSmith is described as the "de-facto trace tool" for the LangChain/LangGraph ecosystem, with the explicit caveat that it works less well outside that ecosystem. It is the only observability tool in the catalog that is structurally tethered to a specific framework.
