<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { itemListLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';

  type PairRow = {
    slug: string;
    aName: string;
    bName: string;
    reason: 'competes-with' | 'top-in-section';
    section: string | null;
  };

  let { data }: { data: { pairs: PairRow[] } } = $props();

  // Group by section so the index reads as a section-by-section
  // "head-to-head" view; competes-with edges land in their own bucket.
  const grouped = (() => {
    const m = new Map<string, PairRow[]>();
    for (const p of data.pairs) {
      const k = p.section ?? 'Explicit competes-with edges';
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(p);
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  })();

  const ldData = itemListLd({
    name: 'AI Agent Memory Comparisons',
    items: data.pairs.slice(0, 50).map((p) => ({
      name: `${p.aName} vs ${p.bName}`,
      url: absoluteUrl(`/compare/${p.slug}`)
    }))
  });
</script>

<SeoHead
  title="AI Agent Memory Comparisons — {data.pairs.length} Head-to-Heads"
  description="Side-by-side comparisons of AI agent memory systems and frameworks: {data.pairs.length} head-to-head pages covering architecture, taxonomy, license, pricing, and direct edges between systems."
  path="/compare"
  ogType="website"
/>
<JsonLd data={ldData} />

<article class="cmpidx">
  <header>
    <h1>Comparisons</h1>
    <p class="lede">
      {data.pairs.length} side-by-side comparison pages, grouped by category. Each
      compares two systems across 19+ dimensions and surfaces any direct edges
      the catalog has between them.
    </p>
  </header>

  {#each grouped as [section, pairs]}
    <section>
      <h2>{section} <span class="count">({pairs.length})</span></h2>
      <ul>
        {#each pairs as p}
          <li>
            <a href="{base}/compare/{p.slug}">{p.aName} vs {p.bName}</a>
            {#if p.reason === 'competes-with'}
              <span class="tag">explicit</span>
            {/if}
          </li>
        {/each}
      </ul>
    </section>
  {/each}
</article>

<style>
  .cmpidx {
    max-width: 820px;
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
  h2 {
    color: #e8e8e8;
    font-size: 1.1rem;
    margin: 2rem 0 0.6rem;
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
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.4rem 1.5rem;
  }
  @media (max-width: 720px) {
    ul {
      grid-template-columns: 1fr;
    }
  }
  li {
    border-left: 2px solid #2a2a2a;
    padding-left: 0.7rem;
  }
  li a {
    color: #d4845f;
    text-decoration: none;
  }
  li a:hover {
    text-decoration: underline;
  }
  .tag {
    margin-left: 0.5rem;
    color: #888;
    font-size: 0.8rem;
    font-style: italic;
  }
</style>
