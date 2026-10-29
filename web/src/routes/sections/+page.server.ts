// Build-time loader for the /sections view (issue #15).
//
// Records with only the cells the stats and filters read, no edges.
// Aggregation happens client-side via $derived so the page reacts to the
// global `filters` store if the user toggled filters before navigating here.

import { getRecordCount } from '$lib/data';
import { slimRecords } from '$lib/slim';

export const prerender = true;

export const load = () => {
  return {
    // Only the cells this page reads (#324); add a slug here before reading a new one.
    records: slimRecords(['license', 'deployment', 'citations', 'gh', 'funding', 'mindshare', 'modalities', 'freshness-date', 'taxonomy-three-layer-rollup', 'licensing-bucket']),
    recordCount: getRecordCount()
  };
};
