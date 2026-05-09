// Column metadata — display order, header text, group bands, trend flags.
//
// The 60 cell columns from SCHEMA.md §2.5 plus three "virtual" columns:
//   - `name` (sticky, leftmost)
//   - `tier` (between name and type — surfaces the row tier as a value)
//   - the seven taxonomy axes (storage, retrieval, persistence, update,
//     unit, governance, conflict) — flattened as their own columns.
//
// Total visible columns by default: 1 (name) + 1 (tier) + 1 (type) +
// 7 (taxonomy axes) + 59 (other cell slugs) = 69. The issue spec aims for
// "all 67 non-name columns", which lines up if you don't double-count
// `tier` (it's already implied in the row class) — we display it for the
// trend-analysis use case.

import type { ColumnSlug } from './types';

/**
 * Group identifiers for the column-band coloring scheme.
 *
 * Why these groups: they mirror the conceptual groupings in landscape.html's
 * column-key legend (Identity / Substance / Activity / Adoption / Commercial
 * / Operational / Memory semantics / Standards / Section-deep / Architecture
 * / Research / Judgement). Group ordering matches the left-to-right order
 * of columns in the rendered table.
 */
export type ColumnGroup =
  | 'identity'
  | 'taxonomy'
  | 'substance'
  | 'activity'
  | 'adoption'
  | 'commercial'
  | 'operational'
  | 'semantics'
  | 'standards'
  | 'section-deep'
  | 'architecture'
  | 'research'
  | 'judgement';

export interface ColumnDef {
  /** Stable key. For cell columns, the slug from SCHEMA.md §2.5. For the
   *  three virtual columns, `name`, `tier`. */
  key: string;
  /** Header text shown in the table head. */
  label: string;
  /** Column-group band identifier — drives the header band color. */
  group: ColumnGroup;
  /** True for the trend-relevant columns called out in issue #9
   *  (created, funding, gh, mindshare, citations). Visually accented. */
  trend?: boolean;
  /** True iff `key` is one of the 60 cell-slug columns. False for the
   *  virtual columns (name, tier) and the seven taxonomy axes. */
  isCell?: boolean;
  /** True iff `key` is one of the seven taxonomy axes. */
  isTaxonomy?: boolean;
  /** Default column width hint in pixels. Used to size <col> elements. */
  width?: number;
}

/**
 * Group display metadata. Color bands chosen to be subtle (low saturation)
 * so the eye can find groups without being overwhelmed. All bands sit on
 * the same dark base; only hue and a small saturation lift differentiate.
 *
 * Picked from a 12-point hue wheel in HSL with L≈22 % and S≈18 % — under
 * 8 % saturation difference between adjacent groups, well within the
 * "subtle" budget the issue spec asks for.
 */
export const GROUP_META: Record<
  ColumnGroup,
  { label: string; bg: string; accent: string }
> = {
  identity:    { label: 'Identity',     bg: '#1a1f24', accent: '#5a8aa8' },
  taxonomy:    { label: 'Taxonomy',     bg: '#1a2420', accent: '#6aa884' },
  substance:   { label: 'Substance',    bg: '#1f1f24', accent: '#8a8ac8' },
  activity:    { label: 'Activity',     bg: '#1a2024', accent: '#5aa8c8' },
  adoption:    { label: 'Adoption',     bg: '#241f1a', accent: '#c89a5a' },
  commercial:  { label: 'Commercial',   bg: '#241a1f', accent: '#c87a8a' },
  operational: { label: 'Operational',  bg: '#1f241a', accent: '#9ac868' },
  semantics:   { label: 'Memory semantics', bg: '#241a24', accent: '#a868c8' },
  standards:   { label: 'Standards',    bg: '#1a2424', accent: '#5ac8b8' },
  'section-deep': { label: 'Section-deep', bg: '#24201a', accent: '#c8a868' },
  architecture: { label: 'Architecture', bg: '#1f241f', accent: '#7ac88a' },
  research:    { label: 'Research',     bg: '#1a1a24', accent: '#7a8ac8' },
  judgement:   { label: 'Judgement',    bg: '#241a1a', accent: '#c87a7a' }
};

/**
 * The full ordered column list. This array is the only place column
 * order, group, label, and trend-flag live; the table component just
 * iterates it.
 */
export const COLUMNS: ColumnDef[] = [
  // — Identity (sticky / leftmost)
  { key: 'name', label: 'System', group: 'identity', width: 220 },
  { key: 'tier', label: 'Tier',   group: 'identity', width: 70 },
  { key: 'type', label: 'Memory model', group: 'identity', isCell: true, width: 180 },

  // — Taxonomy axes
  { key: 'tax:storage',     label: 'Storage',     group: 'taxonomy', isTaxonomy: true, width: 130 },
  { key: 'tax:retrieval',   label: 'Retrieval',   group: 'taxonomy', isTaxonomy: true, width: 130 },
  { key: 'tax:persistence', label: 'Persistence', group: 'taxonomy', isTaxonomy: true, width: 130 },
  { key: 'tax:update',      label: 'Update',      group: 'taxonomy', isTaxonomy: true, width: 130 },
  { key: 'tax:unit',        label: 'Unit',        group: 'taxonomy', isTaxonomy: true, width: 130 },
  { key: 'tax:governance',  label: 'Governance',  group: 'taxonomy', isTaxonomy: true, width: 130 },
  { key: 'tax:conflict',    label: 'Conflict res.', group: 'taxonomy', isTaxonomy: true, width: 130 },

  // — Substance (what it does, claims)
  { key: 'desc',       label: "What it does & what's distinct", group: 'substance', isCell: true, width: 320 },
  { key: 'claims',     label: 'Claims / benefits', group: 'substance', isCell: true, width: 240 },
  { key: 'modalities', label: 'Modalities',        group: 'substance', isCell: true, width: 120 },

  // — Activity (timeline / trend signals)
  { key: 'created',        label: 'Created',        group: 'activity', isCell: true, trend: true, width: 100 },
  { key: 'latest-release', label: 'Latest release', group: 'activity', isCell: true, width: 130 },
  { key: 'license',        label: 'License',        group: 'activity', isCell: true, width: 110 },
  { key: 'gh',             label: 'GitHub',         group: 'activity', isCell: true, trend: true, width: 150 },

  // — Adoption (mindshare / citations)
  { key: 'mindshare',  label: 'Mindshare',  group: 'adoption', isCell: true, trend: true, width: 160 },
  { key: 'citations',  label: 'Citations',  group: 'adoption', isCell: true, trend: true, width: 110 },

  // — Commercial
  { key: 'funding',       label: 'Funding',           group: 'commercial', isCell: true, trend: true, width: 180 },
  { key: 'customers',     label: 'Customers / scale', group: 'commercial', isCell: true, width: 180 },
  { key: 'pricing',       label: 'Pricing',           group: 'commercial', isCell: true, width: 130 },
  { key: 'compliance',    label: 'Compliance',        group: 'commercial', isCell: true, width: 140 },
  { key: 'data-handling', label: 'Data handling',     group: 'commercial', isCell: true, width: 170 },
  { key: 'deployment',    label: 'Deployment',        group: 'commercial', isCell: true, width: 130 },
  { key: 'hq',            label: 'HQ',                group: 'commercial', isCell: true, width: 90 },
  { key: 'founders',      label: 'Founders / pedigree', group: 'commercial', isCell: true, width: 170 },

  // — Operational (volume, perf, repro)
  { key: 'volume',       label: 'Memory volume / scale', group: 'operational', isCell: true, width: 140 },
  { key: 'perf',         label: 'Performance',           group: 'operational', isCell: true, width: 170 },
  { key: 'repro',        label: 'Reproducibility',       group: 'operational', isCell: true, width: 130 },
  { key: 'code-release', label: 'Code/weights release',  group: 'operational', isCell: true, width: 130 },
  { key: 'api-surface',  label: 'API surface',           group: 'operational', isCell: true, width: 150 },
  { key: 'latency',      label: 'Latency p50/p99',       group: 'operational', isCell: true, width: 130 },
  { key: 'throughput',   label: 'Throughput',            group: 'operational', isCell: true, width: 130 },

  // — Memory semantics
  { key: 'backend-storage',  label: 'Backend storage',  group: 'semantics', isCell: true, width: 150 },
  { key: 'multi-tenancy',    label: 'Multi-tenancy',    group: 'semantics', isCell: true, width: 160 },
  { key: 'encryption',       label: 'Encryption',       group: 'semantics', isCell: true, width: 150 },
  { key: 'sso-rbac',         label: 'SSO / RBAC',       group: 'semantics', isCell: true, width: 110 },
  { key: 'embedding-model',  label: 'Embedding model',  group: 'semantics', isCell: true, width: 140 },
  { key: 'consistency',      label: 'Consistency',      group: 'semantics', isCell: true, width: 110 },
  { key: 'versioning',       label: 'Versioning',       group: 'semantics', isCell: true, width: 110 },
  { key: 'tombstoning',      label: 'Tombstoning',      group: 'semantics', isCell: true, width: 130 },
  { key: 'schema-evolution', label: 'Schema evolution', group: 'semantics', isCell: true, width: 140 },
  { key: 'namespace',        label: 'Namespace primitives', group: 'semantics', isCell: true, width: 150 },
  { key: 'contradiction',    label: 'Contradiction handling', group: 'semantics', isCell: true, width: 160 },
  { key: 'forgetting',       label: 'Forgetting policy', group: 'semantics', isCell: true, width: 140 },

  // — Standards
  { key: 'mcp-support', label: 'MCP support',     group: 'standards', isCell: true, width: 130 },
  { key: 'a2a-support', label: 'A2A support',     group: 'standards', isCell: true, width: 130 },
  { key: 'otel',        label: 'OTel',            group: 'standards', isCell: true, width: 110 },
  { key: 'webhooks',    label: 'Webhooks / events', group: 'standards', isCell: true, width: 140 },
  { key: 'import-export', label: 'Import / export', group: 'standards', isCell: true, width: 140 },
  { key: 'integration-count', label: 'Integration count', group: 'standards', isCell: true, width: 110 },

  // — Section-deep (cells specific to certain product categories)
  { key: 'orchestration',         label: 'Orchestration',         group: 'section-deep', isCell: true, width: 130 },
  { key: 'programmatic-control',  label: 'Programmatic control',  group: 'section-deep', isCell: true, width: 160 },
  { key: 'vendor-benchmarks',     label: 'Vendor benchmarks',     group: 'section-deep', isCell: true, width: 170 },
  { key: 'pricing-specifics',     label: 'Pricing specifics',     group: 'section-deep', isCell: true, width: 180 },

  // — Architecture (framework-embedded specifics)
  { key: 'agent-abstraction', label: 'Agent abstraction', group: 'architecture', isCell: true, width: 150 },
  { key: 'memory-primitives', label: 'Memory primitives', group: 'architecture', isCell: true, width: 150 },
  { key: 'llm-lock',          label: 'LLM lock',          group: 'architecture', isCell: true, width: 130 },
  { key: 'runtimes',          label: 'Runtimes',          group: 'architecture', isCell: true, width: 130 },
  { key: 'session-handling',  label: 'Session handling',  group: 'architecture', isCell: true, width: 140 },

  // — Research (validated verticals, time-to-running, anti-fit)
  { key: 'validated-verticals',     label: 'Validated verticals',     group: 'research', isCell: true, width: 170 },
  { key: 'time-to-running',         label: 'Time to running',         group: 'research', isCell: true, width: 140 },
  { key: 'anti-fit',                label: 'Anti-fit',                group: 'research', isCell: true, width: 150 },
  { key: 'optimised-for',           label: 'Optimised for',           group: 'research', isCell: true, width: 170 },
  { key: 'adjacent-infrastructure', label: 'Adjacent infrastructure', group: 'research', isCell: true, width: 200 },

  // — Judgement (pros, cons, links)
  { key: 'pros',  label: 'Pros',                group: 'judgement', isCell: true, width: 220 },
  { key: 'cons',  label: 'Cons',                group: 'judgement', isCell: true, width: 220 },
  { key: 'links', label: 'Project & sources',   group: 'judgement', isCell: true, width: 200 }
];

/**
 * Group runs for the second header row (colspan ranges over consecutive
 * columns sharing the same group). Computed once, cached.
 */
export interface GroupRun {
  group: ColumnGroup;
  start: number;
  span: number;
}

export const GROUP_RUNS: GroupRun[] = (() => {
  const runs: GroupRun[] = [];
  let i = 0;
  while (i < COLUMNS.length) {
    const g = COLUMNS[i].group;
    let j = i + 1;
    while (j < COLUMNS.length && COLUMNS[j].group === g) j++;
    runs.push({ group: g, start: i, span: j - i });
    i = j;
  }
  return runs;
})();

/** Lookup by column key. */
export const COLUMN_BY_KEY: Record<string, ColumnDef> = (() => {
  const m: Record<string, ColumnDef> = {};
  for (const c of COLUMNS) m[c.key] = c;
  return m;
})();

/** Get the cell slug from a column key, or null if not a cell column. */
export function cellSlugOf(key: string): ColumnSlug | null {
  const def = COLUMN_BY_KEY[key];
  if (!def?.isCell) return null;
  return def.key as ColumnSlug;
}

/** Get the taxonomy axis from a column key, or null. */
export function taxonomyAxisOf(
  key: string
): 'storage' | 'retrieval' | 'persistence' | 'update' | 'unit' | 'governance' | 'conflict' | null {
  if (!key.startsWith('tax:')) return null;
  return key.slice(4) as
    | 'storage'
    | 'retrieval'
    | 'persistence'
    | 'update'
    | 'unit'
    | 'governance'
    | 'conflict';
}
