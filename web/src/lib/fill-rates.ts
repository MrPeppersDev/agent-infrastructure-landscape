// Fill rate per cell column (#334): the share of records with a real or
// estimated value. Server-only (imports the catalog). Columns under
// SPARSE_THRESHOLD leave the default table for an opt-in "Sparse" group;
// columns at zero are left out of the table and the exports until they
// have data.

import { getRecords } from './data';

export const SPARSE_THRESHOLD = 0.15;

let cache: Record<string, number> | null = null;

export function fillRates(): Record<string, number> {
  if (cache) return cache;
  const records = getRecords();
  const filled = new Map<string, number>();
  for (const r of records) {
    for (const [slug, c] of Object.entries(r.cells)) {
      if (!filled.has(slug)) filled.set(slug, 0);
      if (c && (c.status === 'real-data' || c.status === 'estimate') && String(c.value ?? '').trim()) {
        filled.set(slug, filled.get(slug)! + 1);
      }
    }
  }
  cache = Object.fromEntries([...filled].map(([slug, n]) => [slug, n / records.length]));
  return cache;
}

/** Cell columns under the threshold, lowest first. */
export function sparseColumns(): string[] {
  return Object.entries(fillRates())
    .filter(([, rate]) => rate < SPARSE_THRESHOLD)
    .sort((a, b) => a[1] - b[1])
    .map(([slug]) => slug);
}
