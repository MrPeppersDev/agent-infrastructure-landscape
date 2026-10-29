// Whole-stack cost estimate: published list prices (data/pricing/stack.json
// for models and metered services, plus data/pricing/memory.json and
// vector.json) applied to one agent workload, for the components a stack
// plan picked.
//
// Same honesty rules as costs.ts and vector-costs.ts:
//   * only plans and rates the vendor publishes are used, each with its
//     source page and the date it was checked;
//   * usage beyond the largest published plan with no published overage is
//     "contact sales" (null), never extrapolated;
//   * a component with no catalogued price is listed as unpriced, and the
//     total says it is a lower bound;
//   * every line shows its arithmetic.
//
// Pure and dependency-free apart from its sibling cost modules.

import { estimate as memoryEstimate, type VendorPricing } from './costs.js';
import { vectorEstimate, DEFAULT_VECTOR_WORKLOAD, type VectorPricing } from './vector-costs.js';

export interface StackWorkload {
  /** Agent runs (conversations / tasks) per day. */
  runsPerDay: number;
  /** Model calls per run. */
  llmCallsPerRun: number;
  inputTokensPerCall: number;
  outputTokensPerCall: number;
  /** Tool calls per run (through the tools layer). */
  toolCallsPerRun: number;
  /** Monthly active end users. */
  users: number;
  /** Sandbox minutes per run (code execution). */
  sandboxMinutesPerRun: number;
  /** Browser-session minutes per run. */
  browserMinutesPerRun: number;
  /** Voice minutes per run. */
  voiceMinutesPerRun: number;
  /** Vectors kept in the vector store. */
  vectors: number;
}

export const DEFAULT_STACK_WORKLOAD: StackWorkload = {
  runsPerDay: 1000,
  llmCallsPerRun: 6,
  inputTokensPerCall: 3000,
  outputTokensPerCall: 400,
  toolCallsPerRun: 4,
  users: 1000,
  sandboxMinutesPerRun: 0,
  browserMinutesPerRun: 0,
  voiceMinutesPerRun: 0,
  vectors: 1_000_000
};

/** Per-token list price for one model in a family row. */
export interface ModelPrice {
  /** Catalog record id of the model family. */
  id: string;
  system: string;
  model: string;
  inputPerMtok: number;
  outputPerMtok: number;
  source: string;
}

export type MeterUnit = 'traces' | 'spans' | 'llm-requests' | 'tool-calls' | 'sandbox-minutes' | 'browser-minutes' | 'voice-minutes' | 'users';

/** A service billed by one metered unit. Plans are monthly; `included` is
 * the units the plan covers. */
export interface MeteredPricing {
  id: string;
  system: string;
  unit: MeterUnit;
  source: string;
  plans: { name: string; usd: number; included: number }[];
  /** Published overage beyond a plan's included units. */
  overage?: { per: number; usd: number } | null;
  beyond: string;
  notes?: string;
}

export interface StackPricing {
  checked: string;
  models: ModelPrice[];
  metered: MeteredPricing[];
}

export interface CostLine {
  layer: string;
  id: string;
  name: string;
  /** null = contact sales / beyond published plans; undefined = no catalogued price. */
  monthlyUsd: number | null | undefined;
  plan: string;
  working: string[];
  caveat: string | null;
  source: string | null;
}

export interface StackCost {
  workload: StackWorkload;
  lines: CostLine[];
  /** Sum of the lines with a number. */
  knownMonthlyUsd: number;
  /** True when some layer has no price or needs a sales quote. */
  lowerBound: boolean;
  checked: string;
}

const num = (n: number) => Math.round(n).toLocaleString('en-US');
const usd = (n: number) => `$${n >= 100 ? Math.round(n).toLocaleString('en-US') : n.toFixed(2)}`;
const cents = (n: number) => Math.round(n * 100) / 100;
const DAYS = 30;

export function monthlyUnits(unit: MeterUnit, w: StackWorkload): number {
  const runs = w.runsPerDay * DAYS;
  switch (unit) {
    case 'traces': return runs;
    case 'spans': return runs * (w.llmCallsPerRun + w.toolCallsPerRun);
    case 'llm-requests': return runs * w.llmCallsPerRun;
    case 'tool-calls': return runs * w.toolCallsPerRun;
    case 'sandbox-minutes': return runs * w.sandboxMinutesPerRun;
    case 'browser-minutes': return runs * w.browserMinutesPerRun;
    case 'voice-minutes': return runs * w.voiceMinutesPerRun;
    case 'users': return w.users;
  }
}

const UNIT_LABEL: Record<MeterUnit, string> = {
  traces: 'traces', spans: 'spans', 'llm-requests': 'model requests', 'tool-calls': 'tool calls',
  'sandbox-minutes': 'sandbox minutes', 'browser-minutes': 'browser minutes', 'voice-minutes': 'voice minutes', users: 'monthly active users'
};

/** Cheapest published plan that covers the usage, with published overage
 * where it is cheaper than moving up a plan. */
export function estimateMetered(p: MeteredPricing, w: StackWorkload): Omit<CostLine, 'layer'> {
  const units = monthlyUnits(p.unit, w);
  const working = [`${num(units)} ${UNIT_LABEL[p.unit]} a month`];
  const base = { id: p.id, name: p.system, source: p.source };
  const options: { usd: number; plan: string; how: string }[] = [];
  for (const pl of p.plans) {
    if (units <= pl.included) options.push({ usd: pl.usd, plan: pl.name, how: `${pl.name}: ${usd(pl.usd)} includes ${num(pl.included)}` });
    else if (p.overage) {
      const extra = Math.ceil((units - pl.included) / p.overage.per) * p.overage.usd;
      options.push({ usd: pl.usd + extra, plan: pl.name, how: `${pl.name}: ${usd(pl.usd)} + ${num(units - pl.included)} over × ${usd(p.overage.usd)} per ${num(p.overage.per)} = ${usd(pl.usd + extra)}` });
    }
  }
  if (!options.length) return { ...base, monthlyUsd: null, plan: p.beyond, working, caveat: 'Usage is beyond the largest published plan; the vendor quotes this privately.' };
  options.sort((a, b) => a.usd - b.usd);
  return { ...base, monthlyUsd: cents(options[0].usd), plan: options[0].plan, working: [...working, options[0].how], caveat: p.notes ?? null };
}

export function estimateModel(m: ModelPrice, w: StackWorkload): Omit<CostLine, 'layer'> {
  const calls = w.runsPerDay * DAYS * w.llmCallsPerRun;
  const inM = (calls * w.inputTokensPerCall) / 1e6;
  const outM = (calls * w.outputTokensPerCall) / 1e6;
  const total = inM * m.inputPerMtok + outM * m.outputPerMtok;
  return {
    id: m.id,
    name: `${m.system} (${m.model})`,
    monthlyUsd: cents(total),
    plan: `${m.model} list price`,
    working: [
      `${num(calls)} model calls a month`,
      `${inM.toFixed(1)}M input tokens × ${usd(m.inputPerMtok)}/M + ${outM.toFixed(1)}M output tokens × ${usd(m.outputPerMtok)}/M = ${usd(total)}`
    ],
    caveat: 'Before prompt caching or batch discounts.',
    source: m.source
  };
}

/** Lower-case first word of a name, for matching price-file vendors to
 * catalog records ("Zep & Graphiti" ↔ "Zep"). */
const key = (s: string) => (s.toLowerCase().match(/[a-z0-9]+/) ?? [''])[0];

export function stackCost(
  components: { layer: string; id: string; name: string }[],
  pricing: { stack: StackPricing; memory: { checked: string; vendors: VendorPricing[] }; vector: { checked: string; vendors: VectorPricing[] } },
  w: StackWorkload = DEFAULT_STACK_WORKLOAD
): StackCost {
  const lines: CostLine[] = [];
  for (const c of components) {
    const model = pricing.stack.models.find((m) => m.id === c.id);
    const metered = pricing.stack.metered.find((m) => m.id === c.id);
    if (model) {
      lines.push({ layer: c.layer, ...estimateModel(model, w) });
      continue;
    }
    if (metered) {
      lines.push({ layer: c.layer, ...estimateMetered(metered, w) });
      continue;
    }
    if (c.layer === 'memory') {
      const v = pricing.memory.vendors.find((x) => key(x.system) === key(c.name));
      if (v) {
        const e = memoryEstimate(v, { users: w.users, messagesPerUser: Math.round((w.runsPerDay * DAYS) / Math.max(1, w.users)) * 2, bytesPerMessage: 600, retrievalsPerMessage: 1, agentsPerUser: 1 });
        lines.push({ layer: c.layer, id: c.id, name: c.name, monthlyUsd: e.monthlyUsd, plan: e.plan, working: e.working, caveat: e.caveat, source: e.source });
        continue;
      }
    }
    if (c.layer === 'vectors') {
      const v = pricing.vector.vendors.find((x) => key(x.system) === key(c.name));
      if (v) {
        const e = vectorEstimate(v, { ...DEFAULT_VECTOR_WORKLOAD, vectors: w.vectors, queriesPerMonth: w.runsPerDay * DAYS * Math.max(1, w.llmCallsPerRun / 2) });
        lines.push({ layer: c.layer, id: c.id, name: c.name, monthlyUsd: e.monthlyUsd, plan: e.plan, working: e.working, caveat: e.caveat ?? (e.atLeast ? 'Some cost components have no published rate.' : null), source: e.source });
        continue;
      }
    }
    lines.push({ layer: c.layer, id: c.id, name: c.name, monthlyUsd: undefined, plan: '', working: [], caveat: 'No published price in the catalog; self-hosted open source costs your own infrastructure.', source: null });
  }
  const known = lines.reduce((s, l) => s + (typeof l.monthlyUsd === 'number' ? l.monthlyUsd : 0), 0);
  return {
    workload: w,
    lines,
    knownMonthlyUsd: cents(known),
    lowerBound: lines.some((l) => typeof l.monthlyUsd !== 'number'),
    checked: [pricing.stack.checked, pricing.memory.checked, pricing.vector.checked].filter(Boolean).sort()[0] ?? ''
  };
}
