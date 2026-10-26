// /compatibility — "do these work together?" Every pair with integration
// evidence (typed edges + integration cells naming the other system) is
// computed once at prerender time; the page looks pairs up client-side.
import { getRecords, getEdges } from '$lib/data';
import { primarySectionOf } from '$lib/families';
import { allLinks } from '$lib/compat';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const links = allLinks(records as never, getEdges() as never);
  const linked = new Set(links.flatMap((l) => [l.a, l.b]));
  const options = records
    .map((r) => ({ id: r.id, name: r.name, section: primarySectionOf(r), linked: linked.has(r.id) }))
    .sort((a, b) => a.name.localeCompare(b.name));
  return { links, options };
};
