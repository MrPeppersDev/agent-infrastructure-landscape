<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  import Table from '$lib/components/Table.svelte';
  import SearchBox from '$lib/components/SearchBox.svelte';
  import FilterRail from '$lib/components/FilterRail.svelte';
  import { sortColumns } from '$lib/stores/sort';
  import { searchQuery, applySearch } from '$lib/stores/search';
  import { filters, applyFilters } from '$lib/stores/filters';
  import { sortRecords } from '$lib/sortRecords';
  import {
    stateToUrl,
    urlToState,
    filterStateEqual,
    sortEntriesEqual
  } from '$lib/url-state';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[]; recordCount: number; edgeCount: number } } =
    $props();

  // --- URL → stores (synchronous, runs before first reactive render) ---
  //
  // The site is prerendered (adapter-static), so +page.ts load() can't read
  // query params — they don't exist at build time. We parse window.location
  // here, synchronously at module-script init time, so the three stores are
  // populated BEFORE any $derived reads them. That eliminates the
  // flash-of-default-view on paste-into-new-tab.
  //
  // Guard with `browser` because this script runs during SSR prerender too
  // (where `window` is undefined).
  if (browser) {
    const initial = urlToState(new URLSearchParams(window.location.search));
    // .set() rather than .update() — we want full replacement, including
    // wiping any value left over from a prior client-side navigation.
    if (initial.search) searchQuery.set(initial.search);
    filters.set(initial.filters);
    sortColumns.set(initial.sort);
  }

  // Reactive pipeline: search → filters → sort.
  const visibleRecords = $derived(
    sortRecords(applyFilters(applySearch(data.records, $searchQuery), $filters), $sortColumns)
  );

  // --- Stores → URL (debounced, replaceState) --------------------------
  //
  // Why debounce: every keystroke in the search box updates $searchQuery,
  // and every click in the filter rail mutates $filters. Without a debounce
  // we'd call goto() 50× during a fast typing burst — each one a no-op for
  // history (replaceState) but still a router operation. 150ms matches the
  // search debounce in #10 and feels instant.
  //
  // Why goto + replaceState rather than history.replaceState directly:
  // - keeps SvelteKit's $page store in sync (so any future code reading
  //   $page.url.searchParams gets the current view)
  // - works with the framework's transition / preload machinery
  // - noScroll: true + keepFocus: true preserves user position
  // - replaceState: true means the back button doesn't fill up with every
  //   filter toggle (it would be unusable otherwise)
  //
  // We track previous serialised state with the equality helpers so we
  // never call goto() when the URL would be identical — saves a router
  // round-trip on store-set-but-no-real-change.

  let lastSearch = $state('');
  let writeTimer: ReturnType<typeof setTimeout> | null = null;

  function writeUrl(search: string, f: typeof $filters, s: typeof $sortColumns) {
    const params = stateToUrl(search, f, s);
    const qs = params.toString();
    const target = qs ? `?${qs}` : window.location.pathname;
    if (window.location.search === (qs ? `?${qs}` : '')) return;
    goto(target, {
      replaceState: true,
      noScroll: true,
      keepFocus: true
    });
  }

  // Snapshot last-written state so $effect can detect real changes and
  // skip writing when only object identity changed (Set mutations under
  // filters.update() preserve identity but re-notify the store).
  let lastFilters: typeof $filters | null = null;
  let lastSort: typeof $sortColumns | null = null;

  $effect(() => {
    if (!browser) return;
    // Subscribe to the three stores.
    const s = $searchQuery;
    const f = $filters;
    const so = $sortColumns;
    untrack(() => {
      if (
        s === lastSearch &&
        lastFilters !== null &&
        filterStateEqual(f, lastFilters) &&
        lastSort !== null &&
        sortEntriesEqual(so, lastSort)
      ) {
        return;
      }
      lastSearch = s;
      // Clone the filter state so subsequent in-place mutations don't
      // make our snapshot equal-to-current and skip a real write.
      lastFilters = cloneFilterState(f);
      lastSort = [...so];

      if (writeTimer !== null) clearTimeout(writeTimer);
      writeTimer = setTimeout(() => {
        writeUrl(s, f, so);
        writeTimer = null;
      }, 150);
    });
  });

  function cloneFilterState(f: typeof $filters): typeof $filters {
    return {
      tier: new Set(f.tier),
      section: new Set(f.section),
      storage: new Set(f.storage),
      retrieval: new Set(f.retrieval),
      persistence: new Set(f.persistence),
      update: new Set(f.update),
      unit: new Set(f.unit),
      governance: new Set(f.governance),
      conflict: new Set(f.conflict),
      license: new Set(f.license),
      deployment: new Set(f.deployment),
      modality: new Set(f.modality)
    };
  }

  // Handle back/forward navigation: re-parse the URL and push it into the
  // stores. Without this, browser back after a filter change leaves the
  // stores stale (the URL changes but the view doesn't).
  onMount(() => {
    const onPop = () => {
      const next = urlToState(new URLSearchParams(window.location.search));
      searchQuery.set(next.search);
      filters.set(next.filters);
      sortColumns.set(next.sort);
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  });
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
