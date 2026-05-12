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

## 2026-05-07: build_edges.py — phrase rules, crossref-relationship mapping, same-team-from-GH-org

**What.** `scripts/build_edges.py` produces `web/landscape.edges.json` from
four sources, in order of confidence: (1) `.agent-results/data-5-cross-references.csv`
explicit pairs, (2) regex-mined phrases inside `cells.{desc,claims,repro,
code-release,adjacent-infrastructure}`, (3) curated cross-listing pairs
(currently the `claude-brain → memvid built-on` edge), and (4)
`same-team-as` inferred from records that share a `--gh-<owner>-<repo>`
GitHub owner. The script writes a deterministic file (sorted by
`(source, target, type)`, fixed `generatedAt`).

Three non-obvious choices:

1. **Crossref-relationship-type mapping is one-to-many.** The CSV's
   `relationship_type` column has 31 distinct values (`integrates_with`,
   `substrate`, `mcp_wrapper`, `bundled_integration`, `graph_backend`,
   `default_substrate_local`, …). We collapse them into the eight-edge
   vocabulary (`built-on` / `extends` / `forks` / `integrates-with` /
   `competes-with` / `inspired-by` / `same-team-as` / `succeeds`) per the
   table in `CROSSREF_TYPE_MAP`. Substrate / backend / store / wrapper
   relationships all map to `built-on`; integration / partnership /
   adapter / toolkit relationships map to `integrates-with`; explicit
   `fork_of` and `variant_of` map to `forks` / `extends` respectively.
   Rationale: SCHEMA's eight types are the consumer-facing taxonomy; the
   CSV's finer-grained labels were research notes, not a vocabulary the
   graph view needs to surface.

2. **Substring resolution rejects single-token contains-matches.** First
   implementation accepted any name where `hint in name` or `name in hint`
   (with len ≥ 4). That mis-resolved `inspired by retrospective consolidation`
   to `retro--arxiv-2112-04426` (the RETRO retrieval paper) — clearly
   wrong, but `retro` is a substring of `retrospective`. The fix: require
   either an exact name, a token-boundary prefix match (`hint` starts the
   name, e.g. "memoryllm" → "MemoryLLM (original)"), or a whole-word
   match. The `NAME_ALIASES` table covers the legitimate short-form
   references (`Memobase`, `Cline`, `Zep`, `MemGPT`, …). When in doubt,
   discard rather than mismatch — the analysis-4 inbound counts depend on
   precision.

3. **`same-team-as` only when GitHub owner publishes ≤5 catalogued repos.**
   When two records share `--gh-<owner>-` (e.g. `mem0ai/mem0` and
   `mem0ai/mem0-mcp`), they're almost always same-team. But organisations
   like `microsoft`, `google-research`, or `huggingface` publish many
   unrelated repos in our corpus; emitting (n choose 2) edges across all
   of them creates spurious lineage clusters. Threshold of 5 was chosen
   empirically: it keeps Mem0/OpenMemory and Zep/Graphiti families intact
   while excluding the umbrella orgs.

**Why.** Edges drive the graph view (issue #6). False edges break the
visual narrative far more than missing edges do — readers can't tell
whether a missing edge means "no relationship" or "we didn't find one",
but a wrong edge actively miscommunicates. Hence the heavy bias toward
discarding rather than guessing.

**Reversal cost.** Low. The mining script is rerun-able from the data;
edits to `PHRASE_RULES`, `CROSSREF_TYPE_MAP`, or `NAME_ALIASES` are
contained to the script and don't touch downstream consumers.

---

## 2026-05-07: fetch_citations.py — S2 cache committed under `extraction/s2-cache/`

**What.** `scripts/fetch_citations.py` writes raw Semantic Scholar
`/paper/{id}/references` responses to `extraction/s2-cache/<paperId>.json`,
one file per paper, sorted-key pretty-printed JSON. The cache directory
is **committed to git** rather than gitignored.

**Why.** Three reasons:

1. **Byte-stable re-runs.** The script's determinism gate is "running it
   twice produces an identical `web/landscape.edges.json`." Without a cache,
   live S2 responses can drift (new references added between runs, S2
   re-ranking `isInfluential`); committing the cache pins the response set
   the edge file was built from. A future re-run on a fresh checkout
   reproduces the exact 189 `cites` edges produced in the first run.
2. **Cheap.** 205 cached responses × ~25 KB each = 4.8 MB total. Small
   compared to the 1.4 MB `landscape.json` and well below GitHub's per-file
   limits. The cache will grow ~linearly with new T3+T4 papers added —
   even at 10× scale it's well under 50 MB.
3. **Polite.** S2 free tier is 100 req / 5 min and we observed live
   throttling at ~5 calls/min in practice. Re-running the script for a
   minor edit to the resolver should hit the cache entirely; only fresh
   papers should hit the network.

The cache is keyed by the exact paperId string we send to S2 (`arXiv:NNNN.NNNNN`
or the 40-char S2 hash), with `:` and `/` replaced by `_` for filesystem
safety. A 404 from S2 (e.g. an arxiv-id that's actually a date typo like
`2604.16839`) is cached as `{"data": [], "_status": "not-found"}` so the
404 isn't refetched on every run.

**Options rejected.**
- *gitignore the cache.* Cleaner repo at the cost of reproducibility — a
  fresh clone would have to make 200+ live S2 requests just to validate
  the existing edges file. Net negative for a research artifact whose
  whole point is being inspectable.
- *Commit only successful responses.* Would require re-fetching the 404s
  every run, defeating the throttle benefit.

**Reversal cost.** Low. To switch back to gitignored cache: add
`extraction/s2-cache/` to `.gitignore`, `git rm -rf` the directory, commit.
The script still works — it just rebuilds the cache from scratch on every
fresh clone.

---

## 2026-05-07: fetch_citations.py — append-only `cites` edges; cell-mined edges win on collision

**What.** `scripts/fetch_citations.py` does NOT regenerate the full
`web/landscape.edges.json` from scratch. It loads the existing edges file
(produced by `scripts/build_edges.py`), generates new `cites` edges from
S2's `isInfluential` citations, and merges via `(source, target, type)`
key — installing the existing edge first and only adding the new `cites`
edge when the key is unclaimed. The merged list is then re-sorted by
`(source, target, type)` for determinism.

**Why.** Cell-mined and cross-ref edges have richer evidence text and a
more specific `type` (e.g. `built-on`, `succeeds`, `extends`). A `cites`
edge between the same `(source, target)` pair would be redundant and would
displace the more specific edge if it sorted first. SCHEMA §4 explicitly
allows multiple edges between the same `(source, target)` pair *iff their
type differs* — so the question is only what to do when both pipelines
produce the same `(source, target, type)` triple, which only happens for
`cites` edges (build_edges.py doesn't produce any). The append-only design
also means we don't have to worry about losing the manual `cross-listings`
curated edges from build_edges.py.

The regeneration alternative — have `fetch_citations.py` rebuild edges
from scratch by re-running build_edges.py first — would couple the two
scripts and create double-runtime on every citation pull. Keeping them
independent matches the existing pattern (`extract.py` writes
`landscape.json`; `build_edges.py` writes `landscape.edges.json`) and lets
either be re-run in isolation.

**Reversal cost.** Low. If a future redesign wants a single-source-of-truth
edge builder, a thin orchestration script (`build_all_edges.py`) can call
both in sequence and replace the merge logic with a flat union.

---

## 2026-05-07: render.py — head/tail template sliced from existing landscape.html

**What.** `scripts/render.py` regenerates *only* the inside of the `<tbody>`
when producing `landscape.html`. The HEAD (everything from `<!doctype>`
through `<tbody>\n`) and TAIL (`</tbody>\n` through the closing `</html>`,
including the `<script>`, `.column-key` legend, and `.analyses` block)
are sliced verbatim from the existing `landscape.html` and concatenated
around the freshly-rendered body.

**Why.** The HEAD/TAIL contain ~330 lines of CSS, the column-key legend
(60 column descriptions), and the cross-cutting analyses block (rating
matrix + 10 finding write-ups). None of that content lives in
`landscape.json` today — it's editorial / chrome / commentary that
isn't part of the records. Three options were considered:

1. *Embed the chrome inline in render.py.* Awkward — putting 330 lines
   of CSS and a 200-line analyses block as Python string literals makes
   render.py the de-facto source of truth for content that is *not*
   structured data.
2. *Move the chrome into separate JSON sidecars.* A clean future direction
   but premature — the column-key and analyses are static prose that
   nobody is editing programmatically. JSON-ifying it would cost
   real time today for no near-term benefit.
3. *Slice from the existing HTML at render time.* What we did. The HEAD
   and TAIL act as a stable template; render.py owns only the bytes
   between them. This keeps the data/chrome split clean and means a
   designer can iterate on the CSS in `landscape.html` directly, just
   as before.

There's a circular-input twist: `--template` defaults to `landscape.html`
and `--output` also defaults to `landscape.html`, so a naive run would
read-then-overwrite the template. For issue #6 the deliverable is "render
to a temp file and diff", not "overwrite landscape.html on every run" —
the writeback workflow lights up in issue #7. Until then, callers should
pass `--output /tmp/foo.html` (or another path) when iterating, and
issue #7's validation script will pin the workflow.

**Options rejected.** See above.

**Reversal cost.** Low. Inlining the chrome would be a string-copy,
and JSON-ifying it would be a separate sidecar similar to
`extraction/section-explainers.json`.

---

## 2026-05-07: render.py — section ordering + explainer copy in `extraction/section-explainers.json`

**What.** Section group ordering (the 20 top-level sections plus their
8 + 7 sub-sections), the `style="padding-left: 28px; ..."` attribute on
sub-section group-rows, and the prose for each section's `<tr
class="section-explainer">` row are stored in
`extraction/section-explainers.json`. render.py reads that sidecar to
emit the section headers and explainers in the correct order.

The sidecar was generated by a one-shot scrape of the current
`landscape.html` (saved alongside this change). It is intended to be
hand-edited as sections are added/removed/renamed, and to round-trip
cleanly through render.py runs.

**Why.** The schema explicitly does not include section *ordering* or
*explainer prose* on records. Both are presentation-layer concerns:
records carry their primary section name, but knowing that "Dedicated
memory layers" comes before "Framework-embedded memory" requires a
declared order. And the explainer for each section is editorial,
~1-3 sentences of context, that has no natural home on any single
record.

Two options were considered:

1. *Hard-code the section list in render.py.* Brittle — adding a new
   section requires editing both render.py and landscape.json. Putting
   the ordering in a sidecar JSON keeps render.py declarative.
2. *Re-derive ordering from the existing landscape.html each run.*
   Possible but couples render.py to BeautifulSoup and bakes the
   "current HTML is canonical" assumption deeper into the pipeline.
   The sidecar is the explicit hand-off point: once it exists, the
   HTML need not be parsed again.

**Reversal cost.** Low. The sidecar is regenerable from `landscape.html`
by re-running the one-shot scraper documented in `scripts/render.py`'s
header. To migrate ordering onto the records themselves (e.g. an
explicit `displayOrder` field), edit the sidecar or replace it.

---

## 2026-05-07: render.py — within-section ordering is (tier ASC, id ASC)

**What.** Within each (section, subsection) group, render.py sorts
records by `(tier, id)` ascending. T1 systems come first; T5 last;
ties broken by id (alphabetical, stable, deterministic).

**Why.** The current `landscape.html` ships with a small inline
`<script>` at the bottom of the file that does exactly this sort
client-side after page load — see lines 38840-38873 of
`landscape.html`. The no-JS view of the file therefore differs from
the with-JS view: source-order in the file vs tier-sorted in the
browser.

Producing tier-sorted output by default has two benefits:

1. The no-JS view (which is what render.py controls) matches what
   readers actually see in the browser today, removing the "why is this
   different?" surprise.
2. It's deterministic — re-running render.py twice gives byte-identical
   output, satisfying the determinism contract from the issue spec.

The cost is that diffing the rendered output against the current
hand-edited `landscape.html` shows row-reordering noise (the source
HTML happens to be in document-add order, not tier-sorted). That
reordering accounts for most of the diff volume between the two files;
the structural skeleton, cell rendering, and section-header markup
all match. A row-aware comparison (key by `(url, name)`, compare row
bodies) confirms ~76% mean similarity per row, with the residual
gap dominated by extract.py's documented HTML-markup loss
(`<span class="signal-num">`, `<br>`, `<span class="sub">`,
`<span class="pill">`, custom `title=` attributes), not by render
issues.

**Options rejected.**

- *Preserve source-document order from the original `landscape.html`.*
  Requires render.py to read source-order from somewhere (record-level
  `documentOrder` field, or sidecar). Would minimise the diff against
  today's HTML but violate the intent that JSON is the source of truth.
- *Sort by id only.* Drops the tier signal that the existing JS sort
  already encodes; losing it would change what readers see in the
  browser today.

**Reversal cost.** Low. Change one `sorted()` key in render.py; the
JS sort at the bottom of `landscape.html` still runs and re-sorts
consistently.

---

## 2026-05-07: render.py — cross-listings render once with an inline marker

**What.** Records with more than one section membership (in
`landscape.json` they have a `sections` array of length ≥ 2 with
exactly one `primary: true` entry) are rendered once, under their
primary section. A `<span class="cross-listed" title="Also listed
under: ...">also in §Section Name</span>` marker is appended after
the name `<a>` to signal the secondary placement.

The four currently-cross-listed records (`mem0`, `zep-graphiti`,
`memobase`, `memorybench-tsinghua-thuir`) all render under their
primary section with the marker.

**Why.** The schema's section model (per-record `sections` array
with one primary) is asymmetric: a record exists once, but appears
in multiple section lenses. Rendering it twice (once per section)
violates the "523 records → 523 rows" invariant. Rendering it only
once under a single section without a marker drops information that
a careful reader should be able to surface from the page itself.
Hence: render once, but flag the secondary placement.

**Options rejected.**

- *Render twice, once per section.* Mirrors the source HTML for the
  four cross-listed records (which appear twice in the existing
  `landscape.html` — that's why `extract.py` followed by
  `reconcile.py` was needed to merge them). Re-introduces the
  same duplication problem the merge was meant to solve.
- *Render once with no marker.* Loses the cross-listing signal in
  the no-JS view. Future readers would have to look at the JSON to
  know it.
- *Use a footnote / sidebar.* Heavyweight for a single span. The
  inline marker is concise and uses the existing CSS variables for
  styling.

The class `cross-listed` is unstyled today; the no-JS view shows the
marker as plain prose. The class is queryable for future styling
(table app row decoration, CSS dimming for cross-listed rows, etc.).

**Reversal cost.** Low. The marker is one helper function in
render.py (`render_cross_listing_marker`); rendering twice is a
second loop body in `render_body`.

---

## 2026-05-07: render.py — escape `<`, `>`, `&` in cell `value` strings

**What.** When rendering each cell's `value` into HTML, render.py
escapes `<`, `>`, and `&` to their HTML entities. Quote characters are
left alone (we never embed `value` into an attribute, so no quote
escaping is needed).

**Why.** The issue spec describes a *future* state where `value` may
contain HTML markup (signal-num spans, `<br>`, `<span class="sub">`,
the `<span class="pill"><a>...</a></span>` constructs in the
`links` cell) and asks render.py to pass that markup through verbatim.
In today's actual `landscape.json`, extract.py uses BeautifulSoup's
`get_text()` which strips all markup and decodes entities — so the
JSON contains plain-text cells with literal `<` and `&` characters
in 310 + 53 records (e.g. `<10min (hosted SaaS sign-up)`,
`Ashpreet Bedi (founder & CEO)`). Passing those through verbatim
produces invalid HTML — `<10min` looks like an unclosed tag.

The escape-always policy fixes the today problem and only loses the
aspirational "verbatim markup" capability. To recover that capability
in the future, the schema would add a `valueHtml` field on the cell
(or a producer-side flag), letting render.py keep `value` as plain
text and `valueHtml` as the markup. That migration is bounded — it
touches the schema, extract.py (preserve markup), and render.py
(prefer `valueHtml`); no consumer downstream depends on the current
loss.

**Options rejected.**

- *Pass-through verbatim per the spec.* Produces invalid HTML for ~310
  records today (literal `<` for `<10min` etc.). Hard to ship.
- *Heuristic escape (only escape `<` not followed by a tag-name
  character).* Fragile — distinguishing `<10min` from `<a>` from
  `<br>` from `<span class="signal-num">` requires real parsing, and
  a parser that's wrong loses either way.

**Reversal cost.** Low. One helper function (`_value_passthrough`).
Once the schema migrates to `valueHtml`, this function reads from
the markup-bearing field and stops escaping.

---

## 2026-05-07: Issue #7 — Path B (defer JSON-as-source until extract.py loses less markup)

**What.** The structured mirror (`web/landscape.json` + `web/landscape.edges.json`)
ships now, with a CI-enforced four-gate validator (`scripts/validate.py`),
but **`landscape.html` remains the hand-maintained source of authority for
the catalog itself**. We do *not* regenerate `landscape.html` from the JSON
on every commit. Phase 2's table app and Phase 3+'s analyses consume the
JSON mirror; the HTML stays as the no-JS reference view.

The cycle-stability gate validates `render.py(json) → extract.py(html) →
render.py(json) ≤ 16-line drift` (the four cross-listing markers we
intentionally inject). It does **not** compare render.py's output to
the current `landscape.html`.

**Why.** Two paths were on the table when issue #7 landed:

- **Path A.** Activate "JSON is the source, HTML is a build artefact"
  immediately. Run `render.py` on every commit and check the result in.
- **Path B.** Keep the hand-maintained HTML as authoritative for now.
  Use `make build` to refresh the JSON mirror after HTML edits. Activate
  Path A later, after `extract.py` is upgraded.

`render.py`'s first-pass output diffs from the current `landscape.html`
by ~50k lines. Most of that diff is two things:

1. **Row ordering.** `landscape.html` rows are in document-add order;
   `render.py` emits them tier-sorted to match the post-JS view (the
   inline `<script>` at the bottom of `landscape.html` re-sorts client-side).
   Documented in `docs/DECISIONS.md` "render.py — within-section ordering
   is (tier ASC, id ASC)".
2. **Markup richness.** `extract.py` uses BeautifulSoup `get_text()` which
   collapses `<span class="signal-num">`, `<br>`, `<span class="sub">`,
   custom `title=` attributes, and the pill-anchor constructs in
   `td.links` to plain text. `render.py` therefore can't reproduce them
   even with a perfect template. Documented in `docs/DECISIONS.md`
   "render.py — escape `<`, `>`, `&` in cell `value` strings".

Activating Path A now would mean replacing the user's six-rounds-of-research
HTML with a structurally-correct but markup-poorer version — net negative
on the human-facing artifact even though the data is preserved.

**Options rejected.**

- *Path A — regenerate `landscape.html` and commit it as canonical.*
  Loses the markup richness above; downgrades the user-visible view to
  pay forward a future maintainability win. Postpone until extract.py
  is upgraded to preserve the spans / `<br>` / pill structure.
- *Compare render.py output directly against current `landscape.html`
  and fail if they differ.* Would block every commit until Path A is
  paid for; defeats the point of shipping the validator now.
- *Skip the round-trip gate entirely.* Loses the most useful guarantee
  — that the JSON mirror is structurally sound enough to be the
  authority once extract.py is upgraded.

**Reversal cost.** Low to activate Path A later. The flip is:
(a) upgrade `extract.py` to preserve markup into a `valueHtml` field;
(b) update `render.py` to prefer `valueHtml` over `value`;
(c) regenerate `landscape.html` once and commit; (d) tighten the
cycle-stability gate to compare render output against `landscape.html`.
None of those touch the schema or downstream consumers.

---

## 2026-05-07: Issue #8 — SvelteKit bootstrap, TypeScript, build-time JSON import, server load

**What.** The Phase 2 SvelteKit project at `web/` uses TypeScript (not plain
JS), imports `landscape.json` and `landscape.edges.json` at build time via
relative-path JSON imports (not runtime `fetch`), and uses a server-only
`+page.server.ts` load function so the landing page's *client* bundle does
not contain the 4.3 MB compiled JSON. The `web/` directory layout follows
the suggested structure exactly: `landscape.json` and `landscape.edges.json`
stay at the root of `web/`; SvelteKit source lives under `web/src/`.

**Why — TypeScript.** The schema in `docs/SCHEMA.md` is non-trivial (60 cell
column slugs, 9 edge types, 4 status values, 3 levels of nested arrays in
the taxonomy / sections / cells shape). Surfacing those as TypeScript types
in `src/lib/types.ts` is a load-bearing artefact for issues #9-#12 — every
downstream agent gets compile-time-checked access to the schema instead of
hand-rolling object-shape assumptions. Plain JS would defer that cost to
runtime.

**Why — build-time JSON import over `fetch`.** Three reasons. (1) The data
is content-addressed: the same JSON ships to all clients, so there's no
reason to pay an extra network round-trip on every page load. (2) The
build pipeline (Vite) tree-shakes unused properties from JSON imports
into `+page.server.ts`, so the landing page's client bundle ends up at
~75 KB instead of 4.3 MB. (3) Vite's import path is statically analysable
— if `landscape.json` is missing or malformed at build time the build
fails loudly, instead of a 404 at runtime in production.

**Why — `+page.server.ts` not `+page.ts`.** A universal `+page.ts` runs
the loader on both server (prerender) and client (hydration), pulling
the full JSON import into the client bundle even when only counts are
referenced. Switching to `+page.server.ts` restricts the import to the
prerender step; the resulting `index.html` contains the prerendered
counts, and the `__data.json` sidecar contains only `{recordCount: 523,
edgeCount: 247}`. Issue #9 (table view) will need the full records[]
array on the client and will use a universal loader there.

**Why — `web/build/` staging dir + `sync-to-docs.mjs` postbuild.** The
project's `docs/` directory predates the GitHub Pages build target — it's
where `BUILD-PLAN.md`, `DECISIONS.md`, and `SCHEMA.md` live. SvelteKit's
adapter-static wipes its output directory before writing, which would
delete the markdown on every build. Two alternatives: (a) move the
markdown elsewhere (breaks every `docs/*.md` reference in the repo), or
(b) build into a staging dir and copy into `docs/` without clobbering
markdown. We took (b). The staging dir is `web/build/` (gitignored); the
postbuild script `web/scripts/sync-to-docs.mjs` removes only the known
build artefact paths (`_app/`, `index.html`, `__data.json`) from `docs/`
before copying. This is the deviation from the issue spec's "build
output to `docs/`" — semantically identical end state, just plumbed via
a staging copy.

**Layout deviation from the suggested structure.** None substantive.
`vite.config.ts` instead of `vite.config.js` because we use TypeScript;
`+layout.ts` (not `.svelte`-only) because we needed somewhere to set
`prerender = true`, `ssr = true`, `csr = true`; `static/.nojekyll`
added so Pages doesn't ignore the `_app/` directory once issue #20
turns on the deploy.

**Reversal cost.** Low. TypeScript → JS is mechanical (rename `.ts` to
`.js`, drop type annotations). Build-time → fetch is a single-file
edit in `src/lib/data.ts`. Move docs/ markdown elsewhere is a one-time
mechanical move. The staging-dir trick is one ~50-line script —
deletable the moment GH Pages can serve from a non-root path.

---

## 2026-05-07: Issue #9 — sentinel-based virtualisation, fixed-height rows

**What.** The table view (`web/src/lib/components/Table.svelte`) renders 523
records via a hand-rolled virtualisation: track `scrollTop` on the scroll
container, compute `firstVisible = floor(scrollTop / ROW_HEIGHT) - OVERSCAN`
and `lastVisible = ceil((scrollTop + viewportHeight) / ROW_HEIGHT) + OVERSCAN`,
slice `records[firstVisible:lastVisible]`, and translate the `<tbody>` by
`firstVisible * ROW_HEIGHT` pixels. A spacer `<div>` inside the scroll
container provides the full `records.length * ROW_HEIGHT` virtual height so
the scrollbar is correctly sized. `ROW_HEIGHT = 56`, `OVERSCAN = 8`.

**Why.** Three options were on the table:

1. *Render all 523 rows.* Easy; works at 67 columns × 523 rows = 35 k cells
   on a fast laptop. Stutters on mid-tier hardware (per the Phase 2 perf
   gate of 60 fps scrolling) once the cells include `{@html}` formatting.
2. *Take a `svelte-virtual-list` dep.* Adds a runtime dep, locks us into
   that lib's row-rendering API for issues #10-#12.
3. *Sentinel-based virtualisation.* What we did. Plain Svelte, ~30 lines of
   logic, fixed-height rows so the math is trivial. Renders ~23 rows at a
   time (visible window + 16 overscan) regardless of dataset size.

The fixed-height assumption is the trade. Cells with very long `desc` /
`claims` text get truncated visually via `overflow: hidden` on the row.
The full text is still in the DOM and accessible via title / hover (issue
#13 will add a detail modal). Going variable-height would mean either
two-pass measurement (slow) or `IntersectionObserver`-driven re-layout
(complex), neither worth it for a table where the user's primary task is
column-comparison sort, not deep prose reading.

**Reversal cost.** Low. The virtualisation is contained to `Table.svelte`;
swapping in `svelte-virtual-list` or going render-all is a 50-line change
with no consumer impact.

---

## 2026-05-07: Issue #9 — `{@html cell.value}` is a deliberate trust boundary

**What.** `TableCell.svelte` renders `real-data` cell values using
`{@html cell.value}` — the markup is passed through verbatim, not escaped.
We rely on the data pipeline (`extract.py` → `landscape.json`) to produce
trusted markup only.

**Why.** The schema (SCHEMA.md §3) describes cells as potentially
containing HTML — `<span class="signal-num">`, `<br>`, `<span class="sub">`,
`<span class="pill">` constructs in the `links` cell. Rendering those
verbatim is what makes the rich landscape.html visual style reproducible
in the SvelteKit app. Escaping would turn them into literal text.

The trust chain:

1. The producer is `extract.py`, run on a hand-curated `landscape.html`
   that we (and only we) edit.
2. The intermediate is `landscape.json`, regenerable byte-stably from
   the HTML and validated by `scripts/validate.py` on every commit.
3. The consumer is the SvelteKit build, which imports the JSON at build
   time and ships it as a static asset.

There is no path for untrusted user input to reach a cell value. If that
ever changes (e.g. a future "submit a system" form), the cell value path
must be re-evaluated — either re-escape, or split into `value` (text) and
`valueHtml` (markup) per the long-deferred SCHEMA upgrade in
"render.py — escape `<`, `>`, `&` in cell `value` strings" above.

In today's `landscape.json` produced by `extract.py`, the cells are
plain text (BeautifulSoup `get_text()` strips markup), so the
`{@html}` is mostly defensive — the moment extract.py is upgraded to
preserve markup, the table view will benefit without code changes.

**Reversal cost.** Low. `{@html cell.value}` → `{cell.value}` is a
one-line change in `TableCell.svelte`. Doing so loses the markup-richness
benefit but keeps everything else intact.

---

## 2026-05-07: Issue #9 — column-band colour scheme: 13 groups at L≈22 % S≈18 %

**What.** Column-group bands in the table header use a 13-colour palette
chosen from a single base (HSL `(_, 18%, 22%)`) by varying hue around the
wheel. All bands sit on the same dark base; only hue differentiates them.
Adjacent groups in the table differ by ≤ 8 % saturation. Group identifiers:
identity / taxonomy / substance / activity / adoption / commercial /
operational / semantics / standards / section-deep / architecture /
research / judgement.

**Why.** The issue spec asked for "max ~8 % saturation difference between
groups so the eye can find groups without being overwhelmed". Empirically
the best way to hit that is to fix L and S and let H do the work. A
candidate palette using one pastel per group (varying L and S) was tried
first and washed out the table — too many colours competing for attention.

The 13 groups roughly mirror the conceptual buckets in
`landscape.html`'s column-key legend (Identity, Substance, Activity,
Adoption, Commercial, Operational, Memory semantics, Standards,
Section-deep, Architecture, Research, Judgement) plus an explicit
"taxonomy" band for the seven axis columns that the legend treated as
their own block.

**Reversal cost.** Low. Group→colour mapping lives in `GROUP_META` in
`web/src/lib/columns.ts`; one-file change to retune.

---

## 2026-05-07: Issue #9 — sort/search/filter stores split into three files

**What.** Three separate stores under `web/src/lib/stores/`:

- `sort.ts`: `sortColumns: Writable<SortEntry[]>` + `cycleSort()` helper.
  Click rules implemented and tested in `Table.svelte`.
- `search.ts`: `searchQuery: Writable<string>` + `applySearch()` no-op.
  #10 fills in the matcher.
- `filters.ts`: `filters: Writable<FilterState>` + `applyFilters()` no-op.
  Type kept deliberately empty (`{}`); #11 fills in facet shape.

The `+page.svelte` reactive expression composes them:

```ts
const visibleRecords = $derived(
  sortRecords(applyFilters(applySearch(records, $searchQuery), $filters), $sortColumns)
);
```

**Why.** Three downstream issues want to fill in different parts. Splitting
the stores means #10 touches one file, #11 touches another, #12 just reads
all three. If they shared a state object, #10 and #11 would have merge
conflicts; this way the integration points are file-level isolated.

The contract for each store is documented in its file header — what
`applySearch` should do, what shape `FilterState` should grow into, where
URL state plumbing should hook in (#12).

**Reversal cost.** Low. Combining the three files into one is a 20-line
mechanical edit; splitting was the cheaper bet for parallel implementation.

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

## 2026-05-07: Search-as-you-type (issue #10)

**What.** `applySearch(records, query)` does a case-insensitive substring
match across `record.name`, `record.cells.desc.value`, and
`record.cells.claims.value`. HTML tags are stripped from desc/claims
(regex `/<[^>]+>/g`) before matching. A `SearchBox.svelte` renders a
`<input type="search">` bound to `$searchQuery`, with a live "X of 523
match" status, an empty-state "Clear search" link, `/` to focus, and Esc
to clear. The reactive pipeline in `+page.svelte` already composed
search → filters → sort, so wiring was a single import + render.

**Why.**
- *Substring over fuzzy.* 523 records is small enough that a linear
  substring scan runs in well under a frame; fuzzy matching would add
  surprise hits and a ranking question we don't need yet.
- *Three fields, not all 60 cells.* Name, desc, and claims are the
  human-readable summary fields. Searching every cell would surface
  matches on schema scaffolding (e.g. "not-applicable", URLs in
  citations) that aren't useful to the user. Future taxonomies belong in
  the filter rail (#11), not the free-text box.
- *HTML strip.* `desc` and `claims` ship rendered HTML; without stripping,
  typing "href" would match every cell with a link.
- *Debounced store exported but unused by the table.* The matcher is
  cheap enough to run on every keystroke (`$searchQuery` direct), but
  `debouncedQuery` is exported for #12 (URL sync) and any future
  server-side index — debouncing the URL writes avoids spamming history.
- *Match-count prop, not a derived store inside SearchBox.* Keeps the
  component dumb; the page owns the pipeline and already knows
  `visibleRecords.length`.

**Deferred.** In-cell match highlighting. It requires either a second
render path for cells or a wrapper component, and #12 (URL state) and
#13 are higher leverage. Re-open when users ask for it.

**Reversal cost.** Low. `applySearch` is a pure function; swapping it
for a fuzzy matcher or a prebuilt index is a one-file change.
SearchBox is self-contained — deleting the import + render line in
`+page.svelte` removes the feature with no other fallout.

