// Prerendered loader for the taxonomy archetypes view (issue #25).
//
// Data is bundled (records only — edges are not needed for clustering).
// Mirrors the loader for /analyses/influence and /sections.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords()
});
