<script lang="ts">
  // Toolbar "Export ▾" dropdown. Issue #19.
  //
  // Format menu: CSV, JSON. Both export the *visible* records (post-search,
  // post-filter, post-sort) — the parent passes the already-pipelined array.
  // We don't expose a column-subset picker yet (the issue lists it as
  // acceptance but flagged optional in the build brief); for now CSV ships
  // a fixed superset of identity+taxonomy+all 60 cell slugs, JSON ships
  // the full structured shape.

  import { onMount } from 'svelte';
  import type { LandscapeRecord } from '$lib/types';
  import { toCSV, toJSON, buildFilename, downloadFile } from '$lib/export';

  let {
    records,
    filterSummary
  }: { records: LandscapeRecord[]; filterSummary: string } = $props();

  let open = $state(false);
  let menuEl: HTMLDivElement | null = $state(null);

  function toggle() {
    open = !open;
  }

  function exportCSV() {
    const filename = buildFilename('csv', filterSummary);
    downloadFile(filename, toCSV(records), 'text/csv;charset=utf-8');
    open = false;
  }

  function exportJSON() {
    const filename = buildFilename('json', filterSummary);
    downloadFile(filename, toJSON(records), 'application/json;charset=utf-8');
    open = false;
  }

  // Close on outside click / Esc.
  onMount(() => {
    function onClick(e: MouseEvent) {
      if (!open) return;
      if (menuEl && !menuEl.contains(e.target as Node)) {
        open = false;
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && open) open = false;
    }
    window.addEventListener('click', onClick);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('click', onClick);
      window.removeEventListener('keydown', onKey);
    };
  });
</script>

<div class="export-wrap" bind:this={menuEl}>
  <button
    type="button"
    class="export-btn"
    onclick={toggle}
    aria-haspopup="menu"
    aria-expanded={open}
    title="Export visible records"
  >
    Export ▾
  </button>
  {#if open}
    <div class="menu" role="menu">
      <div class="menu-header">
        {records.length.toLocaleString()} records · post-filter / post-sort
      </div>
      <button type="button" role="menuitem" class="menu-item" onclick={exportCSV}>
        <span class="menu-label">Download CSV</span>
        <span class="menu-hint">flattened, RFC 4180</span>
      </button>
      <button type="button" role="menuitem" class="menu-item" onclick={exportJSON}>
        <span class="menu-label">Download JSON</span>
        <span class="menu-hint">full structured shape</span>
      </button>
    </div>
  {/if}
</div>

<style>
  .export-wrap {
    position: relative;
    display: inline-block;
  }
  .export-btn {
    padding: 6px 12px;
    font: inherit;
    font-size: 0.85rem;
    color: #c9d1d9;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    cursor: pointer;
    line-height: 1.4;
  }
  .export-btn:hover {
    color: #f0f6fc;
    border-color: #58a6ff;
  }
  .menu {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    min-width: 220px;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    z-index: 100;
    padding: 4px;
  }
  .menu-header {
    padding: 6px 10px;
    font-size: 0.72rem;
    color: #6e7681;
    border-bottom: 1px solid #21262d;
    margin-bottom: 4px;
    font-variant-numeric: tabular-nums;
  }
  .menu-item {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    width: 100%;
    padding: 7px 10px;
    background: transparent;
    border: none;
    text-align: left;
    cursor: pointer;
    border-radius: 4px;
    color: #c9d1d9;
    font: inherit;
    font-size: 0.85rem;
  }
  .menu-item:hover {
    background: #161b22;
    color: #f0f6fc;
  }
  .menu-label {
    font-weight: 500;
  }
  .menu-hint {
    color: #6e7681;
    font-size: 0.72rem;
    margin-top: 2px;
  }
</style>
