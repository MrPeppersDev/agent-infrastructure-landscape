<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { itemListLd, breadcrumbLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';
  import type { BestOfIndexEntry } from './+page';

  let { data }: { data: { entries: BestOfIndexEntry[] } } = $props();

  const title = 'Best agent memory systems — filtered lists';
  const description =
    'Curated lists from the AI Agent Infrastructure Landscape — open-source, self-hostable, MCP-enabled, SOC 2 / HIPAA / GDPR compliant, and more. Each list is ranked by maturity tier.';
  const routePath = '/best';

  const ldData = [
    itemListLd({
      name: 'Best agent memory systems — filtered lists',
      items: data.entries.map((e) => ({
        name: e.title,
        url: absoluteUrl(`/best/${e.slug}`)
      }))
    }),
    breadcrumbLd({
      items: [
        { name: 'Catalog', url: absoluteUrl('/') },
        { name: 'Best of', url: absoluteUrl(routePath) }
      ]
    })
  ];
</script>

<SeoHead {title} {description} path={routePath} ogType="website" />
<JsonLd data={ldData} />

<article class="bestidx">
  <header>
    <p class="breadcrumbs">
      <a href="{base}/">Catalog</a>
      <span aria-hidden="true">›</span>
      <span>Best of</span>
    </p>
    <h1>Best agent memory systems</h1>
    <p class="lede">
      Filtered subsets of the AI Agent Infrastructure Landscape. Pick the
      property that matters to you — protocol support, license model,
      deployment posture, compliance posture, observability stack — and the
      catalog returns the ranked list.
    </p>
  </header>

  <ul>
    {#each data.entries as e}
      <li>
        <a href="{base}/best/{e.slug}">{e.title}</a>
        <span class="count">({e.count})</span>
        <p>{e.description}</p>
      </li>
    {/each}
  </ul>
</article>

<style>
  .bestidx {
    max-width: 820px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    color: #d6d6d6;
    line-height: 1.55;
  }
  .breadcrumbs {
    font-size: 0.85rem;
    color: #888;
    margin: 0 0 0.5rem;
  }
  .breadcrumbs a {
    color: #b0b0b0;
    text-decoration: none;
  }
  .breadcrumbs a:hover {
    text-decoration: underline;
  }
  .breadcrumbs span {
    margin: 0 0.35rem;
  }
  h1 {
    margin: 0 0 0.5rem;
    color: #f0f0f0;
    font-size: 1.9rem;
  }
  .lede {
    color: #c0c0c0;
    margin: 0 0 2rem;
  }
  ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  li {
    padding: 0.9rem 0;
    border-bottom: 1px solid #1f1f1f;
  }
  li a {
    color: #d4845f;
    text-decoration: none;
    font-weight: 500;
    font-size: 1.05rem;
  }
  li a:hover {
    text-decoration: underline;
  }
  .count {
    color: #888;
    font-size: 0.9rem;
    margin-left: 0.4rem;
  }
  li p {
    margin: 0.3rem 0 0;
    color: #aaa;
    font-size: 0.92rem;
    line-height: 1.5;
  }
</style>
