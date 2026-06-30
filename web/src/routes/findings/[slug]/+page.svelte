<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { articleLd, breadcrumbLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';
  import type { Finding } from '$lib/findings';

  let {
    data
  }: { data: { finding: Finding; others: Finding[] } } = $props();

  const f = data.finding;
  const routePath = `/findings/${f.slug}`;

  const ldData = [
    articleLd({
      headline: f.headline,
      description: f.metaDescription,
      url: absoluteUrl(routePath)
    }),
    breadcrumbLd({
      items: [
        { name: 'Catalog', url: absoluteUrl('/') },
        { name: 'Findings', url: absoluteUrl('/findings') },
        { name: f.headline, url: absoluteUrl(routePath) }
      ]
    })
  ];
</script>

<SeoHead
  title="{f.headline} — AI Agent Memory Findings"
  description={f.metaDescription}
  path={routePath}
  ogType="article"
/>
<JsonLd data={ldData} />

<article class="finding">
  <header>
    <p class="breadcrumbs">
      <a href="{base}/">Catalog</a>
      <span aria-hidden="true">›</span>
      <a href="{base}/findings">Findings</a>
      <span aria-hidden="true">›</span>
      <span>Finding #{f.n}</span>
    </p>
    <p class="kicker">Finding #{f.n} of 5</p>
    <h1>{f.headline}</h1>
    <p class="figure">{f.figure}</p>
  </header>

  <section class="body">
    {#each f.body as para}
      <p>{para}</p>
    {/each}
  </section>

  <section class="deepdive">
    <h2>Go deeper</h2>
    <p>
      <a class="deep-link" href="{base}{f.link.href}">{f.link.label} &rarr;</a>
    </p>
    <p class="source">{f.source}</p>
  </section>

  <section class="others">
    <h2>Other findings</h2>
    <ul>
      {#each data.others as o}
        <li>
          <a href="{base}/findings/{o.slug}">#{o.n}. {o.headline}</a>
          <span class="fig">{o.figure}</span>
        </li>
      {/each}
    </ul>
  </section>
</article>

<style>
  .finding {
    max-width: 720px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    color: #d6d6d6;
    line-height: 1.65;
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
  .kicker {
    color: #d4845f;
    font-size: 0.85rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin: 0 0 0.3rem;
    font-variant-numeric: tabular-nums;
  }
  h1 {
    margin: 0 0 0.8rem;
    color: #f0f0f0;
    font-size: 1.9rem;
    line-height: 1.25;
  }
  .figure {
    color: #d4845f;
    font-size: 1rem;
    margin: 0 0 2rem;
    font-variant-numeric: tabular-nums;
  }
  .body p {
    color: #d6d6d6;
    margin: 0 0 1.2rem;
    font-size: 1.02rem;
  }
  h2 {
    color: #e8e8e8;
    font-size: 1.15rem;
    margin: 2.5rem 0 0.7rem;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.3rem;
  }
  .deep-link {
    color: #d4845f;
    text-decoration: none;
    font-weight: 500;
  }
  .deep-link:hover {
    text-decoration: underline;
  }
  .source {
    color: #888;
    font-size: 0.88rem;
    font-family: ui-monospace, SFMono-Regular, monospace;
    margin: 0.3rem 0 0;
  }
  .others ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .others li {
    padding: 0.55rem 0;
    border-bottom: 1px solid #1f1f1f;
  }
  .others a {
    color: #d4845f;
    text-decoration: none;
    font-weight: 500;
  }
  .others a:hover {
    text-decoration: underline;
  }
  .others .fig {
    display: block;
    color: #888;
    font-size: 0.85rem;
    margin-top: 0.15rem;
    font-variant-numeric: tabular-nums;
  }
</style>
