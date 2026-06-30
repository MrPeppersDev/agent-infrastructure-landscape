<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { itemListLd, breadcrumbLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';
  import type { BestOfSystem } from './+page';

  let {
    data
  }: {
    data: {
      slug: string;
      title: string;
      description: string;
      systems: BestOfSystem[];
      totalMatches: number;
    };
  } = $props();

  const routePath = `/best/${data.slug}`;

  const headTitle = `${data.title} (${data.totalMatches})`;

  const ldData = [
    itemListLd({
      name: data.title,
      items: data.systems.slice(0, 50).map((s) => ({
        name: s.name,
        url: absoluteUrl(`/systems/${s.id}`)
      }))
    }),
    breadcrumbLd({
      items: [
        { name: 'Catalog', url: absoluteUrl('/') },
        { name: 'Best of', url: absoluteUrl('/best') },
        { name: data.title, url: absoluteUrl(routePath) }
      ]
    })
  ];

  type TierKey = 1 | 2 | 3 | 4 | 5;
  const tierGroups = (() => {
    const m = new Map<TierKey, BestOfSystem[]>();
    for (const s of data.systems) {
      if (!m.has(s.tier)) m.set(s.tier, []);
      m.get(s.tier)!.push(s);
    }
    return [...m.entries()].sort((a, b) => a[0] - b[0]);
  })();

  const tierLabel: Record<TierKey, string> = {
    1: 'Tier 1 — battle-tested',
    2: 'Tier 2 — production-ready',
    3: 'Tier 3 — emerging',
    4: 'Tier 4 — early / experimental',
    5: 'Tier 5 — theoretical / informal'
  };
</script>

<SeoHead title={headTitle} description={data.description} path={routePath} ogType="website" />
<JsonLd data={ldData} />

<article class="bestof">
  <header>
    <p class="breadcrumbs">
      <a href="{base}/">Catalog</a>
      <span aria-hidden="true">›</span>
      <a href="{base}/best">Best of</a>
      <span aria-hidden="true">›</span>
      <span>{data.title}</span>
    </p>
    <h1>{data.title}</h1>
    <p class="lede">{data.description}</p>
    <p class="count">
      {data.totalMatches} systems match this filter{#if data.systems.length < data.totalMatches}
        — showing top {data.systems.length} by tier and inbound citations.{/if}
    </p>
  </header>

  {#each tierGroups as [tier, systems]}
    <section>
      <h2>{tierLabel[tier]} <span class="tier-count">({systems.length})</span></h2>
      <ul>
        {#each systems as s}
          <li>
            <a href="{base}/systems/{s.id}">{s.name}</a>
            {#if s.type}<span class="type">{s.type}</span>{/if}
            {#if s.desc}<p>{s.desc}</p>{/if}
          </li>
        {/each}
      </ul>
    </section>
  {/each}

  <footer class="meta">
    <p>
      <a href="{base}/best">← All best-of lists</a> · <a href="{base}/systems">All systems</a>
    </p>
  </footer>
</article>

<style>
  .bestof {
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
    font-size: 1.8rem;
    line-height: 1.25;
  }
  .lede {
    color: #c0c0c0;
    margin: 0 0 0.8rem;
  }
  .count {
    color: #888;
    font-size: 0.9rem;
    margin: 0 0 1.5rem;
  }
  h2 {
    color: #e8e8e8;
    font-size: 1.15rem;
    margin: 2rem 0 0.8rem;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.3rem;
  }
  .tier-count {
    color: #888;
    font-size: 0.9rem;
    font-weight: normal;
  }
  ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  li {
    padding: 0.7rem 0;
    border-bottom: 1px solid #1f1f1f;
  }
  li a {
    color: #d4845f;
    text-decoration: none;
    font-weight: 500;
    font-size: 1.02rem;
  }
  li a:hover {
    text-decoration: underline;
  }
  .type {
    margin-left: 0.5rem;
    color: #888;
    font-size: 0.85rem;
  }
  li p {
    margin: 0.3rem 0 0;
    color: #aaa;
    font-size: 0.92rem;
    line-height: 1.45;
  }
  .meta {
    margin-top: 3rem;
    color: #777;
    font-size: 0.9rem;
    border-top: 1px solid #2a2a2a;
    padding-top: 1rem;
  }
  .meta a {
    color: #b0b0b0;
  }
</style>
