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
  RecordSummary,
  LandscapeRecord
} from '../../mcp/dist/tools.js';

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
