// Index for /systems — a flat directory of every record in the catalog.
// Returns only the fields the index needs (id, name, tier, section, type,
// short desc) so the page's __data.json stays small.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const systems = records
    .map((r) => {
      const primary = r.sections.find((s) => s.primary);
      const desc = r.cells.desc?.value?.trim() ?? '';
      return {
        id: r.id,
        name: r.name,
        tier: r.tier,
        section: primary?.section ?? 'Other',
        type: r.cells.type?.value?.trim() ?? null,
        desc: desc.length > 200 ? desc.slice(0, 197) + '…' : desc
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
  return { systems };
};
