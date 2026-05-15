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
  //
  // Round-7 upgrade additions (this file):
  //   - Narrative header + methodology callout (visible by default).
  //   - Tier + section filter dropdowns. Re-render scatter + counts.
  //   - Hex-bin density underlay at low values (the long tail) AND keep
  //     the existing radial-jitter for addressability of individual marks.
  //     Documented as the "density + jitter" compromise in DECISIONS.md.
  //   - Median lines made visible with numeric labels.
  //   - Per-quadrant "so what" cards below the chart.
  //   - Each tooltip / card row links out to the main table, survivorship,
  //     and forecast views.

  import { base } from '$app/paths';
  import type { Edge, LandscapeRecord, Tier } from '$lib/types';
  import {
    buildPoints,
    classifyQuadrant,
    filterPoints,
    HEADLINE_FINDING,
    hexBin,
    hexPolygonPoints,
    nonZeroMedian,
    quadrantCounts,
    QUADRANT_COPY,
    sectionColor,
    tierRadius,
    topInQuadrant,
    type InfluencePoint,
    type Quadrant
  } from '$lib/analyses/influence';

  let { data }: { data: { records: LandscapeRecord[]; edges: Edge[] } } =
    $props();

  const allPoints = $derived(buildPoints(data.records, data.edges));

  // Filter state. Empty set = "all included" by convention (see filterPoints).
  // We hydrate the available section list from the data so the dropdown only
  // ever offers sections that actually have at least one record.
  const allSections = $derived(
    [...new Set(allPoints.map((p) => p.section))].sort()
  );
  const ALL_TIERS: Tier[] = [1, 2, 3, 4, 5];

  let tierFilter = $state<Set<Tier>>(new Set());
  let sectionFilter = $state<Set<string>>(new Set());

  function toggleTier(t: Tier) {
    const next = new Set(tierFilter);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    tierFilter = next;
  }
  function toggleSection(s: string) {
    const next = new Set(sectionFilter);
    if (next.has(s)) next.delete(s);
    else next.add(s);
    sectionFilter = next;
  }
  function clearFilters() {
    tierFilter = new Set();
    sectionFilter = new Set();
  }

  const points = $derived(filterPoints(allPoints, tierFilter, sectionFilter));

  // Cutoffs: non-zero medians of the *filtered* set, so when the user narrows
  // to e.g. Tier 1 only, the quadrant boundaries adapt. Falls back to global
  // medians if the filtered set is too small to compute (avoids a div-by-zero
  // visual where both medians collapse to 0 and every point lands in "Both").
  const citesCut = $derived(
    points.length >= 8
      ? nonZeroMedian(points.map((p) => p.citesIn))
      : nonZeroMedian(allPoints.map((p) => p.citesIn))
  );
  const integCut = $derived(
    points.length >= 8
      ? nonZeroMedian(points.map((p) => p.integrationsIn))
      : nonZeroMedian(allPoints.map((p) => p.integrationsIn))
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
      )
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

  // --- Hex-bin density underlay for the long tail ------------------------
  //
  // We bin only the tail-region points (those at the origin pile) in screen
  // space, then render translucent hex polygons under the markers. This
  // gives the reader an at-a-glance sense of "this corner is dense" without
  // the marker overlap eating the signal.
  //
  // Bins ONLY the tail because hex-binning the high-axis outliers would
  // wrap big hexes around lone points and look misleading.

  const HEX_R = 14; // pixels; chosen so ~8-12 hexes span the tail region

  const tailHexes = $derived.by(() => {
    const tail = points.filter(
      (p) => classifyQuadrant(p, citesCut, integCut) === 'tail'
    );
    const projected = tail.map(jittered);
    return hexBin(projected, HEX_R);
  });

  const hexMaxCount = $derived(
    tailHexes.reduce((m, h) => Math.max(m, h.count), 0)
  );

  function hexOpacity(count: number): number {
    if (hexMaxCount === 0) return 0;
    // Floor opacity so a 1-point hex is still faintly visible.
    return 0.06 + 0.34 * (count / hexMaxCount);
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

  // Drill-down links. We deliberately route through the main table query
  // param so the table opens scoped to that name; survivorship + forecast
  // use deep anchors that those views own.
  function tableHref(p: InfluencePoint): string {
    return `${base}/?q=${encodeURIComponent(p.name)}`;
  }
  function survivorshipHref(p: InfluencePoint): string {
    // Spec asks for `#<id>` anchors here, but the survivorship view doesn't
    // emit per-record DOM ids yet (would fail SvelteKit's link-checker at
    // prerender). Land on the view + open the table scoped to the system so
    // the reader can pick up survivorship context for that record without a
    // broken anchor. When survivorship grows per-record anchors this can
    // upgrade in-place. p is intentionally unused for now.
    void p;
    return `${base}/analyses/survivorship`;
  }
  function forecastHref(): string {
    return `${base}/analyses/forecast`;
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
    const c = new Map<string, number>();
    for (const p of points) c.set(p.section, (c.get(p.section) ?? 0) + 1);
    return [...c.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([section, n]) => ({ section, n, color: sectionColor(section) }));
  });

  // For the per-quadrant cards: top 3 systems by combined score, surfaced
  // as drill-down chips. We want the reader to be able to act on the card.
  function topThreeIn(q: Quadrant): InfluencePoint[] {
    return topInQuadrant(points, citesCut, integCut, q, 3);
  }

  function quadrantClass(q: Quadrant): string {
    return `quad q-${q}`;
  }
</script>

<svelte:head>
  <title>Influence vs adoption · Memory Landscape</title>
</svelte:head>

<main class="page">
  <header class="head">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Influence vs adoption</h1>

    <!-- Narrative header: 3-4 sentence "what you're looking at". -->
    <section class="narrative" aria-label="What you're looking at">
      <h2>What you're looking at</h2>
      <p>
        Every record in the catalog plotted on two axes from the in-catalog
        citation graph. The <strong>X axis</strong> counts inbound
        <code>cites</code> edges (academic influence — how many other records
        cite this one); the <strong>Y axis</strong> counts inbound
        <code>built-on</code> + <code>integrates-with</code> edges (commercial
        adoption — how many other records build on or integrate against this
        one). The chart is sliced into four named quadrants by the
        non-zero medians on each axis. Hover any point for a third lens —
        <strong>inbound <code>runtime-dependency</code> edges</strong> (issue
        #44) — answering "who breaks if this record goes down". Headline
        finding: <strong>{HEADLINE_FINDING}</strong>
      </p>
    </section>

    <!-- Methodology callout: visible by default, bulleted. -->
    <aside class="methodology" aria-label="Methodology">
      <h2>How this chart is computed</h2>
      <ul>
        <li>
          <b>Citation count</b> is the number of inbound <code>cites</code>
          edges in <code>landscape.edges.json</code>. Edges are sourced from
          Semantic Scholar with <code>isInfluential = true</code> at extraction
          time, plus hand-curated edges for products with no S2 record.
        </li>
        <li>
          <b>Integration count</b> is the number of inbound edges of type
          <code>built-on</code> or <code>integrates-with</code>. Both edge
          types collapse to a single Y value because the distinction is fuzzy
          at the catalog level — they both mean "another record in this
          corpus depends on this one".
        </li>
        <li>
          <b>Runtime-dependency count</b> (issue #44; visible per-point in
          the tooltip) is the number of inbound <code>runtime-dependency</code>
          edges — records that <em>break if this one goes down</em>. It is
          intentionally <em>not</em> folded into the Y axis because
          citation-influence ("who cites this paper") and
          dependency-influence ("who breaks without this substrate") answer
          different questions. The two-axis scatter shows the academic vs
          commercial-integration tension; the tooltip exposes a third lens:
          the production-runtime graph. A record can be a substrate (high
          runtime-deps) without being an integration target (low built-on)
          when downstreams call its API rather than embedding it.
        </li>
        <li>
          <b>Marker size</b> encodes tier: T1 = 7px, T2 = 6px … T5 = 3px
          (linear; tiers are an ordinal 1-5 with no log meaning).
          <b>Marker colour</b> encodes the record's primary section.
        </li>
        <li>
          <b>Cutoffs</b> are the non-zero median on each axis. Currently:
          <b>{citesCut}</b> cites, <b>{integCut}</b> integrations. We use the
          non-zero subset because most records sit at the origin and the
          population median would always be 0 — that collapses every quadrant
          boundary onto the axis. Strict greater-than: a point sitting
          exactly on a cutoff stays in the lower quadrant.
        </li>
        <li>
          <b>Long tail rendering.</b> Around 80% of records have zero inbound
          edges on both axes. We apply a deterministic radial jitter (hash of
          record id) so individual marks remain hoverable, and overlay a
          translucent hex-bin density grid so the reader can still read the
          shape of the cloud. See <code>docs/DECISIONS.md</code> for the
          density-vs-jitter rationale.
        </li>
      </ul>
    </aside>
  </header>

  <!-- Filters: tier multi-select + section multi-select. -->
  <section class="filters" aria-label="Filters">
    <div class="filter-row">
      <span class="filter-label">Tier</span>
      <div class="chips">
        {#each ALL_TIERS as t}
          <button
            type="button"
            class="chip"
            class:on={tierFilter.size === 0 || tierFilter.has(t)}
            onclick={() => toggleTier(t)}
            aria-pressed={tierFilter.size === 0 || tierFilter.has(t)}
          >
            T{t}
          </button>
        {/each}
      </div>
    </div>

    <div class="filter-row">
      <span class="filter-label">Section</span>
      <div class="chips chips-scroll">
        {#each allSections as s}
          <button
            type="button"
            class="chip"
            class:on={sectionFilter.size === 0 || sectionFilter.has(s)}
            onclick={() => toggleSection(s)}
            aria-pressed={sectionFilter.size === 0 || sectionFilter.has(s)}
          >
            {s}
          </button>
        {/each}
      </div>
    </div>

    <div class="filter-row">
      <button type="button" class="clear" onclick={clearFilters}
        >Reset filters</button
      >
      <span class="muted small">
        Showing <b>{points.length}</b> of {allPoints.length} records.
      </span>
    </div>
  </section>

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

      <!-- Hex-bin density underlay over the long-tail region. Rendered before
           the markers so individual circles stay on top. -->
      {#each tailHexes as h, i (i)}
        <polygon
          points={hexPolygonPoints(h.cx, h.cy, HEX_R)}
          fill="#d4845f"
          fill-opacity={hexOpacity(h.count)}
          stroke="#d4845f"
          stroke-opacity="0.18"
          stroke-width="0.5"
        />
      {/each}

      <!-- Quadrant cutoff lines (annotated with their numeric values) -->
      <line
        x1={xCutPx}
        y1={PAD_T}
        x2={xCutPx}
        y2={H - PAD_B}
        stroke="#888"
        stroke-dasharray="4 4"
        stroke-width="1"
      />
      <line
        x1={PAD_L}
        y1={yCutPx}
        x2={W - PAD_R}
        y2={yCutPx}
        stroke="#888"
        stroke-dasharray="4 4"
        stroke-width="1"
      />
      <text
        x={xCutPx + 4}
        y={PAD_T + 12}
        class="median-label"
        text-anchor="start"
        >cites median = {citesCut}</text
      >
      <text
        x={W - PAD_R - 4}
        y={yCutPx - 4}
        class="median-label"
        text-anchor="end"
        >integrations median = {integCut}</text
      >

      <!-- Quadrant corner labels -->
      <text x={W - PAD_R - 8} y={PAD_T + 28} text-anchor="end" class="qlabel hi"
        >Both</text
      >
      <text x={PAD_L + 8} y={PAD_T + 28} text-anchor="start" class="qlabel"
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
            aria-label="{p.name}: {p.citesIn} cites in, {p.integrationsIn} integrations in, {p.runtimeDepsIn} runtime-deps in"
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
          <span title="Inbound runtime-dependency edges — records that break if this one goes down (issue #44)">
            runtime-deps in: <b>{hoverPoint.runtimeDepsIn}</b>
          </span>
        </div>
        <div class="t-links">
          <a href={tableHref(hoverPoint)}>table →</a>
          <a href={survivorshipHref(hoverPoint)}>survivorship →</a>
          <a href={forecastHref()}>forecast →</a>
        </div>
      </div>
    {/if}
  </section>

  <!-- Per-quadrant "so what" cards. -->
  <section class="quad-cards" aria-label="Quadrant interpretation">
    {#each ['both', 'engineering', 'orphan', 'tail'] as q (q)}
      {@const copy = QUADRANT_COPY[q as Quadrant]}
      {@const n = counts[q as Quadrant]}
      {@const top = topThreeIn(q as Quadrant)}
      <article class={quadrantClass(q as Quadrant)}>
        <header class="quad-head">
          <h3>{copy.name}</h3>
          <span class="quad-count">{n}</span>
        </header>
        <p class="quad-interpretation">{copy.interpretation}</p>
        <p class="quad-sowhat"><b>So what.</b> {copy.soWhat}</p>
        {#if top.length > 0}
          <div class="quad-top">
            <span class="quad-top-label">Top:</span>
            {#each top as p (p.id)}
              <span class="quad-chip">
                <a href={tableHref(p)}>{p.name}</a>
                <span class="muted small"
                  >· {p.citesIn}c / {p.integrationsIn}i</span
                >
                <a class="mini" href={survivorshipHref(p)} title="Survivorship"
                  >S</a
                >
                <a class="mini" href={forecastHref()} title="Forecast">F</a>
              </span>
            {/each}
          </div>
        {/if}
      </article>
    {/each}
  </section>

  <section class="below">
    <article class="counts">
      <h2>Quadrant counts</h2>
      <ul>
        <li>
          <span class="dot both"></span>
          {QUADRANT_COPY.both.name}: <b>{counts.both}</b>
        </li>
        <li>
          <span class="dot eng"></span>
          {QUADRANT_COPY.engineering.name}: <b>{counts.engineering}</b>
        </li>
        <li>
          <span class="dot orph"></span>
          {QUADRANT_COPY.orphan.name}: <b>{counts.orphan}</b>
        </li>
        <li>
          <span class="dot tail"></span>
          {QUADRANT_COPY.tail.name}: <b>{counts.tail}</b>
        </li>
      </ul>
      <p class="note">
        Cutoffs: cites &gt; <b>{citesCut}</b>, integrations &gt;
        <b>{integCut}</b> (non-zero medians on each axis, recomputed against
        the current filter).
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
        (the bulk of the long tail). Translucent orange hexes are the
        density underlay — darker = more records binned into that cell.
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

  .narrative,
  .methodology {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-left: 3px solid #d4845f;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 12px 0;
  }
  .narrative h2,
  .methodology h2 {
    margin: 0 0 6px;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #d4845f;
    font-weight: 600;
  }
  .narrative p {
    margin: 0;
    line-height: 1.55;
    color: #cdcdcd;
  }
  .methodology {
    border-left-color: #5fa8d4;
  }
  .methodology h2 {
    color: #5fa8d4;
  }
  .methodology ul {
    margin: 0;
    padding-left: 1.1em;
    color: #bbb;
    line-height: 1.55;
    font-size: 0.92rem;
  }
  .methodology li {
    margin-bottom: 4px;
  }
  .methodology code,
  .narrative code {
    background: #1c1c1c;
    border: 1px solid #2a2a2a;
    border-radius: 3px;
    padding: 0 4px;
    font-size: 0.85em;
    color: #d4b59f;
  }

  .filters {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 16px 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .filter-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  .filter-label {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    min-width: 56px;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chips-scroll {
    max-height: 96px;
    overflow-y: auto;
    flex: 1 1 auto;
  }
  .chip {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    color: #999;
    border-radius: 999px;
    padding: 3px 10px;
    font-size: 0.78rem;
    cursor: pointer;
    transition:
      background 80ms ease,
      border-color 80ms ease,
      color 80ms ease;
  }
  .chip:hover {
    border-color: #444;
    color: #ddd;
  }
  .chip.on {
    background: #2a1f17;
    border-color: #d4845f;
    color: #e8c4ad;
  }
  .clear {
    background: transparent;
    border: 1px solid #444;
    color: #aaa;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 0.78rem;
    cursor: pointer;
  }
  .clear:hover {
    border-color: #d4845f;
    color: #d4845f;
  }
  .small {
    font-size: 0.78rem;
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
  .median-label {
    fill: #aaa;
    font-size: 10px;
    font-style: italic;
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
    pointer-events: auto;
    background: #1a1a1a;
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 0.85rem;
    color: #ddd;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    max-width: 280px;
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
  .t-links {
    margin-top: 6px;
    display: flex;
    gap: 8px;
    font-size: 0.78rem;
  }
  .t-links a {
    color: #d4845f;
    text-decoration: none;
  }
  .t-links a:hover {
    text-decoration: underline;
  }

  .quad-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
    margin: 16px 0;
  }
  .quad {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 14px 16px;
    border-top: 3px solid #555;
  }
  .quad.q-both {
    border-top-color: #d4845f;
  }
  .quad.q-engineering {
    border-top-color: #5fa8d4;
  }
  .quad.q-orphan {
    border-top-color: #9b6fd4;
  }
  .quad.q-tail {
    border-top-color: #555;
  }
  .quad-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
  }
  .quad-head h3 {
    margin: 0;
    font-size: 0.98rem;
    color: #e8e8e8;
    font-weight: 600;
  }
  .quad-count {
    color: #d4845f;
    font-weight: 700;
    font-size: 1.05rem;
  }
  .quad-interpretation {
    margin: 0 0 8px;
    color: #bbb;
    font-size: 0.88rem;
    line-height: 1.5;
  }
  .quad-sowhat {
    margin: 0 0 10px;
    color: #cdcdcd;
    font-size: 0.88rem;
    line-height: 1.5;
  }
  .quad-sowhat b {
    color: #d4845f;
  }
  .quad-top {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    border-top: 1px dashed #2a2a2a;
    padding-top: 8px;
  }
  .quad-top-label {
    font-size: 0.75rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .quad-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 0.8rem;
  }
  .quad-chip a {
    color: #cdcdcd;
    text-decoration: none;
  }
  .quad-chip a:hover {
    color: #d4845f;
  }
  .quad-chip .mini {
    font-size: 0.7rem;
    color: #888;
    border: 1px solid #333;
    border-radius: 3px;
    padding: 0 4px;
    margin-left: 2px;
  }
  .quad-chip .mini:hover {
    color: #d4845f;
    border-color: #d4845f;
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
