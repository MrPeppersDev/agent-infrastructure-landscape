// Pure ranking function shared by the /recommend surfaces (issue #96).
//
// SINGLE SOURCE OF TRUTH: web/src/lib/analyses/recommender.ts.
// This file is a verbatim mirror — the mcp/ package ships as a
// standalone npm-installable surface, so a TypeScript rootDir-respecting
// copy lives here. The only intended divergence is the `types.ts`
// import path. Same pattern as `citation-prediction.ts`.
//
// See web/src/lib/analyses/recommender.ts for the full module
// docstring (anchor / constraint modes, provenance gate, determinism
// rules).

import type { LandscapeRecord } from './types.js';

// =========================================================================
// Public types
// =========================================================================

export interface ConstraintSet {
  /** OR-match against record's `use-case-tags`. */
  use_case_tags?: string[];
  /** Maximum acceptable per-Mtok input cost in USD. */
  cost_max_input_usd_per_mtok?: number;
  /** Maximum acceptable cost tier (cost rank ≤ this rank). */
  cost_tier_max?: CostTier;
  /** Minimum acceptable capability band (band rank ≥ this rank). */
  capability_band_min?: CapabilityBand;
}

export interface AnchorPair {
  /** Record id of the low-end positioning anchor. */
  low: string;
  /** Record id of the high-end positioning anchor. */
  high: string;
}

export interface Candidate {
  record: LandscapeRecord;
  /** Score in [0, 1]. Higher = better match. */
  score: number;
  /** One line per reason this row scored well. */
  rationale: string[];
  /** One line per warning — stale cells, LLM-unverified cells, anti-tags, etc. */
  caveats: string[];
}

export interface RankOptions {
  /** ISO date used as "today" for staleness math. Default `"2026-06-29"`. */
  today?: string;
  /** Days after which a `*-last-verified` cell triggers a staleness caveat. Default 30. */
  staleDays?: number;
}

// =========================================================================
// Constants
// =========================================================================

const DEFAULT_K = 5;
const DEFAULT_STALE_DAYS = 30;
const DEFAULT_TODAY = '2026-06-29';

const COST_TIER_ORDER = ['free', 'budget', 'mid', 'premium'] as const;
const CAPABILITY_BAND_ORDER = ['entry', 'competent', 'frontier'] as const;

export type CostTier = (typeof COST_TIER_ORDER)[number];
export type CapabilityBand = (typeof CAPABILITY_BAND_ORDER)[number];

// =========================================================================
// Cell readers
// =========================================================================

function isNotApplicable(value: string | undefined | null): boolean {
  if (!value) return true;
  return /^\s*(not\s+applicable|n\/a)\b/i.test(value);
}

function cellValue(record: LandscapeRecord, slug: string): string | null {
  const cells = record.cells as Record<string, { value?: string } | undefined>;
  const cell = cells[slug];
  if (!cell || typeof cell.value !== 'string') return null;
  if (isNotApplicable(cell.value)) return null;
  return cell.value;
}

function isLlmUnverified(record: LandscapeRecord, slug: string): boolean {
  const prov = record._provenance?.[slug];
  return !!prov && prov.source === 'llm' && prov.verified === false;
}

// =========================================================================
// Value parsers
// =========================================================================

function parseNumber(s: string | null): number | null {
  if (s == null) return null;
  const n = Number(s.trim());
  return isFinite(n) ? n : null;
}

function parseTags(s: string | null): string[] {
  if (s == null) return [];
  return s
    .split(',')
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
}

function parseTier(s: string | null): CostTier | null {
  if (s == null) return null;
  const v = s.trim().toLowerCase();
  return (COST_TIER_ORDER as readonly string[]).includes(v) ? (v as CostTier) : null;
}

function parseBand(s: string | null): CapabilityBand | null {
  if (s == null) return null;
  const v = s.trim().toLowerCase();
  return (CAPABILITY_BAND_ORDER as readonly string[]).includes(v) ? (v as CapabilityBand) : null;
}

function dateDiffDays(today: string, then: string): number {
  const tdy = Date.parse(today + 'T00:00:00Z');
  const thn = Date.parse(then + 'T00:00:00Z');
  if (!isFinite(tdy) || !isFinite(thn)) return NaN;
  return Math.floor((tdy - thn) / 86_400_000);
}

function clamp01(n: number): number {
  if (!isFinite(n)) return 0;
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

function cmpId(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

// =========================================================================
// Derived per-record cell snapshot
// =========================================================================

interface DerivedRow {
  record: LandscapeRecord;
  costUsd: number | null;
  costUsdLlm: boolean;
  costTier: CostTier | null;
  costTierLlm: boolean;
  capScore: number | null;
  capScoreLlm: boolean;
  capBand: CapabilityBand | null;
  capBandLlm: boolean;
  tags: string[];
  tagsLlm: boolean;
  antiTags: string[];
  antiTagsLlm: boolean;
  costLastVerified: string | null;
  capLastVerified: string | null;
}

function derive(record: LandscapeRecord): DerivedRow {
  return {
    record,
    costUsd: parseNumber(cellValue(record, 'cost-input-usd-per-mtok')),
    costUsdLlm: isLlmUnverified(record, 'cost-input-usd-per-mtok'),
    costTier: parseTier(cellValue(record, 'cost-tier')),
    costTierLlm: isLlmUnverified(record, 'cost-tier'),
    capScore: parseNumber(cellValue(record, 'capability-composite-score')),
    capScoreLlm: isLlmUnverified(record, 'capability-composite-score'),
    capBand: parseBand(cellValue(record, 'capability-band')),
    capBandLlm: isLlmUnverified(record, 'capability-band'),
    tags: parseTags(cellValue(record, 'use-case-tags')),
    tagsLlm: isLlmUnverified(record, 'use-case-tags'),
    antiTags: parseTags(cellValue(record, 'use-case-anti-tags')),
    antiTagsLlm: isLlmUnverified(record, 'use-case-anti-tags'),
    costLastVerified: cellValue(record, 'cost-last-verified'),
    capLastVerified: cellValue(record, 'capability-last-verified')
  };
}

// =========================================================================
// Anchor-mode range helpers
// =========================================================================

function numRange(a: number | null, b: number | null): [number, number] | null {
  if (a == null || b == null) return null;
  return a <= b ? [a, b] : [b, a];
}

function inRange(x: number, [lo, hi]: [number, number]): boolean {
  return x >= lo && x <= hi;
}

// =========================================================================
// Scoring
// =========================================================================

function scoreOne(
  d: DerivedRow,
  c: ConstraintSet,
  today: string,
  staleDays: number,
  anchorMode: boolean
): Candidate {
  const rationale: string[] = [];
  const caveats: string[] = [];

  let base = 0;
  let weight = 0;

  if (c.use_case_tags && c.use_case_tags.length > 0) {
    if (d.tagsLlm) {
      caveats.push('use-case-tags excluded from ranking — LLM-unverified');
    } else {
      const matched = c.use_case_tags.filter((t) => d.tags.includes(t));
      const contribution = matched.length / c.use_case_tags.length;
      base += contribution;
      weight += 1;
      if (matched.length > 0) {
        const plural = matched.length > 1 ? 's' : '';
        rationale.push(`matches use-case tag${plural}: ${matched.join(', ')}`);
      }
    }

    if (d.antiTagsLlm) {
      caveats.push('use-case-anti-tags excluded from ranking — LLM-unverified');
    } else if (d.antiTags.length > 0) {
      const antiHits = c.use_case_tags.filter((t) => d.antiTags.includes(t));
      if (antiHits.length > 0) {
        base -= 0.5 * antiHits.length;
        caveats.push(`anti-tag match: ${antiHits.join(', ')}`);
      }
    }
  }

  if (c.cost_max_input_usd_per_mtok != null) {
    if (d.costUsdLlm) {
      caveats.push('cost-input-usd-per-mtok excluded from ranking — LLM-unverified');
    } else if (d.costUsd != null) {
      if (d.costUsd <= c.cost_max_input_usd_per_mtok) {
        base += 1;
        rationale.push(
          `cost within budget ($${d.costUsd}/Mtok ≤ $${c.cost_max_input_usd_per_mtok}/Mtok)`
        );
      } else {
        caveats.push(
          `cost exceeds budget ($${d.costUsd}/Mtok > $${c.cost_max_input_usd_per_mtok}/Mtok)`
        );
      }
      weight += 1;
    }
  }

  if (c.cost_tier_max != null) {
    if (d.costTierLlm) {
      caveats.push('cost-tier excluded from ranking — LLM-unverified');
    } else if (d.costTier != null) {
      const recRank = COST_TIER_ORDER.indexOf(d.costTier);
      const maxRank = COST_TIER_ORDER.indexOf(c.cost_tier_max);
      if (recRank <= maxRank) {
        base += 1;
        rationale.push(`cost-tier ${d.costTier} ≤ ${c.cost_tier_max}`);
      } else {
        caveats.push(`cost-tier ${d.costTier} > requested ${c.cost_tier_max}`);
      }
      weight += 1;
    }
  }

  if (c.capability_band_min != null) {
    if (d.capBandLlm) {
      caveats.push('capability-band excluded from ranking — LLM-unverified');
    } else if (d.capBand != null) {
      const recRank = CAPABILITY_BAND_ORDER.indexOf(d.capBand);
      const minRank = CAPABILITY_BAND_ORDER.indexOf(c.capability_band_min);
      if (recRank >= minRank) {
        base += 1;
        rationale.push(`capability-band ${d.capBand} ≥ ${c.capability_band_min}`);
      } else {
        caveats.push(`capability-band ${d.capBand} < requested ${c.capability_band_min}`);
      }
      weight += 1;
    }
  }

  if (d.costLastVerified) {
    const age = dateDiffDays(today, d.costLastVerified);
    if (isFinite(age) && age > staleDays) {
      caveats.push(`cost data ${age}d stale (cost-last-verified ${d.costLastVerified})`);
    }
  }
  if (d.capLastVerified) {
    const age = dateDiffDays(today, d.capLastVerified);
    if (isFinite(age) && age > staleDays) {
      caveats.push(
        `capability data ${age}d stale (capability-last-verified ${d.capLastVerified})`
      );
    }
  }

  let scoreValue: number;
  if (weight === 0) {
    if (anchorMode && d.capScore != null && !d.capScoreLlm) {
      scoreValue = clamp01(d.capScore / 100);
    } else {
      scoreValue = anchorMode ? 0.5 : 0;
    }
  } else {
    scoreValue = clamp01(base / weight);
  }

  return {
    record: d.record,
    score: scoreValue,
    rationale,
    caveats
  };
}

// =========================================================================
// Public API
// =========================================================================

export function rankCandidates(
  records: LandscapeRecord[],
  constraints: ConstraintSet,
  anchors?: AnchorPair,
  k?: number,
  options?: RankOptions
): Candidate[] {
  const today = options?.today ?? DEFAULT_TODAY;
  const staleDays = options?.staleDays ?? DEFAULT_STALE_DAYS;
  const limit = Math.max(1, k ?? DEFAULT_K);

  const derived: DerivedRow[] = records.map(derive);

  let pool: DerivedRow[];
  if (anchors) {
    const low = derived.find((d) => d.record.id === anchors.low);
    const high = derived.find((d) => d.record.id === anchors.high);
    if (!low || !high) {
      return [];
    }
    const costRange = numRange(low.costUsd, high.costUsd);
    const capRange = numRange(low.capScore, high.capScore);
    pool = derived.filter((d) => {
      if (d.record.id === anchors.low || d.record.id === anchors.high) return false;
      if (costRange && d.costUsd != null && !inRange(d.costUsd, costRange)) return false;
      if (capRange && d.capScore != null && !inRange(d.capScore, capRange)) return false;
      if (d.costUsd == null && d.capScore == null) return false;
      if (!costRange && !capRange) return false;
      return true;
    });
  } else {
    pool = derived;
  }

  const candidates: Candidate[] = pool.map((d) =>
    scoreOne(d, constraints, today, staleDays, !!anchors)
  );

  candidates.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return cmpId(a.record.id, b.record.id);
  });

  return candidates.slice(0, limit);
}
