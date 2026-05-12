// Prerendered loader for the leaderboards page (issue #14).
//
// All the work happens client-side from records + edges that ship as part
// of the bundled JSON. We still expose a +page.ts so the route can be
// statically prerendered alongside the rest of the site.

import { getRecords, getEdges } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords(),
  edges: getEdges()
});
