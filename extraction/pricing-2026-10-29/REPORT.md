# Whole-stack list prices — 2026-10-29

`data/pricing/stack.json` feeds `mcp/src/stack-costs.ts` (the cost estimate in `plan_stack`, `landscape stack` and `/build`). Every price comes from the vendor's own pricing page or docs, and each entry cites the exact URL. Checked on 2026-10-29. The 79 targets were the tier-1 and tier-2 rows in the model, gateway, observability, sandbox, browser, voice, tools and guardrails layers (`input-targets.json`).

## Models: 20 prices, 10 families
Each family has a flagship and its cheapest current model, priced in $ per 1M tokens (input / output). Prices are the standard tier, with no batch or cache discounts.

| Family | Flagship | Cheapest |
|---|---|---|
| Anthropic | Claude Fable 5.1: 10 / 50 | Haiku 5.5: 0.10 / 0.50 (prompts up to 100k) |
| OpenAI | gpt-6-astra: 10 / 50 | gpt-6-luna: 0.10 / 0.50 |
| Google | Gemini 4 Argon: 2 / 10 (rises to 4 / 20 on 2026-12-01) | Gemini 3.1 Flash-Lite: 0.25 / 1.50 |
| xAI | grok-4.7: 2 / 6 | grok-4.3: 1.25 / 2.50 |
| DeepSeek | V4-Pro: 1.32 / 3.96 (peak; off-peak is half) | deepseek-flash: 0.30 / 1.20 |
| Mistral | Medium 3.5: 1.5 / 7.5 | Ministral 3 3B: 0.1 / 0.1 |
| Qwen | qwen3.8-max: 2 / 6 (international) | qwen3.8-flash: 0.15 / 0.47 |
| Amazon Nova | Premier: 2.5 / 12.5 | Micro: 0.035 / 0.14 |
| Phi (Azure) | Phi-4: 0.125 / 0.50 | Phi-4-mini: 0.075 / 0.30 |
| Reka | Flash 3: 0.10 / 0.20 | Edge 2603: 0.10 / 0.10 |

## Metered services: 25 entries
- **Observability:** Arize AX, Langfuse (units, counted as spans), LangSmith (traces), Splunk Agent Observability / Galileo (spans), Traceloop, AgentOps.
- **Gateway and tools:** Portkey (logs), Composio (tool calls), Lakera Guard (requests).
- **Sandboxes:** E2B, Daytona, Modal. Each rate is converted for the vendor's default sandbox size, and the notes say how.
- **Browsers:** Browser Use, Browserbase, Hyperbrowser, Steel, Browserless.
- **Voice:** Bland (all-in), Vapi, Retell, ElevenLabs Agents, LiveKit, Cartesia, Pipecat Cloud.
  - Rates differ in what they include. Vapi, Retell and LiveKit charge the model, speech-to-text and text-to-speech on top, so their totals are lower bounds; the notes say so.

**Free plans are only included when their overage terms are clear.** Hard-capped free tiers are either left out or marked `overage: null`, and the estimator now supports per-plan overage, so a capped free plan is never priced as if it could overflow.

## Not priced, and why
- **Vendor no longer publishes usable prices:** 01.AI (international API suspended), Cohere (only legacy Command models are listed), CodeSandbox (403).
- **Open-weight only or open source only:** Llama, LiteLLM, MCP reference servers, Phoenix, OpenInference, Ragas, TruLens, Stagehand, UI-TARS, Promptfoo.
- **Contact sales only:** Synthflow, Workato, Coder Premium, HiddenLayer, Pillar, Lasso, Mindgard, Apex, Calypso/F5, Protect AI, HackerOne, TruEra, Snyk.
- **Priced per seat or subscription:** the consumer AI browsers, Copilot Autofix, CallRail, the Mistral Vibe plans.
- **The meter doesn't map to one of the estimator's units:**
  - OpenRouter charges a percentage fee on spend.
  - Braintrust and Confident AI bill per GB.
  - Enkrypt and Skyvern use credits.
  - Vonage bills per session.
  - OpenAI Realtime bills by audio token.
  - Helicone's tiers appear only in its calculator.

## Re-check soon
- Gemini 4 Argon rises to $4 / $20 on 2026-12-01.
- Cartesia's agent-minute rate goes from $0.03 to $0.06 after 2026-12-31.
