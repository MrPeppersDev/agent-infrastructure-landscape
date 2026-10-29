// Build-time loader for /analyses/survivorship (issue #23). Same shape as
// /leaderboards — ship records + edges, let the page do the classification
// pass client-side. Round 23: also ship detected lineages so the
// "abandoned but cited" card can label each row with the family it
// belongs to.

import { getEdges } from '$lib/data';
import { slimRecords } from '$lib/slim';
import { detectLineages } from '$lib/lineages';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => {
  const records = slimRecords(['code-release', 'created', 'gh', 'latest-release', 'license']);
  const edges = getEdges();
  const lineages = detectLineages(records, edges);
  return { records, edges, lineages };
};
