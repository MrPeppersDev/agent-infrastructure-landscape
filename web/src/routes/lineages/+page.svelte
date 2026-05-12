<script lang="ts">
  // Lineage timeline view (issue #17). Wikipedia-style "history of X"
  // diagram: X-axis is time (year-quarter), Y-axis is one row per
  // lineage family. Each node is a system; edges between nodes are
  // structural-descent edges (built-on, extends, forks, succeeds, plus
  // influential cites).
  //
  // Pure SVG — matches the timeline / leaderboards / sections views and
  // avoids pulling in a charting library for what is, structurally,
  // ~70 nodes across ~8 tracks.
  //
  // The lineage detection itself lives in $lib/lineages.ts (pure
  // functions, no Svelte deps). This file is presentation only.

  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import type { Edge, LandscapeRecord } from '$lib/types';
  import {
    detectLineages,
    plotDate,
    type Lineage
  } from '$lib/lineages';
  import { TIER_COLOURS } from '$lib/timeline';

  let {
    data
  }: { data: { records: LandscapeRecord[]; edges: Edge[] } } = $props();

  // --- Detection ---------------------------------------------------------
  const lineages = $derived<Lineage[]>(
    detectLineages(data.records, data.edges, { topN: 8, minSize: 3 })
  );

  const byId = $derived<Map<string, LandscapeRecord>>(
    new Map(data.records.map((r) => [r.id, r]))
  );

  // --- Date range across all plotted nodes -------------------------------
  //
  // We project the X-axis from min(year-quarter) to max(year-quarter) so
  // every lineage shares one shared time-line. Year-only dates land in Q1,
  // matching the timeline view's convention.
  const timeRange = $derived.by(() => {
    let min = Infinity;
    let max = -Infinity;
    for (const l of lineages) {
      for (const id of l.members) {
        const r = byId.get(id);
        if (!r) continue;
        const d = plotDate(r);
        if (!d) continue;
        if (d.t < min) min = d.t;
        if (d.t > max) max = d.t;
      }
    }
    if (!isFinite(min) || !isFinite(max)) return { min: 2015, max: 2026 };
    // Pad each side by a quarter so anchor labels don't get clipped.
    return { min: min - 0.25, max: max + 0.25 };
  });

  // --- Plotted nodes -----------------------------------------------------
  //
  // For each lineage we materialise a list of (record, x, y) tuples so the
  // edge-rendering pass can look up endpoints by id. Records without a
  // parseable created date are dropped from the plot — they're rare enough
  // (~4% of catalog per timeline.ts) that they don't change the story.
  type PlottedNode = {
    id: string;
    name: string;
    tier: number;
    x: number;
    y: number;
    t: number;
    claim: string;
  };
  type PlottedLineage = {
    lineage: Lineage;
    rowIndex: number;
    nodes: PlottedNode[];
  };

  // --- SVG geometry ------------------------------------------------------
  const ROW_H = 64;
  const PAD_LEFT = 200; // room for lineage name labels
  const PAD_RIGHT = 32;
  const PAD_TOP = 48;
  const PAD_BOTTOM = 48;
  const NODE_R = 6;
  const MIN_INNER_W = 880;

  const innerW = $derived.by(() => {
    // Scale inner width to span ~80px per year so older lineages have
    // breathing room. Clamp to a sane minimum so the chart never crushes.
    const years = Math.max(1, timeRange.max - timeRange.min);
    return Math.max(MIN_INNER_W, Math.round(years * 80));
  });
  const innerH = $derived(Math.max(ROW_H, lineages.length * ROW_H));
  const totalW = $derived(PAD_LEFT + innerW + PAD_RIGHT);
  const totalH = $derived(PAD_TOP + innerH + PAD_BOTTOM);

  function xScale(t: number): number {
    const range = timeRange.max - timeRange.min;
    if (range <= 0) return PAD_LEFT;
    return PAD_LEFT + ((t - timeRange.min) / range) * innerW;
  }

  function yScale(rowIndex: number): number {
    return PAD_TOP + rowIndex * ROW_H + ROW_H / 2;
  }

  const plotted = $derived<PlottedLineage[]>(
    lineages.map((l, rowIndex) => {
      const nodes: PlottedNode[] = [];
      for (const id of l.members) {
        const r = byId.get(id);
        if (!r) continue;
        const d = plotDate(r);
        if (!d) continue;
        nodes.push({
          id,
          name: r.name,
          tier: r.tier,
          x: xScale(d.t),
          y: yScale(rowIndex),
          t: d.t,
          claim: r.cells.claims?.value ?? r.cells.desc?.value ?? ''
        });
      }
      // Sort left-to-right so adjacent labels stagger predictably.
      nodes.sort((a, b) => a.x - b.x);
      return { lineage: l, rowIndex, nodes };
    })
  );

  // --- X-axis ticks ------------------------------------------------------
  const xTicks = $derived.by(() => {
    const ticks: { t: number; label: string }[] = [];
    const startYear = Math.floor(timeRange.min);
    const endYear = Math.ceil(timeRange.max);
    for (let y = startYear; y <= endYear; y++) {
      ticks.push({ t: y, label: String(y) });
    }
    return ticks;
  });

  // --- Edge rendering ----------------------------------------------------
  //
  // We resolve each edge to (sourceNode, targetNode) coords. If either
  // endpoint isn't plotted (no parseable date, or different lineage) we
  // skip the edge — same-lineage cross-track edges are rare in our data
  // and would crowd the diagram with diagonals across the whole chart.
  type PlottedEdge = {
    edge: Edge;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    sameRow: boolean;
  };

  const plottedEdges = $derived.by<PlottedEdge[]>(() => {
    const out: PlottedEdge[] = [];
    // Build a fast lookup of node coords keyed by record id within each
    // lineage row.
    const idToCoords = new Map<string, { x: number; y: number }>();
    for (const pl of plotted) {
      for (const n of pl.nodes) {
        // First lineage to plot a given id wins; curated seeds are
        // emitted first so they take precedence in cross-track cases.
        if (!idToCoords.has(n.id)) {
          idToCoords.set(n.id, { x: n.x, y: n.y });
        }
      }
    }
    for (const pl of plotted) {
      for (const e of pl.lineage.edges) {
        const s = idToCoords.get(e.source);
        const t = idToCoords.get(e.target);
        if (!s || !t) continue;
        out.push({
          edge: e,
          x1: s.x,
          y1: s.y,
          x2: t.x,
          y2: t.y,
          sameRow: s.y === t.y
        });
      }
    }
    return out;
  });

  // --- Hover state -------------------------------------------------------
  let hoverNode = $state<PlottedNode | null>(null);
  let hoverEdge = $state<PlottedEdge | null>(null);
  let hoverX = $state(0);
  let hoverY = $state(0);

  function onNodeEnter(n: PlottedNode, ev: PointerEvent) {
    hoverNode = n;
    hoverEdge = null;
    hoverX = ev.clientX;
    hoverY = ev.clientY;
  }
  function onNodeMove(ev: PointerEvent) {
    hoverX = ev.clientX;
    hoverY = ev.clientY;
  }
  function onNodeLeave() {
    hoverNode = null;
  }
  function onEdgeEnter(e: PlottedEdge, ev: PointerEvent) {
    hoverEdge = e;
    hoverNode = null;
    hoverX = ev.clientX;
    hoverY = ev.clientY;
  }
  function onEdgeLeave() {
    hoverEdge = null;
  }

  // --- Click → drill into table -----------------------------------------
  function onNodeClick(n: PlottedNode) {
    // Send the user to / with q=<name> — the search bar handles
    // free-text matching across name + desc + claims (see SearchBox).
    // We URL-encode the name so quotes / spaces survive.
    const params = new URLSearchParams();
    params.set('q', n.name);
    goto(`${base}/?${params.toString()}`);
  }

  // Bezier control points for an inter-track edge — gives the diagram
  // a "tree-of-life" feel rather than crossing straight lines.
  function bezierPath(e: PlottedEdge): string {
    if (e.sameRow) {
      // Slight arc above the row for same-row edges so multiple edges
      // between siblings don't all overlap on the row baseline.
      const mx = (e.x1 + e.x2) / 2;
      const my = e.y1 - 14;
      return `M ${e.x1},${e.y1} Q ${mx},${my} ${e.x2},${e.y2}`;
    }
    const dx = (e.x2 - e.x1) * 0.5;
    return `M ${e.x1},${e.y1} C ${e.x1 + dx},${e.y1} ${e.x2 - dx},${e.y2} ${e.x2},${e.y2}`;
  }

  // --- Header stats ------------------------------------------------------
  const stats = $derived.by(() => {
    let totalNodes = 0;
    const seenIds = new Set<string>();
    const seenQuarters = new Set<string>();
    let totalEdges = 0;
    for (const pl of plotted) {
      for (const n of pl.nodes) {
        if (!seenIds.has(n.id)) {
          seenIds.add(n.id);
          totalNodes += 1;
        }
        const q = `${Math.floor(n.t)}-Q${(Math.round((n.t % 1) * 4) + 1)}`;
        seenQuarters.add(q);
      }
      totalEdges += pl.lineage.edges.length;
    }
    return {
      lineages: lineages.length,
      nodes: totalNodes,
      quarters: seenQuarters.size,
      edges: totalEdges,
      curated: lineages.filter((l) => l.curated).length,
      auto: lineages.filter((l) => !l.curated).length
    };
  });
</script>

<svelte:head>
  <title>Memory Systems Landscape — Lineages</title>
</svelte:head>

<div class="wrap">
  <header>
    <h1>Lineage timeline</h1>
    <p class="subtitle">
      {stats.lineages} lineage{stats.lineages === 1 ? '' : 's'}
      ({stats.curated} curated · {stats.auto} auto-detected) ·
      {stats.nodes} systems plotted across {stats.quarters} quarters ·
      {stats.edges} descent edges
      <a class="back" href="{base}/">← back to table</a>
    </p>
  </header>

  <p class="hint">
    Each row is a lineage family. Nodes are plotted by their `created` date;
    arrows are structural-descent edges (built-on / extends / forks / succeeds
    + influential cites). Hover a node for its key claim, click to filter the
    table by that system. RSSM / world-model and Graph-RAG hierarchy are
    pre-seeded from analysis.md; the rest are auto-detected as connected
    components of size ≥ 3 in the descent sub-graph.
  </p>

  <div class="chart-scroll">
    {#if lineages.length === 0}
      <p class="empty">No lineages detected at minSize=3.</p>
    {:else}
      <svg
        viewBox="0 0 {totalW} {totalH}"
        width={totalW}
        height={totalH}
        role="img"
        aria-label="Lineage timeline diagram"
      >
        <!-- arrowhead marker -->
        <defs>
          <marker
            id="arrowhead"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#8b949e" />
          </marker>
          <marker
            id="arrowhead-influential"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#58a6ff" />
          </marker>
        </defs>

        <!-- Track baselines + lineage labels -->
        {#each plotted as pl}
          {@const y = yScale(pl.rowIndex)}
          <line
            x1={PAD_LEFT}
            x2={PAD_LEFT + innerW}
            y1={y}
            y2={y}
            stroke="#21262d"
            stroke-width="1"
            stroke-dasharray="2 4"
          />
          <text
            x={PAD_LEFT - 12}
            y={y + 4}
            text-anchor="end"
            class="track-label"
            class:curated={pl.lineage.curated}
          >
            {pl.lineage.name}
          </text>
          <text
            x={PAD_LEFT - 12}
            y={y + 18}
            text-anchor="end"
            class="track-sublabel"
          >
            {pl.nodes.length} plotted
            {#if pl.lineage.curated}· curated{/if}
          </text>
        {/each}

        <!-- X-axis ticks -->
        {#each xTicks as tick}
          {@const x = xScale(tick.t)}
          <line
            x1={x}
            x2={x}
            y1={PAD_TOP - 8}
            y2={PAD_TOP + innerH}
            stroke="#1f242b"
            stroke-width="1"
          />
          <text
            x={x}
            y={PAD_TOP - 14}
            text-anchor="middle"
            class="tick-label"
          >{tick.label}</text>
          <text
            x={x}
            y={PAD_TOP + innerH + 18}
            text-anchor="middle"
            class="tick-label"
          >{tick.label}</text>
        {/each}

        <!-- Edges (rendered below nodes) -->
        {#each plottedEdges as pe}
          {@const influential = pe.edge.type === 'cites' && pe.edge.isInfluential}
          <path
            d={bezierPath(pe)}
            fill="none"
            stroke={influential ? '#58a6ff' : '#484f58'}
            stroke-width={influential ? 1.4 : 1.1}
            stroke-opacity={hoverEdge === pe ? 1 : influential ? 0.65 : 0.45}
            marker-end={`url(#${influential ? 'arrowhead-influential' : 'arrowhead'})`}
            class="edge"
            role="img"
            aria-label="{pe.edge.type} edge from {pe.edge.source} to {pe.edge.target}"
            onpointerenter={(e) => onEdgeEnter(pe, e)}
            onpointermove={onNodeMove}
            onpointerleave={onEdgeLeave}
          />
        {/each}

        <!-- Nodes -->
        {#each plotted as pl}
          {#each pl.nodes as n}
            <g class="node">
              <circle
                cx={n.x}
                cy={n.y}
                r={n.id === pl.lineage.anchor ? NODE_R + 2 : NODE_R}
                fill={TIER_COLOURS[n.tier as 1 | 2 | 3 | 4 | 5]}
                stroke={n.id === pl.lineage.anchor ? '#f0f6fc' : '#0d1117'}
                stroke-width="1.5"
                class="node-dot"
                class:anchor={n.id === pl.lineage.anchor}
                onpointerenter={(e) => onNodeEnter(n, e)}
                onpointermove={onNodeMove}
                onpointerleave={onNodeLeave}
                onclick={() => onNodeClick(n)}
                onkeydown={(e) => { if (e.key === 'Enter') onNodeClick(n); }}
                role="button"
                tabindex="0"
                aria-label="{n.name}, tier {n.tier}"
              />
              <text
                x={n.x}
                y={n.y - 12}
                text-anchor="middle"
                class="node-label"
                class:anchor-label={n.id === pl.lineage.anchor}
              >{n.name}</text>
            </g>
          {/each}
        {/each}
      </svg>
    {/if}
  </div>

  <ul class="legend">
    <li><span class="lswatch lswatch-strong"></span> structural descent (built-on / extends / forks / succeeds)</li>
    <li><span class="lswatch lswatch-weak"></span> influential citation</li>
    <li><span class="lswatch lswatch-anchor"></span> anchor (oldest member of the lineage)</li>
  </ul>

  {#if hoverNode}
    <div
      class="tooltip"
      style="left: {hoverX + 14}px; top: {hoverY + 14}px"
      aria-hidden="true"
    >
      <div class="tt-head">
        <span class="tt-swatch" style="background:{TIER_COLOURS[hoverNode.tier as 1|2|3|4|5]}"></span>
        {hoverNode.name}
        <span class="tt-tier">T{hoverNode.tier}</span>
      </div>
      {#if hoverNode.claim}
        <div class="tt-body">{hoverNode.claim.slice(0, 320)}{hoverNode.claim.length > 320 ? '…' : ''}</div>
      {/if}
      <div class="tt-foot">Click to filter the table by this system</div>
    </div>
  {/if}

  {#if hoverEdge}
    <div
      class="tooltip"
      style="left: {hoverX + 14}px; top: {hoverY + 14}px"
      aria-hidden="true"
    >
      <div class="tt-head">
        {hoverEdge.edge.source} → {hoverEdge.edge.target}
      </div>
      <div class="tt-body">
        <strong>{hoverEdge.edge.type}{hoverEdge.edge.isInfluential ? ' · influential' : ''}</strong><br />
        {hoverEdge.edge.evidence}
      </div>
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
  .hint {
    color: #6e7681;
    font-size: 0.8rem;
    font-style: italic;
    margin: 0;
    max-width: 960px;
    line-height: 1.5;
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
  :global(.track-label) {
    font-size: 12px;
    fill: #c9d1d9;
    font-weight: 500;
  }
  :global(.track-label.curated) {
    fill: #f0b441;
  }
  :global(.track-sublabel) {
    font-size: 10px;
    fill: #6e7681;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  :global(.tick-label) {
    font-size: 10px;
    fill: #8b949e;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  :global(.node-dot) {
    cursor: pointer;
    transition: r 80ms linear;
  }
  :global(.node-dot:hover) {
    r: 9;
  }
  :global(.node-dot:focus) {
    outline: none;
    stroke: #58a6ff;
    stroke-width: 2;
  }
  :global(.node-label) {
    font-size: 9.5px;
    fill: #8b949e;
    pointer-events: none;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  :global(.anchor-label) {
    fill: #f0f6fc;
    font-weight: 600;
  }
  :global(.edge) {
    cursor: help;
    transition: stroke-opacity 100ms linear;
  }
  .legend {
    list-style: none;
    padding: 0;
    margin: 4px 0 0 0;
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    font-size: 0.78rem;
    color: #8b949e;
  }
  .legend li { display: inline-flex; align-items: center; gap: 6px; }
  .lswatch {
    display: inline-block;
    width: 18px;
    height: 2px;
    background: #484f58;
  }
  .lswatch-weak { background: #58a6ff; height: 2px; }
  .lswatch-anchor {
    width: 10px;
    height: 10px;
    background: #c9d1d9;
    border-radius: 50%;
    border: 1.5px solid #f0f6fc;
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
    max-width: 380px;
    pointer-events: none;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  }
  .tt-head {
    font-weight: 600;
    margin-bottom: 4px;
    color: #f0f6fc;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .tt-swatch {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 2px;
  }
  .tt-tier {
    color: #6e7681;
    font-size: 0.7rem;
    margin-left: auto;
  }
  .tt-body {
    color: #c9d1d9;
    line-height: 1.4;
    margin-bottom: 6px;
  }
  .tt-foot {
    color: #6e7681;
    font-size: 0.72rem;
    font-style: italic;
  }
</style>
