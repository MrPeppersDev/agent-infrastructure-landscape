// Prerendered loader for the influence-vs-adoption matrix (issue #22).
//
// Data is bundled (records + edges) so this just forwards what the page
// needs. Matches the pattern used by /leaderboards/+page.ts.

import { getRecords, getEdges } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords(),
  edges: getEdges()
});
