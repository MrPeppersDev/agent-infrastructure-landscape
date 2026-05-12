<script lang="ts">
  // Influence-vs-adoption matrix (issue #22).
  //
  // Two-axis scatter on the in-catalog citation graph:
  //   X = inbound `cites` edges  (academic influence)
  //   Y = inbound `integrates-with` + `built-on` edges (commercial adoption)
  //
  // Pure SVG — no charting library. We do all geometry in component-local
  // helpers so the markup stays declarative and the projection is testable
  // by reading the source.
  //
  // Scale choice: LINEAR. Both axes have very small integer ranges (cites
  // max ≈ 9, integrations max ≈ 12) and ~80% of records sit at the origin.
  // A log scale would (a) require shifting zeros, (b) compress the
  // interesting outliers, and (c) confuse readers who expect "10 → twice
  // as influential as 5". Documented in DECISIONS.md.

  import { base } from '$app/paths';
  import type { Edge, LandscapeRecord } from '$lib/types';
  import {
    buildPoints,
    classifyQuadrant,
    nonZeroMedian,
    quadrantCounts,
    sectionColor,
    tierRadius,
    topInQuadrant,
    type InfluencePoint,
    type Quadrant
  } from '$lib/analyses/influence';

  let { data }: { data: { records: LandscapeRecord[]; edges: Edge[] } } =
    $props();

  const points = $derived(buildPoints(data.records, data.edges));

  // Cutoffs: non-zero medians. Empirically (May 2026) → cites 2, integ 1.5.
  const citesCut = $derived(nonZeroMedian(points.map((p) => p.citesIn)));
  const integCut = $derived(
    nonZeroMedian(points.map((p) => p.integrationsIn))
  );

  const counts = $derived(quadrantCounts(points, citesCut, integCut));

  // Annotate top-K of each quadrant. We use 4 by default; if a quadrant has
  // fewer points it just shows fewer labels.
  const ANNOTATE_K = 4;
  const annotated = $derived(
    new Set<string>([
      ...topInQuadrant(points, citesCut, integCut, 'both', ANNOTATE_K).map(
        (p) => p.id
      ),
      ...topInQuadrant(points, citesCut, integCut, 'engineering', ANNOTATE_K).map(
        (p) => p.id
      ),
      ...topInQuadrant(points, citesCut, integCut, 'orphan', ANNOTATE_K).map(
        (p) => p.id
      ),
      ...topInQuadrant(points, citesCut, integCut, 'tail', 0).map((p) => p.id)
      // No annotations in the tail by design — too many points, all small.
    ])
  );

  // --- Projection --------------------------------------------------------

  // Padding for axis labels + quadrant chrome.
  const W = 880;
  const H = 560;
  const PAD_L = 64;
  const PAD_R = 24;
  const PAD_T = 32;
  const PAD_B = 56;

  // Pad the data range by 0.5 on each end so points don't sit on the
  // chart edge.
  const xMax = $derived(
    Math.max(1, ...points.map((p) => p.citesIn)) + 0.5
  );
  const yMax = $derived(
    Math.max(1, ...points.map((p) => p.integrationsIn)) + 0.5
  );

  function projX(c: number): number {
    return PAD_L + ((c + 0.0) / xMax) * (W - PAD_L - PAD_R);
  }
  function projY(i: number): number {
    // SVG y grows downward — invert.
    return H - PAD_B - ((i + 0.0) / yMax) * (H - PAD_T - PAD_B);
  }

  // --- Jitter to de-overlap the origin pile ------------------------------
  //
  // Around 80% of records are at (0, 0). Without jitter they pile into a
  // single mark and the reader can't tell that there are 480+ records
  // there. We apply a tiny deterministic radial jitter (based on a hash of
  // the record id) for points whose value on a given axis is 0. Jittered
  // points stay inside the long-tail quadrant by construction (jitter
  // magnitude < the half-distance to the cutoff line).

  function hashTo01(id: string, salt: number): number {
    let h = salt;
    for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
    return ((h % 1000) / 1000) * 2 - 1; // [-1, 1)
  }

  function jittered(p: InfluencePoint): { x: number; y: number } {
    // Magnitude in data-units. We only nudge points whose value is 0 on
    // that axis; once the value > 0 the position is real.
    const jx = p.citesIn === 0 ? hashTo01(p.id, 17) * 0.35 : 0;
    const jy = p.integrationsIn === 0 ? hashTo01(p.id, 91) * 0.35 : 0;
    return { x: projX(p.citesIn + jx), y: projY(p.integrationsIn + jy) };
  }

  // --- Hover state -------------------------------------------------------

  let hoverId = $state<string | null>(null);
  let hoverX = $state(0);
  let hoverY = $state(0);

  function onPointEnter(p: InfluencePoint, ev: MouseEvent) {
    hoverId = p.id;
    const target = ev.currentTarget as SVGElement;
    const svg = target.ownerSVGElement;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    hoverX = ev.clientX - rect.left;
    hoverY = ev.clientY - rect.top;
  }
  function onPointLeave() {
    hoverId = null;
  }
  const hoverPoint = $derived(
    hoverId ? points.find((p) => p.id === hoverId) ?? null : null
  );

  // Drill-down to main table.
  function tableHref(p: InfluencePoint): string {
    return `${base}/?q=${encodeURIComponent(p.name)}`;
  }

  // --- Tick generation ---------------------------------------------------

  function ticks(max: number): number[] {
    const m = Math.ceil(max);
    if (m <= 5) return Array.from({ length: m + 1 }, (_, i) => i);
    // Stride to keep ~6 ticks total.
    const stride = Math.max(1, Math.ceil(m / 6));
    const out: number[] = [];
    for (let v = 0; v <= m; v += stride) out.push(v);
    return out;
  }
  const xTicks = $derived(ticks(xMax - 0.5));
  const yTicks = $derived(ticks(yMax - 0.5));

  // Quadrant cutoff line positions (in svg coords).
  const xCutPx = $derived(projX(citesCut));
  const yCutPx = $derived(projY(integCut));

  // Sort points so annotated ones render last (above the pile).
  const renderOrder = $derived(
    [...points].sort((a, b) => {
      const aa = annotated.has(a.id) ? 1 : 0;
      const bb = annotated.has(b.id) ? 1 : 0;
      return aa - bb;
    })
  );

  // Legend: top-N sections by point count.
  const sectionLegend = $derived.by(() => {
    const counts = new Map<string, number>();
    for (const p of points) counts.set(p.section, (counts.get(p.section) ?? 0) + 1);
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([section, n]) => ({ section, n, color: sectionColor(section) }));
  });

  function quadrantLabel(q: Quadrant): string {
    switch (q) {
      case 'both':
        return 'Both (cited + adopted)';
      case 'engineering':
        return 'Engineering wins (adopted, not cited)';
      case 'orphan':
        return 'Research orphans (cited, not adopted)';
      case 'tail':
        return 'Long tail';
    }
  }
</script>

<svelte:head>
  <title>Influence vs adoption · Memory Landscape</title>
</svelte:head>

<main class="page">
  <header class="head">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Influence vs adoption</h1>
    <p class="lede">
      Every record in the catalog plotted on two axes from the citation graph:
      <strong>inbound cites</strong> (academic influence) against
      <strong>inbound integrations</strong> (commercial adoption — both
      <code>integrates-with</code> and <code>built-on</code> edges count).
      Cutoffs are the non-zero median on each axis ({citesCut} cites,
      {integCut} integrations). The four named quadrants are the patterns
      worth looking at — the bottom-left pile is everything that hasn't yet
      accumulated graph centrality, which is most of the corpus.
    </p>
  </header>

  <section class="chart-wrap">
    <svg
      viewBox="0 0 {W} {H}"
      role="img"
      aria-label="Scatter plot of inbound citations vs inbound integrations per record"
      class="chart"
    >
      <!-- Quadrant background tints -->
      <rect
        x={xCutPx}
        y={PAD_T}
        width={W - PAD_R - xCutPx}
        height={yCutPx - PAD_T}
        fill="#d4845f"
        fill-opacity="0.06"
      />
      <rect
        x={PAD_L}
        y={PAD_T}
        width={xCutPx - PAD_L}
        height={yCutPx - PAD_T}
        fill="#5fa8d4"
        fill-opacity="0.05"
      />
      <rect
        x={xCutPx}
        y={yCutPx}
        width={W - PAD_R - xCutPx}
        height={H - PAD_B - yCutPx}
        fill="#9b6fd4"
        fill-opacity="0.05"
      />
      <rect
        x={PAD_L}
        y={yCutPx}
        width={xCutPx - PAD_L}
        height={H - PAD_B - yCutPx}
        fill="#222"
        fill-opacity="0.25"
      />

      <!-- Quadrant cutoff lines -->
      <line
        x1={xCutPx}
        y1={PAD_T}
        x2={xCutPx}
        y2={H - PAD_B}
        stroke="#555"
        stroke-dasharray="4 4"
        stroke-width="1"
      />
      <line
        x1={PAD_L}
        y1={yCutPx}
        x2={W - PAD_R}
        y2={yCutPx}
        stroke="#555"
        stroke-dasharray="4 4"
        stroke-width="1"
      />

      <!-- Quadrant corner labels -->
      <text x={W - PAD_R - 8} y={PAD_T + 14} text-anchor="end" class="qlabel hi"
        >Both</text
      >
      <text x={PAD_L + 8} y={PAD_T + 14} text-anchor="start" class="qlabel"
        >Engineering wins</text
      >
      <text
        x={W - PAD_R - 8}
        y={H - PAD_B - 6}
        text-anchor="end"
        class="qlabel"
        >Research orphans</text
      >
      <text x={PAD_L + 8} y={H - PAD_B - 6} text-anchor="start" class="qlabel"
        >Long tail</text
      >

      <!-- Axes -->
      <line
        x1={PAD_L}
        y1={H - PAD_B}
        x2={W - PAD_R}
        y2={H - PAD_B}
        stroke="#666"
        stroke-width="1"
      />
      <line
        x1={PAD_L}
        y1={PAD_T}
        x2={PAD_L}
        y2={H - PAD_B}
        stroke="#666"
        stroke-width="1"
      />

      <!-- X ticks -->
      {#each xTicks as t}
        <g>
          <line
            x1={projX(t)}
            y1={H - PAD_B}
            x2={projX(t)}
            y2={H - PAD_B + 4}
            stroke="#666"
          />
          <text
            x={projX(t)}
            y={H - PAD_B + 18}
            text-anchor="middle"
            class="tick">{t}</text
          >
        </g>
      {/each}
      <!-- Y ticks -->
      {#each yTicks as t}
        <g>
          <line
            x1={PAD_L - 4}
            y1={projY(t)}
            x2={PAD_L}
            y2={projY(t)}
            stroke="#666"
          />
          <text
            x={PAD_L - 8}
            y={projY(t) + 4}
            text-anchor="end"
            class="tick">{t}</text
          >
        </g>
      {/each}

      <!-- Axis titles -->
      <text
        x={(PAD_L + W - PAD_R) / 2}
        y={H - 12}
        text-anchor="middle"
        class="axis-title">Inbound cites (academic influence)</text
      >
      <text
        transform="translate(16 {(PAD_T + H - PAD_B) / 2}) rotate(-90)"
        text-anchor="middle"
        class="axis-title"
        >Inbound integrations + built-on (commercial adoption)</text
      >

      <!-- Points -->
      {#each renderOrder as p (p.id)}
        {@const pos = jittered(p)}
        {@const isAnnotated = annotated.has(p.id)}
        {@const isHover = hoverId === p.id}
        <a href={tableHref(p)} aria-label="Open {p.name} in the main table">
          <circle
            cx={pos.x}
            cy={pos.y}
            r={tierRadius(p.tier)}
            fill={sectionColor(p.section)}
            fill-opacity={p.citesIn + p.integrationsIn === 0 ? 0.35 : 0.85}
            stroke={isHover ? '#fff' : '#111'}
            stroke-width={isHover ? 1.5 : 0.5}
            class="pt"
            role="button"
            tabindex="0"
            aria-label="{p.name}: {p.citesIn} cites in, {p.integrationsIn} integrations in"
            onmouseenter={(ev) => onPointEnter(p, ev)}
            onmousemove={(ev) => onPointEnter(p, ev)}
            onmouseleave={onPointLeave}
            onfocus={(ev) => onPointEnter(p, ev as unknown as MouseEvent)}
            onblur={onPointLeave}
          />
        </a>
        {#if isAnnotated}
          <text
            x={pos.x + tierRadius(p.tier) + 3}
            y={pos.y + 3}
            class="anno"
            pointer-events="none">{p.name}</text
          >
        {/if}
      {/each}
    </svg>

    {#if hoverPoint}
      <div
        class="tooltip"
        style="left:{hoverX + 14}px; top:{hoverY + 14}px"
        role="status"
      >
        <strong>{hoverPoint.name}</strong>
        <span class="t-tier">T{hoverPoint.tier}</span>
        <div class="t-section">{hoverPoint.section}</div>
        <div class="t-nums">
          <span>cites in: <b>{hoverPoint.citesIn}</b></span>
          <span>integrations in: <b>{hoverPoint.integrationsIn}</b></span>
        </div>
        <div class="t-hint">click to open in table →</div>
      </div>
    {/if}
  </section>

  <section class="below">
    <article class="counts">
      <h2>Quadrant counts</h2>
      <ul>
        <li>
          <span class="dot both"></span>
          {quadrantLabel('both')}: <b>{counts.both}</b>
        </li>
        <li>
          <span class="dot eng"></span>
          {quadrantLabel('engineering')}: <b>{counts.engineering}</b>
        </li>
        <li>
          <span class="dot orph"></span>
          {quadrantLabel('orphan')}: <b>{counts.orphan}</b>
        </li>
        <li>
          <span class="dot tail"></span>
          {quadrantLabel('tail')}: <b>{counts.tail}</b>
        </li>
      </ul>
      <p class="note">
        Cutoffs: cites &gt; <b>{citesCut}</b>, integrations &gt;
        <b>{integCut}</b> (non-zero medians on each axis).
      </p>
    </article>

    <article class="legend">
      <h2>Section colour key (top {sectionLegend.length})</h2>
      <ul>
        {#each sectionLegend as s (s.section)}
          <li>
            <span class="dot" style="background:{s.color}"></span>
            {s.section}
            <span class="muted">({s.n})</span>
          </li>
        {/each}
      </ul>
      <p class="note">
        Marker size encodes tier: T1 largest (7px), T5 smallest (3px).
        Faded markers are records with zero inbound edges of either type
        (the bulk of the long tail).
      </p>
    </article>
  </section>

  <footer class="foot">
    <a href="{base}/analyses">← All analyses</a>
    <span class="muted"
      >{points.length} records plotted · {data.edges.length} edges sourced
      from the in-catalog citation graph</span
    >
  </footer>
</main>

<style>
  .page {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 16px 64px;
    color: #ddd;
  }

  .head {
    margin-bottom: 20px;
  }
  .crumb {
    margin: 0 0 8px;
    font-size: 0.85rem;
  }
  .crumb a {
    color: #aaa;
    text-decoration: none;
  }
  .crumb a:hover {
    color: #d4845f;
  }
  .head h1 {
    margin: 0 0 12px;
    font-size: 1.6rem;
    color: #e8e8e8;
    letter-spacing: -0.01em;
  }
  .lede {
    margin: 0;
    max-width: 780px;
    color: #bbb;
    line-height: 1.55;
  }
  .lede code {
    background: #1c1c1c;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    padding: 0 4px;
    font-size: 0.85em;
    color: #d4b59f;
  }

  .chart-wrap {
    position: relative;
    background: #131313;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    margin: 16px 0;
    padding: 8px;
  }

  .chart {
    width: 100%;
    height: auto;
    display: block;
  }

  .qlabel {
    fill: #888;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .qlabel.hi {
    fill: #d4845f;
  }
  .tick {
    fill: #888;
    font-size: 10px;
  }
  .axis-title {
    fill: #aaa;
    font-size: 11px;
  }
  .pt {
    cursor: pointer;
    transition: stroke-width 80ms ease;
  }
  .pt:hover {
    stroke: #fff;
    stroke-width: 1.5;
  }
  .anno {
    fill: #ddd;
    font-size: 10px;
    pointer-events: none;
    paint-order: stroke;
    stroke: #131313;
    stroke-width: 2.5;
    stroke-linejoin: round;
  }

  .tooltip {
    position: absolute;
    pointer-events: none;
    background: #1a1a1a;
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 0.85rem;
    color: #ddd;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    max-width: 260px;
    z-index: 5;
  }
  .t-tier {
    background: #2a2a2a;
    color: #d4845f;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.75rem;
    margin-left: 6px;
  }
  .t-section {
    color: #999;
    font-size: 0.78rem;
    margin-top: 2px;
  }
  .t-nums {
    margin-top: 4px;
    display: flex;
    gap: 12px;
    font-size: 0.8rem;
  }
  .t-nums b {
    color: #e8e8e8;
  }
  .t-hint {
    margin-top: 4px;
    color: #777;
    font-size: 0.72rem;
    font-style: italic;
  }

  .below {
    display: grid;
    grid-template-columns: minmax(260px, 1fr) minmax(260px, 2fr);
    gap: 16px;
    margin-bottom: 16px;
  }
  .counts,
  .legend {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 14px 18px;
  }
  .counts h2,
  .legend h2 {
    margin: 0 0 8px;
    font-size: 0.95rem;
    color: #e8e8e8;
    font-weight: 600;
  }
  .counts ul,
  .legend ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .counts li,
  .legend li {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 0;
    font-size: 0.88rem;
    color: #ccc;
  }
  .counts b {
    color: #e8e8e8;
  }
  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #555;
    flex-shrink: 0;
  }
  .dot.both {
    background: #d4845f;
  }
  .dot.eng {
    background: #5fa8d4;
  }
  .dot.orph {
    background: #9b6fd4;
  }
  .dot.tail {
    background: #555;
  }
  .note {
    margin: 8px 0 0;
    color: #888;
    font-size: 0.78rem;
    line-height: 1.45;
  }
  .muted {
    color: #888;
  }

  .foot {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #2a2a2a;
    padding-top: 12px;
    margin-top: 12px;
    font-size: 0.85rem;
  }
  .foot a {
    color: #aaa;
    text-decoration: none;
  }
  .foot a:hover {
    color: #d4845f;
  }

  @media (max-width: 720px) {
    .below {
      grid-template-columns: 1fr;
    }
  }
</style>
