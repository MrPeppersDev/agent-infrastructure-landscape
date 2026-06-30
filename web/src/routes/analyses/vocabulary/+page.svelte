<script lang="ts">
  import SeoHead from '$lib/components/SeoHead.svelte';

  // Vocabulary-drift view, v2 (issue #26 upgrade pass).
  //
  // v1 was a line chart of per-quarter term mentions with cards showing
  // YoY %. The headlines lied: "+550%" hid that the underlying numbers
  // were 2 -> 13 and "-100%" hid 1 -> 0. v2 inverts the presentation:
  // absolute counts come first, percentages second and only when they
  // pass a small-N sniff test. We also add a cumulative-arrival curve
  // (a term doesn't "decline" if accumulated mentions keep climbing), a
  // co-occurrence heatmap to surface clusters, a first-appearance year
  // chronology, a stable-vs-novel ratio per year, and a drill panel
  // that lists every record mentioning a term sorted by recency.
  //
  // The helper module $lib/analyses/vocabulary.ts owns all the pure
  // logic. This component is strictly presentational: derived state +
  // SVG + a single $state for selection / drill / filters.

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
    termColor,
    cumulativeByQuarter,
    cooccurrence,
    pairCount,
    topTermsByCount,
    firstAppearanceByTerm,
    stableVsNovelByYear,
    mentionsForTerm,
    allSections,
    filterRecords,
    SMALL_N_THRESHOLD,
    COOCCUR_THRESHOLD
  } from '$lib/analyses/vocabulary';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  // --- Tier / section filters ------------------------------------------
  //
  // Filters apply to ALL downstream computations — buckets, cards,
  // matrix, ratios — so toggling, say, "only T1" reshapes every
  // visualisation. We store tiers as a Set<number> for O(1) lookup.
  const ALL_TIERS = [1, 2, 3, 4, 5] as const;
  let selectedTiers = $state<Set<number>>(new Set(ALL_TIERS));
  let selectedSection = $state<string | null>(null);

  function toggleTier(t: number) {
    const next = new Set(selectedTiers);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    selectedTiers = next;
  }
  function resetFilters() {
    selectedTiers = new Set(ALL_TIERS);
    selectedSection = null;
  }

  const sectionOptions = $derived(allSections(data.records));
  const records = $derived(
    filterRecords(data.records, selectedTiers, selectedSection)
  );

  // --- Selected terms ---------------------------------------------------
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
  const rawBuckets = $derived(countByQuarter(records, TRACKED_TERMS));
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

  /** "absolute" mode shows raw per-quarter counts (default).
   *  "cumulative" shows running-total arrival curves — more honest for
   *  established terms whose latest quarter happens to be quiet. */
  let chartMode = $state<'absolute' | 'cumulative'>('absolute');

  /** quarter-index -> term -> running total. Computed once and reused. */
  const cumMatrix = $derived.by(() => {
    const m = new Map<string, number[]>();
    for (const t of TRACKED_TERMS) {
      m.set(t, cumulativeByQuarter(fullBuckets, t, quarters));
    }
    return m;
  });

  // Y-axis upper bound across selected terms in the active mode.
  const maxCount = $derived.by(() => {
    let m = 0;
    if (chartMode === 'absolute') {
      for (const q of quarters) {
        const row = matrix.get(q);
        if (!row) continue;
        for (const t of selectedTerms) {
          const v = row.get(t) ?? 0;
          if (v > m) m = v;
        }
      }
    } else {
      for (const t of selectedTerms) {
        const series = cumMatrix.get(t) ?? [];
        for (const v of series) if (v > m) m = v;
      }
    }
    return m;
  });

  // --- SVG geometry -----------------------------------------------------
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

  function seriesAt(term: string, i: number): number {
    if (chartMode === 'absolute') {
      return matrix.get(quarters[i])?.get(term) ?? 0;
    }
    return (cumMatrix.get(term) ?? [])[i] ?? 0;
  }

  /** SVG `d` attribute for one term's polyline. */
  function pathFor(term: string): string {
    const parts: string[] = [];
    for (let i = 0; i < quarters.length; i++) {
      const v = seriesAt(term, i);
      parts.push(`${i === 0 ? 'M' : 'L'}${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)}`);
    }
    return parts.join(' ');
  }

  const yStep = $derived(Math.max(1, Math.ceil(maxCount / 4)));
  const yTicks = $derived.by(() => {
    const t: number[] = [];
    for (let v = 0; v <= maxCount; v += yStep) t.push(v);
    if (maxCount > 0 && t[t.length - 1] !== maxCount) t.push(maxCount);
    return t;
  });

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
  const summaries = $derived.by(() => {
    return selectedTerms.map((term) => {
      const g = termGrowth(fullBuckets, term);
      const top = topSystemsForTerm(records, term, 3);
      return { term, ...g, top };
    });
  });

  function formatGrowth(g: number): string {
    if (!isFinite(g)) return 'new';
    return `${(g * 100).toFixed(0)}%`;
  }
  function formatAbsolute(latest: number, prior: number): string {
    return `${prior} → ${latest}`;
  }

  // --- Co-occurrence ----------------------------------------------------
  //
  // Compute once over the filtered record set. We render the top-15
  // most-mentioned terms as a 15×15 heatmap; raw count is enough for
  // visual clustering and matches DECISIONS.md guidance on threshold.
  const cooccur = $derived(cooccurrence(records, TRACKED_TERMS));
  const HEATMAP_TOP_N = 15;
  const heatTerms = $derived(
    topTermsByCount(cooccur, TRACKED_TERMS, HEATMAP_TOP_N)
  );
  /** Largest off-diagonal count, for heatmap colour normalisation. */
  const heatMaxOff = $derived.by(() => {
    let m = 0;
    for (let i = 0; i < heatTerms.length; i++) {
      for (let j = i + 1; j < heatTerms.length; j++) {
        const v = pairCount(cooccur, heatTerms[i], heatTerms[j]);
        if (v > m) m = v;
      }
    }
    return m;
  });
  function heatFill(v: number): string {
    if (v === 0) return '#0f0f0f';
    if (heatMaxOff === 0) return '#1a1a1a';
    // Blend from dark grey to accent orange.
    const t = Math.min(1, v / heatMaxOff);
    const r = Math.round(0x1a + (0xd4 - 0x1a) * t);
    const g = Math.round(0x1a + 0x84 * t);
    const b = Math.round(0x1a + 0x5f * t * 0.5);
    return `rgb(${r}, ${g}, ${b})`;
  }

  // --- First-appearance year + newcomer cards ---------------------------
  const firstAppearance = $derived(firstAppearanceByTerm(records, TRACKED_TERMS));
  const NEWCOMER_FROM_YEAR = 2024;
  const newcomers = $derived(
    [...firstAppearance.entries()]
      .filter(([, year]) => year >= NEWCOMER_FROM_YEAR)
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  );
  const established = $derived(
    [...firstAppearance.entries()]
      .filter(([, year]) => year < NEWCOMER_FROM_YEAR)
      .sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]))
  );

  // --- Stable vs. novel ratio ------------------------------------------
  const ratios = $derived(stableVsNovelByYear(records, TRACKED_TERMS));
  const ratioMaxTotal = $derived.by(() => {
    let m = 0;
    for (const r of ratios) if (r.total > m) m = r.total;
    return m;
  });

  // --- Drill panel ------------------------------------------------------
  let drillTerm = $state<string | null>(null);
  const drillMentions = $derived(
    drillTerm ? mentionsForTerm(records, drillTerm) : []
  );
  function openDrill(t: string) {
    drillTerm = t;
  }
  function closeDrill() {
    drillTerm = null;
  }
</script>

<svelte:head>
  <SeoHead
    title="Vocabulary Drift: How AI Memory Terminology Evolves"
    description="Track which terms enter, spread, or fade across the AI memory field. From RAG to agentic — the language of adoption."
    path="/analyses/vocabulary"
    ogType="article"
  />
</svelte:head>

<div class="wrap">
  <header>
    <h1>Vocabulary drift</h1>
    <p class="lede">
      The words the memory field uses to describe itself are not static:
      "RAG" arrived in 2020, "agentic memory" became a phrase in 2024,
      "knowledge-graph" peaked then receded. Tracking which terms enter,
      spread, or fade — at the concept level rather than the system level —
      catches recipe shifts the lineage view (which follows specific
      systems) misses. A new vocabulary cluster is usually the first
      signal that practitioners agree a new pattern matters.
    </p>
    <p class="subtitle">
      {TRACKED_TERMS.length} curated memory terms tracked across
      {quarters.length} quarters · {records.length} of {data.records.length}
      records in scope after filters.
      <a class="back" href="{base}/analyses">← back to analyses hub</a>
    </p>
  </header>

  <aside class="method" aria-label="Methodology">
    <h2>How this view counts</h2>
    <ul>
      <li>
        <strong>One record, one mention.</strong> If a term appears 12 times
        in the same record's <code>desc</code> + <code>claims</code> we count
        it once — we want "did this artefact adopt the vocabulary?", not
        "how marketing-heavy was the copy?".
      </li>
      <li>
        <strong>Word-boundary, case-insensitive.</strong> "graph" matches
        "graph" and "graphs" but not "graphical"; "RAG" matches "RAG-fusion".
      </li>
      <li>
        <strong>Bucketed by <code>created</code> date.</strong> Same parser as
        the timeline view; records with year-only dates land in Q1 of that
        year. Records with unparseable dates are excluded from the chart but
        still contribute to co-occurrence and first-appearance counts.
      </li>
      <li>
        <strong>Curated 27-term list.</strong> Five thematic groups (cognitive
        / mechanism / agent-era / architectural / emerging). Extend via the
        helper module + a DECISIONS.md note. Anything outside this list shows
        up only as <em>novel-vocab share</em> in the ratio chart below — we
        don't claim to track every term, just the ones we curate.
      </li>
      <li>
        <strong>Small-N badge.</strong> A growth % is flagged when fewer than
        {SMALL_N_THRESHOLD} records sit on either side of the YoY ratio —
        without this, "2 → 13" reads as "+550%" and dominates the eye. See
        the "so what" callout for how to read flagged numbers.
      </li>
    </ul>
  </aside>

  <aside class="sowhat" aria-label="Interpretation">
    <h2>How to read it</h2>
    <p>
      <strong>Fast-rising terms = emerging recipes.</strong> A term whose
      cumulative arrival curve elbowed up in the last 4–6 quarters has
      crossed from novelty into common vocabulary; the systems mentioning
      it are usually converging on a new pattern. Open the drill panel
      to see which.
    </p>
    <p>
      <strong>Falling terms — two reads.</strong> Either the term is being
      absorbed (e.g. "knowledge-graph" being subsumed by "graph-RAG"
      where the same shape lives under a new label) or genuinely fading.
      Compare against the cumulative chart: if cumulative is still rising,
      the term is alive but quieter; if cumulative has plateaued for ≥4
      quarters, it's actually receding.
    </p>
    <p>
      <strong>Small-N rule.</strong> Percentages with the <span class="smalln-pill">small-N</span>
      badge are computed from fewer than {SMALL_N_THRESHOLD} records on at least
      one side of the ratio. Use the absolute "prior → latest" pair on the
      same card; the percentage is mostly noise.
    </p>
  </aside>

  <section class="filters" aria-label="Catalog filters">
    <div class="filter-row">
      <span class="filter-label">Tier:</span>
      {#each ALL_TIERS as t}
        {@const on = selectedTiers.has(t)}
        <button
          type="button"
          class="tier-chip"
          class:on
          onclick={() => toggleTier(t)}
        >T{t}</button>
      {/each}
    </div>
    <div class="filter-row">
      <label class="filter-label" for="sec">Section:</label>
      <select id="sec" bind:value={selectedSection}>
        <option value={null}>All sections ({data.records.length} records)</option>
        {#each sectionOptions as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
      <button class="btn ghost" type="button" onclick={resetFilters}>Reset</button>
    </div>
  </section>

  <section class="controls" aria-label="Term selector">
    <div class="control-row">
      <button class="btn" type="button" onclick={selectDefault}>Headline 6</button>
      <button class="btn" type="button" onclick={selectAll}>All {TRACKED_TERMS.length}</button>
      <button class="btn" type="button" onclick={selectNone}>None</button>
      <span class="count">{selected.size} selected</span>
      <span class="mode-toggle">
        <button
          class="btn"
          class:active={chartMode === 'absolute'}
          type="button"
          onclick={() => (chartMode = 'absolute')}
        >Per-quarter</button>
        <button
          class="btn"
          class:active={chartMode === 'cumulative'}
          type="button"
          onclick={() => (chartMode = 'cumulative')}
        >Cumulative arrival</button>
      </span>
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
        aria-label="{chartMode === 'absolute' ? 'Per-quarter' : 'Cumulative arrival'} chart, {selectedTerms.length} terms across {quarters.length} quarters"
      >
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

        <text
          transform="rotate(-90 14 {PAD_TOP + innerH / 2})"
          x="14"
          y={PAD_TOP + innerH / 2}
          text-anchor="middle"
          class="axis-label"
        >{chartMode === 'absolute' ? 'records mentioning term' : 'cumulative records'}</text>

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
          {#if hoverIdx !== null}
            {@const v = seriesAt(term, hoverIdx)}
            <circle
              cx={xAt(hoverIdx)}
              cy={yAt(v)}
              r="3"
              fill={termColor(term)}
              pointer-events="none"
            />
          {/if}
        {/each}

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
        {@const v = seriesAt(term, hoverIdx)}
        {#if v > 0}
          <span class="readout-item">
            <span class="swatch" style="background:{termColor(term)}"></span>
            {term} = {v}
          </span>{#if i < selectedTerms.length - 1}{' '}{/if}
        {/if}
      {/each}
    </p>
  {/if}

  <!-- ============================= -->
  <!-- Newcomer / established cards -->
  <!-- ============================= -->
  <section class="newcomers-wrap" aria-label="First-appearance chronology">
    <h2 class="section-h">First appearance by term</h2>
    <p class="section-sub">
      The earliest year each tracked term shows up in any record's
      <code>desc</code> or <code>claims</code> within the current filter.
      "Newcomers" arrived in {NEWCOMER_FROM_YEAR} or later — they are the
      vocabulary candidates most worth watching.
    </p>
    {#if newcomers.length === 0 && established.length === 0}
      <p class="empty">No vocabulary hits in the current filter.</p>
    {:else}
      <div class="cohort-grid">
        <div class="cohort">
          <h3>Newcomers ({newcomers.length}) · first seen ≥ {NEWCOMER_FROM_YEAR}</h3>
          <ul class="cohort-list">
            {#each newcomers as [t, year]}
              <li>
                <button class="link-term" onclick={() => openDrill(t)}>
                  <span class="swatch" style="background:{termColor(t)}"></span>
                  {t}
                </button>
                <span class="year">{year}</span>
              </li>
            {/each}
            {#if newcomers.length === 0}
              <li class="muted">none in scope</li>
            {/if}
          </ul>
        </div>
        <div class="cohort">
          <h3>Established ({established.length}) · first seen &lt; {NEWCOMER_FROM_YEAR}</h3>
          <ul class="cohort-list">
            {#each established as [t, year]}
              <li>
                <button class="link-term" onclick={() => openDrill(t)}>
                  <span class="swatch" style="background:{termColor(t)}"></span>
                  {t}
                </button>
                <span class="year">{year}</span>
              </li>
            {/each}
            {#if established.length === 0}
              <li class="muted">none in scope</li>
            {/if}
          </ul>
        </div>
      </div>
    {/if}
  </section>

  <!-- ============================= -->
  <!-- Per-term cards (absolute first) -->
  <!-- ============================= -->
  <section class="cards" aria-label="Per-term summary">
    {#each summaries as s}
      <article class="card" style="--accent:{termColor(s.term)}">
        <header>
          <span class="swatch" style="background:{termColor(s.term)}"></span>
          <h2>{s.term}</h2>
          <button class="drill-btn" type="button" onclick={() => openDrill(s.term)} aria-label="Show systems mentioning {s.term}">→</button>
        </header>
        <dl>
          <dt>Total records</dt>
          <dd class="hi">{s.total}</dd>
          <dt>YoY (absolute)</dt>
          <dd>
            {#if s.latestYear === -1}
              —
            {:else}
              <span class="abs">{formatAbsolute(s.latestYearCount, s.priorYearCount)}</span>
              <span class="abs-meta">({s.priorYear} → {s.latestYear})</span>
            {/if}
          </dd>
          <dt>YoY (percent)</dt>
          <dd
            class:positive={!s.smallN && isFinite(s.growth_yoy) && s.growth_yoy > 0}
            class:negative={!s.smallN && isFinite(s.growth_yoy) && s.growth_yoy < 0}
            class:emerge={!s.smallN && !isFinite(s.growth_yoy)}
            class:muted={s.smallN}
          >
            {formatGrowth(s.growth_yoy)}
            {#if s.smallN}
              <span class="smalln-pill" title="Small-N — fewer than {SMALL_N_THRESHOLD} records on at least one side of the ratio; interpret cautiously.">small-N</span>
            {/if}
          </dd>
          <dt>First seen</dt>
          <dd>{s.firstYear === -1 ? '—' : s.firstYear}</dd>
          <dt>Latest active</dt>
          <dd>{s.latestQuarter || '—'}</dd>
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

  <!-- ============================= -->
  <!-- Co-occurrence heatmap         -->
  <!-- ============================= -->
  <section class="heatmap-wrap" aria-label="Term co-occurrence">
    <h2 class="section-h">Term co-occurrence (top {HEATMAP_TOP_N})</h2>
    <p class="section-sub">
      How often two terms appear in the same record's <code>desc</code> +
      <code>claims</code>. Darker = more co-mentions. Edges with count
      ≥ {COOCCUR_THRESHOLD} form the cluster signal. Click a row label to
      drill into that term.
    </p>
    {#if heatTerms.length === 0}
      <p class="empty">No terms in scope.</p>
    {:else}
      {@const CELL = 28}
      {@const HEAT_LEFT = 130}
      {@const HEAT_TOP = 96}
      {@const heatW = HEAT_LEFT + heatTerms.length * CELL + 10}
      {@const heatH = HEAT_TOP + heatTerms.length * CELL + 10}
      <div class="heat-scroll">
        <svg viewBox="0 0 {heatW} {heatH}" width={heatW} height={heatH}
             role="img" aria-label="Co-occurrence heatmap of top {HEATMAP_TOP_N} terms">
          <!-- Column labels (rotated) -->
          {#each heatTerms as t, j}
            <text
              x={HEAT_LEFT + j * CELL + CELL / 2}
              y={HEAT_TOP - 6}
              text-anchor="start"
              transform="rotate(-50 {HEAT_LEFT + j * CELL + CELL / 2} {HEAT_TOP - 6})"
              class="heat-label"
            >{t}</text>
          {/each}
          <!-- Row labels + cells -->
          {#each heatTerms as ti, i}
            <text
              x={HEAT_LEFT - 8}
              y={HEAT_TOP + i * CELL + CELL / 2 + 4}
              text-anchor="end"
              class="heat-label heat-label-row"
              role="button"
              tabindex="0"
              aria-label="Drill into {ti}"
              onclick={() => openDrill(ti)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDrill(ti); } }}
              style="cursor:pointer"
            >{ti}</text>
            {#each heatTerms as tj, j}
              {@const v = pairCount(cooccur, ti, tj)}
              {@const isDiag = i === j}
              <rect
                x={HEAT_LEFT + j * CELL}
                y={HEAT_TOP + i * CELL}
                width={CELL - 1}
                height={CELL - 1}
                fill={isDiag ? '#222' : heatFill(v)}
                stroke={v >= COOCCUR_THRESHOLD && !isDiag ? '#d4845f' : '#1a1a1a'}
                stroke-width={v >= COOCCUR_THRESHOLD && !isDiag ? 1 : 0.5}
              >
                <title>{ti} ∩ {tj} = {v}{isDiag ? ' (self)' : ''}</title>
              </rect>
              {#if v > 0}
                <text
                  x={HEAT_LEFT + j * CELL + CELL / 2}
                  y={HEAT_TOP + i * CELL + CELL / 2 + 3.5}
                  text-anchor="middle"
                  class="heat-cell"
                  style="fill: {isDiag ? '#888' : v >= heatMaxOff * 0.5 ? '#0f0f0f' : '#bbb'}"
                  pointer-events="none"
                >{v}</text>
              {/if}
            {/each}
          {/each}
        </svg>
      </div>
      <p class="heat-legend">
        Threshold ≥ {COOCCUR_THRESHOLD} shown with orange border.
        Max off-diagonal: {heatMaxOff}.
      </p>
    {/if}
  </section>

  <!-- ============================= -->
  <!-- Stable vs novel ratio         -->
  <!-- ============================= -->
  <section class="ratio-wrap" aria-label="Stable vs novel vocabulary">
    <h2 class="section-h">Stable vs novel vocabulary per year</h2>
    <p class="section-sub">
      For each year, the share of new records whose <code>desc</code> +
      <code>claims</code> mention at least one of our {TRACKED_TERMS.length}
      curated terms (stable) vs records using none of them (novel /
      drifting). A rising novel share = the field's vocabulary is
      outrunning our curated list. Bar width is the record count for the
      year (normalised to the largest); rising novel slice = vocabulary
      churn.
    </p>
    {#if ratios.length === 0}
      <p class="empty">No data in scope.</p>
    {:else}
      <table class="ratio-table">
        <thead>
          <tr>
            <th scope="col">Year</th>
            <th scope="col">Records</th>
            <th scope="col">Stable</th>
            <th scope="col">Novel</th>
            <th scope="col">Stable share</th>
            <th scope="col" class="bar-col">Mix</th>
          </tr>
        </thead>
        <tbody>
          {#each ratios as r}
            {@const sharePct = (r.stableShare * 100).toFixed(0)}
            {@const widthPct = ratioMaxTotal === 0 ? 0 : (r.total / ratioMaxTotal) * 100}
            <tr>
              <td>{r.year}</td>
              <td class="num">{r.total}</td>
              <td class="num">{r.stable}</td>
              <td class="num">{r.novel}</td>
              <td class="num">{sharePct}%</td>
              <td class="bar-cell">
                <span class="bar-outer" style="width: {widthPct}%">
                  <span class="bar-stable" style="width: {r.stableShare * 100}%"></span>
                  <span class="bar-novel" style="width: {(1 - r.stableShare) * 100}%"></span>
                </span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <!-- ============================= -->
  <!-- Drill panel                   -->
  <!-- ============================= -->
  {#if drillTerm}
    <div class="drill-overlay" role="dialog" aria-modal="true" aria-label="Records mentioning {drillTerm}">
      <div class="drill-panel">
        <header>
          <span class="swatch" style="background:{termColor(drillTerm)}"></span>
          <h2>{drillTerm} · {drillMentions.length} records</h2>
          <button class="close-btn" onclick={closeDrill} aria-label="Close drill panel">×</button>
        </header>
        <p class="drill-sub">
          Sorted by record creation date, newest first. Use this to see
          which systems carry the vocabulary forward and which were the
          early adopters.
        </p>
        <div class="drill-list">
          {#each drillMentions as m}
            <a class="drill-row" href="{base}/?id={m.id}">
              <span class="drill-year">{m.year ?? '—'}{m.year && m.quarter ? `-Q${m.quarter}` : ''}</span>
              <span class="drill-tier" data-tier={m.tier}>T{m.tier}</span>
              <span class="drill-name">{m.name}</span>
              <span class="drill-section">{m.section}</span>
            </a>
          {/each}
          {#if drillMentions.length === 0}
            <p class="empty">No records mention this term in the current filter.</p>
          {/if}
        </div>
      </div>
      <button class="drill-scrim" aria-label="Close" onclick={closeDrill}></button>
    </div>
  {/if}
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
  .lede {
    margin: 0 0 12px;
    color: #cfcfcf;
    font-size: 0.95rem;
    line-height: 1.55;
    max-width: 820px;
  }
  .subtitle {
    margin: 0 0 24px;
    color: #aaa;
    font-size: 0.9rem;
    line-height: 1.5;
  }
  .method code, .section-sub code {
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

  .method, .sowhat {
    background: #121212;
    border: 1px solid #262626;
    border-left: 3px solid #d4845f;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 0 0 16px;
    color: #cfcfcf;
    font-size: 0.88rem;
    line-height: 1.55;
  }
  .sowhat {
    border-left-color: #5fa8d4;
  }
  .method h2, .sowhat h2 {
    margin: 0 0 8px;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    font-weight: 600;
  }
  .method ul {
    margin: 0;
    padding-left: 18px;
  }
  .method li {
    margin-bottom: 4px;
  }
  .sowhat p {
    margin: 0 0 6px;
  }
  .smalln-pill {
    display: inline-block;
    background: #2a1a1a;
    border: 1px solid #4a2a2a;
    color: #d4a55f;
    padding: 1px 6px;
    border-radius: 10px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-left: 4px;
    vertical-align: middle;
  }

  .filters {
    background: #131313;
    border: 1px solid #262626;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 14px;
  }
  .filter-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 6px;
  }
  .filter-row:last-child { margin-bottom: 0; }
  .filter-label {
    color: #888;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-right: 4px;
  }
  .tier-chip {
    background: #181818;
    border: 1px solid #262626;
    color: #888;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    cursor: pointer;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  .tier-chip.on {
    background: #1d1d1d;
    border-color: #d4845f;
    color: #e8e8e8;
  }
  select {
    background: #1a1a1a;
    color: #ddd;
    border: 1px solid #2f2f2f;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 0.85rem;
    min-width: 280px;
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
  .btn.active {
    background: #2a1f17;
    border-color: #d4845f;
    color: #e8e8e8;
  }
  .btn.ghost {
    background: transparent;
    color: #888;
  }
  .count {
    color: #888;
    font-size: 0.82rem;
    margin-left: 4px;
  }
  .mode-toggle {
    display: inline-flex;
    gap: 4px;
    margin-left: auto;
    border-left: 1px solid #262626;
    padding-left: 10px;
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

  .section-h {
    margin: 32px 0 6px;
    font-size: 1.05rem;
    color: #e8e8e8;
    letter-spacing: -0.01em;
  }
  .section-sub {
    margin: 0 0 14px;
    color: #999;
    font-size: 0.85rem;
    line-height: 1.5;
    max-width: 820px;
  }

  .cohort-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  .cohort {
    background: #131313;
    border: 1px solid #262626;
    border-radius: 6px;
    padding: 12px 14px;
  }
  .cohort h3 {
    margin: 0 0 8px;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    font-weight: 600;
  }
  .cohort-list {
    list-style: none;
    padding: 0;
    margin: 0;
    columns: 2;
    column-gap: 14px;
  }
  .cohort-list li {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    padding: 2px 0;
    break-inside: avoid;
  }
  .cohort-list li.muted {
    color: #666;
    font-style: italic;
  }
  .link-term {
    background: none;
    border: none;
    color: #e8e8e8;
    cursor: pointer;
    padding: 0;
    font-size: 0.85rem;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  .link-term:hover {
    color: #d4845f;
  }
  .year {
    color: #888;
    font-variant-numeric: tabular-nums;
    margin-left: auto;
    font-size: 0.78rem;
  }

  .cards {
    margin-top: 18px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
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
  .drill-btn {
    margin-left: auto;
    background: #1a1a1a;
    border: 1px solid #2f2f2f;
    color: #888;
    width: 22px;
    height: 22px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    line-height: 1;
    padding: 0;
  }
  .drill-btn:hover {
    color: #d4845f;
    border-color: #d4845f;
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
  .card dd.hi {
    color: #e8e8e8;
    font-weight: 600;
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
  .card dd.muted {
    color: #888;
    font-style: italic;
  }
  .abs {
    font-family: ui-monospace, SFMono-Regular, monospace;
    color: #ddd;
  }
  .abs-meta {
    color: #777;
    font-size: 0.78rem;
    margin-left: 4px;
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

  /* Heatmap */
  .heatmap-wrap {
    margin-top: 16px;
  }
  .heat-scroll {
    overflow-x: auto;
    background: #0f0f0f;
    border: 1px solid #1f1f1f;
    border-radius: 8px;
    padding: 12px;
  }
  .heat-label {
    fill: #ddd;
    font-size: 11px;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  .heat-label-row:hover {
    fill: #d4845f;
  }
  .heat-cell {
    font-size: 10px;
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-variant-numeric: tabular-nums;
  }
  .heat-legend {
    color: #888;
    font-size: 0.78rem;
    margin: 6px 0 0;
  }

  /* Ratio table */
  .ratio-wrap {
    margin-top: 16px;
  }
  .ratio-table {
    width: 100%;
    border-collapse: collapse;
    background: #131313;
    border: 1px solid #262626;
    border-radius: 6px;
    overflow: hidden;
    font-size: 0.85rem;
  }
  .ratio-table th, .ratio-table td {
    padding: 6px 10px;
    text-align: left;
    border-bottom: 1px solid #1f1f1f;
  }
  .ratio-table th {
    background: #181818;
    color: #888;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
  }
  .ratio-table td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    color: #ddd;
  }
  .bar-col { width: 30%; }
  .bar-cell { padding: 6px 10px; }
  .bar-outer {
    display: inline-flex;
    height: 14px;
    background: #1a1a1a;
    border-radius: 3px;
    overflow: hidden;
  }
  .bar-stable {
    background: #5fa8d4;
    height: 100%;
  }
  .bar-novel {
    background: #d4845f;
    height: 100%;
  }

  /* Drill overlay */
  .drill-overlay {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    align-items: stretch;
    justify-content: flex-end;
  }
  .drill-scrim {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    border: none;
    cursor: pointer;
    z-index: 0;
  }
  .drill-panel {
    position: relative;
    z-index: 1;
    width: min(560px, 95vw);
    background: #111;
    border-left: 1px solid #262626;
    padding: 20px 24px;
    overflow-y: auto;
  }
  .drill-panel header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }
  .drill-panel header h2 {
    margin: 0;
    font-size: 1.05rem;
    color: #e8e8e8;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  .close-btn {
    margin-left: auto;
    background: none;
    border: none;
    color: #888;
    font-size: 1.4rem;
    line-height: 1;
    cursor: pointer;
    padding: 0 6px;
  }
  .close-btn:hover {
    color: #e8e8e8;
  }
  .drill-sub {
    color: #999;
    font-size: 0.85rem;
    line-height: 1.5;
    margin: 0 0 14px;
  }
  .drill-list {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .drill-row {
    display: grid;
    grid-template-columns: 70px 36px 1fr auto;
    gap: 10px;
    align-items: center;
    padding: 8px 10px;
    background: #161616;
    border: 1px solid #1f1f1f;
    border-radius: 4px;
    color: #ddd;
    text-decoration: none;
    font-size: 0.85rem;
  }
  .drill-row:hover {
    background: #1c1c1c;
    border-color: #2f2f2f;
  }
  .drill-year {
    color: #888;
    font-variant-numeric: tabular-nums;
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-size: 0.78rem;
  }
  .drill-tier {
    color: #d4845f;
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-size: 0.78rem;
    text-align: center;
  }
  .drill-tier[data-tier='1'] { color: #5fd49b; }
  .drill-tier[data-tier='2'] { color: #5fa8d4; }
  .drill-tier[data-tier='3'] { color: #d4845f; }
  .drill-tier[data-tier='4'] { color: #d4c25f; }
  .drill-tier[data-tier='5'] { color: #888; }
  .drill-name {
    color: #e8e8e8;
  }
  .drill-section {
    color: #888;
    font-size: 0.75rem;
    text-align: right;
  }

  @media (max-width: 700px) {
    .cohort-grid { grid-template-columns: 1fr; }
    .cohort-list { columns: 1; }
  }
</style>
