#!/usr/bin/env node
// MCP server entrypoint — local stdio transport.
//
// Wraps the 9 pure query helpers from tools.ts in MCP tool-handler
// plumbing. The server is read-only: there are no mutation tools. Data
// is loaded lazily on first tool call and cached in-process for the
// duration of the connection.
//
// Run via:
//   - Direct:   node dist/server.js
//   - npx:      npx -y landscape-mcp
//   - Claude:   see mcp/README.md for client config snippets

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { loadRecords, loadEdges, getMeta, loadFamilies, familyIdForSection, loadStackIndex, loadReplacements, loadLinks, loadChooserItems, loadMigrations, loadHistory, loadSystemAliases, loadRedirects } from './data.js';
import { chooseInfra, DEFAULT_INFRA, NEEDS, type InfraAnswers } from './chooser-infra.js';
import { compatibility, worksWith, setAliases } from './compat.js';
import { buildIndex, search as askSearch, docText, type SearchIndex } from './search.js';
import { estimateAll, DEFAULT_WORKLOAD, type VendorPricing } from './costs.js';
import { loadPricing, loadVectorPricing, loadStackPricing } from './data.js';
import { vectorEstimateAll, DEFAULT_VECTOR_WORKLOAD, type VectorPricing } from './vector-costs.js';
import { checkManifest } from './stack-check.js';
import { planStack, slimPlan, PRODUCTS, LAYERS, type StackAnswers, type LayerId, type ProductType } from './composer.js';
import { choose, alternatives, DEFAULT_ANSWERS, type Answers } from './chooser.js';
import {
  searchRecords,
  getRecord,
  findRelated,
  coverageSummary,
  compareWithEdges,
  listSections,
  recentChanges,
  findEvalOrphans,
  findSubstrateRisk,
  findByDecayCause
} from './tools.js';
import {
  fitCitationCurves,
  topBreakouts,
  findFitById
} from './citation-prediction.js';
import { betweenModels, recommendForProject } from './recommender.js';
import type { RecommendCategory, StructuredForm } from './recommender.js';
import type { EdgeType } from './types.js';

const USE_CASE_TAGS = [
  'scoped-agentic',
  'long-running-session',
  'multi-agent-coordination',
  'memory-augmented-chat',
  'code-generation-focused',
  'analytical-summarization',
  'latency-sensitive',
  'offline-capable'
] as const;

const EDGE_TYPES: readonly EdgeType[] = [
  'built-on',
  'runtime-dependency',
  'extends',
  'forks',
  'integrates-with',
  'competes-with',
  'inspired-by',
  'cites',
  'same-team-as',
  'succeeds'
] as const;

/**
 * Convenience: wrap any tools.ts result in the MCP CallToolResult shape.
 * MCP expects a `content` array of typed parts; we serialise the JSON
 * result as a single text part — clients can re-parse it for structured
 * use, or render it as-is for human consumption.
 */
function jsonResult<T>(value: T) {
  return {
    content: [
      {
        type: 'text' as const,
        text: JSON.stringify(value, null, 2)
      }
    ]
  };
}

async function main() {
  const meta = (() => {
    try {
      // Trigger eager load so we fail fast if the data files are missing.
      loadRecords();
      return getMeta();
    } catch (err) {
      console.error('[landscape-mcp] failed to load catalog:', err);
      throw err;
    }
  })();

  const server = new McpServer(
    {
      name: 'landscape-mcp',
      version: '1.0.0',
      description: `AI agent infrastructure landscape catalog. Schema ${meta.schemaVersion}, generated ${meta.generatedAt}.`
    },
    {
      capabilities: {
        tools: {}
      }
    }
  );

  // Ids of merged-away records resolve to the record they were folded into,
  // for every tool that takes `id`, `ids` or `record_id`. Tools without an
  // input schema are called with `extra` only, so only rewrite two-arg calls.
  const redirects = loadRedirects();
  const resolveId = (v: unknown) => (typeof v === 'string' ? (redirects[v] ?? v) : v);
  const resolveArgs = (a: Record<string, unknown>) => ({
    ...a,
    ...('id' in a ? { id: resolveId(a.id) } : {}),
    ...('record_id' in a ? { record_id: resolveId(a.record_id) } : {}),
    ...(Array.isArray(a.ids) ? { ids: a.ids.map(resolveId) } : {})
  });
  const register = server.registerTool.bind(server) as (...a: unknown[]) => unknown;
  server.registerTool = ((name: string, config: unknown, cb: (...a: unknown[]) => unknown) =>
    register(name, config, (...a: unknown[]) =>
      a.length > 1 ? cb(resolveArgs(a[0] as Record<string, unknown>), ...a.slice(1)) : cb(...a)
    )) as typeof server.registerTool;

  // -----------------------------------------------------------------------
  // 1. search_records
  // -----------------------------------------------------------------------
  server.registerTool(
    'search_records',
    {
      title: 'Search the landscape catalog',
      description:
        'Free-text substring search over record id, name, description, and claims. ' +
        'Returns compact summaries — use get_record for full details. Filters: ' +
        'product (family id from list_products, e.g. "memory"), ' +
        'section (exact match on primary section), tier (1=battle-tested → 5=theoretical), ' +
        'freshWithinMonths (freshness date = latest of upstream last commit and last catalog audit), ' +
        'layer (agent-infra | model-infra | large-models), licensing (open-source | open-core | commercial).',
      inputSchema: {
        query: z.string().describe('Search query (case-insensitive substring match).'),
        product: z
          .string()
          .optional()
          .describe('Filter to a product family id: memory, memory-research, agents, data, models-ops.'),
        section: z
          .string()
          .optional()
          .describe('Filter to records whose primary section equals this exact value.'),
        tier: z
          .number()
          .int()
          .min(1)
          .max(5)
          .optional()
          .describe('Filter to records of this tier (1-5).'),
        freshWithinMonths: z
          .number()
          .int()
          .min(1)
          .max(120)
          .optional()
          .describe('Only records whose freshness date falls within this many months (e.g. 6).'),
        layer: z
          .enum(['agent-infra', 'model-infra', 'large-models'])
          .optional()
          .describe('Three-layer rollup of the primary section.'),
        licensing: z
          .enum(['open-source', 'open-core', 'commercial'])
          .optional()
          .describe('Licensing bucket derived from the license and pricing cells.'),
        limit: z
          .number()
          .int()
          .min(1)
          .max(200)
          .optional()
          .describe('Max results to return (default 25, max 200).')
      }
    },
    async (args) => {
      const records = loadRecords();
      return jsonResult(searchRecords(records, args));
    }
  );

  // -----------------------------------------------------------------------
  // 1b. list_products
  // -----------------------------------------------------------------------
  server.registerTool(
    'list_products',
    {
      title: 'List the product catalogs',
      description:
        'The catalog is split into five product families (Agent Memory, Memory Research & ' +
        'Benchmarks, Agent Frameworks & Harnesses, Retrieval & Data Infrastructure, Models, ' +
        'Serving & Ops). Returns each family id, name, tagline, its sections and record count. ' +
        'Use the id as the `product` filter on search_records.',
      inputSchema: {}
    },
    async () => {
      const records = loadRecords();
      const counts = new Map<string, number>();
      for (const r of records) {
        const primary = r.sections.find((s) => s.primary)?.section ?? r.sections[0]?.section ?? '';
        const id = familyIdForSection(primary);
        counts.set(id, (counts.get(id) ?? 0) + 1);
      }
      return jsonResult({
        products: loadFamilies().map((f) => ({ ...f, recordCount: counts.get(f.id) ?? 0 }))
      });
    }
  );

  // -----------------------------------------------------------------------
  // 1c. check_stack
  // -----------------------------------------------------------------------
  server.registerTool(
    'check_stack',
    {
      title: 'Check a project stack against the catalog',
      description:
        'Paste a dependency manifest — package.json, requirements.txt, pyproject.toml, or an MCP ' +
        'client config (Claude Desktop / Claude Code .mcp.json / Cursor) — and get back which ' +
        'dependencies are catalogued systems that are archived, deprecated, in maintenance mode, ' +
        'acquired, renamed, stale (no commits in 12+ months) or locked to one model vendor. ' +
        '`attention` lists the ones that need action, most severe first, each with the catalog ' +
        'record id (use get_record for detail), an evidence URL and up to three live `replacements`.',
      inputSchema: {
        manifest: z.string().describe('The manifest file contents, or one package per line (npm:/pypi: prefixes optional).'),
        filename: z.string().optional().describe('Original filename, e.g. "requirements.txt" (helps format detection).'),
        format: z
          .enum(['package.json', 'requirements.txt', 'pyproject.toml', 'mcp-config', 'stack.yml', 'list'])
          .optional()
          .describe('Force a format instead of auto-detecting.')
      }
    },
    async (args) => {
      const report = checkManifest(args.manifest, loadStackIndex(), {
        filename: args.filename,
        format: args.format,
        replacements: loadReplacements(),
        links: loadLinks()
      });
      return jsonResult(report);
    }
  );

  // -----------------------------------------------------------------------
  // 1d. choose_memory_layer / find_alternatives
  // -----------------------------------------------------------------------
  server.registerTool(
    'choose_memory_layer',
    {
      title: 'Recommend an agent memory layer',
      description:
        'Which memory layer should this project use? Give what you are building and your ' +
        'requirements; returns three picks (Mem0, Zep/Graphiti, Letta, Cognee, Supermemory, …) ' +
        'each with reasons that are catalogued facts plus source URLs, an also-consider list, and ' +
        '`unconfirmed` systems the catalog cannot confirm a must-have for. Archived systems are ' +
        'never recommended. Same logic as the /choose page.',
      inputSchema: {
        building: z.enum(['app', 'coding']).optional().describe('"app": an app/agent that remembers its users (default); "coding": a coding agent or dev tool.'),
        hosting: z.enum(['self', 'managed', 'any']).optional().describe('Where it must run (default any).'),
        oss: z.boolean().optional().describe('Require an open-source licence.'),
        mcp: z.boolean().optional().describe('Require MCP support.'),
        conflict: z.enum(['history', 'latest', 'llm', 'any']).optional().describe('When a fact changes: keep history (bi-temporal/versioned), latest wins, an LLM decides, or any.'),
        shape: z.enum(['facts', 'conversations', 'documents', 'relationships', 'any']).optional().describe('What it will mostly remember.')
      }
    },
    async (args) => {
      const answers: Answers = { ...DEFAULT_ANSWERS, ...Object.fromEntries(Object.entries(args).filter(([, v]) => v !== undefined)) };
      const r = choose(loadChooserItems(), answers);
      const slim = (x: (typeof r.picks)[number]) => ({
        id: x.item.id, name: x.item.name, section: x.item.section, reasons: x.reasons,
        unconfirmed: x.unconfirmed, warning: x.warning, url: x.item.url
      });
      return jsonResult({
        answers,
        picks: r.picks.map(slim),
        alsoConsider: r.alsoConsider.map((x) => ({ id: x.item.id, name: x.item.name, warning: x.warning })),
        unconfirmed: r.unconfirmed.map(slim),
        poolSize: r.poolSize,
        excludedCount: r.excludedCount
      });
    }
  );

  server.registerTool(
    'choose_framework_or_store',
    {
      title: 'Recommend an agent framework or data store',
      description:
        'Which agent framework, durable-execution engine, tool/auth platform, code sandbox, vector ' +
        'database, knowledge-graph store or embedding service should this project use? Returns three ' +
        'picks with reasons that are catalogued facts plus source URLs, an also-consider list, and ' +
        '`unconfirmed` systems the catalog cannot confirm a must-have for. One product per vendor; ' +
        'archived systems are never recommended. Same logic as /choose/framework and /choose/data. ' +
        'For memory layers use choose_memory_layer.',
      inputSchema: {
        kind: z.enum(['framework', 'data']).describe('"framework": agent frameworks and runtimes; "data": vector / graph / embedding.'),
        need: z.string().optional().describe('framework: library | durable | tools | nocode | sandbox (default library). data: vectors | graph | embeddings (default vectors).'),
        language: z.enum(['python', 'typescript', 'any']).optional().describe('Required SDK language (default any).'),
        hosting: z.enum(['self', 'managed', 'any']).optional().describe('Where it must run (default any).'),
        oss: z.boolean().optional().describe('Require an open-source licence.'),
        mcp: z.boolean().optional().describe('Require MCP support.'),
        existing: z.boolean().optional().describe('data only: prefer something that runs on a database you may already operate (Postgres, MongoDB, Elastic, Redis…).')
      }
    },
    async (args) => {
      const base = DEFAULT_INFRA[args.kind];
      const a: InfraAnswers = { ...base, ...Object.fromEntries(Object.entries(args).filter(([, v]) => v !== undefined)) } as InfraAnswers;
      if (!NEEDS[a.kind].some((n) => n.value === a.need)) {
        return jsonResult({ error: `need must be one of ${NEEDS[a.kind].map((n) => n.value).join(', ')}` });
      }
      const r = chooseInfra(loadChooserItems(), a);
      const slim = (x: (typeof r.picks)[number]) => ({
        id: x.item.id, name: x.item.name, section: x.item.section, reasons: x.reasons,
        unconfirmed: x.unconfirmed, warning: x.warning, url: x.item.url
      });
      return jsonResult({
        answers: a,
        picks: r.picks.map(slim),
        alsoConsider: r.alsoConsider.map((x) => ({ id: x.item.id, name: x.item.name, warning: x.warning })),
        unconfirmed: r.unconfirmed.map(slim),
        poolSize: r.poolSize,
        excludedCount: r.excludedCount
      });
    }
  );

  const layerIds = LAYERS.map((l) => l.id) as [LayerId, ...LayerId[]];
  server.registerTool(
    'plan_stack',
    {
      title: 'Plan a whole agent stack',
      description:
        'Compose a full stack for an AI agent product in one call: one pick per layer (framework, model, ' +
        'gateway, memory, vector store, embeddings, tools/auth, sandbox, browser, voice, evals/observability, ' +
        'guardrails), each with cited reasons, a "why not" for the runners-up and the best-known systems ruled ' +
        'out, and an exit path (self-host fallback, licence, migration notes). Later layers prefer systems with ' +
        'a recorded integration with earlier picks. Also returns which picks have documented integrations, a ' +
        'risk score built only from cited facts (lifecycle, vendor concentration, bus factor, licence, ' +
        'unrecorded integrations), an OWASP LLM Top 10 coverage map, an eval plan, and a stack.yml that ' +
        'check_stack and the GitHub Action can watch. Archived systems are never picked.',
      inputSchema: {
        product: z.enum(Object.keys(PRODUCTS) as [ProductType, ...ProductType[]]).optional()
          .describe('support-agent (default) | coding-agent | research-agent | voice-agent | multi-agent-workflow | rag-copilot'),
        language: z.enum(['python', 'typescript', 'any']).optional().describe('Required SDK language (default any).'),
        hosting: z.enum(['self', 'managed', 'any']).optional().describe('self = run everything yourself (adds model serving); managed = prefer hosted services.'),
        oss: z.boolean().optional().describe('Require open-source licences.'),
        mcp: z.boolean().optional().describe('Require MCP support where it applies (framework, memory, tools).'),
        layers: z.array(z.enum(layerIds)).optional().describe('Replace the product preset\'s layers.'),
        add: z.array(z.enum(layerIds)).optional().describe('Add layers to the preset, e.g. ["voice"].'),
        pin: z.record(z.string(), z.string()).optional().describe('Fix a layer to a record id, e.g. {"vectors": "qdrant--qdrant-tech"}.'),
        avoid: z.array(z.string()).optional().describe('Record ids never to pick.'),
        workload: z.object({
          runsPerDay: z.number().optional(), llmCallsPerRun: z.number().optional(), inputTokensPerCall: z.number().optional(),
          outputTokensPerCall: z.number().optional(), toolCallsPerRun: z.number().optional(), users: z.number().optional(),
          sandboxMinutesPerRun: z.number().optional(), browserMinutesPerRun: z.number().optional(), voiceMinutesPerRun: z.number().optional(), embeddingTokensPerRun: z.number().optional(),
          vectors: z.number().optional()
        }).optional().describe('Workload for the monthly cost estimate from published list prices (defaults: 1,000 runs/day, 6 model calls of 3,000 in / 400 out tokens, 4 tool calls, 1,000 users, 1M vectors).'),
        compliance: z.array(z.string()).optional().describe('Attestations every hosted service must publish, e.g. ["soc2-type2","hipaa"] (codes: ccpa, csa-star, fedramp, gdpr, hipaa, hitrust, iso27001, iso27017, iso27018, iso27701, iso42001, pci-dss, soc2-type1, soc2-type2, soc3). Libraries you run yourself are exempt.')
      }
    },
    async (args) => {
      const a = Object.fromEntries(Object.entries(args).filter(([, v]) => v !== undefined)) as Partial<StackAnswers>;
      const plan = planStack(
        {
          items: loadChooserItems(), records: loadRecords() as never, edges: loadEdges() as never, migrations: loadMigrations() as never,
          pricing: { stack: loadStackPricing() as never, memory: loadPricing() as never, vector: loadVectorPricing() as never }
        },
        a as StackAnswers
      );
      return jsonResult(slimPlan(plan));
    }
  );

  let askIndex: SearchIndex | null = null;
  server.registerTool(
    'ask_catalog',
    {
      title: 'Search the catalog in plain words',
      description:
        'Plain-language search over the whole catalog, e.g. "self-hosted vector db with MCP, python" or ' +
        '"memory that handles contradictions on postgres". Requirement phrases (self-hosted, managed, ' +
        'open source, MCP, Python, TypeScript, memory layer / framework / vector db / paper, maintained) ' +
        'are checked against catalogued facts; the remaining words rank results (BM25 with catalog ' +
        'synonyms). Each hit lists which requirements it confirms and which the catalog cannot confirm.',
      inputSchema: {
        query: z.string().min(2).describe('What you need, in plain words.'),
        limit: z.number().int().min(1).max(50).optional().describe('How many results (default 10).')
      }
    },
    async (args) => {
      if (!askIndex) {
        const items = new Map(loadChooserItems().map((i) => [i.id, i]));
        askIndex = buildIndex(loadRecords().map((r) => {
          const item = items.get(r.id)!;
          return { item, text: docText(r.cells), family: familyIdForSection(item.section) };
        }));
      }
      const r = askSearch(askIndex, args.query, args.limit ?? 10);
      return jsonResult({
        query: args.query,
        requirements: r.constraints.map((c) => c.label),
        rankedBy: r.terms,
        considered: r.considered,
        results: r.hits.map((h) => ({ ...h, page: `https://mrpeppersdev.github.io/agent-infrastructure-landscape/systems/${h.id}` }))
      });
    }
  );

  server.registerTool(
    'estimate_memory_cost',
    {
      title: 'Estimate managed memory-layer cost',
      description:
        'Monthly cost of managed memory layers (Mem0, Zep, Supermemory, Cognee, Letta…) for a workload, ' +
        'using only each vendor\'s published plans and rates, with the arithmetic and the pricing page. ' +
        'Usage beyond the largest published plan is reported as contact-sales, not extrapolated.',
      inputSchema: {
        users: z.number().min(0).optional().describe('Monthly active users (default 1000).'),
        messagesPerUser: z.number().min(0).optional().describe('Messages written to memory per user per month (default 60).'),
        bytesPerMessage: z.number().min(1).optional().describe('Average bytes per message (default 600).'),
        retrievalsPerMessage: z.number().min(0).optional().describe('Memory searches per message (default 1).'),
        agentsPerUser: z.number().min(0).optional().describe('Agents per user, for per-agent pricing (default 1).')
      }
    },
    async (args) => {
      const p = loadPricing();
      const w = { ...DEFAULT_WORKLOAD, ...Object.fromEntries(Object.entries(args).filter(([, v]) => v !== undefined)) };
      return jsonResult({ workload: w, pricesChecked: p.checked, estimates: estimateAll(p.vendors as VendorPricing[], w) });
    }
  );

  server.registerTool(
    'estimate_vector_store_cost',
    {
      title: 'Estimate managed vector-store cost',
      description:
        'Monthly cost of managed vector stores (Pinecone, Turbopuffer, Weaviate Cloud, Zilliz Cloud; Qdrant Cloud and ' +
        'LanceDB Cloud are listed as not published) for a workload, using only published rates, with the arithmetic and ' +
        'the pricing page. A component whose rate is not published is left out and the result is marked atLeast.',
      inputSchema: {
        vectors: z.number().min(0).optional().describe('Vectors stored (default 1,000,000).'),
        dimensions: z.number().min(1).optional().describe('Embedding dimensions (default 1536).'),
        metadataBytes: z.number().min(0).optional().describe('Metadata bytes stored per vector (default 500).'),
        writesPerMonth: z.number().min(0).optional().describe('Vectors written per month (default 100,000).'),
        queriesPerMonth: z.number().min(0).optional().describe('Queries per month (default 1,000,000).'),
        batchSize: z.number().min(1).optional().describe('Vectors per write request (default 100).')
      }
    },
    async (args) => {
      const p = loadVectorPricing();
      const w = { ...DEFAULT_VECTOR_WORKLOAD, ...Object.fromEntries(Object.entries(args).filter(([, v]) => v !== undefined)) };
      return jsonResult({ workload: w, pricesChecked: p.checked, estimates: vectorEstimateAll(p.vendors as VectorPricing[], w) });
    }
  );

  server.registerTool(
    'check_compatibility',
    {
      title: 'Do these systems work together?',
      description:
        'For 2–8 catalogued systems (ids from search_records), returns every pair with the catalog\'s ' +
        'evidence that they integrate: typed edges and integration cells (backend storage, adjacent ' +
        'infrastructure, API surface, embedding model, MCP, runtimes) naming the other, each with a ' +
        'source. "not-recorded" means no source either way, not incompatible. With one id, lists ' +
        'what that system is documented to work with.',
      inputSchema: {
        ids: z.array(z.string()).min(1).max(8).describe('Catalog record ids.'),
        limit: z.number().int().min(1).max(100).optional().describe('With one id: how many systems to list (default 30).')
      }
    },
    async (args) => {
      setAliases(loadSystemAliases());
      const records = loadRecords() as never;
      const edges = loadEdges() as never;
      if (args.ids.length === 1) {
        return jsonResult({ id: args.ids[0], worksWith: worksWith(records, edges, args.ids[0], args.limit ?? 30) });
      }
      return jsonResult(compatibility(records, edges, args.ids));
    }
  );

  server.registerTool(
    'system_history',
    {
      title: 'What changed for a system',
      description:
        'Recorded changes to one catalogued system (lifecycle, licence, latest release, pricing, ' +
        'deployment, MCP/A2A support, ownership), newest first, each with date, source PR and the ' +
        'cell citation, plus any migration note for archived / acquired systems.',
      inputSchema: { id: z.string().describe('Catalog record id.') }
    },
    async (args) => {
      const rec = loadRecords().find((r) => r.id === args.id);
      if (!rec) return jsonResult({ error: `no record with id ${args.id}; use search_records` });
      return jsonResult({
        id: rec.id,
        name: rec.name,
        last_verified_at: rec.last_verified_at ?? null,
        status: loadStackIndex().records[rec.id] ?? { status: 'active' },
        migration: loadMigrations().get(rec.id) ?? null,
        history: loadHistory()[rec.id] ?? []
      });
    }
  );

  server.registerTool(
    'find_alternatives',
    {
      title: 'Find alternatives to a system',
      description:
        'Live alternatives to a catalogued system (use search_records to find its id), ranked by ' +
        'shared memory design (storage, retrieval, conflict handling, memory unit), same section and ' +
        'shared must-haves (open source, self-host, MCP). Archived systems and other packagings of ' +
        'the same product are excluded. Use it to replace an archived or acquired dependency.',
      inputSchema: {
        id: z.string().describe('Catalog record id.'),
        limit: z.number().int().min(1).max(20).optional().describe('How many (default 5).')
      }
    },
    async (args) => {
      const items = loadChooserItems();
      const target = items.find((i) => i.id === args.id);
      if (!target) return jsonResult({ error: `no record with id ${args.id}; use search_records` });
      const fam = familyIdForSection(target.section);
      const pool = items.filter((i) => familyIdForSection(i.section) === fam);
      return jsonResult({
        target: { id: target.id, name: target.name, section: target.section, status: target.status },
        migration: loadMigrations().get(target.id) ?? null,
        alternatives: alternatives(target, pool, args.limit ?? 5)
      });
    }
  );

  // -----------------------------------------------------------------------
  // 2. get_record
  // -----------------------------------------------------------------------
  server.registerTool(
    'get_record',
    {
      title: 'Get a full record by id',
      description:
        'Returns the complete record (all cells, taxonomy, section memberships) for the given stable id. ' +
        'Use search_records to find ids; ids look like "openai-gpt-family-gpt-5-gpt-4o-o3-o4--openai-com".',
      inputSchema: {
        id: z.string().describe('Stable record id from the catalog.')
      }
    },
    async (args) => {
      const records = loadRecords();
      const record = getRecord(records, args);
      if (!record) {
        return jsonResult({ error: `Record not found: ${args.id}` });
      }
      return jsonResult(record);
    }
  );

  // -----------------------------------------------------------------------
  // 3. find_related
  // -----------------------------------------------------------------------
  server.registerTool(
    'find_related',
    {
      title: 'Find records linked to a given record',
      description:
        'Returns all edges touching the given record id (both incoming and outgoing), ' +
        'plus summaries of the records on the other end. Optionally filter by edge_type. ' +
        'Edge types: built-on, runtime-dependency, extends, forks, integrates-with, ' +
        'competes-with, inspired-by, cites, same-team-as, succeeds.',
      inputSchema: {
        id: z.string().describe('Stable record id from the catalog.'),
        edge_type: z
          .enum(EDGE_TYPES as unknown as [EdgeType, ...EdgeType[]])
          .optional()
          .describe('Restrict to a specific edge type (omit for all types).')
      }
    },
    async (args) => {
      const records = loadRecords();
      const edges = loadEdges();
      return jsonResult(findRelated(records, edges, args));
    }
  );

  // -----------------------------------------------------------------------
  // 4. coverage_summary
  // -----------------------------------------------------------------------
  server.registerTool(
    'coverage_summary',
    {
      title: 'Catalog-wide coverage stats per dimension',
      description:
        'Per-feature counts for one of four dimensions: ' +
        '"observability" (7 boolean obs-* columns + obs-custom free-text), ' +
        '"cost" (7 cost-* columns), ' +
        '"eval" (7 eval-* columns), ' +
        '"benchmark" (per-section counts for benchmark-bearing sections). ' +
        'Use this to answer questions like "what fraction of products support LangSmith?".',
      inputSchema: {
        dimension: z
          .enum(['observability', 'cost', 'eval', 'benchmark'])
          .describe('Which coverage dimension to summarise.')
      }
    },
    async (args) => {
      const records = loadRecords();
      return jsonResult(coverageSummary(records, args));
    }
  );

  // -----------------------------------------------------------------------
  // 5. compare
  // -----------------------------------------------------------------------
  server.registerTool(
    'compare',
    {
      title: 'Compare two records side by side',
      description:
        'Returns cell-by-cell comparison of two records across every column. ' +
        'Includes any direct edges between them. Use for "X vs Y" research questions.',
      inputSchema: {
        id_a: z.string().describe('First record id.'),
        id_b: z.string().describe('Second record id.')
      }
    },
    async (args) => {
      const records = loadRecords();
      const edges = loadEdges();
      try {
        return jsonResult(compareWithEdges(records, edges, args));
      } catch (err) {
        return jsonResult({
          error: err instanceof Error ? err.message : String(err)
        });
      }
    }
  );

  // -----------------------------------------------------------------------
  // 6. list_sections
  // -----------------------------------------------------------------------
  server.registerTool(
    'list_sections',
    {
      title: 'List all top-level catalog sections',
      description:
        'Returns the alphabetised set of primary section names. Use these values as the ' +
        '`section` filter on search_records.',
      inputSchema: {}
    },
    async () => {
      const records = loadRecords();
      return jsonResult({ sections: listSections(records) });
    }
  );

  // -----------------------------------------------------------------------
  // 7. recent_changes
  // -----------------------------------------------------------------------
  server.registerTool(
    'recent_changes',
    {
      title: 'Records updated since a date',
      description:
        'Returns records whose latest-release (or created, if no release) is on or after the given date. ' +
        'Omit `since` to return the 20 most-recently-shipped records. ' +
        'Date is the shipping date of the underlying product, not when the catalog was updated.',
      inputSchema: {
        since: z
          .string()
          .optional()
          .describe(
            'ISO date (YYYY-MM-DD or full ISO timestamp), or a bare year (e.g. "2025"). Omit for the 20 most-recent.'
          )
      }
    },
    async (args) => {
      const records = loadRecords();
      return jsonResult(recentChanges(records, args));
    }
  );

  // -----------------------------------------------------------------------
  // 8. find_eval_orphans
  // -----------------------------------------------------------------------
  server.registerTool(
    'find_eval_orphans',
    {
      title: 'Find products with observability but no evals',
      description:
        'Returns products that have observability integration (≥1 obs-* tool) but ZERO eval tools, ' +
        'AND have been researched for evals (so the absence is verified). This surfaces the structural ' +
        'failure mode the LangChain State of Agent Engineering 2025 survey identified: 89% have obs, ' +
        'only 52% have evals — a 37-point gap.',
      inputSchema: {}
    },
    async () => {
      const records = loadRecords();
      return jsonResult({ orphans: findEvalOrphans(records) });
    }
  );

  // -----------------------------------------------------------------------
  // 9. find_substrate_risk
  // -----------------------------------------------------------------------
  server.registerTool(
    'find_substrate_risk',
    {
      title: 'Find products that runtime-depend on a substrate',
      description:
        'Returns records that runtime-depend on a given substrate (e.g. "OpenAI", "Anthropic", ' +
        '"MCP"). Useful for blast-radius questions ("what breaks if X changes pricing?") and ' +
        'lock-in analysis. Resolves the substrate by exact id, then by case-insensitive name/id ' +
        'substring (picks the match with the most incoming runtime-dependency edges).',
      inputSchema: {
        substrate: z
          .string()
          .describe(
            'Substrate name or id (e.g. "OpenAI", "Anthropic", "MCP", or a full record id).'
          )
      }
    },
    async (args) => {
      const records = loadRecords();
      const edges = loadEdges();
      return jsonResult(findSubstrateRisk(records, edges, args));
    }
  );

  // -----------------------------------------------------------------------
  // 10. find_by_decay_cause
  // -----------------------------------------------------------------------
  server.registerTool(
    'find_by_decay_cause',
    {
      title: 'Find records by decay-cause forensics label',
      description:
        'Returns records whose decay_cause matches the given cause. Enum: ' +
        'acquired, pivoted, unfunded, lost-benchmark-race, superseded, archived, research-complete, unknown. ' +
        'Surfaces mortality forensics from T3-1 — useful for "which products in this space ' +
        'were acquired vs ran out of funding vs were archived on GitHub?"',
      inputSchema: {
        cause: z
          .string()
          .describe(
            'Decay cause: acquired | pivoted | unfunded | lost-benchmark-race | superseded | archived | research-complete | unknown.'
          )
      }
    },
    async (args) => {
      const records = loadRecords();
      return jsonResult(findByDecayCause(records, args));
    }
  );

  // -----------------------------------------------------------------------
  // 11. predict_citations
  // -----------------------------------------------------------------------
  //
  // Memoise the fitter — fitting all ~196 academic papers takes ~5 sec
  // and the result is deterministic, so we compute once per server.
  let cachedFits: ReturnType<typeof fitCitationCurves> | null = null;
  function getFits() {
    if (cachedFits === null) {
      const records = loadRecords();
      cachedFits = fitCitationCurves(records);
    }
    return cachedFits;
  }

  server.registerTool(
    'predict_citations',
    {
      title: 'Wang-Song-Barabási citation breakout prediction for a paper',
      description:
        'Returns the fitted WSB log-normal citation model for one academic-paper row: ' +
        'λ (immediacy), μ (peak time), σ (longevity), predicted asymptote with 90% CI, ' +
        '10-year prediction, R², phase (pre-growth/growth/saturation/underfit-data), ' +
        'and breakout probability. Methodology: Wang, Song & Barabási, Science 342:127 (2013). ' +
        'See `list_breakouts` for the leaderboard of top predicted breakouts.',
      inputSchema: {
        record_id: z
          .string()
          .describe('Stable record id (use search_records to find one).')
      }
    },
    async (args) => {
      const fits = getFits();
      const fit = findFitById(fits, args.record_id);
      if (!fit) {
        return jsonResult({
          error: `No fit for record_id "${args.record_id}". The record may not be an academic paper, or its citation trajectory is missing.`
        });
      }
      return jsonResult(fit);
    }
  );

  // -----------------------------------------------------------------------
  // 12. list_breakouts
  // -----------------------------------------------------------------------
  server.registerTool(
    'list_breakouts',
    {
      title: 'Top predicted citation breakouts (WSB log-normal)',
      description:
        'Returns the top-N predicted citation breakouts — growth-phase papers with the ' +
        'largest asymptote/observed ratio (still-growing fastest), restricted to rows ' +
        'with real bucketed citation trajectories. Use this as the watchlist for which ' +
        'papers to track for citation impact over the next 12-24 months.',
      inputSchema: {
        limit: z
          .number()
          .int()
          .min(1)
          .max(50)
          .optional()
          .describe('Max breakouts to return (default 15, max 50).')
      }
    },
    async (args) => {
      const fits = getFits();
      const limit = args.limit ?? 15;
      const top = topBreakouts(fits, limit);
      return jsonResult({ limit, totalMatches: top.length, breakouts: top });
    }
  );

  // -----------------------------------------------------------------------
  // 13. between_models
  // -----------------------------------------------------------------------
  server.registerTool(
    'between_models',
    {
      title: 'Rank candidates between two positioning anchors',
      description:
        'Returns records whose cost × capability composite falls between two anchor record ids. ' +
        'Optional single-tag use-case filter from the controlled vocabulary ' +
        '(scoped-agentic, long-running-session, multi-agent-coordination, memory-augmented-chat, ' +
        'code-generation-focused, analytical-summarization, latency-sensitive, offline-capable). ' +
        'Each candidate carries a score in [0, 1], a rationale list, and a caveats list — ' +
        'LLM-unverified cells are excluded from the score and surfaced as caveats per Phase 2 §3.4.',
      inputSchema: {
        anchor_low_id: z
          .string()
          .describe('Stable record id of the low-end positioning anchor.'),
        anchor_high_id: z
          .string()
          .describe('Stable record id of the high-end positioning anchor.'),
        use_case: z
          .enum(USE_CASE_TAGS as unknown as [string, ...string[]])
          .optional()
          .describe(
            'Optional single use-case tag from the controlled vocabulary (see description).'
          ),
        k: z
          .number()
          .int()
          .min(1)
          .max(50)
          .optional()
          .describe('Max candidates to return (default 5, max 50).')
      }
    },
    async (args) => {
      const records = loadRecords();
      return jsonResult(betweenModels(records, args));
    }
  );

  // -----------------------------------------------------------------------
  // 14. recommend_for_project
  // -----------------------------------------------------------------------
  server.registerTool(
    'recommend_for_project',
    {
      title: 'Recommend records by free-text or structured-form constraints',
      description:
        'Given a free-text project description OR a structured form, returns ranked candidates ' +
        'split by category (memory / harness / model). Parsing is deterministic keyword/synonym ' +
        'matching against the 8-tag controlled vocabulary — NOT an LLM (Phase 2 §4). The response ' +
        'includes `parsed_constraints` plus `matched_terms` / `unmatched_terms` so clients can echo ' +
        '"I interpreted your request as …" before reporting results. If both `description` and ' +
        '`structured` are passed, `structured` wins (spec §4.3). LLM-unverified cells are excluded ' +
        'from scoring and surfaced as caveats per §3.4.',
      inputSchema: {
        description: z
          .string()
          .optional()
          .describe('Free-text project description. Parsed via keyword/synonym matching.'),
        structured: z
          .object({
            project_shape: z
              .enum(['single-agent', 'multi-agent', 'chat', 'pipeline'])
              .optional(),
            scale: z.enum(['prototype', 'production', 'large-scale']).optional(),
            latency_budget_ms: z.number().optional(),
            persistence: z.enum(['none', 'session', 'long-term']).optional(),
            deployment: z.enum(['cloud', 'self-hosted', 'offline']).optional(),
            cost_ceiling_usd_per_mtok: z.number().optional()
          })
          .optional()
          .describe('Structured form. If present, overrides `description`.'),
        max_results: z
          .number()
          .int()
          .min(1)
          .max(50)
          .optional()
          .describe('Max candidates per category (default 5, max 50).'),
        categories: z
          .array(z.enum(['memory', 'harness', 'model']))
          .optional()
          .describe('Categories to return. Default all three.')
      }
    },
    async (args) => {
      const records = loadRecords();
      return jsonResult(
        recommendForProject(records, {
          description: args.description,
          structured: args.structured as StructuredForm | undefined,
          max_results: args.max_results,
          categories: args.categories as RecommendCategory[] | undefined
        })
      );
    }
  );

  // Wire up stdio and start listening.
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Stderr only — stdout is reserved for MCP traffic.
  console.error(
    `[landscape-mcp] ready. schema=${meta.schemaVersion} generated=${meta.generatedAt}`
  );
}

main().catch((err) => {
  console.error('[landscape-mcp] fatal:', err);
  process.exit(1);
});
