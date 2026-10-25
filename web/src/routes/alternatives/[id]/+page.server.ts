import { error } from '@sveltejs/kit';
import { alternativesTo, alternativeIds, familyIdOfItem, familyName } from '$lib/alternatives';
import { allPairs, pairToSlug } from '$lib/seo/compare';
import { attentionIds, type StackIndex } from '../../../../../mcp/src/stack-check';
import stackIndex from '../../../../../data/stack-index.json';

export const prerender = true;

export function entries(): { id: string }[] {
  const ids = new Set(alternativeIds());
  // every flagged dependency must resolve (stack checker links here)
  for (const id of attentionIds(stackIndex as unknown as StackIndex)) ids.add(id);
  return [...ids].map((id) => ({ id }));
}

export function load({ params }: { params: { id: string } }) {
  const r = alternativesTo(params.id, 8);
  if (!r) throw error(404, `No system "${params.id}"`);
  const pairs = new Set(allPairs().map((p) => pairToSlug(p.a, p.b)));
  const compareHref = (otherId: string) => {
    const slug = pairToSlug(r.target.id, otherId);
    if (pairs.has(slug)) return `/compare/${slug}`;
    const rev = pairToSlug(otherId, r.target.id);
    if (pairs.has(rev)) return `/compare/${rev}`;
    return `/compare/custom?a=${encodeURIComponent(r.target.id)}&b=${encodeURIComponent(otherId)}`;
  };
  return {
    target: r.target,
    family: familyName(familyIdOfItem(r.target)),
    alts: r.alts.map((a) => ({ ...a, compare: compareHref(a.id) }))
  };
}
