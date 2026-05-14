// Pure helpers for the cost-economics coverage matrix (issue #41, T1-3).
//
// Cost / token-economics is the #2 demand-signal question in agent
// infrastructure per the May 2026 volumetric agent: 171 HN mentions in
// the last 12 months, Sequoia's "if 60-70% of gross margins go to
// inference, you don't have a sustainable business" framing, Datadog
// 2026's finding that 69% of input tokens are system-prompt overhead.
// The practitioner question has shifted from "how expensive?" to "how
// do I govern spend?" — this helper pivots the seven `cost-*` cells in
// every record into a coverage matrix plus per-feature support stats.
//
// This is a pure pivot — no new ingestion, no network. Coverage is
// gated by what's been backfilled into the catalog (currently the
// top ~100 priority rows; the rest carry no-data placeholders that
// the view surfaces as "unknown").
//
// ---------------------------------------------------------------------------
// Cell-state semantics (mirrors SCHEMA.md §2.5.2)
// ---------------------------------------------------------------------------
//
// Each cost-* cell carries a {value, citation, status, tier}. We normalise
// to three states for display:
//
//   yes      — value === "yes" (case-insensitive). status === "real-data".
//   no       — value === "no"  (case-insensitive). status === "real-data".
//   unknown  — everything else: value === "", status in {no-data,
//              depth-floor-reached, not-applicable, estimate}.
//
// "unknown" deliberately collapses several distinct cell states:
//   1. "Researched and didn't find evidence" (depth-floor-reached)
//   2. "Cell hasn't been researched yet" (no-data)
//   3. "Column doesn't apply" (not-applicable — only research papers)
// The view's coverage callout reports the un-analyzed count separately
// so the reader sees the size of the gap explicitly.

import type { LandscapeRecord, ColumnSlug } from '../types';

export type CostState = 'yes' | 'no' | 'unknown';

/** The seven boolean cost-control columns. */
export const COST_FEATURES = [
  'token-budget',
  'prompt-caching',
  'semantic-caching',
  'batching',
  'model-routing',
  'streaming-only',
  'cost-attribution'
] as const;

export type CostFeature = (typeof COST_FEATURES)[number];

/** Human-readable label for each cost-control feature. */
export const FEATURE_LABEL: Record<CostFeature, string> = {
  'token-budget': 'Token budget',
  'prompt-caching': 'Prompt caching',
  'semantic-caching': 'Semantic caching',
  'batching': 'Batch API',
  'model-routing': 'Model routing',
  'streaming-only': 'Streaming-only',
  'cost-attribution': 'Cost attribution'
};

/**
 * Short tooltip / drill-down description for each cost-control feature.
 * These match the semantics in SCHEMA.md §2.5.2.
 */
export const FEATURE_DESCRIPTION: Record<CostFeature, string> = {
  'token-budget':
    'Per-call token-budget enforcement: framework enforces a max-tokens-per-request limit before sending.',
  'prompt-caching':
    'Anthropic-style prompt caching or equivalent (OpenAI Cached Input, Gemini caching, vendor cache_control blocks).',
  'semantic-caching':
    'Cache results by semantic similarity of the request (e.g. GPTCache, Helicone caching, LangChain SemanticCache).',
  batching:
    'Batch API support (e.g. OpenAI Batch API, Anthropic Message Batches) — async, discounted bulk requests.',
  'model-routing':
    'Dynamic model selection by complexity / cost (e.g. fall back to a cheaper model for simple queries; LLM routers).',
  'streaming-only':
    'Forces streaming responses so partial output can be aborted before the full bill lands.',
  'cost-attribution':
    'Tracks $ per request / per tool call / per user — distinct from generic observability by exposing dollar amounts.'
};

/**
 * Priority order for "primary feature" selection. When a product supports
 * multiple cost-control features, the first 'yes' from this list becomes
 * the displayed primary feature. The order reflects the practitioner's
 * mental hierarchy: token budget is the floor (you can't have governance
 * without a cap), prompt caching the highest-impact lever, then the rest.
 */
export const PRIORITY_ORDER: CostFeature[] = [
  'token-budget',
  'prompt-caching',
  'model-routing',
  'cost-attribution',
  'batching',
  'streaming-only',
  'semantic-caching'
];

/** Map a feature key to its column slug. */
export function costSlug(feature: CostFeature): ColumnSlug {
  if (feature === 'cost-attribution') {
    return 'cost-observability-cost-attribution' as ColumnSlug;
  }
  return `cost-${feature}` as ColumnSlug;
}

export interface CostGovernance {
  productId: string;
  productName: string;
  productUrl: string | null;
  section: string;
  tier: number;
  /** All seven cost-control features, keyed by feature name. */
  features: Record<CostFeature, CostState>;
  /** Citations per feature — null when status==no-data, otherwise the
   *  cell's citation URL (or null if the cell had none). */
  citations: Record<CostFeature, string | null>;
  /** Count of features with state === 'yes' (governance score out of 7). */
  governanceScore: number;
  /** Count of features with state === 'no' (explicit absence). */
  explicitNoCount: number;
  /** Count of features with state === 'unknown'. */
  unknownCount: number;
  /** First 'yes' feature from PRIORITY_ORDER, or null if none. */
  primaryFeature: CostFeature | null;
}

export interface FeatureStat {
  feature: CostFeature;
  label: string;
  /** Number of products with state === 'yes' for this feature. */
  supportedCount: number;
  /** As a percentage of `analyzedCount` (rows that have any cost-* cell
   *  with state in {yes, no} — i.e. excluding rows that are all unknown). */
  supportedPct: number;
}

export interface CostEconomicsMatrix {
  /** One entry per LandscapeRecord. */
  coverage: CostGovernance[];
  /** Per-feature support statistics. */
  featureStats: FeatureStat[];
  /** Total records considered (== records.length). */
  totalProducts: number;
  /** Records with at least one cost-* cell at state 'yes' or 'no'
   *  (i.e. coverage signal is meaningful for them). */
  analyzedCount: number;
  /** Records with at least one 'yes'. */
  withAnyFeatureCount: number;
  /** Records where every cost-* cell is 'unknown' (no signal at all). */
  uncoveredProducts: number;
}

// ---------------------------------------------------------------------------
// Cell → CostState normalisation
// ---------------------------------------------------------------------------

function normaliseCell(value: string, status: string): CostState {
  const v = value.trim().toLowerCase();
  if (status === 'real-data') {
    if (v === 'yes' || v.startsWith('yes')) return 'yes';
    if (v === 'no' || v.startsWith('no')) return 'no';
    // Free text that's neither yes nor no — conservative default: 'unknown'.
    return 'unknown';
  }
  // status === 'depth-floor-reached' | 'no-data' | 'not-applicable' | 'estimate'
  return 'unknown';
}

function primarySection(record: LandscapeRecord): string {
  for (const s of record.sections) {
    if (s.primary) return s.section;
  }
  return record.sections[0]?.section ?? 'Unknown';
}

// ---------------------------------------------------------------------------
// Builder
// ---------------------------------------------------------------------------

export function buildCostEconomics(
  records: LandscapeRecord[]
): CostEconomicsMatrix {
  const coverage: CostGovernance[] = [];
  const featureYesCounts: Record<CostFeature, number> = {
    'token-budget': 0,
    'prompt-caching': 0,
    'semantic-caching': 0,
    batching: 0,
    'model-routing': 0,
    'streaming-only': 0,
    'cost-attribution': 0
  };
  let analyzedCount = 0;
  let withAnyFeatureCount = 0;
  let uncoveredProducts = 0;

  for (const record of records) {
    const features: Record<CostFeature, CostState> = {} as Record<
      CostFeature,
      CostState
    >;
    const citations: Record<CostFeature, string | null> = {} as Record<
      CostFeature,
      string | null
    >;
    let governanceScore = 0;
    let explicitNoCount = 0;
    let unknownCount = 0;

    for (const feature of COST_FEATURES) {
      const cell = record.cells[costSlug(feature)];
      const state = cell ? normaliseCell(cell.value, cell.status) : 'unknown';
      features[feature] = state;
      citations[feature] = cell?.citation ?? null;
      if (state === 'yes') {
        governanceScore += 1;
        featureYesCounts[feature] += 1;
      } else if (state === 'no') {
        explicitNoCount += 1;
      } else {
        unknownCount += 1;
      }
    }

    // Primary feature from priority order.
    let primary: CostFeature | null = null;
    for (const feature of PRIORITY_ORDER) {
      if (features[feature] === 'yes') {
        primary = feature;
        break;
      }
    }

    // Analysis bookkeeping.
    const hasAnySignal = governanceScore > 0 || explicitNoCount > 0;
    if (hasAnySignal) analyzedCount += 1;
    if (governanceScore > 0) withAnyFeatureCount += 1;
    if (!hasAnySignal) uncoveredProducts += 1;

    coverage.push({
      productId: record.id,
      productName: record.name,
      productUrl: record.url,
      section: primarySection(record),
      tier: record.tier,
      features,
      citations,
      governanceScore,
      explicitNoCount,
      unknownCount,
      primaryFeature: primary
    });
  }

  // Per-feature stats computed against analyzedCount so the percentage
  // reflects "of the rows where signal is meaningful". Using records.length
  // as the denominator would punish features just because most rows haven't
  // been backfilled.
  const denom = Math.max(1, analyzedCount);
  const featureStats: FeatureStat[] = COST_FEATURES.map((feature) => ({
    feature,
    label: FEATURE_LABEL[feature],
    supportedCount: featureYesCounts[feature],
    supportedPct: Math.round((featureYesCounts[feature] / denom) * 1000) / 10
  }));

  return {
    coverage,
    featureStats,
    totalProducts: records.length,
    analyzedCount,
    withAnyFeatureCount,
    uncoveredProducts
  };
}

// ---------------------------------------------------------------------------
// Filter helpers
// ---------------------------------------------------------------------------

/** Return the set of unique primary-section names present in coverage. */
export function uniqueSections(matrix: CostEconomicsMatrix): string[] {
  const set = new Set<string>();
  for (const c of matrix.coverage) set.add(c.section);
  return Array.from(set).sort();
}

/** Sort comparator: by governanceScore desc, then by analyzedness, then
 *  alphabetically. Rows that have been researched rank above never-researched
 *  rows of equal coverage. */
export function compareByScore(
  a: CostGovernance,
  b: CostGovernance
): number {
  if (a.governanceScore !== b.governanceScore) {
    return b.governanceScore - a.governanceScore;
  }
  const aAnalyzed = a.governanceScore + a.explicitNoCount;
  const bAnalyzed = b.governanceScore + b.explicitNoCount;
  if (aAnalyzed !== bAnalyzed) return bAnalyzed - aAnalyzed;
  return a.productName.localeCompare(b.productName);
}

export function compareByName(
  a: CostGovernance,
  b: CostGovernance
): number {
  return a.productName.localeCompare(b.productName);
}

export function compareByTier(
  a: CostGovernance,
  b: CostGovernance
): number {
  if (a.tier !== b.tier) return a.tier - b.tier;
  return compareByScore(a, b);
}
