# Handoff — open work (as of 2026-11-01)

Conventions are in [`../CLAUDE.md`](../CLAUDE.md). Work top to bottom, one PR per item, and merge once CI is green.

## Done on 2026-10-31 and 2026-11-01

- **Data:**
  - [#390](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/390): the duplicate Jamba records merged into Foundation models; Smithery recorded after its 2026-10-31 shutdown.
  - [#393](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/393): three duplicate pairs merged (the two Anthropic computer-use rows, two OpenHands rows, two MetaGPT rows); seven memory-layer cells that inherited a model's benchmark score are placeholders now.
  - [#405](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/405): the open data questions from section 2 (Sinequa, Apex → Tenable, Common Room → Zoom, AlphaSense, Endor, Databricks/MLflow funding, Coalfire links, K-Scale and Toplyne shutdowns), plus Hyperproof AI Trust Center merged into Hyperproof. `apply_reverify.py` no longer writes `decay_cause: archived` for a `dead` lifecycle. Report: `extraction/reverify-2026-11-01/REPORT.md`.
  - [#404](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/404): the external-landscape importer also matches on repo links and bare names ([#391](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/391)); new candidates 927 → 877.
- **Catalog silos (section 8):** MCP, worker and CLI scoping by silo ([#394](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/394)), per-silo change feeds and a depth badge ([#395](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/395)).
- **Stack auditor follow-ups (section 7):** the security-review sheet for a checked stack, and `sheet` on the hosted MCP's `check_stack` and `plan_stack` ([#396](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/396)).
- **Roadmap phase 3:** context pack for coding agents, `context_pack` tool and `landscape context` ([#401](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/401), [#398](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/398)); per-stack "what changed" at `/changes#ids=` and `landscape init` writing a starter project ([#402](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/402), [#397](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/397), [#399](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/399)). The "three doors" home page is not built: it conflicts with the maintainer's decision to keep the Atlas home. Raise it with them before building.
- **Product review items:**
  - Golden stack questions run in CI (`mcp/src/golden-stacks.*`, 20 queries; `--update` re-records them), "Was this pick right?" feedback on `/build` with a `pick-feedback` issue form, a "Who is correcting" field on the correction form for vendors, source badges on compare pages, the home `<h1>`, and the writing style section in CLAUDE.md ([#400](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/400)).
  - Daily bot snapshots in `docs/` keep 30 days; monthly dataset releases tagged `dataset-YYYY-MM`; a public bot status page at `/status` ([#403](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/403)).
  - Cells nobody researched read "not checked"; searched-but-absent cells read "not published" ([#404](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/404)).

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

- **Still open after the 2026-11-01 pass** (`extraction/reverify-2026-11-01/REPORT.md`):
  - linq-ai: linq.ai is an unrelated company now. Re-point the record (probably LinqAlpha) and research it fresh.
  - reggie-ai: parked domain, and nothing in the record matches Regie.ai. Retire or rebuild.
  - Pachyderm: repo not archived (last commit 2025-01-09), site unreachable, no end-of-life notice. Leave as is until one appears.
  - Anvilogic: the Series C date needs the company's own announcement.
  - 11x, Gong, Apollo: no newer primary round found.
  - K-Scale Labs and Toplyne shutdowns are medium confidence (secondary reporting of a founder's statement).
- **Vellum:** shuts down its hosted platform on 2026-11-02. Mark it dead together with Hume EVI at the 2026-11-14 check-in.
- **Hume EVI:** after 2026-11-13, set lifecycle `dead` with decay cause.
- **Schema v1.1.0 (#150 option 1 + #166):** decided 2026-10-28. All four steps are done: the schema and gate 8, the OpenDigger fetcher, the derived backfill with the #166 facets and MCP filters, and the research backfill. Locus is filled on 546 of 695 product rows, positioning on 629, and the YC accelerator on 60 (`extraction/v1.1-backfill/REPORT.md`). Lifecycle leads re-verified 2026-10-29 (`extraction/reverify-2026-10-29/REPORT.md`, retries in `reverify-2026-10-29b/`); open-core estimates reviewed and wrong-section rows handled (`extraction/fixes-2026-10-29/REPORT.md`); 95 more locus/positioning cells filled with a headless browser (`extraction/gaps-2026-10-29/REPORT.md`). Next: (1) mark Hume EVI and Vellum dead after their shutdown dates (2026-11-13, 2026-11-02; a check-in is scheduled for 2026-11-14); (2) the gaps-report leads are done (`extraction/reverify-2026-10-29c/REPORT.md`); still open there: Adept (bot wall) and Cellon (no primary page left, removal candidate); (3) non-YC accelerators backfilled on 50 rows (`extraction/accelerators-2026-10-29/REPORT.md`); Plug and Play and the SPC/Neo/Pear near-misses need a visible primary statement before they count. Anthropic Auto Dream and Pluto AI were removed (`extraction/removals-2026-10-29/`). Locally, svelte-check needs `NODE_OPTIONS=--max-old-space-size=6144`.
- **Blocked:** #128 needs the `ANTHROPIC_API_KEY` repository secret. #129 is wired: the Sunday `capability-rebaseline.yml` runs `scripts/capability_sweep.py` once the secret exists (it prints a notice and skips until then) and commits the staged `data/_baselines/capability-sweep-<date>.json`; merging a staged sweep into `landscape.json` stays a reviewed step (`--merge-into-landscape`). #132 waits on the first real sweep. The benchmark-URL research pass is done: 31 rows cite primary sources (`extraction/benchmark-sources-2026-10-31/REPORT.md`), and the sweep now writes `benchmark-maxima.json` from them (12 benchmarks anchored). The 2026 benchmarks are classified in `docs/benchmark-families.yml` (section "ADDED 2026-11-03", **pending the maintainer's ratification**, the `?` entries in particular: swe-atlas-qna, frontierswe, cybench) and nine model rows now cite their vendors' 2026 flagship pages (`extraction/benchmark-sources-2026-11-03/REPORT.md`, DECISIONS 2026-11-03). OpenAI's row still has no first-party 2026 numbers: openai.com blocks fetchers and the system-card tables are images; a session with a browser could read them. The duplicate merges and the inherited scores were done in [#393](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/393).

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
- ~~**Bot PRs:**~~ the maintainer turned on "Allow GitHub Actions to create and approve pull requests" (reported 2026-11-02). No bot has opened a PR since, so the next correction or intake run is the first real test: it should open a PR instead of posting a compare link (the last compare link was on #299, 2026-10-28).
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

**Follow-ups:** all three done in [#400](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/400) (history refreshed, home `<h1>`, compare-page badges).

## 7. Stack-auditor roadmap, phases 1 and 2 (2026-10-30; status 2026-10-31)

Direction agreed with the maintainer: the product is a stack planner and auditor that lives in the engineer's repo and agent; the catalog table is its evidence.

**Done (one PR each, DECISIONS.md 2026-10-31):** [#359](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/359) fit-first ranking · [#360](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/360) edge verification stamps · [#362](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/362) cost range and switching cost · [#363](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/363) stack audit · [#364](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/364) version drift · [#365](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/365) maintainer health (the daily `repo-health.yml` bot fills `data/repo-health.json`; until it has run, every surface says "no health data") · [#366](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/366) security-review sheet.

**Needs the maintainer:** [#358](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/358) add `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` and run **Deploy MCP worker**; add `NPM_TOKEN` and run **Publish MCP server** (`.github/workflows/publish-mcp.yml`, also fires on `data-v*` tags; the MCP Registry step signs in with GitHub OIDC and needs no secret) · [#361](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/361) add `OPENAI_API_KEY` (plus the optional hosted-system keys) and run **Memory benchmark** once · #128 / #132 wait on `ANTHROPIC_API_KEY` (see Blocked above). Intake #194 / #299 (Ghost Beacon, GBR-2500) was done in PR #386 under the rule that user submissions are added and described honestly: tier 4, dated first/last commit, no stars, self-reported figures marked unverifiable.

**Follow-ups filed in DECISIONS:** `verified_version` on edges is empty until hub pages are re-verified with versions (then #364 can flag "integration verified on a different major"); the `/check` sheet and the worker's `sheet` option shipped in [#396](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/396).

## 8. Catalog silos (2026-10-31)

Shipped: `taxonomy/silos.json`, `/catalogs`, `/catalogs/<silo>`, `/catalogs/<silo>/browse`, the Catalogs nav group, per-silo exports and the llms.txt section (DECISIONS.md, 2026-10-31). Follow-ups, in order:

1. ~~MCP and CLI silo scoping~~ done in [#394](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/394): `--silo` / `LANDSCAPE_SILO` on the stdio server, `/mcp/<silo>` on the worker, `landscape --silo` and `landscape silos` in the CLI.
2. ~~Per-silo feeds~~ done in [#395](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/395): `feeds/catalogs/<silo>.xml`.
3. **Silo-aware choosers:** not built. The landing-page tiles already deep-link into `/choose` and `/build` with `?product=`, which covers the case. Revisit only if users ask for a scoped candidate pool.
4. ~~Depth badge~~ done in [#395](https://github.com/MrPeppersDev/agent-infrastructure-landscape/pull/395): Full (≥ 80% of the silo's columns filled), Standard (≥ 50%) or Listed, shown after the lifecycle column. Not yet used as a chooser tiebreaker.
5. **Design pass per silo**: the memory table and the models table want different densities; review `columns` in silos.json with real users.

## 9. Other open items

- **Integration versions:** `verified_version` on edges stays empty until hub pages are re-verified with versions (follow-up to [#360](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/360)).
- **Benchmarks:** ratify the "ADDED 2026-11-03" section of `docs/benchmark-families.yml` (three `?` entries need a call), and get OpenAI's 2026 numbers from its system cards with a browser session (section 2, Blocked).
- **Self-hosted plan:** the self-hosted blueprint picks Gemini as its model, which is a hosted API. The model rows need a self-hostable signal the composer can filter on.
- **Ideas from the product review that need the maintainer:** a citable DOI for the dataset (Zenodo), a real name and domain, user sessions to watch people pick a stack, and outreach (section 4).
- **Parallel sessions:** another session works on this repo too. Check open PRs and recent merges on `main` before starting an item. It has force-pushed its own branch before, so don't build on its branches.
