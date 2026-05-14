# Schema spec — `landscape.json` and `landscape.edges.json`

This document is the **source-of-truth shape** for the structured catalog
that `extract.py` (issue #2) emits and that every Phase 2-5 consumer reads.

It locks in:

- top-level structure of both files
- the exhaustive per-record field set
- the four-state `status` enum semantics
- the nine edge-type vocabulary
- validation rules a build step (or future JSON Schema) must enforce

If something downstream is unclear, the answer should be reachable from
this file. If it isn't, edit *this file* (and the corresponding
`docs/DECISIONS.md` entry) before adapting the consumer — drift between
the spec and the data is the failure mode this doc exists to prevent.

---

## 1. Top-level structure

### `landscape.json`

```json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "2026-05-07T00:00:00Z",
  "sourceHtml": "landscape.html",
  "records": [
    { "id": "...", "name": "...", "tier": 1, ... },
    ...
  ]
}
```

**Recommendation: an object with a `records` array, not a bare array.**

Justification:

1. We need a place to put metadata (`schemaVersion`, `generatedAt`,
   `sourceHtml`) without polluting record shape.
2. A `schemaVersion` is essential the first time the schema breaks
   compatibly — consumers can branch on it.
3. SvelteKit `+page.server.ts` loaders prefer named keys to anonymous
   top-level arrays for readability.
4. Bare-array JSON cannot grow new top-level fields without becoming an
   object anyway; pay the cost up front.

The `records` array order is not significant — consumers must key by
`id`. Producers should still emit it in a stable order (recommended:
sorted by `id` ASC) for diff-friendly commits.

### `landscape.edges.json`

```json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "2026-05-07T00:00:00Z",
  "edges": [
    { "source": "...", "target": "...", "type": "cites", ... },
    ...
  ]
}
```

Same rationale. `edges` is a flat array; multiple edges between the same
`(source, target)` pair are allowed if the `type` differs.

---

## 2. Per-record fields (`records[*]`)

| Field      | Type                                | Required | Notes                                                        |
|------------|-------------------------------------|----------|--------------------------------------------------------------|
| `id`       | string                              | yes      | Stable slug. See [§2.1 Slug algorithm](#21-slug-algorithm).  |
| `name`     | string                              | yes      | Display string from the `<a>` text inside `td.name`.         |
| `tier`     | integer 1-5                         | yes      | See [§2.2 Tier semantics](#22-tier-semantics).               |
| `url`      | string \| null                      | yes      | `href` of the `td.name <a>`, or `null` if no link.           |
| `sections` | array of section-membership objects | yes      | At least one element. Exactly one with `primary: true`.      |
| `taxonomy` | object with 7 axis arrays           | yes      | All 7 keys present. See [§2.4](#24-taxonomy).                |
| `cells`    | object keyed by column-name         | yes      | All ~75 column keys present (with `not-applicable` if N/A).  |

Records are JSON objects; field order is not significant but producers
SHOULD emit fields in the order shown above for diff-friendliness.

### 2.1 Slug algorithm

The `id` is a deterministic slug, generated as follows:

1. **Pick a slug source.** In priority order:
   - If the `<a href>` of `td.name` is an arXiv URL
     (`arxiv.org/abs/<id>` or `arxiv.org/pdf/<id>`), the slug source is
     `<name-slug>--arxiv-<arxiv-id>`.
   - Else if the `<a href>` is a GitHub URL
     (`github.com/<owner>/<repo>`), the slug source is
     `<name-slug>--gh-<owner>-<repo>`.
   - Else if a URL exists, the slug source is
     `<name-slug>--<host-slug>` where `<host-slug>` is the URL's
     registrable domain with dots replaced by `-` and any leading `www-`
     stripped (e.g. `mem0.ai` → `mem0-ai`).
   - Else (no URL), the slug source is `<name-slug>` alone.

2. **Compute `<name-slug>`** from the display name:
   - Lowercase.
   - Replace any run of non-`[a-z0-9]+` characters with `-`.
   - Strip leading and trailing `-`.
   - Collapse runs of `-` to a single `-`.
   - Trim to first 64 chars on a `-` boundary if longer.

3. **Compute `<arxiv-id>`** by stripping the version suffix
   (`v1`, `v2`, …) and replacing `.` with `-`
   (so `2504.19413v2` → `2504-19413`).

4. **Collision rule.** If two records would collide on `id`, the
   extractor MUST append `-2`, `-3`, … to the second, third, …
   occurrence in document order, and emit a warning to stderr. Real
   collisions must be investigated manually — the slug is meant to be
   unique by construction, so a collision usually means the source
   data is genuinely a duplicate.

Examples:

| Name                                   | URL                                       | id                                                 |
|----------------------------------------|-------------------------------------------|----------------------------------------------------|
| Mem0                                   | `https://mem0.ai/`                        | `mem0--mem0-ai`                                    |
| Letta / MemGPT                         | `https://www.letta.com/`                  | `letta-memgpt--letta-com`                          |
| ATLAS (memory paper)                   | `https://arxiv.org/abs/2505.23735`        | `atlas-memory-paper--arxiv-2505-23735`             |
| Atlas (Meta-AI retriever)              | `https://arxiv.org/abs/2208.03299`        | `atlas-meta-ai-retriever--arxiv-2208-03299`        |
| AriGraph                               | `https://github.com/AIRI-Institute/AriGraph` | `arigraph--gh-airi-institute-arigraph`          |
| `CLAUDE.md` (Claude Code memory)       | (no link — Anthropic docs reference)      | `claude-md`                                        |

The slug algorithm is the **interlock that prevents the "two systems
share a name" bug** identified in `docs/DECISIONS.md#stable-ids-decoupled-from-display-names`.
Changing the algorithm post-extraction is High reversal cost — it
re-keys every edge.

### 2.2 Tier semantics

`tier` is an integer 1-5. The mapping below is the canonical definition.
The HTML encodes it via `tr.row-t<N>` class on each row.

| Tier | Class       | Meaning                                                                                       | Rough population              |
|------|-------------|-----------------------------------------------------------------------------------------------|-------------------------------|
| 1    | `row-t1`    | **Battle-tested.** Real customers, real revenue / measurable enterprise adoption.             | ~30 systems                   |
| 2    | `row-t2`    | **Established / mature OSS.** Significant GitHub traction, clear maintainer team, in production at known users. | ~80 systems  |
| 3    | `row-t3`    | **Peer-reviewed.** Published at a recognised venue (ACL, EMNLP, NeurIPS, ICLR, …) with code. | ~100 systems                  |
| 4    | `row-t4`    | **Preprint.** arXiv (or similar) with implementation but not yet peer-reviewed.               | ~250 systems                  |
| 5    | `row-t5`    | **Theoretical / informal.** Idea-stage; blog post, manifesto, taxonomy entry, no code.        | ~70 systems                   |

Consumers SHOULD treat `tier` as ordinal ("higher number = more
speculative") and not as a quality score. Tier-5 entries are not
"worse" — they're different artefacts (manifestos, ideas, frameworks)
that the catalog still needs to track.

### 2.3 Section membership

```typescript
type SectionMembership = {
  section: string;       // Top-level section name (e.g. "Dedicated memory layers")
  subsection: string | null; // Sub-group within the section (e.g. "— Factual & long-term memory (token-level)") or null
  primary: boolean;      // True for the section the record canonically belongs to
  reason: string | null; // Short justification for the placement; null if obvious
};
```

Constraints:

- `sections` array is non-empty.
- Exactly one element has `primary: true`. The HTML's row position
  (which top-level `tr.group-row` it appears under) defines that
  primary section.
- Cross-listed records (e.g. Memvid as both a library product and a
  Claude Code plugin) get one element per section with `primary: true`
  on the primary placement only.
- `subsection` is non-null only when the parent `<tr.group-row>` is a
  level-2 group (the ones with `style="padding-left: 28px"` in the HTML
  — they live underneath a parent group-row).

Canonical section names (from the HTML, in document order):

1. Dedicated memory layers
2. Framework-embedded memory
3. Platform-provider memory
4. Coding-agent memory
5. Browser-agent memory
6. Personal AI / PKM / lifelogging memory
7. Voice-first / wearable AI memory
8. Research / specialised systems
9. Recent method papers — theorized, no distinct product
   - — Factual & long-term memory (token-level)
   - — Experiential & procedural memory (agent learning from experience)
   - — Working memory & context management
   - — Parametric & latent memory (memory in weights / KV / hidden states)
   - — World-model & imagination memory
   - — Continual learning & catastrophic forgetting
   - — Memory-augmented reinforcement learning
   - — Cognitive-architecture-inspired memory
10. Retrieval-as-memory hybrids
11. File-backed / editor paradigms
12. Claude Code memory mechanisms
13. Knowledge-graph platforms
14. Vector-database infrastructure
15. Enterprise-search adjacencies
16. Vertical / domain-specific AI memory
    - — Scientific / research AI memory
    - — Healthcare AI memory
    - — Legal AI memory
    - — Customer support / voice agent memory
    - — Gaming / NPC character memory
    - — Robotics / autonomous-driving / embodied memory
    - — Education AI memory
17. Memory benchmarks & evaluation
18. Memory observability & monitoring
19. Memory governance, privacy & safety
20. Theoretical / informal — ideas without a paper

Producers MUST preserve the leading "— " prefix on subsection names
exactly as it appears in the HTML — this is what distinguishes a
subsection from a top-level section in document-order parsing.

### 2.4 Taxonomy

```typescript
type TaxonomyValue = {
  value: string;         // Lowercase canonical taxonomy term
  primary: boolean;      // True for the dominant value on this axis
  reason: string | null; // Short justification, null if obvious or single-value
};

type Taxonomy = {
  storage:     TaxonomyValue[];
  retrieval:   TaxonomyValue[];
  persistence: TaxonomyValue[];
  update:      TaxonomyValue[];
  unit:        TaxonomyValue[];
  governance:  TaxonomyValue[];
  conflict:    TaxonomyValue[];
};
```

Constraints (apply per-axis, not across the whole taxonomy):

- Each axis array is non-empty.
- Exactly one element per axis has `primary: true`.
- `value` is the lowercased canonical term as it appears inside
  `<span class="tax-pill tax-<value>">` in the HTML.
- For axes whose cell is a free-text "— not applicable" annotation
  (no pills), the array contains a single element with
  `value: "n/a"`, `primary: true`, and the annotation copied verbatim
  into `reason`.

The seven axes and the canonical vocabularies for each are documented
separately in `taxonomy/` (the existing taxonomy work). This schema
spec only locks in the *shape*, not the value vocabularies — the
vocabularies are governed by the controlled-vocab list in `taxonomy/`.

### 2.5 Cells

`cells` is an object keyed by **column slug**, with one entry per
non-name, non-taxonomy column in `landscape.html`. There are 74 such
columns (83 total - 1 name - 1 memory-model-type - 7 taxonomy = 74).

Each cell value:

```typescript
type Cell = {
  value: string;            // The visible text (with HTML stripped, normalised whitespace)
  citation: string | null;  // The href of the cell's <a class="cite"> link, or null
  status: "real-data" | "not-applicable" | "depth-floor-reached" | "no-data" | "estimate";
  tier: "T1" | "T2" | "T3";  // Claim-tier provenance — see §3a.
};
```

The complete column-slug set (in HTML left-to-right order):

| # | Column slug              | HTML `td` class       | Header text                     |
|---|--------------------------|-----------------------|----------------------------------|
| 1 | `type`                   | `type`                | Memory model                     |
| 2 | `desc`                   | `desc`                | What it does & what's distinct   |
| 3 | `claims`                 | `claims`              | Claims / benefits                |
| 4 | `modalities`             | `modalities`          | Modalities                       |
| 5 | `created`                | `created`             | Created                          |
| 6 | `latest-release`         | `latest-release`      | Latest release                   |
| 7 | `license`                | `license`             | License                          |
| 8 | `gh`                     | `gh`                  | GitHub                           |
| 9 | `mindshare`              | `mindshare`           | Mindshare                        |
| 10 | `citations`             | `citations`           | Citations                        |
| 11 | `funding`               | `funding`             | Funding                          |
| 12 | `customers`             | `customers`           | Customers / scale                |
| 13 | `pricing`               | `pricing`             | Pricing                          |
| 14 | `compliance`            | `compliance`          | Compliance                       |
| 15 | `data-handling`         | `data-handling`       | Data handling                    |
| 16 | `deployment`            | `deployment`          | Deployment                       |
| 17 | `hq`                    | `hq`                  | HQ                               |
| 18 | `founders`              | `founders`            | Founders / pedigree              |
| 19 | `volume`                | `volume`              | Memory volume / scale            |
| 20 | `perf`                  | `perf`                | Performance                      |
| 21 | `repro`                 | `repro`               | Reproducibility                  |
| 22 | `code-release`          | `code-release`        | Code/weights release             |
| 23 | `api-surface`           | `api-surface`         | API surface                      |
| 24 | `latency`               | `latency`             | Latency p50/p99                  |
| 25 | `throughput`            | `throughput`          | Throughput                       |
| 26 | `backend-storage`       | `backend-storage`     | Backend storage                  |
| 27 | `multi-tenancy`         | `multi-tenancy`       | Multi-tenancy                    |
| 28 | `encryption`            | `encryption`          | Encryption                       |
| 29 | `sso-rbac`              | `sso-rbac`            | SSO / RBAC                       |
| 30 | `embedding-model`       | `embedding-model`     | Embedding model                  |
| 31 | `consistency`           | `consistency`         | Consistency                      |
| 32 | `versioning`            | `versioning`          | Versioning                       |
| 33 | `tombstoning`           | `tombstoning`         | Tombstoning                      |
| 34 | `schema-evolution`      | `schema-evolution`    | Schema evolution                 |
| 35 | `namespace`             | `namespace`           | Namespace primitives             |
| 36 | `contradiction`         | `contradiction`       | Contradiction handling           |
| 37 | `forgetting`            | `forgetting`          | Forgetting policy                |
| 38 | `mcp-support`           | `mcp-support`         | MCP support                      |
| 39 | `a2a-support`           | `a2a-support`         | A2A support                      |
| 40 | `otel`                  | `otel`                | OTel                             |
| 41 | `webhooks`              | `webhooks`            | Webhooks / events                |
| 42 | `import-export`         | `import-export`       | Import / export                  |
| 43 | `integration-count`     | `integration-count`   | Integration count                |
| 44 | `orchestration`         | `orchestration`       | Orchestration                    |
| 45 | `programmatic-control`  | `programmatic-control`| Programmatic control             |
| 46 | `vendor-benchmarks`     | `vendor-benchmarks`   | Vendor benchmarks                |
| 47 | `pricing-specifics`     | `pricing-specifics`   | Pricing specifics                |
| 48 | `agent-abstraction`     | `agent-abstraction`   | Agent abstraction                |
| 49 | `memory-primitives`     | `memory-primitives`   | Memory primitives                |
| 50 | `llm-lock`              | `llm-lock`            | LLM lock                         |
| 51 | `runtimes`              | `runtimes`            | Runtimes                         |
| 52 | `session-handling`      | `session-handling`    | Session handling                 |
| 53 | `validated-verticals`   | `validated-verticals` | Validated verticals              |
| 54 | `time-to-running`       | `time-to-running`     | Time to running                  |
| 55 | `anti-fit`              | `anti-fit`            | Anti-fit                         |
| 56 | `optimised-for`         | `optimised-for`       | Optimised for                    |
| 57 | `adjacent-infrastructure`| `adjacent-infrastructure` | Adjacent infrastructure      |
| 58 | `pros`                  | `pros`                | Pros                             |
| 59 | `cons`                  | `cons`                | Cons                             |
| 60 | `links`                 | `links`               | Project & sources                |
| 61 | `obs-langsmith`         | `obs-langsmith`       | LangSmith                        |
| 62 | `obs-opentelemetry`     | `obs-opentelemetry`   | OpenTelemetry                    |
| 63 | `obs-datadog`           | `obs-datadog`         | Datadog                          |
| 64 | `obs-helicone`          | `obs-helicone`        | Helicone                         |
| 65 | `obs-weave`             | `obs-weave`           | Weave (W&B)                      |
| 66 | `obs-langfuse`          | `obs-langfuse`        | Langfuse                         |
| 67 | `obs-arize`             | `obs-arize`           | Arize                            |
| 68 | `obs-custom`            | `obs-custom`          | Custom observability             |
| 69 | `cost-token-budget`     | `cost-token-budget`   | Token budget                     |
| 70 | `cost-prompt-caching`   | `cost-prompt-caching` | Prompt caching                   |
| 71 | `cost-semantic-caching` | `cost-semantic-caching` | Semantic caching               |
| 72 | `cost-batching`         | `cost-batching`       | Batch API                        |
| 73 | `cost-model-routing`    | `cost-model-routing`  | Model routing                    |
| 74 | `cost-streaming-only`   | `cost-streaming-only` | Streaming-only                   |
| 75 | `cost-observability-cost-attribution` | `cost-observability-cost-attribution` | Cost attribution     |

The `cells` object MUST contain all 75 keys for every record. Records
where a column is genuinely meaningless (e.g. `funding` for a research
paper) use `status: "not-applicable"`. The `value` field for those
cells is the human-readable annotation copied from the HTML
(typically `"not applicable — <reason>"`).

### 2.5.1 Observability columns (added in T1-1, issue #39)

The eight `obs-*` columns capture which third-party observability
integrations each product / framework supports. They were added
because observability/debugging is the highest-demand question in
agent infrastructure (per the May 2026 volumetric agent: 807 HN
hits, 89% LangChain-survey adoption, 6/7 published surveys).

For `obs-langsmith` through `obs-arize` the `value` field is one of
`"yes"`, `"no"`, or `""` (empty = unknown, surfaced as the standard
`no-data` / `depth-floor-reached` status). Boolean cells MAY also
carry a version string (e.g. `"yes (LangSmith 0.3.x)"`) when the
integration is gated on a specific release.

`obs-custom` is a free-text column for non-standard observability
integrations (Honeycomb, Lightstep, custom OTLP exporters, in-house
dashboards, etc.).

Coverage callout: only the top ~100 rows (T1 + select T2) have been
backfilled. Empty `obs-*` cells on rows below the coverage floor are
deliberate; the `/analyses/observability` view surfaces the coverage
gap rather than papering over it.

### 2.5.2 Cost-control columns (added in T1-3, issue #41)

The seven `cost-*` columns capture which token-economics / cost-governance
features each product or framework offers. They were added because cost is
the #2 demand-signal question per the May 2026 volumetric agent (HN 171
mentions in the last 12 months, Sequoia framing on inference-cost
sustainability, Datadog 2026 finding that 69% of input tokens go to
system-prompt overhead). The practitioner question has shifted from "how
expensive is it?" to "how do I govern spend?" — these columns answer the
latter.

Each cell carries a `{value, citation, status, tier}`. The `value` is
one of `"yes"`, `"no"`, or `""` (empty = unknown, surfaced via the
standard `no-data` / `depth-floor-reached` status). Boolean cells MAY
also carry a version string (e.g. `"yes (Batch API v1)"`) when the
support is gated on a specific release or pricing tier.

Column semantics:

| Slug                                       | Meaning                                                                                                              |
|--------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `cost-token-budget`                        | Per-call token-budget enforcement: framework enforces a max-tokens-per-request limit before sending.                 |
| `cost-prompt-caching`                      | Anthropic-style prompt caching or equivalent (OpenAI Cached Input, Gemini caching, vendor cache_control blocks).     |
| `cost-semantic-caching`                    | Cache results by semantic similarity of the request (e.g. GPTCache, Helicone caching, LangChain SemanticCache).      |
| `cost-batching`                            | Batch API support (e.g. OpenAI Batch API, Anthropic Message Batches) — async, discounted bulk requests.              |
| `cost-model-routing`                       | Dynamic model selection by complexity / cost (e.g. fall back to a cheaper model for simple queries; LLM routers).    |
| `cost-streaming-only`                      | Forces streaming responses so partial output can be aborted before the full bill lands.                              |
| `cost-observability-cost-attribution`      | Tracks $ per request / per tool call / per user — distinct from generic observability by exposing dollar amounts.    |

Coverage callout: only the top ~100 rows (T1 + select T2 in cost-relevant
sections — frameworks, memory layers, agent harnesses, IDEs, vector-database
infrastructure) have been backfilled. Empty `cost-*` cells on rows below
the coverage floor are deliberate; the `/analyses/cost-economics` view
surfaces the coverage gap rather than papering over it.

Per the spec, per-call pricing data (e.g. `$0.003 / 1k input tokens`) is
**out of scope** for these columns — pricing changes too fast and goes
stale within weeks. The cost-* columns capture the *governance features*
that let a practitioner control spend, not the spend itself.

---

## 3. The `status` enum — exact semantics

Every cell carries a `status` from this four-value enum:

| Status                | When to use                                                                                                               | `value` content                                | `citation`                                     |
|-----------------------|---------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|------------------------------------------------|
| `real-data`           | Actual data found from a source. Default state for filled cells.                                                          | The actual data                                | URL the data was sourced from                  |
| `not-applicable`      | Column doesn't apply to this record (e.g. `funding` for a research paper, `vendor-benchmarks` for an unrelated section).  | The N/A annotation, e.g. `"not applicable — research paper"` | URL of source verifying the N/A judgement, or `null`     |
| `depth-floor-reached` | Searched in good faith, found nothing. The record's research depth has bottomed out for this cell.                        | Either the literal phrase `"searched not found"` or a more specific summary | URL where the search bottomed out (vendor docs, GitHub, etc.) |
| `no-data`             | **Transitional only.** Placeholder for a cell not yet researched. Should be rare-to-zero in terminal data.                | `""` or `"no data"`                            | `null`                                         |

Detection rules for a parser converting `landscape.html` cells:

- If the inner HTML contains `<span class="no-data" ... not applicable`,
  status is `not-applicable`.
- If the inner HTML contains `<span class="no-data">searched not found</span>`,
  status is `depth-floor-reached`.
- If the inner HTML contains `<span class="no-data">no data</span>` (with no
  qualifying annotation), status is `no-data`.
- Otherwise, status is `real-data`.

Consumers (table app, leaderboards, graph view) SHOULD use `status` to
filter:

- "Show only filled-in data" → `status === "real-data"`.
- "Show all knowledge gaps" → `status === "depth-floor-reached"`.
- "Hide N/A noise from sort" → exclude `not-applicable`.

A fifth value, `estimate`, is reserved for maintainer-judgement cells with
no hard citation (see §3a — tier T3).

---

## 3a. Claim-tier provenance (the `tier` field on every cell)

Every cell carries a `tier` from this three-value enum. The tier is the
machine-readable answer to "where did this claim come from?" It lets
consumers (UI, validators, audit scripts) reason about claim quality
without re-deriving it from the cell's contents.

The motivation: cell-level claims (benchmark scores, integration counts,
market positioning) are vendor-self-reported. Goodhart's Law applies once
a leaderboard becomes a reputation signal — we can't manually validate
everything, so we surface the *provenance* of every claim.

### Tier definitions

| Tier | Name | Definition | Examples |
|------|------|------------|----------|
| T1 | Auto-verifiable | Derivable from public signal at build time. The `citation` field MUST be a GitHub URL (the only auto-verifiable source we recognise in v1). | GitHub URL, star count, license file, last-commit date. |
| T2 | Source-URL required | Not auto-verifiable, but the `citation` field MUST contain a resolvable URL. Gate 5 fails the build if a T2 cell has missing or malformed citation. Default tier when in doubt. | Benchmark scores, integration claims, production deployment claims, customer logos, funding. |
| T3 | Estimate / inferred | Maintainer judgement, no hard citation. Flagged with `status: "estimate"`, or auto-tagged T3 when the cell is `no-data` or uncited `not-applicable`. T3 cells are NOT validated for citation presence. | Market positioning, "approximate" claims, taxonomy clusters, unsourced N/A annotations. |

### Auto-detection heuristic (applied by `extract.py`)

`extract.py` populates `tier` automatically from the (`citation`,
`status`) pair using a deterministic, conservative heuristic. The intent
is **"when in doubt, classify as T2"** — over-classifying as T2 yields
more validation failures (which we can fix), whereas under-classifying
yields claims that silently pass without provenance.

The heuristic, top-down (first match wins):

1. **`status === "estimate"`** → `T3`. Explicit maintainer judgement.
2. **`status === "no-data"`** → `T3`. Transitional placeholder.
3. **`citation` matches `^https?://github\.com/`** → `T1`.
4. **`citation` is any other `http(s)://` URL** → `T2`.
5. **`status === "not-applicable"` and `citation` absent** → `T3`. An
   N/A annotation is the maintainer's decision that no claim applies;
   demanding a citation defeats the purpose. (If a `not-applicable`
   cell *does* carry a URL verifying the N/A judgement, rule 4
   catches it first as T2.)
6. **`citation` empty AND `status ∈ {real-data, depth-floor-reached}`**
   → `T2` + soft warning. We have a claim but lost the URL; classifying
   T2 ensures gate 5 will eventually surface it.

### Validation rules

`scripts/validate.py` gate 5 enforces:

- For T1 cells: `citation` MUST match `^https?://github\.com/`.
- For T2 cells: `citation` MUST be a non-empty `http(s)://` URL.
- For T3 cells: no validation.

---

## 4. Per-edge structure (`landscape.edges.json` → `edges[*]`)

```typescript
type Edge = {
  source: string;            // Record id (must exist in landscape.json#records)
  target: string;            // Record id (must exist in landscape.json#records)
  type: EdgeType;            // See enum below
  evidence: string;          // 1-2 sentence summary of the source phrase / claim that justified the edge
  citation: string;          // URL where the evidence can be verified
  isInfluential?: boolean;   // Optional. Only present on type:"cites" edges. From Semantic Scholar's isInfluential flag.
};
```

### Edge type enum (9 values)

| `type`            | Direction semantics (source → target)                                                                                    | Typical evidence source                                       |
|-------------------|--------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| `built-on`        | source's product is implemented on top of target's product (target is a dependency or runtime).                           | `desc`/`adjacent-infrastructure` cell mining                  |
| `extends`         | source extends or generalises target's method (paper-to-paper or product-to-product), keeping target's core idea.         | paper abstracts, product changelogs                           |
| `forks`           | source is a literal code fork of target.                                                                                 | GitHub fork relationships, README acknowledgements            |
| `integrates-with` | source has an integration / connector / first-class adapter to target. Symmetric in spirit but stored directionally.      | docs, integration count cell, integration matrices            |
| `competes-with`   | source and target are positioned by the market (or by themselves) as alternatives in the same buyer's mind.               | comparison pages, vendor "vs" docs, analyst writeups          |
| `inspired-by`     | source explicitly cites target as conceptual inspiration without building on its code or extending its method directly.    | author posts, blog posts, talks                               |
| `cites`           | source's paper cites target's paper. The most common edge type, populated from Semantic Scholar.                          | Semantic Scholar API                                          |
| `same-team-as`    | source and target are by the same author / lab / company. Captures lineage where one team produces multiple systems.      | `founders` cell, paper authors, GitHub org                    |
| `succeeds`        | source is an explicit successor / next-version of target by the same team (e.g. MemGPT → Letta).                          | release notes, blog posts                                     |

Choosing the right type when more than one fits:

- `forks` > `built-on` > `extends` > `inspired-by` (use the most specific).
- `succeeds` > `same-team-as` (use `succeeds` only when there's an
  explicit "this replaces that" claim from the team).
- `cites` is the lightest-weight academic edge; if the citation is
  marked `isInfluential` by S2, that's the signal that it's lineage,
  not just a literature-review nod.

### `isInfluential` on `cites` edges

When `type === "cites"`, the edge MAY include an
`isInfluential: boolean` field copied from Semantic Scholar's
`isInfluential` field on the citation. Other edge types MUST NOT
include this field.

### Multiple edges between the same pair

Multiple edges between the same `(source, target)` pair are allowed
**iff their `type` differs**. e.g.: `(letta, memgpt, succeeds)` AND
`(letta, memgpt, same-team-as)` are both valid and both useful.

Same `(source, target, type)` triple MUST be unique — duplicates are a
producer bug.

---

## 5. Full example record (Mem0)

```json
{
  "id": "mem0--mem0-ai",
  "name": "Mem0",
  "tier": 1,
  "url": "https://mem0.ai/",
  "sections": [
    {
      "section": "Dedicated memory layers",
      "subsection": null,
      "primary": true,
      "reason": "Standalone memory product; entire pitch is the memory layer."
    }
  ],
  "taxonomy": {
    "storage": [
      { "value": "vector", "primary": true,  "reason": "Default Qdrant store; the recall path." },
      { "value": "graph",  "primary": false, "reason": "Optional Neo4j store for entity-relations." },
      { "value": "kv",     "primary": false, "reason": "Third concurrent store for raw KV access." }
    ],
    "retrieval": [
      { "value": "similarity",      "primary": true,  "reason": "Vector ANN is the primary recall mechanism." },
      { "value": "graph-traversal", "primary": false, "reason": null },
      { "value": "extraction-pull", "primary": false, "reason": null }
    ],
    "persistence": [
      { "value": "long-term", "primary": true, "reason": null }
    ],
    "update": [
      { "value": "extraction", "primary": true, "reason": "LLM extracts facts; ADD/UPDATE/DELETE/NOOP per LLM decision." }
    ],
    "unit": [
      { "value": "fact",    "primary": true,  "reason": "Facts are the unit committed to memory." },
      { "value": "episode", "primary": false, "reason": null }
    ],
    "governance": [
      { "value": "opaque", "primary": true, "reason": "Stored facts are LLM-extracted summaries, not raw inputs." }
    ],
    "conflict": [
      { "value": "llm-arbitrate", "primary": true, "reason": "Fact-extraction prompt arbitrates ADD/UPDATE/DELETE/NOOP." }
    ]
  },
  "cells": {
    "type":            { "value": "Vector + graph + KV (hybrid)", "citation": null, "status": "real-data" },
    "desc":            { "value": "Universal memory layer for AI agents. Three concurrent stores (vector + graph + KV); LLM-extracted facts; concurrent retrieval via ThreadPoolExecutor.", "citation": null, "status": "real-data" },
    "claims":          { "value": "~51k★. $24M Series A (Oct 2025) at $150M. Exclusive memory provider for AWS Agent SDK. Reports 26% improvement over OpenAI on LOCOMO; 91% lower p95 latency vs full-context.", "citation": null, "status": "real-data" },
    "modalities":      { "value": "text", "citation": "https://docs.mem0.ai/open-source/features/graph-memory", "status": "real-data" },
    "created":         { "value": "2023-06", "citation": null, "status": "real-data" },
    "latest-release":  { "value": "openclaw-v1.0.11 (2026-04-29)", "citation": "https://github.com/mem0ai/mem0/releases/tag/openclaw-v1.0.11", "status": "real-data" },
    "license":         { "value": "Apache-2.0", "citation": "https://github.com/mem0ai/mem0/blob/main/LICENSE", "status": "real-data" },
    "gh":              { "value": "54.9k★, +1.6k/mo, Python", "citation": "https://github.com/mem0ai/mem0", "status": "real-data" },
    "mindshare":       { "value": "12 inbound (57 HN, 4 press)", "citation": "https://techcrunch.com/2025/10/28/mem0-raises-24m-from-yc-peak-xv-and-basis-set-to-build-the-memory-layer-for-ai-apps/", "status": "real-data" },
    "citations":       { "value": "searched not found", "citation": "https://www.semanticscholar.org/paper/Mem0:-Building-Production-Ready-AI-Agents-with-Chhikara-Khant/1d9c21a0fdb1cc16a32c5d490ebaf98436a23382", "status": "depth-floor-reached" },
    "funding":         { "value": "$24M total ($150M val), Series A 2025-10", "citation": "https://kindredventures.com/announcement/mem0-building-the-memory-infrastructure-for-personalized-ai/", "status": "real-data" },
    "customers":       { "value": "1-10 ppl. AWS (exclusive memory provider for Agent SDK), 80k+ developer signups, enterprise unnamed", "citation": "https://techcrunch.com/2025/10/28/mem0-raises-24m-from-yc-peak-xv-and-basis-set-to-build-the-memory-layer-for-ai-apps/", "status": "real-data" },
    "pricing":         { "value": "Free + paid", "citation": "https://mem0.ai/pricing", "status": "real-data" },
    "compliance":      { "value": "SOC 2 Type II, HIPAA-ready", "citation": "https://mem0.ai/security", "status": "real-data" },
    "data-handling":   { "value": "Trains on de-identified/aggregated data (see privacy policy); enterprise controls not publicly detailed", "citation": "https://mem0.ai/privacy-policy", "status": "real-data" },
    "deployment":      { "value": "Both", "citation": "https://mem0.ai/blog/self-host-mem0-docker", "status": "real-data" },
    "hq":              { "value": "US", "citation": "https://www.crunchbase.com/organization/mem0ai", "status": "real-data" },
    "founders":        { "value": "YC S24; co-founders Taranjeet Singh and Deshraj Yadav", "citation": "https://techcrunch.com/2025/10/28/mem0-raises-24m-from-yc-peak-xv-and-basis-set-to-build-the-memory-layer-for-ai-apps/", "status": "real-data" },
    "volume":          { "value": "1B+ memories (vendor blog claims; 80k+ dev signups)", "citation": "https://mem0.ai/research", "status": "real-data" },
    "perf":            { "value": "30 ConvoMem; 91.6 LoCoMo (disputed); ~26% improvement on LMES (disputed)", "citation": "https://mem0.ai/research", "status": "real-data" },
    "repro":           { "value": "searched not found", "citation": "https://github.com/mem0ai/mem0", "status": "depth-floor-reached" },
    "code-release":    { "value": "searched not found", "citation": "https://github.com/mem0ai/mem0", "status": "depth-floor-reached" },
    "api-surface":     { "value": "REST, SDK: Python, Node.js", "citation": "https://docs.mem0.ai/", "status": "real-data" },
    "latency":         { "value": "searched not found", "citation": "https://docs.mem0.ai/", "status": "depth-floor-reached" },
    "throughput":      { "value": "searched not found", "citation": "https://docs.mem0.ai/", "status": "depth-floor-reached" },
    "backend-storage": { "value": "hybrid (vector + graph + KV)", "citation": "https://docs.mem0.ai/components/overview", "status": "real-data" },
    "multi-tenancy":   { "value": "Logical namespace per (user_id, agent_id, run_id); self-hosted/on-prem deployment available for tenant isolation", "citation": "https://docs.mem0.ai/core-concepts/memory-operations", "status": "real-data" },
    "encryption":      { "value": "AES-256 at rest, TLS in transit; BYOK supported; SOC 2 Type I (Type II in progress), HIPAA-ready", "citation": "https://mem0.ai/security", "status": "real-data" },
    "sso-rbac":        { "value": "SSO + RBAC", "citation": "https://mem0.ai/security", "status": "real-data" },
    "embedding-model": { "value": "multiple supported", "citation": "https://docs.mem0.ai/components/embedders/overview", "status": "real-data" },
    "consistency":     { "value": "eventual", "citation": "https://docs.mem0.ai/platform/quickstart", "status": "real-data" },
    "versioning":      { "value": "snapshots", "citation": "https://docs.mem0.ai/platform/features/memory-history", "status": "real-data" },
    "tombstoning":     { "value": "hard-delete supported", "citation": "https://docs.mem0.ai/api-reference/memory/delete-memory", "status": "real-data" },
    "schema-evolution":{ "value": "free-form / no schema", "citation": "https://docs.mem0.ai/core-concepts/memory-types", "status": "real-data" },
    "namespace":       { "value": "hierarchical", "citation": "https://docs.mem0.ai/core-concepts/memory-operations", "status": "real-data" },
    "contradiction":   { "value": "LLM resolves and overwrites", "citation": "https://docs.mem0.ai/core-concepts/memory-operations", "status": "real-data" },
    "forgetting":      { "value": "user-controlled forget", "citation": "https://docs.mem0.ai/api-reference/memory/delete-memory", "status": "real-data" },
    "mcp-support":     { "value": "native (first-party) — official mem0-mcp server", "citation": "https://github.com/mem0ai/mem0-mcp", "status": "real-data" },
    "a2a-support":     { "value": "searched not found", "citation": null, "status": "depth-floor-reached" },
    "otel":            { "value": "via adapter — AgentOps integration", "citation": "https://docs.mem0.ai/integrations/agentops", "status": "real-data" },
    "webhooks":        { "value": "webhooks supported (platform tier)", "citation": "https://docs.mem0.ai/platform/quickstart", "status": "real-data" },
    "import-export":   { "value": "JSON (REST export); ChatGPT history import", "citation": "https://docs.mem0.ai/api-reference/memory/get-memories", "status": "real-data" },
    "integration-count":{ "value": "14", "citation": "https://github.com/mem0ai/mem0", "status": "real-data" },
    "orchestration":   { "value": "both", "citation": "https://docs.mem0.ai/open-source/features/multi-agent-memory", "status": "real-data" },
    "programmatic-control": { "value": "full CRUD + SDK (Python/Node REST)", "citation": "https://docs.mem0.ai/api-reference", "status": "real-data" },
    "vendor-benchmarks": { "value": "LoCoMo 91.6 (vendor); LMES ~26% improvement over OpenAI; ConvoMem 30 (vendor) — disputed by Zep counter-analysis", "citation": "https://mem0.ai/research", "status": "real-data" },
    "pricing-specifics":{ "value": "per-API-call: free tier 1k mem ops/mo; Starter $19/mo (50k ops); Pro $249/mo; Enterprise custom", "citation": "https://mem0.ai/pricing", "status": "real-data" },
    "agent-abstraction":{ "value": "not applicable — wrong section", "citation": null, "status": "not-applicable" },
    "memory-primitives":{ "value": "not applicable — wrong section", "citation": null, "status": "not-applicable" },
    "llm-lock":        { "value": "not applicable — wrong section", "citation": null, "status": "not-applicable" },
    "runtimes":        { "value": "not applicable — wrong section", "citation": null, "status": "not-applicable" },
    "session-handling":{ "value": "not applicable — wrong section", "citation": null, "status": "not-applicable" },
    "validated-verticals": { "value": "healthcare, legal, financial-services, customer support, coding agents (broad horizontal)", "citation": "https://mem0.ai/customers", "status": "real-data" },
    "time-to-running": { "value": "<10min (hosted SaaS sign-up) or <1hr (Docker compose self-host)", "citation": "https://docs.mem0.ai/quickstart", "status": "real-data" },
    "anti-fit":        { "value": "no anti-fit explicitly stated", "citation": "https://docs.mem0.ai/", "status": "real-data" },
    "optimised-for":   { "value": "developer experience + universal memory layer (model-agnostic, multi-store)", "citation": "https://mem0.ai/", "status": "real-data" },
    "adjacent-infrastructure": { "value": "BYO LLM provider; bundles vector store (Qdrant default) and graph store (Neo4j optional)", "citation": "https://docs.mem0.ai/components/vectordbs/overview", "status": "real-data" },
    "pros":            { "value": "Hybrid (vector + graph + KV) gives the most architectural flexibility of any memory layer; AWS Agent SDK exclusivity and 51k★ make it the field's de-facto reference.", "citation": null, "status": "real-data" },
    "cons":            { "value": "LOCOMO benchmark numbers were publicly disputed by Zep in counter-analysis; LLM-extraction approach risks dropping facts that don't fit the prompt.", "citation": null, "status": "real-data" },
    "links":           { "value": "GitHub mem0ai/mem0; arxiv 2504.19413; Graph Memory docs; research page; AWS architecture", "citation": "https://github.com/mem0ai/mem0", "status": "real-data" }
  }
}
```

---

## 6. Full example edges

```json
[
  {
    "source": "letta-memgpt--letta-com",
    "target": "memgpt-paper--arxiv-2310-08560",
    "type": "succeeds",
    "evidence": "Letta is the production successor to MemGPT — UC Berkeley team renamed and re-released the same architecture as letta_v1_agent.",
    "citation": "https://www.letta.com/blog/letta-is-here"
  },
  {
    "source": "letta-memgpt--letta-com",
    "target": "memgpt-paper--arxiv-2310-08560",
    "type": "same-team-as",
    "evidence": "Charles Packer and Sarah Wooders are co-authors on the MemGPT paper and co-founders of Letta.",
    "citation": "https://techcrunch.com/2024/09/23/letta-one-of-uc-berkeleys-most-anticipated-ai-startups-has-just-come-out-of-stealth/"
  },
  {
    "source": "mem0--mem0-ai",
    "target": "qdrant--qdrant-tech",
    "type": "built-on",
    "evidence": "Mem0's default vector store is Qdrant; bundled with `pip install mem0ai`.",
    "citation": "https://docs.mem0.ai/components/vectordbs/overview"
  },
  {
    "source": "mem0--mem0-ai",
    "target": "zep--getzep-com",
    "type": "competes-with",
    "evidence": "Zep published a counter-analysis disputing Mem0's LoCoMo numbers — direct positioning as alternatives in the memory-layer space.",
    "citation": "https://blog.getzep.com/state-of-the-art-agent-memory-mem0-vs-zep/"
  },
  {
    "source": "graphrag-paper--arxiv-2404-16130",
    "target": "kg-rag-survey-paper--arxiv-2306-04136",
    "type": "cites",
    "evidence": "GraphRAG paper cites Edge et al.'s KG-RAG survey as the foundational review of graph-based retrieval methods.",
    "citation": "https://www.semanticscholar.org/paper/From-Local-to-Global%3A-A-Graph-RAG-Approach-to-Edge-Trinh/...",
    "isInfluential": true
  }
]
```

---

## 7. Validation rules

A producer (or a future JSON Schema check) must enforce all of these.
A reviewer can read this list as the acceptance criteria for any
file claiming to conform to the schema.

### 7.1 `landscape.json` validation

1. Top-level keys exactly: `schemaVersion`, `generatedAt`, `sourceHtml`, `records`. Extras are an error.
2. `schemaVersion` is a semver string starting with the major-version this doc describes (currently `1`).
3. `records` is an array of ≥1 objects.
4. Every record has the required keys from §2.
5. **`id` uniqueness:** the multiset of `record.id` over `records` is a set (no duplicates).
6. **`id` regex:** matches `^[a-z0-9]+(-[a-z0-9]+)*(--[a-z0-9]+(-[a-z0-9]+)*)?$` (i.e. lowercase slug, optional `--<source-suffix>`).
7. **`tier` ∈ {1,2,3,4,5}.**
8. **`url`** is either `null` or a valid `http(s)://` URL.
9. **Sections:**
   - `sections` is non-empty.
   - exactly one element has `primary: true`.
   - every `section` value is one of the canonical section names listed in §2.3.
   - `subsection` is non-null only when the section is one that has subsections in §2.3.
10. **Taxonomy:**
    - `taxonomy` has exactly the seven keys: `storage`, `retrieval`, `persistence`, `update`, `unit`, `governance`, `conflict`.
    - each axis array is non-empty.
    - exactly one element per axis has `primary: true`.
11. **Cells:**
    - `cells` has exactly the 75 keys listed in §2.5 (no extras, no missing).
    - every cell's `status` is one of `real-data`, `not-applicable`, `depth-floor-reached`, `no-data`, `estimate`.
    - every cell's `value` is a string (possibly empty).
    - every cell's `citation` is either `null` or an `http(s)://` URL.
    - every cell's `tier` is one of `T1`, `T2`, `T3`.
12. **Claim-tier provenance (gate 5):**
    - For every cell where `tier === "T1"`, `citation` MUST match the GitHub URL regex `^https?://github\.com/`.
    - For every cell where `tier === "T2"`, `citation` MUST be a non-empty `http(s)://` URL.
    - For every cell where `tier === "T3"`, no citation requirement.

### 7.2 `landscape.edges.json` validation

1. Top-level keys exactly: `schemaVersion`, `generatedAt`, `edges`.
2. `edges` is an array (possibly empty, though it shouldn't be in practice).
3. Every edge has required keys: `source`, `target`, `type`, `evidence`, `citation`.
4. **Referential integrity:** `source` and `target` must each match a `record.id` in `landscape.json`.
5. **No self-edges:** `source !== target`.
6. **`type`** is one of the nine values in §4.
7. **`isInfluential`** is present iff `type === "cites"`. When present, it's a boolean.
8. **Pair+type uniqueness:** the multiset of `(source, target, type)` triples is a set.
9. **`citation`** is a non-empty `http(s)://` URL.
10. **`evidence`** is a non-empty string ≤ 500 chars (soft cap; producers should summarise).

### 7.3 Cross-file validation

- Both files share the same `schemaVersion`.
- `generatedAt` on the edges file should be ≥ `generatedAt` on the
  records file (edges depend on records — they're always built after
  or together with records).

---

## 8. Open questions / future work

- **JSON Schema document.** This spec could be encoded as JSON Schema
  (Draft 2020-12) and validated by `ajv` or `jsonschema` in the build.
  Deferred — a Python-side validator inside `extract.py` is fine for
  v1 and doesn't add a JS dep.
- **`taxonomy/*` integration.** The taxonomy axis vocabularies live
  in `taxonomy/` and are not duplicated here; future work may merge
  them into a single canonical place.
- **Edge weighting.** Some edge types (e.g. `cites`) have a natural
  weight (Semantic Scholar similarity score). v1 stores `isInfluential`
  only; numeric weights are deferred.
