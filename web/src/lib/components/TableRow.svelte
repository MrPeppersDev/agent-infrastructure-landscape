<script lang="ts">
  import type { LandscapeRecord } from '$lib/types';
  import { COLUMNS, taxonomyAxisOf, cellSlugOf, type ColumnDef } from '$lib/columns';
  import TableCell from './TableCell.svelte';
  import TaxonomyCell from './TaxonomyCell.svelte';
  import { hasMemoryTaxonomy, primarySectionOf } from '$lib/families';
  import { LIFECYCLE_LABEL, LIFECYCLE_TONE } from '$lib/lifecycle-labels';
  import { corroboration } from '$lib/source-class.js';
  import { searchQuery, highlightPlain } from '$lib/stores/search';

  let { record, columns = COLUMNS }: { record: LandscapeRecord; columns?: ColumnDef[] } = $props();

  const lifecycle = $derived(record.lifecycle ?? 'active');
  const section = $derived(primarySectionOf(record));
  /** Cell text without markup, for the hover title on clipped cells. */
  function plain(html: string | undefined): string {
    return (html ?? '').replace(/<[^>]*>/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/\s+/g, ' ').trim();
  }

  // Searchable cell slugs — only these get the highlight pass.
  // Matches the haystack set in applySearch(): name + desc + claims.
  const HIGHLIGHT_SLUGS = new Set(['desc', 'claims']);

  const nameHtml = $derived(highlightPlain(record.name, $searchQuery));

  // Lifecycle (archived, stale, acquired…) has its own column (#331); the
  // old survivorship stale badge beside the name is retired in its favour.

  // last_verified_at freshness indicator (issue #54 / SCHEMA.md §3b).
  // A tiny dot beside the name keeps visual noise low on the main table
  // while still surfacing rows whose last verification is stale (>= 6
  // months ago). The full date + badge live on the detail modal. Today
  // is pinned in lockstep with the survivorship classifier.
  const FRESHNESS_TODAY = new Date();
  const lvaDot = $derived.by(() => {
    const iso = record.last_verified_at;
    if (!iso) return null;
    const d = new Date(iso + 'T00:00:00Z');
    if (Number.isNaN(d.getTime())) return null;
    const months =
      (FRESHNESS_TODAY.getTime() - d.getTime()) /
      (1000 * 60 * 60 * 24 * 30.4375);
    if (months >= 12) return { tone: 'stale' as const, iso, months };
    if (months >= 6) return { tone: 'aging' as const, iso, months };
    return null;
  });
</script>

<tr class="row row-t{record.tier}">
  {#each columns as col (col.key)}
    {#if col.key === 'name'}
      <td class="cell name sticky-col" data-col={col.key}><div class="clip">
        {#if record.url}
          <a href={record.url} target="_blank" rel="noopener noreferrer">{@html nameHtml}</a>
        {:else}
          {@html nameHtml}
        {/if}
        {#if lvaDot}
          <span
            class="lva-dot {lvaDot.tone}"
            title={`Last verified ${lvaDot.iso} — ${lvaDot.tone === 'stale' ? 'stale (>=12mo)' : 'needs re-audit (>=6mo)'} (SCHEMA.md §3b)`}
            aria-label={`Last verified ${lvaDot.iso}`}
          ></span>
        {/if}
      </div></td>
    {:else if col.key === 'lifecycle'}
      <td class="cell" data-col={col.key}><div class="clip">
        <span class="life {LIFECYCLE_TONE[lifecycle]}" title={`Lifecycle: ${LIFECYCLE_LABEL[lifecycle]} (data/stack-index.json)`}>{LIFECYCLE_LABEL[lifecycle]}</span>
      </div></td>
    {:else if col.key === 'tier'}
      <td class="cell tier" data-col={col.key}><div class="clip">
        <span class="tier-badge t{record.tier}">T{record.tier}</span>
      </div></td>
    {:else if col.key === 'section'}
      <td class="cell" data-col={col.key}><div class="clip" title={section}>{section}</div></td>
    {:else if col.key === 'third-party'}
      {@const c = corroboration(record)}
      <td class="cell" data-col={col.key}><div class="clip" title="{c.thirdParty} of {c.cited} cited facts have a third-party source">{c.thirdParty} / {c.cited}</div></td>
    {:else if col.key === 'verified'}
      <td class="cell" data-col={col.key}><div class="clip">{record.last_verified_at ?? ''}</div></td>
    {:else if col.isTaxonomy}
      {@const axis = taxonomyAxisOf(col.key)}
      <td class="cell tax" data-col={col.key} class:trend={col.trend}><div class="clip">
        {#if !hasMemoryTaxonomy(record)}
          <span class="no-data na" title="Memory taxonomy applies to memory systems only">·</span>
        {:else if axis}
          <TaxonomyCell values={record.taxonomy[axis]} />
        {/if}
      </div></td>
    {:else}
      {@const slug = cellSlugOf(col.key)}
      <td class="cell" data-col={col.key} class:trend={col.trend}><div class="clip" title={slug ? plain(record.cells[slug]?.value) : ''}>
        {#if slug}
          <TableCell
            cell={record.cells[slug]}
            highlight={HIGHLIGHT_SLUGS.has(slug) ? $searchQuery : ''}
          />
        {/if}
      </div></td>
    {/if}
  {/each}
</tr>

<style>
  .row {
    height: var(--row-h, 56px);
  }
  /* Rows are fixed-height so the virtual scroll stays exact: the cell
     content clips to the row (#331). The compact view is one line. */
  .clip {
    max-height: calc(var(--row-h, 56px) - 13px);
    overflow: hidden;
  }
  :global(.compact) .clip {
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  :global(.compact) .clip :global(*) {
    display: inline;
  }
  :global(.compact) .cell {
    padding: 6px 10px;
  }
  .life {
    display: inline-block;
    padding: 0 6px;
    border-radius: 3px;
    font-size: 10.5px;
    font-weight: 600;
    line-height: 1.6;
    border: 1px solid;
    white-space: nowrap;
  }
  .life.ok { background: #1f3a26; color: #8fc99a; border-color: #2c5235; }
  .life.info { background: #1f2e3a; color: #8fb3c9; border-color: #2c4253; }
  .life.warn { background: #3a2e1f; color: #d29922; border-color: #5d4720; }
  .life.bad { background: #3a1f1f; color: #f85149; border-color: #5d2a2a; }
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
  .lva-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-left: 6px;
    border-radius: 50%;
    vertical-align: middle;
    cursor: help;
    border: 1px solid;
  }
  .lva-dot.aging {
    background: #d29922;
    border-color: #5d4720;
  }
  .lva-dot.stale {
    background: #db6d28;
    border-color: #5d3a1f;
  }
  .trend {
    /* Subtle accent: a 1-px inset on the left edge so trend columns
       read as a visual stripe down the table. */
    box-shadow: inset 2px 0 0 rgba(196, 99, 60, 0.3);
  }
</style>
