// /best/ — index of long-tail "best of" landing pages. Refs #105.

import { getRecords, getEdges } from '$lib/data';
import { allBestOf } from '$lib/seo/best-of';

export const prerender = true;

export interface BestOfIndexEntry {
  slug: string;
  title: string;
  description: string;
  count: number;
}

export function load(): { entries: BestOfIndexEntry[] } {
  const records = getRecords();
  void getEdges();
  const entries: BestOfIndexEntry[] = allBestOf().map((p) => ({
    slug: p.slug,
    title: p.title,
    description: p.description,
    count: records.filter(p.match).length
  }));
  // Surface the densest pages first — those are the strongest landing
  // signals and what visitors are most likely to find useful.
  entries.sort((a, b) => b.count - a.count);
  return { entries };
}
