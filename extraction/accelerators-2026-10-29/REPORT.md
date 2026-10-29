# Accelerators other than Y Combinator — 2026-10-29

The schema accepts these programs since #308 (`docs/schema/adoption-accelerator.json` → `programs`). Candidates: the 631 non-paper rows with no accelerator yet (`input-candidates.json`). Two research agents worked from each program's own portfolio pages and matched names and domains to the catalog; they did not search company by company. Applied with `apply_v1_1_research.py --date 2026-10-29`: **50 rows**. As in the YC pass, a company's product rows share its value.

## Applied, by program
| Program | Rows | Companies |
|---|---|---|
| `ai-grant` (no year; aigrant.com gives batch numbers only) | 14 | Chroma, Cursor ×3, Perplexity ×4, Hume EVI, RunPod, Lindy ×2, Browserbase, Granola |
| `betaworks-camp` | 10 | Hugging Face ×9 (BotCamp 2016), Honcho / Plastic Labs (AI Camp 2023) |
| `techstars` | 5 | Comet ML (2017), Saner.ai (2024), Memgraph (2016), Outreach (2011), LogicGate (2016) |
| `aws-genai-accelerator` | 5 | Relevance AI, Cartesia, Enkrypt AI (2024); LlamaIndex ×2 (2025) |
| `cdl` | 3 | Lakera (2022), Mindgard (2023), Botpress (2019) |
| `seedcamp` | 3 | Meilisearch (2020), RunWhen (2023), Memories.ai (2025) |
| `google-for-startups` | 3 | Marqo (2024), Liner, ELSA Speak |
| `ef` | 2 | PolyAI, Genie AI |
| `antler` | 2 | Lovable ×2 |
| `sequoia-arc` (medium) | 2 | Pydantic ×2: Samuel Colvin is quoted on the Arc page about what he learned in Arc |
| `pioneer` | 1 | E2B |

## Dropped (17, in `dropped.json`)
- **Plug and Play, 14 rows** (Glean, Decagon, CrewAI, Sourcegraph and others). The startup pages list each company, but the "accelerated" status is only a hidden flag in the site's data, and no visible text says the company went through the accelerator.
- **Intercom Fin → 500 Global.** The batch ("GA 3") also comes only from the site's hidden data.
- **XBOW → Sequoia Arc.** The founder is featured on the Arc page, but nothing says XBOW took part.
- **Saner.ai → Google for Startups.** The row keeps its dated Techstars 2024 value.

## Coverage
- **Complete or near-complete lists:** AI Grant, Entrepreneur First, Antler (the public directory), a16z speedrun, South Park Commons, betaworks Camp, CDL, Seedcamp, Google for Startups (the alumni directory), AWS (about 97% of the cohorts), Alchemist (516 of its 750+), 500 Global.
- **Partial lists:**
  - Techstars: searched by candidate name and domain.
  - Pioneer, Neo and Sequoia Arc: no public roster.
  - HF0: no portfolio page.
  - PearX: only 4 cohort companies are named.
- **Near-misses not applied:**
  - South Park Commons lists Baseten, Cognition, Imbue and Nyne, but as fund investments rather than the Founder Fellowship.
  - Neo's page names Cursor and Cognition for "programs or seed funding" without saying which.
  - Pear lists Cognition and Voyage AI as investments only.
  - About a dozen same-name, different-company hits were rejected by domain.
