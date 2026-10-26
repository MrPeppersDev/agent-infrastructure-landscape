// Local test of the hosted MCP handler with data read from the repo.
import { readFileSync } from 'node:fs';
import { createHandler } from '../src/handler.js';

const ROOT = new URL('../../', import.meta.url).pathname;
const FILES: Record<string, string> = {
  'landscape.json': 'data/landscape.json', 'landscape.edges.json': 'data/landscape.edges.json', 'stack-index.json': 'data/stack-index.json',
  'families.json': 'taxonomy/families.json', 'migrations.json': 'data/migrations.json', 'history.json': 'data/history.json',
  'system-aliases.json': 'taxonomy/system-aliases.json', 'pricing-memory.json': 'data/pricing/memory.json'
};
const handle = createHandler(async (f) => JSON.parse(readFileSync(ROOT + FILES[f], 'utf8')));
let failures = 0;
const check = (name: string, ok: boolean, detail = '') => { console.log(`  ${ok ? 'PASS' : 'FAIL'} ${name}${ok ? '' : ' ' + detail}`); if (!ok) failures++; };
const post = async (body: unknown) => {
  const r = await handle(new Request('https://x/mcp', { method: 'POST', headers: { 'content-type': 'application/json', accept: 'application/json, text/event-stream' }, body: JSON.stringify(body) }));
  return { status: r.status, json: r.status === 202 ? null : await r.json() };
};
const callTool = async (name: string, args: unknown) => (await post({ jsonrpc: '2.0', id: 9, method: 'tools/call', params: { name, arguments: args } })).json.result;

const init = await post({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '0' } } });
check('initialize', init.json.result.protocolVersion === '2025-06-18' && !!init.json.result.capabilities.tools);
check('initialized notification → 202', (await post({ jsonrpc: '2.0', method: 'notifications/initialized' })).status === 202);
const list = await post({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
check('tools/list', list.json.result.tools.length === 8);
const ask = await callTool('ask_catalog', { query: 'self-hosted vector db with MCP, python', limit: 5 });
check('ask_catalog', !ask.isError && ask.structuredContent.results.length > 0, JSON.stringify(ask).slice(0, 200));
const ch = await callTool('check_stack', { manifest: '{"dependencies":{"flowise":"^3","mem0ai":"^2"}}', filename: 'package.json' });
check('check_stack flags flowise', ch.structuredContent.attention.some((f: { recordId: string }) => f.recordId.startsWith('flowise')));
const alt = await callTool('find_alternatives', { id: 'openai-swarm-deprecated--gh-openai-swarm' });
check('find_alternatives carries migration', alt.structuredContent.migration?.to?.[0]?.name === 'OpenAI Agents SDK');
const comp = await callTool('check_compatibility', { ids: ['mem0--mem0-ai', 'qdrant--qdrant-tech'] });
check('check_compatibility', comp.structuredContent.pairs[0].status === 'documented');
const sys = await callTool('get_system', { id: 'mem0--mem0-ai' });
check('get_system', sys.structuredContent.cells.license?.value?.length > 0);
const cost = await callTool('estimate_memory_cost', { users: 50 });
check('estimate_memory_cost', cost.structuredContent.estimates.length >= 5);
const bad = await callTool('get_system', { id: 'nope' });
check('tool error is isError, not a crash', bad.isError === true);
const unk = await post({ jsonrpc: '2.0', id: 3, method: 'resources/list' });
check('unknown method → -32601', unk.json.error.code === -32601);
const batch = await post([{ jsonrpc: '2.0', id: 4, method: 'ping' }, { jsonrpc: '2.0', id: 5, method: 'tools/list' }]);
check('batch', Array.isArray(batch.json) && batch.json.length === 2);
const get = await handle(new Request('https://x/mcp'));
check('GET /mcp → 405 (no SSE)', get.status === 405);
if (failures) { console.error(`${failures} failure(s)`); process.exit(1); }
console.log('all worker tests passed');
