// Shared loader for the Phase 2 recommender surfaces (issue #97 / Gate 3).
//
// Both /recommend/between and the upcoming /recommend/by-constraints
// (Gate 4) consume the same catalog snapshot. Centralised here so the
// child routes don't repeat the import.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords()
});
