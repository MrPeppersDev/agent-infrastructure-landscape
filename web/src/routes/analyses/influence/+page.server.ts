// Prerendered loader for the influence-vs-adoption matrix (issue #22).
//
// Data is bundled (records + edges) so this just forwards what the page
// needs. Matches the pattern used by /leaderboards/+page.ts.

import { getEdges } from '$lib/data';
import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => ({
  records: slimRecords(['citations', 'funding', 'gh', 'integration-count', 'mindshare']),
  edges: getEdges()
});
