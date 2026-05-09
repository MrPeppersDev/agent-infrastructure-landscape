<script lang="ts">
  // Virtualised table. Approach:
  //
  // - The outer div is the scroll container; it has a fixed height
  //   (`100vh` minus toolbar height) so vertical scroll is local.
  // - The inner spacer div holds the full virtual height
  //   (`records.length * ROW_HEIGHT`). Only the visible window of rows
  //   is rendered, absolutely-positioned via a transform on a wrapper.
  // - We render the table as a real <table>, with a colgroup driving
  //   widths. The thead is `position: sticky; top: 0` so it stays
  //   visible while the body scrolls vertically.
  // - The first <td> per row is `position: sticky; left: 0` for the
  //   horizontal-scroll case. Header cell #1 is `sticky` on both axes.
  //
  // Why fixed-height rows? Variable height + virtualisation is its own
  // research project; SCHEMA cells aren't bounded in length but we
  // truncate visually with overflow:hidden and the ROW_HEIGHT constant.
  // This keeps the math simple and trivially 60fps.

  import type { LandscapeRecord } from '$lib/types';
  import { COLUMNS, GROUP_RUNS, GROUP_META } from '$lib/columns';
  import { sortColumns, cycleSort, type SortEntry } from '$lib/stores/sort';
  import TableRow from './TableRow.svelte';

  let { records }: { records: LandscapeRecord[] } = $props();

  const ROW_HEIGHT = 56;
  /** Render this many extra rows above & below the viewport so fast
   *  scrolling doesn't show empty space at the edges. */
  const OVERSCAN = 8;

  let scrollContainer: HTMLDivElement;
  let scrollTop = $state(0);
  let viewportHeight = $state(800);

  const totalHeight = $derived(records.length * ROW_HEIGHT);

  const firstVisible = $derived(
    Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN)
  );
  const lastVisible = $derived(
    Math.min(
      records.length,
      Math.ceil((scrollTop + viewportHeight) / ROW_HEIGHT) + OVERSCAN
    )
  );
  const offsetY = $derived(firstVisible * ROW_HEIGHT);
  const visibleSlice = $derived(records.slice(firstVisible, lastVisible));

  function onScroll(e: Event) {
    scrollTop = (e.target as HTMLDivElement).scrollTop;
  }

  function onResize() {
    if (scrollContainer) viewportHeight = scrollContainer.clientHeight;
  }

  $effect(() => {
    if (!scrollContainer) return;
    viewportHeight = scrollContainer.clientHeight;
    const ro = new ResizeObserver(() => onResize());
    ro.observe(scrollContainer);
    return () => ro.disconnect();
  });

  function handleHeaderClick(key: string, ev: MouseEvent) {
    sortColumns.update((cur) => cycleSort(cur, key as SortEntry['column'], ev.shiftKey));
  }

  function sortIndex(entries: SortEntry[], key: string): number {
    return entries.findIndex((e) => e.column === key);
  }
</script>

<div
  class="scroll-container"
  bind:this={scrollContainer}
  onscroll={onScroll}
>
  <div class="virtual-spacer" style="height: {totalHeight}px"></div>

  <table>
    <colgroup>
      {#each COLUMNS as col (col.key)}
        <col style="width: {col.width ?? 120}px" />
      {/each}
    </colgroup>

    <thead>
      <tr class="group-band-row">
        {#each GROUP_RUNS as run}
          {@const meta = GROUP_META[run.group]}
          <th
            colspan={run.span}
            class="group-band group-{run.group}"
            style="background: {meta.bg}; color: {meta.accent};"
          >
            {meta.label}
          </th>
        {/each}
      </tr>
      <tr class="head-row">
        {#each COLUMNS as col, i (col.key)}
          {@const sortIdx = sortIndex($sortColumns, col.key)}
          {@const sortEntry = sortIdx >= 0 ? $sortColumns[sortIdx] : null}
          <th
            class="head-cell"
            class:trend={col.trend}
            class:sticky-corner={i === 0}
            style="background: {GROUP_META[col.group].bg};"
            onclick={(ev) => handleHeaderClick(col.key, ev)}
            title={col.label}
          >
            <span class="head-label">{col.label}</span>
            {#if sortEntry}
              <span class="sort-indicator">
                {sortEntry.direction === 'asc' ? '▲' : '▼'}
                {#if $sortColumns.length > 1}
                  <span class="sort-priority">{sortIdx + 1}</span>
                {/if}
              </span>
            {/if}
          </th>
        {/each}
      </tr>
    </thead>

    <tbody style="transform: translateY({offsetY}px)">
      {#each visibleSlice as record (record.id)}
        <TableRow {record} />
      {/each}
    </tbody>
  </table>
</div>

<style>
  .scroll-container {
    position: relative;
    width: 100%;
    height: calc(100vh - 100px);
    overflow: auto;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
  }
  /* This div fakes the full scroll height. The table's tbody is
     translated to align with the visible window. */
  .virtual-spacer {
    position: absolute;
    top: 0;
    left: 0;
    width: 1px;
    pointer-events: none;
  }
  table {
    border-collapse: separate;
    border-spacing: 0;
    table-layout: fixed;
    width: max-content;
    min-width: 100%;
  }
  thead {
    position: sticky;
    top: 0;
    z-index: 5;
  }
  .group-band-row th {
    padding: 4px 12px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: left;
    border-bottom: 1px solid #30363d;
    white-space: nowrap;
  }
  .head-row th {
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.04em;
    color: #c8c8d4;
    border-bottom: 1px solid #30363d;
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    overflow: hidden;
    text-overflow: ellipsis;
    position: relative;
  }
  .head-row th:hover {
    color: #fff;
  }
  .head-cell.trend {
    box-shadow: inset 2px 0 0 rgba(196, 99, 60, 0.45);
  }
  /* Top-left corner needs to be sticky on both axes so it never
     leaves the viewport. */
  .head-row .sticky-corner,
  .group-band-row th:first-child {
    position: sticky;
    left: 0;
    z-index: 6;
  }
  .head-label {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    vertical-align: middle;
  }
  .sort-indicator {
    display: inline-block;
    margin-left: 4px;
    color: #c4633c;
    font-size: 9px;
    vertical-align: middle;
  }
  .sort-priority {
    display: inline-block;
    margin-left: 2px;
    padding: 0 4px;
    background: #c4633c;
    color: #161b22;
    border-radius: 8px;
    font-size: 9px;
    font-weight: 700;
  }
  tbody {
    /* Translated by the offset to put visible rows at the right place
       inside the virtual scroll. */
    will-change: transform;
  }
  /* Zebra striping for visible rows. We can't use :nth-child for the
     real row index because virtualised rendering breaks the count, so
     we apply a single subtle background to every row and don't try
     to alternate. */

  :global(.row:hover) {
    background: rgba(196, 99, 60, 0.05);
  }
  :global(.row:hover td.name) {
    background: rgba(196, 99, 60, 0.08);
  }
</style>
