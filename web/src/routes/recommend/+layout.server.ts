// Shared loader for the Phase 2 recommender surfaces (issue #97 / Gate 3).
//
// Both /recommend/between and the upcoming /recommend/by-constraints
// (Gate 4) consume the same catalog snapshot. Centralised here so the
// child routes don't repeat the import.

import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => ({
  records: slimRecords(['capability-band', 'capability-composite-score', 'capability-last-verified', 'cost-input-usd-per-mtok', 'cost-last-verified', 'cost-tier', 'deployment', 'desc', 'latency', 'orchestration', 'use-case-anti-tags', 'use-case-tags'], { provenance: true })
});
