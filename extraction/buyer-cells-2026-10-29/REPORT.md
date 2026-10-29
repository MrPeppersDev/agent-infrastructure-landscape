# Buyer cells backfill (schema v1.2.0) — 2026-10-29

Targets: the 435 live rows (tier ≤ 3) in the sections the stack composer draws from, in four batches (`input-{1..4}.json`). Four research agents used primary sources only: vendor trust centers and security pages (rendered in headless Chromium), official docs and `llms.txt`, official repos via raw.githubusercontent.com, and the PyPI and npm registries. They made no web searches. Applied with `apply_v1_1_research.py --date 2026-10-29`. All **888 cells** passed the set and enum checks.

| Cell | real-data | not-applicable | Notes |
|---|---|---|---|
| `sdk-languages` | 297 | — | |
| `protocol-support` | 241 | — | mostly `mcp-server` and `mcp-client`; also `a2a`, `ag-ui`, `openai-compatible` and `opentelemetry` |
| `compliance-certifications` | 164 | 120 | not-applicable means open-source code or a paper with no hosted service; 4 rows are `none-published` |
| `maturity` | 66 | — | `ga`, `beta`, `preview`, `alpha`; many come from PyPI "Development Status" classifiers, at medium confidence |

## Rules applied
- **"SOC 2" with no type stated is left out.** This applies to MongoDB, Portkey, Workato (soc3 kept), Synthflow, Vapi, You.com, Demandbase, AWS AgentCore, Cline, Enkrypt, Weaviate and Lavender. Only the other attestations on the page were recorded.
- **Only completed attestations are recorded:**
  - In progress or on a roadmap: Interloom (ISO 27001/42001), LiveKit (PCI, ISO 27001), TrustCloud (ISO 42001).
  - Only a letter of intent: XBOW's ISO 27001.
  - SOC 2 Type 1 completed, Type 2 still in its observation period: Restate.
  - Mem0 publishes only SOC 2 Type 1, and its HIPAA claim is a self-attestation.
- **Platform-wide attestations with no stated scope are medium confidence.** This covers Datadog, Dynatrace, Databricks, Neo4j and OpenAI. For Anthropic, only the API scope is recorded.
- **When a trust portal was gated, blocked by a bot check, or failed to load**, the vendor's own security page or homepage was used where it states the attestations. Otherwise the cell was left empty. The list is in each agent's notes.
- **Stale PyPI classifiers were skipped:** DSPy (marked Alpha at 3.4), LightRAG and Daytona.

## Leads for a lifecycle pass (not applied here)
- **OpenAI Deep Research:** the docs list a shutdown date for `o3-deep-research` (2026-07-23) that has already passed.
- **OpenAI Codex:** `codex mcp-server` has been removed; it is now an MCP client only.
- **Gemini CLI:** replaced by Antigravity CLI for the unpaid tier (2026-06-18).
- **Tabnine:** tabnine.com redirects to Tricentis.
- **Sajari:** redirects to Algolia. Toplyne and Coalfire AIOps return 404.
- **Microsoft Foundry Agent Service Memory** is still in preview. **Anthropic Managed Agents memory** is in beta and is not HIPAA- or ZDR-eligible.

## Effect
For a TypeScript support agent with a SOC 2 Type II requirement, `plan_stack` now picks systems whose attestations are cited: Qdrant, Composio, Braintrust and HiddenLayer. The risk score drops to low.
