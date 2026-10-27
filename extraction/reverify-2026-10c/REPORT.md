# Re-verification 2026-10-27 — frameworks group (42 rows)

- rows seen: 42
- rows verified: 42
- cells applied: 193
- cells skipped: 0
- decayed: 5
- renamed: 0
- url changed: 0
- taxonomy set: 0

## Lifecycle changes found

- **GPT Engineer** — archived: Repository archived by the owner on 2026-04-22; last PyPI release v0.3.1 on 2024-06-06; README points to gptengineer.app/Lovable and aider. ([source](https://github.com/AntonOsika/gpt-engineer))
- **Gitpod AI features** — acquired: Gitpod renamed itself Ona on 2025-09-02; OpenAI agreed to acquire Ona on 2026-06-11 (closed 2026-08-10, team joined Codex) and Ona Cloud is being wound down on 2026-10-31. ([source](https://ona.com/stories/ona-joins-openai))
- **InstructLab (Red Hat / IBM)** — archived: instructlab/instructlab repository archived on 2026-04-23 (last PyPI release v0.26.1 on 2025-05-05); README points to successor SDG Hub and Training Hub repos. ([source](https://github.com/instructlab/instructlab))
- **Magnetic-One** — deprecated: Magentic-One ships in AutoGen (autogen-ext, last release v0.7.5 on 2025-09-30); the microsoft/autogen README now states the project is archived and no longer maintained, with Microsoft Agent Framework as successor. ([source](https://github.com/microsoft/autogen))
- **MetaGPT** — maintenance: Repo (now FoundationAgents/MetaGPT) last pushed 2026-01-21 and last PyPI release v0.8.2 on 2025-03-09; not archived; team focus moved to the MGX (MetaGPT X) product. ([source](https://github.com/FoundationAgents/MetaGPT))
- **Microsoft AutoGen Studio** — deprecated: The microsoft/autogen README now states AutoGen is archived and no longer maintained (no bug or security fixes), naming Microsoft Agent Framework as successor; autogenstudio last released v0.4.2.2 on 2025-05-27. ([source](https://github.com/microsoft/autogen))
- **Microsoft Semantic Kernel** — maintenance: README: "Semantic Kernel is now Microsoft Agent Framework"; SK v1.x still gets critical bug and security fixes and releases (Python v1.45.0, 2026-10-06) while new features go to Agent Framework. ([source](https://github.com/microsoft/semantic-kernel))
- **MultiOn** — renamed: As of 2026-10-27 www.multion.ai 301-redirects to theagi.company (AGI, Inc., building the AGI-0 on-device mobile action agent); the MultiOn Agent V1 Beta docs remain online but the multion Python SDK was last released 2024-10-08. ([source](https://theagi.company/))
- **OpenAI Swarm (deprecated)** — deprecated: The README states Swarm is replaced by the OpenAI Agents SDK (pointer added 2025-03-11); the repo is not archived and its only later commit is a 2026-04-15 pre-commit pin, with no tagged releases. ([source](https://github.com/openai/swarm))
- **Steamship** — dead: As of 2026-10-27 www.steamship.com and docs.steamship.com serve expired TLS certificates/503 and steamship.com returns 404; the steamship SDK was last released 2024-01-24 and the python-client repo last pushed 2024-02-14. ([source](https://pypi.org/project/steamship/))

## Method

- `registry-frameworks.json`: latest version, upload date and license pulled directly from the PyPI JSON API and the npm registry on 2026-10-27 (used for every `latest-release`).
- Two research agents checked 21 rows each (`result-frameworks-a.json`, `result-frameworks-b.json`) against GitHub repo pages, LICENSE/README files, official docs and pricing pages. WebFetch on known URLs; one web search in total.
- Applied with `scripts/apply_reverify.py --date 2026-10-27`, then `make build validate lint` (7/7 gates, 0 lint findings) and the MCP + worker test suites.
- Spot-checked independently before applying: Ona joining OpenAI (ona.com/stories/ona-joins-openai), the daytonaio/daytona archive banner, and the AutoGen "archived and no longer maintained" README notice.

## Notable corrections

- **Licenses:** Mastra is Apache-2.0 (with `ee/` enterprise directories), not Elastic-2.0. Agno is Apache-2.0, not MPL-2.0 (both rows). The Inngest server is SSPL-1.0, with each release converting to Apache-2.0 after three years. The Restate server is BUSL-1.1, while its SDKs are MIT. The MCP spec and reference servers are moving from MIT to Apache-2.0.
- **Language filter (`runtimes`):** now filled for every framework row. LangChain, LangGraph, LlamaIndex, the OpenAI Agents SDK and Strands are Python and TypeScript. Mastra, the Vercel AI SDK, Eliza and Trigger.dev are TypeScript. Temporal covers 8 SDK languages, Restate 7, Inngest 5, and Semantic Kernel C#, Python and Java.
- **MCP spec:** donated to the Linux Foundation's Agentic AI Foundation, announced 2025-12-09 (https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation). This confirms the HANDOFF lead.
- **Marvin / ControlFlow:** the description had the merge direction reversed. Marvin 3.0 absorbed ControlFlow's engine, and the ControlFlow repo was archived on 2026-03-19. This resolves the HANDOFF lead.
- **Daytona:** core development went private in 2026-06, and the daytonaio/daytona monorepo was archived on 2026-10-03. The product and its SDKs (`daytona/clients`, released 2026-10-23) are live. `gh` now points at `daytona/clients` so the stack check doesn't flag a live product as archived.
- **Reflection AI** has pivoted to an open-weight model lab (Beam). **OpenHands** moved to the OpenHands org. **Strands** renamed its Python repo to `strands-agents/harness-sdk`.

## Judgement calls

- **Microsoft Semantic Kernel → `maintenance`, not `deprecated`.** The README names Microsoft Agent Framework as the successor, but SK v1.x still ships releases with bug and security fixes.
- **Microsoft AutoGen Studio:** the agent marked it `deprecated`, and AutoGen is unmaintained per its README. Validation gate 5 rejects `decay_cause=superseded` on rows whose last release falls inside the active window, so the decay was removed. The new description carries "no longer maintained", which `build_stack_index.py` turns into a `deprecated` status.
- **StackBlitz WebContainers `gh`:** reworded to "runtime source is not published" so the contradiction lint doesn't read it as a closed-source claim.

## Code change

- `mcp/src/compat.ts`: "MCP Servers (Reference)" lost its parenthetical to the bare alias "MCP Servers", which now matches most of the new `mcp-support` cells (39 documented links; the test limit is 30). Generic base names now use the full name, and `taxonomy/system-aliases.json` adds specific aliases (`modelcontextprotocol/servers`, "MCP reference servers").

## Migration notes added (`data/migrations.json`)

- **Magentic-One and AutoGen Studio → Microsoft Agent Framework:** official AutoGen migration guide, including `MagenticBuilder`.
- **Gitpod (Ona) → OpenAI Codex cloud:** Ona Cloud shuts down on 2026-10-31.
- **InstructLab → sdg_hub / training_hub:** per the archived repo's README.
- **Semantic Kernel:** the existing note's successor id now resolves to `microsoft-agent-framework--gh-microsoft-agent-framework`.

## Left unchanged (couldn't verify)

- **Funding:** every funding cell.
- **MCP support:** E2B (docs returned 405), Marvin, Temporal, Restate and Swarm.
- **Deployment and pricing:** Sema4.ai (site returned 403). Deployment for the MCP spec, WebContainers, Workato and Steamship.
- **Gitpod:** post-shutdown deployment and pricing.
- **Strands:** the description's "predecessor of AWS Agent SDK" claim.

---

# Re-verification 2026-10-27 — models-a group (45 rows)

- rows seen: 45
- rows verified: 45
- cells applied: 179
- cells skipped: 0
- decayed: 2
- renamed: 0
- url changed: 0
- taxonomy set: 0

## Lifecycle changes found

- **Argilla** — maintenance: README says the original authors have moved on and only bug fixes/patches will ship; last PyPI release 2.8.0 on 2025-03-10 and last develop commit 2025-08. ([source](https://github.com/argilla-io/argilla))
- **Bonito** — maintenance: Only PyPI release bonito-llm 0.1.0 was 2025-02-12 and the repo was last pushed 2025-07; not archived. ([source](https://github.com/BatsResearch/bonito))
- **Cleanba** — maintenance: Last commit 2024-08-22; README says the repo is intended for archiving purposes and work moves to CleanRL; not archived on GitHub. ([source](https://github.com/vwxyzjn/cleanba))
- **Composer (MosaicML)** — archived: GitHub repo archived by the owner on 2026-10-23 (read-only); last PyPI release mosaicml 0.32.1 on 2025-07-26. ([source](https://github.com/mosaicml/composer))
- **DVC** — acquired: lakeFS (Treeverse) acquired the DVC open-source project from Iterative.ai on 2025-11-18; DVC continues as an Apache-2.0 tool under github.com/treeverse/dvc with v3.67.1 released 2026-03-31. ([source](https://lakefs.io/media-mentions/lakefs-acquires-dvc-uniting-data-version-control-pioneers/))
- **Distilabel** — maintenance: README says the original authors have moved on and community collaborators maintain it; fix commits landed 2026-10-06 but the last PyPI release is 1.5.3 (2025-01-28). ([source](https://github.com/argilla-io/distilabel))
- **Galileo** — acquired: Cisco completed its acquisition of Galileo (announced Apr 2026); the product is now Splunk Agent Observability and galileo.ai/pricing redirects to Splunk. ([source](https://www.splunk.com/en_us/about-splunk/acquisitions/galileo.html))
- **Helicone** — maintenance: Mintlify announced the acquisition of Helicone on 2026-03-03 and put the product in maintenance mode (security fixes, bug fixes, new models); helicone.ai now says Helicone is no longer part of Mintlify, with details to come. ([source](https://www.mintlify.com/blog/mintlify-acquires-helicone))
- **Humanloop** — dead: The Humanloop team joined Anthropic and the platform was sunset: billing stopped 2025-07-30 and all accounts and data were deleted on 2025-09-08. ([source](https://humanloop.com/docs/guides/migrating-from-humanloop))

## Method

As for the frameworks group: a PyPI/npm snapshot (`registry-models-a.json`) plus two research agents (`result-models-a-1.json` with 23 rows, `result-models-a-2.json` with 22). They used GitHub repo pages, LICENSE/README files, vendor docs, pricing pages and press pages. Six web searches in total.

## Notable findings

- **lakeFS license change:** from v1.87.0 (2026-09-22) the Community edition is BUSL-1.1, and each release converts to Apache-2.0 after 4 years (https://lakefs.io/blog/lakefs-business-source-license/).
- **DVC:** taken over by lakeFS (Treeverse) from Iterative.ai on 2025-11-18; the repo is now treeverse/dvc.
- **Galileo:** acquired by Cisco and now sold as Splunk Agent Observability (https://www.splunk.com/en_us/about-splunk/acquisitions/galileo.html). Its Series B was 2024-10, not 2024-06.
- **Humanloop:** shut down, with all data deleted on 2025-09-08; the team joined Anthropic. Confirms the HANDOFF lead.
- **Helicone:** Mintlify acquired it (2026-03-03) and put it in maintenance mode. helicone.ai now says it is "no longer part of Mintlify".
- **Covariant was not acquired.** Amazon took a non-exclusive model license and hired the founders (https://www.aboutamazon.com/news/company-news/amazon-covariant-ai-robots). The description no longer says "acqui-hired". This corrects the HANDOFF lead.
- **Composer (MosaicML):** archived on 2026-10-23. **Argilla and Distilabel** are maintenance-only per their READMEs.
- **Smaller corrections:**
  - Arize Phoenix is Elastic-2.0.
  - Megatron-LM/Core is BSD-3-Clause (PyPI metadata says Apache).
  - LLaMA-Factory's repo is now hiyouga/LlamaFactory.
  - Figure's Series C was over $1B at a $39B valuation (2025-09).
  - Apptronik's Series A now totals over $935M.

## Judgement calls

- **K-Scale Labs:** the agent marked it `dead` on a secondary source (36kr). The kscalelabs GitHub org still shows pushes (kinfer, 2026-10-17), so lifecycle is `unknown` and nothing is decayed.
- **Figure `latest-release`:** trimmed to "Helix 2.5 (2026-09-17)".
- **Gemini Robotics `latest-release`:** dropped because the page gives no dates.
- **Cleanba:** written as "no releases", the catalog's existing wording.

## Migration notes

- **Humanloop → Langfuse / Braintrust:** the two alternatives named in Humanloop's own migration guide.
- **Composer:** no note, because the README names no successor.

## Left unchanged (couldn't verify)

- **Funding:** Anyscale (sources conflict), Collaborative Robotics, Covariant's "$1.5B licensing fee", Baseten, Braintrust, Arize, Comet, ClearML, Dagster, Fireworks, Labelbox, Label Studio, LiteLLM, lakeFS and Flyte/Union.
- **Galileo:** the acquisition date isn't on any primary page.
- **MCP support:** wherever docs didn't settle it.

---

# Re-verification 2026-10-27 — models-b group (46 rows)

- rows seen: 46
- rows verified: 46
- cells applied: 163
- cells skipped: 0
- decayed: 0
- renamed: 0
- url changed: 0
- taxonomy set: 0

## Lifecycle changes found

- **OctoAI (now NVIDIA)** — acquired: NVIDIA acquired OctoAI in 2024 (per NVIDIA developer-blog author bio); octo.ai now 301-redirects to nvidia.com, so the OctoAI service is no longer offered. ([source](https://developer.nvidia.com/blog/author/benhamm/))
- **Outerbounds** — acquired: Anaconda announced its acquisition of Outerbounds on 2026-04-29 (closing not stated); outerbounds.com shows an Outerbounds is joining Anaconda banner and /pricing redirects to anaconda.com. Metaflow stays open source. ([source](https://www.anaconda.com/blog/anaconda-acquires-outerbounds))
- **QLoRA** — maintenance: The official implementation artidoro/qlora is not archived, but its last push was 2024-06-10 and the README updates stop at 2023-07; QLoRA lives on in bitsandbytes/PEFT. ([source](https://github.com/artidoro/qlora))
- **RL4LMs** — maintenance: allenai/RL4LMs is not archived but has had no pushes since 2024-03-01; the last dated changelog entry is v0.2.0 (2022-11-23) and nothing is published on PyPI. ([source](https://github.com/allenai/RL4LMs))
- **RLHFlow** — maintenance: Repo not archived, but no commits since 2025-04-24 and no releases as of 2026-10-27. ([source](https://github.com/RLHFlow/RLHF-Reward-Modeling))
- **Replicate** — acquired: Cloudflare announced the acquisition 2025-11-17 and closed it 2025-12-01 (Replicate is officially part of Cloudflare); Replicate continues as a distinct brand and its API is unchanged. ([source](https://blog.cloudflare.com/why-replicate-joining-cloudflare/))
- **Text Generation Inference (TGI)** — archived: README declared maintenance mode, recommending vLLM, SGLang, llama.cpp or MLX instead; the repo was archived (read-only) on 2026-03-21, and the last release was v3.3.7 on 2025-12-19. ([source](https://github.com/huggingface/text-generation-inference))
- **TruEra** — acquired: On 2024-05-22 Snowflake announced a definitive agreement to acquire the TruEra AI observability platform (terms undisclosed); truera.com now shows a join-Snowflake banner and redirects. ([source](https://www.snowflake.com/en/blog/snowflake-acquires-truera-to-bring-llm-ml-observability-to-data-cloud/))
- **Weights & Biases** — acquired: CoreWeave completed its acquisition of Weights & Biases on 2025-05-05; wandb.ai now says "Weights & Biases is now part of CoreWeave Forge", and wandb.ai/site/pricing redirects to CoreWeave Forge pricing. ([source](https://investors.coreweave.com/news/news-details/2025/CoreWeave-Completes-Acquisition-of-Weights--Biases/default.aspx))
- **torchtune (PyTorch)** — maintenance: README says torchtune is no longer actively maintained and development wound down in 2025; last release v0.6.1 on 2025-04-07, and the last commit (2026-04-23) added that notice. Not archived. ([source](https://github.com/pytorch/torchtune))

## Method

Same as the earlier groups: a PyPI/npm snapshot (`registry-models-b.json`) plus two research agents (`result-models-b-1.json` and `result-models-b-2.json`, 23 rows each). Four web searches in total.

## Notable findings

- **Weights & Biases:** acquisition by CoreWeave completed 2025-05-05; W&B is now part of CoreWeave Forge (https://investors.coreweave.com/news/news-details/2025/CoreWeave-Completes-Acquisition-of-Weights--Biases/default.aspx). Confirms the HANDOFF lead.
- **Replicate:** joined Cloudflare; announced 2025-11-17, closed 2025-12-01 (https://blog.cloudflare.com/why-replicate-joining-cloudflare/). Confirms the HANDOFF lead.
- **Scale AI:** Scale's own post dates the Meta deal 2025-06-12, describes a minority stake, and gives a valuation of over $29B (https://scale.com/blog/scale-ai-announces-next-phase-of-company-evolution). The funding cell is corrected. Confirms the HANDOFF date lead.
- **Acquisitions:**
  - **OctoAI:** acquired by NVIDIA (NVIDIA staff bio; octo.ai redirects to nvidia.com).
  - **TruEra:** joined Snowflake.
  - **Outerbounds:** acquisition by Anaconda announced 2026-04-29, close not confirmed, so the row stays active.
- **Text Generation Inference:** maintenance mode, then archived 2026-03-21. The README recommends vLLM or SGLang, or llama.cpp/MLX for local use.
- **torchtune:** the README says it is no longer actively maintained and development ended in 2025.
- **Funding:**
  - Snorkel AI: $350M Series E (2026-09-22) and a pivot to expert data and evals.
  - Together AI: $800M Series C (2026-07-01).
- **Other changes:**
  - Physical Intelligence: Pi API beta (2026-10-13) and pi0.7.
  - Sanctuary AI: strategy shift to hardware-agnostic Physical AI.
  - OM1: moved to a Go runtime.
  - GR00T: now N1.7.
  - Repo moves: Ragas to vibrantlabsai/ragas, verl to verl-project/verl, torchtune to meta-pytorch.

## Judgement calls

- **Vellum:** the agent proposed `deprecated`. Vellum's shutdown notice (2026-11-02) covers only its new Personal Assistant Platform. It says nothing about the LLM development platform, whose SDK last released 2026-10-02. Lifecycle is set to `unknown`; the description records the pivot.
- **torchtune:** the description now carries the README's maintenance notice, so the stack check flags it.
- **TRI `latest-release`:** shortened to the paper title and date.

## Migration notes

- **Text Generation Inference → vLLM / SGLang:** per the archived repo's README.

## Left unchanged / to review

- **Scale AI desc:** still has the "$14B / 49%" figures from secondary press; Scale's post doesn't state them.
- **Nemotron:** the row URL now returns 404 and needs a replacement.
- **Pachyderm:** status unknown; its site was unreachable.
- **Funding:** not re-checked for Surge AI, Roboflow, RunPod, Vellum, ZenML, Unsloth, Modal, Patronus, Portkey or PromptLayer.

---

# Re-verification 2026-10-27 — harnesses group (16 rows)

- rows seen: 16
- rows verified: 16
- cells applied: 40
- cells skipped: 0
- decayed: 3
- renamed: 1
- url changed: 0
- taxonomy set: 0

## Lifecycle changes found

- **Cursor (IDE)** — acquired: Cursor (Anysphere) announced on 2026-08-14 that it has officially been acquired by SpaceX (terms undisclosed); the product continues under the Cursor brand. ([source](https://cursor.com/blog/joining-spacex))
- **Lutra AI** — dead: As of 2026-10-27 lutra.ai shows only a notice that support for Lutra has been discontinued; the shutdown date is not stated. ([source](https://lutra.ai/))
- **OpenAI Operator** — deprecated: The standalone Operator site operator.chatgpt.com now returns a 308 redirect to ChatGPT agent mode (chatgpt.com/?system_hints=agent), checked 2026-10-27; the OpenAI announcement pages could not be fetched (HTTP 403). ([source](https://operator.chatgpt.com/))
- **Project Mariner** — dead: Google states Project Mariner was shut down on 2026-05-04 and points users to Gemini for complex tasks; the DeepMind product page now redirects to the DeepMind homepage. ([source](https://labs.google.com/mariner/))
- **Windsurf (now Devin Desktop)** — renamed: Cognition renamed Windsurf to Devin Desktop on 2026-06-02; windsurf.com now 308-redirects to devin.ai/desktop and existing plans and pricing carry over. ([source](https://devin.ai/blog/windsurf-is-now-devin-desktop))

## Method

One research agent checked vendor blogs, changelogs, pricing pages and acquirers' posts; it used two web searches, only to find the primary pages. The Cursor, Windsurf and Mariner pages were re-checked independently before applying (Mariner from its raw HTML).

## HANDOFF leads

- **Cursor — confirmed, date corrected.** "Cursor has officially been acquired by SpaceX", posted 2026-08-14, not 2026-06 (https://cursor.com/blog/joining-spacex). The brand continues.
- **Windsurf — confirmed.** Renamed Devin Desktop on 2026-06-02 (https://devin.ai/blog/windsurf-is-now-devin-desktop). The record is now "Windsurf (now Devin Desktop)"; the id is unchanged.
- **Manus — confirmed, then reversed.** It joined Meta on 2025-12-29 and resumed independent operations on 2026-09-01 (https://manus.im/blog/manus-resumes-independent-operations). Current ownership isn't stated.
- **OpenAI Operator — partly confirmed.** operator.chatgpt.com redirects to ChatGPT agent mode. openai.com and help.openai.com returned 403, so there is no sunset date.

## Other findings

- **Project Mariner** was shut down on 2026-05-04; Google points users to Gemini Spark (https://labs.google.com/mariner/).
- **Lutra AI** says support has been discontinued.
- **Funding:**
  - Cognition: Series E of over $2B at $48B (2026-09-08).
  - Lovable: $400M Series C at $13.3B (2026-08-12).
  - Synthflow: $20M Series A.
  - Magic: $768M total raised.
- **Latest releases:** Replit Agent 4 (2026-03-13), Manus 2.0 (2026-09-28), Junie CLI 26.10.20.
- **MCP support** confirmed for Junie, Lovable, Replit, Retell and Synthflow.

## Migration notes

- **Project Mariner → Gemini Spark:** as named on the Mariner page.
- **Operator → ChatGPT agent mode:** plus the computer-use migration guide for API users.

## Left unchanged

- **Operator:** the sunset date and ChatGPT pricing (403).
- **Prices:** Vonage (403), Lovable (rendered client-side), Manus and Speechmatics.
- **Speechmatics Flow:** lifecycle `unknown`. Its pages redirect to Agent STT, but there is no deprecation notice.

---

# Re-verification 2026-10-27 — data group (28 rows)

- rows seen: 28
- rows verified: 28
- cells applied: 82
- cells skipped: 0
- decayed: 0
- renamed: 0
- url changed: 1
- taxonomy set: 0

## Lifecycle changes found

- **Databricks Vector Search** — renamed: Databricks Vector Search is now marketed as Databricks AI Search; the vector-search product URL 301-redirects to /product/artificial-intelligence/ai-search (checked 2026-10-27). ([source](https://www.databricks.com/product/artificial-intelligence/ai-search))
- **Hugging Face Inference API (Embeddings)** — renamed: The serverless Inference API is now Inference Providers; huggingface.co/docs/api-inference redirects to /docs/inference-providers (checked 2026-10-27). ([source](https://huggingface.co/docs/inference-providers/en/pricing))
- **Sajari (now Search.io)** — acquired: Algolia announced the acquisition of Search.io (formerly Sajari, Neuralsearch vector engine) on 2022-09-12; www.search.io now 301-redirects to algolia.com (checked 2026-10-27). ([source](https://www.algolia.com/about/news/algolia-disrupts-market-with-search-io-acquisition-ushering-in-a-new-era-of-search-and-discovery))
- **Sinequa** — acquired: Sinequa now operates as 'Sinequa by ChapsVision' and is listed as a ChapsVision platform (checked 2026-10-27); the acquisition date was not confirmed on a primary page this session. ([source](https://www.chapsvision.com/en-us/platform/sinequa/))
- **TopQuadrant (TopBraid EDG)** — renamed: TopBraid EDG is now marketed as TQ Data Foundation; topquadrant.com/topbraid-edg 301-redirects to /tq-data-foundation (checked 2026-10-27). ([source](https://www.topquadrant.com/tq-data-foundation))
- **Voyage AI (MongoDB)** — acquired: MongoDB acquired Voyage AI, announced 2025-02-24; voyageai.com is now branded 'Voyage AI by MongoDB'. ([source](https://www.mongodb.com/blog/post/redefining-database-ai-why-mongodb-acquired-voyage-ai))

## Method

One research agent checked vendor pricing, docs and news pages, plus the PyPI/npm/Hugging Face APIs and GitHub repo search, using one web search. The GTE URL claim was re-checked independently: Alibaba-NLP/gte-large returns 401, while thenlper/gte-large exists and is MIT.

## Notable findings

- **MCP support:** about a dozen rows that said "no first-party MCP adapter as of 2026-05" now have official MCP servers. They are Amazon Neptune, Clarivate, Coveo, Databricks, Diffbot, Lucidworks, Mindbreeze, Palantir, SearchUnify, Sinequa, Stardog and TigerGraph, with Graphwise at medium confidence.
- **Search.io (formerly Sajari)** has been part of Algolia since 2022-09-12.
- **Voyage AI** was acquired by MongoDB on 2025-02-24.
- **Renames:**
  - Databricks Vector Search is now marketed as Databricks AI Search.
  - Hugging Face Inference API is now Inference Providers.
  - TopBraid EDG is now TQ Data Foundation.
- **Graphwise:** formed in 2024, not 2025 as the description said, and Oakley Capital took a majority stake in 2026. PoolParty is now part of the Graphwise Platform.
- **Licenses:**
  - Activeloop Deep Lake is Apache-2.0; the row wrongly said "not OSS".
  - The original GTE models are MIT; the newer Alibaba-NLP GTE models are Apache-2.0.
- **GTE record URL:** changed to https://huggingface.co/thenlper/gte-large; the old URL is dead and the id is unchanged.
- **Pricing:**
  - Turbopuffer: $16 / $256 / ≥$4,096 monthly minimums plus calculator rates.
  - OpenAI embeddings: $0.02 / $0.13 per 1M tokens.
  - Mistral embed: $0.10 per 1M tokens.
  - TigerGraph Savanna: $45 / $126 per GB-month.
  - Neptune Analytics: $0.03 per m-NCU-hour.
- **Nomic** has pivoted to an AEC agent platform; its embed pages return 404, and embedding API access now comes with the Business plan.

## Left unchanged / to review

- **Cohere desc:** still mentions embed-v3/Rerank-v3, while the current models are Embed 5/Rerank 5. The latest-release cell is updated.
- **Sinequa:** acquisition date (ChapsVision press URL redirects).
- **Prices:** Lucidworks (403) and Cohere per-token embed prices.
- **AllegroGraph:** release date and MCP support.
- **Funding:** for the embedding vendors.
