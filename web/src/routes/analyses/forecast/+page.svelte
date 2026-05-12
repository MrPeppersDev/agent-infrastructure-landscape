<script lang="ts">
  // Lineage forward-projection (issue #27). For each detected lineage we
  // project where the next paper/product is likely to land — strictly a
  // "watch list, not a prediction" framing. The maths is openly naïve
  // (mean inter-arrival gap), shown with the calibration disclaimer
  // baked into the page copy.
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

  // Display order: by fastest cadence ascending (most active families
  // first), with NaN-cadence lineages sinking to the end. Within the
  // dated bucket curated lineages still appear in their declared order
  // implicitly because detectLineages emits them first.
  const sorted = $derived<LineageForecast[]>(
    [...forecasts].sort((a, b) => {
      const aOk = isFinite(a.cadence_quarters);
      const bOk = isFinite(b.cadence_quarters);
      if (aOk && !bOk) return -1;
      if (!aOk && bOk) return 1;
      if (!aOk && !bOk) return a.lineage_name.localeCompare(b.lineage_name);
      return a.cadence_quarters - b.cadence_quarters;
    })
  );

  // Stats for the header / commit message.
  const stats = $derived.by(() => {
    let fastest: LineageForecast | null = null;
    for (const f of forecasts) {
      if (!isFinite(f.cadence_quarters)) continue;
      if (!fastest || f.cadence_quarters < fastest.cadence_quarters) {
        fastest = f;
      }
    }
    return {
      count: forecasts.length,
      fastest,
      drops: forecasts
        .filter((f) => f.next_expected)
        .map((f) => `${f.lineage_name} (${f.next_expected})`)
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

  function fmtCadence(f: LineageForecast): string {
    if (!isFinite(f.cadence_quarters)) {
      return f.members_total < 2
        ? 'too few dated members for a cadence'
        : 'cadence not computable';
    }
    return `~${cadenceMonths(f.cadence_quarters)} between members`;
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
    For each of the {stats.count} detected lineage{stats.count === 1 ? '' : 's'},
    project where the next entry is likely to land based on the cadence of
    past releases. Watch list, not prediction.
  </p>
  <div class="calibration" role="note" aria-label="forecast calibration">
    <strong>Calibration:</strong> the projection is a mean-of-inter-arrival
    extrapolation over a handful of dated members. <em>If the cadence holds</em>
    and the family stays active, you can expect the next drop near the
    projected quarter — but a research family can dry up, get absorbed, or
    accelerate in a single quarter. Treat the next-expected dates as
    bookmarks for where to look, not as forecasts to defend.
  </div>
</header>

<ul class="cards">
  {#each sorted as f}
    {@const isFastest = stats.fastest?.lineage_id === f.lineage_id}
    <li class="card" class:fastest={isFastest}>
      <div class="card-head">
        <h2>
          {f.lineage_name}
          {#if isFastest}
            <span class="badge fastest-badge" title="lowest cadence in the set">fastest</span>
          {/if}
          {#if f.curated}
            <span class="badge curated">curated</span>
          {/if}
          {#if f.kind === 'pattern'}
            <span class="badge pattern">pattern</span>
          {/if}
        </h2>
        <p class="meta">
          {f.members_total} member{f.members_total === 1 ? '' : 's'}
          {#if f.earliest && f.latest}
            · earliest {f.earliest} → latest {f.latest}
          {/if}
        </p>
      </div>

      <div class="cadence">
        <span class="label">Cadence:</span>
        <span class="value">{fmtCadence(f)}</span>
        {#if f.next_expected}
          <span class="next">
            ; <em>if the cadence holds</em>, next expected ≈
            <strong>{f.next_expected}</strong>
          </span>
        {/if}
      </div>

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
          <h3>Adjacent lineages <span class="hint">(could cross-pollinate)</span></h3>
          <ul class="adjacent">
            {#each f.adjacent as a}
              <li>{adjacentName(a)}</li>
            {/each}
          </ul>
        </div>
      {/if}

      {#if f.watch_links.length > 0}
        <div class="section watch">
          <h3>Watch this lineage</h3>
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
        Based on the last 3 members. Watch list, not prediction.
      </p>
    </li>
  {/each}
</ul>

<style>
  .hdr {
    max-width: 880px;
    margin: 16px 0 28px;
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
  }
  .calibration strong { color: #f0b441; }
  .calibration em { color: #e6c685; font-style: italic; }

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
  }
  .card.fastest {
    border-color: #d4845f;
    box-shadow: 0 0 0 1px rgba(212, 132, 95, 0.15);
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
  .cadence .next em { color: #b59462; font-style: italic; }
  .cadence strong { color: #f0b441; font-family: ui-monospace, SFMono-Regular, monospace; }

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
  .adjacent li {
    background: rgba(88, 166, 255, 0.08);
    border: 1px solid rgba(88, 166, 255, 0.25);
    color: #79b8ff;
    font-size: 0.75rem;
    padding: 2px 7px;
    border-radius: 3px;
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
