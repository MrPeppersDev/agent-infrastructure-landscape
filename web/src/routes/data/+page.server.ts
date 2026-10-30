import { getRecords } from '$lib/data';
import { getFamilies, familyForSection, primarySectionOf } from '$lib/families';
import { allEvents } from '$lib/history';
import { fillRates, SPARSE_THRESHOLD } from '$lib/fill-rates';
import { COLUMN_BY_KEY } from '$lib/columns';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const counts = new Map<string, number>();
  for (const r of records) {
    const f = familyForSection(primarySectionOf(r))?.id ?? 'other';
    counts.set(f, (counts.get(f) ?? 0) + 1);
  }
  const catalogs = getFamilies().map((f) => ({ id: f.id, name: f.name, count: counts.get(f.id) ?? 0 }));
  const sample = records.find((r) => r.id === 'mem0--mem0-ai') ?? records[0];
  // Fill rate per column (#334), most complete first.
  const fill = Object.entries(fillRates())
    .map(([slug, rate]) => ({ slug, label: COLUMN_BY_KEY[slug]?.label ?? null, rate }))
    .sort((a, b) => b.rate - a.rate || a.slug.localeCompare(b.slug));
  return { catalogs, total: records.length, sample: { id: sample.id, name: sample.name }, changes: allEvents().length, fill, threshold: SPARSE_THRESHOLD };
};
