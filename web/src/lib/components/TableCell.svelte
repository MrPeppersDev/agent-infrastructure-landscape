<script lang="ts">
  // Renders a single <td> for a record × column. Cell-rendering rules
  // follow SCHEMA.md §3:
  //   real-data           → value as-is, append cite ↗ if citation present
  //   not-applicable      → italicised muted text
  //   depth-floor-reached → muted text + cite link
  //   no-data             → empty muted span
  //
  // We use {@html cell.value} because cell values are trusted and may
  // contain HTML — see DECISIONS.md "{@html} trust boundary". The data is
  // produced by extract.py from our own landscape.html and ships in our
  // own bundle; there is no path by which untrusted text reaches a cell.

  import type { Cell } from '$lib/types';

  let { cell }: { cell: Cell | null | undefined } = $props();
</script>

{#if !cell}
  <span class="muted">—</span>
{:else if cell.status === 'not-applicable'}
  <span class="no-data na">{cell.value || 'not applicable'}</span>
{:else if cell.status === 'depth-floor-reached'}
  <span class="no-data">{cell.value || 'searched not found'}</span>
  {#if cell.citation}
    <a class="cite" href={cell.citation} target="_blank" rel="noopener noreferrer">↗</a>
  {/if}
{:else if cell.status === 'no-data'}
  <span class="no-data"></span>
{:else}
  <!-- real-data — trusted HTML pass-through (see header comment) -->
  {@html cell.value}
  {#if cell.citation}
    <a class="cite" href={cell.citation} target="_blank" rel="noopener noreferrer">↗</a>
  {/if}
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
</style>
