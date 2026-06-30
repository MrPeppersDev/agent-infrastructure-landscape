<script lang="ts">
  import SeoHead from '$lib/components/SeoHead.svelte';

  // Product × benchmark coverage matrix (issue #43).
  //
  // Companion-and-pivot to /analyses/benchmarks. That view is
  // benchmark-centric: rows are benchmarks, the lens is "is this
  // benchmark adopted?". This view flips the matrix to product-centric:
  // rows are products, the lens is "is this product publishing on
  // independently-verifiable terrain?". The cell colour at any
  // (product, benchmark) intersection is the integrity tier of the
  // strongest available citation — green when peer-reviewed, yellow
  // when only the vendor itself is making the claim, red when another
  // catalogued source actively disputes it, and so on.
  //
  // The headline filter — "only show products with zero peer-reviewed
  // mentions" — turns this view into a name-and-shame surface: it
  // reveals the population of products that have benchmark mentions in
  // their marketing copy but no peer-reviewed citation anywhere in the
  // catalog backing them up.
  //
  // Layout:
  //   1. Header: title, prose explainer
  //   2. Coverage callout: "X% of catalogued products report zero
  //      peer-reviewed benchmark scores"
  //   3. Filter row: refuses-to-publish toggle, sort mode, category
  //   4. Legend
  //   5. Matrix: sticky header + sticky first column; cells coloured
  //      by integrity tier, click → drilldown to that product
  //   6. Footer: link back to /analyses

  import {
    buildProductBenchmarkMatrix,
    refusesCallout,
    cellLookup,
    categoryOf,
    uniqueCategories,
    compareIntegrity,
    type IntegrityTier,
    type ProductRow
  } from '$lib/analyses/product-benchmark-matrix';
  import { base } from '$app/paths';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  // ----- core derivation -----------------------------------------------
  const matrix = $derived(buildProductBenchmarkMatrix(data.records));
  const lookup = $derived(cellLookup(matrix));
  const callout = $derived(refusesCallout(data.records, matrix));
  const categories = $derived(uniqueCategories(data.records));

  // ----- filter state ---------------------------------------------------
  let onlyRefuses = $state(false);
  let sortMode = $state<'coverage' | 'integrity' | 'alpha'>('coverage');
  let activeCategory = $state<string>('all');

  // For the refuses filter we need the set of product ids that lack any
  // peer-reviewed citation.
  const refusesIds = $derived.by(() => {
    const s = new Set<string>();
    for (const r of matrix.refusesToPublish) s.add(r.id);
    return s;
  });

  // Filtered + sorted product rows.
  const filteredProducts = $derived.by<ProductRow[]>(() => {
    let rows = matrix.products.slice();
    if (onlyRefuses) rows = rows.filter((p) => refusesIds.has(p.id));
    if (activeCategory !== 'all') {
      rows = rows.filter((p) => categoryOf(p.section) === activeCategory);
    }
    switch (sortMode) {
      case 'coverage':
        rows.sort(
          (a, b) =>
            b.coverageCount - a.coverageCount ||
            compareIntegrity(a.topIntegrity, b.topIntegrity) ||
            a.name.localeCompare(b.name)
        );
        break;
      case 'integrity':
        rows.sort(
          (a, b) =>
            compareIntegrity(a.topIntegrity, b.topIntegrity) ||
            b.coverageCount - a.coverageCount ||
            a.name.localeCompare(b.name)
        );
        break;
      case 'alpha':
        rows.sort((a, b) => a.name.localeCompare(b.name));
        break;
    }
    return rows;
  });

  // ----- presentation helpers ------------------------------------------
  function cellOf(productId: string, benchmark: string) {
    return lookup.get(`${productId}::${benchmark}`);
  }

  const integrityLabels: Record<IntegrityTier, string> = {
    'peer-reviewed': 'Peer-reviewed',
    'independently-verified': 'Independently verified',
    'vendor-claimed': 'Vendor-claimed',
    disputed: 'Disputed',
    unverifiable: 'Unverifiable',
    'no-mention': 'No mention'
  };

  const integrityBlurbs: Record<IntegrityTier, string> = {
    'peer-reviewed': 'Cited at a peer-reviewed venue (arXiv, OpenReview, ACL, IEEE, ACM, PMLR).',
    'independently-verified':
      'Cited at a non-vendor third party — neutral leaderboard or independent platform.',
    'vendor-claimed': 'Citation host matches the vendor’s own domain; vendor is making the claim.',
    disputed:
      'Another catalog row contradicts this number — in-cell dispute signal or >7-pt score divergence on the same benchmark.',
    unverifiable: 'No citation that resolves to a host, sentinel value, or depth-floor cell.',
    'no-mention': 'Product makes no mention of this benchmark anywhere in the catalogued cells.'
  };

  const tierLabels: Record<number, string> = {
    1: 'commercial',
    2: 'productized',
    3: 'framework',
    4: 'research',
    5: 'informal'
  };

  function productHref(name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  function pct(n: number): string {
    return `${n.toFixed(1)}%`;
  }

  // Truncate a long score string for in-cell display; full text shows on hover.
  function shortScore(s: string | undefined): string {
    if (!s) return '✓';
    if (s.length > 10) return s.slice(0, 9) + '…';
    return s;
  }
</script>

<svelte:head>
  <SeoHead
    title="Product-Benchmark Coverage: Integrity Tiers and Peer-Review Claims"
    description="Which products publish peer-reviewed benchmark claims? Matrix view showing integrity tiers from vendor-claimed to independently verified."
    path="/analyses/product-benchmark-matrix"
    ogType="article"
  />
</svelte:head>

<main class="pbm-page">
  <header class="pbm-header">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Product × benchmark coverage</h1>
    <p class="pbm-intro">
      The companion-and-pivot to
      <a href="{base}/analyses/benchmarks">benchmark coverage</a>. That view
      is benchmark-centric — rows are benchmarks, the lens is "is this
      benchmark adopted?". This view flips the matrix to
      <strong>product-centric</strong>: each row is a product, each column
      is a benchmark, and the cell colour is the integrity tier of the
      strongest available citation. The flip surfaces the angle no
      comparable catalog publishes: <em>which products refuse to put a
      peer-reviewed score on the record at all</em>.
    </p>
    <p class="pbm-stats">
      <strong>{filteredProducts.length}</strong> products
      {#if onlyRefuses}(refuses-to-publish only){/if}
      · <strong>{matrix.benchmarks.length}</strong> benchmarks shown
      · <strong>{matrix.cells.length}</strong> total cells filled
      {#if activeCategory !== 'all'} · category: <strong>{activeCategory}</strong>{/if}
    </p>
  </header>

  <section class="callout" aria-label="Refuses-to-publish callout">
    <div class="callout-num">{pct(callout.refusingPercent)}</div>
    <div class="callout-body">
      <h2>of catalogued products report zero peer-reviewed benchmark scores</h2>
      <p>
        Of <strong>{callout.totalProducts}</strong> records, only
        <strong>{callout.withPeerReviewed}</strong> have any benchmark mention
        backed by a peer-reviewed citation (arXiv, OpenReview, ACL, IEEE, ACM,
        PMLR). <strong>{callout.refusingProducts}</strong> products do not —
        either because they don't benchmark at all, or because the only
        citations are vendor-self-published. The toggle below narrows the
        matrix to the subset that <em>does</em> mention benchmarks but
        without peer-reviewed backing.
      </p>
    </div>
  </section>

  <section class="filter-row" aria-label="Filter controls">
    <label class="toggle">
      <input type="checkbox" bind:checked={onlyRefuses} />
      <span class="toggle-label">
        Only products with zero peer-reviewed mentions
        <span class="toggle-sub">refuses-to-publish filter</span>
      </span>
    </label>

    <span class="filter-label">Sort:</span>
    <div class="sort-group" role="radiogroup" aria-label="Sort mode">
      <button
        type="button"
        class="sort-btn"
        class:active={sortMode === 'coverage'}
        onclick={() => (sortMode = 'coverage')}
        role="radio"
        aria-checked={sortMode === 'coverage'}
      >
        coverage count
      </button>
      <button
        type="button"
        class="sort-btn"
        class:active={sortMode === 'integrity'}
        onclick={() => (sortMode = 'integrity')}
        role="radio"
        aria-checked={sortMode === 'integrity'}
      >
        best integrity
      </button>
      <button
        type="button"
        class="sort-btn"
        class:active={sortMode === 'alpha'}
        onclick={() => (sortMode = 'alpha')}
        role="radio"
        aria-checked={sortMode === 'alpha'}
      >
        alphabetical
      </button>
    </div>

    <span class="filter-label cat-label">Category:</span>
    <select bind:value={activeCategory} class="cat-select">
      <option value="all">All categories</option>
      {#each categories as c}
        <option value={c}>{c}</option>
      {/each}
    </select>
  </section>

  <section class="legend" aria-label="Integrity tier legend">
    <span class="legend-label">Cell colour:</span>
    {#each ['peer-reviewed', 'independently-verified', 'vendor-claimed', 'disputed', 'unverifiable', 'no-mention'] as t}
      {@const tier = t as IntegrityTier}
      <span class="legend-chip" data-tier={tier}>
        <span class="legend-swatch" data-tier={tier}></span>
        {integrityLabels[tier]}
      </span>
    {/each}
  </section>

  {#if filteredProducts.length === 0}
    <p class="empty">No products match the current filter.</p>
  {:else}
    <section class="matrix-wrap">
      <table class="matrix">
        <thead>
          <tr>
            <th class="prod-col" scope="col">Product</th>
            <th class="num-col" scope="col" title="Distinct benchmarks this product mentions">N</th>
            {#each matrix.benchmarks as b (b.name)}
              <th
                class="bench-col"
                class:headline={['LongMemEval', 'LoCoMo', 'BABILong', 'ConvoMem', 'RULER', 'MemoryAgentBench', 'NIAH'].includes(b.name)}
                scope="col"
                title="{b.name} — {b.mentionCount} mentions across the catalog"
              >
                <span class="bench-name">{b.name}</span>
                <span class="bench-count">{b.mentionCount}</span>
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each filteredProducts as p (p.id)}
            <tr>
              <th class="prod-col" scope="row">
                <a href={productHref(p.name)} class="prod-link">{p.name}</a>
                <span class="prod-meta">
                  <span class="tier-pill" data-tier={p.tier}>T{p.tier}</span>
                  <span class="cat-pill">{categoryOf(p.section)}</span>
                </span>
              </th>
              <td class="num-col"><span class="count-pill">{p.coverageCount}</span></td>
              {#each matrix.benchmarks as b (b.name)}
                {@const cell = cellOf(p.id, b.name)}
                {#if cell}
                  <td
                    class="cell"
                    data-tier={cell.integrity}
                    title={`${b.name}: ${cell.score || '(presence only)'} — ${integrityLabels[cell.integrity]}${cell.citation ? '\nCitation: ' + cell.citation : ''}`}
                  >
                    <a href={productHref(p.name)} class="cell-link">
                      <span class="cell-score">{shortScore(cell.score)}</span>
                    </a>
                  </td>
                {:else}
                  <td class="cell empty" data-tier="no-mention" aria-label="no mention"></td>
                {/if}
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </section>

    <section class="legend-details">
      <h2>What each integrity tier means</h2>
      <dl class="tier-rules">
        {#each ['peer-reviewed', 'independently-verified', 'vendor-claimed', 'disputed', 'unverifiable', 'no-mention'] as t}
          {@const tier = t as IntegrityTier}
          <div class="tier-rule" data-tier={tier}>
            <dt>
              <span class="legend-swatch small" data-tier={tier}></span>
              {integrityLabels[tier]}
            </dt>
            <dd>{integrityBlurbs[tier]}</dd>
          </div>
        {/each}
      </dl>
    </section>
  {/if}

  <footer class="pbm-footer">
    <a href="{base}/analyses">← Analyses hub</a>
    <span class="muted">
      Derived from <code>cells.perf</code> + <code>cells.claims</code> citations.
      Pivot helper in <code>$lib/analyses/product-benchmark-matrix.ts</code>.
    </span>
  </footer>
</main>

<style>
  .pbm-page {
    max-width: 1600px;
    margin: 0 auto;
    padding: 24px 8px 64px;
    color: #e8e8e8;
  }
  .pbm-header { margin-bottom: 18px; }
  .crumb { margin: 0 0 8px 0; font-size: 13px; }
  .crumb a { color: #aaa; text-decoration: none; }
  .crumb a:hover { color: #e8e8e8; }
  .pbm-header h1 {
    font-size: 28px; margin: 0 0 10px 0; letter-spacing: -0.01em;
  }
  .pbm-intro {
    color: #c9c9c9; max-width: 920px; margin: 0 0 12px 0;
    line-height: 1.6; font-size: 14px;
  }
  .pbm-intro em { color: #f0c894; font-style: normal; }
  .pbm-intro strong { color: #e8e8e8; }
  .pbm-intro a { color: #d4845f; }
  .pbm-stats { color: #d4d4d4; margin: 0; font-size: 13.5px; }
  .pbm-stats strong { color: #f0c894; }
  code {
    font-family: 'SF Mono', 'Menlo', Consolas, monospace;
    font-size: 12.5px; background: #1f1f1f;
    padding: 1px 5px; border-radius: 3px; color: #d4d4d4;
  }

  .callout {
    display: grid; grid-template-columns: auto 1fr; gap: 22px;
    align-items: center;
    background: #1d1410; border: 1px solid #4a2a1a;
    border-left: 3px solid #d4845f;
    border-radius: 8px;
    padding: 16px 22px; margin: 0 0 18px 0;
  }
  .callout-num {
    font-size: 56px; font-weight: 700; color: #d4845f;
    font-variant-numeric: tabular-nums; line-height: 1;
    padding-right: 6px; border-right: 1px solid #3a2418;
  }
  .callout-body h2 {
    margin: 0 0 6px 0; font-size: 17px; color: #e8e8e8;
    font-weight: 600; letter-spacing: -0.005em;
  }
  .callout-body p {
    margin: 0; color: #c0c0c0; font-size: 13px; line-height: 1.55;
    max-width: 800px;
  }
  .callout-body strong { color: #f0c894; }
  .callout-body em { color: #d4845f; font-style: normal; }

  .filter-row {
    display: flex; align-items: center; flex-wrap: wrap;
    gap: 12px; margin: 0 0 12px 0;
    padding: 10px 14px;
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 6px;
  }
  .toggle {
    display: flex; align-items: center; gap: 8px; cursor: pointer;
    padding-right: 10px; border-right: 1px solid #2a2a2a;
  }
  .toggle input[type='checkbox'] {
    width: 16px; height: 16px; cursor: pointer;
    accent-color: #d4845f;
  }
  .toggle-label {
    color: #d4d4d4; font-size: 13px; font-weight: 500;
    line-height: 1.3;
  }
  .toggle-sub {
    display: block; color: #888;
    font-size: 11px; font-weight: 400; font-style: italic;
  }
  .filter-label {
    color: #aaa; font-size: 12.5px; font-weight: 600; margin-right: 2px;
  }
  .filter-label.cat-label { margin-left: 6px; }
  .sort-group { display: inline-flex; gap: 4px; }
  .sort-btn {
    background: #1f1f1f; border: 1px solid #2a2a2a; color: #aaa;
    padding: 5px 10px; border-radius: 4px; cursor: pointer;
    font-size: 12px; font-weight: 500; transition: all 120ms;
  }
  .sort-btn:hover { color: #e8e8e8; border-color: #3a3a3a; }
  .sort-btn.active {
    background: #2a1a12; border-color: #6b3a26; color: #d4845f;
  }
  .cat-select {
    background: #1f1f1f; border: 1px solid #2a2a2a; color: #d4d4d4;
    padding: 5px 8px; border-radius: 4px; font-size: 12px;
    font-family: inherit; cursor: pointer;
  }
  .cat-select:focus {
    outline: none; border-color: #6b3a26;
  }

  .legend {
    display: flex; align-items: center; flex-wrap: wrap;
    gap: 8px 14px; margin: 0 0 14px 0;
    padding: 8px 14px;
    background: #161616; border: 1px solid #232323;
    border-radius: 6px;
  }
  .legend-label {
    color: #888; font-size: 11.5px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.05em;
  }
  .legend-chip {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 12px; color: #d4d4d4;
  }
  .legend-swatch {
    display: inline-block; width: 14px; height: 14px;
    border-radius: 3px; border: 1px solid #333;
  }
  .legend-swatch.small { width: 10px; height: 10px; }
  .legend-swatch[data-tier='peer-reviewed'] { background: #2c5e3a; border-color: #4a8a5e; }
  .legend-swatch[data-tier='independently-verified'] { background: #3a6b48; border-color: #5e9a6e; }
  .legend-swatch[data-tier='vendor-claimed'] { background: #6b5a1a; border-color: #9a8a3a; }
  .legend-swatch[data-tier='disputed'] { background: #6b2a26; border-color: #9a4a46; }
  .legend-swatch[data-tier='unverifiable'] { background: #3a3a3a; border-color: #555; }
  .legend-swatch[data-tier='no-mention'] {
    background: transparent; border: 1px dashed #3a3a3a;
  }

  .matrix-wrap {
    overflow-x: auto;
    max-height: 75vh; overflow-y: auto;
    border: 1px solid #2a2a2a; border-radius: 8px;
    background: #161616; margin-bottom: 28px;
  }
  .matrix {
    border-collapse: separate; border-spacing: 0;
    font-size: 12.5px; min-width: 100%;
  }
  .matrix thead th {
    position: sticky; top: 0; background: #1d1d1d;
    border-bottom: 1px solid #333;
    padding: 8px 8px; text-align: left;
    font-weight: 600; color: #d4d4d4; white-space: nowrap;
    z-index: 3;
  }
  .matrix thead th.prod-col {
    left: 0; z-index: 4;
    min-width: 240px; max-width: 280px;
  }
  .matrix thead th.num-col {
    left: 240px; z-index: 4;
    min-width: 44px; text-align: center;
    border-right: 1px solid #2a2a2a;
  }
  .matrix thead th.bench-col {
    text-align: center; min-width: 88px; max-width: 100px;
    padding: 6px 8px;
  }
  .matrix thead th.bench-col.headline {
    background: #2a1f12; color: #f0c894;
  }
  .bench-name {
    display: block; font-size: 12px; line-height: 1.2;
    overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap;
  }
  .bench-count {
    display: block; font-size: 10.5px; color: #888;
    font-weight: 400; margin-top: 2px;
    font-variant-numeric: tabular-nums;
  }
  .matrix thead th.bench-col.headline .bench-count { color: #c9a26e; }

  .matrix tbody th.prod-col {
    position: sticky; left: 0; background: #181818;
    border-right: 1px solid #2a2a2a;
    font-weight: 500; font-size: 13px;
    text-align: left; padding: 6px 10px;
    min-width: 240px; max-width: 280px;
    z-index: 2;
  }
  .matrix tbody td.num-col {
    position: sticky; left: 240px; background: #181818;
    border-right: 1px solid #2a2a2a;
    z-index: 2;
    text-align: center; min-width: 44px;
  }
  .prod-link {
    color: #e8e8e8; text-decoration: none; display: block;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .prod-link:hover { color: #d4845f; }
  .prod-meta {
    display: flex; align-items: center; gap: 4px; margin-top: 2px;
  }
  .matrix tbody tr:hover th.prod-col,
  .matrix tbody tr:hover td.num-col { background: #1f1f1f; }
  .matrix tbody tr:hover td.cell { filter: brightness(1.18); }

  .matrix tbody td {
    border-bottom: 1px solid #232323; padding: 0;
    vertical-align: middle;
  }
  .matrix tbody td.cell {
    text-align: center; font-variant-numeric: tabular-nums;
    min-width: 88px; max-width: 100px;
    cursor: pointer;
  }
  .cell-link {
    display: block; padding: 6px 8px;
    color: inherit; text-decoration: none;
  }
  .cell-score {
    display: inline-block;
    font-size: 11.5px; font-weight: 600;
  }
  .matrix .cell.empty {
    background: transparent; cursor: default;
  }
  .matrix .cell[data-tier='peer-reviewed'] {
    background: #2c5e3a; color: #d4f0c2;
  }
  .matrix .cell[data-tier='independently-verified'] {
    background: #3a6b48; color: #d4f0c2;
  }
  .matrix .cell[data-tier='vendor-claimed'] {
    background: #6b5a1a; color: #f4e2cb;
  }
  .matrix .cell[data-tier='disputed'] {
    background: #6b2a26; color: #f4cdcb;
  }
  .matrix .cell[data-tier='unverifiable'] {
    background: #3a3a3a; color: #c0c0c0;
  }

  .count-pill {
    display: inline-block; background: #2a2a2a; color: #d4845f;
    padding: 1px 7px; border-radius: 10px;
    font-size: 11.5px; font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .tier-pill {
    display: inline-block; font-size: 9.5px; font-weight: 600;
    padding: 1px 5px; border-radius: 3px;
    background: #2a2a2a; color: #aaa;
    font-variant-numeric: tabular-nums; flex-shrink: 0;
  }
  .tier-pill[data-tier='1'] { background: #1a3a2a; color: #8ec99a; }
  .tier-pill[data-tier='2'] { background: #2a3a1a; color: #c9c98e; }
  .tier-pill[data-tier='3'] { background: #3a2a1a; color: #c9a28e; }
  .tier-pill[data-tier='4'] { background: #2a2030; color: #b59ad4; }
  .tier-pill[data-tier='5'] { background: #2a2a2a; color: #888; }
  .cat-pill {
    display: inline-block; font-size: 9.5px;
    padding: 1px 5px; border-radius: 3px;
    background: #1c2530; color: #8eb4d4;
    font-weight: 500;
  }

  .legend-details {
    background: #161616; border: 1px solid #232323;
    border-radius: 8px; padding: 14px 18px;
    margin-bottom: 24px;
  }
  .legend-details h2 {
    margin: 0 0 10px 0; font-size: 13px;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: #d4845f; font-weight: 600;
  }
  .tier-rules {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 8px 18px; margin: 0;
  }
  .tier-rule { display: flex; flex-direction: column; gap: 3px; }
  .tier-rule dt {
    margin: 0; display: flex; align-items: center; gap: 6px;
    color: #e8e8e8; font-size: 12.5px; font-weight: 600;
  }
  .tier-rule dd {
    margin: 0; color: #b0b0b0; font-size: 12px; line-height: 1.5;
  }

  .pbm-footer {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 24px; padding-top: 16px;
    border-top: 1px solid #2a2a2a;
    color: #aaa; font-size: 13px;
  }
  .pbm-footer a { color: #aaa; text-decoration: none; }
  .pbm-footer a:hover { color: #e8e8e8; }
  .muted { color: #777; font-size: 12.5px; }
  .empty {
    color: #888; font-style: italic;
    padding: 24px; text-align: center;
  }

  @media (max-width: 900px) {
    .callout { grid-template-columns: 1fr; gap: 8px; }
    .callout-num { border-right: none; border-bottom: 1px solid #3a2418; padding-bottom: 8px; }
    .filter-row { flex-direction: column; align-items: stretch; gap: 10px; }
    .toggle { border-right: none; border-bottom: 1px solid #2a2a2a; padding-bottom: 10px; }
  }
</style>
