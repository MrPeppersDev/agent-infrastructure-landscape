#!/usr/bin/env node
// landscape — CLI for the AI agent infrastructure landscape catalog.
//
// 9 read-only subcommands mirroring the MCP server in ../mcp. The query
// layer is imported directly from mcp/dist/tools.js so there is exactly
// one source of truth for catalog logic.
//
// Output is text by default. Two machine-friendly modes:
//   --json   stringified result from tools.ts (verbatim)
//   --csv    header row + data rows; only honoured by tabular subcommands
//
// Run via:
//   ./dist/landscape.js <subcommand> [args]
//   npx landscape <subcommand>  (once published)
//   node ./dist/landscape.js sections
//
// See README.md in this directory for full examples.

import { Command } from 'commander';
import {
  searchRecords,
  getRecord,
  findRelated,
  coverageSummary,
  compareWithEdges,
  listSections,
  recentChanges,
  findEvalOrphans,
  findSubstrateRisk
} from '../../mcp/dist/tools.js';
import { loadRecords, loadEdges, getMeta } from '../../mcp/dist/data.js';
import type { EdgeType } from '../../mcp/dist/tools.js';
import {
  formatSearch,
  formatRecord,
  formatRelated,
  formatCoverage,
  formatCompare,
  formatSections,
  formatRecent,
  formatEvalOrphans,
  formatSubstrate,
  type FormatOptions
} from './format.js';

// ===========================================================================
// Setup
// ===========================================================================

const program = new Command();

program
  .name('landscape')
  .description(
    'CLI for the AI agent infrastructure landscape catalog (912 records × 68 columns, 528 edges). ' +
      'Read-only query interface; shares the pure query layer with the local-stdio MCP server in ../mcp.'
  )
  .version('1.0.0')
  .option('--json', 'emit machine-readable JSON to stdout')
  .option('--csv', 'emit CSV to stdout (tabular subcommands only)')
  .showHelpAfterError();

/**
 * Read the global flags off whichever Command we were invoked from. Commander
 * gives the subcommand its own options object; --json / --csv are declared at
 * the root so they live on the root program. We also bubble them from the
 * subcommand in case the user wrote `landscape search foo --json`.
 */
function globalOpts(cmd: Command): FormatOptions {
  const root = cmd.parent ?? cmd;
  const rootOpts = root.opts<{ json?: boolean; csv?: boolean }>();
  const cmdOpts = cmd.opts<{ json?: boolean; csv?: boolean }>();
  return {
    json: !!(rootOpts.json || cmdOpts.json),
    csv: !!(rootOpts.csv || cmdOpts.csv)
  };
}

function emit(s: string): void {
  process.stdout.write(s + '\n');
}

function die(message: string, code = 1): never {
  process.stderr.write('landscape: ' + message + '\n');
  process.exit(code);
}

// ===========================================================================
// 1. search
// ===========================================================================

program
  .command('search')
  .description('Free-text search over id, name, description, and claims (case-insensitive).')
  .argument('<query>', 'search query')
  .option('-s, --section <name>', 'filter to primary section (exact match — see `landscape sections`)')
  .option('-t, --tier <n>', 'filter to tier (1=battle-tested → 5=theoretical)', (v) => parseInt(v, 10))
  .option('-l, --limit <n>', 'max results to return (default 25, max 200)', (v) => parseInt(v, 10))
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV')
  .action((query: string, opts: { section?: string; tier?: number; limit?: number }, cmd: Command) => {
    const records = loadRecords();
    const result = searchRecords(records, {
      query,
      section: opts.section,
      tier: opts.tier,
      limit: opts.limit
    });
    emit(formatSearch(result, globalOpts(cmd)));
  });

// ===========================================================================
// 2. show
// ===========================================================================

program
  .command('show')
  .description('Print the full record for a stable id (all 68 cells + taxonomy + section memberships).')
  .argument('<id>', 'stable record id (use `landscape search` to find one)')
  .option('--json', 'emit JSON (recommended for full record inspection)')
  .option('--csv', 'emit CSV (one row per cell)')
  .action((id: string, _opts, cmd: Command) => {
    const records = loadRecords();
    const record = getRecord(records, { id });
    const opts = globalOpts(cmd);
    if (!record && !opts.json && !opts.csv) {
      die(`record not found: ${id}`);
    }
    emit(formatRecord(record, id, opts));
    if (!record) process.exit(1);
  });

// ===========================================================================
// 3. related
// ===========================================================================

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

program
  .command('related')
  .description('Edges touching a record id, in both directions, with related summaries.')
  .argument('<id>', 'stable record id')
  .option(
    '-e, --edge-type <type>',
    `filter to a single edge type (one of: ${EDGE_TYPES.join(', ')})`
  )
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV')
  .action((id: string, opts: { edgeType?: string }, cmd: Command) => {
    if (opts.edgeType && !EDGE_TYPES.includes(opts.edgeType as EdgeType)) {
      die(`unknown edge type: ${opts.edgeType}. Valid: ${EDGE_TYPES.join(', ')}`);
    }
    const records = loadRecords();
    const edges = loadEdges();
    const result = findRelated(records, edges, {
      id,
      edge_type: opts.edgeType as EdgeType | undefined
    });
    emit(formatRelated(result, globalOpts(cmd)));
  });

// ===========================================================================
// 4. coverage
// ===========================================================================

const COVERAGE_DIMS = ['observability', 'cost', 'eval', 'benchmark'] as const;
type CoverageDim = (typeof COVERAGE_DIMS)[number];

program
  .command('coverage')
  .description('Per-feature coverage stats across the catalog (observability / cost / eval / benchmark).')
  .argument('<dimension>', `one of: ${COVERAGE_DIMS.join(', ')}`)
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV')
  .action((dimension: string, _opts, cmd: Command) => {
    if (!COVERAGE_DIMS.includes(dimension as CoverageDim)) {
      die(`unknown dimension: ${dimension}. Valid: ${COVERAGE_DIMS.join(', ')}`);
    }
    const records = loadRecords();
    const result = coverageSummary(records, { dimension: dimension as CoverageDim });
    emit(formatCoverage(result, globalOpts(cmd)));
  });

// ===========================================================================
// 5. compare
// ===========================================================================

program
  .command('compare')
  .description('Side-by-side comparison of two records across every column, plus direct edges between them.')
  .argument('<id_a>', 'first record id')
  .argument('<id_b>', 'second record id')
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV (one row per cell)')
  .action((idA: string, idB: string, _opts, cmd: Command) => {
    const records = loadRecords();
    const edges = loadEdges();
    try {
      const result = compareWithEdges(records, edges, { id_a: idA, id_b: idB });
      emit(formatCompare(result, globalOpts(cmd)));
    } catch (err) {
      die(err instanceof Error ? err.message : String(err));
    }
  });

// ===========================================================================
// 6. sections
// ===========================================================================

program
  .command('sections')
  .description('List all primary section names in the catalog (alphabetised).')
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV')
  .action((_opts, cmd: Command) => {
    const records = loadRecords();
    const sections = listSections(records);
    emit(formatSections(sections, globalOpts(cmd)));
  });

// ===========================================================================
// 7. recent
// ===========================================================================

program
  .command('recent')
  .description('Records updated since a date (or the 20 most-recently-shipped if --since omitted).')
  .option(
    '-s, --since <date>',
    'ISO date (YYYY-MM-DD or full ISO), or a bare year. Omit for the 20 most-recent.'
  )
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV')
  .action((opts: { since?: string }, cmd: Command) => {
    const records = loadRecords();
    const result = recentChanges(records, { since: opts.since });
    emit(formatRecent(result, globalOpts(cmd)));
  });

// ===========================================================================
// 8. eval-orphans
// ===========================================================================

program
  .command('eval-orphans')
  .description(
    'Products with observability adopted but no evals, where the absence has been verified. ' +
      'Surfaces the 37-point obs-vs-eval adoption gap from State of Agent Engineering 2025.'
  )
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV')
  .action((_opts, cmd: Command) => {
    const records = loadRecords();
    const orphans = findEvalOrphans(records);
    emit(formatEvalOrphans(orphans, globalOpts(cmd)));
  });

// ===========================================================================
// 9. substrate-risk
// ===========================================================================

program
  .command('substrate-risk')
  .description(
    'Records that runtime-depend on a substrate. Use for blast-radius questions ' +
      '("what breaks if OpenAI changes pricing?") and lock-in analysis.'
  )
  .argument('<substrate>', 'substrate name or id (e.g. "OpenAI", "Anthropic", "MCP")')
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV')
  .action((substrate: string, _opts, cmd: Command) => {
    const records = loadRecords();
    const edges = loadEdges();
    const result = findSubstrateRisk(records, edges, { substrate });
    emit(formatSubstrate(result, globalOpts(cmd)));
  });

// ===========================================================================
// Meta — version + dataset info
// ===========================================================================

program
  .command('info')
  .description('Show CLI version, catalog schema version, and dataset stats.')
  .option('--json', 'emit JSON')
  .action((_opts, cmd: Command) => {
    const records = loadRecords();
    const edges = loadEdges();
    const meta = getMeta();
    const payload = {
      cliVersion: '1.0.0',
      schemaVersion: meta.schemaVersion,
      generatedAt: meta.generatedAt,
      records: records.length,
      edges: edges.length
    };
    const opts = globalOpts(cmd);
    if (opts.json) {
      emit(JSON.stringify(payload, null, 2));
      return;
    }
    emit(`landscape-cli ${payload.cliVersion}`);
    emit(`schema:      ${payload.schemaVersion}`);
    emit(`generated:   ${payload.generatedAt}`);
    emit(`records:     ${payload.records}`);
    emit(`edges:       ${payload.edges}`);
  });

// ===========================================================================
// Parse + run
// ===========================================================================

program.parseAsync(process.argv).catch((err: unknown) => {
  die(err instanceof Error ? err.message : String(err));
});
