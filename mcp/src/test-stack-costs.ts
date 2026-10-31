// Tests for stack-costs.ts with fixed fixture prices (not the live price
// file), so the arithmetic is checked exactly.
// Run: npm run build && node dist/test-stack-costs.js
import { estimateEmbedding, estimateMetered, estimateModel, monthlyUnits, stackCost, DEFAULT_STACK_WORKLOAD, type MeteredPricing, type StackPricing } from './stack-costs.js';

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

// per-plan overage: a hard-capped free plan can't take overage; a plan's own rate wins
const capped = estimateMetered({ ...obs, plans: [{ name: 'Free', usd: 0, included: 1000, overage: null }, { name: 'Pro', usd: 50, included: 10000 }] }, w);
ok(capped.monthlyUsd === 50 && capped.plan === 'Pro', `a hard-capped free plan is skipped (got ${capped.monthlyUsd} ${capped.plan})`);
const own = estimateMetered({ ...obs, plans: [{ name: 'Free', usd: 0, included: 1000, overage: { per: 1000, usd: 1 } }, { name: 'Pro', usd: 50, included: 10000 }] }, w);
ok(own.monthlyUsd === 2 && own.plan === 'Free', `a plan's own overage rate is used (got ${own.monthlyUsd})`);

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
ok(c.lowerBound === true && c.lines[2].status === 'unpriced', 'an unpriced component makes the total a lower bound');
ok(c.checked === '2026-10-27', 'checked date is the oldest price file date');

// graduated tiers: 15,000 requests on a plan including 10k; tiers 0–10k free, 10k–12k $0.01, then $0.001
const tieredObs: MeteredPricing = {
  id: 't', system: 'Tiered', unit: 'llm-requests', source: 'https://t/pricing',
  plans: [{ name: 'Hobby', usd: 0, included: 10000, overage: null }, { name: 'Pro', usd: 20, included: 10000 }],
  overage: null, tiers: [{ upTo: 10000, usdPerUnit: 0 }, { upTo: 12000, usdPerUnit: 0.01 }, { upTo: null, usdPerUnit: 0.001 }], beyond: 'Enterprise'
};
const t1 = estimateMetered(tieredObs, w);
ok(t1.monthlyUsd === 20 + 2000 * 0.01 + 3000 * 0.001 && t1.plan === 'Pro', `graduated tiers on the uncapped plan (got ${t1.monthlyUsd} ${t1.plan})`);

// embeddings: 3,000 runs × 1,000 tokens = 3M tokens × $0.02
const emb = estimateEmbedding({ id: 'e', system: 'E', model: 'small', perMtok: 0.02, source: 'https://e' }, { ...w, embeddingTokensPerRun: 1000 });
ok(emb.monthlyUsd === 0.06, `embedding cost = 3M × $0.02 (got ${emb.monthlyUsd})`);

// gateway fee: a share of the stack's priced model spend, wherever the gateway sits
const withFee = stackCost([
  { layer: 'gateway', id: 'gw', name: 'GW' },
  { layer: 'model', id: 'model-a', name: 'V' },
  { layer: 'embeddings', id: 'e', name: 'E' }
], { ...pricing, stack: { ...pricing.stack, gatewayFees: [{ id: 'gw', system: 'GW', feePct: 5, source: 'https://gw' }], embeddings: [{ id: 'e', system: 'E', model: 'small', perMtok: 0.02, source: 'https://e' }] } }, { ...w, embeddingTokensPerRun: 1000 });
ok(withFee.lines[0].monthlyUsd === 10.13 && withFee.lines[0].status === 'priced', `gateway fee = 5% of $202.50 (got ${withFee.lines[0].monthlyUsd})`);
ok(withFee.lines[2].monthlyUsd === 0.06, 'embedding line priced');
const feeOnly = stackCost([{ layer: 'gateway', id: 'gw', name: 'GW' }], { ...pricing, stack: { ...pricing.stack, gatewayFees: [{ id: 'gw', system: 'GW', feePct: 5, source: 'https://gw' }] } }, w);
ok(feeOnly.lines[0].status === 'unpriced' && feeOnly.lowerBound, 'a fee with no priced model spend stays unpriced');

// self-hosting estimates and the range (#362): unpriced lines get a low–high
// estimate from the assumptions table; contact-sales lines stay outside.
const selfHost = {
  checked: '2026-10-31', note: 'test assumptions',
  instances: { small: { label: 'S', usdPerHour: 0.1, source: 'https://i/s', confidence: 'medium' as const }, big: { label: 'B', usdPerHour: 1, source: 'https://i/b', confidence: 'high' as const } },
  layers: { framework: { low: null, high: null, note: 'library' }, memory: { low: 'small', high: 'big', note: 'one instance' } }
};
const ranged = stackCost([
  { layer: 'model', id: 'model-a', name: 'V' },
  { layer: 'framework', id: 'lib', name: 'Lib' },
  { layer: 'memory', id: 'mem', name: 'Mem' },
  { layer: 'observability', id: 'o', name: 'Obs' }
], { ...pricing, stack: { ...pricing.stack, selfHost, metered: [{ ...obs, plans: [{ name: 'Free', usd: 0, included: 10 }], overage: null }] } }, w);
const memLine = ranged.lines.find((l) => l.id === 'mem')!;
ok(memLine.estimate?.lowUsd === 73 && memLine.estimate?.highUsd === 730, `memory estimate = 0.1×730 to 1×730 (got ${JSON.stringify(memLine.estimate)})`);
ok(ranged.lines.find((l) => l.id === 'lib')?.estimate?.highUsd === 0, 'a library layer estimates to zero');
ok(ranged.range?.lowUsd === 202.5 + 73 && ranged.range?.highUsd === 202.5 + 730, `range = priced + estimates (got ${ranged.range?.lowUsd}–${ranged.range?.highUsd})`);
ok(ranged.range?.unquotedLines === 1 && ranged.range?.estimatedLines === 2 && ranged.range?.pricedLines === 1, `range counts priced, estimated and contact-sales lines (got ${JSON.stringify([ranged.range?.pricedLines, ranged.range?.estimatedLines, ranged.range?.unquotedLines])})`);
ok(ranged.knownMonthlyUsd === 202.5, 'estimates never enter the published-price total');
ok(stackCost([{ layer: 'memory', id: 'mem', name: 'Mem' }], pricing, w).range === null, 'no assumptions table → no range');

if (failures) {
  console.error(`${failures} stack-cost test(s) failed`);
  process.exit(1);
}
console.log('all stack-cost tests passed');
