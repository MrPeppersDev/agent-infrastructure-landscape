<script lang="ts">
  import '../app.css';
  import { page } from '$app/state';
  import { base } from '$app/paths';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { websiteLd, organizationLd } from '$lib/seo/jsonld';

  let { children } = $props();

  // Site-wide entity markup. WebSite/SearchAction makes the SERP listing
  // eligible for a sitelinks search box; Organization plants the catalog
  // as a stable entity in the knowledge graph. Both emit on every page —
  // page-specific JSON-LD (Article, Dataset, BreadcrumbList, etc.) is
  // additive and lives on the individual routes.
  const siteLd = [websiteLd(), organizationLd()];

  const routes = [
    { path: '/', label: 'Table' },
    { path: '/findings', label: 'Findings' },
    { path: '/systems', label: 'Systems' },
    { path: '/timeline', label: 'Timeline' },
    { path: '/leaderboards', label: 'Leaderboards' },
    { path: '/sections', label: 'Sections' },
    { path: '/graph', label: 'Graph' },
    { path: '/lineages', label: 'Lineages' },
    { path: '/analyses', label: 'Analyses' },
    { path: '/submit', label: 'Submit' },
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
