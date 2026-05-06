# Data 9: MCP Server Install Indicators and Job Postings

Captured: 2026-05-06. Methods: GitHub API (stars, forks, stargazer timestamps), npm downloads API, MCP official registry API, LinkedIn/ZipRecruiter web searches. All counts are point-in-time snapshots.

---

## Part A: MCP Server Installation Indicators

### Tier 1 — Commercial products with MCP servers

**Official MCP Memory server** (`@modelcontextprotocol/server-memory`) is the clear volume leader with 344,134 npm downloads in the last 30 days. It lives in the `modelcontextprotocol/servers` monorepo (85k stars, 10.6k forks) and is the only entry listed in the official MCP registry. Its dominance reflects its position as the default first-touch MCP memory experiment, not necessarily production deployment.

**Mem0 MCP** (`mem0ai/mem0-mcp`): 650 stars, 139 forks, 8 new stars in the last 30 days. Ships as a PyPI package (`mem0-mcp-server v0.2.1`); npm equivalent not found. Low fork count relative to the parent `mem0ai/mem0` repo (54.9k stars, 366,945 monthly PyPI downloads) suggests most Mem0 users consume the Python SDK directly rather than the MCP wrapper.

**Graphiti MCP Server** (Zep): The Graphiti repo has 25,739 stars and 2,560 forks — the largest fork count among purpose-built memory systems. 39 new stars in the last 30 days. No npm or PyPI package for the MCP server specifically; consumed as a Python import. The v1.0 MCP release announcement drove the 20k-star milestone in late 2025.

**Cognee MCP**: 17,055 stars, 1,780 forks, 55 new stars in the last 30 days — the highest 30-day star velocity among the commercial memory MCP servers. MCP capability was bundled in v0.3.5+.

**Hindsight MCP** (Vectorize): 12,331 stars, 706 forks, 31 new stars in 30 days. MCP server launched March 2026.

**Supermemory / claude-supermemory**: `supermemoryai/claude-supermemory` has 2,561 stars and 61 new stars in 30 days — notably high 30-day velocity for its size. Distributed as a Claude Code plugin rather than npm/PyPI. The parent `supermemory` repo sits at 22,416 stars.

**Memobase MCP**: 2,708 stars, 210 forks, 8 new stars in 30 days. Available on Playbooks MCP directory.

### Tier 2 — Community / author-maintained MCP servers

**mcp-memory-service** (doobidoo): 1,787 stars, 274 forks, 87 new stars in the last 30 days. The highest 30-day velocity in the community tier — a surprising signal for an author-maintained project. No npm package found.

**engram** (Gentleman-Programming): 3,244 stars, 370 forks, 44 new stars in 30 days. Static Go binary with HTTP + MCP + CLI — most operationally self-contained of the community servers.

**mcp-knowledge-graph** (shaneholloman): 849 stars, 102 forks, 13 new stars in 30 days. A stable local fork of the official server, targeted at teams that want the official KG model without npx churn.

**mcp-memory** (Puliczek): 142 stars, 13 forks, 5 new stars in 30 days. Cloudflare-native; lightweight.

**claude-brain** (memvid): 488 stars, 47 forks, 88 new stars in 30 days — the highest 30-day velocity of any entry in this list. This is a Claude Code plugin packaging Memvid. The spike may reflect marketing rather than sustained adoption; the absolute base is small.

**local-memory-mcp** (studiomeyer-io): Only 5 total stars but 784 npm downloads in the last month and 5 stars in the last 30 days. Very new project where npm install counts exceed GitHub discovery — suggests direct package adoption before the repo accrued visibility.

**Claude-CursorMemoryMCP** (Angleito): 4 stars, 0 forks, 0 new stars. Effectively zero adoption.

### Official MCP registry status

The official registry at `registry.modelcontextprotocol.io` returned only the `@modelcontextprotocol/server-memory` entry among memory-related systems across the pages sampled. None of the commercial third-party memory MCP servers (Mem0, Graphiti, Cognee, Hindsight, Memobase) appeared in the registry. The registry appears to be early-stage — each page returned 30 entries, primarily non-memory services — so absence is not necessarily disqualifying.

### Key takeaway (Part A)

The official MCP server is the installation volume leader by two orders of magnitude (344k monthly npm downloads vs. the next-largest, `mem0ai` PyPI at 367k for the full SDK). Among purpose-built third-party MCP servers, Graphiti and Cognee have the largest fork bases (indicative of people running their own copies), while Cognee, mcp-memory-service, claude-supermemory, and claude-brain are the fastest-growing in the last 30 days. There is no centralized install-count registry; forks + npm downloads are the best available proxies.

---

## Part B: Job Postings Mentioning Technology

LinkedIn keyword searches are noisy: "Granola" returns food jobs; "Notion" returns all Notion users and users of the tool generically; small company names (Letta, Zep) return mostly company-internal headcount. Numbers below distinguish between "jobs at the company" and "jobs mentioning the technology as a skill" where that distinction was identifiable. All counts sourced from LinkedIn unless otherwise noted.

| System | Jobs (worldwide) | Notes |
|--------|-----------------|-------|
| LangChain | 15,000+ | Skill-mention count; dominant agentic framework (34.3% of agentic listings per April 2026 analysis) |
| Notion (incl. Notion AI) | 11,000+ | Highly diluted — includes all users of Notion as a tool |
| Neo4j | 2,000+ | Mixture of company and skill-mention |
| AutoGen | ~2,500 | Estimated; noisy keyword |
| Qdrant | 674 | Includes skill-mention jobs, not just Qdrant company roles |
| CrewAI | ~1,200–1,500 | Estimated; noisy keyword |
| Glean | 660 | Company jobs only |
| Pinecone | 433 | Skill-mention + company jobs |
| Replit | 1,000+ | Company jobs |
| Hippocratic AI | 76 | Company jobs only |
| Otter.ai | 146 (17 at company directly) | "Otter.ai" keyword match |
| Cognition (Devin) | 128 | Company jobs |
| Weaviate | ~82 | Company jobs |
| LlamaIndex | 8 | Company jobs only |
| Mem0 | 7 | Company jobs only |
| Zep | 7 | US-filtered; small startup |
| Inworld AI | 10 | Company jobs |
| Letta | ~8 | Ashby/LinkedIn; small team |
| Lovable | 2 | Company jobs only |
| Granola | ~1 AI-relevant | 801 results but dominated by food industry |
| Sierra | ~18 | ZipRecruiter (LinkedIn count not found) |
| Harvey | Unknown | Active hiring but count not enumerated from public search |
| Cursor | Unclear | Two companies named "Cursor" on LinkedIn; anysphere (Cursor IDE) jobs not enumerated |

### Key takeaway (Part B)

LangChain is the only memory-adjacent technology with a five-figure job-posting count, reflecting its status as the dominant orchestration layer. Infrastructure-tier tools (Neo4j, Qdrant, Pinecone, Weaviate) show the next band at 400–2,000. Most dedicated memory-layer companies (Mem0, Zep, Letta, Cognee) are small enough that their "job postings" reflect internal headcount rather than ecosystem demand — single digits to low tens. The workforce-demand proxy is most meaningful for the infrastructure and framework tiers; for the memory-specific products it primarily signals company size, not technology adoption breadth.

**Reliability caveat**: LinkedIn keyword search has significant noise from unrelated uses of common terms (Notion, Granola, Cursor). Job counts for small companies primarily reflect internal headcount; they do not represent external demand for the technology skill. Framework-tier counts (LangChain 15k+, AutoGen 2.5k, CrewAI 1.2k) are the most useful signal of workforce demand; company-tier counts (Mem0: 7, Zep: 7) are nearly independent of adoption breadth.

