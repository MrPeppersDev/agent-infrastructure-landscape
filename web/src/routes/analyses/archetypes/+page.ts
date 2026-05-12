// Prerendered loader for the taxonomy archetypes view (issue #25).
//
// Edges are required for exemplar selection (we rank candidate
// exemplars by inbound integrations/cites). The page payload is still
// fully content-addressed and pre-rendered at build time.

import { getRecords, getEdges } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords(),
  edges: getEdges()
});
