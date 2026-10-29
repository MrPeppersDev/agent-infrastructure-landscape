// Catalog counts for page copy, derived from the data at build time so
// no template carries a literal number. Server-only (imports the full
// catalog); pages read it through the root layout's `stats`.

import { getRecords, getEdgeCount } from './data';
import { COLUMNS } from './columns';

export interface CatalogStats {
  records: number;
  edges: number;
  sections: number;
  columns: number;
  /** Newest per-record verification date (YYYY-MM-DD). */
  dataAsOf: string;
}

export function catalogStats(): CatalogStats {
  const records = getRecords();
  const sections = new Set(records.flatMap((r) => r.sections.map((s) => s.section)));
  const dataAsOf = records.reduce((m, r) => ((r.last_verified_at ?? '') > m ? (r.last_verified_at ?? '') : m), '');
  return { records: records.length, edges: getEdgeCount(), sections: sections.size, columns: COLUMNS.length, dataAsOf };
}

