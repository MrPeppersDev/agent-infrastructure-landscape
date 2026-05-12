<script lang="ts">
  import type { LandscapeRecord } from '$lib/types';
  import { COLUMNS, taxonomyAxisOf, cellSlugOf } from '$lib/columns';
  import TableCell from './TableCell.svelte';
  import TaxonomyCell from './TaxonomyCell.svelte';
  import { searchQuery, highlightPlain } from '$lib/stores/search';

  let { record }: { record: LandscapeRecord } = $props();

  // Searchable cell slugs — only these get the highlight pass.
  // Matches the haystack set in applySearch(): name + desc + claims.
  const HIGHLIGHT_SLUGS = new Set(['desc', 'claims']);

  const nameHtml = $derived(highlightPlain(record.name, $searchQuery));
</script>

<tr class="row row-t{record.tier}">
  {#each COLUMNS as col (col.key)}
    {#if col.key === 'name'}
      <td class="cell name sticky-col" data-col={col.key}>
        {#if record.url}
          <a href={record.url} target="_blank" rel="noopener noreferrer">{@html nameHtml}</a>
        {:else}
          {@html nameHtml}
        {/if}
      </td>
    {:else if col.key === 'tier'}
      <td class="cell tier" data-col={col.key}>
        <span class="tier-badge t{record.tier}">T{record.tier}</span>
      </td>
    {:else if col.isTaxonomy}
      {@const axis = taxonomyAxisOf(col.key)}
      <td class="cell tax" data-col={col.key} class:trend={col.trend}>
        {#if axis}
          <TaxonomyCell values={record.taxonomy[axis]} />
        {/if}
      </td>
    {:else}
      {@const slug = cellSlugOf(col.key)}
      <td class="cell" data-col={col.key} class:trend={col.trend}>
        {#if slug}
          <TableCell
            cell={record.cells[slug]}
            highlight={HIGHLIGHT_SLUGS.has(slug) ? $searchQuery : ''}
          />
        {/if}
      </td>
    {/if}
  {/each}
</tr>

<style>
  .row {
    height: 56px;
  }
  .cell {
    padding: 8px 12px;
    border-bottom: 1px solid #2a2e34;
    vertical-align: top;
    font-size: 12.5px;
    line-height: 1.5;
    overflow: hidden;
    text-overflow: ellipsis;
    /* Cells render their inner content; we keep cell padding consistent
       and let the table column widths govern layout. */
  }
  .name {
    font-weight: 600;
    background: #18191c;
  }
  .name a {
    color: #d4845f;
    text-decoration: none;
  }
  .name a:hover {
    text-decoration: underline;
  }
  .sticky-col {
    position: sticky;
    left: 0;
    z-index: 2;
  }
  .tier-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.04em;
    line-height: 1.4;
    border: 1px solid;
  }
  .tier-badge.t1 {
    background: #1f3a26;
    color: #8fc99a;
    border-color: #2c5235;
  }
  .tier-badge.t2 {
    background: #1f2e3a;
    color: #8fb3c9;
    border-color: #2c4253;
  }
  .tier-badge.t3 {
    background: #321f3a;
    color: #b58fc9;
    border-color: #492c53;
  }
  .tier-badge.t4 {
    background: #3a2e1f;
    color: #c9a98f;
    border-color: #53432c;
  }
  .tier-badge.t5 {
    background: #2a2a2a;
    color: #999;
    border-color: #3a3a3a;
  }
  .trend {
    /* Subtle accent: a 1-px inset on the left edge so trend columns
       read as a visual stripe down the table. */
    box-shadow: inset 2px 0 0 rgba(196, 99, 60, 0.3);
  }
</style>
