// Prerendered loader for /lineages (issue #17).
//
// All lineage detection happens client-side from records + edges that ship
// as part of the bundled JSON. We still expose a +page.ts so the route is
// statically prerendered alongside the rest of the site.

import { getRecords, getEdges } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords(),
  edges: getEdges()
});
