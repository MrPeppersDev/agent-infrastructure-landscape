# Lifecycle leads re-verification (2026-10-29)

The v1.1.0 research (`extraction/v1.1-backfill/lifecycle-leads.md`) turned up about 120 unverified lifecycle leads. They were matched to 160 catalog rows. Four agents then checked each row on primary sources only: the company's own site, docs, blog or repo, or the acquirer's press release. Applied with `apply_reverify.py --date 2026-10-29`; the per-row log is in `apply-report.md`.

**Outcome:** 154 rows verified, 6 left unverified. 89 cells changed, 9 records renamed, 51 URLs moved, and 8 new decay causes. Separately, one duplicate row was merged (`extraction/merges-2026-10-29/`), so the catalog now has 951 records.

## Findings

- **Acquired (23):**
  - Augment Code: Harness bought select assets, 2026-10-08 (not one of the leads).
  - Chroma: definitive agreement to join Replit, 2026-10-23. Chroma Cloud winds down; writes stop 2026-11-22, and the OSS project continues.
  - Gitpod/Ona: OpenAI, closed 2026-08-10; Ona Cloud ends 2026-10-31.
  - Portkey: Palo Alto Networks; now Prisma AIRS AI Gateway.
  - Dagster: Prefect, letter dated 2026-07-13.
  - Stack AI: Asana.
  - Quickwit: Datadog.
  - Limitless: Meta.
  - Outerbounds: Anaconda.
  - Continue: Cursor; the repo is read-only.
  - Pincites: Filevine; now LOIS for Word.
  - Lakera: Check Point.
  - Search.io: Algolia, per Algolia's own release.
  - Already in the catalog, now re-confirmed: Protect AI, Robust Intelligence and SnapAttack (dates corrected from Cisco's and Splunk's own pages), Tonkean, Argilla, TruEra, OctoAI, W&B (now CoreWeave Forge), Pachyderm, Bee.
- **Dead or discontinued (11):**
  - Lutra AI (vendor notice).
  - Project Mariner (shut down 2026-05-04).
  - Roo Code and its .roorules row (shut down 2026-05-15).
  - Patronus AI (eval platform retired; now a research lab).
  - Humanloop (sunset after joining Anthropic).
  - Spirit AI (London Gazette liquidation notice).
  - Reggie.ai and Heyday (domains parked or for sale; medium confidence).
  - The two Continue rules/MCP rows.
- **Archived (12):** Bytebot, GPT Engineer, InstructLab, Acontext, Atlas, ByteRover CLI, Flowise, Mem0 MCP, Kuzu, Cleanba, TGI, torchtune.
- **Deprecated (6):**
  - Amazon Q Developer (IDE plugins end 2027-04-30; successor Kiro).
  - OpenAI Swarm (Agents SDK).
  - Speechmatics Flow (now Agent STT).
  - Redis Agent Memory Server (now managed on Redis Cloud).
  - Marqo OSS.
  - Magnitude (now a local inference engine).
- **Renamed (12):**
  - CrewAI Enterprise → CrewAI AMP
  - ElevenLabs Conversational AI → ElevenAgents
  - MultiOn → AGI, Inc.
  - MemWal → Walrus Memory
  - Mistral Le Chat → Vibe
  - Databricks Vector Search → AI Search
  - TopBraid EDG → TQ Data Foundation (inferred from the site)
  - Vertex AI → Gemini Enterprise Agent Platform
  - Edge Copilot Mode, Windsurf and Memory Bank were already reflected and are now confirmed.
- **Maintenance (7):**
  - Semantic Kernel and its memory row: Microsoft keeps shipping critical fixes, and Agent Framework is the successor.
  - GraphRAG, AutoRAG (legacy library) and Helicone.
  - Hume EVI and Vellum: both are still live until 2026-11-13 and 2026-11-02 respectively. They're recorded as maintenance so gate 5 doesn't flag a decay cause on a live product; the shutdown dates are in their descriptions.
- **Corrections:**
  - Reka was never acquired by Snowflake (its funding cell already said so).
  - Gemini CLI: replaced by Antigravity CLI only for free and consumer tiers; still supported for enterprise.
  - Aleph Alpha's PhariaAI docs are still current.
  - Pachyderm's LICENSE file is Apache-2.0, so the README badge lead was refuted.
  - LabGenius's real site is labgeniustx.com.
  - Roo Code's `gh` and `license` cells were wrong.
- **Moved URLs (51):** A2A, Burr, Goose, OpenHands, Pydantic AI, Vercel AI SDK, Cognition, CoCounsel, Cloudflare Agent Memory, Microsoft Recall, Luminance, Palantir, Supabase Vector, Physical Intelligence, OpenMind, GR00T, Gemini 3, Amazon Nova, Phi-4, Mistral Large 2, and others.

## Not applied

- **Unverified (6):** Pluto AI, Toplyne, Grok Memory, Krutrim Kruti, MemoraX, Tesla FSD. Their only evidence was a site that doesn't load or a secondary source.
- **Unknown (9):** Cursor Memories (its docs page is gone, but the only removal statement is a forum reply), Steamship, Covariant, Soul Machines, LawDroid Copilot, Linq AI, OpenAI Deep Research (openai.com blocks automated access), Anthropic Auto Dream, LazyGraphRAG.
- **Probably in the wrong section:** Hugo.legal (a human lawyer service), Linq AI (the domain now belongs to an unrelated company), LawDroid, Magnitude.
