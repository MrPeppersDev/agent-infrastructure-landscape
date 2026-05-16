// MCP server type definitions for the AI agent infrastructure landscape.
//
// SINGLE SOURCE OF TRUTH: web/src/lib/types.ts. This file is a verbatim
// mirror — the mcp/ package ships as a standalone npm-installable surface,
// so a TypeScript rootDir-respecting copy lives here. If you change one,
// change the other (web/src/lib/types.ts has the canonical SCHEMA.md-aligned
// docstrings).
//
// Keep in sync with web/src/lib/types.ts. Validate gate 1 of
// scripts/validate.py enforces the runtime shape against
// data/landscape.json — schema drift between the two type files will be
// caught the moment either consumer accesses an unexpected field.

export type Status =
  | 'real-data'
  | 'not-applicable'
  | 'depth-floor-reached'
  | 'no-data'
  | 'estimate';

/** Claim-tier provenance — see docs/SCHEMA.md §3a. */
export type ClaimTier = 'T1' | 'T2' | 'T3';

export interface Cell {
  value: string;
  citation: string | null;
  status: Status;
  tier: ClaimTier;
  /**
   * Per-cell ISO date ("YYYY-MM-DD") of the most recent verification of
   * this cell's claim. Present only on high-volatility cells (see
   * docs/SCHEMA.md §3b); other cells inherit the row-level
   * `LandscapeRecord.last_verified_at`.
   */
  last_verified_at?: string;
}

export interface TaxonomyValue {
  value: string;
  primary: boolean;
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
  section: string;
  subsection: string | null;
  primary: boolean;
  reason: string | null;
}

/** Tier 1 (battle-tested) → Tier 5 (theoretical / informal). */
export type Tier = 1 | 2 | 3 | 4 | 5;

/** Decay-cause forensics — see docs/SCHEMA.md §3c (issue #56). */
export type DecayCause =
  | 'acquired'
  | 'pivoted'
  | 'unfunded'
  | 'lost-benchmark-race'
  | 'superseded'
  | 'archived'
  | 'unknown';

/** The 82 column slugs from docs/SCHEMA.md §2.5. */
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
  | 'obs-custom'
  | 'cost-token-budget'
  | 'cost-prompt-caching'
  | 'cost-semantic-caching'
  | 'cost-batching'
  | 'cost-model-routing'
  | 'cost-streaming-only'
  | 'cost-observability-cost-attribution'
  | 'eval-langsmith-evals'
  | 'eval-braintrust'
  | 'eval-weights-and-biases-agent'
  | 'eval-helicone-evals'
  | 'eval-custom-test-harness'
  | 'eval-human-loop'
  | 'eval-production-traffic-replay'
  | 'commit-trajectory'
  | 'citation-trajectory'
  | 'download-trajectory';

export type Cells = Record<ColumnSlug, Cell>;

export interface LandscapeRecord {
  id: string;
  name: string;
  tier: Tier;
  url: string | null;
  /**
   * Row-level ISO date ("YYYY-MM-DD") of the most recent verification
   * of any field on this record. Inherited by every cell that does not
   * carry its own `Cell.last_verified_at`. See docs/SCHEMA.md §3b.
   */
  last_verified_at: string;
  /** Decay-cause forensics — see docs/SCHEMA.md §3c (issue #56). */
  decay_cause?: DecayCause;
  decay_date?: string;
  decay_evidence?: string;
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
  | 'runtime-dependency'
  | 'extends'
  | 'forks'
  | 'integrates-with'
  | 'competes-with'
  | 'inspired-by'
  | 'cites'
  | 'same-team-as'
  | 'succeeds';

export interface Edge {
  source: string;
  target: string;
  type: EdgeType;
  evidence: string;
  citation: string;
  isInfluential?: boolean;
}

export interface EdgesFile {
  schemaVersion: string;
  generatedAt: string;
  edges: Edge[];
}
