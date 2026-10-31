# Benchmark-URL research pass for the capability sweep (2026-10-31)

**Why.** `scripts/capability_sweep.py` (#128/#129) reads the URLs in each row's `capability-benchmark-sources` cell and extracts scores from those pages. Before this pass no cell carried a URL (577 said `estimate`, 428 `n/a`), so a paid sweep would have produced nothing. This pass fills the cells where a primary source publishes a score on one of the composite's benchmarks (docs/benchmark-families.yml: code, agentic, longcontext).

**Inputs.** `candidates.json` (rows by section), two research agents' output `models.json` / `agents.json` with `models-notes.md` / `agents-notes.md` (every page fetched, every row without data and why), the combined `apply.json`, and `apply-report.md` from `apply_reverify.py --date 2026-10-31`.

**Result.** 31 cells on 31 rows set to `real-data` with a citation; 1 row (Reka) checked and left as is. Every entry is formatted `benchmark-id: score% (system or model, metric detail, date) URL`, which the sweep's regex, URL extractor and Haiku path all read.

| Group | Rows filled | Primary sources |
|---|---|---|
| Foundation models | 12 of 13 | vendor announcement pages, model cards (Hugging Face, GitHub), technical reports on arxiv / amazon.science, aider polyglot leaderboard |
| Coding agents | 6 of 32 | swebench.com leaderboard JSON, aider leaderboard, MetaGPT paper, mle-bench README |
| Computer-use / browser agents | 5 of 21 | OSWorld-Verified leaderboard data (osworld-v1.xlang.ai), WebArena official sheet, vendor reports (Browser Use, Skyvern, Google) |
| Research agents | 1 of 10 | OpenAI Deep Research system card (cdn.openai.com), Hugging Face post quoting OpenAI (medium) |
| Frameworks / orchestration | 7 of 57 | GAIA `results_public` dataset, swebench.com, authors' papers |

Benchmark ceilings the sweep will write to `data/_baselines/benchmark-maxima.json` (from cells that cite a URL): aider-polyglot 88.0 (10 rows), gaia 69.1 (8), humaneval 89.0 (4), livecodebench 93.5 (7), longbench-v2 66.3 (2), mbpp 87.7 (3), mle-bench 11.0 (3), osworld 86.0 (8), swe-bench-verified 80.6 (6), swe-lancer 53.0 (1), tau-bench 92.7 (2), webarena 58.1 (2). Dry run: 45 rows would score (24 before, from unsourced estimate text).

**Rules applied.**
- Only numbers read on the fetched page; competitor columns and third-party aggregators excluded. Two medium-confidence exceptions are labelled in the cell: OpenAI's GPT-6 Astra OSWorld 2.1 and GPT-5 LiveCodeBench figures are reproduced on Google's and xAI's comparison pages (openai.com returns 403 to fetchers, and the GPT-5 system card's tables are images); OpenAI Deep Research's GAIA 67.4% is quoted by Hugging Face.
- Dropped: a WebArena 68% entry for "Claude Code + GBOX MCP", a third party's run of the product with an add-on, is not a measurement of Claude Code.
- OSWorld 2.1 "partial score" is used for Anthropic, Google and OpenAI alike (all three publish only that metric); the strict pass rate is stated where the vendor gives it.
- WebVoyager results for Browser Use, Skyvern and Project Mariner are recorded for documentation; WebVoyager is outside the three families and contributes nothing to the composite.
- Benchmarks the 2026 flagships now report (Terminal-Bench 4.0, DeepSWE, SWE-bench Pro, FrontierCode, OSWorld 2.x, AutomationBench, MRCR, GraphWalks) are not in `benchmark-families.yml`, so several code-family entries name a 2025 model. Adding those ids to the families file is the next methodology decision (see HANDOFF).

**Code changes in the same PR.** Parser fix (digits could start a token, so "osworld 66.3%" read as 6.3), maxima refresh from the catalog before scoring, the row's name and note passed to the Haiku extraction prompt so comparison tables yield the subject's column, and `scripts/test_capability_sweep.py` in CI.

**Follow-ups.** Duplicate pairs surfaced by the pass: `anthropic-computer-use--docs-anthropic-com` / `anthropic-computer-use--anthropic-com`, `openhands-all-hands-ai--all-hands-dev` / `opendevin-openhands--gh-all-hands-ai-openhands`, `metagpt-harness--gh-foundationagents-metagpt` / `metagpt--gh-geekan-metagpt`; merge with `scripts/merge_records.py`. Memory-layer rows whose sources cell "inherits" a model's SWE-bench score (Claude memory, Managed Agents memory, Bedrock AgentCore memory, Copilot memory, ChatGPT memory, Mistral Agents API, Realtime API) would score under `--no-llm`; those cells should become placeholders or cite the model row instead.
