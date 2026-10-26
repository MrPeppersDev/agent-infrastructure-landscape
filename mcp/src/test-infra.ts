// Tests for chooser-infra.ts (framework / data-store chooser) and compat.ts
// (compatibility check) against the real catalog.
// Run: npm run build && node dist/test-infra.js
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { toItem, brand, type ChooserItem } from './chooser.js';
import { chooseInfra, DEFAULT_INFRA, NEEDS, paramsToInfra, infraToParams, inNeed } from './chooser-infra.js';
import { compatibility, worksWith, allLinks, aliasesOf, setAliases } from './compat.js';

const here = dirname(fileURLToPath(import.meta.url));
function find(name: string): string {
  let dir = here;
  for (let i = 0; i < 6; i++) {
    for (const p of [join(dir, 'data', name), join(dir, name), join(dir, 'taxonomy', name)]) {
      try { readFileSync(p); return p; } catch { /* next */ }
    }
    dir = dirname(dir);
  }
  throw new Error(`${name} not found`);
}
const L = JSON.parse(readFileSync(find('landscape.json'), 'utf-8'));
const E = JSON.parse(readFileSync(find('landscape.edges.json'), 'utf-8')).edges;
const S = JSON.parse(readFileSync(find('stack-index.json'), 'utf-8')).records;
setAliases(JSON.parse(readFileSync(find('system-aliases.json'), 'utf-8')).aliases);
const items: ChooserItem[] = L.records.map((r: Parameters<typeof toItem>[0]) => toItem(r, S[r.id]));
const idOf = (n: string) => L.records.find((r: { name: string }) => r.name === n)?.id as string;

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  console.log(`  ${ok ? 'PASS' : 'FAIL'} ${name}${ok ? '' : ' ' + detail}`);
  if (!ok) failures++;
};

console.log('chooser-infra');
for (const kind of ['framework', 'data'] as const) {
  for (const need of NEEDS[kind]) {
    const r = chooseInfra(items, { ...DEFAULT_INFRA[kind], need: need.value });
    check(`${kind}/${need.value}: has a pool`, r.poolSize > 0, String(r.poolSize));
    check(`${kind}/${need.value}: nothing archived recommended`, [...r.picks, ...r.alsoConsider].every((s) => s.item.status.severity < 3));
    const brands = [...r.picks, ...r.alsoConsider].map((s) => brand(s.item.name) ?? s.item.id);
    check(`${kind}/${need.value}: one product per brand`, new Set(brands).size === brands.length, brands.join(','));
  }
}
{
  const r = chooseInfra(items, { ...DEFAULT_INFRA.data, hosting: 'self', oss: true });
  check('data self+oss: picks confirm both', r.picks.every((p) => p.item.selfHost === 'yes' && p.item.oss === 'yes'));
}
{
  const r = chooseInfra(items, { ...DEFAULT_INFRA.data, existing: true });
  check('data existing: a Postgres/Mongo/Elastic option ranks first', /pgvector|postgres|mongo|elastic|opensearch|redis|supabase/i.test(r.picks[0]?.item.name ?? ''), r.picks[0]?.item.name);
}
{
  const lib = NEEDS.framework.find((n) => n.value === 'library')!;
  const pool = items.filter((i) => inNeed(i, lib)).map((i) => i.name);
  check('framework/library excludes protocols', !pool.some((n) => /Model Context Protocol|Agent2Agent/.test(n)), pool.join(','));
  check('framework/library keeps LangGraph', pool.some((n) => n.startsWith('LangGraph')));
}
{
  const a = { ...DEFAULT_INFRA.framework, language: 'python' as const, oss: true };
  check('infra params round-trip', JSON.stringify(paramsToInfra('framework', new Map(Object.entries(infraToParams(a))) as never)) === JSON.stringify(a));
}

console.log('compat');
{
  const mem0 = idOf('Mem0'), qdrant = idOf('Qdrant'), neo4j = idOf('Neo4j');
  const r = compatibility(L.records, E, [mem0, qdrant, neo4j]);
  check('three systems → three pairs', r.pairs.length === 3, String(r.pairs.length));
  const mq = r.pairs.find((p) => [p.a, p.b].includes(mem0) && [p.a, p.b].includes(qdrant));
  check('Mem0 + Qdrant documented', mq?.status === 'documented', mq?.status);
  check('evidence carries a source', !!mq?.evidence.some((e) => e.citation));
  const missing = compatibility(L.records, E, [mem0, 'no-such-id']);
  check('unknown ids reported', missing.missing.includes('no-such-id'));
  check('works-with Qdrant lists Mem0', worksWith(L.records, E, qdrant).some((w) => w.id === mem0));
}
{
  const links = allLinks(L.records, E);
  const deg = new Map<string, number>();
  for (const l of links) if (l.status === 'documented') for (const x of [l.a, l.b]) deg.set(x, (deg.get(x) ?? 0) + 1);
  const name = new Map(L.records.map((r: { id: string; name: string }) => [r.id, r.name]));
  const noisy = [...deg].filter(([id, n]) => n > 30 && !/Claude|GPT|Model Context Protocol|Claude Code/.test(String(name.get(id))));
  check('no system over-matched by a generic alias', noisy.length === 0, noisy.map(([id, n]) => `${name.get(id)}:${n}`).join(', '));
  check('aliases never a bare one-word brand of a multi-word name', aliasesOf({ id: 'x', name: 'Stack AI', cells: {} }).every((a) => a !== 'Stack'));
}

if (failures) {
  console.error(`${failures} failure(s)`);
  process.exit(1);
}
console.log('all infra tests passed');
