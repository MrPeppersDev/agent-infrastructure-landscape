// Catalog silos (taxonomy/silos.json): focused views over the one dataset,
// each for an audience and a job. A silo is a set of sections (which may
// cross product families), the columns that audience scans first, and the
// decision tools, research views and exports that apply to it. Nothing is
// removed: the Atlas (the home table) shows every row and every column; a
// silo shows its rows and its columns. Client-safe: no data imports.

import silosRaw from '../../../taxonomy/silos.json';
import { COLUMN_BY_KEY, type ColumnDef } from './columns';
import { primarySectionOf } from './families';
import type { LandscapeRecord } from './types';

export interface SiloLink {
  label: string;
  path: string;
  blurb?: string;
}

export interface Silo {
  id: string;
  /** Product family (taxonomy/families.json) when the silo is exactly one family. */
  family?: string;
  name: string;
  short: string;
  tagline: string;
  audience: string;
  description: string;
  sections: string[];
  /** Whether the seven memory-taxonomy axes apply to this silo's rows. */
  taxonomy: boolean;
  /** Column keys ($lib/columns) for the silo's default table. */
  columns: string[];
  decide: SiloLink[];
  research: SiloLink[];
  bestOf: string[];
  mcpTools: string[];
  cli: string[];
}

const SILOS: Silo[] = (silosRaw as { silos: Silo[] }).silos;

// Fail the build, not the reader, on a column key that no longer exists.
for (const s of SILOS) {
  for (const k of s.columns) {
    if (!COLUMN_BY_KEY[k]) throw new Error(`taxonomy/silos.json: silo "${s.id}" names unknown column "${k}"`);
  }
}

export function getSilos(): Silo[] {
  return SILOS;
}

export function getSilo(id: string): Silo | undefined {
  return SILOS.find((s) => s.id === id);
}

/** The silo that is exactly this product family, if any. */
export function siloForFamily(familyId: string): Silo | undefined {
  return SILOS.find((s) => s.family === familyId);
}

export function inSilo(r: Pick<LandscapeRecord, 'sections'>, silo: Silo): boolean {
  return silo.sections.includes(primarySectionOf(r));
}

export function recordsInSilo<T extends Pick<LandscapeRecord, 'sections'>>(records: T[], silo: Silo): T[] {
  const set = new Set(silo.sections);
  return records.filter((r) => set.has(primarySectionOf(r)));
}

/** Every silo a record belongs to, in file order. */
export function silosOf(r: Pick<LandscapeRecord, 'sections'>): Silo[] {
  const section = primarySectionOf(r);
  return SILOS.filter((s) => s.sections.includes(section));
}

const COMPACT_WIDTH: Record<string, number> = {
  name: 220, lifecycle: 110, tier: 60, section: 210, type: 260, verified: 100
};

/** The silo's default table columns, with compact widths. */
export function siloColumns(silo: Silo): ColumnDef[] {
  return silo.columns.map((k) => {
    const c = COLUMN_BY_KEY[k];
    return { ...c, width: COMPACT_WIDTH[k] ?? Math.min(c.width ?? 160, 200) };
  });
}

/** Id of the flattened JSON / CSV export for a silo (web/scripts/generate-exports.mjs). */
export function siloExportId(silo: Silo): string {
  return silo.family ?? silo.id;
}

export function siloCounts(records: Pick<LandscapeRecord, 'sections'>[]): Map<string, number> {
  const counts = new Map<string, number>(SILOS.map((s) => [s.id, 0]));
  for (const r of records) for (const s of silosOf(r)) counts.set(s.id, (counts.get(s.id) ?? 0) + 1);
  return counts;
}
