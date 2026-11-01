# Handoff — open work (as of 2026-10-29, evening)

Conventions are in [`../CLAUDE.md`](../CLAUDE.md). Work top to bottom, one PR per item, and merge once CI is green.

## Done on 2026-10-29 (second half)

- **Stack builder, data-quality round:**
  - Lifecycle leads round 7 (#338): Tabnine → Tricentis, Windsurf → Devin Desktop, Codex `mcp-server` removed.
  - 22 more production write-ups and 156 hub edges (#339).
  - Cost engine (#340): graduated tiers (Helicone), gateway fees (OpenRouter 5.5%), embedding prices, plus Together and Fireworks model prices.
  - Upgrade advisor (#320): stack-check ranks replacements by documented fit with the rest of the stack.
- **Stack-layers intake (#347):** 57 systems in four new sections: Guardrails & AI security, Agent identity & auth, MCP gateways & registries, Durable execution & workflow engines. Plus gateways, evals and agent benchmarks. Catalog: 1,005 systems.
  - Follow-ups:
    - Lifecycle for six acquisitions (#348).
    - 139 buyer cells (#349).
    - 445 integration edges (#351, `extraction/integrations/2026-10-29-hubs-d.json`).
  - The blueprints' guardrails layer now picks NeMo Guardrails.
- **Site review, all nine bugs fixed** (#321–#329):
  - Live counts (#341).
  - Funding board (#342).
  - Best-of family scope (#343).
  - No page ships the catalog chunk: #344, #345, #346. `web/scripts/check-route-weight.mjs` enforces 3 MB of JS per page.
  - Timeline range (#350).
  - Merge policy docs (#352).
  - Stars in prose: lint `stars-in-prose`, 173 cells fixed (#353).
  - Edge excerpts: lint `edge-midword` (#354).
  - UI fixes (#355).
- **Leads found along the way, not yet fixed:**
  - MLflow's funding cell says "Databricks raised $43.2B", but Databricks' own row says $20.2B total. Re-verify both.
  - Smithery's connection services shut down 2026-10-31 (row already `acquired`; the stack index shows it dead).
  - Toplyne's shutdown is still secondary-only.
  - Okta's trust portal blocks scripts, so the XAA buyer cells are empty.
  - Cohere Embed no longer publishes self-serve per-token prices.

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
- **Blocked:** #128 needs the `ANTHROPIC_API_KEY` repository secret. #129 is wired: the Sunday `capability-rebaseline.yml` runs `scripts/capability_sweep.py` once the secret exists (it prints a notice and skips until then) and commits the staged `data/_baselines/capability-sweep-<date>.json`; merging a staged sweep into `landscape.json` stays a reviewed step (`--merge-into-landscape`). #132 waits on the first real sweep. The benchmark-URL research pass is done: 31 rows cite primary sources (`extraction/benchmark-sources-2026-10-31/REPORT.md`), and the sweep now writes `benchmark-maxima.json` from them (12 benchmarks anchored). Still open before #132: (1) add the benchmarks the 2026 flagships actually report (Terminal-Bench 4.0, DeepSWE, SWE-bench Pro, FrontierCode, OSWorld 2.x, AutomationBench, MRCR, GraphWalks) to `docs/benchmark-families.yml`, then re-run the research pass on the model rows; (2) merge the duplicate pairs the pass surfaced (two Anthropic computer-use rows, two OpenHands rows, two MetaGPT rows); (3) turn the memory-layer cells that "inherit" a model's SWE-bench score into placeholders so they do not score.

- **Stack builder program (2026-10-29, maintainer-approved):** the whole-stack composer is live: `/build`, MCP `plan_stack`, CLI `landscape stack` and `stack.yml` checking (DECISIONS.md, 2026-10-29). Still in progress, in order:
  1. ~~Integration edges~~ done: 1,396 edges from 53 hubs' official integration pages (`extraction/integrations/REPORT.md`). Add a hub by dropping another JSON file there.
  2. ~~New sections plus intake~~ done (#347–#351, see above).
  3. ~~Buyer cells~~ schema v1.2.0 shipped and backfilled on 435 composer rows, 888 cells (`extraction/buyer-cells-2026-10-29/REPORT.md`). That report also lists lifecycle leads.
  4. ~~Whole-stack pricing~~ done: 20 model prices and 25 metered services (`extraction/pricing-2026-10-29/REPORT.md`). Re-check Gemini on 2026-12-01 and Cartesia after 2026-12-31.
  5. ~~Reference blueprints~~ done: `blueprints/`, regenerated by `make blueprints`. Add production write-ups to `data/blueprints/evidence.json` as they appear, for example from stack reports.
  6. ~~Per-stack feed and stack reports~~ done: OPML watch and the `stack-report` issue template. Memory benchmark runs need API keys for the hosted memory services; ask the maintainer.

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

## 6. Site review follow-ups (2026-10-29)

A fresh-eyes review of the live site and dataset filed one issue per finding. All sixteen are closed.

**Fixed:** [#321](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/321) derive the catalog counts (912 / 523 / 528 are stale) · [#322](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/322) funding leaderboard parses market caps · [#323](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/323) best-of lists ignore the family · [#324](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/324) eight routes ship a 21 MB client chunk · [#325](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/325) timeline opens on 1984 · [#326](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/326) claims cell contradicts the gh cell · [#327](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/327) truncated edge excerpts · [#328](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/328) five small UI bugs · [#329](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/329) README merge policy vs CLAUDE.md.

**Product changes, done 2026-10-30:**
- [#330](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/330) identity. The maintainer chose "AI agent stack analysis tool" (`docs/DECISIONS.md`). Copy changed in [#357](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/357). In [#368](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/368) the memory taxonomy shows on memory and memory-research rows only, everywhere including the exports and MCP.
- [#331](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/331) → [#369](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/369): compact one-line table (`?view=full` for every column), Status column, Lifecycle facet (`?lifecycle=`), lifecycle banner on system pages, "data as of … (N re-verified that month)". The table remounts after hydration so URL-filtered views render correctly; smoke tests wait for `main.table-shell[data-hydrated]`.
- [#332](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/332) → [#370](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/370): nav in four groups (Decide / Browse / Research / Data) with a Menu button under 768 px. `/recommend/*` redirects to `/choose`. The sitemap skips redirect stubs.
- [#333](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/333) → [#371](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/371): source class per citation (`web/src/lib/source-class.js`: vendor / repo / registry / paper / third-party / catalog). It drives badges, a third-party count per system, a Sources list on system pages, a leaderboard, and `source_class` in the API. Vendor detection is a heuristic: the record's domain, its name, its GitHub org, plus an alias list for vendors with several domains (Anthropic, OpenAI, Google, Microsoft, Amazon, Meta, xAI). Extend `ALIASES` when a vendor's own docs show up as third-party.
- [#334](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/334) → [#372](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/372): columns under 15% filled are opt-in (`?sparse=1`); empty columns are dropped from the exports; fill rates are at `/data#fill-rates` and `/api/fill-rates.json`.
- [#335](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/335) → [#373](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/373): search shows every match, 25 at a time; phones get a card list instead of the table.
- [#336](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/336) → [#374](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/374): `/changes`, a weekly "What changed" page from `data/history.json` and the stack index.
- Data fix found along the way, [#375](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/375): 59 `code-release` cells cited `https://no data - …`. They are now `depth-floor-reached` with the paper as citation. A new lint rule, `bad-citation`, catches this.

**Follow-ups:**
- The committed `data/history.json` was last built on 2026-10-23. `pages.yml` rebuilds it on every deploy, so the live `/changes` and change logs are current, but local and PR builds show older history. Run `make history` and commit it when convenient.
- The home page `<h1>` still reads "AI Agent Infrastructure Landscape"; the brand in the nav is "AI Agent Stack".
- Compare pages show values without citations, so they have no source badges.

## 7. Stack-auditor roadmap, phases 1 and 2 (2026-10-30; status 2026-10-31)

Direction agreed with the maintainer: the product is a stack planner and auditor that lives in the engineer's repo and agent; the catalog table is its evidence.

**Done (one PR each, DECISIONS.md 2026-10-31):** [#359](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/359) fit-first ranking · [#360](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/360) edge verification stamps · [#362](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/362) cost range and switching cost · [#363](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/363) stack audit · [#364](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/364) version drift · [#365](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/365) maintainer health (the daily `repo-health.yml` bot fills `data/repo-health.json`; until it has run, every surface says "no health data") · [#366](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/366) security-review sheet.

**Needs the maintainer:** [#358](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/358) add `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` and run **Deploy MCP worker**; add `NPM_TOKEN` and run **Publish MCP server** (`.github/workflows/publish-mcp.yml`, also fires on `data-v*` tags; the MCP Registry step signs in with GitHub OIDC and needs no secret) · [#361](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/361) add `OPENAI_API_KEY` (plus the optional hosted-system keys) and run **Memory benchmark** once · #128 / #132 wait on `ANTHROPIC_API_KEY` (see Blocked above). Intake #194 / #299 (Ghost Beacon, GBR-2500) was done in PR #386 under the rule that user submissions are added and described honestly: tier 4, dated first/last commit, no stars, self-reported figures marked unverifiable.

**Follow-ups filed in DECISIONS:** `verified_version` on edges is empty until hub pages are re-verified with versions (then #364 can flag "integration verified on a different major"); the security-review sheet for an audited `/check` stack needs the buyer cells in the browser; the MCP worker does not yet expose `sheet` or the audit.

## 8. Catalog silos (2026-10-31)

Shipped: `taxonomy/silos.json`, `/catalogs`, `/catalogs/<silo>`, `/catalogs/<silo>/browse`, the Catalogs nav group, per-silo exports and the llms.txt section (DECISIONS.md, 2026-10-31). Follow-ups, in order:

1. **MCP and CLI silo scoping.** `--silo <id>` on the stdio server and worker path per silo so an agent configured for one job sees that silo's tools (`mcpTools` in silos.json) and `search_records` / `ask_catalog` default to its sections. CLI: `landscape --silo coding search …`.
2. **Per-silo feeds and OG images.** `feeds/catalogs/<silo>.xml` from the same change events the landing page shows; the OG generator already emits one SVG per route.
3. **Silo-aware choosers.** `/choose` and `/build` accept `?silo=` to preselect the matching product preset and scope the candidate pool; the landing-page tiles then deep-link with it.
4. **Depth badge.** Fill rate within the silo's columns → full / standard / listed per record, shown in the browse table and preferred as a tiebreaker in the choosers (never an exclusion).
5. **Design pass per silo**: the memory table and the models table want different densities; review `columns` in silos.json with real users.
