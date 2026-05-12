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

## 2026-05-12: Round 8 — survivorship Unknown-bucket OSS enrichment (79 rows)

**What.** Filled the `last-commit` signal for every row currently sitting in
the survivorship view's `Unknown — OSS but signal-too-weak` sub-bucket (79
records) by pulling `pushed_at` / `archived` / `stargazers_count` from the
GitHub REST API and writing it into each row's `code-release` cell in
`landscape.html`. After re-extraction, all 79 left the Unknown bucket and
the sub-bucket count dropped to 0.

**Rules used to identify the 79.** Reproduced `classify()` from
`web/src/lib/analyses/survivorship.ts` in Python and selected every record
where `status == 'unknown' && unknownSub == 'oss-weak-signal'`. That sub-bucket
fires when (a) the record is not Tier 3-5 research, (b) `latest-release` and
`code-release` carry no parseable date and any `created` date is >12mo old
and >6mo old, and (c) `hasGitHubPresence()` returns true — i.e. an explicit
`github.com` / `gitlab` URL in `cells.gh.value/.citation` or
`cells['code-release'].value/.citation`, OR a star-count phrasing like
"123 stars", OR an OSS license (apache/mit/bsd/gpl/mpl/agpl/open-source) on
the `license` cell. The license-based path is why 36 of the 79 rows had no
explicit GitHub URL in their cells — for those we mapped each row to its
canonical upstream repo manually (see `/tmp/manual_gh_map.py`).

**Cell format.** Replaced each row's `<td class="code-release">` with
`{Active|Stale|Abandoned|Archived} — last commit YYYY-MM · {stars}★`. The
status label is computed against the 12mo / 24mo bucket boundaries used by
`survivorship.ts`; "Archived" overrides bucket label when GitHub reports
`archived=true`. The cell's citation `<a class="cite" href="...">` always
points at the canonical `github.com/{owner}/{repo}` URL so downstream
parsers (Round 23 / influence-vs-adoption logic) can re-derive owner/repo.
`cells.gh.value` (star count + cite link) is NOT touched.

**gh-cache decision.** Committed `extraction/gh-cache/` to git for the same
reason `extraction/s2-cache/` is committed: reproducibility of the data
pipeline without forcing a fresh GitHub API hit on every reviewer's machine
(API has rate limits; the cache makes Round 8 deterministically reproducible
in seconds). Each file is `{owner}__{repo}.json` containing only the fields
we use (`pushed_at`, `updated_at`, `stargazers_count`, `archived`, `disabled`,
`fork`, `default_branch`, `description`, `created_at`, `full_name`). 79 files,
~30-50KB total. Mirrors the s2-cache pattern.

**Outcome (counts).** Before Round 8 the survivorship distribution was Active 80,
Stale 1, Abandoned 0, Unknown 321, Research 297; sub-buckets inside Unknown
were closed-source 242, oss-weak-signal 79, newly-created 0, na 0. After
Round 8: Active 156 (+76), Stale 4 (+3), Abandoned 0, Unknown 242 (-79),
Research 297. The Unknown floor is now `closed-source = 242` — proprietary
products with no public release cadence. That is a structural ceiling on
survivorship-view observability, not a catalog gap.

**Reversal cost.** Low. The 79 cells are byte-stable diffs in `landscape.html`;
reverting is `git revert`. The gh-cache directory can be re-fetched in ~30s
from cold.

---

## 2026-05-12: analysis.md v2 — refreshed against Round 7 data (699-record delta)

**What.** Second-pass refresh of `analysis.md` against the post-Round-7
catalog (699 records, 26 sections, 278 edges). Treated as a **delta
refresh**, not a rewrite: v2 structure preserved; numbers and findings
updated inline; new findings flagged **✶ v2.1**.

**Why now.** v2 of `analysis.md` (the prior entry below, dated
2026-05-12 same day) was written against the 523-record catalog
before the scope-expansion + Round 7 ingestion landed. Multiple
numeric claims drifted:

- Catalog size 523 → 699 (+176; +34%)
- Section count 20 → 26 (six new top-level sections)
- Tier counts: T1 145→211, T2 136→191, T3 100→140, T4 134→144, T5 13→13
  (note: prompt brief stated T1=213, T2=192, T3=141, T4=145; the
  actual `landscape.json` distribution as of this refresh is the
  numbers above)
- Edge count 247 → 278
- Storage `n/a` distribution: 28 → 182 (scope-expansion artefact —
  training / inference / observability rows that don't own a memory
  primitive)
- Funding pyramid: new mega-cap entries — Databricks / Snowflake
  ($62B parent), Anthropic ($40B parent on 3 rows), Sierra ($15.8B),
  Skild Brain ($14B), Harvey ($11B), Abridge ($5.3B), Decagon
  ($4.5B). Mem0 still at $150M.
- Governance disclosure: every record now has a non-null tag (was 73%
  / 71% in v2 at T3/T4).

**Net changes to analysis.md.**

1. New ✶ v2.1 executive summary (6 bullets, was 5 in v2). Headline
   updates: catalog size, integration leader (Mem0 still 12, now a
   floor), valuation gap (widened to 100-410×), candidate-lineage
   verdict, governance disclosure 100%.
2. §1.1 storage primitive table re-counted against 699 rows; new "n/a
   primitive went 28 → 182" framing.
3. New §1.1 subsection: "The six new (Round 7) adjacent-infrastructure
   sections" — one-row-per-section reference table.
4. §2.3 added "Mem0-inbound recount under Round 7 — *still 12, but a
   floor*" sub-section flagging the cell-mining shortfall.
5. §3.1 Files-as-memory member count corrected to 33 (was ~32 in v2;
   13 File-backed + 20 Claude Code mechanisms).
6. New §3.4: "Five Round-7 candidate lineages — edge-graph verdict."
   Of the five candidate lineages flagged in
   `extraction/round-7-ingestion.md` (Stanford agents, SSM, RLHF,
   Embedding models, Agent protocols), **one** has a confirmed
   3-node descent fragment (ExpeL → Reflexion → Self-Refine),
   **one** has internal descent within MCP only (Continue.dev →
   Official MCP Memory server). The other three (SSM, RLHF,
   embedding models) have zero internal descent edges — they are
   pattern-kind candidates.
7. §4.1 valuation pyramid rebuilt with the new $1B+ entries.
8. §7 horizontal-vs-vertical valuation-gap table broadened with
   substrate-parent and vertical-AI tiers. Gap recomputed: 100-410×.
9. §11.1 cross-listings policy section split into "original" (4
   shared-product cross-listings) and "Round 7 paired records"
   conventions, with the policy distinction made explicit.
10. New §11.3a: scope-expansion narrative — coverage claim
    re-stated against 699 denominator (75% memory-shaped core, 25%
    adjacent infrastructure with depth-floored cells).
11. §11.3 governance disclosure table updated to 100% across all
    tiers (was 73% / 71% at T3/T4 in v2).
12. New §12.4: Round 7 surfaces (substrate-parent vector-search
    consolidation, embedding-model acquisition signal, agent-protocol
    pile-up, labelling industry's revenue concentration, SSM family
    descent watch).
13. Appendix edge count updated to 278.

**What did NOT change (v2 claims that held).**

- Architectural fingerprints A-E
- ConvoMem ~150-turn threshold
- LoCoMo dispute is still unresolved
- Anti-patterns 9.1-9.8
- Decision matrix rows (one or two row examples shifted; structure
  preserved)
- The 7 white-space gaps (gap 3 — bi-temporal KG outside Zep — re-
  verified against 699 records: still UNCHANGED)
- The Pattern C insight (files-as-memory is *pattern*, not descent)

**Five candidate lineages — edge-graph verdict (summary).**

| Candidate | Internal edges | Status |
|-----------|----------------|--------|
| Stanford agents (Gen.Agents → Voyager → Reflexion → ExpeL → Self-Refine → ChunkRAG → RAPTOR) | 2 (ExpeL→Reflexion, Reflexion→Self-Refine) | Partial — 3-node descent fragment |
| SSM (Hyena → Mamba → Mamba-2 → Jamba) | 0 | Pattern, edges sparse |
| RLHF (LoRA → QLoRA → DPO → GRPO → TRL) | 0 | Pattern, edges sparse |
| Embedding (S-Trans → BGE → GTE → Nomic) | 0 | Pattern, edges sparse |
| Agent-protocol (MCP → A2A → AGNTCY) | 2 (within MCP family only) | Pattern, no cross-protocol descent |

**Mem0 inbound recount.** Re-checked `landscape.edges.json`: Mem0 has
**12** inbound (integrates-with + built-on + extends) edges,
unchanged from v2. The Round 7 agent-framework rows (LangChain,
LangGraph, CrewAI, LlamaIndex, AutoGen, n8n) did not add new inbound
edges to Mem0 — the cell-miner needs a second pass over the new HTML
before those built-on relationships will surface. The 12 is now a
*lower bound*, not the corrected count; expect upward revision in
Round 8.

**What's deferred for Round 8.**

- Re-run cell-miner over the 176 new Round 7 rows; expect new
  built-on / integrates-with edges to surface, particularly into
  Mem0, Zep, LangGraph Persistence, and the embedding-API tier.
- Round 9+ would deepen the per-cell research depth on the new
  Training-infrastructure and Inference-platforms rows. Currently
  most have headline cells (desc, claims, created, license,
  founders, funding) populated but the long tail of 60 columns is at
  depth-floor.
- The Stanford-agents and SSM candidate lineages may be
  promotion-eligible after Round 8 cell-mining; until then they
  remain pattern-kind candidates rather than curated descent seeds.
- The §11.3 "quality of governance disclosure is shallow" finding
  should be sharpened with a count of records that engage with
  consent / provenance / audit-by-construction substantively
  (vs records that default to `inspectable` or `opaque` because OSS
  or closed).

**Reversal cost.** Low. The v2 → v2.1 changes are inline edits within
the existing structure; reverting is one `git revert` away.

---

## 2026-05-12: Round 7 ingestion — six new sections, 176 new rows

**What.** Round 7 of the catalog ingestion executes the scope expansion
authorised on the same date (see prior entry). Six new top-level sections
land in the catalog, populated with 176 new rows:

1. Training infrastructure (51 rows)
2. Search platforms (non-memory) (15 rows)
3. Agent frameworks (no first-party memory layer) (39 rows)
4. Inference platforms & gateways (15 rows)
5. Embedding & reranker services (11 rows)
6. Evaluation & observability platforms (15 rows)

Plus 30 additional rows pushed into existing memory-shaped sections
(Dedicated memory layers, Framework-embedded memory, Retrieval-as-memory
hybrids, Recent method papers' five subsections).

**Final catalog: 699 records, 26 sections.**

**Why split into six new sections rather than fewer.** Each of the six
captures a distinct buyer-question / substrate role:

- *Training infrastructure* answers "where will I train / fine-tune". 
- *Search platforms (non-memory)* answers "where will I run a non-memory
  vector / search workload". Distinct from "Vector-database infrastructure"
  (which exists for substrates beneath memory products) — having both lets
  readers find a vector DB whether or not memory is the lens.
- *Agent frameworks (no first-party memory layer)* answers "which
  framework will I build my agent on". This is a different angle on
  systems also covered by Framework-embedded memory; see cross-listings
  policy below.
- *Inference platforms & gateways* answers "where will I host LLM
  inference / how will I route LLM calls". Separated from training
  infrastructure because the buyer's question is genuinely distinct;
  inference + gateway costs dominate operational ML budgets, training
  infra is mostly upfront.
- *Embedding & reranker services* answers "which embedding/reranker
  API am I using". Distinct from inference platforms because the
  procurement and SLO conversation is different (embedding APIs are
  bursty short-request; LLM inference is long-context streaming).
- *Evaluation & observability platforms* answers "how will I watch
  and grade my agent in production". Distinct from the memory-specific
  "Memory observability & monitoring" section, which focuses on
  poisoning detection, memory-quality dashboards, and provenance —
  not generic LLM tracing.

**Cross-listings policy.** Two flavours of cross-listing now exist:

1. *"Same product, two framings"* (original Round 4 convention): one
   record, multiple section memberships, tracked in
   `extraction/cross-listings.json`. Used when the same URL is genuinely
   described differently in two sections (e.g. Mem0 + AgentOps as
   memory-product vs observability lens of the same product).
2. *"Two distinct framings of the same vendor"* (Round 7 convention):
   two separate records, each with its own primary section, linked by
   future descent / same-team-as edges. Used for major frameworks
   (LangChain, LangGraph, LlamaIndex, AutoGen, CrewAI) where the
   memory subsystem and the framework-as-orchestrator are genuinely
   different products that ship side-by-side.

Choice was made per-system based on whether the cross-section content
would be substantively different. For agent frameworks, the memory
row characterises memory primitives, and the agent-framework row
characterises orchestration / tool calls — these are different enough
to warrant separate cells across all 60 columns. The original
cross-listings (Mem0, Zep, Memobase, MemoryBench) were lenses of the
*same* shipped artefact; the new ones are *paired* artefacts of the
same vendor.

**Trade-offs and known issues.**

- *render.py drops cross-listing rows on round-trip.* This is a
  pre-existing limitation surfaced by Round 7's larger run. render.py
  emits each record once under its primary section with a
  `cross-listed` marker; re-extracting that HTML loses the secondary
  section. To preserve cross-listings, Round 7 skips render.py —
  the canonical landscape.html is hand-inserted, and json/edges are
  derived from it. Path B (HTML is source, JSON is derived) remains
  active. A future render.py fix would emit one row per section
  membership (with deduplication on the JSON side).
- *Per-cell research depth varies.* The 176 new rows have headline
  cells (desc, claims, created, license, founders, funding) populated
  with citations where data is plentiful; the long tail of 60 columns
  is mostly depth-floor-reached. This matches the user's "everything
  we can get our hands on" framing: prefer breadth of coverage over
  depth per cell. Round 8+ can deepen the most-trafficked entries.

**Reversal cost.** Medium. Sections are easy to drop (remove from
section-explainers.json and CANONICAL_SECTIONS, regenerate). Records
are easy to drop (delete rows from landscape.html, regenerate).
Cross-listing decisions for the new agent-framework rows can be
flipped into proper cross-listings via reconcile rules.

**Files changed.** See `extraction/round-7-ingestion.md` for a
per-row inventory and source citations.

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

---

## 2026-05-12: analysis.md v2 refresh

**What.** Re-grounded `analysis.md` against the terminal catalog (523
records × 67 cols) and the new structured views the SvelteKit app
exposes — `leaderboards.ts`, `lineages.ts`, `section-stats.ts`,
`landscape.edges.json` (247 edges).

**Why now.** v1 of `analysis.md` was written before Phase 1 (data
extraction) and Phases 3–4 (trend analysis + KG) shipped. Several
numeric claims drifted: Mem0 inbound count was reported correctly but
without the edge-graph methodology; Superpowers GH stars (179.8k) was
a parent-repo conflation; governance disclosure nulls at T3/T4 were
89% / 97.7% in v1 but the tagging pass has since brought those to
27% / 29%; funding cell population went from 32 → 220 with new Sierra
($15.8B) and Glean ($7.2B) entries.

**Net changes.**
1. New executive summary at top (5 bullets).
2. New §1.1.a — section × storage concentration matrix.
3. New §1.1.b — section-level median citations / funding / GH stars.
4. New §3 — Lineages, the descent map. 3 curated seeds (RSSM,
   Graph-RAG, Files-as-memory) + 6 auto-discovered, all per
   `lineages.ts`. Explicit treatment of the descent-vs-pattern split:
   files-as-memory is now a **pattern**-kind curated seed (rather than
   being treated as a missing/failed auto-detection) because its
   members converged on one idea by parallel evolution rather than
   descent.
5. New §6.3 — Top inbound citations within the catalog (vs total
   S2 cites).
6. Renumbered §4 (Commercial), §5 (Performance), §6 (Citations),
   §7 (horizontal-vs-vertical), §8 (Decision matrix), §9
   (Anti-patterns), §10 (White-space, revisited), §11 (catalog
   self-observations including the governance correction), §12
   (NEW: forward-looking with data signals).
7. Tagged every new finding with **✶ v2**.

**What did NOT change.** Pattern A–E descriptions, ConvoMem
threshold, LoCoMo dispute, valuation-gap conclusion, the 7 white-space
gap rows (only item 2 — skill-as-memory — moved from "research-only"
to "partially filled" because Interloom / LangMem / LinkedIn Cognitive
Memory Agent now ship skill-unit memory).

**Reversal cost.** Low. analysis.md is prose; the file is in git, so
v1 is one `git revert` away. The numerical methodology now references
specific `web/src/lib/*.ts` modules — if those refactor, the section
references should be updated alongside.

**Locked-in for Track C second pass (after new-ingestion #2 lands).**
- Re-verify the 6 white-space gaps that are listed UNCHANGED.
- Re-run lineage detection — if `world_model` adds its first
  commercial member, the §3.1 RSSM lineage moves from "5 academic
  nodes" to "first cross-tier descent" and should be promoted in §12.3.
- Re-check Mem0 inbound count — if it crosses 15, the network-effect
  claim should be re-quantified.
- Re-pull S2 citations — Transformer-XL moved 3,000 → 4,300 between
  v1 and v2; expect more 2026 papers to gain cites.

---

## 2026-05-07: Column-subset picker for export (Polish)

**What.** Extended the Export popover with a column picker. Users can
pick any subset of the 73 exportable columns; the picker is grouped by
the same column-band scheme as the table head (Identity / Substance /
Activity / …). Four quick-selects ship in the popover: "All", "None",
"Identity only", "Identity + claims + perf". The selection threads
through to `toCSV(records, columns?)` and `toJSON(records, columns?)`
via an optional `columns` parameter; when omitted the legacy full
export shape is preserved.

**Why.** Issue #19 left the picker flagged optional but real users
exporting for analysis spreadsheets uniformly want narrower slices —
60 cell columns is too wide for almost every downstream tool. The
grouped-band layout lets users target a group ("just architecture") in
two clicks rather than scanning a flat list. Identity-extras (`id`,
`url`, `primary_section`, `sections`) are exposed under the Identity
group because they're useful for cross-references in JSON exports but
aren't visible columns in the table.

**Options rejected.**
- *Separate modal dialog.* Adds a navigation step; users lose the
  "selected N columns" preview when the modal opens, breaking
  fitness-for-purpose feedback.
- *Persistent per-user defaults.* localStorage state would survive
  refreshes but adds a settings-store surface; for a single-export
  workflow the cost outweighs the convenience.
- *Drop identity-extras from the picker.* CSV consumers commonly need
  `id` for join keys; surfacing it explicitly is cheaper than
  documenting "you always get these four columns".

**Reversal cost.** Low. `toCSV` / `toJSON` keep their no-arg
behaviour, so any consumer (tests, future Node-side script) that
ignored the picker continues to work. The picker UI is self-contained
in ExportButton.svelte.

---

## 2026-05-07: Narrow-viewport drawer for filter rail (Polish)

**What.** On viewports under 900px the FilterRail collapses out of the
flex row and reappears as a fixed-position slide-in drawer triggered
by a "Filters (N active)" pill in the toolbar. Backdrop click, an
explicit close (×) button, and Esc all dismiss the drawer. Above 900px
the rail keeps its original 260px sticky-left behaviour.

**Why.** The 260px rail is acceptable on a 1440px laptop but cripples
narrower screens — it eats 25 % of the table area on a 1024px tablet
and pushes the table off-screen on a phone. A drawer is the standard
mobile-pattern for faceted-search rails and lets the table keep its
full width when the user isn't actively faceting. Implemented with a
single MediaQueryList listener (cheaper than a ResizeObserver for a
binary breakpoint) and a `drawer`/`open` prop pair on FilterRail —
no library needed.

**Breakpoint owner.** The parent (`+page.svelte`) owns the breakpoint
decision and passes `drawer={isNarrow}` to the rail. The rail itself
is breakpoint-agnostic: pass `drawer=true` from any caller and it
behaves as a drawer regardless of viewport. This makes the rail
testable at any width and keeps the rail's CSS free of media queries.

**Options rejected.**
- *Collapse the rail to icon-only.* Counts are integral to faceted
  search — hiding them defeats the affordance.
- *Reflow the rail above the table.* Pushes the table down by
  600-800px on every narrow page-load; users would have to scroll
  past it to see any data.
- *Use a library like Headless UI / Vaul.* Pulls a dep tree for a
  100-line component.

**Reversal cost.** Low. Strip the `drawer`/`open`/`onClose` props
from FilterRail and remove the `.drawer` CSS block; the rail
collapses back to its original sticky-left form.

---

## 2026-05-07: In-cell match highlighting for search (Polish)

**What.** When `$searchQuery` is non-empty, every occurrence of the
query string inside the `name`, `desc`, and `claims` cells is wrapped
in `<mark class="search-hit">` (styled with a muted accent background
in `app.css`). Other cells are unchanged. The wrapping happens in two
helpers in `$lib/stores/search.ts`: `highlightPlain` (for the name
column, which is text) and `highlightHtml` (for the cell values,
which are pre-rendered HTML).

**HTML-boundary heuristic.** Cell values may contain markup
(taxonomy pills, `<a>` links, `<br>` tags, signal-num spans). A naive
`String.replace` on the whole value would corrupt attributes like
`<a href="...rocksdb...">`. The implementation splits the value on the
tag-boundary regex `(<[^>]*>)` into alternating text/tag chunks (odd
indices are tags), runs the replace only on the text chunks, and
concatenates. This is the "approximation OK" path called out in the
issue brief — perfect HTML-tree highlighting would require a DOM
parse and is over-budget for the value it adds. Edge case: a literal
"<" appearing as `&lt;` in the source is already encoded by the
extractor, so it doesn't trip the splitter.

**Why limit to name + desc + claims.** Those are the same fields
indexed by `applySearch()` — highlighting matches outside the
haystack would mislead users about why a row passed the filter.

**Reversal cost.** Low. Remove `highlight={…}` from the TableCell
call in TableRow and the `{@html nameHtml}` form on the name column;
both helpers in `search.ts` become dead exports but don't break
anything.

---

## 2026-05-12: Scope expansion — adjacent infrastructure now in catalog

**What.** The previous scope statement excluded "pure LLM training, generic
vector search without a memory story, agent frameworks without a memory layer"
even when adjacent. That exclusion is removed. The catalog now aims at
comprehensive coverage of the broader sphere — memory systems plus all
infrastructure that touches memory work (training platforms, dataset stores,
search products, agent frameworks of all kinds).

**Why.** User direction. The earlier exclusion was a filter for "memory-shaped"
focus, but in practice readers need to compare against the adjacent layers when
making technology choices. A LangChain row that says "no first-party memory,
but ships connectors to Mem0/Letta/Zep" is more useful than a missing entry.

The user explicitly rejected anchoring on category-size estimates ("dont even
bother to calculate the rough size — that just puts soft limitations on the
number of things you pull in"). The new mandate: pull in everything in the
sphere that can be sourced.

**Implications.**
- The "Memory Analysis Program" / "Memory Systems Landscape" name remains for
  now; if the adjacent categories grow to dominate, the name may need to
  evolve to reflect "AI infrastructure landscape, memory-emphasised".
- New sections may be needed for the new categories (e.g. "Training
  infrastructure", "Search platforms (non-memory)", "Agent frameworks
  (no first-party memory)").
- Coverage claim on the about page is now split: ~88-92% for the memory
  core, lower-and-growing for the adjacent categories.
- Existing rows that span scope (e.g. LangChain, already in for its
  embedded-memory subsystem) may need re-tagging to acknowledge their
  broader role.

**Reversal cost.** Medium. Removing rows is easy; re-tagging the cross-scope
ones takes a pass. The scope statement itself is one paragraph.

---

## 2026-05-07: Files-as-memory as 3rd curated lineage seed (Polish)

**What.** Added a third curated lineage to `$lib/lineages.ts`:
"Files-as-memory thread". Anchored on the CLAUDE.md record. Members
are the catalog rows tagged in the "File-backed / editor paradigms"
section plus the "Claude Code memory mechanisms" section (~33 records
including AGENTS.md, Cursor rules, Continue rules, Cline clinerules,
Roo Code, Windsurf memories, Zed rules, aider conventions, and a long
tail of MCP-based memory implementations).

**Pattern lineage vs descent lineage.** Crucially this lineage has
*no* `built-on` / `cites` edges between its members — that's why the
auto-discovery pass didn't surface it. The members converged on the
same architectural pattern (text file the model reads at session
start) by parallel evolution, not common ancestry. We mark this with
a new `kind` field on `Lineage`: `'descent'` (the default — what RSSM
and Graph-RAG are) vs `'pattern'` (parallel implementations of a
shared idea). The /lineages page renders pattern lineages with dashed
connectors between consecutive members, a distinct track sublabel
("· pattern"), and a "parallel-implementations" legend entry — so
the visual cue matches the semantic distinction.

**Materialisation difference.** Descent seeds expand by depth-limited
BFS over the descent sub-graph (built-on / cites edges). Pattern
seeds expand by *section membership* — any record whose `sections`
list intersects the seed's named section list joins the lineage. The
seed declaration carries an explicit `sections` array, so adding a
new pattern lineage later is a single CURATED_SEEDS entry.

**Why.** Files-as-memory is one of the three dominant production
memory patterns (alongside RAG-over-conversation-store and
graph-RAG) but it's invisible on the lineage view because the
discovery algorithm only follows descent edges. A curated pattern
seed is the cheapest way to surface the family without polluting the
edge data with synthesised "parallel-implementations" edges. Anchor
choice: CLAUDE.md is the most-recognised name for the pattern even
though Cursor and aider predate it chronologically; the seed's
preferred anchor is kept when the record is present, otherwise the
code falls back to the oldest member by `created` date.

**Options rejected.**
- *Add synthetic `parallel-implementations` edges to the edge data.*
  Pollutes a primary-source dataset with our derived classification;
  hard to undo and breaks the invariant that edges are evidenced.
- *Make every file-backed system "built-on" CLAUDE.md.* Historically
  wrong — Cursor and aider predate Claude Code; AGENTS.md was a
  consortium effort.
- *Hide the family entirely (status quo).* The user explicitly
  flagged it as a gap; deferring leaves /lineages incomplete.

**Reversal cost.** Low. Drop the curated seed from `CURATED_SEEDS`
and remove the `kind` field from `Lineage` (plus the `pattern` branch
in `detectLineages` and the dashed-edge branch on the page); the
union-find pass is unchanged.

---

## 2026-05-07: Influence-vs-adoption matrix — scale, cutoffs, tier sizing

**What.** The `/analyses/influence` view (issue #22) plots every record
on two axes derived from the in-catalog edge graph:

- **X**: inbound `cites` edges (academic influence).
- **Y**: inbound `integrates-with` + `built-on` edges (commercial adoption).

Three design choices in this view warranted dedicated thought:

1. **Linear, not log.** Both axes have small integer ranges at the current
   corpus size (cites max ≈ 9, integrations max ≈ 12). ~80% of records
   sit at the origin. Log would (a) require a `log(1 + x)` shift to admit
   zeros, (b) compress the outliers we most want to see, and (c) confuse
   readers who reasonably expect "10 means roughly twice 5" on a count
   axis. The brief flagged log "if the distribution warrants" — at this
   data volume it does not. Re-evaluate when either axis exceeds ~50.

2. **Quadrant cutoffs = non-zero median per axis.** A population median
   is 0 on both axes (most records have no inbound edges) and would
   make the cutoff line touch the axis itself, defeating the four-way
   partition. We compute the median of the non-zero subset on each axis
   independently — currently 2 for cites and 1.5 for integrations.
   Strict-greater-than comparison: a record with value === cutoff stays
   in the lower quadrant. This yields concrete quadrant populations of
   roughly 1 "both" / 10 "engineering" / 25 "orphan" / 487 "tail",
   which is the headline the chart should communicate. Alternatives
   considered: fixed numeric cutoffs (brittle as the catalog grows),
   top-N-by-axis (different semantics — would always show 10/10/10),
   percentile of non-zero (similar result, more code).

3. **Tier → marker radius (linear).** T1=7px, T2=6, T3=5, T4=4, T5=3.
   Linear because tier is an ordinal 1-5 with no log meaning. The
   intent is "biggest dots are the systems you should trust most" so
   the eye lands on T1/T2 first. We deliberately keep the smallest dot
   at 3px (still hit-target-viable for hover) rather than going to
   2 or 1 — sub-3px points disappear visually on dark backgrounds.

   The bottom-left long-tail pile is also de-overlapped with a small
   deterministic radial jitter (≤0.35 axis-units, hashed by record id)
   so the reader can perceive density. Jitter is applied only on axes
   where the underlying value is exactly 0; once a record has a real
   value the position is honest.

**Why.** The chart is a recruitment tool for the four named patterns
(both / engineering wins / research orphans / long tail). Each design
choice serves "make the named patterns visible and the rest legible".
Log would hide the patterns; population-median cutoffs would erase
them; uniform marker size would lose the tier signal.

**Options rejected.**
- *Log scale both axes.* Compresses outliers; the patterns are in the
  outliers. Re-evaluate at >50 max on either axis.
- *Fixed cutoffs (e.g. cites ≥ 3, integrations ≥ 2).* Brittle as the
  catalog evolves; documenting "median of non-zero" lets the cutoffs
  follow the data.
- *Annotate every quadrant member.* 25 labels in the orphan quadrant
  would tangle. We annotate top-4 per non-tail quadrant; the tail
  gets no labels by design.

**Reversal cost.** Low. The scale function and cutoff source both
live in `web/src/lib/analyses/influence.ts` as pure helpers; swap
`nonZeroMedian` for a different selector and the chart adapts. The
log/linear projection is two lines in `+page.svelte` (`projX`/`projY`).

---

## 2026-05-07: Lineage forecast — "watch list, not prediction"

**What.** The `/analyses/forecast` view (issue #27) consumes the same
lineages emitted by `detectLineages()` and, for each, surfaces:

- the cadence — mean gap (in quarters) between consecutive dated members
- a projected next-expected year-quarter — `latest_member_idx + cadence`,
  rounded to the nearest quarter
- the 3 most-recent members (the "leading edge"), clickable into the
  main table
- up to ~8 theme keywords pulled from the leading edge's `claims` and
  `cons` cells (no `future-work` cell exists in the schema; claims +
  cons is the closest proxy for "what is the leading edge still arguing
  about")
- adjacent lineages — other detected lineages that share a member or
  have a descent edge crossing the boundary
- watch links — arxiv abstract URLs for any leading-edge member whose
  id encodes an arxiv reference, plus a generic `cs.AI/recent` listing
  as a fallback subscription target

**Why "watch list, not prediction".** The maths is intentionally naïve:
mean-of-inter-arrival on at most ~10 dated members, no confidence
interval, no Poisson fit, no decay weighting. With sample sizes that
small the only honest framing is "if the cadence holds, look here next"
— anything stronger pretends to precision the data can't support. The
copy on the page leads with a calibration disclaimer; every card ends
with a "watch list, not prediction" footer. We borrow the phrasing
from the task brief deliberately because it captures exactly the
epistemic stance: this is a bookmark for where to look, not a forecast
to defend.

**Cadence floor at 0.5 quarters.** Two members in the same quarter
would otherwise yield a 0-quarter gap and predict the next drop in
the same quarter as the latest member — which reads as "tomorrow" and
adds noise rather than signal. We floor zero-gaps at 0.5 so clustered
releases produce a sensible projected quarter.

**Display order = fastest cadence first.** "Most active" families
should be at the top because they're where readers will get the most
near-term return on attention. Lineages with too few dated members
to compute a cadence sink to the end with a "too few dated members"
caption.

**Theme extraction = frequency over claims+cons.** Tiny corpus
(claims + cons of 3 records), no TF-IDF baseline corpus to compare
against, so we use raw frequency with a stopword list tuned for
ML-paper boilerplate ("baseline", "method", "approach", "task" etc.).
The themes are decorative — they help the reader form a quick gut
sense of "what is this lineage actually working on now" — and not
intended to be authoritative.

**Watch links.** Record ids encode arxiv references for paper records
(`<slug>--arxiv-YYMM-NNNNN`). We regex that out into a real
`arxiv.org/abs/` URL and emit one watch link per leading-edge paper.
Product lineages (no arxiv ids on their leading edge) fall back to
the generic `cs.AI/recent` listing so every card has *something*
clickable. We deliberately do not promise these are the right
subscription targets — they're starting points, consistent with the
"watch list" framing.

**Reversal cost.** Low. All logic lives in
`web/src/lib/analyses/forecast.ts` (pure helpers) and
`web/src/routes/analyses/forecast/+page.svelte` (presentation only).
Swap `computeCadence` for a different estimator (median, exponential
decay, Poisson MLE) and the page picks it up unchanged. The page
copy carries the calibration framing — any future change that
strengthens the maths should update the disclaimer to match.


## 2026-05-07: Taxonomy archetypes — primary-only fingerprint clustering

**What.** /analyses/archetypes clusters every record by a
seven-character "fingerprint" formed by concatenating the *primary*
value on each of the seven taxonomy axes (storage, retrieval,
persistence, update, unit, governance, conflict), joined by `|`. Two
records share an archetype iff every one of those seven values
matches exactly. Archetypes are ranked by member count desc; the
top-12 get a card on the page. Singletons go into a "long tail"
roll-up. A separate "white-space candidates" panel surfaces
singletons whose individual axis values are each common in the
catalog (min-axis popularity ≥ 25) — the building blocks exist,
the assembly doesn't.

**Numbers (May 2026 catalog, 523 records):**
- 378 distinct fingerprints
- top 12 cover 15.9% of the catalog
- 307 fingerprints have only one member (58.7% of records)
- dominant archetype: file|injection|cross-session|overwrite|document
  |user-controllable|manual (the CLAUDE.md / AGENTS.md / Aider family,
  11 systems, 2.1%)

**Why primary-only rather than the full axis arrays.** Taxonomy
axes are always-array (see the 2026-05-08: Always-array entry).
Multi-value axes legitimately exist — Memvid stores both vector and
file, some systems mark both vector and graph storage. Three
fingerprint definitions were considered:

1. **Primary only** (chosen). Hash the single primary value per
   axis. Each record contributes one fingerprint.
2. **Full sorted set per axis.** Hash the sorted tuple of all values
   per axis. Each record still contributes one fingerprint, but a
   system that's both vector+graph splits away from systems that are
   "vector with a graph footnote".
3. **Cartesian product across axes.** Each record contributes
   `Π |axis_i|` fingerprints; archetypes count records that share
   *any* element of the product. Allows soft matching.

Option (2) is overly aggressive: an inspection of Memvid's row
showed it would land in a 1-member fingerprint despite being
structurally identical to other vector-store products that just
didn't bother to mark the secondary axis. The labelling cost of "did
the curator remember to add the secondary value?" propagates into the
clustering. Option (3) inflates the archetype-per-record cardinality
and makes the "top 12 cover X%" headline number ill-defined (records
appear in multiple archetypes). Primary-only matches every other
collapsing decision in the codebase — `/sections` reads primary,
filter facets read primary, `section-stats.ts::primaryTaxonomy`
reads primary. Consistency wins.

**Why a 7-element hash bar (not 4 or fewer).** The user's brief
called for archetypes "richer than any single axis" — the brief
implied 4-6 axes was acceptable. A check on collapsing to a 4-axis
hash (storage/retrieval/persistence/unit, omitting update,
governance, conflict) brought the top-12 coverage to 38%, but
collapsed three distinct clinical patterns into one bucket
(append-only vector with episode units vs overwrite vector with
chunk units — these are RAG vs episodic agents, not the same
archetype). Full 7-axis hashing keeps the analytical distinction
visible even at the cost of higher long-tail.

**Why min-axis popularity for the gap panel.** A singleton can be
unique for two reasons: (a) at least one axis value is itself rare
(in which case the singleton is just a rare-axis system, not
white-space), or (b) every axis value is common but no other system
has assembled them this way (which is the interesting case). Sorting
singletons by the *minimum* axis-value popularity across the seven
axes promotes (b) and demotes (a). A floor of 25 (≈ 5% of the
catalog must use each axis value) cuts the noise. Sum-popularity is
the tiebreaker — between two recipes whose rarest axis appears 30×,
the one whose overall axis values appear more often is the bigger
"obvious gap".

**Options rejected.**
- *Embed records and run k-means on the resulting vectors.* Would
  produce "fuzzy" clusters that don't correspond to the discrete
  taxonomy values the rest of the app uses. Off-axis with the
  reader's mental model.
- *Hierarchical clustering with edit distance on the fingerprint
  string.* Better at surfacing "near-recipes", but the resulting
  cluster shapes don't lend themselves to the "fingerprint badge"
  visual idiom — every cluster member has the same 7 badges, which
  is the whole point of the card layout.
- *Use a similarity threshold (≥ 5 of 7 axes match).* Promising,
  but makes the "membership" relation non-transitive and turns the
  list-of-archetypes into a graph-of-overlapping-cliques. Too much
  UI complexity for a sub-view.

**Reversal cost.** Low. Helpers in
`web/src/lib/analyses/archetypes.ts` are pure and self-contained;
the page is presentational. Swapping fingerprint definition is a
one-function edit in `fingerprintOf`. The clustering primitive
(`clusterByFingerprint`) is reusable for any future fingerprint
schema.

---

## 2026-05-07: Vocabulary drift — curated term list + counting rule

**What.** The `/analyses/vocabulary` view (issue #26) tracks
**27 hand-curated memory terms** grouped into five themes —
cognitive-science (episodic / semantic / working / procedural /
declarative), mechanism (parametric / latent / retrieval / vector /
graph / knowledge-graph), agent-era (agentic / lifelong /
world-model / persistent / ephemeral), architectural (bi-temporal /
key-value / KV / attention / RAG / MCP), and emerging
(continual / in-context / hierarchical / episodic-memory /
working-memory). The list lives in `TRACKED_TERMS` in
`web/src/lib/analyses/vocabulary.ts` and is the only curation
surface; extend it via PR + a follow-up entry here.

**Counting rule: one mention per record, not one per occurrence.**
A record contributes 1 to a term's bucket if the term appears
*anywhere* in its `desc` + `claims` cells (case-insensitive,
word-boundary, HTML stripped). Repeated mentions inside the same
record do not increment the count.

**Why one-per-record.**
- The catalog cells are written by us during extraction, with
  variable verbosity. A 4-paragraph `claims` cell mentioning
  "episodic" five times is one *system* that's episodic, not five.
  Counting occurrences would reward verbose entries — i.e. measure
  our writing style rather than the field's vocabulary drift.
- The bucket axis is *records-created-that-quarter*. The
  semantically natural numerator is also records (so the ratio
  "fraction of new systems mentioning X" is well-defined later if
  we add a normalised view).
- Recovery is cheap: `countByQuarter` could be re-implemented to
  return occurrence counts without changing any caller's API. We
  chose record counts because every alternative answers a less
  interesting question.

**Why word-boundary regex.**
- `\bgraph\b` correctly skips "graphical" and matches both
  "graph" and "knowledge-graph" (the hyphen is a non-word char so
  the boundary holds).
- We use case-insensitive matching because the source cells mix
  "RAG", "rag", and "Rag" inconsistently. The visible chip label
  preserves the curated casing (e.g. "RAG", "KV", "MCP" stay
  upper-case in the UI) so the reader sees the canonical term.

**Why these 27 terms and not more (or fewer).**
- The cognitive-science quintet is the academic ground truth for
  memory taxonomy (Tulving 1972 + Squire & Zola 1996); skipping
  any of the five would beg "what counts as memory anyway".
- The mechanism group covers the four answer-storage primitives
  the catalog reliably distinguishes (parametric weights, latent
  activations, retrieval indexes, vector embeddings) plus the two
  structural alternatives (graph, knowledge-graph).
- The agent-era group is the vocabulary that emerged 2023-2025
  specifically to talk about LLM-agent memory ("agentic",
  "lifelong", "world-model", "persistent vs ephemeral").
- The architectural group is named systems/protocols/primitives
  ("bi-temporal", "key-value"/"KV", "attention", "RAG", "MCP")
  that should rise or fall as the surrounding plumbing matures.
- The emerging group is five hyphenated compounds we expect to
  spike in late-2025/2026 — tracked as a leading indicator.
- Excluded on purpose: generic words ("memory", "context",
  "model") that match nearly every record and would dominate the
  chart without signal; brand names ("Pinecone", "Letta") which
  belong on a separate "vendor mindshare" view, not vocabulary;
  and benchmark names (LongMemEval, LoCoMo, …) which have their
  own coverage matrix.

**Anyone-can-extend.** The chosen surface is intentionally a flat
array (`TRACKED_TERMS`) and a five-bucket grouping (`TERM_GROUPS`).
Adding "salient", "consolidation", "neuromorphic", etc. is a
one-line PR plus an entry below this one stating why it deserves a
permanent slot. We will resist growing past ~40 terms — the
visual budget for a line chart is ~10 simultaneous lines and the
term-selector chip grid becomes oppressive past four rows.

**YoY growth formula.** For each term, `termGrowth` finds the
most-recent year with non-zero count and the next-most-recent
year that had data (NOT strictly "year before" — a term that
went quiet for a year is still compared to its last active year,
which captures revivals). Growth = `(latest - prior) / prior`.
When `prior === 0` and `latest > 0` we return `+Infinity` and
the UI renders "new" rather than a number — a term that just
appeared has no meaningful percentage.

**Empirical sanity at the time of writing** (502 parseable
records, ~23 active quarters):
- Fastest-growing 2024→2025: agentic (+550%), procedural
  (+250%), hierarchical (+175%), semantic (+157%), parametric
  (+150%).
- Declining: knowledge-graph, world-model, ephemeral,
  bi-temporal, key-value, in-context all went to zero in 2025
  (low baselines — interpret with caution).
- True newcomers (first seen 2024+): lifelong, ephemeral.
- Exploded specifically in 2025: agentic (2→13), procedural
  (2→7), MCP (6→10) — all consistent with the agent-era
  vocabulary turn.

**Reversal cost.** Low. All logic in
`web/src/lib/analyses/vocabulary.ts` (pure helpers) and the
presentational page at
`web/src/routes/analyses/vocabulary/+page.svelte`. Changing the
counting rule to occurrence-based is a 5-line change in
`countByQuarter`; changing the term list is one constant edit.
Changing the bucket axis (quarter → year) needs a rewrite of the
SVG geometry but not the helper API.

---

## 2026-05-07: Benchmark coverage matrix — canonicalisation + source priority (Analyses)

**What.** Issue #24 ships `/analyses/benchmarks` — a matrix of
systems × headline benchmarks with the score in each cell. Three
non-obvious decisions are documented here so future maintainers
don't have to re-derive them.

**(1) Canonicalisation rules.** The corpus uses several aliases for
the same benchmark. We collapse them at extraction time:

| Canonical | Aliases matched |
|---|---|
| `LongMemEval` | `LongMemEval`, `LongMemEval-S/M/L`, `LMES`, `LME` (word-boundary), `LongMem-Eval` |
| `LoCoMo` | `LoCoMo`, `Lo-Co-Mo` |
| `BABILong` | `BABILong`, `BABI-Long` |
| `ConvoMem` | `ConvoMem` |
| `RULER` | `RULER` (no aliases — uppercase only) |
| `MemoryAgentBench` | `MemoryAgentBench` (the corpus uses this name; the issue's "MemoryBench" was the suggested alias but the only published variant in the catalogue is the AgentBench fork) |
| `ALFWorld` | `ALFWorld`, `AlfWorld` (mixed casing in source) |
| `ScienceWorld` | `ScienceWorld`, `SciWorld` |
| `SWE-bench` | `SWE-bench`, `SWE-Bench`, `SWE-bench-Verified` (Verified collapsed because reporting populations are nearly disjoint) |
| `MMLU` | `MMLU` plus `CMMLU` (Chinese variant — methodologically equivalent for coverage purposes) |
| `BrowseComp` | `BrowseComp`, `BrowseComp-ZH` |

`MemoryAgentBench` vs the "MemoryBench" the issue requested:
inspection of the corpus showed no records using the literal string
"MemoryBench"; the catalogued variant is "MemoryAgentBench". We
shipped the actual corpus name and noted the discrepancy here so
future copy-edits don't silently merge incompatible benchmarks.

**(2) Extract-from-perf-vs-claims priority.** Both `cells.perf.value`
and `cells.claims.value` regularly mention benchmark names. They
serve different purposes:

- `perf` is the curated headline — short, one-line, score-first
  ("74.0% LoCoMo 83.2% LMES"). Always score-bearing.
- `claims` is the marketing / paper-abstract prose, often
  multi-paragraph. Mentions the benchmark by name but may not carry
  a comparable score; also frequently references benchmarks the
  system was *evaluated against* but didn't headline.

We always prefer `perf` when both mention a given benchmark. If
`perf.status !== 'real-data'` or `perf.value` starts with the corpus
sentinel "no public benchmark scores found", we fall back to
`claims` for that record. The `cells` map carries a `source: 'perf'
| 'claims'` discriminator so we can visualise the split in the UI
(claims-sourced cells get a thin blue left border).

**(3) Score-extraction heuristic.** Cell values are free-text. We
match a benchmark name, then scan ±30 chars for a leading
`[+-~]?\d[\d.,]*[%|pp|x|F1|EM|bpc|ppl|poi]?` token, preferring the
nearest one *before* the benchmark name (corpus convention is
"score benchmark", e.g. "74.0% LoCoMo"). When no parseable score is
adjacent we record a presence-only mention (rendered as a check).
Delta-style scores (`+18.7pp`, `-15.3%`) are kept but flagged
non-comparable — the matrix renders them italic and excludes them
from per-column heat scaling, so "+48% LoCoMo relative" doesn't
dominate the colour ramp against absolute scores like "74.0% LoCoMo".

**Why.** The user's prior research surfaced that memory-system
papers often pick *domain* benchmarks (GAIA for agentic, WebArena
for web, SWE-bench for coding) over *memory-specific* benchmarks
(LongMemEval, LoCoMo). The analyses page exposes this by tagging
each benchmark and showing memory-vs-domain coverage side by side.
Canonicalisation is foundational — without aliasing LMES → LongMemEval
the headline benchmark loses half its reported population to spelling
drift.

**Numbers (May 2026 catalog).** 25 distinct benchmarks tracked;
90 systems with at least one reported score; top-5 by coverage:
LoCoMo (29 systems), LongMemEval (16), GAIA (11), HotpotQA (9),
ALFWorld (7). Memory-specific systems: 50; domain-specific
systems: 46; intersection: 6 — only 6 systems report on both
camps, confirming the divide the user predicted is visible in
the data.

**Options rejected.**
- *Take scores only from `perf`.* Drops ~10 systems that only mention
  benchmarks in `claims` (typically vendor pages where perf is
  status=`no-data` but the marketing copy claims a benchmark win).
- *Pull from `vendor-benchmarks` cell too.* That column is even
  noisier (vendor self-report disclaimers); presence-only signal
  there would inflate adoption numbers misleadingly.
- *Synthesise a normalised "score 0-1" per benchmark.* Most
  benchmarks have different score scales (F1 vs accuracy vs pass@k);
  cross-row normalisation would conflate metric units. Per-column
  heat (rank within column) is the right level of comparison.

**Reversal cost.** Low. The whole helper module is ~300 lines, the
canonicalisation list is a single array, and the UI consumes a
narrow `{systems, benchmarks, cells}` shape. To add or rename a
benchmark: edit `BENCHMARKS` in `web/src/lib/analyses/benchmarks.ts`,
optionally add it to `MEMORY_BENCHMARKS` if it's memory-specific.


---

## 2026-05-07: Influence-vs-adoption upgrade — density rendering and threshold rationale (Analyses)

**What.** Upgrade #22 ships `/analyses/influence` with a narrative
header, methodology callout, tier+section filters, visible median
lines, per-quadrant "so what" cards, and a hex-bin density underlay
on top of the existing radial jitter.

**(1) Density-vs-jitter choice: BOTH.** The brief offered either
hex-bin OR radial jitter for the long tail. We landed on BOTH, with
different jobs:

- *Radial jitter* (already in v1) keeps every record individually
  addressable — hoverable, clickable, with a tooltip. That matters
  for a chart whose whole job is to let the reader drill into named
  systems. Pure hex bins would lose this — a hex of "47 records" is
  a number, not a place you can click.
- *Hex-bin underlay* (new) restores the at-a-glance shape of the
  cloud. With jitter alone, 487 marks at ~350pacity still read as
  visual noise — hard to tell whether the corner is "many records"
  or "many overlapping marks at the same spot". A faint translucent
  hex grid (orange, opacity 0.06-0.40 keyed to per-cell count) under
  the markers gives the reader the density signal without burying
  the individual marks.

We restrict the hex grid to tail-quadrant points only. Hex-binning
the high-axis outliers would wrap big hexes around lone points and
lie about density there. The grid is flat-top hexes of pixel radius
14, chosen so ~8-12 hexes span the tail region; bigger hexes lose
resolution, smaller ones look like square pixels.

*Why hex over square bins:* flat-top hexes tile without the
orthogonal-grid artefacts that make square bins look stair-stepped
at low cell counts. The cell aspect ratio is closer to circular, so
"near" reads naturally.

*Why not d3-hexbin:* we already pay for d3 nowhere else in the
bundle (~30KB gzipped). The math is short: a `Map<col:row, count>`
over snapped pixel coords plus a 6-vertex polygon-points string.
We hand-rolled both as exported pure functions in `influence.ts`
(`hexBin`, `hexPolygonPoints`) so they remain unit-testable from
node without spinning up Vite.

**(2) Threshold rationale (revisited).** The brief asks us to make
the cutoff choice explicit. We use the **non-zero median** on each
axis (currently 2 cites, 1 integration), with **strict greater-than**
for the high side. Three knobs were considered:

- *Population median*: always 0 because >900f the corpus has zero
  inbound edges of either kind. Cutoff sits on the axis; quadrant
  partition is degenerate.
- *Non-zero median* (chosen): the median *among records that have
  any signal at all*. Reads naturally as "above median among the
  records that have any inbound graph reach", which is the right
  partition for a "look at the corners" chart.
- *Fixed hard cutoff* (e.g. ≥3 on each axis): brittle to corpus
  growth. As new edges land, a fixed cutoff would either
  silently inflate "Both" or silently empty it. Non-zero median is
  self-adjusting.

Strict greater-than (`p.citesIn > citesCut`, not `>=`) so a record
at the cutoff stays in the lower quadrant. That matches the visual
intent — being above the threshold means *demonstrably* above
median, not tied. Affects mainly `dreamerv3` (3 cites, 1 integ at
time of writing) which lands in "orphan" rather than "Both" under
this rule.

When the filter narrows the set below 8 points, we fall back to the
GLOBAL non-zero median to avoid a degenerate state where every
remaining point lands in "Both" because the local median collapsed
to 0/0.

**(3) Headline finding foregrounded.** The v1 chart had only 1
point in "Both" out of 523 records. That is the headline — academic
citation and commercial integration are essentially **orthogonal**
at this corpus stage. We surface this as `HEADLINE_FINDING` in the
narrative header rather than leaving it to be inferred from a
sparse corner. The most striking single-point demonstration: Mem0
leads the integration axis with 12 inbound integrations and zero
inbound cites (research orphan-of-the-other-direction); the only
system actually surviving the "Both" cut is zep-graphiti (4c/3i).

**(4) Cross-view drill links.** Tooltip and per-quadrant cards link
to: (a) main table scoped to that system via `?q=`, (b)
`/analyses/survivorship` (anchor-less — survivorship view does not
yet emit per-record DOM ids; would fail SvelteKit prerender
link-check), (c) `/analyses/forecast`. When survivorship grows
per-record anchors, `survivorshipHref(p)` upgrades to
`#${id}` in-place.

**Reversal cost.** Low. Density is `tailHexes` derived state in the
route; removing it is deleting one `{#each tailHexes}` block. Filter
mechanism is two `$state<Set<...>>` declarations plus the pure
`filterPoints` helper. Quadrant copy is `QUADRANT_COPY` in
`influence.ts` — single object literal to edit.


---

## 2026-05-07: Lineage forecast upgrade — prediction intervals, low-N gating, editorial watch notes (Analyses)

**What.** Upgrade #27 ships `/analyses/forecast` with a narrative
header, a methodology callout, a "so what" interpretation card,
filters (kind / curated-vs-auto / minimum-N), drill-down links to
`/lineages?lineage=<id>` and the main table, **honest prediction
intervals** computed from inter-arrival standard deviation, **low-N
gating badges** that visually de-emphasise fragile projections, and a
hand-curated **"what to watch for"** editorial paragraph for the three
seeded lineages.

**(1) Prediction-interval methodology.** For each lineage we list its
dated members descending by quarter, compute the mean inter-arrival
gap (`cadence_quarters`, with a 0.5-quarter floor so same-quarter
clusters don't collapse the average), and now also compute the
**population standard deviation** of those same (floored) gaps
(`cadence_stddev_quarters`). The "next expected" date is rendered as
`YYYY-Qn ± X quarters` where X = `Math.max(1, round(stddev))`. We use
the *population* form (divide by N, not N-1) because the gap series
is the complete observed history, not a sample; at N=2 intervals the
sample form blows up. The interval is one σ, not two — at these
sample sizes (typically 2–4 gaps) two σ would saturate at "± 5
quarters" for every card, which is uninformative. The low-end of the
interval is clamped to never precede the most-recent member's
quarter (saying "next drop expected before the most-recent member"
is incoherent for a forward projection).

**(2) Low-N badge rules.** Two thresholds, both visible to the
reader:

- `low_n` when `members_total < 5`. Renders a yellow **small sample**
  badge and dims the next-expected line (opacity 0.55, struck-through
  with a wavy line) plus an inline "directional only" note. The card
  still shows the projection — we want the user to *see* the number
  and *feel* the warning, not have the number disappear.
- `insufficient_data` when `cadence_intervals < 3` (i.e.,
  `members_dated < 4`). Renders a red **no cadence forecast** badge,
  *removes* the projected-date block entirely, and replaces it with
  an "INSUFFICIENT DATA — fewer than 3 inter-arrival gaps. Watch the
  leading edge below" callout. Below 3 gaps, the cadence-plus-stddev
  is a single-point estimate that can swing by 6+ months from one
  added paper; suppressing the date entirely is more honest than
  surfacing it with caveats.

Thresholds were chosen by the rule of thumb that you need ≥3
samples to estimate a mean *and* a spread without the spread being
dominated by one observation. They are exposed as `low_n` /
`insufficient_data` booleans on `LineageForecast` so the page's
filter slider (`minN`) and badge logic are decoupled.

**(3) Editorial "what to watch for" content — disclaimer.** Three
of the eight lineages (the curated ones: RSSM, Graph-RAG,
Files-as-memory) carry a hand-written 1–2 sentence "watch note":

- *RSSM:* watch for the first commercial spinoff — academic-dense,
  T1-product-empty.
- *Graph-RAG:* watch for hybrid retrieval at scale — papers stay
  below 10M entities.
- *Files-as-memory:* watch for cross-tool standardisation — 30+
  implementations of the same pattern can't continue without a
  shared format.

These are **interpretive observations, not algorithmic outputs**.
They live in a single `WATCH_NOTES` object in
`web/src/lib/analyses/forecast.ts` keyed by lineage id (or anchor
record id as a fallback), and are rendered into a clearly-labelled
"What to watch for (editorial)" section on the card with a distinct
yellow left-border so the reader sees the change in voice from
algorithmic ("cadence ≈ 6mo") to editorial ("watch for the first
commercial spinoff"). Auto-discovered lineages get no watch-note by
default; the editorial bar is high and adding a note requires a code
change. We considered keeping these in a sibling data file
(YAML / JSON) but the editorial set is small enough (3 keys today,
maybe 8 long-term) that the indirection isn't worth it.

**(4) Adjacent-lineages observation.** In the current dataset
(8 lineages from `detectLineages({topN: 8, minSize: 3})`), zero
cross-lineage edges exist of any type — `findAdjacent` returns an
empty list for every card. This is mechanistic: the union-find pass
in `detectLineages` absorbs every record connected by a descent edge
into the same component, so by construction there are no descent
edges between auto-discovered lineages. The curated pattern lineage
(Files-as-memory) is built by section membership rather than edges,
and none of its members are linked to RSSM/Graph-RAG members by
*any* edge type in the current edge set. The `findAdjacent` plumbing
is preserved against future edge-type expansion (e.g. adding
`inspired-by` or non-influential cites as a soft-adjacency signal),
and the card section is conditional — empty `adjacent` arrays hide
the section entirely so the cards don't show a stub.

**(5) Drill mechanics.** The lineage name in each card title links
to `/lineages?lineage=<id>` (query param, not hash fragment — the
prerender link-checker validates hash fragments against rendered
DOM ids and would fail for ids not yet emitted by the `/lineages`
view, which is owned by an earlier read-only issue). Leading-edge
member buttons link to `/?q=<system-name>` exactly as before.
Adjacent-lineage chips are now *buttons* that scroll the target card
into view with a brief blue-border flash — within-page navigation
because the page already renders all cards.

**Numbers (May 2026 catalog).** 8 lineages detected. **4 small-sample
(N<5):** I-JEPA, FalkorDB, Qdrant, Milvus families. **2 insufficient
data (cadence intervals <3):** I-JEPA family (3 members, 2 gaps);
Milvus family (3 members, 2 gaps) — the date is hidden on both. The
three curated lineages (Files-as-memory N=33, Graph-RAG N=17,
RSSM N=5) all pass the gating, with Files-as-memory remaining the
fastest at ~6-month cadence. Adjacent-lineage pairs surfaced: 0
(see (4) above).

**Reversal cost.** Low. The new `cadenceStdDev` helper is ~15 lines;
`WATCH_NOTES` is a single object literal; the gating booleans
(`low_n`, `insufficient_data`) and the new fields on `LineageForecast`
are additive. To remove the editorial layer: delete `WATCH_NOTES`
and the `watch_note` field. To loosen the gating: change the two
threshold constants (`< 5` and `< 3`) in `forecastAll`.

---

## 2026-05-07: Survivorship Unknown-bucket subdivision

**What.** The `/analyses/survivorship` view's Unknown bucket — historically
the largest single category and visually dominant on the page — is now
split into FOUR sub-buckets, displayed as a stacked breakdown beneath the
top-row counters:

1. **Closed-source, internal status unknown** — proprietary products with
   no public release cadence. Common for T1 commercial vendors (Slack,
   Notion, Glean, Coral). Status: a limit of our signal, not a property
   of the system.
2. **OSS but signal-too-weak** — record has a GitHub presence (parsed
   from `gh`, `code-release`, or an OSS-licence string) but the catalog
   did not capture a parseable "last commit YYYY-MM" token. Status: fixable
   by deeper data collection.
3. **Newly created (< 6mo)** — `created` cell parses to a date within the
   last 6 months. Too new to assess freshness; the right framing is "wait
   and re-check at the next snapshot".
4. **N/A (research/benchmark-only)** — reserved for the rare T1/T2 row
   that has truly no operational signal (typically a benchmark/eval harness
   miscategorised as a product). T3+ rows already route to the `research`
   bucket, so this sub-bucket is usually 0.

**Why these four.** The user-research finding driving this view is that
the Unknown bucket reads as a failure when it's actually a signal limit.
A single grey block of "Unknown" tells the reader nothing about whether
the catalog could do better or whether the systems are simply unobservable.
Four sub-buckets make the structure visible:

- *closed-source* is the largest sub-bucket and STRUCTURAL — no data-collection
  effort can close it without a vendor publishing a changelog. The right
  caveat for users.
- *oss-weak-signal* is the sub-bucket the catalog itself can fix — listing
  it separately makes it actionable as a to-do for future iter rounds.
- *newly-created* is small but visually important: a 4-month-old system
  shouldn't sit alongside Slack as "we don't know if it's alive". It's
  alive; we just don't have enough lookback.
- *na* exists as a completeness slot; reserving the label avoids forcing
  the rare miscategorised benchmark into "closed-source" (which would be
  wrong).

**Routing rules.** In `subdivideUnknown(record, createdAgeMonths)`:

```
if createdAgeMonths in [0, 6]      → newly-created
else if hasGitHubPresence(record)  → oss-weak-signal
else                                → closed-source
```

`hasGitHubPresence` is a positive heuristic — checks `gh` / `code-release` /
`license` cells for github.com / gitlab / star-count patterns / an OSS-licence
string. Defaults to closed-source when no positive signal fires, because the
catalog skews commercial in the data-starved cells.

The `na` sub-bucket is reserved but never auto-assigned in v1; future hand-
curation could route specific benchmark records there explicitly.

**Options rejected.**

- *Three buckets (drop `na`).* Loses the reserved slot for the rare
  miscategorised row. Trivial to re-add but the slot does no harm and the
  prose is clearer with the explicit "N/A" option present.
- *Split by age cohort of `created`* (0-12mo, 1-3yr, 3-5yr, >5yr). Tested
  internally; this conflates two different things — closed-source age and
  catalog-gap age — and produced four roughly equal blobs that didn't tell
  the user anything actionable.
- *Single "Unknown" with a tooltip explaining the four reasons.* Hides
  the structure; users don't read tooltips on counts. The stacked bar
  forces the user to see the breakdown.

**Reversal cost.** Low. The four sub-buckets are an enum
(`UnknownSubBucket` in `$lib/analyses/survivorship.ts`); collapsing back
to "Unknown" is deleting the `unknownSub` field and the
`<section class="unknown-sub">` block in `+page.svelte`. The classification
data is preserved through the existing `Classification.unknownSub` field —
removing the UI doesn't lose any analytical state.

**Auxiliary upgrades in the same round.** Tier × section multi-select
filters (recompute every count); "so what" interpretation panel; per-section
proportion bar + aging-score ordering; active-cohort year-quarter histogram;
"abandoned-but-cited" promoted from a table at the bottom of the page to a
card grid foregrounded above the strips, with lineage labels resolved via
`detectLineages` in the loader. The view-specific upgrades are documented
in the page-level comments; only the Unknown subdivision rules warrant
this DECISIONS entry because the routing rules are non-obvious and likely
to be revisited.


---

## 2026-05-07: Vocabulary view v2 (upgrade #26) — small-N flagging + co-occurrence threshold

**What.** Round 2 of the /analyses/vocabulary view inverts how growth
numbers are presented. v1 led with percentages ("agentic +550% YoY",
"knowledge-graph -100%") that turned out to hide tiny absolute moves
(2 → 13 records, 1 → 0). v2 leads with the absolute "prior → latest"
pair on every per-term card and only renders the percentage as a
secondary line. Pairs where either side fails a small-N test are
visually demoted with a "small-N" pill so the eye doesn't reach for
them as headlines. The view also gained a cumulative-arrival mode, a
term × term co-occurrence heatmap, a first-appearance chronology
that separates newcomers from established terms, a stable-vs-novel
vocabulary-share table per year, tier/section filters, and a slide-in
drill panel listing every record that mentions a term (sorted by
recency).

**Why a small-N rule rather than just hiding the number.** Some readers
*want* the percentage even when N is tiny (they're tracking a fresh
arrival like "ephemeral" where 0 → 1 is genuine signal). Hiding it
loses information; demoting it preserves the signal while preventing
the small move from being a headline. The pill is also a teaching
move: it tells the reader "you should already know to discount this"
which builds the habit for any future numbers they see.

**Small-N threshold rule.** A growth percentage is flagged
`small-N` when ANY of:

1. `latestYearCount + priorYearCount < 5` — the two cells of the YoY
   ratio together don't carry enough records to make the ratio
   statistically meaningful;
2. `total < 5` — the term has fewer than 5 mentions across the entire
   catalog (a brand-new term where even the running total is small).

Threshold value: **5 records**. Rationale: at N=5 the noise floor on
a year-over-year ratio (assuming roughly Poisson arrivals at λ≈2-3 per
year) is ±50% on the ratio — i.e. a "+100% jump" sits inside the
noise. Anything below that is mostly luck of which quarter a paper
landed in. We picked 5 over 10 because the curated term set is
deliberately small (27 terms) and several intentionally-tracked
"emerging" terms (ephemeral, bi-temporal, working-memory) would be
hidden entirely under a stricter threshold, defeating the surveillance
purpose. The number is exposed as `SMALL_N_THRESHOLD` in
`web/src/lib/analyses/vocabulary.ts` for easy tuning.

**Co-occurrence threshold for cluster detection.** Co-occurrence pairs
are rendered as a 15 × 15 heatmap (top 15 terms by total mentions).
Cells where two terms appear together in at least **4 records** are
outlined in the accent colour as "cluster edges". Threshold value:
**4 records**. Rationale: with ~700 records and ~30 terms, random
co-mention noise is at the 1-2 record level (e.g. one paper happening
to mention "ephemeral" alongside "agentic" by accident). At 4 we
filter out doubletons and triples that would otherwise create false
clusters in the heatmap, while still surfacing genuine micro-clusters
like the architectural pair "KV + attention" (count = 4) that pass
the eye-test as real recipes. Exposed as `COOCCUR_THRESHOLD` in the
same helper module.

**Stable vs novel ratio.** The "vocabulary drift outside our curated
list" metric counts new records per year that mention ≥1 tracked
term (stable) vs records that mention 0 tracked terms (novel /
drifting). This is a record-count share, NOT a term-count share —
it answers "what fraction of new entries are written in vocabulary
we already track?" rather than "how much new vocabulary appeared?".
The latter would require a tokeniser + a stop-word list + a
frequency-vs-precedent comparison, all of which are out of scope
for a one-screen visualisation. Record-share is the right grain for
this view: rising novel share signals that the curated list is going
stale and warrants an update PR.

**Newcomer threshold.** First-appearance year ≥ **2024** marks a
term as a "newcomer". 2024 is "current year − 2" relative to the
catalog's terminal date (May 2026); the choice surfaces terms that
arrived during or after the agent-era inflection point and that the
field is still settling on. Hard-coded in the route (not the helper)
because tuning it is a UI display choice, not a data semantics one.

**Reversal cost.** Low. The helper module gained ~250 lines of pure
functions and the route grew a co-occurrence heatmap, ratio table,
and drill panel. To turn off the small-N badge: drop the `class:muted`
and the pill render block in `+page.svelte`. To tune thresholds: edit
two constants in the helper module. The co-occurrence matrix is
computed eagerly on every record-set change (~700 records × 27² pair
checks ≈ 510k regex tests / recompute); empirically <50ms on the
build host. If filters become very chatty we'd memoise on the
filtered record-id set.


---

## 2026-05-07: Archetypes view — exemplar naming, near-archetype clustering, gap prose (Analyses)

**What.** Upgrade #25 follow-up to `/analyses/archetypes` ships three
non-obvious algorithmic decisions that future maintainers should be
able to walk back if needed.

**(1) Archetype naming algorithm — three-tier.**

We pick a human-readable name for every archetype through a cascade:

  a. **Curated overrides** (`NAMED_ARCHETYPES` table, ~13 entries).
     Match by `fp.startsWith(pattern)` on a partial fingerprint prefix
     (typically the first 5 axes — storage · retrieval · persistence
     · update · unit). These cover the well-known recipes that have
     established names in the literature / product space (Mem0,
     ChatGPT-Memory, Qdrant, CLAUDE.md, Zep, knowledge-graph,
     static-RAG, hybrid-RAG, ExpeL, PKG-notes, state-space, plus the
     two "no-taxonomy" buckets for benchmarks/surveys). First match
     wins; order in the table matters.

  b. **Exemplar-driven names** for archetypes with ≥5 members that
     missed the curated table. The exemplar is the member with the
     highest `exemplarScore`:

         score = inboundIntegrations × 100_000
               + inboundCites         × 10_000
               + log10(funding $ + 1) × 1_000
               + (6 − tier)           × 100

     The name becomes `The {exemplar.name} recipe`. The five-member
     gate is deliberate — for n<5 the exemplar is a bad summary of
     the recipe (a single record's name doesn't represent the
     pattern well enough). The score's priority order
     (integrations >> cites >> funding >> tier) was chosen because:

       - inbound integrations are the strongest signal of "the
         system other systems plug into" — i.e. the de-facto
         standard for the recipe. Most curated overrides exist
         precisely because the canonical product has high inbound
         integration count.
       - cites carries the academic / research weight when no
         commercial integrations exist (e.g. ExpeL family).
       - funding is a coarse commercial-prominence signal that
         breaks ties on the long tail.
       - tier breaks remaining ties so a battle-tested T1 row beats
         a theoretical T5 row at equal funding/cites/integ.

  c. **Section-namesake fallback** for "pattern" archetypes whose
     fingerprint is dominated by `n/a` (≥5 of 7 axes). These are
     benchmarks, surveys, frameworks-without-memory — they have no
     taxonomy identity, so the section they cluster in is what
     gives them their name: `The {section} pattern`.

  d. **Axis-based synthesised fallback** for everything else:
     `{axis1} + {axis2} + {axis3} recipe`. Drops `n/a` and
     `unspecified` from the components. Used when the archetype is
     small (<5 members) and missed all curated patterns.

**Options rejected.**

- *Always exemplar-name, never curate.* Bad because the exemplar
  algorithm picks "Qdrant" for the vector-overwrite-chunk recipe,
  but Mem0 — the recognisable name for the EXTRACTION variant — has
  too few inbound integrations to win its own bucket. Curated
  overrides let us anchor the names readers expect even when the
  graph data says otherwise.
- *Use sub-section name as the namesake.* Tried it; sub-sections
  are too granular (often single-record). Top-level section is the
  right grain.
- *Generate names via LLM at build time.* Non-deterministic, hard
  to diff the analyses page over time, and unnecessary —
  template-driven naming is legible and stable.

**(2) Near-archetype clustering — Hamming-1, anchored to recurring
archetypes.**

For each singleton fingerprint we compute its Hamming distance to
every archetype with ≥2 members. Distance-1 singletons attach to
their closest anchor as a "near-variant"; distance ≥2 stays
unattached. Concretely (May 2026 catalog): 314 singletons →
**103 absorbed** as near-variants, **211 unattached**. The
effective long-tail count drops from 390 distinct fingerprints
to ~287 distinct shapes (76 recurring + 211 unattached).

**Threshold = 1 because:**

- Distance-1 is the most legible boundary. "This system is the
  canonical recipe except for one axis (governance, etc.)" is a
  one-sentence description a reader can hold in their head.
- Distance ≥ 2 starts being a genuinely different shape — two axis
  flips can change three semantic properties at once (e.g. flipping
  both `persistence` and `update` turns "long-term/extraction" into
  "session/replacement", which is no longer the same recipe at all).
- Threshold = 2 would absorb too many singletons into archetypes
  they don't belong with, polluting the per-card variant lists.

**Anchor set = recurring (n≥2), not top-N**, because many singletons
are distance-1 from a small-but-not-tiny archetype further down the
list. Limiting anchors to top-12 would leave most singletons
unattached. The route's UI shows each anchor's variants only on the
anchor's card, so the user only sees variants of the top-12 — but
the absorption count includes every recurring archetype.

**(3) Gap-candidate prose — deterministic, template-driven.**

Each white-space candidate gets a 2-3 sentence description:

    "The {axis1} · {axis2} · ... · {axis7} fingerprint has 0
     members other than {selfName}; every individual axis value is
     mainstream but this specific combination has not been built
     twice. Closest existing: {neighbour} at Hamming-1 (differs on
     {axis}). Also nearby: {neighbour2} ({axis2}), {neighbour3}
     ({axis3}). A product filling this gap could be framed as
     '{neighbour} with {value} on the {axis} axis'."

Deterministic prose was chosen over LLM-generated prose because:

- The page is built into static HTML at deploy time; reproducible
  prose makes the analyses page diffable across commits ("did the
  ranking change, or did the description?").
- The closest-existing system at Hamming-1 is the most actionable
  fact in the description; everything else is scaffolding.
  Template prose foregrounds that fact reliably.
- LLM prose at build time would introduce non-determinism and a
  build-time dependency on an inference endpoint.

The closest-existing lookup is bounded at 3 neighbours, scanned
linearly over records (699 × 7 = ~4.9k comparisons per gap × 8
gaps = ~39k ops). At this scale that's <5ms total, well below the
prerender budget.

**Numbers (May 2026 catalog).** 699 records · 390 distinct
fingerprints · top-12 cover 34.0% of catalog · 314 singletons
(45.0%) · Hamming-1 absorbs 103 singletons (32.8% of singletons)
into 76 recurring archetypes, leaving 211 genuinely bespoke
designs. Top archetype: the no-taxonomy bucket (164 members —
non-memory frameworks/surveys/infra). Top memory archetype: the
CLAUDE.md recipe (11 members — file-backed agent memory).

**Reversal cost.** Low. All logic lives in
`web/src/lib/analyses/archetypes.ts` (pure helpers, no DOM, no
Svelte). To change:

- Naming priority order → edit the `exemplarScore` weights in
  `archetypes.ts`.
- Hamming threshold → pass `nearThreshold: 2` to `buildBundle()`
  in `+page.svelte` (or change the default in `buildBundle`).
- Gap prose template → edit `composeGapProse()`. Single function,
  ~15 lines, no callers outside the module.
- Curated names → edit `NAMED_ARCHETYPES`. First-match wins, so
  order entries from most-specific to least-specific.

---

## 2026-05-07: Upgrade #24 — benchmarks parser tightening, leaderboards, coverage tiers

**What.** Round 8 upgrade of `/analyses/benchmarks`. The prior version
showed presence (checkmarks) for most cells because the proximity
heuristic was too loose to extract numeric scores reliably. This pass
replaces the parser with a tiered priority strategy, surfaces per-cell
scores in the matrix, and adds three new analytical lenses: per-benchmark
leaderboards, coverage tiers (well-covered / emerging / too-narrow), and
a stacked memory-vs-domain split.

**Parser improvements** (`web/src/lib/analyses/benchmarks.ts`).

1. *Tiered score-shape priority.* Five-step lookup in order:
   (1) unit-suffixed score in left window;
   (2) unit-suffixed score in right window;
   (3) bare decimal in left window (perf only);
   (4) bare decimal in right window (perf only);
   (5) short bare int adjacent (≤6 chars, perf only).
   Claims mode skips steps 3-5 because claims prose contains incidental
   numbers (pass@k, model versions, "10x larger") that look score-shaped
   but aren't. Claims parser coverage drops from ~50% naive to ~12%, but
   the surviving 12% are real scores (genuine `+18.7pp` deltas, etc.)
   rather than false positives like "GAIA 3" (interpreted as `pass@3`).

2. *Benchmark-boundary clipping.* The corpus convention is
   `{score} {benchmark}`, so multiple benchmarks per cell look like
   `30 ConvoMem 91.6 LoCoMo`. The score search now clips the right
   window at the next benchmark mention AND drops the trailing score
   that precedes it (which belongs to that next benchmark). The left
   window is clipped at any prior benchmark mention but keeps its
   leading score (which IS our score by the corpus convention).

3. *Removed `x`/`×` from the unit-suffix list.* These multiplier suffixes
   produced false positives like "matches 60x larger models" → score=`60x`.
   The legitimate uses in the corpus (token-reduction multipliers, model
   scale comparisons) aren't benchmark scores.

4. *HTML-aware preprocessing.* `stripHtml()` is applied before scoring,
   so iter-level cells with `<span class="signal-num">…</span>`,
   `<br>`, `<em>`, etc. parse correctly even though the current build
   has these stripped already. Forward-compatible.

5. *Year rejection.* Bare 4-digit tokens matching `^(19|20)\d\d$` are
   rejected as score candidates (years, not scores).

**Parser self-report.** The methodology callout in the rendered view
exposes the parser's own success rate: **93%** of perf-cell mentions
yield a score (69/74); **12%** of claims-cell mentions do (6/50). The
asymmetry is intentional: perf is curated headline data and the
unit-suffix-or-bare-int strategy hits hard there; claims is marketing
prose and we'd rather show a presence ✓ than mislabel a number.

**Heat-color scheme.** Each benchmark column gets independent min/max
of *absolute* (non-delta) scores. A cell's score is rank-mapped to a
0..1 strength `t = (n - min) / (max - min)` and colored as
`hsl(30 (25+t*55)% (16+t*14)% / 0.92)` — a single warm-amber hue with
saturation and lightness modulating together. Delta scores
(`+18.7pp`, `-15.3%`) get italic styling and no shading because they
aren't comparable across baselines. Columns with fewer than 2 absolute
scores are unshaded (no meaningful range).

**Memory-vs-domain visualisation.** Promoted from a 3-stat callout to a
single horizontal stacked bar (memory-only / both / domain-only) plus
three sortable bucket columns underneath. The bar uses the same hue
palette as the heat shading (amber for memory, slate for domain, mixed
for both) so the family colors are consistent across the page. The
2x2 layout was considered and rejected: the system count in "both" is
small (6 systems vs ~40 in each of the other two), and a 2x2 would
waste half its quadrants on the trivial "neither" bucket.

**Coverage tiers.** Benchmarks are split into three groups by reporter
count: **well-covered** (≥10 systems), **emerging** (5-9), and
**too-narrow** (<5). The banner at the top of the page surfaces this
classification, making it obvious which benchmarks are credible
comparison axes (LoCoMo at 29, LongMemEval at 16, GAIA at 11) and
which are effectively single-paper artefacts (ConvoMem at 2,
PersonaBench at 1, ImplicitMemBench at 1). The "too-narrow" tier is
the analytical headline of the page — it's why the ConvoMem callout
in the page narrative says ConvoMem is under-adopted.

**Tier filter.** Multi-select for T1-T5 system tiers. The matrix and
all downstream analytics react to the filter; the parser stats and
coverage-tier banner are computed on the full population (those are
fixed properties of the data, not view state). The filter cannot reach
zero active tiers — clicking the last active tier is a no-op — to
avoid an empty view that hides the filter affordance.

**Drill-down.**
- Click a cell or system row → main table filtered to that record
  (`?q=<encoded-name>`).
- Click a column header → in-page anchor to the leaderboard card for
  that benchmark. Every matrix column has a leaderboard, so the link
  always resolves (this is also enforced by the prerender check —
  SvelteKit `handleMissingId` will fail the build otherwise).

**Headline numbers as of 2026-05-07.**
- LongMemEval #1: MemPalace 96.6% (T2)
- LoCoMo #1: ByteRover 92.2% (T2)
- BABILong #1: ARMT 79.9% (T4)
- ConvoMem #1: Mem0 30 (T1) — single-system benchmark, too narrow
- GAIA #1: Memento 87.88% (T4)
- Memory-only systems: 44; both families: 6; domain-only: 40.
  Confirms the prior observation that memory papers rarely cross-list
  on the memory-specific axes their architecture would seem to target.

**Reversal cost.** Low. The parser is a pure module; the route reads
its outputs. To revert to checkmark-only display, edit the matrix cell
template to drop `{cell.score || '✓'}`. To turn off heat coloring,
remove the `style={heatStyle(…)}` attribute. To remove tier filtering,
delete the `activeTiers` rune and inline the unfiltered `allScores` as
`scores`. To adjust coverage-tier thresholds, edit the two constants
in `coverageTiers()` (currently 10 and 5).

## 2026-05-12: Edge-graph refresh against the 699-record catalog — candidate-lineage verdicts

**Context.** Round 7 added 176 records / 6 sections. `build_edges.py`
had not been re-run since the addition. analysis.md v2 surfaced four
candidate lineages with sparse evidence: SSM, RLHF, Embedding, and
Agent-protocol — plus the previously "partial 3-node" Stanford
agents finding. This pass re-runs cell-mining + S2 citation pulls and
records the resulting lineage status per candidate.

**Numbers.** Total edges 278 → 298 (+20). All 20 new edges are
influential `cites` from S2; no new cell-mined or cross-ref edges.
Top-10 hubs largely unchanged; **GraphRAG (Microsoft) +3** (now tied
with Mem0 at 12 inbound). **Mem0 stays at 12** — the new
agent-framework rows did not cleanly emit Mem0 inbound edges because
they are cross-ref-CSV entries that haven't been added (Round-7
ingest did not refresh `.agent-results/data-5-cross-references.csv`).

**Verdicts.**

- **Stanford agents** — was "partial 3-node". The catalog actually
  carries two duplicate records for the Park et al. paper; the
  primary one is absorbed into the 148-node research-paper
  mega-component (7 inbound influential cites), the duplicate is
  isolated. No discrete 3-node lineage exists today. **Status:
  dissolved** into the mega-component. If we want it as a named
  family it must become a curated seed with depth-limited BFS.

- **SSM (Hyena → Mamba → Mamba-2 → Jamba → RWKV-7)** — 6 members in
  the catalog. **Zero** inter-member descent edges. Hyena / Mamba /
  Mamba-2 are absorbed into the mega-component (because they cite
  shared ancestors like Transformer-XL, not because they cite each
  other influentially). Jamba (2 duplicate records) and RWKV-7 are
  isolated singletons. **Status: still candidate / sparse.** The
  papers do reference each other (Mamba paper cites Hyena, Mamba-2
  cites Mamba), but S2 marks those `isInfluential=false`, so our
  descent-edge filter rejects them. To promote, we would need either
  (a) curated-seed entry in `lineages.ts` with `succeeds`-edge
  curation, or (b) widen the descent filter to include
  `isInfluential=false` within a same-section bound.

- **RLHF (LoRA → QLoRA → DPO → GRPO → TRL / OpenRLHF)** — 6 members
  in the catalog. **2 inter-member descent edges**:
  `QLoRA cites LoRA` and `GRPO cites DPO` (both influential). DPO /
  GRPO / MPO / SeAgent form a **4-node auto-detected component**.
  LoRA / QLoRA sit inside the mega-component. TRL and OpenRLHF are
  isolated infrastructure records (no S2 paper). **Status: still
  candidate.** The DPO sub-cluster is on the verge of qualifying as
  a 4-node auto-lineage but is too small to overshadow the larger
  auto-discovered families; the LoRA / QLoRA pair has lost
  resolution by collapsing into the mega-component. A curated seed
  ("Preference-optimisation family") anchored on DPO would cleanly
  surface this lineage if we want to highlight it.

- **Embedding (Sentence-Transformers → BGE → GTE → Nomic →
  Mixedbread)** — 6 members. **Zero** inter-member descent edges.
  BGE-M3 (the one paper-form member) is in the mega-component
  (citing Sentence-Transformers ancestors); the other 5 are isolated
  product singletons with no incoming or outgoing descent edges.
  **Status: sparse — promotion blocked by 5 isolated singletons.**
  Each non-paper product (SBERT site, BGE-BAAI HF page,
  GTE-AlibabaNLP, Nomic Embed, Mixedbread) would need either a
  cross-listings entry or a curated-seed-by-section rule. Same
  category as the existing `files-as-memory` pattern lineage.

- **Agent-protocol (MCP spec → A2A → AGNTCY)** — 3 members.
  **Zero** inter-member descent edges. All three are isolated
  singletons — none has an S2 paper, none mentions another by name
  in a way the cell-miner picks up. **Status: sparse, as expected.**
  Protocols don't fit the descent model; if we want to surface them
  as a family it must be a pattern-style curated seed (sections-based
  expansion, like `files-as-memory`).

**Where the persistent gap lives.** `build_edges.py` still discards
40 cell-text candidates and 17 cross-ref CSV rows. The largest
single recurring miss is **LangGraph ambiguity**: the catalog now
has two LangGraph records (`langgraph-orchestration` and
`langgraph-persistence`), so any cell that says "uses LangGraph"
returns `ambiguous-substring` from the resolver and the edge is
dropped. The fix is a context-aware alias rule (memory-focused
sections → `langgraph-persistence`); deferred.

**Reversal cost.** Zero. `web/landscape.edges.json` is fully
regenerated by running `python3 scripts/build_edges.py` followed by
`python3 scripts/fetch_citations.py` (cache-warm, runs in ~75s). To
revert to the prior 278-edge state, restore the file from the
previous commit. The S2 cache entries can stay either way — they're
read-only inputs.

**Reproduction.**
```
python3 scripts/build_edges.py
python3 scripts/fetch_citations.py
```
Both honour `BUILD_EDGES_GENERATED_AT` / `FETCH_CITATIONS_GENERATED_AT`
to `2026-05-07T00:00:00Z` and produce byte-identical output on
re-run with warm cache.
