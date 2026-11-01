# AI Agent Infrastructure Landscape

**An analysis tool for the AI agent stack. Work out what's best for the agent or multi-agent system you're building, with a citation behind every claim.**

- **Build a stack:** describe the product; get one cited pick per layer (framework, model, gateway, memory, vector/graph store, tools and auth, sandbox, guardrails, observability), the runners-up and why not, integrations, risk, OWASP coverage, cost and a `stack.yml`.
- **Choose one layer:** memory, framework or data store.
- **Check a stack you run:** archived, acquired or stale dependencies, with replacements that fit the rest of your stack.

Underneath is an open, comparative catalog of **1,005 systems** across the agent stack. Every cell links to the source it came from and carries a verifiability tier. Bots keep it fresh, and anyone can submit a missing system.

**[Build a stack →](https://mrpeppersdev.github.io/agent-infrastructure-landscape/build)** · [Check your stack](https://mrpeppersdev.github.io/agent-infrastructure-landscape/check) · [Choose a component](https://mrpeppersdev.github.io/agent-infrastructure-landscape/choose) · [Browse the catalog](https://mrpeppersdev.github.io/agent-infrastructure-landscape/) · [Findings](https://mrpeppersdev.github.io/agent-infrastructure-landscape/findings) · [Submit a system](https://mrpeppersdev.github.io/agent-infrastructure-landscape/submit) · [Raw data (CC-BY-4.0)](./data/landscape.json)

## Five catalogs in one dataset

The catalog is split into five product families. Each one stands on its own; the typed edges connect them.

| Catalog | Systems | What's in it | Open it |
|---|---:|---|---|
| **Agent Memory** | 283 | Shipping memory layers (Mem0, Zep/Graphiti, Letta, Cognee…), platform memory (ChatGPT, Claude, Gemini, AgentCore, Vertex), coding-agent memory, personal/lifelogging memory, memory governance | [`?product=memory`](https://mrpeppersdev.github.io/agent-infrastructure-landscape/?product=memory) |
| **Memory Research & Benchmarks** | 247 | Method papers, benchmarks (LongMemEval, LoCoMo…), research systems and informal ideas, before they ship as products | [`?product=memory-research`](https://mrpeppersdev.github.io/agent-infrastructure-landscape/?product=memory-research) |
| **Agent Frameworks & Harnesses** | 206 | Agent frameworks, multi-agent orchestration, coding IDEs and harnesses, computer-use and voice agents, sandboxes | [`?product=agents`](https://mrpeppersdev.github.io/agent-infrastructure-landscape/?product=agents) |
| **Retrieval & Data Infrastructure** | 67 | Vector databases, knowledge-graph platforms, embedding/reranker services, search | [`?product=data`](https://mrpeppersdev.github.io/agent-infrastructure-landscape/?product=data) |
| **Models, Serving & Ops** | 109 | Foundation models, inference gateways, training infra, eval/observability, robotics stacks | [`?product=models-ops`](https://mrpeppersdev.github.io/agent-infrastructure-landscape/?product=models-ops) |

The section → family map lives in [`taxonomy/families.json`](./taxonomy/families.json).

**Focused catalogs.** The same dataset is also served one audience at a time at [`/catalogs`](https://mrpeppersdev.github.io/agent-infrastructure-landscape/catalogs): the five families above plus use-case views for coding agents, security and identity, evals and observability, voice and embodied agents, assistant memory and vertical agents. Each shows its rows, the columns that audience scans first and the decision tools that apply; the home table is the Atlas with every row and every column. Defined in [`taxonomy/silos.json`](./taxonomy/silos.json).

## Questions it answers

- *Which memory layer / agent framework / vector database should I use?* → [**/choose**](https://mrpeppersdev.github.io/agent-infrastructure-landscape/choose), [/choose/framework](https://mrpeppersdev.github.io/agent-infrastructure-landscape/choose/framework), [/choose/data](https://mrpeppersdev.github.io/agent-infrastructure-landscape/choose/data): a few questions, three picks with cited reasons, a side-by-side table
- *Do these work together?* → [**/compatibility**](https://mrpeppersdev.github.io/agent-infrastructure-landscape/compatibility): integration evidence for every pair, with sources
- *Is anything in my stack archived, acquired or stale, and what should replace it?* → [**/check**](https://mrpeppersdev.github.io/agent-infrastructure-landscape/check): paste a package.json, requirements.txt, pyproject.toml or MCP config
- *What are the alternatives to Mem0 / Zep / Flowise / Chroma…, and how do I migrate off an archived one?* → [**/alternatives**](https://mrpeppersdev.github.io/agent-infrastructure-landscape/alternatives), with cited migration notes
- *What would Mem0 / Zep / Supermemory cost for my app?* → [**/costs**](https://mrpeppersdev.github.io/agent-infrastructure-landscape/costs), from published list prices
- *Just describe it* → [**/search**](https://mrpeppersdev.github.io/agent-infrastructure-landscape/search): "self-hosted vector db with MCP, python"
- *What changed?* → each system page's change log, [per-system feeds](https://mrpeppersdev.github.io/agent-infrastructure-landscape/data#feeds) and the [JSON/CSV API](https://mrpeppersdev.github.io/agent-infrastructure-landscape/data)
- *Which self-hostable memory layers support MCP and SOC 2?* → [best-of lists](https://mrpeppersdev.github.io/agent-infrastructure-landscape/best/self-hostable-agent-memory)
- *How does each memory system handle contradictions and forgetting?* → the `contradiction`, `forgetting` and `conflict` columns, filterable in the table

## Use it in CI (GitHub Action)

```yaml
- uses: MrPeppersDev/agent-infrastructure-landscape@main
  with:
    fail-on: archived   # none | attention | archived
```

Flags archived, deprecated, acquired or stale AI dependencies in `package.json`, `requirements.txt`, `pyproject.toml` and MCP configs, comments on the PR with replacements, and can write a badge. See [`action/`](./action/README.md).

## Use it from your agent (MCP)

The MCP server exposes the catalog to Claude Code, Claude Desktop, Cursor or any MCP client. It provides 24 read-only tools, including `ask_catalog`, `estimate_memory_cost`, `estimate_vector_store_cost`, `choose_memory_layer`, `choose_framework_or_store`, `check_compatibility`, `find_alternatives`, `check_stack`, `system_history`, `search_records`, `compare`, `find_related`, `find_substrate_risk` and `recent_changes`.

```sh
git clone https://github.com/MrPeppersDev/agent-infrastructure-landscape
cd agent-infrastructure-landscape/mcp && npm install && npm run build
claude mcp add landscape -- node $PWD/dist/server.js
```

A hosted, no-install endpoint is ready in [`worker/`](./worker/README.md) (Cloudflare Workers, 8 tools). A [CLI](./cli/README.md) offers the same queries for scripts (`--json` / `--csv`), including `landscape choose`, `landscape choose-stack framework|data`, `landscape compat <ids…>`, `landscape alternatives <id>` and `landscape check <manifest> --fail-on-attention` for CI.

## What a record looks like

Each record has a stable id, a tier (1 battle-tested → 5 theoretical), its section(s), and **99 attribute cells**. Memory systems also carry a memory taxonomy (storage, retrieval, persistence, update, unit, governance, conflict); the site, exports, API and MCP show it for the memory and memory-research families only. These cover license, deployment, pricing, MCP/A2A support, observability and eval integrations, cost and capability scores, and more. Every cell carries:

- **value**: the claim itself
- **citation**: the URL it came from
- **status**: `real-data`, `estimate`, `not-applicable`, `no-data` or `depth-floor-reached`
- **tier**: T1 (auto-verifiable from GitHub), T2 (resolvable source required) or T3 (estimate)

Full schema: [`docs/SCHEMA.md`](docs/SCHEMA.md). Claims are vendor-stated unless marked otherwise. Many cells are honestly empty, because a voice-agent platform has no `vector-index` and a paper has no `pricing`. The site hides those so they don't clutter the view.

## How it stays fresh

| Bot | Cadence | What it does |
|---|---|---|
| Section audit | weekly | Re-verifies one section and searches for missing systems; opens a draft PR |
| Intake research | on submission | Researches a [submitted system](https://mrpeppersdev.github.io/agent-infrastructure-landscape/submit) across all columns and opens a draft PR |
| External-landscape diff | monthly | Diffs against [Agentic Community](https://github.com/agentic-community/agentic-landscape) and other landscapes and files candidate batches |
| Staleness / release / price watch | daily | Flags abandoned repos, new model releases and vendor price changes |

**How changes land.** Every change goes through a pull request. Nothing is written to `main` directly, and no workflow merges its own output.

The gate is CI:
- the eight `make validate` gates, including the JSON → HTML → JSON round-trip and the enum checks;
- the contradiction lint;
- type-checking;
- the full site build with link and JSON-LD validation;
- a per-page JS budget;
- a browser smoke test;
- the MCP server, worker and Action tests.

Agent sessions working for the maintainer merge their own PRs once CI is green ([`CLAUDE.md`](./CLAUDE.md)). The maintainer reviews after the fact, and the PR history is the audit trail. Bot output (the draft PRs and branches from the audit, intake and correction workflows) is merged only after a maintainer or one of those sessions has checked it against its sources.

The maintenance contract (scope, freshness SLA, succession) is in [`MAINTAINER.md`](./MAINTAINER.md), §"Merge policy".

## Contributing

- **Missing a system?** Use the [submit form](https://mrpeppersdev.github.io/agent-infrastructure-landscape/submit) or open an issue titled `Intake: <name>`.
- **Wrong cell?** Use **Suggest a correction** on the system page: it opens a pre-filled issue and a bot turns it into a PR.
- **Pipeline:** `make build` reconciles the JSON, rebuilds edges and re-renders `landscape.html`. `make validate` runs the offline gates (~25 s). Commit the JSON, the edges file and the HTML together.

Co-maintainers are welcome, especially for a single product family. See [`MAINTAINER.md`](./MAINTAINER.md) §4.

## Repository layout

| Path | What |
|---|---|
| `data/` | The dataset (`landscape.json`, `landscape.edges.json`). Source of truth. |
| `taxonomy/` | Product families, tags, use-case taxonomy |
| `web/` | SvelteKit site; built into `docs/` for GitHub Pages |
| `mcp/`, `cli/` | MCP server and CLI over the dataset |
| `scripts/`, `.github/workflows/` | Pipeline and bots |
| `docs/` | Schema, decisions and findings, plus the built site |
| `analysis.md` | Long-form analysis behind the findings |
| `extraction/`, `audit/`, `.agent-results/` | Pipeline working data, caches and research logs |

## License and credits

Data: **CC-BY-4.0**. MCP server and CLI: **MIT**. The catalog cross-references and, where licensing allows, imports data from the [Agentic Community Landscape](https://github.com/agentic-community/agentic-landscape) (Apache-2.0), the [SylphAI YC Agent Landscape](https://github.com/SylphAI-Inc/yc-agent-landscape) (MIT) and the [AI System Design Guide](https://github.com/ombharatiya/ai-system-design-guide) (MIT). The [InclusionAI Agentic AI Landscape](https://github.com/antgroup/agentic-ai-landscape) is noted as prior art and not imported (no licence). See [`extraction/external/LICENCES.md`](./extraction/external/LICENCES.md).

Maintained by [Brian Sayer](https://www.linkedin.com/in/brian-s-5b8b7914a).
