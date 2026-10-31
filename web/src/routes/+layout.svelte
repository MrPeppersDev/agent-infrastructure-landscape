<script lang="ts">
  import '../app.css';
  import { page } from '$app/state';
  import { base } from '$app/paths';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { websiteLd, organizationLd } from '$lib/seo/jsonld';
  import { getSilos } from '$lib/silos';

  let { children } = $props();
  let nav: HTMLElement | undefined = $state();
  let mobileOpen = $state(false);
  // Each group is a <details> dropdown: opening one closes the others, and
  // a click outside, Escape or the pointer leaving closes it, so a menu
  // never sits open over the page (#328).
  function openMenus(): HTMLDetailsElement[] {
    return [...(nav?.querySelectorAll('details[open]') ?? [])] as HTMLDetailsElement[];
  }
  function closeMenu(e: Event) {
    const escape = e instanceof KeyboardEvent && e.key === 'Escape';
    if (!(e instanceof KeyboardEvent) || escape) {
      for (const d of openMenus()) if (escape || !d.contains(e.target as Node)) d.removeAttribute('open');
    }
    if (escape || (e.type === 'click' && !nav?.contains(e.target as Node))) mobileOpen = false;
  }
  function onToggle(e: Event) {
    const d = e.currentTarget as HTMLDetailsElement;
    if (d.open) for (const o of openMenus()) if (o !== d) o.removeAttribute('open');
  }
  function navigated() {
    for (const d of openMenus()) d.removeAttribute('open');
    mobileOpen = false;
  }

  // Site-wide entity markup. WebSite/SearchAction makes the SERP listing
  // eligible for a sitelinks search box; Organization plants the catalog
  // as a stable entity in the knowledge graph. Both emit on every page —
  // page-specific JSON-LD (Article, Dataset, BreadcrumbList, etc.) is
  // additive and lives on the individual routes.
  const siteLd = [websiteLd(), organizationLd()];

  // Navigation in four groups (#332): deciding on a stack, browsing the
  // catalog, the research views, and the data itself.
  const groups: { label: string; items: { path: string; label: string }[] }[] = [
    {
      label: 'Decide',
      items: [
        { path: '/build', label: 'Build a stack' },
        { path: '/choose', label: 'Choose a component' },
        { path: '/check', label: 'Check your stack' },
        { path: '/compatibility', label: 'Compatibility' },
        { path: '/costs', label: 'Costs' }
      ]
    },
    {
      label: 'Catalogs',
      items: [
        { path: '/catalogs', label: 'All catalogs' },
        ...getSilos().map((s) => ({ path: `/catalogs/${s.id}`, label: s.name }))
      ]
    },
    {
      label: 'Browse',
      items: [
        { path: '/', label: 'Atlas (every system)' },
        { path: '/search', label: 'Ask the catalog' },
        { path: '/alternatives', label: 'Alternatives' },
        { path: '/compare', label: 'Compare' },
        { path: '/best', label: 'Best-of lists' }
      ]
    },
    {
      label: 'Research',
      items: [
        { path: '/changes', label: 'What changed' },
        { path: '/findings', label: 'Findings' },
        { path: '/analyses', label: 'Analyses' },
        { path: '/benchmarks', label: 'Benchmarks' },
        { path: '/leaderboards', label: 'Leaderboards' },
        { path: '/graph', label: 'Graph' },
        { path: '/timeline', label: 'Timeline' },
        { path: '/lineages', label: 'Lineages' },
        { path: '/sections', label: 'Sections' }
      ]
    },
    {
      label: 'Data',
      items: [
        { path: '/data', label: 'Data & API' },
        { path: '/submit', label: 'Submit a system' },
        { path: '/about', label: 'About' }
      ]
    }
  ];
  const href = (path: string) => (path === '/' ? `${base}/` : `${base}${path}`);
  const isActive = (path: string, rel: string) =>
    path === '/' ? rel === '/' : path === '/catalogs' ? rel === '/catalogs' : rel === path || rel.startsWith(path + '/');

  // Strip the base prefix from the current path for active-route matching.
  const relPath = $derived(
    (page.url.pathname.startsWith(base) ? page.url.pathname.slice(base.length) : page.url.pathname) || '/'
  );
</script>

<svelte:window onclick={closeMenu} onkeydown={closeMenu} />

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

<nav class="topnav" aria-label="Primary" bind:this={nav}>
  <a class="brand" href="{base}/" onclick={navigated}>AI Agent Stack</a>
  <button
    type="button"
    class="burger"
    aria-expanded={mobileOpen}
    aria-controls="nav-panel"
    onclick={() => (mobileOpen = !mobileOpen)}
  >
    {mobileOpen ? 'Close' : 'Menu'}
  </button>
  <ul class="groups">
    {#each groups as g}
      <li class="group">
        <details ontoggle={onToggle} onmouseleave={(e) => (e.currentTarget as HTMLDetailsElement).removeAttribute('open')}>
          <summary class:active={g.items.some((r) => isActive(r.path, relPath))}>{g.label} <span aria-hidden="true">▾</span></summary>
          <ul class="menu">
            {#each g.items as r}
              <li><a href={href(r.path)} onclick={navigated} class:active={isActive(r.path, relPath)}>{r.label}</a></li>
            {/each}
          </ul>
        </details>
      </li>
    {/each}
  </ul>
  {#if mobileOpen}
    <div id="nav-panel" class="panel">
      {#each groups as g}
        <p class="panel-head">{g.label}</p>
        <ul>
          {#each g.items as r}
            <li><a href={href(r.path)} onclick={navigated} class:active={isActive(r.path, relPath)}>{r.label}</a></li>
          {/each}
        </ul>
      {/each}
    </div>
  {/if}
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
    white-space: nowrap;
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
    white-space: nowrap;
  }
  .topnav summary::-webkit-details-marker { display: none; }
  .topnav summary:hover, .topnav summary.active { color: #e8e8e8; background: #202020; }
  .group { position: relative; }
  .menu {
    position: absolute;
    left: 0;
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
  .topnav a.active {
    color: #e8e8e8;
    background: #242424;
  }
  .burger {
    display: none;
    margin-left: auto;
    font: inherit;
    font-size: 0.9rem;
    color: #e8e8e8;
    background: #202020;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 5px 12px;
    cursor: pointer;
  }

  .panel { display: none; }

  /* Phones: one row with the brand and a menu button; the groups open as
     one stacked panel with every item visible. */
  @media (max-width: 767px) {
    .topnav { flex-wrap: wrap; gap: 8px; }
    .burger { display: inline-block; }
    .topnav .groups { display: none; }
    .panel { display: block; width: 100%; max-height: 75vh; overflow-y: auto; padding-bottom: 6px; }
    .panel ul { flex-wrap: wrap; }
    .panel-head { margin: 8px 10px 2px; color: #777; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
  }

  /* Full-bleed page for the table view. The narrow centered look from
     the landing page (#8) doesn't fit a 67-column scrollable table —
     we want every available pixel for the data. */
  .page {
    width: 100%;
    padding: 16px 16px 0;
  }
</style>
