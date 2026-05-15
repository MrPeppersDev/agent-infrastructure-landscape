<script lang="ts">
  // Per-row detail modal. Shows all 68 fields of a record, grouped by the
  // same column-group bands used in the table — so the eye finds related
  // fields by the same color cues. Issue #18.
  //
  // Rendering rules mirror TableCell/TaxonomyCell so cells look the same
  // here as in the row. We inline the cell rendering (rather than reusing
  // TableCell.svelte) because the table cells assume a <td> context with
  // specific overflow/truncation styling — the modal wants the full,
  // unbounded text instead.

  import type { LandscapeRecord, Cell, TaxonomyValue } from '$lib/types';
  import { COLUMNS, GROUP_META, type ColumnGroup, type ColumnDef } from '$lib/columns';
  import { onMount } from 'svelte';

  let {
    record,
    onClose
  }: { record: LandscapeRecord; onClose: () => void } = $props();

  // Group the columns into their bands once. Same data the table thead
  // uses, but presented as a vertical layout.
  type GroupedColumns = { group: ColumnGroup; cols: ColumnDef[] };
  const grouped: GroupedColumns[] = (() => {
    const out: GroupedColumns[] = [];
    let currentGroup: ColumnGroup | null = null;
    let bucket: ColumnDef[] = [];
    for (const c of COLUMNS) {
      if (c.group !== currentGroup) {
        if (bucket.length) out.push({ group: currentGroup!, cols: bucket });
        currentGroup = c.group;
        bucket = [];
      }
      bucket.push(c);
    }
    if (bucket.length) out.push({ group: currentGroup!, cols: bucket });
    return out;
  })();

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  }

  function handleBackdrop(e: MouseEvent) {
    // Only close when the backdrop itself (not a child) was clicked.
    if (e.target === e.currentTarget) onClose();
  }

  onMount(() => {
    // Lock body scroll while modal is open so the page underneath
    // doesn't scroll with the wheel.
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  });

  function fieldValue(col: ColumnDef): {
    kind: 'name' | 'tier' | 'taxonomy' | 'cell';
    cell?: Cell;
    taxValues?: TaxonomyValue[];
  } {
    if (col.key === 'name') return { kind: 'name' };
    if (col.key === 'tier') return { kind: 'tier' };
    if (col.isTaxonomy) {
      const axis = col.key.slice(4) as keyof typeof record.taxonomy;
      return { kind: 'taxonomy', taxValues: record.taxonomy[axis] };
    }
    const slug = col.key as keyof typeof record.cells;
    return { kind: 'cell', cell: record.cells[slug] };
  }

  // ---------------------------------------------------------------------
  // last_verified_at freshness — SCHEMA.md §3b / issue #54.
  // ---------------------------------------------------------------------
  // Today is hard-pinned to match the survivorship analyses + the
  // validate.py FRESHNESS_TODAY constant. Move all three in lockstep
  // when bumping the catalog snapshot date.
  const FRESHNESS_TODAY = new Date('2026-05-14T00:00:00Z');

  function ageMonths(iso: string | undefined): number | null {
    if (!iso) return null;
    const d = new Date(iso + 'T00:00:00Z');
    if (Number.isNaN(d.getTime())) return null;
    const ms = FRESHNESS_TODAY.getTime() - d.getTime();
    return ms / (1000 * 60 * 60 * 24 * 30.4375);
  }

  function freshnessBadge(iso: string | undefined): {
    label: string;
    tone: 'fresh' | 'aging' | 'stale';
  } | null {
    const m = ageMonths(iso);
    if (m === null) return null;
    if (m >= 12) return { label: 'stale', tone: 'stale' };
    if (m >= 6) return { label: 'needs re-audit', tone: 'aging' };
    return null; // fresh — no badge
  }

  const rowLva = $derived(record.last_verified_at);
  const rowBadge = $derived(freshnessBadge(rowLva));

  // Per-cell freshness override — when a cell carries its own
  // last_verified_at, the effective verification date for that cell
  // is the cell-level date (not the row-level one). The badge applies
  // to that override, displayed inline beside the cell value.
  function effectiveCellLva(cell: Cell | undefined): string | undefined {
    return cell?.last_verified_at ?? rowLva;
  }

  function cellBadge(cell: Cell | undefined): {
    label: string;
    tone: 'fresh' | 'aging' | 'stale';
  } | null {
    // Only show a per-cell badge when the cell carries its own date AND
    // that date is staler than fresh. Cells inheriting the row-level
    // date get no extra badge — the row's badge already covers them.
    if (!cell?.last_verified_at) return null;
    return freshnessBadge(cell.last_verified_at);
  }

  // Pre-compute sorted taxonomy values per axis for stable rendering.
  function sortTax(values: TaxonomyValue[] | undefined): TaxonomyValue[] {
    if (!values) return [];
    return [...values].sort((a, b) => {
      if (a.primary && !b.primary) return -1;
      if (!a.primary && b.primary) return 1;
      return a.value.localeCompare(b.value);
    });
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
  class="backdrop"
  role="dialog"
  aria-modal="true"
  aria-labelledby="detail-title"
  tabindex="-1"
  onclick={handleBackdrop}
>
  <div class="modal">
    <header class="modal-header">
      <div class="title-row">
        <h2 id="detail-title">
          {#if record.url}
            <a href={record.url} target="_blank" rel="noopener noreferrer">{record.name} ↗</a>
          {:else}
            {record.name}
          {/if}
        </h2>
        <span class="tier-badge t{record.tier}">T{record.tier}</span>
      </div>
      <div class="sub-row">
        {#each record.sections as s}
          <span class="section-pill" class:primary={s.primary}>
            {s.section}{s.subsection ? ` — ${s.subsection}` : ''}
          </span>
        {/each}
      </div>
      {#if rowLva}
        <div class="verified-row">
          <span class="verified-label">Last verified:</span>
          <span class="verified-date">{rowLva}</span>
          {#if rowBadge}
            <span
              class="freshness-badge {rowBadge.tone}"
              title="Row-level last_verified_at is older than {rowBadge.tone === 'stale' ? 12 : 6} months — see SCHEMA.md §3b"
              >{rowBadge.label}</span
            >
          {/if}
        </div>
      {/if}
      <button class="close" onclick={onClose} aria-label="Close modal">×</button>
    </header>

    <div class="modal-body">
      {#each grouped as g}
        {@const meta = GROUP_META[g.group]}
        <section class="group" style="--accent: {meta.accent}; --bg: {meta.bg};">
          <h3 class="group-label">{meta.label}</h3>
          <dl class="fields">
            {#each g.cols as col (col.key)}
              {@const fv = fieldValue(col)}
              <div class="field">
                <dt class="field-label">{col.label}</dt>
                <dd class="field-value">
                  {#if fv.kind === 'name'}
                    {record.name}
                  {:else if fv.kind === 'tier'}
                    <span class="tier-badge t{record.tier}">T{record.tier}</span>
                  {:else if fv.kind === 'taxonomy'}
                    {#each sortTax(fv.taxValues) as v}
                      <span class="tax-pill" class:primary={v.primary} title={v.reason ?? ''}>
                        {v.value}{v.primary ? ' ★' : ''}
                      </span>
                    {/each}
                    {#if !fv.taxValues || fv.taxValues.length === 0}
                      <span class="no-data">—</span>
                    {/if}
                  {:else if fv.cell}
                    {@const cell = fv.cell}
                    {@const cb = cellBadge(cell)}
                    {#if cell.status === 'not-applicable'}
                      <span class="no-data na">{cell.value || 'not applicable'}</span>
                    {:else if cell.status === 'depth-floor-reached'}
                      <span class="no-data">{cell.value || 'searched not found'}</span>
                      {#if cell.citation}
                        <a class="cite" href={cell.citation} target="_blank" rel="noopener noreferrer">↗</a>
                      {/if}
                    {:else if cell.status === 'no-data'}
                      <span class="no-data">—</span>
                    {:else}
                      <span class="cell-value">{@html cell.value}</span>
                      {#if cell.citation}
                        <a class="cite" href={cell.citation} target="_blank" rel="noopener noreferrer">↗</a>
                      {/if}
                    {/if}
                    {#if cell.last_verified_at}
                      <span
                        class="cell-verified"
                        title={`Cell verified ${cell.last_verified_at} (overrides row date)`}
                      >verified {cell.last_verified_at}</span>
                    {/if}
                    {#if cb}
                      <span class="freshness-badge {cb.tone} mini" title="Cell last_verified_at is older than {cb.tone === 'stale' ? 12 : 6} months">{cb.label}</span>
                    {/if}
                  {:else}
                    <span class="no-data">—</span>
                  {/if}
                </dd>
              </div>
            {/each}
          </dl>
        </section>
      {/each}
    </div>

    <footer class="modal-footer">
      {#if record.url}
        <a class="footer-link" href={record.url} target="_blank" rel="noopener noreferrer">
          Open primary URL ↗
        </a>
      {/if}
      <span class="footer-id">id: <code>{record.id}</code></span>
      <button class="footer-close" onclick={onClose}>Close (Esc)</button>
    </footer>
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(8, 10, 14, 0.7);
    backdrop-filter: blur(2px);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
  .modal {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    width: min(960px, 100%);
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  }
  .modal-header {
    position: relative;
    padding: 16px 56px 12px 20px;
    border-bottom: 1px solid #30363d;
    flex-shrink: 0;
  }
  .title-row {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  h2 {
    margin: 0;
    font-size: 1.15rem;
    color: #f0f6fc;
    letter-spacing: -0.01em;
  }
  h2 a {
    color: #f0f6fc;
    text-decoration: none;
  }
  h2 a:hover {
    color: #d4845f;
    text-decoration: underline;
  }
  .sub-row {
    margin-top: 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .section-pill {
    padding: 2px 8px;
    border-radius: 10px;
    background: #1a1f24;
    border: 1px solid #30363d;
    color: #8b949e;
    font-size: 11px;
  }
  .section-pill.primary {
    background: #24201a;
    border-color: #53432c;
    color: #c8a868;
  }
  .verified-row {
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11.5px;
    color: #8b949e;
  }
  .verified-label {
    color: #6e7681;
    letter-spacing: 0.02em;
  }
  .verified-date {
    color: #c9d1d9;
    font-variant-numeric: tabular-nums;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .freshness-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: lowercase;
    border: 1px solid;
    cursor: help;
  }
  .freshness-badge.aging {
    background: #3a2e1f;
    color: #d29922;
    border-color: #5d4720;
  }
  .freshness-badge.stale {
    background: #3a2419;
    color: #db6d28;
    border-color: #5d3a1f;
  }
  .freshness-badge.mini {
    font-size: 9px;
    margin-left: 4px;
    padding: 0 4px;
  }
  .cell-verified {
    display: inline-block;
    margin-left: 6px;
    font-size: 10px;
    color: #6e7681;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    cursor: help;
  }
  .close {
    position: absolute;
    top: 12px;
    right: 12px;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    background: transparent;
    border: 1px solid #30363d;
    color: #8b949e;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
  }
  .close:hover {
    color: #f0f6fc;
    border-color: #58a6ff;
  }

  .modal-body {
    overflow-y: auto;
    padding: 16px 20px;
    flex: 1;
  }
  .group {
    margin-bottom: 24px;
    padding-left: 12px;
    border-left: 3px solid var(--accent);
  }
  .group-label {
    margin: 0 0 8px 0;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
  }
  .fields {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 6px 16px;
    margin: 0;
  }
  .field {
    display: contents;
  }
  .field-label {
    color: #8b949e;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 0;
  }
  .field-value {
    margin: 0;
    color: #c9d1d9;
    font-size: 13px;
    line-height: 1.55;
    padding: 4px 0;
    word-break: break-word;
  }
  .cell-value :global(a) {
    color: #58a6ff;
    text-decoration: none;
  }
  .cell-value :global(a:hover) {
    text-decoration: underline;
  }
  .tax-pill {
    display: inline-block;
    padding: 1px 6px;
    margin: 1px 4px 1px 0;
    border-radius: 3px;
    font-size: 10.5px;
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
    padding: 1px 7px;
    border-radius: 3px;
    font-size: 10.5px;
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

  .modal-footer {
    flex-shrink: 0;
    padding: 12px 20px;
    border-top: 1px solid #30363d;
    background: #161b22;
    border-radius: 0 0 8px 8px;
    display: flex;
    align-items: center;
    gap: 16px;
    justify-content: flex-end;
  }
  .footer-link {
    color: #58a6ff;
    text-decoration: none;
    font-size: 0.85rem;
    margin-right: auto;
  }
  .footer-link:hover {
    text-decoration: underline;
  }
  .footer-id {
    color: #6e7681;
    font-size: 0.78rem;
  }
  .footer-id code {
    color: #8b949e;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.9em;
  }
  .footer-close {
    padding: 6px 14px;
    background: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
  }
  .footer-close:hover {
    background: #30363d;
    border-color: #58a6ff;
  }
</style>
