<script lang="ts">
  import { base } from '$app/paths';
  import { page } from '$app/state';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { itemListLd, breadcrumbLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';

  type Row = { id: string; name: string; short: string; tagline: string; audience: string; count: number; sections: number; attention: number; family: string | null };
  let { data }: { data: { silos: Row[]; total: number } } = $props();

  const families = $derived(data.silos.filter((s) => s.family));
  const crossCut = $derived(data.silos.filter((s) => !s.family));

  const ld = $derived([
    breadcrumbLd({ items: [{ name: 'Catalog', url: absoluteUrl('/') }, { name: 'Catalogs', url: absoluteUrl('/catalogs') }] }),
    itemListLd({ name: 'Catalogs', items: data.silos.map((s) => ({ name: s.name, url: absoluteUrl(`/catalogs/${s.id}`) })) })
  ]);
</script>

<SeoHead
  title="Catalogs — focused views of the AI agent stack ({data.total.toLocaleString('en-US')} systems)"
  description="One dataset, many views: agent memory, frameworks, retrieval, models and ops, research, coding agents, security, evals, voice and embodied agents, assistant memory and vertical agents. Each catalog shows the rows, columns and decision tools for one audience; the Atlas shows everything."
  path="/catalogs"
/>
<JsonLd data={ld} />

<article class="wrap">
  <header>
    <p class="crumbs"><a href="{base}/">Catalog</a> <span aria-hidden="true">›</span> <span>Catalogs</span></p>
    <h1>Catalogs</h1>
    <p class="lede">
      One dataset of {data.total.toLocaleString()} systems, as of {page.data.stats.dataAsOf}, viewed one audience at a time.
      Each catalog shows the rows, the columns and the decision tools that matter for its job, and nothing is left out:
      the <a href="{base}/">Atlas</a> is every system and every column in one table.
    </p>
  </header>

  <section>
    <h2>By layer of the stack</h2>
    <ul class="grid">
      {#each families as s (s.id)}
        <li>
          <a href="{base}/catalogs/{s.id}">
            <span class="name">{s.name}</span>
            <span class="n">{s.count.toLocaleString()} systems · {s.sections} sections{#if s.attention} · <em>{s.attention} need attention</em>{/if}</span>
            <span class="tag">{s.tagline}</span>
            <span class="aud">For {s.audience.replace(/\.$/, '').toLowerCase()}</span>
          </a>
        </li>
      {/each}
    </ul>
  </section>

  <section>
    <h2>By what you are building</h2>
    <p class="note">These cut across the layers. A system can appear in more than one.</p>
    <ul class="grid">
      {#each crossCut as s (s.id)}
        <li>
          <a href="{base}/catalogs/{s.id}">
            <span class="name">{s.name}</span>
            <span class="n">{s.count.toLocaleString()} systems · {s.sections} sections{#if s.attention} · <em>{s.attention} need attention</em>{/if}</span>
            <span class="tag">{s.tagline}</span>
            <span class="aud">For {s.audience.replace(/\.$/, '').toLowerCase()}</span>
          </a>
        </li>
      {/each}
    </ul>
  </section>

  <section class="atlas">
    <h2>The Atlas</h2>
    <p>
      <a href="{base}/">Every system in one table</a>, with every column behind the "All columns" toggle, every filter, export and comparison.
      Add a catalog of your own by editing <code>taxonomy/silos.json</code>: a list of sections, the columns to show first, and the tools that apply.
    </p>
  </section>
</article>

<style>
  .wrap { max-width: 1040px; margin: 0 auto; padding: 1.25rem 1rem 4rem; color: #d6d6d6; line-height: 1.55; }
  .crumbs { font-size: 0.85rem; color: #888; margin: 0 0 0.5rem; }
  .crumbs a { color: #8b949e; text-decoration: none; }
  h1 { font-size: 1.9rem; margin: 0 0 0.5rem; letter-spacing: -0.01em; }
  h2 { font-size: 1.15rem; margin: 2rem 0 0.6rem; color: #e6edf3; }
  .lede { color: #8b949e; max-width: 78ch; margin: 0; }
  .lede a, .atlas a { color: #58a6ff; }
  .note { color: #6e7681; font-size: 0.88rem; margin: 0 0 0.6rem; }
  .grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
  .grid a { display: grid; gap: 4px; padding: 14px 16px; border: 1px solid #30363d; border-radius: 10px; background: #161b22; color: inherit; text-decoration: none; height: 100%; }
  .grid a:hover { border-color: #58a6ff; }
  .name { font-weight: 600; color: #e6edf3; font-size: 1.02rem; }
  .n { font-size: 0.82rem; color: #8b949e; font-variant-numeric: tabular-nums; }
  .n em { color: #d29922; font-style: normal; }
  .tag { font-size: 0.9rem; color: #c9d1d9; }
  .aud { font-size: 0.8rem; color: #6e7681; }
  .atlas p { color: #c9d1d9; max-width: 78ch; }
  code { font-family: var(--font-mono); font-size: 0.85em; background: #1f242b; padding: 1px 5px; border-radius: 4px; }
</style>
