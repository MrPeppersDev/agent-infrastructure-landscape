// Pure helpers for Wang-Song-Barabási citation modelling per record (issue #58).
//
// Methodology
// -----------
// Wang, Song & Barabási, "Quantifying long-term scientific impact",
// Science 342:127-132 (2013) — the academic gold-standard model for paper
// citation trajectories. ~0.75-0.80 Spearman correlation between the
// model's 10-year prediction and observed counts on the original PNAS
// + APS corpora. Two distinguishing claims of the WSB framework that we
// reproduce here:
//
//   1. Predicted breakouts — papers in their growth phase with high λ
//      (immediacy) but small σ (longevity) signal long-run impact.
//   2. Sleeping beauties — papers with low λ but small σ signal slow-burn
//      impact (citations accumulate years after publication). Originally
//      surfaced as a finding in the same Science 2013 paper.
//
// We fit the log-normal cumulative-citation formula:
//
//        c(t) = m · (exp(λ · Φ((log(t) − μ) / σ)) − 1)
//
// where
//   t  = years since publication                       (independent)
//   m  = field-average citations-per-paper             (catalog constant)
//   λ  = immediacy — total "ultimate impact" param      (fit)
//   μ  = log-time of the citation peak                  (fit)
//   σ  = longevity — peak width on a log-time axis      (fit)
//   Φ  = standard normal CDF
//
// As t → ∞, c(t) → m · (exp(λ) − 1) is the long-run citation ceiling
// (the asymptote / c_∞ in WSB's notation).
//
// We solve (λ, μ, σ) by a 3-d grid search (deterministic; no randomness),
// then refine with a 3-pass local sweep around the best grid point —
// the log-normal CDF is well-behaved enough on this small parameter
// envelope that a full Levenberg-Marquardt isn't needed. ~3000 grid
// evaluations + ~750 refinement evaluations per fit; ~1ms per paper on
// modern hardware.
//
// A seeded bootstrap (100 resamples, fixed RNG seed per record) gives a
// 90 % CI on the asymptote — the spread is the headline uncertainty
// readers see beside each prediction. The seed is derived from the record
// id so reruns are byte-identical, keeping the validate-pipeline
// determinism gate clean.
//
// Data sources per record (priority order):
//   1. citation-trajectory cell from T3-prep-2 / issue #51 — real yearly
//      cumulative within-catalog inbound-citation counts bucketed from
//      the S2 reference cache. Requires ≥3 distinct years for a true fit.
//   2. citations cell + created cell — synthesised trajectory from
//      (total cites, cites/yr, publication date). Fallback that lets us
//      generate predictions on the broader 186-paper population, but
//      under-fit and flagged as such (lower R², wider CI).
//
// Records that hit neither path go to phase: 'underfit-data'. Don't
// force a 3-parameter fit on too little signal.

import type { LandscapeRecord } from '$lib/types';

// =========================================================================
// Public types
// =========================================================================

export type CitationPhase =
  | 'pre-growth'
  | 'growth'
  | 'saturation'
  | 'underfit-data';

export interface CitationFit {
  recordId: string;
  recordName: string;
  /** Primary section name, for grouping in the page. */
  section: string;
  /** 1=battle-tested → 5=theoretical. */
  tier: number;
  /** Inferred publication year (calendar year, integer). */
  publishedYear: number;
  /** Number of full years between publication and the latest observation. */
  yearsObserved: number;
  /** Cumulative citations as of the latest observation. */
  observedCitations: number;
  /** Cumulative influential-citations as of the latest observation. */
  observedInfluential: number;

  // --- Wang-Song-Barabási parameters --------------------------------------
  /** λ — overall "ultimate impact" parameter. NaN when not fit. */
  lambda: number;
  /** μ — log-time of the citation peak. NaN when not fit. */
  mu: number;
  /** σ — longevity / peak width on log-time axis. NaN when not fit. */
  sigma: number;

  // --- Predictions --------------------------------------------------------
  /** c_∞ = m · (exp(λ) − 1) — long-run citation ceiling. NaN when not fit. */
  asymptote: number;
  /** 90 % bootstrap CI on the asymptote (5th, 95th percentile). */
  asymptoteCI: [number, number];
  /** Expected cumulative citations at year-10 since publication. */
  predictedAt10y: number;
  /** Coefficient of determination on the fit observations. */
  fitR2: number;

  // --- Classification -----------------------------------------------------
  phase: CitationPhase;
  /**
   * P(asymptote > 3× median asymptote) from the bootstrap distribution.
   * Heuristic readout: how likely is this paper to be in the top 33 %ile
   * of long-run impact?
   */
  breakoutProbability: number;

  // --- Series for sparkline / drilldown ----------------------------------
  /** Observed series: (years since pub, cumulative). */
  observedSeries: Array<{ t: number; y: number }>;
  /** Fitted curve over the observed range (smoothed). */
  fittedSeries: Array<{ t: number; y: number }>;
  /** Extrapolation from latest observed year out to year 10. */
  extrapolatedSeries: Array<{ t: number; y: number }>;
  /** Source descriptor for the UI (e.g. "30 cites · 4yr · trajectory"). */
  source: string;
  /** 'trajectory' = real bucketed data; 'synthesised' = (total, rate, created) fallback. */
  sourceKind: 'trajectory' | 'synthesised' | 'none';
}

export interface CitationCohort {
  /** Cohort year = floor(publication year / 2) · 2 — 2-year buckets. */
  startYear: number;
  /** Median asymptote across cohort members in the fit population. */
  medianAsymptote: number;
  /** Members included. */
  members: CitationFit[];
}

// =========================================================================
// Phase metadata
// =========================================================================

export const PHASE_ORDER: CitationPhase[] = [
  'pre-growth',
  'growth',
  'saturation',
  'underfit-data'
];

export const PHASE_LABELS: Record<CitationPhase, string> = {
  'pre-growth': 'Pre-growth',
  growth: 'Growth',
  saturation: 'Saturation',
  'underfit-data': 'Underfit data'
};

export const PHASE_COLOURS: Record<CitationPhase, string> = {
  'pre-growth': '#79c0ff',
  growth: '#3fb950',
  saturation: '#d29922',
  'underfit-data': '#8b949e'
};

export const PHASE_DESCRIPTION: Record<CitationPhase, string> = {
  'pre-growth':
    'Fewer than 2 years observed. Curve is still ramping; the asymptote is the most uncertain estimate.',
  growth:
    'Latest observed cumulative cites are below 50 % of the predicted asymptote. Steepest accumulation phase.',
  saturation:
    'Latest observed cumulative cites are at or above 50 % of the predicted asymptote. Most of the eventual impact is already on the books.',
  'underfit-data':
    'Fewer than 3 distinct year buckets in the citation trajectory. Cannot fit a 3-parameter log-normal.'
};

// =========================================================================
// WSB math primitives
// =========================================================================

/**
 * Standard normal CDF Φ(x) via the Abramowitz-Stegun rational
 * approximation (max abs error ~ 7.5 × 10^-8). Pure, deterministic.
 */
function normalCdf(x: number): number {
  // erf approximation: Abramowitz & Stegun 7.1.26
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x) / Math.SQRT2;
  const t = 1.0 / (1.0 + p * ax);
  const y =
    1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-ax * ax);
  return 0.5 * (1.0 + sign * y);
}

/**
 * WSB cumulative-citation curve.
 *   c(t) = m · (exp(λ · Φ((log(t) − μ) / σ)) − 1)
 * Returns 0 for t ≤ 0 (predates publication).
 */
function wsbCumulative(
  t: number,
  m: number,
  lambda: number,
  mu: number,
  sigma: number
): number {
  if (t <= 0) return 0;
  if (sigma <= 0) return 0;
  const z = (Math.log(t) - mu) / sigma;
  const phi = normalCdf(z);
  // Guard against overflow / underflow.
  const exponent = lambda * phi;
  if (!isFinite(exponent)) return 0;
  if (exponent > 50) return m * (Math.exp(50) - 1);
  if (exponent < -50) return 0;
  return m * (Math.exp(exponent) - 1);
}

/**
 * Asymptote / c_∞ — long-run citation ceiling.
 *   lim_{t → ∞} c(t) = m · (exp(λ) − 1)
 */
function wsbAsymptote(m: number, lambda: number): number {
  if (lambda > 50) return m * (Math.exp(50) - 1);
  if (lambda < 0) return 0;
  return m * (Math.exp(lambda) - 1);
}

// =========================================================================
// Field constant m
// =========================================================================

/**
 * Catalog-wide median citations-per-paper for academic-paper rows that
 * have a parseable `citations` cell. This is our `m` field constant —
 * documented in the methodology footer of the page so readers know
 * what's holding the asymptote up.
 *
 * Computed lazily on first call and cached; deterministic input → output.
 */
let cachedFieldConstant: number | null = null;

export function fieldConstant(records: LandscapeRecord[]): number {
  if (cachedFieldConstant !== null) return cachedFieldConstant;
  const totals: number[] = [];
  for (const r of records) {
    const c = parseCitationsCell(r.cells['citations']?.value);
    if (c && c.total > 0) totals.push(c.total);
  }
  totals.sort((a, b) => a - b);
  if (totals.length === 0) {
    cachedFieldConstant = 30; // WSB 2013 paper's PNAS-corpus default.
    return cachedFieldConstant;
  }
  const mid = Math.floor(totals.length / 2);
  cachedFieldConstant =
    totals.length % 2 ? totals[mid] : (totals[mid - 1] + totals[mid]) / 2;
  return cachedFieldConstant;
}

/** Visible for tests / pages that want to display the value. */
export function resetFieldConstant(): void {
  cachedFieldConstant = null;
}

// =========================================================================
// Cell parsers
// =========================================================================

/**
 * Parse the citation-trajectory cell's stringified JSON. Mirrors the
 * parser in s-curve.ts (issue #47). Expected shape:
 *   [{"year":YYYY,"cum":N,"infl":M}, ...]
 */
function parseCitationTrajectory(
  raw: string | null | undefined
): Array<{ year: number; cum: number; infl: number }> | null {
  if (!raw) return null;
  const s = raw.trim();
  if (!s || s === 'no data' || s === 'searched not found') return null;
  if (!s.startsWith('[')) return null;
  try {
    const arr = JSON.parse(s);
    if (!Array.isArray(arr)) return null;
    const out: Array<{ year: number; cum: number; infl: number }> = [];
    for (const item of arr) {
      if (!item || typeof item !== 'object') continue;
      const year = (item as { year?: unknown }).year;
      const cum = (item as { cum?: unknown }).cum;
      const infl = (item as { infl?: unknown }).infl;
      if (typeof year !== 'number' || !isFinite(year) || year < 1900 || year > 2099)
        continue;
      if (typeof cum !== 'number' || !isFinite(cum) || cum < 0) continue;
      if (typeof infl !== 'number' || !isFinite(infl) || infl < 0) continue;
      out.push({ year: Math.round(year), cum, infl });
    }
    out.sort((a, b) => a.year - b.year);
    return out.length > 0 ? out : null;
  } catch {
    return null;
  }
}

/** Parse "4.3k cites 612/yr" / "443 cites 443/yr" into {total, ratePerYear}. */
function parseCitationsCell(
  raw: string | null | undefined
): { total: number; ratePerYear: number } | null {
  if (!raw) return null;
  const v = raw.toLowerCase();

  function parseAmount(s: string): number | null {
    const m = s.match(/^([\d.]+)(k)?$/);
    if (!m) return null;
    const n = Number(m[1]);
    if (!isFinite(n)) return null;
    return m[2] === 'k' ? n * 1000 : n;
  }

  // Compact "4.3k cites 612/yr" form.
  let m = v.match(/([\d.]+k?)\s*cites?\s+([\d.]+k?)\s*\/\s*yr/);
  if (!m) {
    // Plain "4300 cites 612/yr" form (already-expanded; covers comma cases).
    m = v.match(/(\d{1,3}(?:,\d{3})+|\d+)\s*cites?\s+(\d{1,3}(?:,\d{3})+|\d+)\s*\/\s*yr/);
    if (!m) return null;
    const total = Number(m[1].replace(/,/g, ''));
    const rate = Number(m[2].replace(/,/g, ''));
    if (!isFinite(total) || !isFinite(rate)) return null;
    return { total, ratePerYear: rate };
  }
  const total = parseAmount(m[1]);
  const rate = parseAmount(m[2]);
  if (total === null || rate === null) return null;
  return { total, ratePerYear: rate };
}

/** Pull the earliest YYYY from a free-text cell (publication year proxy). */
function parsePublicationYear(raw: string | null | undefined): number | null {
  if (!raw) return null;
  const m = raw.match(/(19|20)\d{2}/);
  if (!m) return null;
  const y = Number(m[0]);
  if (y < 1950 || y > 2099) return null;
  return y;
}

// =========================================================================
// Series extraction
// =========================================================================

interface ExtractedSeries {
  /** Cumulative observations, ordered by t (years since publication). */
  observations: Array<{ t: number; y: number }>;
  publishedYear: number;
  observedCitations: number;
  observedInfluential: number;
  source: string;
  sourceKind: 'trajectory' | 'synthesised';
}

/**
 * Best-effort extraction of a citation observation series for one paper.
 *
 * Priority:
 *   1. citation-trajectory cell with ≥3 distinct years
 *   2. citations cell + created year, synthesised quarterly (≥2 years
 *      of life so we have ≥4 points and a meaningful curve)
 *   3. null → underfit-data
 */
function extractSeries(record: LandscapeRecord): ExtractedSeries | null {
  // --- Try real bucketed trajectory first ---------------------------------
  const trajectory = parseCitationTrajectory(
    record.cells['citation-trajectory']?.value
  );
  if (trajectory && trajectory.length >= 3) {
    const firstYear = trajectory[0].year;
    const lastYear = trajectory[trajectory.length - 1].year;
    if (lastYear > firstYear) {
      const observations = trajectory.map((p) => ({
        t: p.year - firstYear + 1, // t=1 at the first observation year
        y: p.cum
      }));
      const last = trajectory[trajectory.length - 1];
      return {
        observations,
        publishedYear: firstYear,
        observedCitations: last.cum,
        observedInfluential: last.infl,
        source: `${last.cum} cites · ${observations[observations.length - 1].t}yr · trajectory`,
        sourceKind: 'trajectory'
      };
    }
  }

  // --- Fall back to synthesised series ------------------------------------
  // For papers without a rich trajectory, synthesise from the citations
  // cell (total + per-year rate) and the created cell (publication year).
  // The series is built as: assume citations accumulate at the observed
  // per-year rate (cite.ratePerYear) for the full lifetime, capped at the
  // observed total. We sample 4 anchor points across the lifetime so the
  // log-normal fit has enough leverage to estimate (λ, μ, σ).
  //
  // This synth series is flagged with sourceKind='synthesised'; the
  // page surfaces it with a "synth" badge and excludes it from the
  // breakout / sleeping-beauty leaderboards (which require trajectory
  // data) — the fitted parameters are only suggestive on a 4-point
  // monotone ramp.
  const cite = parseCitationsCell(record.cells['citations']?.value);
  const created = parsePublicationYear(record.cells['created']?.value);
  if (!cite || cite.total <= 0 || !created) return null;
  const TODAY_YEAR = 2026;
  const lifeYears = Math.max(1, TODAY_YEAR - created);
  // Need ≥1 year of life so the (year=0 → today=total) ramp has slope.
  if (lifeYears < 1) return null;

  // Build anchor points at fractions 0.25, 0.5, 0.75, 1.0 of the life,
  // assuming linear-ish accumulation (slight front-load by raising to a
  // power of 0.9 — citations typically accumulate slightly faster early
  // for high-mindshare papers, slower for slow-burns, but we have no
  // per-year cadence to leverage here).
  const observations: Array<{ t: number; y: number }> = [];
  for (let i = 1; i <= 4; i++) {
    const frac = i / 4;
    observations.push({
      t: frac * lifeYears,
      y: cite.total * Math.pow(frac, 0.9)
    });
  }
  return {
    observations,
    publishedYear: created,
    observedCitations: cite.total,
    observedInfluential: 0, // unknown from the synth fallback
    source: `${cite.total} cites · ${cite.ratePerYear}/yr · synth`,
    sourceKind: 'synthesised'
  };
}

// =========================================================================
// Grid-search fit
// =========================================================================

interface WsbParams {
  lambda: number;
  mu: number;
  sigma: number;
}

function squaredError(
  obs: Array<{ t: number; y: number }>,
  m: number,
  p: WsbParams
): number {
  let sse = 0;
  for (const o of obs) {
    const pred = wsbCumulative(o.t, m, p.lambda, p.mu, p.sigma);
    const diff = pred - o.y;
    sse += diff * diff;
  }
  return sse;
}

function rSquared(
  obs: Array<{ t: number; y: number }>,
  m: number,
  p: WsbParams
): number {
  if (obs.length === 0) return 0;
  const mean = obs.reduce((s, o) => s + o.y, 0) / obs.length;
  let ssRes = 0;
  let ssTot = 0;
  for (const o of obs) {
    const pred = wsbCumulative(o.t, m, p.lambda, p.mu, p.sigma);
    ssRes += (o.y - pred) ** 2;
    ssTot += (o.y - mean) ** 2;
  }
  if (ssTot === 0) return 0;
  return Math.max(0, Math.min(1, 1 - ssRes / ssTot));
}

// Grid points: deliberate small grid sized for the ≤45s build budget.
// λ ∈ [0.1, 7]: 12 log-spaced. λ controls total impact via c_∞ = m·(exp(λ)−1).
//   The WSB 2013 paper reports λ ∈ ~[1, 5] for the top tail of PNAS papers;
//   we cap at 7 so the asymptote stays within sensible extrapolation bounds
//   (m=42 catalog median × (e^7 − 1) ≈ 46k citations is a plausible upper
//   end). The issue spec mentioned λ up to 30 but on our short-window data
//   (≤8yr trajectories) any λ > 7 produces wild extrapolations — that's
//   the difference between WSB's 30-year corpora and our 2-5yr per row.
// μ ∈ [−5, 10]: 11 linearly-spaced. μ is the log-time of the citation peak
//   — μ = ln(T_peak), so range −5..10 covers T_peak from e^-5 ≈ 0.007yr
//   (essentially immediate) to e^10 ≈ 22000yr (effectively never).
// σ ∈ [0.1, 5]: 10 log-spaced. σ is peak width on log-time axis; smaller
//   = shorter-lived peak; longevity goes the other way (small σ + late μ
//   = sleeping-beauty profile).
//
// 12 × 11 × 10 = 1320 grid evaluations + ~5 × 5 × 5 = 125 refinement
// evaluations × 3 passes = ~1700 evaluations per fit. ~1ms each on V8.
const LAMBDA_GRID: number[] = (() => {
  const out: number[] = [];
  for (let i = 0; i < 12; i++) {
    // Log-spaced 0.1 → 7
    const exp = Math.log(0.1) + (i / 11) * (Math.log(7) - Math.log(0.1));
    out.push(Math.exp(exp));
  }
  return out;
})();
const MU_GRID: number[] = (() => {
  const out: number[] = [];
  for (let i = 0; i < 11; i++) {
    out.push(-5 + (i / 10) * 15);
  }
  return out;
})();
const SIGMA_GRID: number[] = (() => {
  const out: number[] = [];
  for (let i = 0; i < 10; i++) {
    const exp = Math.log(0.1) + (i / 9) * (Math.log(5) - Math.log(0.1));
    out.push(Math.exp(exp));
  }
  return out;
})();

/** Hard upper bound on λ post-refinement — keeps asymptote sane. */
const LAMBDA_MAX = 7;

function fitWsb(
  obs: Array<{ t: number; y: number }>,
  m: number
): WsbParams | null {
  if (obs.length < 3) return null;

  let bestSse = Infinity;
  let best: WsbParams = { lambda: 1, mu: 0, sigma: 1 };

  for (const lambda of LAMBDA_GRID) {
    for (const mu of MU_GRID) {
      for (const sigma of SIGMA_GRID) {
        const sse = squaredError(obs, m, { lambda, mu, sigma });
        if (sse < bestSse) {
          bestSse = sse;
          best = { lambda, mu, sigma };
        }
      }
    }
  }

  // 3-pass local refinement around the best grid point.
  const passes = 3;
  for (let pass = 0; pass < passes; pass++) {
    let improved = false;
    const dl = best.lambda * 0.3;
    const dm = 1.5;
    const ds = Math.max(0.05, best.sigma * 0.3);
    for (let li = -5; li <= 5; li++) {
      for (let mi = -5; mi <= 5; mi++) {
        for (let si = -5; si <= 5; si++) {
          const lambda = Math.max(
            0.001,
            Math.min(LAMBDA_MAX, best.lambda + (li / 5) * dl)
          );
          const mu = best.mu + (mi / 5) * dm;
          const sigma = Math.max(0.01, best.sigma + (si / 5) * ds);
          const sse = squaredError(obs, m, { lambda, mu, sigma });
          if (sse < bestSse) {
            bestSse = sse;
            best = { lambda, mu, sigma };
            improved = true;
          }
        }
      }
    }
    if (!improved) break;
  }

  return best;
}

// =========================================================================
// Bootstrap CI
// =========================================================================

/**
 * Seeded LCG (linear congruential generator) — Numerical Recipes
 * parameters. Deterministic + fast; 2^32 period is ample for 100
 * resamples × ~6 picks each.
 */
function seedFromId(id: string): number {
  // Simple hash → 32-bit unsigned seed, deterministic for any string.
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) {
    h = (h ^ id.charCodeAt(i)) >>> 0;
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h || 1;
}

function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    // LCG: Numerical Recipes (Park-Miller-ish)
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 0x100000000;
  };
}

const BOOTSTRAP_SAMPLES = 100;

function bootstrapAsymptoteCi(
  obs: Array<{ t: number; y: number }>,
  m: number,
  baseFit: WsbParams,
  seed: number
): { ci: [number, number]; distribution: number[] } {
  const rng = makeRng(seed);
  const asymptotes: number[] = [];
  const n = obs.length;
  for (let b = 0; b < BOOTSTRAP_SAMPLES; b++) {
    const resample: Array<{ t: number; y: number }> = [];
    for (let i = 0; i < n; i++) {
      const idx = Math.floor(rng() * n);
      resample.push(obs[idx]);
    }
    // Sort by t so duplicate-removed series still has the monotone
    // structure the fit expects.
    resample.sort((a, b2) => a.t - b2.t);

    // Cheap refit using a 1-pass refinement around the baseline — this
    // is far faster than full grid search and gives a useful CI proxy.
    let bestSse = squaredError(resample, m, baseFit);
    let best = { ...baseFit };
    const dl = baseFit.lambda * 0.3;
    const dm = 1.5;
    const ds = Math.max(0.05, baseFit.sigma * 0.3);
    for (let li = -3; li <= 3; li++) {
      for (let mi = -3; mi <= 3; mi++) {
        for (let si = -3; si <= 3; si++) {
          const lambda = Math.max(
            0.001,
            Math.min(LAMBDA_MAX, baseFit.lambda + (li / 3) * dl)
          );
          const mu = baseFit.mu + (mi / 3) * dm;
          const sigma = Math.max(0.01, baseFit.sigma + (si / 3) * ds);
          const sse = squaredError(resample, m, { lambda, mu, sigma });
          if (sse < bestSse) {
            bestSse = sse;
            best = { lambda, mu, sigma };
          }
        }
      }
    }
    asymptotes.push(wsbAsymptote(m, best.lambda));
  }
  asymptotes.sort((a, b) => a - b);
  const lo = asymptotes[Math.floor(BOOTSTRAP_SAMPLES * 0.05)];
  const hi = asymptotes[Math.floor(BOOTSTRAP_SAMPLES * 0.95)];
  return { ci: [lo, hi], distribution: asymptotes };
}

// =========================================================================
// Classification + helpers
// =========================================================================

function primarySection(r: LandscapeRecord): string {
  const p = r.sections.find((s) => s.primary);
  return p?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

function classifyPhase(
  yearsObserved: number,
  observedCitations: number,
  asymptote: number,
  enoughData: boolean
): CitationPhase {
  if (!enoughData) return 'underfit-data';
  if (yearsObserved < 2) return 'pre-growth';
  if (asymptote <= 0) return 'underfit-data';
  if (observedCitations < 0.5 * asymptote) return 'growth';
  return 'saturation';
}

function emptyFit(record: LandscapeRecord, source: string): CitationFit {
  return {
    recordId: record.id,
    recordName: record.name,
    section: primarySection(record),
    tier: record.tier,
    publishedYear: 0,
    yearsObserved: 0,
    observedCitations: 0,
    observedInfluential: 0,
    lambda: NaN,
    mu: NaN,
    sigma: NaN,
    asymptote: NaN,
    asymptoteCI: [NaN, NaN],
    predictedAt10y: NaN,
    fitR2: NaN,
    phase: 'underfit-data',
    breakoutProbability: 0,
    observedSeries: [],
    fittedSeries: [],
    extrapolatedSeries: [],
    source,
    sourceKind: 'none'
  };
}

/**
 * Build a smoothed fitted curve over the observed range and an
 * extrapolation out to year-10 (or 2× yearsObserved, whichever is
 * larger).
 */
function buildCurves(
  obs: Array<{ t: number; y: number }>,
  m: number,
  p: WsbParams,
  samples = 30
): {
  fitted: Array<{ t: number; y: number }>;
  extrapolated: Array<{ t: number; y: number }>;
} {
  if (obs.length === 0) return { fitted: [], extrapolated: [] };
  const tMin = Math.max(0.001, obs[0].t);
  const tMax = obs[obs.length - 1].t;
  const fitted: Array<{ t: number; y: number }> = [];
  for (let i = 0; i <= samples; i++) {
    const t = tMin + ((tMax - tMin) * i) / samples;
    fitted.push({ t, y: wsbCumulative(t, m, p.lambda, p.mu, p.sigma) });
  }
  const tExtrapMax = Math.max(10, tMax * 2);
  const extrapolated: Array<{ t: number; y: number }> = [];
  const extraSamples = 20;
  for (let i = 0; i <= extraSamples; i++) {
    const t = tMax + ((tExtrapMax - tMax) * i) / extraSamples;
    extrapolated.push({ t, y: wsbCumulative(t, m, p.lambda, p.mu, p.sigma) });
  }
  return { fitted, extrapolated };
}

// =========================================================================
// Filter — academic-paper rows only
// =========================================================================

/**
 * The WSB model applies to research papers, not products or benchmarks.
 * We restrict the fit to rows in sections that contain academic-paper
 * substrate. The catalog convention: section names containing "paper",
 * "research", or "method" are research sections; "benchmark" sections
 * also have papers behind them; "Theoretical / informal" is excluded
 * (no paper to model). Documented in the methodology footer.
 */
function isAcademicPaper(r: LandscapeRecord): boolean {
  // Filter by presence of citation-trajectory cell OR citations cell with
  // year-rate data — those are the operational signatures of a paper row.
  const hasTraj = r.cells['citation-trajectory']?.status === 'real-data';
  const citesCell = r.cells['citations']?.value ?? '';
  const hasParseable = /cites?\s+[\d.]+k?\s*\/\s*yr/i.test(citesCell);
  return hasTraj || hasParseable;
}

// =========================================================================
// Public API
// =========================================================================

/**
 * Fit Wang-Song-Barabási to every academic-paper row with a populated
 * citation trajectory. Rows without enough signal get an underfit-data
 * placeholder.
 *
 * Deterministic for fixed input: grid search has no randomness; bootstrap
 * RNG is seeded from each record's id.
 */
export function fitCitationCurves(records: LandscapeRecord[]): CitationFit[] {
  // Reset the field-constant cache so callers can re-fit after data changes.
  resetFieldConstant();
  const m = fieldConstant(records);

  const out: CitationFit[] = [];
  for (const r of records) {
    if (!isAcademicPaper(r)) continue;
    const extracted = extractSeries(r);
    if (!extracted) {
      out.push(emptyFit(r, 'no parseable citation signal'));
      continue;
    }
    const obs = extracted.observations;
    // `enoughData` gates the phase classifier: trajectory rows with ≥3
    // distinct year buckets get a real phase; everything else (synth
    // fallback) gets a phase too, since synth has 4 anchor points by
    // construction. We only hit 'underfit-data' when there's no usable
    // series at all (which is short-circuited at the start of the loop).
    const enoughData = obs.length >= 3;
    const yearsObserved = obs[obs.length - 1].t;

    const fit = fitWsb(obs, m);
    if (!fit) {
      out.push(emptyFit(r, extracted.source));
      continue;
    }
    const asymptote = wsbAsymptote(m, fit.lambda);
    const r2 = rSquared(obs, m, fit);
    const phase = classifyPhase(
      yearsObserved,
      extracted.observedCitations,
      asymptote,
      enoughData
    );

    const seed = seedFromId(r.id);
    const boot = bootstrapAsymptoteCi(obs, m, fit, seed);
    const predictedAt10y = wsbCumulative(10, m, fit.lambda, fit.mu, fit.sigma);
    const { fitted, extrapolated } = buildCurves(obs, m, fit);

    out.push({
      recordId: r.id,
      recordName: r.name,
      section: primarySection(r),
      tier: r.tier,
      publishedYear: extracted.publishedYear,
      yearsObserved,
      observedCitations: extracted.observedCitations,
      observedInfluential: extracted.observedInfluential,
      lambda: fit.lambda,
      mu: fit.mu,
      sigma: fit.sigma,
      asymptote,
      asymptoteCI: boot.ci,
      predictedAt10y,
      fitR2: r2,
      phase,
      breakoutProbability: 0, // filled below using median
      observedSeries: obs,
      fittedSeries: fitted,
      extrapolatedSeries: extrapolated,
      source: extracted.source,
      sourceKind: extracted.sourceKind
    });
  }

  // Second pass: compute breakout probability using the bootstrap
  // distribution and the catalog-wide median asymptote among fit rows.
  const asymptotes = out
    .filter((f) => f.phase !== 'underfit-data' && isFinite(f.asymptote))
    .map((f) => f.asymptote)
    .sort((a, b) => a - b);
  if (asymptotes.length > 0) {
    const mid = Math.floor(asymptotes.length / 2);
    const medianAsymp =
      asymptotes.length % 2
        ? asymptotes[mid]
        : (asymptotes[mid - 1] + asymptotes[mid]) / 2;
    const threshold = medianAsymp * 3;
    for (let i = 0; i < out.length; i++) {
      const f = out[i];
      if (f.phase === 'underfit-data' || !isFinite(f.asymptote)) continue;
      // Re-derive boot distribution from the per-row seed so we don't
      // need to retain the distribution in memory across all rows.
      const r = records.find((rr) => rr.id === f.recordId);
      if (!r) continue;
      const extracted = extractSeries(r);
      if (!extracted) continue;
      const fit: WsbParams = { lambda: f.lambda, mu: f.mu, sigma: f.sigma };
      const seed = seedFromId(r.id);
      const boot = bootstrapAsymptoteCi(extracted.observations, m, fit, seed);
      let above = 0;
      for (const a of boot.distribution) if (a > threshold) above += 1;
      out[i] = {
        ...f,
        breakoutProbability: above / boot.distribution.length
      };
    }
  }

  return out;
}

// =========================================================================
// Leaderboard helpers
// =========================================================================

/**
 * Top-N predicted breakouts: papers with the highest
 * `asymptote / observed` ratio (still-growing the fastest), constrained
 * to growth-phase rows with at least a 1.5× growth headroom and a real
 * trajectory (so synth-fallback synthetic rows don't dominate). Ties
 * broken by asymptote magnitude (the bigger ceiling wins).
 */
export function topBreakouts(fits: CitationFit[], limit = 15): CitationFit[] {
  return fits
    .filter(
      (f) =>
        f.phase === 'growth' &&
        f.sourceKind === 'trajectory' &&
        isFinite(f.asymptote) &&
        f.observedCitations > 0 &&
        f.asymptote > 1.5 * f.observedCitations
    )
    .sort((a, b) => {
      const ra = a.asymptote / Math.max(1, a.observedCitations);
      const rb = b.asymptote / Math.max(1, b.observedCitations);
      if (rb !== ra) return rb - ra;
      return b.asymptote - a.asymptote;
    })
    .slice(0, limit);
}

/**
 * Underperformers: saturation-phase papers whose asymptote is BELOW
 * the median asymptote for their 2-year publication cohort. The
 * "hyped but won't last" callout.
 */
export function underperformers(fits: CitationFit[], limit = 15): CitationFit[] {
  const cohortMedians = new Map<number, number>();
  const byCohort = new Map<number, CitationFit[]>();
  for (const f of fits) {
    if (f.phase === 'underfit-data' || !isFinite(f.asymptote)) continue;
    const cohort = Math.floor(f.publishedYear / 2) * 2;
    if (!byCohort.has(cohort)) byCohort.set(cohort, []);
    byCohort.get(cohort)!.push(f);
  }
  for (const [cohort, members] of byCohort.entries()) {
    const xs = members.map((f) => f.asymptote).sort((a, b) => a - b);
    const mid = Math.floor(xs.length / 2);
    const median = xs.length % 2 ? xs[mid] : (xs[mid - 1] + xs[mid]) / 2;
    cohortMedians.set(cohort, median);
  }
  return fits
    .filter((f) => {
      if (f.phase !== 'saturation') return false;
      if (f.sourceKind !== 'trajectory') return false;
      if (!isFinite(f.asymptote)) return false;
      const cohort = Math.floor(f.publishedYear / 2) * 2;
      const med = cohortMedians.get(cohort);
      if (!med || !isFinite(med)) return false;
      return f.asymptote < med;
    })
    .sort((a, b) => {
      const cohortA = Math.floor(a.publishedYear / 2) * 2;
      const cohortB = Math.floor(b.publishedYear / 2) * 2;
      const ga = (cohortMedians.get(cohortA) ?? 1) - a.asymptote;
      const gb = (cohortMedians.get(cohortB) ?? 1) - b.asymptote;
      return gb - ga;
    })
    .slice(0, limit);
}

/**
 * Sleeping beauties: papers with small σ (longevity > immediacy) AND
 * later μ (peak in the future) — accumulation profile is slow-burn,
 * not front-loaded. WSB 2013 introduced the concept; we report the
 * top candidates by (σ × exp(μ)) ratio adjusted by R².
 */
export function sleepingBeauties(fits: CitationFit[], limit = 10): CitationFit[] {
  return fits
    .filter(
      (f) =>
        f.phase !== 'underfit-data' &&
        f.sourceKind === 'trajectory' &&
        isFinite(f.sigma) &&
        isFinite(f.mu) &&
        f.sigma > 0.5 && // wide peak on log-time = long-lived
        f.mu > 0.5 &&    // peak after t ≈ 1.65yr (since mu = log peak time)
        isFinite(f.fitR2) &&
        f.fitR2 > 0.5
    )
    .sort((a, b) => {
      // Rank by "sleeping-ness": small λ + small σ + late μ.
      // Higher score = more sleeping-beauty-like.
      const score = (f: CitationFit) =>
        f.mu - Math.log(Math.max(0.001, f.lambda)) - 0.5 * f.sigma;
      return score(b) - score(a);
    })
    .slice(0, limit);
}

// =========================================================================
// Aggregates for headers / methodology footer
// =========================================================================

export interface PhaseCounts {
  'pre-growth': number;
  growth: number;
  saturation: number;
  'underfit-data': number;
  total: number;
}

export function countPhases(fits: CitationFit[]): PhaseCounts {
  const c: PhaseCounts = {
    'pre-growth': 0,
    growth: 0,
    saturation: 0,
    'underfit-data': 0,
    total: 0
  };
  for (const f of fits) {
    c[f.phase] += 1;
    c.total += 1;
  }
  return c;
}

export function medianR2(fits: CitationFit[]): number {
  const xs = fits
    .filter(
      (f) =>
        f.phase !== 'underfit-data' &&
        f.sourceKind === 'trajectory' &&
        isFinite(f.fitR2)
    )
    .map((f) => f.fitR2)
    .sort((a, b) => a - b);
  if (xs.length === 0) return NaN;
  const mid = Math.floor(xs.length / 2);
  return xs.length % 2 ? xs[mid] : (xs[mid - 1] + xs[mid]) / 2;
}

/**
 * Bucket the fits into bins for the R² distribution histogram. Returns
 * 10 bins from 0.0 to 1.0. Only "real trajectory" fits — synth
 * fallbacks would mislead because the fit isn't really informative.
 */
export function r2Histogram(fits: CitationFit[]): number[] {
  const bins = Array(10).fill(0);
  for (const f of fits) {
    if (f.phase === 'underfit-data') continue;
    if (f.sourceKind !== 'trajectory') continue;
    if (!isFinite(f.fitR2)) continue;
    const idx = Math.min(9, Math.max(0, Math.floor(f.fitR2 * 10)));
    bins[idx] += 1;
  }
  return bins;
}

/** Find one fit by record id. */
export function findFitById(
  fits: CitationFit[],
  id: string
): CitationFit | undefined {
  return fits.find((f) => f.recordId === id);
}
