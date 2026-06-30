<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { itemListLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';

  type System = {
    id: string;
    name: string;
    tier: 1 | 2 | 3 | 4 | 5;
    section: string;
    type: string | null;
    desc: string;
  };

  let { data }: { data: { systems: System[] } } = $props();

  // Group by section so the index doubles as a coarse browse-by-category.
  const grouped = (() => {
    const m = new Map<string, System[]>();
    for (const s of data.systems) {
      const k = s.section;
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(s);
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  })();

  // ItemList JSON-LD over the first 50 entries — keeps the schema payload
  // bounded while still giving Google a typed list to crawl.
  const ldData = itemListLd({
    name: 'AI Agent Infrastructure systems',
    items: data.systems.slice(0, 50).map((s) => ({
      name: s.name,
      url: absoluteUrl(`/systems/${s.id}`)
    }))
  });
</script>

<SeoHead
  title="All Systems — AI Agent Infrastructure Landscape"
  description="Browse every AI agent memory system, framework, and research project in the landscape. {data.systems.length} entries grouped by section, each with a dedicated profile page."
  path="/systems"
  ogType="website"
/>
<JsonLd data={ldData} />

<article class="index">
  <header>
    <h1>All systems</h1>
    <p class="lede">
      {data.systems.length} entries in the AI Agent Infrastructure Landscape — every
      memory system, framework, library, and research project we track, grouped
      by where they sit in the architecture.
    </p>
  </header>

  {#each grouped as [section, systems]}
    <section>
      <h2>{section} <span class="count">({systems.length})</span></h2>
      <ul>
        {#each systems as s}
          <li>
            <a href="{base}/systems/{s.id}">{s.name}</a>
            <span class="tier">T{s.tier}</span>
            {#if s.type}<span class="type">· {s.type}</span>{/if}
            {#if s.desc}<p>{s.desc}</p>{/if}
          </li>
        {/each}
      </ul>
    </section>
  {/each}
</article>

<style>
  .index {
    max-width: 900px;
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
    font-size: 1.2rem;
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
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem 1.5rem;
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
    font-weight: 500;
  }
  li a:hover {
    text-decoration: underline;
  }
  .tier {
    margin-left: 0.4rem;
    color: #999;
    font-size: 0.85rem;
  }
  .type {
    color: #888;
    font-size: 0.85rem;
  }
  li p {
    margin: 0.25rem 0 0;
    color: #aaa;
    font-size: 0.9rem;
    line-height: 1.4;
  }
</style>
