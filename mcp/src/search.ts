// Natural-language catalog search ("memory that handles contradictions and
// runs on Postgres", "self-hosted vector db with MCP, python").
//
// Two parts, both explainable:
//   1. constraint parsing — phrases like "self-hosted", "open source",
//      "with MCP", "python", "managed" become must-haves checked against
//      catalogued facts (same tri-state logic as the choosers);
//   2. BM25 ranking of the remaining words over name, type, description,
//      claims, optimised-for, backend storage and taxonomy values, with a
//      small boost for maintained, well-documented systems.
// No embeddings and no network: it runs in the browser, the MCP server and
// the hosted worker over the same items.
//
// Pure and dependency-free apart from chooser.ts.

import { type ChooserItem, type Tri } from './chooser.js';
import { languageTri } from './chooser-infra.js';

export interface SearchDoc {
  item: ChooserItem;
  /** Extra text to index (optimised-for, backend storage, claims…). */
  text: string;
  family: string;
}

export interface Constraint {
  key: 'selfHost' | 'managed' | 'oss' | 'mcp' | 'python' | 'typescript' | 'family' | 'active';
  label: string;
  value?: string;
}

export interface SearchHit {
  id: string;
  name: string;
  section: string;
  family: string;
  score: number;
  /** Query terms that matched, for "why this result". */
  matched: string[];
  /** Constraints this system confirms / can't confirm. */
  confirmed: string[];
  unconfirmed: string[];
  warning: string | null;
  desc: string;
}

const RULES: { rx: RegExp; c: Constraint }[] = [
  { rx: /\b(self[- ]?host(ed|able)?|on[- ]?prem(ise)?s?|run (it )?(myself|locally)|local[- ]first)\b/i, c: { key: 'selfHost', label: 'self-hostable' } },
  { rx: /\b(managed|hosted|saas|cloud service|fully managed)\b/i, c: { key: 'managed', label: 'managed service' } },
  { rx: /\b(open[- ]?source|oss|apache|mit licen[cs]ed?|permissive)\b/i, c: { key: 'oss', label: 'open source' } },
  { rx: /\b(mcp|model context protocol)\b/i, c: { key: 'mcp', label: 'MCP support' } },
  { rx: /\bpython\b/i, c: { key: 'python', label: 'Python SDK' } },
  { rx: /\b(typescript|javascript|node(\.js)?|\bts\b)\b/i, c: { key: 'typescript', label: 'TypeScript / JavaScript SDK' } },
  { rx: /\b(memory layers?|agent memory|long[- ]term memory)\b/i, c: { key: 'family', label: 'Agent Memory', value: 'memory' } },
  { rx: /\b(agent frameworks?|orchestration|multi[- ]agent)\b/i, c: { key: 'family', label: 'Agent Frameworks', value: 'agents' } },
  { rx: /\b(vector (db|database|store|search)s?|knowledge graphs?|graph (db|database)s?|embeddings?|rerankers?)\b/i, c: { key: 'family', label: 'Retrieval & Data', value: 'data' } },
  { rx: /\b(papers?|research|benchmarks?)\b/i, c: { key: 'family', label: 'Research & Benchmarks', value: 'memory-research' } },
  { rx: /\b(not (archived|dead)|maintained|active|alive)\b/i, c: { key: 'active', label: 'actively maintained' } }
];

const STOP = new Set(
  'a an and or the of for to in on with without that which who is are be can i my me we our it its this these those use using used want need needs something tool tools system systems one ones like support supports supporting good best what how do does handle handles handling store stores storing run runs running based work works from into by as at any some'.split(' ')
);

// Words → catalog vocabulary (taxonomy values and common cell phrasing).
const SYNONYMS: Record<string, string[]> = {
  contradiction: ['contradiction', 'conflict', 'bi-temporal', 'invalidate', 'llm-arbitrate', 'overwrite'],
  contradictions: ['contradiction', 'conflict', 'bi-temporal', 'invalidate', 'llm-arbitrate'],
  conflicts: ['conflict', 'contradiction', 'bi-temporal'],
  forget: ['forgetting', 'decay', 'ttl', 'expire'],
  forgetting: ['forgetting', 'decay', 'ttl', 'expire'],
  postgres: ['postgres', 'postgresql', 'pgvector'],
  postgresql: ['postgres', 'postgresql', 'pgvector'],
  graph: ['graph', 'knowledge-graph', 'graph-traversal', 'neo4j'],
  temporal: ['temporal', 'bi-temporal', 'time'],
  history: ['bi-temporal', 'versioned', 'document-version', 'history'],
  versioned: ['versioned', 'document-version', 'bi-temporal'],
  facts: ['fact', 'facts', 'profile'],
  preferences: ['preference', 'profile', 'fact'],
  conversations: ['episode', 'turn', 'conversation', 'summary'],
  documents: ['document', 'chunk', 'file'],
  coding: ['coding', 'code', 'ide', 'repository'],
  voice: ['voice', 'speech', 'telephony'],
  browser: ['browser', 'web', 'computer-use'],
  sandbox: ['sandbox', 'isolated', 'microvm', 'container'],
  durable: ['durable', 'workflow', 'long-running'],
  hybrid: ['hybrid', 'bm25', 'keyword'],
  privacy: ['privacy', 'encryption', 'on-device', 'local'],
  enterprise: ['enterprise', 'sso', 'rbac', 'soc', 'compliance'],
  cheap: ['free', 'open-source', 'pricing'],
  free: ['free', 'open-source']
};

function tokens(s: string): string[] {
  return (s.toLowerCase().match(/[a-z0-9][a-z0-9.+#-]*/g) ?? []).map((t) => t.replace(/[.-]+$/, '')).filter((t) => t.length > 1);
}

export interface SearchIndex {
  docs: SearchDoc[];
  tf: Map<string, number>[];
  len: number[];
  df: Map<string, number>;
  avg: number;
}

export function buildIndex(docs: SearchDoc[]): SearchIndex {
  const tf: Map<string, number>[] = [];
  const len: number[] = [];
  const df = new Map<string, number>();
  for (const d of docs) {
    const i = d.item;
    // Name and type count three times: they say what the system *is*.
    const text = [i.name, i.name, i.name, i.type, i.type, i.section, i.desc, d.text, i.storage.join(' '), i.retrieval.join(' '), i.unit.join(' '), i.conflict.join(' ')].join(' ');
    const m = new Map<string, number>();
    const ts = tokens(text);
    for (const t of ts) m.set(t, (m.get(t) ?? 0) + 1);
    for (const t of m.keys()) df.set(t, (df.get(t) ?? 0) + 1);
    tf.push(m);
    len.push(ts.length);
  }
  return { docs, tf, len, df, avg: len.reduce((a, b) => a + b, 0) / Math.max(1, len.length) };
}

export function parseQuery(q: string): { constraints: Constraint[]; terms: string[] } {
  const constraints: Constraint[] = [];
  let rest = q;
  for (const { rx, c } of RULES) {
    if (rx.test(rest)) {
      if (!constraints.some((x) => x.key === c.key && x.value === c.value)) constraints.push(c);
      rest = rest.replace(rx, ' ');
    }
  }
  // Only one family constraint (the first mentioned wins).
  const fam = constraints.filter((c) => c.key === 'family');
  const cons = [...constraints.filter((c) => c.key !== 'family'), ...fam.slice(0, 1)];
  const terms = tokens(rest).filter((t) => !STOP.has(t));
  return { constraints: cons, terms };
}

function check(c: Constraint, d: SearchDoc): Tri {
  const i = d.item;
  switch (c.key) {
    case 'selfHost': return i.selfHost;
    case 'managed': return i.managed;
    case 'oss': return i.oss;
    case 'mcp': return i.mcp;
    case 'python': return languageTri(i, 'python').tri;
    case 'typescript': return languageTri(i, 'typescript').tri;
    case 'family': return d.family === c.value ? 'yes' : 'no';
    case 'active': return i.status.severity >= 2 ? 'no' : 'yes';
  }
}

export function search(index: SearchIndex, q: string, limit = 20): { constraints: Constraint[]; terms: string[]; hits: SearchHit[]; considered: number } {
  const { constraints, terms } = parseQuery(q);
  const N = index.docs.length;
  const k1 = 1.2, b = 0.75;
  const expanded = terms.map((t) => [...new Set([t, ...(SYNONYMS[t] ?? [])])]);
  const hits: SearchHit[] = [];
  let considered = 0;
  index.docs.forEach((d, n) => {
    const confirmed: string[] = [];
    const unconfirmed: string[] = [];
    for (const c of constraints) {
      const t = check(c, d);
      if (t === 'no') return;
      (t === 'yes' ? confirmed : unconfirmed).push(c.label);
    }
    considered++;
    let s = 0;
    const matched: string[] = [];
    for (let k = 0; k < terms.length; k++) {
      let best = 0;
      for (const [j, t] of expanded[k].entries()) {
        const f = index.tf[n].get(t) ?? 0;
        if (!f) continue;
        const df = index.df.get(t) ?? 0;
        const idf = Math.log(1 + (N - df + 0.5) / (df + 0.5));
        const sc = (idf * (f * (k1 + 1))) / (f + k1 * (1 - b + (b * index.len[n]) / index.avg)) * (j === 0 ? 1 : 0.6);
        best = Math.max(best, sc);
      }
      if (best > 0) matched.push(terms[k]);
      s += best;
    }
    if (terms.length && !matched.length) return;
    const i = d.item;
    // Gentle priors: maintained, documented, adopted.
    s += ({ 1: 0.6, 2: 0.4, 3: 0.2 } as Record<number, number>)[i.tier] ?? 0;
    if (i.stars) s += Math.min(0.8, Math.max(0, Math.log10(i.stars) - 2) * 0.3);
    s -= i.status.severity * 0.6;
    s -= unconfirmed.length * 0.8;
    if (terms.length) s *= 0.5 + (0.5 * matched.length) / terms.length;
    hits.push({
      id: i.id, name: i.name, section: i.section, family: d.family, score: Math.round(s * 100) / 100,
      matched, confirmed, unconfirmed,
      warning: i.status.severity >= 1 && i.status.status !== 'active' ? `${i.status.status}${i.status.note ? ' — ' + i.status.note : ''}` : null,
      desc: i.desc
    });
  });
  hits.sort((x, y) => y.score - x.score || x.name.localeCompare(y.name));
  return { constraints, terms, hits: hits.slice(0, limit), considered };
}

/** Text a SearchDoc indexes beyond the ChooserItem fields. */
export function docText(cells: unknown, max = 600): string {
  const c = cells as Record<string, { value?: string; status?: string } | undefined>;
  return ['optimised-for', 'backend-storage', 'claims', 'api-surface', 'runtimes', 'contradiction', 'forgetting', 'modalities', 'validated-verticals']
    .map((k) => {
      const x = c[k];
      return x && x.value && !['no-data', 'not-applicable', 'depth-floor-reached'].includes(x.status ?? '') ? String(x.value).slice(0, max) : '';
    })
    .join(' ');
}

/** A ChooserItem trimmed to what search reads (for shipping to a browser). */
export function slimForSearch(i: ChooserItem): ChooserItem {
  const empty = { value: '', citation: null };
  return {
    ...i,
    facts: {
      license: empty, deployment: empty, mcp: empty, pricing: empty, release: empty, gh: empty, conflictText: empty,
      runtimes: { value: i.facts.runtimes.value.slice(0, 160), citation: null },
      api: { value: i.facts.api.value.slice(0, 160), citation: null },
      sdk: { value: i.facts.sdk.value, citation: null },
      protocols: empty, maturity: empty, compliance: empty
    }
  };
}
