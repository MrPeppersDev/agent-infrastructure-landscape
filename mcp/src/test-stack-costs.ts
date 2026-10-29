// Tests for stack-costs.ts with fixed fixture prices (not the live price
// file), so the arithmetic is checked exactly.
// Run: npm run build && node dist/test-stack-costs.js
import { estimateMetered, estimateModel, monthlyUnits, stackCost, DEFAULT_STACK_WORKLOAD, type MeteredPricing, type StackPricing } from './stack-costs.js';

let failures = 0;
function ok(cond: unknown, msg: string): void {
  if (!cond) {
    failures++;
    console.error(`FAIL: ${msg}`);
  }
}

const w = { ...DEFAULT_STACK_WORKLOAD, runsPerDay: 100, llmCallsPerRun: 5, toolCallsPerRun: 3, inputTokensPerCall: 2000, outputTokensPerCall: 500, sandboxMinutesPerRun: 2 };

// units
ok(monthlyUnits('traces', w) === 3000, 'traces = runs per month');
ok(monthlyUnits('spans', w) === 3000 * 8, 'spans = runs × (llm + tool calls)');
ok(monthlyUnits('llm-requests', w) === 15000, 'llm requests = runs × calls');
ok(monthlyUnits('sandbox-minutes', w) === 6000, 'sandbox minutes');
ok(monthlyUnits('users', w) === w.users, 'users');

// models: 15,000 calls × 2,000 in = 30M in; × 500 out = 7.5M out
const m = estimateModel({ id: 'x', system: 'V', model: 'M', inputPerMtok: 3, outputPerMtok: 15, source: 'https://v/pricing' }, w);
ok(m.monthlyUsd === 30 * 3 + 7.5 * 15, `model cost = 30M×$3 + 7.5M×$15 (got ${m.monthlyUsd})`);
ok(m.working.length === 2 && m.source === 'https://v/pricing', 'model line shows working and source');

// metered: cheapest covering plan; overage when cheaper; contact sales beyond
const obs: MeteredPricing = {
  id: 'o', system: 'Obs', unit: 'traces', source: 'https://o/pricing',
  plans: [{ name: 'Free', usd: 0, included: 1000 }, { name: 'Pro', usd: 50, included: 10000 }],
  overage: { per: 1000, usd: 5 }, beyond: 'Enterprise'
};
const e1 = estimateMetered(obs, w); // 3,000 traces: Free + 2,000 over = $10 < Pro $50
ok(e1.monthlyUsd === 10 && e1.plan === 'Free', `overage on the free plan is cheaper (got ${e1.monthlyUsd} ${e1.plan})`);
const e2 = estimateMetered({ ...obs, overage: null }, w); // no overage: Pro covers 3,000
ok(e2.monthlyUsd === 50 && e2.plan === 'Pro', 'without overage the smallest covering plan is used');
const e3 = estimateMetered({ ...obs, overage: null }, { ...w, runsPerDay: 10_000 }); // 300k traces, beyond Pro
ok(e3.monthlyUsd === null && e3.plan === 'Enterprise', 'beyond the largest plan with no overage is contact sales, never extrapolated');

// stackCost: priced, unpriced, lower bound
const pricing: { stack: StackPricing; memory: { checked: string; vendors: never[] }; vector: { checked: string; vendors: never[] } } = {
  stack: { checked: '2026-10-29', models: [{ id: 'model-a', system: 'V', model: 'M', inputPerMtok: 3, outputPerMtok: 15, source: 'https://v' }], metered: [obs] },
  memory: { checked: '2026-10-27', vendors: [] },
  vector: { checked: '2026-10-27', vendors: [] }
};
const c = stackCost([
  { layer: 'model', id: 'model-a', name: 'V' },
  { layer: 'observability', id: 'o', name: 'Obs' },
  { layer: 'framework', id: 'lib', name: 'Some library' }
], pricing, w);
ok(c.lines.length === 3, 'one line per component');
ok(c.knownMonthlyUsd === 202.5 + 10, `total sums priced lines (got ${c.knownMonthlyUsd})`);
ok(c.lowerBound === true && c.lines[2].monthlyUsd === undefined, 'an unpriced component makes the total a lower bound');
ok(c.checked === '2026-10-27', 'checked date is the oldest price file date');

if (failures) {
  console.error(`${failures} stack-cost test(s) failed`);
  process.exit(1);
}
console.log('all stack-cost tests passed');
