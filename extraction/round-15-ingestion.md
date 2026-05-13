# Round 15 — substrate / orchestration / sandbox sweep (2026-05-13)

Three-pass expansion adding the missing substrate layers underneath the
existing agent-shaped sections. Each pass ships as its own commit.

## Pass A — Foundation models (substrate reference)

**Goal**: ~10-15 frontier foundation model rows. These are the parametric
substrate that ~100+ other catalog rows (agent frameworks, coding harnesses,
IDE-agents, use-case harnesses) sit on top of. Adding them makes the edges
explicit instead of dangling.

**Rows shipped**: 13

| Name | Tier | URL |
|------|------|-----|
| Anthropic Claude (foundation models) | 1 | https://www.anthropic.com/claude |
| OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | 1 | https://openai.com/index/introducing-gpt-5/ |
| Google Gemini 3 family | 1 | https://blog.google/technology/google-deepmind/gemini-3/ |
| Meta Llama 4 family | 1 | https://ai.meta.com/blog/llama-4-multimodal-intelligence/ |
| DeepSeek R1 / V3 family | 1 | https://www.deepseek.com/ |
| Mistral Large 2 / Mixtral family | 1 | https://mistral.ai/news/mistral-large-2/ |
| Cohere Command R+ / Command A | 1 | https://cohere.com/command |
| xAI Grok 4 | 1 | https://x.ai/news/grok-4 |
| Alibaba Qwen 3 family | 1 | https://qwenlm.github.io/blog/qwen3/ |
| Reka Core / Flash / Edge | 2 | https://www.reka.ai/ |
| 01.AI Yi family | 2 | https://www.01.ai/ |
| Amazon Nova family | 2 | https://www.aboutamazon.com/news/aws/amazon-nova-foundation-models |
| Microsoft Phi-4 family | 2 | https://azure.microsoft.com/en-us/blog/welcome-phi-4/ |

**Taxonomy**: parametric storage + parametric-recall / attention retrieval +
parametric-permanent persistence + read-only update (at inference time) +
weight / kv-token unit + opaque governance + n/a conflict-resolution.
Conflict-resolution column carries `n/a — substrate model` because foundation
models don't have memory-write semantics; the "memory" is in their weights.

**Surprises**:
- Aleph Alpha already exists in catalog at row ~432; declined to add a
  separate Aleph Alpha row since the Cohere row mentions the merger.
- DeepSeek + Qwen 3 + Llama 4 + Mistral Mixtral are all Apache 2.0 /
  permissive-license — the open-weights frontier tier is now dominated by
  Chinese labs (DeepSeek + Qwen + Yi) plus Meta and Mistral. Cohere weights
  are CC-BY-NC (non-commercial).
- Magic.dev's 100M context claim (LTM-2-mini, Aug-2024) is not independently
  reproduced — flagged in cons. Same for Reka Core's "matched GPT-4 / Gemini
  Ultra" claim on MMMU (Apr-2024).
- Adept ACT marked T3 (historical) — Amazon AGI acqui-hire June 2024 ended
  ACT as a commercial product.

**Commit**: TBD

## Pass B — Multi-agent orchestration platforms

**Goal**: ~10-15 platforms whose primary identity is *multi-agent coordination*.
Distinct from frameworks-without-memory (libraries) and IDE-harnesses.

**Rows shipped**: 12

| Name | Tier | URL |
|------|------|-----|
| CrewAI Enterprise | 2 | https://www.crewai.com/enterprise |
| Microsoft AutoGen Studio | 2 | https://microsoft.github.io/autogen/dev/user-guide/autogenstudio-user-guide/index.html |
| MultiOn | 2 | https://www.multion.ai/ |
| Reflection AI | 2 | https://reflection.ai/ |
| Adept ACT | 3 | https://www.adept.ai/ |
| Sema4.ai | 2 | https://sema4.ai/ |
| Imbue (formerly Generally Intelligent) | 3 | https://imbue.com/ |
| Steamship | 3 | https://www.steamship.com/ |
| Phidata / Agno | 2 | https://www.agno.com/ |
| Burr (DAGWorks) | 2 | https://burr.dagworks.io/ |
| InstructLab (Red Hat / IBM) | 2 | https://instructlab.ai/ |
| Lindy | 2 | https://www.lindy.ai/ |

**Surprises**:
- Magic.dev was on the spec list but already exists in catalog at
  `Agent IDEs & coding harnesses` (id `magic-dev--magic-dev`). Skipped per
  spec's "verify not duplicate".
- Phidata's rebrand to Agno (2024) is real; treated as the same product
  family for one row.
- Adept ACT marked T3 — Amazon AGI acqui-hire June 2024 ended product
  development.
- InstructLab is more a fine-tuning / alignment framework than a
  multi-agent orchestration platform per se, but included because Red Hat /
  IBM position it as agent-substrate. Acknowledged in row's pros/cons.
- Lindy added (not on original list) as a no-code SMB-targeted multi-agent
  automation platform — fills a gap left by Magic.dev being a duplicate.

**Commit**: TBD

## Pass C — AI sandbox & runtime environments

**Goal**: ~8-12 sandbox + dev-env + browser-farm + sandbox-runtime rows that
are substrate for AI agents. Distinct from inference platforms (which serve
the model) — this serves the *environment* the agent operates in.

**Rows shipped**: TBD

**Commit**: TBD
