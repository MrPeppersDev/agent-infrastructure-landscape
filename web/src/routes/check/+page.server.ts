// /check — stack checker. Matching runs client-side against the prebuilt
// data/stack-index.json (nothing pasted leaves the browser); live
// replacements for every flagged dependency are precomputed here at
// prerender time so the page doesn't ship the catalog.

import { getRecords } from '$lib/data';
import { familyForSection } from '$lib/families';
import { alternativesFor } from '$lib/chooser';
import { attentionIds, type StackIndex, type Replacement } from '../../../../mcp/src/stack-check';
import stackIndex from '../../../../data/stack-index.json';

export const prerender = true;

export const load = () => {
  const index = stackIndex as unknown as StackIndex;
  const alts = alternativesFor(
    getRecords() as unknown as Parameters<typeof alternativesFor>[0],
    attentionIds(index),
    (s) => familyForSection(s)?.id ?? 'other',
    index.records,
    3
  );
  const replacements: Record<string, Replacement[]> = {};
  for (const [id, list] of Object.entries(alts)) replacements[id] = list.map(({ id, name, why }) => ({ id, name, why }));
  return { replacements };
};
