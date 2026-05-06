# Memory Analysis Program — Plan

## Where we left off (2026-05-06)

The `landscape.html` catalog is at ~510 entries across 22+ sections / sub-groups
with tier badges (T1–T5), explainers, and source links. Built across multiple
sessions of research and ~27 parallel research-agent sweeps.

We just finished the third "exhaustive" push (browser agents, education AI,
last-30-days launches), and three sets of results are still pending integration:

1. **Browser-agent memory** (8 entries) — Perplexity Comet, Dia, Edge Copilot Mode,
   Brave Leo, Opera AI, Sigma, Fellou, Browserbase. **Already integrated as a new
   top-level group.**
2. **Education AI memory** (9 entries) — Khanmigo, Synthesis Tutor, SchoolAI,
   Duolingo Max, ELSA Speak, Speak, Quizlet, ChatGPT Study Mode, MagicSchool.
   **Not yet integrated** — would go as a new sub-group under "Vertical / domain-
   specific AI memory".
3. **Last-30-days launches** (10 entries, April 6 – May 6 2026) — Anthropic
   Managed Agents Memory, MemMachine paper (separate from framework), MIA, Memory
   in the LLM Era, ImplicitMemBench, MemEvoBench, Memory as Metabolism, Era
   Computer ($11M), ICLR 2026 MemAgents Workshop, Externalization in LLM Agents.
   **Not yet integrated** — goes across multiple sections (platform-provider for
   Anthropic, parametric / continual / benchmarks for the papers, dedicated for
   Era Computer).

Plus wave-4 leftovers from the prior session that never made it in:

4. **Sakana CTM, NAVER Provence/PISCO, NAVER trajectory memory, RIKEN tensor
   decomposition, Mistral Agents API** — five papers / framework features that
   should be added to method-paper sub-groups + framework-embedded.

Plus content from earlier industrial-labs research that was attempted but failed
silently mid-edit:

5. **IBM Meta-Tokens, NVIDIA Nemotron 3, Anthropic Circuit Tracing, MemoryLLM
   (different from M+), SELF-PARAM, ShadowKV (ByteDance), Tencent ima.copilot,
   MemoryBench (Tsinghua, distinct from Renmin's MemBench), MemR³, Engram
   (DeepSeek), AutoGLM (Zhipu), M3-Agent (ByteDance)** — some of these may
   already be in the file; others may have been lost in failed edits. **Re-verify
   each before adding to avoid duplicates.**

## Major next-session task: Pros & Cons columns

User decision: add **two new columns** to the table (6th and 7th):
- **Pros** — what makes this system distinctive / where it wins
- **Cons** — known weaknesses / where it loses

Plan:
- Structurally add both columns; update `<thead>`, group-row colspans (`colspan="7"`),
  section-explainer colspans, and the empty placeholder rows.
- Populate T1 entries (~50 rows, the highest-impact production / battle-tested
  systems) in the first pass. T2/T3 in subsequent passes; T4/T5 may stay
  partially empty.
- Width allocation tightens — expect some adjustment to the existing column
  widths.

## Side-by-side analysis + trend / adoption analysis

User decision: **build these as a separate document, not in this HTML file.**
This file stays as the substrate.

Before building those documents, we need to gather data we don't currently have.

### Data we need before trend / adoption analysis is meaningful

For **adoption signal** (per row, where applicable):
- GitHub stars (current + 90-day velocity for OSS frameworks)
- Package download counts (npm, pip, crates) for libraries
- Customer logos / named deployments for commercial systems
- ARR / revenue figures where disclosed
- Funding totals + valuation (we have some of this in the Claims column already)
- Employee count / team size (proxy for sustainability)
- Integration count — how many other products embed this one (e.g. how many agent
  frameworks ship a Mem0 connector vs Zep vs Cognee?)
- MCP server install counts (where observable from registries)
- Stack Overflow / Reddit / HN mention volume
- Job postings mentioning the technology

For **trend signal**:
- arxiv submission counts per memory category per month (factual / world-model /
  continual / etc.)
- Conference acceptance counts by year (NeurIPS, ICLR, EMNLP, ACL memory papers
  per year)
- Repo creation date + first-commit date for OSS projects
- Citation curves for landmark papers (RMT → MemGPT → Mem0 → Titans → ?)
- Funding timeline (when did the field start raising? what's the velocity?)
- Benchmark leaderboard timeline (who held top spot on LongMemEval / LoCoMo /
  ConvoMem and when)
- Architecture preference shifts visible in venue acceptances (RAG → KG → world-
  model → ?)
- Press coverage volume per system over time

For **what's actually being used**:
- Cross-references between products (e.g. Strands integrates Mem0; LangGraph
  uses LangMem; Pydantic-AI uses Hindsight) — these existing cross-mentions are
  the strongest adoption signal we already partially have.
- "Memory provider" choices in major frameworks (Mastra defaults to LibSQL,
  Agno defaults to Postgres + pgvector, etc.) — these tell you which substrate
  is winning.

### Suggested research passes

When ready to build the analysis document, run these in parallel:

1. **GitHub adoption pass** — for every OSS row with a GitHub URL, fetch stars,
   forks, contributors, last-commit-date, 90-day star velocity. Use `gh api`
   where possible.
2. **arxiv volume pass** — for each memory sub-category, count papers per month
   2023–2026.
3. **Conference acceptance pass** — count "memory" / "agent memory" papers per
   NeurIPS, ICLR, EMNLP, ACL year.
4. **Funding timeline pass** — for every commercial row with disclosed funding,
   pull the round dates and amounts; build a chronological view.
5. **Cross-reference pass** — extract every "integrates with" / "built on" /
   "powered by" mention from existing rows; map the dependency graph.
6. **Benchmark leaderboard timeline** — for LongMemEval, LoCoMo, ConvoMem,
   reconstruct who held #1 each month from 2024 onwards.

These passes feed a separate `analysis.md` (or similar) document that will live
alongside `landscape.html`.

## Other known caveats

- The **Claims** column is still ~70% empty across older T2/T3 rows. A focused
  population pass remains deferred. Worth doing alongside Pros/Cons — same
  rows, similar effort per row.
- A few entries are slightly mis-categorised (Limitless / Heyday / Mem.ai /
  Reflect / MS Recall / Personal.ai are in PKM/lifelogging but Limitless
  specifically belongs in Voice-first/wearable). Easy cleanup.
- Memvid appears twice (as a product and as a Claude Code plugin via claude-brain).
  Mild duplication — could disambiguate.
- A handful of 2026 arxiv IDs are recent enough that the canonical form may
  shift; the paper-verification agent confirmed most of them but a few
  (TierMem, GAM, MemoryArena, MemoBrain) reflect agent-reported facts not
  independently re-read.

## Resume prompt for next session

Paste this into a new session:

> Resume the Memory Analysis Program. The landscape catalog lives at
> `/Users/b.sayer/src/memory-analysis-program/landscape.html`. State and plan
> are in `PLAN.md`. GitHub repo: see `git remote -v` in that directory.
>
> Pending work in priority order:
>
> 1. Integrate the three pending agent-result batches (browser already done;
>    education + last-30-days + wave-4 leftovers + verified-but-not-added
>    industrial-lab papers — see `PLAN.md` "Where we left off").
> 2. Add Pros & Cons columns (6th and 7th) — structural add, then populate T1
>    rows first.
> 3. Categorisation cleanup — move Limitless to Voice-first / wearable; resolve
>    Memvid duplicate.
> 4. Plan and execute the adoption + trend research passes listed in `PLAN.md`
>    "Data we need before trend / adoption analysis is meaningful". These feed
>    a separate `analysis.md` document — not the landscape HTML.
>
> Do not start the analysis document until the data passes are complete. The
> landscape is the substrate; analysis is downstream.
