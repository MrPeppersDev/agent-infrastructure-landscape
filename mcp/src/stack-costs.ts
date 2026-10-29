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
  /** Tokens sent to the embedding model per run (queries plus new content). */
  embeddingTokensPerRun: number;
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
  vectors: 1_000_000,
  embeddingTokensPerRun: 1000
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
 * the units the plan covers. A plan's own `overage` overrides the
 * service-wide one; `overage: null` on a plan means it is hard-capped. */
export interface MeteredPricing {
  id: string;
  system: string;
  unit: MeterUnit;
  source: string;
  plans: { name: string; usd: number; included: number; overage?: { per: number; usd: number } | null }[];
  /** Published overage beyond a plan's included units. */
  overage?: { per: number; usd: number } | null;
  /** Graduated per-unit rates over the month's total units, where the
   * vendor publishes them; used instead of the flat overage. The last
   * tier has `upTo: null`. */
  tiers?: { upTo: number | null; usdPerUnit: number }[];
  beyond: string;
  notes?: string;
}

/** A gateway that charges a percentage of the model spend routed through it. */
export interface GatewayFee {
  id: string;
  system: string;
  feePct: number;
  /** What the vendor says about bring-your-own-key usage. */
  byok?: string;
  source: string;
  notes?: string;
}

/** Per-token list price for one embedding model. */
export interface EmbeddingPrice {
  id: string;
  system: string;
  model: string;
  perMtok: number;
  dims?: number;
  source: string;
  notes?: string;
}

export interface StackPricing {
  checked: string;
  models: ModelPrice[];
  metered: MeteredPricing[];
  gatewayFees?: GatewayFee[];
  embeddings?: EmbeddingPrice[];
}

export interface CostLine {
  layer: string;
  id: string;
  name: string;
  /** priced: monthlyUsd is set; contact-sales: beyond published plans;
   * unpriced: the catalog has no published price for it. */
  status: 'priced' | 'contact-sales' | 'unpriced';
  monthlyUsd: number | null;
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
    else if (p.tiers && pl.overage !== null) {
      const extra = tiered(p.tiers, pl.included, units);
      options.push({ usd: pl.usd + extra, plan: pl.name, how: `${pl.name}: ${usd(pl.usd)} + ${num(units - pl.included)} over at the published graduated rates = ${usd(pl.usd + extra)}` });
    } else {
      const ov = pl.overage !== undefined ? pl.overage : p.overage;
      if (!ov) continue;
      const extra = Math.ceil((units - pl.included) / ov.per) * ov.usd;
      options.push({ usd: pl.usd + extra, plan: pl.name, how: `${pl.name}: ${usd(pl.usd)} + ${num(units - pl.included)} over × ${usd(ov.usd)} per ${num(ov.per)} = ${usd(pl.usd + extra)}` });
    }
  }
  if (!options.length) return { ...base, status: 'contact-sales', monthlyUsd: null, plan: p.beyond, working, caveat: 'Usage is beyond the largest published plan; the vendor quotes this privately.' };
  options.sort((a, b) => a.usd - b.usd);
  return { ...base, status: 'priced', monthlyUsd: cents(options[0].usd), plan: options[0].plan, working: [...working, options[0].how], caveat: p.notes ?? null };
}

/** Cost of the units between `included` and `units` at graduated rates. */
function tiered(tiers: { upTo: number | null; usdPerUnit: number }[], included: number, units: number): number {
  let total = 0;
  let from = 0;
  for (const t of tiers) {
    const to = t.upTo ?? Infinity;
    const lo = Math.max(from, included);
    const hi = Math.min(to, units);
    if (hi > lo) total += (hi - lo) * t.usdPerUnit;
    from = to;
    if (from >= units) break;
  }
  return total;
}

export function estimateEmbedding(e: EmbeddingPrice, w: StackWorkload): Omit<CostLine, 'layer'> {
  const mtok = (w.runsPerDay * DAYS * w.embeddingTokensPerRun) / 1e6;
  const total = mtok * e.perMtok;
  return {
    id: e.id,
    name: `${e.system} (${e.model})`,
    status: 'priced',
    monthlyUsd: cents(total),
    plan: `${e.model} list price`,
    working: [`${mtok.toFixed(1)}M tokens embedded a month × ${usd(e.perMtok)}/M = ${usd(total)}`],
    caveat: 'Ongoing embedding only; embedding an existing corpus once is extra.' + (e.notes ? ' ' + e.notes : ''),
    source: e.source
  };
}

export function estimateModel(m: ModelPrice, w: StackWorkload): Omit<CostLine, 'layer'> {
  const calls = w.runsPerDay * DAYS * w.llmCallsPerRun;
  const inM = (calls * w.inputTokensPerCall) / 1e6;
  const outM = (calls * w.outputTokensPerCall) / 1e6;
  const total = inM * m.inputPerMtok + outM * m.outputPerMtok;
  return {
    id: m.id,
    name: `${m.system} (${m.model})`,
    status: 'priced',
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
  const fees: { at: number; fee: GatewayFee; layer: string }[] = [];
  for (const c of components) {
    const model = pricing.stack.models.find((m) => m.id === c.id);
    const metered = pricing.stack.metered.find((m) => m.id === c.id);
    const fee = pricing.stack.gatewayFees?.find((f) => f.id === c.id);
    const embedding = pricing.stack.embeddings?.find((e) => e.id === c.id);
    if (fee) {
      // Priced once the model spend is known, below.
      fees.push({ at: lines.length, fee, layer: c.layer });
      lines.push({ layer: c.layer, id: c.id, name: fee.system, status: 'unpriced', monthlyUsd: null, plan: '', working: [], caveat: null, source: fee.source });
      continue;
    }
    if (embedding) {
      // The first entry is the vendor's default model; others are shown as alternatives.
      const line = estimateEmbedding(embedding, w);
      for (const alt of pricing.stack.embeddings!.filter((e) => e.id === c.id && e !== embedding)) {
        line.working.push(`With ${alt.model} instead: ${usd(estimateEmbedding(alt, w).monthlyUsd ?? 0)} a month`);
      }
      lines.push({ layer: c.layer, ...line });
      continue;
    }
    if (model) {
      // The first entry for a family is its flagship; show the others
      // (e.g. the cheapest current model) as alternatives in the working.
      const line = estimateModel(model, w);
      for (const alt of pricing.stack.models.filter((m) => m.id === c.id && m !== model)) {
        const e = estimateModel(alt, w);
        line.working.push(`With ${alt.model} instead: ${usd(e.monthlyUsd ?? 0)} a month`);
      }
      lines.push({ layer: c.layer, ...line });
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
        lines.push({ layer: c.layer, id: c.id, name: c.name, status: e.monthlyUsd === null ? 'contact-sales' : 'priced', monthlyUsd: e.monthlyUsd, plan: e.plan, working: e.working, caveat: e.caveat, source: e.source });
        continue;
      }
    }
    if (c.layer === 'vectors') {
      const v = pricing.vector.vendors.find((x) => key(x.system) === key(c.name));
      if (v) {
        const e = vectorEstimate(v, { ...DEFAULT_VECTOR_WORKLOAD, vectors: w.vectors, queriesPerMonth: w.runsPerDay * DAYS * Math.max(1, w.llmCallsPerRun / 2) });
        lines.push({ layer: c.layer, id: c.id, name: c.name, status: e.monthlyUsd === null ? 'contact-sales' : 'priced', monthlyUsd: e.monthlyUsd, plan: e.plan, working: e.working, caveat: e.caveat ?? (e.atLeast ? 'Some cost components have no published rate.' : null), source: e.source });
        continue;
      }
    }
    lines.push({ layer: c.layer, id: c.id, name: c.name, status: 'unpriced', monthlyUsd: null, plan: '', working: [], caveat: 'No published price in the catalog; self-hosted open source costs your own infrastructure.', source: null });
  }
  const modelSpend = lines.filter((l) => pricing.stack.models.some((m) => m.id === l.id)).reduce((s, l) => s + (l.monthlyUsd ?? 0), 0);
  for (const { at, fee } of fees) {
    const amount = (modelSpend * fee.feePct) / 100;
    lines[at] = {
      ...lines[at],
      status: modelSpend > 0 ? 'priced' : 'unpriced',
      monthlyUsd: modelSpend > 0 ? cents(amount) : null,
      plan: `${fee.feePct}% platform fee`,
      working: modelSpend > 0 ? [`${fee.feePct}% of ${usd(modelSpend)} model spend = ${usd(amount)}`] : [],
      caveat: [modelSpend > 0 ? null : 'The fee is a share of model spend, and no model in this stack has a published price.', fee.byok ? `Bring your own key: ${fee.byok}.` : null, fee.notes ?? null].filter(Boolean).join(' ') || null
    };
  }
  const known = lines.reduce((s, l) => s + (typeof l.monthlyUsd === 'number' ? l.monthlyUsd : 0), 0);
  return {
    workload: w,
    lines,
    knownMonthlyUsd: cents(known),
    lowerBound: lines.some((l) => l.status !== 'priced'),
    checked: [pricing.stack.checked, pricing.memory.checked, pricing.vector.checked].filter(Boolean).sort()[0] ?? ''
  };
}
