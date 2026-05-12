<script lang="ts">
  // Toolbar "Export ▾" dropdown. Issue #19.
  //
  // Format menu: CSV, JSON. Both export the *visible* records (post-search,
  // post-filter, post-sort) — the parent passes the already-pipelined array.
  //
  // Column-subset picker: opens a sub-popover with grouped checkboxes built
  // from COLUMNS / GROUP_RUNS in $lib/columns. Defaults to all columns
  // checked. Quick-selects: All, None, Identity only, Identity + claims + perf.
  // Threaded through to toCSV / toJSON via the optional `columns` param —
  // see export.ts for the encoding.
  //
  // UX choice: column-picker is on the same popover (not a separate modal)
  // so the user can preview "X columns selected" without losing the export
  // affordance. Closing the popover discards the selection.

  import { onMount } from 'svelte';
  import type { LandscapeRecord } from '$lib/types';
  import { toCSV, toJSON, buildFilename, downloadFile } from '$lib/export';
  import { COLUMNS, GROUP_META, type ColumnGroup } from '$lib/columns';

  let {
    records,
    filterSummary
  }: { records: LandscapeRecord[]; filterSummary: string } = $props();

  let open = $state(false);
  let menuEl: HTMLDivElement | null = $state(null);
  let pickerOpen = $state(false);

  // --- Column picker state ---------------------------------------------
  //
  // We mirror the column list in $lib/columns. Every column key in COLUMNS
  // is available for export. Identity-only columns (id, url, sections,
  // primary_section) are added as virtual entries — the table doesn't show
  // them as columns but the export format includes them.
  //
  // Identity-only export keys (id, url, primary_section, sections) live
  // outside the visible-column list because they're synthesized fields,
  // not screen columns. We expose them in the "Identity" group so users
  // can pick id/url specifically for cross-references.

  const IDENTITY_EXTRA_KEYS = [
    { key: 'id', label: 'Record id' },
    { key: 'url', label: 'Project URL' },
    { key: 'primary_section', label: 'Primary section' },
    { key: 'sections', label: 'All sections' }
  ] as const;

  /** All exportable column keys. Order matches the CSV column order in
   *  export.ts when no override is passed — identity extras first, then
   *  the visible table columns in their display order. */
  const ALL_EXPORT_KEYS: string[] = [
    ...IDENTITY_EXTRA_KEYS.map((c) => c.key),
    ...COLUMNS.map((c) => c.key)
  ];

  type PickerEntry = { key: string; label: string; group: ColumnGroup };

  /** Grouped list for rendering. Identity-extras land in the "identity"
   *  group ahead of the visible-column entries. */
  const GROUPED_ENTRIES: { group: ColumnGroup; label: string; entries: PickerEntry[] }[] = (() => {
    const byGroup = new Map<ColumnGroup, PickerEntry[]>();
    function push(g: ColumnGroup, e: PickerEntry) {
      const arr = byGroup.get(g) ?? [];
      arr.push(e);
      byGroup.set(g, arr);
    }
    for (const x of IDENTITY_EXTRA_KEYS) {
      push('identity', { key: x.key, label: x.label, group: 'identity' });
    }
    for (const c of COLUMNS) {
      push(c.group, { key: c.key, label: c.label, group: c.group });
    }
    const out: { group: ColumnGroup; label: string; entries: PickerEntry[] }[] = [];
    for (const [g, entries] of byGroup) {
      out.push({ group: g, label: GROUP_META[g].label, entries });
    }
    return out;
  })();

  // Selected set; reactive so checkbox state updates live.
  let selected = $state<Set<string>>(new Set(ALL_EXPORT_KEYS));

  const selectedCount = $derived(selected.size);
  const totalCount = ALL_EXPORT_KEYS.length;

  function toggle() {
    open = !open;
    if (!open) pickerOpen = false;
  }

  function togglePicker() {
    pickerOpen = !pickerOpen;
  }

  function toggleColumn(key: string) {
    const next = new Set(selected);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    selected = next;
  }

  function selectAll() {
    selected = new Set(ALL_EXPORT_KEYS);
  }
  function selectNone() {
    selected = new Set();
  }
  function selectIdentityOnly() {
    selected = new Set(['id', 'name', 'tier', 'url', 'primary_section']);
  }
  function selectIdentityClaimsPerf() {
    selected = new Set([
      'id', 'name', 'tier', 'url', 'primary_section',
      'type', 'desc', 'claims',
      'perf', 'latency', 'throughput', 'volume', 'repro'
    ]);
  }

  function exportCSV() {
    const cols = [...selected];
    const filename = buildFilename('csv', filterSummary);
    downloadFile(filename, toCSV(records, cols), 'text/csv;charset=utf-8');
    open = false;
    pickerOpen = false;
  }

  function exportJSON() {
    const cols = [...selected];
    const filename = buildFilename('json', filterSummary);
    downloadFile(filename, toJSON(records, cols), 'application/json;charset=utf-8');
    open = false;
    pickerOpen = false;
  }

  // Close on outside click / Esc.
  onMount(() => {
    function onClick(e: MouseEvent) {
      if (!open) return;
      if (menuEl && !menuEl.contains(e.target as Node)) {
        open = false;
        pickerOpen = false;
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && open) {
        if (pickerOpen) pickerOpen = false;
        else open = false;
      }
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
        {records.length.toLocaleString()} records · {selectedCount}/{totalCount} columns
      </div>
      <button
        type="button"
        class="menu-item picker-toggle"
        onclick={togglePicker}
        aria-expanded={pickerOpen}
      >
        <span class="menu-label">Columns…</span>
        <span class="menu-hint">
          {selectedCount === totalCount
            ? 'all columns'
            : `${selectedCount} selected`} {pickerOpen ? '▴' : '▾'}
        </span>
      </button>
      {#if pickerOpen}
        <div class="picker" role="group" aria-label="Columns to export">
          <div class="picker-quick">
            <button type="button" class="quick-btn" onclick={selectAll}>All</button>
            <button type="button" class="quick-btn" onclick={selectNone}>None</button>
            <button type="button" class="quick-btn" onclick={selectIdentityOnly}>
              Identity only
            </button>
            <button
              type="button"
              class="quick-btn"
              onclick={selectIdentityClaimsPerf}
              title="Identity + claims + performance"
            >
              Identity + claims + perf
            </button>
          </div>
          <div class="picker-body">
            {#each GROUPED_ENTRIES as group (group.group)}
              <details class="picker-group" open>
                <summary>
                  <span
                    class="group-swatch"
                    style="background: {GROUP_META[group.group].accent}"
                  ></span>
                  <span class="group-name">{group.label}</span>
                  <span class="group-count">
                    {group.entries.filter((e) => selected.has(e.key)).length}/{group.entries.length}
                  </span>
                </summary>
                <ul>
                  {#each group.entries as entry (entry.key)}
                    <li>
                      <label>
                        <input
                          type="checkbox"
                          checked={selected.has(entry.key)}
                          onchange={() => toggleColumn(entry.key)}
                        />
                        <span class="entry-label">{entry.label}</span>
                      </label>
                    </li>
                  {/each}
                </ul>
              </details>
            {/each}
          </div>
        </div>
      {/if}
      <button
        type="button"
        role="menuitem"
        class="menu-item"
        onclick={exportCSV}
        disabled={selectedCount === 0}
      >
        <span class="menu-label">Download CSV</span>
        <span class="menu-hint">flattened, RFC 4180</span>
      </button>
      <button
        type="button"
        role="menuitem"
        class="menu-item"
        onclick={exportJSON}
        disabled={selectedCount === 0}
      >
        <span class="menu-label">Download JSON</span>
        <span class="menu-hint">structured shape, pruned</span>
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
    min-width: 280px;
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
  .menu-item:hover:not(:disabled) {
    background: #161b22;
    color: #f0f6fc;
  }
  .menu-item:disabled {
    cursor: not-allowed;
    opacity: 0.45;
  }
  .menu-item.picker-toggle {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
  .menu-label {
    font-weight: 500;
  }
  .menu-hint {
    color: #6e7681;
    font-size: 0.72rem;
    margin-top: 2px;
  }
  .picker {
    border: 1px solid #21262d;
    border-radius: 4px;
    margin: 4px 4px 6px 4px;
    background: #0a0d12;
    overflow: hidden;
  }
  .picker-quick {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 6px;
    border-bottom: 1px solid #21262d;
  }
  .quick-btn {
    flex: 1 0 auto;
    padding: 3px 8px;
    font: inherit;
    font-size: 0.72rem;
    color: #58a6ff;
    background: transparent;
    border: 1px solid #30363d;
    border-radius: 4px;
    cursor: pointer;
    white-space: nowrap;
  }
  .quick-btn:hover {
    border-color: #58a6ff;
    background: rgba(88, 166, 255, 0.08);
  }
  .picker-body {
    max-height: 320px;
    overflow-y: auto;
    padding: 2px;
  }
  .picker-group {
    border-bottom: 1px solid #161b22;
  }
  .picker-group:last-child {
    border-bottom: none;
  }
  .picker-group > summary {
    list-style: none;
    cursor: pointer;
    padding: 5px 6px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #c9d1d9;
    user-select: none;
  }
  .picker-group > summary::-webkit-details-marker {
    display: none;
  }
  .picker-group > summary::after {
    content: '▸';
    color: #6e7681;
    font-size: 0.65rem;
    margin-left: auto;
    transition: transform 100ms ease;
  }
  .picker-group[open] > summary::after {
    transform: rotate(90deg);
  }
  .group-swatch {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .group-name {
    flex: 0 1 auto;
  }
  .group-count {
    color: #6e7681;
    font-size: 0.7rem;
    font-variant-numeric: tabular-nums;
    margin-right: 4px;
  }
  ul {
    list-style: none;
    padding: 2px 6px 8px 22px;
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
    border-radius: 3px;
    cursor: pointer;
    line-height: 1.3;
    font-size: 0.78rem;
  }
  label:hover {
    background: rgba(88, 166, 255, 0.06);
  }
  input[type='checkbox'] {
    accent-color: #58a6ff;
    margin: 0;
    flex-shrink: 0;
  }
  .entry-label {
    color: #c9d1d9;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
