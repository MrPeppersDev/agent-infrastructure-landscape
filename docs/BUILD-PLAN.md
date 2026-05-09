# Build plan — navigable landscape app

## Goal

Turn the static `landscape.html` (528 systems × 68 columns) into an interactive
analyst's workbench with search, filters, sort, trend views, and a knowledge
graph showing how systems descend from each other.

The catalog itself is now terminal (every cell is real-data or a justified
"not applicable"). What's missing is the navigability layer that makes the
data usable for the user's stated goal: **trend analysis to identify
best-of-category and inform future additions**.

## Phases

| Phase | Milestone | Scope |
|---|---|---|
| 1 | Data extraction | Convert `landscape.html` → structured `landscape.json` + `landscape.edges.json`. HTML becomes a build artifact. |
| 2 | Table app | SvelteKit static app: virtualized table, search-as-you-type, faceted filters, multi-sort, URL state. |
| 3 | Trend analysis | Created-date timeline, top-N leaderboards, section-vs-section stats. |
| 4 | Knowledge graph | Cytoscape.js force-directed graph + lineage timeline. |
| 5 | Polish & deploy | Detail/compare modals, CSV export, GitHub Pages deploy, "how to read this" page. |

## Issue tracker

GitHub issues #1–#21 in `MrPeppersDev/memory-analysis-program`.
Each issue has a milestone (one of the five phases) and a checklist of
acceptance criteria. Issues are filed serial-first: Phase 1 must finish
before Phase 2; within Phase 2 most issues can parallelize once the project
is bootstrapped.

## Stack decisions

See `docs/DECISIONS.md` for the rationale behind every locked-in choice.
At a glance:

- **SvelteKit + static-adapter** (deployable to GitHub Pages, no server)
- **Plain Svelte components, hand-written CSS** (no Tailwind / shadcn — keep lightweight)
- **Cytoscape.js** for graph viz
- **Always-array** taxonomy and section memberships (so multi-section /
  multi-axis records are first-class, not a special case)
- **Structured cells** (`{value, citation, status}`) — preserves the audit
  trail that 5+ research passes built up
- **Stable IDs** decoupled from display names (so name collisions don't
  merge unrelated systems)

## Workflow once Phase 1 lands

Until Phase 1 is done: edit `landscape.html` directly, as today.

After Phase 1 lands, the workflow inverts:
1. Edit `landscape.json` (or `landscape.edges.json`)
2. Run `make build` → re-renders `landscape.html` as a build artifact
3. Round-trip validation prevents the JSON and HTML from drifting apart
4. Commit both

The rationale for that inversion is in `docs/DECISIONS.md#html-as-build-artifact`.
