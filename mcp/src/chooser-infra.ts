// Agent-framework and data-store chooser (/choose/framework, /choose/data):
// the same honesty rules as the memory-layer chooser (chooser.ts), with
// question sets for the Agents and Data catalogs.
//
//   * Every reason is a catalogued cell value with its citation.
//   * A must-have counts as met only when a cell confirms it; when the
//     catalog has no data the system goes under "might fit".
//   * Archived / deprecated / shut-down systems are never recommended.
//   * Only one product per brand is recommended (Qdrant and Qdrant Cloud
//     are one choice).
//
// Pure and dependency-free apart from chooser.ts.

import { brand, monthsSince, type ChooserItem, type Fact, type Reason, type Rank, type Scored, type Tri, type Hosting } from './chooser.js';

const r1 = (n: number) => Math.round(n * 10) / 10;

/** Fit first, then maturity, then adoption (#359); name last for stability. */
export function byFit(x: Scored, y: Scored): number {
  const a = x.rank ?? { fit: 0, maturity: 0, adoption: 0 };
  const b = y.rank ?? { fit: 0, maturity: 0, adoption: 0 };
  return b.fit - a.fit || b.maturity - a.maturity || b.adoption - a.adoption || x.item.name.localeCompare(y.item.name);
}

/** Display score: the three components, fit weighted most. */
export function rankScore(r: Rank): number {
  return r1(r.fit * 10 + r.maturity + r.adoption / 10);
}

const HARD_LABELS = ['Python SDK', 'TypeScript / JavaScript SDK', 'Self-hostable', 'Managed service', 'Open source', 'MCP', 'Compliance'];
/** Reasons in the order they matter (#359): the constraints the user set,
 *  then integration and infrastructure fit, then other facts, adoption last. */
export function orderReasons(reasons: Reason[]): Reason[] {
  const k = (r: Reason) => {
    const c = r.text.split(':')[0];
    if (HARD_LABELS.includes(c)) return 0;
    if (r.text.startsWith('Works with') || r.text.startsWith('Runs on or inside')) return 1;
    if (c === 'Adoption' || c === 'Ecosystem') return 3;
    return 2;
  };
  return reasons.map((r, i) => ({ r, i })).sort((a, b) => k(a.r) - k(b.r) || a.i - b.i).map((x) => x.r);
}

export type InfraKind = 'framework' | 'data';
export type Language = 'python' | 'typescript' | 'any';

export interface InfraAnswers {
  kind: InfraKind;
  need: string;
  language: Language;
  hosting: Hosting;
  oss: boolean;
  mcp: boolean;
  /** data only: prefer a store you may already run (Postgres, Mongo, Elastic, Redis…) */
  existing: boolean;
}

export interface Need {
  value: string;
  label: string;
  sections: string[];
  /** Keep only systems whose type label (or name) matches… */
  match?: RegExp;
  /** …and drop those that match this. */
  exclude?: RegExp;
}

export const FW_SECTIONS = ['Agent frameworks (no first-party memory layer)', 'Multi-agent orchestration platforms'];
export const NOT_A_FRAMEWORK = /protocol|\bMCP\b|coding (agent|assistant)|VS Code|SWE agent|spec-to-codebase|durable|workflow|long-running|jobs|event-driven|OAuth|tools? ?\/ ?auth|tool\/auth|computer[- ]use|research lab|foundation lab|fine-tuning|\(origin\)|no-code|low-code|web-agent|browser-agent/i;

export const NEEDS: Record<InfraKind, Need[]> = {
  framework: [
    { value: 'library', label: 'A framework to build agents in code', sections: FW_SECTIONS, exclude: NOT_A_FRAMEWORK },
    { value: 'durable', label: 'Durable execution for long-running agents', sections: FW_SECTIONS, match: /durable|workflow|long-running|jobs|event-driven/i },
    { value: 'tools', label: 'Tools and auth for agents', sections: FW_SECTIONS, match: /tools?\b.*\bauth|OAuth|tool\/auth/i },
    { value: 'nocode', label: 'A no-code / low-code agent builder', sections: [...FW_SECTIONS, 'Use-case-specific agent harnesses'], match: /no-code|low-code|visual builder|drag/i },
    { value: 'sandbox', label: 'A sandbox to run agent-generated code', sections: ['AI sandbox & runtime environments'] }
  ],
  data: [
    { value: 'vectors', label: 'Vector search for RAG or memory', sections: ['Vector-database infrastructure', 'Search platforms (non-memory)'] },
    { value: 'graph', label: 'A knowledge graph', sections: ['Knowledge-graph platforms'] },
    { value: 'embeddings', label: 'Embedding or reranking models', sections: ['Embedding & reranker services'] }
  ]
};

export const KIND_LABEL: Record<InfraKind, string> = { framework: 'agent framework', data: 'vector database or graph store' };

export const DEFAULT_INFRA: Record<InfraKind, InfraAnswers> = {
  framework: { kind: 'framework', need: 'library', language: 'any', hosting: 'any', oss: false, mcp: false, existing: false },
  data: { kind: 'data', need: 'vectors', language: 'any', hosting: 'any', oss: false, mcp: false, existing: false }
};

/** Every section either chooser draws from (for slimming page data). */
export const INFRA_SECTIONS: string[] = [...new Set(Object.values(NEEDS).flat().flatMap((n) => n.sections))];

const LANG_RX: Record<Exclude<Language, 'any'>, RegExp> = {
  python: /\bpython\b|\bpypi\b|pip install/i,
  typescript: /\b(typescript|javascript|node(\.js)?|npm|deno|bun)\b/i
};
const ANY_LANG = /\b(any (language|http)|language[- ]agnostic|rest api|http api|grpc|openapi)\b/i;

/** Does the system offer an SDK in this language? From the runtimes and
 * api-surface cells only. */
export function languageTri(i: ChooserItem, lang: Language): { tri: Tri; fact: Fact } {
  if (lang === 'any') return { tri: 'yes', fact: { value: '', citation: null } };
  // The sdk-languages cell (v1.2.0) is a checked set; when filled it decides.
  const sdk = i.facts.sdk;
  if (sdk?.value) {
    const set = sdk.value.split(',');
    const want = lang === 'typescript' ? ['typescript', 'javascript'] : [lang];
    return { tri: set.some((s) => want.includes(s)) ? 'yes' : 'no', fact: sdk };
  }
  const facts = [i.facts.runtimes, i.facts.api].filter((f) => f.value);
  const hit = facts.find((f) => LANG_RX[lang].test(f.value)) ?? facts.find((f) => ANY_LANG.test(f.value));
  if (hit) return { tri: 'yes', fact: hit };
  // Fall back to the catalog's own type label / description ("TypeScript
  // agent framework"), which is how many framework rows state it.
  const label = `${i.type} ${i.desc}`;
  if (LANG_RX[lang].test(label)) return { tri: 'yes', fact: { value: i.type || i.desc, citation: i.url } };
  if (!facts.length) return { tri: 'unknown', fact: { value: '', citation: null } };
  return { tri: i.facts.runtimes.value ? 'no' : 'unknown', fact: facts[0] };
}

/** GitHub owner/repo a record points at, to treat two rows for the same
 * repo (pgvector / PostgreSQL pgvector) as one product. */
function repoOf(i: ChooserItem): string | null {
  const m = i.facts.gh.value.match(/^\s*([\w.-]+)\/([\w.-]+)/) || (i.facts.gh.citation ?? '').match(/github\.com\/([\w.-]+)\/([\w.-]+)/i);
  return m ? `${m[1]}/${m[2]}`.toLowerCase() : null;
}

const EXISTING = /\b(postgres(ql)?|pgvector|mongo(db)?|elastic(search)?|opensearch|redis|supabase|sqlite|clickhouse|cassandra|astra)\b/i;

export function inNeed(i: ChooserItem, need: Need): boolean {
  if (!need.sections.includes(i.section)) return false;
  const label = `${i.type} ${i.name}`;
  if (need.match && !need.match.test(label)) return false;
  if (need.exclude && need.exclude.test(label)) return false;
  return true;
}

/** Why a system was ruled out: the requirement it fails and the cited
 * fact that shows it. */
export interface Exclusion {
  excluded: string;
  fact: Fact | null;
}

export function scoreInfra(item: ChooserItem, a: InfraAnswers): Scored | 'excluded' {
  const r = scoreInfraDetailed(item, a);
  return 'excluded' in r ? 'excluded' : r;
}

export function scoreInfraDetailed(item: ChooserItem, a: InfraAnswers): Scored | Exclusion {
  if (item.status.severity >= 3) return { excluded: `${item.status.status}${item.status.note ? ' — ' + item.status.note : ''}`, fact: null };
  const reasons: Reason[] = [];
  const unconfirmed: string[] = [];
  let failed: Exclusion | null = null;
  const req = (want: boolean, have: Tri, label: string, f: Fact) => {
    if (!want) return true;
    if (have === 'no') {
      failed = { excluded: `not ${label.toLowerCase()}`, fact: f.value ? f : null };
      return false;
    }
    if (have === 'unknown') unconfirmed.push(label);
    else reasons.push({ text: `${label}: ${f.value || 'yes'}`, citation: f.citation });
    return true;
  };
  const lang = languageTri(item, a.language);
  const langLabel = a.language === 'python' ? 'Python SDK' : 'TypeScript / JavaScript SDK';
  if (!req(a.language !== 'any', lang.tri, langLabel, lang.fact)) return failed!;
  if (!req(a.hosting === 'self', item.selfHost, 'Self-hostable', item.facts.deployment.value ? item.facts.deployment : item.facts.license)) return failed!;
  if (!req(a.hosting === 'managed', item.managed, 'Managed service', item.facts.deployment)) return failed!;
  if (!req(a.oss, item.oss, 'Open source', item.facts.license)) return failed!;
  if (!req(a.mcp, item.mcp, 'MCP', item.facts.mcp)) return failed!;

  // Ranked fit → maturity → adoption (#359). Hard constraints above are
  // filters; what's left ranks on how well it fits, then how mature it is,
  // and only then on how popular.
  const rank: Rank = { fit: 0, maturity: ({ 1: 3, 2: 2, 3: 1 } as Record<number, number>)[item.tier] ?? 0, adoption: 0 };
  if (a.kind === 'data' && a.existing) {
    const m = `${item.name} ${item.desc}`.match(EXISTING);
    if (m) {
      rank.fit += 1;
      reasons.push({ text: `Runs on or inside ${m[0]}, which you may already operate` });
    }
  }
  if (item.releaseDate && monthsSince(item.releaseDate) <= 6) {
    rank.adoption += 0.5;
    reasons.push({ text: `Recently released: ${item.facts.release.value}`, citation: item.facts.release.citation });
  }
  if (a.language === 'any' && item.facts.runtimes.value) reasons.push({ text: `SDKs: ${item.facts.runtimes.value}`, citation: item.facts.runtimes.citation });
  if (!a.oss && item.oss === 'yes') reasons.push({ text: `Licence: ${item.facts.license.value}`, citation: item.facts.license.citation });
  if (a.hosting === 'any' && item.facts.deployment.value) reasons.push({ text: `Deployment: ${item.facts.deployment.value}`, citation: item.facts.deployment.citation });
  if (!a.mcp && item.mcp === 'yes' && item.facts.mcp.value) reasons.push({ text: `MCP support: ${item.facts.mcp.value}`, citation: item.facts.mcp.citation });
  if (item.facts.pricing.value) reasons.push({ text: `Pricing: ${item.facts.pricing.value}`, citation: item.facts.pricing.citation });
  // Thin records (no licence, deployment or repo facts) rank below
  // well-documented ones.
  const known = [item.facts.license, item.facts.deployment, item.facts.gh, item.facts.release].filter((f) => f.value).length;
  rank.adoption += known * 0.25;

  const warning = item.status.severity >= 1 && item.status.status !== 'active'
    ? `${item.status.status}${item.status.note ? ' — ' + item.status.note : ''}`
    : null;
  if (warning) rank.maturity -= item.status.severity;
  // Adoption is a tiebreaker and is labelled as such, after the facts.
  const facts = reasons.slice(0, 5);
  if (item.stars) {
    // Uncapped: as a tiebreaker it has to tell 149k stars from 45k.
    rank.adoption += Math.max(0, Math.log10(item.stars));
    facts.push({ text: `Adoption: ${item.facts.gh.value.split(' — ').slice(0, 2).join(' — ')}`, citation: item.facts.gh.citation });
  }
  rank.maturity = r1(rank.maturity);
  rank.adoption = r1(rank.adoption);
  return { item, score: rankScore(rank), reasons: facts, unconfirmed, warning, rank };
}

export interface InfraResult {
  picks: Scored[];
  alsoConsider: Scored[];
  unconfirmed: Scored[];
  excludedCount: number;
  poolSize: number;
  fitIds: string[];
}

export function chooseInfra(items: ChooserItem[], a: InfraAnswers): InfraResult {
  const need = NEEDS[a.kind].find((n) => n.value === a.need) ?? NEEDS[a.kind][0];
  const pool = items.filter((i) => inNeed(i, need));
  let excluded = 0;
  const ok: Scored[] = [];
  const maybe: Scored[] = [];
  const HARD = ['Self-hostable', 'Managed service', 'Open source', 'MCP', 'Python SDK', 'TypeScript / JavaScript SDK'];
  for (const i of pool) {
    const r = scoreInfra(i, a);
    if (r === 'excluded') {
      excluded++;
      continue;
    }
    (r.unconfirmed.some((u) => HARD.includes(u)) ? maybe : ok).push(r);
  }
  ok.sort(byFit);
  maybe.sort(byFit);
  // One recommendation per product: same brand ("Qdrant" / "Qdrant Cloud")
  // or same repo ("pgvector" / "PostgreSQL pgvector").
  const seen = new Set<string>();
  const uniq = (xs: Scored[]) =>
    xs.filter((x) => {
      const keys = [brand(x.item.name) ?? x.item.id, repoOf(x.item)].filter((k): k is string => !!k);
      if (keys.some((k) => seen.has(k))) return false;
      for (const k of keys) seen.add(k);
      return true;
    });
  const okU = uniq(ok);
  const maybeU = uniq(maybe);
  return {
    picks: okU.slice(0, 3),
    alsoConsider: okU.slice(3, 9),
    unconfirmed: maybeU.slice(0, 8),
    excludedCount: excluded,
    poolSize: pool.length,
    fitIds: [...ok, ...maybe].map((x) => x.item.id)
  };
}

export function infraToParams(a: InfraAnswers): Record<string, string> {
  const d = DEFAULT_INFRA[a.kind] as unknown as Record<string, unknown>;
  const p: Record<string, string> = {};
  for (const [k, v] of Object.entries(a)) if (k !== 'kind' && v !== d[k]) p[k] = String(v);
  return p;
}

export function paramsToInfra(kind: InfraKind, p: { get(name: string): string | null }): InfraAnswers {
  const a = { ...DEFAULT_INFRA[kind] };
  const need = p.get('need');
  if (need && NEEDS[kind].some((n) => n.value === need)) a.need = need;
  const lang = p.get('language');
  if (lang === 'python' || lang === 'typescript' || lang === 'any') a.language = lang;
  const h = p.get('hosting');
  if (h === 'self' || h === 'managed' || h === 'any') a.hosting = h;
  a.oss = p.get('oss') === 'true';
  a.mcp = p.get('mcp') === 'true';
  a.existing = p.get('existing') === 'true';
  return a;
}
