// Build-time loader for the per-system detail page (refs #105).
//
// One prerendered page per record. Each page carries only the data it
// needs — the system's own record, edges touching this id, and a
// {relatedId → name} map for the in-page links. Loading the full
// landscape into each of 912 __data.json sidecars would balloon the
// build by ~5 GB; the per-page slice keeps each sidecar under ~10 kB.

import { error } from '@sveltejs/kit';
import { getRecords, getEdges } from '$lib/data';
import { allPairs, pairToSlug } from '$lib/seo/compare';
import type { LandscapeRecord, Edge } from '$lib/types';

export const prerender = true;

export type RelatedPair = { slug: string; otherId: string; otherName: string };
export type SimilarSystem = { id: string; name: string; tier: 1 | 2 | 3 | 4 | 5; desc: string | null };

export function entries(): { slug: string }[] {
  return getRecords().map((r) => ({ slug: r.id }));
}

export function load({ params }: { params: { slug: string } }): {
  record: LandscapeRecord;
  outgoing: Edge[];
  incoming: Edge[];
  relatedNames: Record<string, string>;
  relatedPairs: RelatedPair[];
  similar: SimilarSystem[];
} {
  const records = getRecords();
  const record = records.find((r) => r.id === params.slug);
  if (!record) throw error(404, `System "${params.slug}" not found`);

  const edges = getEdges();
  const outgoing = edges.filter((e) => e.source === params.slug);
  const incoming = edges.filter((e) => e.target === params.slug);

  const relatedIds = new Set<string>();
  for (const e of outgoing) relatedIds.add(e.target);
  for (const e of incoming) relatedIds.add(e.source);

  const relatedNames: Record<string, string> = {};
  for (const r of records) {
    if (relatedIds.has(r.id)) relatedNames[r.id] = r.name;
  }

  // Related comparisons: every mined /compare/[pair] page that features
  // this system. Surfaces the compare graph from system pages — a single
  // change here adds ~3 outbound links per system × 912 systems = denser
  // internal link graph for Google to crawl.
  const nameById = new Map(records.map((r) => [r.id, r.name] as const));
  const relatedPairs: RelatedPair[] = allPairs()
    .filter((p) => p.a === params.slug || p.b === params.slug)
    .map((p) => {
      const otherId = p.a === params.slug ? p.b : p.a;
      return {
        slug: pairToSlug(p.a, p.b),
        otherId,
        otherName: nameById.get(otherId) ?? otherId
      };
    })
    .sort((a, b) => a.otherName.localeCompare(b.otherName));

  // Similar systems: same primary section, excluding self, ranked by
  // inbound-edge count (the "most referenced" signal that already drives
  // compare-pair selection) so we surface the peers users actually want.
  // Capped at 6 so the page doesn't get cluttered.
  const primarySection = record.sections.find((s) => s.primary)?.section ?? null;
  const incomingCount = new Map<string, number>();
  for (const e of edges) incomingCount.set(e.target, (incomingCount.get(e.target) ?? 0) + 1);

  let similar: SimilarSystem[] = [];
  if (primarySection) {
    similar = records
      .filter((r) => {
        if (r.id === params.slug) return false;
        return r.sections.some((s) => s.primary && s.section === primarySection);
      })
      .sort((a, b) => {
        const da = incomingCount.get(a.id) ?? 0;
        const db = incomingCount.get(b.id) ?? 0;
        if (db !== da) return db - da;
        return a.name.localeCompare(b.name);
      })
      .slice(0, 6)
      .map((r) => ({
        id: r.id,
        name: r.name,
        tier: r.tier,
        desc: r.cells.desc?.value?.trim() || null
      }));
  }

  return { record, outgoing, incoming, relatedNames, relatedPairs, similar };
}
