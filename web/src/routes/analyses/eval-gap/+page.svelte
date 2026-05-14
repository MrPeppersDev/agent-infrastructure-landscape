<script lang="ts">
  // Eval-gap analysis view (issue #40, T1-2).
  //
  // The eval gap is the next frontier after observability. LangChain's
  // State of Agent Engineering 2025 survey found 89% observability
  // adoption but only 52% eval adoption — a 37-point structural gap.
  // This view does two things no comparable catalog view does:
  //
  //   1. Reports the catalog's observed obs / eval adoption side by
  //      side, so the reader can see whether the catalog matches the
  //      89/52 industry headline.
  //   2. Surfaces "eval orphans" — products that have observability
  //      ≥1 tool but ZERO eval tools. That's the structural failure
  //      mode the LangChain survey identified, and the view is the
  //      first catalog-level surface for it.
  //
  // The view is deliberately honest about coverage gaps: only the top
  // ~100 priority rows (same selection as T1-1 obs + T1-3 cost) are
  // backfilled, and the matrix is filtered to those analyzed rows by
  // default. Hiding all-unknown rows keeps the orphan + gap signals
  // legible.

  import { base } from '$app/paths';
  import {
    buildEvalGap,
    uniqueSections,
    compareByGap,
    compareByEvalCount,
    compareByName,
    compareByTier,
    EVAL_TOOLS,
    TOOL_LABEL,
    TOOL_DESCRIPTION,
    type EvalTool,
    type EvalState,
    type EvalCoverage
  } from '$lib/analyses/eval-gap';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  const matrix = $derived(buildEvalGap(data.records));
  const sections = $derived(uniqueSections(matrix));

  // ----- filter / sort state ---------------------------------------------
  type SortMode = 'gap' | 'eval' | 'tier' | 'alpha';
  let sortMode = $state<SortMode>('gap');
  let activeSection = $state<string>('all');
  let activeTool = $state<EvalTool | 'all'>('all');
  // Default: only show rows that have been analyzed (have either obs or
  // eval signal). Otherwise the table is mostly empty for the 812
  // un-backfilled rows.
  let hideUnanalyzed = $state(true);
  // The headline filter: show only eval-orphans (obs ≥1, eval = 0).
  let onlyEvalOrphans = $state(false);

  const filteredCoverage = $derived.by<EvalCoverage[]>(() => {
    let rows = matrix.coverage.slice();
    if (hideUnanalyzed) {
      rows = rows.filter((r) => r.isAnalyzed);
    }
    if (onlyEvalOrphans) {
      rows = rows.filter((r) => r.isEvalOrphan);
    }
    if (activeSection !== 'all') {
      rows = rows.filter((r) => r.section === activeSection);
    }
    if (activeTool !== 'all') {
      rows = rows.filter((r) => r.evalIntegrations[activeTool] === 'yes');
    }
    switch (sortMode) {
      case 'gap':
        rows.sort(compareByGap);
        break;
      case 'eval':
        rows.sort(compareByEvalCount);
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

  // Top-supported eval tool.
  const topTool = $derived.by(() => {
    if (matrix.toolStats.length === 0) return null;
    return matrix.toolStats
      .slice()
      .sort((a, b) => b.supportedCount - a.supportedCount)[0];
  });

  // Maximum supportedCount across tools, for bar scaling.
  const maxSupportedCount = $derived(
    Math.max(1, ...matrix.toolStats.map((t) => t.supportedCount))
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
    tool: EvalTool,
    state: EvalState,
    citation: string | null
  ): string {
    const label = TOOL_LABEL[tool];
    const stateText =
      state === 'yes'
        ? 'integration supported'
        : state === 'no'
          ? 'integration absent / not exposed'
          : 'unknown (not yet researched or depth-floor reached)';
    return citation
      ? `${label}: ${stateText}\n${citation}`
      : `${label}: ${stateText}`;
  }
</script>

<svelte:head>
  <title>Evaluation gap — Memory Landscape</title>
</svelte:head>

<main class="eg-page">
  <header class="eg-header">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Evaluation gap (the next frontier after observability)</h1>
    <p class="eg-intro">
      <strong>LangChain's State of Agent Engineering 2025</strong> found
      that <strong>89% of practitioners have observability adopted</strong>
      but only <strong>52% have evals</strong> — a 37-point structural gap.
      The Berkeley RDI MAP study (Q1 2026) corroborates: 74% rely
      primarily on human evaluation. The Datadog State of AI Agents 2026
      report lists "reliable evaluation loops" as a top recommendation.
      This view answers the catalog-level question
      <em>"how do I know if my agent is actually getting better?"</em> —
      the question that had no catalog-level surface before T1-2.
    </p>
    <p class="eg-intro eg-distinctive">
      This view's distinctive value is the <strong>gap</strong>. Every
      comparable catalog tracks eval tooling on its own. We're the first
      to surface <em>"products that have observability but no eval"</em>
      row-by-row — the structural failure mode the LangChain survey
      identified.
    </p>
    <p class="eg-intro eg-scope-note">
      <em>Out of scope:</em> eval methodology comparison (LLM-as-judge
      vs human rubric vs canary set) and benchmark scores
      (T1-4 territory). This view tracks <strong>integration support</strong>
      only — which products plug into which eval tooling.
    </p>
  </header>

  <section class="gap-callout" aria-label="The eval gap">
    <article class="gap-card gap-card-obs">
      <h2>Observability adoption</h2>
      <div class="gap-number">{matrix.observabilityAdoptionPct.toFixed(1)}%</div>
      <p class="gap-sub">
        of {matrix.totalAnalyzed} analyzed catalog products ship at
        least one observability integration. Industry headline:
        <strong>89%</strong> (LangChain 2025).
      </p>
    </article>
    <article class="gap-card gap-card-eval">
      <h2>Eval adoption</h2>
      <div class="gap-number">{matrix.evalAdoptionPct.toFixed(1)}%</div>
      <p class="gap-sub">
        of {matrix.totalAnalyzed} analyzed catalog products ship at
        least one eval integration. Industry headline:
        <strong>52%</strong> (LangChain 2025).
      </p>
    </article>
    <article class="gap-card gap-card-orphan">
      <h2>Eval orphans</h2>
      <div class="gap-number gap-orphans">{matrix.evalOrphanCount}</div>
      <p class="gap-sub">
        products with observability ≥1 tool but
        <strong>zero</strong> eval tools. These are the structural
        failures the LangChain survey identified. Use the
        <em>"only eval-orphans"</em> filter below to see them.
      </p>
    </article>
  </section>

  <section class="callout-bar" aria-label="Per-tool support callouts">
    <article class="callout">
      <h2>Per-eval-tool support</h2>
      <p class="callout-sub">
        Out of {matrix.totalAnalyzed} analyzed products. Bars scale to
        the leader; numbers are absolute supportedCount.
      </p>
      <ul class="tool-bars">
        {#each matrix.toolStats as t (t.tool)}
          <li class="tool-bar">
            <span class="tool-label">{t.label}</span>
            <span class="tool-bar-wrap" aria-hidden="true">
              <span
                class="tool-bar-fill"
                style:width="{(t.supportedCount / maxSupportedCount) * 100}%"
                data-tool={t.tool}
              ></span>
            </span>
            <span class="tool-count">{t.supportedCount}</span>
            <span class="tool-pct">({t.supportedPct.toFixed(1)}%)</span>
          </li>
        {/each}
      </ul>
      {#if topTool}
        <p class="callout-foot">
          Leader: <strong>{topTool.label}</strong>
          with {topTool.supportedCount} supported products
          ({topTool.supportedPct.toFixed(1)}% of analyzed).
        </p>
      {/if}
    </article>
  </section>

  <section class="filters" aria-label="Filter controls">
    <div class="filter-group">
      <label for="sort-mode">Sort by:</label>
      <select id="sort-mode" bind:value={sortMode}>
        <option value="gap">Gap (obs − eval) ↓</option>
        <option value="eval">Eval count ↓</option>
        <option value="tier">Tier then gap</option>
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
      <label for="tool-filter">Has eval tool:</label>
      <select id="tool-filter" bind:value={activeTool}>
        <option value="all">Any (no filter)</option>
        {#each EVAL_TOOLS as tool}
          <option value={tool}>{TOOL_LABEL[tool]}</option>
        {/each}
      </select>
    </div>
    <div class="filter-group filter-toggles">
      <label class="toggle">
        <input type="checkbox" bind:checked={hideUnanalyzed} />
        Hide un-analyzed rows
      </label>
      <label class="toggle toggle-headline">
        <input type="checkbox" bind:checked={onlyEvalOrphans} />
        <strong>Only eval-orphans</strong>
      </label>
    </div>
  </section>

  <section class="legend" aria-label="Legend">
    <h2>Legend</h2>
    <ul class="legend-list">
      <li>
        <span class="pill" data-state="yes">yes</span>
        eval tool integration documented — citation in cell tooltip
      </li>
      <li>
        <span class="pill" data-state="no">no</span>
        eval tool absent / not exposed for this product class
      </li>
      <li>
        <span class="pill" data-state="unknown">unknown</span>
        not yet researched, depth-floor reached, or not applicable
      </li>
      <li>
        <span class="orphan-badge">orphan</span>
        product has observability ≥1 but zero eval tools
      </li>
    </ul>
  </section>

  <section class="board" aria-label="Eval-gap matrix">
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
            <th class="num-col" title="Count of observability tools supported (0-8)">Obs</th>
            <th class="num-col" title="Count of eval tools supported (0-7)">Eval</th>
            <th class="num-col" title="Obs count minus eval count">Gap</th>
            <th class="orphan-col">Orphan</th>
            {#each EVAL_TOOLS as tool}
              <th
                class="tool-col"
                data-tool={tool}
                title={TOOL_DESCRIPTION[tool]}
              >
                <span class="tool-h">{TOOL_LABEL[tool]}</span>
              </th>
            {/each}
            <th class="section-col">Section</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredCoverage as row (row.productId)}
            {@const isOpen = expanded === row.productId}
            <tr
              class="row"
              class:open={isOpen}
              class:orphan={row.isEvalOrphan}
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
                {#if row.primaryTool}
                  <span class="primary-tag" title="Primary eval tool (first 'yes' from priority order)">
                    {TOOL_LABEL[row.primaryTool]}
                  </span>
                {/if}
              </td>
              <td class="tier-col">
                <span class="tier-pill" data-tier="t{row.tier}">T{row.tier}</span>
              </td>
              <td class="num-col num-obs">
                <span class="count-num">{row.observabilityCount}</span>
                <span class="count-meta">/ 8</span>
              </td>
              <td class="num-col num-eval">
                <span class="count-num">{row.evalCount}</span>
                <span class="count-meta">/ 7</span>
              </td>
              <td class="num-col num-gap" class:gap-positive={row.gap > 0}>
                <span class="count-num">{row.gap > 0 ? `+${row.gap}` : row.gap}</span>
              </td>
              <td class="orphan-col">
                {#if row.isEvalOrphan}
                  <span class="orphan-badge">orphan</span>
                {/if}
              </td>
              {#each EVAL_TOOLS as tool}
                <td class="tool-cell" data-tool={tool}>
                  <span
                    class="pill"
                    data-state={row.evalIntegrations[tool]}
                    title={pillTitle(tool, row.evalIntegrations[tool], row.citations[tool])}
                  >
                    {row.evalIntegrations[tool] === 'yes'
                      ? '●'
                      : row.evalIntegrations[tool] === 'no'
                        ? '○'
                        : '–'}
                  </span>
                </td>
              {/each}
              <td class="section-col">{row.section}</td>
            </tr>
            {#if isOpen}
              <tr class="drill-row">
                <td colspan="14">
                  <div class="drill-body">
                    <h3>
                      {row.productName}
                      <span class="drill-sub">
                        T{row.tier} · {row.section} · obs: {row.observabilityCount} · eval: {row.evalCount}
                        {#if row.isEvalOrphan}
                          · <span class="orphan-badge">eval orphan</span>
                        {/if}
                      </span>
                    </h3>
                    <ul class="drill-list">
                      {#each EVAL_TOOLS as tool}
                        {@const state = row.evalIntegrations[tool]}
                        {@const citation = row.citations[tool]}
                        <li>
                          <span class="drill-label">
                            <strong>{TOOL_LABEL[tool]}</strong>
                            <span class="drill-desc">{TOOL_DESCRIPTION[tool]}</span>
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
              <td colspan="14" class="empty-row">
                No products match the current filters.
              </td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
  </section>

  <footer class="eg-footer">
    <a href="{base}/analyses">← Analyses hub</a>
    <span class="muted">
      Pivot of <code>obs-*</code> and <code>eval-*</code> cells. Helper
      in <code>$lib/analyses/eval-gap.ts</code>. Schema in
      <code>docs/SCHEMA.md</code> §2.5.1 and §2.5.3.
    </span>
  </footer>
</main>

<style>
  .eg-page {
    max-width: 1700px;
    margin: 0 auto;
    padding: 24px 8px 64px;
    color: #e8e8e8;
  }
  .eg-header { margin-bottom: 18px; }
  .crumb { margin: 0 0 8px 0; font-size: 13px; }
  .crumb a { color: #aaa; text-decoration: none; }
  .crumb a:hover { color: #e8e8e8; }
  .eg-header h1 {
    font-size: 28px; margin: 0 0 10px 0; letter-spacing: -0.01em;
  }
  .eg-intro {
    color: #c9c9c9; max-width: 920px; margin: 0 0 12px 0;
    line-height: 1.6; font-size: 14px;
  }
  .eg-intro strong { color: #e8e8e8; }
  .eg-intro em { color: #c0c0c0; font-style: italic; }
  .eg-distinctive {
    background: #1a1612;
    border-left: 3px solid #c89a5a;
    padding: 10px 14px;
    border-radius: 0 4px 4px 0;
  }
  .eg-scope-note {
    color: #888;
    font-size: 13px;
  }
  .eg-scope-note em { color: #aaa; }
  code {
    font-family: 'SF Mono', 'Menlo', Consolas, monospace;
    font-size: 12.5px; background: #1f1f1f;
    padding: 1px 5px; border-radius: 3px; color: #d4d4d4;
  }

  /* ---- The gap callout (3-column hero) ---- */
  .gap-callout {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 14px;
    margin-bottom: 20px;
  }
  .gap-card {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 18px 20px;
  }
  .gap-card h2 {
    margin: 0 0 8px 0;
    font-size: 12px;
    color: #aaa;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .gap-number {
    font-size: 42px;
    font-weight: 700;
    color: #e8e8e8;
    line-height: 1;
    margin-bottom: 8px;
    font-variant-numeric: tabular-nums;
  }
  .gap-card-obs { border-left: 3px solid #5ac8b8; }
  .gap-card-obs .gap-number { color: #8eddc7; }
  .gap-card-eval { border-left: 3px solid #c89a5a; }
  .gap-card-eval .gap-number { color: #c8a868; }
  .gap-card-orphan { border-left: 3px solid #c87a7a; }
  .gap-card-orphan .gap-orphans { color: #c87a7a; }
  .gap-sub {
    margin: 0;
    color: #aaa;
    font-size: 12.5px;
    line-height: 1.5;
  }
  .gap-sub strong { color: #d4d4d4; }
  .gap-sub em { color: #d4845f; font-style: normal; font-weight: 500; }

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

  .tool-bars {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 6px;
  }
  .tool-bar {
    display: grid;
    grid-template-columns: 160px 1fr 40px 60px;
    align-items: center;
    gap: 10px;
    font-size: 12.5px;
  }
  .tool-label { color: #d4d4d4; }
  .tool-bar-wrap {
    height: 12px; background: #232323;
    border-radius: 3px; overflow: hidden;
    display: inline-block;
  }
  .tool-bar-fill {
    display: block; height: 100%;
    background: #c89a5a;
    border-radius: 3px; transition: width 200ms;
  }
  .tool-bar-fill[data-tool='langsmith-evals'] { background: #d4845f; }
  .tool-bar-fill[data-tool='braintrust'] { background: #c89a5a; }
  .tool-bar-fill[data-tool='weights-and-biases-agent'] { background: #c4c97b; }
  .tool-bar-fill[data-tool='helicone-evals'] { background: #9fc5e0; }
  .tool-bar-fill[data-tool='custom-test-harness'] { background: #6b9a4a; }
  .tool-bar-fill[data-tool='human-loop'] { background: #a868c8; }
  .tool-bar-fill[data-tool='production-traffic-replay'] { background: #5ac8b8; }
  .tool-count {
    color: #f4e2cb; font-variant-numeric: tabular-nums;
    font-weight: 600; text-align: right;
  }
  .tool-pct { color: #888; font-size: 11.5px; }

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
  .toggle-headline {
    color: #c87a7a;
    padding: 4px 10px;
    background: #221414;
    border: 1px solid #3a2222;
    border-radius: 4px;
  }
  .toggle-headline strong { color: #d49494; }
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

  .orphan-badge {
    display: inline-block;
    background: #2a1414;
    color: #d49494;
    padding: 2px 7px;
    border-radius: 3px;
    font-size: 10.5px;
    font-weight: 600;
    text-transform: lowercase;
    letter-spacing: 0.04em;
    border: 1px solid #3a2222;
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
  .board-table thead th.tool-col {
    text-align: center;
    color: #c9c9c9;
    cursor: help;
  }
  .board-table thead th.num-col {
    text-align: right;
  }
  .board-table thead th.orphan-col {
    text-align: center;
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
  .board-table tbody tr.row.orphan {
    background: #1c1414;
  }
  .board-table tbody tr.row.orphan:hover {
    background: #221818;
  }
  .board-table tbody tr.row.orphan.open {
    background: #271c1a;
  }

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

  .num-col {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    min-width: 56px;
  }
  .num-obs .count-num { color: #8eddc7; font-weight: 600; }
  .num-eval .count-num { color: #c8a868; font-weight: 600; }
  .num-gap .count-num { color: #d4d4d4; font-weight: 600; }
  .num-gap.gap-positive .count-num { color: #c87a7a; }
  .count-meta { color: #777; font-size: 11px; margin-left: 2px; }

  .orphan-col {
    text-align: center;
    min-width: 70px;
  }

  .section-col {
    color: #aaa; font-size: 11.5px;
    max-width: 200px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }

  .tool-cell {
    text-align: center;
    padding: 4px 6px !important;
  }
  .tool-h {
    /* Make headers more compact */
    display: inline-block;
    font-size: 11px;
  }

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

  .eg-footer {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 24px; padding-top: 16px;
    border-top: 1px solid #2a2a2a;
    color: #aaa; font-size: 13px;
    flex-wrap: wrap; gap: 8px;
  }
  .eg-footer a { color: #aaa; text-decoration: none; }
  .eg-footer a:hover { color: #e8e8e8; }
  .muted { color: #777; font-size: 12.5px; }

  @media (max-width: 1100px) {
    .filters { gap: 10px 16px; }
    .tool-bar { grid-template-columns: 130px 1fr 36px 50px; gap: 6px; }
    .gap-number { font-size: 32px; }
  }
</style>
