<script lang="ts">
  let { data } = $props();
</script>

<svelte:head>
  <title>Memory Systems Landscape</title>
</svelte:head>

<header>
  <h1>Memory Systems Landscape</h1>
  <p class="subtitle">
    A navigable catalog of AI memory systems, frameworks, papers, products,
    and theoretical proposals — built as the foundation for downstream
    comparative and trend analysis.
  </p>
</header>

<section class="stats" aria-label="Catalog statistics">
  <div class="stat">
    <span class="num">{data.recordCount.toLocaleString()}</span>
    <span class="label">systems catalogued</span>
  </div>
  <div class="stat">
    <span class="num">{data.edgeCount.toLocaleString()}</span>
    <span class="label">edges between systems</span>
  </div>
</section>

<section class="teaser">
  <h2>Under construction</h2>
  <p>
    Table view, filters, knowledge graph — the navigability layer is being
    built phase by phase. This page is a proof-of-life that the data wiring
    works; the table arrives in <a
      href="https://github.com/MrPeppersDev/memory-analysis-program/issues/9"
      >issue #9</a
    >.
  </p>
  <ul>
    <li>Phase 2 — virtualised table, search, filters, multi-sort</li>
    <li>Phase 3 — created-date timeline, top-N leaderboards</li>
    <li>Phase 4 — Cytoscape force-directed knowledge graph</li>
    <li>Phase 5 — detail/compare modals, CSV export, GitHub Pages deploy</li>
  </ul>
</section>

<footer>
  <p>
    <a href="https://github.com/MrPeppersDev/memory-analysis-program">
      Source on GitHub
    </a>
    ·
    <a
      href="https://github.com/MrPeppersDev/memory-analysis-program/blob/main/docs/SCHEMA.md"
    >
      Schema
    </a>
    ·
    <a
      href="https://github.com/MrPeppersDev/memory-analysis-program/blob/main/docs/BUILD-PLAN.md"
    >
      Build plan
    </a>
  </p>
</footer>

<style>
  header {
    margin-bottom: var(--space-5);
  }

  h1 {
    font-size: 2.25rem;
    letter-spacing: -0.02em;
  }

  .subtitle {
    color: var(--c-muted);
    font-size: 1.05rem;
    max-width: 60ch;
  }

  .stats {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
    margin-bottom: var(--space-5);
  }

  .stat {
    flex: 1 1 220px;
    padding: var(--space-3) var(--space-4);
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
  }

  .stat .num {
    display: block;
    font-size: 2.25rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    line-height: 1.1;
  }

  .stat .label {
    display: block;
    color: var(--c-muted);
    margin-top: var(--space-1);
  }

  .teaser h2 {
    font-size: 1.15rem;
    color: var(--c-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
  }

  .teaser ul {
    padding-left: var(--space-3);
    color: var(--c-muted);
  }

  .teaser li {
    margin: var(--space-1) 0;
  }

  footer {
    margin-top: var(--space-6);
    padding-top: var(--space-3);
    border-top: 1px solid var(--c-border);
    color: var(--c-muted);
    font-size: 0.9rem;
  }
</style>
