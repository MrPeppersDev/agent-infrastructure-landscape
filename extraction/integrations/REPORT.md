# Integration edges from official integration pages — 2026-10-29

`scripts/build_edges.py` reads every `*.json` file in this folder: lists of `{source, target, type, evidence, citation}`. Ids removed by a merge follow `taxonomy/system-aliases.json` → `redirects`; any other unknown id fails the build. This pass adds **1,396 `integrates-with` edges**, taking the total from 41 to 1,432. They come from 53 hub systems and reach 250+ distinct targets.

**Method.** For each hub, two research agents opened the official integrations, providers or connectors pages: the docs site, its `llms.txt` and sitemap, or the integration folders of the official repo. They kept every listed integration whose counterpart is in the catalog, matched on name *and* domain. The edge's source is the system whose page documents the integration. The citation is the per-integration page where one exists, otherwise the index page. Only connectors, providers, adapters, plugins, SDK callbacks and documented first-class support count; customer logos and comparisons don't.

**Checks.**
- Every id resolves.
- There are no duplicate pairs or self-edges, and the two files share no pair.
- All citations are HTTPS.
- Non-GitHub citations returned HTTP 200 when checked. GitHub pages return 403 to the session proxy, so their paths were confirmed in shallow clones instead.

## `2026-10-29-hubs-a.json` — 709 edges (frameworks, memory, gateways)
| Hub | Source pages | Matched |
|---|---|---|
| LangChain | docs.langchain.com providers index and integration pages | 65 |
| LangGraph | checkpointers, long-term memory, observability | 3 |
| LlamaIndex | `llama-index-integrations/*` packages | 74 |
| CrewAI | observability, tools, LLMs, knowledge, memory, MCP | 34 |
| AutoGen / AG2 | ag2 docs plus Microsoft autogen-ext | 16 |
| Semantic Kernel | vector store connectors, chat services | 12 |
| Haystack | haystack.deepset.ai/integrations | 46 |
| Pydantic AI | models, durable execution, evals, harness | 31 |
| Mastra | stores, observability, voice, browser | 30 |
| Vercel AI SDK | providers, observability, adapters | 43 |
| Agno | vectordb, models, tools, embedders | 44 |
| DSPy | language models, observability, retrievers | 7 |
| OpenAI Agents SDK | tracing processors, LiteLLM, sandboxes, MCP | 16 |
| Google ADK | adk.dev integrations, models, memory | 24 |
| Strands Agents | model providers, traces, tools | 21 |
| smolagents | models, inspect runs, code execution | 10 |
| Mem0 | integrations, vector stores, LLMs, embedders | 48 |
| Zep / Graphiti | framework pages, Graphiti README | 20 |
| Letta | model providers, MCP | 10 |
| LiteLLM | providers, observability, guardrails, MCP | 50 |
| OpenRouter | providers API, broadcast destinations | 36 |
| Portkey | integrations index | 69 |

## `2026-10-29-hubs-b.json` — 687 edges (data, evals, runtime, voice)
| Hub | Matched | Hub | Matched |
|---|---|---|---|
| Pinecone | 16 | Braintrust | 42 |
| Weaviate | 28 | W&B Weave | 22 |
| Qdrant | 30 | AgentOps | 17 |
| Milvus | 28 | Comet Opik | 46 |
| Chroma | 22 | Galileo | 12 |
| LanceDB | 11 | OpenLLMetry | 29 |
| Supabase | 4 | E2B | 17 |
| MongoDB Atlas | 28 | Daytona | 23 |
| Elastic | 7 | Modal | 4 |
| Neo4j | 19 | Browserbase | 10 |
| Langfuse | 63 | Stagehand | 8 |
| LangSmith | 28 | Composio | 9 |
| Arize Phoenix | 44 | Arcade | 14 |
| OpenInference | 27 | LiveKit Agents | 20 |
| Helicone | 21 | Pipecat | 22 |
| | | Vapi | 16 |

## Matching notes
- **MongoDB** maps to `mongodb-atlas-vector-search` only for vector-search and store integrations, not for session or log storage.
- **Opik** maps to the Comet ML row, and the evidence names Opik.
- **Microsoft AutoGen** extensions map to the AG2 row, except its memory modules, which map to `autogen-memory`.
- **Embedding-specific pages** map to the embedding rows (OpenAI Embeddings, Cohere Embed, Mistral Embed), not to the model rows.
- **Excluded where the catalog row is a different product:** Databricks, Snowflake, Datadog, New Relic, Redis (the only Redis row is Agent Memory Server), CopilotKit and Azure OpenAI.
- **Weaker citations, kept but worth knowing:**
  - About 20 LangChain edges cite only the providers index card.
  - The Daytona and Modal edges come from tutorial pages.
  - MongoDB marks some integrations as community-maintained, and the evidence says so.
  - Strands → Langfuse and Strands → Opik come from a "visualization options" list.
- **Dropped:** Strands → Mem0, because Strands' community-tools package is deprecated.

## Effect
`plan_stack` for a customer-support agent now documents 17 of its 36 component pairs, up from 5. The picks follow the evidence: Mem0, Milvus, Composio and Arize Phoenix replace picks that had no recorded links.
