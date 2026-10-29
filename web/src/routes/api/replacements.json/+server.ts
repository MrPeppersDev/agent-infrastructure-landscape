// /api/replacements.json — live replacements (top 6; the checker keeps 3 after ranking by fit) for every system the
// stack checker flags. Prerendered; used by the GitHub Action
// (action/check.mjs) and anyone running the checker elsewhere.
import { json } from '@sveltejs/kit';
import { getRecords } from '$lib/data';
import { familyForSection } from '$lib/families';
import { alternativesFor } from '$lib/chooser';
import { attentionIds, type StackIndex } from '../../../../../mcp/src/stack-check';
import stackIndex from '../../../../../data/stack-index.json';

export const prerender = true;

export const GET = () => {
  const index = stackIndex as unknown as StackIndex;
  const alts = alternativesFor(
    getRecords() as unknown as Parameters<typeof alternativesFor>[0],
    attentionIds(index),
    (s) => familyForSection(s)?.id ?? 'other',
    index.records,
    6
  );
  const out: Record<string, { id: string; name: string; why: string[] }[]> = {};
  for (const [id, list] of Object.entries(alts)) out[id] = list.map(({ id, name, why }) => ({ id, name, why }));
  return json(out);
};
