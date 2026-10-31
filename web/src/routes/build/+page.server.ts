// /build — whole-stack composer (logic: mcp/src/composer.ts). Ships only
// the records in the layers' sections, with only the cells the composer
// reads, and the edges between them.
import { getRecords, getEdges } from '$lib/data';
import { toItem, POOLS, type StackStatusLite } from '$lib/chooser';
import { LAYERS } from '../../../../mcp/src/composer';
import { INTEGRATION_CELLS } from '../../../../mcp/src/compat';
import { SHEET_COLUMNS } from '../../../../mcp/src/procurement';
import stackIndex from '../../../../data/stack-index.json';
import migrations from '../../../../data/migrations.json';
import stackPricing from '../../../../data/pricing/stack.json';
import memoryPricing from '../../../../data/pricing/memory.json';
import vectorPricing from '../../../../data/pricing/vector.json';

export const prerender = true;

// desc / claims mentions only ever make a pair "mentioned", never
// "documented", so they're left out to keep the page small.
const KEEP_CELLS = new Set([...Object.keys(INTEGRATION_CELLS).filter((c) => c !== 'desc' && c !== 'claims'), 'developer-activity-opendigger', ...SHEET_COLUMNS.map((c) => c.slug)]);
const LINK_EDGES = new Set(['integrates-with', 'built-on', 'runtime-dependency', 'extends', 'forks']);

export const load = () => {
  const sections = new Set([...LAYERS.flatMap((l) => l.sections), ...POOLS.app, ...POOLS.coding, 'Memory benchmarks & evaluation']);
  const status = (stackIndex as unknown as { records: Record<string, StackStatusLite> }).records;
  const recs = getRecords().filter((r) => sections.has(r.sections.find((s) => s.primary)?.section ?? ''));
  const ids = new Set(recs.map((r) => r.id));
  const items = recs.map((r) => {
    const s = status[r.id];
    return toItem(r, s ? { status: s.status, severity: s.severity, note: s.note } : undefined);
  });
  const records = recs.map((r) => ({
    id: r.id,
    name: r.name,
    tier: r.tier,
    url: r.url,
    sections: r.sections,
    taxonomy: {},
    last_verified_at: r.last_verified_at ?? null,
    cells: Object.fromEntries(Object.entries(r.cells).filter(([k]) => KEEP_CELLS.has(k)))
  }));
  const edges = getEdges()
    .filter((e) => LINK_EDGES.has(e.type) && ids.has(e.source) && ids.has(e.target))
    .map(({ source, target, type, evidence, citation }) => ({ source, target, type, evidence, citation }));
  const notes = (migrations as unknown as { notes: { id: string; summary: string; sources: string[] }[] }).notes
    .filter((n) => ids.has(n.id))
    .map(({ id, summary, sources }) => ({ id, summary, sources }));
  return { items, records, edges, migrations: notes, pricing: { stack: stackPricing, memory: memoryPricing, vector: vectorPricing } };
};
