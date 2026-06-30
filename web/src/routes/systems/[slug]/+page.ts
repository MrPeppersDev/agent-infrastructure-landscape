// Build-time loader for the per-system detail page (refs #105).
//
// One prerendered page per record. Each page carries only the data it
// needs — the system's own record, edges touching this id, and a
// {relatedId → name} map for the in-page links. Loading the full
// landscape into each of 912 __data.json sidecars would balloon the
// build by ~5 GB; the per-page slice keeps each sidecar under ~10 kB.

import { error } from '@sveltejs/kit';
import { getRecords, getEdges } from '$lib/data';
import type { LandscapeRecord, Edge } from '$lib/types';

export const prerender = true;

export function entries(): { slug: string }[] {
  return getRecords().map((r) => ({ slug: r.id }));
}

export function load({ params }: { params: { slug: string } }): {
  record: LandscapeRecord;
  outgoing: Edge[];
  incoming: Edge[];
  relatedNames: Record<string, string>;
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

  return { record, outgoing, incoming, relatedNames };
}
