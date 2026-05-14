<script lang="ts">
  // Renders a single <td> for a record × column. Cell-rendering rules
  // follow SCHEMA.md §3:
  //   real-data           → value as-is, append cite ↗ if citation present
  //   not-applicable      → italicised muted text
  //   depth-floor-reached → muted text + cite link
  //   no-data             → empty muted span
  //   estimate            → maintainer-judgement value (T3 — see §3a)
  //
  // We use {@html cell.value} because cell values are trusted and may
  // contain HTML — see DECISIONS.md "{@html} trust boundary".
  //
  // Tier badge (T0-3, issue #37): every cell carries a `tier` ∈ {T1,T2,T3}
  // computed at extract time from (citation, status). A tiny badge after
  // the citation surfaces the provenance: T1 = green dot, T2 = yellow
  // glyph "2", T3 = grey glyph "3". See SCHEMA.md §3a.

  import type { Cell } from '$lib/types';
  import { highlightHtml } from '$lib/stores/search';

  let {
    cell,
    highlight = ''
  }: { cell: Cell | null | undefined; highlight?: string } = $props();

  const renderedValue = $derived.by(() => {
    if (!cell) return '';
    if (!highlight) return cell.value ?? '';
    return highlightHtml(cell.value ?? '', highlight);
  });

  function tierGlyph(t: 'T1' | 'T2' | 'T3'): string {
    return t === 'T1' ? '●' : t.slice(1);
  }
  function tierTitle(t: 'T1' | 'T2' | 'T3'): string {
    if (t === 'T1') return 'T1 — auto-verifiable (GitHub citation)';
    if (t === 'T2') return 'T2 — source-URL required';
    return 'T3 — estimate / inferred (no citation)';
  }
</script>

{#if !cell}
  <span class="muted">—</span>
{:else if cell.status === 'not-applicable'}
  <span class="no-data na">{cell.value || 'not applicable'}</span>
  <span class="tier-badge tier-{cell.tier}" title={tierTitle(cell.tier)}
    >{tierGlyph(cell.tier)}</span
  >
{:else if cell.status === 'depth-floor-reached'}
  <span class="no-data">{cell.value || 'searched not found'}</span>
  {#if cell.citation}
    <a class="cite" href={cell.citation} target="_blank" rel="noopener noreferrer">↗</a>
  {/if}
  <span class="tier-badge tier-{cell.tier}" title={tierTitle(cell.tier)}
    >{tierGlyph(cell.tier)}</span
  >
{:else if cell.status === 'no-data'}
  <span class="no-data"></span>
  <span class="tier-badge tier-{cell.tier}" title={tierTitle(cell.tier)}
    >{tierGlyph(cell.tier)}</span
  >
{:else}
  <!-- real-data + estimate — trusted HTML pass-through -->
  {@html renderedValue}
  {#if cell.citation}
    <a class="cite" href={cell.citation} target="_blank" rel="noopener noreferrer">↗</a>
  {/if}
  <span class="tier-badge tier-{cell.tier}" title={tierTitle(cell.tier)}
    >{tierGlyph(cell.tier)}</span
  >
{/if}

<style>
  .muted {
    color: #555;
  }
  .no-data {
    font-style: italic;
    color: #777;
    font-size: 0.93em;
    letter-spacing: 0.02em;
  }
  .no-data.na {
    color: #555;
  }
  .cite {
    font-size: 9px;
    color: #888;
    text-decoration: none;
    margin-left: 2px;
    vertical-align: super;
    line-height: 1;
  }
  .cite:hover {
    color: #d4845f;
    text-decoration: underline;
  }
  /* Tier-provenance badge — minimal, single-glyph, color-coded. */
  .tier-badge {
    display: inline-block;
    margin-left: 4px;
    padding: 0 3px;
    font-size: 9px;
    line-height: 1.3;
    vertical-align: super;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    border-radius: 2px;
    user-select: none;
    cursor: help;
  }
  .tier-badge.tier-T1 {
    color: #56c878;
    background: transparent;
  }
  .tier-badge.tier-T2 {
    color: #d4a85a;
    background: rgba(212, 168, 90, 0.08);
  }
  .tier-badge.tier-T3 {
    color: #888;
    background: rgba(136, 136, 136, 0.08);
  }
</style>
