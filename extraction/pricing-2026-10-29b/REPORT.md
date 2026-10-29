# Stack pricing, round 2 (2026-10-29)

Every price comes from the vendor's own pricing page or pricing docs, and each entry cites one. The raw agent output is in `result.json`. `data/pricing/stack.json` holds the normalized version: Helicone's tiers are rewritten into the `tiers` shape and the notes are shortened.

The cost engine (`mcp/src/stack-costs.ts`) gains three price shapes for this round:

- **Graduated tiers** (`MeteredPricing.tiers`): per-unit rates across the month's total, used instead of a flat overage. Helicone publishes these only in the pricing calculator's "How is this calculated?" panel. At the default 180k requests a month, a flat first-tier rate would overstate the cost by more than 2×.
- **Gateway fees** (`gatewayFees`): a percentage of the stack's priced model spend. OpenRouter charges 5.5% when credits are bought, and BYOK is free up to $25k of list-price inference a month.
- **Embeddings** (`embeddings`): per 1M tokens. The workload gains `embeddingTokensPerRun` (default 1,000), which covers queries plus new content.

| Kind | Added |
|---|---|
| Models | Together AI: GLM-5.3, Qwen3.5 9B. Fireworks AI: GLM 5.3, Nemotron 3.5 Lightning 30B A3B |
| Metered | Helicone (graduated per-request rates) |
| Gateway fee | OpenRouter |
| Embeddings | OpenAI text-embedding-3-small, Voyage voyage-4 and voyage-4-lite, Jina v5 text small, Mistral Embed |

**Skipped, with reasons**

- **Braintrust**: billed per GB processed, with no per-span equivalent published.
- **Arize Phoenix**: the hosted page redirects to Arize AX, which is already priced.
- **LiteLLM Enterprise**: sales only.
- **Modal**: per-second compute, with no per-request meter.
- **Portkey**: already priced per log; no percentage fee.
- **Cohere Embed**: no self-serve per-token price any more, only dedicated Model Vault instances.
- **Nomic**: seat plans only.
- **Gemini embeddings**: no catalog row.
