// /compare/many — 2–5 systems side by side. Only the picker list ships with
// the page; each selected system's full record is fetched from the static
// /api/systems/<id>.json export.
import { getRecords } from '$lib/data';
import { primarySectionOf } from '$lib/families';

export const prerender = true;

export const load = () => ({
  options: getRecords()
    .map((r) => ({ id: r.id, name: r.name, section: primarySectionOf(r) }))
    .sort((a, b) => a.name.localeCompare(b.name))
});
