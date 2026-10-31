// /catalogs/<silo>/browse: the silo's rows in the shared table view, with
// the silo's default columns. Ships only this silo's records.

import { error } from '@sveltejs/kit';
import { getRecords, getEdgeCount } from '$lib/data';
import { getSilos, getSilo, recordsInSilo } from '$lib/silos';
import { lifecycleOf } from '$lib/lifecycle';
import { fillRates } from '$lib/fill-rates';
import { COLUMNS } from '$lib/columns';

export const prerender = true;
export const entries = () => getSilos().map((s) => ({ silo: s.id }));

export const load = ({ params }: { params: { silo: string } }) => {
  const silo = getSilo(params.silo);
  if (!silo) throw error(404, `No catalog named "${params.silo}"`);
  const rows = recordsInSilo(getRecords(), silo)
    .map((r) => ({ ...r, lifecycle: lifecycleOf(r.id).status }))
    .sort((a, b) => a.tier - b.tier || a.name.localeCompare(b.name));
  return {
    siloId: silo.id,
    records: rows,
    recordCount: rows.length,
    edgeCount: getEdgeCount(),
    fill: Object.fromEntries(COLUMNS.filter((c) => c.isCell).map((c) => [c.key, fillRates()[c.key] ?? 0]))
  };
};
