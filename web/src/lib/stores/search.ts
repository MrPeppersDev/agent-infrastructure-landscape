// Free-text search state. Empty by default; issue #10 fills in the actual
// search UI and the matcher logic. Issue #12 mirrors the value into the URL
// as `q=`.
//
// Contract for #10: read $searchQuery, render an input bound to it. The
// table filters via `applySearch(records, $searchQuery)` (below) — replace
// the no-op body with a real matcher (probably a case-insensitive substring
// scan across name + cells.{desc, claims, type}, or a small index).

import { writable } from 'svelte/store';
import type { LandscapeRecord } from '$lib/types';

export const searchQuery = writable<string>('');

/**
 * No-op for #9. #10 replaces this body with a real matcher.
 *
 * Why a free function rather than a derived store: search is parameterised
 * by *records* (which change as filters apply), not just by the query, so
 * a derived store would either re-key on the records identity (fine) or
 * close over a snapshot (bad). The free-function form composes cleanly with
 * `applyFilters(...)` in the same expression on +page.svelte.
 */
export function applySearch(
  records: LandscapeRecord[],
  query: string
): LandscapeRecord[] {
  if (!query.trim()) return records;
  // Placeholder: returns input unchanged. #10 fills this in.
  return records;
}
