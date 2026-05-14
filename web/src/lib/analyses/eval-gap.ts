// Pure helpers for the eval-gap analysis view (issue #40, T1-2).
//
// The eval gap is the next frontier after observability. LangChain's
// State of Agent Engineering 2025 survey found that 89% of practitioners
// have observability adopted but only 52% have evals — a structural
// 37-point gap. The Berkeley RDI MAP study corroborates: 74% rely
// primarily on human evaluation. Datadog 2026 listed "reliable evaluation
// loops" as a top recommendation. The catalog-level question "how do I
// know if my agent is actually getting better?" had no good answer
// before T1-2.
//
// This helper does TWO things that distinguish the eval-gap view from
// a generic eval-coverage matrix:
//
//   1. It reads BOTH observability data (from T1-1's obs-* columns) and
//      eval data (from T1-2's eval-* columns) so it can identify
//      "eval orphans" — products that have observability ≥1 but zero
//      evals. That's the structural failure mode the LangChain survey
//      identified, and surfacing it row-by-row is the view's distinctive
//      value.
//
//   2. It reports the catalog's observed obs-adoption % and eval-adoption %
//      side by side, so the reader can see whether the catalog matches or
//      diverges from the 89/52 industry headline.
//
// This is a pure pivot — no new ingestion, no network. Coverage is
// gated by what's been backfilled into the catalog (the same top ~100
// priority rows that T1-1 and T1-3 used; the rest carry no-data
// placeholders that the view surfaces as "unknown").
//
// ---------------------------------------------------------------------------
// Cell-state semantics (mirrors SCHEMA.md §2.5.3)
// ---------------------------------------------------------------------------
//
// Each eval-* cell carries a {value, citation, status, tier}. We normalise
// to three states for display:
//
//   yes      — value === "yes" (case-insensitive). status === "real-data".
//   no       — value === "no"  (case-insensitive). status === "real-data".
//   unknown  — everything else: value === "", status in {no-data,
//              depth-floor-reached, not-applicable, estimate}.
//
// "unknown" collapses three distinct cell states:
//   1. "Researched and didn't find evidence" (depth-floor-reached)
//   2. "Cell hasn't been researched yet" (no-data)
//   3. "Column doesn't apply" (not-applicable — research papers)
// The view's coverage callout reports the un-analyzed count separately
// so the reader sees the size of the gap explicitly.

import type { LandscapeRecord, ColumnSlug } from '../types';

export type EvalState = 'yes' | 'no' | 'unknown';

/** The seven boolean eval-tooling columns. */
export const EVAL_TOOLS = [
  'langsmith-evals',
  'braintrust',
  'weights-and-biases-agent',
  'helicone-evals',
  'custom-test-harness',
  'human-loop',
  'production-traffic-replay'
] as const;

export type EvalTool = (typeof EVAL_TOOLS)[number];

/** Human-readable label for each eval tool. */
export const TOOL_LABEL: Record<EvalTool, string> = {
  'langsmith-evals': 'LangSmith Evals',
  braintrust: 'Braintrust',
  'weights-and-biases-agent': 'W&B Agent Eval',
  'helicone-evals': 'Helicone Evals',
  'custom-test-harness': 'Custom test harness',
  'human-loop': 'Human-in-loop',
  'production-traffic-replay': 'Prod traffic replay'
};

/**
 * Short tooltip / drill-down description for each eval tool. Match
 * SCHEMA.md §2.5.3 semantics.
 */
export const TOOL_DESCRIPTION: Record<EvalTool, string> = {
  'langsmith-evals':
    "LangSmith Evals integration — LangChain ecosystem's eval framework (datasets, evaluators, regression detection).",
  braintrust:
    'Braintrust integration — independent eval platform (proxy, scoring, experiments).',
  'weights-and-biases-agent':
    "W&B Agent Eval / Weave integration — W&B's agentic evaluation suite.",
  'helicone-evals':
    "Helicone's eval features — request-level evaluations via OpenLLMetry custom evaluators.",
  'custom-test-harness':
    'Built-in test or eval harness — framework ships its own (e.g. DSPy Evaluate, LangGraph testing).',
  'human-loop':
    'Human-in-loop eval workflow — manual review queue, annotation UI, expert grading integrated.',
  'production-traffic-replay':
    'Capture-replay tooling — replay production traffic against new agent versions for eval.'
};

/**
 * Priority order for "primary tool" selection. When a product supports
 * multiple eval tools, the first 'yes' from this list becomes its
 * displayed primary integration. The order reflects LangChain
 * ecosystem dominance + the vendor-vs-internal split: LangSmith leads
 * because LangChain-ecosystem products inherit it; Braintrust and W&B
 * follow as the dominant independent platforms; Helicone fills the
 * proxy / OSS slot; then the framework-shipped + human + replay
 * categories.
 */
export const PRIORITY_ORDER: EvalTool[] = [
  'langsmith-evals',
  'braintrust',
  'weights-and-biases-agent',
  'helicone-evals',
  'custom-test-harness',
  'human-loop',
  'production-traffic-replay'
];

/** Map an eval-tool key to its column slug. */
export function evalSlug(tool: EvalTool): ColumnSlug {
  return `eval-${tool}` as ColumnSlug;
}

// ---------------------------------------------------------------------------
// Observability slugs (mirror obs-* family from T1-1)
// ---------------------------------------------------------------------------

/** The seven boolean observability columns (excluding free-text obs-custom). */
const OBS_TOOLS = [
  'langsmith',
  'opentelemetry',
  'datadog',
  'helicone',
  'weave',
  'langfuse',
  'arize'
] as const;
const OBS_CUSTOM: ColumnSlug = 'obs-custom' as ColumnSlug;

// ---------------------------------------------------------------------------
// Per-record coverage shape
// ---------------------------------------------------------------------------

export interface EvalCoverage {
  productId: string;
  productName: string;
  productUrl: string | null;
  section: string;
  tier: number;
  /** All seven eval tools as yes/no/unknown. */
  evalIntegrations: Record<EvalTool, EvalState>;
  /** Citations per eval tool — the cell's citation or null. */
  citations: Record<EvalTool, string | null>;
  /** Count of obs-* cells with state === 'yes' (0-8 incl. obs-custom). */
  observabilityCount: number;
  /** Count of eval-* cells with state === 'yes' (0-7). */
  evalCount: number;
  /** observabilityCount > 0. */
  hasObservability: boolean;
  /** evalCount > 0. */
  hasEval: boolean;
  /**
   * STRUCTURAL FAILURE MODE: product has observability ≥1 tool but
   * exactly zero eval tools. This is the row-level "eval orphan" the
   * LangChain State of Agent Engineering 2025 survey identified.
   */
  isEvalOrphan: boolean;
  /** observabilityCount − evalCount, useful for sorting. */
  gap: number;
  /** First 'yes' eval tool from PRIORITY_ORDER, or null. */
  primaryTool: EvalTool | null;
  /** Whether this record has at least one obs-* or eval-* cell with
   *  state ∈ {yes, no} — i.e. the row has been backfilled at all. */
  isAnalyzed: boolean;
}

export interface ToolStat {
  tool: EvalTool;
  label: string;
  supportedCount: number;
  supportedPct: number;
}

export interface EvalGapMatrix {
  /** One entry per LandscapeRecord. */
  coverage: EvalCoverage[];
  /** Per-eval-tool support statistics. */
  toolStats: ToolStat[];
  /** Total records considered (== records.length). */
  totalProducts: number;
  /** Records analyzed for obs *or* eval (any non-unknown signal).
   *  This is the denominator for adoption percentages. */
  totalAnalyzed: number;
  /** Catalog observability adoption % = analyzedAndHasObs / totalAnalyzed. */
  observabilityAdoptionPct: number;
  /** Catalog eval adoption % = analyzedAndHasEval / totalAnalyzed. */
  evalAdoptionPct: number;
  /** Count of products with hasObservability && !hasEval. */
  evalOrphanCount: number;
  /** Quick-reference list of every eval-orphan. */
  evalOrphanList: Array<{ id: string; name: string; section: string }>;
}

// ---------------------------------------------------------------------------
// Cell → state normalisation
// ---------------------------------------------------------------------------

function normaliseCell(value: string, status: string): EvalState {
  const v = value.trim().toLowerCase();
  if (status === 'real-data') {
    if (v === 'yes' || v.startsWith('yes')) return 'yes';
    if (v === 'no' || v.startsWith('no')) return 'no';
    // Free text other than yes/no — conservative: 'unknown'.
    return 'unknown';
  }
  return 'unknown';
}

function primarySection(record: LandscapeRecord): string {
  for (const s of record.sections) {
    if (s.primary) return s.section;
  }
  return record.sections[0]?.section ?? 'Unknown';
}

function obsSlug(tool: (typeof OBS_TOOLS)[number]): ColumnSlug {
  return `obs-${tool}` as ColumnSlug;
}

function countObservability(record: LandscapeRecord): number {
  let n = 0;
  for (const tool of OBS_TOOLS) {
    const cell = record.cells[obsSlug(tool)];
    if (cell && normaliseCell(cell.value, cell.status) === 'yes') n += 1;
  }
  // Custom observability is free-text; we treat any non-empty real-data
  // value as a +1 to the observability surface area.
  const customCell = record.cells[OBS_CUSTOM];
  if (
    customCell &&
    customCell.status === 'real-data' &&
    customCell.value.trim() !== ''
  ) {
    n += 1;
  }
  return n;
}

function hasAnyObsSignal(record: LandscapeRecord): boolean {
  for (const tool of OBS_TOOLS) {
    const cell = record.cells[obsSlug(tool)];
    const s = cell ? normaliseCell(cell.value, cell.status) : 'unknown';
    if (s === 'yes' || s === 'no') return true;
  }
  const customCell = record.cells[OBS_CUSTOM];
  if (customCell && customCell.status === 'real-data') return true;
  return false;
}

// ---------------------------------------------------------------------------
// Builder
// ---------------------------------------------------------------------------

export function buildEvalGap(records: LandscapeRecord[]): EvalGapMatrix {
  const coverage: EvalCoverage[] = [];
  const toolYesCounts: Record<EvalTool, number> = {
    'langsmith-evals': 0,
    braintrust: 0,
    'weights-and-biases-agent': 0,
    'helicone-evals': 0,
    'custom-test-harness': 0,
    'human-loop': 0,
    'production-traffic-replay': 0
  };

  let totalAnalyzed = 0;
  let analyzedAndHasObs = 0;
  let analyzedAndHasEval = 0;
  let evalOrphanCount = 0;
  const evalOrphanList: EvalGapMatrix['evalOrphanList'] = [];

  for (const record of records) {
    const evalIntegrations: Record<EvalTool, EvalState> = {} as Record<
      EvalTool,
      EvalState
    >;
    const citations: Record<EvalTool, string | null> = {} as Record<
      EvalTool,
      string | null
    >;
    let evalCount = 0;
    let evalSignal = false;

    for (const tool of EVAL_TOOLS) {
      const cell = record.cells[evalSlug(tool)];
      const state = cell ? normaliseCell(cell.value, cell.status) : 'unknown';
      evalIntegrations[tool] = state;
      citations[tool] = cell?.citation ?? null;
      if (state === 'yes') {
        evalCount += 1;
        toolYesCounts[tool] += 1;
      }
      if (state === 'yes' || state === 'no') evalSignal = true;
    }

    const observabilityCount = countObservability(record);
    const hasObservability = observabilityCount > 0;
    const hasEval = evalCount > 0;

    const obsSignal = hasAnyObsSignal(record);
    const isAnalyzed = obsSignal || evalSignal;

    // Eval-orphan: must have obs ≥1 AND eval = 0 AND must be analyzed
    // for eval (so we know the absence is researched, not just unknown).
    const isEvalOrphan = hasObservability && !hasEval && evalSignal;

    let primary: EvalTool | null = null;
    for (const tool of PRIORITY_ORDER) {
      if (evalIntegrations[tool] === 'yes') {
        primary = tool;
        break;
      }
    }

    if (isAnalyzed) {
      totalAnalyzed += 1;
      if (hasObservability) analyzedAndHasObs += 1;
      if (hasEval) analyzedAndHasEval += 1;
    }
    if (isEvalOrphan) {
      evalOrphanCount += 1;
      evalOrphanList.push({
        id: record.id,
        name: record.name,
        section: primarySection(record)
      });
    }

    coverage.push({
      productId: record.id,
      productName: record.name,
      productUrl: record.url,
      section: primarySection(record),
      tier: record.tier,
      evalIntegrations,
      citations,
      observabilityCount,
      evalCount,
      hasObservability,
      hasEval,
      isEvalOrphan,
      gap: observabilityCount - evalCount,
      primaryTool: primary,
      isAnalyzed
    });
  }

  const obsPct =
    totalAnalyzed > 0
      ? Math.round((analyzedAndHasObs / totalAnalyzed) * 1000) / 10
      : 0;
  const evalPct =
    totalAnalyzed > 0
      ? Math.round((analyzedAndHasEval / totalAnalyzed) * 1000) / 10
      : 0;

  const denom = Math.max(1, totalAnalyzed);
  const toolStats: ToolStat[] = EVAL_TOOLS.map((tool) => ({
    tool,
    label: TOOL_LABEL[tool],
    supportedCount: toolYesCounts[tool],
    supportedPct: Math.round((toolYesCounts[tool] / denom) * 1000) / 10
  }));

  // Sort orphan list alphabetically for stable display.
  evalOrphanList.sort((a, b) => a.name.localeCompare(b.name));

  return {
    coverage,
    toolStats,
    totalProducts: records.length,
    totalAnalyzed,
    observabilityAdoptionPct: obsPct,
    evalAdoptionPct: evalPct,
    evalOrphanCount,
    evalOrphanList
  };
}

// ---------------------------------------------------------------------------
// Filter helpers
// ---------------------------------------------------------------------------

/** Unique primary-section names present in the coverage. */
export function uniqueSections(matrix: EvalGapMatrix): string[] {
  const set = new Set<string>();
  for (const c of matrix.coverage) set.add(c.section);
  return Array.from(set).sort();
}

/** Sort by gap (obs − eval) descending — primary view sort.
 *  Bigger gap = more obs without eval = more "orphan-leaning". */
export function compareByGap(a: EvalCoverage, b: EvalCoverage): number {
  if (a.gap !== b.gap) return b.gap - a.gap;
  // Tiebreak: more obs wins so the leaders are obvious.
  if (a.observabilityCount !== b.observabilityCount) {
    return b.observabilityCount - a.observabilityCount;
  }
  return a.productName.localeCompare(b.productName);
}

/** Sort by eval count desc (then by obs count desc, then alpha). */
export function compareByEvalCount(
  a: EvalCoverage,
  b: EvalCoverage
): number {
  if (a.evalCount !== b.evalCount) return b.evalCount - a.evalCount;
  if (a.observabilityCount !== b.observabilityCount) {
    return b.observabilityCount - a.observabilityCount;
  }
  return a.productName.localeCompare(b.productName);
}

/** Sort alphabetically by product name. */
export function compareByName(a: EvalCoverage, b: EvalCoverage): number {
  return a.productName.localeCompare(b.productName);
}

/** Sort by tier first, then by gap. */
export function compareByTier(a: EvalCoverage, b: EvalCoverage): number {
  if (a.tier !== b.tier) return a.tier - b.tier;
  return compareByGap(a, b);
}
