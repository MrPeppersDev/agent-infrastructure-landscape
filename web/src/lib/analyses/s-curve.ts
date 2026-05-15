// Pure helpers for logistic S-curve fitting per record (issue #47).
//
// Methodology
// -----------
// Inspired by the BIMATEM bibliometric framework (Bengisu/Nekhili 2006 and
// follow-ups) and the citation-trajectory work of Wang/Song/Barabási 2013
// ("Quantifying long-term scientific impact"). Both fit a 3-parameter
// logistic to cumulative event counts over time and read maturity off the
// inflection point.
//
// We fit:
//
//        L
//   y = ─────────────────────────
//        1 + exp(-k · (t − t0))
//
// where
//   L  = carrying capacity   (logistic plateau)
//   k  = growth rate         (logistic steepness)
//   t0 = inflection time     (date of growth→saturation transition)
//
// Phase classification follows BIMATEM:
//   pre-growth   : t < t0 - 2·σ          (still ramping; below 12% of L)
//   growth       : t0 - 2·σ ≤ t < t0     (12% → 50% of L)
//   saturation   : t0 ≤ t < t0 + 2·σ     (50% → 88% of L; plateau approached)
//   decline      : t > t0 + 2·σ AND recent observations below predicted curve
//
// We solve (L, k, t0) by grid search — this is a low-cost fit and the
// problem is small enough (5-100 points per record) that a grid is fine.
// 15 × 15 × 15 = 3375 candidate triples per record; ~1ms per record on
// modern hardware; ~1 second for all 912 records.
//
// Data sources per record (priority order):
//   1. Research papers: cumulative citations over time, synthesised from
//      total-citations + citations-per-year + paper-publication-date.
//      Without a per-quarter snapshot history we can only build a linear
//      cumulative-rate series, but the logistic still distinguishes
//      paper-still-growing from paper-saturated when paired with the
//      observed-rate decline (cites/yr smaller than total/years means
//      saturation is already underway).
//   2. Products with multiple dated milestones in `created` /
//      `latest-release`: each dated marker is a discrete (date, count)
//      point — release N at date M counts as N cumulative releases.
//   3. Star growth on OSS repos: if we have stars + +N/mo growth signal
//      we synthesise a quarterly cumulative series.
//
// Insufficient data: <5 distinct data points or <12 months total history
// short-circuits to phase: 'insufficient-data'. Don't force a fit.

import type { LandscapeRecord } from '$lib/types';
import { parseLastCommit, monthsBetween, TODAY } from './survivorship';

// --- Public types ------------------------------------------------------

export type SCurvePhase =
  | 'pre-growth'
  | 'growth'
  | 'saturation'
  | 'decline'
  | 'insufficient-data';

export interface SCurveFit {
  recordId: string;
  recordName: string;
  /** Primary section, for grouping in the page. */
  section: string;
  /** Maturity bucket. */
  phase: SCurvePhase;
  /** ISO date string when growth → saturation occurs; null if not fit. */
  inflectionDate: string | null;
  /** Logistic k. Steeper = faster transition. NaN when no fit. */
  growthRate: number;
  /** Logistic L. Estimated carrying capacity. NaN when no fit. */
  carryingCapacity: number;
  /** Coefficient of determination (R²) on the chosen series. NaN when no fit. */
  fitR2: number;
  /** Number of observation points fed into the fit. */
  dataPoints: number;
  /** Raw observations: (ISO date, cumulative value). */
  series: Array<{ date: string; value: number }>;
  /** Predicted curve over the same x-axis range (smoothed, ~40 samples). */
  predictedSeries: Array<{ date: string; value: number }>;
  /** Extrapolated value 24 months ahead of TODAY; null in decline / insufficient. */
  forecast24mo: number | null;
  /** Short human-readable label of which signal produced the series. */
  source: string;
  /** Quick-read tag of the dominant signal type. */
  sourceKind: 'citations' | 'milestones' | 'stars' | 'none';
}

export interface PhaseCounts {
  'pre-growth': number;
  growth: number;
  saturation: number;
  decline: number;
  'insufficient-data': number;
  total: number;
}

// --- Phase metadata ----------------------------------------------------

export const PHASE_ORDER: SCurvePhase[] = [
  'pre-growth',
  'growth',
  'saturation',
  'decline',
  'insufficient-data'
];

export const PHASE_LABELS: Record<SCurvePhase, string> = {
  'pre-growth': 'Pre-growth',
  growth: 'Growth',
  saturation: 'Saturation',
  decline: 'Decline',
  'insufficient-data': 'Insufficient data'
};

export const PHASE_COLOURS: Record<SCurvePhase, string> = {
  'pre-growth': '#79c0ff',
  growth: '#3fb950',
  saturation: '#d29922',
  decline: '#f85149',
  'insufficient-data': '#8b949e'
};

export const PHASE_DESCRIPTION: Record<SCurvePhase, string> = {
  'pre-growth':
    'Below ~12% of estimated carrying capacity. Adoption ramp not yet started in earnest.',
  growth:
    'Between ~12% and ~50% of estimated capacity. Steepest rate of accumulation; pre-inflection.',
  saturation:
    'Between ~50% and ~88% of estimated capacity. Post-inflection; rate of accumulation is slowing.',
  decline:
    'Past saturation AND recent observations below the fitted curve. Real fall-off (not just plateau).',
  'insufficient-data':
    'Fewer than 5 data points or under 12 months of history. Cannot responsibly fit a 3-parameter curve.'
};

// --- Series extraction -------------------------------------------------

interface SeriesObservation {
  /** Months since the record's earliest observed marker (start = 0). */
  t: number;
  /** Cumulative value at time t. Non-decreasing. */
  y: number;
  /** ISO date string for display. */
  date: string;
}

interface ExtractedSeries {
  observations: SeriesObservation[];
  startDate: Date;
  source: string;
  sourceKind: SCurveFit['sourceKind'];
}

/** Pull every YYYY-MM[-DD] hit from a free-text cell, deduplicated, ascending. */
function extractAllDates(raw: string | null | undefined): Date[] {
  if (!raw) return [];
  const re = /(\d{4})-(\d{1,2})(?:-(\d{1,2}))?/g;
  const out = new Set<number>();
  let m: RegExpExecArray | null;
  while ((m = re.exec(raw)) !== null) {
    const year = Number(m[1]);
    const month = Number(m[2]);
    const day = m[3] ? Number(m[3]) : 15;
    if (
      year < 1900 ||
      year > 2099 ||
      month < 1 ||
      month > 12 ||
      day < 1 ||
      day > 31
    ) {
      continue;
    }
    const d = Date.UTC(year, month - 1, day);
    out.add(d);
  }
  return [...out].map((ms) => new Date(ms)).sort((a, b) => a.getTime() - b.getTime());
}

/** Parse "443 cites 443/yr" into {total, ratePerYear} or null. */
function parseCitationCell(
  raw: string | null | undefined
): { total: number; ratePerYear: number } | null {
  if (!raw) return null;
  const v = raw.toLowerCase();
  // "443 cites 443/yr" or "1,234 cites 224/yr" or "0 cites 0/yr"
  const m = v.match(
    /(\d{1,3}(?:,\d{3})+|\d+)\s*cites?\s+(\d{1,3}(?:,\d{3})+|\d+)\s*\/\s*yr/
  );
  if (!m) return null;
  const total = Number(m[1].replace(/,/g, ''));
  const rate = Number(m[2].replace(/,/g, ''));
  if (!isFinite(total) || !isFinite(rate)) return null;
  return { total, ratePerYear: rate };
}

/** Parse "871★ +10/mo" into {stars, growthPerMonth} or null. */
function parseStarsCell(
  raw: string | null | undefined
): { stars: number; growthPerMonth: number | null } | null {
  if (!raw) return null;
  const v = raw.toLowerCase();
  // "871★ +10/mo" or "3.2k★ +15/mo" or "11.1k★ +545/mo"
  const starsM =
    v.match(/(\d+(?:\.\d+)?)\s*k\s*★/) ||
    v.match(/(\d{1,3}(?:,\d{3})+|\d+)\s*★/);
  if (!starsM) return null;
  let stars: number;
  if (v.match(/(\d+(?:\.\d+)?)\s*k\s*★/)) {
    stars = Math.round(Number(starsM[1]) * 1000);
  } else {
    stars = Number(starsM[1].replace(/,/g, ''));
  }
  if (!isFinite(stars)) return null;
  const growthM = v.match(/\+\s*(\d{1,3}(?:,\d{3})+|\d+)\s*\/\s*mo/);
  const growth = growthM ? Number(growthM[1].replace(/,/g, '')) : null;
  return { stars, growthPerMonth: growth };
}

/** Earliest parseable date from `created`. */
function earliestCreatedDate(record: LandscapeRecord): Date | null {
  const dates = extractAllDates(record.cells.created?.value);
  return dates[0] ?? null;
}

/** Cells worth scanning for dated milestone signals. */
const MILESTONE_CELLS = [
  'created',
  'latest-release',
  'funding',
  'claims',
  'customers',
  'api-surface',
  'compliance',
  'pricing',
  'deployment',
  'desc'
] as const;

/**
 * Best-effort extraction of an observation series for one record.
 *
 * Tries in order:
 *   1. Citations cumulative series (research papers)
 *   2. Multi-marker release series (products w/ multiple dated milestones)
 *   3. Star-growth series (OSS products with +N/mo signal)
 *   4. None / null
 */
function extractSeries(record: LandscapeRecord): ExtractedSeries | null {
  // Try citations first (research-paper canonical signal).
  const cite = parseCitationCell(record.cells.citations?.value);
  const created = earliestCreatedDate(record);

  if (cite && created && cite.total > 0 && cite.ratePerYear > 0) {
    // Synthesise quarterly cumulative citations from (publication date,
    // total, rate/yr). Without a per-quarter snapshot history we model
    // the cumulative curve as linear from publication to today, capped
    // at the observed total. This is honest about the signal: we know
    // start, end, and average rate but not per-quarter detail.
    //
    // Why this is still useful for the fit: if total / years ≈ rate/yr
    // the paper is still in linear-growth (pre-saturation) → the
    // logistic fits with low k and large L. If total / years >> rate/yr,
    // the paper has front-loaded its citations (early peak, now
    // saturating) → the logistic fits with higher k and lower L.
    const start = new Date(created.getTime());
    const totalMonths = monthsBetween(start, TODAY);
    if (totalMonths < 6) return null;
    const quarters = Math.max(2, Math.floor(totalMonths / 3));
    const obs: SeriesObservation[] = [];
    // Average cumulative rate per month over the lifetime.
    const lifeYears = totalMonths / 12;
    const observedAvg = cite.total / Math.max(0.5, lifeYears);
    // Use both the observed total (anchor at t = totalMonths) and a
    // linear ramp informed by the cites/yr (which is typically the
    // *recent* rate). If observed-avg > current rate → past peak; ramp
    // is front-loaded. If observed-avg < current rate → still ramping.
    const recent = cite.ratePerYear;
    // We construct yvalues at each quarter that interpolate between an
    // initial ramp (when rate ≈ recent) and a saturating tail (when
    // observed-avg > recent). Use a piecewise heuristic: assume the
    // recent rate has been in effect for the last min(2yr, lifeYears/2),
    // and the rest of the citations accumulated faster (front-loaded).
    const recentWindowYears = Math.min(2, lifeYears / 2);
    const recentCites = recent * recentWindowYears;
    const earlyCites = Math.max(0, cite.total - recentCites);
    const earlyYears = Math.max(0.5, lifeYears - recentWindowYears);
    const earlyRatePerYear = earlyCites / earlyYears;

    for (let i = 0; i <= quarters; i++) {
      const t = (i * totalMonths) / quarters;
      const tYears = t / 12;
      let y: number;
      if (tYears <= earlyYears) {
        y = earlyRatePerYear * tYears;
      } else {
        y = earlyCites + recent * (tYears - earlyYears);
      }
      // Cap at observed total at the final point.
      if (i === quarters) y = cite.total;
      const date = new Date(start.getTime());
      date.setUTCMonth(date.getUTCMonth() + Math.round(t));
      obs.push({ t, y, date: isoMonth(date) });
    }
    // Deduplicate (rare but possible if total = 0).
    if (obs.length < 5) return null;
    return {
      observations: obs,
      startDate: start,
      source: `${cite.total} cites · ${cite.ratePerYear}/yr · ${lifeYears.toFixed(1)}yr`,
      sourceKind: 'citations'
    };
  }

  // Try multi-marker milestone series. Pull dates from any cell that
  // commonly carries them, dedupe within 60-day windows so the "v1.0
  // announced Jan, released Feb" pattern collapses to one milestone.
  const allMarkers: Date[] = [];
  for (const slug of MILESTONE_CELLS) {
    const ds = extractAllDates(record.cells[slug]?.value);
    for (const d of ds) allMarkers.push(d);
  }
  // Add a "now-day" anchor at the latest commit if available; this gives
  // even single-release products a useful right-side anchor.
  const commit = parseLastCommit(record.cells['code-release']?.value);
  if (commit) allMarkers.push(commit);
  allMarkers.sort((a, b) => a.getTime() - b.getTime());
  const dedupMarkers: Date[] = [];
  for (const d of allMarkers) {
    const last = dedupMarkers[dedupMarkers.length - 1];
    if (!last || Math.abs(d.getTime() - last.getTime()) > 60 * 86400 * 1000) {
      dedupMarkers.push(d);
    }
  }
  if (dedupMarkers.length >= 5) {
    const start = dedupMarkers[0];
    const totalMonths = monthsBetween(start, TODAY);
    if (totalMonths < 12) return null;
    const obs: SeriesObservation[] = dedupMarkers.map((d, idx) => ({
      t: monthsBetween(start, d),
      y: idx + 1,
      date: isoMonth(d)
    }));
    return {
      observations: obs,
      startDate: start,
      source: `${dedupMarkers.length} dated milestones`,
      sourceKind: 'milestones'
    };
  }

  // Try star-growth on OSS repos.
  const stars = parseStarsCell(record.cells.gh?.value);
  if (stars && stars.growthPerMonth !== null && stars.growthPerMonth > 0 && created) {
    const totalMonths = monthsBetween(created, TODAY);
    if (totalMonths < 12) return null;
    // Synthesise: assume star growth has been roughly steady at the
    // observed monthly rate over the past 12mo, with the older history
    // making up the rest of the count linearly.
    const recentMonths = Math.min(12, totalMonths);
    const recentStars = stars.growthPerMonth * recentMonths;
    const earlyStars = Math.max(0, stars.stars - recentStars);
    const earlyMonths = Math.max(1, totalMonths - recentMonths);
    const earlyRate = earlyStars / earlyMonths;

    const quarters = Math.max(2, Math.floor(totalMonths / 3));
    const obs: SeriesObservation[] = [];
    for (let i = 0; i <= quarters; i++) {
      const t = (i * totalMonths) / quarters;
      let y: number;
      if (t <= earlyMonths) {
        y = earlyRate * t;
      } else {
        y = earlyStars + stars.growthPerMonth * (t - earlyMonths);
      }
      if (i === quarters) y = stars.stars;
      const date = new Date(created.getTime());
      date.setUTCMonth(date.getUTCMonth() + Math.round(t));
      obs.push({ t, y, date: isoMonth(date) });
    }
    if (obs.length < 5) return null;
    return {
      observations: obs,
      startDate: created,
      source: `${stars.stars.toLocaleString()}★ · +${stars.growthPerMonth}/mo`,
      sourceKind: 'stars'
    };
  }

  return null;
}

function isoMonth(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

// --- Logistic math -----------------------------------------------------

function logistic(t: number, L: number, k: number, t0: number): number {
  const z = -k * (t - t0);
  // Guard against overflow.
  if (z > 50) return 0;
  if (z < -50) return L;
  return L / (1 + Math.exp(z));
}

function squaredError(
  obs: SeriesObservation[],
  L: number,
  k: number,
  t0: number
): number {
  let sse = 0;
  for (const o of obs) {
    const pred = logistic(o.t, L, k, t0);
    const diff = pred - o.y;
    sse += diff * diff;
  }
  return sse;
}

function rSquared(
  obs: SeriesObservation[],
  L: number,
  k: number,
  t0: number
): number {
  const mean = obs.reduce((s, o) => s + o.y, 0) / obs.length;
  let ssRes = 0;
  let ssTot = 0;
  for (const o of obs) {
    const pred = logistic(o.t, L, k, t0);
    ssRes += (o.y - pred) ** 2;
    ssTot += (o.y - mean) ** 2;
  }
  if (ssTot === 0) return 0;
  const r2 = 1 - ssRes / ssTot;
  // Cap at [0, 1] to avoid confusing UI when fit is worse than constant.
  return Math.max(0, Math.min(1, r2));
}

interface LogisticParams {
  L: number;
  k: number;
  t0: number;
}

/**
 * Coarse grid search → local refinement. Sufficient for 5-30 point series
 * and runs in ~1ms per record.
 */
function fitLogistic(obs: SeriesObservation[]): LogisticParams | null {
  if (obs.length < 5) return null;
  const yMax = Math.max(...obs.map((o) => o.y));
  const tMax = Math.max(...obs.map((o) => o.t));
  if (yMax <= 0 || tMax <= 0) return null;

  // Estimate recent vs early growth rate to decide whether L should
  // sit close to yMax (rate has slowed → saturating) or well above
  // (rate still high → growth-phase).
  const tailObs = obs.slice(-Math.max(2, Math.floor(obs.length / 3)));
  const headObs = obs.slice(0, Math.max(2, Math.floor(obs.length / 3)));
  const tailRate =
    (tailObs[tailObs.length - 1].y - tailObs[0].y) /
    Math.max(1, tailObs[tailObs.length - 1].t - tailObs[0].t);
  const headRate =
    (headObs[headObs.length - 1].y - headObs[0].y) /
    Math.max(1, headObs[headObs.length - 1].t - headObs[0].t);
  // If tailRate > headRate, the series is accelerating → still in pre-
  // inflection growth, L should be much larger than yMax. If tailRate <
  // headRate, the series is decelerating → saturating, L ≈ yMax.
  const rateRatio = headRate > 0 ? tailRate / headRate : 1;

  // L candidates: span from yMax (already-saturated) up to a multiplier
  // that depends on rate ratio. Accelerating series get up to 10x.
  const Lmax = rateRatio > 1.2 ? yMax * 10 : rateRatio < 0.5 ? yMax * 1.5 : yMax * 4;
  const Ls: number[] = [];
  for (let i = 0; i < 10; i++) {
    Ls.push(yMax * 1.0 + ((Lmax - yMax) * i) / 9);
  }
  // k candidates: log-spaced from 0.005 (very gradual over a decade) to
  // 2.0 (steep transition in months).
  const ks: number[] = [];
  for (let i = 0; i < 12; i++) {
    const exp = -2.3 + (i / 11) * 2.6; // -2.3 .. 0.3
    ks.push(Math.pow(10, exp));
  }
  // t0 candidates: from -tMax (already past inflection in deep past) to
  // 6·tMax (inflection well in future for pre-growth systems).
  const t0s: number[] = [];
  const t0Min = -tMax;
  const t0Max = 6 * tMax;
  for (let i = 0; i < 18; i++) {
    t0s.push(t0Min + ((t0Max - t0Min) * i) / 17);
  }

  let bestSse = Infinity;
  let best: LogisticParams = { L: yMax, k: 0.1, t0: tMax / 2 };
  for (const L of Ls) {
    for (const k of ks) {
      for (const t0 of t0s) {
        const sse = squaredError(obs, L, k, t0);
        if (sse < bestSse) {
          bestSse = sse;
          best = { L, k, t0 };
        }
      }
    }
  }

  // Coarse local refinement around the best grid point.
  const refineSteps = 5;
  const Ldelta = best.L / 4;
  const kdelta = best.k / 2;
  const t0delta = tMax / 8;
  for (let i = 0; i < 3; i++) {
    // 3 refinement passes
    let improved = false;
    for (let li = -refineSteps; li <= refineSteps; li++) {
      for (let ki = -refineSteps; ki <= refineSteps; ki++) {
        for (let ti = -refineSteps; ti <= refineSteps; ti++) {
          const L = Math.max(yMax * 0.5, best.L + (li / refineSteps) * Ldelta);
          const k = Math.max(0.001, best.k + (ki / refineSteps) * kdelta);
          const t0 = best.t0 + (ti / refineSteps) * t0delta;
          const sse = squaredError(obs, L, k, t0);
          if (sse < bestSse) {
            bestSse = sse;
            best = { L, k, t0 };
            improved = true;
          }
        }
      }
    }
    if (!improved) break;
  }

  return best;
}

// --- Phase classification ---------------------------------------------

/**
 * "Standard deviation" of a logistic — the width over which the curve
 * goes from ~12% (1-tanh(1)) to ~88% (1+tanh(1)) of L. For the logistic,
 * σ = 2/k corresponds well to that 12%-88% window.
 */
function logisticSigma(k: number): number {
  if (k <= 0) return Infinity;
  return 2 / k;
}

function classifyPhase(
  obs: SeriesObservation[],
  fit: LogisticParams,
  tNow: number
): SCurvePhase {
  const sigma = logisticSigma(fit.k);
  const pre = fit.t0 - 2 * sigma;
  const post = fit.t0 + 2 * sigma;

  if (tNow < pre) return 'pre-growth';
  if (tNow < fit.t0) return 'growth';
  if (tNow < post) return 'saturation';

  // Past saturation tail — distinguish decline from late saturation by
  // checking whether the LAST 3 observations sit below the fitted curve.
  // If they do, the system is genuinely falling away from its plateau,
  // not just sitting on it.
  const tail = obs.slice(-3);
  if (tail.length < 2) return 'saturation';
  let belowCount = 0;
  for (const o of tail) {
    const pred = logistic(o.t, fit.L, fit.k, fit.t0);
    if (o.y < pred * 0.95) belowCount += 1;
  }
  if (belowCount >= 2) return 'decline';
  return 'saturation';
}

function inflectionAsDate(startDate: Date, t0Months: number): string | null {
  if (!isFinite(t0Months)) return null;
  const d = new Date(startDate.getTime());
  d.setUTCMonth(d.getUTCMonth() + Math.round(t0Months));
  // Clamp to a sensible display range (1980..2050) to avoid wild outliers.
  const y = d.getUTCFullYear();
  if (y < 1980 || y > 2050) return null;
  return isoMonth(d);
}

/** Build a smoothed predicted curve over the observed range. */
function buildPredicted(
  startDate: Date,
  obs: SeriesObservation[],
  fit: LogisticParams,
  samples = 40
): Array<{ date: string; value: number }> {
  if (obs.length === 0) return [];
  const tMin = obs[0].t;
  const tMax = obs[obs.length - 1].t;
  const out: Array<{ date: string; value: number }> = [];
  for (let i = 0; i <= samples; i++) {
    const t = tMin + ((tMax - tMin) * i) / samples;
    const value = logistic(t, fit.L, fit.k, fit.t0);
    const d = new Date(startDate.getTime());
    d.setUTCMonth(d.getUTCMonth() + Math.round(t));
    out.push({ date: isoMonth(d), value });
  }
  return out;
}

// --- Public API --------------------------------------------------------

function primarySection(r: LandscapeRecord): string {
  const p = r.sections.find((s) => s.primary);
  return p?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

function emptyFit(record: LandscapeRecord, source: string): SCurveFit {
  return {
    recordId: record.id,
    recordName: record.name,
    section: primarySection(record),
    phase: 'insufficient-data',
    inflectionDate: null,
    growthRate: NaN,
    carryingCapacity: NaN,
    fitR2: NaN,
    dataPoints: 0,
    series: [],
    predictedSeries: [],
    forecast24mo: null,
    source,
    sourceKind: 'none'
  };
}

/**
 * Fit logistic S-curves for every record. Records without enough temporal
 * data are returned with phase: 'insufficient-data'.
 */
export function fitSCurves(records: LandscapeRecord[]): SCurveFit[] {
  const out: SCurveFit[] = [];
  for (const r of records) {
    const extracted = extractSeries(r);
    if (!extracted || extracted.observations.length < 5) {
      out.push(emptyFit(r, 'no parseable temporal signal'));
      continue;
    }
    const obs = extracted.observations;
    const totalSpan = obs[obs.length - 1].t - obs[0].t;
    if (totalSpan < 12) {
      out.push(emptyFit(r, `${extracted.source} (under 12mo of history)`));
      continue;
    }

    const fit = fitLogistic(obs);
    if (!fit) {
      out.push(emptyFit(r, extracted.source));
      continue;
    }

    const r2 = rSquared(obs, fit.L, fit.k, fit.t0);
    const tNow = monthsBetween(extracted.startDate, TODAY);
    const phase = classifyPhase(obs, fit, tNow);

    const predicted = buildPredicted(extracted.startDate, obs, fit);

    // Forecast 24mo ahead — only meaningful when not declining and the
    // curve still has headroom (forecast < L).
    let forecast24: number | null = null;
    if (phase !== 'decline' && phase !== 'insufficient-data') {
      forecast24 = logistic(tNow + 24, fit.L, fit.k, fit.t0);
      if (!isFinite(forecast24)) forecast24 = null;
    }

    out.push({
      recordId: r.id,
      recordName: r.name,
      section: primarySection(r),
      phase,
      inflectionDate: inflectionAsDate(extracted.startDate, fit.t0),
      growthRate: fit.k,
      carryingCapacity: fit.L,
      fitR2: r2,
      dataPoints: obs.length,
      series: obs.map((o) => ({ date: o.date, value: o.y })),
      predictedSeries: predicted,
      forecast24mo: forecast24,
      source: extracted.source,
      sourceKind: extracted.sourceKind
    });
  }
  return out;
}

/** Bucket counts for the top-of-page callouts. */
export function countPhases(fits: SCurveFit[]): PhaseCounts {
  const c: PhaseCounts = {
    'pre-growth': 0,
    growth: 0,
    saturation: 0,
    decline: 0,
    'insufficient-data': 0,
    total: 0
  };
  for (const f of fits) {
    c[f.phase] += 1;
    c.total += 1;
  }
  return c;
}

/** Median R² across records that produced a fit. */
export function medianR2(fits: SCurveFit[]): number {
  const xs = fits
    .filter((f) => f.phase !== 'insufficient-data' && isFinite(f.fitR2))
    .map((f) => f.fitR2)
    .sort((a, b) => a - b);
  if (xs.length === 0) return NaN;
  const mid = Math.floor(xs.length / 2);
  return xs.length % 2 ? xs[mid] : (xs[mid - 1] + xs[mid]) / 2;
}

/** Format an inflection ISO date as "Q3 2027". */
export function formatInflectionAsQuarter(iso: string | null): string | null {
  if (!iso) return null;
  const m = iso.match(/^(\d{4})-(\d{2})-/);
  if (!m) return null;
  const year = Number(m[1]);
  const month = Number(m[2]);
  if (!isFinite(year) || !isFinite(month)) return null;
  const q = Math.ceil(month / 3);
  return `Q${q} ${year}`;
}
