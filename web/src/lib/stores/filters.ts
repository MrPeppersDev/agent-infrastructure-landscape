// Faceted filter state. Empty by default; issue #11 fills in the actual
// filter UI (left rail) and the predicate logic. Issue #12 mirrors the
// state into the URL.
//
// Contract for #11: pick a shape (sets of allowed values per facet) and
// keep this store the source of truth. The most likely shape is something
// like:
//
//   {
//     tier: Set<Tier>,
//     section: Set<string>,
//     status: Set<Status>,                  // "show only real-data", etc.
//     taxonomy: { storage: Set<string>, ... }
//   }
//
// For #9 we keep the type loose (`FilterState = Record<string, never>`) so
// the store is unambiguously "no filters applied" until #11 promotes it.

import { writable } from 'svelte/store';
import type { LandscapeRecord } from '$lib/types';

export interface FilterState {
  // Empty until #11 lands. Don't add fields opportunistically — every
  // consumer (URL sync in #12, tests, future facets) reads this shape.
}

export const filters = writable<FilterState>({});

/**
 * No-op for #9. #11 replaces this body with a real predicate fold.
 */
export function applyFilters(
  records: LandscapeRecord[],
  _state: FilterState
): LandscapeRecord[] {
  return records;
}
