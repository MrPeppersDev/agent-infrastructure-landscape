// /compare — index of every mined comparison pair, grouped by section.

import { getRecords } from '$lib/data';
import { allPairs, pairToSlug } from '$lib/seo/compare';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const nameById = new Map(records.map((r) => [r.id, r.name] as const));

  const pairs = allPairs()
    .map((p) => ({
      slug: pairToSlug(p.a, p.b),
      aName: nameById.get(p.a) ?? p.a,
      bName: nameById.get(p.b) ?? p.b,
      reason: p.reason,
      section: p.section ?? null
    }))
    .sort((a, b) => {
      const sa = a.section ?? 'zzz';
      const sb = b.section ?? 'zzz';
      if (sa !== sb) return sa.localeCompare(sb);
      return a.aName.localeCompare(b.aName);
    });

  return { pairs };
};
