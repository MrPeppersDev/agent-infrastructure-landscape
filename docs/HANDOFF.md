# Handoff — open work (as of 2026-10-28)

Conventions are in [`../CLAUDE.md`](../CLAUDE.md). Work top to bottom, one PR per item, and merge once CI is green.

## Done since the last handoff (2026-10-27)

- **October re-verification:** all 177 rows in `extraction/reverify-2026-10c/todo.json` are verified. That's frameworks #270, models-a #271, models-b #272, harnesses #273 and data #274; findings are in `extraction/reverify-2026-10c/REPORT.md`. Every lead from the last handoff was checked on primary sources.
  - **Confirmed:** Cursor's acquisition by SpaceX (2026-08-14), Windsurf becoming Devin Desktop, Manus joining Meta and then going independent again, Operator redirecting to ChatGPT agent, Humanloop shutting down, W&B going to CoreWeave, Replicate going to Cloudflare, Scale's Meta deal date (2025-06), MCP moving to the Linux Foundation, and the Marvin/ControlFlow merge direction.
  - **Refuted:** Covariant was not acquired. Amazon took a license and hired the founders.
- **Duplicate rows merged:** #275 took the catalog from 964 to 952 records. Removed ids redirect via `taxonomy/system-aliases.json` → `redirects`. Use `scripts/merge_records.py` for future merges.
- **Costs:** #284 added a vector-store tab with Pinecone, Turbopuffer, Weaviate and Zilliz, plus Qdrant and LanceDB marked "not published". It also added Honcho. Memobase publishes no prices, so it isn't included.
- **Correction bot:** tested in #285. It parses the issue form, patches one cell and falls back to a compare link because Actions can't open PRs (see item 3).
- **Issue triage (#290):** release-watch and stale-row issues closed; the staleness bot now skips papers and rows whose lifecycle is already recorded, and the capability re-baseline closes the previous tracking issue.
- **Small data fixes (#291):** moved repo URLs (Ragas, verl, LLaMA-Factory, torchtune, DeepSpeed) and the Cohere Embed 5 description.
- **Vector-cost MCP tool (#292):** `estimate_vector_store_cost` in the stdio server (24 tools) and the worker (9 tools); `mcp/server.json` is ready for the MCP Registry.
- **Oldest-row re-verification (this PR):** 285 of the 298 rows last verified before 2026-07-01 are done; see `extraction/reverify-2026-10-28/REPORT.md`. It found 10 acquisitions (including Promptfoo → OpenAI and Calypso AI → F5), 5 renames, Hume EVI's shutdown on 2026-11-13, and corrected Genie AI, Cleric and Strands.
- **Svelte-check:** #286 fixed the 0-error baseline, and the Type-check step now blocks PRs.

## 1. Finish the 13 unverified old rows

Listed at the end of `extraction/reverify-2026-10-28/REPORT.md`: five OpenReview papers (scripts get a challenge page; try a browser or the paper's arXiv version), four repos GitHub search can't find (ARMT, NLE, NIAH, osrs-bench: find where they moved), and four unreachable sites (MDPI, minerl.io, heypluto.ai, robustintelligence.com).

## 2. Open data questions

- **Primary sources still needed:** Sinequa's acquisition date (ChapsVision), Apex Security's deal closing (Tenable), Common Room → Zoom (only the CEO's post), funding for AlphaSense, 11x, Gong, Apollo, Endor and Anvilogic, and K-Scale Labs / Vellum lifecycle.
- **Rows that may need re-pointing or removal:** linq-ai (linq.ai is now an unrelated company; maybe LinqAlpha), reggie-ai (parked domain; maybe Regie.ai), toplyne (dead site), and the Coalfire AIOps and Hyperproof Trust Center product pages (404).
- **Pachyderm:** pachyderm.com still doesn't respond; the repo isn't archived.
- **Hume EVI:** after 2026-11-13, set lifecycle `dead` with decay cause.
- **Schema v1.1.0 (#150 option 1 + #166):** decided 2026-10-28. All four steps are done: the schema and gate 8, the OpenDigger fetcher, the derived backfill with the #166 facets and MCP filters, and the research backfill. Locus is filled on 546 of 695 product rows, positioning on 629, and the YC accelerator on 60 (`extraction/v1.1-backfill/REPORT.md`). Lifecycle leads re-verified 2026-10-29 (`extraction/reverify-2026-10-29/REPORT.md`, retries in `reverify-2026-10-29b/`); open-core estimates reviewed and wrong-section rows handled (`extraction/fixes-2026-10-29/REPORT.md`); 95 more locus/positioning cells filled with a headless browser (`extraction/gaps-2026-10-29/REPORT.md`). Next: (1) mark Hume EVI and Vellum dead after their shutdown dates (2026-11-13, 2026-11-02; a check-in is scheduled for 2026-11-14); (2) the gaps-report leads are done (`extraction/reverify-2026-10-29c/REPORT.md`); still open there: Adept (bot wall) and Cellon (no primary page left, removal candidate); (3) non-YC accelerators backfilled on 50 rows (`extraction/accelerators-2026-10-29/REPORT.md`); Plug and Play and the SPC/Neo/Pear near-misses need a visible primary statement before they count. Anthropic Auto Dream and Pluto AI were removed (`extraction/removals-2026-10-29/`). Locally, svelte-check needs `NODE_OPTIONS=--max-old-space-size=6144`.
- **Blocked:** #128 needs `ANTHROPIC_API_KEY`, and #129 / #132 wait on #128.

- **Stack builder program (2026-10-29, maintainer-approved):** the whole-stack composer is live: `/build`, MCP `plan_stack`, CLI `landscape stack` and `stack.yml` checking (DECISIONS.md, 2026-10-29). Still in progress, in order:
  1. ~~Integration edges~~ done: 1,396 edges from 53 hubs' official integration pages (`extraction/integrations/REPORT.md`). Add a hub by dropping another JSON file there.
  2. New sections plus intake for guardrails, agent identity and auth, MCP gateways and registries, and durable execution.
  3. ~~Buyer cells~~ schema v1.2.0 shipped and backfilled on 435 composer rows, 888 cells (`extraction/buyer-cells-2026-10-29/REPORT.md`). That report also lists lifecycle leads.
  4. Whole-stack pricing.
  5. Reference blueprints and scaffolds.
  6. Per-stack feed and "we use this stack" submissions.

## 3. Things that need the maintainer

These need a human. List them back to the maintainer, with links, if they're still open.
- **Hosted MCP:** add the repo secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, then run **Deploy MCP worker** (see `worker/README.md`). Once it's live, add the endpoint URL to `README.md`, `/data`, `llms.txt` (`web/scripts/generate-exports.mjs`) and `mcp/README.md`.
- **Benchmark:** add the repo secret `OPENAI_API_KEY`, then run the **Memory benchmark** workflow. Results land on a `bench/results-<run>` branch; a PR from it publishes [/benchmarks](https://mrpeppersdev.github.io/agent-infrastructure-landscape/benchmarks).
- **Bot PRs:** Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests". Until then the correction and intake bots post a compare link (confirmed in #285).
- **npm + MCP Registry:** `cd mcp && npm publish` (landscape-mcp 1.0.1, needs their npm login), then `mcp-publisher login github` and `mcp-publisher publish` (reads `mcp/server.json`; see `mcp/README.md`).
- **Housekeeping:**
  - Close spam issues #194 and #175.
  - Delete the merged branches: `feat/*`, `fix/*`, `data/*`, `intake-batch/*`, `ci/*`, `intake/*`, `capability-incremental/*`, `claude/fervent-wozniak-7hdul3` and `correction/285-trl-hugging-face--gh-huggingface-trl`.

## 4. Outreach (only with the maintainer's go-ahead)

These publish outside this repo under the maintainer's name, so ask first.
- Listing PRs to Agent-Memory-Paper-List, the awesome-* lists and the MCP Registry.
- GitHub Marketplace for the Action, which needs a release tag `v1`.
- A write-up of the contradiction and lifecycle findings. The October re-verification report is a good source.

## 5. Smaller follow-ups

- **Costs:** re-check Qdrant and LanceDB if they start publishing unit rates, and Turbopuffer's data-returned rate.
