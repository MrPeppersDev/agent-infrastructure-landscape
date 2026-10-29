// Prerendered loader for the taxonomy archetypes view (issue #25).
//
// Edges are required for exemplar selection (we rank candidate
// exemplars by inbound integrations/cites). The page payload is still
// fully content-addressed and pre-rendered at build time.

import { getEdges } from '$lib/data';
import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => ({
  records: slimRecords(['citations', 'funding', 'gh', 'integration-count', 'mindshare']),
  edges: getEdges()
});
