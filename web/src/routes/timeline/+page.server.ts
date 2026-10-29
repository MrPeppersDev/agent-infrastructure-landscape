// Build-time loader for /timeline (issue #13): prerendered, with the page
// doing the bucketing client-side. Server-only, so only the `created`
// cell ships (in __data.json), not the catalog.

import { slimRecords } from '$lib/slim';

export const prerender = true;

export const load = () => {
  return {
    // Only the cells this page reads (#324); add a slug here before reading a new one.
    records: slimRecords(['created'])
  };
};
