import { alternativeIds, allItems, familyIdOfItem, familyName } from '$lib/alternatives';

export const prerender = true;

export function load() {
  const ids = new Set(alternativeIds());
  const groups: Record<string, { id: string; name: string; flagged: boolean }[]> = {};
  for (const i of allItems()) {
    if (!ids.has(i.id)) continue;
    const f = familyName(familyIdOfItem(i));
    (groups[f] ??= []).push({ id: i.id, name: i.name, flagged: i.status.severity >= 2 });
  }
  for (const g of Object.values(groups)) g.sort((a, b) => a.name.localeCompare(b.name));
  return { groups, count: ids.size };
}
