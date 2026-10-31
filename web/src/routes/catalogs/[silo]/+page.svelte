<script lang="ts">
  import { base } from '$app/paths';
  import { page } from '$app/state';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { itemListLd, breadcrumbLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';
  import { LIFECYCLE_LABEL, LIFECYCLE_TONE, LIFECYCLE_ORDER } from '$lib/lifecycle-labels';
  import type { Silo } from '$lib/silos';
  import type { StackStatus } from '../../../../../mcp/src/stack-check';

  type Top = { id: string; name: string; tier: number; type: string | null; lifecycle: StackStatus; inbound: number };
  let {
    data
  }: {
    data: {
      silo: Silo;
      count: number;
      lifecycle: Partial<Record<StackStatus, number>>;
      attention: number;
      tiers: number[];
      sections: { name: string; slug: string; count: number }[];
      top: Top[];
      recent: { date: string; id: string; name: string; text: string }[];
      bestOf: { slug: string; title: string; count: number }[];
      exportId: string;
      others: { id: string; short: string }[];
    };
  } = $props();

  const s = $derived(data.silo);
  const path = $derived(`/catalogs/${s.id}`);
  const lifeRows = $derived(LIFECYCLE_ORDER.filter((k) => (data.lifecycle[k] ?? 0) > 0).map((k) => ({ k, n: data.lifecycle[k] ?? 0 })));
  const ld = $derived([
    breadcrumbLd({ items: [{ name: 'Catalog', url: absoluteUrl('/') }, { name: 'Catalogs', url: absoluteUrl('/catalogs') }, { name: s.name, url: absoluteUrl(path) }] }),
    itemListLd({ name: s.name, items: data.top.map((t) => ({ name: t.name, url: absoluteUrl(`/systems/${t.id}`) })) })
  ]);
</script>

<SeoHead
  title="{s.name} — {data.count.toLocaleString('en-US')} systems, compared with sources"
  description="{s.tagline} {data.count.toLocaleString('en-US')} systems across {data.sections.length} sections, with lifecycle status, the columns that matter for {s.audience.replace(/\.$/, '').toLowerCase()}, decision tools and open data."
  path={path}
/>
<JsonLd data={ld} />

<article class="wrap">
  <header>
    <p class="crumbs">
      <a href="{base}/">Catalog</a> <span aria-hidden="true">›</span>
      <a href="{base}/catalogs">Catalogs</a> <span aria-hidden="true">›</span>
      <span>{s.name}</span>
    </p>
    <nav class="switch" aria-label="Other catalogs">
      {#each data.others as o (o.id)}<a href="{base}/catalogs/{o.id}">{o.short}</a>{/each}
      <a href="{base}/" class="atlas">Atlas</a>
    </nav>
    <h1>{s.name}</h1>
    <p class="tagline">{s.tagline} <span class="aud">For {s.audience.replace(/\.$/, '').toLowerCase()}.</span></p>
    <p class="desc">{s.description}</p>
    <p class="stats">
      <strong>{data.count.toLocaleString()}</strong> systems ·
      <strong>{data.sections.length}</strong> sections ·
      {#if data.attention}<strong class="warn">{data.attention}</strong> acquired, archived, stale or shut down ·{/if}
      data as of {page.data.stats.dataAsOf}
    </p>
    <p class="cta">
      <a class="primary" href="{base}{path}/browse">Browse the table →</a>
      <a href="{base}/api/catalogs/{data.exportId}.json">JSON</a> ·
      <a href="{base}/api/catalogs/{data.exportId}.csv">CSV</a>
    </p>
  </header>

  <section>
    <h2>Decide</h2>
    <ul class="tiles">
      {#each s.decide as d}
        <li><a href="{base}{d.path}"><strong>{d.label}</strong>{#if d.blurb}<span>{d.blurb}</span>{/if}</a></li>
      {/each}
    </ul>
  </section>

  <div class="cols">
    <section>
      <h2>Most referenced</h2>
      <p class="note">Lowest tier first, then by how many other systems in the catalog reference each one.</p>
      <ol class="top">
        {#each data.top as t (t.id)}
          <li>
            <a href="{base}/systems/{t.id}">{t.name}</a>
            <span class="tier">T{t.tier}</span>
            {#if t.lifecycle !== 'active'}<span class="life {LIFECYCLE_TONE[t.lifecycle]}">{LIFECYCLE_LABEL[t.lifecycle]}</span>{/if}
            {#if t.type}<span class="type">{t.type}</span>{/if}
          </li>
        {/each}
      </ol>
      <p class="more"><a href="{base}{path}/browse">All {data.count.toLocaleString()} in the table →</a></p>
    </section>

    <section>
      <h2>Sections</h2>
      <ul class="plain">
        {#each data.sections as sec (sec.name)}
          <li><a href="{base}/category/{sec.slug}">{sec.name}</a> <span class="n">{sec.count}</span></li>
        {/each}
      </ul>

      <h2>Lifecycle</h2>
      <ul class="plain">
        {#each lifeRows as l (l.k)}
          <li><span class="life {LIFECYCLE_TONE[l.k]}">{LIFECYCLE_LABEL[l.k]}</span> <span class="n">{l.n}</span></li>
        {/each}
      </ul>
      <p class="note">Tiers: {data.tiers.map((n, i) => `T${i + 1} ${n}`).join(' · ')}</p>
    </section>
  </div>

  {#if data.recent.length}
    <section>
      <h2>Recently changed</h2>
      <ul class="recent">
        {#each data.recent as e (e.date + e.id + e.text)}
          <li><time datetime={e.date}>{e.date}</time> <a href="{base}/systems/{e.id}">{e.name}</a> <span>{e.text}</span></li>
        {/each}
      </ul>
      <p class="more"><a href="{base}/changes">Everything that changed →</a></p>
    </section>
  {/if}

  <div class="cols">
    <section>
      <h2>Research</h2>
      <ul class="plain">
        {#each s.research as r}<li><a href="{base}{r.path}">{r.label}</a></li>{/each}
        {#each data.bestOf as b (b.slug)}<li><a href="{base}/best/{b.slug}">{b.title}</a> <span class="n">{b.count}</span></li>{/each}
      </ul>
    </section>
    <section>
      <h2>Data and tools</h2>
      <ul class="plain">
        <li><a href="{base}/api/catalogs/{data.exportId}.json">JSON</a> · <a href="{base}/api/catalogs/{data.exportId}.csv">CSV</a>, flattened, one row per system, CC-BY-4.0</li>
        <li>MCP tools: {#each s.mcpTools as t, i}{i ? ', ' : ''}<code>{t}</code>{/each}</li>
        <li>CLI: {#each s.cli as c, i}{i ? ' · ' : ''}<code>{c}</code>{/each}</li>
        <li><a href="{base}/data">Data &amp; API</a> · <a href="{base}/submit">Submit a system</a></li>
      </ul>
    </section>
  </div>
</article>

<style>
  .wrap { max-width: 1040px; margin: 0 auto; padding: 1.25rem 1rem 4rem; color: #d6d6d6; line-height: 1.55; }
  .crumbs { font-size: 0.85rem; color: #888; margin: 0 0 0.5rem; }
  .crumbs a { color: #8b949e; text-decoration: none; }
  .switch { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 0.9rem; }
  .switch a { font-size: 0.78rem; color: #8b949e; border: 1px solid #30363d; border-radius: 999px; padding: 2px 10px; text-decoration: none; }
  .switch a:hover { color: #e6edf3; border-color: #58a6ff; }
  .switch a.atlas { color: #58a6ff; border-color: #1f6feb; }
  h1 { font-size: 1.9rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; }
  h2 { font-size: 1.1rem; margin: 1.6rem 0 0.5rem; color: #e6edf3; }
  .tagline { margin: 0; color: #c9d1d9; }
  .aud { color: #6e7681; }
  .desc { color: #8b949e; max-width: 78ch; margin: 0.5rem 0 0; }
  .stats { margin: 0.8rem 0 0; color: #8b949e; font-size: 0.9rem; font-variant-numeric: tabular-nums; }
  .stats strong { color: #e6edf3; }
  .stats .warn { color: #d29922; }
  .cta { margin: 0.8rem 0 0; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .cta a { color: #58a6ff; }
  .cta .primary { background: #1f6feb; color: #fff; text-decoration: none; padding: 7px 14px; border-radius: 8px; font-weight: 600; }
  .tiles { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }
  .tiles a { display: grid; gap: 2px; padding: 10px 14px; border: 1px solid #1f6feb; border-radius: 10px; background: #0f1b2d; color: inherit; text-decoration: none; height: 100%; }
  .tiles a:hover { background: #13223a; }
  .tiles strong { color: #58a6ff; }
  .tiles span { font-size: 0.85rem; color: #8b949e; }
  .cols { display: grid; grid-template-columns: 1.4fr 1fr; gap: 28px; }
  @media (max-width: 760px) { .cols { grid-template-columns: 1fr; } }
  .note { color: #6e7681; font-size: 0.85rem; margin: 0 0 0.5rem; }
  .top { margin: 0; padding-left: 1.3rem; }
  .top li { margin: 4px 0; }
  .top a, .plain a, .recent a, .more a { color: #58a6ff; text-decoration: none; }
  .top a:hover, .plain a:hover, .recent a:hover { text-decoration: underline; }
  .tier { font-size: 0.72rem; color: #8b949e; border: 1px solid #30363d; border-radius: 4px; padding: 0 4px; margin-left: 6px; }
  .type { display: block; font-size: 0.82rem; color: #8b949e; }
  .life { font-size: 0.72rem; border-radius: 4px; padding: 0 5px; margin-left: 6px; }
  .life.ok { color: #3fb950; background: rgba(63, 185, 80, 0.12); }
  .life.info { color: #58a6ff; background: rgba(88, 166, 255, 0.12); }
  .life.warn { color: #d29922; background: rgba(210, 153, 34, 0.14); }
  .life.bad { color: #f85149; background: rgba(248, 81, 73, 0.14); }
  .plain { list-style: none; margin: 0; padding: 0; }
  .plain li { margin: 3px 0; }
  .n { color: #6e7681; font-size: 0.82rem; font-variant-numeric: tabular-nums; }
  .recent { list-style: none; margin: 0; padding: 0; }
  .recent li { margin: 4px 0; font-size: 0.92rem; }
  .recent time { color: #6e7681; font-variant-numeric: tabular-nums; margin-right: 6px; }
  .recent span { color: #8b949e; }
  .more { margin: 0.5rem 0 0; font-size: 0.9rem; }
  code { font-family: var(--font-mono); font-size: 0.82em; background: #1f242b; padding: 1px 5px; border-radius: 4px; }
</style>
