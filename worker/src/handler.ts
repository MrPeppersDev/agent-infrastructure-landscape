// Hosted, read-only MCP endpoint for the AI Agent Infrastructure Landscape.
//
// Implements the MCP Streamable HTTP transport in its stateless form: every
// POST carries one JSON-RPC message (or a batch) and gets a JSON response.
// No sessions, no server-sent events, no auth — the catalog is public data.
// Tool logic is the same pure modules the stdio server, the CLI and the
// website use (mcp/src/*.ts).
//
// `createHandler(load)` takes a loader for the data files so the same code
// runs on Cloudflare Workers (fetch from GitHub) and in local tests (fs).

import { toItem, choose, alternatives, DEFAULT_ANSWERS, type Answers, type ChooserItem } from '../../mcp/src/chooser.js';
import { chooseInfra, DEFAULT_INFRA, NEEDS, type InfraAnswers } from '../../mcp/src/chooser-infra.js';
import { compatibility, worksWith, setAliases } from '../../mcp/src/compat.js';
import { checkManifest, type StackIndex } from '../../mcp/src/stack-check.js';
import { buildIndex, search, docText, type SearchIndex } from '../../mcp/src/search.js';
import { estimateAll, DEFAULT_WORKLOAD, type VendorPricing } from '../../mcp/src/costs.js';
import { vectorEstimateAll, DEFAULT_VECTOR_WORKLOAD, type VectorPricing } from '../../mcp/src/vector-costs.js';
import { alternativesFor } from '../../mcp/src/chooser.js';
import { attentionIds } from '../../mcp/src/stack-check.js';

export type Loader = (file: string) => Promise<unknown>;
const SITE = 'https://mrpeppersdev.github.io/agent-infrastructure-landscape';
const PROTOCOL_VERSIONS = ['2025-06-18', '2025-03-26', '2024-11-05'];

type Rec = { id: string; name: string; url: string | null; tier: number; sections: { section: string; primary: boolean }[]; cells: Record<string, { value?: string; citation?: string | null; status?: string }>; taxonomy: unknown; last_verified_at?: string };

interface Data {
  records: Rec[];
  edges: unknown[];
  index: StackIndex;
  famOf: (section: string) => string;
  items: ChooserItem[];
  migrations: Map<string, unknown>;
  history: Record<string, unknown[]>;
  pricing: { checked: string; vendors: VendorPricing[] };
  vectorPricing: { checked: string; vendors: VectorPricing[] };
  redirects: Record<string, string>;
  search?: SearchIndex;
  replacements?: Record<string, { id: string; name: string; why: string[] }[]>;
}

const S = {
  str: (description: string) => ({ type: 'string', description }),
  bool: (description: string) => ({ type: 'boolean', description }),
  num: (description: string) => ({ type: 'number', description }),
  enum: (values: string[], description: string) => ({ type: 'string', enum: values, description })
};

export const TOOLS = [
  {
    name: 'ask_catalog',
    description: 'Plain-language search over 950+ AI agent systems, e.g. "self-hosted vector db with MCP, python". Requirement phrases (self-hosted, managed, open source, MCP, Python, TypeScript, memory layer / framework / vector db) are checked against catalogued facts; the rest ranks results.',
    inputSchema: { type: 'object', properties: { query: S.str('What you need, in plain words.'), limit: S.num('Results (default 10, max 50).') }, required: ['query'] }
  },
  {
    name: 'choose_memory_layer',
    description: 'Three cited memory-layer picks (Mem0, Zep/Graphiti, Letta, Cognee, Supermemory…) for your requirements, plus also-consider and might-fit lists. Archived systems are never recommended.',
    inputSchema: { type: 'object', properties: {
      building: S.enum(['app', 'coding'], 'app (default) or coding agent / dev tool'),
      hosting: S.enum(['self', 'managed', 'any'], 'where it must run'),
      oss: S.bool('require open source'), mcp: S.bool('require MCP support'),
      conflict: S.enum(['history', 'latest', 'llm', 'any'], 'when a fact changes'),
      shape: S.enum(['facts', 'conversations', 'documents', 'relationships', 'any'], 'what it mostly remembers')
    } }
  },
  {
    name: 'choose_framework_or_store',
    description: 'Three cited picks among agent frameworks (kind=framework; need: library | durable | tools | nocode | sandbox) or vector / graph / embedding stores (kind=data; need: vectors | graph | embeddings).',
    inputSchema: { type: 'object', properties: {
      kind: S.enum(['framework', 'data'], 'what you are choosing'), need: S.str('see description'),
      language: S.enum(['python', 'typescript', 'any'], 'required SDK language'), hosting: S.enum(['self', 'managed', 'any'], 'where it must run'),
      oss: S.bool('require open source'), mcp: S.bool('require MCP support'), existing: S.bool('data: prefer a database you may already run')
    }, required: ['kind'] }
  },
  {
    name: 'check_stack',
    description: 'Paste a package.json, requirements.txt, pyproject.toml or MCP config; returns AI dependencies that are archived, deprecated, acquired, in maintenance mode, renamed or stale, with evidence and live replacements.',
    inputSchema: { type: 'object', properties: { manifest: S.str('File contents.'), filename: S.str('Optional file name, helps format detection.') }, required: ['manifest'] }
  },
  {
    name: 'find_alternatives',
    description: 'Live alternatives to a catalogued system (id from ask_catalog), plus the official migration path when the system is archived or acquired.',
    inputSchema: { type: 'object', properties: { id: S.str('Record id.'), limit: S.num('How many (default 5).') }, required: ['id'] }
  },
  {
    name: 'check_compatibility',
    description: 'Do these systems work together? Integration evidence for every pair, with sources. One id: what it is documented to work with.',
    inputSchema: { type: 'object', properties: { ids: { type: 'array', items: { type: 'string' }, description: 'Record ids (1–8).' } }, required: ['ids'] }
  },
  {
    name: 'get_system',
    description: 'One system\'s cited facts (licence, deployment, pricing, latest release, MCP, storage design…), lifecycle status, change history and migration note.',
    inputSchema: { type: 'object', properties: { id: S.str('Record id.') }, required: ['id'] }
  },
  {
    name: 'estimate_memory_cost',
    description: 'Monthly cost of managed memory layers for a workload from published list prices only, with the arithmetic and pricing page.',
    inputSchema: { type: 'object', properties: {
      users: S.num('monthly active users'), messagesPerUser: S.num('messages written per user per month'),
      bytesPerMessage: S.num('average bytes per message'), retrievalsPerMessage: S.num('searches per message'), agentsPerUser: S.num('agents per user')
    } }
  },
  {
    name: 'estimate_vector_store_cost',
    description: 'Monthly cost of managed vector stores (Pinecone, Turbopuffer, Weaviate Cloud, Zilliz Cloud) for a workload from published rates only, with the arithmetic and pricing page; unpublished components are left out and marked atLeast.',
    inputSchema: { type: 'object', properties: {
      vectors: S.num('vectors stored'), dimensions: S.num('embedding dimensions'), metadataBytes: S.num('metadata bytes per vector'),
      writesPerMonth: S.num('vectors written per month'), queriesPerMonth: S.num('queries per month'), batchSize: S.num('vectors per write request')
    } }
  }
];

const EMPTY = new Set(['no-data', 'not-applicable', 'depth-floor-reached']);

export function createHandler(load: Loader) {
  let dataP: Promise<Data> | null = null;
  const getData = () =>
    (dataP ??= (async () => {
      const [L, E, I, F, M, H, A, P, V] = await Promise.all([
        load('landscape.json'), load('landscape.edges.json'), load('stack-index.json'), load('families.json'),
        load('migrations.json').catch(() => ({ notes: [] })), load('history.json').catch(() => ({ records: {} })),
        load('system-aliases.json').catch(() => ({ aliases: {} })), load('pricing-memory.json').catch(() => ({ checked: '', vendors: [] })),
        load('pricing-vector.json').catch(() => ({ checked: '', vendors: [] }))
      ]) as [{ records: Rec[] }, { edges: unknown[] }, StackIndex, { families: { id: string; sections: string[] }[] }, { notes: { id: string }[] }, { records: Record<string, unknown[]> }, { aliases: Record<string, string[]>; redirects?: Record<string, string> }, { checked: string; vendors: VendorPricing[] }, { checked: string; vendors: VectorPricing[] }];
      const fam = new Map<string, string>();
      for (const f of F.families) for (const s of f.sections) fam.set(s, f.id);
      setAliases(A.aliases);
      const items = L.records.map((r) => toItem(r as never, I.records[r.id] as never));
      return {
        records: L.records, edges: E.edges, index: I, famOf: (s: string) => fam.get(s) ?? 'other', items,
        migrations: new Map(M.notes.map((n) => [n.id, n])), history: H.records, pricing: P, vectorPricing: V, redirects: A.redirects ?? {}
      };
    })().catch((e) => {
      dataP = null;
      throw e;
    }));

  async function call(name: string, args: Record<string, unknown>): Promise<unknown> {
    const d = await getData();
    // Ids of merged-away records resolve to the record they were folded into.
    const resolve = (v: unknown) => (typeof v === 'string' ? (d.redirects[v] ?? v) : v);
    const a = { ...args, ...('id' in args ? { id: resolve(args.id) } : {}), ...(Array.isArray(args.ids) ? { ids: args.ids.map(resolve) } : {}) };
    switch (name) {
      case 'ask_catalog': {
        d.search ??= buildIndex(d.records.map((r, n) => ({ item: d.items[n], text: docText(r.cells), family: d.famOf(d.items[n].section) })));
        const r = search(d.search, String(a.query ?? ''), Math.min(50, Number(a.limit ?? 10)));
        return { requirements: r.constraints.map((c) => c.label), rankedBy: r.terms, considered: r.considered, results: r.hits.map((h) => ({ ...h, page: `${SITE}/systems/${h.id}` })) };
      }
      case 'choose_memory_layer': {
        const ans = { ...DEFAULT_ANSWERS, ...a } as Answers;
        const r = choose(d.items, ans);
        const slim = (x: (typeof r.picks)[number]) => ({ id: x.item.id, name: x.item.name, reasons: x.reasons, unconfirmed: x.unconfirmed, warning: x.warning, page: `${SITE}/systems/${x.item.id}` });
        return { answers: ans, picks: r.picks.map(slim), alsoConsider: r.alsoConsider.map((x) => x.item.name), unconfirmed: r.unconfirmed.map(slim) };
      }
      case 'choose_framework_or_store': {
        const kind = a.kind === 'data' ? 'data' : 'framework';
        const ans = { ...DEFAULT_INFRA[kind], ...a, kind } as InfraAnswers;
        if (!NEEDS[kind].some((n) => n.value === ans.need)) throw new Error(`need must be one of ${NEEDS[kind].map((n) => n.value).join(', ')}`);
        const r = chooseInfra(d.items, ans);
        const slim = (x: (typeof r.picks)[number]) => ({ id: x.item.id, name: x.item.name, reasons: x.reasons, unconfirmed: x.unconfirmed, warning: x.warning, page: `${SITE}/systems/${x.item.id}` });
        return { answers: ans, picks: r.picks.map(slim), alsoConsider: r.alsoConsider.map((x) => x.item.name), unconfirmed: r.unconfirmed.map(slim) };
      }
      case 'check_stack': {
        d.replacements ??= Object.fromEntries(
          Object.entries(alternativesFor(d.records as never, attentionIds(d.index), d.famOf, d.index.records as never, 3)).map(([id, l]) => [id, l.map(({ id, name, why }) => ({ id, name, why }))])
        );
        return checkManifest(String(a.manifest ?? ''), d.index, { filename: a.filename ? String(a.filename) : undefined, replacements: d.replacements });
      }
      case 'find_alternatives': {
        const t = d.items.find((i) => i.id === a.id);
        if (!t) throw new Error(`no record ${a.id}; use ask_catalog to find ids`);
        const fam = d.famOf(t.section);
        return { target: { id: t.id, name: t.name, status: t.status }, migration: d.migrations.get(t.id) ?? null, alternatives: alternatives(t, d.items.filter((i) => d.famOf(i.section) === fam), Number(a.limit ?? 5)) };
      }
      case 'check_compatibility': {
        const ids = (Array.isArray(a.ids) ? a.ids : []).map(String).slice(0, 8);
        if (!ids.length) throw new Error('ids is required');
        return ids.length === 1 ? { id: ids[0], worksWith: worksWith(d.records as never, d.edges as never, ids[0], 30) } : compatibility(d.records as never, d.edges as never, ids);
      }
      case 'get_system': {
        const r = d.records.find((x) => x.id === a.id);
        if (!r) throw new Error(`no record ${a.id}; use ask_catalog to find ids`);
        const cells = Object.fromEntries(Object.entries(r.cells).filter(([, c]) => c?.value && !EMPTY.has(c.status ?? '')).map(([k, c]) => [k, { value: c.value, citation: c.citation ?? null }]));
        return { id: r.id, name: r.name, url: r.url, section: r.sections.find((s) => s.primary)?.section, tier: r.tier, last_verified_at: r.last_verified_at ?? null, lifecycle: d.index.records[r.id] ?? { status: 'active' }, migration: d.migrations.get(r.id) ?? null, history: d.history[r.id] ?? [], taxonomy: r.taxonomy, cells, page: `${SITE}/systems/${r.id}` };
      }
      case 'estimate_memory_cost': {
        const w = { ...DEFAULT_WORKLOAD, ...Object.fromEntries(Object.entries(a).filter(([, v]) => typeof v === 'number')) };
        return { workload: w, pricesChecked: d.pricing.checked, estimates: estimateAll(d.pricing.vendors, w) };
      }
      case 'estimate_vector_store_cost': {
        const w = { ...DEFAULT_VECTOR_WORKLOAD, ...Object.fromEntries(Object.entries(a).filter(([, v]) => typeof v === 'number')) };
        return { workload: w, pricesChecked: d.vectorPricing.checked, estimates: vectorEstimateAll(d.vectorPricing.vendors, w) };
      }
    }
    throw Object.assign(new Error(`unknown tool ${name}`), { code: -32602 });
  }

  type Msg = { jsonrpc: '2.0'; id?: string | number | null; method?: string; params?: Record<string, unknown> };
  async function rpc(m: Msg): Promise<object | null> {
    const isNote = m.id === undefined || m.id === null;
    const ok = (result: unknown) => ({ jsonrpc: '2.0', id: m.id, result });
    const err = (code: number, message: string) => ({ jsonrpc: '2.0', id: m.id ?? null, error: { code, message } });
    if (m.jsonrpc !== '2.0' || typeof m.method !== 'string') return err(-32600, 'invalid request');
    if (isNote) return null; // notifications/initialized etc.
    switch (m.method) {
      case 'initialize': {
        const want = String(m.params?.protocolVersion ?? '');
        return ok({
          protocolVersion: PROTOCOL_VERSIONS.includes(want) ? want : PROTOCOL_VERSIONS[0],
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: 'agent-infrastructure-landscape', title: 'AI Agent Infrastructure Landscape', version: '1.0.0' },
          instructions: 'Read-only, citation-backed catalog of 950+ AI agent systems. Start with ask_catalog to find ids, then get_system, find_alternatives or check_compatibility. Every fact carries a source URL.'
        });
      }
      case 'ping':
        return ok({});
      case 'tools/list':
        return ok({ tools: TOOLS });
      case 'tools/call': {
        const name = String(m.params?.name ?? '');
        if (!TOOLS.some((t) => t.name === name)) return err(-32602, `unknown tool ${name}`);
        try {
          const out = await call(name, (m.params?.arguments as Record<string, unknown>) ?? {});
          return ok({ content: [{ type: 'text', text: JSON.stringify(out, null, 1) }], structuredContent: out });
        } catch (e) {
          return ok({ content: [{ type: 'text', text: (e as Error).message }], isError: true });
        }
      }
      default:
        return err(-32601, `method not found: ${m.method}`);
    }
  }

  const CORS = {
    'access-control-allow-origin': '*',
    'access-control-allow-methods': 'POST, GET, OPTIONS',
    'access-control-allow-headers': 'content-type, accept, mcp-protocol-version, mcp-session-id',
    'access-control-expose-headers': 'mcp-protocol-version'
  };

  return async function handle(req: Request): Promise<Response> {
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
    const url = new URL(req.url);
    if (req.method === 'GET') {
      if (url.pathname === '/' || url.pathname === '/health') {
        return new Response(
          JSON.stringify({ name: 'AI Agent Infrastructure Landscape MCP', transport: 'streamable-http (stateless)', endpoint: `${url.origin}/mcp`, tools: TOOLS.map((t) => t.name), site: SITE }),
          { headers: { 'content-type': 'application/json', ...CORS } }
        );
      }
      return new Response('Method Not Allowed: this server does not offer an SSE stream', { status: 405, headers: { allow: 'POST, OPTIONS', ...CORS } });
    }
    if (req.method !== 'POST') return new Response(null, { status: 405, headers: CORS });
    let body: unknown;
    try {
      body = await req.json();
    } catch {
      return Response.json({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'parse error' } }, { status: 400, headers: CORS });
    }
    const msgs = Array.isArray(body) ? (body as Msg[]) : [body as Msg];
    const out = (await Promise.all(msgs.map(rpc))).filter((x): x is object => x !== null);
    if (!out.length) return new Response(null, { status: 202, headers: CORS });
    return Response.json(Array.isArray(body) ? out : out[0], { headers: CORS });
  };
}
