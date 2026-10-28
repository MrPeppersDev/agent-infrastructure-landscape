# Re-verification of the oldest rows — 2026-10-28

Targets: every row whose `last_verified_at` was before 2026-07-01 (298 rows: 87 agents, 8 memory, 203 memory-research), plus #57's open cells and the leftovers from the October pass. 285 of the 298 are now verified; 13 remain (listed at the end). Applied with `apply_reverify.py --date 2026-10-28`; per-row output is in `apply-report.md`.

## Files

| File | Rows | How |
|---|---|---|
| `input-agents.json` | 87 | snapshot of the agents rows given to the researchers |
| `result-agents-1.json`, `result-agents-2.json` | 44 + 43 | two research agents, WebFetch on vendor pages, PyPI/npm, GitHub search |
| `result-memory.json` | 8 | vendor sites and source articles |
| `result-research.json` | 192 of 203 | arXiv API (156 ids, none withdrawn), GitHub search for 54 linked repos (archived flag), Crossref for 3 ACM DOIs, HTTP check for the rest |
| `result-issue57.json` | 2 | Hume EVI, Jina AI Embeddings |
| `result-leftovers.json` | 4 | Strands, Galileo ×2, Sinequa |

## Lifecycle findings

**Acquired**
- **Calypso AI → F5** (announced 2025-09-11). [F5](https://www.f5.com/company/news/press-releases/f5-to-acquire-calypsoai-to-bring-advanced-ai-guardrails-to-large-enterprises)
- **Apex Security → Tenable.** Intent announced 2025-05-29; no closing notice found, and apex.security no longer resolves. [Tenable](https://www.tenable.com/press-releases/tenable-announces-intent-to-acquire-apex-security-to-expand-exposure-management-across-the-ai-attack-surface)
- **Common Room → Zoom.** Stated in the CEO's post of 2026-09-16; no Zoom release found. [Common Room](https://www.commonroom.io/blog/revenue-os/)
- **Composer → SoFi** (2026-06-23). [Composer](https://www.composer.trade/blog/composer-joins-sofi)
- **DX → Atlassian** (definitive agreement 2025-09-18). [Atlassian](https://www.atlassian.com/blog/announcements/atlassian-acquires-dx)
- **Promptfoo → OpenAI** (agreement 2026-03-09; the open-source project continues). [Promptfoo](https://www.promptfoo.dev/blog/promptfoo-joining-openai/)
- **Pincites → Filevine** (2026-01-14; now LOIS for Word). [Filevine](https://www.filevine.com/news/filevine-announces-lois-for-word-as-it-acquires-pincites/)
- **Tonkean → Coupa** (2026-05-21). [Coupa](https://www.coupa.com/newsroom/coupa-acquires-tonkean-to-accelerate-agentic-intake-and-orchestration-for-global-trade/)
- **OpenBB → OpenBQ.** The non-profit OpenBQ took over OpenBB's assets (announced 2026-10-01). The repo moved to `openbq-org/OpenBB` and the licence is now Apache-2.0. [OpenBB](https://openbb.co/)
- **Galileo → Cisco.** Announced 2026-04-09; completed by 2026-05-22, per the update on Cisco's post. [Cisco](https://blogs.cisco.com/news/cisco-announces-the-intent-to-acquire-galileo)

**Renamed**
- AuditBoard → Optro
- People.ai → Backstory
- Dynatrace Davis CoPilot → Dynatrace Assist
- Sysdig Sage → Sysdig GenAI Assistant
- Semgrep Assistant → Semgrep Multimodal. The only evidence is a docs redirect, so confidence is medium.

**Shutting down**
- **Hume EVI.** Hume will shut down the EVI and TTS APIs on 2026-11-13. [Hume docs](https://dev.hume.ai/docs/speech-to-speech-evi/overview)
  - The row stays active until that date, so it gets no decay cause (gate 5). The description carries the date instead.

**Maintenance**
- **Sakana AI Scientist:** last push 2025-12. Its licence is also corrected: it is not MIT.
- **Stanford STORM:** no push since 2025-09-30.

**Archived repos (research)**
- SmartPlay
- OpenAI Gym Retro
- Hanabi Learning Environment

## Corrections to wrong facts

- **Genie AI** was never acquired by Robin AI. Its own timeline shows a $17.8M Series A in 2023, led by GV and Khosla.
- **Cleric's seed** was $4.3M led by Zetta, not "$10M (Greylock + Innovation Endeavors)".
- **Hugo.legal** is a lawyer-matching service, not an AI research product. Confidence is medium.
- **Strands Agents** was announced on 2025-05-16, not in March 2025. The unverified line "predecessor of AWS Agent SDK / Bedrock AgentCore" is removed. [AWS](https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/)
- **SpecterOps BloodHound** has about 3.5k stars, not 12k.
- **Jina AI Embeddings:** the latest release is now recorded as jina-embeddings-v5-omni (2026-05-07) and Rerank v3.5 (2026-07-27). [Jina](https://jina.ai/models/)

## Not verified (13 rows left before 2026-07-01)

- **OpenReview papers (5).** OpenReview serves a challenge page to scripts, and its API does too: evolve-mem, memorizing-transformers, memreasoner, sers, and the JEPA position paper.
- **Repos not found by GitHub search (4).** These may be renamed, deleted or missing from the index:
  - ARMT (RodkinIvan/associative-recurrent-memory-transformer)
  - NLE (heiner/nle)
  - NIAH (gkamradt/LLMTest_NeedleInAHaystack)
  - osrs-bench
- **Sites unreachable (4):**
  - MDPI (403)
  - minerl.io (no response)
  - heypluto.ai (blocked by the session proxy)
  - robustintelligence.com (503)

## Left unchanged on purpose

- **Funding with secondary sources only:**
  - AlphaSense's $350M round (newsroom links to WSJ only)
  - 11x, Gong, Apollo, Endor and Anvilogic
- **Sinequa's acquisition date.** The site brands itself "Sinequa by ChapsVision", but no dated primary source was found.
- **mcp-support "no" was not written** for vendors whose pages simply don't mention MCP.
- **Possibly dead, no primary notice** (kept at lifecycle unknown):
  - linq.ai now belongs to an unrelated company.
  - reggie.ai is a parked domain.
  - toplyne.io shows a dead Wix page.
- **Pages returning 404** (parents active, lifecycle unknown): the Coalfire AIOps and Hyperproof Trust Center product pages.
