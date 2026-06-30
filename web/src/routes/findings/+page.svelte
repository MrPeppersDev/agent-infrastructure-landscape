<script lang="ts">
  import SeoHead from '$lib/components/SeoHead.svelte';
  import { base } from '$app/paths';
  import { findings } from '$lib/findings';

  // /findings — the externalizing entry point for the v6 catalog.
  //
  // Card data is sourced from $lib/findings so the per-finding article
  // pages at /findings/[slug] render from the same canonical entries.
  //
  // Visual pattern reuses the /analyses hub card grid so the two pages
  // feel like a pair (findings = the "what's interesting", analyses =
  // the "how we got there").

</script>

<svelte:head>
  <SeoHead
    title="AI Agent Memory: 5 Key Findings from a 912-System Catalog"
    description="Five publishable headlines from the catalog: the semantic-cache gap, the 91.3% no-benchmark finding, MCP-as-substrate, the bridge node, single-vendor FM concentration."
    path="/findings"
    ogType="website"
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
        <h2>
          <a href="{base}/findings/{f.slug}">{f.headline}</a>
        </h2>
      </div>
      <p class="figure">{f.figure}</p>
      <p class="so-what">{f.cardSoWhat}</p>
      <div class="card-foot">
        <a class="deep-link" href="{base}/findings/{f.slug}">Read the full finding &rarr;</a>
        <a class="deep-link analysis-link" href="{base}{f.link.href}">{f.link.label}</a>
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
  .analysis-link {
    color: #b0b0b0;
    font-size: 0.85rem;
  }
  .source {
    color: #6e7681;
    font-size: 0.78rem;
    font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  }
</style>
