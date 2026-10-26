// /api/search-docs.json — the slim documents /search ranks client-side
// (mcp/src/search.ts). Prerendered; fetched lazily so the page shell stays small.
import { json } from '@sveltejs/kit';
import { getRecords } from '$lib/data';
import { familyForSection } from '$lib/families';
import { toItem, type StackStatusLite } from '$lib/chooser';
import { docText, slimForSearch } from '../../../../../mcp/src/search';
import stackIndex from '../../../../../data/stack-index.json';

export const prerender = true;

export const GET = () => {
  const status = (stackIndex as unknown as { records: Record<string, StackStatusLite> }).records;
  const docs = getRecords().map((r) => {
    const s = status[r.id];
    const item = slimForSearch(toItem(r, s ? { status: s.status, severity: s.severity, note: s.note } : undefined));
    return { item, text: docText(r.cells, 220), family: familyForSection(item.section)?.id ?? 'other' };
  });
  return json(docs);
};
