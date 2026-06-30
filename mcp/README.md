# landscape-mcp

A local-stdio MCP server that exposes the [AI Agent Infrastructure Landscape](../README.md) catalog as a structured query interface for MCP clients (Claude Desktop, Claude Code, Cursor, Cline, etc).

**Read-only.** Wraps `data/landscape.json` (912 records × 85 columns) plus `data/landscape.edges.json` (528 typed edges). Submissions still go through the [/submit route](../web) and GitHub Issues.

## Why this exists

The catalog's edge over LLM synthesis is structured, maintained data. This MCP server makes that data directly addressable from any MCP-capable client — search, compare, drill into edges, surface coverage gaps. Instead of competing with LLMs, it becomes a tool LLMs use.

See [issue #48](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/48) for context.

## Quickstart — local clone (recommended today)

```bash
git clone https://github.com/MrPeppersDev/agent-infrastructure-landscape.git
cd agent-infrastructure-landscape/mcp
npm install
npm run build
node dist/test-tools.js   # smoke test — calls every tool, prints results
npm start                 # runs the server on stdio (Ctrl-C to exit)
```

To wire your local clone into Claude Code:

```bash
claude mcp add landscape -- node /absolute/path/to/repo/mcp/dist/server.js
```

Restart Claude Code; the 12 tools below are now available.

To wire your local clone into Claude Desktop, edit your config:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

Add:

```json
{
  "mcpServers": {
    "landscape": {
      "command": "node",
      "args": ["/absolute/path/to/repo/mcp/dist/server.js"]
    }
  }
}
```

Restart Claude Desktop. The `landscape` server should appear in the MCP menu.

## Quickstart — npx

The package is published to npm with a bundled dataset snapshot, so the install collapses to one line:

```bash
# Claude Code
claude mcp add landscape -- npx -y landscape-mcp@1.0.0
```

```json
// Claude Desktop config
{
  "mcpServers": {
    "landscape": {
      "command": "npx",
      "args": ["-y", "landscape-mcp@1.0.0"]
    }
  }
}
```

### Versions

npm version tracks the bundled `data-vX.Y.Z` tag; bump on dataset releases only. Pin to a specific version (e.g. `landscape-mcp@1.0.0`) when you care about reproducibility — otherwise `npx -y landscape-mcp` picks up whichever dataset shipped most recently.

## Tools

All 12 tools are read-only. Inputs are JSON; outputs are JSON-serialisable.

### `search_records(query, section?, tier?, limit?)`

Free-text substring search over id, name, `desc` cell, and `claims` cell. Case-insensitive. Returns compact summaries — use `get_record` for full details.

- `query` — required search string
- `section` — exact match on primary section name (use `list_sections` for valid values)
- `tier` — 1 (battle-tested) through 5 (theoretical / informal)
- `limit` — default 25, max 200

### `get_record(id)`

Full record by stable id (all 68 cells, taxonomy, section memberships). Returns `null` if the id isn't in the catalog. Find ids via `search_records`.

### `find_related(id, edge_type?)`

Every edge touching the given record id, in both directions, with summaries of the records on the other end. Optionally filter by edge type:

- `built-on` — built on top of another product
- `runtime-dependency` — declared dependency at run time (e.g. on a foundation model)
- `extends` — extends another product's capability
- `forks` — code fork
- `integrates-with` — supports integration with the target
- `competes-with` — competes for the same customer
- `inspired-by` — design / research influence
- `cites` — academic citation (from Semantic Scholar; surfaces `isInfluential` flag)
- `same-team-as` — same originating team / org
- `succeeds` — successor product / paper

### `coverage_summary(dimension)`

Catalog-wide per-feature counts for one of four dimensions:

- `observability` — 7 boolean obs-* columns (LangSmith, OpenTelemetry, Datadog, Helicone, Weave, Langfuse, Arize)
- `cost` — 7 cost-* columns (token budget, prompt caching, semantic caching, batch API, model routing, streaming-only, cost attribution)
- `eval` — 7 eval-* columns (LangSmith Evals, Braintrust, W&B Agent Eval, Helicone Evals, custom test harness, human-loop, prod traffic replay)
- `benchmark` — per-section counts for benchmark-bearing sections

Percentages are denominated against the **analyzed** set (records with ≥1 yes/no signal), not the full catalog — so a low overall backfill rate doesn't artificially deflate every feature.

### `compare(id_a, id_b)`

Side-by-side comparison of two records across every column. Returns each cell pair plus a `match` flag for trivial diffability. Also includes any direct edges between the two records.

### `list_sections()`

Alphabetised list of unique primary section names. Use as the `section` filter on `search_records`.

### `recent_changes(since?)`

Records whose `latest-release` (or `created`, if no release) is on or after the given date. Date is the **shipping date of the upstream product**, not when the catalog was updated. Accepts `YYYY`, `YYYY-MM-DD`, or full ISO timestamps. Omit `since` for the 20 most-recent.

### `find_eval_orphans()`

Products with observability ≥1 tool but ZERO eval tools, where the absence has been verified (≥1 eval cell carries a `yes`/`no`/researched signal). Surfaces the structural failure mode from [LangChain's State of Agent Engineering 2025](https://www.langchain.com/state-of-agent-engineering-2025) survey: 89% of practitioners have observability adopted, only 52% have evals — a 37-point gap that costs builders real production trust.

### `find_substrate_risk(substrate)`

Records that runtime-depend on a given substrate. Useful for blast-radius questions ("how many products break if OpenAI changes pricing?") and lock-in analysis ("which framework is most coupled to a single LLM provider?").

Substrate resolves by exact id first, then by case-insensitive name/id substring (picks the match with the most incoming runtime-dependency edges). Examples:

- `Anthropic` → resolves to Anthropic Claude foundation models, ~62 dependents
- `OpenAI` → resolves to OpenAI GPT family, ~49 dependents
- `MCP` → resolves to the MCP spec, ~34 dependents

### `find_by_decay_cause(cause)`

Records whose `decay_cause` field matches the given cause. Surfaces the mortality forensics from T3-1 — useful for "which products in this space were acquired vs ran out of funding vs were archived on GitHub?"

Enum values: `acquired`, `pivoted`, `unfunded`, `lost-benchmark-race`, `superseded`, `archived`, `research-complete`, `unknown`.

### `predict_citations(record_id)`

Wang-Song-Barabási log-normal citation breakout prediction for a single academic-paper row. Returns the fitted parameters (λ immediacy, μ peak time, σ longevity), predicted asymptote with 90% CI, 10-year prediction, R², phase (`pre-growth` / `growth` / `saturation` / `underfit-data`), and breakout probability. Methodology: Wang, Song & Barabási, *Science* 342:127 (2013).

Returns an error if the record is not an academic paper or its citation trajectory is missing. Use `list_breakouts` for the leaderboard of top predicted breakouts.

### `list_breakouts(limit?)`

Top-N predicted citation breakouts — growth-phase papers with the largest asymptote/observed ratio (still-growing fastest), restricted to rows with real bucketed citation trajectories. Use as a watchlist for which papers to track for citation impact over the next 12-24 months.

- `limit` — default 15, max 50

### `between_models(anchor_low_id, anchor_high_id, use_case?, k?)`

Phase 2 / Gate 3 (issue #97) — positioning recommender. Returns records whose cost × capability composite falls between two anchor record ids. Each candidate carries a score in `[0, 1]`, a rationale list, and a caveats list — LLM-unverified cells are excluded from scoring and surfaced as caveats per spec §3.4.

- `anchor_low_id` / `anchor_high_id` — stable record ids
- `use_case` — optional single tag from the controlled vocabulary: `scoped-agentic`, `long-running-session`, `multi-agent-coordination`, `memory-augmented-chat`, `code-generation-focused`, `analytical-summarization`, `latency-sensitive`, `offline-capable`
- `k` — default 5, max 50

Identical contract is exposed by the `landscape recommend between` CLI subcommand and the `/recommend/between` web route.

## Data freshness

The server loads `data/landscape.json` and `data/landscape.edges.json` from the repo at process start and caches in memory. Restart the server (or your MCP client) to pick up dataset updates. The data files are semver-tagged via GitHub Releases (`data-v1.0.0` onwards) — see [`data/README.md`](../data/README.md).

## Implementation notes

- **Pure query layer.** [`src/tools.ts`](./src/tools.ts) contains every query as a pure function: `(records, edges, args) → result`. The MCP server (`src/server.ts`) is a thin wrapper that registers each function with the SDK. The CLI in issue #49 imports the same `tools.ts` directly.
- **No mutations.** Submissions go through the [/submit web form](../web) → GitHub Issues. This is intentional: an editorial review step is what makes the catalog trustworthy, and a write tool would bypass that.
- **No network.** All queries run against the local JSON snapshot. No external API calls.

## Constraints

- **Local stdio only.** No remote / hosted MCP, no SSE, no streaming.
- **Read-only.** No write tools.
- **No auth.** Not needed for local stdio.

## Related work

- [#35](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/35) — standalone versioned dataset (T0-1)
- [#37](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/37) — claim-tier provenance (T0-3)
- [#46](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/46) — runtime-dependency edges (T2-1) — powers `find_substrate_risk`
- [#49](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/49) — local CLI tool (consumes `tools.ts` directly)
