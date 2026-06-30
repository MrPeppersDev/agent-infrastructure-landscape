<script lang="ts">
  import SeoHead from '$lib/components/SeoHead.svelte';

  // Cost-economics coverage matrix (issue #41, T1-3).
  //
  // Cost / token-economics is the #2 demand-signal question in agent
  // infrastructure (171 HN mentions in last 12 months, Sequoia framing
  // on inference-cost sustainability, Datadog 2026 found 69% of input
  // tokens go to system-prompt overhead). The practitioner question
  // has shifted from "how expensive?" to "how do I govern spend?" —
  // this view pivots the seven cost-* cells (added in T1-3) into a
  // governance-score matrix.
  //
  // The view is deliberately honest about coverage gaps: the top ~100
  // priority rows have been backfilled; the rest are surfaced as
  // "unknown" so the reader can see the limit of the research, not
  // just the cost-features that did surface.

  import { base } from '$app/paths';
  import {
    buildCostEconomics,
    uniqueSections,
    compareByScore,
    compareByName,
    compareByTier,
    COST_FEATURES,
    FEATURE_LABEL,
    FEATURE_DESCRIPTION,
    type CostFeature,
    type CostState,
    type CostGovernance
  } from '$lib/analyses/cost-economics';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  const matrix = $derived(buildCostEconomics(data.records));
  const sections = $derived(uniqueSections(matrix));

  // ----- filter / sort state ---------------------------------------------
  type SortMode = 'score' | 'tier' | 'alpha';
  let sortMode = $state<SortMode>('score');
  let activeSection = $state<string>('all');
  let activeFeature = $state<CostFeature | 'all'>('all');
  let hideAllUnknown = $state(true); // hide rows that aren't backfilled
  let onlyUncovered = $state(false); // only zero-yes rows
  let onlyFullCoverage = $state(false); // only governanceScore === 7

  const filteredCoverage = $derived.by<CostGovernance[]>(() => {
    let rows = matrix.coverage.slice();
    if (hideAllUnknown) {
      rows = rows.filter(
        (r) => r.governanceScore + r.explicitNoCount > 0
      );
    }
    if (onlyUncovered) {
      rows = rows.filter((r) => r.governanceScore === 0);
    }
    if (onlyFullCoverage) {
      rows = rows.filter((r) => r.governanceScore === COST_FEATURES.length);
    }
    if (activeSection !== 'all') {
      rows = rows.filter((r) => r.section === activeSection);
    }
    if (activeFeature !== 'all') {
      rows = rows.filter((r) => r.features[activeFeature] === 'yes');
    }
    switch (sortMode) {
      case 'score':
        rows.sort(compareByScore);
        break;
      case 'tier':
        rows.sort(compareByTier);
        break;
      case 'alpha':
        rows.sort(compareByName);
        break;
    }
    return rows;
  });

  // Coverage callout numbers.
  const analyzedPct = $derived(
    matrix.totalProducts > 0
      ? Math.round((matrix.analyzedCount / matrix.totalProducts) * 1000) / 10
      : 0
  );
  const anyFeaturePct = $derived(
    matrix.analyzedCount > 0
      ? Math.round(
          (matrix.withAnyFeatureCount / matrix.analyzedCount) * 1000
        ) / 10
      : 0
  );

  // Top-supported feature.
  const topFeature = $derived.by(() => {
    if (matrix.featureStats.length === 0) return null;
    return matrix.featureStats.slice().sort(
      (a, b) => b.supportedCount - a.supportedCount
    )[0];
  });

  // Maximum supportedCount across features, for bar scaling.
  const maxSupportedCount = $derived(
    Math.max(1, ...matrix.featureStats.map((t) => t.supportedCount))
  );

  // ----- inline drilldown -------------------------------------------------
  let expanded = $state<string | null>(null);
  function toggleExpand(id: string) {
    expanded = expanded === id ? null : id;
  }

  function tableHref(name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  function pillTitle(
    feature: CostFeature,
    state: CostState,
    citation: string | null
  ): string {
    const label = FEATURE_LABEL[feature];
    const stateText =
      state === 'yes'
        ? 'feature supported'
        : state === 'no'
          ? 'feature absent / not exposed'
          : 'unknown (not yet researched or depth-floor reached)';
    return citation
      ? `${label}: ${stateText}\n${citation}`
      : `${label}: ${stateText}`;
  }
</script>

<svelte:head>
  <SeoHead
    title="AI Memory Cost Economics: Pricing Coverage"
    description="Pricing model coverage across the AI agent memory catalog — per-token, per-request, subscription, self-hosted, free-tier. Where the market gaps are."
    path="/analyses/cost-economics"
    ogType="article"
  />
</svelte:head>

<main class="ce-page">
  <header class="ce-header">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Cost-economics &amp; token-governance coverage</h1>
    <p class="ce-intro">
      Which products and frameworks ship cost-control features?
      Per the May 2026 volumetric agent, cost / token-economics is the
      <strong>#2 most-asked question</strong> in agent infrastructure
      (171 HN mentions in the last 12 months, Sequoia's "60-70% gross
      margins to inference is unsustainable" framing, LangChain's
      State-of-Agents survey logging cost as the second-biggest
      blocker). The practitioner question has shifted from
      <em>"how expensive is this?"</em> to
      <em>"how do I govern spend?"</em> — this matrix pivots the
      catalog's seven <code>cost-*</code> columns into a
      governance-score view.
    </p>
    <p class="ce-intro ce-datadog-callout">
      <strong>Datadog State of AI Agents 2026</strong> found that
      <strong>69% of input tokens go to system-prompt overhead</strong> —
      the cost-governance crisis is real, but the picture below shows
      which frameworks have the features practitioners can actually
      pull. <em>Token budgets, prompt caching, and cost attribution are
      the load-bearing trio; semantic caching is still almost nowhere.</em>
    </p>
    <p class="ce-intro ce-coverage-note">
      <strong>Coverage:</strong>
      {matrix.analyzedCount}/{matrix.totalProducts}
      products ({analyzedPct}%) have at least one cost-economics cell
      filled in. Of those analyzed,
      <strong>{anyFeaturePct}%</strong> declare support for at least one
      of the seven tracked governance features. The rest of the catalog
      (mostly research papers and depth-floor rows) is surfaced as
      <em>unknown</em> by default — the matrix explicitly shows where
      research has bottomed out rather than papering over the gap.
    </p>
    <p class="ce-intro ce-scope-note">
      <em>Out of scope:</em> per-call pricing data
      (e.g. <code>$0.003 / 1k input tokens</code>) — pricing changes
      too fast and goes stale within weeks. This view tracks the
      <strong>governance features</strong> that let you control spend,
      not the spend itself.
    </p>
  </header>

  <section class="callout-bar" aria-label="Per-feature support callouts">
    <article class="callout">
      <h2>Per-feature support</h2>
      <p class="callout-sub">
        Out of {matrix.analyzedCount} analyzed products. Bars scale to
        the leader; numbers are absolute supportedCount.
      </p>
      <ul class="feature-bars">
        {#each matrix.featureStats as f (f.feature)}
          <li class="feature-bar">
            <span class="feature-label">{f.label}</span>
            <span class="feature-bar-wrap" aria-hidden="true">
              <span
                class="feature-bar-fill"
                style:width="{(f.supportedCount / maxSupportedCount) * 100}%"
                data-feature={f.feature}
              ></span>
            </span>
            <span class="feature-count">{f.supportedCount}</span>
            <span class="feature-pct">({f.supportedPct.toFixed(1)}%)</span>
          </li>
        {/each}
      </ul>
      {#if topFeature}
        <p class="callout-foot">
          Leader: <strong>{topFeature.label}</strong>
          with {topFeature.supportedCount} supported products
          ({topFeature.supportedPct.toFixed(1)}% of analyzed).
        </p>
      {/if}
    </article>
  </section>

  <section class="filters" aria-label="Filter controls">
    <div class="filter-group">
      <label for="sort-mode">Sort by:</label>
      <select id="sort-mode" bind:value={sortMode}>
        <option value="score">Governance score</option>
        <option value="tier">Tier then score</option>
        <option value="alpha">Alphabetical</option>
      </select>
    </div>
    <div class="filter-group">
      <label for="section-filter">Section:</label>
      <select id="section-filter" bind:value={activeSection}>
        <option value="all">All sections</option>
        {#each sections as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
    </div>
    <div class="filter-group">
      <label for="feature-filter">Has feature:</label>
      <select id="feature-filter" bind:value={activeFeature}>
        <option value="all">Any (no filter)</option>
        {#each COST_FEATURES as feature}
          <option value={feature}>{FEATURE_LABEL[feature]}</option>
        {/each}
      </select>
    </div>
    <div class="filter-group filter-toggles">
      <label class="toggle">
        <input type="checkbox" bind:checked={hideAllUnknown} />
        Hide all-unknown rows
      </label>
      <label class="toggle">
        <input
          type="checkbox"
          bind:checked={onlyUncovered}
          onchange={() => { if (onlyUncovered) onlyFullCoverage = false; }}
        />
        Only fully-uncovered
      </label>
      <label class="toggle">
        <input
          type="checkbox"
          bind:checked={onlyFullCoverage}
          onchange={() => { if (onlyFullCoverage) onlyUncovered = false; }}
        />
        Only 7/7 governance score
      </label>
    </div>
  </section>

  <section class="legend" aria-label="Legend">
    <h2>Legend</h2>
    <ul class="legend-list">
      <li>
        <span class="pill" data-state="yes">yes</span>
        feature documented — citation in the cell tooltip
      </li>
      <li>
        <span class="pill" data-state="no">no</span>
        feature absent / not exposed for this product class
      </li>
      <li>
        <span class="pill" data-state="unknown">unknown</span>
        not yet researched, depth-floor reached, or not applicable
      </li>
    </ul>
  </section>

  <section class="board" aria-label="Cost-economics matrix">
    <h2 class="section-h">
      Matrix —
      <span class="filter-count">
        showing {filteredCoverage.length} of {matrix.totalProducts}
      </span>
    </h2>
    <div class="table-wrap">
      <table class="board-table">
        <thead>
          <tr>
            <th class="product-col">Product</th>
            <th class="tier-col">Tier</th>
            <th class="section-col">Section</th>
            {#each COST_FEATURES as feature}
              <th
                class="feature-col"
                data-feature={feature}
                title={FEATURE_DESCRIPTION[feature]}
              >
                <span class="feature-h">{FEATURE_LABEL[feature]}</span>
              </th>
            {/each}
            <th class="score-col">Score</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredCoverage as row (row.productId)}
            {@const isOpen = expanded === row.productId}
            <tr
              class="row"
              class:open={isOpen}
              onclick={() => toggleExpand(row.productId)}
            >
              <td class="product-col">
                <span class="caret" aria-hidden="true">
                  {isOpen ? '▾' : '▸'}
                </span>
                <a
                  href={tableHref(row.productName)}
                  onclick={(e) => e.stopPropagation()}
                  class="prod-link"
                >{row.productName}</a>
                {#if row.primaryFeature}
                  <span class="primary-tag" title="Primary feature (first 'yes' from priority order)">
                    {FEATURE_LABEL[row.primaryFeature]}
                  </span>
                {/if}
              </td>
              <td class="tier-col">
                <span class="tier-pill" data-tier="t{row.tier}">T{row.tier}</span>
              </td>
              <td class="section-col">{row.section}</td>
              {#each COST_FEATURES as feature}
                <td class="feature-cell" data-feature={feature}>
                  <span
                    class="pill"
                    data-state={row.features[feature]}
                    title={pillTitle(feature, row.features[feature], row.citations[feature])}
                  >
                    {row.features[feature] === 'yes' ? '●' :
                     row.features[feature] === 'no'  ? '○' : '–'}
                  </span>
                </td>
              {/each}
              <td class="score-col">
                <span class="score-num">{row.governanceScore}</span>
                <span class="score-meta">/ 7</span>
              </td>
            </tr>
            {#if isOpen}
              <tr class="drill-row">
                <td colspan="11">
                  <div class="drill-body">
                    <h3>
                      {row.productName}
                      <span class="drill-sub">
                        T{row.tier} · {row.section} ·
                        {row.governanceScore} yes ·
                        {row.explicitNoCount} explicit no ·
                        {row.unknownCount} unknown
                      </span>
                    </h3>
                    <ul class="drill-list">
                      {#each COST_FEATURES as feature}
                        {@const state = row.features[feature]}
                        {@const citation = row.citations[feature]}
                        <li>
                          <span class="drill-label">
                            <strong>{FEATURE_LABEL[feature]}</strong>
                            <span class="drill-desc">{FEATURE_DESCRIPTION[feature]}</span>
                          </span>
                          <span class="drill-state">
                            <span class="pill" data-state={state}>
                              {state === 'yes' ? 'yes' :
                               state === 'no'  ? 'no'  : 'unknown'}
                            </span>
                            {#if citation}
                              <a
                                class="drill-citation"
                                href={citation}
                                target="_blank"
                                rel="noopener noreferrer"
                                onclick={(e) => e.stopPropagation()}
                              >source ↗</a>
                            {/if}
                          </span>
                        </li>
                      {/each}
                    </ul>
                    {#if row.productUrl}
                      <p class="drill-url">
                        <a
                          href={row.productUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          onclick={(e) => e.stopPropagation()}
                        >{row.productUrl} ↗</a>
                      </p>
                    {/if}
                  </div>
                </td>
              </tr>
            {/if}
          {/each}
          {#if filteredCoverage.length === 0}
            <tr>
              <td colspan="11" class="empty-row">
                No products match the current filters.
              </td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
  </section>

  <footer class="ce-footer">
    <a href="{base}/analyses">← Analyses hub</a>
    <span class="muted">
      Pivot of <code>cost-*</code> cells. Helper in
      <code>$lib/analyses/cost-economics.ts</code>. Schema in
      <code>docs/SCHEMA.md</code> §2.5.2.
    </span>
  </footer>
</main>

<style>
  .ce-page {
    max-width: 1600px;
    margin: 0 auto;
    padding: 24px 8px 64px;
    color: #e8e8e8;
  }
  .ce-header { margin-bottom: 18px; }
  .crumb { margin: 0 0 8px 0; font-size: 13px; }
  .crumb a { color: #aaa; text-decoration: none; }
  .crumb a:hover { color: #e8e8e8; }
  .ce-header h1 {
    font-size: 28px; margin: 0 0 10px 0; letter-spacing: -0.01em;
  }
  .ce-intro {
    color: #c9c9c9; max-width: 920px; margin: 0 0 12px 0;
    line-height: 1.6; font-size: 14px;
  }
  .ce-intro strong { color: #e8e8e8; }
  .ce-intro em { color: #c0c0c0; font-style: italic; }
  .ce-intro a { color: #d4845f; }
  .ce-datadog-callout {
    background: #1a1612;
    border-left: 3px solid #c89a5a;
    padding: 10px 14px;
    border-radius: 0 4px 4px 0;
  }
  .ce-coverage-note {
    background: #14191d;
    border-left: 3px solid #d4845f;
    padding: 10px 14px;
    border-radius: 0 4px 4px 0;
  }
  .ce-scope-note {
    color: #888;
    font-size: 13px;
    font-style: normal;
  }
  .ce-scope-note em {
    color: #aaa;
  }
  code {
    font-family: 'SF Mono', 'Menlo', Consolas, monospace;
    font-size: 12.5px; background: #1f1f1f;
    padding: 1px 5px; border-radius: 3px; color: #d4d4d4;
  }

  .callout-bar { margin-bottom: 20px; }
  .callout {
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 8px; padding: 14px 18px;
    border-left: 3px solid #c89a5a;
  }
  .callout h2 {
    margin: 0 0 6px 0; font-size: 14px;
    color: #c8a868; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .callout-sub { color: #888; font-size: 11.5px; margin: 0 0 10px 0; }
  .callout-foot {
    color: #c9c9c9; font-size: 12.5px; margin: 8px 0 0 0;
    padding-top: 8px; border-top: 1px solid #232323;
  }
  .callout-foot strong { color: #c8a868; }

  .feature-bars {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 6px;
  }
  .feature-bar {
    display: grid;
    grid-template-columns: 140px 1fr 40px 60px;
    align-items: center;
    gap: 10px;
    font-size: 12.5px;
  }
  .feature-label { color: #d4d4d4; }
  .feature-bar-wrap {
    height: 12px; background: #232323;
    border-radius: 3px; overflow: hidden;
    display: inline-block;
  }
  .feature-bar-fill {
    display: block; height: 100%;
    background: #c89a5a;
    border-radius: 3px; transition: width 200ms;
  }
  .feature-bar-fill[data-feature='token-budget'] { background: #d4845f; }
  .feature-bar-fill[data-feature='prompt-caching'] { background: #c89a5a; }
  .feature-bar-fill[data-feature='semantic-caching'] { background: #9fc5e0; }
  .feature-bar-fill[data-feature='batching'] { background: #6b9a4a; }
  .feature-bar-fill[data-feature='model-routing'] { background: #a868c8; }
  .feature-bar-fill[data-feature='streaming-only'] { background: #5ac8b8; }
  .feature-bar-fill[data-feature='cost-attribution'] { background: #c87a8a; }
  .feature-count {
    color: #f4e2cb; font-variant-numeric: tabular-nums;
    font-weight: 600; text-align: right;
  }
  .feature-pct { color: #888; font-size: 11.5px; }

  .filters {
    display: flex; flex-wrap: wrap; gap: 14px 24px;
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 8px; padding: 12px 16px;
    margin: 0 0 14px 0;
  }
  .filter-group {
    display: flex; align-items: center; gap: 8px;
    font-size: 12.5px;
  }
  .filter-group label {
    color: #aaa; font-weight: 500;
  }
  .filter-group select {
    background: #1d1d1d; color: #e8e8e8;
    border: 1px solid #333; border-radius: 4px;
    padding: 4px 8px; font: inherit; font-size: 12.5px;
  }
  .filter-group select:focus {
    outline: none; border-color: #c89a5a;
  }
  .filter-toggles { gap: 14px; }
  .toggle {
    display: inline-flex; align-items: center; gap: 6px;
    color: #c9c9c9; cursor: pointer; user-select: none;
  }
  .toggle input { margin: 0; cursor: pointer; }

  .legend {
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 8px; padding: 10px 16px;
    margin: 0 0 18px 0;
  }
  .legend h2 {
    margin: 0 0 6px 0; font-size: 11.5px;
    color: #aaa; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .legend-list {
    list-style: none; margin: 0; padding: 0;
    display: flex; flex-wrap: wrap; gap: 14px 24px;
    font-size: 12px; color: #aaa;
  }
  .legend-list li {
    display: inline-flex; align-items: center; gap: 6px;
  }

  .pill {
    display: inline-flex; align-items: center; justify-content: center;
    min-width: 22px; height: 22px;
    padding: 0 4px;
    font-size: 12px; font-weight: 600;
    border-radius: 4px;
    text-align: center;
    line-height: 1;
  }
  .pill[data-state='yes'] {
    background: #1a3a2a; color: #8ec99a;
    border: 1px solid #2a4a3a;
  }
  .pill[data-state='no'] {
    background: #2a1a1a; color: #c87a7a;
    border: 1px solid #3a2a2a;
  }
  .pill[data-state='unknown'] {
    background: #1f1f1f; color: #666;
    border: 1px solid #2a2a2a;
  }

  .section-h {
    margin: 0 0 8px 0; font-size: 18px;
    color: #e8e8e8; letter-spacing: -0.005em;
  }
  .filter-count {
    color: #888; font-size: 13px; font-weight: 400;
  }

  .board { margin-bottom: 28px; }
  .table-wrap {
    overflow-x: auto; border: 1px solid #2a2a2a; border-radius: 8px;
    background: #181818;
  }
  .board-table {
    border-collapse: collapse; font-size: 12.5px;
    min-width: 100%; width: 100%;
  }
  .board-table thead th {
    position: sticky; top: 0; background: #1d1d1d;
    border-bottom: 1px solid #333;
    padding: 8px 10px; text-align: left;
    font-weight: 600; color: #d4d4d4; white-space: nowrap;
    font-size: 11.5px; letter-spacing: 0.02em;
  }
  .board-table thead th.feature-col {
    text-align: center;
    color: #c9c9c9;
    cursor: help;
  }
  .board-table thead th.score-col {
    text-align: right;
  }
  .board-table tbody td {
    border-bottom: 1px solid #232323; padding: 6px 10px;
    vertical-align: middle;
  }
  .board-table tbody tr.row {
    cursor: pointer; transition: background 80ms;
  }
  .board-table tbody tr.row:hover { background: #1c1c1c; }
  .board-table tbody tr.row.open { background: #1f1d1a; }
  .board-table tbody tr.row.open td { border-bottom-color: #1f1d1a; }

  .product-col {
    color: #e8e8e8; font-weight: 500;
    display: flex; align-items: center; gap: 8px;
    min-width: 220px;
  }
  .caret {
    color: #777; font-size: 11px;
    width: 12px; flex-shrink: 0;
  }
  .prod-link {
    color: #e8e8e8; text-decoration: none;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .prod-link:hover { color: #c89a5a; }

  .primary-tag {
    display: inline-block; background: #2a221a; color: #c8a868;
    padding: 1px 6px; border-radius: 3px; font-size: 10.5px;
    text-transform: none; letter-spacing: 0.02em;
    margin-left: auto;
    flex-shrink: 0;
  }

  .tier-col { min-width: 50px; }
  .tier-pill {
    display: inline-block; padding: 2px 6px;
    border-radius: 3px; font-size: 10.5px; font-weight: 600;
    background: #2a2a2a; color: #d4d4d4;
    font-variant-numeric: tabular-nums;
  }
  .tier-pill[data-tier='t1'] { background: #1a3a2a; color: #8ec99a; }
  .tier-pill[data-tier='t2'] { background: #1d2530; color: #9fc5e0; }
  .tier-pill[data-tier='t3'] { background: #2a221a; color: #c8a868; }
  .tier-pill[data-tier='t4'] { background: #2a1f10; color: #c98a4e; }
  .tier-pill[data-tier='t5'] { background: #2a1414; color: #c87a7a; }

  .section-col {
    color: #aaa; font-size: 11.5px;
    max-width: 200px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }

  .feature-cell {
    text-align: center;
    padding: 4px 6px !important;
  }

  .score-col {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    min-width: 60px;
  }
  .score-num {
    color: #f4e2cb; font-weight: 600; font-size: 13px;
  }
  .score-meta { color: #777; font-size: 11px; margin-left: 2px; }

  .drill-row {
    background: #1a1815;
  }
  .drill-row td {
    padding: 12px 18px 16px !important;
    border-bottom: 1px solid #2a2a2a !important;
  }
  .drill-body h3 {
    margin: 0 0 10px 0; font-size: 14px; color: #f4e2cb;
    font-weight: 600;
  }
  .drill-sub {
    color: #888; font-size: 12px; font-weight: 400;
    margin-left: 8px;
  }
  .drill-list {
    list-style: none; margin: 0; padding: 0;
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .drill-list li {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center; gap: 12px;
    font-size: 12px;
    padding: 5px 0;
    border-bottom: 1px solid #232323;
  }
  .drill-list li:last-child {
    border-bottom: none;
  }
  .drill-label {
    display: flex; flex-direction: column; gap: 2px;
  }
  .drill-label strong {
    color: #f4e2cb;
    font-weight: 600;
    font-size: 12.5px;
  }
  .drill-desc {
    color: #888;
    font-size: 11px;
    line-height: 1.4;
  }
  .drill-state {
    display: inline-flex; align-items: center; gap: 8px;
    flex-shrink: 0;
  }
  .drill-citation {
    color: #c89a5a; text-decoration: none;
    font-size: 11px;
  }
  .drill-citation:hover { text-decoration: underline; }

  .drill-url {
    margin: 10px 0 0 0; font-size: 12px;
  }
  .drill-url a { color: #aaa; text-decoration: none; }
  .drill-url a:hover { color: #e8e8e8; }

  .empty-row {
    text-align: center; color: #888; font-style: italic;
    padding: 24px !important;
  }

  .ce-footer {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 24px; padding-top: 16px;
    border-top: 1px solid #2a2a2a;
    color: #aaa; font-size: 13px;
    flex-wrap: wrap; gap: 8px;
  }
  .ce-footer a { color: #aaa; text-decoration: none; }
  .ce-footer a:hover { color: #e8e8e8; }
  .muted { color: #777; font-size: 12.5px; }

  @media (max-width: 1100px) {
    .filters { gap: 10px 16px; }
    .feature-bar { grid-template-columns: 110px 1fr 36px 50px; gap: 6px; }
  }
</style>
