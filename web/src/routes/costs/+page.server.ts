import { getRecords } from '$lib/data';
import pricing from '../../../../data/pricing/memory.json';
import vectorPricing from '../../../../data/pricing/vector.json';

export const prerender = true;

export const load = () => {
  const ids = new Map(getRecords().map((r) => [r.name, r.id]));
  const p = pricing as unknown as { checked: string; vendors: { system: string }[] };
  const vp = vectorPricing as unknown as { checked: string; vendors: { system: string; record: string }[] };
  return {
    pricing: p,
    vectorPricing: vp,
    ids: {
      ...Object.fromEntries(p.vendors.map((v) => [v.system, ids.get(v.system) ?? null])),
      ...Object.fromEntries(vp.vendors.map((v) => [v.system, v.record]))
    }
  };
};
