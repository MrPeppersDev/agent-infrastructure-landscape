<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import CatalogView from '$lib/components/CatalogView.svelte';
  import { getSilo, getSilos, siloColumns } from '$lib/silos';
  import type { LandscapeRecord } from '$lib/types';

  let {
    data
  }: { data: { siloId: string; records: LandscapeRecord[]; recordCount: number; edgeCount: number; fill: Record<string, number> } } =
    $props();

  const silo = $derived(getSilo(data.siloId)!);
  const columns = $derived(siloColumns(silo));
  const others = $derived(getSilos().filter((s) => s.id !== data.siloId));
</script>

<SeoHead
  title="{silo.name} — table of {data.recordCount.toLocaleString('en-US')} systems"
  description="{silo.tagline} Filter, sort, compare and export {data.recordCount.toLocaleString('en-US')} systems with the columns that matter for {silo.audience.replace(/\.$/, '').toLowerCase()}; every other column is one toggle away."
  path="/catalogs/{silo.id}/browse"
/>

<CatalogView {data} title={silo.name} lede={silo.tagline} {columns}>
  {#snippet banner()}
    <nav class="strip" aria-label="Catalogs">
      <a class="back" href="{base}/catalogs/{silo.id}">← {silo.short} overview</a>
      <span class="sep" aria-hidden="true">·</span>
      {#each others as o (o.id)}<a href="{base}/catalogs/{o.id}/browse">{o.short}</a>{/each}
      <a class="atlas" href="{base}/">Atlas: everything</a>
    </nav>
  {/snippet}
</CatalogView>

<style>
  .strip { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; padding: 2px 12px 8px; border-bottom: 1px solid #21262d; font-size: 0.8rem; }
  .strip a { color: #8b949e; border: 1px solid #30363d; border-radius: 999px; padding: 2px 10px; text-decoration: none; }
  .strip a:hover { color: #e6edf3; border-color: #58a6ff; }
  .strip .back { color: #e6edf3; }
  .strip .atlas { color: #58a6ff; border-color: #1f6feb; }
  .sep { color: #30363d; }
</style>
