// Build-time loader for side-by-side system comparison pages. Refs #105.

import { error } from '@sveltejs/kit';
import { getRecords, getEdges } from '$lib/data';
import { allPairs, pairFromSlug, pairToSlug } from '$lib/seo/compare';
import type { LandscapeRecord, Edge } from '$lib/types';

export const prerender = true;

export function entries(): { pair: string }[] {
  return allPairs().map((p) => ({ pair: pairToSlug(p.a, p.b) }));
}

export function load({ params }: { params: { pair: string } }) {
  const parsed = pairFromSlug(params.pair);
  if (!parsed) throw error(404, `Comparison "${params.pair}" not found`);

  const records = getRecords();
  const a = records.find((r) => r.id === parsed.a);
  const b = records.find((r) => r.id === parsed.b);
  if (!a || !b) throw error(404, `Comparison "${params.pair}" not found`);

  // Direct edges between the two — typed evidence of an actual
  // relationship (competes-with, builds-on, integrates-with, cites…).
  const edges = getEdges();
  const between: Edge[] = edges.filter(
    (e) =>
      (e.source === a.id && e.target === b.id) ||
      (e.source === b.id && e.target === a.id)
  );

  function slim(r: LandscapeRecord) {
    return {
      id: r.id,
      name: r.name,
      tier: r.tier,
      url: r.url,
      last_verified_at: r.last_verified_at,
      sections: r.sections,
      taxonomy: r.taxonomy,
      cells: r.cells
    };
  }

  return {
    a: slim(a),
    b: slim(b),
    between
  };
}
