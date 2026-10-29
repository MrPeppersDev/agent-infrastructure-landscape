# Catalog fixes and open-core review (2026-10-29)

## Open-core licensing review (`result-opencore-*.json`)

`derive_v1_1_cells.py` had marked 105 `licensing-bucket` cells `open-core` (status `estimate`), using a rule: OSI licence plus a paid plan in the pricing cell. Two agents checked each one against the vendor's pricing page and the repo's LICENSE/README. Results were applied with `apply_v1_1_research.py --force`; reviewed cells are never re-derived after that.

- **Decided (93):** open-core 55 confirmed, 26 changed to open-source, 12 changed to commercial.
  - **To open-source:** rows where the paid offering is only hosting or support of the same code (Temporal, Trigger.dev, Langflow, e2b, Memobase), where it's a separate product (smolagents, Nomic Embed, Codex CLI), or where there's no paid tier at all.
  - **To commercial:** non-OSI core licences (ArangoDB and lakeFS are BSL-1.1, Inngest is SSPL, Charm Crush is FSL, AutoGPT's platform is Polyform Shield), or now closed (Daytona moved core development to a private codebase in June 2026; Gitpod/Ona; Jina; Modal; the Codex cloud agent; RunWhen; BloodHound Enterprise).
- **Undecided (12):** these keep status `estimate`. The pages didn't settle them: Helicone, AgentOps, claude-mem, 01.AI Yi, Qwen 3, Jamba, Unsloth, Sema4.ai, OpenMind OM1, Reka, Logseq, Steamship.

## Other fixes

- **Hugo (Hugo Legal) removed** (`removed.json`). hugo.legal is an Estonian service that connects clients with human lawyers (from 39 EUR per 30 min) and sells no AI product, so it's out of scope. It had no edges and no aliases. The catalog now has 950 records.
- **Linq AI:** linq.ai now belongs to an unrelated higher-education company. The description notes this and lifecycle is `unknown`. LinqAlpha sells a similar platform, but nothing on its site links it to Linq AI, so the row wasn't renamed.
- **Left as is:**
  - LawDroid: the description already records the pivot to LawDroid Assist. lawdroid.ai renders only with JavaScript, so it couldn't be re-read.
  - Magnitude: the row describes the deprecated browser agent, already recorded as `superseded`.

## New leads from this pass (not applied)

- Langfuse: the site says "Langfuse joins ClickHouse", and the LICENSE copyright is now ClickHouse, Inc.
- Daytona: core development has moved to a private codebase, and the public repo is unmaintained.
- Memobase: memobase.io returns 404, so the cloud may be gone.
- claude-mem: a paid hosted tier, "CMEM Pro", now exists.
- Jina v4: the model card says the license is the Qwen Research License (it had been mislabelled CC-BY-NC).
- Mistral Large 2: under the non-OSI Mistral Research License.
- Letta: the `letta-ai/letta` repo is now a stub pointing to `letta-ai/letta-code`.
- OpenMemory has been renamed LongMemory.
- K-Scale: kscale.dev returns 502.
