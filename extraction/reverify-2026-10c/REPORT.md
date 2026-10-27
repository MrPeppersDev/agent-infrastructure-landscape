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
