# Research notes, 2026-11-01

I used about 22 web searches. Sources are primary unless marked otherwise.

## 1. Sinequa (sinequa--sinequa-com): verified, acquired
- Fetched https://www.sinequa.com/company/press/chapsvision-strengthens-ai-capabilities-with-sinequa-acquisition-and-completes-new-us90m-funding-round/ . The release is dated Nov 18, 2024 (New York / Paris) and says ChapsVision "has announced the acquisition of Sinequa". It is written as a completed deal, with no pending conditions.
- The ChapsVision-hosted copy (chapsvision.com/press-release/chapsvision-accelerates-ai-expansion-with-sinequa-acquisition-and-completes-a-3rd-fundraising/) returned 429. Search shows it posted 2024-11-25 and the French release dated 2024-11-18. The Business Wire copy returned 403.
- Conclusion: the existing "2024-11" is correct. I proposed the exact day (2024-11-18) and a citation from the company's own site instead of Business Wire.

## 2. Apex Security (apex-security--apex-security): verified, acquired
- Tenable press release, dated 2025-05-29: https://www.tenable.com/press-releases/tenable-announces-intent-to-acquire-apex-security-to-expand-exposure-management-across-the-ai-attack-surface . It states intent to acquire, terms not disclosed, close expected later that quarter.
- Tenable's Q2 2025 results (8-K exhibit, 2025-07-30): https://www.sec.gov/Archives/edgar/data/1660280/000166028025000087/q22025financialresults-ear.htm . It says "Completed our acquisition of Apex Security" but gives no exact close date. Closed by 2025-07-30.
- The ~$105M price comes only from press reports (Calcalist) and is not in the update.

## 3. Common Room (common-room--commonroom-io): verified, acquired
- Zoom blog post by CSO Abhisht Arora, 2026-07-02: https://www.zoom.com/en/blog/zoom-to-acquire-common-room/ . It covers the definitive agreement, says terms were not disclosed, and an update line says "The transaction closed in July 2026".
- Zoom investor release https://investors.zoom.us/news-releases/news-release-details/zoom-acquire-common-room-bringing-buyer-intelligence-its-ai returned 403 and could not be read.
- Common Room's own post https://www.commonroom.io/blog/revenue-os/ (2026-09-16) says "Zoom acquired Common Room", and its homepage now presents "Common Room + Zoom".

## 4. Funding totals
- **AlphaSense**: updated. https://www.alpha-sense.com/press/alphasense-raises-350m-at-7-5b-valuation-and-surpasses-600m-in-annual-recurring-revenue/ (2026-06-03): $350M at $7.5B, led by Vitruvian, Accenture Ventures and J.P. Morgan AM. D. E. Shaw Ventures and Pinegrove also invested. Total funding is "well over $1 billion".
- **Endor Labs**: updated. https://endorlabs.com/learn/why-we-raised-a-93m-series-b-in-this-market (2025-04-23): $93M Series B led by DFJ Growth, with Salesforce Ventures. The current "$93M total" was really the Series B amount. No primary page states a cumulative total, so the update gives none.
  - CB Insights lists Endor as "Acquired 2/11/2026" (secondary). The endorlabs.com homepage shows no acquisition and I found no primary source, so it is unverified and not applied.
- **11x**: no change. The 11x.ai homepage has no funding or newsroom page, and search found nothing newer than the Series B. I can't verify the current value's date (search shows the round closing Nov 2024 vs the stored "Oct-2024") against a primary page.
- **Gong**: no change. Page 1 of the gong.io/press newsroom (Mar–Oct 2026) has no funding release. Only a 2026-05-12 "ARR tops $500M" release appears. One aggregator claims a "$250M Series F Oct-2025", which I could not verify.
- **Apollo.io**: no change. apollo.io/newsroom shows no new round, only a Pocus acquisition (Mar 2026, via Built In). Search found no round after Aug-2023.
- **Anvilogic**: no change. No 2025/26 round turned up. Anvilogic's press pages (/news, /press-releases) return 404.
  - Secondary sources (SecurityWeek, Cervin Ventures 2024-04-17) date the $45M Series C to **April 2024**, not "Jul-2024" as stored. I found no primary page, so this is not applied. It is worth a follow-up.

## 5. Databricks / MLflow: verified
- Databricks newsroom chronology:
  - Series J, $62B, Dec-2024
  - Series K at >$100B, 2025-08-19
  - Series L of >$4B at $134B, 2025-12-16
  - "Raising strategic round at $188B" (Coatue, term sheet), 2026-07-16: https://www.databricks.com/company/newsroom/press-releases/databricks-raising-strategic-round-funding-188-billion-valuation
  - **Closed $5B strategic round at $190B valuation**, 2026-08-13: https://www.databricks.com/company/newsroom/press-releases/databricks-grows-80-yoy-surpasses-7b-revenue-run-rate-scales . Led by Coatue, with Blackstone, MGX and T. Rowe Price.
- No Databricks page states a cumulative total raised, so both proposed texts drop the "$20.2B total" and "$43.2B" figures. MLflow's "$43.2B" looks like a confusion with the Series I $43B valuation.

## 6. Lifecycle
- **Vellum (vellum-ai--vellum-ai)**: verified, set to deprecated. https://www.vellum.ai/vellum-assistant-platform-shutdown says the Personal Assistant Platform shuts down on Nov 2, 2026. After that, cloud assistants stop working, "you will not be able to log in to www.vellum.ai", and data is deleted. Self-hosted assistants keep working, but the OSS repo will no longer be actively maintained.
  - The page has no publication date. A tracker dates it around 2026-10-23.
  - I used "deprecated" because today is Nov 1. Re-mark as dead after Nov 2.
  - The notice does not mention the legacy Workflows/LLM-dev product. Because vellum.ai login ends, it effectively ends the hosted service.
- **K-Scale Labs (k-scale-labs--kscale-dev)**: set to dead, medium confidence.
  - kscale.dev does not resolve (DNS EAI_AGAIN from this session, so that alone is not conclusive).
  - The Robot Report (2026-03-02) carries a first-hand piece by former COO Rui Xu: https://www.therobotreport.com/6-lessons-learned-watching-a-robotics-startup-die-from-the-inside/ . It says "The company shut down in late 2025" and open-sourced its IP.
  - I found no primary company statement; the founder's farewell letter was reported by 36Kr but not fetched.
  - The github.com/kscalelabs org has no shutdown banner, and some repos are still being pushed (kinfer, Oct 2026), probably by the community or ex-staff. So the OSS code lives on but the company is gone.
- **Pachyderm (pachyderm-hpe--pachyderm-com)**: not verified, left out of results.
  - github.com/pachyderm/pachyderm is not archived and shows no EOL notice. The last commit on master was 2025-01-09.
  - pachyderm.com does not resolve from this session. HPE's docs host (docs.ai-solutions.ext.hpe.com) is blocked by the session's network allowlist. A search snippet shows it still listing "Data Management" (MLDM) with release notes.
  - I found no HPE EOL/end-of-sale notice. The repo has been dormant for 22 months, but there is no primary statement of maintenance or deprecation. Suggest someone with network access check HPE's docs/lifecycle page.

## 7. Rows that may point at the wrong company
- **linq-ai--linq-ai** (record: "AI agent for financial analysts", SF, founded 2023): **wrong company**. https://www.linq.ai/ is LINQ.AI, an ed-tech company (Oxygen Platform, online degree programs).
  - The likely intended product is **LinqAlpha** (https://www.linqalpha.com/): "the first domain-specialized multi-agent AI platform for investment research" for hedge funds, asset managers and banks.
  - The LinqAlpha homepage does not state HQ, founding year or funding, so I could not confirm the record's other facts belong to it. I left links unchanged. Recommend renaming/re-pointing it to LinqAlpha and re-researching the cells.
- **reggie-ai--reggie-ai**: www.reggie.ai 307-redirects to a GoDaddy "for sale" parked page.
  - https://www.regie.ai/ is a live AI sales product (RegieGO, "agentic sales workspace" with AI prospecting agents), but its homepage names no founders or funding.
  - The record's facts (founders "Tomer Sole + Yair Snir", "$4.7M seed Jul-2024 Lightspeed + Mantis") could not be matched to Regie.ai or anything else. They may be fabricated, so they should not simply be moved onto Regie.ai.
  - Recommendation: either retire the record as unverifiable or re-research it as Regie.ai from scratch. Not put in results.
- **toplyne--toplyne-io**: dead (in results).
  - www.toplyne.io and toplyne.io return 404.
  - Inc42 (2024-10-11, secondary): https://inc42.com/?p=481809 . It quotes CEO Rishen Kapoor's LinkedIn post: "we've made the tough decision to wind down operations and return capital to our investors". I could not fetch the LinkedIn post itself, hence medium confidence. No acquisition was reported.
- **coalfire-ai-operations--coalfire-com**: the record URL https://coalfire.com/services/advisory/ai-security-and-trust-engineering is live ("Coalfire AI Security and Trust Engineering", offerings CoalfireForgeAI / LegionAI / GuardianAI).
  - The `links` cell (www.coalfire.com/services/managed-services/aiops) returns 404, so results include a links update.
  - The record name "Coalfire AI Operations" no longer matches any product. Consider renaming to "Coalfire AI Security and Trust Engineering" (keep the id).
- **hyperproof-ai-trust-center--hyperproof-io**: not put in results.
  - https://hyperproof.io/trust-center/ returns 404, and I found no standalone trust-center product page.
  - https://trust.hyperproof.io/ is Hyperproof's own security trust portal, not a product.
  - The capability now lives inside the GRC platform. The homepage has a "Trust" tab: "Automate trust center operations and streamline security questionnaire responses with verified control data". https://hyperproof.io/product/hyperproof-ai/ lists "Security questionnaire responses" but does not claim AI auto-fill.
  - Recommendation: re-point links to https://hyperproof.io/product/hyperproof-ai/ or merge into a Hyperproof platform record if one exists. The standalone "AI Trust Center" product framing is not supported by current pages.
