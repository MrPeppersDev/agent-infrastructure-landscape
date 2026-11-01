// Tests for `--silo` scoping (HANDOFF §8.1): each silo's tools exist, a
// scoped server lists only the discovery tools plus the silo's own, and
// search defaults to the silo's sections.
// Run: npm run build && node dist/test-silos.js
import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadSilos, loadRecords, inSilo } from './data.js';

const server = join(dirname(fileURLToPath(import.meta.url)), 'server.js');
let failures = 0;
function ok(cond: unknown, msg: string): void {
  if (!cond) {
    failures++;
    console.error(`FAIL: ${msg}`);
  }
}

/** Start the stdio server with `args`, send JSON-RPC requests, return the responses by id. */
function rpc(args: string[], requests: object[]): Promise<Map<number, any>> {
  return new Promise((resolve, reject) => {
    const p = spawn(process.execPath, [server, ...args], { stdio: ['pipe', 'pipe', 'pipe'] });
    const out = new Map<number, any>();
    let buf = '';
    let err = '';
    const want = requests.filter((r: any) => 'id' in r).length;
    const timer = setTimeout(() => { p.kill(); reject(new Error(`timeout; stderr: ${err}`)); }, 60000);
    p.stderr.on('data', (d) => (err += d));
    p.stdout.on('data', (d) => {
      buf += d;
      let i;
      while ((i = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        if (!line) continue;
        const m = JSON.parse(line);
        if (m.id !== undefined) out.set(m.id, m);
        if (out.size === want) { clearTimeout(timer); p.kill(); resolve(out); }
      }
    });
    p.on('exit', (code) => { if (out.size < want) { clearTimeout(timer); reject(new Error(`exited ${code}: ${err}`)); } });
    for (const r of requests) p.stdin.write(JSON.stringify({ jsonrpc: '2.0', ...r }) + '\n');
  });
}

const init = { id: 0, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'test', version: '0' } } };
const initialized = { method: 'notifications/initialized' };

const full = await rpc([], [init, initialized, { id: 1, method: 'tools/list' }]);
const allTools = new Set<string>(full.get(1).result.tools.map((t: any) => t.name));
ok(allTools.size > 20, `unscoped server lists every tool (${allTools.size})`);

const silos = loadSilos();
ok(silos.length >= 5, 'silos load from taxonomy/silos.json');
for (const s of silos) for (const t of s.mcpTools ?? []) ok(allTools.has(t), `silo ${s.id}: tool ${t} exists`);

const memory = silos.find((s) => s.id === 'memory')!;
const scoped = await rpc(['--silo', 'memory'], [
  init,
  initialized,
  { id: 1, method: 'tools/list' },
  { id: 2, method: 'tools/call', params: { name: 'search_records', arguments: { query: 'a', limit: 200 } } },
  { id: 3, method: 'tools/call', params: { name: 'search_records', arguments: { query: 'langchain', product: 'agents' } } }
]);
const names = scoped.get(1).result.tools.map((t: any) => t.name);
ok(names.includes('choose_memory_layer') && names.includes('search_records'), 'memory silo keeps its tools and search');
ok(!names.includes('estimate_vector_store_cost') && !names.includes('predict_citations'), `memory silo hides other tools (${names.length} listed)`);
const parse = (m: any) => JSON.parse(m.result.content[0].text);
const hits = parse(scoped.get(2));
const list = hits.results ?? hits.records ?? hits;
const byId = new Map(loadRecords().map((r) => [r.id, r]));
ok(Array.isArray(list) && list.length > 0 && list.every((h: any) => inSilo(byId.get(h.id)!, memory)), "search_records defaults to the silo's sections");
const cross = parse(scoped.get(3));
ok((cross.results ?? cross.records ?? cross).length > 0, 'an explicit product filter still reaches the whole catalog');

const bad = await rpc(['--silo', 'nope'], [init]).then(() => 'started', (e: Error) => e.message);
ok(/unknown silo "nope"/.test(bad), 'an unknown silo id fails with the valid ids');

if (failures) {
  console.error(`${failures} silo test(s) failed`);
  process.exit(1);
}
console.log('all silo tests passed');
