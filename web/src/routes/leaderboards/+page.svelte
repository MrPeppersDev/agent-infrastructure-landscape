<script lang="ts">
  // Leaderboards view (issue #14). Five curated boards + a "build your own"
  // panel. Everything renders from data already bundled with the app; no
  // fetch, no SSR-side compute.
  //
  // Strict file scope per issue: only this folder + lib/leaderboards.ts.
  // Stores are read-only here; we don't write filter state — the user can
  // jump into the main table via "Open in table" links, which carry a
  // ?search= query the existing table page will pick up.

  import {
    topBy,
    topByInboundEdges,
    cellExtractor,
    customExtractor,
    filterForCustom,
    distinctSections,
    primarySection,
    isResearchTier,
    ALL_TIERS,
    CUSTOM_COLUMNS,
    type CustomColumn,
    type Ranked
  } from '$lib/leaderboards';
  import { base } from '$app/paths';
  import type { LandscapeRecord, Edge, Tier } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[]; edges: Edge[] } } = $props();

  // --- Curated boards (computed once; data is bundled, never mutates) ---

  // 1. Most-cited research papers: T3/T4 only. Tier filter happens before
  //    extraction so we don't waste cycles parsing commercial-product
  //    citation cells that are all "not applicable".
  const mostCited = $derived(
    topBy(
      data.records.filter(isResearchTier),
      cellExtractor('citations'),
      10
    )
  );

  // 2. Most-starred OSS.
  const mostStarred = $derived(topBy(data.records, cellExtractor('gh'), 10));

  // 3. Best-funded commercial.
  const bestFunded = $derived(topBy(data.records, cellExtractor('funding'), 10));

  // 4. Highest inbound citations within the catalog.
  const mostInboundCites = $derived(
    topByInboundEdges(data.records, data.edges, ['cites'], 10)
  );

  // 5. Highest inbound integrations (built-on + integrates-with). Mem0
  //    should top this at 12.
  const mostIntegrated = $derived(
    topByInboundEdges(
      data.records,
      data.edges,
      ['integrates-with', 'built-on'],
      10
    )
  );

  // --- Custom mode -----------------------------------------------------

  let customCol = $state<CustomColumn>('citations');
  let customN = $state(10);
  let customTiers = $state<Set<Tier>>(new Set<Tier>());
  let customSections = $state<Set<string>>(new Set<string>());

  const sectionOptions = $derived(distinctSections(data.records));

  const customResults = $derived.by<Ranked[]>(() => {
    const pool = filterForCustom(data.records, customTiers, customSections);
    return topBy(pool, customExtractor(customCol), customN);
  });

  function toggleTier(t: Tier) {
    const next = new Set(customTiers);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    customTiers = next;
  }

  function toggleSection(s: string) {
    const next = new Set(customSections);
    if (next.has(s)) next.delete(s);
    else next.add(s);
    customSections = next;
  }

  // --- Display helpers --------------------------------------------------

  function fmt(n: number): string {
    if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
    return `${Math.round(n)}`;
  }

  // Drill-down link: drop the user on the table view with a search query
  // for the record's name. The table page's URL codec uses ?q= (see
  // lib/url-state.ts) so we match that.
  function tableHref(r: LandscapeRecord): string {
    return `${base}/?q=${encodeURIComponent(r.name)}`;
  }

  // Stats line for the commit message + page footer.
  const totalRanked = $derived(
    mostCited.length +
      mostStarred.length +
      bestFunded.length +
      mostInboundCites.length +
      mostIntegrated.length
  );
</script>

<svelte:head>
  <title>Leaderboards — Memory Landscape</title>
</svelte:head>

<main class="lb-page">
  <header class="lb-header">
    <h1>Leaderboards</h1>
    <p class="lb-sub">
      Top-N rankings across the {data.records.length}-record memory-systems
      catalog. Curated boards below cover the headline signals (citations,
      stars, funding, in-catalog citation graph, integration centrality).
      Use the "build your own" panel at the bottom for ad-hoc queries.
    </p>
  </header>

  <section class="grid">
    {#each [{ title: 'Most-cited research (T3 / T4)', desc: 'Papers ranked by Semantic Scholar citation count parsed from the citations cell.', rows: mostCited, valueHeader: 'Citations' }, { title: 'Most-starred OSS', desc: 'GitHub repos ranked by leading star count in the gh cell ("18.8k★ / 1.4k forks" → 18 800).', rows: mostStarred, valueHeader: 'Stars' }, { title: 'Best-funded commercial', desc: 'Records ranked by the leading dollar figure in the funding cell. "Total raised" wins over "valuation" because the headline number leads.', rows: bestFunded, valueHeader: 'Funding' }, { title: 'Highest inbound citations (in-catalog)', desc: 'How many other records in the catalog cite this one. Pure graph metric — no external lookup.', rows: mostInboundCites, valueHeader: 'Inbound cites' }, { title: 'Most-integrated (built-on + integrates-with)', desc: 'How many other records depend on or integrate this one. Mem0 should top this list.', rows: mostIntegrated, valueHeader: 'Inbound' }] as board (board.title)}
      <article class="card">
        <h2>{board.title}</h2>
        <p class="card-desc">{board.desc}</p>
        {#if board.rows.length === 0}
          <p class="empty">No rankable records.</p>
        {:else}
          <table>
            <thead>
              <tr>
                <th class="rank">#</th>
                <th>Name</th>
                <th class="num">{board.valueHeader}</th>
              </tr>
            </thead>
            <tbody>
              {#each board.rows as row, i (row.record.id)}
                <tr>
                  <td class="rank">{i + 1}</td>
                  <td>
                    <a href={tableHref(row.record)} title="Open in main table">
                      {row.record.name}
                    </a>
                    <span class="tier-pill">T{row.record.tier}</span>
                  </td>
                  <td class="num" title={row.display}>{fmt(row.value)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </article>
    {/each}
  </section>

  <section class="custom">
    <h2>Build your own</h2>
    <p class="card-desc">
      Pick a ranking column and optionally narrow to specific tiers or
      sections. Results update live.
    </p>

    <div class="controls">
      <label>
        <span>Rank by</span>
        <select bind:value={customCol}>
          {#each CUSTOM_COLUMNS as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
      </label>

      <label>
        <span>Top N</span>
        <input
          type="number"
          min="1"
          max="100"
          step="1"
          bind:value={customN}
        />
      </label>

      <fieldset>
        <legend>Tier</legend>
        {#each ALL_TIERS as t}
          <label class="chip">
            <input
              type="checkbox"
              checked={customTiers.has(t)}
              onchange={() => toggleTier(t)}
            />
            T{t}
          </label>
        {/each}
      </fieldset>

      <fieldset class="sections">
        <legend>Section</legend>
        <div class="section-chips">
          {#each sectionOptions as s}
            <label class="chip">
              <input
                type="checkbox"
                checked={customSections.has(s)}
                onchange={() => toggleSection(s)}
              />
              {s}
            </label>
          {/each}
        </div>
      </fieldset>
    </div>

    {#if customResults.length === 0}
      <p class="empty">No records match the current filters with a parseable value.</p>
    {:else}
      <table>
        <thead>
          <tr>
            <th class="rank">#</th>
            <th>Name</th>
            <th>Section</th>
            <th class="num">Value</th>
            <th>Raw cell</th>
          </tr>
        </thead>
        <tbody>
          {#each customResults as row, i (row.record.id)}
            <tr>
              <td class="rank">{i + 1}</td>
              <td>
                <a href={tableHref(row.record)}>{row.record.name}</a>
                <span class="tier-pill">T{row.record.tier}</span>
              </td>
              <td>{primarySection(row.record)}</td>
              <td class="num">{fmt(row.value)}</td>
              <td class="raw">{row.display}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <footer class="lb-footer">
    <a href="{base}/">← Back to table</a>
    <span class="muted">
      {totalRanked} rows across 5 curated boards · {CUSTOM_COLUMNS.length}
      custom ranking columns
    </span>
  </footer>
</main>

<style>
  .lb-page {
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px 8px 64px;
  }

  .lb-header {
    margin-bottom: 32px;
  }

  .lb-header h1 {
    font-size: 28px;
    margin: 0 0 8px 0;
  }

  .lb-sub {
    color: var(--c-muted);
    max-width: 720px;
    margin: 0;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
    gap: 16px;
    margin-bottom: 40px;
  }

  .card,
  .custom {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--radius);
    padding: 16px;
  }

  .card h2,
  .custom h2 {
    font-size: 16px;
    margin: 0 0 4px 0;
  }

  .card-desc {
    color: var(--c-muted);
    font-size: 13px;
    margin: 0 0 12px 0;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }

  thead th {
    text-align: left;
    font-weight: 600;
    font-size: 12px;
    color: var(--c-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--c-border);
    padding: 6px 8px;
  }

  tbody td {
    padding: 6px 8px;
    border-bottom: 1px solid rgba(48, 54, 61, 0.5);
    vertical-align: top;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  .rank {
    width: 2.5em;
    color: var(--c-muted);
    font-variant-numeric: tabular-nums;
  }

  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-family: var(--font-mono);
    font-size: 13px;
  }

  .raw {
    color: var(--c-muted);
    font-size: 12px;
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tier-pill {
    display: inline-block;
    margin-left: 6px;
    padding: 0 6px;
    font-size: 10px;
    line-height: 16px;
    border-radius: 8px;
    background: var(--c-accent-bg);
    color: var(--c-accent);
    vertical-align: 1px;
  }

  .empty {
    color: var(--c-muted);
    font-style: italic;
    margin: 0;
    font-size: 13px;
  }

  .custom {
    margin-bottom: 32px;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: flex-start;
    margin: 12px 0 16px 0;
  }

  .controls label > span {
    display: block;
    font-size: 12px;
    color: var(--c-muted);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .controls select,
  .controls input[type='number'] {
    background: var(--c-bg);
    color: var(--c-text);
    border: 1px solid var(--c-border);
    border-radius: 4px;
    padding: 6px 8px;
    font-family: inherit;
    font-size: 13px;
    min-width: 200px;
  }

  .controls input[type='number'] {
    min-width: 80px;
    width: 80px;
  }

  fieldset {
    border: 1px solid var(--c-border);
    border-radius: 4px;
    padding: 8px 12px;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    align-items: center;
  }

  fieldset legend {
    font-size: 11px;
    color: var(--c-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0 4px;
  }

  .sections {
    flex: 1 1 100%;
  }

  .section-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: var(--c-text);
    cursor: pointer;
    user-select: none;
  }

  .chip input {
    margin: 0;
  }

  .lb-footer {
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid var(--c-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
  }

  .muted {
    color: var(--c-muted);
  }
</style>
