// Prerendered loader for the leaderboards page (issue #14).
//
// All the work happens client-side from the records + edges this
// server-only loader ships (only the cells the boards read).

import { getEdges, getRecords } from '$lib/data';
import { corroboration } from '$lib/source-class.js';
import { slimRecords } from '$lib/slim';
import { healthOf } from '$lib/lifecycle';

export const prerender = true;

// Most depended-on systems whose maintainer-health signals meet a concern
// threshold (#365): inbound integration edges × GitHub health. Empty until
// the repo-health bot has covered repos.
function leastHealthy() {
  const inbound = new Map<string, number>();
  for (const e of getEdges()) {
    if (!['integrates-with', 'built-on', 'runtime-dependency'].includes(e.type)) continue;
    inbound.set(e.target, (inbound.get(e.target) ?? 0) + 1);
  }
  return getRecords()
    .flatMap((r) => {
      const h = healthOf(r.id);
      return h && h.concerns.length ? [{ id: r.id, inbound: inbound.get(r.id) ?? 0, concerns: h.concerns, asOf: h.health.as_of }] : [];
    })
    .sort((a, b) => b.inbound - a.inbound || a.id.localeCompare(b.id))
    .slice(0, 10);
}

export const load = () => ({
  leastHealthy: leastHealthy(),
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
