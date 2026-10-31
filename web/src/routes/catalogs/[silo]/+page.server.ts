// /catalogs/<silo>: the landing page of one focused view (taxonomy/silos.json).
// Counts, lifecycle mix, sections, the most-referenced systems, recent
// changes, and the decision tools, research views and exports for it.

import { error } from '@sveltejs/kit';
import { getRecords, getEdges } from '$lib/data';
import { getSilos, getSilo, recordsInSilo, siloExportId } from '$lib/silos';
import { lifecycleOf } from '$lib/lifecycle';
import { LIFECYCLE_TONE } from '$lib/lifecycle-labels';
import { allEvents } from '$lib/history';
import { allBestOf } from '$lib/seo/best-of';
import type { StackStatus } from '../../../../../mcp/src/stack-check';

export const prerender = true;
export const entries = () => getSilos().map((s) => ({ silo: s.id }));

const slugOf = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

export const load = ({ params }: { params: { silo: string } }) => {
  const silo = getSilo(params.silo);
  if (!silo) throw error(404, `No catalog named "${params.silo}"`);

  const rows = recordsInSilo(getRecords(), silo);
  const ids = new Set(rows.map((r) => r.id));
  const byId = new Map(rows.map((r) => [r.id, r]));

  const lifecycle: Partial<Record<StackStatus, number>> = {};
  let attention = 0;
  for (const r of rows) {
    const st = lifecycleOf(r.id).status;
    lifecycle[st] = (lifecycle[st] ?? 0) + 1;
    if (['warn', 'bad'].includes(LIFECYCLE_TONE[st])) attention++;
  }
  const tiers = [1, 2, 3, 4, 5].map((t) => rows.filter((r) => r.tier === t).length);

  const sectionCount = new Map<string, number>();
  for (const r of rows) {
    const s = r.sections.find((x) => x.primary)?.section ?? r.sections[0]?.section ?? '';
    sectionCount.set(s, (sectionCount.get(s) ?? 0) + 1);
  }
  const sections = silo.sections
    .map((name) => ({ name, slug: slugOf(name), count: sectionCount.get(name) ?? 0 }))
    .filter((s) => s.count > 0)
    .sort((a, b) => b.count - a.count);

  // Most referenced: inbound edges from anywhere in the catalog.
  const inbound = new Map<string, number>();
  for (const e of getEdges()) if (ids.has(e.target)) inbound.set(e.target, (inbound.get(e.target) ?? 0) + 1);
  const top = [...rows]
    .sort((a, b) => a.tier - b.tier || (inbound.get(b.id) ?? 0) - (inbound.get(a.id) ?? 0) || a.name.localeCompare(b.name))
    .slice(0, 12)
    .map((r) => ({
      id: r.id,
      name: r.name,
      tier: r.tier,
      type: r.cells.type?.status === 'real-data' ? r.cells.type.value : null,
      lifecycle: lifecycleOf(r.id).status,
      inbound: inbound.get(r.id) ?? 0
    }));

  const recent = allEvents()
    .filter((e) => ids.has(e.id) && e.kind !== 'removed')
    .slice(0, 8)
    .map((e) => ({
      date: e.date,
      id: e.id,
      name: byId.get(e.id)?.name ?? e.id,
      text:
        e.kind === 'added'
          ? 'Added to the catalog'
          : e.changes
              .slice(0, 2)
              .map((c) => (c.to ? `${c.label}: ${c.to}` : `${c.label} cleared`))
              .join(' · ')
    }));

  const bestOf = allBestOf()
    .filter((p) => silo.bestOf.includes(p.slug))
    .map((p) => ({ slug: p.slug, title: p.title, count: rows.filter(p.match).length }));

  return {
    silo,
    count: rows.length,
    lifecycle,
    attention,
    tiers,
    sections,
    top,
    recent,
    bestOf,
    exportId: siloExportId(silo),
    others: getSilos().filter((s) => s.id !== silo.id).map((s) => ({ id: s.id, short: s.short }))
  };
};
