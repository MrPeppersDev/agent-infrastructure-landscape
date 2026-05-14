// Types mirror docs/SCHEMA.md. Keep in sync with that spec.

export type Status =
  | 'real-data'
  | 'not-applicable'
  | 'depth-floor-reached'
  | 'no-data'
  | 'estimate';

/**
 * Claim-tier provenance — see docs/SCHEMA.md §3a.
 *
 *   T1 — auto-verifiable (GitHub-URL citations today)
 *   T2 — source-URL required (resolvable http(s) URL)
 *   T3 — estimate / inferred (no citation requirement)
 *
 * Populated automatically by scripts/extract.py from the (citation,
 * status) pair using the conservative heuristic in §3a. Validated by
 * gate 5 of scripts/validate.py.
 */
export type ClaimTier = 'T1' | 'T2' | 'T3';

export interface Cell {
  /** Visible text with HTML stripped, whitespace normalised. */
  value: string;
  /** http(s):// URL the data was sourced from, or null. */
  citation: string | null;
  status: Status;
  /** Provenance tier — see docs/SCHEMA.md §3a. */
  tier: ClaimTier;
}

export interface TaxonomyValue {
  /** Lowercase canonical taxonomy term. */
  value: string;
  /** True for the dominant value on this axis. Exactly one per axis. */
  primary: boolean;
  /** Short justification, null if obvious or single-value. */
  reason: string | null;
}

export interface Taxonomy {
  storage: TaxonomyValue[];
  retrieval: TaxonomyValue[];
  persistence: TaxonomyValue[];
  update: TaxonomyValue[];
  unit: TaxonomyValue[];
  governance: TaxonomyValue[];
  conflict: TaxonomyValue[];
}

export interface SectionMembership {
  /** Top-level section name (e.g. "Dedicated memory layers"). */
  section: string;
  /** Sub-group within the section, or null. Subsections start with "— ". */
  subsection: string | null;
  /** True for the canonical primary placement. Exactly one per record. */
  primary: boolean;
  /** Short justification for the placement, or null. */
  reason: string | null;
}

/** Tier 1 (battle-tested) → Tier 5 (theoretical / informal). */
export type Tier = 1 | 2 | 3 | 4 | 5;

/**
 * The 68 column slugs from docs/SCHEMA.md §2.5. Every record's `cells`
 * object MUST contain all of these keys (with status: "not-applicable"
 * when the column is meaningless for that record).
 *
 * Columns 61-68 (the `obs-*` family) were appended in T1-1 (issue #39)
 * to capture observability-stack integration support. See SCHEMA.md
 * §2.5.1 for semantics.
 */
export type ColumnSlug =
  | 'type'
  | 'desc'
  | 'claims'
  | 'modalities'
  | 'created'
  | 'latest-release'
  | 'license'
  | 'gh'
  | 'mindshare'
  | 'citations'
  | 'funding'
  | 'customers'
  | 'pricing'
  | 'compliance'
  | 'data-handling'
  | 'deployment'
  | 'hq'
  | 'founders'
  | 'volume'
  | 'perf'
  | 'repro'
  | 'code-release'
  | 'api-surface'
  | 'latency'
  | 'throughput'
  | 'backend-storage'
  | 'multi-tenancy'
  | 'encryption'
  | 'sso-rbac'
  | 'embedding-model'
  | 'consistency'
  | 'versioning'
  | 'tombstoning'
  | 'schema-evolution'
  | 'namespace'
  | 'contradiction'
  | 'forgetting'
  | 'mcp-support'
  | 'a2a-support'
  | 'otel'
  | 'webhooks'
  | 'import-export'
  | 'integration-count'
  | 'orchestration'
  | 'programmatic-control'
  | 'vendor-benchmarks'
  | 'pricing-specifics'
  | 'agent-abstraction'
  | 'memory-primitives'
  | 'llm-lock'
  | 'runtimes'
  | 'session-handling'
  | 'validated-verticals'
  | 'time-to-running'
  | 'anti-fit'
  | 'optimised-for'
  | 'adjacent-infrastructure'
  | 'pros'
  | 'cons'
  | 'links'
  | 'obs-langsmith'
  | 'obs-opentelemetry'
  | 'obs-datadog'
  | 'obs-helicone'
  | 'obs-weave'
  | 'obs-langfuse'
  | 'obs-arize'
  | 'obs-custom';

export type Cells = Record<ColumnSlug, Cell>;

export interface LandscapeRecord {
  /** Stable slug. See SCHEMA.md §2.1. */
  id: string;
  /** Display name. */
  name: string;
  tier: Tier;
  /** http(s):// URL or null. */
  url: string | null;
  /** Non-empty array. Exactly one element has primary: true. */
  sections: SectionMembership[];
  taxonomy: Taxonomy;
  cells: Cells;
}

export interface LandscapeFile {
  schemaVersion: string;
  generatedAt: string;
  sourceHtml: string;
  records: LandscapeRecord[];
}

export type EdgeType =
  | 'built-on'
  | 'extends'
  | 'forks'
  | 'integrates-with'
  | 'competes-with'
  | 'inspired-by'
  | 'cites'
  | 'same-team-as'
  | 'succeeds';

export interface Edge {
  /** Record id; must exist in landscape records. */
  source: string;
  /** Record id; must exist in landscape records. */
  target: string;
  type: EdgeType;
  /** 1-2 sentence summary of the source claim that justified the edge. */
  evidence: string;
  /** http(s):// URL where evidence can be verified. */
  citation: string;
  /** Present iff type === 'cites'. From Semantic Scholar. */
  isInfluential?: boolean;
}

export interface EdgesFile {
  schemaVersion: string;
  generatedAt: string;
  edges: Edge[];
}
