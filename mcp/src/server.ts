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
import { loadRecords, loadEdges, getMeta } from './data.js';
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
        'section (exact match on primary section), tier (1=battle-tested → 5=theoretical).',
      inputSchema: {
        query: z.string().describe('Search query (case-insensitive substring match).'),
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
