// Procurement / security-review sheet (#366): for every pick in a stack
// plan, the buyer cells a reviewer asks for, each with its source. Blank
// cells read "not published" and link the vendor's trust page when the
// catalog has one; nothing is guessed. Pure and dependency-free so the
// builder page, the blueprints, `plan_stack` and the CLI share it.

import type { StackPlan } from './composer.js';
import type { RecordLike } from './chooser.js';

export interface SheetColumn {
  slug: string;
  label: string;
  /** Enum cells print their codes with spaces after commas. */
  enumList?: boolean;
}

/** Column order on the sheet. Slugs are cells in docs/SCHEMA.md §2.5. */
export const SHEET_COLUMNS: SheetColumn[] = [
  { slug: 'compliance-certifications', label: 'Attestations', enumList: true },
  { slug: 'compliance', label: 'Compliance (as stated)' },
  { slug: 'data-handling', label: 'Data handling' },
  { slug: 'encryption', label: 'Encryption' },
  { slug: 'sso-rbac', label: 'SSO / RBAC' },
  { slug: 'deployment', label: 'Deployment' },
  { slug: 'architecture-deployment-locus', label: 'Deployment locus', enumList: true },
  { slug: 'license', label: 'Licence' },
  { slug: 'licensing-bucket', label: 'Licensing model', enumList: true },
  { slug: 'sdk-languages', label: 'SDK languages', enumList: true },
  { slug: 'protocol-support', label: 'Protocols', enumList: true },
  { slug: 'maturity', label: 'Maturity', enumList: true },
  { slug: 'hq', label: 'HQ' },
  { slug: 'pricing', label: 'Pricing' }
];

export interface SheetCell {
  value: string | null;
  citation: string | null;
}

export interface SheetRow {
  layer: string;
  label: string;
  id: string;
  name: string;
  url: string | null;
  page: string;
  lifecycle: string;
  lifecycleNote: string;
  /** Record-level verification date, when the record carries one. */
  verifiedAt: string | null;
  /** Vendor security / trust page: the citation of the compliance cells. */
  trustPage: string | null;
  cells: Record<string, SheetCell>;
}

export interface ProcurementSheet {
  product: string;
  generatedAt: string;
  site: string;
  columns: SheetColumn[];
  rows: SheetRow[];
  note: string;
}

const EMPTY = new Set(['not-applicable', 'no-data', 'depth-floor-reached']);

function cellOf(r: RecordLike | undefined, slug: string, enumList = false): SheetCell {
  const c = (r?.cells as Record<string, { value?: string; status?: string; citation?: string | null } | undefined> | undefined)?.[slug];
  if (!c || EMPTY.has(c.status ?? '') || !c.value) return { value: null, citation: null };
  let v = String(c.value).replace(/<[^>]+>/g, '').trim();
  if (enumList) v = v.replace(/,(?=\S)/g, ', ');
  return { value: v || null, citation: c.citation ?? null };
}

export function procurementSheet(plan: StackPlan, records: RecordLike[], site: string, today: string = new Date().toISOString().slice(0, 10)): ProcurementSheet {
  const byId = new Map(records.map((r) => [r.id, r]));
  const rows: SheetRow[] = [];
  for (const l of plan.layers) {
    if (!l.pick) continue;
    const item = l.pick.item;
    const r = byId.get(item.id);
    const cells: Record<string, SheetCell> = {};
    for (const col of SHEET_COLUMNS) cells[col.slug] = cellOf(r, col.slug, col.enumList);
    const trust = cells['compliance-certifications'].citation ?? cells.compliance.citation ?? cells.encryption.citation ?? null;
    rows.push({
      layer: l.layer,
      label: l.label,
      id: item.id,
      name: item.name,
      url: item.url,
      page: `${site}/systems/${item.id}`,
      lifecycle: item.status.status,
      lifecycleNote: item.status.note ?? '',
      verifiedAt: (r as { last_verified_at?: string } | undefined)?.last_verified_at ?? null,
      trustPage: trust,
      cells
    });
  }
  return {
    product: plan.product,
    generatedAt: today,
    site,
    columns: SHEET_COLUMNS,
    rows,
    note: 'Every value is a catalogued fact with the page it was read from; "not published" means the catalog found no public statement, and links the vendor\'s trust page where one is known. Check the source before relying on it: attestations lapse and pages change.'
  };
}

const NOT_PUBLISHED = 'not published';

function show(c: SheetCell, trust: string | null, md: boolean): string {
  if (c.value) return md && c.citation ? `${c.value} ([source](${c.citation}))` : c.value;
  if (md && trust) return `${NOT_PUBLISHED} ([trust page](${trust}))`;
  return NOT_PUBLISHED;
}

const csvCell = (v: string) => (/[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);

/** One row per pick; each buyer column is followed by its source column. */
export function sheetToCsv(sheet: ProcurementSheet): string {
  const head = ['layer', 'system', 'id', 'catalog_page', 'vendor_url', 'lifecycle', 'verified_at', 'trust_page'];
  for (const c of sheet.columns) head.push(c.slug, `${c.slug}_source`);
  const lines = [head.join(',')];
  for (const r of sheet.rows) {
    const vals = [r.label, r.name, r.id, r.page, r.url ?? '', r.lifecycle + (r.lifecycleNote ? ` (${r.lifecycleNote})` : ''), r.verifiedAt ?? '', r.trustPage ?? ''];
    for (const c of sheet.columns) {
      const cell = r.cells[c.slug];
      vals.push(cell.value ?? NOT_PUBLISHED, cell.citation ?? (cell.value ? '' : r.trustPage ?? ''));
    }
    lines.push(vals.map(csvCell).join(','));
  }
  return lines.join('\n') + '\n';
}

/** A Markdown document: one section per pick with a two-column table, so
 * it pastes into a review ticket. */
export function sheetToMarkdown(sheet: ProcurementSheet): string {
  const L: string[] = [
    `# Security review sheet — ${sheet.product}`,
    '',
    `Generated ${sheet.generatedAt} from the [AI Agent Infrastructure Landscape](${sheet.site}). ${sheet.note}`,
    ''
  ];
  for (const r of sheet.rows) {
    L.push(`## ${r.label}: [${r.name}](${r.page})`, '');
    const meta = [`Lifecycle: ${r.lifecycle}${r.lifecycleNote ? ` (${r.lifecycleNote})` : ''}`];
    if (r.verifiedAt) meta.push(`catalog record verified ${r.verifiedAt}`);
    if (r.url) meta.push(`vendor: ${r.url}`);
    L.push(meta.join(' · '), '', '| Item | Value |', '|---|---|');
    for (const c of sheet.columns) L.push(`| ${c.label} | ${show(r.cells[c.slug], r.trustPage, true).replace(/\|/g, '\\|')} |`);
    L.push('');
  }
  return L.join('\n');
}
