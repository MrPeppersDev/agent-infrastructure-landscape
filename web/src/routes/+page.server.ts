// Build-time loader for the table view (issue #9).
//
// The table needs the full records array. We load it server-side at
// prerender time and pass it through to the client; Vite emits the JSON
// as a hashed asset, and SvelteKit serialises it into the page's
// __data.json sidecar. The full landscape.json is ~6.4 MB but the
// post-serialisation payload is comparable to a hand-rolled fetch and
// avoids an extra round-trip on first paint.
//
// Edges aren't needed for the table view — they're loaded only by the
// graph page (issue #16). Keeping them out of this load keeps the
// prerendered payload focused.

import { getRecords, getRecordCount, getEdgeCount } from '$lib/data';
import { getFamilies, familyIdOf } from '$lib/families';
import { lifecycleOf } from '$lib/lifecycle';
import { fillRates } from '$lib/fill-rates';
import { COLUMNS } from '$lib/columns';

export const prerender = true;

export const load = () => {
  return {
    records: defaultOrder(getRecords()).map((r) => ({ ...r, lifecycle: lifecycleOf(r.id).status })),
    recordCount: getRecordCount(),
    edgeCount: getEdgeCount(),
    // Fill rate per table cell column, for hiding sparse ones (#334).
    fill: Object.fromEntries(COLUMNS.filter((c) => c.isCell).map((c) => [c.key, fillRates()[c.key] ?? 0]))
  };
};

// Default (unsorted) table order: product family (Agent Memory first),
// then tier (battle-tested first), then name. Before this the table was
// in raw id order, so a first-time visitor's first rows were robotics
// models and sales tools rather than the memory systems the catalog is
// known for. Any explicit column sort still overrides this.
function defaultOrder<T extends { name: string; tier: number }>(records: T[]): T[] {
  const famIndex = new Map(getFamilies().map((f, i) => [f.id, i]));
  return [...records].sort((a, b) => {
    const fa = famIndex.get(familyIdOf(a as never)) ?? 99;
    const fb = famIndex.get(familyIdOf(b as never)) ?? 99;
    if (fa !== fb) return fa - fb;
    if (a.tier !== b.tier) return a.tier - b.tier;
    return a.name.localeCompare(b.name);
  });
}
