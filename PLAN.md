# Plan

Operational dashboard. Single-page answer to "what's the state of this
project and what's happening next?" Replaces the prior build-phase
PLAN.md (preserved in git history if you want the archaeology).

*Last updated: 2026-05-18.*

## Posture

**Steady-state operate + distribute.** The T0→T3 build ladder
completed end-to-end (23 closed tier issues; v6 analysis.md shipped in
`ad449da`). No T4 build phase is open. Rationale captured in
`docs/DECISIONS.md` § 2026-05-18.

## Catalog state

- **912 records** across **34 sections** (see README for the section
  list; MAINTAINER §1 for the scope boundary).
- **85 cells per record**, **528 typed edges** (212 of which are
  runtime-dependency from T2-1).
- **15 analytical views** under `web/src/routes/analyses/` (latest:
  breakout-prediction from T3-4).
- **Three consumption surfaces**: the SvelteKit web app at
  `https://mrpeppersdev.github.io/agent-infrastructure-landscape/`,
  the local-stdio MCP server at `mcp/`, the `landscape` CLI at `cli/`.
- **Dataset is its own product**: `data/landscape.json` +
  `data/landscape.edges.json` under CC-BY-4.0, semver-tagged
  (`data-v1.0.0` shipped from T0-1).

## Active workstreams

These are the things that have human attention right now, in rough
priority:

1. **MCP-server npm publish** (#66) — the literal "distribute what
   exists" action. Today's MCP install requires a local clone; an
   `npx -y landscape-mcp` install is the unblocker for external users
   wanting to query the catalog from Claude Code / Desktop. Gating
   decision documented separately under #66 when resolved.
2. **v6-findings writeup for external audiences** — the v6 analysis.md
   surfaces several publishable headlines (semantic-caching is an
   empty market; 91.3% of catalogued products publish no peer-reviewed
   benchmark; MCP-spec-as-substrate at #3 inbound runtime-dependencies;
   Graphiti MCP Server as biggest betweenness bridge). A blog post or
   short paper makes these findings reachable to people not browsing
   the catalog directly.
3. **Co-maintainer recruitment** — MAINTAINER §4 currently has the
   co-maintainer slot *open* but passive. Distribution-phase work
   includes actively offering ownership over a section family
   (foundation models is the highest-decay candidate; vector DBs is
   the lowest-friction onboarding).

## Operational cadence

Best-effort, ad-hoc. No fixed weekly review block. The three cron
workflows (`staleness.yml`, `audit-section.yml`,
`intake-research.yml`) keep generating signal; a quarterly catch-up
sweep handles the backlog. Full description in MAINTAINER §6.

Expect submissions and auto-PRs to sit for weeks before maintainer
attention. The `urgent` label is the escalation path for time-
sensitive issues.

## Open issues snapshot

| # | Title | State |
|---|-------|-------|
| 57 | T3-1 revisit (13 stale rows) | Waiting on external trigger (foundation-models section audit). Passive. |
| 64 | Cron-workflow review cadence | Resolved by this file + MAINTAINER §6. |
| 66 | MCP npm publish gate | Active. Top of distribute queue. |
| 67 | Path A vs B (HTML vs JSON authoritative) | Independent. Worth revisiting now that dataset-as-product is the dominant story; medium effort. |

## When to revisit this posture

Re-evaluate steady-state vs. resuming active build when **any** of:

- A compelling T4 candidate surfaces (a new analytical lens that the
  existing 15 views can't answer, or a new data source that warrants
  schema expansion).
- The catalog's row count or section count shifts >10% via the intake
  pipeline (the v5→v6 doc refresh trigger).
- A co-maintainer is onboarded — their attention bandwidth changes the
  cadence math.
- The cron workflows produce signal that demands faster human
  response than ad-hoc / quarterly can give (e.g., contributors
  expressing frustration with response times).

## Where the documentation lives

- **README.md** — what the project is, how to use the three surfaces.
- **MAINTAINER.md** — scope, freshness SLA, validation policy,
  succession, contact, operational cadence (§1–§6).
- **docs/DECISIONS.md** — every non-obvious design call with rationale
  and reversal cost.
- **docs/SCHEMA.md** — record/edge shape.
- **docs/INTAKE.md** — auto-research pipeline.
- **docs/AUDIT.md** — section-audit rotation.
- **analysis.md** — narrative findings (v6 current).
- **This file** — operational state.
