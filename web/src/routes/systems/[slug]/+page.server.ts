// Build-time loader for the per-system detail page (refs #105).
//
// One prerendered page per record. Each page carries only the data it
// needs — the system's own record, edges touching this id, and a
// {relatedId → name} map for the in-page links. Loading the full
// landscape into each of ~950 __data.json sidecars would balloon the
// build by ~5 GB; the per-page slice keeps each sidecar under ~10 kB.

import { error, redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import { getRecords, getEdges, getRedirects } from '$lib/data';
import { allPairs, pairToSlug } from '$lib/seo/compare';
import { familyForSection } from '$lib/families';
import { historyFor, type HistoryEvent } from '$lib/history';
import { lifecycleOf, type LifecycleInfo } from '$lib/lifecycle';

// Families with /alternatives/<id> pages (mirror of $lib/alternatives ALT_FAMILIES).
const ALT_FAMILIES = new Set(['memory', 'agents', 'data']);
import type { LandscapeRecord, Edge } from '$lib/types';

export const prerender = true;

export type RelatedPair = { slug: string; otherId: string; otherName: string };
export type SimilarSystem = { id: string; name: string; tier: 1 | 2 | 3 | 4 | 5; desc: string | null };

/** One row per related system: edges between the same pair that differ only
 * by type collapse into one, listing every type and keeping the longest
 * evidence (#327). */
export type PairEdge = Edge & { types: Edge['type'][] };
function byPair(list: Edge[], other: (e: Edge) => string): PairEdge[] {
  const rows = new Map<string, PairEdge>();
  for (const e of list) {
    const row = rows.get(other(e));
    if (!row) rows.set(other(e), { ...e, types: [e.type] });
    else {
      if (!row.types.includes(e.type)) row.types.push(e.type);
      if ((e.evidence ?? '').length > (row.evidence ?? '').length) Object.assign(row, { evidence: e.evidence, citation: e.citation, verified_at: e.verified_at, verified_version: e.verified_version });
    }
  }
  return [...rows.values()];
}

export function entries(): { slug: string }[] {
  // Merged-away ids keep a page that redirects to the kept record.
  return [...getRecords().map((r) => r.id), ...Object.keys(getRedirects())].map((slug) => ({ slug }));
}

export function load({ params }: { params: { slug: string } }): {
  record: LandscapeRecord;
  outgoing: PairEdge[];
  incoming: PairEdge[];
  relatedNames: Record<string, string>;
  relatedPairs: RelatedPair[];
  similar: SimilarSystem[];
  hasAlternatives: boolean;
  history: HistoryEvent[];
  citedCells: number;
  lifecycle: LifecycleInfo;
} {
  const records = getRecords();
  const record = records.find((r) => r.id === params.slug);
  const movedTo = getRedirects()[params.slug];
  if (!record && movedTo) redirect(308, `${base}/systems/${movedTo}`);
  if (!record) throw error(404, `System "${params.slug}" not found`);

  const edges = getEdges();
  const outgoing = byPair(edges.filter((e) => e.source === params.slug), (e) => e.target);
  const incoming = byPair(edges.filter((e) => e.target === params.slug), (e) => e.source);

  const relatedIds = new Set<string>();
  for (const e of outgoing) relatedIds.add(e.target);
  for (const e of incoming) relatedIds.add(e.source);

  const relatedNames: Record<string, string> = {};
  for (const r of records) {
    if (relatedIds.has(r.id)) relatedNames[r.id] = r.name;
  }

  // Related comparisons: every mined /compare/[pair] page that features
  // this system. Surfaces the compare graph from system pages — a single
  // change here adds ~3 outbound links per system × ~950 systems = denser
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

  const primary = record.sections.find((s) => s.primary)?.section ?? record.sections[0]?.section ?? '';
  const hasAlternatives = ALT_FAMILIES.has(familyForSection(primary)?.id ?? '');

  const citedCells = Object.values(record.cells).filter((c) => c && c.citation && c.status === 'real-data').length;

  return { record, outgoing, incoming, relatedNames, relatedPairs, similar, hasAlternatives, history: historyFor(record.id), citedCells, lifecycle: lifecycleOf(record.id) };
}
