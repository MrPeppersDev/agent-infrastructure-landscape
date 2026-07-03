// Capability composite calculation.
//
// Single source of truth for the formula specified in
// docs/composite-methodology.md. Anything that produces
// `capability-composite-score` / `capability-band` values written to
// data/landscape.json MUST route through this file. Anything that
// reads those cells without recomputing should not — those cells are
// the persisted output of this function.
//
// Pure, deterministic, no network or filesystem access. The eligibility
// filter (benchmark trust threshold + family classification) is applied
// by the caller before invoking compute functions here; this file is
// only the arithmetic.

// =========================================================================
// Public types
// =========================================================================

/** A single benchmark observation eligible for inclusion in the composite. */
export interface BenchmarkObservation {
  /** Stable benchmark identifier (e.g. "aider-polyglot", "swe-bench-verified"). */
  id: string;
  /** Raw score reported by the benchmark for this row. Units are benchmark-specific. */
  score: number;
  /** Trust weight from benchmark-trust.ts, in [0, 1]. */
  trust: number;
  /** Family classification — exactly one. Caller is responsible for assignment. */
  family: TaskFamily;
}

export type TaskFamily = 'code' | 'agentic' | 'longcontext';

export const TASK_FAMILIES: readonly TaskFamily[] = ['code', 'agentic', 'longcontext'] as const;

/** Per-benchmark min/max anchors for normalisation. */
export interface BenchmarkAnchor {
  /** Floor used in min-max normalisation. Defaults to 0 if undefined. */
  min?: number;
  /** Ceiling used in min-max normalisation — typically the catalog-wide max. */
  max: number;
}

export type BenchmarkAnchors = Record<string, BenchmarkAnchor>;

export type CapabilityBand = 'entry' | 'competent' | 'frontier';

export interface CompositeResult {
  /** Composite score in [0, 100], or null if no family had eligible benchmarks. */
  composite: number | null;
  /** Per-family sub-scores. null when that family had no eligible benchmarks. */
  byFamily: Record<TaskFamily, number | null>;
  /** Derived band. null when composite is null. */
  band: CapabilityBand | null;
  /**
   * Diagnostic counts so callers can surface "ranked on 2/3 families" caveats.
   * Keyed by family.
   */
  benchmarkCount: Record<TaskFamily, number>;
}

// =========================================================================
// Normalisation (§6 of docs/composite-methodology.md)
// =========================================================================

/**
 * Per-benchmark min-max → [0, 100]. Anchor is the catalog-wide max captured
 * at most recent rebaseline; floor defaults to 0.
 *
 * Out-of-range scores (negative or above max) are clamped, not errored —
 * benchmark methodology revisions sometimes push older reported scores
 * above the new normalisation ceiling; we tolerate this on the read path.
 */
export function normalize(score: number, anchor: BenchmarkAnchor): number {
  const min = anchor.min ?? 0;
  const max = anchor.max;
  if (!Number.isFinite(score) || !Number.isFinite(max) || max <= min) {
    return 0;
  }
  const x = (score - min) / (max - min);
  if (x <= 0) return 0;
  if (x >= 1) return 100;
  return x * 100;
}

// =========================================================================
// Within-family — trust-weighted arithmetic mean (§7.1)
// =========================================================================

/**
 * Aggregate one family's benchmark observations into a sub-score in [0, 100].
 *
 * Returns null if no observations have positive trust weight. Returns 0 if
 * observations exist but all normalized scores are 0 — that distinction
 * matters for the geometric mean in computeComposite (see §7.2 "special
 * case: zero family scores").
 */
export function computeFamilyScore(
  observations: BenchmarkObservation[],
  anchors: BenchmarkAnchors
): number | null {
  let weightedSum = 0;
  let trustSum = 0;
  for (const obs of observations) {
    if (!(obs.trust > 0)) continue;
    const anchor = anchors[obs.id];
    if (!anchor) continue;
    const normalized = normalize(obs.score, anchor);
    weightedSum += obs.trust * normalized;
    trustSum += obs.trust;
  }
  if (trustSum === 0) return null;
  return weightedSum / trustSum;
}

// =========================================================================
// Across families — geometric mean (§7.2)
// =========================================================================

/**
 * Geometric mean of present family scores. Equal inter-family weighting (§7.3).
 *
 * Behaviour:
 * - All families null → composite null (row has zero capability evidence)
 * - Some families null → geometric mean over present families only
 * - Any present family = 0 → composite collapses to 0 (intentional, §7.2)
 */
export function computeComposite(byFamily: Record<TaskFamily, number | null>): number | null {
  const present = TASK_FAMILIES.map((f) => byFamily[f]).filter((s): s is number => s != null);
  if (present.length === 0) return null;
  if (present.some((s) => s <= 0)) return 0;
  const logSum = present.reduce((acc, s) => acc + Math.log(s), 0);
  return Math.exp(logSum / present.length);
}

// =========================================================================
// Band derivation (§10)
// =========================================================================

/** Cutoffs per docs/composite-methodology.md §10. */
export const BAND_CUTOFFS = {
  competent: 50,
  frontier: 75
} as const;

export function deriveBand(composite: number | null): CapabilityBand | null {
  if (composite == null) return null;
  if (composite < BAND_CUTOFFS.competent) return 'entry';
  if (composite < BAND_CUTOFFS.frontier) return 'competent';
  return 'frontier';
}

// =========================================================================
// One-shot row computation
// =========================================================================

/**
 * Full pipeline for a single row: bucket observations by family, compute
 * family sub-scores, aggregate to composite, derive band, return all four
 * plus diagnostic counts.
 *
 * Caller is responsible for:
 * - Filtering observations by trust threshold (§3.1)
 * - Assigning `family` per observation (§3.2)
 * - Providing per-benchmark `anchors`
 */
export function computeRow(
  observations: BenchmarkObservation[],
  anchors: BenchmarkAnchors
): CompositeResult {
  const byFamilyObs: Record<TaskFamily, BenchmarkObservation[]> = {
    code: [],
    agentic: [],
    longcontext: []
  };
  const benchmarkCount: Record<TaskFamily, number> = {
    code: 0,
    agentic: 0,
    longcontext: 0
  };
  for (const obs of observations) {
    byFamilyObs[obs.family].push(obs);
    benchmarkCount[obs.family]++;
  }
  const byFamily: Record<TaskFamily, number | null> = {
    code: computeFamilyScore(byFamilyObs.code, anchors),
    agentic: computeFamilyScore(byFamilyObs.agentic, anchors),
    longcontext: computeFamilyScore(byFamilyObs.longcontext, anchors)
  };
  const composite = computeComposite(byFamily);
  const band = deriveBand(composite);
  return { composite, byFamily, band, benchmarkCount };
}
