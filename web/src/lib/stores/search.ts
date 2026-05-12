// Free-text search state. Issue #10 wires this up to a real matcher and
// SearchBox component. Issue #12 mirrors the value into the URL as `q=`.
//
// Contract: read $searchQuery, render an input bound to it. The table
// filters via `applySearch(records, $searchQuery)` in +page.svelte's
// reactive chain (search → filters → sort).

import { writable, derived, type Readable } from 'svelte/store';
import type { LandscapeRecord } from '$lib/types';

export const searchQuery = writable<string>('');

const HTML_TAG = /<[^>]+>/g;

function stripHtml(s: string): string {
  return s.replace(HTML_TAG, '');
}

/**
 * Case-insensitive substring match across name + cells.desc + cells.claims.
 * HTML tags are stripped from desc/claims before matching so that markup
 * like `<a href="...">` doesn't pollute the haystack.
 *
 * Why a free function rather than a derived store: search is parameterised
 * by *records* (which change as filters apply), not just by the query, so
 * a derived store would either re-key on the records identity (fine) or
 * close over a snapshot (bad). The free-function form composes cleanly
 * with `applyFilters(...)` in the same expression on +page.svelte.
 */
export function applySearch(
  records: LandscapeRecord[],
  query: string
): LandscapeRecord[] {
  const q = query.trim().toLowerCase();
  if (!q) return records;
  return records.filter((r) => {
    if (r.name.toLowerCase().includes(q)) return true;
    const desc = stripHtml(r.cells.desc?.value ?? '').toLowerCase();
    if (desc.includes(q)) return true;
    const claims = stripHtml(r.cells.claims?.value ?? '').toLowerCase();
    if (claims.includes(q)) return true;
    return false;
  });
}

/**
 * Debounced mirror of `searchQuery`. Updates 100ms after the last keystroke.
 * Use this if you ever wire search into an expensive pipeline; the current
 * matcher is cheap enough that +page.svelte reads `$searchQuery` directly,
 * but the debounced store is exported for future consumers (e.g. URL sync
 * in #12, or a server-side index).
 */
export const debouncedQuery: Readable<string> = derived(
  searchQuery,
  ($q, set) => {
    const handle = setTimeout(() => set($q), 100);
    return () => clearTimeout(handle);
  },
  ''
);
