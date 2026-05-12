<script lang="ts">
  // /analyses/archetypes — taxonomy archetypes (issue #25).
  //
  // Clusters all records by their 7-axis primary-only taxonomy fingerprint
  // and surfaces the recurring recipes. The page is intentionally one
  // Svelte file: every section (header summary, top-K archetype cards,
  // long-tail breakdown, white-space panel) is presentational and reads
  // from the same pure helpers in $lib/analyses/archetypes.
  //
  // No charting library — the only graphic is a horizontal usage-bar
  // beside each fingerprint card, drawn with plain CSS.

  import { base } from '$app/paths';
  import type { LandscapeRecord } from '$lib/types';
  import {
    AXES,
    clusterByFingerprint,
    detectGapCandidates,
    parseFingerprint,
    suggestArchetypeName,
    summarise,
    type Archetype
  } from '$lib/analyses/archetypes';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  const TOP_N = 12;

  const archetypes = $derived(clusterByFingerprint(data.records));
  const summary = $derived(summarise(archetypes, TOP_N));
  const topArchetypes = $derived(archetypes.slice(0, TOP_N));
  const recurringCount = $derived(
    archetypes.filter((a) => a.members.length >= 2).length
  );
  const gapCandidates = $derived(
    detectGapCandidates(data.records, archetypes, {
      minAxisFloor: 25,
      limit: 8
    })
  );

  // Tier colour scale: T1 (battle-tested) → T5 (theoretical). Reuses the
  // palette established by /sections so the visual language is consistent.
  const TIER_COLORS: Record<number, string> = {
    1: '#3fb950',
    2: '#58a6ff',
    3: '#d29922',
    4: '#bc8cff',
    5: '#8b949e'
  };

  function pct(n: number, total: number): string {
    if (total === 0) return '0.0%';
    return ((n / total) * 100).toFixed(1) + '%';
  }

  // Stable colour per axis — used for the small badge backgrounds so the
  // 7 axes are visually distinguishable at a glance.
  const AXIS_TINT: Record<string, string> = {
    storage: '#1f3a4d',
    retrieval: '#2a3a5c',
    persistence: '#3a2a5c',
    update: '#4d2a5c',
    unit: '#5c2a48',
    governance: '#5c3a2a',
    conflict: '#3a5c2a'
  };

</script>

<svelte:head>
  <title>Taxonomy archetypes · Memory Landscape</title>
</svelte:head>

<div class="wrap">
  <header class="hdr">
    <div>
      <p class="crumb">
        <a href="{base}/analyses">← Analyses</a>
      </p>
      <h1>Taxonomy archetypes</h1>
      <p class="sub">
        <strong>{summary.distinct}</strong> distinct fingerprints across
        <strong>{summary.total}</strong> systems;
        top <strong>{summary.topN}</strong> cover
        <strong>{(summary.topNCoverage * 100).toFixed(1)}%</strong> of the
        catalog. <strong>{recurringCount}</strong> recurring recipes
        ({summary.singletons} singletons in the long tail).
      </p>
    </div>
    <nav class="nav">
      <a href="{base}/">Table</a>
      <a href="{base}/sections">Sections</a>
    </nav>
  </header>

  <p class="explainer">
    Every record's seven taxonomy axes collapse to a single
    <em>fingerprint</em> — the primary value on each of
    <code>storage · retrieval · persistence · update · unit · governance ·
    conflict</code>. Systems with the same fingerprint share a "recipe".
    Recipes that recur many times are the memory landscape's archetypes;
    fingerprints with only one member are bespoke designs.
  </p>

  <!-- Top-K archetype cards -->
  <section class="grid">
    {#each topArchetypes as a, idx}
      {@const parts = parseFingerprint(a.fingerprint)}
      {@const name = suggestArchetypeName(a.fingerprint)}
      <article class="card">
        <header class="card-hdr">
          <div class="card-title">
            <span class="rank">#{idx + 1}</span>
            <h2>{name}</h2>
          </div>
          <div class="card-counts">
            <span class="count">{a.members.length}</span>
            <span class="pctv">{pct(a.members.length, summary.total)}</span>
          </div>
        </header>

        <!-- Fingerprint badges -->
        <ul class="fp">
          {#each AXES as axis}
            <li
              class="fp-cell"
              style="background:{AXIS_TINT[axis]}"
              title="{axis} = {parts[axis]}"
            >
              <span class="fp-axis">{axis}</span>
              <span class="fp-val">{parts[axis]}</span>
            </li>
          {/each}
        </ul>

        <!-- Tier distribution -->
        <div class="rowblock">
          <span class="block-h">Tier mix</span>
          <div class="tier-strip">
            {#each [1, 2, 3, 4, 5] as t}
              {@const c = a.tiers.get(t) ?? 0}
              {#if c > 0}
                <span
                  class="tier-seg"
                  style="flex:{c}; background:{TIER_COLORS[t]}"
                  title="T{t}: {c}"
                >T{t}·{c}</span>
              {/if}
            {/each}
          </div>
        </div>

        <!-- Section distribution -->
        <div class="rowblock">
          <span class="block-h">Sections</span>
          <ul class="sec-list">
            {#each [...a.sections.entries()].slice(0, 3) as [section, n]}
              <li>
                <span class="sec-name" title={section}>{section}</span>
                <span class="sec-n">{n}</span>
              </li>
            {/each}
            {#if a.sections.size > 3}
              <li class="sec-extra">
                + {a.sections.size - 3} other section{a.sections.size - 3 > 1 ? 's' : ''}
              </li>
            {/if}
          </ul>
        </div>

        <!-- Example members -->
        <div class="rowblock">
          <span class="block-h">Example systems</span>
          <ul class="ex-list">
            {#each a.memberNames.slice(0, 5) as nm}
              <li>
                <a
                  href="{base}/?q={encodeURIComponent(nm)}"
                  title="Open in main table"
                >
                  {nm}
                </a>
              </li>
            {/each}
            {#if a.members.length > 5}
              <li class="ex-extra">
                + {a.members.length - 5} more
              </li>
            {/if}
          </ul>
        </div>
      </article>
    {/each}
  </section>

  <!-- Long-tail summary -->
  <section class="longtail">
    <h2>The long tail</h2>
    <p>
      Beyond the top {TOP_N},
      <strong>{archetypes.length - TOP_N}</strong> further fingerprints
      cover the remaining
      <strong>{((1 - summary.topNCoverage) * 100).toFixed(1)}%</strong>
      of the catalog. Of those, <strong>{summary.singletons}</strong>
      have only one member — each represents a system whose 7-axis
      combination is, in this catalog, unique.
    </p>
    <p class="muted">
      Two systems are in the "same archetype" only when every one of the
      seven primary axis values matches. The bar is therefore high; even
      one-axis disagreements (e.g. <code>graph + traversal</code> vs
      <code>graph + injection</code>) split a recipe into two
      fingerprints. The fingerprint set is downloadable from the
      JSON export shipped with the table view.
    </p>
  </section>

  <!-- White-space gap panel -->
  {#if gapCandidates.length > 0}
    <section class="gaps">
      <h2>White-space candidates</h2>
      <p class="gap-explainer">
        Singletons whose individual axis values are common elsewhere — the
        building blocks exist in the literature, but this specific
        combination has never been built twice. Min-popularity is the
        rarest axis value in the recipe, measured across the whole
        catalog. High min means every part is mainstream; what's missing
        is the assembly.
      </p>
      <table class="gap-table">
        <thead>
          <tr>
            <th>System</th>
            <th>Fingerprint</th>
            <th>Min axis pop.</th>
            <th>Sum axis pop.</th>
          </tr>
        </thead>
        <tbody>
          {#each gapCandidates as g}
            <tr>
              <td>
                <a href="{base}/?q={encodeURIComponent(g.member)}">{g.member}</a>
              </td>
              <td class="gap-fp">{g.fingerprint}</td>
              <td class="num">{g.minAxisPopularity}</td>
              <td class="num">{g.sumAxisPopularity}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}
</div>

<style>
  .wrap {
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding: 4px 0 48px;
    color: #c9d1d9;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    max-width: 1200px;
  }
  .hdr {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 1px solid #21262d;
    padding-bottom: 10px;
    gap: 16px;
    flex-wrap: wrap;
  }
  .crumb {
    margin: 0 0 4px;
    font-size: 0.8rem;
  }
  .crumb a {
    color: #8b949e;
    text-decoration: none;
  }
  .crumb a:hover { color: #58a6ff; }
  h1 {
    margin: 0;
    font-size: 1.45rem;
    letter-spacing: -0.01em;
    color: #f0f6fc;
  }
  .sub {
    margin: 6px 0 0;
    color: #8b949e;
    font-size: 0.88rem;
    max-width: 760px;
    line-height: 1.5;
  }
  .sub strong { color: #f0f6fc; font-weight: 600; }
  .nav { display: flex; gap: 14px; }
  .nav a {
    color: #58a6ff;
    font-size: 0.85rem;
    text-decoration: none;
  }
  .nav a:hover { text-decoration: underline; }

  .explainer {
    margin: 0;
    color: #8b949e;
    font-size: 0.85rem;
    line-height: 1.6;
    max-width: 920px;
  }
  .explainer code {
    background: #161b22;
    padding: 1px 5px;
    border-radius: 3px;
    color: #d29922;
    font-size: 0.8rem;
  }
  .explainer em {
    color: #c9d1d9;
    font-style: normal;
    font-weight: 600;
  }

  /* --- Grid of archetype cards --- */
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 14px;
  }
  .card {
    border: 1px solid #21262d;
    border-radius: 6px;
    background: #0d1117;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 0;
  }
  .card-hdr {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
  }
  .card-title {
    display: flex;
    align-items: baseline;
    gap: 8px;
    min-width: 0;
  }
  .rank {
    color: #6e7681;
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
    flex-shrink: 0;
  }
  .card h2 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: #f0f6fc;
    line-height: 1.25;
    word-wrap: break-word;
  }
  .card-counts {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
  }
  .count {
    font-size: 1.1rem;
    color: #f0f6fc;
    font-weight: 600;
    line-height: 1.1;
  }
  .pctv {
    color: #8b949e;
    font-size: 0.72rem;
  }

  /* --- Fingerprint badge strip --- */
  .fp {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
  }
  .fp-cell {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    padding: 4px 5px;
    border-radius: 3px;
    min-width: 0;
    border: 1px solid rgba(255, 255, 255, 0.04);
  }
  .fp-axis {
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: rgba(255, 255, 255, 0.55);
    line-height: 1.1;
  }
  .fp-val {
    font-size: 0.72rem;
    color: #f0f6fc;
    line-height: 1.2;
    margin-top: 1px;
    word-break: break-word;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  /* --- Block label --- */
  .rowblock {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .block-h {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6e7681;
    font-weight: 600;
  }

  /* --- Tier strip --- */
  .tier-strip {
    display: flex;
    gap: 2px;
    height: 18px;
    border-radius: 3px;
    overflow: hidden;
  }
  .tier-seg {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #0d1117;
    font-size: 0.62rem;
    font-weight: 600;
    min-width: 0;
    padding: 0 4px;
  }

  /* --- Section list --- */
  .sec-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 0.78rem;
  }
  .sec-list li {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    min-width: 0;
  }
  .sec-name {
    color: #c9d1d9;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sec-n {
    color: #8b949e;
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
  }
  .sec-extra {
    color: #6e7681;
    font-style: italic;
    font-size: 0.74rem;
  }

  /* --- Example list --- */
  .ex-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 8px;
    font-size: 0.78rem;
  }
  .ex-list a {
    color: #58a6ff;
    text-decoration: none;
  }
  .ex-list a:hover { text-decoration: underline; }
  .ex-list li:not(:last-child)::after {
    content: '·';
    color: #30363d;
    margin-left: 8px;
  }
  .ex-extra {
    color: #6e7681;
    font-style: italic;
  }

  /* --- Long-tail block --- */
  .longtail {
    border-top: 1px solid #21262d;
    padding-top: 12px;
  }
  .longtail h2 {
    margin: 0 0 8px;
    font-size: 1.05rem;
    color: #f0f6fc;
    font-weight: 600;
  }
  .longtail p {
    margin: 0 0 8px;
    color: #c9d1d9;
    font-size: 0.88rem;
    line-height: 1.55;
    max-width: 860px;
  }
  .longtail .muted {
    color: #8b949e;
    font-size: 0.82rem;
  }
  .longtail code {
    background: #161b22;
    padding: 1px 5px;
    border-radius: 3px;
    color: #d29922;
    font-size: 0.78rem;
  }

  /* --- Gap panel --- */
  .gaps {
    border-top: 1px solid #21262d;
    padding-top: 12px;
  }
  .gaps h2 {
    margin: 0 0 8px;
    font-size: 1.05rem;
    color: #f0f6fc;
    font-weight: 600;
  }
  .gap-explainer {
    margin: 0 0 10px;
    color: #8b949e;
    font-size: 0.82rem;
    line-height: 1.55;
    max-width: 860px;
  }
  .gap-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
  }
  .gap-table th,
  .gap-table td {
    text-align: left;
    padding: 6px 10px;
    border-bottom: 1px solid #21262d;
  }
  .gap-table th {
    color: #6e7681;
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .gap-table .gap-fp {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.75rem;
    color: #8b949e;
  }
  .gap-table .num {
    font-variant-numeric: tabular-nums;
    color: #c9d1d9;
    text-align: right;
  }
  .gap-table td a {
    color: #58a6ff;
    text-decoration: none;
  }
  .gap-table td a:hover { text-decoration: underline; }
</style>
