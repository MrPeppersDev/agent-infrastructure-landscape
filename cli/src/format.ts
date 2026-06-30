// Output formatters for the landscape CLI.
//
// Three modes, selectable via global flags:
//   - text (default) : human-readable; colorised when stdout is a TTY
//   - --json         : JSON.stringify of the raw tools.ts result
//   - --csv          : header row + data rows; only meaningful for
//                      tabular results (search, sections, recent,
//                      eval-orphans, substrate-risk dependents)
//
// Each subcommand calls one of the format* helpers below with its
// already-computed query result and the parsed global flags.

import type {
  SearchResult,
  RelatedResult,
  CoverageResult,
  CompareResult,
  RecentResult,
  SubstrateResult,
  DecayCauseResult,
  RecordSummary,
  LandscapeRecord
} from '../../mcp/dist/tools.js';
import type { CitationFit } from '../../mcp/dist/citation-prediction.js';
import type { Candidate } from '../../mcp/dist/recommender.js';

export interface FormatOptions {
  json: boolean;
  csv: boolean;
  /** True if stdout is a TTY — enables colour. Defaults to detection. */
  color?: boolean;
}

// ===========================================================================
// ANSI colour helpers — zero-dep
// ===========================================================================
// We deliberately avoid chalk/picocolors to keep the dep surface minimal
// (one runtime dep: commander). If colour is disabled the wrappers
// just return the string unmodified.

function makeColors(enabled: boolean) {
  if (!enabled) {
    const id = (s: string) => s;
    return {
      bold: id,
      dim: id,
      cyan: id,
      green: id,
      yellow: id,
      red: id,
      magenta: id,
      blue: id
    };
  }
  const wrap = (code: number) => (s: string) => `\x1b[${code}m${s}\x1b[0m`;
  return {
    bold: wrap(1),
    dim: wrap(2),
    red: wrap(31),
    green: wrap(32),
    yellow: wrap(33),
    blue: wrap(34),
    magenta: wrap(35),
    cyan: wrap(36)
  };
}

export function resolveColor(opts: FormatOptions): boolean {
  if (opts.json || opts.csv) return false;
  if (typeof opts.color === 'boolean') return opts.color;
  // Respect NO_COLOR (https://no-color.org/) and FORCE_COLOR.
  if (process.env.NO_COLOR) return false;
  if (process.env.FORCE_COLOR) return true;
  return process.stdout.isTTY === true;
}

// ===========================================================================
// CSV helpers
// ===========================================================================

function csvEscape(value: unknown): string {
  if (value === null || value === undefined) return '';
  const s = String(value);
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function toCsv(headers: string[], rows: Array<Array<unknown>>): string {
  const lines = [headers.map(csvEscape).join(',')];
  for (const row of rows) lines.push(row.map(csvEscape).join(','));
  return lines.join('\n');
}

// ===========================================================================
// JSON helper
// ===========================================================================

function toJson<T>(value: T): string {
  return JSON.stringify(value, null, 2);
}

// ===========================================================================
// last_verified_at freshness helper — issue #54 / SCHEMA.md §3b
// ===========================================================================
// `tone` is shared with the Svelte UI's badge palette (see
// DetailModal.svelte / TableRow.svelte). Today is pinned in lockstep
// with scripts/validate.py's FRESHNESS_TODAY constant.

const FRESHNESS_TODAY = new Date('2026-05-14T00:00:00Z');

function freshnessLabel(iso: string | undefined): {
  tone: 'fresh' | 'aging' | 'stale';
  months: number | null;
} {
  if (!iso) return { tone: 'fresh', months: null };
  const d = new Date(iso + 'T00:00:00Z');
  if (Number.isNaN(d.getTime())) return { tone: 'fresh', months: null };
  const months =
    (FRESHNESS_TODAY.getTime() - d.getTime()) /
    (1000 * 60 * 60 * 24 * 30.4375);
  if (months >= 12) return { tone: 'stale', months };
  if (months >= 6) return { tone: 'aging', months };
  return { tone: 'fresh', months };
}

// ===========================================================================
// search_records
// ===========================================================================

export function formatSearch(result: SearchResult, opts: FormatOptions): string {
  if (opts.json) return toJson(result);
  if (opts.csv) {
    return toCsv(
      [
        'id',
        'name',
        'tier',
        'primarySection',
        'url',
        'last_verified_at',
        'description'
      ],
      result.results.map((r) => [
        r.id,
        r.name,
        r.tier,
        r.primarySection,
        r.url ?? '',
        r.lastVerifiedAt ?? '',
        r.description
      ])
    );
  }

  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(
    c.bold(`${result.totalMatches} match${result.totalMatches === 1 ? '' : 'es'}`) +
      c.dim(` for "${result.query}"`) +
      (result.results.length < result.totalMatches
        ? c.dim(` (showing first ${result.results.length})`)
        : '')
  );
  lines.push('');
  for (const r of result.results) {
    lines.push(
      `  ${c.cyan(r.name)} ${c.dim(`[T${r.tier}]`)} ${c.dim('—')} ${c.magenta(r.primarySection)}`
    );
    lines.push(`    ${c.dim('id:')} ${r.id}`);
    if (r.url) lines.push(`    ${c.dim('url:')} ${r.url}`);
    if (r.description) lines.push(`    ${r.description}`);
    lines.push('');
  }
  return lines.join('\n').trimEnd();
}

// ===========================================================================
// get_record — full record
// ===========================================================================

export function formatRecord(
  record: LandscapeRecord | null,
  id: string,
  opts: FormatOptions
): string {
  if (opts.json) return toJson(record);
  if (opts.csv) {
    if (!record) return `column,value\nerror,record not found: ${csvEscape(id)}`;
    const rows: Array<[string, unknown]> = [
      ['id', record.id],
      ['name', record.name],
      ['tier', record.tier],
      ['url', record.url ?? ''],
      ['last_verified_at', record.last_verified_at ?? ''],
      [
        'primarySection',
        record.sections.find((s) => s.primary)?.section ?? ''
      ]
    ];
    for (const [slug, cell] of Object.entries(record.cells)) {
      rows.push([slug, cell.value]);
    }
    return toCsv(['column', 'value'], rows);
  }

  const c = makeColors(resolveColor(opts));
  if (!record) {
    return c.red(`Record not found: ${id}`);
  }

  const lines: string[] = [];
  lines.push(c.bold(record.name) + c.dim(`  [T${record.tier}]`));
  lines.push(c.dim('id:    ') + record.id);
  if (record.url) lines.push(c.dim('url:   ') + record.url);

  const primarySec = record.sections.find((s) => s.primary);
  if (primarySec) {
    lines.push(
      c.dim('section: ') +
        c.magenta(primarySec.section) +
        (primarySec.subsection ? c.dim(' / ') + primarySec.subsection : '')
    );
  }

  // Last-verified caption — issue #54 / SCHEMA.md §3b. Shown
  // prominently after the section line so it lands above-the-fold and
  // colourised when the date is older than 6 months (yellow) or 12
  // months (red-ish).
  if (record.last_verified_at) {
    const lvaBadge = freshnessLabel(record.last_verified_at);
    let line = c.dim('verified: ') + record.last_verified_at;
    if (lvaBadge.tone === 'aging')
      line += '  ' + c.yellow('(needs re-audit)');
    else if (lvaBadge.tone === 'stale') line += '  ' + c.red('(stale)');
    lines.push(line);
  }

  // Highlight a curated set of high-signal cells; show the rest only on --json.
  const HIGHLIGHT_COLS = [
    'desc',
    'claims',
    'pricing',
    'mcp-support',
    'a2a-support',
    'pros',
    'cons',
    'created',
    'latest-release',
    'license',
    'gh',
    'links'
  ] as const;

  lines.push('');
  lines.push(c.bold('Key cells:'));
  for (const slug of HIGHLIGHT_COLS) {
    const cell = (record.cells as Record<string, { value: string; status: string; tier: string }>)[slug];
    if (!cell || cell.status !== 'real-data' || !cell.value.trim()) continue;
    lines.push(`  ${c.dim(slug + ':')} ${cell.value}`);
  }

  // Taxonomy summary. Cast through unknown — Taxonomy is a structural type
  // with named axes (storage/retrieval/...), but we want to iterate generically.
  const tax = record.taxonomy as unknown as Record<
    string,
    Array<{ value: string; primary: boolean }>
  >;
  const taxLines: string[] = [];
  for (const [k, vs] of Object.entries(tax)) {
    const primary = vs.find((v) => v.primary)?.value;
    const all = vs.map((v) => v.value).join(', ');
    if (primary || all) {
      taxLines.push(
        `  ${c.dim(k + ':')} ${c.cyan(primary ?? '—')}${all && all !== primary ? c.dim(` (all: ${all})`) : ''}`
      );
    }
  }
  if (taxLines.length > 0) {
    lines.push('');
    lines.push(c.bold('Taxonomy:'));
    lines.push(...taxLines);
  }

  const cellCount = Object.values(record.cells).filter(
    (c) => c.status === 'real-data' && c.value.trim() !== ''
  ).length;
  lines.push('');
  lines.push(
    c.dim(
      `${cellCount} filled cells of ${Object.keys(record.cells).length}. Use --json for the full record.`
    )
  );
  return lines.join('\n');
}

// ===========================================================================
// find_related
// ===========================================================================

export function formatRelated(result: RelatedResult, opts: FormatOptions): string {
  if (opts.json) return toJson(result);
  if (opts.csv) {
    return toCsv(
      ['direction', 'edge_type', 'related_id', 'related_name', 'tier', 'evidence'],
      result.edges.map((e) => [
        e.direction,
        e.edge.type,
        e.related.id,
        e.related.name,
        e.related.tier,
        e.edge.evidence
      ])
    );
  }

  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(
    c.bold(`${result.totalEdges} edge${result.totalEdges === 1 ? '' : 's'}`) +
      c.dim(` for ${result.name} (${result.id})`)
  );
  const types = Object.entries(result.edgeTypes)
    .sort((a, b) => b[1] - a[1])
    .map(([t, n]) => `${c.cyan(t)}=${n}`)
    .join(' ');
  if (types) lines.push(c.dim('by type: ') + types);
  lines.push('');
  for (const e of result.edges) {
    const arrow = e.direction === 'outgoing' ? '→' : '←';
    lines.push(
      `  ${c.dim(arrow)} ${c.cyan(e.edge.type.padEnd(20))} ${c.bold(e.related.name)} ${c.dim('[T' + e.related.tier + ']')}`
    );
    lines.push(`    ${c.dim('id:')} ${e.related.id}`);
    if (e.edge.evidence) lines.push(`    ${c.dim(e.edge.evidence)}`);
  }
  return lines.join('\n');
}

// ===========================================================================
// coverage_summary
// ===========================================================================

export function formatCoverage(result: CoverageResult, opts: FormatOptions): string {
  if (opts.json) return toJson(result);
  if (opts.csv) {
    return toCsv(
      ['feature', 'label', 'yes', 'no', 'unknown', 'supported_pct'],
      result.features.map((f) => [
        f.feature,
        f.label,
        f.yesCount,
        f.noCount,
        f.unknownCount,
        f.supportedPct
      ])
    );
  }

  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(c.bold(`Coverage: ${result.dimension}`));
  lines.push(
    c.dim(
      `${result.analyzedCount} analyzed of ${result.totalRecords} total records`
    )
  );
  lines.push('');
  const maxLabel = Math.max(...result.features.map((f) => f.label.length));
  for (const f of result.features) {
    const bar = '█'.repeat(Math.round(f.supportedPct / 5));
    lines.push(
      `  ${f.label.padEnd(maxLabel)}  ${c.green(f.yesCount.toString().padStart(4))} yes  ${c.dim(f.noCount.toString().padStart(4) + ' no')}  ${c.yellow(f.supportedPct.toFixed(1).padStart(5) + '%')} ${c.cyan(bar)}`
    );
  }
  return lines.join('\n');
}

// ===========================================================================
// compare
// ===========================================================================

export function formatCompare(result: CompareResult, opts: FormatOptions): string {
  if (opts.json) return toJson(result);
  if (opts.csv) {
    return toCsv(
      ['column', 'a_value', 'a_status', 'b_value', 'b_status', 'match'],
      result.cells.map((c) => [
        c.column,
        c.a?.value ?? '',
        c.a?.status ?? '',
        c.b?.value ?? '',
        c.b?.status ?? '',
        c.match
      ])
    );
  }

  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(
    c.bold('A: ') + result.a.name + c.dim(' [T' + result.a.tier + '] (' + result.a.id + ')')
  );
  lines.push(
    c.bold('B: ') + result.b.name + c.dim(' [T' + result.b.tier + '] (' + result.b.id + ')')
  );
  lines.push('');

  if (result.directEdges.length > 0) {
    lines.push(c.bold('Direct edges:'));
    for (const e of result.directEdges) {
      lines.push(`  ${c.cyan(e.type)}: ${e.source} → ${e.target}`);
      if (e.evidence) lines.push(`    ${c.dim(e.evidence)}`);
    }
    lines.push('');
  }

  const bothPresent = result.cells.filter((cell) => cell.a && cell.b);
  const matches = bothPresent.filter((cell) => cell.match).length;
  lines.push(
    c.dim(
      `${result.cells.length} cells compared; ${matches} of ${bothPresent.length} both-present match`
    )
  );
  lines.push('');

  for (const cell of result.cells) {
    const av = cell.a?.value ?? c.dim('(empty)');
    const bv = cell.b?.value ?? c.dim('(empty)');
    if (!cell.a && !cell.b) continue;
    const marker = cell.match ? c.green('=') : c.yellow('≠');
    lines.push(`  ${marker} ${c.bold(cell.column)}`);
    lines.push(`      A: ${truncate(av, 80)}`);
    lines.push(`      B: ${truncate(bv, 80)}`);
  }
  return lines.join('\n');
}

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + '…';
}

// ===========================================================================
// list_sections
// ===========================================================================

export function formatSections(sections: string[], opts: FormatOptions): string {
  if (opts.json) return toJson({ sections });
  if (opts.csv) {
    return toCsv(['section'], sections.map((s) => [s]));
  }
  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(c.bold(`${sections.length} sections:`));
  for (const s of sections) lines.push('  ' + c.magenta(s));
  return lines.join('\n');
}

// ===========================================================================
// recent_changes
// ===========================================================================

export function formatRecent(result: RecentResult, opts: FormatOptions): string {
  if (opts.json) return toJson(result);
  if (opts.csv) {
    return toCsv(
      [
        'id',
        'name',
        'latest_release',
        'created',
        'primary_section',
        'last_verified_at'
      ],
      result.records.map((r) => [
        r.id,
        r.name,
        r.latestRelease ?? '',
        r.created ?? '',
        r.primarySection,
        r.lastVerifiedAt ?? ''
      ])
    );
  }
  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(
    c.bold(`${result.totalMatches} record${result.totalMatches === 1 ? '' : 's'}`) +
      c.dim(result.since ? ` since ${result.since}` : ' (most recent)') +
      (result.records.length < result.totalMatches
        ? c.dim(` (showing first ${result.records.length})`)
        : '')
  );
  lines.push('');
  for (const r of result.records) {
    const date = r.latestRelease ?? r.created ?? '';
    lines.push(
      `  ${c.yellow(date.padEnd(10))}  ${c.bold(r.name)}  ${c.dim('— ' + r.primarySection)}`
    );
    lines.push(`    ${c.dim('id:')} ${r.id}`);
  }
  return lines.join('\n');
}

// ===========================================================================
// find_eval_orphans
// ===========================================================================

export function formatEvalOrphans(
  orphans: RecordSummary[],
  opts: FormatOptions
): string {
  if (opts.json) return toJson({ orphans });
  if (opts.csv) {
    return toCsv(
      ['id', 'name', 'tier', 'primary_section', 'url', 'description'],
      orphans.map((r) => [
        r.id,
        r.name,
        r.tier,
        r.primarySection,
        r.url ?? '',
        r.description
      ])
    );
  }
  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(
    c.bold(`${orphans.length} eval orphan${orphans.length === 1 ? '' : 's'}`) +
      c.dim(' (has observability, no evals, verified absence)')
  );
  lines.push('');
  for (const r of orphans) {
    lines.push(
      `  ${c.cyan(r.name)} ${c.dim('[T' + r.tier + ']')} ${c.dim('— ' + r.primarySection)}`
    );
    lines.push(`    ${c.dim('id:')} ${r.id}`);
  }
  return lines.join('\n');
}

// ===========================================================================
// find_substrate_risk
// ===========================================================================

export function formatSubstrate(result: SubstrateResult, opts: FormatOptions): string {
  if (opts.json) return toJson(result);
  if (opts.csv) {
    return toCsv(
      ['id', 'name', 'tier', 'primary_section', 'url'],
      result.dependents.map((r) => [
        r.id,
        r.name,
        r.tier,
        r.primarySection,
        r.url ?? ''
      ])
    );
  }
  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  if (!result.substrateRecord) {
    lines.push(c.red(`No substrate match for "${result.substrate}".`));
    return lines.join('\n');
  }
  lines.push(
    c.bold('Substrate: ') + result.substrateRecord.name + c.dim(' (' + result.substrateRecord.id + ')')
  );
  lines.push(
    c.bold('Dependents: ') +
      c.yellow(String(result.totalDependents)) +
      c.dim(' runtime-dependency edges')
  );
  lines.push('');
  for (const d of result.dependents) {
    lines.push(
      `  ${c.cyan(d.name)} ${c.dim('[T' + d.tier + ']')} ${c.dim('— ' + d.primarySection)}`
    );
    lines.push(`    ${c.dim('id:')} ${d.id}`);
  }
  return lines.join('\n');
}

// ===========================================================================
// find_by_decay_cause
// ===========================================================================

export function formatDecayCause(
  result: DecayCauseResult,
  opts: FormatOptions
): string {
  if (opts.json) return toJson(result);
  if (opts.csv) {
    return toCsv(
      ['id', 'name', 'tier', 'primary_section', 'decay_cause', 'decay_date', 'decay_evidence'],
      result.records.map((r) => [
        r.id,
        r.name,
        r.tier,
        r.primarySection,
        r.decay_cause,
        r.decay_date ?? '',
        r.decay_evidence ?? ''
      ])
    );
  }
  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(
    c.bold('Decay cause: ') + c.yellow(result.cause) +
      c.dim(' — ') + c.yellow(String(result.totalMatches)) + c.dim(' records')
  );
  if (result.totalMatches === 0) {
    lines.push('');
    lines.push(c.dim('No records match that cause.'));
    return lines.join('\n');
  }
  lines.push('');
  for (const r of result.records) {
    lines.push(`  ${c.cyan(r.name)} ${c.dim('[T' + r.tier + ']')} ${c.dim('— ' + r.primarySection)}`);
    if (r.decay_date) lines.push(`    ${c.dim('decay-date:')} ${r.decay_date}`);
    if (r.decay_evidence) lines.push(`    ${c.dim('evidence:')} ${r.decay_evidence}`);
    lines.push(`    ${c.dim('id:')} ${r.id}`);
  }
  return lines.join('\n');
}

// ===========================================================================
// predict — single-paper WSB fit
// ===========================================================================

function fmtN(n: number): string {
  if (!isFinite(n)) return '—';
  if (n >= 10000) return `${(n / 1000).toFixed(0)}k`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return Math.round(n).toLocaleString();
}

export function formatPredict(
  fit: CitationFit | null,
  id: string,
  opts: FormatOptions
): string {
  if (opts.json) return toJson(fit);
  if (opts.csv) {
    if (!fit) return `field,value\nerror,no fit for ${csvEscape(id)}`;
    return toCsv(
      ['field', 'value'],
      [
        ['recordId', fit.recordId],
        ['recordName', fit.recordName],
        ['section', fit.section],
        ['tier', fit.tier],
        ['publishedYear', fit.publishedYear],
        ['yearsObserved', fit.yearsObserved],
        ['observedCitations', fit.observedCitations],
        ['observedInfluential', fit.observedInfluential],
        ['lambda', fit.lambda],
        ['mu', fit.mu],
        ['sigma', fit.sigma],
        ['asymptote', fit.asymptote],
        ['asymptoteCI_low', fit.asymptoteCI[0]],
        ['asymptoteCI_high', fit.asymptoteCI[1]],
        ['predictedAt10y', fit.predictedAt10y],
        ['fitR2', fit.fitR2],
        ['phase', fit.phase],
        ['breakoutProbability', fit.breakoutProbability],
        ['sourceKind', fit.sourceKind],
        ['source', fit.source]
      ]
    );
  }

  const c = makeColors(resolveColor(opts));
  if (!fit) {
    return c.red(`No fit for "${id}". Run \`landscape show ${id}\` to inspect.`);
  }

  const lines: string[] = [];
  lines.push(
    c.bold(fit.recordName) +
      c.dim(`  [T${fit.tier}] · ${fit.section}`)
  );
  lines.push(c.dim('id:           ') + fit.recordId);
  lines.push(c.dim('phase:        ') + c.yellow(fit.phase));
  lines.push(c.dim('source:       ') + fit.source);
  lines.push('');
  lines.push(c.bold('Observed'));
  lines.push(c.dim('  published:  ') + (fit.publishedYear || '—'));
  lines.push(
    c.dim('  observed:   ') +
      fmtN(fit.observedCitations) +
      c.dim(` cites · ${fit.yearsObserved.toFixed(1)}yr · ${fmtN(fit.observedInfluential)} influential`)
  );
  lines.push('');
  lines.push(c.bold('Wang-Song-Barabási fit'));
  lines.push(c.dim('  λ (immediacy):  ') + fmtR(fit.lambda));
  lines.push(c.dim('  μ (peak log-t): ') + fmtR(fit.mu));
  lines.push(c.dim('  σ (longevity):  ') + fmtR(fit.sigma));
  lines.push(c.dim('  R²:             ') + fmtR(fit.fitR2));
  lines.push('');
  lines.push(c.bold('Predictions'));
  lines.push(
    c.dim('  asymptote:    ') +
      c.green(fmtN(fit.asymptote)) +
      c.dim(' cites (long-run ceiling)')
  );
  lines.push(
    c.dim('  90% CI:       ') +
      fmtN(fit.asymptoteCI[0]) +
      c.dim(' – ') +
      fmtN(fit.asymptoteCI[1])
  );
  lines.push(
    c.dim('  10y count:    ') +
      fmtN(fit.predictedAt10y) +
      c.dim(' cites at t=10yr from publication')
  );
  lines.push(
    c.dim('  breakout P:   ') +
      `${Math.round(fit.breakoutProbability * 100)}%` +
      c.dim(' (asymptote > 3× catalog median)')
  );
  return lines.join('\n');
}

function fmtR(n: number): string {
  if (!isFinite(n)) return '—';
  if (Math.abs(n) >= 1) return n.toFixed(2);
  return n.toFixed(3);
}

// ===========================================================================
// breakouts — top-N predicted breakouts
// ===========================================================================

export function formatBreakouts(
  top: CitationFit[],
  limit: number,
  opts: FormatOptions
): string {
  if (opts.json) {
    return toJson({ limit, totalMatches: top.length, breakouts: top });
  }
  if (opts.csv) {
    return toCsv(
      [
        'rank',
        'name',
        'section',
        'tier',
        'publishedYear',
        'observedCitations',
        'asymptote',
        'asymptoteCI_low',
        'asymptoteCI_high',
        'predictedAt10y',
        'lambda',
        'mu',
        'sigma',
        'fitR2',
        'breakoutProbability',
        'recordId'
      ],
      top.map((f, i) => [
        i + 1,
        f.recordName,
        f.section,
        f.tier,
        f.publishedYear,
        f.observedCitations,
        f.asymptote,
        f.asymptoteCI[0],
        f.asymptoteCI[1],
        f.predictedAt10y,
        f.lambda,
        f.mu,
        f.sigma,
        f.fitR2,
        f.breakoutProbability,
        f.recordId
      ])
    );
  }

  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(
    c.bold(`Top ${top.length} predicted citation breakouts`) +
      c.dim(' (Wang-Song-Barabási, growth-phase, trajectory-fit only)')
  );
  if (top.length === 0) {
    lines.push('');
    lines.push(c.dim('No breakout candidates clear the bar.'));
    return lines.join('\n');
  }
  lines.push('');
  // Header line
  lines.push(
    c.dim(
      '  rank  obs    c_inf    run-up  R²    paper'
    )
  );
  for (let i = 0; i < top.length; i++) {
    const f = top[i];
    const rank = String(i + 1).padStart(4);
    const obs = fmtN(f.observedCitations).padStart(5);
    const asymp = fmtN(f.asymptote).padStart(7);
    const ratio =
      f.observedCitations > 0
        ? `${(f.asymptote / f.observedCitations).toFixed(1)}×`.padStart(7)
        : '—'.padStart(7);
    const r2 = fmtR(f.fitR2).padStart(5);
    lines.push(
      `  ${rank}  ${obs}  ${asymp}  ${ratio}  ${r2}  ${c.cyan(f.recordName)} ${c.dim('[T' + f.tier + ']')}`
    );
  }
  lines.push('');
  lines.push(
    c.dim(
      `Methodology: Wang, Song & Barabási, Science 342:127 (2013). ` +
        `Use \`landscape predict <id>\` for full per-paper detail.`
    )
  );
  return lines.join('\n');
}

// ===========================================================================
// recommend between — Phase 2 / Gate 3 (issue #97)
// ===========================================================================

export function formatBetween(
  candidates: Candidate[],
  anchors: { low: string; high: string },
  opts: FormatOptions
): string {
  if (opts.json) return toJson(candidates);
  if (opts.csv) {
    return toCsv(
      ['rank', 'id', 'name', 'tier', 'score', 'rationale', 'caveats'],
      candidates.map((cand, i) => [
        i + 1,
        cand.record.id,
        cand.record.name,
        cand.record.tier,
        cand.score.toFixed(4),
        cand.rationale.join(' | '),
        cand.caveats.join(' | ')
      ])
    );
  }

  const c = makeColors(resolveColor(opts));
  const lines: string[] = [];
  lines.push(
    c.bold(`Candidates between ${anchors.low} and ${anchors.high}`) +
      c.dim(` (${candidates.length} returned)`)
  );
  if (candidates.length === 0) {
    lines.push('');
    lines.push(
      c.dim(
        'No candidates in the positioning band. Verify the anchor ids and ' +
          'that they carry cost/capability cells (cost-input-usd-per-mtok ' +
          'and/or capability-composite-score).'
      )
    );
    return lines.join('\n');
  }
  lines.push('');
  for (let i = 0; i < candidates.length; i++) {
    const cand = candidates[i]!;
    lines.push(
      c.bold(`${i + 1}. ${cand.record.name}`) +
        c.dim(`  [T${cand.record.tier}] · score ${cand.score.toFixed(3)}`)
    );
    lines.push(c.dim('   id: ') + cand.record.id);
    if (cand.rationale.length > 0) {
      for (const r of cand.rationale) {
        lines.push(c.green('   ✓ ') + r);
      }
    }
    if (cand.caveats.length > 0) {
      for (const cv of cand.caveats) {
        // Mark LLM-unverified caveats inline so MCP-vs-CLI text output
        // surfaces the same provenance gate (§3.4).
        const tag = /LLM-unverified/i.test(cv) ? c.yellow('[LLM-unverified] ') : '';
        lines.push(c.yellow('   ! ') + tag + cv);
      }
    }
    if (i < candidates.length - 1) lines.push('');
  }
  return lines.join('\n');
}
