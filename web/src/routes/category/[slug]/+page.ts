// Build-time loader for /category/[slug] — a section landing page that
// lists every system whose primary section matches. Refs #105.

import { error } from '@sveltejs/kit';
import { getRecords } from '$lib/data';
import { allSections, sectionFromSlug } from '$lib/seo/sections';

export const prerender = true;

export function entries(): { slug: string }[] {
  return allSections().map((s) => ({ slug: s.slug }));
}

export function load({ params }: { params: { slug: string } }) {
  const sectionName = sectionFromSlug(params.slug);
  if (!sectionName) throw error(404, `Section "${params.slug}" not found`);

  const systems = getRecords()
    .filter((r) => r.sections.some((s) => s.primary && s.section === sectionName))
    .map((r) => {
      const desc = r.cells.desc?.value?.trim() ?? '';
      return {
        id: r.id,
        name: r.name,
        tier: r.tier,
        type: r.cells.type?.value?.trim() ?? null,
        desc: desc.length > 240 ? desc.slice(0, 237) + '…' : desc,
        url: r.url
      };
    })
    .sort((a, b) => {
      if (a.tier !== b.tier) return a.tier - b.tier;
      return a.name.localeCompare(b.name);
    });

  return { sectionName, systems };
}
