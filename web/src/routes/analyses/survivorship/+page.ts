// Build-time loader for /analyses/survivorship (issue #23). Same shape as
// /leaderboards — ship records + edges, let the page do the classification
// pass client-side. Round 23: also ship detected lineages so the
// "abandoned but cited" card can label each row with the family it
// belongs to.

import { getRecords, getEdges } from '$lib/data';
import { detectLineages } from '$lib/lineages';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const edges = getEdges();
  const lineages = detectLineages(records, edges);
  return { records, edges, lineages };
};
