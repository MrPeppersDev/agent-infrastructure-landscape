<script lang="ts">
  // Shared shell for the recommender surfaces (Phase 2 / Gate 3).
  // Gate 4 will add a second sub-route under the same shell.

  import { page } from '$app/state';
  import { base } from '$app/paths';

  let { children } = $props();

  const subroutes = [
    { path: '/recommend/between', label: 'Between anchors' },
    { path: '/recommend/by-constraints', label: 'By constraints' }
  ];

  const relPath = $derived(
    (page.url.pathname.startsWith(base)
      ? page.url.pathname.slice(base.length)
      : page.url.pathname) || '/'
  );
</script>

<header class="hub-header">
  <h1>Recommender</h1>
  <p>
    Phase 2 recommender surfaces — positioning (anchor mode) and
    constraint-matching (Gate 4). Cells with LLM-unverified provenance are
    excluded from scoring and surfaced as caveats per spec §3.4.
  </p>
  {#if subroutes.length > 1}
    <nav class="subnav" aria-label="Recommender modes">
      {#each subroutes as r}
        <a
          href={`${base}${r.path}`}
          class:active={relPath.startsWith(r.path)}>{r.label}</a>
      {/each}
    </nav>
  {/if}
</header>

{@render children?.()}

<style>
  .hub-header {
    max-width: 1100px;
    margin: 24px 0 16px;
  }
  .hub-header h1 {
    margin: 0 0 8px;
    font-size: 1.75rem;
    color: #e8e8e8;
    letter-spacing: -0.01em;
  }
  .hub-header p {
    margin: 0 0 16px;
    color: #aaa;
    line-height: 1.55;
    max-width: 760px;
  }
  .subnav {
    display: flex;
    gap: 4px;
  }
  .subnav a {
    color: #aaa;
    text-decoration: none;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.92rem;
    border: 1px solid #2a2a2a;
  }
  .subnav a:hover {
    color: #e8e8e8;
    background: #202020;
  }
  .subnav a.active {
    color: #e8e8e8;
    background: #242424;
    border-color: #3a3a3a;
  }
</style>
