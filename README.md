# AI Agent Infrastructure Landscape

A comprehensive catalog of AI agent infrastructure — memory systems, harnesses, IDEs,
frameworks, training platforms, search substrates, vertical agent products, voice
platforms, robotics stacks, and adjacent infrastructure. Built as the foundation for
comparative and trend analysis for builders making technology decisions.

This project began as a "Memory Systems Landscape" (memory remains the most-developed
sub-narrative — analysis.md, lineage detection, archetype recipes) and expanded
in Round 7 / Round 11 / Round 12 to cover the broader agent-infrastructure sphere.
The repo path and historical commits still reference "memory-analysis-program";
the URL and Pages deployment remain at that path.

## What's in here

- **`data/landscape.json` + `data/landscape.edges.json`** — the canonical
  dataset. 912 records × 68 columns of catalog data plus 316 typed edges
  between them. Released under CC-BY-4.0; semver-tagged via GitHub
  Releases (`data-v1.0.0` onwards). Decoupled from the web app per
  [issue #35](https://github.com/MrPeppersDev/memory-analysis-program/issues/35)
  so the data outlives any single rendering surface. See
  [`data/README.md`](./data/README.md) for schema + intended use.
- **`landscape.html`** — the human-edited source of authority. ~912 entries
  across ~30 sections / sub-groups, with tier badges (T1 battle-tested →
  T5 theoretical / informal). Run `make build` to regenerate the JSON
  mirror.
- **`PLAN.md`** — current state, deferred work, and the data we need to pull in
  before doing real trend / adoption analysis.

## Sections currently in the landscape

Production / commercial:
- Dedicated memory layers
- Framework-embedded memory
- Platform-provider memory
- Coding-agent memory
- Browser-agent memory
- Personal AI / PKM / lifelogging memory
- Voice-first / wearable AI memory
- Vertical / domain-specific AI memory (sub-groups: scientific, healthcare, legal,
  customer-support / voice, gaming / NPC, robotics / autonomous-driving / embodied)

Research / academic:
- Research / specialised systems
- Recent method papers (sub-groups: factual / experiential / working memory /
  parametric & latent / world-model / continual learning / memory-augmented RL /
  cognitive-architecture-inspired)
- Retrieval-as-memory hybrids

Adjacent / infrastructure:
- File-backed / editor paradigms
- Claude Code memory mechanisms (incl. MCP servers)
- Knowledge-graph platforms
- Vector-database infrastructure
- Enterprise-search adjacencies
- Memory benchmarks & evaluation
- Memory observability & monitoring
- Memory governance, privacy & safety

Speculative:
- Theoretical / informal — ideas without a paper

## Why this exists

Three distinct uses, in priority order:

1. **Cross-system comparison** — given a problem, what tools / techniques exist?
2. **Adoption signal** — what's actually being used in production vs. just published?
3. **Trend signal** — what's growing, what's saturating, what's being abandoned?

The landscape catalog is the substrate for (1). Adoption and trend analysis are
downstream uses that need additional data we haven't gathered yet — see `PLAN.md`.

## Methodology / provenance

Every entry was sourced from one of:
- Curated lists (Agent-Memory-Paper-List, Awesome-GraphMemory)
- Survey papers (`arxiv.org/abs/2512.13564`, `arxiv.org/abs/2508.10824`)
- Benchmark leaderboards (LongMemEval, LoCoMo, ConvoMem)
- Vendor websites and academic venue pages
- Targeted research-agent sweeps (~25 agents over multiple sessions)

URLs verified at time of entry. Claims (the right-hand column for many rows) are
vendor-stated unless otherwise marked. Some 2026 arxiv IDs were independently
verified by a paper-verification pass.

## Status

The catalog is comprehensive enough for use as a reference. Honest confidence on
landscape coverage: ~88-92% as of 2026-05-06. The known gaps and the plan to close
them are in `PLAN.md`.

A weekly staleness check (`.github/workflows/staleness.yml`, scheduled
Mondays 12:00 UTC) walks every row with a GitHub repo URL and opens a
`stale-row` labelled issue when the upstream repo hasn't had a commit
inside the freshness SLA from `MAINTAINER.md` §2 (active <12mo, stale
12-24mo, abandoned >24mo). Run `make stale-check` for the same scan
offline. The web app surfaces flagged rows with a small badge in the
main table.

## Governance

This catalog has an explicit maintenance contract — see
[`MAINTAINER.md`](./MAINTAINER.md). It defines:

- What's in scope and what's not (anti-creep armor).
- Freshness SLA per cell type and per-row status thresholds (active /
  stale / abandoned).
- The 3-tier claim-validation schema (T1 auto-verifiable → T3 estimate).
- Succession plan (one maintainer today; data is published under
  CC-BY-4.0 so the catalog outlives any single steward).
- How to submit, where to report, and how to ask for co-maintainer
  rights.

Adopted to close the catalog-deaths-research-identified governance vacuum
(single-maintainer bus factor, scope inflation, silent decay). Survivors
of the catalog-decay graveyard (DB-Engines, State of JS, dbdb.io) all
publish a maintenance contract; this is ours.

## MCP server

A local-stdio MCP server lives in [`mcp/`](./mcp) and exposes the catalog as
a structured query interface for Claude Code, Claude Desktop, and any other
MCP-capable client. Nine read-only tools cover search, get-by-id, edge
traversal, coverage stats, comparison, recent-changes, eval-orphan detection,
and substrate blast-radius analysis. See [`mcp/README.md`](./mcp/README.md)
for the tool reference and client config snippets.

Quickstart from a local clone:

```
cd mcp && npm install && npm run build
claude mcp add landscape -- node $PWD/dist/server.js
```

Once published to npm (gated on a separate release-cadence decision), it
collapses to `claude mcp add landscape -- npx -y landscape-mcp`.

The MCP server is the first alternative consumption surface for the
standalone dataset (T0-1). A local CLI tool (issue #49) will follow,
sharing the same pure query layer in [`mcp/src/tools.ts`](./mcp/src/tools.ts).

## CLI

A headless command-line interface lives in [`cli/`](./cli) and exposes the
same nine query functions as `landscape <subcommand>` calls. Use it for
terminal exploration, scripting, agentic pipelines that aren't MCP-based,
and CI integrations. See [`cli/README.md`](./cli/README.md) for the full
reference.

Quickstart from a local clone:

```
cd mcp && npm install && npm run build
cd ../cli && npm install && npm run build
./dist/landscape.js sections        # smoke test
```

Examples:

```
landscape search "memory" --tier 1 --section "Dedicated memory layers"
landscape substrate-risk Anthropic
landscape compare mem0--mem0-ai zep-graphiti--getzep-com
landscape eval-orphans --json | jq -r '.orphans[] | .id'
```

Output is text by default with optional ANSI colour; pass `--json` for a
machine-readable result (verbatim from `tools.ts`) or `--csv` where the
result is tabular (search / sections / recent / eval-orphans / coverage /
substrate-risk).

## Web app

A SvelteKit static-export landing page lives in `web/` (Phase 2). Today it's
proof-of-life — the row and edge counts are wired to `data/landscape.json` and
`data/landscape.edges.json` at build time. Phase 2 issues #9-#12 will fill in
the table view, search, filters, and URL state.

Live site: <https://mrpeppersdev.github.io/memory-analysis-program/> (after deploy).

```
cd web
npm install
npm run dev      # local dev server at http://localhost:5173/
npm run build    # static export → ../docs/ (committed for GitHub Pages)
```

The build output is checked in under `docs/` (alongside the project markdown
in the same directory). The deploy is wired by
`.github/workflows/pages.yml` — push to main, the workflow rebuilds with
`BASE_PATH=/memory-analysis-program` and publishes via
`actions/deploy-pages@v4`. Locally you can still open `docs/index.html`
from a fresh checkout (with no base-path) for a quick sanity check.

## Editing the catalog

Phase 1 (issues #1–#7) shipped a structured mirror of the catalog in
`data/landscape.json` and a relationship file in `data/landscape.edges.json`,
plus a render-from-JSON script in `scripts/render.py`. **Today's source of
authority is still `landscape.html`** — `render.py`'s output diffs from the
hand-edited HTML by ~50k lines (mostly tier-sort row reordering and dropped
inline markup like `<span class="signal-num">`, `<br>`, etc. that
`extract.py` collapses to plain text). Inverting that — making JSON the
authority and HTML a build artefact — is **deferred** until `extract.py`
preserves more of that markup. See the Path A vs Path B decision in
`docs/DECISIONS.md`.

Workflow today (Path B):

1. Edit `landscape.html` by hand as you have through Rounds 1–6.
2. Run `make build` to refresh `data/landscape.json` and
   `data/landscape.edges.json` from the new HTML.
3. Run `make validate` (described below). Fix any reported failures.
4. Commit `landscape.html` plus the regenerated JSON mirrors together.
   The CI workflow at `.github/workflows/validate.yml` re-runs the gates on
   push and PR.

**New systems submitted via the [`/submit`](web/src/routes/submit/+page.svelte)
form (or the `intake` Issue template) are auto-researched by the workflow
at `.github/workflows/intake-research.yml` — see [docs/INTAKE.md](docs/INTAKE.md)
for the end-to-end flow, per-cell tier strategy, local-test recipe, and
failure modes.**

`make refresh-citations` is a separate target that re-pulls Semantic Scholar
data — it takes ~15 min and is only needed when new research-paper rows have
been added or the catalog wants to refresh inbound-influence counts.

## Validation

`make validate` runs four cheap correctness gates in ~25 seconds. None of
them touch the network.

| # | Gate                    | Catches                                                                                          |
|---|-------------------------|--------------------------------------------------------------------------------------------------|
| 1 | JSON schema             | Records or edges that violate `docs/SCHEMA.md` §7 (bad enums, missing primary, dangling edges).  |
| 2 | Fast-step determinism   | Non-determinism in `extract.py` / `reconcile.py` / `build_edges.py` (random orders, clock-driven IDs). |
| 3 | Render-cycle stability  | Markup drift in `render.py` ↔ `extract.py` round-trips beyond the documented 16-line ceiling.    |
| 4 | S2 cache integrity      | Corrupted `extraction/s2-cache/*.json` files (so `fetch_citations.py` won't surprise-fail).      |

A pre-commit hook that runs `make validate` automatically before every commit
ships in `scripts/git-hooks/pre-commit`. Install it with `make install-hooks`
(idempotent). The hook short-circuits when no pipeline-relevant files are
staged, so commits to `PLAN.md` or `analysis.md` aren't slowed down. Bypass
the hook for a single commit with `git commit --no-verify`.

A CI workflow that runs the same `make validate` on push and PR is in the
issue tracker but not yet committed — the working OAuth token doesn't have
the `workflow` scope. To add it, refresh your `gh` token with
`gh auth refresh -s workflow` and commit a `.github/workflows/validate.yml`
that runs `make validate` on a Python 3.11 runner with `beautifulsoup4`
installed.
