// Product families — the top-level split of the catalog into separate
// sub-catalogs (Agent Memory, Memory Research & Benchmarks, Agent
// Frameworks & Harnesses, Retrieval & Data Infrastructure, Models,
// Serving & Ops). Source of truth: taxonomy/families.json, shared with
// the MCP server, CLI and validate gate. Families are presentation and
// query scaffolding only: records keep their section memberships.

import familiesRaw from '../../../taxonomy/families.json';
import type { LandscapeRecord, Taxonomy } from './types';

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

export function primarySectionOf(r: Pick<LandscapeRecord, 'sections'>): string {
  const primary = r.sections.find((s) => s.primary);
  return primary?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

/** Family id for a record, by its primary section. */
export function familyIdOf(r: Pick<LandscapeRecord, 'sections'>): string {
  return familyForSection(primarySectionOf(r))?.id ?? UNASSIGNED_FAMILY_ID;
}

/**
 * The seven taxonomy axes (storage, retrieval, persistence, update, unit,
 * governance, conflict) describe how a system remembers. They are only
 * meaningful for the memory families; on a framework, model or vector
 * database they read as noise, so every surface shows them for these
 * families only (#330).
 */
export const MEMORY_TAXONOMY_FAMILIES: ReadonlySet<string> = new Set(['memory', 'memory-research']);

export function hasMemoryTaxonomy(r: Pick<LandscapeRecord, 'sections'>): boolean {
  return MEMORY_TAXONOMY_FAMILIES.has(familyIdOf(r));
}

const NO_TAXONOMY: Taxonomy = {
  storage: [],
  retrieval: [],
  persistence: [],
  update: [],
  unit: [],
  governance: [],
  conflict: []
};

/** The record's memory taxonomy, or empty axes when it isn't a memory system. */
export function memoryTaxonomyOf(r: Pick<LandscapeRecord, 'sections' | 'taxonomy'>): Taxonomy {
  return hasMemoryTaxonomy(r) ? r.taxonomy : NO_TAXONOMY;
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
