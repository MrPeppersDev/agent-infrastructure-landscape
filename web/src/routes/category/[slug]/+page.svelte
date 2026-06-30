<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { itemListLd, breadcrumbLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';

  type System = {
    id: string;
    name: string;
    tier: 1 | 2 | 3 | 4 | 5;
    type: string | null;
    desc: string;
    url: string | null;
  };

  let {
    data
  }: { data: { sectionName: string; systems: System[] } } = $props();

  const routePath = `/category/${data.sectionName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')}`;

  const title = `${data.sectionName} — AI Agent Memory Systems (${data.systems.length})`;
  const description = `${data.systems.length} ${data.sectionName} entries in the AI Agent Infrastructure Landscape. Compare typed edges, tiers, licenses, and architecture across every system in this category.`;

  const ldData = [
    itemListLd({
      name: data.sectionName,
      items: data.systems.slice(0, 50).map((s) => ({
        name: s.name,
        url: absoluteUrl(`/systems/${s.id}`)
      }))
    }),
    breadcrumbLd({
      items: [
        { name: 'Catalog', url: absoluteUrl('/') },
        { name: 'Categories', url: absoluteUrl('/category') },
        { name: data.sectionName, url: absoluteUrl(routePath) }
      ]
    })
  ];

  // Group by tier so the page surfaces the production-grade entries first.
  type TierKey = 1 | 2 | 3 | 4 | 5;
  const tierGroups = (() => {
    const m = new Map<TierKey, System[]>();
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

<SeoHead {title} {description} path={routePath} ogType="website" />
<JsonLd data={ldData} />

<article class="cat">
  <header>
    <p class="breadcrumbs">
      <a href="{base}/">Catalog</a>
      <span aria-hidden="true">›</span>
      <a href="{base}/category">Categories</a>
      <span aria-hidden="true">›</span>
      <span>{data.sectionName}</span>
    </p>
    <h1>{data.sectionName}</h1>
    <p class="lede">
      {data.systems.length} systems in the {data.sectionName.toLowerCase()} category of
      the AI Agent Infrastructure Landscape, grouped by maturity tier.
    </p>
  </header>

  {#each tierGroups as [tier, systems]}
    <section>
      <h2>{tierLabel[tier]} <span class="count">({systems.length})</span></h2>
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
      <a href="{base}/category">← All categories</a> · <a href="{base}/systems"
        >All systems</a
      >
    </p>
  </footer>
</article>

<style>
  .cat {
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
  }
  .lede {
    color: #c0c0c0;
    margin: 0 0 2rem;
  }
  h2 {
    color: #e8e8e8;
    font-size: 1.15rem;
    margin: 2rem 0 0.8rem;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.3rem;
  }
  .count {
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
