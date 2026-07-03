// Tests for composite.ts — matches the no-framework convention of
// test-tools.ts and test-recommender.ts. Each assertion throws on
// failure; process exits non-zero.
//
// Run with:  node dist/test-composite.js

import {
  BAND_CUTOFFS,
  BenchmarkAnchors,
  BenchmarkObservation,
  computeComposite,
  computeFamilyScore,
  computeRow,
  deriveBand,
  normalize,
  TaskFamily,
  TASK_FAMILIES
} from './composite.js';

// =========================================================================
// Assertion helpers
// =========================================================================

let testsRun = 0;
let testsFailed = 0;

function assertEq(actual: unknown, expected: unknown, label: string): void {
  testsRun++;
  if (Object.is(actual, expected)) return;
  testsFailed++;
  console.error(`FAIL  ${label}\n  expected: ${String(expected)}\n  actual:   ${String(actual)}`);
}

function assertClose(actual: number | null, expected: number, label: string, eps = 1e-6): void {
  testsRun++;
  if (actual != null && Math.abs(actual - expected) < eps) return;
  testsFailed++;
  console.error(`FAIL  ${label}\n  expected: ${expected}\n  actual:   ${actual}`);
}

function assertNull(actual: unknown, label: string): void {
  testsRun++;
  if (actual === null) return;
  testsFailed++;
  console.error(`FAIL  ${label}\n  expected: null\n  actual:   ${String(actual)}`);
}

// =========================================================================
// normalize()
// =========================================================================

assertEq(normalize(50, { max: 100 }), 50, 'normalize: midpoint with default min=0');
assertEq(normalize(0, { max: 100 }), 0, 'normalize: floor → 0');
assertEq(normalize(100, { max: 100 }), 100, 'normalize: ceiling → 100');
assertEq(normalize(150, { max: 100 }), 100, 'normalize: above ceiling clamps to 100');
assertEq(normalize(-10, { max: 100 }), 0, 'normalize: below floor clamps to 0');
assertEq(normalize(75, { min: 50, max: 100 }), 50, 'normalize: with explicit min');
assertEq(normalize(50, { max: 0 }), 0, 'normalize: degenerate max ≤ min → 0');
assertEq(normalize(NaN, { max: 100 }), 0, 'normalize: NaN score → 0');

// =========================================================================
// computeFamilyScore()
// =========================================================================

const anchors: BenchmarkAnchors = {
  'bench-a': { max: 100 },
  'bench-b': { max: 100 },
  'bench-c': { max: 50 }
};

assertClose(
  computeFamilyScore(
    [
      { id: 'bench-a', score: 80, trust: 1.0, family: 'code' },
      { id: 'bench-b', score: 60, trust: 1.0, family: 'code' }
    ],
    anchors
  ),
  70,
  'family: equal trust, two benchmarks → arithmetic mean'
);

assertClose(
  computeFamilyScore(
    [
      { id: 'bench-a', score: 80, trust: 1.0, family: 'code' },
      { id: 'bench-b', score: 60, trust: 0.5, family: 'code' }
    ],
    anchors
  ),
  (1.0 * 80 + 0.5 * 60) / 1.5,
  'family: unequal trust → trust-weighted mean'
);

assertClose(
  computeFamilyScore(
    [
      { id: 'bench-c', score: 25, trust: 1.0, family: 'code' }
    ],
    anchors
  ),
  50,
  'family: normalised against per-benchmark max (25/50 → 50)'
);

assertNull(
  computeFamilyScore([], anchors),
  'family: empty observations → null'
);

assertNull(
  computeFamilyScore(
    [{ id: 'bench-a', score: 80, trust: 0, family: 'code' }],
    anchors
  ),
  'family: all-zero trust → null'
);

assertNull(
  computeFamilyScore(
    [{ id: 'unknown-bench', score: 80, trust: 1.0, family: 'code' }],
    anchors
  ),
  'family: benchmark with no anchor → ignored, returns null'
);

// =========================================================================
// computeComposite() — geometric mean (§7.2)
// =========================================================================

assertClose(
  computeComposite({ code: 80, agentic: 80, longcontext: 80 }),
  80,
  'composite: all equal → equal output'
);

assertClose(
  computeComposite({ code: 100, agentic: 25, longcontext: 25 }),
  Math.pow(100 * 25 * 25, 1 / 3),
  'composite: geometric mean penalises one-axis strength vs arithmetic'
);

// Arithmetic mean of (100, 25, 25) = 50; geometric < 50. Specifically prove this.
const oneAxisStrong = computeComposite({ code: 100, agentic: 25, longcontext: 25 });
if (oneAxisStrong != null && oneAxisStrong >= 50) {
  testsRun++;
  testsFailed++;
  console.error(
    `FAIL  composite: one-axis strength must be penalised below arithmetic mean (got ${oneAxisStrong})`
  );
} else {
  testsRun++;
}

assertClose(
  computeComposite({ code: 60, agentic: null, longcontext: null }),
  60,
  'composite: single present family → its score directly'
);

assertClose(
  computeComposite({ code: 80, agentic: 50, longcontext: null }),
  Math.sqrt(80 * 50),
  'composite: two present families → geometric mean over present only'
);

assertNull(
  computeComposite({ code: null, agentic: null, longcontext: null }),
  'composite: all null → null (no evidence at all)'
);

assertEq(
  computeComposite({ code: 0, agentic: 80, longcontext: 80 }),
  0,
  'composite: any present family at 0 → composite collapses to 0 (intentional §7.2)'
);

// =========================================================================
// deriveBand() — cutoffs (§10)
// =========================================================================

assertEq(deriveBand(null), null, 'band: null composite → null');
assertEq(deriveBand(0), 'entry', 'band: 0 → entry');
assertEq(deriveBand(BAND_CUTOFFS.competent - 0.1), 'entry', 'band: just below competent → entry');
assertEq(deriveBand(BAND_CUTOFFS.competent), 'competent', 'band: at competent cutoff → competent');
assertEq(deriveBand(BAND_CUTOFFS.frontier - 0.1), 'competent', 'band: just below frontier → competent');
assertEq(deriveBand(BAND_CUTOFFS.frontier), 'frontier', 'band: at frontier cutoff → frontier');
assertEq(deriveBand(100), 'frontier', 'band: 100 → frontier');

// =========================================================================
// computeRow() — end-to-end one-row pipeline
// =========================================================================

const rowAnchors: BenchmarkAnchors = {
  'aider-polyglot': { max: 100 },
  'swe-bench-verified': { max: 70 },
  'gaia': { max: 80 },
  'ruler-128k': { max: 95 }
};

const rowObs: BenchmarkObservation[] = [
  { id: 'aider-polyglot', score: 70, trust: 0.9, family: 'code' },
  { id: 'swe-bench-verified', score: 49, trust: 0.85, family: 'code' },
  { id: 'gaia', score: 40, trust: 0.8, family: 'agentic' },
  { id: 'ruler-128k', score: 76, trust: 0.85, family: 'longcontext' }
];

const row = computeRow(rowObs, rowAnchors);

assertEq(row.benchmarkCount.code, 2, 'row: code benchmarks counted');
assertEq(row.benchmarkCount.agentic, 1, 'row: agentic benchmarks counted');
assertEq(row.benchmarkCount.longcontext, 1, 'row: longcontext benchmarks counted');

// Code: trust-weighted mean of (70, 70 from 49/70 * 100). 70 normalised over 100 = 70;
// 49 normalised over 70 = 70. Both at 70 → family = 70.
assertClose(row.byFamily.code, 70, 'row: code sub-score');
// Agentic: 40 normalised over 80 = 50.
assertClose(row.byFamily.agentic, 50, 'row: agentic sub-score');
// Longcontext: 76 normalised over 95 = 80.
assertClose(row.byFamily.longcontext, 80, 'row: longcontext sub-score');

assertClose(
  row.composite,
  Math.pow(70 * 50 * 80, 1 / 3),
  'row: composite is geometric mean of sub-scores'
);

// Composite ≈ 65.8 → competent band
assertEq(row.band, 'competent', 'row: band derived from composite');

// =========================================================================
// All families present at TASK_FAMILIES exactly
// =========================================================================

assertEq(TASK_FAMILIES.length, 3, 'task families: three exactly (code, agentic, longcontext)');
assertEq(TASK_FAMILIES.includes('code' as TaskFamily), true, 'task families: includes code');
assertEq(TASK_FAMILIES.includes('agentic' as TaskFamily), true, 'task families: includes agentic');
assertEq(TASK_FAMILIES.includes('longcontext' as TaskFamily), true, 'task families: includes longcontext');

// =========================================================================
// Summary
// =========================================================================

console.log(`\ncomposite tests: ${testsRun - testsFailed}/${testsRun} passed`);
if (testsFailed > 0) {
  process.exit(1);
}
