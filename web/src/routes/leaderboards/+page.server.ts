// Prerendered loader for the leaderboards page (issue #14).
//
// All the work happens client-side from the records + edges this
// server-only loader ships (only the cells the boards read).

import { getEdges, getRecords } from '$lib/data';
import { corroboration } from '$lib/source-class.js';
import { slimRecords } from '$lib/slim';

export const prerender = true;

export const load = () => ({
  // Only the cells this page reads (#324); add a slug here before reading a new one.
  records: slimRecords(['citations', 'gh', 'funding', 'mindshare', 'integration-count']),
  edges: getEdges(),
  // Most third-party-sourced facts (#333), counted on the full records.
  corroborated: getRecords()
    .map((r) => ({ id: r.id, ...corroboration(r) }))
    .filter((c) => c.thirdParty > 0)
    .sort((a, b) => b.thirdParty - a.thirdParty || a.cited - b.cited)
    .slice(0, 10)
});
