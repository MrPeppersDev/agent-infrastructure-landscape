# landscape-cli

A headless command-line interface to the [AI Agent Infrastructure Landscape](../README.md) catalog. Pairs with the [local-stdio MCP server](../mcp/README.md) — same data, same query layer, different consumption mode.

**Use the CLI when** you want terminal exploration, scripting / agentic pipelines, CI integrations, or one-off queries without spinning up a chat interface.
**Use the MCP server when** you want LLM-driven interactive use through Claude Code, Claude Desktop, Cursor, or any other MCP client.

The pure query layer lives in [`../mcp/src/tools.ts`](../mcp/src/tools.ts) and is imported directly — there is exactly one source of truth for catalog logic, no drift between the CLI and the MCP server.

## Quickstart

From a fresh checkout:

```bash
git clone https://github.com/MrPeppersDev/agent-infrastructure-landscape.git
cd agent-infrastructure-landscape/mcp && npm install && npm run build
cd ../cli && npm install && npm run build
./dist/landscape.js sections        # smoke test
```

The CLI imports compiled JS from `../mcp/dist/`, so `mcp/` must be built first. (The `npm install` step in `cli/` runs `tsc` via the `prepare` script, which builds the CLI itself.)

To put `landscape` on your PATH:

```bash
cd cli && npm link        # symlinks `landscape` into your npm global bin
landscape sections
```

## Subcommands

Nine read-only subcommands, mirroring the nine MCP tools.

| Subcommand | What it does |
|---|---|
| `landscape search <query>` | Free-text search over id, name, description, and claims |
| `landscape show <id>` | Print the full record (all 82 cells + taxonomy + sections) |
| `landscape related <id>` | All edges touching a record, in both directions |
| `landscape coverage <dim>` | Per-feature coverage stats (observability / cost / eval / benchmark) |
| `landscape compare <a> <b>` | Side-by-side cell-by-cell comparison plus direct edges |
| `landscape sections` | List all primary section names |
| `landscape recent [--since]` | Records updated since a date (or 20 most-recent) |
| `landscape eval-orphans` | Products with obs but no evals (verified absence) |
| `landscape substrate-risk <s>` | Records that runtime-depend on a substrate |
| `landscape info` | CLI version, schema version, record / edge counts |

Plus `landscape --help` for the auto-generated reference and `landscape <cmd> --help` for subcommand details.

### Global flags

- `--json` — emit machine-readable JSON to stdout (the verbatim result from `tools.ts`)
- `--csv` — emit CSV (header row + data rows; honoured by tabular subcommands)
- `--help`, `-h` — auto-generated help
- `--version`, `-V` — print the CLI version

`NO_COLOR=1` disables ANSI colour; `FORCE_COLOR=1` enables it even when stdout isn't a TTY. By default colour is on when stdout is interactive.

## Worked examples

### Find production-ready memory products

```bash
landscape search "memory" --tier 1 --section "Dedicated memory layers"
```

Returns the T1 (battle-tested) records in the Dedicated memory layers section, sorted as the catalog stores them. Pair with `--limit 5` to cap output.

### Blast-radius analysis: what depends on Anthropic?

```bash
landscape substrate-risk Anthropic
```

Resolves "Anthropic" to the foundation-models record (picking the substrate with the most incoming runtime-dependency edges, by default) and lists every product that declares a runtime dependency. Useful for answering "how many products break if Claude pricing changes?".

### Compare two memory products

```bash
landscape compare mem0--mem0-ai zep-graphiti--getzep-com
```

Cell-by-cell side-by-side. Shows direct edges between the two records first, then prints each column with `=` for matching cells and `≠` for diverging cells. Use `--json` to feed into a diff tool.

### Pipe into a script

```bash
landscape eval-orphans --json | jq -r '.orphans[] | .id'
```

The `--json` flag emits the raw `tools.ts` result; pair it with `jq`, `yq`, or any JSON-aware downstream to extract whatever shape you need. CSV output works the same way for `search`, `sections`, `recent`, `eval-orphans`, `coverage`, and `substrate-risk`.

### Build a Makefile target around the catalog

```make
.PHONY: list-eval-orphans
list-eval-orphans:
	@cd cli && ./dist/landscape.js eval-orphans --csv > ../extraction/eval-orphans.csv
```

The CLI is designed to be composable into scripts and CI: deterministic output, non-zero exit on errors (record not found, unknown dimension, etc.), and machine-readable formats on demand.

## How the CLI relates to the MCP server

| | MCP server | CLI |
|---|---|---|
| Surface | stdio JSON-RPC | shell commands |
| Consumer | MCP clients (Claude Code, Claude Desktop, Cursor, …) | shell, scripts, Makefiles, CI |
| Auth | none (local stdio) | none (local exec) |
| Mutations | none (read-only) | none (read-only) |
| Query layer | [`mcp/src/tools.ts`](../mcp/src/tools.ts) | imports from `mcp/dist/tools.js` |

Both layers share the same nine pure query functions. If one finds a bug or wants a new query, fix `tools.ts` in `mcp/src/` and both consumers pick it up after a rebuild.

## Data freshness

The CLI loads `data/landscape.json` and `data/landscape.edges.json` from the repo at process start. Each subcommand is a one-shot — no caching between invocations. To pick up dataset updates, re-run `make build` from the repo root and run the CLI again.

## Implementation notes

- **One runtime dep**: `commander` (12.x). Colour output is zero-dep ANSI escapes.
- **TypeScript**, compiled to ES2022 ESM, output to `dist/`.
- **No write commands**, no interactive REPL, no plugin system — see issue [#49](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/49) for the scope decision.
- **Exit codes**: 0 success, 1 on usage errors (record not found, unknown dimension, …). All errors go to stderr; output goes to stdout.

## Related work

- [#48](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/48) — MCP server (shares query layer)
- [#35](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/35) — standalone versioned dataset (T0-1)
- [#46](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/46) — runtime-dependency edges (powers `substrate-risk`)
