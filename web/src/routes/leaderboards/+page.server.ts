// Prerendered loader for the leaderboards page (issue #14).
//
// All the work happens client-side from the records + edges this
// server-only loader ships (only the cells the boards read).

import { getEdges } from '$lib/data';
import { slimRecords } from '$lib/slim';

export const prerender = true;

export const load = () => ({
  // Only the cells this page reads (#324); add a slug here before reading a new one.
  records: slimRecords(['citations', 'gh', 'funding', 'mindshare', 'integration-count']),
  edges: getEdges()
});
