// Shared prerender helpers for /alternatives pages: build chooser items for
// the whole catalog once per build, then answer "alternatives to X" from
// the same product family. Logic lives in mcp/src/chooser.ts.

import { getRecords } from '$lib/data';
import { familyForSection, getFamilies } from '$lib/families';
import { toItem, alternatives, type ChooserItem, type Alternative, type StackStatusLite } from '$lib/chooser';
import stackIndex from '../../../data/stack-index.json';

const status = (stackIndex as unknown as { records: Record<string, StackStatusLite> }).records;

let items: ChooserItem[] | null = null;
let byFamily: Map<string, ChooserItem[]> | null = null;

export function allItems(): ChooserItem[] {
  if (!items) {
    items = getRecords().map((r) => toItem(r as unknown as Parameters<typeof toItem>[0], status[r.id]));
    byFamily = new Map();
    for (const i of items) {
      const f = familyForSection(i.section)?.id ?? 'other';
      if (!byFamily.has(f)) byFamily.set(f, []);
      byFamily.get(f)!.push(i);
    }
  }
  return items;
}

export function familyIdOfItem(i: ChooserItem): string {
  return familyForSection(i.section)?.id ?? 'other';
}

export function alternativesTo(id: string, n = 8): { target: ChooserItem; alts: Alternative[] } | null {
  const target = allItems().find((i) => i.id === id);
  if (!target) return null;
  return { target, alts: alternatives(target, byFamily!.get(familyIdOfItem(target)) ?? [], n) };
}

/** Families that get alternatives pages (research papers and model
 * substrates don't have meaningful "alternatives"). */
export const ALT_FAMILIES = new Set(['memory', 'agents', 'data']);

/** Ids that get an /alternatives page: every record in ALT_FAMILIES (so
 * system pages can link by family alone) plus every flagged (severity >= 2)
 * record, so the stack checker's "more alternatives" link always resolves. */
export function alternativeIds(): string[] {
  return allItems()
    .filter((i) => ALT_FAMILIES.has(familyIdOfItem(i)) || i.status.severity >= 2)
    .map((i) => i.id);
}

export function familyName(id: string): string {
  return getFamilies().find((f) => f.id === id)?.name ?? 'Other';
}
