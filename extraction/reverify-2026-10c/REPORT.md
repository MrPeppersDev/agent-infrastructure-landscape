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
