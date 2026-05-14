// Pure helpers for the observability-coverage matrix (issue #39, T1-1).
//
// Observability/debugging is the single highest-demand question in agent
// infrastructure per the May 2026 volumetric agent: 807 HN hits, 89%
// LangChain-survey adoption, 6/7 published surveys treat it as a top
// concern. This helper pivots the eight `obs-*` cells in every record
// into a coverage matrix plus per-tool support statistics.
//
// This is a pure pivot — no new ingestion, no network. Coverage is
// gated by what's been backfilled into the catalog (currently the
// top ~100 priority rows; the rest carry depth-floor placeholders
// that the view surfaces as "unknown").
//
// ---------------------------------------------------------------------------
// Cell-state semantics (mirrors SCHEMA.md §2.5.1)
// ---------------------------------------------------------------------------
//
// Each obs-* cell carries a {value, citation, status, tier}. We normalise
// to three states for display:
//
//   yes      — value === "yes" (case-insensitive). status === "real-data".
//   no       — value === "no"  (case-insensitive). status === "real-data".
//   unknown  — everything else: value === "", status in {no-data,
//              depth-floor-reached}, or status === "not-applicable".
//
// "unknown" deliberately collapses two distinct claims:
//   1. "Researched and didn't find evidence" (depth-floor-reached)
//   2. "Cell hasn't been researched yet" (no-data)
// The view's coverage callout reports both — the integration support
// is unknown either way from the reader's perspective.
//
// "Custom" (obs-custom) is free text and is rendered separately as a
// drill-down note, not as part of the yes/no/unknown grid.

import type { LandscapeRecord, ColumnSlug } from '../types';

export type ObsState = 'yes' | 'no' | 'unknown';

/** The seven boolean observability columns (excludes obs-custom). */
export const OBS_TOOLS = [
  'langsmith',
  'opentelemetry',
  'datadog',
  'helicone',
  'weave',
  'langfuse',
  'arize'
] as const;

export type ObsTool = (typeof OBS_TOOLS)[number];

/** Human-readable label for each tool. */
export const TOOL_LABEL: Record<ObsTool, string> = {
  langsmith: 'LangSmith',
  opentelemetry: 'OpenTelemetry',
  datadog: 'Datadog',
  helicone: 'Helicone',
  weave: 'Weave (W&B)',
  langfuse: 'Langfuse',
  arize: 'Arize'
};

/**
 * Priority order for "primary integration" selection. When a product
 * supports multiple tools, the first 'yes' from this list becomes the
 * displayed primary integration. The order roughly tracks 2026 mindshare
 * (LangSmith leads LangChain's ecosystem; OTel is the open standard;
 * Datadog dominates enterprise; Langfuse / Helicone / Weave / Arize are
 * the OSS / specialist crowd).
 */
export const PRIORITY_ORDER: ObsTool[] = [
  'langsmith',
  'opentelemetry',
  'datadog',
  'langfuse',
  'helicone',
  'weave',
  'arize'
];

export interface ObservabilityCoverage {
  productId: string;
  productName: string;
  productUrl: string | null;
  section: string;
  tier: number;
  /** All seven boolean integrations, keyed by tool. */
  integrations: Record<ObsTool, ObsState>;
  /** Citations per tool — null when status==no-data, otherwise the
   *  cell's citation URL (or null if the cell had none). */
  citations: Record<ObsTool, string | null>;
  /** Free-text from obs-custom, or null if empty. */
  customText: string | null;
  customCitation: string | null;
  /** Count of integrations with state === 'yes'. */
  coverageCount: number;
  /** Count of integrations with state === 'no' (explicit absence). */
  explicitNoCount: number;
  /** Count of integrations with state === 'unknown'. */
  unknownCount: number;
  /** First 'yes' tool from PRIORITY_ORDER, or null if none. */
  primaryIntegration: ObsTool | null;
}

export interface ToolStat {
  tool: ObsTool;
  label: string;
  /** Number of products with state === 'yes' for this tool. */
  supportedCount: number;
  /** As a percentage of `analyzedCount` (rows that have any obs-* cell
   *  with state in {yes, no} — i.e. excluding rows that are all unknown). */
  supportedPct: number;
}

export interface ObservabilityMatrix {
  /** One entry per LandscapeRecord. */
  coverage: ObservabilityCoverage[];
  /** Per-tool support statistics. */
  toolStats: ToolStat[];
  /** Total records considered (== records.length). */
  totalProducts: number;
  /** Records with at least one obs-* cell at state 'yes' or 'no'
   *  (i.e. coverage gap signal is meaningful for them). */
  analyzedCount: number;
  /** Records with at least one 'yes'. */
  withAnyIntegrationCount: number;
  /** Records where every obs-* cell is 'unknown' (no signal at all). */
  uncoveredProducts: number;
}

// ---------------------------------------------------------------------------
// Cell → ObsState normalisation
// ---------------------------------------------------------------------------

function normaliseCell(value: string, status: string): ObsState {
  const v = value.trim().toLowerCase();
  if (status === 'real-data') {
    if (v === 'yes' || v.startsWith('yes')) return 'yes';
    if (v === 'no' || v.startsWith('no')) return 'no';
    // Free text that's neither yes nor no — treat as 'yes' if it
    // mentions specific versions or details, otherwise 'unknown'.
    // Conservative default: 'unknown' so we don't fabricate signal.
    return 'unknown';
  }
  // status === 'depth-floor-reached' | 'no-data' | 'not-applicable' | 'estimate'
  return 'unknown';
}

function obsSlug(tool: ObsTool): ColumnSlug {
  return `obs-${tool}` as ColumnSlug;
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

export function buildObservabilityMatrix(
  records: LandscapeRecord[]
): ObservabilityMatrix {
  const coverage: ObservabilityCoverage[] = [];
  const toolYesCounts: Record<ObsTool, number> = {
    langsmith: 0,
    opentelemetry: 0,
    datadog: 0,
    helicone: 0,
    weave: 0,
    langfuse: 0,
    arize: 0
  };
  let analyzedCount = 0;
  let withAnyIntegrationCount = 0;
  let uncoveredProducts = 0;

  for (const record of records) {
    const integrations: Record<ObsTool, ObsState> = {} as Record<
      ObsTool,
      ObsState
    >;
    const citations: Record<ObsTool, string | null> = {} as Record<
      ObsTool,
      string | null
    >;
    let coverageCount = 0;
    let explicitNoCount = 0;
    let unknownCount = 0;

    for (const tool of OBS_TOOLS) {
      const cell = record.cells[obsSlug(tool)];
      const state = cell ? normaliseCell(cell.value, cell.status) : 'unknown';
      integrations[tool] = state;
      citations[tool] = cell?.citation ?? null;
      if (state === 'yes') {
        coverageCount += 1;
        toolYesCounts[tool] += 1;
      } else if (state === 'no') {
        explicitNoCount += 1;
      } else {
        unknownCount += 1;
      }
    }

    // Custom column.
    const customCell = record.cells['obs-custom' as ColumnSlug];
    const customText = customCell && customCell.status === 'real-data' && customCell.value.trim()
      ? customCell.value.trim()
      : null;
    const customCitation = customCell?.citation ?? null;

    // Primary integration from priority order.
    let primary: ObsTool | null = null;
    for (const tool of PRIORITY_ORDER) {
      if (integrations[tool] === 'yes') {
        primary = tool;
        break;
      }
    }

    // Analysis bookkeeping.
    const hasAnySignal = coverageCount > 0 || explicitNoCount > 0;
    if (hasAnySignal) analyzedCount += 1;
    if (coverageCount > 0) withAnyIntegrationCount += 1;
    if (!hasAnySignal) uncoveredProducts += 1;

    coverage.push({
      productId: record.id,
      productName: record.name,
      productUrl: record.url,
      section: primarySection(record),
      tier: record.tier,
      integrations,
      citations,
      customText,
      customCitation,
      coverageCount,
      explicitNoCount,
      unknownCount,
      primaryIntegration: primary
    });
  }

  // Per-tool stats are computed against analyzedCount (the population
  // where the signal is meaningful), not against records.length — that
  // would punish tools just because most rows haven't been backfilled.
  const denom = Math.max(1, analyzedCount);
  const toolStats: ToolStat[] = OBS_TOOLS.map((tool) => ({
    tool,
    label: TOOL_LABEL[tool],
    supportedCount: toolYesCounts[tool],
    supportedPct: Math.round((toolYesCounts[tool] / denom) * 1000) / 10
  }));

  return {
    coverage,
    toolStats,
    totalProducts: records.length,
    analyzedCount,
    withAnyIntegrationCount,
    uncoveredProducts
  };
}

// ---------------------------------------------------------------------------
// Filter helpers
// ---------------------------------------------------------------------------

/** Return the set of unique primary-section names present in coverage. */
export function uniqueSections(matrix: ObservabilityMatrix): string[] {
  const set = new Set<string>();
  for (const c of matrix.coverage) set.add(c.section);
  return Array.from(set).sort();
}

/** Sort comparator: by coverageCount desc, then by analyzedness, then
 *  alphabetically. Rows that have been researched (analyzedCount > 0)
 *  rank above never-researched rows of equal coverage. */
export function compareByCoverage(
  a: ObservabilityCoverage,
  b: ObservabilityCoverage
): number {
  if (a.coverageCount !== b.coverageCount) return b.coverageCount - a.coverageCount;
  const aAnalyzed = a.coverageCount + a.explicitNoCount;
  const bAnalyzed = b.coverageCount + b.explicitNoCount;
  if (aAnalyzed !== bAnalyzed) return bAnalyzed - aAnalyzed;
  return a.productName.localeCompare(b.productName);
}

export function compareByName(
  a: ObservabilityCoverage,
  b: ObservabilityCoverage
): number {
  return a.productName.localeCompare(b.productName);
}

export function compareByTier(
  a: ObservabilityCoverage,
  b: ObservabilityCoverage
): number {
  if (a.tier !== b.tier) return a.tier - b.tier;
  return compareByCoverage(a, b);
}
