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

// --- In-cell highlighting (Polish 2026-05-07) ---------------------------
//
// `highlightMatches` wraps every case-insensitive occurrence of `query` in
// `value` with a `<mark class="search-hit">…</mark>` span. Both forms below
// preserve HTML tag boundaries — a literal "<" or ">" inside an attribute
// will not get the wrapper, only the text between tags.
//
// The plain-text variant (`highlightPlain`) is used for the `name` column
// (which is rendered as text, not HTML); the HTML variant handles `desc`
// and `claims` cells whose values may contain `<a>` links, taxonomy pills,
// etc. See TableRow.svelte for the wiring.

const HTML_BOUNDARY_RE = /(<[^>]*>)/g;

/** Escape a string for safe inclusion as text inside `{@html}`. We
 *  HTML-encode `&`, `<`, `>` so that plain-text cell values can't break
 *  out of the wrapper. */
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/** Escape a string for safe inclusion in a regex pattern. */
function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Wrap every case-insensitive occurrence of `query` in `text` (which is
 * plain text, not HTML) with `<mark class="search-hit">…</mark>`. The
 * non-matching segments are HTML-escaped so the consumer can pass the
 * result straight to `{@html}` without XSS risk.
 */
export function highlightPlain(text: string, query: string): string {
  const q = query.trim();
  if (!q) return escapeHtml(text);
  const re = new RegExp(escapeRegex(q), 'gi');
  let out = '';
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    out += escapeHtml(text.slice(last, m.index));
    out += `<mark class="search-hit">${escapeHtml(m[0])}</mark>`;
    last = m.index + m[0].length;
    if (m[0].length === 0) re.lastIndex++; // guard against zero-length match
  }
  out += escapeHtml(text.slice(last));
  return out;
}

/**
 * Wrap every case-insensitive occurrence of `query` in `html` with
 * `<mark class="search-hit">…</mark>`, BUT only inside text nodes — i.e.
 * runs of characters that sit between `>` and `<`. Tag interiors
 * (attributes, tag names) are passed through untouched.
 *
 * The implementation splits `html` on the tag-boundary regex into
 * alternating text/tag chunks (odd indices are tags), wraps the text
 * chunks only, and concatenates back. This is the "approximation" called
 * out in the issue brief — perfect HTML-tree highlighting requires a DOM
 * parse and is over-budget for the value it adds.
 */
export function highlightHtml(html: string, query: string): string {
  const q = query.trim();
  if (!q) return html;
  const re = new RegExp(escapeRegex(q), 'gi');
  // Split keeps the delimiters because the regex is capturing.
  const parts = html.split(HTML_BOUNDARY_RE);
  for (let i = 0; i < parts.length; i++) {
    // Odd indices are tag chunks (the captured group); leave them alone.
    if (i % 2 === 1) continue;
    if (!parts[i]) continue;
    parts[i] = parts[i].replace(
      re,
      (match) => `<mark class="search-hit">${match}</mark>`
    );
  }
  return parts.join('');
}
