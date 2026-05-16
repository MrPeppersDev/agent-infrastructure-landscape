// Wang-Song-Barabási log-normal citation model (issue #58).
//
// SINGLE SOURCE OF TRUTH: web/src/lib/analyses/citation-prediction.ts.
// This file is a verbatim mirror — the mcp/ package ships as a
// standalone npm-installable surface, so a TypeScript rootDir-respecting
// copy lives here. View-only helpers (PHASE_COLOURS, etc.) are omitted.
// Where logic overlaps with the Svelte UI we mirror exactly, so MCP /
// CLI / web all return identical fits.
//
// See web/src/lib/analyses/citation-prediction.ts for the full
// methodology docstring + math derivation.

import type { LandscapeRecord } from './types.js';

export type CitationPhase =
  | 'pre-growth'
  | 'growth'
  | 'saturation'
  | 'underfit-data';

export interface CitationFit {
  recordId: string;
  recordName: string;
  section: string;
  tier: number;
  publishedYear: number;
  yearsObserved: number;
  observedCitations: number;
  observedInfluential: number;
  lambda: number;
  mu: number;
  sigma: number;
  asymptote: number;
  asymptoteCI: [number, number];
  predictedAt10y: number;
  fitR2: number;
  phase: CitationPhase;
  breakoutProbability: number;
  observedSeries: Array<{ t: number; y: number }>;
  fittedSeries: Array<{ t: number; y: number }>;
  extrapolatedSeries: Array<{ t: number; y: number }>;
  source: string;
  sourceKind: 'trajectory' | 'synthesised' | 'none';
}

// =========================================================================
// WSB math primitives
// =========================================================================

function normalCdf(x: number): number {
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
  const exponent = lambda * phi;
  if (!isFinite(exponent)) return 0;
  if (exponent > 50) return m * (Math.exp(50) - 1);
  if (exponent < -50) return 0;
  return m * (Math.exp(exponent) - 1);
}

function wsbAsymptote(m: number, lambda: number): number {
  if (lambda > 50) return m * (Math.exp(50) - 1);
  if (lambda < 0) return 0;
  return m * (Math.exp(lambda) - 1);
}

// =========================================================================
// Cell parsers
// =========================================================================

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
      if (
        typeof year !== 'number' ||
        !isFinite(year) ||
        year < 1900 ||
        year > 2099
      )
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

  let m = v.match(/([\d.]+k?)\s*cites?\s+([\d.]+k?)\s*\/\s*yr/);
  if (!m) {
    m = v.match(
      /(\d{1,3}(?:,\d{3})+|\d+)\s*cites?\s+(\d{1,3}(?:,\d{3})+|\d+)\s*\/\s*yr/
    );
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

function parsePublicationYear(raw: string | null | undefined): number | null {
  if (!raw) return null;
  const m = raw.match(/(19|20)\d{2}/);
  if (!m) return null;
  const y = Number(m[0]);
  if (y < 1950 || y > 2099) return null;
  return y;
}

// =========================================================================
// Field constant m
// =========================================================================

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
    cachedFieldConstant = 30;
    return cachedFieldConstant;
  }
  const mid = Math.floor(totals.length / 2);
  cachedFieldConstant =
    totals.length % 2 ? totals[mid] : (totals[mid - 1] + totals[mid]) / 2;
  return cachedFieldConstant;
}

export function resetFieldConstant(): void {
  cachedFieldConstant = null;
}

// =========================================================================
// Series extraction
// =========================================================================

interface ExtractedSeries {
  observations: Array<{ t: number; y: number }>;
  publishedYear: number;
  observedCitations: number;
  observedInfluential: number;
  source: string;
  sourceKind: 'trajectory' | 'synthesised';
}

function extractSeries(record: LandscapeRecord): ExtractedSeries | null {
  const trajectory = parseCitationTrajectory(
    record.cells['citation-trajectory']?.value
  );
  if (trajectory && trajectory.length >= 3) {
    const firstYear = trajectory[0].year;
    const lastYear = trajectory[trajectory.length - 1].year;
    if (lastYear > firstYear) {
      const observations = trajectory.map((p) => ({
        t: p.year - firstYear + 1,
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

  const cite = parseCitationsCell(record.cells['citations']?.value);
  const created = parsePublicationYear(record.cells['created']?.value);
  if (!cite || cite.total <= 0 || !created) return null;
  const TODAY_YEAR = 2026;
  const lifeYears = Math.max(1, TODAY_YEAR - created);
  if (lifeYears < 1) return null;

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
    observedInfluential: 0,
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

const LAMBDA_GRID: number[] = (() => {
  const out: number[] = [];
  for (let i = 0; i < 12; i++) {
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

function seedFromId(id: string): number {
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
    resample.sort((a, b2) => a.t - b2.t);

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

function isAcademicPaper(r: LandscapeRecord): boolean {
  const hasTraj = r.cells['citation-trajectory']?.status === 'real-data';
  const citesCell = r.cells['citations']?.value ?? '';
  const hasParseable = /cites?\s+[\d.]+k?\s*\/\s*yr/i.test(citesCell);
  return hasTraj || hasParseable;
}

// =========================================================================
// Public API
// =========================================================================

export function fitCitationCurves(records: LandscapeRecord[]): CitationFit[] {
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
      breakoutProbability: 0,
      observedSeries: obs,
      fittedSeries: fitted,
      extrapolatedSeries: extrapolated,
      source: extracted.source,
      sourceKind: extracted.sourceKind
    });
  }

  // Second pass: compute breakout probability via median asymptote.
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

export function findFitById(
  fits: CitationFit[],
  id: string
): CitationFit | undefined {
  return fits.find((f) => f.recordId === id);
}
