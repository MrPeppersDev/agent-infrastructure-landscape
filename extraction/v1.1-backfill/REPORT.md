# v1.1.0 research backfill — agents family (2026-10-28)

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
