// Pure helpers for the /timeline view (issue #13).
//
// The chart is a stacked bar histogram of "when systems were created" bucketed
// into year-quarters. The data lives in `record.cells.created.value`, which is
// free-text — heuristic parsing is unavoidable. See docs/DECISIONS.md
// (2026-05-07 entry "Timeline date parsing") for the rules.
//
// Everything in this module is pure: feed it records, get back numbers. Keeps
// the Svelte component thin and the parsing rules independently testable
// (and reusable for Phase 4's graph view, which will want the same
// founding-year heuristic to colour nodes by era).

import type { LandscapeRecord, Tier } from '$lib/types';

export type Quarter = 1 | 2 | 3 | 4;

export interface ParsedDate {
  year: number;
  quarter: Quarter;
}

/** A single (year, quarter) bucket. */
export interface BucketKey {
  year: number;
  quarter: Quarter;
}

/** Stable string key for a bucket. */
export function bucketLabel(b: BucketKey): string {
  return `${b.year}-Q${b.quarter}`;
}

/**
 * Parse a free-text "created" cell into a year + quarter, or null if we
 * can't get even a year out of it. Heuristics (first match wins):
 *
 *   1. Full date: "2023-04-15"  → year=2023, quarter from month
 *   2. Year+month: "2023-04"    → year=2023, quarter from month
 *   3. Year range: "2022-2024"  → earlier year, Q1
 *   4. Bare year: "2023"        → 2023, Q1
 *   5. Year embedded in prose: "Announced 2026-04 (..." → first YYYY-MM
 *      hit, else first YYYY hit. Falls through to (4)/(2) via regex.
 *
 * Returns null for "searched not found", "no data", "Pre-existing",
 * "Various", and anything without a 4-digit year between 1900 and 2099.
 *
 * The 1900-2099 floor/ceiling rejects things like phone numbers or
 * version strings ("Python 3.11") from accidentally producing a year.
 */
export function parseCreatedDate(raw: string | null | undefined): ParsedDate | null {
  if (!raw) return null;
  const v = raw.trim();
  if (v.length === 0) return null;

  // Bail on common sentinel phrasings before regex even runs — cheaper
  // and lets us be lenient with the regex below (no need to anchor it).
  const lower = v.toLowerCase();
  if (lower === 'no data' || lower === 'searched not found') return null;
  if (lower.includes('pre-existing') || lower === 'various') return null;

  // (1) + (2): YYYY-MM[-DD] anywhere in the string. We match anywhere
  // (not anchored) so prose like "Announced 2026-04 (GTC season)" still
  // resolves. We pick the *first* such occurrence on the assumption that
  // the founding/release date is named first; later dates are usually
  // GA / acquisition / etc. and less interesting for "when was this
  // created".
  const ymd = v.match(/(\d{4})-(\d{1,2})(?:-(\d{1,2}))?/);
  if (ymd) {
    const year = Number(ymd[1]);
    const month = Number(ymd[2]);
    if (year >= 1900 && year <= 2099 && month >= 1 && month <= 12) {
      return { year, quarter: monthToQuarter(month) };
    }
  }

  // (3): YYYY-YYYY range. Match before bare-year so we don't grab just
  // the first year and lose the range context.
  const range = v.match(/(\d{4})\s*[-–]\s*(\d{4})/);
  if (range) {
    const a = Number(range[1]);
    const b = Number(range[2]);
    if (a >= 1900 && a <= 2099 && b >= 1900 && b <= 2099) {
      return { year: Math.min(a, b), quarter: 1 };
    }
  }

  // (4)/(5): first plausible bare year.
  const yearOnly = v.match(/\b(\d{4})\b/);
  if (yearOnly) {
    const year = Number(yearOnly[1]);
    if (year >= 1900 && year <= 2099) {
      return { year, quarter: 1 };
    }
  }

  return null;
}

function monthToQuarter(month: number): Quarter {
  if (month <= 3) return 1;
  if (month <= 6) return 2;
  if (month <= 9) return 3;
  return 4;
}

/** Primary section helper (mirrors stores/filters.ts but kept local so
 *  timeline.ts has no Svelte dependency and stays unit-testable). */
export function primarySection(r: LandscapeRecord): string {
  const p = r.sections.find((s) => s.primary);
  return p?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

export interface BucketRow {
  key: string;          // "2023-Q1"
  year: number;
  quarter: Quarter;
  /** Count per tier (1..5). Indices 0..4. */
  byTier: [number, number, number, number, number];
  /** Records that fell into this bucket — preserves order for tooltips. */
  records: LandscapeRecord[];
}

/**
 * Group records into year-quarter buckets, optionally filtered to a single
 * section. Returns buckets in chronological order, with empty buckets
 * inserted between min and max year-quarters so the X-axis is continuous
 * (otherwise "2023-Q1, 2023-Q4, 2024-Q2" would look fine but mislead the
 * eye about pacing — empty quarters are information).
 */
export function bucketRecords(
  records: LandscapeRecord[],
  sectionFilter: string | null
): BucketRow[] {
  const filtered = sectionFilter
    ? records.filter((r) => primarySection(r) === sectionFilter)
    : records;

  const map = new Map<string, BucketRow>();
  let minYear = Infinity;
  let maxYear = -Infinity;

  for (const r of filtered) {
    const parsed = parseCreatedDate(r.cells.created?.value);
    if (!parsed) continue;
    const key = `${parsed.year}-Q${parsed.quarter}`;
    let row = map.get(key);
    if (!row) {
      row = {
        key,
        year: parsed.year,
        quarter: parsed.quarter,
        byTier: [0, 0, 0, 0, 0],
        records: []
      };
      map.set(key, row);
    }
    const tierIdx = (r.tier - 1) as 0 | 1 | 2 | 3 | 4;
    row.byTier[tierIdx] += 1;
    row.records.push(r);
    if (parsed.year < minYear) minYear = parsed.year;
    if (parsed.year > maxYear) maxYear = parsed.year;
  }

  if (map.size === 0) return [];

  // Fill empty quarters between min and max year so the X-axis is
  // continuous. Without this, a "gap quarter" with no releases would
  // be visually collapsed and the eye would underestimate dry spells.
  const out: BucketRow[] = [];
  for (let y = minYear; y <= maxYear; y++) {
    for (let q = 1 as Quarter; q <= 4; q = ((q + 1) as Quarter)) {
      const key = `${y}-Q${q}`;
      const row = map.get(key);
      if (row) out.push(row);
      else {
        out.push({
          key,
          year: y,
          quarter: q,
          byTier: [0, 0, 0, 0, 0],
          records: []
        });
      }
      if (q === 4) break;
    }
  }
  return out;
}

/** Tier colour palette — distinct hues, monotonic darkness for tier number.
 *  Tier 1 (battle-tested) → strongest colour; tier 5 (theoretical) → mutest. */
export const TIER_COLOURS: Record<Tier, string> = {
  1: '#3fb950', // green — production
  2: '#58a6ff', // blue — late-stage
  3: '#d29922', // amber — emerging
  4: '#bc8cff', // purple — research
  5: '#8b949e'  // grey — theoretical
};

export const TIER_LABELS: Record<Tier, string> = {
  1: 'Tier 1 · battle-tested',
  2: 'Tier 2 · late-stage',
  3: 'Tier 3 · emerging',
  4: 'Tier 4 · research',
  5: 'Tier 5 · theoretical'
};

export const TIERS: Tier[] = [1, 2, 3, 4, 5];
