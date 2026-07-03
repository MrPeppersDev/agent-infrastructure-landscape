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

  let query = $state('');

  const filteredPairs = $derived.by(() => {
    const q = query.trim().toLowerCase();
    if (!q) return data.pairs;
    return data.pairs.filter(
      (p) =>
        p.aName.toLowerCase().includes(q) ||
        p.bName.toLowerCase().includes(q) ||
        (p.section?.toLowerCase().includes(q) ?? false)
    );
  });

  // Group by section so the index reads as a section-by-section
  // "head-to-head" view; competes-with edges land in their own bucket.
  const grouped = $derived.by(() => {
    const m = new Map<string, PairRow[]>();
    for (const p of filteredPairs) {
      const k = p.section ?? 'Explicit competes-with edges';
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(p);
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  });

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
    <label class="search">
      <span class="sr">Filter comparisons</span>
      <input
        type="search"
        placeholder="Filter by system or category name…"
        bind:value={query}
        autocomplete="off" />
    </label>
    {#if query.trim()}
      <p class="match-count">
        {filteredPairs.length} match{filteredPairs.length === 1 ? '' : 'es'}
        for &ldquo;{query.trim()}&rdquo;
      </p>
    {/if}
  </header>

  {#if grouped.length === 0}
    <p class="empty">No comparisons match &ldquo;{query.trim()}&rdquo;. Try a shorter query or a different name.</p>
  {/if}

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
    margin: 0 0 1rem;
  }
  .search {
    display: block;
    margin: 0 0 0.5rem;
  }
  .search input {
    width: 100%;
    box-sizing: border-box;
    background: #181818;
    color: #e8e8e8;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 0.55rem 0.8rem;
    font-size: 0.95rem;
    font-family: inherit;
  }
  .search input:focus {
    outline: none;
    border-color: #4a4a4a;
    background: #1c1c1c;
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  .match-count {
    margin: 0 0 1.5rem;
    font-size: 0.85rem;
    color: #888;
  }
  .empty {
    color: #888;
    font-style: italic;
    padding: 1.5rem 0;
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
