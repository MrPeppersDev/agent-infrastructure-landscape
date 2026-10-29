// Prerendered loader for the /analyses/forecast view (issue #27).
//
// Records + edges are bundled; the route does its own lineage detection
// (via $lib/analyses/forecast → $lib/lineages) so this loader is just a
// thin pass-through matching the pattern used by /analyses/influence
// and /lineages.

import { getEdges } from '$lib/data';
import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => ({
  records: slimRecords(['claims', 'cons', 'created']),
  edges: getEdges()
});
