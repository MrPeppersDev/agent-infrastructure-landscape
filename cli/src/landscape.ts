#!/usr/bin/env node
// landscape — CLI for the AI agent infrastructure landscape catalog.
//
// Read-only subcommands mirroring the MCP server in ../mcp. The query
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
  findSubstrateRisk,
  findByDecayCause
} from '../../mcp/dist/tools.js';
import {
  fitCitationCurves,
  topBreakouts,
  findFitById,
  type CitationFit
} from '../../mcp/dist/citation-prediction.js';
import { betweenModels, recommendForProject } from '../../mcp/dist/recommender.js';
import type { RecommendCategory, StructuredForm } from '../../mcp/dist/recommender.js';
import { loadRecords, loadEdges, getMeta, loadStackIndex, loadReplacements, loadChooserItems, familyIdForSection, loadMigrations, loadSystemAliases, loadRedirects, loadPricing, loadVectorPricing, loadStackPricing } from '../../mcp/dist/data.js';
import { chooseInfra, DEFAULT_INFRA, NEEDS } from '../../mcp/dist/chooser-infra.js';
import type { InfraAnswers, InfraKind } from '../../mcp/dist/chooser-infra.js';
import { compatibility, worksWith, setAliases } from '../../mcp/dist/compat.js';
import { choose, alternatives, DEFAULT_ANSWERS } from '../../mcp/dist/chooser.js';
import type { Answers } from '../../mcp/dist/chooser.js';
import { checkManifest, STATUS_LABEL } from '../../mcp/dist/stack-check.js';
import { planStack, slimPlan, PRODUCTS, LAYERS } from '../../mcp/dist/composer.js';
import type { StackAnswers, LayerId, ProductType } from '../../mcp/dist/composer.js';
import { writeFileSync } from 'node:fs';
import type { ManifestFormat } from '../../mcp/dist/stack-check.js';
import { readFileSync } from 'node:fs';
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
  formatDecayCause,
  formatPredict,
  formatBreakouts,
  formatBetween,
  formatRecommendation,
  type FormatOptions
} from './format.js';

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
type UseCaseTag = (typeof USE_CASE_TAGS)[number];

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
  // Walk to the program root — nested subcommands (e.g. `recommend
  // between`) have an intermediate parent that doesn't carry the
  // global --json / --csv flags.
  let root: Command = cmd;
  while (root.parent) root = root.parent;
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
// 1b. check — is anything in my stack archived / acquired / stale?
// ===========================================================================

program
  .command('check')
  .description('Check a manifest (package.json, requirements.txt, pyproject.toml, MCP config) for catalogued dependencies that are archived, deprecated, acquired, renamed or stale.')
  .argument('[file]', 'manifest path (reads stdin when omitted or "-")')
  .option('-f, --format <fmt>', 'force format: package.json | requirements.txt | pyproject.toml | mcp-config | list')
  .option('--all', 'also list matched dependencies that are fine')
  .option('--fail-on-attention', 'exit 2 when any dependency needs attention (for CI)')
  .option('--json', 'emit JSON')
  .action((file: string | undefined, opts: { format?: string; all?: boolean; failOnAttention?: boolean }, cmd: Command) => {
    const text = !file || file === '-' ? readFileSync(0, 'utf-8') : readFileSync(file, 'utf-8');
    const report = checkManifest(text, loadStackIndex(), {
      filename: file,
      format: opts.format as ManifestFormat | undefined,
      replacements: loadReplacements()
    });
    if (globalOpts(cmd).json) {
      emit(JSON.stringify(report, null, 2));
    } else {
      const lines: string[] = [];
      lines.push(`${report.dependencyCount} dependencies (${report.format}) · ${report.matched.length} in the catalog · ${report.attention.length} need attention`);
      const show = opts.all ? report.matched : report.attention;
      for (const f of show) {
        const r = f.record;
        lines.push('');
        lines.push(`  ${f.dependency.name}  →  ${r.name}`);
        lines.push(`    ${STATUS_LABEL[r.status]}${r.note ? ' — ' + r.note : ''}`);
        if (r.context) lines.push(`    ${r.context}`);
        if (r.llm_lock) lines.push(`    model lock-in: ${r.llm_lock}`);
        if (r.evidence) lines.push(`    evidence: ${r.evidence}`);
        if (f.replacements?.length) lines.push(`    consider instead: ${f.replacements.map((x) => x.name).join(', ')}`);
        lines.push(`    record: landscape show ${f.recordId}`);
      }
      if (!report.attention.length && !opts.all) lines.push('\n  Nothing archived, deprecated, acquired or stale among the catalogued dependencies.');
      lines.push(`\nindex built ${report.indexGeneratedAt}`);
      emit(lines.join('\n'));
    }
    if (opts.failOnAttention && report.attention.length) process.exit(2);
  });

// ===========================================================================
// 1c. choose / alternatives
// ===========================================================================

program
  .command('choose')
  .description('Recommend a memory layer: three picks with cited reasons (same logic as /choose).')
  .option('--coding', 'building a coding agent / dev tool (default: an app that remembers users)')
  .option('--hosting <h>', 'self | managed | any', 'any')
  .option('--oss', 'require an open-source licence')
  .option('--mcp', 'require MCP support')
  .option('--conflict <c>', 'history | latest | llm | any', 'any')
  .option('--shape <s>', 'facts | conversations | documents | relationships | any', 'any')
  .option('--json', 'emit JSON')
  .action((o: { coding?: boolean; hosting: string; oss?: boolean; mcp?: boolean; conflict: string; shape: string }, cmd: Command) => {
    const answers = {
      ...DEFAULT_ANSWERS,
      building: o.coding ? 'coding' : 'app',
      hosting: o.hosting,
      oss: !!o.oss,
      mcp: !!o.mcp,
      conflict: o.conflict,
      shape: o.shape
    } as Answers;
    const r = choose(loadChooserItems(), answers);
    if (globalOpts(cmd).json) return emit(JSON.stringify(r, null, 2));
    const lines: string[] = [];
    r.picks.forEach((p, i) => {
      lines.push(`${i + 1}. ${p.item.name}${p.warning ? '  ⚠ ' + p.warning : ''}`);
      for (const x of p.reasons) lines.push(`     · ${x.text}${x.citation ? '  ' + x.citation : ''}`);
      if (p.unconfirmed.length) lines.push(`     not confirmed: ${p.unconfirmed.join(', ')}`);
    });
    if (!r.picks.length) lines.push('No catalogued system confirms all of those must-haves.');
    if (r.alsoConsider.length) lines.push('', `also consider: ${r.alsoConsider.map((x) => x.item.name).join(', ')}`);
    if (r.unconfirmed.length) lines.push(`might fit (unconfirmed): ${r.unconfirmed.map((x) => x.item.name).join(', ')}`);
    emit(lines.join('\n'));
  });

program
  .command('choose-stack')
  .description('Recommend an agent framework or data store: three picks with cited reasons (same logic as /choose/framework and /choose/data).')
  .argument('<kind>', 'framework | data')
  .option('--need <n>', 'framework: library | durable | tools | nocode | sandbox; data: vectors | graph | embeddings')
  .option('--language <l>', 'python | typescript | any', 'any')
  .option('--hosting <h>', 'self | managed | any', 'any')
  .option('--oss', 'require an open-source licence')
  .option('--mcp', 'require MCP support')
  .option('--existing', 'data: prefer a store on a database you may already run (Postgres, MongoDB, Elastic, Redis…)')
  .option('--json', 'emit JSON')
  .action((kind: string, o: { need?: string; language: string; hosting: string; oss?: boolean; mcp?: boolean; existing?: boolean }, cmd: Command) => {
    if (kind !== 'framework' && kind !== 'data') die('kind must be framework or data');
    const k = kind as InfraKind;
    const need = o.need ?? DEFAULT_INFRA[k].need;
    if (!NEEDS[k].some((n) => n.value === need)) die(`--need must be one of ${NEEDS[k].map((n) => n.value).join(', ')}`);
    const a = { ...DEFAULT_INFRA[k], need, language: o.language, hosting: o.hosting, oss: !!o.oss, mcp: !!o.mcp, existing: !!o.existing } as InfraAnswers;
    const r = chooseInfra(loadChooserItems(), a);
    if (globalOpts(cmd).json) return emit(JSON.stringify(r, null, 2));
    const lines: string[] = [];
    r.picks.forEach((p, i) => {
      lines.push(`${i + 1}. ${p.item.name}${p.warning ? '  ⚠ ' + p.warning : ''}`);
      for (const x of p.reasons) lines.push(`     · ${x.text}${x.citation ? '  ' + x.citation : ''}`);
      if (p.unconfirmed.length) lines.push(`     not confirmed: ${p.unconfirmed.join(', ')}`);
    });
    if (!r.picks.length) lines.push('No catalogued system confirms all of those must-haves.');
    if (r.alsoConsider.length) lines.push('', `also consider: ${r.alsoConsider.map((x) => x.item.name).join(', ')}`);
    if (r.unconfirmed.length) lines.push(`might fit (unconfirmed): ${r.unconfirmed.map((x) => x.item.name).join(', ')}`);
    emit(lines.join('\n'));
  });

program
  .command('stack')
  .description('Plan a whole agent stack: one cited pick per layer, why-not for runners-up, exit paths, integrations, risk score, OWASP LLM Top 10 coverage, eval plan and a stack.yml.')
  .argument('[product]', `${Object.keys(PRODUCTS).join(' | ')} (default support-agent)`)
  .option('--language <l>', 'python | typescript | any', 'any')
  .option('--hosting <h>', 'self | managed | any', 'any')
  .option('--oss', 'require open-source licences')
  .option('--mcp', 'require MCP support where it applies')
  .option('--add <layers>', `extra layers, comma-separated (${LAYERS.map((l) => l.id).join(', ')})`)
  .option('--avoid <ids>', 'record ids never to pick, comma-separated')
  .option('--pin <pairs>', 'layer=record-id pairs, comma-separated')
  .option('--compliance <codes>', 'attestations every hosted service must publish, e.g. soc2-type2,hipaa')
  .option('-o, --out <file>', 'also write the stack.yml to this file')
  .option('--json', 'emit JSON')
  .action((product: string | undefined, o: { language: string; hosting: string; oss?: boolean; mcp?: boolean; add?: string; avoid?: string; pin?: string; compliance?: string; out?: string }, cmd: Command) => {
    const p = (product ?? 'support-agent') as ProductType;
    if (!(p in PRODUCTS)) die(`product must be one of ${Object.keys(PRODUCTS).join(', ')}`);
    const list = (v?: string) => (v ? v.split(',').map((x) => x.trim()).filter(Boolean) : undefined);
    const moved = loadRedirects();
    const a: StackAnswers = {
      product: p, language: o.language as StackAnswers['language'], hosting: o.hosting as StackAnswers['hosting'], oss: !!o.oss, mcp: !!o.mcp,
      add: list(o.add) as LayerId[] | undefined,
      avoid: list(o.avoid)?.map((i) => moved[i] ?? i),
      compliance: list(o.compliance),
      pin: o.pin ? Object.fromEntries(list(o.pin)!.map((kv) => kv.split('=')).map(([k, v]) => [k, moved[v] ?? v])) : undefined
    };
    setAliases(loadSystemAliases());
    const plan = planStack({
      items: loadChooserItems(), records: loadRecords() as never, edges: loadEdges() as never, migrations: loadMigrations() as never,
      pricing: { stack: loadStackPricing() as never, memory: loadPricing() as never, vector: loadVectorPricing() as never }
    }, a);
    if (o.out) writeFileSync(o.out, plan.stackYaml);
    if (globalOpts(cmd).json) return emit(JSON.stringify(slimPlan(plan), null, 2));
    const lines: string[] = [`${plan.product} — risk ${plan.risk.level} (${plan.risk.score})`, ''];
    for (const l of plan.layers) {
      const pk = l.pick;
      lines.push(`${l.label}: ${pk ? pk.item.name : '— nothing in the catalog meets the requirements'}${pk?.warning ? '  ⚠ ' + pk.warning : ''}${l.pickUnconfirmed ? '  (unconfirmed)' : ''}`);
      for (const x of pk?.reasons.slice(0, 4) ?? []) lines.push(`     · ${x.text}${x.citation ? '  ' + x.citation : ''}`);
      for (const w of l.whyNot.slice(0, 3)) lines.push(`     not ${w.name}: ${w.because.map((b) => b.text).join('; ')}`);
      if (l.exit?.fallback) lines.push(`     exit: self-host ${l.exit.selfHost.tri}, open source ${l.exit.openSource.tri}; fallback ${l.exit.fallback.name}`);
    }
    lines.push('', 'Risk factors:');
    for (const f of plan.risk.factors) lines.push(`  +${f.points}  ${f.detail}`);
    lines.push('', `Security (OWASP LLM Top 10, ${plan.security.source}):`);
    for (const s of plan.security.items) lines.push(`  ${s.id} ${s.risk}: ${s.status}${s.by.length ? ' — ' + s.by.join(', ') : ''}${s.status !== 'addressed' ? ' — ' + s.note : ''}`);
    if (plan.evals.benchmarks.length) lines.push('', `Benchmarks to run: ${plan.evals.benchmarks.map((b) => b.name).join(', ')}`);
    if (plan.cost) {
      const c = plan.cost;
      lines.push('', `Monthly cost from published list prices: ${c.lowerBound ? 'at least ' : ''}$${Math.round(c.knownMonthlyUsd).toLocaleString('en-US')} (prices checked ${c.checked}; ${c.workload.runsPerDay} runs/day)`);
      for (const l of c.lines) lines.push(`  ${l.name}: ${typeof l.monthlyUsd === 'number' ? '$' + Math.round(l.monthlyUsd).toLocaleString('en-US') : l.monthlyUsd === null ? 'contact sales' : 'no published price'}${l.plan ? ' — ' + l.plan : ''}`);
    }
    lines.push('', o.out ? `stack.yml written to ${o.out}` : plan.stackYaml);
    emit(lines.join('\n'));
  });

program
  .command('compat')
  .description('Do these systems work together? Integration evidence for every pair (or, with one id, what it works with).')
  .argument('<ids...>', 'record ids (see `landscape search`)')
  .option('--json', 'emit JSON')
  .action((rawIds: string[], _o: unknown, cmd: Command) => {
    const moved = loadRedirects();
    const ids = rawIds.map((i) => moved[i] ?? i);
    setAliases(loadSystemAliases());
    const records = loadRecords() as never;
    const edges = loadEdges() as never;
    if (ids.length === 1) {
      const w = worksWith(records, edges, ids[0], 50);
      if (globalOpts(cmd).json) return emit(JSON.stringify({ id: ids[0], worksWith: w }, null, 2));
      return emit([`Documented to work with ${ids[0]}:`, ...w.map((x) => `  ${x.name}  (${x.evidence.length} source${x.evidence.length === 1 ? '' : 's'})`)].join('\n'));
    }
    const r = compatibility(records, edges, ids);
    if (globalOpts(cmd).json) return emit(JSON.stringify(r, null, 2));
    const name = new Map(r.systems.map((s) => [s.id, s.name]));
    const lines: string[] = r.missing.length ? [`unknown ids: ${r.missing.join(', ')}`] : [];
    for (const p of r.pairs) {
      lines.push(`${name.get(p.a)} + ${name.get(p.b)}: ${p.status}`);
      for (const e of p.evidence) lines.push(`     · ${e.kind === 'edge' ? `${e.type}: ${e.text}` : `${e.cell}: ${e.text}`}${e.citation ? '  ' + e.citation : ''}`);
    }
    emit(lines.join('\n'));
  });

program
  .command('alternatives')
  .description('Live alternatives to a system, ranked by shared memory design and must-haves.')
  .argument('<id>', 'record id (see `landscape search`)')
  .option('-l, --limit <n>', 'how many (default 5)', (v) => parseInt(v, 10))
  .option('--json', 'emit JSON')
  .action((id: string, o: { limit?: number }, cmd: Command) => {
    const items = loadChooserItems();
    const t = items.find((i) => i.id === (loadRedirects()[id] ?? id));
    if (!t) die(`record not found: ${id}`);
    const fam = familyIdForSection(t.section);
    const alts = alternatives(t, items.filter((i) => familyIdForSection(i.section) === fam), o.limit ?? 5);
    const mig = loadMigrations().get(t.id) ?? null;
    if (globalOpts(cmd).json) return emit(JSON.stringify({ target: t.name, migration: mig, alternatives: alts }, null, 2));
    if (mig && mig.action === 'migrate') {
      emit([`Official migration path for ${t.name}: ${mig.summary}`, ...mig.steps.map((x, i) => `  ${i + 1}. ${x}`), `  sources: ${mig.sources.join(' ')}`, ''].join('\n'));
    }
    emit([`Alternatives to ${t.name}:`, ...alts.map((a) => `  ${a.name}${a.warning ? '  ⚠ ' + a.warning : ''}\n     ${a.why.join('; ')}`)].join('\n'));
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
// 10. decay-cause
// ===========================================================================

program
  .command('decay-cause')
  .description(
    'Records labeled with a given decay cause from the T3-1 forensics backfill. ' +
      'Enum: acquired | pivoted | unfunded | lost-benchmark-race | superseded | archived | research-complete | unknown.'
  )
  .argument('<cause>', 'decay cause (e.g. archived, acquired, superseded, research-complete)')
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV')
  .action((cause: string, _opts, cmd: Command) => {
    const records = loadRecords();
    const result = findByDecayCause(records, { cause });
    emit(formatDecayCause(result, globalOpts(cmd)));
  });

// ===========================================================================
// 11. predict — single-paper WSB citation forecast
// ===========================================================================

// Memoise so `landscape predict` followed by `landscape breakouts` only
// pays the ~5sec fit cost once. CitationFit is plain data — caching the
// whole result is cheap.
let cachedFits: CitationFit[] | null = null;
function getFits(): CitationFit[] {
  if (cachedFits === null) {
    cachedFits = fitCitationCurves(loadRecords());
  }
  return cachedFits;
}

program
  .command('predict')
  .description(
    'Wang-Song-Barabási citation breakout forecast for a paper. Returns lambda/mu/sigma, ' +
      'predicted asymptote with 90% CI, R², phase, and breakout probability. ' +
      'See `landscape breakouts` for the top-N watchlist across the catalog.'
  )
  .argument('<id>', 'stable record id of an academic-paper row')
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV (single-row summary)')
  .action((id: string, _opts, cmd: Command) => {
    const fits = getFits();
    const fit = findFitById(fits, id);
    const opts = globalOpts(cmd);
    if (!fit && !opts.json && !opts.csv) {
      die(
        `no fit for record_id "${id}". Run \`landscape show ${id}\` to confirm it's an academic-paper row with a populated citation trajectory.`
      );
    }
    emit(formatPredict(fit ?? null, id, opts));
    if (!fit) process.exit(1);
  });

// ===========================================================================
// 12. breakouts — top predicted citation breakouts
// ===========================================================================

program
  .command('breakouts')
  .description(
    'Top predicted citation breakouts — growth-phase papers with the largest ' +
      'asymptote/observed ratio (still-growing fastest), restricted to rows with ' +
      'real bucketed citation trajectories. Read as the catalog\'s watchlist.'
  )
  .option('-l, --limit <n>', 'max breakouts to return (default 15, max 50)', (v) => parseInt(v, 10))
  .option('--json', 'emit JSON')
  .option('--csv', 'emit CSV')
  .action((opts: { limit?: number }, cmd: Command) => {
    const fits = getFits();
    const limit = Math.max(1, Math.min(50, opts.limit ?? 15));
    const top = topBreakouts(fits, limit);
    emit(formatBreakouts(top, limit, globalOpts(cmd)));
  });

// ===========================================================================
// 13. recommend — Phase 2 / Gate 3 (issue #97)
// ===========================================================================

const recommend = program
  .command('recommend')
  .description('Ranked recommender surfaces (Phase 2 / Gate 3 — positioning + constraint).');

recommend
  .command('between')
  .description(
    'Rank candidates whose cost × capability falls between two anchor records. ' +
      'Filter optionally by a single use-case tag from the controlled vocabulary.'
  )
  .argument('<low-id>', 'stable record id of the low-end positioning anchor')
  .argument('<high-id>', 'stable record id of the high-end positioning anchor')
  .option(
    '-u, --use-case <tag>',
    `single use-case tag (one of: ${USE_CASE_TAGS.join(', ')})`
  )
  .option('-k, --k <n>', 'max candidates to return (default 5, max 50)', (v) => parseInt(v, 10))
  .option('--json', 'emit JSON (matches the `between_models` MCP tool response byte-for-byte)')
  .option('--csv', 'emit CSV (one row per candidate)')
  .action(
    (
      lowId: string,
      highId: string,
      opts: { useCase?: string; k?: number },
      cmd: Command
    ) => {
      if (opts.useCase && !USE_CASE_TAGS.includes(opts.useCase as UseCaseTag)) {
        die(`unknown use-case tag: ${opts.useCase}. Valid: ${USE_CASE_TAGS.join(', ')}`);
      }
      const records = loadRecords();
      const candidates = betweenModels(records, {
        anchor_low_id: lowId,
        anchor_high_id: highId,
        use_case: opts.useCase as UseCaseTag | undefined,
        k: opts.k
      });
      emit(formatBetween(candidates, { low: lowId, high: highId }, globalOpts(cmd)));
    }
  );

const PROJECT_SHAPES = ['single-agent', 'multi-agent', 'chat', 'pipeline'] as const;
const SCALES = ['prototype', 'production', 'large-scale'] as const;
const PERSISTENCES = ['none', 'session', 'long-term'] as const;
const DEPLOYMENTS = ['cloud', 'self-hosted', 'offline'] as const;
const CATEGORIES = ['memory', 'harness', 'model'] as const;

type ProjectShape = (typeof PROJECT_SHAPES)[number];
type Scale = (typeof SCALES)[number];
type Persistence = (typeof PERSISTENCES)[number];
type Deployment = (typeof DEPLOYMENTS)[number];

recommend
  .command('for')
  .description(
    'Recommend candidates by free-text description OR structured-form flags. ' +
      'Returns ranked candidates split by category (memory / harness / model). ' +
      'Parsing is deterministic keyword matching — no LLM (Phase 2 §4).'
  )
  .argument('[description]', 'free-text project description (omit when using structured-form flags)')
  .option('--shape <shape>', `project shape (one of: ${PROJECT_SHAPES.join(', ')})`)
  .option('--scale <scale>', `scale (one of: ${SCALES.join(', ')})`)
  .option('--latency-ms <n>', 'latency budget in ms (≤1000 triggers latency-sensitive)', (v) => parseInt(v, 10))
  .option('--persistence <p>', `persistence (one of: ${PERSISTENCES.join(', ')})`)
  .option('--deployment <d>', `deployment (one of: ${DEPLOYMENTS.join(', ')})`)
  .option('--cost-ceiling <usd>', 'max $/Mtok input cost', (v) => parseFloat(v))
  .option('-k, --k <n>', 'max candidates per category (default 5, max 50)', (v) => parseInt(v, 10))
  .option(
    '--category <list>',
    `comma-separated subset of: ${CATEGORIES.join(', ')} (default all three)`
  )
  .option('--json', 'emit JSON (matches the `recommend_for_project` MCP tool response byte-for-byte)')
  .option('--csv', 'emit CSV (one row per candidate, with category column)')
  .action(
    (
      description: string | undefined,
      opts: {
        shape?: string;
        scale?: string;
        latencyMs?: number;
        persistence?: string;
        deployment?: string;
        costCeiling?: number;
        k?: number;
        category?: string;
      },
      cmd: Command
    ) => {
      // Validate enums up front so we fail fast with a helpful message
      // rather than letting bad input flow into the parser silently.
      if (opts.shape && !PROJECT_SHAPES.includes(opts.shape as ProjectShape)) {
        die(`unknown shape: ${opts.shape}. Valid: ${PROJECT_SHAPES.join(', ')}`);
      }
      if (opts.scale && !SCALES.includes(opts.scale as Scale)) {
        die(`unknown scale: ${opts.scale}. Valid: ${SCALES.join(', ')}`);
      }
      if (opts.persistence && !PERSISTENCES.includes(opts.persistence as Persistence)) {
        die(`unknown persistence: ${opts.persistence}. Valid: ${PERSISTENCES.join(', ')}`);
      }
      if (opts.deployment && !DEPLOYMENTS.includes(opts.deployment as Deployment)) {
        die(`unknown deployment: ${opts.deployment}. Valid: ${DEPLOYMENTS.join(', ')}`);
      }

      let categories: RecommendCategory[] | undefined;
      if (opts.category) {
        const parsed = opts.category.split(',').map((s) => s.trim()).filter(Boolean);
        for (const c of parsed) {
          if (!CATEGORIES.includes(c as RecommendCategory)) {
            die(`unknown category: ${c}. Valid: ${CATEGORIES.join(', ')}`);
          }
        }
        categories = parsed as RecommendCategory[];
      }

      const hasStructured =
        opts.shape ||
        opts.scale ||
        opts.latencyMs != null ||
        opts.persistence ||
        opts.deployment ||
        opts.costCeiling != null;

      if (!hasStructured && !description) {
        die('provide a free-text description or at least one structured-form flag');
      }

      const structured: StructuredForm | undefined = hasStructured
        ? {
            project_shape: opts.shape as ProjectShape | undefined,
            scale: opts.scale as Scale | undefined,
            latency_budget_ms: opts.latencyMs,
            persistence: opts.persistence as Persistence | undefined,
            deployment: opts.deployment as Deployment | undefined,
            cost_ceiling_usd_per_mtok: opts.costCeiling
          }
        : undefined;

      const records = loadRecords();
      const result = recommendForProject(records, {
        description: structured ? undefined : description,
        structured,
        max_results: opts.k,
        categories
      });
      emit(formatRecommendation(result, globalOpts(cmd)));
    }
  );

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
