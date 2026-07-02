# Capability composite — methodology

This document specifies how `capability-composite-score` is computed
from `capability-benchmark-sources`, and how `capability-band` is
derived from the composite. It is the source-of-truth for the score
that drives `rank_candidates()` anchor mode and informs every
recommender surface.

It is intentionally short and intentionally explicit — implicit
methodology is the failure mode this document exists to prevent.

**Last updated:** 2026-07-01
**Status:** Ratified by maintainer 2026-07-01 (all six §1.x
methodology decisions confirmed; band cutoff *values* held
provisional per §10 lock-on-data plan)
**Applies to:** `data/landscape.json` rows where Phase 2 capability
cells are non-null
**Implementation:** `mcp/src/composite.ts` (single source of truth);
mirrored to `web/src/lib/analyses/composite.ts` per existing
shared-analysis convention

---

## 1. Framing

We construct a single capability score per row by aggregating
benchmark-derived scores into three task families and then aggregating
families into a composite. The composite is a **descriptive index**,
not a leaderboard rank — its job is to support context-dependent
ranking inside `rank_candidates()`, not to declare an absolute winner.

The methodology follows the OECD/JRC *Handbook on Constructing
Composite Indicators* (2008) sequence:

1. Theoretical framework (§2)
2. Data selection (§3)
3. Imputation of missing data (§4)
4. Multivariate analysis — *skipped at current benchmark density; see §5*
5. Normalisation (§6)
6. Weighting and aggregation (§7)
7. Robustness and sensitivity analysis (§8)
8. Deconstruction (§9 — per-family scores are first-class outputs)

Each section below records the explicit choice and the reason for it.
The reason matters more than the choice: a future maintainer can
revisit any of these decisions without re-deriving the framework, as
long as the next decision is also defended in this file.

---

## 2. Theoretical framework

Capability is decomposed into **three task families**, matching Phase
2 spec §3.2:

| Family       | Cell                              | What it measures                                                                                            |
|--------------|-----------------------------------|-------------------------------------------------------------------------------------------------------------|
| Code         | `capability-code-score`           | Coding assistance, refactoring, multi-file edits, IDE workflows. Anchor benchmarks: Aider Polyglot, SWE-Bench Verified, LiveCodeBench. |
| Agentic      | `capability-agentic-score`        | Tool use, planning, multi-step task completion in agent harnesses. Anchor benchmarks: GAIA, AgentBench, τ-bench, OSWorld.              |
| Long-context | `capability-longcontext-score`    | Recall and reasoning over 100k+ token inputs. Anchor benchmarks: RULER, LongBench-v2, "Needle in a Haystack" variants.                 |

Each family score is in [0, 100]. The composite, `capability-composite-score`,
is also in [0, 100].

**Why three, not more, not fewer.** Fewer than three (e.g. raw
benchmark averages without family clustering) loses interpretability
and lets a model strong on one benchmark dominate. More than three
(e.g. splitting long-context into "retrieval" and "reasoning")
introduces sparseness — most rows have benchmark data for at most
two of three families today; further fragmentation would make the
imputation problem (§4) dominate the methodology.

The three-family decomposition is also tractable to verify by hand
from a small panel of canonical benchmarks per family, which matters
for §8 cross-checks.

---

## 3. Data selection

For each row, the input data is **the contents of
`capability-benchmark-sources`** — an array of
`{benchmark, score, run_date, source_url}` records.

Benchmark eligibility is governed by **the existing `benchmark-trust`
view** (`web/src/lib/analyses/benchmark-trust.ts`), which already
emits a `trustScore` per benchmark. We do not maintain a parallel
benchmark trust list.

A benchmark is included in this composite if and only if:

1. Its `trustScore` (from `benchmark-trust.ts`) is ≥ 40 — the
   existing `medium` tier cutoff defined in `benchmark-trust.ts`
   (`tierFor`: high ≥ 70, medium ≥ 40, low < 40). Reusing the existing
   `medium` cutoff means we have exactly one place where benchmark
   trust is defined; no parallel threshold to keep in sync. This
   should be the **only** place benchmarks are filtered; no second
   filtering happens inside `composite.ts`.
2. It is classified into exactly one task family. The classification
   table lives at `docs/benchmark-families.yml` (created alongside
   this doc) and is a flat `benchmark_id → family` map. Unclassified
   benchmarks are ignored, not assigned a family by default — a
   benchmark with no clear family belongs in no family.
3. The most recent eligible score per row × benchmark is used; older
   scores on the same benchmark are dropped to avoid double-counting
   when methodology revisions produce a new number.

---

## 4. Imputation

**We do not impute.** If a task family has zero eligible benchmark
results for a row, that family's sub-score is `null`, and the row's
composite is computed over the present families only (§7).

Imputation is the part of OECD §3 most likely to introduce
indefensible numbers. The cheap alternative — set missing families to
the cross-row mean — would silently make the recommender favour rows
with thinner benchmark coverage (because their composite would be
pulled toward the dataset average rather than reflecting their actual
profile). Better to expose the gap.

Where coverage is null for **all three** families, the composite is
itself `null` and the row's `capability-band` is null. The recommender
already handles null capability cells (existing `recommender.ts`
guards on `d.capBand != null`).

---

## 5. Multivariate analysis — skipped

OECD §3 step 4 calls for factor / principal-component analysis to
verify the chosen family decomposition reflects covariance structure
in the data. We skip this step because at current density
(~50 distinct benchmarks across 912 rows, with most rows reporting on
0–3 benchmarks) factor analysis is statistically unstable and would
give a false sense of empirical grounding.

The decomposition in §2 is **asserted on theoretical grounds**, not
discovered. This is acceptable but should be revisited when benchmark
coverage density doubles (rough target: median row reports on ≥ 6
benchmarks across ≥ 2 families).

---

## 6. Normalisation

**Per-benchmark min-max to [0, 100]**, anchored at the catalog's
current maximum:

```
normalized(score) = clamp01((score - bench_min) / (bench_max - bench_min)) * 100
```

`bench_min` defaults to 0. `bench_max` is the highest recorded score
on that benchmark across the catalog at most-recent rebaseline
(`scripts/capability_rebaseline.py`), persisted to
`data/_baselines/benchmark-maxima.json`. This file is read by
`composite.ts`; if absent, `composite.ts` falls back to "max observed
in the current input set," logs a warning, and refuses to write to
landscape.json — only the read path tolerates the fallback.

**Why this, not z-score / rank-normal.** Min-max preserves intuitive
"how close to SOTA" interpretation; z-score makes inter-benchmark
comparison harder for a human reader; rank-normal loses the gap
between near-SOTA and SOTA, which is the gap users care about most
when choosing between models near the top.

**Why anchored to current SOTA, not all-time SOTA.** Catalog records
include retired and superseded models. Anchoring on current SOTA
keeps the "100 = best available today" interpretation valid as the
frontier advances.

**Refresh cadence.** Rebaseline of `bench_max` happens weekly, in
the existing `capability-rebaseline.yml` cron. New benchmarks (or
re-runs producing higher scores) are detected automatically; **all
historical composites are recomputed against the new ceiling on the
same run** — we do not freeze old rows against the previous week's
anchor. This is the OECD-recommended approach (§6 anchor refresh)
and matches HDI practice.

**Consequence: week-to-week composite drift.** A row's composite can
shift by a few points across rebaselines even when its own benchmark
data did not change, because a competitor pushed the ceiling. This
is honest but can confuse readers ("why did this drop?"). The weekly
rebaseline emits a drift summary to the FINDINGS doc — top 10 rows
by absolute composite change, with the responsible ceiling movement
named. UI surfaces should tooltip the drift when it exceeds ±3
points week-over-week.

---

## 7. Weighting and aggregation

### 7.1 Within-family — trust-weighted arithmetic mean

For each task family, the sub-score is:

```
family_score = sum_i (trust_i * normalized_i) / sum_i (trust_i)
```

over eligible benchmark results in that family for that row.
`trust_i` comes verbatim from `benchmark-trust.ts`.

**Why arithmetic, not geometric, within a family.** Benchmarks
inside a family are intended to measure the same underlying
construct. Variation between them is partly noise; arithmetic mean
smooths it. Geometric mean inside a family would over-penalise a
single low score from an outlier benchmark.

**Median fallback (explicit, not automatic).** If a family shows
`|median − trust-weighted mean| > 15` across the catalog at any
rebaseline, that is a signal one or more within-family benchmarks
is measuring something different from the rest. The rebaseline job
surfaces this in FINDINGS; the response is a maintainer review of
that family's benchmark set (drop the outlier, split the family, or
switch that family's aggregator to median). We do not silently swap
to median mid-run — the switch is a maintainer decision documented
in this file.

### 7.2 Across families — geometric mean

```
composite = (product_f family_score_f) ^ (1 / |present families|)
```

over the families where `family_score_f != null`.

**Why geometric.** A model that is frontier-tier on code but
entry-tier on long-context should not present as "competent overall."
Arithmetic mean lets one strong axis hide a weak axis; geometric mean
penalises imbalance. This is the same logic the UN Human Development
Index used to switch from arithmetic to geometric mean in 2010 (HDR
2010, methodological note) — the exact failure mode is the same.

**Special case: zero family scores.** A geometric mean across a set
containing zero collapses to zero. This is the intended behaviour —
a model with one demonstrated capability and zero on another is not
broadly capable. Documented here so it is not later "fixed" by
adding an epsilon or switching to arithmetic.

### 7.3 No inter-family weights

The cross-family geometric mean is equally weighted. We do not
introduce a vector of inter-family weights (e.g. `0.4 code + 0.3
agentic + 0.3 longcontext`). Reason: any choice would be arbitrary
and would be the first thing a reviewer questioned. Equal weighting
is the OECD-recommended default when no domain-specific
justification exists, and "all three families matter" is the only
domain claim we are prepared to defend.

Use-case-specific reweighting — "for this query, code matters more" —
belongs in `rank_candidates()` at query time, not in the composite.

---

## 8. Robustness and sensitivity

The two robustness checks are:

1. **Weight perturbation sweep.** Run `scripts/composite_sensitivity.py`
   (to be created alongside the migration that adds the sub-score
   cells) sweeping the inter-family weight vector through Dirichlet
   samples around `(1/3, 1/3, 1/3)` with concentration parameter
   α = 10. For each sample, rank all rows and record top-5 stability
   across the 55 entries in `docs/canonical-questions.yml`. Target:
   ≥ 90% of canonical questions show ≥ 4/5 overlap in top 5 across
   100 samples. Failures are documented in the rebaseline FINDINGS
   doc, not silently absorbed.

2. **Arena cross-check.** For the subset of rows that also appear in
   Chatbot Arena's leaderboard (foundation models, identifiable by
   matching `id` to a curated `data/arena-mapping.json`), compute
   Spearman ρ between our composite and Arena's Elo. Target:
   ρ ≥ 0.7 on the overlapping set. Lower correlation triggers a
   methodology re-review, not a "fix" of the cross-check itself.

Both checks run as part of the weekly rebaseline cron, with results
appended to `docs/FINDINGS-YYYY-MM-DD.md`. The composite is published
even when checks fail — but the failure is named, with row examples,
so readers know the score's load-bearing limits.

---

## 9. Deconstruction — per-family scores are first-class

The composite is a **sidekick**, not a headline. UI surfaces show the
three sub-scores prominently; the composite drops into tooltips and
serves as the recommender's sort key. This framing choice matters:
because the sub-scores are visible directly, users see imbalance
without needing the composite to punish it for them. That said, we
keep the geometric mean at §7.2 — as a sort key that penalises
imbalance, it still produces the ranking order we want, and the HDI
precedent stands.

Concretely, everywhere the composite is exposed the three sub-scores
(`capability-code-score`, `capability-agentic-score`,
`capability-longcontext-score`) are exposed with equal or greater
visual weight:

- **Web:** scatter plots and tables lead with sub-score columns.
  Composite appears as a tooltip / expandable row detail, not as the
  headline number. Compare page shows three side-by-side sub-score
  bars per model with composite as small caption text.
- **MCP:** `between_models` and `recommend_for_project` return
  `capability` as an object `{composite, code, agentic, longcontext}`,
  not a scalar. Clients that only render one number should render one
  of the sub-scores relevant to the query, not the composite.
- **CLI:** `landscape recommend` JSON output mirrors the MCP shape;
  human-readable output prints sub-scores first, composite last.

Per-cell provenance is tracked separately for each sub-score and the
composite. The composite's provenance points to the script /
methodology version that produced it, not to a benchmark URL —
the benchmark URLs are reachable via the sub-scores.

---

## 10. Band derivation

**Band shape (ratified):** three bands — `entry`, `competent`,
`frontier`, plus `null`. Names and count are stable across
rebaselines.

**Cutoff values (provisional until first sweep):**

```
entry        : composite ∈ [0,    50)
competent    : composite ∈ [50,   75)
frontier     : composite ∈ [75,   100]
null         : composite is null
```

Because normalisation anchors top = 100, these values have a direct
interpretation:

- `frontier` = "within 25 points of the current SOTA on the family
  axes the row reports."
- `competent` = "more than halfway from the floor to the SOTA."
- `entry` = "below the halfway mark — useful for narrow scoped tasks,
  not a general-purpose recommendation."

**Lock-on-data plan.** Cutoff values are held provisional until the
first full sweep produces a real composite distribution across the
catalog. At that point:

1. If the distribution is roughly thirds (each band holds 20–45% of
   ranked rows), the 50/75 values are ratified as-is and the
   "provisional" tag is removed.
2. If the distribution is lopsided (any single band holds > 60% or
   < 10%), the first response is to revisit normalisation (§6) —
   most lopsidedness upstream of the bands is a normalisation-anchor
   issue, not a cutoff-choice issue.
3. Only if (2) is investigated and normalisation is confirmed
   correct do we relocate cutoffs at the ranked 33rd / 67th
   percentiles of the observed distribution. This choice is then
   documented in this file with the distribution snapshot that
   justified it.

The cutoffs are not magic numbers chosen to fit a desired band
distribution. What we ratify now is the **process** for locking
them; the **values** are honestly deferred to first-sweep data.

---

## 11. New cells added by this methodology

Migration to `data/landscape.json` schema (additive, null-default):

| Cell                            | Type   | Provenance source initially | Notes                                    |
|---------------------------------|--------|------------------------------|------------------------------------------|
| `capability-code-score`         | number | `llm` (computed by sweep)    | 0–100, null when no eligible code benchmarks. |
| `capability-agentic-score`      | number | `llm` (computed by sweep)    | 0–100, null when no eligible agentic benchmarks. |
| `capability-longcontext-score`  | number | `llm` (computed by sweep)    | 0–100, null when no eligible long-context benchmarks. |

The existing `capability-composite-score` and `capability-band` cells
are kept; their values are recomputed from the sub-scores per this
methodology on the first sweep and on every subsequent rebaseline.

The schema update is its own migration PR; this doc declares the
target shape only.

---

## 12. References

- OECD / JRC, *Handbook on Constructing Composite Indicators:
  Methodology and User Guide* (2008). Free PDF, OECD Publishing.
  Doi: 10.1787/9789264043466-en. Step structure followed in §§1–8.
- UNDP, *Human Development Report 2010 — Technical Notes*. Source
  for the arithmetic → geometric switch rationale used in §7.2.
- Polo et al., *tinyBenchmarks: Evaluating LLMs with Fewer Examples*
  (NeurIPS 2024 / arXiv:2402.14992). Item Response Theory framing
  considered and deferred per §5; revisit when coverage density
  doubles.
- Chiang et al., *Chatbot Arena: An Open Platform for Evaluating
  LLMs by Human Preference* (arXiv:2403.04132). Source for the
  Bradley-Terry / Elo cross-check in §8.2.

---

## 13. Open methodology questions

- Family classification: a `benchmark-families.yml` controlled list
  must be authored to back §3.2. Initial seed comes from inspecting
  the union of `capability-benchmark-sources` values currently in
  `landscape.json`. Maintainer-judgment call per benchmark; not
  derivable mechanically.
- Trust threshold (§3.1, `trustScore ≥ 40`) reuses the `medium` tier
  cutoff from `benchmark-trust.ts`. Should be spot-checked once a
  real benchmark panel exists: confirm the excluded set (low tier)
  contains the benchmarks we'd intuitively distrust, and the
  included set doesn't admit anything obviously self-reported.
- Whether Arena cross-check should gate publication or only warn
  (§8.2). Current spec says warn only. Reconsider after first three
  weekly runs.
