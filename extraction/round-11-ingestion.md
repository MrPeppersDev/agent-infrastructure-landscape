# Round 11 — Agentic-harness ingestion (2026-05-13)

The "agentic / agent harnesses" sweep authorised by the user direction
on 2026-05-13: *"lets start adding agentic/agent harnesses"* with
**kiro.dev** named as the user-specified seed.

## Mandate

> "continue increasing our primary load" — pull in everything in this
> category that's citable; skip rows where no source is available.

The category covers user-facing **agentic IDEs**, **terminal harnesses**,
and **agent-runtime products**. Distinct from:

- **Coding-agent memory** (Round-pre-7) — the *memory layer* of these
  products (CLAUDE.md, .cursorrules, Devin Knowledge, etc.).
- **Agent frameworks (no first-party memory layer)** (Round 7) —
  import-and-compose libraries (LangChain, CrewAI, AutoGen, Mastra).

This round captures the layer where the **harness / IDE itself is the
product**.

## Result

**Total catalog: 731 records (was 699, +32 net).**

32 new rows landed inside one new top-level section:
**"Agent IDEs & coding harnesses"**.

## New section created

One new section (the 27th):

**Agent IDEs & coding harnesses** — registered in
`scripts/extract.py::CANONICAL_SECTIONS` and in
`extraction/section-explainers.json`.

Explainer copy frames the section against the two adjacent ones
(Coding-agent memory; Agent frameworks (no first-party memory layer))
so a reader landing on the section knows why each row sits there.

## Rows added (32)

Grouped by orientation:

### Tier-1 (battle-tested commercial harnesses) — 13

- **Kiro** — kiro.dev, AWS (preview Jul 2025) — the seed for this sweep
- **Cursor (IDE)** — cursor.com — Anysphere $9.9B val / $200M ARR
- **Windsurf (Codeium / OpenAI)** — windsurf.com — the OpenAI ($3B) →
  Google reverse-acqui-hire ($2.4B) → Cognition (IP-remainder) saga
- **Zed (Agentic Editing)** — zed.dev — native Rust editor
- **Claude Code (Anthropic)** — anthropic.com/claude-code
- **OpenAI Codex CLI** — github.com/openai/codex — OSS, Apr 2025
- **GitHub Copilot Workspace** — githubnext.com/projects/copilot-workspace
- **GitHub Copilot (Agent Mode)** — github.com/features/copilot
- **JetBrains AI Assistant** — jetbrains.com/ai
- **Amazon Q Developer** — aws.amazon.com/q/developer
- **Sourcegraph Cody (agent)** — sourcegraph.com/cody
- **Replit Agent v3** — replit.com/ai (cross-listing with Coding-agent
  memory; harness framing)
- **Bolt.new (StackBlitz)** — bolt.new (cross-listing)

### Tier-1 (cross-listings of memory-section products at the harness layer) — 4

- **Cognition Devin v2 / Spec Mode** — devin.ai / cognition.ai
- **Lovable.dev — harness** — lovable.dev
- **v0 (Vercel)** — v0.app
- **ChatGPT — Codex (cloud agent)** — chatgpt.com/codex (distinct from
  Codex CLI)
- **Anthropic Computer Use** — docs.anthropic.com/.../computer-use

### Tier-2 (mature OSS / smaller commercial) — 9

- **Aider (harness)** — aider.chat (cross-listing — Aider is also in
  Coding-agent memory)
- **Cline (harness)** — cline.bot (cross-listing — Cline framework /
  memory bank rows exist)
- **Continue.dev (harness)** — continue.dev (cross-listing)
- **Goose (Block)** — block.github.io/goose
- **Opencode (SST)** — opencode.ai
- **Manus AI** — manus.im — general-purpose autonomous agent
- **Magic.dev** — magic.dev — $465M raised; ultra-long-context play
- **OpenHands (All Hands AI)** — all-hands.dev (formerly OpenDevin)
- **MetaGPT (harness)** — github.com/FoundationAgents/MetaGPT
  (cross-listing; framework row exists)
- **JetBrains Junie** — jetbrains.com/junie
- **Bedrock AgentCore (AWS)** — aws.amazon.com/bedrock/agentcore

### Tier-3 (smaller / experimental) — 3

- **Charm Crush** — github.com/charmbracelet/crush — TUI-first Go
- **Roo Code** — roocode.com — Cline fork with modes
- **smol-developer** — github.com/smol-ai/developer — historical
  Swyx-era reference loop

## Skipped (already in catalog)

These were considered but already have a row under a different framing.
Where the existing row covers the harness framing well, we did NOT add
a duplicate:

- **Augment Code** — already in Coding-agent memory (sufficient as
  the canonical row; its desc already describes the harness)
- **Tabnine** — already in Coding-agent memory
- **OpenAI Codex (cloud agent)** — already in Coding-agent memory
  (the new "ChatGPT — Codex (cloud agent)" row is a cross-listing for
  the new ChatGPT-integrated surface, distinct framing)
- **Sweep AI** — already in Coding-agent memory; not re-added (low
  recent activity)

The Aider / Cline / Continue.dev / MetaGPT / Replit / Bolt / Lovable /
v0 / Devin entries DO add new rows because the existing rows are
purely memory-tier, and the harness-tier framing is materially
different. Pattern follows Round-7 convention of "two distinct framings,
two records" rather than the older "cross-listing" pattern.

## Per-category counts

| Category | New rows |
|---|---:|
| Tier-1 agentic IDEs (Kiro, Cursor, Windsurf, Zed, Claude Code, Codex CLI, Copilot Workspace, Copilot, JetBrains AI, Amazon Q, Cody, Replit v3, Bolt) | 13 |
| Tier-1 cross-listing harnesses (Devin v2, Lovable, v0, ChatGPT Codex, Computer Use) | 5 |
| Tier-2 OSS / mid-commercial (Aider, Cline, Continue, Goose, Opencode, Manus, Magic.dev, OpenHands, MetaGPT, Junie, Bedrock AgentCore) | 11 |
| Tier-3 (Charm Crush, Roo Code, smol-developer) | 3 |
| **Total** | **32** |

## Cross-listings created (this round)

Five entries are intentional cross-listings — same product, harness
framing, with the memory-tier row remaining canonical for the memory
framing. Per Round-7 convention these are stored as separate rows, not
in `cross-listings.json`:

- Aider (Coding-agent memory) ↔ Aider (harness, this round)
- Cline (framework / memory bank rows) ↔ Cline (harness)
- Continue.dev (framework / memory MCP) ↔ Continue.dev (harness)
- Devin (Coding-agent memory) ↔ Cognition Devin v2 / Spec Mode (harness)
- Replit Agent (Coding-agent memory) ↔ Replit Agent v3 (harness)
- Bolt.new (Coding-agent memory) ↔ Bolt.new — harness
- Lovable (Coding-agent memory) ↔ Lovable.dev — harness
- MetaGPT (Agent frameworks) ↔ MetaGPT (harness)
- OpenAI Codex (Coding-agent memory) ↔ ChatGPT — Codex (cloud agent)
  + OpenAI Codex CLI (two separate harness rows for two surfaces)

## Surprises

- **Windsurf three-way M&A saga.** OpenAI announced acquisition (~$3B,
  May 2025), Google did a reverse-acqui-hire of leadership (~$2.4B,
  July 2025) for an inverse license; Cognition then acquired the
  remaining Windsurf IDE/IP in August 2025. Three different acquirers
  in three months for one company.
- **Cursor at $9.9B and $200M ARR (May 2025)**, then Anthropic-released
  pricing changes mid-2025 created backlash — the highest-velocity
  startup in the category.
- **Kiro's framing as "spec-driven"** is a genuine product-design bet
  by AWS — files (specs, steering, hooks) ARE the memory in their
  model. That's the same posture as CLAUDE.md / .cursorrules but
  formalised into a workflow stage. Worth tracking as a category
  movement.
- **Charm Crush** — a TUI-first Go-native coding agent. Niche, but
  Charm's existing audience makes the launch credible.
- **Manus AI** — Chinese-origin general-purpose autonomous agent that
  went viral in March 2025; raises Western data-residency questions.
- **Magic.dev** — $465M raised but mostly unreleased product through
  2025. The "ultra-long-context" model claim has not been independently
  verified.
- **OpenHands ex-OpenDevin** — Robert Brennan (CEO) was actually a
  former Cognition employee. The OSS Devin started inside Cognition.
- **Bedrock AgentCore** — AWS's framework-agnostic agent runtime
  (preview Jul 2025) picks Mem0 as its canonical memory provider,
  consistent with the "Mem0 is the AWS Agent SDK memory layer"
  earlier-reported relationship.

## What's locked in for Track A v3 (running in parallel)

- **Section count is now 27** (was 26 after Round 7). Re-running
  section-vs-section stats needs to handle the new section.
- **Tier population: T1=230, T2=201, T3=143, T4=144, T5=13** (was
  T1=213/T2=192/T3=141/T4=145/T5=13 after Round 7). The harness sweep
  was almost entirely T1+T2 — 13 + 11 = 24 of 32 rows are top-two-tier
  commercial products.
- **New "two-row pair" lineages**:
  - Cursor (harness) — Cursor Rules (memory)
  - Windsurf (harness) — Windsurf Rules & Memories (memory)
  - Claude Code (harness) — Claude Code auto-memory + CLAUDE.md
  - Codex CLI (harness) — OpenAI Codex (cloud agent)
    + the older OpenAI Codex (cloud agent) → ChatGPT Codex pair
  - Devin v2 (harness) — Devin (memory)
  - Replit v3 (harness) — Replit Agent + replit.md
  - Bolt (harness) — Bolt.new (memory)
  - Lovable (harness) — Lovable (memory)
- **Harness-vs-memory framing now has a complete pair set.** Track A
  v3 can compute per-product "memory-layer-vs-harness valuation /
  adoption / inbound" cross-comparisons cleanly.
- **Cross-references via edges**: build_edges discarded a few
  cell-mining edges as "ambiguous-substring: Claude" — Anthropic
  Computer Use desc mentions "Claude" and matches both Claude Code
  rows. Re-running with the larger record set may resolve these.
- **Possible new lineages**:
  - **Spec-driven lineage**: Windsurf Cascade → Kiro specs →
    Devin Spec Mode (Aug 2025, post-Windsurf-IP). Three independent
    products converging on durable specs as the memory unit.
  - **Cline fork chain**: Cline → Roo Code → (community forks).
  - **OpenDevin / OpenHands → SWE-bench-Verified OSS race**: OpenHands
    + Aider + GPT Engineer / smol-developer share the OSS-Devin
    framing and compete on SWE-bench.

## Pipeline state

- Extract → Reconcile → Build_edges → fetch_citations (--offline) → Validate: ALL PASS.
- All 4 validate.py gates green; gate 2 (determinism) re-passes after
  the `fetch_citations.py --offline` refresh that adds back the cached
  cites edges.
- audit_gaps.py: 0 gap rows; 43860 cells all-terminal (15546 real-data,
  16993 not-applicable, 11321 depth-floor-reached, 0 no-data).
- Render NOT re-run (Round-7 convention — render.py loses
  cross-listings on round-trip; the hand-inserted HTML is canonical).

## Files modified

- `landscape.html` — 32 new rows inserted; 1 new section header + 1
  new section explainer.
- `web/landscape.json` — regenerated, 731 records.
- `web/landscape.edges.json` — regenerated, 298 edges.
- `extraction/section-explainers.json` — extended with the new section.
- `scripts/extract.py` — `CANONICAL_SECTIONS` extended with the new
  section.
- `docs/DECISIONS.md` — new entry (this round).
- `extraction/round-11-ingestion.md` — this file.

## What I deliberately did NOT add

Some candidates from the user's seed list were skipped:

- **OpenAI Codex (the cloud agent)** — already in Coding-agent memory;
  the new ChatGPT — Codex (cloud agent) row captures the new
  ChatGPT-integrated surface as a separate harness, but the original
  Codex memory-tier row stays canonical.
- **Tabnine Agent** — already in Coding-agent memory under "Tabnine";
  no new harness row added (the existing row already characterises
  the IDE plugin).
- **HuggingFace SmolaAgents** — already in Agent frameworks as
  "smolagents (Hugging Face)" — that row already represents the
  harness-level identity.
- **gpt-engineer** — already in Agent frameworks as "GPT Engineer";
  the Lovable.dev row was added as the commercial-descendant harness.
- **AutoGen / AutoGPT / OpenAI Agents SDK** — already in Agent
  frameworks; those are libraries-to-import, not user-facing
  harnesses.
- **Cognosys** — searched, low public surface; deferred.
- **TraceAI** — searched, low public surface; deferred.
- **Augment Code** — already in Coding-agent memory; the existing row
  is already harness-shaped, so no double-counting.

Net signal: the agentic-IDE / harness layer now has dense coverage at
T1+T2. The category cap is not budgeting — it's the absence of
public sources for the next-tier candidates.
