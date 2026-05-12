// Faceted filter state. The shape is a Set per facet — every selected
// value within a facet is OR'd, and the facets themselves are AND'd. An
// empty Set means "this facet imposes no constraint".
//
// Issue #12 (URL sync) reads/writes this same store; the contract it
// depends on is:
//   - `filters` is a writable<FilterState>
//   - every facet name in FacetName is a property on FilterState
//   - each property is a Set (so url-encoding is "name=a,b,c")
//
// Mutating Sets inside a Svelte store requires re-assigning the object
// to trigger reactivity. The recommended pattern is:
//   filters.update(s => { s.tier.add(1); return s; });
// which works because `update` always notifies, even if the object
// identity is unchanged.
//
// Facet semantics:
//   tier          → numeric record.tier (1..5)
//   section       → record.sections.find(s => s.primary).section
//   {storage…conflict}  → record.taxonomy[axis].find(v => v.primary).value
//   license / deployment / modality → canonicalised bucket of
//     record.cells.{license|deployment|modalities}.value
//
// Canonicalisation: see docs/DECISIONS.md (2026-05-07 entry). Anything
// that isn't real-data becomes the bucket "NA"; anything that fails all
// keyword tests becomes "other".
//
// Counts ("Apache-2.0 (47)") are computed by `facetCounts`, which excludes
// the current facet from the predicate when counting — so a user toggling
// values inside tier still sees the other tiers' record counts, which is
// how every faceted-search UI behaves.

import { writable } from 'svelte/store';
import type { LandscapeRecord, Tier } from '$lib/types';

export type TaxonomyFacet =
  | 'storage'
  | 'retrieval'
  | 'persistence'
  | 'update'
  | 'unit'
  | 'governance'
  | 'conflict';

export type CellFacet = 'license' | 'deployment' | 'modality';

export type FacetName =
  | 'tier'
  | 'section'
  | TaxonomyFacet
  | CellFacet;

export interface FilterState {
  tier: Set<number>;
  section: Set<string>;
  storage: Set<string>;
  retrieval: Set<string>;
  persistence: Set<string>;
  update: Set<string>;
  unit: Set<string>;
  governance: Set<string>;
  conflict: Set<string>;
  license: Set<string>;
  deployment: Set<string>;
  modality: Set<string>;
}

export const TAXONOMY_FACETS: TaxonomyFacet[] = [
  'storage',
  'retrieval',
  'persistence',
  'update',
  'unit',
  'governance',
  'conflict'
];

export const FACET_ORDER: FacetName[] = [
  'tier',
  'section',
  ...TAXONOMY_FACETS,
  'license',
  'deployment',
  'modality'
];

export const FACET_LABEL: Record<FacetName, string> = {
  tier: 'Tier',
  section: 'Section',
  storage: 'Storage',
  retrieval: 'Retrieval',
  persistence: 'Persistence',
  update: 'Update',
  unit: 'Unit',
  governance: 'Governance',
  conflict: 'Conflict',
  license: 'License',
  deployment: 'Deployment',
  modality: 'Modality'
};

export function emptyState(): FilterState {
  return {
    tier: new Set<number>(),
    section: new Set<string>(),
    storage: new Set<string>(),
    retrieval: new Set<string>(),
    persistence: new Set<string>(),
    update: new Set<string>(),
    unit: new Set<string>(),
    governance: new Set<string>(),
    conflict: new Set<string>(),
    license: new Set<string>(),
    deployment: new Set<string>(),
    modality: new Set<string>()
  };
}

export const filters = writable<FilterState>(emptyState());

export function isEmpty(state: FilterState): boolean {
  for (const facet of FACET_ORDER) {
    if (state[facet].size > 0) return false;
  }
  return true;
}

// --- Canonicalisation maps ---------------------------------------------
//
// All three live here so the URL-sync layer (#12) can serialise the same
// buckets the UI displays. Keep them in sync with docs/DECISIONS.md.

export function canonicaliseLicense(raw: string, status: string): string {
  if (status !== 'real-data') return 'NA';
  const v = raw.toLowerCase();
  if (v.includes('apache')) return 'Apache-2.0';
  if (v.includes('agpl')) return 'AGPL';
  if (v.includes('gpl')) return 'GPL';
  if (v.includes('mit')) return 'MIT';
  if (v.includes('bsd')) return 'BSD';
  if (v.includes('proprietary') || v.includes('closed')) return 'proprietary';
  if (
    v.includes('research') ||
    v.includes('noncommercial') ||
    v.includes('non-commercial') ||
    v.includes('nc 4.0') ||
    v.includes('cc-by-nc')
  ) {
    return 'research-license';
  }
  return 'other';
}

export function canonicaliseDeployment(raw: string, status: string): string {
  if (status !== 'real-data') return 'NA';
  const v = raw.toLowerCase();
  if (v.includes('self-host') || v.includes('self host') || v.includes('on-prem') || v.includes('on prem')) {
    return 'self-hosted';
  }
  if (v.includes('saas') || v.includes('managed') || v.includes('hosted')) return 'saas';
  if (v.includes('cloud')) return 'cloud';
  if (v.includes('library') || v.includes('embedded') || v.includes('sdk')) return 'library';
  if (v.includes('cli') || v.includes('desktop') || v.includes('local')) return 'local';
  return 'other';
}

export function canonicaliseModality(raw: string, status: string): string {
  if (status !== 'real-data') return 'NA';
  const v = raw.toLowerCase();
  // Multi-modal records will fall into whichever bucket they mention
  // first; the cell is a free-text list so a record can match more than
  // one bucket. For simplicity we return the first hit and let the
  // record show up under that facet only.
  if (v.includes('multimodal') || v.includes('multi-modal')) return 'multimodal';
  if (v.includes('text')) return 'text';
  if (v.includes('vision') || v.includes('image')) return 'vision';
  if (v.includes('audio') || v.includes('speech')) return 'audio';
  if (v.includes('video')) return 'video';
  if (v.includes('code')) return 'code';
  if (v.includes('embedding') || v.includes('vector')) return 'embeddings';
  return 'other';
}

// --- Facet value extraction --------------------------------------------

function primarySection(r: LandscapeRecord): string {
  const primary = r.sections.find((s) => s.primary);
  return primary?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

function primaryTaxonomy(r: LandscapeRecord, axis: TaxonomyFacet): string {
  const values = r.taxonomy[axis] ?? [];
  const primary = values.find((v) => v.primary);
  return primary?.value ?? values[0]?.value ?? 'unspecified';
}

/**
 * Returns the bucket value for a single facet on a single record. For
 * facets where a record naturally has only one value (tier, section,
 * taxonomy primaries, canonicalised cells) we just return that value.
 */
export function recordFacetValue(
  r: LandscapeRecord,
  facet: FacetName
): string | number {
  if (facet === 'tier') return r.tier;
  if (facet === 'section') return primarySection(r);
  if (facet === 'license') {
    const cell = r.cells.license;
    return canonicaliseLicense(cell?.value ?? '', cell?.status ?? 'no-data');
  }
  if (facet === 'deployment') {
    const cell = r.cells.deployment;
    return canonicaliseDeployment(cell?.value ?? '', cell?.status ?? 'no-data');
  }
  if (facet === 'modality') {
    const cell = r.cells.modalities;
    return canonicaliseModality(cell?.value ?? '', cell?.status ?? 'no-data');
  }
  return primaryTaxonomy(r, facet as TaxonomyFacet);
}

// --- Predicates --------------------------------------------------------

function passesFacet(
  r: LandscapeRecord,
  facet: FacetName,
  state: FilterState
): boolean {
  const selected = state[facet];
  if (selected.size === 0) return true;
  const value = recordFacetValue(r, facet);
  // Sets are typed Set<string> | Set<number>; `.has` with the union value
  // is safe because tier is the only numeric facet.
  return (selected as Set<string | number>).has(value);
}

/**
 * AND across facets, OR within. Returns the input array unchanged if no
 * facet is active (cheap fast-path so we don't allocate on every keystroke
 * from the search box).
 */
export function applyFilters(
  records: LandscapeRecord[],
  state: FilterState
): LandscapeRecord[] {
  if (isEmpty(state)) return records;
  return records.filter((r) =>
    FACET_ORDER.every((facet) => passesFacet(r, facet, state))
  );
}

/**
 * Count records per value of `facet`, applying every *other* facet's
 * filter but not this one. That's the standard faceted-search behaviour:
 * inside a facet, you see the counts you'd get if you toggled that
 * particular value on, not the counts post-toggle.
 *
 * Returns a Map keyed by the bucket value, with insertion order matching
 * descending count then alphabetical — callers can iterate directly.
 */
export function facetCounts(
  records: LandscapeRecord[],
  facet: FacetName,
  state: FilterState
): Map<string | number, number> {
  // Predicate that ignores the queried facet.
  const otherFacets = FACET_ORDER.filter((f) => f !== facet);
  const passesOthers = (r: LandscapeRecord) =>
    otherFacets.every((f) => passesFacet(r, f, state));

  const counts = new Map<string | number, number>();
  for (const r of records) {
    if (!passesOthers(r)) continue;
    const v = recordFacetValue(r, facet);
    counts.set(v, (counts.get(v) ?? 0) + 1);
  }

  // Sort: numeric (tier) ascending; everything else by count desc then alpha.
  const entries = [...counts.entries()];
  if (facet === 'tier') {
    entries.sort((a, b) => (a[0] as number) - (b[0] as number));
  } else {
    entries.sort((a, b) => {
      if (b[1] !== a[1]) return b[1] - a[1];
      return String(a[0]).localeCompare(String(b[0]));
    });
  }
  return new Map(entries);
}

/**
 * Used by the rail's "Clear filters" button. Lives here (rather than in
 * the component) so #12's URL sync can wipe state via the same entry
 * point without re-implementing the empty-state shape.
 */
export function clearFilters(): void {
  filters.set(emptyState());
}

/**
 * Toggle a single value in a facet's Set. Re-assigns inside `update` so
 * Svelte sees the change (Sets don't have a deep-equality check).
 */
export function toggleFacetValue(facet: FacetName, value: string | number): void {
  filters.update((s) => {
    // Cast narrows the union to a single Set type per branch — TS can't
    // prove that `facet` and `value` types match without the assertion.
    const set = s[facet] as Set<string | number>;
    if (set.has(value)) set.delete(value);
    else set.add(value);
    return s;
  });
}

export function clearFacet(facet: FacetName): void {
  filters.update((s) => {
    (s[facet] as Set<string | number>).clear();
    return s;
  });
}

// Re-export Tier for any consumer importing FilterState — keeps the
// import surface tidy for #12.
export type { Tier };
