// Pure query functions over the AI agent infrastructure landscape.
//
// These are the canonical query helpers for the MCP server (and the CLI
// in #49 which imports from this same module). Every function is pure:
// records + edges + args → result. No I/O, no caching, no side effects.
// The server / CLI layer is responsible for loading the data and
// passing it through.
//
// Why duplicate vs. import from web/src/lib/analyses/? Two reasons:
//   1. The MCP surface area is narrower (9 read-only tools); the
//      analyses/ helpers carry view-specific shape (sorting, display
//      labels) the MCP doesn't need.
//   2. mcp/ ships as a standalone npm package — importing from web/
//      would pull SvelteKit-adjacent types into the published bundle.
// Where logic overlaps (eval-orphan detection, observability counting)
// we mirror the same cell-state semantics so results stay consistent.

import type {
  LandscapeRecord,
  Edge,
  EdgeType,
  ColumnSlug,
  Cell,
  Cells
} from './types.js';

// ===========================================================================
// Public result types
// ===========================================================================

/**
 * Compact record shape returned by list/search tools. Full record is
 * available via `get_record` — this trim is to keep tool responses
 * within MCP message size limits when a result set has many rows.
 */
export interface RecordSummary {
  id: string;
  name: string;
  tier: number;
  url: string | null;
  primarySection: string;
  primarySubsection: string | null;
  /** Short description from the `desc` cell, truncated to 200 chars. */
  description: string;
  /**
   * Row-level ISO date ("YYYY-MM-DD") of the most recent verification
   * of this record's claims. See docs/SCHEMA.md §3b. Issue #54.
   */
  lastVerifiedAt: string;
}

export interface SearchResult {
  query: string;
  totalMatches: number;
  /** Capped at the requested limit (default 25). */
  results: RecordSummary[];
}

export interface RelatedRecord {
  edge: Edge;
  /** The record on the OTHER end of the edge from the requested id. */
  related: RecordSummary;
  /** 'outgoing' = id is source; 'incoming' = id is target. */
  direction: 'outgoing' | 'incoming';
}

export interface RelatedResult {
  id: string;
  name: string;
  totalEdges: number;
  edgeTypes: Record<string, number>;
  edges: RelatedRecord[];
}

export interface CoverageEntry {
  /** Tool / feature slug (e.g. "langsmith", "token-budget"). */
  feature: string;
  /** Human-readable label. */
  label: string;
  /** Records with state === 'yes'. */
  yesCount: number;
  /** Records with state === 'no'. */
  noCount: number;
  /** Records with state === 'unknown' or unresearched. */
  unknownCount: number;
  /** Percentage of analyzed records (yes + no) where the answer is yes. */
  supportedPct: number;
}

export interface CoverageResult {
  dimension: 'observability' | 'cost' | 'eval' | 'benchmark';
  totalRecords: number;
  analyzedCount: number;
  features: CoverageEntry[];
}

export interface CellComparison {
  column: ColumnSlug;
  a: Cell | null;
  b: Cell | null;
  /** True if both cells exist and have identical values. */
  match: boolean;
}

export interface CompareResult {
  a: RecordSummary;
  b: RecordSummary;
  cells: CellComparison[];
  /** Edges directly between a and b (in either direction). */
  directEdges: Edge[];
}

export interface RecentChange {
  id: string;
  name: string;
  /** Date string extracted from the `latest-release` cell, or null. */
  latestRelease: string | null;
  /** Date string from `created` cell, or null. */
  created: string | null;
  primarySection: string;
  /**
   * Row-level ISO date ("YYYY-MM-DD") of the most recent catalog
   * verification — distinct from latestRelease/created which describe
   * upstream product activity. See docs/SCHEMA.md §3b. Issue #54.
   */
  lastVerifiedAt: string;
}

export interface RecentResult {
  since: string | null;
  totalMatches: number;
  records: RecentChange[];
}

export interface SubstrateResult {
  substrate: string;
  /** Resolved record for the substrate, or null if input didn't match. */
  substrateRecord: RecordSummary | null;
  totalDependents: number;
  dependents: RecordSummary[];
}

// ===========================================================================
// Cell-state semantics — must mirror web/src/lib/analyses/observability.ts
// ===========================================================================

type BoolState = 'yes' | 'no' | 'unknown';

function normaliseCell(cell: Cell | undefined): BoolState {
  if (!cell) return 'unknown';
  if (cell.status !== 'real-data') return 'unknown';
  const v = cell.value.trim().toLowerCase();
  if (v === 'yes' || v.startsWith('yes')) return 'yes';
  if (v === 'no' || v.startsWith('no')) return 'no';
  return 'unknown';
}

function primarySection(record: LandscapeRecord): string {
  for (const s of record.sections) {
    if (s.primary) return s.section;
  }
  return record.sections[0]?.section ?? 'Unknown';
}

function primarySubsection(record: LandscapeRecord): string | null {
  for (const s of record.sections) {
    if (s.primary) return s.subsection;
  }
  return record.sections[0]?.subsection ?? null;
}

function toSummary(record: LandscapeRecord): RecordSummary {
  const descCell = record.cells['desc' as ColumnSlug];
  const desc = descCell?.value ?? '';
  return {
    id: record.id,
    name: record.name,
    tier: record.tier,
    url: record.url,
    primarySection: primarySection(record),
    primarySubsection: primarySubsection(record),
    description: desc.length > 200 ? desc.slice(0, 197) + '...' : desc,
    lastVerifiedAt: record.last_verified_at
  };
}

// ===========================================================================
// 1. searchRecords
// ===========================================================================

export interface SearchArgs {
  /** Free-text query — matches against id, name, desc, claims (case-insensitive). */
  query: string;
  /** Filter to records whose primary section equals this. */
  section?: string;
  /** Filter to records of this tier (1-5). */
  tier?: number;
  /** Cap result count. Default 25, max 200. */
  limit?: number;
}

/**
 * Free-text search over records. Matches against id, name, desc cell,
 * and claims cell. Case-insensitive substring match — no fuzzy logic
 * (caller can rely on substring semantics to compose queries).
 *
 * Why these four fields? They cover both the slug-style lookup (id),
 * the human-name lookup (name), the marketing/desc lookup (desc), and
 * the technical-claim lookup (claims) without needing to scan all 68
 * columns. For column-specific search, use `get_record` after a hit.
 */
export function searchRecords(
  records: LandscapeRecord[],
  args: SearchArgs
): SearchResult {
  const q = args.query.trim().toLowerCase();
  if (!q) {
    return { query: args.query, totalMatches: 0, results: [] };
  }
  const limit = Math.min(Math.max(args.limit ?? 25, 1), 200);

  const matches: LandscapeRecord[] = [];
  for (const record of records) {
    if (args.tier !== undefined && record.tier !== args.tier) continue;
    if (args.section !== undefined && primarySection(record) !== args.section)
      continue;

    const haystack = [
      record.id,
      record.name,
      record.cells['desc' as ColumnSlug]?.value ?? '',
      record.cells['claims' as ColumnSlug]?.value ?? ''
    ]
      .join(' ')
      .toLowerCase();

    if (haystack.includes(q)) matches.push(record);
  }

  return {
    query: args.query,
    totalMatches: matches.length,
    results: matches.slice(0, limit).map(toSummary)
  };
}

// ===========================================================================
// 2. getRecord
// ===========================================================================

export interface GetRecordArgs {
  id: string;
}

/**
 * Returns the full record (all 85 cells + taxonomy + sections) by
 * stable id. Returns null if the id isn't in the catalog.
 */
export function getRecord(
  records: LandscapeRecord[],
  args: GetRecordArgs
): LandscapeRecord | null {
  return records.find((r) => r.id === args.id) ?? null;
}

// ===========================================================================
// 3. findRelated
// ===========================================================================

export interface FindRelatedArgs {
  id: string;
  /** Restrict to a specific edge type. Omit for all types. */
  edge_type?: EdgeType;
}

/**
 * Returns every edge touching the given record id, plus a summary of
 * the record on the other end. Includes both outgoing edges
 * (source === id) and incoming edges (target === id).
 */
export function findRelated(
  records: LandscapeRecord[],
  edges: Edge[],
  args: FindRelatedArgs
): RelatedResult {
  const recordById = new Map(records.map((r) => [r.id, r]));
  const self = recordById.get(args.id);
  const selfName = self?.name ?? args.id;

  const collected: RelatedRecord[] = [];
  const edgeTypes: Record<string, number> = {};

  for (const edge of edges) {
    if (args.edge_type && edge.type !== args.edge_type) continue;

    let direction: 'outgoing' | 'incoming' | null = null;
    let otherId: string | null = null;
    if (edge.source === args.id) {
      direction = 'outgoing';
      otherId = edge.target;
    } else if (edge.target === args.id) {
      direction = 'incoming';
      otherId = edge.source;
    }
    if (!direction || !otherId) continue;

    const other = recordById.get(otherId);
    if (!other) continue; // Edge points to a non-existent record (shouldn't happen post-validate)

    edgeTypes[edge.type] = (edgeTypes[edge.type] ?? 0) + 1;
    collected.push({
      edge,
      related: toSummary(other),
      direction
    });
  }

  return {
    id: args.id,
    name: selfName,
    totalEdges: collected.length,
    edgeTypes,
    edges: collected
  };
}

// ===========================================================================
// 4. coverageSummary
// ===========================================================================

const OBS_TOOLS: Array<[ColumnSlug, string]> = [
  ['obs-langsmith' as ColumnSlug, 'LangSmith'],
  ['obs-opentelemetry' as ColumnSlug, 'OpenTelemetry'],
  ['obs-datadog' as ColumnSlug, 'Datadog'],
  ['obs-helicone' as ColumnSlug, 'Helicone'],
  ['obs-weave' as ColumnSlug, 'Weave (W&B)'],
  ['obs-langfuse' as ColumnSlug, 'Langfuse'],
  ['obs-arize' as ColumnSlug, 'Arize']
];

const COST_FEATURES: Array<[ColumnSlug, string]> = [
  ['cost-token-budget' as ColumnSlug, 'Token budget'],
  ['cost-prompt-caching' as ColumnSlug, 'Prompt caching'],
  ['cost-semantic-caching' as ColumnSlug, 'Semantic caching'],
  ['cost-batching' as ColumnSlug, 'Batch API'],
  ['cost-model-routing' as ColumnSlug, 'Model routing'],
  ['cost-streaming-only' as ColumnSlug, 'Streaming-only'],
  ['cost-observability-cost-attribution' as ColumnSlug, 'Cost attribution']
];

const EVAL_TOOLS: Array<[ColumnSlug, string]> = [
  ['eval-langsmith-evals' as ColumnSlug, 'LangSmith Evals'],
  ['eval-braintrust' as ColumnSlug, 'Braintrust'],
  ['eval-weights-and-biases-agent' as ColumnSlug, 'W&B Agent Eval'],
  ['eval-helicone-evals' as ColumnSlug, 'Helicone Evals'],
  ['eval-custom-test-harness' as ColumnSlug, 'Custom test harness'],
  ['eval-human-loop' as ColumnSlug, 'Human-in-loop'],
  ['eval-production-traffic-replay' as ColumnSlug, 'Prod traffic replay']
];

// "Benchmark" coverage piggybacks on the `vendor-benchmarks` cell + records
// in the dedicated benchmark sections. We expose per-section counts here.
const BENCHMARK_SECTIONS = [
  'Memory benchmarks & evaluation',
  'Evaluation & observability platforms'
];

export interface CoverageArgs {
  dimension: 'observability' | 'cost' | 'eval' | 'benchmark';
}

/**
 * Per-feature counts for one of the four boolean-cell families
 * (observability, cost-control, eval-tooling) or per-section benchmark
 * counts. "Analyzed" rows are those with at least one yes/no cell in
 * the family — the percentage denominator. Rows with all-unknown cells
 * are excluded from the percentage so a low backfill rate doesn't
 * artificially deflate every feature.
 */
export function coverageSummary(
  records: LandscapeRecord[],
  args: CoverageArgs
): CoverageResult {
  let columns: Array<[ColumnSlug, string]>;
  switch (args.dimension) {
    case 'observability':
      columns = OBS_TOOLS;
      break;
    case 'cost':
      columns = COST_FEATURES;
      break;
    case 'eval':
      columns = EVAL_TOOLS;
      break;
    case 'benchmark':
      // Special-case: benchmark coverage is by section membership,
      // not by boolean cell. Returns one entry per benchmark-bearing
      // section with `yesCount` = # records primary in that section.
      return benchmarkCoverage(records);
    default:
      // TS exhaustiveness guard
      throw new Error(`Unknown dimension: ${args.dimension}`);
  }

  // Count yes/no/unknown per feature; track analyzed-set per record.
  const features: CoverageEntry[] = [];
  let analyzedCount = 0;

  // First pass: find the analyzed set (any yes/no across any feature).
  for (const record of records) {
    let hasSignal = false;
    for (const [slug] of columns) {
      const state = normaliseCell(record.cells[slug]);
      if (state === 'yes' || state === 'no') {
        hasSignal = true;
        break;
      }
    }
    if (hasSignal) analyzedCount += 1;
  }

  // Second pass: per-feature counts.
  for (const [slug, label] of columns) {
    let yes = 0;
    let no = 0;
    let unknown = 0;
    for (const record of records) {
      const state = normaliseCell(record.cells[slug]);
      if (state === 'yes') yes += 1;
      else if (state === 'no') no += 1;
      else unknown += 1;
    }
    const denom = Math.max(1, analyzedCount);
    features.push({
      feature: slug.replace(/^(obs|cost|eval)-/, ''),
      label,
      yesCount: yes,
      noCount: no,
      unknownCount: unknown,
      supportedPct: Math.round((yes / denom) * 1000) / 10
    });
  }

  return {
    dimension: args.dimension,
    totalRecords: records.length,
    analyzedCount,
    features
  };
}

function benchmarkCoverage(records: LandscapeRecord[]): CoverageResult {
  const features: CoverageEntry[] = [];
  let analyzedCount = 0;
  for (const section of BENCHMARK_SECTIONS) {
    const count = records.filter((r) => primarySection(r) === section).length;
    analyzedCount += count;
    features.push({
      feature: section.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      label: section,
      yesCount: count,
      noCount: 0,
      unknownCount: 0,
      supportedPct: count > 0 ? 100 : 0
    });
  }
  return {
    dimension: 'benchmark',
    totalRecords: records.length,
    analyzedCount,
    features
  };
}

// ===========================================================================
// 5. compare
// ===========================================================================

export interface CompareArgs {
  id_a: string;
  id_b: string;
}

/**
 * Side-by-side comparison of two records across every column slug. The
 * client (LLM or human) can decide what to surface — match-only,
 * diff-only, single-column drill-down — from the full cell pairs.
 */
export function compare(
  records: LandscapeRecord[],
  args: CompareArgs
): CompareResult {
  const a = records.find((r) => r.id === args.id_a);
  const b = records.find((r) => r.id === args.id_b);
  if (!a) throw new Error(`Record not found: ${args.id_a}`);
  if (!b) throw new Error(`Record not found: ${args.id_b}`);

  const slugs = new Set<ColumnSlug>([
    ...(Object.keys(a.cells) as ColumnSlug[]),
    ...(Object.keys(b.cells) as ColumnSlug[])
  ]);

  const cells: CellComparison[] = [];
  for (const slug of slugs) {
    const cellA = a.cells[slug] ?? null;
    const cellB = b.cells[slug] ?? null;
    const match =
      !!cellA &&
      !!cellB &&
      cellA.value.trim() === cellB.value.trim() &&
      cellA.value.trim() !== '';
    cells.push({ column: slug, a: cellA, b: cellB, match });
  }
  // Stable order for diffability.
  cells.sort((x, y) => x.column.localeCompare(y.column));

  return {
    a: toSummary(a),
    b: toSummary(b),
    cells,
    directEdges: []
  };
}

/** Decorate compare result with edges between the two records. */
export function compareWithEdges(
  records: LandscapeRecord[],
  edges: Edge[],
  args: CompareArgs
): CompareResult {
  const result = compare(records, args);
  result.directEdges = edges.filter(
    (e) =>
      (e.source === args.id_a && e.target === args.id_b) ||
      (e.source === args.id_b && e.target === args.id_a)
  );
  return result;
}

// ===========================================================================
// 6. listSections
// ===========================================================================

/** Distinct primary-section names in the catalog, alphabetised. */
export function listSections(records: LandscapeRecord[]): string[] {
  const set = new Set<string>();
  for (const r of records) set.add(primarySection(r));
  return Array.from(set).sort();
}

// ===========================================================================
// 7. recentChanges
// ===========================================================================

export interface RecentChangesArgs {
  /** ISO date string (YYYY-MM-DD or full ISO). Records with latest-release
   *  on or after this date are returned. Omit to return the 20 most-recent
   *  by latest-release date. */
  since?: string;
}

/**
 * Records updated since a date. Reads from the `latest-release` cell
 * (the canonical "last shipping" signal). Falls back to `created` for
 * records without a release date. The git-log path the issue mentions
 * was considered but rejected: it answers "when was the catalog
 * updated" not "when did the upstream product ship" — the latter is
 * what an MCP client cares about.
 *
 * Date extraction is heuristic: scans for YYYY or YYYY-MM-DD in the
 * cell value. Catalog rows often carry prose like "v0.4.2 — 2025-03-14".
 */
export function recentChanges(
  records: LandscapeRecord[],
  args: RecentChangesArgs
): RecentResult {
  const since = args.since ? parseDate(args.since) : null;

  const decorated = records.map((r) => {
    const latest = extractDate(r.cells['latest-release' as ColumnSlug]?.value);
    const created = extractDate(r.cells['created' as ColumnSlug]?.value);
    return { record: r, latest, created };
  });

  let filtered: typeof decorated;
  if (since) {
    filtered = decorated.filter((d) => {
      const target = d.latest ?? d.created;
      return target !== null && target >= since;
    });
  } else {
    filtered = decorated.filter((d) => d.latest !== null || d.created !== null);
  }

  // Sort by latest-release desc, falling back to created.
  filtered.sort((a, b) => {
    const aDate = a.latest ?? a.created ?? 0;
    const bDate = b.latest ?? b.created ?? 0;
    return bDate - aDate;
  });

  const limit = since ? filtered.length : Math.min(filtered.length, 20);

  return {
    since: args.since ?? null,
    totalMatches: filtered.length,
    records: filtered.slice(0, limit).map(({ record, latest, created }) => ({
      id: record.id,
      name: record.name,
      latestRelease: latest ? new Date(latest).toISOString().slice(0, 10) : null,
      created: created ? new Date(created).toISOString().slice(0, 10) : null,
      primarySection: primarySection(record),
      lastVerifiedAt: record.last_verified_at
    }))
  };
}

function parseDate(s: string): number | null {
  // Accept YYYY, YYYY-MM, YYYY-MM-DD, full ISO.
  const trimmed = s.trim();
  if (!trimmed) return null;
  // Plain year → midnight Jan 1 UTC.
  if (/^\d{4}$/.test(trimmed)) return Date.UTC(parseInt(trimmed, 10), 0, 1);
  const d = new Date(trimmed);
  return Number.isNaN(d.getTime()) ? null : d.getTime();
}

function extractDate(s: string | undefined): number | null {
  if (!s) return null;
  // YYYY-MM-DD first, then YYYY-MM, then bare YYYY.
  const ymd = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (ymd) return Date.UTC(+ymd[1], +ymd[2] - 1, +ymd[3]);
  const ym = s.match(/(\d{4})-(\d{2})/);
  if (ym) return Date.UTC(+ym[1], +ym[2] - 1, 1);
  const y = s.match(/\b(20\d{2})\b/);
  if (y) return Date.UTC(+y[1], 0, 1);
  return null;
}

// ===========================================================================
// 8. findEvalOrphans
// ===========================================================================

/**
 * Eval orphans: products with at least one observability tool integrated
 * (obs-* === yes) but ZERO eval tools (eval-* === yes) AND at least one
 * eval cell with a real-data signal (so we know the absence is
 * researched, not just unfilled).
 *
 * This is the row-level "structural failure mode" the LangChain State
 * of Agent Engineering 2025 survey identified — 89% have obs, 52% have
 * evals, leaving a 37-point gap.
 *
 * Mirrors web/src/lib/analyses/eval-gap.ts to keep results consistent
 * across the web view and the MCP tool.
 */
export function findEvalOrphans(records: LandscapeRecord[]): RecordSummary[] {
  const orphans: RecordSummary[] = [];
  for (const r of records) {
    let hasObs = false;
    let hasEval = false;
    let evalSignal = false;

    for (const [slug] of OBS_TOOLS) {
      if (normaliseCell(r.cells[slug]) === 'yes') {
        hasObs = true;
        break;
      }
    }
    // Custom observability free-text counts too.
    const customObs = r.cells['obs-custom' as ColumnSlug];
    if (
      customObs &&
      customObs.status === 'real-data' &&
      customObs.value.trim() !== ''
    ) {
      hasObs = true;
    }

    for (const [slug] of EVAL_TOOLS) {
      const state = normaliseCell(r.cells[slug]);
      if (state === 'yes') hasEval = true;
      if (state === 'yes' || state === 'no') evalSignal = true;
    }

    if (hasObs && !hasEval && evalSignal) {
      orphans.push(toSummary(r));
    }
  }
  // Stable: alphabetical by name.
  orphans.sort((a, b) => a.name.localeCompare(b.name));
  return orphans;
}

// ===========================================================================
// 9. findSubstrateRisk
// ===========================================================================

export interface SubstrateRiskArgs {
  /** Substrate name or id — e.g. "OpenAI", "Anthropic", "openai-gpt-family-gpt-5-gpt-4o-o3-o4--openai-com". */
  substrate: string;
}

/**
 * Records that runtime-depend on a given substrate. Uses the
 * runtime-dependency edges from T2-1. Useful for blast-radius questions
 * ("how many products break if OpenAI changes pricing?") and lock-in
 * analysis ("which framework is most-/least-coupled to a single LLM
 * provider?").
 *
 * Resolution: tries id match first, then case-insensitive substring
 * match on record names. If multiple substrates match (e.g. "Anthropic"
 * could match the foundation models AND Claude Memory), picks the one
 * with the most incoming runtime-dependency edges.
 */
export function findSubstrateRisk(
  records: LandscapeRecord[],
  edges: Edge[],
  args: SubstrateRiskArgs
): SubstrateResult {
  const query = args.substrate.trim();
  const lower = query.toLowerCase();

  // Resolve substrate id.
  let target: LandscapeRecord | null = records.find((r) => r.id === query) ?? null;
  if (!target) {
    // Pick the matching record with the most incoming runtime-deps.
    const candidates = records.filter(
      (r) =>
        r.id.toLowerCase().includes(lower) ||
        r.name.toLowerCase().includes(lower)
    );
    if (candidates.length > 0) {
      const depCounts = new Map<string, number>();
      for (const e of edges) {
        if (e.type === 'runtime-dependency') {
          depCounts.set(e.target, (depCounts.get(e.target) ?? 0) + 1);
        }
      }
      candidates.sort(
        (a, b) => (depCounts.get(b.id) ?? 0) - (depCounts.get(a.id) ?? 0)
      );
      target = candidates[0];
    }
  }

  if (!target) {
    return {
      substrate: args.substrate,
      substrateRecord: null,
      totalDependents: 0,
      dependents: []
    };
  }

  const targetId = target.id;
  const recordById = new Map(records.map((r) => [r.id, r]));

  const dependents: RecordSummary[] = [];
  const seen = new Set<string>();
  for (const e of edges) {
    if (e.type !== 'runtime-dependency') continue;
    if (e.target !== targetId) continue;
    if (seen.has(e.source)) continue;
    seen.add(e.source);
    const src = recordById.get(e.source);
    if (src) dependents.push(toSummary(src));
  }
  dependents.sort((a, b) => a.name.localeCompare(b.name));

  return {
    substrate: args.substrate,
    substrateRecord: toSummary(target),
    totalDependents: dependents.length,
    dependents
  };
}

// ===========================================================================
// 10. findByDecayCause
// ===========================================================================

export type DecayCause =
  | 'acquired'
  | 'pivoted'
  | 'unfunded'
  | 'lost-benchmark-race'
  | 'superseded'
  | 'archived'
  | 'research-complete'
  | 'unknown';

export interface DecayCauseArgs {
  /** One of acquired | pivoted | unfunded | lost-benchmark-race | superseded | archived | research-complete | unknown. */
  cause: string;
}

export interface DecayCauseResult {
  cause: string;
  totalMatches: number;
  records: Array<RecordSummary & {
    decay_cause: string;
    decay_date?: string;
    decay_evidence?: string;
  }>;
}

/**
 * Records whose decay_cause matches the given cause. Surfaces the
 * mortality forensics from T3-1 — useful for "which products in this
 * space were acquired vs ran out of funding vs were archived?"
 */
export function findByDecayCause(
  records: LandscapeRecord[],
  args: DecayCauseArgs
): DecayCauseResult {
  const want = args.cause.trim().toLowerCase();
  const matches = records.filter((r) => (r.decay_cause ?? '').toLowerCase() === want);
  matches.sort((a, b) => a.name.localeCompare(b.name));
  return {
    cause: want,
    totalMatches: matches.length,
    records: matches.map((r) => ({
      ...toSummary(r),
      decay_cause: r.decay_cause ?? '',
      decay_date: r.decay_date,
      decay_evidence: r.decay_evidence
    }))
  };
}

// ===========================================================================
// Re-exports for the CLI in #49
// ===========================================================================

export type { LandscapeRecord, Edge, EdgeType, Cell, Cells, ColumnSlug } from './types.js';
