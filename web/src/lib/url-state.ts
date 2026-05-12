// URL ↔ state codec for issue #12. The three stores (search, filters, sort)
// are serialised into compact query params so views are bookmarkable and
// shareable. The codec is intentionally side-effect-free: callers wire it
// to `goto()` / `window.location` in +page.svelte. Keeping the I/O at the
// edge makes this trivial to test (every transform is pure).
//
// Encoding contract (kept compact — skip empty values so the URL stays
// readable for the common "default view" case):
//   q=<search>                         only if non-empty
//   <facet>=v1,v2,...                  one param per non-empty facet Set
//   sort=col1:asc,col2:desc            only if non-empty
//
// Round-trip guarantee: `urlToState(stateToUrl(s, f, x))` must equal
// `{ search: s, filters: f, sort: x }` for any legal triple. Values not
// in the canonical bucket vocabulary are dropped on the way in
// (forward-compat: unknown facets / values are silently ignored).
//
// Why URLSearchParams rather than hand-rolled string-building: URLSearchParams
// handles percent-encoding (e.g. spaces in section names like "Dedicated
// memory layers" become "+") and gives us a stable iteration order. We don't
// build the leading "?" — callers can call `params.toString()` themselves.
//
// Why not base64 / lz-string compression: the URL is well under browser
// length limits (~2 KB) even with every facet maxed out, and a readable
// `?tier=1,2&license=Apache-2.0` is shareable in chat / email / etc.
// Compression is deferred until we hit a real length problem.
//
// Facet value canonicalisation: the URL accepts the same bucket strings
// the filter rail shows (Apache-2.0, self-hosted, etc.). Tier is the
// only numeric facet; values are coerced to integers 1-5 on parse.

import {
  FACET_ORDER,
  emptyState,
  type FacetName,
  type FilterState
} from '$lib/stores/filters';
import type { SortEntry, SortColumn, SortDirection } from '$lib/stores/sort';

// --- Encoding ---------------------------------------------------------

/**
 * Build a URLSearchParams from the three store values. Returns an empty
 * params object for the default view (no search, no filters, no sort), so
 * the resulting URL is `/` rather than `/?` — handled by the caller.
 */
export function stateToUrl(
  search: string,
  filters: FilterState,
  sort: SortEntry[]
): URLSearchParams {
  const params = new URLSearchParams();

  const trimmed = search.trim();
  if (trimmed.length > 0) {
    params.set('q', trimmed);
  }

  for (const facet of FACET_ORDER) {
    const set = filters[facet] as Set<string | number>;
    if (set.size === 0) continue;
    // Sort within a facet for deterministic URLs (so two browsers landing
    // on the same view share the same URL — important for cache hits and
    // "compare URLs" debugging). Numbers sort numerically, strings alpha.
    const values = [...set].sort((a, b) => {
      if (typeof a === 'number' && typeof b === 'number') return a - b;
      return String(a).localeCompare(String(b));
    });
    params.set(facet, values.join(','));
  }

  if (sort.length > 0) {
    params.set(
      'sort',
      sort.map((e) => `${e.column}:${e.direction}`).join(',')
    );
  }

  return params;
}

// --- Decoding ---------------------------------------------------------

const VALID_DIRECTIONS = new Set<SortDirection>(['asc', 'desc']);
const FACET_NAME_SET = new Set<string>(FACET_ORDER);

/**
 * Parse query params back into the three store shapes. Unknown params are
 * ignored (forward-compat). Values that aren't real strings (or, for tier,
 * aren't integers 1-5) are dropped — this is deliberately lenient so a
 * stale URL never crashes the app.
 *
 * NOTE: we don't validate facet values against the canonical bucket list
 * here. If a user shares a URL after the bucket vocabulary expands, the
 * value will simply select no records — which is the correct behaviour
 * (the URL is honest about what the user asked for, even if no record
 * matches today). Old facets disappearing from FACET_ORDER drop their
 * params silently via the FACET_NAME_SET check.
 */
export function urlToState(params: URLSearchParams): {
  search: string;
  filters: FilterState;
  sort: SortEntry[];
} {
  const search = params.get('q') ?? '';
  const filters = emptyState();

  for (const [key, raw] of params.entries()) {
    if (key === 'q' || key === 'sort') continue;
    if (!FACET_NAME_SET.has(key)) continue;
    const facet = key as FacetName;
    const values = raw.split(',').map((v) => v.trim()).filter(Boolean);
    if (values.length === 0) continue;

    if (facet === 'tier') {
      for (const v of values) {
        const n = Number(v);
        if (!Number.isInteger(n) || n < 1 || n > 5) continue;
        filters.tier.add(n);
      }
    } else {
      const set = filters[facet] as Set<string>;
      for (const v of values) set.add(v);
    }
  }

  const sort: SortEntry[] = [];
  const sortRaw = params.get('sort');
  if (sortRaw) {
    for (const piece of sortRaw.split(',')) {
      const [column, direction] = piece.split(':');
      if (!column || !direction) continue;
      if (!VALID_DIRECTIONS.has(direction as SortDirection)) continue;
      // Don't validate `column` against the 60-slug enum here — it's a
      // closed list but the sort store accepts any string and the
      // comparator handles unknown columns gracefully. Keeps this codec
      // independent of the column schema.
      sort.push({
        column: column as SortColumn,
        direction: direction as SortDirection
      });
    }
  }

  return { search, filters, sort };
}

// --- Equality (used to skip redundant goto() calls) -------------------

/**
 * Cheap structural equality on FilterState. Sets are compared by size +
 * membership. Used by the +page.svelte URL writer to avoid pushing the
 * same URL twice (which would still be a wasted history entry / focus
 * disruption even with replaceState).
 */
export function filterStateEqual(a: FilterState, b: FilterState): boolean {
  for (const facet of FACET_ORDER) {
    const sa = a[facet] as Set<string | number>;
    const sb = b[facet] as Set<string | number>;
    if (sa.size !== sb.size) return false;
    for (const v of sa) if (!sb.has(v)) return false;
  }
  return true;
}

export function sortEntriesEqual(a: SortEntry[], b: SortEntry[]): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i].column !== b[i].column) return false;
    if (a[i].direction !== b[i].direction) return false;
  }
  return true;
}
