// Memory-layer chooser (/choose): turn a few answers about what you're
// building into three cited picks, plus a side-by-side table.
//
// Pure and dependency-free (no imports), shared by the web app (/choose,
// /alternatives, /check — via web/src/lib/chooser.ts), the MCP server
// (choose_memory_layer, find_alternatives, check_stack) and the CLI.
//
// Honesty rules:
//   * Every reason shown is a catalogued cell value with its citation.
//   * A requirement is "met" only when the cell confirms it. When the cell
//     is empty ("searched not found"), the system goes in the "might fit —
//     unconfirmed" list instead of being silently dropped or recommended.
//   * Archived / deprecated / shut-down systems (stack-index severity >= 3)
//     are never recommended; acquired / maintenance / stale ones are
//     shown with a warning.

/** The subset of a catalog record the chooser reads (structurally
 * compatible with both the MCP and web LandscapeRecord types). */
export interface RecordLike {
  id: string;
  name: string;
  tier: number;
  url: string | null;
  sections: { section: string; primary: boolean }[];
  taxonomy: unknown;
  cells: unknown;
  decay_cause?: string;
}
type LandscapeRecord = RecordLike;

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
  /** The catalog's short type label ("TypeScript agent framework"). */
  type: string;
  selfHost: Tri;
  managed: Tri;
  oss: Tri;
  mcp: Tri;
  facts: Record<'license' | 'deployment' | 'mcp' | 'pricing' | 'release' | 'gh' | 'conflictText' | 'runtimes' | 'api' | 'sdk' | 'protocols' | 'maturity' | 'compliance', Fact>;
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

/** Shorten to <= max chars at a sentence end, else a word boundary + "…" —
 * never mid-word. */
export function clip(text: string, max: number): string {
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  const sentence = cut.lastIndexOf('. ');
  if (sentence > max * 0.5) return cut.slice(0, sentence + 1);
  const space = cut.lastIndexOf(' ');
  return (space > 0 ? cut.slice(0, space) : cut).replace(/[,;:(—-]+$/, '').trimEnd() + '…';
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

export function toItem(r: LandscapeRecord, status?: StackStatusLite | { status: string; severity: number; note: string }): ChooserItem {
  const lic = fact(r, 'license');
  const dep = fact(r, 'deployment');
  const mcp = fact(r, 'mcp-support');
  // v1.2.0 buyer cells (SCHEMA.md §2.5.11): enum sets, preferred over
  // parsing free text when filled.
  const protocols = fact(r, 'protocol-support');
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
    desc: clip(fact(r, 'desc').value, 260),
    type: clip(fact(r, 'type').value, 120),
    ...hosting(dep.value, oss, hasRepo),
    oss,
    mcp: /\bmcp-(server|client)\b/.test(protocols.value) ? 'yes' : mcpTri(mcp.value),
    facts: {
      license: lic,
      deployment: dep,
      mcp,
      pricing: fact(r, 'pricing'),
      release: rel,
      gh,
      conflictText: fact(r, 'contradiction'),
      runtimes: fact(r, 'runtimes'),
      api: fact(r, 'api-surface'),
      sdk: fact(r, 'sdk-languages'),
      protocols,
      maturity: fact(r, 'maturity'),
      compliance: fact(r, 'compliance-certifications')
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

export function monthsSince(iso: string): number {
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
  // Fit first (#359): tier, fit for an app's memory, fit facts the question
  // did not already require, documentation depth and a recent release.
  // GitHub stars are not scored; they break ties in the sort and are
  // labelled as the tiebreaker. For memory built into a framework or
  // platform the stars measure the host (n8n, LlamaIndex…), not its memory.
  const hosted = HOSTED_SECTIONS.has(item.section);
  s += { 1: 3, 2: 2, 3: 1 }[item.tier] ?? 0;
  if (a.building === 'app' && item.section === 'Dedicated memory layers') s += 1;
  if (!a.oss && item.oss === 'yes') reasons.push({ text: `Licence: ${item.facts.license.value}`, citation: item.facts.license.citation });
  if (a.hosting === 'any' && item.facts.deployment.value) reasons.push({ text: `Deployment: ${item.facts.deployment.value}`, citation: item.facts.deployment.citation });
  if (item.facts.pricing.value) reasons.push({ text: `Pricing: ${item.facts.pricing.value}`, citation: item.facts.pricing.citation });
  const known = [item.facts.license, item.facts.deployment, item.facts.gh, item.facts.release].filter((f) => f.value).length;
  s += known * 0.25;
  if (item.releaseDate && monthsSince(item.releaseDate) <= 6) {
    s += 1;
    reasons.push({ text: `Recently released: ${item.facts.release.value}`, citation: item.facts.release.citation });
  }
  if (item.stars) {
    const gh = item.facts.gh.value.split(' — ').slice(0, 2).join(' — ');
    reasons.push({ text: hosted ? `Adoption of the host framework (tiebreaker): ${gh}` : `Adoption (tiebreaker): ${gh}`, citation: item.facts.gh.citation });
  }

  const warning = item.status.severity >= 1 && item.status.status !== 'active'
    ? `${item.status.status}${item.status.note ? ' — ' + item.status.note : ''}`
    : null;
  if (warning) s -= item.status.severity;

  return { item, score: Math.round(s * 10) / 10, reasons: reasons.slice(0, 7), unconfirmed, warning };
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

/** Non-default answers as query-param pairs (pass to URLSearchParams). */
export function answersToParams(a: Answers): Record<string, string> {
  const p: Record<string, string> = {};
  for (const [k, v] of Object.entries(a)) {
    if (v !== (DEFAULT_ANSWERS as unknown as Record<string, unknown>)[k]) p[k] = String(v);
  }
  return p;
}

export function paramsToAnswers(p: { get(name: string): string | null }): Answers {
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

// ---------------------------------------------------------------------------
// Alternatives — "what else does what X does?"
// ---------------------------------------------------------------------------

export interface Alternative {
  id: string;
  name: string;
  section: string;
  /** Shared traits, in plain words (each from catalogued cells/taxonomy). */
  why: string[];
  similarity: number;
  warning: string | null;
  stars: number | null;
  oss: Tri;
  selfHost: Tri;
  managed: Tri;
  mcp: Tri;
  license: string;
  releaseDate: string | null;
}

const IGNORE = new Set(['none', 'none-trivial', 'out-of-scope']);

/** Shared values and overlap coefficient (|A∩B| / min(|A|,|B|)), which
 * doesn't punish a system for listing more values than the target. */
function overlap(a: string[], b: string[]): { score: number; shared: string[] } {
  const A = [...new Set(a.filter((x) => !IGNORE.has(x)))];
  const B = new Set(b.filter((x) => !IGNORE.has(x)));
  if (!A.length || !B.size) return { score: 0, shared: [] };
  const shared = A.filter((x) => B.has(x));
  return { score: shared.length / Math.min(A.length, B.size), shared };
}

function repoKey(i: ChooserItem): string | null {
  const m = i.facts.gh.value.match(/([\w.-]+)\/([\w.-]+)/) || (i.facts.gh.citation ?? '').match(/github\.com\/([\w.-]+)\/([\w.-]+)/);
  return m ? `${m[1]}/${m[2]}`.toLowerCase() : null;
}

export function brand(name: string): string | null {
  const t = name.toLowerCase().match(/[a-z0-9]+/);
  return t && t[0].length >= 3 && !['the', 'open', 'agent', 'memory', 'ai'].includes(t[0]) ? t[0] : null;
}

function host(u: string | null): string | null {
  const m = (u ?? '').match(/^https?:\/\/(?:www\.)?([^/]+)/i);
  return m ? m[1].toLowerCase() : null;
}

/**
 * Rank live systems that do what `target` does. Candidates come from the
 * caller (typically the same product family). Similarity is mostly the
 * memory taxonomy (storage, retrieval, conflict handling, memory unit)
 * plus same section and shared must-haves; maturity breaks ties.
 * Archived / shut-down systems and other packagings of the same product
 * (same GitHub repo or same site) are skipped.
 */
export function alternatives(target: ChooserItem, candidates: ChooserItem[], n = 5): Alternative[] {
  const tRepo = repoKey(target);
  const tHost = host(target.url);
  const tBrand = brand(target.name);
  const out: Alternative[] = [];
  for (const c of candidates) {
    if (c.id === target.id || c.status.severity >= 3) continue;
    const cRepo = repoKey(c);
    if ((tRepo && cRepo === tRepo) || (tHost && host(c.url) === tHost)) continue;
    // other packagings of the same product ("Mem0" vs "Mem0 MCP (official)")
    if (tBrand && brand(c.name) === tBrand) continue;
    const why: string[] = [];
    let sim = 0;
    if (c.section === target.section) {
      sim += 2;
      why.push(`also in ${c.section}`);
    }
    const axes: [keyof ChooserItem, string][] = [
      ['storage', 'storage'],
      ['retrieval', 'retrieval'],
      ['conflict', 'conflict handling'],
      ['unit', 'memory unit']
    ];
    for (const [k, label] of axes) {
      const o = overlap(target[k] as string[], c[k] as string[]);
      sim += o.score * 2;
      if (o.shared.length) why.push(`same ${label} (${o.shared.slice(0, 2).join(', ')})`);
    }
    if (target.oss === 'yes' && c.oss === 'yes') { sim += 0.7; why.push('also open source'); }
    if (target.selfHost === 'yes' && c.selfHost === 'yes') { sim += 0.4; why.push('also self-hostable'); }
    if (target.managed === 'yes' && c.managed === 'yes') { sim += 0.3; why.push('also offered managed'); }
    if (target.mcp === 'yes' && c.mcp === 'yes') { sim += 0.4; why.push('also has MCP'); }
    if (sim < 2) continue; // not meaningfully similar
    // maturity: live, adopted options should rise above research code
    // that merely shares a design (tiers 4–5 are papers / ideas)
    sim += ({ 1: 0.8, 2: 0.5, 3: 0.2, 4: -0.6, 5: -1 } as Record<number, number>)[c.tier] ?? 0;
    if (c.stars) sim += Math.min(0.6, Math.max(0, Math.log10(c.stars) - 2) * 0.2);
    if (c.status.severity >= 2) sim -= 1;
    out.push({
      id: c.id,
      name: c.name,
      section: c.section,
      why: why.slice(0, 7),
      similarity: Math.round(sim * 100) / 100,
      warning: c.status.severity >= 1 && c.status.status !== 'active' ? `${c.status.status}${c.status.note ? ' — ' + c.status.note : ''}` : null,
      stars: c.stars,
      oss: c.oss,
      selfHost: c.selfHost,
      managed: c.managed,
      mcp: c.mcp,
      license: c.facts.license.value,
      releaseDate: c.releaseDate
    });
  }
  out.sort((a, b) => b.similarity - a.similarity || (b.stars ?? 0) - (a.stars ?? 0) || a.name.localeCompare(b.name));
  return out.slice(0, n);
}

/** Section → product family id, for choosing the candidate pool. */
export type FamilyOf = (section: string) => string;

/**
 * Build items for every record once, then return alternatives for the
 * requested ids, drawing candidates from the same product family.
 */
export function alternativesFor(
  records: RecordLike[],
  ids: string[],
  familyOf: FamilyOf,
  status: Record<string, StackStatusLite | undefined> = {},
  n = 3
): Record<string, Alternative[]> {
  const items = records.map((r) => toItem(r, status[r.id]));
  const byId = new Map(items.map((i) => [i.id, i]));
  const byFamily = new Map<string, ChooserItem[]>();
  for (const i of items) {
    const f = familyOf(i.section);
    if (!byFamily.has(f)) byFamily.set(f, []);
    byFamily.get(f)!.push(i);
  }
  const out: Record<string, Alternative[]> = {};
  for (const id of ids) {
    const t = byId.get(id);
    if (!t) continue;
    out[id] = alternatives(t, byFamily.get(familyOf(t.section)) ?? [], n);
  }
  return out;
}
