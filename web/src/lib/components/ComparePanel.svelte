<script lang="ts">
  // Side-by-side compare panel for 2-4 selected records. Lays out as a
  // table-like grid: leftmost column is the field label, then one column
  // per record. Each row is one field. Differences are highlighted with
  // a soft accent border on the cell. Issue #18.
  //
  // We use a CSS grid (rather than a real <table>) because we want each
  // record card to have its own header (name + tier + section + remove
  // button) that spans only that column — easier with `display: grid`
  // and `grid-column`.

  import type {
    LandscapeRecord,
    Cell,
    Cells,
    Taxonomy,
    TaxonomyValue,
    ColumnSlug
  } from '$lib/types';
  import { COLUMNS, GROUP_META, type ColumnGroup, type ColumnDef } from '$lib/columns';
  import { removeSelected, clearSelection } from '$lib/stores/selection';
  import { onMount } from 'svelte';

  let {
    records,
    onClose
  }: { records: LandscapeRecord[]; onClose: () => void } = $props();

  // Build a group → cols list, same as DetailModal.
  type GroupedColumns = { group: ColumnGroup; cols: ColumnDef[] };
  const grouped: GroupedColumns[] = (() => {
    const out: GroupedColumns[] = [];
    let g: ColumnGroup | null = null;
    let bucket: ColumnDef[] = [];
    for (const c of COLUMNS) {
      if (c.group !== g) {
        if (bucket.length) out.push({ group: g!, cols: bucket });
        g = c.group;
        bucket = [];
      }
      bucket.push(c);
    }
    if (bucket.length) out.push({ group: g!, cols: bucket });
    return out;
  })();

  /** Comparable string form of a field's value (for difference detection). */
  function comparableValue(record: LandscapeRecord, col: ColumnDef): string {
    if (col.key === 'name') return record.name;
    if (col.key === 'tier') return String(record.tier);
    if (col.isTaxonomy) {
      const axis = col.key.slice(4) as keyof typeof record.taxonomy;
      const values = record.taxonomy[axis] ?? [];
      return [...values]
        .sort((a, b) => a.value.localeCompare(b.value))
        .map((v) => `${v.value}${v.primary ? '*' : ''}`)
        .join('|');
    }
    const cell = record.cells[col.key as keyof typeof record.cells] as Cell | undefined;
    if (!cell) return '';
    if (cell.status !== 'real-data') return `__${cell.status}__`;
    // Strip HTML so a `<br>` formatting difference doesn't trigger a diff.
    return (cell.value ?? '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
  }

  /** True if not all records have the same comparable value for this column. */
  function isDifferent(col: ColumnDef): boolean {
    if (records.length < 2) return false;
    const first = comparableValue(records[0], col);
    return records.some((r) => comparableValue(r, col) !== first);
  }

  function sortTax(values: TaxonomyValue[] | undefined): TaxonomyValue[] {
    if (!values) return [];
    return [...values].sort((a, b) => {
      if (a.primary && !b.primary) return -1;
      if (!a.primary && b.primary) return 1;
      return a.value.localeCompare(b.value);
    });
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  }

  function handleBackdrop(e: MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  function handleClearAll() {
    clearSelection();
    onClose();
  }

  onMount(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  });

  // Grid template: label column + N record columns.
  const gridTemplate = $derived(
    `200px ${records.map(() => 'minmax(220px, 1fr)').join(' ')}`
  );
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
  class="backdrop"
  role="dialog"
  aria-modal="true"
  aria-labelledby="compare-title"
  tabindex="-1"
  onclick={handleBackdrop}
>
  <div class="panel">
    <header class="panel-header">
      <h2 id="compare-title">Compare ({records.length})</h2>
      <div class="header-actions">
        <button class="action-btn" onclick={handleClearAll}>Clear selection</button>
        <button class="close" onclick={onClose} aria-label="Close compare panel">×</button>
      </div>
    </header>

    <div class="panel-body">
      <div class="grid" style="grid-template-columns: {gridTemplate};">
        <!-- Card headers row -->
        <div class="card-header card-label-spacer"></div>
        {#each records as record (record.id)}
          <div class="card-header">
            <div class="card-title">
              {#if record.url}
                <a href={record.url} target="_blank" rel="noopener noreferrer">{record.name} ↗</a>
              {:else}
                {record.name}
              {/if}
              <span class="tier-badge t{record.tier}">T{record.tier}</span>
            </div>
            <div class="card-section">
              {record.sections.find((s) => s.primary)?.section ?? record.sections[0]?.section ?? ''}
            </div>
            <button
              class="remove-btn"
              onclick={() => removeSelected(record.id)}
              aria-label="Remove {record.name} from comparison"
              title="Remove from comparison"
            >×</button>
          </div>
        {/each}

        {#each grouped as g}
          {@const meta = GROUP_META[g.group]}
          <!-- Group band row spans every column. -->
          <div
            class="group-band"
            style="grid-column: 1 / -1; --accent: {meta.accent};"
          >
            {meta.label}
          </div>

          {#each g.cols as col (col.key)}
            {@const diff = isDifferent(col)}
            <div class="field-label" class:diff>
              {col.label}
            </div>
            {#each records as record (record.id + ':' + col.key)}
              <div class="field-cell" class:diff>
                {#if col.key === 'name'}
                  <span>{record.name}</span>
                {:else if col.key === 'tier'}
                  <span class="tier-badge t{record.tier}">T{record.tier}</span>
                {:else if col.isTaxonomy}
                  {@const axis = col.key.slice(4) as keyof Taxonomy}
                  {@const values = sortTax(record.taxonomy[axis])}
                  {#if values.length === 0}
                    <span class="no-data">—</span>
                  {:else}
                    {#each values as v}
                      <span class="tax-pill" class:primary={v.primary} title={v.reason ?? ''}>
                        {v.value}{v.primary ? ' ★' : ''}
                      </span>
                    {/each}
                  {/if}
                {:else}
                  {@const cell = record.cells[col.key as ColumnSlug]}
                  {#if !cell}
                    <span class="no-data">—</span>
                  {:else if cell.status === 'not-applicable'}
                    <span class="no-data na">{cell.value || 'not applicable'}</span>
                  {:else if cell.status === 'no-data'}
                    <span class="no-data">—</span>
                  {:else if cell.status === 'depth-floor-reached'}
                    <span class="no-data">{cell.value || 'searched not found'}</span>
                    {#if cell.citation}
                      <a class="cite" href={cell.citation} target="_blank" rel="noopener noreferrer">↗</a>
                    {/if}
                  {:else}
                    <span class="cell-html">{@html cell.value}</span>
                    {#if cell.citation}
                      <a class="cite" href={cell.citation} target="_blank" rel="noopener noreferrer">↗</a>
                    {/if}
                  {/if}
                {/if}
              </div>
            {/each}
          {/each}
        {/each}
      </div>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(8, 10, 14, 0.75);
    backdrop-filter: blur(2px);
    z-index: 1000;
    display: flex;
    align-items: stretch;
    justify-content: center;
    padding: 16px;
  }
  .panel {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    width: min(1400px, 100%);
    max-height: 100%;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  }
  .panel-header {
    flex-shrink: 0;
    padding: 14px 20px;
    border-bottom: 1px solid #30363d;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  h2 {
    margin: 0;
    color: #f0f6fc;
    font-size: 1.05rem;
    letter-spacing: -0.01em;
  }
  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .action-btn {
    padding: 5px 12px;
    background: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.83rem;
  }
  .action-btn:hover {
    background: #30363d;
    border-color: #58a6ff;
  }
  .close {
    width: 30px;
    height: 30px;
    border-radius: 6px;
    background: transparent;
    border: 1px solid #30363d;
    color: #8b949e;
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
  }
  .close:hover {
    color: #f0f6fc;
    border-color: #58a6ff;
  }

  .panel-body {
    overflow: auto;
    flex: 1;
  }
  .grid {
    display: grid;
    /* grid-template-columns set inline */
    align-items: stretch;
  }
  .card-header {
    position: sticky;
    top: 0;
    z-index: 2;
    background: #161b22;
    padding: 12px 14px;
    border-bottom: 1px solid #30363d;
    border-right: 1px solid #21262d;
    min-height: 64px;
  }
  .card-label-spacer {
    background: #0d1117;
  }
  .card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    color: #f0f6fc;
    font-weight: 600;
    font-size: 0.95rem;
    padding-right: 30px;
  }
  .card-title a {
    color: #f0f6fc;
    text-decoration: none;
  }
  .card-title a:hover {
    color: #d4845f;
    text-decoration: underline;
  }
  .card-section {
    color: #8b949e;
    font-size: 11px;
    margin-top: 4px;
  }
  .remove-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 22px;
    height: 22px;
    border-radius: 4px;
    background: transparent;
    border: 1px solid #30363d;
    color: #8b949e;
    font-size: 14px;
    line-height: 1;
    cursor: pointer;
    padding: 0;
  }
  .remove-btn:hover {
    color: #f85149;
    border-color: #f85149;
  }

  .group-band {
    padding: 6px 16px;
    background: #1a1f24;
    color: var(--accent);
    border-top: 1px solid #30363d;
    border-bottom: 1px solid #21262d;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .field-label {
    padding: 8px 12px 8px 16px;
    color: #8b949e;
    font-size: 12px;
    font-weight: 500;
    border-bottom: 1px solid #1f242a;
    background: #0d1117;
  }
  .field-cell {
    padding: 8px 14px;
    color: #c9d1d9;
    font-size: 12.5px;
    line-height: 1.5;
    border-bottom: 1px solid #1f242a;
    border-right: 1px solid #1f242a;
    word-break: break-word;
    background: #11161d;
  }
  .field-label.diff,
  .field-cell.diff {
    /* Soft accent so the eye lands on differing rows without screaming. */
    box-shadow: inset 0 0 0 1px rgba(196, 99, 60, 0.25);
    background: rgba(196, 99, 60, 0.04);
  }
  .field-label.diff {
    color: #d4845f;
  }
  .cell-html :global(a) {
    color: #58a6ff;
    text-decoration: none;
  }
  .cell-html :global(a:hover) {
    text-decoration: underline;
  }
  .tax-pill {
    display: inline-block;
    padding: 1px 6px;
    margin: 1px 4px 1px 0;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    background: #2a2a2a;
    border: 1px solid #3a3a3a;
    color: #c8c8c8;
  }
  .tax-pill.primary {
    background: #24201a;
    border-color: #53432c;
    color: #c8a868;
  }
  .tier-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.04em;
    border: 1px solid;
  }
  .tier-badge.t1 { background: #1f3a26; color: #8fc99a; border-color: #2c5235; }
  .tier-badge.t2 { background: #1f2e3a; color: #8fb3c9; border-color: #2c4253; }
  .tier-badge.t3 { background: #321f3a; color: #b58fc9; border-color: #492c53; }
  .tier-badge.t4 { background: #3a2e1f; color: #c9a98f; border-color: #53432c; }
  .tier-badge.t5 { background: #2a2a2a; color: #999; border-color: #3a3a3a; }
  .no-data {
    font-style: italic;
    color: #6e7681;
    font-size: 0.92em;
  }
  .no-data.na {
    color: #555;
  }
  .cite {
    font-size: 10px;
    color: #888;
    text-decoration: none;
    margin-left: 2px;
    vertical-align: super;
  }
  .cite:hover {
    color: #d4845f;
  }
</style>
