# Handoff — open work (as of 2026-10-27)

This picks up from a long chat session that shipped PRs #253–#260. Those added the new nav, corrections bot, change history and feeds, JSON/CSV API, framework and data choosers, compatibility check, 5-way compare, migration notes, GitHub Action, hosted MCP worker, plain-language search, cost calculator, benchmarks page, browser smoke test, a 119-row re-verification and 9 new frameworks. Conventions are in [`../CLAUDE.md`](../CLAUDE.md).

Work top to bottom. Each item is one PR. Merge once CI is green.

## 1. Finish the October re-verification (177 rows) — highest value

The October pass ran out of search budget. The rows it couldn't verify are listed, with their current values, in [`extraction/reverify-2026-10c/todo.json`](../extraction/reverify-2026-10c/todo.json):

| Group | Rows |
|---|---|
| frameworks | 42 |
| models-a | 45 |
| models-b | 46 |
| data | 28 |
| harnesses | 16 |

**Start with the frameworks group.** Its stale rows (LangGraph, LangChain, Mastra, CrewAI Enterprise, Vercel AI SDK, OpenAI Agents SDK, Pydantic-AI, smolagents, Strands…) currently rank below freshly verified ones such as Burr in [/choose/framework](https://mrpeppersdev.github.io/agent-infrastructure-landscape/choose/framework).

- Check each row against primary sources: the GitHub repo page, PyPI or npm, official docs, the pricing page and press releases. Prefer WebFetch on known URLs over web search, and run at most 1–2 research agents per turn (see the fan-out lesson in CLAUDE.md).
- Cells to check:
  - `license`: SPDX-style.
  - `deployment`: starts with "Both (self-hosted + managed cloud)", "Self-hosted only" or "Managed-only".
  - `latest-release`: "vX.Y.Z (YYYY-MM-DD)".
  - `gh`: "owner/repo — ~N stars, last commit YYYY-MM".
  - `mcp-support`: "yes — …" or "no".
  - `runtimes`: SDK languages. **This one matters for the chooser's language filter.**
  - `pricing` and `funding`: only when something changed.
- Write results to `extraction/reverify-2026-10c/result-<group>.json`, using the format in CLAUDE.md. Then apply them, run `make build validate lint`, and open a PR with a REPORT.md.
- Leads from the last pass. These are unverified, so confirm each one before applying it:
  - **Cursor:** may have been acquired by SpaceX in June 2026. The only source so far is The New Stack, 2026-06-22.
  - **Windsurf:** may now be Cognition's "Devin Desktop".
  - **Manus:** possibly Meta-owned.
  - **OpenAI Operator:** may have been folded into ChatGPT agent.
  - **Humanloop:** possibly shut down, with the team joining Anthropic in 2025.
  - **Covariant:** founders reportedly went to Amazon in 2024.
  - **Weights & Biases:** acquired by CoreWeave?
  - **Replicate:** acquisition by Cloudflare announced 2025-11?
  - **Scale AI:** Meta's investment was 2025-06, not 2024-06.
  - **MCP spec:** donated to the Linux Foundation's Agentic AI Foundation, 2025-12?
  - **Marvin / ControlFlow:** the merge direction is probably reversed in the description.
  - **OpenAI Realtime API:** pricing is the 2024 launch rates.
- Add migration notes in `data/migrations.json` for any newly archived or acquired system. Use official steps only; they appear on `/alternatives/<id>` and in MCP `find_alternatives`.

## 2. Merge duplicate rows

The Data pass found products that have more than one record. Each set should become one record, with the others' names moved to aliases and edges re-pointed. Ids must stay resolvable: keep the oldest id, and add a redirect or alias for the others if any external links depend on them.

- **Vector and search engines:**
  - Qdrant / Qdrant Cloud
  - Weaviate / Weaviate Cloud
  - pgvector / PostgreSQL pgvector
  - Vespa / Vespa Cloud
  - Milvus / Zilliz Cloud
  - Meilisearch / Meilisearch (Cloud)
  - Algolia / Algolia (NeuralSearch)
  - Elastic Cloud / Elasticsearch / OpenSearch / OpenSearch (AWS). Here the fix is to split Elasticsearch from OpenSearch and merge the Cloud rows into them.
- **Knowledge graph:** Ontotext GraphDB / Graphwise / PoolParty (now Graphwise).
- **Agents:**
  - Phidata (now Agno) / Phidata / Agno
  - the two Burr (DAGWorks) rows
  - Continue.dev (framework) / Continue.dev (harness)

The choosers already dedupe by brand and repo, so this cleanup is for the catalog, compare pages and counts.

## 3. Things that need the maintainer

These need a human. List them back to the maintainer, with links, if they're still open.

- **Hosted MCP:** add the repo secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, then run **Deploy MCP worker** (see `worker/README.md`). Once it's live, add the endpoint URL to `README.md`, `/data`, `llms.txt` (`web/scripts/generate-exports.mjs`) and `mcp/README.md`.
- **Benchmark:** add the repo secret `OPENAI_API_KEY`, then run the **Memory benchmark** workflow. Results land on a `bench/results-<run>` branch, and a PR from it publishes [/benchmarks](https://mrpeppersdev.github.io/agent-infrastructure-landscape/benchmarks).
- **Bot PRs:** Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests". Until then the correction and intake bots post a compare link instead of opening a PR.
- **npm:** `cd mcp && npm publish` (package `landscape-mcp`), which needs their npm login.
- **Housekeeping:**
  - Close spam issues #194 and #175.
  - Triage the 6 product stale-row issues.
  - Delete the merged branches: `feat/*`, `fix/*`, `data/reverify-2026-10b`, `intake-batch/*`, `ci/*` and `intake/*`. This includes `intake-batch/2026-10-frameworks`, which was superseded by `-b`.

## 4. Smaller follow-ups

- **Costs:** [/costs](https://mrpeppersdev.github.io/agent-infrastructure-landscape/costs) covers 5 vendors. Add Pinecone, Turbopuffer, Qdrant Cloud, Weaviate Cloud, Zilliz and LanceDB Cloud (these are vector stores, so add a separate model or tab), plus Honcho and Memobase. Use published unit prices only, and add a `checked` date. The pricing pages for Pinecone and Turbopuffer were read on 2026-10-26: Pinecone publishes plan minimums but not unit prices; Turbopuffer publishes calculator rates.
- **Correction bot:** it hasn't run on a real issue yet. Open one test correction issue on a harmless field, confirm the bot posts a PR or a compare link, then close it without merging.
- **Svelte-check:** 3 pre-existing type errors in `web/src/routes/analyses/{observability,eval-gap,cost-economics}`, all the same `'all'` index issue. Fix them and make the Type-check step in `web-check.yml` blocking.
- **Outreach:** listing PRs to Agent-Memory-Paper-List, the awesome-* lists and the MCP Registry; GitHub Marketplace for the Action (it needs a release tag `v1`); and a write-up of the contradiction and lifecycle findings.
