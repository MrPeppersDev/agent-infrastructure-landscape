# Handoff — open work (as of 2026-10-28)

Conventions are in [`../CLAUDE.md`](../CLAUDE.md). Work top to bottom, one PR per item, and merge once CI is green.

## Done since the last handoff (2026-10-27)

- **October re-verification:** all 177 rows in `extraction/reverify-2026-10c/todo.json` are verified. That's frameworks #270, models-a #271, models-b #272, harnesses #273 and data #274; findings are in `extraction/reverify-2026-10c/REPORT.md`. Every lead from the last handoff was checked on primary sources.
  - **Confirmed:** Cursor's acquisition by SpaceX (2026-08-14), Windsurf becoming Devin Desktop, Manus joining Meta and then going independent again, Operator redirecting to ChatGPT agent, Humanloop shutting down, W&B going to CoreWeave, Replicate going to Cloudflare, Scale's Meta deal date (2025-06), MCP moving to the Linux Foundation, and the Marvin/ControlFlow merge direction.
  - **Refuted:** Covariant was not acquired. Amazon took a license and hired the founders.
- **Duplicate rows merged:** #275 took the catalog from 964 to 952 records. Removed ids redirect via `taxonomy/system-aliases.json` → `redirects`. Use `scripts/merge_records.py` for future merges.
- **Costs:** #284 added a vector-store tab with Pinecone, Turbopuffer, Weaviate and Zilliz, plus Qdrant and LanceDB marked "not published". It also added Honcho. Memobase publishes no prices, so it isn't included.
- **Correction bot:** tested in #285. It parses the issue form, patches one cell and falls back to a compare link because Actions can't open PRs (see item 3).
- **Svelte-check:** #286 fixed the 0-error baseline, and the Type-check step now blocks PRs.

## 1. Triage open intake and stale-row issues

- **Release-watch intake:** #266, #267 and #268 cover OpenAI's GPT-6.1 Terra and Sol. Update the OpenAI model-family rows where these change a cell, then close the issues. Older release-watch issues #220, #221 and #246 look off-topic (game streaming, a forum tool): close them if so.
- **Stale rows:** 11 issues are open: #226, #229, #235, #236, #242, #243, and #261 to #265. Check each repo; update the row (lifecycle, gh, latest-release) or add a decay cause, then close the issue. #242 (Bonito) is already marked maintenance in #271.

## 2. Re-verify the next oldest rows

The October pass covered only the 177 rows it had stalled on. Use each row's own `last_verified_at` to pick targets. On 2026-10-28, 298 rows were last verified before 2026-07-01: 203 memory-research, 87 agents and 8 memory. Don't use gate 6 of `make validate`: it ages cells against a fixed date (2026-05-14) and reports everything as fresh.
- **Order:** agents first, because they feed the choosers. Then memory. Research papers last; they mostly need only a lifecycle check.
- **Inputs:** collect a PyPI/npm snapshot first; the registries are reachable from the shell. Use the same result format and `apply_reverify.py`, with one PR per group.
- **Agents:** run 1–2 per turn and have them use WebFetch on known URLs. GitHub stars, `pushed_at` and archived status come from the GitHub MCP `search_repositories` tool, because `gh api` is blocked for other repos.
- **Leftovers from the October pass:** these were left unverified.
  - Funding cells for most vendors.
  - Sinequa's acquisition date.
  - Galileo's acquisition date.
  - Pachyderm's status (its site was unreachable).
  - The Strands description claim.
  - K-Scale Labs and Vellum, marked `unknown`; they need a primary source.

## 3. Things that need the maintainer

These need a human. List them back to the maintainer, with links, if they're still open.
- **Hosted MCP:** add the repo secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, then run **Deploy MCP worker** (see `worker/README.md`). Once it's live, add the endpoint URL to `README.md`, `/data`, `llms.txt` (`web/scripts/generate-exports.mjs`) and `mcp/README.md`.
- **Benchmark:** add the repo secret `OPENAI_API_KEY`, then run the **Memory benchmark** workflow. Results land on a `bench/results-<run>` branch; a PR from it publishes [/benchmarks](https://mrpeppersdev.github.io/agent-infrastructure-landscape/benchmarks).
- **Bot PRs:** Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests". Until then the correction and intake bots post a compare link (confirmed in #285).
- **npm:** `cd mcp && npm publish` (package `landscape-mcp`), which needs their npm login.
- **Housekeeping:**
  - Close spam issues #194 and #175.
  - Delete the merged branches: `feat/*`, `fix/*`, `data/*`, `intake-batch/*`, `ci/*`, `intake/*`, `capability-incremental/*`, `claude/fervent-wozniak-7hdul3` and `correction/285-trl-hugging-face--gh-huggingface-trl`.

## 4. Outreach (only with the maintainer's go-ahead)

These publish outside this repo under the maintainer's name, so ask first.
- Listing PRs to Agent-Memory-Paper-List, the awesome-* lists and the MCP Registry.
- GitHub Marketplace for the Action, which needs a release tag `v1`.
- A write-up of the contradiction and lifecycle findings. The October re-verification report is a good source.

## 5. Smaller follow-ups

- **Costs:**
  - Add an MCP tool for vector-store costs (`mcp/src/vector-costs.ts` already exists; the stdio server and the worker only expose `estimate_memory_cost`).
  - Re-check Qdrant and LanceDB if they start publishing unit rates.
  - Re-check Turbopuffer's data-returned rate.
- **Data hygiene:**
  - The Cohere Embed description still names embed-v3 / Rerank-v3 (current: Embed 5 / Rerank 5).
  - The Strands description's "predecessor of AWS Agent SDK" claim is unverified.
  - Several rows' URLs point at moved repos (Ragas → vibrantlabsai/ragas, verl → verl-project/verl, LLaMA-Factory → hiyouga/LlamaFactory, torchtune → meta-pytorch); update `url` with `record.url` in a re-verify result.
