<script lang="ts">
  // /sections — per-section aggregates + 2-section compare view (issue #15).
  //
  // The whole view is one Svelte file by design: it's a single page with
  // tight cohesion (cards + compare panel) and ~ a screen of UI. Splitting
  // into sub-components would force prop drilling for the aggregate shape
  // for no real reuse benefit (the Phase-4 graph will consume the pure
  // helpers from section-stats.ts directly, not the rendered cards).
  //
  // Filter integration: we read the global `filters` store and re-aggregate
  // when it changes. Honouring filters means a user can ask "in T1-only
  // systems, which section has the highest median funding?" via the rail
  // on the main page, then jump here. We don't render a rail on this page
  // — the existing rail is rooted in the table view. A small banner shows
  // when filters are active so the user knows the cards are scoped.
  import type { LandscapeRecord } from '$lib/types';
  import { filters, applyFilters, isEmpty } from '$lib/stores/filters';
  import {
    aggregateAllSections,
    formatCompact,
    topNWithOther,
    deltaLabel,
    type SectionAggregate,
    type CategoryCount
  } from '$lib/section-stats';

  let { data }: { data: { records: LandscapeRecord[]; recordCount: number } } =
    $props();

  const TIERS = [1, 2, 3, 4, 5] as const;
  const AXES = [
    'storage',
    'retrieval',
    'persistence',
    'update',
    'unit',
    'governance',
    'conflict'
  ] as const;

  const visibleRecords = $derived(applyFilters(data.records, $filters));
  const sections = $derived(aggregateAllSections(visibleRecords));
  const filtersActive = $derived(!isEmpty($filters));

  // Compare-mode dropdown selections. Default to the two largest sections
  // so the page lands on something meaningful even if the user doesn't pick.
  let compareA = $state<string>('');
  let compareB = $state<string>('');
  $effect(() => {
    if (sections.length === 0) return;
    if (!compareA || !sections.find((s) => s.section === compareA)) {
      compareA = sections[0].section;
    }
    if (!compareB || !sections.find((s) => s.section === compareB)) {
      compareB = sections[1]?.section ?? sections[0].section;
    }
  });

  const sectionA = $derived(sections.find((s) => s.section === compareA));
  const sectionB = $derived(sections.find((s) => s.section === compareB));

  // Max tier count across all sections — used to scale the sparkline bars
  // so visual height is comparable across cards.
  const maxTierCount = $derived(
    Math.max(
      1,
      ...sections.flatMap((s) => TIERS.map((t) => s.tierCounts[t]))
    )
  );

  function tierPct(count: number): number {
    return (count / maxTierCount) * 100;
  }

  function barPct(value: number, total: number): number {
    return total > 0 ? (value / total) * 100 : 0;
  }
</script>

<svelte:head>
  <title>Sections — Memory Systems Landscape</title>
</svelte:head>

<div class="wrap">
  <header class="hdr">
    <div>
      <h1>Section-vs-section</h1>
      <p class="sub">
        {sections.length} sections · {visibleRecords.length.toLocaleString()} of
        {data.recordCount.toLocaleString()} records
        {#if filtersActive}
          · <span class="filter-tag">filtered</span>
        {/if}
      </p>
    </div>
    <nav class="nav">
      <a href="./">Table</a>
    </nav>
  </header>

  <!-- Compare panel: 2 dropdowns + side-by-side cards with deltas. -->
  <section class="compare">
    <div class="compare-controls">
      <label>
        <span>A</span>
        <select bind:value={compareA}>
          {#each sections as s}
            <option value={s.section}>{s.section} ({s.rowCount})</option>
          {/each}
        </select>
      </label>
      <span class="vs">vs</span>
      <label>
        <span>B</span>
        <select bind:value={compareB}>
          {#each sections as s}
            <option value={s.section}>{s.section} ({s.rowCount})</option>
          {/each}
        </select>
      </label>
    </div>

    {#if sectionA && sectionB}
      <div class="compare-grid">
        {#each [sectionA, sectionB] as side, i}
          <article class="card card-compare">
            <header class="card-hdr">
              <h2>{side.section}</h2>
              <span class="row-count">{side.rowCount} rows</span>
            </header>

            <div class="metrics">
              {#each [
                { label: 'Median citations', a: sectionA.numeric.citations.median, b: sectionB.numeric.citations.median, cur: false },
                { label: 'Median GH stars', a: sectionA.numeric.gh.median, b: sectionB.numeric.gh.median, cur: false },
                { label: 'Median funding', a: sectionA.numeric.funding.median, b: sectionB.numeric.funding.median, cur: true },
                { label: 'Median mindshare', a: sectionA.numeric.mindshare.median, b: sectionB.numeric.mindshare.median, cur: false }
              ] as m}
                {@const own = i === 0 ? m.a : m.b}
                {@const other = i === 0 ? m.b : m.a}
                {@const delta = i === 0 ? deltaLabel(m.b, m.a, m.cur) : deltaLabel(m.a, m.b, m.cur)}
                {@const sign = own === null || other === null ? 0 : (own - other)}
                <div class="metric">
                  <span class="m-label">{m.label}</span>
                  <span class="m-value">{formatCompact(own, m.cur)}</span>
                  <span
                    class="m-delta"
                    class:up={sign > 0}
                    class:down={sign < 0}
                  >{delta}</span>
                </div>
              {/each}
            </div>

            <h3 class="block-h">Tier</h3>
            <div class="tier-row">
              {#each TIERS as t}
                <div class="tier-cell">
                  <div class="tier-bar" style="height:{tierPct(side.tierCounts[t])}%"></div>
                  <span class="tier-lab">T{t}</span>
                  <span class="tier-n">{side.tierCounts[t]}</span>
                </div>
              {/each}
            </div>

            <h3 class="block-h">Taxonomy</h3>
            <div class="axes">
              {#each AXES as axis}
                {@const top = topNWithOther(side.taxonomy[axis], 3)}
                <div class="axis">
                  <span class="axis-name">{axis}</span>
                  <div class="axis-bars">
                    {#each top.top as c}
                      <div class="row">
                        <span class="row-lab" title={c.value}>{c.value}</span>
                        <div class="row-bar"><div class="row-fill" style="width:{barPct(c.count, side.rowCount)}%"></div></div>
                        <span class="row-n">{c.count}</span>
                      </div>
                    {/each}
                    {#if top.otherDistinct > 0}
                      <div class="row row-other">
                        <span class="row-lab">+ {top.otherDistinct} other</span>
                        <div class="row-bar"><div class="row-fill row-fill-other" style="width:{barPct(top.otherCount, side.rowCount)}%"></div></div>
                        <span class="row-n">{top.otherCount}</span>
                      </div>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>

            <h3 class="block-h">License · Deployment</h3>
            <div class="dual">
              <div>
                <strong>License</strong>
                {#each topNWithOther(side.license, 3).top as c}
                  <div class="mini-row">
                    <span>{c.value}</span><span>{c.count}</span>
                  </div>
                {/each}
              </div>
              <div>
                <strong>Deployment</strong>
                {#each topNWithOther(side.deployment, 3).top as c}
                  <div class="mini-row">
                    <span>{c.value}</span><span>{c.count}</span>
                  </div>
                {/each}
              </div>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>

  <!-- Full grid of every section's card. -->
  <section class="all">
    <h2 class="all-h">All sections</h2>
    <div class="grid">
      {#each sections as s}
        <article class="card">
          <header class="card-hdr">
            <h3>{s.section}</h3>
            <span class="row-count">{s.rowCount}</span>
          </header>

          <!-- Tier sparkline -->
          <div class="tier-row tier-row-mini">
            {#each TIERS as t}
              <div class="tier-cell">
                <div class="tier-bar" style="height:{tierPct(s.tierCounts[t])}%"></div>
                <span class="tier-lab">T{t}</span>
                <span class="tier-n">{s.tierCounts[t]}</span>
              </div>
            {/each}
          </div>

          <div class="numeric-row">
            <div><span class="nlab">med citations</span><span class="nval">{formatCompact(s.numeric.citations.median)}</span></div>
            <div><span class="nlab">med GH stars</span><span class="nval">{formatCompact(s.numeric.gh.median)}</span></div>
            <div><span class="nlab">med funding</span><span class="nval">{formatCompact(s.numeric.funding.median, true)}</span></div>
          </div>

          <div class="axes axes-mini">
            {#each AXES as axis}
              {@const top = topNWithOther(s.taxonomy[axis], 3)}
              <div class="axis">
                <span class="axis-name">{axis}</span>
                <div class="axis-bars">
                  {#each top.top as c}
                    <div class="row">
                      <span class="row-lab" title={c.value}>{c.value}</span>
                      <div class="row-bar"><div class="row-fill" style="width:{barPct(c.count, s.rowCount)}%"></div></div>
                      <span class="row-n">{c.count}</span>
                    </div>
                  {/each}
                  {#if top.otherDistinct > 0}
                    <div class="row row-other">
                      <span class="row-lab">+ {top.otherDistinct} other</span>
                      <div class="row-bar"><div class="row-fill row-fill-other" style="width:{barPct(top.otherCount, s.rowCount)}%"></div></div>
                      <span class="row-n">{top.otherCount}</span>
                    </div>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        </article>
      {/each}
    </div>
  </section>
</div>

<style>
  .wrap {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 4px 0 32px;
    color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  .hdr {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 1px solid #21262d;
    padding-bottom: 8px;
  }
  h1 {
    font-size: 1.4rem;
    margin: 0;
    letter-spacing: -0.01em;
  }
  .sub {
    color: #8b949e;
    font-size: 0.85rem;
    margin: 4px 0 0 0;
  }
  .filter-tag {
    background: #1f6feb;
    color: #fff;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 500;
  }
  .nav a {
    color: #58a6ff;
    font-size: 0.85rem;
    text-decoration: none;
  }
  .nav a:hover { text-decoration: underline; }

  /* --- Compare panel --- */
  .compare {
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 14px;
    background: #0d1117;
  }
  .compare-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }
  .compare-controls label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
  }
  .compare-controls label span {
    color: #8b949e;
    font-weight: 600;
  }
  .compare-controls select {
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 0.85rem;
    min-width: 220px;
  }
  .vs {
    color: #6e7681;
    font-size: 0.8rem;
    font-style: italic;
  }
  .compare-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  @media (max-width: 900px) {
    .compare-grid { grid-template-columns: 1fr; }
  }

  /* --- Card (shared between compare + all-sections grid) --- */
  .card {
    border: 1px solid #21262d;
    border-radius: 6px;
    background: #0d1117;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }
  .card-compare {
    background: #11161e;
  }
  .card-hdr {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
  }
  .card-hdr h2, .card-hdr h3 {
    margin: 0;
    font-size: 0.95rem;
    line-height: 1.2;
    color: #f0f6fc;
  }
  .card-hdr h3 { font-size: 0.85rem; }
  .row-count {
    color: #8b949e;
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
  }

  /* --- Compare metrics row --- */
  .metrics {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px 12px;
    margin: 4px 0;
  }
  .metric {
    display: flex;
    flex-direction: column;
    gap: 1px;
    font-variant-numeric: tabular-nums;
  }
  .m-label {
    font-size: 0.7rem;
    color: #8b949e;
  }
  .m-value {
    font-size: 1rem;
    color: #f0f6fc;
    font-weight: 500;
  }
  .m-delta {
    font-size: 0.72rem;
    color: #6e7681;
  }
  .m-delta.up { color: #3fb950; }
  .m-delta.down { color: #f85149; }

  /* --- Block headings inside cards --- */
  .block-h {
    margin: 4px 0 2px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6e7681;
    font-weight: 600;
  }

  /* --- Tier sparkline --- */
  .tier-row {
    display: flex;
    align-items: flex-end;
    gap: 4px;
    height: 48px;
  }
  .tier-row-mini { height: 36px; }
  .tier-cell {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    height: 100%;
    position: relative;
    min-width: 0;
  }
  .tier-bar {
    width: 100%;
    background: linear-gradient(180deg, #58a6ff 0%, #1f6feb 100%);
    border-radius: 2px 2px 0 0;
    min-height: 2px;
  }
  .tier-lab {
    font-size: 0.62rem;
    color: #8b949e;
    margin-top: 2px;
  }
  .tier-n {
    position: absolute;
    top: -2px;
    font-size: 0.6rem;
    color: #6e7681;
    font-variant-numeric: tabular-nums;
  }

  /* --- Numeric row (small cards) --- */
  .numeric-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    font-variant-numeric: tabular-nums;
  }
  .numeric-row > div {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 4px 6px;
    background: #161b22;
    border-radius: 4px;
  }
  .nlab {
    font-size: 0.62rem;
    color: #6e7681;
    text-transform: lowercase;
  }
  .nval {
    font-size: 0.85rem;
    color: #f0f6fc;
  }

  /* --- Axes (taxonomy distribution bars) --- */
  .axes {
    display: grid;
    grid-template-columns: 1fr;
    gap: 6px;
  }
  .axes-mini {
    grid-template-columns: 1fr 1fr;
    gap: 4px 10px;
  }
  .axis {
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 0;
  }
  .axis-name {
    font-size: 0.65rem;
    color: #8b949e;
    text-transform: capitalize;
    font-weight: 600;
  }
  .axis-bars {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .row {
    display: grid;
    grid-template-columns: 70px 1fr 22px;
    align-items: center;
    gap: 4px;
    font-size: 0.7rem;
    font-variant-numeric: tabular-nums;
  }
  .row-lab {
    color: #c9d1d9;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .row-bar {
    background: #161b22;
    height: 8px;
    border-radius: 2px;
    overflow: hidden;
  }
  .row-fill {
    background: #2ea043;
    height: 100%;
    border-radius: 2px;
  }
  .row-fill-other {
    background: #30363d;
  }
  .row-n {
    color: #8b949e;
    text-align: right;
  }
  .row-other .row-lab {
    color: #6e7681;
    font-style: italic;
  }

  /* --- Dual block (license + deployment) --- */
  .dual {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    font-size: 0.75rem;
  }
  .dual strong {
    display: block;
    color: #8b949e;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 2px;
  }
  .mini-row {
    display: flex;
    justify-content: space-between;
    color: #c9d1d9;
    font-variant-numeric: tabular-nums;
    padding: 1px 0;
  }

  /* --- All-sections grid --- */
  .all-h {
    font-size: 0.95rem;
    margin: 8px 0 4px;
    color: #f0f6fc;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 10px;
  }
</style>
