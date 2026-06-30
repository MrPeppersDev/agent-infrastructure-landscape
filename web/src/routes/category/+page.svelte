<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { itemListLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';

  type Category = { name: string; slug: string; count: number };

  let { data }: { data: { categories: Category[] } } = $props();

  const ldData = itemListLd({
    name: 'AI Agent Memory Categories',
    items: data.categories.map((c) => ({
      name: c.name,
      url: absoluteUrl(`/category/${c.slug}`)
    }))
  });
</script>

<SeoHead
  title="AI Agent Memory Categories — Browse by Section"
  description="All {data.categories.length} categories in the AI Agent Infrastructure Landscape — dedicated memory layers, framework-embedded memory, browser-agent memory, voice memory, and more. Each links to the full system list."
  path="/category"
  ogType="website"
/>
<JsonLd data={ldData} />

<article class="catlist">
  <header>
    <h1>Categories</h1>
    <p class="lede">
      {data.categories.length} sections across the AI Agent Infrastructure Landscape.
      Each page lists every system in that category, ranked by maturity tier.
    </p>
  </header>

  <ul>
    {#each data.categories as c}
      <li>
        <a href="{base}/category/{c.slug}">{c.name}</a>
        <span class="count">{c.count} systems</span>
      </li>
    {/each}
  </ul>
</article>

<style>
  .catlist {
    max-width: 760px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    color: #d6d6d6;
    line-height: 1.55;
  }
  h1 {
    margin: 0 0 0.5rem;
    color: #f0f0f0;
    font-size: 1.8rem;
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
    padding: 0.7rem 0;
    border-bottom: 1px solid #1f1f1f;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
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
    flex-shrink: 0;
  }
</style>
