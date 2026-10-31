<script lang="ts">
  // Product-family switcher (taxonomy/families.json). Each family is a
  // self-contained sub-catalog; this bar is the primary way to pick one.
  // It drives the same `product` facet the filter rail exposes, so the
  // selection round-trips through the URL (?product=memory).
  import { filters } from '$lib/stores/filters';
  import { base } from '$app/paths';
  import { getFamilies, familyCounts } from '$lib/families';
  import { siloForFamily } from '$lib/silos';
  import type { LandscapeRecord } from '$lib/types';

  let { records }: { records: LandscapeRecord[] } = $props();

  const families = getFamilies();
  const counts = $derived(familyCounts(records));
  const selected = $derived([...$filters.product]);
  const active = $derived(selected.length === 1 ? selected[0] : null);
  const activeFamily = $derived(families.find((f) => f.id === active) ?? null);

  function pick(id: string | null) {
    filters.update((s) => {
      s.product.clear();
      if (id) s.product.add(id);
      // A section chosen in another family would yield an empty table.
      if (id) {
        const fam = families.find((f) => f.id === id);
        for (const sec of [...s.section]) {
          if (fam && !fam.sections.includes(sec)) s.section.delete(sec);
        }
      }
      return s;
    });
  }
</script>

<nav class="products" aria-label="Product catalogs">
  <div class="tabs" role="tablist">
    <button
      type="button"
      role="tab"
      aria-selected={selected.length === 0}
      class:on={selected.length === 0}
      onclick={() => pick(null)}
    >
      All <span class="n">{records.length}</span>
    </button>
    {#each families as f (f.id)}
      <button
        type="button"
        role="tab"
        aria-selected={active === f.id}
        class:on={active === f.id}
        title={f.tagline}
        onclick={() => pick(f.id)}
      >
        {f.name} <span class="n">{counts.get(f.id) ?? 0}</span>
      </button>
    {/each}
  </div>
  <p class="tagline">
    {#if activeFamily}
      <strong>{activeFamily.name}:</strong> {activeFamily.tagline}
      <span class="aud">For: {activeFamily.audience}</span>
      {#if siloForFamily(activeFamily.id)}
        <a class="open" href="{base}/catalogs/{siloForFamily(activeFamily.id)?.id}">Open the {activeFamily.name} catalog →</a>
      {/if}
    {:else}
      Every system in one table. Filter by layer here, or open a <a class="open" href="{base}/catalogs">focused catalog</a>
      for one audience: memory, frameworks, retrieval, models, research, coding agents, security, evals and more.
    {/if}
  </p>
</nav>

<style>
  .products {
    padding: 4px 12px 8px;
    border-bottom: 1px solid #21262d;
  }
  .tabs {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    scrollbar-width: thin;
    padding-bottom: 4px;
  }
  .tabs button {
    flex: 0 0 auto;
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid #30363d;
    background: #161b22;
    color: #c9d1d9;
    font: inherit;
    font-size: 13px;
    cursor: pointer;
    white-space: nowrap;
  }
  .tabs button:hover {
    border-color: #58a6ff;
  }
  .tabs button.on {
    background: #1f6feb;
    border-color: #1f6feb;
    color: #fff;
  }
  .n {
    opacity: 0.7;
    font-variant-numeric: tabular-nums;
    margin-left: 4px;
  }
  .tagline {
    margin: 4px 2px 0;
    font-size: 13px;
    color: #8b949e;
  }
  .open {
    margin-left: 8px;
    color: #58a6ff;
    text-decoration: none;
  }
  .open:hover {
    text-decoration: underline;
  }
  .aud {
    margin-left: 8px;
    color: #6e7681;
  }
  .link {
    background: none;
    border: none;
    padding: 0;
    color: #58a6ff;
    font: inherit;
    cursor: pointer;
    text-decoration: underline;
  }
</style>
