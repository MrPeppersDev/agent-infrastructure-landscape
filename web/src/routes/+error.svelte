<script lang="ts">
  // App-level error page. Replaces the old hand-authored static/404.html:
  // with the adapter-static SPA fallback (build/404.html, see
  // svelte.config.js) GitHub Pages serves the shell for unknown paths, the
  // client router finds no matching route, and this component renders —
  // same helpful entry-point map as before, now inside the site layout.
  import { base } from '$app/paths';
  import { page } from '$app/state';
</script>

<svelte:head>
  <title>Page not found — AI Agent Infrastructure Landscape</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<main class="wrap">
  <p class="code">{page.status} · {page.status === 404 ? 'Not found' : (page.error?.message ?? 'Error')}</p>
  <h1>That URL isn't in the catalog</h1>
  <p>
    It may have been renamed, removed, or never existed. The catalog covers 912 AI
    agent memory and infrastructure systems — try one of these entry points:
  </p>

  <h2>Hubs</h2>
  <ul>
    <li><a href="{base}/">Catalog</a> <span class="sub">— the full table view</span></li>
    <li><a href="{base}/findings">Findings</a> <span class="sub">— the five publishable headlines</span></li>
    <li><a href="{base}/systems">Systems</a> <span class="sub">— all 912 systems by section</span></li>
    <li><a href="{base}/category">Categories</a> <span class="sub">— 34 section landings</span></li>
    <li><a href="{base}/compare">Comparisons</a> <span class="sub">— 265 head-to-head pages</span></li>
    <li><a href="{base}/analyses">Analyses</a> <span class="sub">— derivation pages</span></li>
    <li><a href="{base}/about">About</a> <span class="sub">— how to read the catalog</span></li>
  </ul>

  <h2>Data &amp; feeds</h2>
  <ul>
    <li><a href="{base}/sitemap.xml">Sitemap</a> <span class="sub">— all crawlable URLs</span></li>
    <li><a href="{base}/feed.xml">Atom feed</a> <span class="sub">— most-recently verified systems</span></li>
    <li><a href="https://github.com/MrPeppersDev/agent-infrastructure-landscape">GitHub</a> <span class="sub">— raw landscape.json, issue tracker</span></li>
  </ul>
</main>

<style>
  .wrap {
    max-width: 640px;
    margin: 0 auto;
    padding: 4rem 1.5rem;
    color: #e6edf3;
    line-height: 1.55;
  }
  .code {
    color: #d4845f;
    font-size: 0.85rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-variant-numeric: tabular-nums;
    margin: 0 0 0.4rem;
  }
  h1 {
    font-size: 1.75rem;
    margin: 0 0 1rem;
    color: #f0f0f0;
    letter-spacing: -0.01em;
  }
  p {
    color: #c0c0c0;
    margin: 0 0 1.4rem;
  }
  h2 {
    font-size: 0.95rem;
    color: #e8e8e8;
    margin: 2rem 0 0.7rem;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.35rem;
  }
  ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  li {
    padding: 0.45rem 0;
    border-bottom: 1px solid #1a1a1a;
  }
  a {
    color: #d4845f;
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
  .sub {
    color: #8b949e;
    font-size: 0.85rem;
    margin-left: 0.4rem;
  }
</style>
