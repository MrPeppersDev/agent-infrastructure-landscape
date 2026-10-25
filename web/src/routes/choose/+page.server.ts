// /choose — memory-layer chooser. The candidate pools are prepared at
// prerender time as slim ChooserItems (only the cells the chooser reads),
// so the page doesn't ship the full 27 MB dataset.

import { getRecords } from '$lib/data';
import { toItem, POOLS, type StackStatusLite } from '$lib/chooser';
import stackIndex from '../../../../data/stack-index.json';

export const prerender = true;

export const load = () => {
  const pool = new Set(Object.values(POOLS).flat());
  const status = (stackIndex as unknown as { records: Record<string, StackStatusLite> }).records;
  const items = getRecords()
    .filter((r) => pool.has(r.sections.find((s) => s.primary)?.section ?? ''))
    .map((r) => {
      const s = status[r.id];
      return toItem(r, s ? { status: s.status, severity: s.severity, note: s.note } : undefined);
    });
  return { items };
};
