import { getRecords } from '$lib/data';
import pricing from '../../../../data/pricing/memory.json';

export const prerender = true;

export const load = () => {
  const ids = new Map(getRecords().map((r) => [r.name, r.id]));
  const p = pricing as unknown as { checked: string; vendors: { system: string }[] };
  return { pricing: p, ids: Object.fromEntries(p.vendors.map((v) => [v.system, ids.get(v.system) ?? null])) };
};
