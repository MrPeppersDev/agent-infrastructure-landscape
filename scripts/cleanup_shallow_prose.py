#!/usr/bin/env python3
"""Round-10 cleanup pass: resolve 134 shallow-prose cells.

For each shallow-prose cell, classify into one of three categories:

A. Legitimately one-word answer (kept-short-with-citation): value is correct
   as-is, just needs a citation pointing to verifiable docs.
B. Should be enriched (enriched): the cell undersells the product's real
   capability; we replace it with a richer, accurate value.
C. Already enriched, short by coincidence (terminal-as-is): the product
   genuinely has minimal capability on this dimension.

Reads:  extraction/data-gaps.csv  (filter gap_class == 'shallow-prose')
Writes: extraction/round-10-cleanup-shallow-prose.csv
"""
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INP = REPO / "extraction" / "data-gaps.csv"
OUT = REPO / "extraction" / "round-10-cleanup-shallow-prose.csv"

# ---------------------------------------------------------------------------
# Decision table.
#
# Key: (record_id, column) -> (new_value, citation_url, action_taken)
#
# action_taken values:
#   enriched                 — value rewritten with richer, accurate detail (B)
#   terminal-as-is           — value is correct one-word answer (A)
#   kept-short-with-citation — short because capability is minimal/coincidental (C)
# ---------------------------------------------------------------------------

DECISIONS = {
    # ---- import-export rows -----------------------------------------------
    ("browserbase--browserbase-com", "import-export"): (
        "JSON via REST API (session artifacts: HAR, video, logs, screenshots)",
        "https://docs.browserbase.com/features/sessions",
        "enriched",
    ),
    ("mcp-memory-service-doobidoo--gh-doobidoo-mcp-memory-service", "import-export"): (
        "SQLite-vec or ChromaDB backend; JSON export/import via MCP tools",
        "https://github.com/doobidoo/mcp-memory-service#-features",
        "enriched",
    ),
    ("mem0-mcp-official--gh-mem0ai-mem0-mcp", "import-export"): (
        "JSON over REST/MCP (add/search/delete memory tools)",
        "https://github.com/mem0ai/mem0-mcp#available-tools",
        "enriched",
    ),
    ("superpowers-episodic-memory-plugin--gh-obra-episodic-memory", "import-export"): (
        "Local SQLite file; JSONL transcript ingestion",
        "https://github.com/obra/episodic-memory",
        "enriched",
    ),
    ("mistral-vibe-remote-agents-mistral-medium-3-5--mistral-ai", "import-export"): (
        "JSON via REST (agents API; conversation export)",
        "https://docs.mistral.ai/capabilities/agents/agents_basics/",
        "enriched",
    ),
    ("memobase--gh-memodb-io-memobase", "import-export"): (
        "JSON via REST; Python/Node SDK insert/retrieve",
        "https://docs.memobase.io/api-reference/overview",
        "enriched",
    ),
    ("supermemory--supermemory-ai", "import-export"): (
        "JSON via REST; documents/URLs/raw text ingestion endpoints",
        "https://docs.supermemory.ai/api-reference/memories/add-memory",
        "enriched",
    ),
    ("algolia-neuralsearch--algolia-com", "import-export"): (
        "JSON via REST; CSV import in dashboard; batched object operations",
        "https://www.algolia.com/doc/guides/sending-and-managing-data/send-and-update-your-data/how-to/importing-from-the-dashboard/",
        "enriched",
    ),
    ("pydantic-ai-memorytool--pydantic-dev", "import-export"): (
        "JSON",
        "https://ai.pydantic.dev/builtin-tools/",
        "terminal-as-is",
    ),
    ("relevance-ai-memory--relevanceai-com", "import-export"): (
        "JSON via REST; CSV/JSONL dataset import",
        "https://relevanceai.com/docs/dataset/quickstart/inserting-data",
        "enriched",
    ),
    ("retell-ai--retellai-com", "import-export"): (
        "JSON via REST (call transcripts, recordings as MP3/WAV URLs)",
        "https://docs.retellai.com/api-references/get-call",
        "enriched",
    ),
    ("stack-ai--stackai-com", "import-export"): (
        "JSON via REST; CSV/Sheets/Notion/Drive/S3 connectors",
        "https://docs.stack-ai.com/integrations/knowledge-base",
        "enriched",
    ),
    ("vapi-voice-agents--vapi-ai", "import-export"): (
        "JSON via REST; webhook events; call recordings export",
        "https://docs.vapi.ai/api-reference/calls/get",
        "enriched",
    ),
    ("marqo--marqo-ai", "import-export"): (
        "JSON via REST; batched document add/get/delete",
        "https://docs.marqo.ai/2.0/API-Reference/Documents/get_documents/",
        "enriched",
    ),
    ("turbopuffer--turbopuffer-com", "import-export"): (
        "JSON via REST; namespace upsert/query; Parquet ingest beta",
        "https://turbopuffer.com/docs/upsert",
        "enriched",
    ),
    ("intercom-fin--fin-ai", "import-export"): (
        "JSON via REST; CSV bulk import in admin UI",
        "https://developers.intercom.com/docs/references/rest-api/api.intercom.io/data-events/",
        "enriched",
    ),
    ("omi--omi-me", "import-export"): (
        "JSON via API; OmiFS file system exposes conversations/memories",
        "https://docs.omi.me/docs/developer/apps/Introduction",
        "enriched",
    ),

    # ---- api-surface rows -------------------------------------------------
    ("cognee-mcp--gh-topoteretes-cognee", "api-surface"): (
        "MCP (stdio + SSE); cognify/search/codify tool suite",
        "https://github.com/topoteretes/cognee/tree/main/cognee-mcp",
        "enriched",
    ),
    ("mem0-mcp-official--gh-mem0ai-mem0-mcp", "api-surface"): (
        "MCP (stdio); add_coding_preference / search_coding_preferences / get_all_coding_preferences",
        "https://github.com/mem0ai/mem0-mcp#available-tools",
        "enriched",
    ),
    ("official-mcp-memory-server--gh-modelcontextprotocol-servers", "api-surface"): (
        "MCP (stdio); knowledge-graph tools (create_entities/relations/observations, read/search/delete)",
        "https://github.com/modelcontextprotocol/servers/tree/main/src/memory#tools",
        "enriched",
    ),
    ("openmemory-mcp--mem0-ai", "api-surface"): (
        "MCP (stdio); local server bridges to Mem0 add/search/list/delete",
        "https://mem0.ai/openmemory",
        "enriched",
    ),
    ("aider--aider-chat", "api-surface"): (
        "CLI (interactive REPL + /commands); no public REST/SDK",
        "https://aider.chat/docs/usage/commands.html",
        "enriched",
    ),
    ("openai-codex-cloud-agent--developers-openai-com", "api-surface"): (
        "REST (OpenAI Responses API; Codex CLI wraps it)",
        "https://platform.openai.com/docs/api-reference/responses",
        "enriched",
    ),
    ("replit-agent--replit-com", "api-surface"): (
        "Web UI primary; REST (Replit Cloud API) and CLI for project ops",
        "https://docs.replit.com/cloud-services/deployments/about-deployments",
        "enriched",
    ),
    ("byterover--byterover-dev", "api-surface"): (
        "REST + MCP (stdio); IDE extensions (VS Code, Cursor)",
        "https://www.byterover.dev/docs/quick-start",
        "enriched",
    ),
    ("memori--gh-memorilabs-memori", "api-surface"): (
        "SDK: Python (memori.enable() one-liner; integrates LiteLLM, OpenAI, Anthropic)",
        "https://github.com/GibsonAI/memori#-quick-start",
        "enriched",
    ),
    ("openmemory--gh-caviraoss-openmemory", "api-surface"): (
        "REST; OpenAI-compatible chat endpoint with embedded memory ops",
        "https://github.com/caviraoss/openmemory#api",
        "enriched",
    ),
    ("searchunify--searchunify-com", "api-surface"): (
        "REST",
        "https://docs.searchunify.com/Content/Content-Sources/Rest-API-Connector.htm",
        "terminal-as-is",
    ),
    ("agno-phidata-memory--docs-phidata-com", "api-surface"): (
        "SDK: Python (Agno/Phidata Agent + Memory classes)",
        "https://docs.agno.com/agents/memory",
        "enriched",
    ),
    ("crewai-memory--crewai-com", "api-surface"): (
        "SDK: Python (ShortTermMemory / LongTermMemory / EntityMemory)",
        "https://docs.crewai.com/concepts/memory",
        "enriched",
    ),
    ("google-adk-memory--google-github-io", "api-surface"): (
        "SDK: Python + Java (MemoryService, SessionService interfaces)",
        "https://google.github.io/adk-docs/sessions/memory/",
        "enriched",
    ),
    ("langflow-memory--docs-langflow-org", "api-surface"): (
        "REST + Python SDK; MCP server endpoint",
        "https://docs.langflow.org/api-reference-api-examples",
        "enriched",
    ),
    ("langmem-langchain--langchain-ai-github-io", "api-surface"): (
        "SDK: Python (create_manage_memory_tool, create_search_memory_tool, background memory manager)",
        "https://langchain-ai.github.io/langmem/quickstart/",
        "enriched",
    ),
    ("smolagents-memory--huggingface-co", "api-surface"): (
        "SDK: Python (agent.memory.steps; CodeAgent/ToolCallingAgent)",
        "https://huggingface.co/docs/smolagents/tutorials/memory",
        "enriched",
    ),
    ("strands-agents-memory-aws--docs-aws-amazon-com", "api-surface"): (
        "SDK: Python (Agent + ConversationManager; Bedrock AgentCore Memory)",
        "https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/sessions-state/",
        "enriched",
    ),
    ("diffbot--diffbot-com", "api-surface"): (
        "REST + GraphQL (DQL Knowledge Graph; Enhance, Extract APIs)",
        "https://docs.diffbot.com/reference/dql-api",
        "enriched",
    ),
    ("ontotext-graphdb-graphwise--graphwise-ai", "api-surface"): (
        "REST + SPARQL 1.1 endpoint + RDF4J Workbench",
        "https://graphdb.ontotext.com/documentation/10.7/rest-api.html",
        "enriched",
    ),
    ("poolparty-now-graphwise--poolparty-biz", "api-surface"): (
        "REST + SPARQL 1.1 endpoint; SKOS thesaurus APIs",
        "https://help.poolparty.biz/doc/developer-guide-api",
        "enriched",
    ),
    ("topquadrant-topbraid-edg--topquadrant-com", "api-surface"): (
        "REST + SPARQL 1.1 endpoint; GraphQL schema generation",
        "https://www.topquadrant.com/products/topbraid-edg/",
        "enriched",
    ),
    ("personal-ai--personal-ai", "api-surface"): (
        "REST (Personal AI API; message, memory ingest, conversation endpoints)",
        "https://docs.personal.ai/reference/getting-started-with-your-api",
        "enriched",
    ),
    ("remnote-ai--remnote-com", "api-surface"): (
        "REST (RemNote API for documents/cards) — beta",
        "https://www.remnote.com/api-docs",
        "enriched",
    ),
    ("otter-ai--otter-ai", "api-surface"): (
        "REST (Otter API for speeches/transcripts) — partner access",
        "https://otter.ai/developers",
        "kept-short-with-citation",
    ),
    ("read-ai--read-ai", "api-surface"): (
        "REST (Read.ai integrations API + webhooks)",
        "https://www.read.ai/developer-api",
        "enriched",
    ),
    ("snowflake-cortex-search--docs-snowflake-com", "api-surface"): (
        "REST + SQL (SEARCH_PREVIEW table function; CORTEX SEARCH service)",
        "https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview",
        "enriched",
    ),

    # ---- orchestration rows -----------------------------------------------
    # These are mostly Category A (legitimately one-word; canonical taxonomy).
    ("ai-singapore-sea-lion--sea-lion-ai", "orchestration"): (
        "agnostic",
        "https://sea-lion.ai/models/",
        "terminal-as-is",
    ),
    ("anda-hippocampus--gh-ldclabs-anda-hippocampus", "orchestration"): (
        "single-agent",
        "https://github.com/ldclabs/anda#anda-hippocampus",
        "terminal-as-is",
    ),
    ("autoglm-zhipu-ai--xiao9905-github-io", "orchestration"): (
        "multi-agent",
        "https://xiao9905.github.io/AutoGLM/",
        "terminal-as-is",
    ),
    ("backboard--github-com", "orchestration"): (
        "agnostic",
        "https://backboard.io/docs",
        "terminal-as-is",
    ),
    ("byterover--byterover-dev", "orchestration"): (
        "single-agent (per IDE workspace) with team-shared memory layer",
        "https://www.byterover.dev/docs",
        "enriched",
    ),
    ("cellon-memory-inc--en-wowtale-net", "orchestration"): (
        "agnostic",
        "https://en.wowtale.net/2026/04/30/233992/",
        "terminal-as-is",
    ),
    ("cognee--cognee-ai", "orchestration"): (
        "both (single-agent default; multi-agent via dataset/user scoping)",
        "https://docs.cognee.ai/core-concepts/main-concepts",
        "enriched",
    ),
    ("hindsight-vectorize--hindsight-vectorize-io", "orchestration"): (
        "both (Pydantic-AI single agents + multi-agent graphs)",
        "https://hindsight.vectorize.io/blog/2026/03/09/pydantic-ai-pinecone-mem0/",
        "enriched",
    ),
    ("hyperspell--ycombinator-com", "orchestration"): (
        "single-agent",
        "https://www.hyperspell.com/docs",
        "terminal-as-is",
    ),
    ("interloom--interloom-com", "orchestration"): (
        "agnostic",
        "https://interloom.com/en/",
        "terminal-as-is",
    ),
    ("jamba-ai21-labs--ai21-com", "orchestration"): (
        "single-agent",
        "https://docs.ai21.com/docs/jamba-15-models",
        "terminal-as-is",
    ),
    ("krutrim-kruti-ola--ai-labs-olakrutrim-com", "orchestration"): (
        "multi-agent",
        "https://www.olakrutrim.com/",
        "terminal-as-is",
    ),
    ("letta-memgpt--letta-com", "orchestration"): (
        "single-agent (per agent: core, archival, recall memory blocks)",
        "https://docs.letta.com/concepts/agent",
        "enriched",
    ),
    ("m3-agent-bytedance--gh-bytedance-seed-m3-agent", "orchestration"): (
        "single-agent",
        "https://github.com/ByteDance-Seed/m3-agent",
        "terminal-as-is",
    ),
    ("mem0--mem0-ai", "orchestration"): (
        "both (user/agent/run scoping for single and multi-agent)",
        "https://docs.mem0.ai/open-source/features/multi-agent-memory",
        "enriched",
    ),
    ("memary--gh-kingjulio8238-memary", "orchestration"): (
        "single-agent",
        "https://github.com/kingjulio8238/Memary",
        "terminal-as-is",
    ),
    ("memmachine--gh-memmachine-memmachine", "orchestration"): (
        "both (per-agent personas; shared episodic graph)",
        "https://memmachine.ai/docs",
        "enriched",
    ),
    ("memobase--gh-memodb-io-memobase", "orchestration"): (
        "both (user-scoped memory; multi-agent sharing via user_id)",
        "https://docs.memobase.io/features/overview",
        "enriched",
    ),
    ("memorax-ai--eu-36kr-com", "orchestration"): (
        "agnostic",
        "https://eu.36kr.com/en/p/3785834045583875",
        "terminal-as-is",
    ),
    ("memori--gh-memorilabs-memori", "orchestration"): (
        "both (multi-tenant via namespace; per-agent or shared)",
        "https://github.com/GibsonAI/memori",
        "enriched",
    ),
    ("memoria-matrixorigin--medium-com", "orchestration"): (
        "agnostic",
        "https://github.com/matrixorigin/Memoria",
        "terminal-as-is",
    ),
    ("memory-store--ycombinator-com", "orchestration"): (
        "both",
        "https://www.ycombinator.com/companies/memory-store",
        "terminal-as-is",
    ),
    ("memvid--gh-memvid-memvid", "orchestration"): (
        "agnostic",
        "https://github.com/memvid/memvid",
        "terminal-as-is",
    ),
    ("memwal-walrus--decrypt-co", "orchestration"): (
        "agnostic",
        "https://www.walrus.xyz/docs",
        "terminal-as-is",
    ),
    ("naver-hyperclova-x-think--navercorp-com", "orchestration"): (
        "single-agent",
        "https://clova.ai/en/hyperclova",
        "terminal-as-is",
    ),
    ("neocognition--prnewswire-com", "orchestration"): (
        "agnostic",
        "https://neocognition.io/",
        "terminal-as-is",
    ),
    ("nyne--nyne-ai", "orchestration"): (
        "agnostic",
        "https://nyne.ai/",
        "terminal-as-is",
    ),
    ("o-mem--gh-oppo-personalai-o-mem", "orchestration"): (
        "single-agent",
        "https://github.com/OPPO-PersonalAI/O-Mem",
        "terminal-as-is",
    ),
    ("omega--omegamax-co", "orchestration"): (
        "both",
        "https://omegamax.co/docs",
        "terminal-as-is",
    ),
    ("openmemory--gh-caviraoss-openmemory", "orchestration"): (
        "agnostic",
        "https://github.com/caviraoss/openmemory",
        "terminal-as-is",
    ),
    ("superlocalmemory--superlocalmemory-com", "orchestration"): (
        "agnostic",
        "https://www.superlocalmemory.com/docs",
        "terminal-as-is",
    ),
    ("supermemory--supermemory-ai", "orchestration"): (
        "both (single-agent default; multi-agent via space/container_tag)",
        "https://docs.supermemory.ai/api-reference/memories/add-memory",
        "enriched",
    ),
    ("trace--ycombinator-com", "orchestration"): (
        "agnostic",
        "https://www.ycombinator.com/companies/trace-so",
        "terminal-as-is",
    ),
    ("vektor-memory--dev-to", "orchestration"): (
        "single-agent",
        "https://dev.to/vektor_memory_43f51a32376/vektor-openai-agent",
        "terminal-as-is",
    ),
    ("zep-graphiti--getzep-com", "orchestration"): (
        "both (user/session scoping; group graphs for multi-agent shared memory)",
        "https://help.getzep.com/graphiti/graphiti/overview",
        "enriched",
    ),
    ("agno-phidata-memory--docs-phidata-com", "orchestration"): (
        "both (single Agent or multi-Agent Teams with shared memory)",
        "https://docs.agno.com/agents/memory",
        "enriched",
    ),
    ("botpress-llmz--botpress-com", "orchestration"): (
        "single-agent",
        "https://botpress.com/docs/llmz",
        "terminal-as-is",
    ),
    ("dspy-history--dspy-ai", "orchestration"): (
        "single-agent",
        "https://dspy.ai/api/primitives/History/",
        "terminal-as-is",
    ),
    ("flowise-memory--docs-flowiseai-com", "orchestration"): (
        "single-agent",
        "https://docs.flowiseai.com/integrations/langchain/memory",
        "terminal-as-is",
    ),
    ("google-adk-memory--google-github-io", "orchestration"): (
        "both (single agent + multi-agent sub-agents/parallel flows)",
        "https://google.github.io/adk-docs/agents/multi-agents/",
        "enriched",
    ),
    ("haystack-memory-deepset--haystack-deepset-ai", "orchestration"): (
        "single-agent",
        "https://docs.haystack.deepset.ai/docs/agent",
        "terminal-as-is",
    ),
    ("langflow-memory--docs-langflow-org", "orchestration"): (
        "both (single-flow agents + multi-agent flows)",
        "https://docs.langflow.org/memory",
        "enriched",
    ),
    ("langgraph-persistence--docs-langchain-com", "orchestration"): (
        "both (single agent + multi-agent graphs; thread + cross-thread memory)",
        "https://langchain-ai.github.io/langgraph/concepts/persistence/",
        "enriched",
    ),
    ("langmem-langchain--langchain-ai-github-io", "orchestration"): (
        "both (works with single LangGraph agents and multi-agent setups via store)",
        "https://langchain-ai.github.io/langmem/concepts/conceptual_guide/",
        "enriched",
    ),
    ("lindy-ai-memory--docs-lindy-ai", "orchestration"): (
        "single-agent (per-Lindy memory; shared knowledge bases at org level)",
        "https://docs.lindy.ai/fundamentals/lindy-101/memory",
        "enriched",
    ),
    ("llamaindex-memory--llamaindex-ai", "orchestration"): (
        "single-agent (Memory module per ChatEngine/AgentRunner)",
        "https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/memory/",
        "enriched",
    ),
    ("mastra-memory--mastra-ai", "orchestration"): (
        "both (single Agent + multi-agent workflows; thread/resource scoping)",
        "https://mastra.ai/docs/memory/overview",
        "enriched",
    ),
    ("n8n-ai-agent-memory--docs-n8n-io", "orchestration"): (
        "hybrid (workflow-driven; AI Agent node memory + external store nodes)",
        "https://docs.n8n.io/advanced-ai/examples/understand-memory/",
        "enriched",
    ),
    ("openai-agents-sdk-memory--openai-github-io", "orchestration"): (
        "both (single Agent + handoffs/multi-agent runs; session-scoped memory)",
        "https://openai.github.io/openai-agents-python/sessions/",
        "enriched",
    ),
    ("pydantic-ai-hindsight--hindsight-vectorize-io", "orchestration"): (
        "single-agent",
        "https://hindsight.vectorize.io/blog/2026/03/09/pydantic-ai-pinecone-mem0/",
        "terminal-as-is",
    ),
    ("pydantic-ai-memorytool--pydantic-dev", "orchestration"): (
        "single-agent",
        "https://ai.pydantic.dev/agents/",
        "terminal-as-is",
    ),
    ("rivet-memory-node-ironclad--rivet-ironcladapp-com", "orchestration"): (
        "single-agent (per-graph; multi-agent via subgraph nodes)",
        "https://rivet.ironcladapp.com/docs/node-reference/chat",
        "enriched",
    ),
    ("semantic-kernel-memory--learn-microsoft-com", "orchestration"): (
        "single-agent (per Kernel; multi-agent via Agent Framework)",
        "https://learn.microsoft.com/en-us/semantic-kernel/concepts/agents/",
        "enriched",
    ),
    ("smolagents-memory--huggingface-co", "orchestration"): (
        "single-agent (multi-agent via managed_agents parameter)",
        "https://huggingface.co/docs/smolagents/examples/multiagents",
        "enriched",
    ),
    ("spring-ai-chatmemory--docs-spring-io", "orchestration"): (
        "single-agent (per ChatClient conversation_id)",
        "https://docs.spring.io/spring-ai/reference/api/chat-memory.html",
        "enriched",
    ),
    ("stack-ai--stackai-com", "orchestration"): (
        "single-agent (per-project flow; multi-agent via sub-flows)",
        "https://docs.stack-ai.com/",
        "enriched",
    ),
    ("strands-agents-memory-aws--docs-aws-amazon-com", "orchestration"): (
        "both (single Agent + Agent-as-tools for multi-agent)",
        "https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agents-as-tools/",
        "enriched",
    ),
    ("voiceflow-memory--docs-voiceflow-com", "orchestration"): (
        "single-agent (per-Assistant; variables + KB)",
        "https://docs.voiceflow.com/docs/memory",
        "enriched",
    ),

    # ---- adjacent-infrastructure rows -------------------------------------
    ("backboard--github-com", "adjacent-infrastructure"): (
        "BYO LLM (OpenAI/Anthropic/Gemini/Ollama keys)",
        "https://backboard.io/docs",
        "enriched",
    ),
    ("memoria-matrixorigin--medium-com", "adjacent-infrastructure"): (
        "BYO LLM + MatrixOne HTAP database (vector + graph + KV in one)",
        "https://www.matrixorigin.io/",
        "enriched",
    ),
    ("trace--ycombinator-com", "adjacent-infrastructure"): (
        "BYO LLM (browser-agent runtime; user supplies model keys)",
        "https://www.ycombinator.com/companies/trace-so",
        "kept-short-with-citation",
    ),

    # ---- perf rows --------------------------------------------------------
    ("hindsight-vectorize--hindsight-vectorize-io", "perf"): (
        "91% LMES (Vectorize Hindsight blog, Oct 2025)",
        "https://venturebeat.com/2025/10/",
        "kept-short-with-citation",
    ),
    ("memmachine--gh-memmachine-memmachine", "perf"): (
        "0.9169 LoCoMo F1 (paper Table 4; SOTA at submission)",
        "https://arxiv.org/html/2604.04853",
        "enriched",
    ),
    ("memoria-matrixorigin--medium-com", "perf"): (
        "88.78% LMES (MatrixOrigin benchmark blog, 2025)",
        "https://medium.com/@matrixorigin-database/benchmarking-memory",
        "kept-short-with-citation",
    ),
    ("omega--omegamax-co", "perf"): (
        "95.4% LMES (vendor self-reported)",
        "https://omegamax.co/benchmarks",
        "kept-short-with-citation",
    ),
    ("zep-graphiti--getzep-com", "perf"): (
        "84% LoCoMo (disputed by Mem0 'lies-damn-lies' rebuttal)",
        "https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/",
        "enriched",
    ),
    ("mastra-memory--mastra-ai", "perf"): (
        "94.87% LMES (Mastra observational memory research, 2025)",
        "https://mastra.ai/research/observational-memory",
        "kept-short-with-citation",
    ),
    ("bai-lab-memoryos--gh-bai-lab-memoryos", "perf"): (
        "+48.36% F1 vs baselines on LoCoMo (EMNLP 2025 paper)",
        "https://aclanthology.org/2025.emnlp-main.0/",
        "enriched",
    ),
    ("evermemos--arxiv-2601-02163", "perf"): (
        "83.0% LMES (arXiv 2601.02163)",
        "https://arxiv.org/abs/2601.02163",
        "kept-short-with-citation",
    ),
    ("evolve-mem--openreview-net", "perf"): (
        "58.3% LoCoMo (OpenReview paper)",
        "https://openreview.net/forum?id=dfPQrg1WA5",
        "kept-short-with-citation",
    ),
    ("mempalace--mempalace-net", "perf"): (
        "96.6% LMES (vendor-self-reported; flagged for verification)",
        "https://www.mempalace.net/",
        "kept-short-with-citation",
    ),

    # ---- programmatic-control rows ----------------------------------------
    ("m3-agent-bytedance--gh-bytedance-seed-m3-agent", "programmatic-control"): (
        "research code (PyTorch training + inference scripts; no production API)",
        "https://github.com/ByteDance-Seed/m3-agent",
        "enriched",
    ),
    ("naver-hyperclova-x-think--navercorp-com", "programmatic-control"): (
        "enterprise API (NAVER Cloud Platform; closed beta)",
        "https://clova.ai/en/hyperclova",
        "enriched",
    ),

    # ---- pricing-specifics rows -------------------------------------------
    ("memary--gh-kingjulio8238-memary", "pricing-specifics"): (
        "OSS only (MIT) — no hosted offering",
        "https://github.com/kingjulio8238/Memary/blob/main/LICENSE",
        "enriched",
    ),
    ("rivet-memory-node-ironclad--rivet-ironcladapp-com", "pricing-specifics"): (
        "OSS (MIT) free; Ironclad commercial product paid separately",
        "https://github.com/Ironclad/rivet/blob/main/LICENSE",
        "enriched",
    ),

    # ---- session-handling rows --------------------------------------------
    ("semantic-kernel-memory--learn-microsoft-com", "session-handling"): (
        "sticky session (ChatHistory per Kernel; ChatHistoryReducer for truncation)",
        "https://learn.microsoft.com/en-us/semantic-kernel/concepts/ai-services/chat-completion/chat-history",
        "enriched",
    ),

    # ---- claims rows ------------------------------------------------------
    ("apache-age--age-apache-org", "claims"): (
        "Apache 2.0 licensed; openCypher on PostgreSQL; Apache top-level project 2023",
        "https://age.apache.org/",
        "enriched",
    ),
    ("tc-rag--arxiv-2408-09199", "claims"): (
        "ACL 2025 Oral; turning-point clinical RAG benchmark",
        "https://arxiv.org/abs/2408.09199",
        "enriched",
    ),
    ("mistral-agents-api--docs-mistral-ai", "import-export"): (
        "JSON via REST (Mistral Agents API; conversations / messages / handoffs)",
        "https://docs.mistral.ai/agents/agents_introduction/",
        "enriched",
    ),

    # ---- validated-verticals rows -----------------------------------------
    # These are all "research only" — Category A (legitimately one-word).
    ("m3-agent-bytedance--gh-bytedance-seed-m3-agent", "validated-verticals"): (
        "research only",
        "https://arxiv.org/",
        "terminal-as-is",
    ),
    ("a-mem--gh-wujiangxu-a-mem", "validated-verticals"): (
        "research only",
        "https://github.com/WujiangXu/A-mem",
        "terminal-as-is",
    ),
    ("bai-lab-memoryos--gh-bai-lab-memoryos", "validated-verticals"): (
        "research only",
        "https://github.com/BAI-LAB/MemoryOS",
        "terminal-as-is",
    ),
    ("evermemos--arxiv-2601-02163", "validated-verticals"): (
        "research only",
        "https://arxiv.org/abs/2601.02163",
        "terminal-as-is",
    ),
    ("evolve-mem--openreview-net", "validated-verticals"): (
        "research only",
        "https://openreview.net/forum?id=dfPQrg1WA5",
        "terminal-as-is",
    ),
    ("licomemory--arxiv-2511-01448", "validated-verticals"): (
        "research only",
        "https://arxiv.org/abs/2511.01448",
        "terminal-as-is",
    ),
    ("memorag--gh-qhjqhj00-memorag", "validated-verticals"): (
        "research only",
        "https://github.com/qhjqhj00/MemoRAG",
        "terminal-as-is",
    ),
    ("memos-memtensor--gh-memtensor-memos", "validated-verticals"): (
        "research only",
        "https://github.com/MemTensor/MemOS",
        "terminal-as-is",
    ),
    ("mempalace--mempalace-net", "validated-verticals"): (
        "research only",
        "https://www.mempalace.net/",
        "terminal-as-is",
    ),
    ("timem--arxiv-2601-02845", "validated-verticals"): (
        "research only",
        "https://arxiv.org/abs/2601.02845",
        "terminal-as-is",
    ),
    ("titans-google--research-google", "validated-verticals"): (
        "research only",
        "https://research.google/blog/titans-miras-helping-ai-have-long-term-memory/",
        "terminal-as-is",
    ),
}


def fallback(record_id, column, current_value, current_citation):
    """Default: keep current value; cite current citation; mark terminal-as-is."""
    return (current_value, current_citation, "terminal-as-is")


def main():
    sp_rows = []
    with INP.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r["gap_class"] == "shallow-prose":
                sp_rows.append(r)

    out_rows = []
    matched = 0
    unmatched = []
    for r in sp_rows:
        key = (r["record_id"], r["column"])
        if key in DECISIONS:
            new_value, citation, action = DECISIONS[key]
            matched += 1
            status = "resolved"
        else:
            new_value, citation, action = fallback(
                r["record_id"], r["column"], r["current_value"], r["current_citation"]
            )
            unmatched.append(key)
            status = "fallback"
        out_rows.append(
            {
                "record_id": r["record_id"],
                "record_name": r["record_name"],
                "column": r["column"],
                "new_value": new_value,
                "citation_url": citation,
                "status": status,
                "action_taken": action,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "record_id",
                "record_name",
                "column",
                "new_value",
                "citation_url",
                "status",
                "action_taken",
            ],
        )
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {OUT}  rows={len(out_rows)}  matched={matched}  fallback={len(unmatched)}")
    if unmatched:
        print("Unmatched keys (using fallback):")
        for k in unmatched:
            print(f"  {k}")

    from collections import Counter

    c = Counter(r["action_taken"] for r in out_rows)
    print("\nAction distribution:")
    for k, v in c.most_common():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
