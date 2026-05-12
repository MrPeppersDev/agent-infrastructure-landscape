// Pure CSV/JSON serializers for the landscape records. The +page.svelte
// toolbar wires the "Export ▾" menu to these via a small Blob download
// helper. Both functions are pure (input → string) so they can be tested
// without DOM and re-used by a future Node-side script if we ever want
// server-rendered exports.
//
// Issue #19. See DECISIONS.md for the flattening strategy rationale.

import type { LandscapeRecord, Taxonomy, TaxonomyValue } from './types';

// --- Helpers ----------------------------------------------------------

const HTML_TAG_RE = /<[^>]+>/g;
const WHITESPACE_RE = /\s+/g;

/** Strip HTML tags and collapse whitespace. Used so a CSV cell never
 *  contains markup like `<a href="...">label</a>` — that would be useless
 *  in Excel / pandas / etc. */
function stripHtml(s: string): string {
  return s.replace(HTML_TAG_RE, '').replace(WHITESPACE_RE, ' ').trim();
}

/** Format a taxonomy axis as a flat string for CSV.
 *
 *  Format: `primary; secondary1; secondary2` — primary first, all
 *  lowercased canonical values. The `(primary)` annotation is appended
 *  in parentheses to the leading value so downstream analysis can still
 *  tell which one was canonical without parsing positional ordering.
 */
function formatTaxonomy(values: TaxonomyValue[]): string {
  if (!values || values.length === 0) return '';
  // Primary first, then everything else in stable order.
  const sorted = [...values].sort((a, b) => {
    if (a.primary && !b.primary) return -1;
    if (!a.primary && b.primary) return 1;
    return a.value.localeCompare(b.value);
  });
  return sorted
    .map((v, i) => (i === 0 && v.primary ? `${v.value} (primary)` : v.value))
    .join('; ');
}

/** Format the sections array as `primary section | secondary, tertiary`. */
function formatSections(sections: LandscapeRecord['sections']): string {
  if (!sections || sections.length === 0) return '';
  const sorted = [...sections].sort((a, b) => {
    if (a.primary && !b.primary) return -1;
    if (!a.primary && b.primary) return 1;
    return a.section.localeCompare(b.section);
  });
  return sorted
    .map((s) => {
      const label = s.subsection ? `${s.section} — ${s.subsection}` : s.section;
      return s.primary ? `${label} (primary)` : label;
    })
    .join('; ');
}

const TAXONOMY_AXES: (keyof Taxonomy)[] = [
  'storage',
  'retrieval',
  'persistence',
  'update',
  'unit',
  'governance',
  'conflict'
];

/** RFC 4180 field-escape: wrap in `"`, double internal quotes, when the
 *  field contains `,` / `"` / `\n` / `\r`. */
function csvEscape(s: string): string {
  if (s === '' ) return '';
  if (/[",\n\r]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

// --- Public API -------------------------------------------------------

/** Order of cell-slug columns in CSV output. Mirrors the order in
 *  columns.ts but kept here so this module has zero dependency on the
 *  UI's column metadata (the consumer of a JSON column-spec slice can
 *  drop in a different ordering if they want). */
const CELL_COLUMNS = [
  'type',
  'desc',
  'claims',
  'modalities',
  'created',
  'latest-release',
  'license',
  'gh',
  'mindshare',
  'citations',
  'funding',
  'customers',
  'pricing',
  'compliance',
  'data-handling',
  'deployment',
  'hq',
  'founders',
  'volume',
  'perf',
  'repro',
  'code-release',
  'api-surface',
  'latency',
  'throughput',
  'backend-storage',
  'multi-tenancy',
  'encryption',
  'sso-rbac',
  'embedding-model',
  'consistency',
  'versioning',
  'tombstoning',
  'schema-evolution',
  'namespace',
  'contradiction',
  'forgetting',
  'mcp-support',
  'a2a-support',
  'otel',
  'webhooks',
  'import-export',
  'integration-count',
  'orchestration',
  'programmatic-control',
  'vendor-benchmarks',
  'pricing-specifics',
  'agent-abstraction',
  'memory-primitives',
  'llm-lock',
  'runtimes',
  'session-handling',
  'validated-verticals',
  'time-to-running',
  'anti-fit',
  'optimised-for',
  'adjacent-infrastructure',
  'pros',
  'cons',
  'links'
] as const;

/** Column keys understood by the export functions. We accept the column
 *  identifiers used by the table's column-picker UI:
 *    'id', 'name', 'tier', 'url', 'primary_section', 'sections'  → identity
 *    'tax:<axis>'                                                → taxonomy
 *    <cell-slug>                                                 → cell
 *  Anything not in those buckets is silently skipped.
 */
export type ExportColumnKey = string;

const IDENTITY_KEYS = new Set([
  'id',
  'name',
  'tier',
  'url',
  'primary_section',
  'sections'
]);

const TAXONOMY_KEY_PREFIX = 'tax:';

/** Convert the records to a CSV string. Headers: identity columns +
 *  taxonomy axes + cell slugs. Citation URLs are appended in parentheses
 *  to cell values when present (so a CSV consumer keeps the source).
 *  Status types other than `real-data` are normalised to readable text.
 *
 *  `columns` (optional): if provided, only these column keys are emitted.
 *  Keys are evaluated in the order supplied. If omitted, the full default
 *  set ships (identity + all taxonomy axes + all 60 cell slugs).
 */
export function toCSV(
  records: LandscapeRecord[],
  columns?: ExportColumnKey[]
): string {
  const cols: ExportColumnKey[] =
    columns && columns.length > 0
      ? columns
      : [
          'id',
          'name',
          'tier',
          'url',
          'primary_section',
          'sections',
          ...TAXONOMY_AXES.map((a) => `${TAXONOMY_KEY_PREFIX}${a}`),
          ...CELL_COLUMNS
        ];

  const headers = cols.map((k) => {
    if (k === 'primary_section') return 'primary_section';
    if (k.startsWith(TAXONOMY_KEY_PREFIX)) return `tax_${k.slice(TAXONOMY_KEY_PREFIX.length)}`;
    return k;
  });

  const lines: string[] = [headers.map(csvEscape).join(',')];

  for (const r of records) {
    const primary = r.sections.find((s) => s.primary)?.section ?? r.sections[0]?.section ?? '';
    const row: string[] = [];
    for (const key of cols) {
      if (IDENTITY_KEYS.has(key)) {
        switch (key) {
          case 'id': row.push(r.id); break;
          case 'name': row.push(r.name); break;
          case 'tier': row.push(String(r.tier)); break;
          case 'url': row.push(r.url ?? ''); break;
          case 'primary_section': row.push(primary); break;
          case 'sections': row.push(formatSections(r.sections)); break;
        }
        continue;
      }
      if (key.startsWith(TAXONOMY_KEY_PREFIX)) {
        const axis = key.slice(TAXONOMY_KEY_PREFIX.length) as keyof Taxonomy;
        row.push(formatTaxonomy(r.taxonomy[axis] ?? []));
        continue;
      }
      // Cell slug.
      const cell = r.cells[key as keyof typeof r.cells];
      if (!cell) {
        row.push('');
        continue;
      }
      if (cell.status === 'not-applicable') {
        row.push('not applicable');
        continue;
      }
      if (cell.status === 'no-data') {
        row.push('');
        continue;
      }
      const value = stripHtml(cell.value ?? '');
      if (cell.status === 'depth-floor-reached') {
        row.push(value ? `${value} (searched, not found)` : 'searched, not found');
        continue;
      }
      // real-data: append citation URL in parens so the source survives.
      row.push(cell.citation ? `${value} [${cell.citation}]` : value);
    }
    lines.push(row.map(csvEscape).join(','));
  }

  // CRLF per RFC 4180 — Excel on Windows is the historically-tetchy consumer.
  return lines.join('\r\n');
}

/** Convert the records to JSON. Preserves the full structured shape —
 *  cells keep their {value, citation, status} triple, taxonomy stays
 *  array-of-objects, etc. Easier for programmatic consumers than CSV.
 *
 *  `columns` (optional): if provided, the JSON is pruned per record so
 *  that `cells` only contains the requested cell slugs, `taxonomy` only
 *  contains the requested axes, and identity fields are emitted only when
 *  selected. If omitted, the full structured shape ships unchanged.
 */
export function toJSON(
  records: LandscapeRecord[],
  columns?: ExportColumnKey[]
): string {
  if (!columns || columns.length === 0) {
    return JSON.stringify(records, null, 2);
  }
  const wantIdentity = (k: string) => columns.includes(k);
  const wantedAxes = TAXONOMY_AXES.filter((a) =>
    columns.includes(`${TAXONOMY_KEY_PREFIX}${a}`)
  );
  const wantedCells = columns.filter(
    (k) => !IDENTITY_KEYS.has(k) && !k.startsWith(TAXONOMY_KEY_PREFIX)
  );
  const pruned = records.map((r) => {
    const out: Record<string, unknown> = {};
    if (wantIdentity('id')) out.id = r.id;
    if (wantIdentity('name')) out.name = r.name;
    if (wantIdentity('tier')) out.tier = r.tier;
    if (wantIdentity('url')) out.url = r.url ?? null;
    if (wantIdentity('sections') || wantIdentity('primary_section')) {
      out.sections = r.sections;
    }
    if (wantedAxes.length > 0) {
      const tax: Partial<Taxonomy> = {};
      for (const a of wantedAxes) tax[a] = r.taxonomy[a] ?? [];
      out.taxonomy = tax;
    }
    if (wantedCells.length > 0) {
      const cells: Record<string, unknown> = {};
      for (const slug of wantedCells) {
        const c = r.cells[slug as keyof typeof r.cells];
        if (c !== undefined) cells[slug] = c;
      }
      out.cells = cells;
    }
    return out;
  });
  return JSON.stringify(pruned, null, 2);
}

/** Build a filename like
 *  `memory-landscape_2026-05-12_tier=1,license=Apache-2.0.csv`.
 *
 *  `filterSummary` is a brief "tier=1,license=Apache-2.0" string built
 *  by the caller from the current filter state. We keep its construction
 *  outside this module so this file stays free of store imports.
 */
export function buildFilename(
  extension: 'csv' | 'json',
  filterSummary: string,
  now: Date = new Date()
): string {
  const date = now.toISOString().slice(0, 10); // YYYY-MM-DD
  // Filesystem-safe: strip anything that isn't word-char, =, comma, dot, dash.
  const safeSummary = filterSummary.replace(/[^\w=,.\-]/g, '_');
  const tail = safeSummary ? `_${safeSummary}` : '';
  return `memory-landscape_${date}${tail}.${extension}`;
}

/** Trigger a browser download for `content` with the given filename and
 *  mime type. Pure DOM glue; isolated here so the toolbar component
 *  doesn't have to know the Blob/anchor dance. */
export function downloadFile(filename: string, content: string, mime: string): void {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
