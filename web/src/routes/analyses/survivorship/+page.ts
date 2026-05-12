// Build-time loader for /analyses/survivorship (issue #23). Same shape as
// /leaderboards — ship records + edges, let the page do the classification
// pass client-side. The classification is ~O(R) so doing it at render time
// is fine.

import { getRecords, getEdges } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords(),
  edges: getEdges()
});
