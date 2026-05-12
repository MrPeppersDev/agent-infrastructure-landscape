// Pure helpers for top-N leaderboards (issue #14).
//
// Why a separate module: the page component would otherwise carry ~150 lines
// of parsing/ranking logic, which is hard to unit-test through Svelte. Pure
// functions over records + edges are also reusable by Phase 4 (graph) and
// Phase 5 (export / share-card endpoints).
//
// Number extraction lives here too. Cell values in landscape.json are
// human-readable strings (see SCHEMA.md §2.5), so every leaderboard that
// ranks on a "numeric-ish" column has to parse them back into numbers. We
// do that with a single tolerant regex-driven extractor — see
// extractNumber().

import type { Edge, EdgeType, LandscapeRecord, Tier } from './types';

/**
 * Pulls the headline numeric value out of a free-text cell.
 *
 * Heuristics (documented in DECISIONS.md 2026-05-07 "leaderboard number
 * extraction"):
 *   - The FIRST number-with-suffix token wins. We rely on the corpus
 *     convention that the headline always leads the cell (e.g.
 *     "1.2k cites · 5/mo" — the 1.2k is the headline; the 5/mo is rate).
 *   - "$" prefix → dollar amount, suffix multipliers k/m/b/t (case-insensitive
 *     and tolerant of "$2.5B" / "$2.5 billion" / "$2m total").
 *   - Bare number + k/M/B/T (e.g. "18.8k★", "1.2k cites") multiplies.
 *   - Plain integers / decimals ("405 cites", "443") pass through.
 *   - Returns null when nothing parses or the token is clearly noise
 *     ("undisclosed", "n/a", "bootstrapped").
 *
 * We deliberately don't try to be smart about ranges ("$2–5M"), aggregated
 * sums across rounds, or composite "$X total $Yval"-style headlines beyond
 * grabbing the first dollar number — for ranking purposes the leading
 * figure is the right signal in 95%+ of cells.
 */
export function extractNumber(raw: string | null | undefined): number | null {
  if (!raw) return null;
  const s = raw.trim();
  if (s.length === 0) return null;

  // Common "no data" sentinels in the corpus.
  const lower = s.toLowerCase();
  if (
    lower.startsWith('undisclosed') ||
    lower.startsWith('bootstrapped') ||
    lower.startsWith('n/a') ||
    lower.startsWith('not applicable') ||
    lower.startsWith('searched not found') ||
    lower.startsWith('not yet')
  ) {
    return null;
  }

  // Dollar form first — covers "$400M", "$2.5B val", "~$20M total".
  const dollar = s.match(/\$\s*([\d.,]+)\s*([kmbt])?/i);
  if (dollar) {
    const n = parseFloat(dollar[1].replace(/,/g, ''));
    if (!Number.isNaN(n)) return applyMultiplier(n, dollar[2]);
  }

  // Generic leading number — possibly with k/M/B/T suffix. Skips tokens
  // that begin with the dollar sign (handled above). Also skips a bare
  // leading "0" that's followed by " (too recent" — citation cells use
  // that convention to mean "not yet indexed", not literally zero.
  if (/^0\s*\(/.test(s)) return null;

  const generic = s.match(/([\d][\d.,]*)\s*([kmbt])?/i);
  if (generic) {
    const n = parseFloat(generic[1].replace(/,/g, ''));
    if (!Number.isNaN(n)) return applyMultiplier(n, generic[2]);
  }

  return null;
}

function applyMultiplier(n: number, suffix: string | undefined): number {
  if (!suffix) return n;
  switch (suffix.toLowerCase()) {
    case 'k':
      return n * 1_000;
    case 'm':
      return n * 1_000_000;
    case 'b':
      return n * 1_000_000_000;
    case 't':
      return n * 1_000_000_000_000;
    default:
      return n;
  }
}

// --- Ranking primitives ------------------------------------------------

export interface Ranked {
  record: LandscapeRecord;
  value: number;
  /** Original cell string for display (so we don't lose "1.2k cites · 5/mo"). */
  display: string;
}

/**
 * Returns the top-N records by `extractor(record)`, descending. Records
 * for which the extractor returns null are dropped.
 */
export function topBy(
  records: LandscapeRecord[],
  extractor: (r: LandscapeRecord) => { value: number | null; display: string },
  n: number
): Ranked[] {
  const out: Ranked[] = [];
  for (const r of records) {
    const { value, display } = extractor(r);
    if (value === null || Number.isNaN(value)) continue;
    out.push({ record: r, value, display });
  }
  out.sort((a, b) => b.value - a.value);
  return out.slice(0, n);
}

// --- Curated extractors ------------------------------------------------

export function cellExtractor(slug: 'citations' | 'gh' | 'funding' | 'mindshare') {
  return (r: LandscapeRecord) => {
    const cell = r.cells[slug];
    if (!cell || cell.status !== 'real-data') {
      return { value: null, display: cell?.value ?? '' };
    }
    return { value: extractNumber(cell.value), display: cell.value };
  };
}

/**
 * Counts inbound edges of `types` per target record id. Used for the two
 * graph-based leaderboards (inbound citations, inbound integrations).
 */
export function inboundEdgeCounts(
  edges: Edge[],
  types: EdgeType[]
): Map<string, number> {
  const set = new Set(types);
  const counts = new Map<string, number>();
  for (const e of edges) {
    if (!set.has(e.type)) continue;
    counts.set(e.target, (counts.get(e.target) ?? 0) + 1);
  }
  return counts;
}

export function topByInboundEdges(
  records: LandscapeRecord[],
  edges: Edge[],
  types: EdgeType[],
  n: number
): Ranked[] {
  const counts = inboundEdgeCounts(edges, types);
  const out: Ranked[] = [];
  for (const r of records) {
    const c = counts.get(r.id) ?? 0;
    if (c === 0) continue;
    out.push({ record: r, value: c, display: `${c}` });
  }
  out.sort((a, b) => b.value - a.value);
  return out.slice(0, n);
}

// --- Custom-mode column registry ---------------------------------------

export type CustomColumn =
  | 'citations'
  | 'gh'
  | 'funding'
  | 'mindshare'
  | 'integration-count';

export const CUSTOM_COLUMNS: { value: CustomColumn; label: string }[] = [
  { value: 'citations', label: 'Citations' },
  { value: 'gh', label: 'GitHub stars' },
  { value: 'funding', label: 'Funding ($)' },
  { value: 'mindshare', label: 'Mindshare (leading number)' },
  { value: 'integration-count', label: 'Integration count (cell)' }
];

/**
 * Returns a {value, display} extractor for any custom-mode column.
 * "integration-count" is a free-text cell whose headline is usually a
 * raw integer; extractNumber handles it fine.
 */
export function customExtractor(col: CustomColumn) {
  if (col === 'integration-count') {
    return (r: LandscapeRecord) => {
      const cell = r.cells['integration-count'];
      if (!cell || cell.status !== 'real-data') {
        return { value: null, display: cell?.value ?? '' };
      }
      return { value: extractNumber(cell.value), display: cell.value };
    };
  }
  return cellExtractor(col);
}

// --- Tier / section filter helpers (for custom mode) -------------------

export const ALL_TIERS: Tier[] = [1, 2, 3, 4, 5];

export function primarySection(r: LandscapeRecord): string {
  const p = r.sections.find((s) => s.primary);
  return p?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

export function distinctSections(records: LandscapeRecord[]): string[] {
  const s = new Set<string>();
  for (const r of records) s.add(primarySection(r));
  return [...s].sort((a, b) => a.localeCompare(b));
}

export function filterForCustom(
  records: LandscapeRecord[],
  tiers: Set<Tier>,
  sections: Set<string>
): LandscapeRecord[] {
  if (tiers.size === 0 && sections.size === 0) return records;
  return records.filter((r) => {
    if (tiers.size > 0 && !tiers.has(r.tier)) return false;
    if (sections.size > 0 && !sections.has(primarySection(r))) return false;
    return true;
  });
}

// --- T3/T4 helper used by the citations board --------------------------

export function isResearchTier(r: LandscapeRecord): boolean {
  return r.tier === 3 || r.tier === 4;
}
