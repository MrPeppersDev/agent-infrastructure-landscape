<script lang="ts">
  // Lineage forward-projection (issue #27, upgrade-#27).
  //
  // For each detected lineage we project where the next paper/product is
  // likely to land — strictly a "watch list, not a prediction" framing.
  // The maths is openly naïve (mean inter-arrival gap with a population
  // standard deviation as the prediction interval).
  //
  // Upgrade-#27 additions over the original view:
  //   - Narrative header + methodology callout + "so what" interpretation
  //   - Honest prediction intervals (Q ± stddev quarters), de-emphasised
  //     when the cadence-interval count is small
  //   - Low-N gating: "small sample" badge at N<5 members,
  //     "no cadence forecast" badge at <3 inter-arrival gaps (members<4)
  //   - Filters: kind (descent / pattern), curated vs auto, minimum-N slider
  //   - Drill: card title links to /lineages#<lineage-id>
  //   - Editorial "what to watch for" prose per curated lineage
  //
  // Lineage detection itself is owned by $lib/lineages.ts (read-only from
  // this scope). All forecast-specific maths lives in
  // $lib/analyses/forecast.ts.

  import { base } from '$app/paths';
  import { goto } from '$app/navigation';
  import type { Edge, LandscapeRecord } from '$lib/types';
  import { forecastAll, cadenceMonths, type LineageForecast } from '$lib/analyses/forecast';

  let {
    data
  }: { data: { records: LandscapeRecord[]; edges: Edge[] } } = $props();

  const forecasts = $derived<LineageForecast[]>(
    forecastAll(data.records, data.edges)
  );

  // Quick lookup so clicking a leading-edge id can pivot to a record name.
  const byId = $derived<Map<string, LandscapeRecord>>(
    new Map(data.records.map((r) => [r.id, r]))
  );

  // --- Filters ----------------------------------------------------------
  //
  // Three orthogonal filters: lineage kind, curation provenance, and
  // minimum member count. We keep them simple (radio + slider) because
  // the universe is small (~8 lineages) and aggressive filtering would
  // empty the page.
  type KindFilter = 'all' | 'descent' | 'pattern';
  type CuratedFilter = 'all' | 'curated' | 'auto';
  let kindFilter = $state<KindFilter>('all');
  let curatedFilter = $state<CuratedFilter>('all');
  let minN = $state<number>(3); // hide tiny families by default? no — show all so the gating badges are visible
  // Default to 3 (the smallest size detectLineages emits) so nothing
  // is hidden out of the gate; the slider lets the user push to 5+ when
  // they want to ignore the small-sample warnings.

  const filtered = $derived<LineageForecast[]>(
    forecasts.filter((f) => {
      if (kindFilter !== 'all' && f.kind !== kindFilter) return false;
      if (curatedFilter === 'curated' && !f.curated) return false;
      if (curatedFilter === 'auto' && f.curated) return false;
      if (f.members_total < minN) return false;
      return true;
    })
  );

  // Display order: by fastest cadence ascending (most active families
  // first), with NaN-cadence lineages sinking to the end. Within the
  // dated bucket curated lineages still appear in their declared order
  // implicitly because detectLineages emits them first.
  const sorted = $derived<LineageForecast[]>(
    [...filtered].sort((a, b) => {
      const aOk = isFinite(a.cadence_quarters);
      const bOk = isFinite(b.cadence_quarters);
      if (aOk && !bOk) return -1;
      if (!aOk && bOk) return 1;
      if (!aOk && !bOk) return a.lineage_name.localeCompare(b.lineage_name);
      return a.cadence_quarters - b.cadence_quarters;
    })
  );

  // Stats for the header / commit message. Always computed over the full
  // forecast set (not the filtered view) so the "X of Y lineages" hint
  // can show the filter's effect.
  const stats = $derived.by(() => {
    let fastest: LineageForecast | null = null;
    for (const f of forecasts) {
      if (!isFinite(f.cadence_quarters)) continue;
      if (!fastest || f.cadence_quarters < fastest.cadence_quarters) {
        fastest = f;
      }
    }
    return {
      total: forecasts.length,
      shown: filtered.length,
      fastest,
      smallSample: forecasts.filter((f) => f.low_n).length,
      noCadence: forecasts.filter((f) => f.insufficient_data).length
    };
  });

  // Lookup lineage by id for adjacent-lineage chip rendering.
  const lineageById = $derived<Map<string, LineageForecast>>(
    new Map(forecasts.map((f) => [f.lineage_id, f]))
  );

  function adjacentName(id: string): string {
    return lineageById.get(id)?.lineage_name ?? id;
  }

  function clickLeadingEdge(memberId: string) {
    const r = byId.get(memberId);
    if (!r) return;
    const params = new URLSearchParams();
    params.set('q', r.name);
    goto(`${base}/?${params.toString()}`);
  }

  function lineageDrillUrl(lineageId: string): string {
    // Deep-link convention: ?lineage=<id>. The /lineages view doesn't
    // consume the param yet (owned by an earlier issue, read-only here)
    // but the link is forward-compatible — when that page learns to
    // highlight by id, every card on this page gets a free upgrade.
    // We use a query param rather than a hash fragment so SvelteKit's
    // prerender link check doesn't complain about missing element ids.
    const params = new URLSearchParams({ lineage: lineageId });
    return `${base}/lineages?${params.toString()}`;
  }

  function scrollToLineage(lineageId: string) {
    // Within-page hop: clicking an "adjacent lineage" chip scrolls the
    // adjacent card into view instead of leaving the page.
    if (typeof document === 'undefined') return;
    const el = document.getElementById(`lineage-card-${lineageId}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // Brief highlight pulse via class toggle so the user sees where
      // they landed.
      el.classList.add('flash');
      setTimeout(() => el.classList.remove('flash'), 1200);
    }
  }

  function fmtCadence(f: LineageForecast): string {
    if (!isFinite(f.cadence_quarters)) {
      return f.members_dated < 2
        ? 'too few dated members for a cadence'
        : 'cadence not computable';
    }
    return `~${cadenceMonths(f.cadence_quarters)} between members`;
  }

  function fmtInterval(f: LineageForecast): string {
    // "Q3 2026 ± 2 quarters" or just "Q3 2026" if no stddev.
    if (!f.next_expected) return '';
    if (!isFinite(f.cadence_stddev_quarters) || f.cadence_stddev_quarters <= 0) {
      return f.next_expected;
    }
    const spread = Math.max(1, Math.round(f.cadence_stddev_quarters));
    return `${f.next_expected} ± ${spread} quarter${spread === 1 ? '' : 's'}`;
  }
</script>

<svelte:head>
  <title>Lineage forecast · Memory Landscape</title>
</svelte:head>

<header class="hdr">
  <p class="crumbs">
    <a href="{base}/analyses">← Analyses</a>
  </p>
  <h1>Lineage forecast</h1>
  <p class="subtitle">
    For each of the {stats.total} detected lineage{stats.total === 1 ? '' : 's'},
    project where the next entry is likely to land based on the cadence of
    past releases. <strong>Exploratory</strong> — watch list, not prediction.
  </p>

  <div class="calibration" role="note" aria-label="forecast calibration">
    <strong>Read this first.</strong> Most lineages on this page have only
    3–5 dated members. A cadence computed from 2 or 3 inter-arrival gaps
    is informative <em>directionally</em> (is this family active or
    stalled?) but is not a statistical prediction. The "next expected"
    quarter is a <em>watch trigger</em> — a date to check the source
    feeds — not a forecast to defend. If a family dries up, gets absorbed,
    or accelerates by a single release, the projection moves by a year.
  </div>

  <details class="method">
    <summary>How the cadence is computed</summary>
    <ul>
      <li>
        For each lineage we list its members in descending order by
        <code>created</code> date, parsed to quarter granularity
        (year × 4 + quarter).
      </li>
      <li>
        The <strong>cadence</strong> is the mean of the inter-arrival
        gaps in quarters, with a floor of 0.5 quarters per gap so that
        same-quarter clusters don't crash the average to zero.
      </li>
      <li>
        The <strong>prediction interval</strong> is the population
        standard deviation of those gaps. We surface it as
        "Q3 2026 ± 2 quarters" — read this as "if the cadence holds,
        the next entry will probably land within this window."
      </li>
      <li>
        <strong>Discount the projection</strong> when (a) the lineage
        has fewer than 5 members (small-sample badge), (b) the cadence
        is built from fewer than 3 gaps (insufficient-data badge —
        we hide the date entirely), or (c) the gap spread is large
        relative to the mean.
      </li>
    </ul>
  </details>

  <div class="so-what">
    <strong>So what?</strong>
    A short-cadence lineage means the architectural idea is still
    earning new contributions — reading the next 2–3 arXiv updates in
    that lineage is high-leverage. A long-cadence lineage means the idea
    is either mature (settled, low marginal returns) or stalled
    (researchers moved on). Adjacent lineages are where
    <em>cross-pollination</em> shows up first: work in one family
    routinely informs predictions for its neighbours.
  </div>

  <p class="stats-line">
    {stats.shown} of {stats.total} lineage{stats.total === 1 ? '' : 's'} shown ·
    {stats.smallSample} small-sample (N&lt;5) ·
    {stats.noCadence} insufficient data (cadence intervals &lt;3)
  </p>
</header>

<section class="filters" aria-label="filters">
  <div class="fgroup">
    <span class="flabel">Kind</span>
    <div class="fopts" role="radiogroup" aria-label="lineage kind">
      <label class:active={kindFilter === 'all'}>
        <input type="radio" bind:group={kindFilter} value="all" /> all
      </label>
      <label class:active={kindFilter === 'descent'}>
        <input type="radio" bind:group={kindFilter} value="descent" /> descent
      </label>
      <label class:active={kindFilter === 'pattern'}>
        <input type="radio" bind:group={kindFilter} value="pattern" /> pattern
      </label>
    </div>
  </div>
  <div class="fgroup">
    <span class="flabel">Provenance</span>
    <div class="fopts" role="radiogroup" aria-label="lineage provenance">
      <label class:active={curatedFilter === 'all'}>
        <input type="radio" bind:group={curatedFilter} value="all" /> all
      </label>
      <label class:active={curatedFilter === 'curated'}>
        <input type="radio" bind:group={curatedFilter} value="curated" /> curated
      </label>
      <label class:active={curatedFilter === 'auto'}>
        <input type="radio" bind:group={curatedFilter} value="auto" /> auto
      </label>
    </div>
  </div>
  <div class="fgroup">
    <span class="flabel">Min members</span>
    <div class="fopts slider-row">
      <input
        type="range"
        min="3"
        max="10"
        step="1"
        bind:value={minN}
        aria-label="minimum lineage size"
      />
      <span class="slider-val">N ≥ {minN}</span>
    </div>
  </div>
</section>

<ul class="cards">
  {#each sorted as f}
    {@const isFastest = stats.fastest?.lineage_id === f.lineage_id}
    <li
      id={`lineage-card-${f.lineage_id}`}
      class="card"
      class:fastest={isFastest}
      class:low-n={f.insufficient_data}
    >
      <div class="card-head">
        <h2>
          <a class="lineage-link" href={lineageDrillUrl(f.lineage_id)}>
            {f.lineage_name}
          </a>
          {#if isFastest && !f.insufficient_data}
            <span class="badge fastest-badge" title="lowest cadence in the set">fastest</span>
          {/if}
          {#if f.curated}
            <span class="badge curated">curated</span>
          {/if}
          {#if f.kind === 'pattern'}
            <span class="badge pattern">pattern</span>
          {/if}
          {#if f.insufficient_data}
            <span class="badge warn-strong" title="fewer than 3 cadence intervals">
              no cadence forecast
            </span>
          {:else if f.low_n}
            <span class="badge warn" title="fewer than 5 members — interpret with care">
              small sample
            </span>
          {/if}
        </h2>
        <p class="meta">
          {f.members_total} member{f.members_total === 1 ? '' : 's'}
          ({f.members_dated} dated, {f.cadence_intervals} interval{f.cadence_intervals === 1 ? '' : 's'})
          {#if f.earliest && f.latest}
            · earliest {f.earliest} → latest {f.latest}
          {/if}
        </p>
      </div>

      {#if f.insufficient_data}
        <div class="cadence insufficient">
          <strong>INSUFFICIENT DATA</strong> — fewer than 3 inter-arrival gaps.
          Watch the leading edge below instead of trusting a projected date.
        </div>
      {:else}
        <div class="cadence">
          <span class="label">Cadence:</span>
          <span class="value">{fmtCadence(f)}</span>
          {#if f.next_expected}
            <div class="next-line" class:dim={f.low_n}>
              <em>if the cadence holds</em>, next expected ≈
              <strong>{fmtInterval(f)}</strong>
              {#if f.low_n}
                <span class="dim-note">(small sample — directional only)</span>
              {/if}
            </div>
          {/if}
        </div>
      {/if}

      <div class="section">
        <h3>Leading edge <span class="hint">(3 most-recent dated members)</span></h3>
        {#if f.leading_edge.length === 0}
          <p class="empty">No dated members on the leading edge.</p>
        {:else}
          <ul class="leading">
            {#each f.leading_edge as id, i}
              <li>
                <button
                  type="button"
                  class="le-btn"
                  onclick={() => clickLeadingEdge(id)}
                  title="Filter the table by this system"
                >
                  {f.leading_edge_names[i] ?? id}
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>

      <div class="section">
        <h3>Themes the leading edge is exploring</h3>
        {#if f.themes.length === 0}
          <p class="empty">No salient themes extracted (sparse claims).</p>
        {:else}
          <ul class="themes">
            {#each f.themes as t}
              <li class="theme">{t}</li>
            {/each}
          </ul>
        {/if}
      </div>

      {#if f.adjacent.length > 0}
        <div class="section">
          <h3>
            Adjacent lineages
            <span class="hint">(cross-pollination candidates)</span>
          </h3>
          <ul class="adjacent">
            {#each f.adjacent as a}
              <li>
                <button
                  type="button"
                  class="adj-btn"
                  onclick={() => scrollToLineage(a)}
                  title="Jump to this lineage's card"
                >
                  {adjacentName(a)}
                </button>
              </li>
            {/each}
          </ul>
        </div>
      {/if}

      {#if f.watch_note}
        <div class="section watch-note">
          <h3>
            What to watch for
            <span class="hint">(editorial)</span>
          </h3>
          <p>{f.watch_note}</p>
        </div>
      {/if}

      {#if f.watch_links.length > 0}
        <div class="section watch">
          <h3>Subscribe / monitor</h3>
          <ul class="watch-links">
            {#each f.watch_links as w}
              <li>
                <a href={w.url} target="_blank" rel="noopener noreferrer">
                  {w.label} ↗
                </a>
              </li>
            {/each}
          </ul>
        </div>
      {/if}

      <p class="speculation">
        {#if f.insufficient_data}
          Too few intervals for a projection — leading edge is the signal.
        {:else}
          Based on {f.cadence_intervals} inter-arrival gap{f.cadence_intervals === 1 ? '' : 's'}.
          Watch list, not prediction.
        {/if}
      </p>
    </li>
  {/each}
  {#if sorted.length === 0}
    <li class="card empty-card">
      No lineages match the current filters. Lower the "min members" slider
      or reset the kind / provenance filters.
    </li>
  {/if}
</ul>

<style>
  .hdr {
    max-width: 880px;
    margin: 16px 0 20px;
    color: #c9d1d9;
  }
  .crumbs {
    margin: 0 0 8px;
    font-size: 0.85rem;
  }
  .crumbs a {
    color: #58a6ff;
    text-decoration: none;
  }
  .crumbs a:hover { text-decoration: underline; }
  h1 {
    margin: 0 0 8px;
    font-size: 1.5rem;
    letter-spacing: -0.01em;
    color: #f0f6fc;
  }
  .subtitle {
    margin: 0 0 14px;
    color: #8b949e;
    line-height: 1.5;
  }
  .subtitle strong { color: #f0b441; }
  .calibration {
    background: #1a1410;
    border: 1px dashed #5c4530;
    border-left-width: 4px;
    border-left-style: solid;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.85rem;
    color: #d2b48c;
    line-height: 1.5;
    margin-bottom: 12px;
  }
  .calibration strong { color: #f0b441; }
  .calibration em { color: #e6c685; font-style: italic; }

  .method {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.85rem;
    color: #c9d1d9;
    margin-bottom: 12px;
  }
  .method summary {
    cursor: pointer;
    font-weight: 600;
    color: #f0f6fc;
    padding: 6px 0;
    user-select: none;
  }
  .method summary:hover { color: #58a6ff; }
  .method ul {
    margin: 0 0 8px;
    padding-left: 20px;
    color: #c9d1d9;
    line-height: 1.55;
  }
  .method li { margin-bottom: 4px; }
  .method code {
    background: #21262d;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 0.82rem;
  }
  .method strong { color: #f0f6fc; }

  .so-what {
    background: #0e1a14;
    border: 1px solid #1d3a2b;
    border-left: 4px solid #2da44e;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.85rem;
    color: #c9d1d9;
    line-height: 1.55;
    margin-bottom: 12px;
  }
  .so-what strong { color: #56d364; }
  .so-what em { color: #79c0ff; font-style: italic; }

  .stats-line {
    margin: 0;
    color: #6e7681;
    font-size: 0.78rem;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }

  /* --- Filters ---------------------------------------------------------- */
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 14px 22px;
    padding: 12px 14px;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    margin: 0 0 18px;
    max-width: 880px;
  }
  .fgroup {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .flabel {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #8b949e;
    font-weight: 600;
  }
  .fopts {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .fopts label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.82rem;
    color: #c9d1d9;
    padding: 3px 8px;
    border: 1px solid #30363d;
    border-radius: 4px;
    cursor: pointer;
    background: #0d1117;
  }
  .fopts label:hover { border-color: #58a6ff; }
  .fopts label.active {
    background: rgba(88, 166, 255, 0.1);
    border-color: #58a6ff;
    color: #79b8ff;
  }
  .fopts input { display: none; }
  .slider-row {
    gap: 10px;
  }
  .slider-row input[type='range'] {
    width: 140px;
  }
  .slider-val {
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-size: 0.8rem;
    color: #79b8ff;
    min-width: 44px;
  }

  /* --- Cards ----------------------------------------------------------- */
  .cards {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 18px;
    max-width: 1200px;
  }
  .card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    scroll-margin-top: 16px;
    transition: box-shadow 0.6s ease, border-color 0.6s ease;
  }
  .card.fastest {
    border-color: #d4845f;
    box-shadow: 0 0 0 1px rgba(212, 132, 95, 0.15);
  }
  .card.low-n {
    opacity: 0.92;
    border-style: dashed;
  }
  /* `.flash` is toggled imperatively via classList.add(), so Svelte's
   *  static analyser can't see it. Mark as :global to keep the rule
   *  from being pruned and to silence the unused-selector warning. */
  :global(.card.flash) {
    border-color: #58a6ff;
    box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.3);
  }
  .empty-card {
    text-align: center;
    color: #8b949e;
    font-style: italic;
    grid-column: 1 / -1;
    padding: 28px;
  }

  .card-head h2 {
    margin: 0 0 4px;
    font-size: 1rem;
    color: #f0f6fc;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }
  .lineage-link {
    color: #f0f6fc;
    text-decoration: none;
    border-bottom: 1px dotted #30363d;
  }
  .lineage-link:hover {
    color: #58a6ff;
    border-bottom-color: #58a6ff;
  }
  .badge {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
    border: 1px solid;
  }
  .badge.fastest-badge {
    background: rgba(212, 132, 95, 0.12);
    border-color: #d4845f;
    color: #d4845f;
  }
  .badge.curated {
    background: rgba(240, 180, 65, 0.1);
    border-color: #b08433;
    color: #f0b441;
  }
  .badge.pattern {
    background: rgba(181, 148, 98, 0.12);
    border-color: #7a6a4c;
    color: #b59462;
  }
  .badge.warn {
    background: rgba(240, 180, 65, 0.12);
    border-color: #b08433;
    color: #f0b441;
  }
  .badge.warn-strong {
    background: rgba(220, 80, 60, 0.12);
    border-color: #b24a3c;
    color: #ff7b72;
  }
  .meta {
    margin: 0;
    color: #6e7681;
    font-size: 0.78rem;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }

  .cadence {
    font-size: 0.88rem;
    color: #c9d1d9;
    padding: 8px 10px;
    background: #0d1117;
    border-radius: 4px;
    line-height: 1.5;
  }
  .cadence .label { color: #8b949e; font-weight: 500; }
  .cadence .value { color: #f0f6fc; }
  .cadence .next-line {
    margin-top: 4px;
    color: #c9d1d9;
  }
  .cadence .next-line em { color: #b59462; font-style: italic; }
  .cadence strong { color: #f0b441; font-family: ui-monospace, SFMono-Regular, monospace; }
  .cadence .next-line.dim {
    opacity: 0.55;
  }
  .cadence .next-line.dim strong {
    color: #b59462;
    text-decoration: line-through wavy rgba(176, 132, 51, 0.25);
    text-decoration-thickness: 1px;
  }
  .cadence .dim-note {
    font-size: 0.75rem;
    color: #8b949e;
    font-style: italic;
    margin-left: 4px;
  }
  .cadence.insufficient {
    background: #1a1410;
    border: 1px dashed #5c4530;
    color: #d2b48c;
    font-size: 0.83rem;
  }
  .cadence.insufficient strong {
    color: #ff7b72;
    font-family: inherit;
  }

  .section h3 {
    margin: 0 0 6px;
    font-size: 0.78rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
  }
  .section h3 .hint {
    color: #6e7681;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    font-size: 0.72rem;
    font-style: italic;
    margin-left: 6px;
  }
  .leading {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .le-btn {
    all: unset;
    cursor: pointer;
    color: #58a6ff;
    font-size: 0.88rem;
    padding: 2px 0;
    text-align: left;
  }
  .le-btn:hover { text-decoration: underline; }
  .le-btn:focus { outline: 1px solid #58a6ff; outline-offset: 2px; }

  .themes {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
  .theme {
    background: #21262d;
    border: 1px solid #30363d;
    color: #c9d1d9;
    font-size: 0.75rem;
    padding: 2px 7px;
    border-radius: 10px;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }

  .adjacent {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
  .adj-btn {
    all: unset;
    cursor: pointer;
    background: rgba(88, 166, 255, 0.08);
    border: 1px solid rgba(88, 166, 255, 0.25);
    color: #79b8ff;
    font-size: 0.75rem;
    padding: 2px 7px;
    border-radius: 3px;
  }
  .adj-btn:hover {
    background: rgba(88, 166, 255, 0.16);
    border-color: #58a6ff;
  }
  .adj-btn:focus { outline: 1px solid #58a6ff; outline-offset: 2px; }

  .watch-note p {
    margin: 0;
    color: #c9d1d9;
    font-size: 0.84rem;
    line-height: 1.5;
    background: rgba(240, 180, 65, 0.05);
    border-left: 3px solid #b08433;
    padding: 6px 10px;
    border-radius: 0 4px 4px 0;
  }

  .watch-links {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 0.82rem;
  }
  .watch-links a {
    color: #58a6ff;
    text-decoration: none;
  }
  .watch-links a:hover { text-decoration: underline; }

  .empty {
    margin: 0;
    color: #6e7681;
    font-style: italic;
    font-size: 0.82rem;
  }

  .speculation {
    margin: 0;
    color: #6e7681;
    font-size: 0.72rem;
    font-style: italic;
    border-top: 1px dashed #21262d;
    padding-top: 8px;
  }
</style>
