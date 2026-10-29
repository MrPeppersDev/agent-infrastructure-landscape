// /category — overview index linking out to every section landing.

import { getRecords } from '$lib/data';
import { allSections } from '$lib/seo/sections';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const counts = new Map<string, number>();
  for (const r of records) {
    const p = r.sections.find((s) => s.primary);
    if (p) counts.set(p.section, (counts.get(p.section) ?? 0) + 1);
  }

  const categories = allSections().map((s) => ({
    name: s.name,
    slug: s.slug,
    count: counts.get(s.name) ?? 0
  }));

  return { categories };
};
