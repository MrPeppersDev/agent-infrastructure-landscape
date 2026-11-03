# Benchmark families for 2026 flagships, and model rows re-sourced (2026-11-03)

**Why.** The 2026-10-31 pass could only record benchmarks the composite knew, and every 2026 flagship announcement reports different ones (Terminal-Bench 4.0, DeepSWE, SWE-bench Pro, FrontierCode, FrontierSWE, OSWorld 2.x, AutomationBench, MRCR, GraphWalks, BrowseComp, Agents' Last Exam). So the model rows' composites rested on 2025 models.

**Inputs.** `benchmark-descriptions.md`: facts about 26 benchmarks read from their official sources (papers, repos, maintainers' sites; Codeforces is behind a bot wall). `flagship-scores.json` / `flagship-scores-notes.md`: 188 score entries read from the 13 model vendors' current announcement pages, model cards and system cards (openai.com blocks fetchers and its system-card tables are images, so OpenAI has no first-party 2026 number). `apply.json` and `apply-report.md`: the cells applied with `apply_reverify.py --date 2026-11-03`.

**Classification (docs/benchmark-families.yml, "ADDED 2026-11-03", pending ratification).**

| Family | Added | Flagged `?` for the maintainer |
|---|---|---|
| code | swe-bench-pro, deepswe, swe-sweep, nl2repo-bench, frontiercode (~) | swe-atlas-qna (comprehension, LLM-judged), frontierswe (gated 0-1 reward) |
| agentic | terminal-bench (4.x), terminal-bench-2 (2.x), osworld-2, automationbench, browsecomp (~), agents-last-exam (~) | cybench (offensive security only) |
| longcontext | mrcr (~), graphwalks (~) | |
| excluded | cursorbench, gdpval, gdpval-aa, aa-briefcase, eebench, hle, arc-agi-2, aime, mmmu, codeforces-rating, vals-index, the two Artificial Analysis indices, terminal-bench-1 / -3 / -hard / -science | |

Rules: a new task set gets a new id, a bug-fix release of the same tasks does not; superseded versions and vendor subsets are excluded ids so the canonicaliser stops at them; non-percentage metrics (Elo, ratings, win rates, indices) are excluded; OSWorld 2.x cells record the partial score every vendor publishes and give the strict rate in parentheses; a competitor column on a vendor page is never a source for that competitor.

**Cells rewritten (8 rows).** Anthropic (Opus 5.5 system card and post), Google (Gemini 4 Carbon table), xAI (Grok 4.7), Mistral (Large 4 preview and open-weight posts), Qwen (Qwen3.8-Max and 27B cards), DeepSeek (V4.1-Flash-1017 card, V4.1 tech report, V4 paper), Meta (Muse Wonder and Muse Spark 1.3 pages; row renamed "Meta Llama 4 family (now Muse)"), OpenAI (only the OSWorld 2.1 entry relabelled to `osworld-2`; still medium). Amazon, Cohere, Microsoft, 01.AI and Reka publish no classified 2026 benchmark and keep their cells.

**Ceilings the sweep will write** (from cells citing a URL; dry run 35 rows score):

| Benchmark | Max | Rows | Top row |
|---|---|---|---|
| swe-bench-pro | 89.9 | 3 | Anthropic Claude |
| deepswe | 79.0 | 6 | Meta Muse |
| terminal-bench (4.x) | 66.4 | 6 | Anthropic Claude |
| terminal-bench-2 | 90.6 | 3 | DeepSeek |
| osworld-2 | 81.8 | 4 | Anthropic Claude |
| automationbench | 60.5 | 6 | DeepSeek |
| frontierswe | 73.5 | 3 | Qwen |
| nl2repo-bench | 68.2 | 2 | DeepSeek |
| swe-atlas-qna | 59.4 | 2 | Meta Muse |
| agents-last-exam | 35.4 | 2 | DeepSeek |
| browsecomp | 84.5 | 2 | Mistral |
| mrcr | 98.5 | 3 | Meta Muse |
| graphwalks | 96.2 | 1 | Google Gemini |
| swe-sweep | 9.6 | 1 | Google Gemini |
| frontiercode | 54.4 | 1 | Anthropic Claude |
| cybench | 93.0 | 1 | Mistral |

Unchanged from 2026-10-31: aider-polyglot 88.0, gaia 69.1, livecodebench 93.5, swe-bench-verified 80.6, osworld 86.0, tau-bench 92.7, webarena 58.1, mle-bench 11.0, swe-lancer 53.0, longbench-v2 66.3, humaneval 89.0, mbpp 87.7.

**Caveats recorded in the cells.** AutomationBench numbers come from three variants (Zapier private set, Zapier public set, Artificial Analysis set) and fold into one id with the variant named. FrontierCode has a pass rate and a rubric score; vendors print the rubric score from Artificial Analysis's v1.1 run. Google's OSWorld 2.1 figure is an 82-task offline subset. MRCR bins differ (256K, 256K to 512K, 1M). Meta's pages carry no date, so the cells say "read 2026-11-03".

**Validation.** `make validate` 8 gates, `make lint` 0 findings, `scripts/test_capability_sweep.py` passes (canonicaliser folds versions and stops at excluded ids).

**Follow-ups.** Ratify the three `?` entries. OpenAI's 2026 numbers need a browser session on its system cards. Amazon's Nova 2 Pro reports Terminal-Bench 1.0 only (excluded); Cohere's Command A+ reports Terminal-Bench Hard only (excluded).
