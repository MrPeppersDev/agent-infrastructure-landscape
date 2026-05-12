// Section-aggregate statistics for issue #15.
//
// Pure functions only — no Svelte / no DOM. Consumed by
// routes/sections/+page.svelte for the per-section cards and the
// 2-section compare view.
//
// Design notes:
// - Aggregations are O(R) per section (R = records in that section). We
//   compute everything in a single pass via `aggregateSection`.
// - Numeric extraction is a local heuristic. If issue #14 lands a shared
//   parseNumberFromCell helper, this file should switch to that import —
//   for now we ship our own (see DECISIONS.md 2026-05-07 entry).
// - "Section" here means the *primary* SectionMembership only. The
//   `sections` array can have multiple entries per record but only the
//   primary placement counts for this view (matches FilterRail behaviour).
// - The 20-section catalog is derived from the data rather than
//   hard-coded; we just take the unique set of primary sections, sorted
//   by row count desc.
//
// Reversal cost: low. Helpers are pure.
//
// Reused by Phase 4 (graph): the per-section taxonomy histograms make a
// natural "colour the cluster by storage axis" overlay; node tooltips
// can pull the median funding / citation numbers from here directly.
import type {
  LandscapeRecord,
  Tier,
  TaxonomyValue,
  Cell
} from './types';
import {
  canonicaliseLicense,
  canonicaliseDeployment,
  type TaxonomyFacet,
  TAXONOMY_FACETS
} from './stores/filters';

// --- Number extraction --------------------------------------------------
//
// Cell values are free-text like "1.2k stars", "$2.4B raised", "47000
// citations (Semantic Scholar)". We greedy-match the first number with
// optional suffix and ignore the rest of the string. Failures return null
// (so callers can skip them in median/mean computation rather than have
// 0 drag the average down).
//
// Recognised suffixes (case-insensitive):
//   k = 1e3   m / mm = 1e6   b / bn = 1e9   t = 1e12
// "$" / "€" / "£" are stripped. Commas inside the number are stripped.

const NUMBER_RE = /([$€£]?)\s*(-?[\d][\d,]*\.?\d*)\s*([kmbt]|mm|bn)?/i;

const SUFFIX: Record<string, number> = {
  k: 1e3,
  m: 1e6,
  mm: 1e6,
  b: 1e9,
  bn: 1e9,
  t: 1e12
};

export function parseNumber(cell: Cell | undefined): number | null {
  if (!cell || cell.status !== 'real-data') return null;
  const v = cell.value;
  if (!v) return null;
  const match = NUMBER_RE.exec(v);
  if (!match) return null;
  const numStr = match[2].replace(/,/g, '');
  const n = parseFloat(numStr);
  if (!Number.isFinite(n)) return null;
  const suffix = match[3]?.toLowerCase();
  const mult = suffix ? SUFFIX[suffix] ?? 1 : 1;
  return n * mult;
}

// --- Aggregation primitives --------------------------------------------

export interface NumericStats {
  count: number; // sample size that parsed
  mean: number | null;
  median: number | null;
  min: number | null;
  max: number | null;
}

function numericStats(values: (number | null)[]): NumericStats {
  const parsed = values.filter((v): v is number => v !== null);
  if (parsed.length === 0) {
    return { count: 0, mean: null, median: null, min: null, max: null };
  }
  const sorted = [...parsed].sort((a, b) => a - b);
  const sum = parsed.reduce((acc, n) => acc + n, 0);
  const mid = Math.floor(sorted.length / 2);
  const median =
    sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
  return {
    count: parsed.length,
    mean: sum / parsed.length,
    median,
    min: sorted[0],
    max: sorted[sorted.length - 1]
  };
}

export interface CategoryCount {
  value: string;
  count: number;
}

function countCategories(values: string[]): CategoryCount[] {
  const map = new Map<string, number>();
  for (const v of values) map.set(v, (map.get(v) ?? 0) + 1);
  return [...map.entries()]
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
}

function primarySection(r: LandscapeRecord): string {
  const p = r.sections.find((s) => s.primary);
  return p?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

function primaryTaxonomy(values: TaxonomyValue[]): string {
  const p = values.find((v) => v.primary);
  return p?.value ?? values[0]?.value ?? 'unspecified';
}

// --- Section aggregate -------------------------------------------------

export interface SectionAggregate {
  section: string;
  rowCount: number;
  tierCounts: Record<Tier, number>; // T1..T5
  taxonomy: Record<TaxonomyFacet, CategoryCount[]>; // axis → sorted
  license: CategoryCount[];
  deployment: CategoryCount[];
  numeric: {
    citations: NumericStats;
    gh: NumericStats;
    funding: NumericStats;
    mindshare: NumericStats;
  };
}

export function aggregateSection(
  section: string,
  records: LandscapeRecord[]
): SectionAggregate {
  const tierCounts: Record<Tier, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  const taxonomyBuckets: Record<TaxonomyFacet, string[]> = {
    storage: [],
    retrieval: [],
    persistence: [],
    update: [],
    unit: [],
    governance: [],
    conflict: []
  };
  const licenseBucket: string[] = [];
  const deploymentBucket: string[] = [];
  const citations: (number | null)[] = [];
  const gh: (number | null)[] = [];
  const funding: (number | null)[] = [];
  const mindshare: (number | null)[] = [];

  for (const r of records) {
    tierCounts[r.tier]++;
    for (const axis of TAXONOMY_FACETS) {
      taxonomyBuckets[axis].push(primaryTaxonomy(r.taxonomy[axis] ?? []));
    }
    const lic = r.cells.license;
    licenseBucket.push(
      canonicaliseLicense(lic?.value ?? '', lic?.status ?? 'no-data')
    );
    const dep = r.cells.deployment;
    deploymentBucket.push(
      canonicaliseDeployment(dep?.value ?? '', dep?.status ?? 'no-data')
    );
    citations.push(parseNumber(r.cells.citations));
    gh.push(parseNumber(r.cells.gh));
    funding.push(parseNumber(r.cells.funding));
    mindshare.push(parseNumber(r.cells.mindshare));
  }

  const taxonomy = {} as Record<TaxonomyFacet, CategoryCount[]>;
  for (const axis of TAXONOMY_FACETS) {
    taxonomy[axis] = countCategories(taxonomyBuckets[axis]);
  }

  return {
    section,
    rowCount: records.length,
    tierCounts,
    taxonomy,
    license: countCategories(licenseBucket),
    deployment: countCategories(deploymentBucket),
    numeric: {
      citations: numericStats(citations),
      gh: numericStats(gh),
      funding: numericStats(funding),
      mindshare: numericStats(mindshare)
    }
  };
}

/**
 * Group records by primary section, then aggregate each group. Returns
 * sections sorted by rowCount desc — the most populous catalog area first.
 */
export function aggregateAllSections(
  records: LandscapeRecord[]
): SectionAggregate[] {
  const groups = new Map<string, LandscapeRecord[]>();
  for (const r of records) {
    const s = primarySection(r);
    let bucket = groups.get(s);
    if (!bucket) {
      bucket = [];
      groups.set(s, bucket);
    }
    bucket.push(r);
  }
  return [...groups.entries()]
    .map(([section, recs]) => aggregateSection(section, recs))
    .sort((a, b) => b.rowCount - a.rowCount);
}

// --- Display helpers ---------------------------------------------------

/** Compact number formatter: 1234 → "1.2k", 2.5e9 → "$2.5B" with `currency`. */
export function formatCompact(n: number | null, currency = false): string {
  if (n === null || !Number.isFinite(n)) return '—';
  const prefix = currency ? '$' : '';
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${prefix}${(n / 1e12).toFixed(1)}T`;
  if (abs >= 1e9) return `${prefix}${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${prefix}${(n / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${prefix}${(n / 1e3).toFixed(1)}k`;
  return `${prefix}${n.toFixed(0)}`;
}

/** Top-N categories with a "+ N other" rollup for the long tail. */
export function topNWithOther(
  cats: CategoryCount[],
  n = 3
): { top: CategoryCount[]; otherCount: number; otherDistinct: number } {
  if (cats.length <= n) {
    return { top: cats, otherCount: 0, otherDistinct: 0 };
  }
  const top = cats.slice(0, n);
  const rest = cats.slice(n);
  const otherCount = rest.reduce((acc, c) => acc + c.count, 0);
  return { top, otherCount, otherDistinct: rest.length };
}

/** Signed delta string for compare mode. */
export function deltaLabel(a: number | null, b: number | null, currency = false): string {
  if (a === null || b === null) return '—';
  const diff = b - a;
  if (diff === 0) return '±0';
  const sign = diff > 0 ? '+' : '−';
  return `${sign}${formatCompact(Math.abs(diff), currency)}`;
}
