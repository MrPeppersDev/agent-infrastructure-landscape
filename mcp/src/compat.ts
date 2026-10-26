// Compatibility check: "do these systems work together?"
//
// For every pair of selected systems, collect the catalog's evidence that
// they integrate:
//   1. typed edges between them (integrates-with, built-on,
//      runtime-dependency, extends, forks) with the edge's evidence;
//   2. one system's integration cells (backend storage, adjacent
//      infrastructure, API surface, embedding model, MCP, claims…) naming
//      the other, with that cell's citation.
// A pair with no evidence is "not recorded", never "incompatible": the
// catalog only knows what it has a source for.
//
// Pure and dependency-free; shared by the web /compatibility page, the MCP
// tool `check_compatibility` and the CLI.

export interface CompatRecord {
  id: string;
  name: string;
  cells: unknown;
}

export interface CompatEdge {
  source: string;
  target: string;
  type: string;
  evidence?: string;
  citation?: string | null;
}

export type CompatEvidence =
  | { kind: 'edge'; type: string; from: string; to: string; text: string; citation: string | null }
  | { kind: 'cell'; in: string; cell: string; text: string; citation: string | null };

export interface CompatPair {
  a: string;
  b: string;
  status: 'documented' | 'mentioned' | 'not-recorded';
  evidence: CompatEvidence[];
}

const LINK_EDGES = new Set(['integrates-with', 'built-on', 'runtime-dependency', 'extends', 'forks']);
export const INTEGRATION_CELLS: Record<string, string> = {
  'backend-storage': 'backend storage',
  'adjacent-infrastructure': 'adjacent infrastructure',
  'api-surface': 'API surface',
  'embedding-model': 'embedding model',
  'mcp-support': 'MCP support',
  runtimes: 'runtimes',
  deployment: 'deployment',
  claims: 'claims',
  desc: 'description'
};
/** Extra names a system goes by (taxonomy/system-aliases.json), keyed by
 * record name. */
export type AliasMap = Record<string, string[]>;
let ALIASES: AliasMap = {};
export function setAliases(a: AliasMap): void {
  ALIASES = a;
}

function esc(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Names a record is likely to be referred to by in another record's text:
 * its full name without parentheticals, slash-separated parts, a "(now X)"
 * rename, and curated aliases. A bare brand token ("Stack", "Redis") is
 * deliberately not used: it matches far too much prose. */
export function aliasesOf(r: CompatRecord): string[] {
  const out = new Set<string>();
  const base = r.name.replace(/\s*\([^)]*\)\s*/g, ' ').replace(/\s+/g, ' ').trim();
  if (base.length >= 3) out.add(base);
  for (const part of base.split(/\s*[\/·]\s*/)) if (part.length >= 4) out.add(part.trim());
  const now = r.name.match(/\(now ([^)]+)\)/);
  if (now) out.add(now[1].trim());
  for (const a of ALIASES[r.name] ?? []) out.add(a);
  return [...out];
}

function cellText(r: CompatRecord, slug: string): { value: string; citation: string | null } | null {
  const c = (r.cells as Record<string, { value?: string; status?: string; citation?: string | null } | undefined>)[slug];
  if (!c || !c.value || ['no-data', 'not-applicable', 'depth-floor-reached'].includes(c.status ?? '')) return null;
  return { value: String(c.value), citation: c.citation ?? null };
}

function snippet(text: string, idx: number, len: number): string {
  const start = Math.max(0, text.lastIndexOf(' ', Math.max(0, idx - 70)));
  const end = Math.min(text.length, idx + len + 90);
  return `${start > 0 ? '…' : ''}${text.slice(start, end).trim()}${end < text.length ? '…' : ''}`;
}

function mentions(inRec: CompatRecord, of: CompatRecord): CompatEvidence[] {
  const rx = aliasesOf(of).map((a) => new RegExp(`(^|[^\\w-])${esc(a)}(?![\\w-])`, 'i'));
  const out: CompatEvidence[] = [];
  for (const [slug, label] of Object.entries(INTEGRATION_CELLS)) {
    const c = cellText(inRec, slug);
    if (!c) continue;
    for (const r of rx) {
      const m = c.value.match(r);
      if (m && m.index !== undefined) {
        out.push({ kind: 'cell', in: inRec.id, cell: label, text: snippet(c.value, m.index, m[0].length), citation: c.citation });
        break;
      }
    }
  }
  return out;
}

export function compatibility(records: CompatRecord[], edges: CompatEdge[], ids: string[]): { systems: { id: string; name: string }[]; pairs: CompatPair[]; missing: string[] } {
  const byId = new Map(records.map((r) => [r.id, r]));
  const sel = [...new Set(ids)].map((id) => byId.get(id)).filter((r): r is CompatRecord => !!r);
  const missing = ids.filter((id) => !byId.has(id));
  const pairs: CompatPair[] = [];
  for (let i = 0; i < sel.length; i++) {
    for (let j = i + 1; j < sel.length; j++) {
      const a = sel[i], b = sel[j];
      const ev: CompatEvidence[] = [];
      for (const e of edges) {
        if (!LINK_EDGES.has(e.type)) continue;
        if ((e.source === a.id && e.target === b.id) || (e.source === b.id && e.target === a.id)) {
          ev.push({ kind: 'edge', type: e.type, from: e.source, to: e.target, text: e.evidence ?? '', citation: e.citation ?? null });
        }
      }
      ev.push(...mentions(a, b), ...mentions(b, a));
      const status = ev.some((e) => e.kind === 'edge' && e.type !== 'competes-with')
        ? 'documented'
        : ev.some((e) => e.kind === 'cell' && e.cell !== 'description' && e.cell !== 'claims')
          ? 'documented'
          : ev.length
            ? 'mentioned'
            : 'not-recorded';
      pairs.push({ a: a.id, b: b.id, status, evidence: ev.slice(0, 6) });
    }
  }
  return { systems: sel.map((r) => ({ id: r.id, name: r.name })), pairs, missing };
}

/** Systems the catalog records as integrating with `id` (edges + cell
 * mentions in either direction), for "what works with X?". */
export function worksWith(records: CompatRecord[], edges: CompatEdge[], id: string, limit = 40): { id: string; name: string; evidence: CompatEvidence[] }[] {
  const target = records.find((r) => r.id === id);
  if (!target) return [];
  const out = new Map<string, CompatEvidence[]>();
  const add = (oid: string, e: CompatEvidence) => {
    if (oid === id) return;
    (out.get(oid) ?? out.set(oid, []).get(oid)!).push(e);
  };
  for (const e of edges) {
    if (!LINK_EDGES.has(e.type)) continue;
    if (e.source === id) add(e.target, { kind: 'edge', type: e.type, from: e.source, to: e.target, text: e.evidence ?? '', citation: e.citation ?? null });
    if (e.target === id) add(e.source, { kind: 'edge', type: e.type, from: e.source, to: e.target, text: e.evidence ?? '', citation: e.citation ?? null });
  }
  for (const r of records) {
    if (r.id === id) continue;
    for (const e of mentions(r, target)) if (e.kind === 'cell' && e.cell !== 'description' && e.cell !== 'claims') add(r.id, e);
    for (const e of mentions(target, r)) if (e.kind === 'cell' && e.cell !== 'description' && e.cell !== 'claims') add(r.id, e);
  }
  const name = new Map(records.map((r) => [r.id, r.name]));
  return [...out.entries()]
    .map(([oid, evidence]) => ({ id: oid, name: name.get(oid) ?? oid, evidence }))
    .sort((x, y) => y.evidence.length - x.evidence.length || x.name.localeCompare(y.name))
    .slice(0, limit);
}

/** Every pair with any integration evidence, computed once (for a static
 * page). O(n²) regex tests over the integration cells; ~1 s for 1k records. */
export function allLinks(records: CompatRecord[], edges: CompatEdge[]): CompatPair[] {
  const key = (a: string, b: string) => (a < b ? `${a}\u0000${b}` : `${b}\u0000${a}`);
  const acc = new Map<string, CompatEvidence[]>();
  const push = (a: string, b: string, e: CompatEvidence) => {
    const k = key(a, b);
    (acc.get(k) ?? acc.set(k, []).get(k)!).push(e);
  };
  const ids = new Set(records.map((r) => r.id));
  for (const e of edges) {
    if (!LINK_EDGES.has(e.type) || !ids.has(e.source) || !ids.has(e.target) || e.source === e.target) continue;
    push(e.source, e.target, { kind: 'edge', type: e.type, from: e.source, to: e.target, text: e.evidence ?? '', citation: e.citation ?? null });
  }
  const rxs = records.map((r) => ({ r, rx: aliasesOf(r).map((a) => new RegExp(`(^|[^\\w-])${esc(a)}(?![\\w-])`, 'i')) }));
  for (const inRec of records) {
    const cells = Object.entries(INTEGRATION_CELLS)
      .map(([slug, label]) => ({ label, c: cellText(inRec, slug) }))
      .filter((x): x is { label: string; c: { value: string; citation: string | null } } => !!x.c);
    if (!cells.length) continue;
    for (const { r: of, rx } of rxs) {
      if (of.id === inRec.id) continue;
      for (const { label, c } of cells) {
        let m: RegExpMatchArray | null = null;
        for (const x of rx) if ((m = c.value.match(x))) break;
        if (m && m.index !== undefined) {
          push(inRec.id, of.id, { kind: 'cell', in: inRec.id, cell: label, text: snippet(c.value, m.index, m[0].length), citation: c.citation });
        }
      }
    }
  }
  const out: CompatPair[] = [];
  for (const [k, ev] of acc) {
    const [a, b] = k.split('\u0000');
    const status = ev.some((e) => e.kind === 'edge') || ev.some((e) => e.kind === 'cell' && e.cell !== 'description' && e.cell !== 'claims')
      ? 'documented'
      : 'mentioned';
    out.push({ a, b, status, evidence: ev.slice(0, 6) });
  }
  return out;
}
