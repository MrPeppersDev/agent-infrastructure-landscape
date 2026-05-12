<script lang="ts">
  import '../app.css';
  import { page } from '$app/state';

  let { children } = $props();

  const routes = [
    { href: '/', label: 'Table' },
    { href: '/timeline', label: 'Timeline' },
    { href: '/leaderboards', label: 'Leaderboards' },
    { href: '/sections', label: 'Sections' },
    { href: '/graph', label: 'Graph' },
    { href: '/lineages', label: 'Lineages' }
  ];
</script>

<nav class="topnav" aria-label="Primary">
  <a class="brand" href="/">Memory Landscape</a>
  <ul>
    {#each routes as r}
      <li>
        <a
          href={r.href}
          class:active={r.href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(r.href)}
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
