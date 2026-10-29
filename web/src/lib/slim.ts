// Server-only: catalog records cut down to the cells a page actually reads,
// so prerendered pages ship a slice instead of the whole catalog (#324).
// Top-level fields (id, name, tier, url, sections, taxonomy,
// last_verified_at) are kept; provenance is dropped.

import { getRecords } from './data';
import type { LandscapeRecord } from './types';

export function slimRecords(cells: readonly string[], opts: { provenance?: boolean } = {}): LandscapeRecord[] {
  return getRecords().map((r) => {
    const { _provenance: prov, cells: all, ...rest } = r as LandscapeRecord & { _provenance?: Record<string, unknown> };
    const kept: Record<string, unknown> = {};
    const keptProv: Record<string, unknown> = {};
    for (const c of cells) {
      const cell = (all as Record<string, unknown>)[c];
      if (cell) kept[c] = cell;
      if (opts.provenance && prov?.[c]) keptProv[c] = prov[c];
    }
    return { ...rest, cells: kept, ...(opts.provenance ? { _provenance: keptProv } : {}) } as LandscapeRecord;
  });
}
