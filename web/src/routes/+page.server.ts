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

export const prerender = true;

export const load = () => {
  return {
    records: getRecords(),
    recordCount: getRecordCount(),
    edgeCount: getEdgeCount()
  };
};
