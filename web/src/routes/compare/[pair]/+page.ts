// Build-time loader for side-by-side system comparison pages. Refs #105, #125.

import { error } from '@sveltejs/kit';
import { getRecords, getEdges } from '$lib/data';
import { allPairs, pairFromSlug, pairToSlug } from '$lib/seo/compare';
import type { LandscapeRecord, Edge } from '$lib/types';

export const prerender = true;

export function entries(): { pair: string }[] {
  return allPairs().map((p) => ({ pair: pairToSlug(p.a, p.b) }));
}

export type SiblingPair = { id: string; name: string; slug: string };

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

  // For the "compare with another…" pickers on the page: every other
  // pre-computed pair that shares a.id or b.id. Kept slim so the payload
  // stays lean.
  const nameById = new Map<string, string>();
  for (const r of records) nameById.set(r.id, r.name);

  const currentSlug = pairToSlug(a.id, b.id);
  const siblingsForA: SiblingPair[] = [];
  const siblingsForB: SiblingPair[] = [];
  for (const p of allPairs()) {
    const slug = pairToSlug(p.a, p.b);
    if (slug === currentSlug) continue;
    if (p.a === a.id || p.b === a.id) {
      const otherId = p.a === a.id ? p.b : p.a;
      const otherName = nameById.get(otherId);
      if (otherName) siblingsForA.push({ id: otherId, name: otherName, slug });
    }
    if (p.a === b.id || p.b === b.id) {
      const otherId = p.a === b.id ? p.b : p.a;
      const otherName = nameById.get(otherId);
      if (otherName) siblingsForB.push({ id: otherId, name: otherName, slug });
    }
  }
  siblingsForA.sort((x, y) => x.name.localeCompare(y.name));
  siblingsForB.sort((x, y) => x.name.localeCompare(y.name));

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
    between,
    siblingsForA,
    siblingsForB
  };
}
