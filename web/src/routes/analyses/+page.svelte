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
        'Every system plotted on two axes: inbound citations (academic influence) × inbound integrations (commercial adoption). Surfaces research orphans, engineering wins, and the diagonal of both-cited-and-adopted. Now includes Brandes betweenness + k-core decomposition — the "bridge surprises" callout flags records that hold the graph together without showing up in raw citation counts, and the nucleus callout lists the densest mutually-connected substrate.'
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
      slug: 'observability',
      title: 'Observability coverage',
      summary:
        'The #1 demand-signal question in agent infrastructure (807 HN hits, 89% LangChain-survey adoption, 6/7 published surveys). Matrix of products × observability tools (LangSmith, OpenTelemetry, Datadog, Helicone, Weave, Langfuse, Arize). Top ~100 priority rows backfilled; the rest surfaced as "unknown" so the coverage gap is explicit.'
    },
    {
      slug: 'cost-economics',
      title: 'Cost-economics & token-governance',
      summary:
        'The #2 demand-signal question (171 HN mentions last 12mo, Sequoia framing on inference-cost sustainability, Datadog 2026 found 69% of input tokens are system-prompt overhead). Matrix of products × cost-control features (token budget, prompt caching, semantic caching, batch API, model routing, streaming-only, cost attribution). Per-row governance score (0/7 → 7/7). Top ~100 priority rows backfilled.'
    },
    {
      slug: 'eval-gap',
      title: 'Evaluation gap (89% obs vs 52% evals)',
      summary:
        'The next frontier after observability. LangChain State of Agent Engineering 2025: 89% have observability adopted but only 52% have evals — a 37-point structural gap. This view is the first catalog-level surface for it: side-by-side obs vs eval adoption %, plus an "eval orphan" filter that surfaces products with observability ≥1 tool but zero eval tools. Matrix of products × eval tools (LangSmith Evals, Braintrust, W&B Agent Eval, Helicone Evals, Custom test harness, Human-in-loop, Prod traffic replay). Top ~100 priority rows backfilled (same set as observability + cost-economics so cross-cuts work cleanly).'
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
        'Combines funding cadence, release recency, GH stars, mindshare/citations, and lineage membership into one velocity story per record. Six panels: cohort, substrate-dependency risk, consolidation candidates, billion-$ candidates, dying candidates, and a BIMATEM-style logistic S-curve fit per row that reads pre-growth / growth / saturation / decline straight off the inflection date — the math the Gartner Hype Cycle waves at without ever publishing.'
    },
    {
      slug: 'co-citation',
      title: 'Co-citation & bibliographic coupling',
      summary:
        'Bibliometric staple since Henry Small 1973: cluster systems by how the community pairs them (co-citation) and by what they collectively cite (bibliographic coupling). Force-directed map plus a disagreement panel that flags pairs the community pairs tightly together but our hand-built taxonomy splits across sections — the headline finding no comparable catalog publishes.'
    },
    {
      slug: 'breakout-prediction',
      title: 'Citation breakout prediction',
      summary:
        'Fits the Wang-Song-Barabási (Science 2013) log-normal citation model to every paper row with a citation trajectory — the academic gold-standard for paper-level impact prediction. Three views: papers most likely to break out (still-growing fastest), hyped-but-won\'t-last identification (saturation below cohort median), and sleeping beauties (slow-burn impact with low immediacy but long tail). The catalog\'s watchlist for what to add next quarter.'
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
