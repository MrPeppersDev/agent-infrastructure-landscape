<script lang="ts">
  import Table from '$lib/components/Table.svelte';
  import SearchBox from '$lib/components/SearchBox.svelte';
  import FilterRail from '$lib/components/FilterRail.svelte';
  import { sortColumns } from '$lib/stores/sort';
  import { searchQuery, applySearch } from '$lib/stores/search';
  import { filters, applyFilters } from '$lib/stores/filters';
  import { sortRecords } from '$lib/sortRecords';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[]; recordCount: number; edgeCount: number } } =
    $props();

  // Reactive pipeline: search → filters → sort.
  // search() and filters() are no-ops until #10 / #11 wire them up.
  const visibleRecords = $derived(
    sortRecords(applyFilters(applySearch(data.records, $searchQuery), $filters), $sortColumns)
  );
</script>

<svelte:head>
  <title>Memory Systems Landscape — Table</title>
</svelte:head>

<div class="app">
  <header class="toolbar">
    <div class="title-block">
      <h1>Memory Systems Landscape</h1>
      <p class="subtitle">
        {data.recordCount.toLocaleString()} systems · {data.edgeCount.toLocaleString()} edges
        · {visibleRecords.length.toLocaleString()} visible
        {#if $sortColumns.length}
          · sorted by {$sortColumns
            .map((s) => `${s.column} ${s.direction === 'asc' ? '↑' : '↓'}`)
            .join(', ')}
        {/if}
      </p>
    </div>
    <div class="hint">
      Click a column header to sort · shift-click to add a secondary sort
    </div>
    <SearchBox matchCount={visibleRecords.length} totalCount={data.recordCount} />
  </header>

  <div class="body">
    <FilterRail records={data.records} />
    <main class="table-shell">
      <Table records={visibleRecords} />
    </main>
  </div>
</div>

<style>
  /* Override the layout's narrow .page padding for the table view so
     the table fills the viewport. The layout still wraps everything in
     a centered .page div but we expand inside it. */
  .app {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 8px 0;
  }
  .toolbar {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }
  h1 {
    font-size: 1.4rem;
    margin: 0;
    letter-spacing: -0.01em;
  }
  .subtitle {
    color: #8b949e;
    font-size: 0.85rem;
    margin: 4px 0 0 0;
    font-variant-numeric: tabular-nums;
  }
  .hint {
    color: #6e7681;
    font-size: 0.8rem;
    font-style: italic;
  }
  .body {
    display: flex;
    flex-direction: row;
    gap: 12px;
    align-items: stretch;
    min-height: 0;
    flex: 1;
  }
  .table-shell {
    flex: 1;
    min-width: 0;
    min-height: 0;
  }
</style>
