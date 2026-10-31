# Benchmark sources, agent-product rows — notes (2026-10-31)

Scope: candidate groups `coding`, `computer-use`, `browser`, `harnesses`, `orchestration`, `frameworks` (the `models` and `inference` groups in candidates.json were not part of this task and were not touched). Web searches used: 1.

## Sources actually fetched

- SWE-bench Verified: the leaderboard JSON embedded in https://www.swebench.com (element `leaderboard-data`; 180 Verified entries, newest 2026-02-26). The experiments repo listing on GitHub was truncated and the GitHub API was not enabled for this session, so numbers come from swebench.com only.
- Aider polyglot: https://aider.chat/docs/leaderboards/ (69 entries, newest 2025-10-03; all entries run under aider itself).
- OSWorld / OSWorld-Verified: os-world.github.io 301-redirects to https://osworld-v1.xlang.ai/, whose leaderboard is loaded from `static/data/osworld_verified_results.xlsx` (verified re-runs) and `static/data/self_reported_results.xlsx`; both were downloaded and parsed. OSWorld 2.0 (osworld-v2.xlang.ai) has a different task set and was not used.
- GAIA: the Space UI is dynamic; the underlying dataset `gaia-benchmark/results_public` (config 2023, splits validation 96 rows / test 4,075 rows) was read via the HF datasets-server API. Citation URL is the Space.
- WebArena: webarena.dev/og/ links to the Google Sheet leaderboard, exported as CSV.
- tau-bench / tau2-bench: README and taubench.com list only LLMs (plus Act/ReAct strategies); no catalog system appears.
- MLE-bench: https://github.com/openai/mle-bench README leaderboard.
- AgentBench: README results are images / a Google Sheet; no catalog system verified. Not used.
- OpenAI pages (openai.com/index/*, chatgpt.com/codex) and perplexity.ai return 403 to WebFetch; the Operator and Deep Research system-card PDFs on cdn.openai.com were fetched instead.

## Per-filled-row notes

- **aider-harness**: top polyglot entry is a model (gpt-5 high, 88.0%) run through aider's own harness; the leaderboard has no harness other than aider. No SWE-bench Verified entry for aider.
- **amazon-q-developer**: four leaderboard entries (25.6% v20240430, 38.8% v20240719, 55.0% v20241202, 65.4% v20250405); model undisclosed. The AWS blog posts about the result 404 now; aws.amazon.com/q/developer only says "highest scores" without a number.
- **anthropic-computer-use (both ids)**: the OSWorld-Verified leaderboard lists Anthropic model entries run with the computer-use tool: claude-sonnet-4-5-20250929 62.88% (100 steps, 2025-10-31), claude-sonnet-4-6 72.11% (2026-03-08), claude-opus-5[1m] 83.39% and claude-fable-5[1m] 85.96% (both 2026-08-01). The latest/top entry was used. Anthropic's own Sonnet 4.5 page (2025-09-29) states 61.4% OSWorld-Verified (100 steps, avg of 4 runs). The old cell's SWE-bench Verified 49% is a model score (Claude 3.5 Sonnet, 2024-10-22), not a computer-use result, so it was dropped.
- **claude-code-anthropic**: no first-party benchmark on claude.com/product/claude-code or the Anthropic model posts (Anthropic's SWE-bench/Terminal-Bench numbers use a "simple scaffold"/Terminus 2, not Claude Code; swebench.com's "Tools + Claude ..." entries are that scaffold). The only leaderboard entry naming the product is WebArena "Claude Code + GBOX MCP" 68% (GBOX AI, self-reported, 10/2025) — a third party running Claude Code with an add-on MCP, hence `medium`. GAIA also has third-party "Claude Code 2.1.224 · Qwen3.8-27B-NVFP4" entries (AgentEval, 60.8%, 2026-09-15) using a non-Anthropic model; not used.
- **metagpt (both ids)**: 85.9% HumanEval / 87.7% MBPP pass@1 are in the body of the authors' paper (arXiv 2308.00352 v7), not the abstract; the model is not stated in the extracted passage, so none is written. README has no numbers. No GAIA entry.
- **openhands (both ids)**: swebench.com entries by the OpenHands org: 53.0% (CodeAct v2.1 + claude-3-5-sonnet, 2024-10-29), 60.8% (4x Scaled, 2025-02-03), 65.8% (2025-04-15), 70.4% (Claude 4 Sonnet, 2025-05-24), 71.8% (GPT-5, 2025-08-07); a third-party "Salesforce AI Research SAGE (OpenHands)" scores 73.8% (2025-11-03). GAIA: "OpenHands v0.28.1" 37.21% test (2025-06-03); the research variant "OpenHands-Versa" (CMU, All Hands AI) scores 51.16% test (2025-06-09) and was not used. MLE-bench: 4.89% any-medal with gpt-4o (2024-10-08).
- **openai-operator**: OSWorld-Verified re-run of `computer-use-preview` 31.4% at 100 steps (also 26.0%/15 steps, 31.3%/50 steps); the self-reported tab lists "OpenAI CUA 4o (200 steps)" 38.1% (2025-01-24) and "OpenAI CUA o3 (200 steps)" 42.9% (2025-05-23), and the Operator system card (2025-01-23, updated 2025-03-11) also states 38.1% OSWorld. WebArena 58.1% is the official sheet's "OpenAI Operator" row sourced from the system card. The system card's WebArena/WebVoyager figures are in images, not text.
- **ui-tars**: OSWorld-Verified entries: UI-TARS-2-2509 53.1% (2025-10-14), UI-TARS-250705 41.84% (2025-09-16), uitars-1.5-7b up to 29.6%, uitars-72b-dpo up to 27.1%. The README's 42.5% (UI-TARS-1.5, 100 steps) and the UI-TARS-2 paper's 47.5% are self-reported on the original OSWorld. The leaderboard's 2025-07-28 blog re-eval lists "UI-TARS" 40.0% without a version.
- **openai-deep-research**: `medium` because the GAIA 67.36% validation figure comes from Hugging Face's open-deep-research post quoting OpenAI (openai.com 403; GAIA leaderboard has no OpenAI entry). MLE-bench 11% in the system card is bronze-medal pass@1, a different metric from the leaderboard's any-medal column. SWE-Lancer 53% is IC SWE Diamond tasks solved (browsing model, $87,708 earned). HLE 26.6% was not re-verified.
- **autogen-ag2**: entry is Microsoft's "Multi-Agent Experiment v0.1 (powered by AutoGen)" (32.23% test, 39.39% validation, 2024-03-01); AG2 is the community fork and has no entry of its own.
- **autogpt**: "AutoGPT4" 4.98% test / 4.85% validation (2023-11-03), submitted by the AutoGPT org; an old GPT-4 result.
- **camel**: leaderboard name is "🦉 OWL - Workforce" (emoji dropped in the cell); validation split, 69.09%, matches the OWL README (2025-04-18). OWL is CAMEL-AI's agent built on CAMEL; the earlier "OWL - Roleplaying" scored 58.18% (2025-03-07). An "OWL++" 60.8% test entry (2025-05-16) has no organisation and was not used.
- **magnetic-one**: GAIA "Magentic-1 (o1)" 37.87% test (2024-10-19); "Magentic-1" (GPT-4o) 32.23% test. WebArena 32.8% (GPT-4o, all 812 tasks) is from the authors' paper (Table 1); AssistantBench 27.7% is not in the composite and was omitted. "Magentic-UI" (42.52% test, 2025-05-24) is a different product.
- **smolagents**: leaderboard name is "open Deep Research | pass@1" (pipe replaced by parentheses); 49.83% test (2025-02-10), 55.15% validation (2025-02-04, matches the HF blog).

## Rows without data (what was checked)

### coding
- bedrock-agentcore-aws: aws.amazon.com/bedrock/agentcore not fetched (runtime product; no swebench.com entry).
- bolt-new-stackblitz-harness: no swebench.com / aider entry; vendor site not benchmark-bearing.
- charm-crush: no swebench.com entry.
- chatgpt-codex-cloud-agent: chatgpt.com/codex 403, openai.com 403; swebench.com has only model entries (GPT 5.1 Codex / 5.2 Codex under mini-SWE-agent), none for the Codex agent. GAIA "Codex CLI 0.149.1" entries are third party (AgentEval) with DeepSeek/Qwen models.
- cline-harness: cline.bot has no benchmark claim; no swebench.com entry.
- cognition-devin-v2-spec-mode: cognition.com SWE-bench technical report (2024-03-15) is 13.86% on a random 25% of full SWE-bench (570 tasks) — out of scope (not Verified); no Verified entry; devin.ai/desktop 403.
- continue-dev-harness: no swebench.com entry.
- cursor-ide: cursor.com has no benchmark claim; no swebench.com entry.
- github-copilot-agent-mode / github-copilot-workspace: GitHub changelog has no SWE-bench claim; no swebench.com entry.
- goose-block: goose docs redirect page has no benchmark; no swebench.com entry.
- jetbrains-ai-assistant: no entry.
- jetbrains-junie: junie.jetbrains.com only says "top performer on SWE-Rebench" with no number; no swebench.com entry.
- kiro: kiro.dev has no benchmark claim; no entry.
- lovable-dev-harness, v0-vercel, sourcegraph-cody-agent, opencode-sst, zed-agentic-editing: no benchmark claims on vendor pages fetched (zed.dev/agentic), no leaderboard entries.
- magic-dev: no entry (HashHop is not in the composite).
- manus-ai: manus.im home, blog index and Manus 2.0 post contain no GAIA numbers; one web search found only third-party articles; GAIA leaderboard has only unaffiliated "xManus"/"testManus" entries. No update.
- replit-agent-v3: replit.com/ai has no benchmark claim.
- roo-code: README has no claim (extension shut down 2026-05-15 per README).
- smol-developer: no entry.
- windsurf-codeium-openai: devin.ai/desktop 403; no swebench.com entry.

### computer-use
- browser-use: no composite benchmark. Non-composite only: WebVoyager 89.1% (GPT-4o, 586 tasks, browser-use.com/posts/sota-technical-report, 2024-12-15); the site now shows only its own "Browser Use Bench v2.1". Not written to agents.json per the no-composite-score rule; cell text if wanted: `webvoyager: 89.1% (Browser Use + GPT-4o, 586 tasks, vendor report 2024-12-15) https://browser-use.com/posts/sota-technical-report`.
- bytebot: README has no benchmark.
- claude-for-chrome: claude.com/blog/claude-for-chrome has only prompt-injection safety rates (23.6% → 11.2% attack success), no capability benchmark.
- highlight-ai, lutra-ai: not benchmark-bearing products; no leaderboard entries.
- hyperbrowser, steel-dev: vendor pages have no benchmark claims.
- magnitude: magnitude.dev now markets local-inference speed vs Ollama; no agent benchmark on site or README.
- project-mariner: non-composite only: WebVoyager 83.5% (Gemini 2.0, blog.google 2024-12-11); deepmind.google/models/project-mariner has no numbers. Cell text if wanted: `webvoyager: 83.5% (Project Mariner, Gemini 2.0, single-agent, Google blog 2024-12-11) https://blog.google/technology/google-deepmind/google-gemini-ai-update-december-2024/`.
- skyvern: non-composite only: WebVoyager 85.85% (Skyvern 2.0, GPT-4o/GPT-4o-mini, 2025-01-16) and WebBench 64.4% (README). Cell text if wanted: `webvoyager: 85.9% (Skyvern 2.0 + GPT-4o, vendor report 2025-01-16) https://www.skyvern.com/blog/skyvern-2-0-state-of-the-art-web-navigation-with-85-8-on-webvoyager-eval/`.
- stagehand: docs and README have no benchmark.

### browser
- brave-leo, browserbase, dia-atlassian, fellou, microsoft-edge-copilot-mode-journeys, opera-ai-formerly-aria, sigma-private-ai-browser: no leaderboard entries on any fetched leaderboard; browser products without published agent benchmarks. perplexity-comet: perplexity.ai 403; no leaderboard entry.

### harnesses
- alphasense, hebbia, iris-ai, liner, scite-ai, you-com-research: no GAIA/AgentBench entries.
- perplexity-deep-research: vendor hub 403; HLE/SimpleQA are non-composite anyway; no GAIA entry.
- sakana-ai-scientist: sakana.ai/ai-scientist and the AI-Scientist README have no benchmark numbers; MLE-bench README does not list Sakana.
- stanford-storm: FreshWiki/WildSeek are not in the composite; no GAIA entry.

### orchestration
- adept-act, crewai-enterprise, imbue, instructlab, lindy, multion, reflection-ai, sema4-ai, steamship: no entries on any fetched leaderboard.
- microsoft-autogen-studio: no AutoGen Studio-specific score; the AutoGen GAIA entry is recorded on the autogen-ag2 row.

### frameworks (no update)
- agency-swarm, babyagi, beeai-framework, burr, claude-agent-sdk, cline-framework, crewai, dify, dspy, eliza, genkit, google-adk, gpt-engineer, haystack, langchain, langflow, langgraph, llamaindex, marvin, mastra, microsoft-agent-framework (README: none), microsoft-semantic-kernel, n8n, openai-agents-sdk, openai-swarm, phidata-agno, pydantic-ai, strands-agents, vercel-ai-sdk: no entries on swebench.com, GAIA, OSWorld, WebArena, tau-bench or MLE-bench. GAIA has unaffiliated hobby entries ("langgraph agent" 2.99%, "gaia_langchain_v1" 0%, "fhswf-smolagents") and a third-party "ADK-GAIA" (SZU-GML, 37.54% test / 50.91% validation) that is not Google's; none used. GAIA "Eliza | Eliza Labs & AI3 Labs" 1.0% test (2025-01-06) exists but the README does not confirm Eliza Labs as maintainer and the score looks like a broken submission; skipped.
- Protocol/infra rows (a2a, agntcy, arcade-dev, composio, inngest, mcp-servers, mcp-spec, restate, temporal, trigger-dev): not applicable, unchanged.
