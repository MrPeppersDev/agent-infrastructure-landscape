# Schema spec — `landscape.json` and `landscape.edges.json`

This document is the **source-of-truth shape** for the structured catalog
that `extract.py` (issue #2) emits and that every Phase 2-5 consumer reads.

It locks in:

- top-level structure of both files
- the exhaustive per-record field set
- the four-state `status` enum semantics
- the ten edge-type vocabulary
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
| `cells`    | object keyed by column-name         | yes      | All 96 column keys present (with `not-applicable` if N/A).   |
| `_provenance` | object keyed by cell slug         | no       | Per-cell provenance. Added in Phase 2 / Gate 1 (issue #95). See §3d. Empty `{}` until backfill lands. |

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
non-name, non-taxonomy column in `landscape.html`. There are 96 such
columns as of Phase 2 / Gate 1 (issue #95) — the 85 pre-Phase-2 columns
documented below plus the 11 Phase 2 column families introduced in
§2.5.7–9 (cost, capability, use-case). The total `<td>` count per data
row is 1 + 1 + 7 + 95 = 104 (name + type + 7 taxonomy + 95 remaining
cells).

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
| 76 | `eval-langsmith-evals`  | `eval-langsmith-evals`| LangSmith Evals                  |
| 77 | `eval-braintrust`       | `eval-braintrust`     | Braintrust                       |
| 78 | `eval-weights-and-biases-agent` | `eval-weights-and-biases-agent` | W&B Agent Eval         |
| 79 | `eval-helicone-evals`   | `eval-helicone-evals` | Helicone Evals                   |
| 80 | `eval-custom-test-harness` | `eval-custom-test-harness` | Custom test harness        |
| 81 | `eval-human-loop`       | `eval-human-loop`     | Human-in-loop eval               |
| 82 | `eval-production-traffic-replay` | `eval-production-traffic-replay` | Prod traffic replay |
| 83 | `commit-trajectory`     | `commit-trajectory`   | Commit trajectory                |
| 84 | `citation-trajectory`   | `citation-trajectory` | Citation trajectory              |
| 85 | `download-trajectory`   | `download-trajectory` | Download trajectory              |

The `cells` object MUST contain all 85 keys for every record. Records
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

### 2.5.3 Eval-tooling columns (added in T1-2, issue #40)

The seven `eval-*` columns capture which evaluation / scoring tools each
product or framework integrates with. They were added because the eval
gap is the **next frontier after observability**: LangChain's State of
Agent Engineering 2025 survey found that 89% of practitioners have
observability adopted but only **52% have evals** — an explicit 37-point
gap. The Berkeley RDI MAP study (Q1 2026) corroborates: 74% rely
primarily on human evaluation. The Datadog 2026 State-of-AI-Agents
report calls "reliable evaluation loops" a top recommendation. The
catalog-level question "how do I know if my agent is actually getting
better?" had no good answer before T1-2 — these columns answer the
integration-support half of it (benchmark methodology comparison is
T1-4 territory).

Each cell carries a `{value, citation, status, tier}`. The `value` is
one of `"yes"`, `"no"`, or `""` (empty = unknown, surfaced via the
standard `no-data` / `depth-floor-reached` status). Boolean cells MAY
also carry a version string (e.g. `"yes (Braintrust SDK v0.0.x)"`) when
the integration is gated on a specific release.

Column semantics:

| Slug                                 | Meaning                                                                                                                  |
|--------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `eval-langsmith-evals`               | LangSmith Evals integration (LangChain ecosystem's eval framework — datasets, evaluators, regression detection).         |
| `eval-braintrust`                    | Braintrust integration (independent eval platform — proxy, scoring, experiments).                                        |
| `eval-weights-and-biases-agent`      | Weights & Biases Agent Eval / Weave eval support (W&B's agentic evaluation suite).                                       |
| `eval-helicone-evals`                | Helicone's eval features (request-level evaluations, custom evaluators via OpenLLMetry).                                 |
| `eval-custom-test-harness`           | Built-in test or eval harness, regardless of vendor (framework ships its own; e.g. DSPy Evaluate, LangGraph testing).    |
| `eval-human-loop`                    | Human-in-loop eval workflow built in — manual review queue, annotation UI, expert grading integrated with the system.   |
| `eval-production-traffic-replay`     | Ability to replay production traffic against new agent versions for eval (e.g. capture-replay, golden-set from prod).    |

Coverage callout: only the top ~100 rows (the same selection as T1-1
observability and T1-3 cost-economics — T1 + select T2 in priority
sections) have been backfilled. Empty `eval-*` cells on rows below the
coverage floor are deliberate; the `/analyses/eval-gap` view surfaces
the observability-vs-eval gap directly and the coverage gap rather than
papering over either.

Out of scope: eval methodology comparison (eg. LLM-as-judge vs human
rubric vs canary set), benchmark scores (those are T1-4 territory).
These columns track *integration support* only — which products plug
into which eval tooling.

### 2.5.4 Commit-trajectory column (added in T3-prep-1, issue #50)

The single `commit-trajectory` column carries a per-row monthly
cumulative-commit-count time series, fetched from the GitHub Commits
API. It was added to backfill temporal signal for the S-curve maturity
fit (T2-4, issue #47), which previously could fit only 15.7% of rows
because most records lacked a per-quarter cumulative history. With a
real commit trajectory we get a monthly granularity series spanning the
project's life, which fits the logistic far more honestly than the
piecewise synthetic series used as a fallback.

The `value` field is a JSON-stringified array of `{ym, cum}` objects in
chronological order, one per calendar month from the repo's first
commit to its most recent:

```json
[
  {"ym": "2023-01", "cum": 4},
  {"ym": "2023-02", "cum": 11},
  {"ym": "2023-03", "cum": 23},
  ...
]
```

- `ym` is a `YYYY-MM` string. Months with zero commits MAY be omitted —
  the cumulative value in the next present month encodes the gap, so
  consumers MUST treat the series as a sparse cumulative growth curve
  rather than a dense per-month delta.
- `cum` is the cumulative commit count to the end of that month
  (running total over the project's lifetime, never decreasing).

Status semantics:

| `status`              | Meaning                                                                                                | `value`               | `citation`                            |
|-----------------------|--------------------------------------------------------------------------------------------------------|-----------------------|---------------------------------------|
| `real-data`           | Trajectory fetched OK.                                                                                  | JSON-stringified array | `https://github.com/<owner>/<repo>`  |
| `depth-floor-reached` | Fetch failed (404 / archived-with-no-history / rate-limited-after-retry / private repo).                | `""`                  | The attempted GitHub URL              |
| `not-applicable`      | Row has no `repo-url` cell (research paper without code, theoretical entry, benchmark without repo).    | The N/A annotation     | `null`                                |

Tier semantics:

- `real-data` cells are T1 (auto-verifiable — the same API call can be
  re-run to produce the same data; the `citation` is the GitHub URL).
- `depth-floor-reached` cells are T3 (no auto-verifiable signal; future
  work could retry against a less-bottlenecked auth context).
- `not-applicable` cells are T3 (a maintainer judgement that this row
  has no GitHub repo to fetch — paper-only rows, theoretical entries).

The fetch script lives at `scripts/fetch_commit_trajectories.py` and
runs via `make refresh-commit-trajectories` (slow, network-dependent —
similar to `make refresh-citations`). Raw API responses are cached
under `extraction/commit-cache/<owner>__<repo>.json` so deterministic
rebuilds with `make build` work offline against the committed cache.

Coverage callout: only rows with a parseable GitHub repo URL (the same
~230 rows the staleness CI walks) are eligible for `real-data`. All
other rows are `not-applicable`. The S-curve view picks up these
trajectories automatically (preferring them over the synthesised
piecewise series used by T2-4 before this column existed) — see
`web/src/lib/analyses/s-curve.ts`.

Out of scope:
- Per-quarter granularity (monthly is enough resolution for the S-curve
  fit; per-quarter aggregation is trivial downstream).
- Star history (separate signal, separate API path, deferred to a
  follow-up if needed).
- Issue / PR activity counts.

### 2.5.5 Citation-trajectory column (added in T3-prep-2, issue #51)

The single `citation-trajectory` column carries a per-row yearly
cumulative-inbound-citation time series for academic-paper rows,
reconstructed offline from `extraction/s2-cache/`. It was added as the
research-paper counterpart to `commit-trajectory` — the S-curve maturity
fit (T2-4, issue #47) previously had to synthesise a piecewise series
for every paper from `(total cites, cites/yr, publication date)`. With
a real yearly trajectory we get a non-decreasing cumulative curve
spanning the paper's life, which fits the logistic far more honestly
than the linear-then-tail interpolation the fallback uses.

The trajectory is **within-catalog inbound citations only** — for each
target record T, we count the catalog rows C that have T in their S2
references-out cache, grouped by C's publication year (extracted from
C's arxiv id-suffix). This gives a deterministic, cache-derived signal
that requires no network calls. The fetch script for the underlying
S2 cache lives at `scripts/fetch_citations.py` / `make refresh-citations`;
the offline bucketing script lives at `scripts/bucket_s2_citations.py`
and runs as part of `make build`.

The `value` field is a JSON-stringified array of `{year, cum, infl}`
objects in chronological order:

```json
[
  {"year": 2023, "cum": 3, "infl": 1},
  {"year": 2024, "cum": 11, "infl": 5},
  {"year": 2025, "cum": 28, "infl": 9},
  {"year": 2026, "cum": 35, "infl": 11}
]
```

- `year` is a calendar year (integer). Years with zero new citations
  MAY be omitted; the cumulative value in the next present year carries
  the gap forward.
- `cum` is the cumulative count of all inbound citing-papers from the
  catalog through the end of that year (running total over the paper's
  lifetime, never decreasing).
- `infl` is the cumulative count restricted to citing-papers where S2
  flagged the citation as `isInfluential: true` (Wang/Song/Barabási
  show influential citations are more predictive of long-term impact
  than raw count). Always `infl <= cum`.

Status semantics:

| `status`              | Meaning                                                                                                                  | `value`                | `citation`                                                |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------|------------------------|-----------------------------------------------------------|
| `real-data`           | Paper has an S2 cache file; trajectory built from cached references-out across the catalog. May be `[]` if no inbound.    | JSON-stringified array | `https://www.semanticscholar.org/paper/<paperId>`         |
| `depth-floor-reached` | Paper has cache file but parse / resolution failed (corrupt cache, no externalIds, etc.).                                 | `""`                   | The S2 paper URL that was attempted                       |
| `not-applicable`      | Row is not an academic paper (no arxiv URL, no DOI, no S2 paper hash — e.g. commercial product, blog post, OSS framework). | The N/A annotation     | `null`                                                    |

Tier semantics:

- `real-data` cells are T2 (citation is the S2 paper URL — semi-verifiable;
  re-running `make refresh-citations` against live S2 plus the bucket
  script will reproduce the trajectory).
- `depth-floor-reached` cells are T3 (no auto-verifiable signal).
- `not-applicable` cells are T3 (maintainer judgement that this row
  has no S2 paper to bucket).

Coverage callout: only rows with a parseable arxiv URL or S2 hash and
a populated cache file (~230 of 912 rows) are eligible for `real-data`.
A trajectory of `[]` (empty array) is a valid `real-data` value — it
means "we know about this paper, no in-catalog citations yet." All
non-paper rows are `not-applicable`. The S-curve view picks up these
trajectories automatically — see `web/src/lib/analyses/s-curve.ts`.

Out of scope:
- Citations from outside the catalog (would require a different S2
  endpoint and ~10x more API calls).
- Per-month granularity (S2 references don't carry month resolution
  consistently; arxiv IDs encode YYMM but the year alone is enough
  signal for the S-curve fit on papers, which typically have <8 years
  of citation history).
- Citation velocity / acceleration features (those are Tier 3 modeling
  work, not catalog data).

### 2.5.6 Download-trajectory column (added in T3-prep-3, issue #52)

The single `download-trajectory` column carries a per-row monthly
cumulative-download time series for library / SDK rows that publish to
NPM or PyPI. It was added as the third T3-prep adoption signal — paired
with `commit-trajectory` (real GitHub activity) and `citation-trajectory`
(real academic uptake) it gives the S-curve maturity fit (T2-4, issue
#47) a clean monotonic adoption curve for OSS libraries that ship as
installable packages.

Download trajectories are typically the **smoothest, fit-friendliest
signal** we have for OSS libraries — packages get installed in
production CI / dev loops at a rate that swamps stargazer noise and
isn't driven by the bursty issue / PR churn that commit counts pick up.

The `value` field is a JSON-stringified array of `{ym, monthly, cum}`
objects in chronological order, one per calendar month from the
package's first observed downloads to the most recent full month:

```json
[
  {"ym": "2024-01", "monthly": 42000, "cum": 42000},
  {"ym": "2024-02", "monthly": 58000, "cum": 100000},
  {"ym": "2024-03", "monthly": 71000, "cum": 171000},
  ...
]
```

- `ym` is a `YYYY-MM` string. Months with zero downloads MAY be omitted
  — the cumulative value in the next present month encodes the gap, so
  consumers MUST treat the series as a sparse cumulative growth curve
  rather than a dense per-month delta.
- `monthly` is the count of downloads in that month (integer ≥ 0).
- `cum` is the cumulative download count to the end of that month
  (running total over the package's observed lifetime, never decreasing).

For rows that ship both NPM **and** PyPI packages, the column carries
the **higher-traffic** of the two (typical pattern: a Python core
library with a much smaller JS wrapper, or vice versa). The `citation`
field disambiguates which source was chosen. Cross-source aggregation
is out of scope — NPM and PyPI count different audiences and combining
them would mix populations.

Status semantics:

| `status`              | Meaning                                                                                                | `value`                | `citation`                                                  |
|-----------------------|--------------------------------------------------------------------------------------------------------|------------------------|-------------------------------------------------------------|
| `real-data`           | Trajectory fetched OK.                                                                                  | JSON-stringified array | `https://www.npmjs.com/package/<name>` or `https://pypi.org/project/<name>/` |
| `depth-floor-reached` | Detected as a library but package-not-found / removed / yanked / fetch failure after retry.             | `""`                   | The attempted package URL                                   |
| `not-applicable`      | Row isn't a library / SDK (no NPM nor PyPI publication — research paper, hosted service, hardware).     | The N/A annotation     | `null`                                                      |

Tier semantics:

- `real-data` cells are T2 (citation is the package URL on the relevant
  registry — semi-verifiable; re-running `make refresh-download-trajectories`
  against live NPM / PyPI APIs will reproduce the trajectory. T1 is
  reserved for GitHub URLs per §3a; broadening T1 to package registries
  is deliberately out of scope for this column).
- `depth-floor-reached` cells are T2 (the citation is the attempted
  registry URL — still semi-verifiable: future work can retry against a
  different registry or relax the detection heuristics).
- `not-applicable` cells are T3 (a maintainer judgement that this row
  doesn't publish a package — paper-only rows, theoretical entries,
  hosted-only commercial products).

The fetch script lives at `scripts/fetch_download_trajectories.py` and
runs via `make refresh-download-trajectories` (slow, network-dependent
— similar to `make refresh-citations` and `make refresh-commit-trajectories`).
Raw API responses are cached under `extraction/download-cache/<source>__<sanitized-name>.json`
so deterministic rebuilds with `make build` work offline against the
committed cache.

Detection (in priority order):
1. Cell value or citation contains `npmjs.com/package/<name>` → NPM.
2. Cell value or citation contains `pypi.org/project/<name>/` → PyPI.
3. Cell value or citation contains `pip install <name>` (Python keyword)
   → PyPI, with the captured `<name>`.
4. Cell value or citation contains `npm install <name>` (JS keyword)
   → NPM, with the captured `<name>`.
5. A curated `KNOWN_PACKAGES` mapping (record-id → (source, name))
   for ambiguous / unstated cases where the catalog says e.g. "Mem0"
   without spelling out that `pip install mem0ai` is the install path.
   This is the largest source of coverage in practice.

Out of scope:
- GitHub release / version-specific download counts (different signal
  — package-manager downloads dominate post-publication).
- Crates.io / RubyGems / Go-module downloads (NPM + PyPI cover the
  bulk of catalog libraries; other registries are a follow-up).
- Geographic / region breakdowns.
- Per-version popularity (latest-N popularity is volatile and not what
  the cumulative S-curve cares about).

### 2.5.7 Normalized cost columns (added in Phase 2 / Gate 1, issue #95)

Five cells covering the cost-economics axis used by the
positioning recommender (`/recommend/between`, see
[`PHASE_2_SPEC.html`](../PHASE_2_SPEC.html) §3.1, §4.2):

| # | Column slug                  | Meaning                                                                                   |
|---|------------------------------|-------------------------------------------------------------------------------------------|
| 86 | `cost-input-usd-per-mtok`   | Public list price in USD per million input tokens. `value` is the stringified number.     |
| 87 | `cost-output-usd-per-mtok`  | Same for output tokens.                                                                   |
| 88 | `cost-tier`                 | Derived bucket: `free` \| `budget` \| `mid` \| `premium`. Recomputed nightly.            |
| 89 | `cost-pricing-model`        | Enum: `per-token` \| `per-request` \| `subscription` \| `self-hosted` \| `free-tier`.    |
| 90 | `cost-last-verified`        | ISO date of last vendor-pricing-page scrape.                                              |

Each cell carries the standard `{value, citation, status, tier}`
envelope (§2.5). `not-applicable` is the right status for research
papers and self-hosted-only systems; cost cells are skip-eligible per
PHASE_2_SPEC §3.1.

### 2.5.8 Capability tier columns (added in Phase 2 / Gate 1, issue #95)

Four cells covering the capability axis (PHASE_2_SPEC §3.2):

| # | Column slug                       | Meaning                                                                          |
|---|-----------------------------------|----------------------------------------------------------------------------------|
| 91 | `capability-composite-score`     | Weighted composite (0–100) across code / agentic reasoning / long-context.      |
| 92 | `capability-band`                | Derived bucket: `entry` \| `competent` \| `frontier`.                            |
| 93 | `capability-benchmark-sources`   | Array of `{benchmark, score, run_date, source_url}`. `value` is JSON-stringified.|
| 94 | `capability-last-verified`       | ISO date of last quarterly recalibration run.                                    |

The composite draws on the `benchmark-trust` analytical view's vetted
benchmark sources — not a new trust-evaluation pass.

### 2.5.9 Use-case suitability columns (added in Phase 2 / Gate 1, issue #95)

Two cells covering the constraint-matching axis (PHASE_2_SPEC §3.3):

| # | Column slug              | Meaning                                                                                                |
|---|--------------------------|--------------------------------------------------------------------------------------------------------|
| 95 | `use-case-tags`         | Multi-select from the controlled vocabulary (8 tags as of 2026-06-29). `value` is JSON-stringified.   |
| 96 | `use-case-anti-tags`    | Explicit "do not use for" tags from the same vocabulary. Equally load-bearing for ranking.            |

**Initial controlled vocabulary:** `scoped-agentic`,
`long-running-session`, `multi-agent-coordination`,
`memory-augmented-chat`, `code-generation-focused`,
`analytical-summarization`, `latency-sensitive`, `offline-capable`.

Growth thresholds (PHASE_2_SPEC §3.3): monitor at 10% catalog
membership, promote-to-hierarchy at 20%.

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

## 3b. Catalog freshness (`last_verified_at`)

Issue #54 added explicit row-level and per-cell freshness timestamps so
consumers can answer "is this claim still likely to be true?" without
inspecting git history. Honest catalogs caveat their freshness; this is
the cheapest, most direct user-facing signal of catalog quality.

### Row-level `last_verified_at`

Every record carries a `last_verified_at` field at the top level
(alongside `id`, `name`, `tier`):

```typescript
type LandscapeRecord = {
  id: string;
  name: string;
  tier: 1 | 2 | 3 | 4 | 5;
  url: string | null;
  last_verified_at: string;  // ISO date "YYYY-MM-DD"
  sections: SectionMembership[];
  taxonomy: Taxonomy;
  cells: Cells;
};
```

The row-level date represents "the most recent commit that modified any
part of this row's `<tr>` block." It is the **inherited default** for
every cell in the row: a cell with no per-cell `last_verified_at` is
considered verified as of the row-level date.

### Per-cell `last_verified_at` (high-volatility only)

For high-volatility cells, the per-cell `Cell` shape extends to:

```typescript
type Cell = {
  value: string;
  citation: string | null;
  status: Status;
  tier: ClaimTier;
  last_verified_at?: string;  // ISO date — present only on volatile cells
};
```

The per-cell field, **when present, overrides** the row-level date for
that cell. When absent, the cell inherits the row-level date.

### Volatile cell set (per-cell `last_verified_at` enabled)

The following column slugs are considered high-volatility and therefore
carry per-cell `last_verified_at`. All other slugs inherit the row
date.

| Group                              | Column slugs                                                                                                   |
|------------------------------------|----------------------------------------------------------------------------------------------------------------|
| Lifecycle / release dates          | `created`, `latest-release`                                                                                    |
| Adoption / inbound signals         | `gh` (star count + last-commit date), `mindshare`, `citations`                                                 |
| Funding state                      | `funding`                                                                                                      |
| Benchmark scores                   | `vendor-benchmarks`                                                                                            |
| Observability integrations (8)     | `obs-langsmith`, `obs-opentelemetry`, `obs-datadog`, `obs-helicone`, `obs-weave`, `obs-langfuse`, `obs-arize`, `obs-custom` |
| Cost-control features (7)          | `cost-token-budget`, `cost-prompt-caching`, `cost-semantic-caching`, `cost-batching`, `cost-model-routing`, `cost-streaming-only`, `cost-observability-cost-attribution` |
| Eval-tooling integrations (7)      | `eval-langsmith-evals`, `eval-braintrust`, `eval-weights-and-biases-agent`, `eval-helicone-evals`, `eval-custom-test-harness`, `eval-human-loop`, `eval-production-traffic-replay` |
| Trajectory time-series             | `commit-trajectory`, `citation-trajectory`, `download-trajectory`                                              |

That's 32 volatile cell slugs in total. The remaining 53 slugs
(taxonomy axes, license, primary URL, descriptions, etc.) are
low-volatility and inherit the row-level date.

### HTML representation

In `landscape.html`, the timestamps live as attributes:

```html
<tr class="row-t1" data-last-verified="2026-05-14">
  <td class="vendor-benchmarks" data-last-verified="2026-05-12">…</td>
</tr>
```

`scripts/extract.py` reads these attributes and projects them into
`record.last_verified_at` (row-level) and `cell.last_verified_at`
(per-cell, only on volatile cells). `scripts/render.py` emits them
when present and omits them when absent. The cycle gate
(`scripts/validate.py` gate 3) enforces round-trip stability of the
attributes.

### Initial backfill

`scripts/backfill_verified_at.py` populates `landscape.html` with the
initial dates derived from `git blame -p landscape.html`. The row-level
date is the *latest* blame date across every line in the `<tr>` block.
The per-cell date for a volatile cell is the blame date of that cell's
specific line.

Re-running the backfill is idempotent for unmodified rows: blame dates
stay attributed to the most recent meaningful commit, even if the only
change is the `data-last-verified` attribute itself.

### Validation

`scripts/validate.py` gate 5 also validates:

- Every record MUST have `last_verified_at` matching `^\d{4}-\d{2}-\d{2}$`.
- Volatile cells MAY have `last_verified_at`; when present it MUST
  match the same regex.
- The build does NOT fail on stale rows. Stale rows are reported as an
  informational metric (counts in four freshness buckets):
    - **fresh** — verified < 6 months ago
    - **aging** — 6-12 months
    - **stale** — 12-24 months
    - **very stale** — ≥ 24 months

Surfacing the metric rather than failing the build keeps the freshness
signal honest without forcing maintainers to re-verify on every commit.

---

## 3c. Decay-cause forensics (issue #56)

Issue #56 added three record-level fields so consumers can distinguish
*why* a stale or abandoned row stopped shipping. The dichotomy
"active vs. abandoned" is too coarse for downstream prediction — an
acquisition is a clean exit, a paper superseded by its own authors is
intellectual progress, an unfunded vendor is a market signal. The three
fields below capture that distinction.

The fields are **record-level**, not cell-level: they live at the top
of each `LandscapeRecord` alongside `id`, `name`, `tier`, and
`last_verified_at`, mirroring the row-level shape of §3b.

```typescript
type LandscapeRecord = {
  id: string;
  name: string;
  tier: 1 | 2 | 3 | 4 | 5;
  url: string | null;
  last_verified_at: string;
  // Decay-cause forensics (issue #56) — empty / absent for active rows.
  decay_cause?: DecayCause;     // enum, see below
  decay_date?: string;          // ISO YYYY-MM-DD, optional
  decay_evidence?: string;      // URL or "[unverifiable] <free-text>"
  sections: SectionMembership[];
  taxonomy: Taxonomy;
  cells: Cells;
};

type DecayCause =
  | "acquired"
  | "pivoted"
  | "unfunded"
  | "lost-benchmark-race"
  | "superseded"
  | "archived"
  | "research-complete"
  | "unknown";
```

### Enum values

| Value                  | When to use                                                                                                                                                                                                  | Typical evidence                                              |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| `acquired`             | Company / project was bought by another vendor. The product may continue under new branding or fold into the acquirer's stack.                                                                               | TechCrunch / Crunchbase acquisition page, press release.      |
| `pivoted`              | Team moved to a different product space. The original artefact remains in catalog history but is no longer the team's focus.                                                                                 | Founder tweet / blog post, new product page, GitHub redirect. |
| `unfunded`             | Funding ran out, no acquisition. Long inactivity + LinkedIn changes + lack of recent funding round; commercial-only.                                                                                         | Wayback Machine showing primary URL dark for >6 months, HN obit thread, "ceased operations" post. |
| `lost-benchmark-race`  | Outpaced by a clearly better system in the same niche. The row's claims still hold, but no one would adopt it today.                                                                                          | Benchmark scores trailing competitors over time, comparison posts. |
| `superseded`           | Academic-paper variant: authors published a follow-up paper that replaces this one. The follow-up cites this row as prior work.                                                                              | S2 cache showing later paper by overlapping authors that cites this one. |
| `archived`             | Explicit `archived: true` on the GitHub repo. The mechanical signal we trust most — the project's maintainers explicitly flagged it.                                                                          | GitHub repo URL (the `/archived` indicator is visible on the page). |
| `research-complete`    | Academic-paper variant where the artefact IS the paper and no maintained software was ever intended (e.g. arXiv-only releases, conference workshop pieces, one-shot research demos). The row isn't "decayed" in a market sense — it shipped, did its job, and the team moved on. Distinct from `superseded` (which requires a specific follow-up paper) and `unknown` (which signals exhausted research). | A URL to the arXiv / paper page; or `[unverifiable] research paper; no maintained codebase intended`; or any explicit "research-only" attribution. |
| `unknown`              | Researched but no clear cause found. Honest acknowledgement, not a placeholder. Used when the row is plausibly stale but the researcher exhausted the priority sources without resolution.                  | `decay_evidence` records what was searched: e.g. `"[unverifiable] researched: techcrunch, vbeat, hn algolia, wayback; no clear cause found"`. |

### When to populate

- **Active rows** (status not `stale` or `abandoned` per the survivorship
  classifier in `web/src/lib/analyses/survivorship.ts`): the three
  fields MUST be absent or empty. An active row with a `decay_cause`
  is a contradiction — `scripts/validate.py` rejects it.
- **Stale / abandoned rows**: the three fields SHOULD be populated. The
  validator emits a *warning* (not failure) for stale/abandoned rows
  without a `decay_cause`; this lets the backfill land incrementally
  without blocking the build.

### Evidence-URL conventions

- Prefer a resolvable `http(s)://` URL. Treated as a T2-equivalent
  citation for downstream provenance reasoning.
- For unverifiable evidence (e.g. the original landing page is
  Wayback-only, the only mention is a deleted tweet), use a free-text
  string prefixed with `[unverifiable] ` — e.g.
  `"[unverifiable] LinkedIn shows team scattered to FAANG roles 2024-Q3"`.
- For `archived`: evidence MUST be the GitHub repo URL (the source of
  truth for the `archived: true` flag).

### HTML representation

In `landscape.html`, the three fields live as `<tr>` attributes
alongside `data-last-verified`:

```html
<tr class="row-t1"
    data-last-verified="2026-05-14"
    data-decay-cause="acquired"
    data-decay-date="2024-03-15"
    data-decay-evidence="https://techcrunch.com/2024/03/14/...">
  …
</tr>
```

Empty / absent attributes mean "active row, no decay." `extract.py`
reads these attributes and projects them into the JSON; `render.py`
emits them when present and omits them when absent. The cycle gate
(`scripts/validate.py` gate 3) enforces round-trip stability.

### Backfill workflow

`scripts/research_decay_causes.py` runs the backfill in three phases:

1. **Phase C — archive-flag sweep** (cheapest): for every row with a
   GitHub repo URL, hit `GET /repos/{owner}/{repo}` and check
   `archived`. Mark `archived` with the repo URL as evidence.
2. **Phase A — commercial products** (research-heavy): for stale /
   abandoned rows in commercial sections, search TechCrunch /
   VentureBeat / HN Algolia / Wayback Machine in priority order.
   Hard 2-minute budget per row; mark `unknown` if unresolved.
3. **Phase B — academic papers**: for stale / abandoned rows in
   research sections, search the S2 cache for follow-up papers by the
   same authors. The dominant cause here is `superseded`.

The per-row research output is cached under
`extraction/decay-cause-cache/<row-id>.json` so reruns are deterministic
and skip already-resolved rows.

### Validation

`scripts/validate.py` gate 5 also validates:

- `decay_cause`, when present, MUST be one of the eight enum values.
- `decay_date`, when present, MUST match `^\d{4}-\d{2}-\d{2}$`.
- `decay_evidence`, when present, MUST be a string (URL or
  `[unverifiable] …` prose).
- Active rows MUST have empty decay fields (hard failure).
- Stale / abandoned rows SHOULD have non-empty `decay_cause` (soft
  warning — informational metric, not a build break).

The validator also surfaces an informational distribution count
("acquired=A pivoted=P unfunded=U lost-benchmark-race=L superseded=S
archived=Ar research-complete=Rc unknown=X"). This is the seed metric
for the Tier 3 mortality-cause prediction work.

### MCP / CLI exposure

`find_by_decay_cause(cause)` returns the compact-summary list of all
records with the given decay cause (one of the eight enum values).
Available as an MCP tool and as the `landscape decay-cause <cause>` CLI
subcommand. Mirrors the existing nine-tool surface — same `RecordSummary`
shape, same JSON / CSV options.

---

## 3d. Per-cell provenance (`_provenance` — Phase 2 / Gate 1, issue #95)

Tier (§3a) captures *what kind of claim* a cell is (auto-verifiable, sourced,
estimate). Provenance is the orthogonal axis: *who or what put this value
here, and has a human confirmed it?* The recommender's defensibility
depends on being able to answer the second question for any cell that
ends up in a ranking rationale, so an LLM-generated guess cannot
masquerade as a curated fact.

See [`PHASE_2_SPEC.html`](../PHASE_2_SPEC.html) §3.4 for the full
motivation and surface-rendering rules.

### Shape

Each record carries an optional `_provenance` object keyed by cell slug
(the same kebab-case keys used in `cells`):

```typescript
type CellProvenance =
  | { source: "human";  verified: boolean; author: string;       edited_at: string; }
  | { source: "scrape"; verified: boolean; scraped_at: string;   scrape_url: string; script?: string; }
  | { source: "llm";    verified: boolean; generated_at: string; model_id?: string; }
  | { source: "legacy"; verified: true; };

type Record = {
  // ... id, name, tier, url, sections, taxonomy, cells ...
  _provenance?: { [cellSlug: string]: CellProvenance };
};
```

Phase 1 of Gate 1 (this PR) introduces the field as `{}` on every row.
Phases 2-4 backfill entries.

### Source enum

| Source | When it applies | Required fields |
|--------|-----------------|-----------------|
| `human`  | Cell was authored or last-edited by a person (PR or web form). | `author` (handle), `edited_at` (ISO date). |
| `scrape` | Cell was mechanically derived (GitHub API, arXiv API, vendor pricing-page extraction, etc.). | `scraped_at` (ISO date), `scrape_url` (the URL the value came from), optional `script` (relative path of the writing script). |
| `llm`    | Cell was suggested by an LLM during intake enrichment. | `generated_at` (ISO date), optional `model_id`. |
| `legacy` | Cell predates the provenance model — assigned during Gate 1's existing-cell backfill for the 85 pre-Phase-2 cells. | `verified: true` is fixed (legacy cells were trusted catalog state before Phase 2 began). |

### Verification rules

- **Every cell is fillable by LLM enrichment.** No cell is off-limits
  to `source: "llm"` if mechanical extraction fails — including cost
  cells. The `verified` bit, not the source, controls load-bearing-ness.
- **`source: "llm"` is always surfaced.** Web UI shows an
  "LLM, unverified" badge; MCP tool responses include it in the
  `caveats` array; CLI prints it inline.
- **Unverified LLM cells are non-load-bearing for ranking.**
  `rank_candidates()` excludes cells with `source: "llm",
  verified: false` from score calculation. They appear in the
  candidate's profile but cannot influence position; the rationale
  explicitly notes when a cell was skipped for this reason.
- **Verification flips the bit, not the value.** A human reviewing an
  LLM cell either edits it (changing source to `human`) or sets
  `verified: true` with their handle. Verified-LLM cells become
  load-bearing.
- **Scraped cells are verified-by-default.** Mechanical extraction
  with a stored `scrape_url` is treated as load-bearing without
  separate human sign-off; the staleness pipeline (gates 6 + 8)
  catches drift.
- **Legacy cells are verified-by-default.** Same rationale — they
  were already in the catalog and trusted before the provenance
  model existed.

### HTML carrier

Each `<td>` may carry a `data-provenance="..."` attribute whose value is
the cell's provenance entry encoded as compact JSON
(`json.dumps(entry, sort_keys=True, separators=(",", ":"))`).
Cells without an entry emit no attribute, so cost / capability / use-case
cells stay carrier-free until Phases 3 & 4 of Gate 1 populate them.

`render.py` emits the attribute; `extract.py` recovers the entry via
`parse_provenance_attr()`. Fields inside the JSON are alphabetized (the
serializer's `sort_keys=True`); cell-slug keys in the `_provenance` dict
follow `cells` iteration order. Both orderings are required for the
round-trip cycle (gate 2) to remain byte-stable.

### Backfill state (Gate 1, Phases 2-4 — complete)

- **Phase 2** (`scripts/phase_2_provenance_backfill.py`) populated entries
  for every claim-bearing pre-Phase-2 cell. Default source is `legacy`.
  The three trajectory cells (`commit-trajectory`, `citation-trajectory`,
  `download-trajectory`) are upgraded to `source: "scrape"` when the cell
  carries a usable http(s) citation, with `script` pointing at the
  identified writer in `scripts/`. Cells with `status: "no-data"` carry
  no claim and have no entry.
- **Phase 3** (`scripts/phase_2_cost_mechanical_fill.py`) filled the 5
  new cost cells (§2.5.7) for 773/912 records mechanically by leveraging
  the existing `pricing` cell:
    - 543 rows propagated from `pricing.status` ∈ {not-applicable,
      depth-floor-reached} → cost cells mirror the same status.
    - 163 rows pattern-matched as free/OSS → `cost-tier: "free"`,
      `cost-pricing-model: "free-tier"`.
    - 66 rows pattern-matched as subscription/per-seat/enterprise →
      `cost-pricing-model: "subscription"`, per-token cells `not-applicable`.
    - 1 row pattern-matched as self-hosted-only.
    - Remaining 139 rows (mixed-pricing prose, numeric per-token text)
      are left at `no-data` for Phase 4 LLM fill.
- **Phase 4** (`scripts/phase_2_llm_fill_apply.py` + parallel sub-agents)
  filled the remaining 11 Phase 2 cells via LLM judgment per
  PHASE_2_SPEC §3.5:
    - **4a** (pilot, 13 foundation-model rows × 4 capability cells = 52 cells).
    - **4b** (capability cells for the remaining 899 rows = 3,596 cells,
      14 batched parallel sub-agents). Status split: 475 `estimate`
      (runnable systems) + 437 `not-applicable` (infrastructure / research /
      benchmarks). Band distribution: 38 frontier / 407 competent / 30 entry.
    - **4c** (use-case-tags + use-case-anti-tags for all 912 rows =
      1,824 cells, 15 batched parallel sub-agents). Status split:
      500 / 485 `estimate` and 412 / 427 `not-applicable`. All positive
      tags drawn from the §3.3 controlled vocabulary.
    - **4d** (residual 139 cost rows × 5 cells = 695 cells, single
      sub-agent reading the existing `pricing` prose). All marked
      `source: "llm", verified: false, model_id: "claude-opus-4-7",
      generated_at: "2026-06-29"`. status `"estimate"` → claim-tier T3
      (citation not required by §3a); non-load-bearing for ranking per
      §3.4 until a human verifies.

End-state: zero `no-data` cells across all 11 Phase 2 slugs. Every
cell in `landscape.json` has a populated `_provenance` entry covering
all 85 pre-Phase-2 cells + 11 new Phase 2 cells = ~85,000 provenance
entries across the catalog.

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

### Edge type enum (10 values)

| `type`               | Direction semantics (source → target)                                                                                    | Typical evidence source                                       |
|----------------------|--------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| `built-on`           | source's product is implemented on top of target's product (target is a dependency or runtime).                           | `desc`/`adjacent-infrastructure` cell mining                  |
| `runtime-dependency` | source explicitly requires target at runtime to function (target is a substrate, model, or library that source is built on). Distinct from `built-on` (broader, architectural lineage) and `integrates-with` (looser, optional integration). MUST point from the consumer (source) to the substrate (target). | cell-text mining: `powered by`, `built on`, `built with`, `requires`, `depends on`, `runs on`, `uses` + provider/memory/framework substrate alias table |
| `extends`            | source extends or generalises target's method (paper-to-paper or product-to-product), keeping target's core idea.         | paper abstracts, product changelogs                           |
| `forks`              | source is a literal code fork of target.                                                                                 | GitHub fork relationships, README acknowledgements            |
| `integrates-with`    | source has an integration / connector / first-class adapter to target. Symmetric in spirit but stored directionally.      | docs, integration count cell, integration matrices            |
| `competes-with`      | source and target are positioned by the market (or by themselves) as alternatives in the same buyer's mind.               | comparison pages, vendor "vs" docs, analyst writeups          |
| `inspired-by`        | source explicitly cites target as conceptual inspiration without building on its code or extending its method directly.    | author posts, blog posts, talks                               |
| `cites`              | source's paper cites target's paper. The most common edge type, populated from Semantic Scholar.                          | Semantic Scholar API                                          |
| `same-team-as`       | source and target are by the same author / lab / company. Captures lineage where one team produces multiple systems.      | `founders` cell, paper authors, GitHub org                    |
| `succeeds`           | source is an explicit successor / next-version of target by the same team (e.g. MemGPT → Letta).                          | release notes, blog posts                                     |

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
    - `cells` has exactly the 85 keys listed in §2.5 (no extras, no missing).
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
6. **`type`** is one of the ten values in §4.
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
