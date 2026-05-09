// Build-time loader. Returning *only* counts here means the landing page's
// client bundle does not pull in the full 6.4 MB landscape.json — Vite
// tree-shakes the data import out of the client chunk because nothing in
// +page.svelte references it after this loader runs at build time.
//
// Issue #9 (table view) will load records[] and edges[] in its own +page.ts.

import { getRecordCount, getEdgeCount } from '$lib/data';

export const prerender = true;

export const load = () => {
  return {
    recordCount: getRecordCount(),
    edgeCount: getEdgeCount()
  };
};
