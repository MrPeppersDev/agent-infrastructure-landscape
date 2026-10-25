// Memory-layer chooser (/choose): turn a few answers about what you're
// building into three cited picks, plus a side-by-side table.
//
// Pure functions over LandscapeRecord, so the logic can be tested
// without Svelte and reused by the MCP server later.
//
// Honesty rules:
//   * Every reason shown is a catalogued cell value with its citation.
//   * A requirement is "met" only when the cell confirms it. When the cell
//     is empty ("searched not found"), the system goes in the "might fit —
//     unconfirmed" list instead of being silently dropped or recommended.
//   * Archived / deprecated / shut-down systems (stack-index severity >= 3)
//     are never recommended; acquired / maintenance / stale ones are
//     shown with a warning.

import type { LandscapeRecord } from './types';

export type Building = 'app' | 'coding';
export type Hosting = 'self' | 'managed' | 'any';
export type Conflict = 'history' | 'latest' | 'llm' | 'any';
export type Shape = 'facts' | 'conversations' | 'documents' | 'relationships' | 'any';

export interface Answers {
  building: Building;
  hosting: Hosting;
  oss: boolean;
  mcp: boolean;
  conflict: Conflict;
  shape: Shape;
}

export const DEFAULT_ANSWERS: Answers = {
  building: 'app',
  hosting: 'any',
  oss: false,
  mcp: false,
  conflict: 'any',
  shape: 'any'
};

export const POOLS: Record<Building, string[]> = {
  app: [
    'Dedicated memory layers',
    'Framework-embedded memory',
    'Platform-provider memory',
    'Retrieval-as-memory hybrids'
  ],
  coding: ['Coding-agent memory', 'File-backed / editor paradigms', 'Claude Code memory mechanisms']
};

export type Tri = 'yes' | 'no' | 'unknown';

export interface Fact {
  value: string;
  citation: string | null;
}

export interface StackStatusLite {
  status: string;
  severity: number;
  note: string;
}

export interface ChooserItem {
  id: string;
  name: string;
  section: string;
  tier: number;
  url: string | null;
  desc: string;
  selfHost: Tri;
  managed: Tri;
  oss: Tri;
  mcp: Tri;
  facts: Record<'license' | 'deployment' | 'mcp' | 'pricing' | 'release' | 'gh' | 'conflictText', Fact>;
  storage: string[];
  unit: string[];
  conflict: string[];
  retrieval: string[];
  stars: number | null;
  releaseDate: string | null;
  status: StackStatusLite;
}

// ---------------------------------------------------------------------------
// Record → item
// ---------------------------------------------------------------------------

const EMPTY = new Set(['not-applicable', 'no-data', 'depth-floor-reached']);
const OSI = /\b(MIT|Apache[- ]?2(\.0)?|BSD|MPL|LGPL|AGPL|GPL|ISC|Unlicense)\b/i;
const NOT_OSS = /^\s*(proprietary|closed|commercial|not applicable|n\/a|elastic|bsl|business source|sspl)/i;

function fact(r: LandscapeRecord, slug: string): Fact {
  const c = (r.cells as Record<string, { value?: string; status?: string; citation?: string | null } | undefined>)[slug];
  if (!c || EMPTY.has(c.status ?? '')) return { value: '', citation: null };
  return { value: String(c.value ?? '').replace(/<[^>]+>/g, '').trim(), citation: c.citation ?? null };
}

function tax(r: LandscapeRecord, axis: string): string[] {
  const vals = (r.taxonomy as unknown as Record<string, { value: string }[]>)[axis] ?? [];
  return vals.map((v) => v.value).filter((v) => v && v !== 'n/a');
}

function hosting(dep: string, lic: Tri, hasRepo: boolean): { selfHost: Tri; managed: Tri } {
  if (!dep) {
    // An open-source repo you can run is self-hostable even if the
    // deployment cell is empty.
    return { selfHost: lic === 'yes' && hasRepo ? 'yes' : 'unknown', managed: 'unknown' };
  }
  const both = /\bboth\b/i.test(dep);
  const self = both || /self[- ]?host|on[- ]?prem|local|offline|open[- ]source|docker|kubernetes|library|embedded|in[- ]process|pip install|npm install|byoc|vpc/i.test(dep);
  const man = both || /managed|cloud|saas|hosted|\bapi\b|platform/i.test(dep);
  return { selfHost: self ? 'yes' : lic === 'yes' && hasRepo ? 'yes' : 'no', managed: man ? 'yes' : 'no' };
}

function mcpTri(v: string): Tri {
  if (!v) return 'unknown';
  if (/^(no\b|not supported|none|n\/a)/i.test(v)) return 'no';
  if (/not documented|unclear|unknown/i.test(v)) return 'unknown';
  if (/\b(yes|native|first[- ]party|official|built[- ]in|supported|mcp server|community)\b/i.test(v)) return 'yes';
  return 'unknown';
}

function stars(gh: string): number | null {
  const m = gh.match(/~?\s*([\d.,]+)\s*(k)?\s*(?:★|stars)/i) || gh.match(/\((\d[\d,]{2,})/);
  if (!m) return null;
  const n = parseFloat(m[1].replace(/,/g, ''));
  return Number.isFinite(n) ? Math.round(m[2] ? n * 1000 : n) : null;
}

export function toItem(r: LandscapeRecord, status?: StackStatusLite): ChooserItem {
  const lic = fact(r, 'license');
  const dep = fact(r, 'deployment');
  const mcp = fact(r, 'mcp-support');
  const gh = fact(r, 'gh');
  const rel = fact(r, 'latest-release');
  const oss: Tri = !lic.value ? 'unknown' : NOT_OSS.test(lic.value) ? 'no' : OSI.test(lic.value) ? 'yes' : 'no';
  const hasRepo = /[\w.-]+\/[\w.-]+/.test(gh.value);
  const date = rel.value.match(/(20\d\d-\d\d-\d\d)/);
  const section = r.sections.find((s) => s.primary)?.section ?? r.sections[0]?.section ?? '';
  const decay = (r as unknown as { decay_cause?: string }).decay_cause;
  return {
    id: r.id,
    name: r.name,
    section,
    tier: r.tier,
    url: r.url,
    desc: fact(r, 'desc').value.slice(0, 260),
    ...hosting(dep.value, oss, hasRepo),
    oss,
    mcp: mcpTri(mcp.value),
    facts: {
      license: lic,
      deployment: dep,
      mcp,
      pricing: fact(r, 'pricing'),
      release: rel,
      gh,
      conflictText: fact(r, 'contradiction')
    },
    storage: tax(r, 'storage'),
    unit: tax(r, 'unit'),
    conflict: tax(r, 'conflict'),
    retrieval: tax(r, 'retrieval'),
    stars: stars(gh.value),
    releaseDate: date ? date[1] : null,
    status:
      status ??
      (decay ? { status: decay, severity: decay === 'research-complete' ? 1 : 3, note: decay } : { status: 'active', severity: 0, note: '' })
  };
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

const CONFLICT_MATCH: Record<Exclude<Conflict, 'any'>, string[]> = {
  history: ['bi-temporal', 'document-version', 'grounded-ranking'],
  latest: ['overwrite', 'last-write-wins', 'deterministic-overwrite'],
  llm: ['llm-arbitrate']
};
const CONFLICT_LABEL: Record<Exclude<Conflict, 'any'>, string> = {
  history: 'keeps history when facts change',
  latest: 'latest value wins',
  llm: 'an LLM resolves conflicts'
};
const SHAPE_MATCH: Record<Exclude<Shape, 'any'>, (i: ChooserItem) => boolean> = {
  facts: (i) => i.unit.some((u) => ['fact', 'profile'].includes(u)),
  conversations: (i) => i.unit.some((u) => ['episode', 'turn', 'summary', 'trajectory'].includes(u)),
  documents: (i) => i.unit.some((u) => ['document', 'chunk', 'file'].includes(u)),
  relationships: (i) => i.storage.includes('graph') || i.retrieval.includes('graph-traversal')
};
const SHAPE_LABEL: Record<Exclude<Shape, 'any'>, string> = {
  facts: 'stores user facts and preferences',
  conversations: 'stores conversation history',
  documents: 'stores documents and knowledge',
  relationships: 'models relationships as a graph'
};

export interface Reason {
  text: string;
  citation?: string | null;
}

export interface Scored {
  item: ChooserItem;
  score: number;
  reasons: Reason[];
  /** Requirements the catalog can't confirm for this system. */
  unconfirmed: string[];
  warning: string | null;
}

export interface ChooserResult {
  picks: Scored[];
  alsoConsider: Scored[];
  unconfirmed: Scored[];
  excludedCount: number;
  poolSize: number;
  /** Ids of every system that wasn't ruled out (for the comparison table). */
  fitIds: string[];
}

const TODAY = () => new Date();
const HOSTED_SECTIONS = new Set(['Framework-embedded memory', 'Platform-provider memory']);

function monthsSince(iso: string): number {
  const d = new Date(iso + 'T00:00:00Z');
  const t = TODAY();
  return (t.getUTCFullYear() - d.getUTCFullYear()) * 12 + (t.getUTCMonth() - d.getUTCMonth());
}

export function score(item: ChooserItem, a: Answers): Scored | 'excluded' {
  if (item.status.severity >= 3) return 'excluded';
  const reasons: Reason[] = [];
  const unconfirmed: string[] = [];

  // Hard requirements: confirmed → reason; unknown → unconfirmed list; no → excluded.
  const req = (want: boolean, have: Tri, label: string, f: Fact) => {
    if (!want) return true;
    if (have === 'no') return false;
    if (have === 'unknown') unconfirmed.push(label);
    else reasons.push({ text: `${label}: ${f.value || 'yes'}`, citation: f.citation });
    return true;
  };
  if (!req(a.hosting === 'self', item.selfHost, 'Self-hostable', item.facts.deployment.value ? item.facts.deployment : item.facts.license)) return 'excluded';
  if (!req(a.hosting === 'managed', item.managed, 'Managed service', item.facts.deployment)) return 'excluded';
  if (!req(a.oss, item.oss, 'Open source', item.facts.license)) return 'excluded';
  if (!req(a.mcp, item.mcp, 'MCP', item.facts.mcp)) return 'excluded';

  let s = 0;
  if (a.conflict !== 'any') {
    if (item.conflict.some((c) => CONFLICT_MATCH[a.conflict as Exclude<Conflict, 'any'>].includes(c))) {
      s += 4;
      reasons.push({
        text: `Conflict handling: ${CONFLICT_LABEL[a.conflict as Exclude<Conflict, 'any'>]} (${item.conflict.join(', ')})`,
        citation: item.facts.conflictText.citation
      });
    } else if (!item.conflict.length) {
      unconfirmed.push('how it handles changing facts');
    }
  }
  if (a.shape !== 'any') {
    if (SHAPE_MATCH[a.shape as Exclude<Shape, 'any'>](item)) {
      s += 3;
      reasons.push({ text: `Memory model: ${SHAPE_LABEL[a.shape as Exclude<Shape, 'any'>]} (${[...new Set([...item.unit, ...item.storage])].slice(0, 4).join(', ')})` });
    } else if (!item.unit.length && !item.storage.length) {
      unconfirmed.push('its memory model');
    }
  }
  // Maturity signals. For memory built into a framework or platform, the
  // repo's stars measure the host (n8n, LlamaIndex…), not its memory, so
  // they count for less and are labelled as such.
  const hosted = HOSTED_SECTIONS.has(item.section);
  s += { 1: 3, 2: 2, 3: 1 }[item.tier] ?? 0;
  if (a.building === 'app' && item.section === 'Dedicated memory layers') s += 1;
  if (item.stars) {
    s += Math.min(2.5, Math.log10(item.stars) - 2) * (hosted ? 0.4 : 1);
    const gh = item.facts.gh.value.split(' — ').slice(0, 2).join(' — ');
    reasons.push({ text: hosted ? `Adoption (of the host framework): ${gh}` : `Adoption: ${gh}`, citation: item.facts.gh.citation });
  }
  if (item.releaseDate && monthsSince(item.releaseDate) <= 6) {
    s += 1;
    reasons.push({ text: `Recently released: ${item.facts.release.value}`, citation: item.facts.release.citation });
  }
  if (!a.oss && item.oss === 'yes') reasons.push({ text: `Licence: ${item.facts.license.value}`, citation: item.facts.license.citation });
  if (a.hosting === 'any' && item.facts.deployment.value) reasons.push({ text: `Deployment: ${item.facts.deployment.value}`, citation: item.facts.deployment.citation });
  if (item.facts.pricing.value) reasons.push({ text: `Pricing: ${item.facts.pricing.value}`, citation: item.facts.pricing.citation });

  const warning = item.status.severity >= 1 && item.status.status !== 'active'
    ? `${item.status.status}${item.status.note ? ' — ' + item.status.note : ''}`
    : null;
  if (warning) s -= item.status.severity;

  return { item, score: Math.round(s * 10) / 10, reasons: reasons.slice(0, 6), unconfirmed, warning };
}

export function choose(items: ChooserItem[], a: Answers): ChooserResult {
  const pool = items.filter((i) => POOLS[a.building].includes(i.section));
  let excluded = 0;
  const ok: Scored[] = [];
  const maybe: Scored[] = [];
  for (const i of pool) {
    const r = score(i, a);
    if (r === 'excluded') {
      excluded++;
      continue;
    }
    // Unconfirmed hard requirements go to "might fit"; unconfirmed soft
    // preferences only lower confidence.
    const hardUnknown = r.unconfirmed.some((u) => ['Self-hostable', 'Managed service', 'Open source', 'MCP'].includes(u));
    (hardUnknown ? maybe : ok).push(r);
  }
  const byScore = (x: Scored, y: Scored) => y.score - x.score || (y.item.stars ?? 0) - (x.item.stars ?? 0) || x.item.name.localeCompare(y.item.name);
  ok.sort(byScore);
  maybe.sort(byScore);
  return {
    picks: ok.slice(0, 3),
    alsoConsider: ok.slice(3, 9),
    unconfirmed: maybe.slice(0, 8),
    excludedCount: excluded,
    poolSize: pool.length,
    fitIds: [...ok, ...maybe].map((x) => x.item.id)
  };
}

// ---------------------------------------------------------------------------
// URL state
// ---------------------------------------------------------------------------

export function answersToParams(a: Answers): URLSearchParams {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(a)) {
    if (v !== (DEFAULT_ANSWERS as unknown as Record<string, unknown>)[k]) p.set(k, String(v));
  }
  return p;
}

export function paramsToAnswers(p: URLSearchParams): Answers {
  const a = { ...DEFAULT_ANSWERS };
  const pick = <T extends string>(k: string, allowed: readonly T[]): T | undefined => {
    const v = p.get(k);
    return v && (allowed as readonly string[]).includes(v) ? (v as T) : undefined;
  };
  a.building = pick('building', ['app', 'coding'] as const) ?? a.building;
  a.hosting = pick('hosting', ['self', 'managed', 'any'] as const) ?? a.hosting;
  a.conflict = pick('conflict', ['history', 'latest', 'llm', 'any'] as const) ?? a.conflict;
  a.shape = pick('shape', ['facts', 'conversations', 'documents', 'relationships', 'any'] as const) ?? a.shape;
  a.oss = p.get('oss') === 'true';
  a.mcp = p.get('mcp') === 'true';
  return a;
}
