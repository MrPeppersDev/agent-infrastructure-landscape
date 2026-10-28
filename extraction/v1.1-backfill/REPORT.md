# v1.1.0 research backfill (2026-10-28)

Step 4 of #150 (option 1). Applied with `scripts/apply_v1_1_research.py`, which writes one cell plus its provenance, checks each value against `docs/schema/`, and leaves the row's `last_verified_at` alone.

## adoption-accelerator: 60 rows, all Y Combinator

- **Candidates.** The open yc-oss mirror of YC's directory was used only as an index. Rows were matched by website domain, by a YC URL on the row, or by exact name when the YC-listed website also appears among the row's citations.
- **Confirmation.** Every value was confirmed on the company's own YC page (`ycombinator.com/companies/<slug>`), which is also the citation. The batch code was parsed from the page data and the page's website was checked against the row.
- **Medium confidence (2):** Screenpipe (the row cites the repo, and screenpi.pe redirects to the YC-listed site) and Memory Store (the row was created from the YC page, but its URL is now mem.store). Magnitude's site moved from magnitude.run to magnitude.dev; it stays high because the YC page links the row's GitHub org.
- **No `none` values written.** Absence from the YC directory doesn't prove a company had no accelerator, and other accelerators need their own sources.
- **Batch codes.** YC writes Spring 2025 as `X25` and Spring 2026 as `P26`, so the schema pattern accepts `p`.

## architecture-deployment-locus and positioning-platform-vs-product: 214 agents rows

Four research agents worked on batches of about 54 rows each (`input-locus-agents-*.json` → `result-locus-agents-*.json`). Every value cites the vendor's own site, docs, pricing page or official repo, and secondary sources were not allowed. A row was left empty wherever the page didn't settle the question.

- **Locus (160 rows):**
  - cloud 62, local 49, hybrid 29, ide 10, computer-use 9
  - MCP and A2A are not-applicable (protocol specs)
- **Positioning (191 rows):**
  - product 89, platform 85, both 16
  - MCP is not-applicable
- **Rule applied across batches:** `hybrid` means both user-run and vendor-hosted are first-class options. On-prem offered only as an enterprise arrangement reads as `cloud`, which is why Bland and Retell were changed from `hybrid` to `cloud`, matching Composio and Anchor.
- **Confidence:** about half the cells are medium. Most enterprise SaaS homepages imply hosting without saying so outright, and those provenance entries carry `verified: false`.

## Lifecycle leads found along the way (not applied; verify before writing)

- **Dead or discontinued:**
  - Continue: continue.dev says "Continue was acquired by Cursor"; the repo is read-only.
  - Lutra AI: lutra.ai says support is discontinued.
  - Steamship: the site returns 404.
  - Reggie.ai: the domain is parked and for sale.
  - heypluto.ai: doesn't resolve.
  - Toplyne: the site returns 404.
- **Redirected or absorbed:**
  - Roo Code → roomote.dev
  - Project Mariner → the deepmind.google homepage
  - SnapAttack → Splunk ES
  - Protect AI → Prisma AIRS
  - OpsRamp → HPE
- **Renamed or repositioned:**
  - Gitpod → Ona
  - MultiOn → AGI, Inc. (now a phone agent)
  - Reflection AI is now an open-weight model lab
  - LawDroid has pivoted to legal-aid tools
  - Magnitude is now a local inference engine (wrong section?)
  - Highlight AI is now focused on meetings and follow-ups
  - Speechmatics Flow → "Agent STT"
  - ElevenLabs → "ElevenAgents"
  - You.com is now "search and inference APIs"
- **End-of-life dates:**
  - Amazon Q Developer's IDE plugins end 2027-04-30
  - OpenAI's deep-research API models shut down 2026-07-23
  - Perplexity Sonar Chat Completions ended 2026-09-27
  - Hume EVI shuts down 2026-11-13 (already recorded)
- **Archived repos:** GPT Engineer, Bytebot, InstructLab.
- **Wrong section or URL:**
  - Hugo.legal is a human-lawyer service.
  - Pincites' URL points to a Filevine page that doesn't mention it.
  - Tonkean's LegalWorks URL returns 404.
- **Moved domains:**
  - Goose → goose-docs.ai
  - OpenHands → openhands.dev
  - Burr → apache/burr
  - A2A → a2a-protocol.org
  - Vercel AI SDK → ai-sdk.dev
  - Pydantic AI → pydantic.dev/docs/ai
  - Claude Code → claude.com/product/claude-code
  - Cognition → cognition.com

## Memory (314 rows) and data (58 rows) families

Six memory batches and two data batches, briefed the same way as the agents batches (`input-locus-{memory,data}-*.json` → `result-locus-{memory,data}-*.json`). That's 637 cells; values were only applied where the vendor's own page settled them.

- **Rules added for these families:**
  - A memory plugin or MCP server that end users install into their own coding agent or assistant is `product` (medium). A memory backend with an API or SDK for builders is `platform`.
  - A self-hostable "cloud" edition you run yourself with docker is `local`.
  - A memory feature or memory file inside a host product takes the host's values. If the host runs on several surfaces with no primary one, locus is omitted.
  - Research papers with no deployed system are `not-applicable`. Their released code usually has its own GitHub row.
  - Embedding vendors whose models you can run yourself (open weights, or a public cloud-marketplace listing) alongside the hosted API are `hybrid`.
- **Running totals after this PR:**
  - Locus on 458 rows: cloud 149, local 145, hybrid 104, ide 19, computer-use 13, not-applicable 28.
  - Positioning on 531 rows.

### More lifecycle leads (not applied; verify before writing)

- **Ownership changes:**
  - Character.ai announced a voluntary Chapter 11 sale (blog post, 2026-10-12).
  - Meta acquired Limitless; the Pendant is no longer sold.
  - Stack AI: the homepage says Asana acquired it.
  - Lakera is now part of Check Point.
  - Chroma says it is joining Replit.
  - Quickwit says it is joining Datadog.
  - Search.io now redirects to Algolia.
- **Archived or no longer maintained:**
  - Flowise (archived) and Atlas.
  - Kuzu (repo archived).
  - Acontext; the official Mem0 MCP (repo archived).
  - Microsoft GraphRAG and TGI are in maintenance mode.
  - Marqo's open-source engine is deprecated.
  - Letta's V1 API server is archived; its source has moved to letta-code.
- **Dead or empty sites:** Steamship, Heyday, Spirit AI and Covariant.
- **Pivots:**
  - Nyne → data licensing.
  - Personal.ai → telecom.
  - Nomic → architecture, engineering and construction agents.
  - Backboard → inference.
  - Redis Agent Memory Server → a managed Redis Cloud service.
  - AutoRAG → a desktop app.
  - Gemini CLI → Antigravity CLI.
  - Edge Copilot Mode was retired.
- **Renames:**
  - MemWal → Walrus Memory
  - Mistral Le Chat → Vibe
  - Databricks Vector Search → AI Search
  - TopBraid EDG → TQ Data Foundation
  - ArangoDB → Arango
- **Catalog fixes:**
  - The two Google Memory Bank rows are likely duplicates.
  - Grok Memory, Tesla FSD and CoCounsel cite secondary sources.
  - LabGenius' URL points to an unrelated site.
  - ByteRover's homepage says MIT, but the catalog has Elastic-2.0.

## Models-ops family (109 rows) — research backfill complete

Three batches (`input-locus-models-ops-*.json` → `result-locus-models-ops-*.json`), 186 cells.

- **Rules added for this family:**
  - A model family that's sold both as a chat app and as an API under the same name is `both`: Claude, GPT, Gemini, Grok, DeepSeek and Qwen. Mistral and Llama are `platform`, because Le Chat and Meta AI carry different brands.
  - Open weights plus a public API makes a row `hybrid`.
  - Physical robots installed at a customer site get positioning only; locus is left empty.
  - Labelling and data services (Scale, Snorkel, Surge) get positioning only.

## Final coverage of the researched cells (695 non-paper rows)

| Cell | Rows filled | Breakdown |
|---|---|---|
| `architecture-deployment-locus` | 546 | local 182, cloud 170, hybrid 134, ide 19, computer-use 13, not-applicable 28 |
| `positioning-platform-vs-product` | 629 | platform 331, product 230, both 41, not-applicable 27 |
| `adoption-accelerator` | 60 | all Y Combinator; no `none` values written |

Rows still empty are those where the vendor's own page didn't settle the question: pages that block automated access, sites that render only with JavaScript, enterprise SaaS sites that don't say where they're hosted, and dead products.

All lifecycle leads from every batch are collected in `lifecycle-leads.md` for a re-verification pass. None has been applied, and each needs a primary-source check first.
