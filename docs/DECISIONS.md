# Decision log

This log captures every non-obvious design decision made during the build of
the navigable landscape app. Each entry explains:

- **What** was decided
- **Why** (the reasoning, including options considered and rejected)
- **When** (date — so future readers know how stale the decision might be)
- **Reversal cost** (how hard it would be to change later)

The goal: if anyone (including the user, including future-Claude) wants to
walk back a decision, they can find the original rationale and the tradeoffs
that were on the table.

---

## 2026-05-08: Five-phase build plan

**What.** Build the navigability layer in five phases: (1) data extraction,
(2) table app, (3) trend analysis, (4) knowledge graph, (5) polish & deploy.
Tracked as 21 GitHub issues across 5 milestones.

**Why.** The user's primary use-case is *trend analysis to identify
best-of-category and inform future additions*. That demands sorting,
filtering, leaderboards, and lineage tracing — all of which need the data
in queryable form first. Hence Phase 1 (extraction) is foundational.

The KG was originally proposed as Phase 4 but on user request was kept in
v1 rather than deferred to v2 — they want to "visually see the interaction
and evolution of work that has been built off others' progressions".

**Reversal cost.** Low. Phases can be re-ordered if priorities shift. The
schema in Phase 1 is the only thing that locks downstream choices.

---

## 2026-05-08: HTML-as-build-artifact

**What.** After Phase 1 lands, `landscape.html` becomes a generated
artifact. Source of truth becomes `landscape.json`. Edits flow:
edit JSON → run build → commit both.

**Why.** The user confirmed this was always the intention. The HTML is an
end-user view; the data is the asset. Once an app exists, the HTML is just
the no-JS fallback / shareable static export.

**Options rejected.**
- *Keep HTML as source.* Would force every future data update to hand-edit
  HTML, which 5 rounds of work has shown is error-prone (column-balance
  bugs, cell-format inconsistencies).
- *Drop HTML entirely.* Loses the no-JS-required readable artifact. The
  HTML rendered from JSON is also useful as a check (does the rendered
  output match what the prior HTML had?).

**Reversal cost.** Medium. Going back to HTML-as-source means redoing
extraction; not catastrophic but wasteful.

---

## 2026-05-08: Stable IDs decoupled from display names

**What.** Every record has a stable `id` (slug from name + arxiv-id / URL).
The id is what edges and cross-references use; display name is just for
humans.

**Why.** Two kinds of name collisions exist:
1. **Same paper, different capitalization** (AriGraph / Arigraph) — must
   collapse to one record.
2. **Different systems, similar names** (ATLAS-the-memory-paper at arxiv
   2505.23735 vs Atlas-the-Meta-AI-retriever at arxiv 2208.03299) — must
   stay distinct.

Without stable IDs, normalize-and-merge would conflate (2). Without
explicit dedup, (1) gets two records.

**Options rejected.**
- *Use the display name as id.* Breaks for case-difference duplicates and
  forces every consumer to call a normalize() function.
- *Use arxiv-id as id when available, fallback to slugged name.* Cleaner
  but doesn't help for products without arxiv IDs.

**Reversal cost.** High after edges file is built — every edge would need
to be re-keyed.

---

## 2026-05-08: Always-array for taxonomy axes and section membership

**What.** `taxonomy.storage` is `[{value, primary, reason}]`, never a bare
string. `sections` is `[{section, subsection, primary, reason}]`. Even
single-value records use 1-element arrays.

**Why.** Multi-value cases legitimately exist (Memvid is both a library
and a Claude Code plugin; some systems use both vector and graph storage).
Modelling them as a special case via "primary value + secondary array"
makes consumers branch on the shape; always-array means consumers pay a
small unwrap tax everywhere but never a special-case tax.

User decision: "always array" — they prioritized future-proofing over
the small ergonomic cost.

**Reversal cost.** Medium. Going scalar after the fact requires a
migration script + every consumer to be updated.

---

## 2026-05-08: Structured cells, not plain strings

**What.** Each of the ~60 non-taxonomy cells is `{value, citation, status}`
where `status ∈ {real-data, not-applicable, depth-floor-reached, no-data}`.

**Why.** Five rounds of research-pass work built up a meaningful audit
trail per cell — citation URLs, "we searched here and found nothing" markers,
"not applicable because this is a research paper" markers. Plain strings
would lose that. The status enum lets the UI filter ("show only cells with
real data") and lets future editors see at a glance which cells are
deliberately empty vs unfilled.

**Options rejected.**
- *Plain strings.* Loses provenance. Would force every UI filter to
  re-parse phrases.
- *Per-cell objects with arbitrary keys.* Too loose; the four-status enum
  gives consistent semantics across all cells.

**Reversal cost.** Low for collapsing back to strings (just take `.value`).
High for regenerating citations and statuses from collapsed strings.

---

## 2026-05-08: SvelteKit + static-adapter, no UI framework

**What.** Phase 2 is a SvelteKit project in `web/` with `@sveltejs/adapter-static`.
Plain Svelte components, hand-written CSS. No Tailwind, shadcn, Material,
etc. Build output to `docs/` for GitHub Pages.

**Why.** User said "small svelte build" + "lightweight" + "show all 68
columns by default". They want a fast, focused tool, not a designed-system
showcase. Hand-written CSS for ~5 components is less code than configuring
a CSS framework.

**Options rejected.**
- *Plain JS + DataTables / similar library.* Faster to start, but Phase 3+
  needs custom components (timeline, leaderboards, graph) that don't fit a
  one-size-fits-all table lib.
- *Next.js / React.* Would work; Svelte is leaner for a static site of this
  size and the user explicitly chose it.

**Reversal cost.** Medium. Could migrate to React/Next later but would
rewrite components.

---

## 2026-05-08: Cytoscape.js for graph viz

**What.** Phase 4 uses Cytoscape.js for the force-directed graph view.

**Why.** 528 nodes + estimated 1-3k edges is in Cytoscape's sweet spot.
It handles node/edge styling per type, supports the cola/fcose layouts
needed for legible clusters, and degrades gracefully on larger sets if
the catalog grows.

**Options rejected.**
- *svelte-flow.* Native Svelte but designed for editor-style flowcharts;
  weaker at >500 nodes.
- *D3 from scratch.* Full control but multiplies build time.
- *vis-network.* Comparable to Cytoscape but smaller community.

**Reversal cost.** Low. The graph view is one component; swapping libraries
is contained.

---

## 2026-05-08: KG edges sourced from S2 citations + cell mining

**What.** Phase 1 extracts edges from (a) `data-5-cross-references.csv`,
(b) regex-mining over `claims`/`desc`/`repro`/`code-release` cells, and
(c) Semantic Scholar `isInfluential` citations for every research-paper
row.

**Why.** User chose "full to (b) from start" rather than the lighter
option of (a)+(b) only. The reasoning: cell-mining gives commercial
edges (built-on, integrates-with) but misses academic lineage (paper A
cites paper B). For trend analysis the academic lineage is the more
interesting story — that's what surfaces architectural fork chains
(RSSM family, KV-cache eviction family, Graph-RAG hierarchy, Files-as-
memory thread already identified in `analysis.md`).

S2's `isInfluential` flag avoids the long tail of cites that don't
matter. Free tier is rate-limited (100 req / 5min) which is enough for
the ~150 research-paper rows.

**Reversal cost.** Low. Edges file is rebuilt by the script; trim or
expand sources by editing `scripts/build_edges.py`.

---

## 2026-05-07: Slug algorithm — `<name-slug>--<source-suffix>`

**What.** The `id` for each record is the lowercase name-slug, joined
to a source-suffix by a double-dash (`--`). Suffix priority:
arxiv-id → github owner/repo → registrable domain → none. Full
algorithm in `docs/SCHEMA.md#21-slug-algorithm`.

**Why.** Two pressures: (1) the slug must distinguish ATLAS-the-memory-paper
from Atlas-the-Meta-AI-retriever (same `<name-slug>`, different arXiv IDs),
and (2) it must be human-readable in URLs and grep output (so
`atlas--arxiv-2505-23735` beats a hash like `7f3a2c1`).

The double-dash is the visual separator: a single `-` would conflict
with the in-name word separator (e.g. "AriGraph" → `ari-graph`). `--`
is unambiguous.

**Options rejected.**
- *UUID per record.* Stable but unreadable; defeats grep / URL ergonomics.
- *Just the arXiv ID where present.* Doesn't help products; mixed-shape
  ids are uglier than uniformly-shaped ones.
- *Single-dash separator.* Clashes with name words. Tried it on paper
  and `atlas-arxiv-2505-23735` reads as "atlas-arxiv 2505 23735" which
  is wrong.

**Reversal cost.** High. Re-keying every edge in `landscape.edges.json`
is mechanical but a hassle.

---

## 2026-05-07: Top-level shape is `{schemaVersion, generatedAt, records}`, not a bare array

**What.** `landscape.json` is a JSON object with metadata fields and a
`records: [...]` array, rather than an anonymous top-level array.
Same for `landscape.edges.json` with `edges: [...]`.

**Why.** Need a place to stash `schemaVersion` for forward-compat,
plus `generatedAt` and `sourceHtml` for traceability. A bare array
would force adding a sidecar file or moving to an object later anyway.

**Options rejected.**
- *Bare array.* Cheaper today, costlier the first time we break the
  schema and consumers can't tell which version they're reading.
- *NDJSON / JSONL.* Streams better but loses JSON Schema validation
  ergonomics; consumers are SvelteKit static loaders that prefer
  whole-file JSON.

**Reversal cost.** Low. Wrap or unwrap with one-line script.

---

## 2026-05-07: extract.py — silently drop non-URL citation hrefs

**What.** When `<a class="cite" href="X">` has an `href` that is not an
`http(s)://` URL — e.g. `href="N/A"`, `href="taxonomy/tags.json"`,
`href="inferred from primary tags ..."`, `href="searched 2026-05-06 — ..."`,
`href="no funding — academic research"` — the extractor sets the cell's
`citation` to `null` rather than passing the placeholder through.

**Why.** SCHEMA.md §7.1.11 requires `citation` to be either `null` or an
`http(s)://` URL — the validator rejects anything else, and consumers that
treat `citation` as a click target would break on these strings. The
placeholders are bookkeeping the researchers used to record provenance
inline; they aren't real URLs. We carry the same information through the
cell's `value` (most of the time) and via `status` (e.g. `not-applicable`,
`depth-floor-reached`), so dropping the bogus `citation` doesn't lose
signal that downstream needs.

**Reversal cost.** Low. The extraction can be rerun at any time; if a
future consumer wants the placeholders, add a `citationNotes` field and
re-emit.

---

## 2026-05-07: extract.py — `type` is the first cell, not a separate top-level field

**What.** The HTML row layout is `name | type | tax-storage | tax-retrieval
| tax-persistence | tax-update | tax-unit | tax-governance | tax-conflict
| desc | claims | …`. The extractor stores `type` (Memory model) inside
the `cells` object as the first key, even though it visually sits between
`name` and the taxonomy axes in the HTML.

**Why.** SCHEMA.md §2.5 lists `type` as cell #1 of the 60 cell columns.
Keeping it inside `cells` (and using the same `{value, citation, status}`
shape as every other cell) means consumers don't need to special-case a
67th top-level field; iterating `record.cells` covers every non-taxonomy,
non-name column uniformly.

**Reversal cost.** Low. Promoting `type` to a top-level field would
require updating the schema, the extractor, and every consumer — but
nothing else is keyed on the choice, so the migration is mechanical.

---

## 2026-05-07: extract.py — taxonomy axis values from free-text fall back to first-token

**What.** Most tax-* cells use `<span class="tax-pill tax-<value>">` pills
(easy to extract). Some — older NVIDIA-style rows, plus the tax-conflict
column which is mostly free-text descriptions — have bare text instead
(e.g. `<td class="tax-storage">kv ↗</td>` or `<td class="tax-conflict">
LLM-arbitrate via fact-extraction prompt: extracts facts, …</td>`). For
these the extractor takes the first `[a-z0-9-]+` token of the cell text
as the canonical `value` and stores the full text in `reason` if the two
differ.

**Why.** The schema requires every taxonomy axis to be a non-empty array
with exactly one primary value. Pulling the first token preserves the
single-value invariant for downstream consumers, and stashing the full
text in `reason` keeps the human-written nuance available for the table
view. The reconciliation pass (#3) and any future taxonomy-vocabulary
audit can clean up tokens that aren't in the controlled vocabulary list.

**Reversal cost.** Low. Re-running the extractor after vocabularly
fixes is mechanical.

---

## 2026-05-07: extract.py — `<span class="no-data">` content drives status detection

**What.** The four `status` values (`real-data`, `not-applicable`,
`depth-floor-reached`, `no-data`) are detected by inspecting the *text
content* of any `<span class="no-data">` inside a cell. A cell with no
such span is `real-data`; a span containing "not applicable" or starting
with "n/a" is `not-applicable`; a span containing "searched not found",
"depth-floor reached", "not specified", "position paper", or any of a few
other documented good-faith-search annotations is `depth-floor-reached`;
an empty span or one containing only "no data" is `no-data`. Anything
else inside a `no-data` span defaults to `depth-floor-reached`.

**Why.** SCHEMA.md §3 documents the detection rules at a high level but
deliberately stops short of enumerating every researcher-written
annotation phrase. The HTML accumulated several stylistic variants over
the five rounds of fill ("no public funding", "parent is public",
"position paper / no quantitative eval", …); detecting them robustly via
substring matching avoids re-fighting the formatting once the JSON is
the source of truth.

**Reversal cost.** Low. New phrasings can be added to the substring
table; the test is that the per-status counts (printed at the end of
`extract.py`) move in the expected direction.

---

## 2026-05-07: extract.py — fixed `generatedAt` for byte-stable round-trips

**What.** `extract.py` writes `generatedAt: "2026-05-07T00:00:00Z"` by
default (overridable via `EXTRACT_GENERATED_AT` env var). It does *not*
use `datetime.utcnow()`.

**Why.** Issue #2's acceptance gate is "running extract twice produces
byte-identical JSON". A clock-driven timestamp would defeat that gate
and pollute every git commit with a timestamp diff even when the data
is unchanged. The extractor is meant to run on demand; a CI/release
script can override the env var when a real timestamp matters.

**Reversal cost.** Low. Set the env var, or change the default constant
on a release commit.

---

## 2026-05-07: reconcile.py — cell merge prefers status, then primary's framing for cross-listings

**What.** When the reconciliation pass collapses two records into one, the
cell merge function prefers cells by status (`real-data` > `not-applicable`
> `depth-floor-reached` > `no-data`) and within the same status falls back
to one of two strategies:

- For **true duplicates** (case-difference dups of the same paper, e.g.
  `arigraph` + `AriGraph`): the substantively-longer real-data cell wins.
  Both records purport to describe the same thing, so the longer text
  almost always reflects an extra round of research depth.
- For **cross-listings** (one product listed in two sections, e.g.
  Mem0 in both Dedicated-memory-layers and Memory-observability-&-monitoring):
  the primary record's cell wins verbatim — even when the secondary cell
  is longer. The two records describe the same product through different
  lenses, and the primary section's framing is the canonical one we want
  the final record to wear.

**Why.** Initial implementation used "longer real-data wins" everywhere.
That degraded cross-listed records: Mem0's `desc` ended up being the
AgentOps-integration-specific description ("surfaces Memory Operation
Timeline, Search Analytics, …") rather than the canonical product
description ("Universal memory layer for AI agents, three concurrent
stores"). The longer text was about a *secondary* framing; using it as
the canonical content misrepresents the system. Switching the
cross-listing path to "primary wins on ties" preserves the canonical
framing while still letting the secondary record fill in cells where it
genuinely had higher-status data.

**Reversal cost.** Low. The merge logic is one function in
`scripts/reconcile.py`; flipping the `prefer_longer` flag back on is a
one-line change.

---

## How to extend this log

When you make a non-obvious decision while implementing an issue, add
an entry here. Template:

```markdown
## YYYY-MM-DD: Short title

**What.** One-paragraph description.

**Why.** The reasoning. Include options considered and why you rejected them.

**Reversal cost.** Low / Medium / High, with one sentence explaining.
```

Skip entries for obvious decisions ("we used Python because the project
uses Python"). Skip entries for things derivable from the code itself
("we named the function `extract_row`"). The log is for design choices
where reading the code alone wouldn't tell future-you why it was done
that way.
