<script lang="ts">
  // The Atlas: every system and every column in one table. The focused
  // views for one audience live under /catalogs (taxonomy/silos.json) and
  // render the same CatalogView with their own rows and columns.
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { datasetLd } from '$lib/seo/jsonld';
  import { page } from '$app/state';
  import CatalogView from '$lib/components/CatalogView.svelte';
  import ProductTabs from '$lib/components/ProductTabs.svelte';
  import StartHere from '$lib/components/StartHere.svelte';
  import { COMPACT_COLUMNS } from '$lib/columns';
  import { filters, FACET_ORDER } from '$lib/stores/filters';
  import { searchQuery } from '$lib/stores/search';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[]; recordCount: number; edgeCount: number; fill: Record<string, number> } } =
    $props();

  const busy = $derived(
    $searchQuery.trim().length > 0 || FACET_ORDER.some((f) => ($filters[f] as Set<unknown>).size > 0)
  );
</script>

<SeoHead
  title="AI Agent Stack Analysis — Choose and Check Your Agent Stack ({page.data.stats.records.toLocaleString('en-US')} Systems)"
  description="Pick the components of an AI agent or multi-agent system and check the stack you run: {page.data.stats.records.toLocaleString('en-US')} frameworks, models, memory layers, data stores, gateways, guardrails and tools, compared on {page.data.stats.columns} cited columns with lifecycle, pricing and integrations."
  path="/"
  ogType="website"
/>
<JsonLd data={datasetLd({ recordCount: data.recordCount, edgeCount: data.edgeCount })} />

<CatalogView {data} title="AI Agent Infrastructure Landscape" columns={COMPACT_COLUMNS}>
  {#snippet banner()}
    <StartHere hidden={busy} />
    <ProductTabs records={data.records} />
  {/snippet}
</CatalogView>
