# Memory Analysis Program — Plan

## Where we left off (2026-05-06, evening pass)

The `landscape.html` catalog is at **~520 entries** across 23+ sections /
sub-groups with tier badges (T1–T5), explainers, and source links. Recent
integrations completed in this session:

- **Pros & Cons columns added** (6th and 7th) — structural change applied to
  all 490 prior rows + 30 new rows. CSS placeholder ("—") shows for empty cells.
- **Education AI memory sub-group** added under "Vertical / domain-specific
  AI memory" — 9 entries (ELSA Speak, Duolingo Max, Quizlet, MagicSchool,
  Khanmigo, SchoolAI, Speak, Synthesis Tutor, ChatGPT Study Mode) with full
  Pros/Cons populated.
- **Last-30-days launches** (10 entries) integrated across Platform-provider,
  Method papers (experiential), Memory benchmarks, Theoretical/informal,
  Voice-first/wearable. Pros/Cons populated.
- **Wave-4 + industrial-lab papers** (11 NEW; 5 already present; 1 unresolved)
  integrated across Method papers (parametric & latent, continual learning,
  experiential), Platform-provider, Personal AI / PKM. Pros/Cons populated.
- **Categorisation cleanup**: Limitless moved from PKM to Voice-first/wearable;
  Memvid claude-brain entry reframed to cross-reference the Memvid library row
  rather than duplicate its description.

Verified no items lost: 520 data rows total, 30 with populated Pros/Cons (the
new entries), 490 with empty placeholder. TR/TD balance clean. Agent-result
batches preserved at `.agent-results/batch-{1,2,3}-*.md` for durability.

### Outstanding integration caveat

The wave-4 batch flagged "NAVER trajectory memory" as **UNRESOLVABLE** — no
specific NAVER Labs paper canonically titled "trajectory memory" was found. The
closest candidate is RANa (arxiv 2504.03524, NAVER Labs Europe robot navigation
with episodic retrieval). Skipped to avoid misattribution; user should supply
the exact title/arxiv ID if the intended paper is something else.

## Status (in-depth analysis pass complete)

All seven background agents returned. Outputs:

- `taxonomy/schema.md` — 6-axis schema
- `taxonomy/tags.json` — 520 rows tagged
- `.agent-results/data-{1..6}-*.{md,csv}` — six data passes (GitHub adoption,
  arxiv volume, conferences, funding, cross-references, benchmarks)
- `analysis.md` — first synthesis pass written, 8 sections

## Major findings now in analysis.md

- **Cross-section pattern reuse**: 3 architectural patterns recur across
  many sections (commodity vector-extraction, bi-temporal KG, file-as-memory).
  Several sections collapse into structurally-one pattern across vendors.
- **4 architectural lineages traced**: World-model RSSM family,
  KV-cache eviction family, Graph-RAG hierarchy, Files-as-memory thread.
- **Mem0 = central hub** (14 inbound integrations); MCP = transport layer.
- **Vocabulary-then-funding pattern**: arxiv "agent memory" terminology
  crystallized late Q3 2025; funding wave for dedicated layers followed
  Q1 2026 (1-quarter lag).
- **60× valuation gap** between coding-agent products ($6.6B–$10B) and
  dedicated memory layers ($150M peak). Capital is betting memory becomes
  a vertical-product feature, not horizontal infrastructure.
- **Two memory products with cross-pass anomaly signals** (MemPalace,
  Mem0 vs Zep dispute) — flagged in analysis.md §5.
- **ConvoMem 150-interaction threshold**: long-context LLM beats
  RAG-based memory below it; memory layer wins above it.
- **5 white-space gaps identified** in §8.

## Table-grounded analysis (final)

`landscape.html` now has 20 columns including 6 taxonomy axes + 7 signal
columns (GitHub, Created, Funding, Customers, Performance, Mindshare,
Citations). 9 data passes populated cells. `analysis.md` rewritten so
every numeric claim cites the column you can verify in the row.

## (Earlier — now superseded) In-depth analysis update

`taxonomy/pivots.json` added — programmatic pivots of `tags.json` produce:
- 21 cross-section recurring fingerprints (3+ sections)
- 9 domain-specific single-section fingerprints
- Per-section architectural diversity ratios
- Per-axis distributions across 520 rows

`analysis.md` expanded substantially. Now 11 numbered sections including:

- **§1**: 8 cross-section pattern subsections (was 3) + new inverse
  domain-specific subsection (§1.9)
- **§2**: architectural lineages + 3 fork chains
- **§3**: velocity-by-category, language distribution, per-company
  funding trajectories with specific dates and rounds
- **§5**: full LongMemEval leadership timeline; benchmarks-without-
  competition phenomenon; governance-null-rate-as-academic-gap finding
- **§6**: sharpened with defensible argument — "memory becomes
  horizontal at substrate/integration, vertical at value-capture"
- **§7**: new Quantitative summary (storage, persistence, section
  diversity, tier distribution)
- **§10**: new Anti-patterns section (8 anti-patterns enumerated)
- **§11**: forward-looking questions to track

## Remaining work

1. **Human review of T1 taxonomy tags** — agent did first-pass; spot-check
   would catch any axis-tagging mistakes that affected the §1 pivots.
2. Optional: claims population pass for older T2/T3 framework rows where
   the Claims column is still empty (~70%).
3. Quarterly tracking — re-run the data-pass agents in 3–6 months to
   measure trajectory of the §11 forward-looking questions.

## Pros & Cons populate — DONE (all tiers)

Done 2026-05-06. **All 520 rows across T1–T5 now have populated Pros/Cons.**

Per-tier counts:
- T1 (battle-tested): 140/140 populated
- T2 (established / mature OSS): 134/134 populated
- T3 (peer-reviewed): 100/100 populated
- T4 (preprint): 133/133 populated
- T5 (theoretical / informal): 13/13 populated

Pros/Cons quality varies by depth of available source material. T1/T2 entries
have specific architectural / market comparisons. T3 entries focus on the
paper's contribution and known limitations. T4 entries (preprints) typically
have shorter Pros/Cons since the field has not yet evaluated them deeply —
a "preprint stage / narrow eval" caveat is the dominant Cons note for many.

## Pros & Cons column add — DONE

Done 2026-05-06. Structural change:
- Updated `<thead>` to 7 columns with adjusted widths.
- Replaced all 68 instances of `colspan="5"` with `colspan="7"`.
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
