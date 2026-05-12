<script lang="ts">
  // Vocabulary-drift view (issue #26). One line per tracked term across
  // year-quarter buckets; users toggle which lines render via the term
  // selector at the top. Pure SVG line chart — same rationale as the
  // /timeline page: ~27 terms × ~25 quarters = ~675 points, well under
  // anything that needs canvas.
  //
  // The helper module $lib/analyses/vocabulary.ts owns all the pure
  // logic (term regexes, bucketing, growth math). This component is
  // strictly presentational: derived state + SVG.

  import { base } from '$app/paths';
  import type { LandscapeRecord } from '$lib/types';
  import {
    TRACKED_TERMS,
    TERM_GROUPS,
    countByQuarter,
    allQuarters,
    fillMissing,
    termGrowth,
    topSystemsForTerm,
    termColor
  } from '$lib/analyses/vocabulary';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  // --- Selected terms ---------------------------------------------------
  //
  // Start with the six "headline" terms from the issue summary so the
  // chart shows something meaningful on first paint. Users toggle via
  // checkboxes; we keep one Set state for O(1) lookup during render.
  const DEFAULT_SELECTED = new Set<string>([
    'episodic',
    'working',
    'parametric',
    'agentic',
    'lifelong',
    'RAG'
  ]);
  let selected = $state(new Set(DEFAULT_SELECTED));

  function toggleTerm(t: string) {
    const next = new Set(selected);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    selected = next;
  }
  function selectAll() {
    selected = new Set(TRACKED_TERMS);
  }
  function selectNone() {
    selected = new Set();
  }
  function selectDefault() {
    selected = new Set(DEFAULT_SELECTED);
  }

  // --- Bucket computation -----------------------------------------------
  //
  // We compute the full bucket set once over ALL terms (not just the
  // selected ones) so toggling a checkbox is instantaneous and the per-
  // term summary cards below the chart can show growth even for hidden
  // terms. Cost: ~523 records × 27 terms × 2 cells = ~28k regex tests
  // per recompute. Empirically <10ms; fine for build-time + on-mount.
  const rawBuckets = $derived(countByQuarter(data.records, TRACKED_TERMS));
  const quarters = $derived(allQuarters(rawBuckets));
  const fullBuckets = $derived(
    fillMissing(rawBuckets, TRACKED_TERMS, quarters)
  );

  /** quarter -> term -> count, for fast SVG path generation. */
  const matrix = $derived.by(() => {
    const m = new Map<string, Map<string, number>>();
    for (const q of quarters) m.set(q, new Map());
    for (const b of fullBuckets) {
      if (b.quarter === 'unparseable') continue;
      m.get(b.quarter)?.set(b.term, b.count);
    }
    return m;
  });

  const selectedTerms = $derived(
    TRACKED_TERMS.filter((t) => selected.has(t))
  );

  // Y-axis upper bound across selected terms only (rescales as user
  // toggles to keep the chart legible at any subset).
  const maxCount = $derived.by(() => {
    let m = 0;
    for (const q of quarters) {
      const row = matrix.get(q);
      if (!row) continue;
      for (const t of selectedTerms) {
        const v = row.get(t) ?? 0;
        if (v > m) m = v;
      }
    }
    return m;
  });

  // --- SVG geometry -----------------------------------------------------
  //
  // 36px per quarter so labels stay legible. Match the /timeline page's
  // padding so the two pages feel like one family.
  const COL_W = 36;
  const CHART_H = 360;
  const PAD_LEFT = 56;
  const PAD_RIGHT = 24;
  const PAD_TOP = 16;
  const PAD_BOTTOM = 56;

  const innerW = $derived(Math.max(1, (quarters.length - 1) * COL_W));
  const totalW = $derived(PAD_LEFT + innerW + PAD_RIGHT + COL_W);
  const innerH = CHART_H - PAD_TOP - PAD_BOTTOM;

  function xAt(i: number): number {
    return PAD_LEFT + i * COL_W;
  }
  function yAt(v: number): number {
    if (maxCount === 0) return PAD_TOP + innerH;
    return PAD_TOP + innerH - (v / maxCount) * innerH;
  }

  /** SVG `d` attribute for one term's polyline. */
  function pathFor(term: string): string {
    const parts: string[] = [];
    for (let i = 0; i < quarters.length; i++) {
      const v = matrix.get(quarters[i])?.get(term) ?? 0;
      parts.push(`${i === 0 ? 'M' : 'L'}${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)}`);
    }
    return parts.join(' ');
  }

  // Y-axis ticks: 4-5 evenly spaced.
  const yStep = $derived(Math.max(1, Math.ceil(maxCount / 4)));
  const yTicks = $derived.by(() => {
    const t: number[] = [];
    for (let v = 0; v <= maxCount; v += yStep) t.push(v);
    if (maxCount > 0 && t[t.length - 1] !== maxCount) t.push(maxCount);
    return t;
  });

  // X-axis label cadence: never more than ~15 labels.
  const labelStride = $derived(Math.max(1, Math.ceil(quarters.length / 16)));

  // --- Hover state ------------------------------------------------------
  let hoverIdx = $state<number | null>(null);
  function onColEnter(i: number) {
    hoverIdx = i;
  }
  function onColLeave() {
    hoverIdx = null;
  }

  // --- Per-term summary cards -------------------------------------------
  //
  // Computed once per render: each selected term gets a card with
  // first-appearance year, latest active quarter, YoY growth, and the
  // top 3 mentioning systems by tier.
  const summaries = $derived.by(() => {
    return selectedTerms.map((term) => {
      const g = termGrowth(fullBuckets, term);
      const top = topSystemsForTerm(data.records, term, 3);
      return { term, ...g, top };
    });
  });

  function formatGrowth(g: number): string {
    if (!isFinite(g)) return 'new';
    return `${(g * 100).toFixed(0)}%`;
  }
</script>

<svelte:head>
  <title>Vocabulary drift · Memory Landscape analyses</title>
</svelte:head>

<div class="wrap">
  <header>
    <h1>Vocabulary drift</h1>
    <p class="subtitle">
      {TRACKED_TERMS.length} curated memory terms tracked across
      {quarters.length} quarters · each line = number of records mentioning
      the term in <code>desc</code> + <code>claims</code>, bucketed by
      <code>created</code> quarter.
      <a class="back" href="{base}/analyses">← back to analyses hub</a>
    </p>
  </header>

  <section class="controls" aria-label="Term selector">
    <div class="control-row">
      <button class="btn" type="button" onclick={selectDefault}>Headline 6</button>
      <button class="btn" type="button" onclick={selectAll}>All {TRACKED_TERMS.length}</button>
      <button class="btn" type="button" onclick={selectNone}>None</button>
      <span class="count">{selected.size} selected</span>
    </div>
    {#each TERM_GROUPS as group}
      <fieldset class="group">
        <legend>{group.label}</legend>
        {#each group.terms as term}
          {@const on = selected.has(term)}
          <label class="chip" class:on>
            <input
              type="checkbox"
              checked={on}
              onchange={() => toggleTerm(term)}
            />
            <span class="swatch" style="background:{termColor(term)}"></span>
            {term}
          </label>
        {/each}
      </fieldset>
    {/each}
  </section>

  <div class="chart-scroll">
    {#if quarters.length === 0}
      <p class="empty">No parseable created-date data in the catalog.</p>
    {:else if selectedTerms.length === 0}
      <p class="empty">No terms selected — pick at least one above.</p>
    {:else}
      <svg
        viewBox="0 0 {totalW} {CHART_H}"
        width={totalW}
        height={CHART_H}
        role="img"
        aria-label="Vocabulary drift line chart, {selectedTerms.length} terms across {quarters.length} quarters"
      >
        <!-- Gridlines + Y-axis ticks -->
        {#each yTicks as t}
          <line
            x1={PAD_LEFT}
            x2={PAD_LEFT + innerW + COL_W / 2}
            y1={yAt(t)}
            y2={yAt(t)}
            stroke="#21262d"
            stroke-width="1"
          />
          <text
            x={PAD_LEFT - 8}
            y={yAt(t) + 4}
            text-anchor="end"
            class="tick-label"
          >{t}</text>
        {/each}

        <!-- Y-axis label -->
        <text
          transform="rotate(-90 14 {PAD_TOP + innerH / 2})"
          x="14"
          y={PAD_TOP + innerH / 2}
          text-anchor="middle"
          class="axis-label"
        >records mentioning term</text>

        <!-- Per-quarter hover columns. Transparent rect spans the column
             so hover works anywhere along the X. -->
        {#each quarters as q, i}
          <rect
            x={xAt(i) - COL_W / 2}
            y={PAD_TOP}
            width={COL_W}
            height={innerH}
            fill="transparent"
            class="col-hit"
            onpointerenter={() => onColEnter(i)}
            onpointerleave={onColLeave}
            role="presentation"
          />
          <!-- X-axis ticks + selective labels -->
          <line
            x1={xAt(i)}
            x2={xAt(i)}
            y1={PAD_TOP + innerH}
            y2={PAD_TOP + innerH + (i % labelStride === 0 ? 6 : 3)}
            stroke="#30363d"
            stroke-width="1"
          />
          {#if i % labelStride === 0}
            <text
              x={xAt(i)}
              y={PAD_TOP + innerH + 20}
              text-anchor="middle"
              class="tick-label"
            >{q}</text>
          {/if}
        {/each}

        <!-- Vertical guide on hover -->
        {#if hoverIdx !== null}
          <line
            x1={xAt(hoverIdx)}
            x2={xAt(hoverIdx)}
            y1={PAD_TOP}
            y2={PAD_TOP + innerH}
            stroke="#30363d"
            stroke-dasharray="3 3"
            stroke-width="1"
            pointer-events="none"
          />
        {/if}

        <!-- One polyline per selected term -->
        {#each selectedTerms as term}
          <path
            d={pathFor(term)}
            fill="none"
            stroke={termColor(term)}
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
            opacity={hoverIdx === null ? 0.9 : 0.55}
            pointer-events="none"
          />
          <!-- Dots at the hovered column for legibility -->
          {#if hoverIdx !== null}
            {@const v = matrix.get(quarters[hoverIdx])?.get(term) ?? 0}
            <circle
              cx={xAt(hoverIdx)}
              cy={yAt(v)}
              r="3"
              fill={termColor(term)}
              pointer-events="none"
            />
          {/if}
        {/each}

        <!-- X-axis baseline -->
        <line
          x1={PAD_LEFT}
          x2={PAD_LEFT + innerW + COL_W / 2}
          y1={PAD_TOP + innerH}
          y2={PAD_TOP + innerH}
          stroke="#30363d"
          stroke-width="1"
        />
      </svg>
    {/if}
  </div>

  {#if hoverIdx !== null && quarters.length > 0}
    <p class="hover-readout">
      <strong>{quarters[hoverIdx]}:</strong>
      {#each selectedTerms as term, i}
        {@const v = matrix.get(quarters[hoverIdx])?.get(term) ?? 0}
        {#if v > 0}
          <span class="readout-item">
            <span class="swatch" style="background:{termColor(term)}"></span>
            {term} = {v}
          </span>{#if i < selectedTerms.length - 1}{' '}{/if}
        {/if}
      {/each}
    </p>
  {/if}

  <section class="cards" aria-label="Per-term summary">
    {#each summaries as s}
      <article class="card" style="--accent:{termColor(s.term)}">
        <header>
          <span class="swatch" style="background:{termColor(s.term)}"></span>
          <h2>{s.term}</h2>
        </header>
        <dl>
          <dt>First seen</dt>
          <dd>{s.firstYear === -1 ? '—' : s.firstYear}</dd>
          <dt>Latest active</dt>
          <dd>{s.latestQuarter || '—'}</dd>
          <dt>YoY growth</dt>
          <dd class:positive={isFinite(s.growth_yoy) && s.growth_yoy > 0}
              class:negative={isFinite(s.growth_yoy) && s.growth_yoy < 0}
              class:emerge={!isFinite(s.growth_yoy)}>
            {formatGrowth(s.growth_yoy)}
          </dd>
          <dt>Total records</dt>
          <dd>{s.total}</dd>
        </dl>
        {#if s.top.length > 0}
          <p class="top">
            <span class="top-label">Top mentions:</span>
            {#each s.top as r, i}
              <a href="{base}/?id={r.id}">{r.name}</a>{#if i < s.top.length - 1}, {/if}
            {/each}
          </p>
        {/if}
      </article>
    {/each}
  </section>
</div>

<style>
  .wrap {
    max-width: 1200px;
    padding: 24px;
  }
  header h1 {
    margin: 0 0 8px;
    font-size: 1.6rem;
    color: #e8e8e8;
    letter-spacing: -0.01em;
  }
  .subtitle {
    margin: 0 0 24px;
    color: #aaa;
    font-size: 0.9rem;
    line-height: 1.5;
  }
  .subtitle code {
    background: #1a1a1a;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.85em;
  }
  .back {
    color: #d4845f;
    margin-left: 12px;
    text-decoration: none;
  }
  .back:hover {
    text-decoration: underline;
  }

  .controls {
    background: #131313;
    border: 1px solid #262626;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 18px;
  }
  .control-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }
  .btn {
    background: #1f1f1f;
    border: 1px solid #2f2f2f;
    color: #ddd;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 0.82rem;
    cursor: pointer;
  }
  .btn:hover {
    background: #2a2a2a;
    border-color: #444;
  }
  .count {
    color: #888;
    font-size: 0.82rem;
    margin-left: 4px;
  }
  .group {
    border: none;
    padding: 0;
    margin: 0 0 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  .group legend {
    color: #888;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-right: 8px;
    padding: 0;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #181818;
    border: 1px solid #262626;
    color: #999;
    padding: 3px 8px;
    border-radius: 14px;
    font-size: 0.82rem;
    cursor: pointer;
    user-select: none;
  }
  .chip:hover {
    border-color: #3a3a3a;
    color: #ddd;
  }
  .chip.on {
    background: #1d1d1d;
    border-color: #444;
    color: #e8e8e8;
  }
  .chip input {
    display: none;
  }
  .swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    display: inline-block;
  }

  .chart-scroll {
    overflow-x: auto;
    background: #0f0f0f;
    border: 1px solid #1f1f1f;
    border-radius: 8px;
    padding: 8px 0;
  }
  .empty {
    color: #888;
    text-align: center;
    padding: 60px 20px;
    margin: 0;
    font-size: 0.9rem;
  }
  .tick-label {
    fill: #888;
    font-size: 11px;
    font-family: ui-sans-serif, system-ui, sans-serif;
  }
  .axis-label {
    fill: #aaa;
    font-size: 11px;
    font-family: ui-sans-serif, system-ui, sans-serif;
  }
  .col-hit {
    cursor: crosshair;
  }

  .hover-readout {
    margin: 10px 0 0;
    font-size: 0.85rem;
    color: #ddd;
    line-height: 1.7;
  }
  .hover-readout strong {
    color: #e8e8e8;
    margin-right: 8px;
  }
  .readout-item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #181818;
    border: 1px solid #262626;
    padding: 2px 8px;
    border-radius: 12px;
    margin-right: 4px;
  }

  .cards {
    margin-top: 28px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }
  .card {
    background: #131313;
    border: 1px solid #262626;
    border-left: 3px solid var(--accent, #888);
    border-radius: 6px;
    padding: 12px 14px;
  }
  .card header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  .card header h2 {
    margin: 0;
    font-size: 0.98rem;
    color: #e8e8e8;
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-weight: 600;
  }
  .card dl {
    margin: 0;
    display: grid;
    grid-template-columns: max-content 1fr;
    column-gap: 10px;
    row-gap: 3px;
    font-size: 0.82rem;
  }
  .card dt {
    color: #888;
  }
  .card dd {
    margin: 0;
    color: #ddd;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .card dd.positive {
    color: #3fb950;
  }
  .card dd.negative {
    color: #d4655f;
  }
  .card dd.emerge {
    color: #d4845f;
  }
  .top {
    margin: 10px 0 0;
    padding-top: 8px;
    border-top: 1px solid #1f1f1f;
    font-size: 0.78rem;
    color: #999;
    line-height: 1.5;
  }
  .top-label {
    color: #666;
    margin-right: 4px;
  }
  .top a {
    color: #d4845f;
    text-decoration: none;
  }
  .top a:hover {
    text-decoration: underline;
  }
</style>
