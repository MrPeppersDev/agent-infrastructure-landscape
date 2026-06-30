# AI Agent Infrastructure Landscape

An open, comparative catalog of the tools developers use to build, deploy,
and operate **autonomous AI agents** — the software systems (Claude Code,
Cursor, AutoGen, LangGraph, Mem0, Zep, etc.) that take instructions, plan,
call tools, remember things across sessions, and act in the world.

Each entry is tracked across **85 attributes** (license, maturity tier,
deployment model, MCP / A2A protocol support, observability stack,
compliance posture, latency, pricing, and dozens more), with **typed
relationships** between systems (built-on, extends, competes-with,
cites…). Today the catalog covers **912 systems and 528 relationships**.

The goal is straightforward: give builders, researchers, and analysts a
single place to compare what exists, see what's actually shipping vs.
just published, and spot the gaps.

## Start here

- **Browse the catalog →** <https://mrpeppersdev.github.io/agent-infrastructure-landscape/>
  — sortable, filterable table with full per-system detail pages, side-by-
  side comparisons, lineages, leaderboards, and "best of" lists (e.g.
  [open-source agent memory](https://mrpeppersdev.github.io/agent-infrastructure-landscape/best/open-source-agent-memory),
  [MCP-enabled systems](https://mrpeppersdev.github.io/agent-infrastructure-landscape/best/agent-memory-with-mcp)).
- **Headline findings →** five short, citable stories distilled from the
  catalog. Read them as [cards on the site](https://mrpeppersdev.github.io/agent-infrastructure-landscape/findings)
  or in source: [`docs/FINDINGS.md`](docs/FINDINGS.md).
- **Raw data →** [`data/landscape.json`](./data/landscape.json) + 
  [`data/landscape.edges.json`](./data/landscape.edges.json). Licensed
  **CC-BY-4.0** — use it however you like, just credit the source.

## What's in the data

Each record is a JSON object with a stable ID, display name, tier
(1 battle-tested → 5 theoretical), one or more section memberships
(e.g. "Dedicated memory layers", "Framework-embedded memory",
"Vector-database infrastructure" — 34 sections in total), and the 85
attribute cells. Every cell carries:

- The claim itself (free-text value).
- A source URL (where the claim came from).
- A status (`real-data`, `estimate`, `not-applicable`, `no-data`, etc.).
- A **provenance tier** (T1 auto-verifiable from a GitHub URL, T2
  resolvable source URL required, T3 estimate).
- A last-verified date for high-volatility cells.

Sources include curated lists (Agent-Memory-Paper-List,
Awesome-GraphMemory), survey papers, benchmark leaderboards (LongMemEval,
LoCoMo, ConvoMem), vendor sites, academic venue pages, and targeted
research-agent sweeps. Claims are vendor-stated unless otherwise marked.
Honest coverage confidence is roughly **88–92%** — known gaps are tracked
in [`PLAN.md`](./PLAN.md). Full schema: [`docs/SCHEMA.md`](docs/SCHEMA.md).

## Use it in your own tools

**MCP server** — query the catalog from any Model Context Protocol
client (Claude Code, Claude Desktop, Continue, etc.). Nine read-only
tools: search, get-by-id, edge traversal, coverage stats, side-by-side
comparison, recent changes, eval-orphan detection, substrate
blast-radius analysis. See [`mcp/`](./mcp) and
[`mcp/README.md`](./mcp/README.md).

```sh
cd mcp && npm install && npm run build
claude mcp add landscape -- node $PWD/dist/server.js
```

**CLI** — the same nine queries as a `landscape <subcommand>` tool.
Text output by default, `--json` / `--csv` for machine-readable use.
See [`cli/`](./cli) and [`cli/README.md`](./cli/README.md).

```sh
cd cli && npm install && npm run build
./dist/landscape.js search "memory" --tier 1 --section "Dedicated memory layers"
```

**Web app** — SvelteKit static export in [`web/`](./web), deployed to
GitHub Pages on every push to `main`.

```sh
cd web && npm install
npm run dev      # local server at http://localhost:5173/
npm run build    # static export
```

## How the catalog stays honest

Three things keep the data trustworthy:

1. **Per-cell provenance.** Every claim points at the source URL it was
   sourced from, with a tier marking how verifiable the claim is. You can
   audit any entry by walking the citation.
2. **Automated freshness checks.** A weekly job
   (`.github/workflows/staleness.yml`) flags rows whose upstream repo
   has gone quiet beyond the freshness SLA defined in
   [`MAINTAINER.md`](./MAINTAINER.md) §2. Stale rows surface in the live
   table with a visible badge.
3. **Self-maintaining workflows.** New systems submitted via the
   [`/submit`](https://mrpeppersdev.github.io/agent-infrastructure-landscape/submit)
   form (or an `intake`-labelled GitHub Issue) are auto-researched into a
   draft PR ([`docs/INTAKE.md`](docs/INTAKE.md)). Existing sections are
   periodically re-audited section-by-section
   ([`docs/AUDIT.md`](docs/AUDIT.md)).

## Editing the catalog (contributors)

`data/landscape.json` is the source of truth — the rendered
`landscape.html` is a build artefact, never edited by hand.

1. Edit `data/landscape.json` directly, or let the intake-research /
   section-audit bots open a PR for you. PRs get a rendered-cell preview
   comment from `.github/workflows/diff-preview.yml` so reviewers see
   exactly what each touched row will look like.
2. Run `make build` locally — reconciles JSON, rebuilds edges and
   citation trajectories, re-renders `landscape.html`.
3. Run `make validate` — five offline gates, ~25 seconds:

   | # | Gate                        | Catches                                                                                  |
   |---|-----------------------------|------------------------------------------------------------------------------------------|
   | 1 | JSON schema                 | Records or edges violating `docs/SCHEMA.md` §7.                                          |
   | 2 | Fast-step determinism       | Non-determinism in extract / reconcile / edge-build scripts.                             |
   | 3 | Render-cycle stability      | Markup drift in render ↔ extract round-trips beyond the documented ceiling.              |
   | 4 | S2 cache integrity          | Corrupted Semantic Scholar cache files.                                                  |
   | 5 | Tier-provenance + freshness | Cells whose tier disagrees with their citation, or rows missing required date metadata.  |

4. Commit the JSON, the regenerated edges file, and the regenerated
   `landscape.html` together. CI re-runs validation plus a byte-identity
   check (the JSON must round-trip cleanly to the committed HTML) on
   every push.

A pre-commit hook is available via `make install-hooks` (idempotent;
short-circuits on changes that don't touch the pipeline).
`make refresh-citations` re-pulls Semantic Scholar data (~15 min); only
needed when adding research-paper rows.

## Governance and license

This catalog has an explicit maintenance contract:
[`MAINTAINER.md`](./MAINTAINER.md). It defines what's in scope (and what
isn't), the freshness SLA per cell type, the 3-tier claim-validation
schema, the succession plan, and how to contribute or request
co-maintainer rights. The contract exists because comparative catalogs
historically die quietly — DB-Engines, State of JS, dbdb.io — and the
surviving ones all publish one.

The catalog data is released under **CC-BY-4.0**. The MCP server and
CLI packages are **MIT** (see their `package.json`).
