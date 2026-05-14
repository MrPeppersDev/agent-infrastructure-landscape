<script lang="ts">
  // Observability coverage matrix (issue #39, T1-1).
  //
  // Observability/debugging is the highest-demand question in agent
  // infrastructure (807 HN hits in last 12 months, 89% LangChain-survey
  // adoption, 6/7 published surveys). This view answers "which products
  // integrate with which observability stack?" by pivoting the eight
  // obs-* cells (added in T1-1) into a coverage matrix.
  //
  // The view is deliberately honest about coverage gaps: the top ~100
  // priority rows have been backfilled; the rest are surfaced as
  // "unknown" so the reader can see the limit of the research, not
  // just the integration claims that did surface.

  import { base } from '$app/paths';
  import {
    buildObservabilityMatrix,
    uniqueSections,
    compareByCoverage,
    compareByName,
    compareByTier,
    OBS_TOOLS,
    TOOL_LABEL,
    type ObsTool,
    type ObsState,
    type ObservabilityCoverage
  } from '$lib/analyses/observability';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  const matrix = $derived(buildObservabilityMatrix(data.records));
  const sections = $derived(uniqueSections(matrix));

  // ----- filter / sort state ---------------------------------------------
  type SortMode = 'coverage' | 'tier' | 'alpha';
  let sortMode = $state<SortMode>('coverage');
  let activeSection = $state<string>('all');
  let activeTool = $state<ObsTool | 'all'>('all');
  let hideAllUnknown = $state(true); // default: hide the never-researched
                                     // rows so the matrix isn't 90% empty
  let onlyUncovered = $state(false); // show only rows where every cell
                                     // is unknown OR no
  let onlyFullyCovered = $state(false); // show only rows with at least one yes

  const filteredCoverage = $derived.by<ObservabilityCoverage[]>(() => {
    let rows = matrix.coverage.slice();
    if (hideAllUnknown) {
      rows = rows.filter(
        (r) => r.coverageCount + r.explicitNoCount > 0
      );
    }
    if (onlyUncovered) {
      rows = rows.filter((r) => r.coverageCount === 0);
    }
    if (onlyFullyCovered) {
      rows = rows.filter((r) => r.coverageCount > 0);
    }
    if (activeSection !== 'all') {
      rows = rows.filter((r) => r.section === activeSection);
    }
    if (activeTool !== 'all') {
      rows = rows.filter((r) => r.integrations[activeTool] === 'yes');
    }
    switch (sortMode) {
      case 'coverage':
        rows.sort(compareByCoverage);
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
  const anyIntegrationPct = $derived(
    matrix.analyzedCount > 0
      ? Math.round(
          (matrix.withAnyIntegrationCount / matrix.analyzedCount) * 1000
        ) / 10
      : 0
  );

  // Top-supported tool.
  const topTool = $derived.by(() => {
    if (matrix.toolStats.length === 0) return null;
    return matrix.toolStats.slice().sort(
      (a, b) => b.supportedCount - a.supportedCount
    )[0];
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
    tool: ObsTool,
    state: ObsState,
    citation: string | null
  ): string {
    const label = TOOL_LABEL[tool];
    const stateText =
      state === 'yes'
        ? 'documented integration'
        : state === 'no'
          ? 'no integration / not applicable'
          : 'unknown (not yet researched or depth-floor reached)';
    return citation
      ? `${label}: ${stateText}\n${citation}`
      : `${label}: ${stateText}`;
  }
</script>

<svelte:head>
  <title>Observability coverage — Memory Landscape</title>
</svelte:head>

<main class="ob-page">
  <header class="ob-header">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Observability coverage</h1>
    <p class="ob-intro">
      Which products and frameworks integrate with which observability
      stack? Per the May 2026 volumetric agent,
      <strong>observability / debugging is the single highest-demand
      question</strong> in agent infrastructure (807 HN hits in the
      last 12 months, 89% adoption in LangChain's State of Agent
      Engineering 2025, six of seven published surveys treat it as a
      top-three challenge). This matrix pivots the catalog's eight
      <code>obs-*</code> columns into a coverage view.
    </p>
    <p class="ob-intro ob-coverage-note">
      <strong>Coverage:</strong>
      {matrix.analyzedCount}/{matrix.totalProducts}
      products ({analyzedPct}%) have at least one observability cell
      filled in. Of those analyzed, <strong>{anyIntegrationPct}%</strong>
      declare support for at least one of the seven tracked tools.
      The rest of the catalog (mostly research papers and depth-floor
      rows) is surfaced as <em>unknown</em> by default — the matrix
      explicitly shows where research has bottomed out rather than
      papering over the gap.
    </p>
  </header>

  <section class="callout-bar" aria-label="Per-tool support callouts">
    <article class="callout">
      <h2>Per-tool support</h2>
      <p class="callout-sub">
        Out of {matrix.analyzedCount} analyzed products. Bars scale to
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
        <option value="coverage">Coverage count</option>
        <option value="tier">Tier then coverage</option>
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
      <label for="tool-filter">Has integration with:</label>
      <select id="tool-filter" bind:value={activeTool}>
        <option value="all">Any (no filter)</option>
        {#each OBS_TOOLS as tool}
          <option value={tool}>{TOOL_LABEL[tool]}</option>
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
          onchange={() => { if (onlyUncovered) onlyFullyCovered = false; }}
        />
        Only fully-uncovered
      </label>
      <label class="toggle">
        <input
          type="checkbox"
          bind:checked={onlyFullyCovered}
          onchange={() => { if (onlyFullyCovered) onlyUncovered = false; }}
        />
        Only ≥1 integration
      </label>
    </div>
  </section>

  <section class="legend" aria-label="Legend">
    <h2>Legend</h2>
    <ul class="legend-list">
      <li>
        <span class="pill" data-state="yes">yes</span>
        documented integration — citation in the cell tooltip
      </li>
      <li>
        <span class="pill" data-state="no">no</span>
        no integration / not applicable for this product class
      </li>
      <li>
        <span class="pill" data-state="unknown">unknown</span>
        not yet researched or research bottomed out at the
        depth-floor; treat as "we don't know"
      </li>
    </ul>
  </section>

  <section class="board" aria-label="Observability matrix">
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
            {#each OBS_TOOLS as tool}
              <th class="tool-col" data-tool={tool}>
                <span class="tool-h">{TOOL_LABEL[tool]}</span>
              </th>
            {/each}
            <th class="cov-col">Coverage</th>
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
                {#if row.primaryIntegration}
                  <span class="primary-tag" title="Primary integration (first 'yes' from priority order)">
                    {TOOL_LABEL[row.primaryIntegration]}
                  </span>
                {/if}
              </td>
              <td class="tier-col">
                <span class="tier-pill" data-tier="t{row.tier}">T{row.tier}</span>
              </td>
              <td class="section-col">{row.section}</td>
              {#each OBS_TOOLS as tool}
                <td class="tool-cell" data-tool={tool}>
                  <span
                    class="pill"
                    data-state={row.integrations[tool]}
                    title={pillTitle(tool, row.integrations[tool], row.citations[tool])}
                  >
                    {row.integrations[tool] === 'yes' ? '●' :
                     row.integrations[tool] === 'no'  ? '○' : '–'}
                  </span>
                </td>
              {/each}
              <td class="cov-col">
                <span class="cov-num">{row.coverageCount}</span>
                <span class="cov-meta">/ 7</span>
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
                        {row.coverageCount} supported ·
                        {row.explicitNoCount} explicit no ·
                        {row.unknownCount} unknown
                      </span>
                    </h3>
                    <ul class="drill-list">
                      {#each OBS_TOOLS as tool}
                        {@const state = row.integrations[tool]}
                        {@const citation = row.citations[tool]}
                        <li>
                          <span class="drill-label">{TOOL_LABEL[tool]}</span>
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
                        </li>
                      {/each}
                    </ul>
                    {#if row.customText}
                      <p class="drill-custom">
                        <strong>Custom / notes:</strong>
                        {row.customText}
                        {#if row.customCitation}
                          <a
                            href={row.customCitation}
                            target="_blank"
                            rel="noopener noreferrer"
                            onclick={(e) => e.stopPropagation()}
                          > ↗</a>
                        {/if}
                      </p>
                    {/if}
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

  <footer class="ob-footer">
    <a href="{base}/analyses">← Analyses hub</a>
    <span class="muted">
      Pivot of <code>obs-*</code> cells. Helper in
      <code>$lib/analyses/observability.ts</code>. Schema in
      <code>docs/SCHEMA.md</code> §2.5.1.
    </span>
  </footer>
</main>

<style>
  .ob-page {
    max-width: 1600px;
    margin: 0 auto;
    padding: 24px 8px 64px;
    color: #e8e8e8;
  }
  .ob-header { margin-bottom: 18px; }
  .crumb { margin: 0 0 8px 0; font-size: 13px; }
  .crumb a { color: #aaa; text-decoration: none; }
  .crumb a:hover { color: #e8e8e8; }
  .ob-header h1 {
    font-size: 28px; margin: 0 0 10px 0; letter-spacing: -0.01em;
  }
  .ob-intro {
    color: #c9c9c9; max-width: 920px; margin: 0 0 12px 0;
    line-height: 1.6; font-size: 14px;
  }
  .ob-intro strong { color: #e8e8e8; }
  .ob-intro em { color: #c0c0c0; font-style: italic; }
  .ob-intro a { color: #d4845f; }
  .ob-coverage-note {
    background: #14191d;
    border-left: 3px solid #d4845f;
    padding: 10px 14px;
    border-radius: 0 4px 4px 0;
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
    border-left: 3px solid #6b9a4a;
  }
  .callout h2 {
    margin: 0 0 6px 0; font-size: 14px;
    color: #8ec99a; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .callout-sub { color: #888; font-size: 11.5px; margin: 0 0 10px 0; }
  .callout-foot {
    color: #c9c9c9; font-size: 12.5px; margin: 8px 0 0 0;
    padding-top: 8px; border-top: 1px solid #232323;
  }
  .callout-foot strong { color: #d4845f; }

  .tool-bars {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 6px;
  }
  .tool-bar {
    display: grid;
    grid-template-columns: 110px 1fr 40px 60px;
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
    background: #6b9a4a;
    border-radius: 3px; transition: width 200ms;
  }
  .tool-bar-fill[data-tool='langsmith'] { background: #d4845f; }
  .tool-bar-fill[data-tool='opentelemetry'] { background: #9fc5e0; }
  .tool-bar-fill[data-tool='datadog'] { background: #c89a5a; }
  .tool-bar-fill[data-tool='helicone'] { background: #c87a8a; }
  .tool-bar-fill[data-tool='weave'] { background: #a868c8; }
  .tool-bar-fill[data-tool='langfuse'] { background: #6b9a4a; }
  .tool-bar-fill[data-tool='arize'] { background: #5ac8b8; }
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
    outline: none; border-color: #d4845f;
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
  .board-table thead th.tool-col {
    text-align: center;
    color: #c9c9c9;
  }
  .board-table thead th.cov-col {
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
  .prod-link:hover { color: #d4845f; }

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

  .tool-cell {
    text-align: center;
    padding: 4px 6px !important;
  }

  .cov-col {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    min-width: 60px;
  }
  .cov-num {
    color: #f4e2cb; font-weight: 600; font-size: 13px;
  }
  .cov-meta { color: #777; font-size: 11px; margin-left: 2px; }

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
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 4px 14px;
  }
  .drill-list li {
    display: flex; align-items: center; gap: 8px;
    font-size: 12px;
    padding: 3px 0;
  }
  .drill-label {
    color: #c9c9c9; flex: 1;
  }
  .drill-citation {
    color: #d4845f; text-decoration: none;
    font-size: 11px;
  }
  .drill-citation:hover { text-decoration: underline; }

  .drill-custom {
    margin: 10px 0 6px 0; padding: 8px 12px;
    background: #14191d; border-left: 2px solid #d4845f;
    border-radius: 0 4px 4px 0;
    color: #c9c9c9; font-size: 12.5px; line-height: 1.5;
  }
  .drill-custom strong { color: #f4e2cb; }
  .drill-custom a { color: #d4845f; text-decoration: none; }
  .drill-custom a:hover { text-decoration: underline; }

  .drill-url {
    margin: 6px 0 0 0; font-size: 12px;
  }
  .drill-url a { color: #aaa; text-decoration: none; }
  .drill-url a:hover { color: #e8e8e8; }

  .empty-row {
    text-align: center; color: #888; font-style: italic;
    padding: 24px !important;
  }

  .ob-footer {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 24px; padding-top: 16px;
    border-top: 1px solid #2a2a2a;
    color: #aaa; font-size: 13px;
    flex-wrap: wrap; gap: 8px;
  }
  .ob-footer a { color: #aaa; text-decoration: none; }
  .ob-footer a:hover { color: #e8e8e8; }
  .muted { color: #777; font-size: 12.5px; }

  @media (max-width: 1100px) {
    .filters { gap: 10px 16px; }
    .tool-bar { grid-template-columns: 90px 1fr 36px 50px; gap: 6px; }
  }
</style>
