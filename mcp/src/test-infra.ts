// Tests for chooser-infra.ts (framework / data-store chooser) and compat.ts
// (compatibility check) against the real catalog.
// Run: npm run build && node dist/test-infra.js
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { toItem, brand, type ChooserItem } from './chooser.js';
import { chooseInfra, scoreInfraDetailed, DEFAULT_INFRA, NEEDS, paramsToInfra, infraToParams, inNeed } from './chooser-infra.js';
import { compatibility, worksWith, allLinks, aliasesOf, setAliases } from './compat.js';
import { buildIndex, search, parseQuery, docText } from './search.js';

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
    const repos = [...r.picks, ...r.alsoConsider].map((s) => (s.item.facts.gh.value.match(/^\s*([\w.-]+\/[\w.-]+)/)?.[1] ?? s.item.id).toLowerCase());
    check(`${kind}/${need.value}: one product per repo`, new Set(repos).size === repos.length, repos.join(','));
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

{
  const r = chooseInfra(items, { ...DEFAULT_INFRA.framework, language: 'typescript' });
  check('framework typescript: has picks or might-fits', r.picks.length + r.unconfirmed.length > 0);
  check('framework typescript: Mastra or Vercel AI SDK considered', [...r.picks, ...r.alsoConsider, ...r.unconfirmed].some((s) => /Mastra|Vercel AI SDK/.test(s.item.name)));
}

{
  // Fit before adoption (#359): with the same tier, a well-documented record
  // with a recent release outranks a far more starred one whose licence and
  // deployment are unknown; stars only break ties and are labelled as such.
  const base = items.find((i) => i.name === 'Qdrant')!;
  const today = new Date().toISOString().slice(0, 10);
  const empty = { value: '', citation: null };
  const starred: ChooserItem = { ...base, id: 'x-starred', name: 'X Starred', stars: 150000, releaseDate: null, status: { status: 'active', severity: 0, note: '' },
    facts: { ...base.facts, license: empty, deployment: empty, release: empty, gh: { value: 'x/starred — ~150k stars', citation: 'https://github.com/x/starred' } } };
  const fit: ChooserItem = { ...base, id: 'y-fit', name: 'Y Fit', stars: 50, releaseDate: today, status: { status: 'active', severity: 0, note: '' },
    facts: { ...base.facts, release: { value: `v1.0 (${today})`, citation: 'https://example.com/release' }, gh: { value: 'y/fit — 50 stars', citation: 'https://github.com/y/fit' } } };
  const a = { ...DEFAULT_INFRA.data, oss: true, hosting: 'self' as const };
  const sx = scoreInfraDetailed(starred, a);
  const sy = scoreInfraDetailed(fit, a);
  check('fit-first: documented low-star record outranks undocumented high-star one', 'score' in sy && !('score' in sx && sx.score >= sy.score), JSON.stringify({ sx, sy }).slice(0, 200));
  if ('reasons' in sy) {
    check('fit-first: first reason is a must-have, not adoption', !/^Adoption/.test(sy.reasons[0]?.text ?? ''), sy.reasons[0]?.text);
    check('fit-first: adoption is last and labelled as the tiebreaker', /^Adoption \(tiebreaker\)/.test(sy.reasons[sy.reasons.length - 1]?.text ?? ''), sy.reasons.map((r) => r.text).join(' | '));
  }
  const tie: ChooserItem = { ...fit, id: 'z-tie', name: 'Z Tie', stars: 5000 };
  const r = chooseInfra([fit, tie], a);
  check('fit-first: equal fit falls back to stars', r.picks[0]?.item.id === 'z-tie', r.picks.map((p) => p.item.id).join(','));
}

console.log('compat');
{
  const mem0 = idOf('Mem0'), qdrant = idOf('Qdrant'), neo4j = idOf('Neo4j');
  const r = compatibility(L.records, E, [mem0, qdrant, neo4j]);
  check('three systems → three pairs', r.pairs.length === 3, String(r.pairs.length));
  const mq = r.pairs.find((p) => [p.a, p.b].includes(mem0) && [p.a, p.b].includes(qdrant));
  check('Mem0 + Qdrant documented', mq?.status === 'documented', mq?.status);
  check('evidence carries a source', !!mq?.evidence.some((e) => e.citation));
  check('curated edge evidence carries a verification date (#360)', !!mq?.evidence.some((e) => e.kind === 'edge' && /^\d{4}-\d{2}-\d{2}$/.test(e.verifiedAt ?? '')), JSON.stringify(mq?.evidence.filter((e) => e.kind === 'edge')).slice(0, 200));
  const missing = compatibility(L.records, E, [mem0, 'no-such-id']);
  check('unknown ids reported', missing.missing.includes('no-such-id'));
  check('works-with Qdrant lists Mem0', worksWith(L.records, E, qdrant).some((w) => w.id === mem0));
}
{
  const links = allLinks(L.records, E);
  const deg = new Map<string, number>();
  // Alias noise shows up in cell mentions; hubs with many curated
  // integration edges (extraction/integrations/) are legitimately busy.
  const byAlias = (l: (typeof links)[number]) => l.status === 'documented' && !l.evidence.some((e) => e.kind === 'edge');
  for (const l of links) if (byAlias(l)) for (const x of [l.a, l.b]) deg.set(x, (deg.get(x) ?? 0) + 1);
  const name = new Map(L.records.map((r: { id: string; name: string }) => [r.id, r.name]));
  const noisy = [...deg].filter(([id, n]) => n > 30 && !/Claude|GPT|Model Context Protocol|Claude Code/.test(String(name.get(id))));
  check('no system over-matched by a generic alias', noisy.length === 0, noisy.map(([id, n]) => `${name.get(id)}:${n}`).join(', '));
  check('aliases never a bare one-word brand of a multi-word name', aliasesOf({ id: 'x', name: 'Stack AI', cells: {} }).every((a) => a !== 'Stack'));
}

{
  // Every curated integration edge (extraction/integrations/*.json) must be
  // in the built edges file — guards against a build that drops the loader.
  const dir = join(dirname(find('landscape.json')), '..', 'extraction', 'integrations');
  let curated: { source: string; target: string }[] = [];
  try {
    curated = readdirSync(dir).filter((f) => f.endsWith('.json')).flatMap((f) => JSON.parse(readFileSync(join(dir, f), 'utf-8')));
  } catch { /* npm tarball: no extraction/ folder */ }
  if (curated.length) {
    const have = new Set(E.filter((e: { type: string }) => e.type === 'integrates-with').map((e: { source: string; target: string }) => `${e.source}>${e.target}`));
    const missing = curated.filter((c) => !have.has(`${c.source}>${c.target}`));
    check('curated integration edges are all built', missing.length === 0, `${missing.length} of ${curated.length} missing`);
  }
}

console.log('search');
{
  const F = JSON.parse(readFileSync(find('families.json'), 'utf-8')).families as { id: string; sections: string[] }[];
  const fam = new Map<string, string>();
  for (const f of F) for (const sec of f.sections) fam.set(sec, f.id);
  const ix = buildIndex(L.records.map((r: { id: string; cells: unknown }, n: number) => ({ item: items[n], text: docText(r.cells), family: fam.get(items[n].section) ?? 'other' })));
  const p = parseQuery('self-hosted vector db with MCP, python');
  check('parses requirements', ['self-hostable', 'MCP support', 'Python SDK'].every((l) => p.constraints.some((c) => c.label === l)), p.constraints.map((c) => c.label).join(','));
  const r = search(ix, 'self-hosted vector db with MCP, python', 10);
  check('requirements never contradicted', r.hits.every((h) => {
    const i = items.find((x) => x.id === h.id)!;
    return i.selfHost !== 'no' && i.mcp !== 'no';
  }));
  check('vector db query returns data-family systems', r.hits.length > 0 && r.hits.every((h) => h.family === 'data'));
  const g = search(ix, 'open source graph memory with temporal history', 5);
  check('graph+temporal finds Zep/Graphiti first', /Zep|Graphiti/.test(g.hits[0]?.name ?? ''), g.hits[0]?.name);
  const s = search(ix, 'sandbox for running agent code', 5);
  check('sandbox query finds a sandbox', s.hits.some((h) => /e2b|Daytona|Modal/i.test(h.name)), s.hits.map((h) => h.name).join(','));
}

if (failures) {
  console.error(`${failures} failure(s)`);
  process.exit(1);
}
console.log('all infra tests passed');
