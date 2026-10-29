// Whole-stack composer (/build, MCP `plan_stack`, CLI `landscape stack`):
// turn one set of answers about the product into one pick per layer of an
// agent stack, then check the picks against each other.
//
// Same honesty rules as the single-layer choosers (chooser.ts,
// chooser-infra.ts):
//   * Every reason is a catalogued cell value or edge with its citation.
//   * A must-have counts as met only when a cell confirms it.
//   * Archived / deprecated / shut-down systems are never picked.
//   * A pair of picks with no recorded integration is "not recorded",
//     never "incompatible".
//   * The risk score only adds up cited facts; nothing is a judgement call.
//   * Compliance must-haves count only when the vendor's published
//     attestations (compliance-certifications cell) confirm them.
//
// Pure and dependency-free apart from its sibling modules.

import { brand, POOLS, type ChooserItem, type Fact, type Reason, type Scored, type Tri, type Hosting, type RecordLike } from './chooser.js';
import { scoreInfraDetailed, FW_SECTIONS, NOT_A_FRAMEWORK, type Language, type InfraAnswers, type Exclusion } from './chooser-infra.js';
import { compatibility, type CompatEdge, type CompatEvidence } from './compat.js';

// ---------------------------------------------------------------------------
// Layers and product presets
// ---------------------------------------------------------------------------

export type LayerId =
  | 'model' | 'serving' | 'gateway' | 'framework' | 'orchestration' | 'memory' | 'vectors' | 'graph' | 'embeddings'
  | 'tools' | 'sandbox' | 'browser' | 'voice' | 'observability' | 'guardrails';

export interface Layer {
  id: LayerId;
  label: string;
  /** What the layer does in an agent stack (shown as help text). */
  role: string;
  sections: string[];
  /** Matched against the type label and name; with `matchDesc`, the
   * description too (for layers whose rows sit in mixed sections). */
  match?: RegExp;
  matchDesc?: boolean;
  exclude?: RegExp;
  /** The language requirement applies (the layer is used through an SDK). */
  sdk: boolean;
  /** The MCP requirement applies. */
  mcp: boolean;
  /** A library you embed rather than a service, so "managed" doesn't apply. */
  library: boolean;
}

/** Sections that don't exist yet are harmless: the layer simply draws from
 * the ones that do. New sections from the thin-layer intake slot in here. */
export const LAYERS: Layer[] = [
  { id: 'framework', label: 'Agent framework', role: 'Defines agents, tool calls and control flow in code.', sections: FW_SECTIONS, exclude: NOT_A_FRAMEWORK, sdk: true, mcp: true, library: true },
  { id: 'model', label: 'Foundation model', role: 'The LLM the agents reason with.', sections: ['Foundation models (substrate reference)'], sdk: false, mcp: false, library: false },
  { id: 'serving', label: 'Model serving', role: 'Runs open-weight models on your own GPUs or a GPU cloud.', sections: ['Inference platforms & gateways'], match: /inference|serving|runtime|GPU|compiler|serverless/i, exclude: /gateway|proxy|router|universal llm api|multi-provider/i, sdk: false, mcp: false, library: false },
  { id: 'gateway', label: 'Model gateway', role: 'One API in front of every model: routing, fallbacks, caching, budgets and rate limits.', sections: ['Inference platforms & gateways'], match: /gateway|proxy|router|universal llm api|multi-provider/i, sdk: false, mcp: false, library: false },
  { id: 'orchestration', label: 'Durable execution', role: 'Keeps long-running and multi-agent workflows alive across failures and restarts.', sections: [...FW_SECTIONS, 'Durable execution & workflow engines'], match: /durable|workflow|long-running|jobs|event-driven|orchestrat/i, sdk: true, mcp: false, library: true },
  { id: 'memory', label: 'Memory layer', role: 'Remembers users, facts and past sessions across conversations.', sections: POOLS.app, sdk: true, mcp: true, library: false },
  { id: 'vectors', label: 'Vector store', role: 'Stores embeddings for retrieval (RAG) and semantic search.', sections: ['Vector-database infrastructure', 'Search platforms (non-memory)'], sdk: true, mcp: false, library: false },
  { id: 'graph', label: 'Knowledge graph', role: 'Stores entities and relationships for graph retrieval.', sections: ['Knowledge-graph platforms'], sdk: true, mcp: false, library: false },
  { id: 'embeddings', label: 'Embeddings / reranker', role: 'Turns text into vectors and reranks retrieved results.', sections: ['Embedding & reranker services'], sdk: false, mcp: false, library: false },
  { id: 'tools', label: 'Tools, auth and MCP', role: 'Gives agents authenticated access to external apps and APIs, scoped per user.', sections: [...FW_SECTIONS, 'Agent identity & auth', 'MCP gateways & registries'], match: /tools?\b.*\bauth|OAuth|tool\/auth|integrations? platform|identity|MCP (gateway|registry|server)|connector/i, sdk: true, mcp: true, library: false },
  { id: 'sandbox', label: 'Code sandbox', role: 'Runs agent-generated code in isolation.', sections: ['AI sandbox & runtime environments'], sdk: true, mcp: false, library: false },
  { id: 'browser', label: 'Browser / computer use', role: 'Lets agents browse the web or operate a desktop.', sections: ['Browser-agent memory', 'Computer-use & desktop agents'], match: /browser|headless|computer[- ]use|desktop|web agent/i, matchDesc: true, sdk: true, mcp: false, library: false },
  { id: 'voice', label: 'Voice runtime', role: 'Real-time speech in and out: transport, STT, TTS, turn-taking.', sections: ['Voice agent platforms'], sdk: true, mcp: false, library: false },
  { id: 'observability', label: 'Evals & observability', role: 'Traces every step, runs evaluations, catches regressions.', sections: ['Evaluation & observability platforms', 'Memory observability & monitoring'], sdk: true, mcp: false, library: false },
  { id: 'guardrails', label: 'Guardrails & security', role: 'Screens inputs and outputs for prompt injection, data leaks and unsafe actions.', sections: ['Guardrails & AI security', 'Memory governance, privacy & safety', 'Use-case-specific agent harnesses'], match: /guardrail|prompt[- ]injection|jailbreak|red[- ]team|\bPII\b|redact|firewall|AI security|LLM security|safety|vulnerab/i, matchDesc: true, sdk: false, mcp: false, library: false }
];

export const LAYER_BY_ID: Record<LayerId, Layer> = Object.fromEntries(LAYERS.map((l) => [l.id, l])) as Record<LayerId, Layer>;

export type ProductType = 'support-agent' | 'coding-agent' | 'research-agent' | 'voice-agent' | 'multi-agent-workflow' | 'rag-copilot';

export interface ProductPreset {
  label: string;
  layers: LayerId[];
  /** Memory pool: an app that remembers users, or a coding agent's memory. */
  memory: 'app' | 'coding';
  /** Benchmarks worth running for this kind of product (matched by name). */
  benchmarks: RegExp;
}

export const PRODUCTS: Record<ProductType, ProductPreset> = {
  'support-agent': { label: 'Customer-support agent', layers: ['framework', 'model', 'gateway', 'memory', 'vectors', 'embeddings', 'tools', 'observability', 'guardrails'], memory: 'app', benchmarks: /longmemeval|locomo|tau[- ]?bench|τ-bench/i },
  'coding-agent': { label: 'Coding agent', layers: ['framework', 'model', 'gateway', 'memory', 'sandbox', 'tools', 'observability', 'guardrails'], memory: 'coding', benchmarks: /swe[- ]?bench|terminal[- ]?bench|humaneval|osworld/i },
  'research-agent': { label: 'Research agent', layers: ['framework', 'model', 'gateway', 'browser', 'vectors', 'embeddings', 'memory', 'observability', 'guardrails'], memory: 'app', benchmarks: /webarena|mind2web|\bgaia\b|browsecomp|webvoyager|osworld/i },
  'voice-agent': { label: 'Voice agent', layers: ['voice', 'model', 'framework', 'memory', 'tools', 'observability', 'guardrails'], memory: 'app', benchmarks: /longmemeval|locomo|tau[- ]?bench|τ-bench/i },
  'multi-agent-workflow': { label: 'Multi-agent workflow', layers: ['framework', 'model', 'gateway', 'orchestration', 'memory', 'tools', 'sandbox', 'observability', 'guardrails'], memory: 'app', benchmarks: /tau[- ]?bench|τ-bench|\bgaia\b|agentbench|memoryarena|memoryagentbench/i },
  'rag-copilot': { label: 'RAG copilot', layers: ['framework', 'model', 'gateway', 'vectors', 'embeddings', 'memory', 'observability', 'guardrails'], memory: 'app', benchmarks: /longmemeval|locomo|beir|mteb|ragas/i }
};

/** Picking order: anchors first, so later layers can prefer what works
 * with them. */
const ORDER: LayerId[] = ['framework', 'voice', 'model', 'serving', 'gateway', 'orchestration', 'memory', 'vectors', 'graph', 'embeddings', 'tools', 'sandbox', 'browser', 'observability', 'guardrails'];

export interface StackAnswers {
  product: ProductType;
  language: Language;
  hosting: Hosting;
  oss: boolean;
  mcp: boolean;
  /** Replace the preset's layers. */
  layers?: LayerId[];
  /** Add layers to the preset (e.g. voice for a support agent). */
  add?: LayerId[];
  /** Pin a choice for a layer: layer → record id. */
  pin?: Partial<Record<LayerId, string>>;
  /** Never pick these record ids. */
  avoid?: string[];
  /** Attestations every hosted service in the stack must publish, as codes
   * from docs/schema/compliance-certifications.json (e.g. soc2-type2, hipaa).
   * Libraries you run yourself are exempt. */
  compliance?: string[];
}

export const DEFAULT_STACK: StackAnswers = { product: 'support-agent', language: 'any', hosting: 'any', oss: false, mcp: false };

// ---------------------------------------------------------------------------
// Result types
// ---------------------------------------------------------------------------

export interface WhyNot {
  id: string;
  name: string;
  /** Plain statements, each backed by a cell or the score breakdown. */
  because: Reason[];
}

export interface ExitPath {
  selfHost: { tri: Tri; fact: Fact };
  openSource: { tri: Tri; fact: Fact };
  /** The best-ranked other option that you could run yourself. */
  fallback: { id: string; name: string } | null;
  /** Official migration guidance, when the catalog has it. */
  migration: { summary: string; sources: string[] } | null;
}

export interface LayerResult {
  layer: LayerId;
  label: string;
  role: string;
  pick: (Scored & { pinned?: boolean }) | null;
  /** True when every candidate left has a must-have the catalog can't confirm. */
  pickUnconfirmed: boolean;
  whyNot: WhyNot[];
  exit: ExitPath | null;
  poolSize: number;
  excludedCount: number;
}

export interface PairResult {
  a: string;
  b: string;
  status: 'documented' | 'mentioned' | 'not-recorded';
  evidence: CompatEvidence[];
}

export interface RiskFactor {
  factor: 'lifecycle' | 'maturity' | 'vendor-concentration' | 'bus-factor' | 'licence' | 'unrecorded-integration' | 'unconfirmed' | 'gap';
  points: number;
  detail: string;
  citation?: string | null;
}

export interface SecurityItem {
  id: string;
  risk: string;
  /** addressed: the stack has a component aimed at this risk (not a
   * guarantee it's mitigated); gap: no such component; practice: no
   * component covers it on its own — it's a process to follow. */
  status: 'addressed' | 'gap' | 'practice';
  by: string[];
  note: string;
}

export interface StackPlan {
  answers: StackAnswers;
  product: string;
  layers: LayerResult[];
  pairs: PairResult[];
  risk: { score: number; level: 'low' | 'medium' | 'high'; factors: RiskFactor[] };
  security: { source: string; items: SecurityItem[] };
  evals: { observability: { id: string; name: string } | null; benchmarks: { id: string; name: string; url: string | null }[] };
  stackYaml: string;
}

export interface ComposerContext {
  items: ChooserItem[];
  records: RecordLike[];
  edges: CompatEdge[];
  migrations?: Map<string, { summary: string; sources: string[] }>;
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

function inLayer(i: ChooserItem, l: Layer, memory: 'app' | 'coding'): boolean {
  const sections = l.id === 'memory' ? POOLS[memory] : l.sections;
  if (!sections.includes(i.section)) return false;
  const label = `${i.type} ${i.name}`;
  if (l.match && !l.match.test(l.matchDesc ? `${label} ${i.desc}` : label)) return false;
  if (l.exclude && l.exclude.test(label)) return false;
  return true;
}

function layerAnswers(l: Layer, a: StackAnswers): InfraAnswers {
  return {
    kind: 'framework',
    need: '',
    language: l.sdk ? a.language : 'any',
    hosting: l.library && a.hosting === 'managed' ? 'any' : a.hosting,
    oss: a.oss,
    mcp: l.mcp && a.mcp,
    existing: false
  };
}

const HARD = ['Self-hostable', 'Managed service', 'Open source', 'MCP', 'Python SDK', 'TypeScript / JavaScript SDK', 'Compliance'];

/** Does the item publish every required attestation? From the
 * compliance-certifications cell only. */
function complianceTri(i: ChooserItem, need: string[]): Tri {
  const v = i.facts.compliance?.value ?? '';
  if (!v) return 'unknown';
  const have = new Set(v.split(','));
  return need.every((c) => have.has(c)) ? 'yes' : 'no';
}
const category = (r: Reason) => r.text.split(':')[0];

function pairEvidence(ctx: ComposerContext, byId: Map<string, RecordLike>, a: string, b: string): PairResult {
  const ra = byId.get(a);
  const rb = byId.get(b);
  if (!ra || !rb) return { a, b, status: 'not-recorded', evidence: [] };
  const p = compatibility([ra, rb], ctx.edges, [a, b]).pairs[0];
  return p ? { a, b, status: p.status, evidence: p.evidence } : { a, b, status: 'not-recorded', evidence: [] };
}

function evidenceReason(withName: string, p: PairResult): Reason {
  const e = p.evidence[0];
  const text = e ? (e.kind === 'edge' ? e.text : `${e.cell}: ${e.text}`) : '';
  return { text: `Works with ${withName}${text ? ': ' + text : ''}`, citation: e?.citation ?? null };
}

function participants(r: RecordLike | undefined): { n: number | null; citation: string | null } {
  const c = ((r?.cells ?? {}) as Record<string, { value?: string; citation?: string | null; status?: string }>)['developer-activity-opendigger'];
  if (!c || c.status !== 'real-data' || !c.value) return { n: null, citation: null };
  try {
    const v = JSON.parse(c.value) as { participants?: number | null };
    return { n: typeof v.participants === 'number' ? v.participants : null, citation: c.citation ?? null };
  } catch {
    return { n: null, citation: null };
  }
}

const SOURCE_AVAILABLE = /\b(BSL|business source|FSL|functional source|SSPL|elastic licen[cs]e|ELv2|polyform|commons clause|source[- ]available)\b/i;
const RELICENSED = /\b(relicens|changed (its |the )?licen[cs]e|moved (from|to) .{0,30}licen[cs]e|licen[cs]e change)/i;

// ---------------------------------------------------------------------------
// Compose
// ---------------------------------------------------------------------------

export function planStack(ctx: ComposerContext, answers: StackAnswers): StackPlan {
  const a: StackAnswers = { ...DEFAULT_STACK, ...answers };
  const preset = PRODUCTS[a.product] ?? PRODUCTS['support-agent'];
  // Self-hosting the whole stack means serving the model yourself too.
  const auto: LayerId[] = a.hosting === 'self' && !a.layers ? ['serving'] : [];
  const wanted = new Set<LayerId>([...(a.layers ?? preset.layers), ...(a.add ?? []), ...auto].filter((l) => l in LAYER_BY_ID));
  const avoid = new Set(a.avoid ?? []);
  const recById = new Map(ctx.records.map((r) => [r.id, r]));
  const itemById = new Map(ctx.items.map((i) => [i.id, i]));

  const picked: { layer: LayerId; item: ChooserItem }[] = [];
  const results: LayerResult[] = [];

  for (const lid of ORDER) {
    if (!wanted.has(lid)) continue;
    const l = LAYER_BY_ID[lid];
    const la = layerAnswers(l, a);
    const pool = ctx.items.filter((i) => inLayer(i, l, preset.memory) && !avoid.has(i.id));
    const ok: Scored[] = [];
    const maybe: Scored[] = [];
    const excluded: { item: ChooserItem; why: Exclusion }[] = [];
    for (const i of pool) {
      const r = scoreInfraDetailed(i, la);
      if ('excluded' in r) {
        excluded.push({ item: i, why: r });
        continue;
      }
      if (a.compliance?.length && !l.library) {
        const c = complianceTri(i, a.compliance);
        if (c === 'no') {
          excluded.push({ item: i, why: { excluded: `doesn't publish ${a.compliance.join(', ')}`, fact: i.facts.compliance } });
          continue;
        }
        if (c === 'unknown') r.unconfirmed.push('Compliance');
        else r.reasons.unshift({ text: `Compliance: ${i.facts.compliance.value}`, citation: i.facts.compliance.citation });
      }
      if (/^(alpha|preview)$/.test(i.facts.maturity?.value ?? '')) r.score = Math.round((r.score - 0.5) * 10) / 10;
      // Prefer what works with the layers already chosen.
      for (const p of picked) {
        if (p.item.id === i.id) continue;
        const pe = pairEvidence(ctx, recById, i.id, p.item.id);
        if (pe.status === 'documented') {
          r.score = Math.round((r.score + 1.5) * 10) / 10;
          r.reasons.unshift(evidenceReason(p.item.name, pe));
        } else if (pe.status === 'mentioned') {
          r.score = Math.round((r.score + 0.5) * 10) / 10;
        }
      }
      // One product shouldn't fill two layers when anything else fits.
      if (picked.some((p) => p.item.id === i.id)) r.score -= 5;
      (r.unconfirmed.some((u) => HARD.includes(u)) ? maybe : ok).push(r);
    }
    const byScore = (x: Scored, y: Scored) => y.score - x.score || (y.item.stars ?? 0) - (x.item.stars ?? 0) || x.item.name.localeCompare(y.item.name);
    ok.sort(byScore);
    maybe.sort(byScore);
    const seen = new Set<string>();
    const uniq = (xs: Scored[]) => xs.filter((x) => {
      const k = brand(x.item.name) ?? x.item.id;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
    const okU = uniq(ok);
    const maybeU = uniq(maybe);

    let pick: (Scored & { pinned?: boolean }) | null = null;
    const pinId = a.pin?.[lid];
    const pinItem = pinId ? itemById.get(pinId) : undefined;
    if (pinItem) {
      const r = scoreInfraDetailed(pinItem, la);
      pick = 'excluded' in r
        ? { item: pinItem, score: 0, reasons: [], unconfirmed: [], warning: `pinned, but ${r.excluded}`, pinned: true }
        : { ...r, pinned: true };
    } else {
      pick = okU[0] ?? maybeU[0] ?? null;
    }
    const pickUnconfirmed = !!pick && !pick.pinned && !okU.length;
    if (pick) picked.push({ layer: lid, item: pick.item });

    const rest = [...okU, ...maybeU].filter((x) => x.item.id !== pick?.item.id);
    results.push({
      layer: lid,
      label: l.label,
      role: l.role,
      pick,
      pickUnconfirmed,
      whyNot: pick ? whyNot(pick, rest.slice(0, 2), excluded) : [],
      exit: pick ? exitPath(pick.item, rest, ctx.migrations) : null,
      poolSize: pool.length,
      excludedCount: excluded.length
    });
  }

  // Order the output the way the preset lists the layers.
  const rank = (id: LayerId) => {
    const order = [...(a.layers ?? preset.layers), ...(a.add ?? []), ...auto];
    return order.indexOf(id);
  };
  results.sort((x, y) => rank(x.layer) - rank(y.layer));

  const pairs = stackPairs(ctx, recById, results);
  return {
    answers: a,
    product: preset.label,
    layers: results,
    pairs,
    risk: riskOf(results, pairs, recById, wanted),
    security: securityOf(results),
    evals: evalsOf(ctx, results, preset),
    stackYaml: toStackYaml(a, results)
  };
}

function whyNot(pick: Scored, ranked: Scored[], excluded: { item: ChooserItem; why: Exclusion }[]): WhyNot[] {
  const out: WhyNot[] = [];
  const pickCats = new Set(pick.reasons.map(category));
  for (const r of ranked) {
    const because: Reason[] = [];
    const theirs = new Set(r.reasons.map(category));
    const edge = pick.reasons.filter((x) => x.text.startsWith('Works with') && !r.reasons.some((y) => y.text === x.text));
    if (edge.length) because.push({ text: `No recorded integration with ${edge.map((x) => x.text.replace(/^Works with ([^:]+).*$/, '$1')).join(', ')}` });
    const missing = [...pickCats].filter((c) => !c.startsWith('Works with') && !theirs.has(c));
    if (missing.length) because.push({ text: `The catalog has no ${missing.slice(0, 3).map((m) => m.toLowerCase()).join(', ')} fact for it` });
    if (r.unconfirmed.length) because.push({ text: `Can't confirm: ${r.unconfirmed.join(', ')}` });
    if (r.warning) because.push({ text: `Lifecycle: ${r.warning}` });
    because.push({
      text: r.score > pick.score && r.unconfirmed.length
        ? `Scores higher (${r.score} vs ${pick.score}), but a must-have is unconfirmed, so it ranks below systems that confirm all of them`
        : r.score === pick.score
          ? `Tied on score (${r.score}); ${pick.item.name} ranks first on adoption (${pick.item.stars ?? '—'} vs ${r.item.stars ?? '—'} GitHub stars)`
          : `Score ${r.score} vs ${pick.score} for ${pick.item.name}`
    });
    out.push({ id: r.item.id, name: r.item.name, because });
  }
  // The best-known systems ruled out by a hard requirement.
  const notable = excluded
    .filter((e) => e.item.tier <= 2)
    .sort((x, y) => (y.item.stars ?? 0) - (x.item.stars ?? 0) || x.item.tier - y.item.tier)
    .slice(0, 2);
  for (const e of notable) {
    const f = e.why.fact;
    out.push({ id: e.item.id, name: e.item.name, because: [{ text: `Ruled out: ${e.why.excluded}${f?.value ? ` (${f.value})` : ''}`, citation: f?.citation ?? null }] });
  }
  return out;
}

function exitPath(item: ChooserItem, rest: Scored[], migrations?: ComposerContext['migrations']): ExitPath {
  const own = brand(item.name);
  const runnable = (r: Scored) => (r.item.oss === 'yes' || r.item.selfHost === 'yes') && brand(r.item.name) !== own;
  const fb = rest.find((r) => runnable(r) && r.item.status.severity === 0) ?? rest.find(runnable);
  const m = migrations?.get(item.id);
  return {
    selfHost: { tri: item.selfHost, fact: item.facts.deployment.value ? item.facts.deployment : item.facts.license },
    openSource: { tri: item.oss, fact: item.facts.license },
    fallback: fb ? { id: fb.item.id, name: fb.item.name } : null,
    migration: m ? { summary: m.summary, sources: m.sources } : null
  };
}

function stackPairs(ctx: ComposerContext, byId: Map<string, RecordLike>, layers: LayerResult[]): PairResult[] {
  const ids = [...new Set(layers.map((l) => l.pick?.item.id).filter((x): x is string => !!x))];
  const out: PairResult[] = [];
  for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) out.push(pairEvidence(ctx, byId, ids[i], ids[j]));
  return out;
}

/** Layer pairs where a missing integration matters (the framework talks to
 * everything; the gateway sits in front of the model). */
const MUST_CONNECT: [LayerId, LayerId][] = [
  ['framework', 'memory'], ['framework', 'vectors'], ['framework', 'tools'], ['framework', 'observability'],
  ['framework', 'sandbox'], ['framework', 'orchestration'], ['framework', 'browser'], ['voice', 'model'],
  ['gateway', 'model'], ['vectors', 'embeddings'], ['memory', 'vectors']
];

function riskOf(layers: LayerResult[], pairs: PairResult[], byId: Map<string, RecordLike>, wanted: Set<LayerId>): StackPlan['risk'] {
  const f: RiskFactor[] = [];
  const picks = layers.filter((l) => l.pick).map((l) => ({ layer: l.layer, s: l.pick! }));
  for (const p of picks) {
    const st = p.s.item.status;
    if (st.severity >= 1 && st.status !== 'active') f.push({ factor: 'lifecycle', points: st.severity, detail: `${p.s.item.name}: ${st.status}${st.note ? ' — ' + st.note : ''}` });
    const m = p.s.item.facts.maturity;
    if (m?.value && m.value !== 'ga') f.push({ factor: 'maturity', points: m.value === 'beta' ? 0.5 : 1, detail: `${p.s.item.name}: ${m.value}, not generally available`, citation: m.citation });
  }
  const byBrand = new Map<string, string[]>();
  for (const p of picks) {
    const b = brand(p.s.item.name);
    if (b) byBrand.set(b, [...(byBrand.get(b) ?? []), LAYER_BY_ID[p.layer].label]);
  }
  for (const [b, ls] of byBrand) if (ls.length >= 2) f.push({ factor: 'vendor-concentration', points: ls.length >= 3 ? 2 : 1, detail: `${ls.length} layers from one vendor (${b}): ${ls.join(', ')}` });
  for (const p of picks) {
    const pt = participants(byId.get(p.s.item.id));
    if (pt.n !== null && pt.n < 5) f.push({ factor: 'bus-factor', points: 1, detail: `${p.s.item.name}: ${pt.n} active participant${pt.n === 1 ? '' : 's'} last month (OpenDigger)`, citation: pt.citation });
    const lic = p.s.item.facts.license;
    if (SOURCE_AVAILABLE.test(lic.value)) f.push({ factor: 'licence', points: 1, detail: `${p.s.item.name}: source-available licence (${lic.value})`, citation: lic.citation });
    else if (RELICENSED.test(`${lic.value} ${p.s.item.desc}`)) f.push({ factor: 'licence', points: 1, detail: `${p.s.item.name}: licence has changed before (${lic.value})`, citation: lic.citation });
    if (p.s.unconfirmed.length) f.push({ factor: 'unconfirmed', points: 0.5, detail: `${p.s.item.name}: can't confirm ${p.s.unconfirmed.join(', ')}` });
  }
  const pickOf = new Map(picks.map((p) => [p.layer, p.s.item]));
  for (const [x, y] of MUST_CONNECT) {
    const ix = pickOf.get(x);
    const iy = pickOf.get(y);
    if (!ix || !iy || ix.id === iy.id) continue;
    const pr = pairs.find((p) => (p.a === ix.id && p.b === iy.id) || (p.a === iy.id && p.b === ix.id));
    if (!pr || pr.status === 'not-recorded') f.push({ factor: 'unrecorded-integration', points: 0.5, detail: `No recorded integration between ${ix.name} and ${iy.name}; check before committing` });
  }
  for (const l of wanted) if (!pickOf.has(l)) f.push({ factor: 'gap', points: 1, detail: `${LAYER_BY_ID[l].label}: no catalogued option meets the requirements` });
  const score = Math.round(f.reduce((s, x) => s + x.points, 0) * 10) / 10;
  return { score, level: score < 3 ? 'low' : score < 6 ? 'medium' : 'high', factors: f };
}

// OWASP Top 10 for LLM Applications (2025), mapped to the layers that
// address each risk. "practice" means no component covers it on its own.
const OWASP_URL = 'https://genai.owasp.org/llm-top-10/';
const OWASP: { id: string; risk: string; layers: LayerId[]; practice?: string; note: string }[] = [
  { id: 'LLM01', risk: 'Prompt injection', layers: ['guardrails'], note: 'Screen user input and retrieved content before it reaches the model.' },
  { id: 'LLM02', risk: 'Sensitive information disclosure', layers: ['guardrails'], note: 'Detect and redact PII and secrets in prompts and outputs.' },
  { id: 'LLM03', risk: 'Supply chain', layers: [], practice: 'Run the stack check (GitHub Action) on every PR so archived or acquired components are flagged.', note: 'Components and models you depend on.' },
  { id: 'LLM04', risk: 'Data and model poisoning', layers: ['observability'], note: 'Evaluate on fixed test sets and watch for drift after data or model changes.' },
  { id: 'LLM05', risk: 'Improper output handling', layers: ['guardrails', 'sandbox'], note: 'Validate model output before it reaches other systems; run generated code in a sandbox.' },
  { id: 'LLM06', risk: 'Excessive agency', layers: ['tools', 'sandbox'], note: 'Give agents scoped, per-user credentials and isolate what they execute.' },
  { id: 'LLM07', risk: 'System prompt leakage', layers: ['guardrails'], note: 'Keep secrets out of prompts; filter outputs that echo them.' },
  { id: 'LLM08', risk: 'Vector and embedding weaknesses', layers: [], practice: 'Enforce per-tenant access control in the vector store and memory layer; never mix tenants in one index without filters.', note: 'Retrieval can leak other users\' data.' },
  { id: 'LLM09', risk: 'Misinformation', layers: ['observability'], note: 'Evaluate groundedness and accuracy before and after release.' },
  { id: 'LLM10', risk: 'Unbounded consumption', layers: ['gateway'], note: 'Rate limits, budgets and timeouts on model calls.' }
];

function securityOf(layers: LayerResult[]): StackPlan['security'] {
  const have = new Map(layers.filter((l) => l.pick).map((l) => [l.layer, l.pick!.item.name]));
  return {
    source: OWASP_URL,
    items: OWASP.map((o) => {
      const by = o.layers.filter((l) => have.has(l)).map((l) => have.get(l)!);
      if (!o.layers.length) return { id: o.id, risk: o.risk, status: 'practice' as const, by: [], note: o.practice ?? o.note };
      return by.length
        ? { id: o.id, risk: o.risk, status: 'addressed' as const, by, note: o.note }
        : { id: o.id, risk: o.risk, status: 'gap' as const, by: [], note: `${o.note} Add a layer for it: ${o.layers.map((l) => LAYER_BY_ID[l].label).join(' or ')}.` };
    })
  };
}

function evalsOf(ctx: ComposerContext, layers: LayerResult[], preset: ProductPreset): StackPlan['evals'] {
  const obs = layers.find((l) => l.layer === 'observability')?.pick?.item ?? null;
  const memRx = layers.some((l) => l.layer === 'memory' && l.pick) ? /longmemeval|locomo/i : null;
  const benchmarks = ctx.items
    .filter((i) => (i.section === 'Memory benchmarks & evaluation' || /benchmark/i.test(i.type)) && i.status.severity < 3)
    .filter((i) => preset.benchmarks.test(i.name) || (memRx && memRx.test(i.name)))
    .sort((x, y) => x.tier - y.tier || x.name.localeCompare(y.name))
    .slice(0, 6)
    .map((i) => ({ id: i.id, name: i.name, url: i.url }));
  return { observability: obs ? { id: obs.id, name: obs.name } : null, benchmarks };
}

// ---------------------------------------------------------------------------
// stack.yml
// ---------------------------------------------------------------------------

/** The portable stack file. One `layer: record-id` line per component; the
 * CLI, the GitHub Action and the MCP servers all read it back
 * (stack-check.ts → parseStackFile). */
export function toStackYaml(a: StackAnswers, layers: LayerResult[]): string {
  const lines = [
    '# Agent stack — generated by the AI Agent Infrastructure Landscape (plan_stack).',
    '# Check it any time: npx landscape check stack.yml, or the "AI stack check" GitHub Action.',
    'version: 1',
    `product: ${a.product}`,
    'requirements:',
    `  language: ${a.language}`,
    `  hosting: ${a.hosting}`,
    `  oss: ${a.oss}`,
    `  mcp: ${a.mcp}`,
    'components:'
  ];
  for (const l of layers) if (l.pick) lines.push(`  ${l.layer}: ${l.pick.item.id}  # ${l.pick.item.name.replace(/#/g, '')}`);
  return lines.join('\n') + '\n';
}

// ---------------------------------------------------------------------------
// Compact JSON for tool output (MCP server, hosted worker, CLI --json)
// ---------------------------------------------------------------------------

/** The plan without the internal item objects: names, ids, cited reasons.
 * `page` builds a link to a system's page when given. */
export function slimPlan(p: StackPlan, page?: (id: string) => string) {
  const name = new Map(p.layers.filter((l) => l.pick).map((l) => [l.pick!.item.id, l.pick!.item.name]));
  return {
    product: p.product,
    answers: p.answers,
    layers: p.layers.map((l) => ({
      layer: l.layer,
      label: l.label,
      role: l.role,
      pick: l.pick
        ? {
            id: l.pick.item.id,
            name: l.pick.item.name,
            ...(page ? { page: page(l.pick.item.id) } : {}),
            reasons: l.pick.reasons,
            unconfirmed: l.pick.unconfirmed,
            warning: l.pick.warning,
            ...(l.pick.pinned ? { pinned: true } : {})
          }
        : null,
      pickUnconfirmed: l.pickUnconfirmed,
      whyNot: l.whyNot,
      exit: l.exit && {
        selfHost: l.exit.selfHost.tri,
        openSource: l.exit.openSource.tri,
        licence: l.exit.openSource.fact.value || null,
        fallback: l.exit.fallback,
        migration: l.exit.migration
      },
      candidates: l.poolSize,
      ruledOut: l.excludedCount
    })),
    integrations: {
      documented: p.pairs.filter((x) => x.status === 'documented').map((x) => ({
        a: name.get(x.a) ?? x.a,
        b: name.get(x.b) ?? x.b,
        evidence: x.evidence[0] ? (x.evidence[0].kind === 'edge' ? x.evidence[0].text : x.evidence[0].text) : '',
        citation: x.evidence[0]?.citation ?? null
      })),
      mentioned: p.pairs.filter((x) => x.status === 'mentioned').length,
      notRecorded: p.pairs.filter((x) => x.status === 'not-recorded').length
    },
    risk: p.risk,
    security: p.security,
    evals: p.evals,
    stackYaml: p.stackYaml
  };
}
