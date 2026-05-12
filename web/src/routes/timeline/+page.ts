// Build-time loader for /timeline (issue #13). Same pattern as the table
// view: prerender, ship the full records array, let the page do all the
// bucketing client-side. The site is static (adapter-static) so loading
// here happens once at build time and the JSON is shipped in __data.json.
//
// We don't need edges for the timeline — only the `created` cell — but
// re-using getRecords() keeps the data path identical to the table view.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => {
  return {
    records: getRecords()
  };
};
