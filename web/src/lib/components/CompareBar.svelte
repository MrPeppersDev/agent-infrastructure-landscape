<script lang="ts">
  // Sticky "Compare N selected" bar under the chooser tables.
  import { base } from '$app/paths';
  let { ids, names, onclear }: { ids: string[]; names: { id: string; name: string }[]; onclear: () => void } = $props();
  const label = $derived(ids.map((id) => names.find((n) => n.id === id)?.name ?? id).join(', '));
</script>

{#if ids.length}
  <div class="bar" role="region" aria-label="Selected for comparison">
    <span class="sel">{ids.length} selected: {label}</span>
    {#if ids.length >= 2}
      <a class="go" href="{base}/compare/many?ids={ids.join(',')}">Compare side by side →</a>
      <a href="{base}/compatibility?ids={ids.join(',')}">Do they work together?</a>
    {:else}
      <span class="hint">tick one more to compare</span>
    {/if}
    <button type="button" onclick={onclear}>Clear</button>
  </div>
{/if}

<style>
  .bar { position: sticky; bottom: 12px; display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 10px; padding: 10px 14px; border: 1px solid #1f6feb; border-radius: 10px; background: #0d1d33; font-size: 13px; z-index: 5; }
  .sel { color: #c9d1d9; flex: 1 1 240px; }
  a { color: #58a6ff; }
  .go { font-weight: 600; }
  .hint { color: #8b949e; }
  button { background: none; border: 1px solid #30363d; color: #8b949e; border-radius: 6px; padding: 3px 10px; font: inherit; cursor: pointer; }
</style>
