// Prerendered loader for /lineages (issue #17).
//
// All lineage detection happens client-side from the records + edges this
// server-only loader ships (only the cells the page reads).

import { getEdges } from '$lib/data';
import { slimRecords } from '$lib/slim';

export const prerender = true;

export const load = () => ({
  // Only the cells this page reads (#324); add a slug here before reading a new one.
  records: slimRecords(['created', 'claims', 'desc']),
  edges: getEdges()
});
