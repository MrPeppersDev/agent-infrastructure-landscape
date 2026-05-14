<script lang="ts">
  import { base } from '$app/paths';

  // Hub page for the six analytical views. Each card links to a
  // sub-route owned by its own +page.svelte. Until those routes land
  // their links will 404 — that's expected during build-out.
  const analyses = [
    {
      slug: 'influence',
      title: 'Influence vs adoption',
      summary:
        'Every system plotted on two axes: inbound citations (academic influence) × inbound integrations (commercial adoption). Surfaces research orphans, engineering wins, and the diagonal of both-cited-and-adopted.'
    },
    {
      slug: 'survivorship',
      title: 'Survivorship map',
      summary:
        'Active / Stale (>12mo) / Abandoned (>24mo). Cross-references latest-release and code-release against created date. Filters downstream analysis to alive systems without losing the dead-but-influential rows.'
    },
    {
      slug: 'benchmarks',
      title: 'Benchmark coverage matrix',
      summary:
        'For each headline memory benchmark (LongMemEval, LoCoMo, BABILong, ConvoMem, RULER, MemoryBench), which systems published a score? Reveals which benchmarks have critical mass.'
    },
    {
      slug: 'benchmark-integrity',
      title: 'Benchmark integrity',
      summary:
        'Companion to coverage. Classifies every benchmark mention as peer-reviewed / independently-verified / vendor-claimed / disputed / unverifiable, exposes gaming patterns, and surfaces the canonical disputed case (Mem0 vs Zep on LoCoMo).'
    },
    {
      slug: 'product-benchmark-matrix',
      title: 'Product × benchmark coverage',
      summary:
        'Pivot of the benchmark coverage view, flipped from benchmark-centric to product-centric. Rows are products, columns are benchmarks, cells are coloured by integrity tier. The "refuses to publish" filter surfaces every product that mentions benchmarks but has zero peer-reviewed citations behind them.'
    },
    {
      slug: 'benchmark-trust',
      title: 'Benchmark trust leaderboard',
      summary:
        'Pivots the integrity classifications into a single composite trust score per benchmark. Sortable leaderboard with top-5 trusted / most-gamed callouts and per-benchmark drilldowns showing which systems contributed to each integrity bucket.'
    },
    {
      slug: 'archetypes',
      title: 'Taxonomy archetypes',
      summary:
        'Clusters systems by their 7-axis taxonomy fingerprint. Surfaces recurring recipes (vector+semantic+persistent; graph+structural+temporal; file+text+manual; etc.) richer than any single axis.'
    },
    {
      slug: 'vocabulary',
      title: 'Vocabulary drift',
      summary:
        'Quarterly occurrence of key memory terms (episodic, working, parametric, agentic, lifelong, world-model) in descriptions and claims. Reveals what is emerging vs declining at the concept level.'
    },
    {
      slug: 'forecast',
      title: 'Lineage forecast',
      summary:
        'For each detected lineage, what does the leading edge tell us about where the next paper/product is likely coming from? Pairs with the influence-vs-adoption view to anticipate Q3 additions.'
    },
    {
      slug: 'trajectory',
      title: 'Trajectory — used vs growing/dying',
      summary:
        'Combines funding cadence, release recency, GH stars, mindshare/citations, and lineage membership into one velocity story per record. Five panels: cohort, substrate-dependency risk, consolidation candidates, billion-$ candidates, dying candidates.'
    }
  ];
</script>

<svelte:head>
  <title>Analyses · Memory Landscape</title>
</svelte:head>

<header class="hub-header">
  <h1>Analyses</h1>
  <p>
    Six analytical views on top of the catalog substrate. Each surfaces a
    pattern that's hard to see in the main table — influence dynamics,
    survivorship, benchmark coverage, taxonomy recipes, vocabulary drift,
    forward projection.
  </p>
</header>

<ul class="cards">
  {#each analyses as a}
    <li class="card">
      <h2><a href="{base}/analyses/{a.slug}">{a.title}</a></h2>
      <p>{a.summary}</p>
    </li>
  {/each}
</ul>

<style>
  .hub-header {
    max-width: 760px;
    margin: 24px 0 32px;
  }
  .hub-header h1 {
    margin: 0 0 12px;
    font-size: 1.75rem;
    color: #e8e8e8;
    letter-spacing: -0.01em;
  }
  .hub-header p {
    margin: 0;
    color: #aaa;
    line-height: 1.55;
  }
  .cards {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
    max-width: 1100px;
  }
  .card {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 18px 20px;
  }
  .card h2 {
    margin: 0 0 8px;
    font-size: 1.05rem;
    color: #e8e8e8;
    font-weight: 600;
  }
  .card h2 a {
    color: inherit;
    text-decoration: none;
  }
  .card h2 a:hover {
    color: #d4845f;
  }
  .card p {
    margin: 0;
    color: #aaa;
    font-size: 0.92rem;
    line-height: 1.55;
  }
</style>
