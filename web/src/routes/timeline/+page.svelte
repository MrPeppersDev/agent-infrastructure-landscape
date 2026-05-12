<script lang="ts">
  // Timeline view (issue #13): a stacked-bar histogram showing when systems
  // in the landscape were created, bucketed by year-quarter and stacked by
  // tier. Pure SVG — no charting library — because the data is small
  // (~500 records, ~25 quarters, 5 tiers = ~125 rects) and hand-rolled
  // gives us pixel-perfect control over click targets and tooltips.
  //
  // See $lib/timeline.ts for the parsing and bucketing logic, and
  // docs/DECISIONS.md (2026-05-07 "Timeline view") for the stacking
  // choice rationale (tier over section).

  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import type { LandscapeRecord, Tier } from '$lib/types';
  import {
    bucketRecords,
    primarySection,
    parseCreatedDate,
    TIERS,
    TIER_COLOURS,
    TIER_LABELS,
    type BucketRow
  } from '$lib/timeline';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  // --- Section filter ----------------------------------------------------
  //
  // null = "All sections". Sections are sorted by record count desc so the
  // most populated options appear at the top (the user's primary
  // exploration mode is "find waves in a specific corner of the landscape").
  const sectionOptions = $derived.by<{ section: string; count: number }[]>(() => {
    const counts = new Map<string, number>();
    for (const r of data.records) {
      const s = primarySection(r);
      counts.set(s, (counts.get(s) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([section, count]) => ({ section, count }))
      .sort((a, b) => b.count - a.count || a.section.localeCompare(b.section));
  });

  let selectedSection = $state<string>(''); // '' === all

  const buckets = $derived<BucketRow[]>(
    bucketRecords(data.records, selectedSection || null)
  );

  // Total parseable / unparseable for the subtitle. Recomputed lazily — at
  // 523 records this is microseconds.
  const stats = $derived.by(() => {
    const pool = selectedSection
      ? data.records.filter((r) => primarySection(r) === selectedSection)
      : data.records;
    let parseable = 0;
    let unparseable = 0;
    for (const r of pool) {
      if (parseCreatedDate(r.cells.created?.value)) parseable += 1;
      else unparseable += 1;
    }
    return { parseable, unparseable, total: pool.length };
  });

  // --- SVG geometry ------------------------------------------------------
  //
  // We size the chart by the bucket count so wide ranges (decades worth of
  // quarters) get a horizontally-scrollable canvas rather than a smushed
  // bar chart with 4px-wide rects. 32px per bar leaves room for a slim gap
  // between bars and a readable label every 4 buckets.
  const BAR_W = 28;
  const BAR_GAP = 6;
  const CHART_H = 320;
  const PAD_LEFT = 56;
  const PAD_RIGHT = 16;
  const PAD_TOP = 16;
  const PAD_BOTTOM = 56;

  const innerW = $derived(buckets.length * (BAR_W + BAR_GAP));
  const totalW = $derived(PAD_LEFT + innerW + PAD_RIGHT);
  const innerH = CHART_H - PAD_TOP - PAD_BOTTOM;

  const maxCount = $derived(
    buckets.reduce((m, b) => {
      const sum = b.byTier.reduce((a, n) => a + n, 0);
      return sum > m ? sum : m;
    }, 0)
  );

  // Y-axis tick count: 4 evenly spaced ticks above zero, snapped to a nice
  // round step. For the catalog's actual counts (single-digit-per-bucket
  // common, max usually <30) a step of `ceil(max/4)` is fine.
  const yStep = $derived(Math.max(1, Math.ceil(maxCount / 4)));
  const yTicks = $derived.by(() => {
    const ticks: number[] = [];
    for (let t = 0; t <= maxCount; t += yStep) ticks.push(t);
    if (ticks[ticks.length - 1] !== maxCount && maxCount > 0) ticks.push(maxCount);
    return ticks;
  });

  function yScale(v: number): number {
    if (maxCount === 0) return innerH;
    return innerH - (v / maxCount) * innerH;
  }

  // --- Hover tooltip -----------------------------------------------------
  let hoverIdx = $state<number | null>(null);
  let hoverX = $state(0);
  let hoverY = $state(0);

  function onBarEnter(i: number, ev: PointerEvent) {
    hoverIdx = i;
    hoverX = ev.clientX;
    hoverY = ev.clientY;
  }
  function onBarMove(ev: PointerEvent) {
    hoverX = ev.clientX;
    hoverY = ev.clientY;
  }
  function onBarLeave() {
    hoverIdx = null;
  }

  // --- Click → drill-through to table -----------------------------------
  //
  // We send the user to / with section=<>&tier=<list> using the same param
  // format the table's URL codec understands (csv values, tier as int).
  // We don't import url-state.ts here because we'd need to build a full
  // FilterState; the codec format is stable and a hand-rolled URL avoids
  // the round-trip through emptyState() / stateToUrl(). Tier is included
  // only if the bucket has *any* tier represented (so the table shows a
  // useful subset rather than empty if a tier wasn't created that
  // quarter).
  //
  // Caveat: there's no "year" facet on the table today. So the drill is
  // an over-approximation — "everything in this section in these tiers",
  // not "everything in this bucket". That's the best fidelity we can give
  // without inventing a new facet, and it's still a useful zoom-in.
  function onBarClick(bucket: BucketRow) {
    const tiersInBucket: Tier[] = TIERS.filter((t) => bucket.byTier[t - 1] > 0);
    const params = new URLSearchParams();
    if (selectedSection) params.set('section', selectedSection);
    if (tiersInBucket.length > 0) params.set('tier', tiersInBucket.join(','));
    const qs = params.toString();
    goto(qs ? `/?${qs}` : '/');
  }

  // Tier counts for legend (and small "n records charted" stats).
  const tierTotals = $derived.by(() => {
    const tot: [number, number, number, number, number] = [0, 0, 0, 0, 0];
    for (const b of buckets) {
      for (let i = 0; i < 5; i++) tot[i] += b.byTier[i];
    }
    return tot;
  });

  const charted = $derived(tierTotals.reduce((a, n) => a + n, 0));

  // X-axis label cadence: label every Nth bar, where N is chosen so we
  // never crowd more than ~15 labels onto the axis. Empty quarters get a
  // tick mark but no label.
  const labelStride = $derived(Math.max(1, Math.ceil(buckets.length / 16)));
</script>

<svelte:head>
  <title>Memory Systems Landscape — Timeline</title>
</svelte:head>

<div class="wrap">
  <header>
    <h1>Created-date timeline</h1>
    <p class="subtitle">
      {charted.toLocaleString()} of {stats.total.toLocaleString()} records charted
      across {buckets.length} quarters · stacked by tier
      {#if stats.unparseable > 0}
        · {stats.unparseable} unparseable
      {/if}
      <a class="back" href="{base}/">← back to table</a>
    </p>
  </header>

  <div class="controls">
    <label>
      Section:
      <select bind:value={selectedSection}>
        <option value="">All sections ({data.records.length})</option>
        {#each sectionOptions as opt}
          <option value={opt.section}>{opt.section} ({opt.count})</option>
        {/each}
      </select>
    </label>
    <ul class="legend">
      {#each TIERS as t}
        <li>
          <span class="swatch" style="background:{TIER_COLOURS[t]}"></span>
          {TIER_LABELS[t]} ({tierTotals[t - 1]})
        </li>
      {/each}
    </ul>
  </div>

  <div class="chart-scroll">
    {#if buckets.length === 0}
      <p class="empty">No parseable created-date data for this section.</p>
    {:else}
      <svg
        viewBox="0 0 {totalW} {CHART_H}"
        width={totalW}
        height={CHART_H}
        role="img"
        aria-label="Created-date histogram, year-quarter buckets, stacked by tier"
      >
        <!-- Gridlines + Y-axis ticks -->
        {#each yTicks as t}
          <line
            x1={PAD_LEFT}
            x2={PAD_LEFT + innerW}
            y1={PAD_TOP + yScale(t)}
            y2={PAD_TOP + yScale(t)}
            stroke="#21262d"
            stroke-width="1"
          />
          <text
            x={PAD_LEFT - 8}
            y={PAD_TOP + yScale(t) + 4}
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
        >records created</text>

        <!-- Bars -->
        {#each buckets as bucket, i}
          {@const x = PAD_LEFT + i * (BAR_W + BAR_GAP)}
          {@const total = bucket.byTier.reduce((a, n) => a + n, 0)}
          <!-- One transparent hit target spanning the full column height so
               hover and click work even when the stacked bars are short. -->
          <rect
            x={x}
            y={PAD_TOP}
            width={BAR_W}
            height={innerH}
            fill="transparent"
            class="hit"
            onpointerenter={(e) => onBarEnter(i, e)}
            onpointermove={onBarMove}
            onpointerleave={onBarLeave}
            onclick={() => onBarClick(bucket)}
            onkeydown={(e) => { if (e.key === 'Enter') onBarClick(bucket); }}
            role="button"
            tabindex="0"
            aria-label="{bucket.key}: {total} records"
          />
          <!-- Stack tiers bottom-up: tier 1 at the base, tier 5 at the top.
               This matches the legend reading order (1 = strongest tier
               first / most prominent at eye-level). -->
          {#each TIERS as t}
            {@const below = TIERS.slice(0, t - 1).reduce((acc, tt) => acc + bucket.byTier[tt - 1], 0)}
            {@const n = bucket.byTier[t - 1]}
            {#if n > 0}
              <rect
                x={x}
                y={PAD_TOP + yScale(below + n)}
                width={BAR_W}
                height={yScale(below) - yScale(below + n)}
                fill={TIER_COLOURS[t]}
                class={hoverIdx === i ? 'bar bar-hover' : 'bar'}
                pointer-events="none"
              />
            {/if}
          {/each}

          <!-- X-axis ticks and selective labels -->
          <line
            x1={x + BAR_W / 2}
            x2={x + BAR_W / 2}
            y1={PAD_TOP + innerH}
            y2={PAD_TOP + innerH + (i % labelStride === 0 ? 6 : 3)}
            stroke="#30363d"
            stroke-width="1"
          />
          {#if i % labelStride === 0}
            <text
              x={x + BAR_W / 2}
              y={PAD_TOP + innerH + 20}
              text-anchor="middle"
              class="tick-label"
            >{bucket.key}</text>
          {/if}
        {/each}

        <!-- X-axis baseline -->
        <line
          x1={PAD_LEFT}
          x2={PAD_LEFT + innerW}
          y1={PAD_TOP + innerH}
          y2={PAD_TOP + innerH}
          stroke="#484f58"
          stroke-width="1"
        />

        <!-- X-axis label -->
        <text
          x={PAD_LEFT + innerW / 2}
          y={CHART_H - 8}
          text-anchor="middle"
          class="axis-label"
        >year-quarter created</text>
      </svg>
    {/if}
  </div>

  <p class="hint">
    Click a bar to drill into the table filtered by this bucket's section + tiers.
    Year-only dates are placed in Q1; year ranges use the earlier year.
  </p>

  <!-- Tooltip is a position:fixed div outside the SVG so it can overflow
       the chart-scroll container. Mouse-coords are clientX/Y, hence fixed. -->
  {#if hoverIdx !== null && buckets[hoverIdx]}
    {@const b = buckets[hoverIdx]}
    {@const total = b.byTier.reduce((a, n) => a + n, 0)}
    <div
      class="tooltip"
      style="left: {hoverX + 14}px; top: {hoverY + 14}px"
      aria-hidden="true"
    >
      <div class="tt-head">{b.key} · {total} record{total === 1 ? '' : 's'}</div>
      {#if total > 0}
        <ul class="tt-list">
          {#each b.records.slice(0, 12) as r}
            <li>
              <span class="tt-swatch" style="background:{TIER_COLOURS[r.tier]}"></span>
              {r.name}
              <span class="tt-tier">T{r.tier}</span>
            </li>
          {/each}
          {#if b.records.length > 12}
            <li class="tt-more">… and {b.records.length - 12} more</li>
          {/if}
        </ul>
      {:else}
        <div class="tt-empty">(no records this quarter)</div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .wrap {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 8px 0 24px;
    color: #c9d1d9;
  }
  header h1 {
    font-size: 1.4rem;
    margin: 0;
    letter-spacing: -0.01em;
  }
  .subtitle {
    color: #8b949e;
    font-size: 0.85rem;
    margin: 4px 0 0 0;
    font-variant-numeric: tabular-nums;
  }
  .back {
    margin-left: 12px;
    color: #58a6ff;
    text-decoration: none;
  }
  .back:hover { text-decoration: underline; }
  .controls {
    display: flex;
    align-items: center;
    gap: 24px;
    flex-wrap: wrap;
  }
  .controls label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85rem;
    color: #8b949e;
  }
  .controls select {
    background: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 0.85rem;
    min-width: 280px;
  }
  .legend {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    font-size: 0.78rem;
    color: #8b949e;
  }
  .legend li { display: inline-flex; align-items: center; gap: 6px; }
  .swatch {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }
  .chart-scroll {
    overflow-x: auto;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #0d1117;
    padding: 8px 4px;
  }
  .empty {
    color: #8b949e;
    font-style: italic;
    padding: 32px;
    text-align: center;
  }
  :global(.bar) {
    transition: opacity 80ms linear;
  }
  :global(.bar-hover) {
    opacity: 0.78;
  }
  :global(.hit) {
    cursor: pointer;
  }
  :global(.hit:focus) {
    outline: 1px solid #58a6ff;
  }
  :global(.tick-label) {
    font-size: 10px;
    fill: #8b949e;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  :global(.axis-label) {
    font-size: 11px;
    fill: #6e7681;
  }
  .hint {
    color: #6e7681;
    font-size: 0.8rem;
    font-style: italic;
    margin: 0;
  }
  .tooltip {
    position: fixed;
    z-index: 50;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 0.8rem;
    color: #c9d1d9;
    max-width: 320px;
    pointer-events: none;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  }
  .tt-head {
    font-weight: 600;
    margin-bottom: 4px;
    color: #f0f6fc;
  }
  .tt-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .tt-list li {
    display: flex;
    align-items: center;
    gap: 6px;
    line-height: 1.5;
  }
  .tt-swatch {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .tt-tier {
    color: #6e7681;
    font-size: 0.7rem;
    margin-left: auto;
  }
  .tt-more {
    color: #8b949e;
    font-style: italic;
    margin-top: 4px;
  }
  .tt-empty {
    color: #6e7681;
    font-style: italic;
  }
</style>
