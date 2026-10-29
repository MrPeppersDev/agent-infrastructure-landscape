# Retry of unverified rows and new leads — 2026-10-29 (b)

Targets: 23 rows. Some were left unverified by the 2026-10-28 and 2026-10-29 passes; others are new leads found during the open-core review. 18 are now verified, with 30 cell updates and 4 URL moves. Applied with `apply_reverify.py --date 2026-10-29`; the per-row output is in `apply-report.md`.

## Lifecycle and fact changes

- **Langfuse → acquired by ClickHouse** (2026-01-16). [ClickHouse](https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability)
- **Soul Machines:** receivers (KPMG) were appointed on 2026-02-05, per NZ Gazette notice 2026-ar623. No liquidation notice was found, so lifecycle stays `unknown`.
- **Krutrim Kruti:** Ola's own page says it is "under maintenance… will be back shortly". The "shut down" wording came only from press reports, so it is removed and lifecycle is `unknown`.
- **Steamship:** the old `archived` status is not supported, because the repo shows no archive banner. The site returns 404, so lifecycle is `unknown`.
- **Covariant:** the site is now a placeholder. Lifecycle `unknown`.
- **Memobase:** the repo is live, but the cloud service (memobase.io) is down. Lifecycle is `unknown` and the pricing cell notes the outage.
- **OpenMemory → LongMemory:** the rename is confirmed in the repo README.
- **OpenAI Deep Research:** `active`, per developers.openai.com.

## URL moves
- **MemoraX AI:** now the company's own site, memoraxai.com. Its terms name the Shenzhen operator. The gh, license and latest-release cells now describe MemoraX Code: MIT, npm 0.1.21.
- **Grok Memory:** now xAI's official @grok announcement (2025-04-17). Pricing comes from docs.x.ai.
- **LazyGraphRAG:** now the Microsoft Research post. Its 2025-06-06 editor's note says LazyGraphRAG ships inside Microsoft Discovery and Azure Local, not in the open-source GraphRAG library.
- **Krutrim Kruti:** now olakrutrim.com/kruti.

## Licence and pricing fixes
- **Jina v4:** Qwen Research License. The model card says the earlier CC-BY-NC label was an error.
- **Mistral:**
  - Large 2 (2407 and 2411) is under the Mistral Research License.
  - Codestral 22B is under the Mistral Non-Production License.
- **claude-mem:** CMEM Pro costs $30, $70 or $100 a month.
- **Logseq:** Sync beta goes to $5/$15-a-month Open Collective backers, per Logseq's own blog.
- **Daytona:** the archived repo is AGPL-3.0, at v0.190.0.
- **Letta and Sleep-time Compute:**
  - Both rows: gh now points to letta-ai/letta-code (Apache-2.0), and latest-release is npm v0.34.30.
  - Sleep-time row only: sleep-time compute is now called "dreaming".

## Still unverified (5)
- **Anthropic Auto Dream:** no primary source. "dream" appears in neither the Claude Code CHANGELOG nor the docs. It is a candidate for removal; the maintainer decides.
- **Pluto AI:** heypluto.ai is not registered (NXDOMAIN). The row is tagged wrong-section, so it is a removal candidate.
- **Toplyne:** the domain shows a Wix "not connected" page. Only press reports say it shut down.
- **K-Scale Labs:** kscale.dev's DNS no longer answers. Only press reports say it shut down, and one repo was still pushed on 2026-10-17.
- **Tesla FSD:** tesla.com blocks scripts. The shareholder deck confirms "end-to-end neural networks", not the occupancy or 4D world-model claim.
