<script lang="ts">
  import '../app.css';
  import { page } from '$app/state';
  import { base } from '$app/paths';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { websiteLd, organizationLd } from '$lib/seo/jsonld';

  let { children } = $props();
  let menu: HTMLDetailsElement | undefined = $state();

  // Site-wide entity markup. WebSite/SearchAction makes the SERP listing
  // eligible for a sitelinks search box; Organization plants the catalog
  // as a stable entity in the knowledge graph. Both emit on every page —
  // page-specific JSON-LD (Article, Dataset, BreadcrumbList, etc.) is
  // additive and lives on the individual routes.
  const siteLd = [websiteLd(), organizationLd()];

  // Primary nav: the six things people come for. Everything else (the
  // research views) lives under one "Research" menu so the bar stays
  // readable on a laptop.
  const routes = [
    { path: '/choose', label: 'Choose' },
    { path: '/check', label: 'Check stack' },
    { path: '/alternatives', label: 'Alternatives' },
    { path: '/', label: 'Catalog' },
    { path: '/compare', label: 'Compare' },
    { path: '/findings', label: 'Findings' }
  ];
  const research = [
    { path: '/systems', label: 'All systems' },
    { path: '/compatibility', label: 'Compatibility' },
    { path: '/compare/many', label: 'Compare up to 5' },
    { path: '/search', label: 'Ask the catalog' },
    { path: '/costs', label: 'Memory & vector cost calculator' },
    { path: '/benchmarks', label: 'Benchmarks' },
    { path: '/best', label: 'Best-of lists' },
    { path: '/leaderboards', label: 'Leaderboards' },
    { path: '/timeline', label: 'Timeline' },
    { path: '/sections', label: 'Sections' },
    { path: '/graph', label: 'Graph' },
    { path: '/lineages', label: 'Lineages' },
    { path: '/analyses', label: 'Analyses' },
    { path: '/data', label: 'Data & API' },
    { path: '/submit', label: 'Submit a system' },
    { path: '/about', label: 'About' }
  ];

  // Strip the base prefix from the current path for active-route matching.
  const relPath = $derived(
    (page.url.pathname.startsWith(base) ? page.url.pathname.slice(base.length) : page.url.pathname) || '/'
  );
</script>

<svelte:head>
  <link
    rel="alternate"
    type="application/atom+xml"
    title="AI Agent Infrastructure Landscape — recent activity"
    href="{base}/feed.xml"
  />
  <link rel="alternate" type="application/atom+xml" title="AI Agent Infrastructure Landscape — changes" href="{base}/changes.xml" />
</svelte:head>

<JsonLd data={siteLd} />

<nav class="topnav" aria-label="Primary">
  <a class="brand" href="{base}/">AI Agent Infrastructure</a>
  <ul>
    {#each routes as r}
      <li>
        <a
          href={r.path === '/' ? `${base}/` : `${base}${r.path}`}
          class:active={r.path === '/' ? relPath === '/' : relPath.startsWith(r.path)}
        >
          {r.label}
        </a>
      </li>
    {/each}
    <li class="more">
      <details bind:this={menu}>
        <summary class:active={research.some((r) => relPath.startsWith(r.path))}>Research ▾</summary>
        <ul class="menu">
          {#each research as r}
            <li><a href="{base}{r.path}" onclick={() => menu?.removeAttribute('open')} class:active={relPath.startsWith(r.path)}>{r.label}</a></li>
          {/each}
        </ul>
      </details>
    </li>
  </ul>
</nav>

<div class="page">
  {@render children?.()}
</div>

<style>
  .topnav {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 10px 16px;
    border-bottom: 1px solid #2a2a2a;
    background: #161616;
    position: sticky;
    top: 0;
    z-index: 50;
  }
  .topnav .brand {
    font-weight: 600;
    color: #e8e8e8;
    text-decoration: none;
    letter-spacing: -0.01em;
  }
  .topnav ul {
    display: flex;
    gap: 4px;
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .topnav a {
    color: #aaa;
    text-decoration: none;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 0.92rem;
  }
  .topnav a:hover {
    color: #e8e8e8;
    background: #202020;
  }
  .topnav summary {
    color: #aaa;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 0.92rem;
    cursor: pointer;
    list-style: none;
  }
  .topnav summary::-webkit-details-marker { display: none; }
  .topnav summary:hover, .topnav summary.active { color: #e8e8e8; background: #202020; }
  .more { position: relative; }
  .menu {
    position: absolute;
    right: 0;
    top: calc(100% + 6px);
    flex-direction: column;
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 6px !important;
    min-width: 190px;
    z-index: 60;
  }
  .menu a { display: block; white-space: nowrap; }
  .topnav { flex-wrap: wrap; }
  .topnav ul { flex-wrap: wrap; }
  .topnav a.active {
    color: #e8e8e8;
    background: #242424;
  }

  /* Full-bleed page for the table view. The narrow centered look from
     the landing page (#8) doesn't fit a 67-column scrollable table —
     we want every available pixel for the data. */
  .page {
    width: 100%;
    padding: 16px 16px 0;
  }
</style>
