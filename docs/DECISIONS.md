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

---

## 2026-05-07: Faceted filters — shape, semantics, canonicalisation (issue #11)

**What.** The faceted-filter rail (`FilterRail.svelte` + `filters.ts`)
exposes twelve facets. `FilterState` is a flat object whose every
property is a `Set` of allowed values for that facet; an empty Set means
"no constraint on this facet". Predicate semantics: **AND across facets,
OR within a facet** — the standard faceted-search shape. Each record
contributes exactly one value per facet, so a record is either in or out
of each value's bucket.

The twelve facets and their value-extraction rules:

| Facet | Source on record | Value space |
| --- | --- | --- |
| `tier` | `r.tier` | numbers 1..5 |
| `section` | primary `r.sections[].section` | free-form strings |
| `storage`..`conflict` | primary value of `r.taxonomy[axis]` | taxonomy terms |
| `license` | canonicalised `r.cells.license` | bucketed (see below) |
| `deployment` | canonicalised `r.cells.deployment` | bucketed |
| `modality` | canonicalised `r.cells.modalities` | bucketed |

For the three cell-derived facets, the raw cell value is free text, so
we keyword-match (substring, lowercased) into a small fixed bucket set.
Anything that doesn't match any keyword becomes `other`; anything whose
cell status is not `real-data` becomes `NA` (so users can filter to "only
records with real licence data").

**License buckets.** apache → `Apache-2.0`; agpl → `AGPL`; gpl → `GPL`;
mit → `MIT`; bsd → `BSD`; proprietary/closed → `proprietary`;
research/noncommercial/nc-4.0/cc-by-nc → `research-license`; everything
else → `other`. `agpl` is checked before `gpl` so AGPL isn't swallowed
by GPL's substring.

**Deployment buckets.** self-host/on-prem → `self-hosted`;
saas/managed/hosted → `saas`; cloud → `cloud`;
library/embedded/sdk → `library`; cli/desktop/local → `local`;
else → `other`.

**Modality buckets.** multimodal → `multimodal`; text → `text`;
vision/image → `vision`; audio/speech → `audio`; video → `video`;
code → `code`; embedding/vector → `embeddings`; else → `other`. First
match wins; a record whose cell mentions both "text" and "vision" lands
under `multimodal` if it says so, else `text` (text is checked before
vision). This is the right call for faceting (one bucket per record)
but loses information; if multi-modality ever becomes a first-class
facet axis we should switch to a multi-valued shape rather than
expanding the bucket list.

**Why a Set per facet rather than a per-axis FilterAxis object.**
Considered:
- *Nested taxonomy sub-object* (`{ taxonomy: { storage: Set, ... } }`)
  to mirror the LandscapeRecord shape. Rejected — flat is one less hop
  in the URL serialiser (#12) and the rail doesn't visually group them
  any more tightly than the rest.
- *Single `Set<{facet,value}>` discriminated-union.* Rejected — facet
  membership tests become O(n) on the set size rather than O(1).
- *Arrays instead of Sets.* Rejected — Sets give us O(1) `.has()` for
  the per-record predicate, which runs once per facet per record on
  every filter toggle.

**Why counts exclude the current facet.** Standard faceted-UX behaviour:
if you've already selected "tier=1" and look at the section facet, you
see the count *given tier=1*, but inside the tier facet itself you see
the count of records-that-match-every-other-facet broken down by tier —
otherwise once you pick "tier=1" the other tiers show 0 and the user
can't expand their selection. Implemented in `facetCounts()` by
filtering with `FACET_ORDER.filter(f => f !== facet)` before tallying.

**Why `<details>` instead of a custom collapsible.** Built-in
accessibility, keyboard support, and the rotate-on-open arrow comes for
free via CSS. Trade-off: harder to animate, but we don't animate anyway.

**Contract for #12 (URL sync).** Read/write through the exported
helpers: `filters` writable, `toggleFacetValue(facet, value)`,
`clearFacet(facet)`, `clearFilters()`. Serialisation can iterate
`FACET_ORDER` and join each Set as `?tier=1,2&section=...`. The
canonicalisation functions are also exported so URL params can be
validated against the same bucket set the UI shows.

**Deferred.**
- *Hierarchical section/subsection.* The data has subsections under
  some sections; the filter rail treats every primary section as a
  flat string. A future issue can split this into a tree picker if
  the section list gets unwieldy.
- *Narrow-viewport drawer.* Below ~900px the rail will wrap below the
  table area awkwardly; the responsive layout is left for a later pass.
- *Multi-valued modality matching.* A record with "text+vision" is
  bucketed into one value only. If users complain, switch modality to
  a multi-bucket per record (record passes the facet if any of its
  buckets match).

**Reversal cost.** Low. The store API (`filters`, `applyFilters`,
`facetCounts`, `toggleFacetValue`, `clearFacet`, `clearFilters`) is the
only public surface; the rail and any future URL-sync consumer go
through it. Adding facets is one line in `FACET_ORDER` plus an extractor
case in `recordFacetValue`. Canonicalisation buckets can be widened by
adding keyword tests without changing the API.

---

## 2026-05-07: URL state encoding (issue #12)

**What.** Three stores (`searchQuery`, `filters`, `sortColumns`) round-trip
through `window.location.search` via a pure codec in
`web/src/lib/url-state.ts`. Encoding format:

- `q=<search>` — only if non-empty
- one param per non-empty facet Set: `tier=1,2&license=Apache-2.0,MIT`
- `sort=col1:asc,col2:desc` — only if non-empty

Empty values are omitted so the default view is `/` (not `/?q=&tier=&...`).
Values within a facet are sorted (numeric for tier, alpha otherwise) for
deterministic URLs.

**URL read happens client-side in `+page.svelte`**, not in a `+page.ts`
load function. Reason: the site uses `adapter-static` with `prerender =
true`, so `+page.ts` runs at build time where `url.searchParams` is empty.
Parsing `window.location.search` synchronously in the component script
(guarded by `browser`) runs before any `$derived` resolves, which is
what eliminates the flash-of-default-view on paste-into-new-tab.

**Stores → URL** uses `goto(?<qs>, { replaceState, noScroll, keepFocus })`
debounced 150 ms. Chosen over `history.replaceState` directly because:

- keeps SvelteKit's `$page` store in sync (future consumers reading
  `$page.url.searchParams` see the right value)
- routes through the framework's transition machinery
- `replaceState: true` keeps the back button useful — without it, every
  keystroke would push a history entry

A `$effect` snapshots last-written state (cloning Sets so in-place
`filters.update()` mutations are detected) and skips redundant writes.
`popstate` listener re-parses the URL into the stores so browser back /
forward navigates between filter states correctly.

**Validation / forward-compat.** Unknown query params are ignored (the
codec only reads keys in `FACET_NAME_SET`, plus `q` and `sort`). Tier
values that aren't integers 1-5 are dropped. Sort directions outside
`{asc, desc}` are dropped. The codec does *not* validate facet values
against the current canonical bucket list — a URL referencing a value
that no longer exists will silently match no records, which is the
right behaviour (URLs stay readable, no crashes).

**Skipped.**
- *Multi-tab sync via BroadcastChannel.* Overkill for now; one user, one
  tab is the dominant use-case.
- *URL compression (base64 / lz-string).* Max-fill URL is well under
  2 KB (12 facets × ~6 values × ~12 chars ≈ 900 bytes including param
  names). Compression sacrifices readability for no real gain.
- *Validate sort columns against `ColumnSlug` enum.* The comparator
  already handles unknown columns gracefully; coupling the codec to the
  column schema would force a change here on every column addition.

**Reversal cost.** Low. The codec is two pure functions plus two equality
helpers; the wiring in `+page.svelte` is ~40 lines. Swapping the encoding
format means changing `stateToUrl` / `urlToState` in lockstep; nothing
else in the app touches the URL. Adding new state to the URL (e.g. column
visibility from a future issue) is a one-place edit in url-state.ts.


---

## 2026-05-07: Timeline view — stacking by tier (issue #13)

**What.** The `/timeline` view stacks year-quarter bars by **tier** (5
stacks) rather than by **section** (20 stacks). Section is exposed as a
filter dropdown instead.

**Why.**
- *Stack count vs. legibility.* Twenty-stack bars at 28px wide turn into
  visual noise — each tier-segment in a tall bar would be 1–2px, and the
  legend would dominate the page.
- *Tier carries the most information about "wave shape".* The user's
  primary trend-analysis question ("when did each layer of the landscape
  light up?") maps onto tier directly: tier-1 systems lead, tier-3
  follow-ons cluster a few quarters later, tier-4 papers form their own
  research wave. Section is *what kind of thing* it is, which is better
  answered by the filter dropdown ("show me just dedicated memory
  layers").
- *Click drill-through.* A bar click sends the user to the table filtered
  by `section=<current> & tier=<tiers in bucket>`. Stacking by tier
  makes that param obvious to construct; stacking by section would
  require encoding "which sections are non-zero in this quarter" — less
  intuitive.

**Date parsing heuristics** (`lib/timeline.ts → parseCreatedDate`):
1. `YYYY-MM-DD` or `YYYY-MM` anywhere in the string → exact quarter.
2. `YYYY-YYYY` range → earlier year, Q1.
3. Bare `YYYY` (1900–2099) → that year, Q1.
4. Sentinel phrasings (`no data`, `searched not found`, `Pre-existing`,
   `Various`) return null up front.
5. Prose like `"Announced 2026-04 (GTC season)"` is handled because the
   regex is *not* anchored — first plausible `YYYY-MM` wins. We assume
   the founding/release date appears first in the string; later dates
   are usually GA/acquisition/etc. and less interesting for "when was
   this created".

**Result on the current dataset.** 501 of 523 records (96%) parse to a
year-quarter; 22 are unparseable (status `depth-floor-reached` or
literal `"no data"`). Records without a parseable date are silently
omitted from the chart and counted in the subtitle as "N unparseable".

**Empty-quarter handling.** `bucketRecords()` inserts empty rows between
the min and max year so the X-axis is continuous. A "dry quarter" with
no releases conveys real information (the pause before a wave); collapsing
it would mislead the eye about pacing.

**Rendering choice — pure SVG, no library.** ~25 quarters × 5 tiers ≈
125 `<rect>` elements. A charting library (chart.js, d3, layercake)
would add a 30–80 KB dependency and force us to fight its tooltip /
click-target / colour systems. Hand-rolled SVG is ~250 lines including
the tooltip, gives pixel-perfect control over click hit-zones (we use a
full-column transparent hit-rect so short bars are still clickable), and
keeps the bundle small.

**Drill-through fidelity.** Bar click goes to
`/?section=<>&tier=<csv>`. There is no "year" facet on the table today,
so the drill is an over-approximation — it shows the section+tier
intersection across *all* time, not just the clicked quarter. This is the
best fidelity available without inventing a new facet, and it's still a
useful zoom-in. A future issue could add a `?created-year=` param if the
imprecision proves annoying.

**Reusable for Phase 4 (graph view).** The `parseCreatedDate` and
`primarySection` helpers in `lib/timeline.ts` are deliberately
Svelte-free pure functions. Phase 4 will reuse them to colour graph
nodes by creation era (era bands on a force layout = "when did this
cluster light up?") and to size them by section membership.

**Skipped.**
- *Y-axis log scale.* Counts top out around 30 per bucket; linear is fine.
- *Animated transitions on filter change.* Section filter swaps the
  whole bucket set; cross-fade looked worse than instant replace.
- *Saving the section filter to the URL.* The table view already owns
  the section facet; the timeline filter is a transient view setting
  rather than a shareable state. Reverse if user feedback asks for
  shareable timeline-with-filter links.

**Reversal cost.** Low. The bucketing and parsing logic are pure
functions in `lib/timeline.ts`; the view is a single Svelte file. To
re-stack by section, swap `byTier[t-1]` for a `bySection[name]` map and
update the legend. To swap to a library, replace the SVG block; the
parsing helpers stay.

---

## 2026-05-07: Leaderboards page — number extraction & curated boards

**What.** Built `/leaderboards` (issue #14) with five curated top-N
boards plus a "build your own" panel. All ranking math lives in
`web/src/lib/leaderboards.ts` as pure functions; the page is a thin
Svelte 5 view.

**The five curated boards.**
1. *Most-cited research (T3 / T4).* `record.cells.citations.value`,
   tier-filtered first so we don't waste cycles parsing the
   "not applicable" sentinels that fill commercial-product citation
   cells.
2. *Most-starred OSS.* `record.cells.gh.value` — leading star count.
3. *Best-funded commercial.* `record.cells.funding.value` — leading
   dollar figure (total-raised by corpus convention; valuation trails).
4. *Highest inbound citations within catalog.* Counts `cites` edges
   in `landscape.edges.json` whose `target` is the record. Pure graph
   metric, independent of Semantic Scholar.
5. *Highest inbound integrations.* `integrates-with` + `built-on`
   inbound edges. Mem0 tops this at 12, matching the issue spec.

**Number extraction heuristics** (`extractNumber()` in
`lib/leaderboards.ts`):
- The **first** number token wins; corpus convention is that rate-tails
  ("· 5/mo") and breakdowns ("/ 1.4k forks") always trail the headline.
- Dollar form (`$2.5B`, `~$20M total`) is tried first because the `$`
  sigil is unambiguous; regex tolerates leading `~`, internal commas,
  and trailing `+` (e.g. `$57B+ raised`).
- Suffix multipliers `k`/`M`/`B`/`T` are case-insensitive.
- "No-data" sentinels detected by lowercase-prefix match
  (`undisclosed`, `bootstrapped`, `n/a`, `not applicable`,
  `searched not found`, `not yet`) return null — they'd otherwise
  parse to misleading zeros or stray years.
- The string `"0 (too recent — ...)"` for fresh preprints is matched
  by `^0\s*\(` and treated as null, not literal zero — otherwise these
  papers would rank as "least cited" rather than "no data".
- Ranges (`$2–5M`), composite multi-headlines, and currency conversion
  are not handled. The leading figure is correct for ~95% of cells in
  the corpus; everything unparseable drops to the bottom of the board,
  which is where users expect data-poor entries.

**Custom mode columns.** citations, gh, funding, mindshare, and
integration-count (free-text cell). Tier and section filters AND
together. N defaults to 10, clamps to [1, 100].

**Drill-down.** Name links jump to `/?q=<encoded name>` — the table
view's existing URL codec (`q=`, see `lib/url-state.ts`) drops the
user straight into a name-filtered table. No per-record deep link
exists yet.

**Why a separate `lib/leaderboards.ts`.** Phase 4 (graph) will reuse
`inboundEdgeCounts()` for centrality measures; Phase 5 (export /
share-cards) will reuse `topBy()` + `extractNumber()` for static
"top 10" image cards. Keeping these as pure functions over
`LandscapeRecord[]` / `Edge[]` means neither downstream pulls in Svelte.

**Options rejected.**
- *Server-side computed ranking.* The site is fully prerendered; records
  are already in the bundle. Server-side ranking just snapshots at build
  time and complicates filter-aware custom mode.
- *Filter-aware curated boards (read from `$filters`).* Out of scope —
  curated boards are meant to be the canonical answer. Custom mode is
  where filter interaction lives.
- *Unit-aware NLP parser.* Overkill. The heuristic regex catches every
  cell in the sample test (~600 cells per column).

**Reversal cost.** Low. The page is two files plus one library; nothing
else imports them. Re-tuning extraction is a single-function edit.
Adding a curated board is ~15 lines in the page.

---

## 2026-05-07: Section-stats page (issue #15)

**What.** Shipped `/sections` with a compare panel + responsive grid of
all 20 section cards. Aggregation lives in `web/src/lib/section-stats.ts`
as pure functions over `LandscapeRecord[]`; the view is a single Svelte
file (`web/src/routes/sections/+page.svelte`).

**Per-section card content.**
- Row count
- Tier sparkline (5 bars, T1..T5) — heights scaled to the **global**
  max-tier-count across all sections, so a 1-row section's tier bar
  isn't visually as tall as a 50-row section's.
- 4 numeric medians: citations, GH stars, funding, mindshare
- 7 taxonomy axis distributions (storage, retrieval, persistence,
  update, unit, governance, conflict) — horizontal mini bars, top-3
  + "+ N other" rollup so the long tail is acknowledged without
  blowing out card height
- License + deployment distributions, top-3 each, using the existing
  `canonicaliseLicense` / `canonicaliseDeployment` helpers from
  `stores/filters.ts`

**Compare mode.** Two `<select>`s above the grid, default to the two
largest sections. Side-by-side cards show the same data plus signed
deltas on the four median metrics (green up, red down). Deltas are
sectionB − sectionA on card A and the inverse on card B, so each card's
delta reads as "vs. the other one".

**Number extraction.** Local `parseNumber(cell)` in `section-stats.ts`.
First-number-wins with optional `$`/`€`/`£` prefix, `k`/`m`/`b`/`t`
suffix, comma stripping; null on `status !== 'real-data'`. Differs from
issue #14's `extractNumber` in that we don't special-case the
`"0 (too recent — ...)"` sentinel — for medians, the few stray zeros
are absorbed; for top-N rankings, they'd pollute the top. The two
helpers should converge into `lib/numeric.ts` in a follow-up PR.

**Filter-store integration.** The page reads the global `filters` store
and re-aggregates inside a `$derived`. Toggling filters on the table
view and navigating to /sections shows scoped aggregates. A "filtered"
tag in the header signals the scope. No rail is rendered on this page
(the rail lives in the table view).

**Why one Svelte file rather than sub-components.** The card is rendered
twice in the compare panel and once per section in the grid — but the
DOM shape diverges (compare adds the delta column and the
license/deployment block) and the component would need a slot soup of
"is this the compare variant?" props. Inlining is clearer at this
size. The Phase-4 graph will not consume the rendered card — it'll pull
from the pure helpers in `section-stats.ts` (`aggregateAllSections`,
`topNWithOther`, `formatCompact`) for tooltips and cluster overlays.

**Tier-bar global scaling — why.** Per-card scaling makes T-mix shape
read incorrectly: an 8-row section concentrated entirely in T1 has a
full-height T1 bar that *looks* identical to the full-height T1 bar of
a 50-row T1-concentrated section. Global scaling preserves the "how
much of the catalog is this section" signal alongside the "what's its
internal tier mix" signal.

**Top-3 + other rollup.** Some axes (storage especially) have 12+
distinct values across the catalog. The cards collapse to top-3 with
"+ N other (count)" for the tail. The user can drill via the table
view's facet rail for the full distribution; the card surfaces the
shape, not the long tail.

**Reused by Phase 4 (graph).**
- `parseNumber` → node tooltips, "size by funding" overlay
- `aggregateAllSections` → cluster summaries on hover
- `topNWithOther` → side-panel histograms when a cluster is selected
- `formatCompact` → universal number formatter for graph labels

**Options rejected.**
- *Mean instead of median.* Funding & citations are heavy-tailed; one
  outlier dominates. Median is the right default.
- *D3 / chart library.* SVG-less divs with percentage widths render
  in ~25 lines of CSS; a library would add ≥ 30 KB for nothing.
- *Per-card tier scale.* Misleading (see above).
- *Separate `/sections/compare` route.* Forces a click-and-load when
  the same page can host both. Compare panel sits on top, grid below.
- *Section ordering by name alphabetical.* Sorted by `rowCount` desc
  so the most populous catalog areas anchor the top of the grid.

**Reversal cost.** Low. The view is one file; the helpers are pure
and ~200 lines. Layout tweaks are CSS-only. Adding a new aggregated
metric is two lines (one in `SectionAggregate`, one in
`aggregateSection`) plus a row in the card markup.

---

## 2026-05-07: Lineage detection heuristics (/lineages, issue #17)

**What.** Detect "history of X" lineage families from records + edges
and render them as a Wikipedia-style timeline diagram. Two curated
seeds (RSSM / world-model anchored on DreamerV3, Graph-RAG hierarchy
anchored on GraphRAG-Microsoft) come from `analysis.md`; everything
else is auto-discovered as connected components in a descent
sub-graph. Pure detection logic in `web/src/lib/lineages.ts`; SVG
view in `web/src/routes/lineages/+page.svelte`.

**Edge-type weighting.**

| Edge type | Treatment | Why |
|-----------|-----------|-----|
| `built-on` / `extends` / `forks` / `succeeds` | Strong descent — always counts | These are explicit "B was built from A" claims. |
| `cites` with `isInfluential === true` | Weak descent — counts | S2's influential flag is a high-precision signal that the cited work is foundational to the citing one, not a glancing reference. |
| `cites` without isInfluential | Excluded | Too many false positives; pollutes components. |
| `inspired-by` / `integrates-with` / `competes-with` / `same-team-as` | Excluded | Sideways or attributional, not descent. |

**Curated-seed expansion: depth-limited BFS.** Naive expansion takes
the connected component of each anchor through the full descent
sub-graph. The data showed this collapses *both* curated seeds (and
half the auto-discovery candidates) into one 119-node giant component
— the influential-cite backbone of the catalog. Solution: cap curated
BFS to 2 hops from the anchor. Yields RSSM≈5 and GraphRAG≈16 — focused
enough to read as families, dense enough to feel like a history.
Two hops is the sweet spot: 1 hop loses grand-children, 3 hops starts
absorbing unrelated descendants via shared citations.

**Auto-discovery: union-find on the remainder.** After curated seeds
claim their members, the rest is processed by classic union-find with
the same descent-edge predicate. Components < 3 are dropped (too small
to be a "family"). Top results are sorted by size desc, then anchor
date asc. Combined with curated, capped at 8 total lineages — the
diagram becomes unreadable beyond 8 rows.

**Naming rule.** A lineage's display name is `${anchor.name} family`,
where the anchor is the oldest member by `created` date (ties broken
by lexicographic id, then by undated-last so an anchor with a real
date always wins over one without). Curated seeds override this with
hand-written names ("RSSM / world-model family", "Graph-RAG
hierarchy"). The anchor is rendered with a larger, outlined node and
its label is brighter so the eye finds the family root immediately.

**Layout choices.**
- X-axis: continuous date axis (year + (quarter-1)/4), not a quarter
  bucket grid. The bucket-grid look fits histograms (timeline view)
  but a lineage diagram is read as "who came first" — continuous time
  is the right metaphor.
- Y-axis: one row per lineage, ordered curated-first then by size.
  No vertical packing (no within-row collision avoidance) — at
  ≤16 nodes per row in our data, simple horizontal positioning is
  legible.
- Edges: quadratic Bezier for same-row (slight arc upward so multiple
  sibling edges don't fully overlap); cubic Bezier for cross-row
  (currently rare; the curated/auto split usually contains its edges
  within one row).
- Arrows: filled triangle markers, blue for influential cites, grey
  for strong descent. Source → target convention matches the edge
  direction in the data.

**Why pure SVG.** Same rationale as the timeline view: small N
(≤8 rows × ~16 nodes each = ~130 nodes total), full control over
hit targets, no library cost. The cytoscape graph view (#16) is a
different beast — interactive force layout, 500+ nodes — and pays
the library cost there.

**Interactivity scope.**
- Hover node → tooltip with name, tier swatch, and first 320 chars of
  the `claims` cell (falls back to `desc`).
- Click node → navigate to `/?q=<name>` so the table filters to that
  system via free-text search. We don't drill to an id-specific facet
  because the table doesn't have one; search-by-name is the closest.
- Hover edge → tooltip with edge type, isInfluential flag, and the
  `evidence` blurb. No click navigation on edges.

**Reused by Phase 5.** The pure helpers in `lineages.ts` will feed
into the polish/share phase:
- `detectLineages()` → "filter graph (#16) to one named lineage"
  overlay. The same `Lineage.members` set becomes a node filter on
  the cytoscape graph.
- `isDescentEdge` predicate → consistent edge filtering across the
  graph, lineage, and any future "evolution view".
- Curated seed list → narrative blurbs on share cards ("the RSSM
  family: from DreamerV3 to PWM, R2I, and DIAMOND").

**Options rejected.**
- *Strong-only edges (no influential cites).* Produces 2-node
  components for both curated seeds — too sparse to be a "family".
- *Unbounded BFS for curated seeds.* Collapses everything into one
  giant component (see above).
- *Plot every member of every component.* The 119-node giant component
  would visually dominate the diagram. We cap the lineage **count**
  (8) but not the **member count per lineage**; the auto-discovery's
  largest survivor (~96 nodes) becomes one dense row that signals
  "research-paper citation backbone" — that *is* useful information.
- *D3 or vis.js timeline.* Overkill; SVG works.

**Reversal cost.** Low. Detection is one ~250-line pure-TS module;
the view is one Svelte file. Tuning the depth cap or the edge-type
weights is a one-line change. Adding a third curated seed is one
entry in `CURATED_SEEDS`.

---

## 2026-05-07: Cytoscape force-directed graph view (issue #16)

**What.** A new `/graph` route renders the full 523-record / 247-edge
landscape as an interactive force-directed graph using
[Cytoscape.js](https://js.cytoscape.org/) v3.33 with the
`cytoscape-fcose` layout plugin. Features: nodes coloured by primary
section (20-section categorical palette), edges styled by type
(distinct colour + dash for each of the six present edge types), a
search box that highlights the matched node and its 1-hop neighbours
while fading the rest, a side-panel record inspector with the
headline cells (desc / claims / perf / citations / gh), an edge-type
legend with checkbox toggles, and a "hub view" toggle that hides
everything outside the top 40 most-connected nodes.

**Bundle-size impact.** Cytoscape's minified ES build is **~430 KB raw
/ ~141 KB gzip**, and `cytoscape-fcose` adds another **~57 KB raw /
~16 KB gzip**. We isolate the cost via a dynamic `await import()` in
the +page.svelte `onMount` — Vite emits both packages into a separate
chunk (currently `D6wf7S9e.js`) that loads only when a user visits
`/graph`. The landing page, table view, timeline, leaderboards,
sections, and lineages pages stay at their pre-graph bundle sizes.
The trade is worth it: rendering 523 connected nodes with hand-rolled
SVG would need its own force-direction implementation, edge bundling,
and hit-testing — easily 50% of the cytoscape code re-written from
scratch.

**Layout choice — fcose, not cola or cose-bilkent.** fcose
("Fast Compound Spring Embedder") is bilkent's modern replacement for
cose; it tiles disconnected components (we have several — the
research clusters connect through citation chains but products often
sit isolated), and on this scale (~500 nodes, ~250 edges) it settles
in ~1s with `randomize: true`. Considered:

- **cola** — requires a separate plugin, more configuration knobs,
  and is slower on disconnected components (it doesn't tile out of
  the box).
- **cose** (built-in) — fcose's older sibling; visibly less even
  spacing on disconnected clusters in our test.
- **dagre / klay** — layered/hierarchical, wrong shape for this data
  (the edges aren't a DAG; cites + integrates-with form cycles).

Tuned parameters: `nodeRepulsion: 8000`, `idealEdgeLength: 70`,
`edgeElasticity: 0.45`, `gravity: 0.25`, `numIter: 2500`,
`nodeSeparation: 75`, `tile: true`. Picked empirically — bigger
`nodeRepulsion` blew clusters apart; smaller `nodeSeparation` tangled
the dense research cluster around foundational papers like MemGPT.

**Palette — 20-section categorical, hand-picked HSL anchors.** We
considered using d3-scale-chromatic's `schemeTableau10` doubled or
`interpolateSinebow` sampled at 20 points, but the catalog has no
strong "natural ordering" between sections so a sequential or
diverging palette would invent a relationship that doesn't exist.
The hand-picked palette in `graph.ts` rotates the hue circle so
adjacent palette entries don't share colour space, and every swatch
was checked against the dark `#0d1117` background for contrast.
Section order is by record count desc so the busiest cluster gets
the most recognisable colour (palette[0] = azure).

**Edge styling — colour AND dash, not colour alone.** Roughly 8% of
male users have red/green colour vision deficiency; relying on hue
alone for edge-type discrimination would leave the legend toggle
ineffective for them. Each edge type gets a hue + a line-style
(solid / dashed / dotted) + a width. Cites edges (189 of 247) are
the most common and get the thinnest, most muted style so they don't
dominate the rendering; built-on / extends / forks are heavier so
lineage chains read clearly even when zoomed out.

**SSR handling — `ssr = false` on the route.** Cytoscape constructs
against a live DOM container and starts the fcose worker
immediately, neither of which can happen during the prerender pass.
We `export const ssr = false` in `+page.ts` so SvelteKit emits a
hydration-only shell for `/graph` rather than crashing during build,
and keep `export const prerender = true` so the static-adapter still
emits a `graph.html` entry point. The cytoscape import is also
guarded by `if (!browser) return;` inside `onMount` as a belt-and-
braces defense if someone toggles ssr back on later.

**Search-highlight via class toggle, not viewport filter.** The
search box matches case-insensitive substring on `record.name` and
the first hit gets selected. We add a `faded` class to all elements
then strip it from the selected node and its 1-hop ring (precomputed
in `neighbourhoodIndex` so toggling is O(degree), not O(E)). The
faded class drops opacity to 0.08; the highlighted class adds a
white border + boosts opacity. The alternative — actually removing
non-matched elements from the cytoscape collection — would shift
the layout when the search clears, which is jarring. Fading
preserves position.

**Hub view — top-40 by total degree.** A toggle that hides
non-hub nodes by adding a `hub-hidden` class (with `display: none`).
We rank by total degree (in + out) so both "papers cited 30 times"
and "platforms integrating with 30 things" surface — inbound-only
would erase platforms; outbound-only would erase foundational
papers. Forty is the cutoff because the degree distribution drops
sharply after the top ~40 (long tail of 1-edge nodes); the view
becomes legible without a search narrowing it further. We don't
re-run the layout on toggle — re-positioning the hub subset would
be confusing; instead we fit the viewport to the visible subset.

**Reused from Phase 3.** `primarySection` (leaderboards.ts),
`inboundEdgeCounts` (leaderboards.ts) for the hub ranking. We
deliberately did NOT copy or re-export `parseNumber` /
`extractNumber` — the graph view doesn't rank by numeric cells
(yet); when it does (Phase 5 "size by citations" overlay), it'll
pull from `section-stats.ts`.

**Reused by Phase 5 (polish & deploy).** The data-shaping helpers in
`graph.ts` are pure — Phase 5's export endpoint can call
`recordsToNodes` + `edgesToCytoscape` to emit a GraphML / GEXF
static export for users who want the raw graph in Gephi / yEd. The
`SECTION_PALETTE` is the source of truth for any other view that
wants section-colour consistency (a hypothetical "section colour
band" on the table header rows would import the same map). The
`neighbourhoodIndex` helper is also reusable by the lineage view
if it wants "1-hop ring" highlighting on hover.

**Performance observation.** On the dev build, fcose's initial
layout takes ~800ms on this scale; subsequent re-renders (search,
toggle, hub-view) batch through `cy.batch()` and complete in under
20ms. Memory footprint of the live cytoscape instance is ~12 MB
resident — well within the 100 MB working budget for a client-side
app.

**Options rejected.**
- *D3 force-directed.* Would need ~150 lines of hand-rolled
  force-direction + drag-and-drop + zoom + hit-testing for a worse
  result than `cytoscape.use(fcose)`'s one-liner. The bundle
  saving (~80 KB gzip) isn't worth the maintenance.
- *Sigma.js.* Smaller bundle (~60 KB) but WebGL-only — no SVG
  fallback for screen-grab / accessibility tooling. We may revisit
  if Phase 5 adds a 10k-node future expansion.
- *Pre-computed layout baked into JSON.* Would let us drop fcose
  entirely (-57 KB), but then the user couldn't drag nodes around
  to inspect dense clusters. Force-direction is the whole point of
  this view.
- *Render at /graph/[section] with one section per page.*
  Considered for performance, rejected because cross-section
  citations are exactly what the user wants to see (e.g. AriGraph
  → MemGPT → Letta as a single chain of "built-on").

**Reversal cost.** Medium. Replacing cytoscape with another graph
library would mean rewriting the +page.svelte and its stylesheet
(the `style: [...]` array is cytoscape-specific syntax), but
`graph.ts` is pure data-shaping and trivially portable. The
DECISIONS-recorded fcose tuning is the only piece that's tied
specifically to this library family (cose / fcose / cose-bilkent
share the parameter names).

---

## 2026-05-07: Per-row detail — modal, not side panel (issue #18)

**What.** Click a row → opens a centered, viewport-sized **modal** showing
all 68 fields of the record, grouped by the same column-band scheme used
in the table header. Shift-click adds the row to a transient "selected"
set (cap 4); when ≥2 rows are selected, a "Compare" pill appears in the
toolbar that opens a **separate ComparePanel** (full-bleed side-by-side
cards). Both close on Esc / backdrop click; ComparePanel cards have an
inline X-remove and a "Clear selection" header button.

**Why modal vs side panel.**

- *Modal (chosen).* The detail view needs a lot of vertical space — 68
  fields × ~30px each is over 2000px. A right-docked side panel would
  either be too narrow (truncating multi-line cells) or eat half the
  viewport (defeating the "stay in the table" benefit). A modal can be
  ~960px wide and scroll vertically without competing for horizontal
  pixels with the table.
- *Side panel rejected.* Considered a Notion-style right rail (40 % of
  width). On a 67-column scrollable table the side panel would force
  horizontal scroll just to see the first few columns when the panel was
  open — and the user's main interaction is *staying in the row context*,
  which means seeing the row they clicked while reading details. The
  modal preserves the row's table context (still visible behind the
  backdrop) while giving the detail view full width.
- *Inline expand-row rejected.* The virtualised table assumes a fixed
  row height (56px). Variable-height rows would break the math.

**Why a separate ComparePanel (not "modal of N records").** The compare
view *needs* the horizontal width — 4 cards × 220px-min + label column
= ~1000px minimum. The modal at 960px would barely fit 3 cards. The
compare panel is full-bleed (1400px max-width) and uses a CSS grid so
each card lays out independently.

**Difference highlighting.** Each row of the compare grid is checked
for "all cards agree" vs "at least one differs". Differing rows get a
soft accent border (`box-shadow: inset 0 0 0 1px rgba(196,99,60,0.25)`)
and the field label switches to the accent color. Subtle so it doesn't
scream, but findable at a glance.

**Reversal cost.** Low. Each surface is its own file
(`DetailModal.svelte`, `ComparePanel.svelte`) wired to the page via
two small props. Switching to a side panel would mean changing the
backdrop element and removing the centered flex — minutes of work.

---

## 2026-05-07: Compare selection — transient store, not URL (issue #18)

**What.** The "selected for compare" set lives in a Svelte writable
store (`web/src/lib/stores/selection.ts`), capped at `MAX_COMPARE = 4`.
It does **not** round-trip through the URL.

**Why.** The set is genuinely transient — a "scratch pad" the user
collects rows into during a single browsing session. Pushing it into
the URL would:

1. Bloat the query string (`compare=id1,id2,id3,id4` adds ~150 chars
   for arxiv-slugged ids).
2. Encourage users to bookmark a comparison, which then breaks when
   one of the records is later renamed (id is stable, but a stale
   bookmark to a removed/merged record gives a confusing "1 record
   in compare" state).
3. Conflict with the existing URL-state contract in `url-state.ts`
   — every new param costs cognitive overhead for users sharing links.

A future "share this comparison" feature could be added by serialising
the ids on demand (a Copy Link button on the ComparePanel header) —
that's the right ergonomic shape for an explicit-share action, vs.
the implicit-share-by-bookmark that URL-sync implies.

**Reversal cost.** Trivial. Selection is one Set; URL sync is the
same shape as the existing facet sets.

---

## 2026-05-07: CSV flattening strategy (issue #19)

**What.** `web/src/lib/export.ts` exposes two pure functions, `toCSV`
and `toJSON`, that take `LandscapeRecord[]` and return a string. CSV
output has 73 columns: identity (id, name, tier, url, primary_section,
sections) + 7 taxonomy axes (`tax_storage`...`tax_conflict`) + 60 cell
slugs. JSON output is `JSON.stringify(records, null, 2)` — the full
structured shape, untouched.

**Flattening rules for CSV:**

- **Taxonomy axes.** Joined with `; ` (primary first, all values
  lower-cased canonical). The primary value gets `(primary)`
  appended in parens so downstream analysis can tell which one was
  canonical without parsing positional ordering. Example:
  `vector (primary); graph; hybrid`.
- **Sections.** Same pattern — `;`-joined, `(primary)` annotation,
  subsection joined with em-dash.
- **Cells.** `.value` is HTML-stripped and whitespace-collapsed, so
  no `<br>` or `<a href="...">` ends up in Excel. Status types map as:
  - `real-data` → value, with `[citation_url]` appended in brackets
    when present (so the source survives the export).
  - `not-applicable` → literal string `not applicable`.
  - `depth-floor-reached` → value + ` (searched, not found)`.
  - `no-data` → empty cell.
- **RFC 4180 escaping.** Fields containing `,` / `"` / `\n` / `\r`
  are wrapped in `"` with internal quotes doubled. Lines joined with
  `\r\n` (Windows Excel is the tetchy consumer here).

**Why bracket-annotate citations rather than a separate column.**
Doubling the column count (60 → 120) makes the CSV unwieldy in Excel
and forces consumers to know about column pairing. Bracket annotation
keeps the URL recoverable with a regex and the cell readable without
one.

**Why not include the columns spec.** The build brief explicitly says
"don't include the columns spec — let consumers slice". The flat shape
is intentionally one-row-per-record with a fixed superset of columns,
so a pandas user can `df[['tier','license','funding']]` without first
parsing a metadata header.

**Filename format.** `memory-landscape_<YYYY-MM-DD>_<filter_summary>.<ext>`,
e.g. `memory-landscape_2026-05-07_q=letta_tier=1,2.csv`. Summary is
truncated to first 3 values per facet to keep the filename a sane
length; characters outside `\w=,.\-` are replaced with `_`.

**Reversal cost.** Low. Both functions are pure; tests would mock no
DOM. A future "column-subset picker" can be added by passing an extra
`columns?: ColumnSlug[]` parameter — the function signatures are
forwards-compatible.

---

## 2026-05-07: Row-click wiring via tbody event delegation (issue #18)

**What.** Table.svelte attaches a single `onclick` listener on
`<tbody>`, walks up from the click target to the nearest `tr.row`, and
maps the row's position-in-children to the matching record in
`visibleSlice`. TableRow.svelte is **not** modified.

**Why delegation.** Two reasons:

1. *Performance.* 8-row overscan + ~25 visible rows × 1 listener each
   is fine, but the broader pattern of "interact with rows in a
   virtualised table" wants a single listener anyway.
2. *Locality of change.* The build brief constrains touching TableRow
   ("read only — only add a row-click handler in Table.svelte itself").
   Delegation respects that constraint.

**Why position-index rather than ID lookup.** TableRow doesn't put the
record id on the `<tr>` (only a tier class). Adding `data-record-id`
would mean touching TableRow. Position-in-children works because the
order of `visibleSlice` and the order of rendered `<tr>` children are
identical by construction (Svelte's `{#each}` with key preserves
insertion order).

**Interaction precedence.** The handler bails out early if the click
target is inside an `<a>` or `<button>` — so clicking the name link
opens the URL (not the modal), and clicking the citation ↗ opens the
citation. Shift-click toggles the row in the compare set; plain click
opens the modal.

**Reversal cost.** Low. Three lines in Table.svelte.

---

## 2026-05-07: `/about` page as embedded "how to read this" explainer

**What.** Issue #21. Added a 7th top-nav route, `/about`, holding a
single-column (~640px) prose explainer of tiers, taxonomy axes, cell
status indicators, edge types, methodology, and acknowledgements.

**Why.** First-time visitors land on a 67-column dense table with no
key. The README explains the catalog's *purpose* but not the *visual
grammar* — what a T3 badge means, why a cell says "searched not found",
how `same-team-as` differs from `succeeds`. An in-app page beats an
external doc because the user is already in the dark-theme web UI when
they need the explanation; tab-switching to GitHub breaks flow.

**Options rejected.**
- *Modal on first visit.* Cheap to dismiss-and-forget; can't be
  revisited via a stable URL; can't be linked to (e.g. "see /about
  §taxonomy" from a section description).
- *Inline footer help on the table page.* Would compete with the 67
  columns for screen real estate; modal #18+#19 already owns the
  table-row detail UX.
- *Move into README.md.* Loses the in-context theming, can't render
  visual samples of tier badges and status pills.

**Headline counts (523 / 67 / 247) are hardcoded** rather than pulled
from `landscape.json` via a loader. Justification: these change roughly
once per ingestion round, the page already has a "as of last update"
note, and avoiding a data dependency keeps the route a pure leaf —
nothing to wire into the +page.server.ts loader, nothing to invalidate.
Reviewers should refresh the numbers when they add a new ingestion
round (3 strings to edit; cheap).

**Tier-badge and status-pill samples are locally styled** rather than
imported from `TableRow.svelte` or a shared component. The styles are
duplicated (~30 lines) — but the alternative was either factoring a
presentational primitive out of `TableRow.svelte` (touches Phase-2
files, scope-creep) or importing a row component just to render five
badges (over-engineering for an explainer). The visual contract is
documented in this file; if the table's tier colours change, this
page's samples must change too (~5-line edit).

**Reversal cost.** Low. The page is a leaf route with no consumers.
Deleting it removes a nav item and one file; nothing else depends on
it.

---

## 2026-05-07: GitHub Pages workflow + base-path strategy (Issue #20)

**What.** Wired Pages deploy via `.github/workflows/pages.yml`. The
workflow runs on push-to-main + workflow_dispatch, sets up Node 20,
runs `cd web && npm ci && npm run build`, uploads `docs/` as the
Pages artifact with `actions/upload-pages-artifact@v3`, and deploys
with `actions/deploy-pages@v4`. The build job sets
`BASE_PATH=/memory-analysis-program` in env so that `svelte.config.js`
(which reads `process.env.BASE_PATH ?? ''`) emits asset URLs under
the project subpath that GitHub Pages serves at
`https://mrpeppersdev.github.io/memory-analysis-program/`.

**Base-path strategy.** Already correctly configured in
`web/svelte.config.js` — no code tweak needed. Two-mode behaviour:
- *Local builds / `docs/index.html` opened directly:* `BASE_PATH`
  unset → base `''` → all asset paths are root-relative. Works when
  served from a filesystem root or a `python -m http.server` at the
  repo root.
- *CI build for Pages:* `BASE_PATH=/memory-analysis-program` →
  SvelteKit prepends the project subpath to every internal link and
  asset reference. Pages serves the artifact under that subpath.
Caveat: if anyone opens `docs/index.html` after a CI-flavoured build
runs locally with the env var set, asset links will 404 (they'll
point to `/memory-analysis-program/_app/…`). The fix is to rebuild
without the env var. Documented this in the README so contributors
don't get confused.

**Path A vs Path B (workflow-scope wall).** Chose **Path A**: ship
the workflow file as a local commit even though the working OAuth
token (`gho_…`) lacks the `workflow` scope (only has `gist`,
`read:org`, `repo`). On push, GitHub rejects the workflow file
addition with `refusing to allow an OAuth App to create or update
workflow .github/workflows/pages.yml without workflow scope`. The
file is committed locally and surfaces in the commit message; the
user must either run `gh auth refresh -s workflow` and re-push, or
push from a context with a PAT/SSH key that has workflow scope.

**Prerequisite the user must satisfy manually.** GitHub Pages is
*not yet enabled* on this repo (`gh api repos/MrPeppersDev/memory-analysis-program --jq '.has_pages'` returns
`false`, and the repo is `private`). The user must:
1. Refresh the gh token with workflow scope (or push the workflow
   file via another means).
2. Verify the account has GitHub Pro or higher (Pages on private
   repos is paywalled — Free tier blocks deploys).
3. In Settings → Pages, set Source to "GitHub Actions" (not the
   default "Deploy from a branch", which would serve the
   already-committed `docs/` via Jekyll instead of running our
   workflow).
4. Push to main (or use workflow_dispatch) to trigger the first
   deploy.

**Options rejected.**
- *Serve `docs/` via the legacy "Deploy from branch" Pages mode.*
  Tempting because `docs/` already has the build committed and a
  `.nojekyll` marker, but locks us out of build-time env vars (the
  in-tree `docs/` was built with `BASE_PATH=''`, so its asset links
  would 404 on Pages). Would also mean every PR has to remember to
  rebuild before merge.
- *Build into a separate `gh-pages` branch instead of uploading the
  artifact.* The official `actions/deploy-pages@v4` flow is simpler
  and avoids the orphan-branch dance.
- *Commit a `BASE_PATH=/memory-analysis-program` into the in-tree
  build.* Breaks the local-file-open dev path and would create churn
  in `docs/` every time the deploy URL changes.
- *Set the base-path via a Vite config override instead of
  SvelteKit `paths.base`.* SvelteKit's own `paths.base` is the
  documented seam and it threads through `$app/paths`. Vite-level
  overrides wouldn't update link rewrites in
  `<a href="{base}/foo">` patterns that the route files already use.

**Reversal cost.** Low. The workflow file is self-contained; if the
deploy strategy changes (custom domain, separate org page,
docs.example.com), edit the one file. The base-path env var is the
only coupling between CI and the SvelteKit config.
