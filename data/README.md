# AI Agent Infrastructure Landscape — Dataset

This directory is the **canonical home of the catalog data**. It is a
first-class data product, decoupled from the SvelteKit display layer in
`web/` so that the dataset can outlive any single rendering surface.

If the web app stops deploying, this dataset is still useful.

## Files

| File                     | Size   | Description                                                                                  |
|--------------------------|--------|----------------------------------------------------------------------------------------------|
| `landscape.json`         | ~11 MB | All catalog records (currently 912 systems × 68 columns). Source of truth for table / graph. |
| `landscape.edges.json`   | ~94 KB | Typed relationships between records (built-on, extends, integrates-with, cites, …).          |

## Schema

The full schema spec — top-level shape, per-record field set, the
four-state `status` enum, the nine edge-type vocabulary, validation
rules — is at [`../docs/SCHEMA.md`](../docs/SCHEMA.md).

The top-level shape of each file:

```json
// landscape.json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "2026-05-14T00:00:00Z",
  "sourceHtml": "landscape.html",
  "records": [
    { "id": "...", "name": "...", "tier": 1, ... }
  ]
}
```

```json
// landscape.edges.json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "2026-05-14T00:00:00Z",
  "edges": [
    { "from": "...", "to": "...", "type": "built-on", ... }
  ]
}
```

Each record's `schemaVersion` field tracks the *data schema* (see
`docs/SCHEMA.md`); the *dataset release* is versioned separately
via GitHub Releases (`data-vMAJOR.MINOR.PATCH`).

## Versioning

The dataset is published on GitHub Releases under tags shaped
`data-vMAJOR.MINOR.PATCH`, semver-style.

- **MAJOR** — schema-breaking change (renamed field, removed column,
  changed enum). Consumers must update their parser.
- **MINOR** — additive schema change (new field, new enum value) OR
  bulk row additions / new section. Old consumers still parse.
- **PATCH** — content corrections, citation refreshes, no schema
  change.

Current version: **`v1.0.0`** (first standalone release).

See [`../docs/DECISIONS.md`](../docs/DECISIONS.md) for the rationale
behind any specific schema choice.

## Provenance

Every record was sourced from one of:

- Curated lists (Agent-Memory-Paper-List, Awesome-GraphMemory)
- Survey papers (`arxiv.org/abs/2512.13564`, `arxiv.org/abs/2508.10824`)
- Benchmark leaderboards (LongMemEval, LoCoMo, ConvoMem)
- Vendor websites and academic venue pages
- Targeted research-agent sweeps (~25 agents over multiple sessions)

URLs were verified at time of entry. Claims (the right-hand column for
many rows) are vendor-stated unless otherwise marked. Some 2026 arxiv
IDs were independently verified by a paper-verification pass.

## How the data is produced

`landscape.html` is the human-edited source of authority. `make build`
runs the deterministic pipeline:

```
extract.py  →  reconcile.py  →  build_edges.py  →  fetch_citations.py --offline
```

…which regenerates `data/landscape.json` and `data/landscape.edges.json`
from the HTML. `make validate` enforces schema + determinism +
round-trip + cache gates. See the top-level [`README.md`](../README.md)
for the full workflow.

## Intended use

- **Cross-system comparison** — given a problem, what tools / techniques exist?
- **Adoption signal** — what's actually being used in production vs. just published?
- **Trend signal** — what's growing, what's saturating, what's being abandoned?
- **Analytics** — pull the JSON, parse it, drop it into your favourite tool
  (pandas, DuckDB, jq, Observable, …). No API key, no rate limit, no shutdown
  risk.

The dataset is intentionally self-contained: every record has a stable `id`,
a primary `url`, and enough fields to be useful in isolation. No external
service lookup is required to make sense of a row.

## License

The dataset is released under
[**CC-BY-4.0**](LICENSE) — free to use, redistribute, and adapt, with
attribution. Suggested citation:

> AI Agent Infrastructure Landscape (Memory Analysis Program), Dataset v1.0.0.
> https://github.com/MrPeppersDev/memory-analysis-program

The repository code (scripts, web app, build pipeline) uses a separate
license; see the repo root for details. Code and data licenses are
deliberately distinct so the data can be redistributed without dragging
in code obligations.

## Stability guarantee

For a given `data-vX.Y.Z` release tag, the two JSON files are immutable —
fetching them from the release assets will always return byte-identical
content. The `main` branch may drift between releases as new rows land
and citations refresh.

For reproducible analysis, **always pin to a release tag**, not the
`main` branch.

## Related

- Top-level [`README.md`](../README.md) — repo overview, build, and editing workflow.
- [`../docs/SCHEMA.md`](../docs/SCHEMA.md) — exhaustive field reference and validation rules.
- [`../docs/DECISIONS.md`](../docs/DECISIONS.md) — historical rationale for schema choices.
- [`../docs/BUILD-PLAN.md`](../docs/BUILD-PLAN.md) — pipeline structure (extract → reconcile → render).
