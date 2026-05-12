<script lang="ts">
  // Sticky left rail with one <details> per facet. Counts live-update
  // because they're recomputed via $derived from $filters + records.
  //
  // We render checkboxes (rather than chips) because the facets are
  // mutually-non-exclusive lists and "click to toggle" is the obvious
  // affordance. Counts are computed with the *other* facets applied —
  // see facetCounts() in the store.

  import {
    filters,
    facetCounts,
    toggleFacetValue,
    clearFacet,
    clearFilters,
    isEmpty,
    FACET_ORDER,
    FACET_LABEL,
    type FacetName
  } from '$lib/stores/filters';
  import type { LandscapeRecord } from '$lib/types';

  let { records }: { records: LandscapeRecord[] } = $props();

  // One counts map per facet. Recomputed when either records or filter
  // state changes — cheap (linear in records, constant in facets).
  const allCounts = $derived(
    new Map<FacetName, Map<string | number, number>>(
      FACET_ORDER.map((f) => [f, facetCounts(records, f, $filters)])
    )
  );

  const anyActive = $derived(!isEmpty($filters));

  // Sections expanded by default for the most-useful facets; the rest
  // start collapsed so the rail isn't a wall of text on first load.
  const DEFAULT_OPEN: ReadonlySet<FacetName> = new Set(['tier', 'section']);

  function isChecked(facet: FacetName, value: string | number): boolean {
    return ($filters[facet] as Set<string | number>).has(value);
  }
</script>

<aside class="rail" aria-label="Filters">
  <div class="rail-header">
    <h2>Filters</h2>
    {#if anyActive}
      <button type="button" class="clear-all" onclick={clearFilters}>
        Clear all
      </button>
    {/if}
  </div>

  {#each FACET_ORDER as facet (facet)}
    {@const counts = allCounts.get(facet) ?? new Map()}
    {@const selectedCount = $filters[facet].size}
    {@const isOpen = DEFAULT_OPEN.has(facet) || selectedCount > 0}
    <details class="facet" open={isOpen}>
      <summary>
        <span class="facet-name">{FACET_LABEL[facet]}</span>
        {#if selectedCount > 0}
          <span class="facet-badge">{selectedCount}</span>
        {/if}
      </summary>
      <div class="facet-body">
        {#if selectedCount > 0}
          <button
            type="button"
            class="clear-facet"
            onclick={() => clearFacet(facet)}
          >
            Clear {FACET_LABEL[facet].toLowerCase()}
          </button>
        {/if}
        {#if counts.size === 0}
          <p class="empty">No values.</p>
        {:else}
          <ul>
            {#each [...counts.entries()] as [value, count] (value)}
              <li>
                <label class:active={isChecked(facet, value)}>
                  <input
                    type="checkbox"
                    checked={isChecked(facet, value)}
                    onchange={() => toggleFacetValue(facet, value)}
                  />
                  <span class="value-label" title={String(value)}>{value}</span>
                  <span class="value-count">{count}</span>
                </label>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </details>
  {/each}
</aside>

<style>
  .rail {
    width: 260px;
    flex: 0 0 260px;
    align-self: flex-start;
    position: sticky;
    top: 8px;
    max-height: calc(100vh - 16px);
    overflow-y: auto;
    padding: 8px 10px;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    font-size: 0.85rem;
    color: #c9d1d9;
  }
  .rail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 2px 8px 2px;
    border-bottom: 1px solid #21262d;
    margin-bottom: 6px;
  }
  .rail-header h2 {
    margin: 0;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #8b949e;
  }
  .clear-all {
    background: none;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 2px 8px;
    color: #58a6ff;
    font: inherit;
    font-size: 0.75rem;
    cursor: pointer;
  }
  .clear-all:hover {
    border-color: #58a6ff;
    background: rgba(88, 166, 255, 0.08);
  }
  .facet {
    border-bottom: 1px solid #161b22;
  }
  .facet:last-child {
    border-bottom: none;
  }
  .facet > summary {
    list-style: none;
    cursor: pointer;
    user-select: none;
    padding: 6px 2px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    color: #c9d1d9;
  }
  .facet > summary::-webkit-details-marker {
    display: none;
  }
  .facet > summary::before {
    content: '▸';
    color: #6e7681;
    font-size: 0.7rem;
    transition: transform 100ms ease;
    display: inline-block;
    width: 10px;
  }
  .facet[open] > summary::before {
    transform: rotate(90deg);
  }
  .facet-name {
    flex: 1;
  }
  .facet-badge {
    background: rgba(88, 166, 255, 0.18);
    color: #58a6ff;
    font-size: 0.7rem;
    padding: 1px 6px;
    border-radius: 10px;
    font-weight: 600;
  }
  .facet-body {
    padding: 2px 4px 8px 18px;
  }
  .clear-facet {
    background: none;
    border: none;
    padding: 0 0 4px 0;
    color: #58a6ff;
    font: inherit;
    font-size: 0.75rem;
    cursor: pointer;
    text-decoration: underline;
  }
  ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  li {
    margin: 0;
  }
  label {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 4px;
    border-radius: 4px;
    cursor: pointer;
    line-height: 1.3;
  }
  label:hover {
    background: rgba(88, 166, 255, 0.06);
  }
  label.active {
    color: #e6edf3;
  }
  input[type='checkbox'] {
    accent-color: #58a6ff;
    margin: 0;
    flex-shrink: 0;
  }
  .value-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 0.82rem;
  }
  .value-count {
    color: #6e7681;
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
  }
  .empty {
    color: #6e7681;
    font-size: 0.75rem;
    font-style: italic;
    margin: 0;
  }
</style>
