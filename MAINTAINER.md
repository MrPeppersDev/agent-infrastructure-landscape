# MAINTAINER

Governance contract for this catalog. Defines what's in scope, how fresh data
must be, how claims are validated, what happens if the maintainer disappears,
and how to reach us. Closes the governance vacuum identified in the
catalog-deaths post-mortem (single-maintainer bus factor, scope inflation,
silent decay).

Survivors of the catalog-decay graveyard (DB-Engines, State of JS, dbdb.io)
all publish a maintenance contract. This is ours.

Companion documents:

- `README.md` — what the catalog is and how to use it
- `PLAN.md` — what's next, what's deferred
- `docs/SCHEMA.md` — record / edge shape (the **what** of every cell)
- `docs/DECISIONS.md` — why specific design calls were made

Tier-0 issues referenced below:

- **T0-1** (#35) — landscape data as a standalone versioned dataset (CC-BY-4.0)
- **T0-3** (#37) — claim-tier schema (T1 / T2 / T3 per cell)
- **T0-4** (#38) — automated staleness CI

---

## 1. Scope

The catalog covers **AI agent infrastructure**, broadly construed. The
boundary is documented, not vibes-based, so contributors and reviewers can
say no without negotiation.

### In scope

1. **Production / commercial memory systems** — dedicated memory layers
   (Mem0, Letta, Zep), framework-embedded memory (LangChain / LlamaIndex
   memory modules), platform-provider memory (OpenAI memory, Anthropic
   memory), coding-agent memory, browser-agent memory, personal AI / PKM /
   lifelogging memory.
2. **Agent harnesses and frameworks** — LangGraph, AutoGen, CrewAI, OpenAI
   Agents SDK, multi-agent orchestration platforms, computer-use / desktop
   agents, use-case-specific agent harnesses.
3. **Coding IDEs and agent-aware editors** — Cursor, Continue, Aider, Kiro,
   Claude Code, and similar editor surfaces whose memory or agent
   architecture is documented and distinct.
4. **Research method papers** — factual / experiential / working /
   parametric & latent memory, world-model, continual learning,
   memory-augmented RL, cognitive-architecture-inspired systems. Retrieval-
   as-memory hybrids count when retrieval is positioned as memory.
5. **Memory benchmarks and evaluation** — LongMemEval, LoCoMo, BABILong,
   ConvoMem, RULER, MemoryBench, and any other eval suite that targets
   memory or long-horizon agent behavior.
6. **Vector, graph, and knowledge databases** — Pinecone, Weaviate, Qdrant,
   Chroma, Neo4j, etc., when they're documented as memory / agent
   substrates.
7. **Vertical agent products** — legal, healthcare, scientific,
   customer-support, gaming / NPC, robotics / autonomous-driving / embodied,
   voice-first / wearable.
8. **Memory observability, governance, privacy, and safety** — eval
   tooling, audit surfaces, redaction layers, PII handling.
9. **Adjacent infrastructure** — file-backed editor paradigms, Claude Code
   memory mechanisms, MCP servers, enterprise-search adjacencies.

A complete enumerated section list lives in `.github/ISSUE_TEMPLATE/intake.yml`
(the same picker used for new submissions).

### Out of scope

Each out-of-scope category has a rationale; the rationale is the armor
against scope creep.

1. **Pure foundation-model training infrastructure with no agent or memory
   story.** Generic CUDA kernels, raw transformer libraries, training-only
   inference engines, pretraining datasets. Rationale: these are the
   substrate *below* agent infrastructure; tracking them would explode
   the catalog without serving its question (what tools / techniques exist
   for the *agent-and-memory* problem?).
2. **Consumer chatbots without a distinct memory architecture.** Generic
   GPT wrappers, persona bots, "AI girlfriend" apps, etc. Rationale: no
   defensible architecture to compare; nothing to learn from inclusion.
3. **General-purpose web search and vector DBs with zero documented agent
   or memory integration.** Plain Algolia, plain Elasticsearch usage,
   etc. Rationale: included only when the vendor documents an agent
   posture (see Pinecone, Weaviate, Qdrant — all in scope because they
   ship explicit agent / memory integrations).
4. **Pure prompt-engineering tools with no memory or agent angle.**
   Promptbase, prompt-marketplace style sites, prompt linters. Rationale:
   not an agent infrastructure category; would invite a long tail with
   no analytical value.

### Borderline rule

When a candidate row is borderline, include it only if at least one of:

- **(a)** It has a *documented* memory architecture (a paper, a section
  in the docs, a public design doc).
- **(b)** It has a *documented* agent harness (runtime, orchestration,
  tool-use loop).
- **(c)** It is cited by ≥2 existing catalog rows as adjacent
  infrastructure (e.g., a database that ≥2 in-scope rows depend on).

If none of (a) / (b) / (c) hold, decline and link to this section in the
rejection comment.

---

## 2. Freshness SLA

Different cells decay at different rates. Stale-threshold per cell type:

| Cell type | Refresh cadence | Rationale |
|-----------|-----------------|-----------|
| **GitHub-derivable** (stars, last-commit, license, issue count) | Quarterly (every 90 days) | T0-4 staleness CI hits the GitHub API on a weekly cron and re-runs cheap signals. Quarterly is the upper bound before a row is considered drifted. |
| **Vendor-claimed** (production scale, latency, benchmark scores, named customers, funding) | Annually, or when a new round happens | Vendor claims aren't auto-verifiable. We refresh them when (i) a new round of ingestion runs, or (ii) the row has been ≥12 months untouched. |
| **Maintainer judgment** (tier, taxonomy axes, "approximate" claims) | When re-tier is requested, or at section-level audits | These are T3 (see §3) and revision is a curatorial call, not a deterministic refresh. |

### Status enum (per row)

Each row has a `status` driven by **last release / last meaningful
commit**:

- **active** — last release within 12 months.
- **stale** — last release 12-24 months ago. Worth flagging but not
  presumed dead.
- **abandoned** — last release >24 months ago. Presumed dead absent
  contrary evidence (active fork, active research group, etc.).

When a row crosses a threshold, **T0-4** (staleness CI, issue #38)
automatically opens a GitHub Issue labeled `stale-row` with the row ID,
last-known status, days since last commit, and a suggested action
(re-tier / mark abandoned / cite reason to retain). The workflow is
implemented in `.github/workflows/staleness.yml`; the testable core is
`scripts/check_staleness.py` (run locally with `make stale-check`). The
web app surfaces the same flag as a small badge on the row in the main
table.

### Section-level reviews

Every six months, a full section audit runs:

- Walks every row in the section.
- Re-runs T1 auto-verifiable signals against live APIs.
- Surfaces T2 cells whose citation URLs no longer resolve.
- Reports a section-health summary to a tracking issue.

Section audits are tracked as Round-N+1 ingestion issues (see #28, #30
for the existing intake-batch processor cadence).

---

## 3. Validation policy

Every cell falls into one of three tiers, defined in **T0-3** (#37) and
mirrored in `docs/SCHEMA.md`.

| Tier | Meaning | Required evidence | Verification |
|------|---------|-------------------|--------------|
| **T1** | Auto-verifiable | GitHub URL, star count, license, last-commit date, issue count | CI re-derives from a live API (GitHub) on each build. |
| **T2** | Source-URL required | Benchmark scores, integration claims, production-deployment claims, named customers | `citation` field MUST be a resolvable URL. `validate.py` rejects T2 cells with no citation. |
| **T3** | Estimate / inferred | Tier, taxonomy axes, "approximate" or qualitative claims | No hard citation; maintainer judgment. Rendered with a distinct UI badge so readers know. |

Drift between a cell and its evidence is the primary failure mode this
schema exists to prevent. When in doubt, **down-tier** (mark T3) rather
than guess.

### How to submit a claim or new row

1. **Web form (preferred)** — `/submit` route on the deployed site.
   Lives at <https://mrpeppersdev.github.io/agent-infrastructure-landscape/submit>.
   The form has a live preview and inline validation; it opens a GitHub
   Issue using the schema below.
2. **GitHub Issue form (fallback)** — `.github/ISSUE_TEMPLATE/intake.yml`.
   Land on the issue tracker, pick "System intake", fill the fields.
3. **Direct PR** — for trivial corrections (typos, dead URLs), open a
   PR against `landscape.html` plus the regenerated JSON mirrors. See
   `README.md` § Editing the catalog for the workflow.

### Who can submit

Anyone. Submissions are public; review is by the maintainer.

### Review SLA

**Best-effort, no fixed cadence.** The project is in steady-state
operation (see `PLAN.md`); the maintainer reviews submissions and
cron-generated PRs when time allows, not on a weekly schedule.
Quarterly catch-up sweeps are the worst-case turnaround.

Review can result in:

- Accepted into a near-term ingestion batch (timing depends on
  available maintainer attention; not promised within N days).
- Held with a follow-up question (commented on the issue).
- Declined with a pointer to §1 (Scope) explaining which boundary it
  crosses.

Per the intake template, every submission is verified before it lands in
`data/landscape.json` — no auto-merge.

If a submission is time-sensitive (e.g., disclosure of incorrect or
outdated information about a vendor), apply the **`urgent`** label and
the maintainer will prioritise. Otherwise treat the queue as quarterly.

---

## 4. Succession plan

Honest description of the current bus factor and what mitigates it.

### Current state

**One maintainer with merge rights.** (MrPeppersDev / repo owner.) This
is the entire risk surface that this section exists to address.

### If the maintainer goes inactive >3 months

The mitigation is **not** "find a successor in advance" — it's
**make the data outlive the maintainer**.

- Per **T0-1** (#35), `data/landscape.json` and `data/landscape.edges.json`
  are first-class data products published under **CC-BY-4.0**. Anyone can
  fork the repo, take the dataset, and run their own display layer.
- The dataset is the asset. The web app, the HTML render, the `make`
  targets, and this maintainer contract are all replaceable downstream
  of the data.
- The render pipeline is documented end-to-end in `Makefile`,
  `docs/SCHEMA.md`, and `docs/DECISIONS.md`. A successor can rebuild
  from `landscape.html` + the JSON mirrors without speaking to the
  original maintainer.

### Co-maintainer slot

**Open.** If you want commit rights on a section or row family, open a
GitHub Issue with the subject line **`Co-maintainer interest`** and
describe:

- Which sections or row categories you want to own.
- Your background / why you're qualified to curate that area.
- Your expected time commitment.

Co-maintainership is granted at the current maintainer's discretion,
typically after a couple of well-scoped contributions.

### Hand-off protocol

**TBD — placeholder for future.** When a second maintainer joins, this
section gets written for real (key rotation, default-reviewer config,
release-tag authority, dispute-resolution rule). Until then, the
durability story is the license, the data, and the documented build.

---

## 5. Contact and reporting

### GitHub Issues — default channel

Open a GitHub Issue for:

- Bug reports (broken links, wrong claims, render errors)
- New row submissions (use the `/submit` form or the intake template)
- Scope questions
- Corrections to existing rows
- Co-maintainer interest

Tracker: <https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues>

### Sensitive issues

For private vendor concerns, takedown requests, or conflict-of-interest
disclosures: open an issue and apply the **`confidential`** label. The
maintainer will triage and follow up out-of-band. Do not include
proprietary or under-NDA material in a public issue body.

### Public discussion

GitHub Discussions is the venue for open-ended conversation (taxonomy
debates, "is X really in scope", "what should be the next analytical
view"). If the Discussions tab is not yet enabled on this repo, request
it via issue and it'll be turned on.

---

## 6. Operational cadence

Honest description of how the maintenance work actually happens, so
contributors know what to expect from the review queue.

### What runs automatically

GitHub Actions workflows generate signal without human action. Daily
crons are staggered across the 12:00–16:00 UTC window so jobs don't
pile up. **Every workflow produces issues or PRs, never direct writes
to `data/landscape.json`** — maintainer review remains the gate for
catalog-state changes. Daily runs move signal, not state.

- **`.github/workflows/staleness.yml`** — daily 12:00 UTC. Walks every
  row with a GitHub URL; opens `stale-row` issues for repos that
  crossed the freshness threshold in §2. Driven by
  `scripts/check_staleness.py`.
- **`.github/workflows/recommendation-drift.yml`** — daily 13:00 UTC
  (Phase 2 / Gate 6, issue #100). Replays `docs/canonical-questions.yml`
  through the Phase 2 recommender (`rankCandidates()`); diffs each
  question's top-5 against yesterday's snapshot. Material movement
  opens a `drift-detected` issue; either way, today's snapshot lands
  in `docs/drift-YYYY-MM-DD.md`. Driven by
  `scripts/cron_recommendation_drift.py` via the Node bridge at
  `mcp/dist/cron-rank-batch.js`.
- **`.github/workflows/capability-incremental.yml`** — daily 14:00 UTC
  (Gate 6). Walks all rows; re-derives `capability-composite-score`
  for any row whose `capability-benchmark-sources` cell changed in the
  past 24h. Opens one auto-PR per affected row. Capped at 20 emitted
  PRs per run. Driven by `scripts/cron_capability_incremental.py`.
- **`.github/workflows/catalog-pulse.yml`** — daily 15:00 UTC (Gate 6).
  Aggregate snapshot: new rows, retirements, stale-cell count, drift
  hot-spots from the prior day's drift run, plus a placeholder for
  per-surface query telemetry once that lands. Writes
  `docs/pulse-YYYY-MM-DD.md`. Driven by
  `scripts/cron_catalog_pulse.py`.
- **`.github/workflows/vendor-price-sweep.yml`** — daily 16:00 UTC
  (Gate 6). Scrapes vendor pricing pages for every hosted-service row
  (`cost-pricing-model` ∈ `per-token`, `per-request`, `subscription`);
  diffs against stored cost cells. Opens one auto-PR per change. When
  the change crosses a `cost-tier` boundary, also opens an issue
  labelled `cost-tier-crossed`. Driven by
  `scripts/cron_vendor_price_sweep.py`.
- **`.github/workflows/audit-section.yml`** — weekly cron. Picks the
  oldest-audited section, opens a reverify or expand PR with proposed
  delta. Rotation policy in `docs/AUDIT.md`.
- **`.github/workflows/capability-rebaseline.yml`** — weekly cron,
  Sundays 06:00 UTC (Phase 2 / Gate 8, issue #102). Snapshots every
  row's current capability score + band into
  `data/_baselines/rebaseline-YYYY-MM-DD.json`; diffs against the
  prior baseline; emits `docs/FINDINGS-YYYY-MM-DD.md` listing top
  movers / band shifts / new / retired rows; opens a
  `phase-2-rebaseline` tracking issue. Ground-truth anchor that
  catches drift from upstream benchmark-methodology shifts that the
  daily incremental cron's per-cell diff would miss. Driven by
  `scripts/capability_rebaseline.py`.
- **`.github/workflows/model-release-watch.yml`** — every 30 minutes
  (Gate 8). Polls vendor RSS/Atom feeds listed in `data/_feeds.yml`;
  release-shaped entries open an issue labelled `intake` +
  `intake-release-watch`, which `intake-research.yml` then picks up
  for enrichment and a draft PR. Per-feed seen-set lives in
  `data/_feeds-seen.json` (first sight of a feed primes the set
  without opening issues). Driven by
  `scripts/model_release_watch.py`.
- **`.github/workflows/intake-research.yml`** — fires on `intake`-
  labeled issues. Runs auto-research; opens a draft PR with proposed
  catalog row. Process documented in `docs/INTAKE.md`.

These workflows produce queue, not throughput. They are useful even
when not acted on immediately — the issues and PRs serve as a durable
record of what changed upstream.

### Human cadence

**Ad-hoc, best-effort.** No fixed weekly review block. The maintainer
processes the queue when time allows. Worst-case turnaround is the
**quarterly catch-up sweep** described below.

### Quarterly catch-up sweep

Approximately every three months (loosely tied to the §2 section-level
review timing), the maintainer does a focused triage pass:

- Close stale `stale-row` issues that the row's status moved past.
- Merge clean reverify PRs from `audit-section.yml`.
- Decide on or close auto-research draft PRs from
  `intake-research.yml`.
- Re-read MAINTAINER.md and DECISIONS.md for drift; update if practice
  has changed.
- Decide whether a vN+1 analysis.md refresh is warranted (the v5→v6
  pattern; typically warranted when row count or schema has shifted
  >5% or a major new analytical view has landed).

### Expectations for contributors

- A submission or comment may sit for **weeks** before the maintainer
  responds. Silence is queue-depth, not rejection.
- Apply the `urgent` label only for time-sensitive issues (vendor
  data is wrong, takedown request, broken-link disclosure that affects
  trust). Overuse erodes the signal.
- The cron workflows mean the catalog stays *measurably* fresh even
  during long gaps in human attention — staleness CI flags drift, the
  section-audit reverify finds dead links, intake-research drafts
  proposals that wait safely until reviewed.

### When this section is wrong

If practice drifts above or below the ad-hoc steady state — e.g., the
project enters a new active build phase, or human attention drops to
zero for >6 months — update this section before the practice gap
becomes a contributor-trust problem.

---

*Last reviewed: 2026-05-18. This file is the governance contract; if
something here disagrees with day-to-day practice, fix this file before
the practice drifts further.*
