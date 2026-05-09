// Multi-column sort state, kept in a Svelte writable store.
//
// Contract: the store holds an ordered array of {column, direction} entries.
// The first entry is the primary sort key; subsequent entries break ties.
// Click on a header → toggle/append per the rules in `cycleSort` below.
//
// Issue #12 (URL state) will mirror this store into the URL as a `sort=`
// query param. The store is the source of truth; the URL sync layer reads
// from and writes to it. Keeping the URL coupling out of this file keeps
// #9's wiring decoupled from #12's plumbing.

import { writable } from 'svelte/store';
import type { ColumnSlug } from '$lib/types';

/**
 * Sort key vocabulary. `name` and `tier` are virtual columns that don't
 * live in `record.cells`; everything else is one of the 60 column slugs.
 */
export type SortColumn = 'name' | 'tier' | ColumnSlug;
export type SortDirection = 'asc' | 'desc';

export interface SortEntry {
  column: SortColumn;
  direction: SortDirection;
}

export const sortColumns = writable<SortEntry[]>([]);

/**
 * Apply a header click. The interaction:
 *
 * - plain click on column not yet sorted → set as the only sort, asc
 * - plain click on the primary sort      → flip its direction
 * - plain click on a secondary sort      → promote to primary, asc
 * - shift-click on column not yet sorted → append as next sort, asc
 * - shift-click on already-sorted column → flip that column's direction
 *                                          (preserve its position)
 *
 * Returns the new array (so callers can `sortColumns.set(cycleSort(...))`).
 */
export function cycleSort(
  current: SortEntry[],
  column: SortColumn,
  shiftKey: boolean
): SortEntry[] {
  const idx = current.findIndex((e) => e.column === column);

  if (shiftKey) {
    if (idx === -1) {
      return [...current, { column, direction: 'asc' }];
    }
    return current.map((e, i) =>
      i === idx ? { ...e, direction: e.direction === 'asc' ? 'desc' : 'asc' } : e
    );
  }

  if (idx === 0) {
    return [
      { column, direction: current[0].direction === 'asc' ? 'desc' : 'asc' },
      ...current.slice(1)
    ];
  }
  return [{ column, direction: 'asc' }];
}
