// Build-time loader for the /sections view (issue #15).
//
// Mirrors web/src/routes/+page.server.ts: full records snapshot, no edges.
// Aggregation happens client-side via $derived so the page reacts to the
// global `filters` store if the user toggled filters before navigating here.

import { getRecords, getRecordCount } from '$lib/data';

export const prerender = true;

export const load = () => {
  return {
    records: getRecords(),
    recordCount: getRecordCount()
  };
};
