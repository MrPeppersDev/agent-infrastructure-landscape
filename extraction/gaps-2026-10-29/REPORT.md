# Locus and positioning gaps — 2026-10-29

Rows whose `architecture-deployment-locus` or `positioning-platform-vs-product` cell was still empty after the #150 backfill. The earlier pass left them empty because the vendor pages blocked plain fetches, rendered only with JavaScript, or didn't say where the product runs. This pass used a headless Chromium (Playwright) for JavaScript-only pages. Applied with `apply_v1_1_research.py --date 2026-10-29`.

## Batch 1 (68 rows): 54 cells applied
- **Locus, 46:** cloud 38, local 6, hybrid 2.
- **Positioning, 8:** product 4, platform 2, both 2.
- **Dropped:** both Clio Duo cells. clio.com returns 403 to every automated fetch, and the values rested on search-result snippets of Clio's help pages.
- **Medium values worth a look:**
  - Claude memory tool → `local`: memory operations run client-side on storage the developer controls.
  - F5 AI Guardrails → `local`: F5 lists only customer-run deployments.
  - Dia → `local`: history is stored on the device by default.
  - Cognigy and DraftWise → `cloud`: on-prem is offered only as an enterprise arrangement.
- **Left empty:**
  - Robots, by rule: 1X, Agility, Apptronik, Collaborative Robotics, Figure.
  - Papers: DPO, GRPO.
  - Dead or rebranded: Continue.dev, Covariant, Adept, Apex Security, FutureHouse, Cellon (memory.inc now redirects to Pogl) and the Hyperproof AI Trust Center.
  - No primary statement: Anthropic Auto Dream, Era, Acuvity, Coalfire AI Ops, and locus for both Iris.ai rows.
- **Leads for a later pass:**
  - AuditBoard is now Optro, and BenevolentAI now sells Qor.
  - Enkrypt AI says it has joined Anaconda.
  - Backboard now leads with an inference-engine licence.
  - 01.AI suspended its international API.
  - Bee is now an Amazon product.

## Batch 2 (68 rows): 41 cells applied
- **Locus, 35:** cloud 31, ide 2 (Tabnine, Sweep), local 1 (JetBrains Junie), computer-use 1 (OpenAI Operator).
- **Positioning, 6:** product 5, platform 1 (Magnitude).
- **Dropped:** Sema4.ai `hybrid`. Neither of its deployments is public self-serve, so the hybrid definition doesn't fit.
- **Judgement calls under the "enterprise-only on-prem counts as cloud" rule:** Palantir Ontology and Tonkean LegalWorks. Both are `cloud`, medium.
- **Left empty:**
  - Dead or folded in: OctoAI (now NVIDIA), Sajari (Algolia), TruEra (Snowflake), Robust Intelligence (Cisco), SnapAttack (Splunk), Protect AI (Palo Alto), Toplyne, Pluto AI, K-Scale.
  - Robots and data services, by rule: Pickle, Sanctuary ×2, Skild, Scale AI, Snorkel, Surge, TRI LBM, Tesla FSD.
  - No product sold: Magic.dev, MemoraX AI, NeoCognition, LazyGraphRAG, Sakana AI Scientist, Numerai Signals, LabGenius.
  - No primary statement: Linq AI, Nyne, Lucidworks, Lasso, TopQuadrant, Edge Copilot.
- **Leads for a later pass:**
  - OpenMemory is now hosted by Mem0 only; the local Docker server is gone from the repo.
  - Operator became ChatGPT agent mode in July 2025.
  - Limitless was acquired by Meta and is winding down the Pendant and Rewind.
  - Junie now leads with a CLI.
  - Litera AI is now "Lito".
  - Sweep has pivoted to a JetBrains plugin.
  - Tana's outliner has moved to outliner.tana.inc.
  - Bee is now an Amazon product; Enkrypt AI has joined Anaconda.
