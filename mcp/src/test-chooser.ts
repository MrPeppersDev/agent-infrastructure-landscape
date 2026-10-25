// Tests for chooser.ts (choose + alternatives) against the real catalog.
// Run: npm run build && node dist/test-chooser.js
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { toItem, choose, alternatives, alternativesFor, DEFAULT_ANSWERS, paramsToAnswers, answersToParams, type ChooserItem } from './chooser.js';

const here = dirname(fileURLToPath(import.meta.url));
function find(name: string): string {
  let dir = here;
  for (let i = 0; i < 6; i++) {
    for (const p of [join(dir, 'data', name), join(dir, name)]) {
      try { readFileSync(p); return p; } catch { /* next */ }
    }
    dir = dirname(dir);
  }
  throw new Error(`${name} not found`);
}
const L = JSON.parse(readFileSync(find('landscape.json'), 'utf-8'));
const S = JSON.parse(readFileSync(find('stack-index.json'), 'utf-8')).records;
const items: ChooserItem[] = L.records.map((r: Parameters<typeof toItem>[0]) => toItem(r, S[r.id]));
const byName = (n: string) => items.find((i) => i.name === n)!;

let failures = 0;
const check = (name: string, ok: boolean, detail = '') => {
  console.log(`  ${ok ? 'PASS' : 'FAIL'} ${name}${ok ? '' : ' ' + detail}`);
  if (!ok) failures++;
};

{
  const r = choose(items, DEFAULT_ANSWERS);
  check('defaults give 3 picks', r.picks.length === 3, String(r.picks.length));
  check('no archived system recommended', [...r.picks, ...r.alsoConsider].every((s) => s.item.status.severity < 3));
  check('every pick has a cited reason', r.picks.every((p) => p.reasons.some((x) => !!x.citation)));
}
{
  const r = choose(items, { ...DEFAULT_ANSWERS, hosting: 'self', oss: true, mcp: true });
  check('must-haves confirmed for picks', r.picks.every((p) => p.item.oss === 'yes' && p.item.mcp === 'yes' && p.item.selfHost === 'yes'));
  check('unconfirmed must-haves go to "might fit"', r.unconfirmed.every((u) => u.unconfirmed.length > 0));
}
{
  const r = choose(items, { ...DEFAULT_ANSWERS, conflict: 'history', shape: 'relationships' });
  check('history+graph puts Zep & Graphiti first', r.picks[0]?.item.name === 'Zep & Graphiti', r.picks.map((p) => p.item.name).join(', '));
}
{
  const a = { ...DEFAULT_ANSWERS, hosting: 'self' as const, oss: true };
  const p = answersToParams(a);
  check('URL round-trip', JSON.stringify(paramsToAnswers({ get: (k) => p[k] ?? null })) === JSON.stringify(a));
}
{
  const flowise = byName('Flowise Memory');
  const alts = alternatives(flowise, items.filter((i) => i.section === flowise.section), 5);
  check('alternatives exclude the target and archived systems', alts.every((x) => x.id !== flowise.id && !/archived/.test(x.warning ?? '')));
  check('alternatives have reasons', alts.length > 0 && alts.every((x) => x.why.length > 0));
  const mcp = byName('Mem0 MCP (official)');
  const ma = alternatives(mcp, items, 6);
  check('other packagings of the same product are skipped', !ma.some((x) => /^mem0\b/i.test(x.name)), ma.map((x) => x.name).join(', '));
  const chroma = byName('Chroma');
  const ca = alternatives(chroma, items.filter((i) => i.section === chroma.section), 4).map((x) => x.name);
  check('Chroma alternatives are vector DBs', ca.some((n) => /Qdrant|Milvus|Weaviate|Pinecone|LanceDB/.test(n)), ca.join(', '));
  const map = alternativesFor(L.records, [flowise.id], () => 'x', S, 3);
  check('alternativesFor returns up to n', (map[flowise.id] ?? []).length <= 3 && (map[flowise.id] ?? []).length > 0);
}

console.log(failures ? `\n${failures} failure(s)` : '\nall chooser tests passed');
process.exit(failures ? 1 : 0);
