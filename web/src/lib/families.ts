// Product families — the top-level split of the catalog into separate
// sub-catalogs (Agent Memory, Memory Research & Benchmarks, Agent
// Frameworks & Harnesses, Retrieval & Data Infrastructure, Models,
// Serving & Ops). Source of truth: taxonomy/families.json, shared with
// the MCP server, CLI and validate gate. Families are presentation and
// query scaffolding only: records keep their section memberships.

import familiesRaw from '../../../taxonomy/families.json';
import type { LandscapeRecord } from './types';

export interface Family {
  id: string;
  name: string;
  tagline: string;
  audience: string;
  sections: string[];
}

const FAMILIES: Family[] = (familiesRaw as { families: Family[] }).families;
const SECTION_TO_FAMILY = new Map<string, Family>();
for (const f of FAMILIES) for (const s of f.sections) SECTION_TO_FAMILY.set(s, f);

export const UNASSIGNED_FAMILY_ID = 'other';

export function getFamilies(): Family[] {
  return FAMILIES;
}

export function getFamily(id: string): Family | undefined {
  return FAMILIES.find((f) => f.id === id);
}

export function familyForSection(section: string): Family | undefined {
  return SECTION_TO_FAMILY.get(section);
}

export function primarySectionOf(r: LandscapeRecord): string {
  const primary = r.sections.find((s) => s.primary);
  return primary?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

/** Family id for a record, by its primary section. */
export function familyIdOf(r: LandscapeRecord): string {
  return familyForSection(primarySectionOf(r))?.id ?? UNASSIGNED_FAMILY_ID;
}

export function familyNameOf(id: string): string {
  return getFamily(id)?.name ?? 'Other';
}

export function familyCounts(records: LandscapeRecord[]): Map<string, number> {
  const counts = new Map<string, number>(FAMILIES.map((f) => [f.id, 0]));
  for (const r of records) {
    const id = familyIdOf(r);
    counts.set(id, (counts.get(id) ?? 0) + 1);
  }
  return counts;
}
