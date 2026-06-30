// Fixture-based tests for rankCandidates (issue #96).
//
// Runs under node — no test framework — same convention as
// test-tools.ts. Each assertion throws on failure; the process exits
// non-zero. The fixtures are minimal LandscapeRecord shapes that only
// populate the Phase 2 cells `rankCandidates` reads + the Cell shape
// required by `LandscapeRecord.cells`.
//
// Run with:  node dist/test-recommender.js

import type {
  Cell,
  Cells,
  CellProvenance,
  LandscapeRecord
} from './types.js';
import {
  rankCandidates,
  betweenModels,
  type AnchorPair,
  type Candidate,
  type ConstraintSet
} from './recommender.js';

// =========================================================================
// Fixture builders
// =========================================================================

type Phase2Slug =
  | 'cost-input-usd-per-mtok'
  | 'cost-output-usd-per-mtok'
  | 'cost-tier'
  | 'cost-pricing-model'
  | 'cost-last-verified'
  | 'capability-composite-score'
  | 'capability-band'
  | 'capability-benchmark-sources'
  | 'capability-last-verified'
  | 'use-case-tags'
  | 'use-case-anti-tags';

interface RowSpec {
  id: string;
  costUsd?: string | null;
  costTier?: string | null;
  costPricingModel?: string;
  costLastVerified?: string;
  capScore?: string | null;
  capBand?: string | null;
  capLastVerified?: string;
  tags?: string;
  antiTags?: string;
  /** Per-slug provenance override. Anything not specified gets `legacy/verified:true`. */
  provenance?: Partial<Record<Phase2Slug, CellProvenance>>;
}

function cell(value: string | null, hasData = true): Cell {
  return {
    value: value ?? '',
    citation: null,
    status: hasData && value != null ? 'estimate' : 'no-data',
    tier: 'T3'
  };
}

function buildCells(spec: RowSpec): Cells {
  // Only Phase 2 cells are read by the recommender. All other cells get
  // an empty placeholder so the Cells type is satisfied.
  const phase2: Record<Phase2Slug, Cell> = {
    'cost-input-usd-per-mtok': cell(spec.costUsd ?? null),
    'cost-output-usd-per-mtok': cell(null),
    'cost-tier': cell(spec.costTier ?? null),
    'cost-pricing-model': cell(spec.costPricingModel ?? 'per-token'),
    'cost-last-verified': cell(spec.costLastVerified ?? null),
    'capability-composite-score': cell(spec.capScore ?? null),
    'capability-band': cell(spec.capBand ?? null),
    'capability-benchmark-sources': cell(null),
    'capability-last-verified': cell(spec.capLastVerified ?? null),
    'use-case-tags': cell(spec.tags ?? null),
    'use-case-anti-tags': cell(spec.antiTags ?? null)
  };
  return phase2 as unknown as Cells;
}

function buildProvenance(
  spec: RowSpec
): Record<string, CellProvenance> | undefined {
  if (!spec.provenance) return undefined;
  const out: Record<string, CellProvenance> = {};
  for (const [k, v] of Object.entries(spec.provenance)) {
    if (v) out[k] = v;
  }
  return Object.keys(out).length > 0 ? out : undefined;
}

function makeRecord(spec: RowSpec): LandscapeRecord {
  return {
    id: spec.id,
    name: spec.id,
    tier: 3,
    url: null,
    last_verified_at: '2026-06-29',
    sections: [
      {
        section: 'Test',
        subsection: null,
        primary: true,
        reason: null
      }
    ],
    taxonomy: {
      storage: [],
      retrieval: [],
      persistence: [],
      update: [],
      unit: [],
      governance: [],
      conflict: []
    },
    cells: buildCells(spec),
    _provenance: buildProvenance(spec)
  };
}

// =========================================================================
// Provenance helpers
// =========================================================================

const VERIFIED_LLM: CellProvenance = {
  source: 'llm',
  verified: true,
  generated_at: '2026-06-29',
  model_id: 'claude-opus-4-7'
};

const UNVERIFIED_LLM: CellProvenance = {
  source: 'llm',
  verified: false,
  generated_at: '2026-06-29',
  model_id: 'claude-opus-4-7'
};

// =========================================================================
// Assertion helpers
// =========================================================================

function banner(title: string) {
  console.log('\n' + '='.repeat(70));
  console.log(' ' + title);
  console.log('='.repeat(70));
}

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) {
    throw new Error('assertion failed: ' + msg);
  }
}

function assertEqual<T>(actual: T, expected: T, msg: string): void {
  if (actual !== expected) {
    throw new Error(
      `${msg}: expected ${JSON.stringify(expected)} got ${JSON.stringify(actual)}`
    );
  }
}

function findById(cands: Candidate[], id: string): Candidate | undefined {
  return cands.find((c) => c.record.id === id);
}

// =========================================================================
// Fixtures — common pool
// =========================================================================

function buildPool(): LandscapeRecord[] {
  return [
    // Ideal: cheap, frontier, scoped-agentic, fully verified.
    makeRecord({
      id: 'alpha',
      costUsd: '0.5',
      costTier: 'budget',
      capScore: '85',
      capBand: 'frontier',
      tags: 'scoped-agentic, code-generation-focused',
      antiTags: '',
      costLastVerified: '2026-06-29',
      capLastVerified: '2026-06-29'
    }),
    // Premium / over-budget alternative.
    makeRecord({
      id: 'beta',
      costUsd: '20',
      costTier: 'premium',
      capScore: '90',
      capBand: 'frontier',
      tags: 'scoped-agentic, analytical-summarization',
      antiTags: '',
      costLastVerified: '2026-06-29',
      capLastVerified: '2026-06-29'
    }),
    // Anti-tag match against scoped-agentic.
    makeRecord({
      id: 'gamma',
      costUsd: '0.3',
      costTier: 'budget',
      capScore: '60',
      capBand: 'competent',
      tags: 'long-running-session',
      antiTags: 'scoped-agentic',
      costLastVerified: '2026-06-29',
      capLastVerified: '2026-06-29'
    }),
    // Low capability (entry-band).
    makeRecord({
      id: 'delta',
      costUsd: '0.1',
      costTier: 'free',
      capScore: '20',
      capBand: 'entry',
      tags: 'scoped-agentic',
      antiTags: '',
      costLastVerified: '2026-06-29',
      capLastVerified: '2026-06-29'
    }),
    // Mid-priced, mid-capability — useful as anchor "high".
    makeRecord({
      id: 'epsilon',
      costUsd: '5',
      costTier: 'mid',
      capScore: '70',
      capBand: 'competent',
      tags: 'scoped-agentic, multi-agent-coordination',
      antiTags: '',
      costLastVerified: '2026-06-29',
      capLastVerified: '2026-06-29'
    })
  ];
}

// =========================================================================
// 1. Anchor mode — candidates between two anchors on cost/capability
// =========================================================================

function testAnchorMode() {
  banner('1. Anchor mode — between low-end (delta) and high-end (beta)');

  const pool = buildPool();
  const anchors: AnchorPair = { low: 'delta', high: 'beta' };
  // delta: cost=0.1 cap=20 ; beta: cost=20 cap=90 → range cost [0.1, 20], cap [20, 90].
  // Expected in-band: alpha, gamma, epsilon. Anchors themselves excluded.
  const result = rankCandidates(pool, {}, anchors, 10);

  console.log(`  in-band candidates: ${result.length}`);
  for (const c of result) {
    console.log(
      `    ${c.record.id.padEnd(10)} score=${c.score.toFixed(3)} (capScore=${
        c.record.cells['capability-composite-score'].value
      })`
    );
  }
  const ids = result.map((c) => c.record.id);
  assert(ids.includes('alpha'), 'alpha should be in the anchor band');
  assert(ids.includes('gamma'), 'gamma should be in the anchor band');
  assert(ids.includes('epsilon'), 'epsilon should be in the anchor band');
  assert(!ids.includes('delta'), 'low anchor delta must be excluded');
  assert(!ids.includes('beta'), 'high anchor beta must be excluded');

  // Sort order: anchor-only mode ranks by capability score desc.
  assertEqual(result[0].record.id, 'alpha', 'highest-cap in band ranks first');
}

// =========================================================================
// 2. Constraint mode — use_case_tags boosts score; anti-tag deducts
// =========================================================================

function testConstraintMode() {
  banner('2. Constraint mode — scoped-agentic boost + anti-tag deduction');

  const pool = buildPool();
  const constraints: ConstraintSet = {
    use_case_tags: ['scoped-agentic']
  };
  const result = rankCandidates(pool, constraints, undefined, 10);
  for (const c of result) {
    console.log(
      `    ${c.record.id.padEnd(10)} score=${c.score.toFixed(3)} rationale=${JSON.stringify(c.rationale)} caveats=${JSON.stringify(c.caveats)}`
    );
  }

  const alpha = findById(result, 'alpha');
  const gamma = findById(result, 'gamma');
  const delta = findById(result, 'delta');
  const beta = findById(result, 'beta');

  assert(alpha, 'alpha must appear in constraint result');
  assert(gamma, 'gamma must appear');
  assert(delta, 'delta must appear');
  assert(beta, 'beta must appear');

  // alpha has the tag, no anti-tag → score 1.0
  assertEqual(alpha.score, 1, 'alpha (tag match, no anti-tag) → score 1');
  // delta has the tag, no anti-tag → score 1.0
  assertEqual(delta.score, 1, 'delta (tag match, no anti-tag) → score 1');
  // gamma has anti-tag scoped-agentic → score 0 after penalty
  assertEqual(gamma.score, 0, 'gamma (anti-tag scoped-agentic) → score 0');
  assert(
    gamma.caveats.some((cv) => cv.includes('anti-tag match: scoped-agentic')),
    'gamma must surface an anti-tag caveat'
  );
  // beta has scoped-agentic in positive tags → score 1
  assertEqual(beta.score, 1, 'beta tag-only match → score 1');
}

// =========================================================================
// 3. Provenance — LLM-unverified cell excluded from score + caveat surfaces
// =========================================================================

function testProvenanceLlmUnverifiedExcluded() {
  banner('3. Provenance — capability-band LLM-unverified is excluded');

  const recVerified = makeRecord({
    id: 'verified-row',
    capScore: '85',
    capBand: 'frontier',
    tags: 'scoped-agentic',
    provenance: {
      'capability-band': VERIFIED_LLM
    }
  });
  const recUnverified = makeRecord({
    id: 'unverified-row',
    capScore: '85',
    capBand: 'frontier',
    tags: 'scoped-agentic',
    provenance: {
      'capability-band': UNVERIFIED_LLM
    }
  });
  const pool = [recVerified, recUnverified];
  const constraints: ConstraintSet = {
    capability_band_min: 'frontier'
  };
  const result = rankCandidates(pool, constraints, undefined, 10);

  const v = findById(result, 'verified-row');
  const u = findById(result, 'unverified-row');
  assert(v, 'verified-row missing');
  assert(u, 'unverified-row missing');

  console.log(`    verified-row:   score=${v.score} caveats=${JSON.stringify(v.caveats)}`);
  console.log(`    unverified-row: score=${u.score} caveats=${JSON.stringify(u.caveats)}`);

  // verified-row: capability-band frontier ≥ frontier → score 1, no caveat.
  assertEqual(v.score, 1, 'verified row scored on capability-band');
  assert(
    !v.caveats.some((cv) => cv.includes('capability-band excluded')),
    'verified row must not have a capability-band exclusion caveat'
  );
  // unverified-row: capability-band excluded → no constraint left to score → score 0.
  assertEqual(u.score, 0, 'unverified row has no scoring constraint left');
  assert(
    u.caveats.some((cv) => cv === 'capability-band excluded from ranking — LLM-unverified'),
    'unverified row must surface the exclusion caveat'
  );
}

// =========================================================================
// 4. Provenance verified=true → cell IS ranked, no exclusion caveat
// =========================================================================

function testProvenanceVerifiedRanks() {
  banner('4. Provenance — verified:true cells DO rank with no caveat');

  const rec = makeRecord({
    id: 'allgood',
    costUsd: '0.5',
    costTier: 'budget',
    capScore: '85',
    capBand: 'frontier',
    tags: 'scoped-agentic',
    provenance: {
      'cost-input-usd-per-mtok': VERIFIED_LLM,
      'cost-tier': VERIFIED_LLM,
      'capability-band': VERIFIED_LLM,
      'use-case-tags': VERIFIED_LLM
    }
  });
  const result = rankCandidates(
    [rec],
    {
      use_case_tags: ['scoped-agentic'],
      cost_max_input_usd_per_mtok: 1,
      capability_band_min: 'frontier'
    },
    undefined,
    10
  );
  const c = result[0];
  assert(c, 'expected single result');
  console.log(`    allgood: score=${c.score} rationale=${JSON.stringify(c.rationale)}`);
  assertEqual(c.score, 1, 'verified-true row with full match → score 1');
  assert(
    !c.caveats.some((cv) => cv.includes('excluded from ranking')),
    'no exclusion caveats expected'
  );
  assert(c.rationale.length >= 3, 'rationale should enumerate the three matches');
}

// =========================================================================
// 5. Staleness — cost-last-verified older than staleDays surfaces caveat
// =========================================================================

function testStaleCaveat() {
  banner('5. Staleness — cost-last-verified > 30 days yields a caveat');

  const rec = makeRecord({
    id: 'stale-row',
    costUsd: '0.5',
    costTier: 'budget',
    capScore: '85',
    capBand: 'frontier',
    tags: 'scoped-agentic',
    costLastVerified: '2026-01-01' // ~180 days before default today 2026-06-29
  });
  const result = rankCandidates([rec], { use_case_tags: ['scoped-agentic'] }, undefined, 1);
  const c = result[0];
  assert(c, 'stale-row missing');
  console.log(`    caveats: ${JSON.stringify(c.caveats)}`);
  assert(
    c.caveats.some((cv) => /cost data \d+d stale/.test(cv)),
    'stale-row must surface a cost-data staleness caveat'
  );
  // Score is unaffected by staleness — visibility-only.
  assertEqual(c.score, 1, 'staleness must not change the score');
}

// =========================================================================
// 6. Determinism — same inputs → byte-identical output
// =========================================================================

function testDeterminism() {
  banner('6. Determinism — repeated calls yield byte-identical output');

  const pool = buildPool();
  const constraints: ConstraintSet = {
    use_case_tags: ['scoped-agentic'],
    cost_max_input_usd_per_mtok: 1,
    capability_band_min: 'competent'
  };
  const a = rankCandidates(pool, constraints, undefined, 5);
  const b = rankCandidates(pool, constraints, undefined, 5);
  const aStr = JSON.stringify(a.map(({ record, ...rest }) => ({ id: record.id, ...rest })));
  const bStr = JSON.stringify(b.map(({ record, ...rest }) => ({ id: record.id, ...rest })));
  assertEqual(aStr, bStr, 'two runs must produce byte-identical Candidate arrays');
  console.log('    two runs are byte-identical');

  // Tie-break order: when scores tie, id order is alphabetical.
  const allTied = rankCandidates(buildPool(), {}, undefined, 10);
  const ids = allTied.map((c) => c.record.id);
  const sorted = [...ids].sort();
  assertEqual(
    JSON.stringify(ids),
    JSON.stringify(sorted),
    'all-tied result must be alphabetical by id'
  );
}

// =========================================================================
// 7. Combined — anchors filter, constraints score
// =========================================================================

function testAnchorPlusConstraints() {
  banner('7. Combined — anchors filter pool, constraints score what remains');

  const pool = buildPool();
  // Restrict to mid-range (delta..beta), then score by scoped-agentic.
  const result = rankCandidates(
    pool,
    { use_case_tags: ['scoped-agentic'] },
    { low: 'delta', high: 'beta' },
    10
  );
  const ids = result.map((c) => c.record.id);
  console.log(`    candidates: ${ids.join(', ')}`);
  // alpha has scoped-agentic, no anti-tag → top score.
  assertEqual(result[0].record.id, 'alpha', 'alpha (full match) ranks first in combined mode');
}

// =========================================================================
// 8. Empty / k cap
// =========================================================================

function testEmptyAndKCap() {
  banner('8. Edge cases — empty pool, k cap, unknown anchor');

  const empty = rankCandidates([], { use_case_tags: ['scoped-agentic'] }, undefined, 5);
  assertEqual(empty.length, 0, 'empty pool → empty result');

  const pool = buildPool();
  const capped = rankCandidates(pool, {}, undefined, 2);
  assertEqual(capped.length, 2, 'k=2 must return exactly 2');

  const badAnchor = rankCandidates(pool, {}, { low: 'nope', high: 'alpha' }, 5);
  assertEqual(badAnchor.length, 0, 'unknown anchor id → empty result');
}

// =========================================================================
// Main
// =========================================================================

// =========================================================================
// 9. betweenModels — surface adapter contract (issue #97 / Gate 3)
// =========================================================================
// Asserts that the snake_cased argument shape consumed by the MCP tool
// and the CLI subcommand produces the SAME ranking the underlying
// rankCandidates would for the equivalent constraint/anchor pair.
// Because web/MCP/CLI all import this single function (via verbatim
// mirror), surface-level identity reduces to this adapter test.

function testBetweenModelsAdapter() {
  banner('9. betweenModels — surface adapter matches rankCandidates 1:1');

  const pool = buildPool();

  // No use-case → adapter passes empty constraints.
  const viaAdapter = betweenModels(pool, {
    anchor_low_id: 'delta',
    anchor_high_id: 'beta',
    k: 5
  });
  const viaCore = rankCandidates(pool, {}, { low: 'delta', high: 'beta' }, 5);
  assertEqual(
    JSON.stringify(viaAdapter.map((c) => [c.record.id, c.score])),
    JSON.stringify(viaCore.map((c) => [c.record.id, c.score])),
    'adapter without use_case matches rankCandidates with empty constraints'
  );
  console.log(`    pass-through (no use_case): ${viaAdapter.length} candidate(s)`);

  // With use-case → adapter wraps it into use_case_tags: [tag].
  const viaAdapterTag = betweenModels(pool, {
    anchor_low_id: 'delta',
    anchor_high_id: 'beta',
    use_case: 'scoped-agentic',
    k: 5
  });
  const viaCoreTag = rankCandidates(
    pool,
    { use_case_tags: ['scoped-agentic'] },
    { low: 'delta', high: 'beta' },
    5
  );
  assertEqual(
    JSON.stringify(viaAdapterTag.map((c) => [c.record.id, c.score])),
    JSON.stringify(viaCoreTag.map((c) => [c.record.id, c.score])),
    'adapter with use_case matches rankCandidates with use_case_tags: [tag]'
  );
  console.log(`    pass-through (use_case): ${viaAdapterTag[0]?.record.id ?? '(empty)'} first`);

  // Default k = 5 (rankCandidates' default propagates).
  const defaultK = betweenModels(pool, {
    anchor_low_id: 'delta',
    anchor_high_id: 'beta'
  });
  if (defaultK.length > 5) {
    throw new Error(`betweenModels default k should cap at 5, got ${defaultK.length}`);
  }
  console.log(`    default-k cap honoured (≤5)`);

  // Determinism via the adapter — two calls byte-identical.
  const a = JSON.stringify(
    betweenModels(pool, {
      anchor_low_id: 'delta',
      anchor_high_id: 'beta',
      use_case: 'scoped-agentic',
      k: 5
    }).map(({ record, ...rest }) => ({ id: record.id, ...rest }))
  );
  const b = JSON.stringify(
    betweenModels(pool, {
      anchor_low_id: 'delta',
      anchor_high_id: 'beta',
      use_case: 'scoped-agentic',
      k: 5
    }).map(({ record, ...rest }) => ({ id: record.id, ...rest }))
  );
  assertEqual(a, b, 'two betweenModels calls must be byte-identical');
  console.log('    adapter is deterministic across runs');
}

function main() {
  testAnchorMode();
  testConstraintMode();
  testProvenanceLlmUnverifiedExcluded();
  testProvenanceVerifiedRanks();
  testStaleCaveat();
  testDeterminism();
  testAnchorPlusConstraints();
  testEmptyAndKCap();
  testBetweenModelsAdapter();

  banner('All recommender tests PASSED.');
}

try {
  main();
} catch (err) {
  console.error('\n[test-recommender] FAILED:');
  console.error(err instanceof Error ? err.stack : err);
  process.exit(1);
}
