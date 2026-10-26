// Memory-layer cost estimator: published list prices (data/pricing/memory.json)
// applied to a workload (users × messages × size × retrievals).
//
// Honesty rules: only plans and rates the vendor publishes are used; usage
// beyond the largest published plan with no published overage is reported
// as "contact sales", never extrapolated; every result names its plan,
// shows the arithmetic, and links the pricing page with the date checked.
//
// Pure and dependency-free.

export interface Workload {
  users: number;
  /** Messages (turns written to memory) per user per month. */
  messagesPerUser: number;
  /** Average bytes per message written. */
  bytesPerMessage: number;
  /** Memory searches per message. */
  retrievalsPerMessage: number;
  /** Agents per user (for per-agent pricing). */
  agentsPerUser: number;
}

export const DEFAULT_WORKLOAD: Workload = { users: 1000, messagesPerUser: 60, bytesPerMessage: 600, retrievalsPerMessage: 1, agentsPerUser: 1 };

type Plan = Record<string, number | string | boolean | undefined> & { name: string; usd: number };
export interface VendorPricing {
  system: string;
  model: 'requests' | 'credits' | 'metered-credits' | 'tokens' | 'agents';
  source: string;
  plans: Plan[];
  beyond: string;
  notes?: string;
  credit_bytes?: number;
  rates?: Record<string, number>;
}

export interface Estimate {
  system: string;
  monthlyUsd: number | null;
  plan: string;
  /** Plain-words arithmetic. */
  working: string[];
  caveat: string | null;
  source: string;
}

const TOKENS_PER_BYTE = 0.25;
const fmt = (n: number) => (n >= 100 ? Math.round(n).toLocaleString('en-US') : n.toFixed(2).replace(/\.00$/, ''));
const num = (n: number) => Math.round(n).toLocaleString('en-US');

export function estimate(v: VendorPricing, w: Workload): Estimate {
  const msgs = w.users * w.messagesPerUser;
  const retrievals = msgs * w.retrievalsPerMessage;
  const tokens = msgs * w.bytesPerMessage * TOKENS_PER_BYTE;
  const base = { system: v.system, source: v.source };
  const over = (working: string[]): Estimate => ({ ...base, monthlyUsd: null, plan: v.beyond, working, caveat: 'Usage is beyond the largest published plan; the vendor quotes this privately.' });

  switch (v.model) {
    case 'requests': {
      const working = [`${num(msgs)} memory writes and ${num(retrievals)} searches a month`];
      const p = v.plans.find((p) => msgs <= Number(p.adds) && retrievals <= Number(p.retrievals));
      if (!p) return over(working);
      return { ...base, monthlyUsd: p.usd, plan: p.name, working: [...working, `${p.name} plan covers ${num(Number(p.adds))} writes and ${num(Number(p.retrievals))} searches`], caveat: null };
    }
    case 'credits': {
      const per = Math.max(1, Math.ceil(w.bytesPerMessage / (v.credit_bytes ?? 350)));
      const credits = msgs * per;
      const working = [`${num(msgs)} episodes × ${per} credit${per > 1 ? 's' : ''} (${w.bytesPerMessage} bytes ÷ ${v.credit_bytes} per credit) = ${num(credits)} credits`];
      let best: { usd: number; plan: Plan; extra: number } | null = null;
      for (const p of v.plans) {
        const inc = Number(p.credits);
        let usd = p.usd, extra = 0;
        if (credits > inc) {
          if (!p.topup_credits) continue;
          extra = Math.ceil((credits - inc) / Number(p.topup_credits));
          usd += extra * Number(p.topup_usd);
        }
        if (!best || usd < best.usd) best = { usd, plan: p, extra };
      }
      if (!best) return over(working);
      return {
        ...base, monthlyUsd: best.usd, plan: best.plan.name, caveat: null,
        working: [...working, `${best.plan.name}: $${best.plan.usd} incl. ${num(Number(best.plan.credits))} credits${best.extra ? ` + ${best.extra} top-up${best.extra > 1 ? 's' : ''} × $${best.plan.topup_usd}` : ''}`]
      };
    }
    case 'metered-credits': {
      const r = v.rates ?? {};
      const usage = (tokens / 1e6) * (r.memory_text_per_m_tokens ?? 0) + (retrievals / 1e6) * (r.search_per_m_queries ?? 0);
      const working = [`~${num(tokens)} tokens written × $${r.memory_text_per_m_tokens}/1M + ${num(retrievals)} searches × $${r.search_per_m_queries}/1M = $${fmt(usage)} of usage`];
      let best: { usd: number; plan: Plan } | null = null;
      for (const p of v.plans) {
        const credit = Number(p.credit_usd);
        if (usage > credit && !p.topup) continue;
        const usd = p.usd + Math.max(0, usage - credit);
        if (!best || usd < best.usd) best = { usd, plan: p };
      }
      if (!best) return over(working);
      return { ...base, monthlyUsd: Math.round(best.usd * 100) / 100, plan: best.plan.name, caveat: null, working: [...working, `${best.plan.name}: $${best.plan.usd} incl. $${best.plan.credit_usd} credit${best.usd > best.plan.usd ? `, + $${fmt(best.usd - best.plan.usd)} extra credits` : ''}`] };
    }
    case 'tokens': {
      const free = v.plans.find((p) => p.tokens !== undefined);
      const paid = v.plans.find((p) => p.per_m_tokens !== undefined);
      const working = [`~${num(tokens)} tokens a month (${w.bytesPerMessage} bytes per message ≈ ${Math.round(w.bytesPerMessage * TOKENS_PER_BYTE)} tokens)`];
      if (free && tokens <= Number(free.tokens)) return { ...base, monthlyUsd: 0, plan: free.name, caveat: null, working: [...working, `${free.name} plan includes ${num(Number(free.tokens))} tokens`] };
      if (!paid) return over(working);
      const usd = (tokens / 1e6) * Number(paid.per_m_tokens);
      return { ...base, monthlyUsd: Math.round(usd * 100) / 100, plan: paid.name, caveat: 'One workspace assumed; a published per-token rate is applied to all tokens.', working: [...working, `${paid.name}: $${paid.per_m_tokens} per 1M tokens`] };
    }
    case 'agents': {
      const agents = w.users * w.agentsPerUser;
      const working = [`${num(agents)} agents (${w.agentsPerUser} per user)`];
      const flat = v.plans.find((p) => p.agents !== undefined && agents <= Number(p.agents));
      if (flat) return { ...base, monthlyUsd: flat.usd, plan: flat.name, caveat: null, working: [...working, `${flat.name} plan allows ${p(flat.agents)} agents`] };
      const per = v.plans.find((p) => p.per_active_agent !== undefined);
      if (!per) return over(working);
      return {
        ...base, monthlyUsd: Math.round(agents * Number(per.per_active_agent) * 100) / 100, plan: per.name,
        caveat: 'Plus LLM and tool-execution usage, which the vendor bills separately and this doesn\'t estimate.',
        working: [...working, `${per.name}: $${per.per_active_agent} per active agent`]
      };
    }
  }
}

function p(x: unknown): string {
  return num(Number(x));
}

export function estimateAll(vendors: VendorPricing[], w: Workload): Estimate[] {
  return vendors
    .map((v) => estimate(v, w))
    .sort((a, b) => (a.monthlyUsd ?? Infinity) - (b.monthlyUsd ?? Infinity) || a.system.localeCompare(b.system));
}
