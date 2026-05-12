// Prerendered loader for the /analyses/forecast view (issue #27).
//
// Records + edges are bundled; the route does its own lineage detection
// (via $lib/analyses/forecast → $lib/lineages) so this loader is just a
// thin pass-through matching the pattern used by /analyses/influence
// and /lineages.

import { getRecords, getEdges } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords(),
  edges: getEdges()
});
