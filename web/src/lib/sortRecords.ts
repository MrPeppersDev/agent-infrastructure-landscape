// Multi-column comparator. Builds a stable comparison function from a
// sortColumns array and applies it to records.
//
// Performance budget (issue #9): full-table sort under 500ms on 523 rows.
// 523 × log₂(523) ≈ 4 700 compare ops; even the most expensive comparator
// (numeric extraction from a free-text cell) clears that budget by 1-2
// orders of magnitude.

import type { LandscapeRecord } from './types';
import type { SortEntry } from './stores/sort';
import { cellSlugOf, taxonomyAxisOf } from './columns';

/**
 * Pull a comparable value out of a record for a given sort column.
 *
 * Returns either a number (for fields where numeric extraction succeeds)
 * or a lowercased string (everything else). Numbers sort before strings —
 * mirrors the lexical convention that empty / unknown sort to the end.
 */
function extractSortValue(record: LandscapeRecord, column: string): number | string {
  if (column === 'name') return record.name.toLowerCase();
  if (column === 'tier') return record.tier;

  const axis = taxonomyAxisOf(column);
  if (axis) {
    const arr = record.taxonomy[axis];
    const primary = arr.find((v) => v.primary) ?? arr[0];
    return primary?.value.toLowerCase() ?? '';
  }

  const slug = cellSlugOf(column);
  if (!slug) return '';
  const cell = record.cells[slug];
  if (!cell) return '';

  // Try numeric extraction for known-numeric fields.
  const numeric = tryNumeric(slug, cell.value);
  if (numeric !== null) return numeric;

  // Fall back to lowercased string.
  return cell.value.toLowerCase();
}

/**
 * Numeric extraction for trend / quantitative columns. Returns null if
 * the field isn't numeric in nature or the cell can't be parsed.
 *
 * The extractors are deliberately forgiving — `54.9k★, +1.6k/mo` should
 * sort by the leading 54900, not by the literal string "54.9k★".
 */
function tryNumeric(slug: string, value: string): number | null {
  if (!value) return null;
  switch (slug) {
    case 'gh': {
      // "54.9k★, +1.6k/mo, Python" → 54_900
      const m = value.match(/([\d.]+)\s*([kKmM]?)\s*★?/);
      if (!m) return null;
      const n = parseFloat(m[1]);
      if (isNaN(n)) return null;
      const mul = m[2].toLowerCase() === 'k' ? 1_000 : m[2].toLowerCase() === 'm' ? 1_000_000 : 1;
      return n * mul;
    }
    case 'created':
    case 'latest-release': {
      // "2023-06" / "openclaw-v1.0.11 (2026-04-29)" → year*12+month
      const m = value.match(/(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?/);
      if (!m) return null;
      const y = parseInt(m[1], 10);
      const mo = parseInt(m[2], 10);
      const d = m[3] ? parseInt(m[3], 10) : 1;
      return y * 10000 + mo * 100 + d;
    }
    case 'funding': {
      // "$24M total ($150M val)" → 24_000_000
      const m = value.match(/\$\s*([\d.]+)\s*([kKmMbB])/);
      if (!m) return null;
      const n = parseFloat(m[1]);
      if (isNaN(n)) return null;
      const mul =
        m[2].toLowerCase() === 'k'
          ? 1_000
          : m[2].toLowerCase() === 'm'
            ? 1_000_000
            : 1_000_000_000;
      return n * mul;
    }
    case 'citations':
    case 'integration-count': {
      const m = value.match(/^(\d+)/);
      if (!m) return null;
      return parseInt(m[1], 10);
    }
    case 'mindshare': {
      // "12 inbound (57 HN, 4 press)" → 12
      const m = value.match(/^(\d+)/);
      if (!m) return null;
      return parseInt(m[1], 10);
    }
    default:
      return null;
  }
}

export function sortRecords(
  records: LandscapeRecord[],
  entries: SortEntry[]
): LandscapeRecord[] {
  if (entries.length === 0) return records;
  const enriched = records.map((r) => ({
    record: r,
    keys: entries.map((e) => extractSortValue(r, e.column))
  }));
  enriched.sort((a, b) => {
    for (let i = 0; i < entries.length; i++) {
      const ka = a.keys[i];
      const kb = b.keys[i];
      const dir = entries[i].direction === 'asc' ? 1 : -1;
      const aEmpty = ka === '' || ka === undefined || ka === null;
      const bEmpty = kb === '' || kb === undefined || kb === null;
      if (aEmpty && bEmpty) continue;
      if (aEmpty) return 1; // empty always last
      if (bEmpty) return -1;
      if (typeof ka === 'number' && typeof kb === 'number') {
        if (ka < kb) return -1 * dir;
        if (ka > kb) return 1 * dir;
        continue;
      }
      // mixed or string-string: coerce to string
      const sa = String(ka);
      const sb = String(kb);
      if (sa < sb) return -1 * dir;
      if (sa > sb) return 1 * dir;
    }
    // Stable tiebreak by id.
    return a.record.id < b.record.id ? -1 : a.record.id > b.record.id ? 1 : 0;
  });
  return enriched.map((e) => e.record);
}
