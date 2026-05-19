<script lang="ts">
  import { base } from '$app/paths';

  // /findings — the externalizing entry point for the v6 catalog.
  //
  // Mirrors docs/FINDINGS.md (commit bab1421). Each card surfaces one of
  // the five publishable headlines plus a deep-link to the analytical
  // view that produced it. Keep the prose tight — full derivations live
  // in analysis.md; the card layout is for scanning, not reading.
  //
  // Visual pattern reuses the /analyses hub card grid so the two pages
  // feel like a pair (findings = the "what's interesting", analyses =
  // the "how we got there").

  type Finding = {
    n: number;
    headline: string;
    figure: string;
    soWhat: string;
    link: { href: string; label: string };
    source: string;
  };

  const findings: Finding[] = [
    {
      n: 1,
      headline: 'Semantic caching is an empty market',
      figure: '1 of 100 priority-cohort products',
      soWhat:
        "Only LangChain's SemanticCache ships a true semantic-cache layer in the v6 priority cohort. The cleanest product gap in the catalog: a vendor-shipped Anthropic / OpenAI semantic cache with cross-model similarity would have no direct competitor.",
      link: { href: `${base}/analyses/cost-economics`, label: 'See the cost-economics matrix' },
      source: 'analysis.md §25.2 · commit f2b95c1'
    },
    {
      n: 2,
      headline: '91.3% of catalogued products publish no peer-reviewed benchmark',
      figure: '833 of 912 products · only 2 scores on a neutral leaderboard',
      soWhat:
        'The product × benchmark matrix is 119 × 25 with 169 filled cells — the story is the empty cells. Of the 169 filled, the integrity split is 111 peer-reviewed / 2 independently-verified / 52 vendor-claimed / 4 disputed. Almost every claim is a paper or a vendor blog.',
      link: {
        href: `${base}/analyses/product-benchmark-matrix`,
        label: 'See the product × benchmark matrix'
      },
      source: 'analysis.md §24.2 · commit ea70f89 (T1-5)'
    },
    {
      n: 3,
      headline: "The MCP spec is the catalog's #3 inbound substrate",
      figure: 'Inbound runtime-deps: Claude 62 · GPT 52 · MCP spec 34 · Gemini 22 · Qwen 16',
      soWhat:
        "From the T2-1 runtime-dependency graph (212 edges of 'X depends on Y at runtime'). A protocol specification ranking #3 — ahead of every foundation model except Claude and GPT — is the v6 finding that wasn't visible in citation-graph hubs. The MCP spec is becoming a substrate, not just a protocol.",
      link: {
        href: `${base}/graph?edges=runtime-dependency`,
        label: 'See the runtime-dependency graph'
      },
      source: 'analysis.md §23 · commit ddb26c7 (T2-1)'
    },
    {
      n: 4,
      headline: 'Graphiti MCP Server is the most under-acknowledged connector in the catalog',
      figure: '0 inbound edges · 0.71 normalised betweenness — highest non-trivial in the graph',
      soWhat:
        'Sits on the shortest path between the MCP-spec substrate cluster and the Zep / Graphiti citation-anchor pair. A high-betweenness / low-inbound node is the structural definition of an under-acknowledged-but-load-bearing connector. Top-5 bridge-surprise: Graphiti MCP Server, MAGMA, Memformers, MemEvolve, RGMem.',
      link: {
        href: `${base}/analyses/influence`,
        label: 'See the bridge-surprises callout'
      },
      source: 'analysis.md §26.2 · v6 centrality view'
    },
    {
      n: 5,
      headline: '77% of FM-dependent products lock onto three vendors',
      figure: '108 of 140 FM-dependent rows depend on OpenAI / Anthropic / Google',
      soWhat:
        'Of the 140 rows (~16% of non-FM rows) that name a foundation model, 77.1% sit on the OpenAI / Anthropic / Google single-vendor-risk tier. The long tail (Qwen 16, Mistral 12, Cohere 8, DeepSeek 6, Jamba 3, Grok 2, Nova 2) is sparse. The substrate-risk map is concentrated on three labs.',
      link: {
        href: `${base}/analyses/trajectory`,
        label: 'See the substrate-dependency risk panel'
      },
      source: 'analysis.md §19.5 + §21.3 · v5/v6 FM substrate mining'
    }
  ];
</script>

<svelte:head>
  <title>Findings · AI Agent Infrastructure Landscape</title>
  <meta
    name="description"
    content="Five publishable headlines from the v6 AI agent infrastructure catalog: the semantic-cache gap, the 91.3% no-benchmark finding, MCP-spec-as-substrate, the under-acknowledged bridge node, and the single-vendor FM concentration."
  />
</svelte:head>

<header class="hub-header">
  <h1>Findings</h1>
  <p>
    Five publishable headlines from the v6 catalog — 912 records × 68 columns
    across 34 sections, 528 typed edges. Each card cites the analytical view
    that produced it; full derivations live in
    <a class="inline" href="https://github.com/MrPeppersDev/agent-infrastructure-landscape/blob/main/analysis.md"
      >analysis.md</a
    >.
  </p>
</header>

<ol class="cards">
  {#each findings as f}
    <li class="card">
      <div class="card-head">
        <span class="num">{f.n}</span>
        <h2>{f.headline}</h2>
      </div>
      <p class="figure">{f.figure}</p>
      <p class="so-what">{f.soWhat}</p>
      <div class="card-foot">
        <a class="deep-link" href={f.link.href}>{f.link.label} &rarr;</a>
        <span class="source">{f.source}</span>
      </div>
    </li>
  {/each}
</ol>

<style>
  /* Reuses the visual language of /analyses (card grid, dark surface,
     accent #d4845f for interactive heads) so the two pages feel like a
     pair. Single-column on narrow screens; two-up on wide. The numbered
     list shape (<ol>) reinforces "these are the top five." */
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
  .hub-header a.inline {
    color: #d4845f;
    text-decoration: none;
  }
  .hub-header a.inline:hover {
    text-decoration: underline;
  }
  .cards {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 16px;
    max-width: 1100px;
    counter-reset: finding;
  }
  .card {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 20px 22px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .card-head {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }
  .num {
    font-size: 0.85rem;
    font-weight: 600;
    color: #d4845f;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.04em;
    min-width: 1.4em;
  }
  .card h2 {
    margin: 0;
    font-size: 1.1rem;
    color: #e8e8e8;
    font-weight: 600;
    line-height: 1.35;
    letter-spacing: -0.005em;
  }
  .figure {
    margin: 0;
    color: #d4845f;
    font-size: 0.92rem;
    font-variant-numeric: tabular-nums;
    line-height: 1.4;
  }
  .so-what {
    margin: 0;
    color: #c9d1d9;
    font-size: 0.93rem;
    line-height: 1.55;
  }
  .card-foot {
    margin-top: 4px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .deep-link {
    color: #d4845f;
    text-decoration: none;
    font-size: 0.9rem;
    font-weight: 500;
  }
  .deep-link:hover {
    text-decoration: underline;
  }
  .source {
    color: #6e7681;
    font-size: 0.78rem;
    font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  }
</style>
