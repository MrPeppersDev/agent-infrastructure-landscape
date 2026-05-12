<script lang="ts">
  // Force-directed graph view (issue #16). 523 nodes, 247 edges. Cytoscape
  // 3.x + fcose layout. See $lib/graph.ts for the pure data-shaping
  // helpers (palette, edge styles, neighbour index, hub selection) and
  // docs/DECISIONS.md (2026-05-07 "Graph view") for the layout-choice and
  // bundle-size rationale.
  //
  // Why client-only: Cytoscape constructs against a live DOM container
  // and the fcose worker spins the layout client-side. `ssr = false` in
  // +page.ts skips the server pass; we also guard the dynamic import on
  // `browser` so the bundle is split out of the main route chunk.

  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import { base } from '$app/paths';
  import type { LandscapeRecord, EdgeType } from '$lib/types';
  import {
    recordsToNodes,
    edgesToCytoscape,
    degreeMap,
    neighbourhoodIndex,
    sectionColourMap,
    EDGE_STYLES,
    topHubIds,
    recordById,
    primarySection,
    type CyNode,
    type CyEdge,
    type Neighbourhood
  } from '$lib/graph';

  let { data }: { data: { records: LandscapeRecord[]; edges: import('$lib/types').Edge[] } } =
    $props();

  // --- Static maps (computed once) ---------------------------------------
  //
  // These don't change with user interaction so we memoise them at module
  // init. Recomputing on every keystroke would be wasteful (523 records,
  // 247 edges → ~25 KB of element data each pass).
  //
  // We capture `data` into untracked locals first. Reading the prop
  // outside a closure is technically a Svelte warning ("only captures
  // initial value"), and that's exactly what we want — the build-time
  // data really never changes after load.
  const records: LandscapeRecord[] = data.records;
  const allEdges = data.edges;
  const colourMap = sectionColourMap(records);
  const degrees = degreeMap(allEdges);
  const byId = recordById(records);
  const nodeIds = new Set(records.map((r) => r.id));
  const nodes: CyNode[] = recordsToNodes(records, degrees);
  const cyEdges: CyEdge[] = edgesToCytoscape(allEdges, nodeIds);
  const neighbours: Neighbourhood = neighbourhoodIndex(allEdges);

  // Sorted list of sections (by record count desc) so the legend matches
  // the colour-assignment order.
  const sectionsInOrder = [...colourMap.keys()];

  // Edge-type frequencies for the legend label "(N)".
  const edgeTypeCounts = new Map<EdgeType, number>();
  for (const e of allEdges) {
    edgeTypeCounts.set(e.type, (edgeTypeCounts.get(e.type) ?? 0) + 1);
  }
  const presentEdgeTypes: EdgeType[] = [...edgeTypeCounts.keys()].sort(
    (a, b) => (edgeTypeCounts.get(b) ?? 0) - (edgeTypeCounts.get(a) ?? 0)
  );

  // --- UI state ----------------------------------------------------------
  let container: HTMLDivElement;
  // Cytoscape instance held as plain (non-reactive) ref — reactive proxies
  // would trip up cytoscape's internal === identity checks.
  let cy: any = null;

  // Edge-type visibility (legend toggles). Default: all on.
  let visibleEdgeTypes = $state<Set<EdgeType>>(new Set(presentEdgeTypes));

  // Search box.
  let query = $state('');
  // Selected node id → drives the side panel.
  let selectedId = $state<string | null>(null);
  // Hub view toggle.
  let hubViewOn = $state(false);
  const HUB_N = 40;
  const hubSet = topHubIds(records, allEdges, HUB_N);
  // Loading flag for the initial fcose pass — ~1s on this dataset.
  let layoutRunning = $state(true);

  // --- Cytoscape style --------------------------------------------------
  //
  // Hand-written stylesheet. Selectors:
  //   - node: base appearance (colour by section, size by sqrt(degree))
  //   - node:selected: blue ring
  //   - .faded: 0.08 opacity (for the "fade everything else" search mode)
  //   - .hub-hidden: hidden when hub view is on and node isn't a hub
  //   - edge[type = "X"]: per-edge-type colour + dash + width
  //   - .edge-hidden: hidden when its type is toggled off in the legend
  //
  // Why not return the array from a $derived: cytoscape's setStyle()
  // accepts the array directly, and rebuilding the full stylesheet is
  // cheap compared to mutating individual selectors.
  function buildStyle() {
    const sectionRules = sectionsInOrder.map((section) => ({
      selector: `node[section = "${cssEscape(section)}"]`,
      style: {
        'background-color': colourMap.get(section) ?? '#8b949e'
      }
    }));
    const edgeRules = (Object.keys(EDGE_STYLES) as EdgeType[]).map((t) => {
      const s = EDGE_STYLES[t];
      return {
        selector: `edge[type = "${t}"]`,
        style: {
          'line-color': s.colour,
          'target-arrow-color': s.colour,
          'width': s.width,
          'line-style': s.lineStyle
        }
      };
    });
    return [
      {
        selector: 'node',
        style: {
          'background-color': '#8b949e',
          'label': 'data(label)',
          'color': '#c9d1d9',
          'font-size': 9,
          'font-family': 'ui-monospace, SFMono-Regular, monospace',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 3,
          'text-outline-color': '#0d1117',
          'text-outline-width': 2,
          // Node radius: sqrt scaling so a degree-30 hub is ~5.5× the
          // area of a degree-1 leaf — visually obvious but not so big it
          // smothers the cluster.
          'width': 'mapData(degree, 0, 30, 6, 26)',
          'height': 'mapData(degree, 0, 30, 6, 26)',
          'border-width': 0
        }
      },
      ...sectionRules,
      {
        selector: 'node:selected',
        style: {
          'border-width': 3,
          'border-color': '#f0f6fc',
          'font-size': 11,
          'font-weight': 600
        }
      },
      {
        selector: 'node.highlighted',
        style: {
          'border-width': 2,
          'border-color': '#f0f6fc',
          'font-size': 11
        }
      },
      {
        selector: 'node.faded',
        style: {
          'opacity': 0.08,
          'text-opacity': 0,
          'background-color': '#30363d'
        }
      },
      {
        selector: 'node.hub-hidden',
        style: { 'display': 'none' }
      },
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'opacity': 0.55,
          'target-arrow-shape': 'triangle',
          'arrow-scale': 0.8
        }
      },
      ...edgeRules,
      {
        selector: 'edge.faded',
        style: { 'opacity': 0.04 }
      },
      {
        selector: 'edge.highlighted',
        style: { 'opacity': 0.95, 'width': 2.2 }
      },
      {
        selector: 'edge.edge-hidden',
        style: { 'display': 'none' }
      }
    ];
  }

  // Cytoscape selector-attribute escape — we use the raw section name in
  // a string-quoted attribute selector, so any embedded `"` would
  // detonate the parser. The section names in the corpus don't contain
  // double-quotes today, but defensively strip them.
  function cssEscape(s: string): string {
    return s.replace(/["\\]/g, '');
  }

  // --- Mount ------------------------------------------------------------
  //
  // Dynamic import of cytoscape so the (~430 KB minified) library lands in
  // its own chunk rather than the main app bundle. The /graph route is
  // the only consumer; users who never click into it never pay the cost.
  onMount(async () => {
    if (!browser) return;
    const cytoscapeMod = await import('cytoscape');
    // cytoscape-fcose ships JS only; cast to any rather than depend on a
    // generated .d.ts file we'd need to keep in sync.
    const fcoseMod: any = await import('cytoscape-fcose' as any);
    const cytoscape = cytoscapeMod.default;
    const fcose = fcoseMod.default;
    cytoscape.use(fcose);

    cy = cytoscape({
      container,
      elements: [...nodes, ...cyEdges],
      // Style array uses cytoscape's loose JSON shape; the typed definition
      // is strict about per-property literal unions and rejects our
      // generic string values. The runtime accepts them fine.
      style: buildStyle() as any,
      // fcose tuning: edge-elasticity & node-repulsion picked empirically
      // for this scale (523 nodes, mostly low-degree, a handful of
      // hubs). `randomize: true` so the layout doesn't pile on the same
      // spot every hot-reload during dev.
      layout: {
        name: 'fcose',
        quality: 'default',
        animate: false,
        randomize: true,
        nodeRepulsion: 8000,
        idealEdgeLength: 70,
        edgeElasticity: 0.45,
        gravity: 0.25,
        numIter: 2500,
        tile: true,
        nodeSeparation: 75
      } as any,
      // Default cytoscape behaviour disables wheelSensitivity warnings; we
      // pick a comfortable value for trackpad + mouse wheel.
      wheelSensitivity: 0.25,
      minZoom: 0.15,
      maxZoom: 4
    });

    cy.on('tap', 'node', (evt: any) => {
      const id = evt.target.data('id');
      selectedId = id;
      applyHighlight(id);
    });
    cy.on('tap', (evt: any) => {
      // Background tap → clear selection (cytoscape gives us the core).
      if (evt.target === cy) {
        selectedId = null;
        clearHighlight();
      }
    });

    // Layout-done flips the "loading" flag. fcose fires `layoutstop` on
    // completion when `animate: false`; this resolves the spinner.
    cy.one('layoutstop', () => {
      layoutRunning = false;
    });
    // Safety: in case `layoutstop` doesn't fire for some reason, time it
    // out after 5s and just show the graph.
    setTimeout(() => { layoutRunning = false; }, 5000);
  });

  onDestroy(() => {
    if (cy) {
      cy.destroy();
      cy = null;
    }
  });

  // --- Highlight / fade -------------------------------------------------
  //
  // Search-highlight semantics: when a query matches a node, that node
  // and its 1-hop ring keep full opacity; everything else fades. When
  // the query is empty, all fading is cleared.
  //
  // Implementation: maintain two classes on cytoscape elements (`faded`
  // and `highlighted`) and toggle them in bulk via the collection API.
  // This is O(N) but cytoscape batches the style recomputation, so the
  // perceived cost is ~5ms on 523 nodes.

  function applyHighlight(centerId: string) {
    if (!cy) return;
    const ring = neighbours.byId.get(centerId) ?? new Set<string>();
    cy.batch(() => {
      cy.elements().removeClass('highlighted faded');
      cy.elements().addClass('faded');
      const sel = cy.$id(centerId);
      sel.removeClass('faded').addClass('highlighted');
      ring.forEach((nid: string) => {
        const n = cy.$id(nid);
        n.removeClass('faded').addClass('highlighted');
        // Edges between center and ring members also un-fade.
        n.edgesWith(sel).removeClass('faded').addClass('highlighted');
      });
    });
  }

  function clearHighlight() {
    if (!cy) return;
    cy.elements().removeClass('faded highlighted');
  }

  // --- Search effect ----------------------------------------------------
  //
  // We match on case-insensitive name substring against the records
  // list, take the first hit, and pretend the user clicked it. Empty
  // string clears everything (and also clears the selectedId so the
  // side panel collapses).
  $effect(() => {
    const q = query.trim().toLowerCase();
    if (!cy) return;
    if (!q) {
      if (!selectedId) clearHighlight();
      return;
    }
    const hit = records.find((r) => r.name.toLowerCase().includes(q));
    if (!hit) {
      // No match: fade everything (visual feedback that the query is
      // unproductive) but leave selected node un-faded.
      cy.batch(() => {
        cy.elements().removeClass('highlighted');
        cy.elements().addClass('faded');
        if (selectedId) cy.$id(selectedId).removeClass('faded').addClass('highlighted');
      });
      return;
    }
    selectedId = hit.id;
    applyHighlight(hit.id);
    // Re-centre on the match so the user can see it.
    cy.animate({ center: { eles: cy.$id(hit.id) }, zoom: 1.2 }, { duration: 280 });
  });

  // --- Edge-type legend effect ------------------------------------------
  //
  // Toggling a legend checkbox adds/removes the `edge-hidden` class on
  // all edges of that type. We don't relayout — fcose-positioned nodes
  // stay put; only edge visibility changes.
  $effect(() => {
    if (!cy) return;
    cy.batch(() => {
      for (const t of Object.keys(EDGE_STYLES) as EdgeType[]) {
        const sel = cy.edges(`[type = "${t}"]`);
        if (visibleEdgeTypes.has(t)) sel.removeClass('edge-hidden');
        else sel.addClass('edge-hidden');
      }
    });
  });

  // --- Hub-view effect ---------------------------------------------------
  //
  // When on, non-hub nodes get `hub-hidden` (display: none in the
  // stylesheet — so cytoscape skips their layout consideration too if
  // we relayout). We DON'T relayout on toggle — that'd jitter the
  // remaining nodes' positions unproductively. Instead we fit the
  // viewport to the visible (hub) subset.
  $effect(() => {
    if (!cy) return;
    cy.batch(() => {
      const nodesCol = cy.nodes();
      if (hubViewOn) {
        nodesCol.forEach((n: any) => {
          if (!hubSet.has(n.data('id'))) n.addClass('hub-hidden');
          else n.removeClass('hub-hidden');
        });
      } else {
        nodesCol.removeClass('hub-hidden');
      }
    });
    if (hubViewOn) {
      cy.fit(cy.nodes(':visible'), 40);
    } else {
      cy.fit(undefined, 40);
    }
  });

  // --- Side panel helpers -----------------------------------------------
  const selectedRecord = $derived<LandscapeRecord | null>(
    selectedId ? byId.get(selectedId) ?? null : null
  );

  function toggleEdgeType(t: EdgeType) {
    // Replace the Set (rather than mutate-then-reassign) so the $effect
    // dependency tracker sees a fresh value. Mutating a $state Set still
    // notifies in Svelte 5, but a re-creation keeps the intent clear.
    const next = new Set(visibleEdgeTypes);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    visibleEdgeTypes = next;
  }

  function resetView() {
    if (!cy) return;
    selectedId = null;
    query = '';
    clearHighlight();
    cy.fit(undefined, 40);
  }

  // Pretty cell display: trim absurdly long text, fall back to a status
  // word when the cell has no real data.
  function cellText(r: LandscapeRecord, slug: keyof LandscapeRecord['cells']) {
    const c = r.cells[slug];
    if (!c) return '—';
    if (c.status !== 'real-data') return c.status === 'not-applicable' ? 'n/a' : '—';
    return c.value.length > 280 ? c.value.slice(0, 280) + '…' : c.value;
  }
</script>

<svelte:head>
  <title>Memory Systems Landscape — Graph</title>
</svelte:head>

<div class="wrap">
  <header>
    <h1>Force-directed graph</h1>
    <p class="subtitle">
      {data.records.length.toLocaleString()} systems · {data.edges.length.toLocaleString()} edges
      · fcose layout
      <a class="back" href="{base}/">← back to table</a>
    </p>
  </header>

  <div class="layout">
    <aside class="controls">
      <div class="control-group">
        <label class="ctrl-label" for="graph-search">Search</label>
        <input
          id="graph-search"
          type="search"
          placeholder="Highlight node by name…"
          bind:value={query}
          autocomplete="off"
          spellcheck="false"
        />
      </div>

      <div class="control-group">
        <label class="ctrl-label">
          <input type="checkbox" bind:checked={hubViewOn} />
          Hub view (top {HUB_N} by degree)
        </label>
        <button class="reset" onclick={resetView}>Reset view</button>
      </div>

      <div class="control-group">
        <div class="ctrl-label">Edge types</div>
        <ul class="edge-legend">
          {#each presentEdgeTypes as t}
            {@const s = EDGE_STYLES[t]}
            <li>
              <label>
                <input
                  type="checkbox"
                  checked={visibleEdgeTypes.has(t)}
                  onchange={() => toggleEdgeType(t)}
                />
                <span
                  class="edge-swatch"
                  style="--c: {s.colour}; --ls: {s.lineStyle === 'solid' ? 'solid' : s.lineStyle};"
                ></span>
                {s.label}
                <span class="count">{edgeTypeCounts.get(t)}</span>
              </label>
            </li>
          {/each}
        </ul>
      </div>

      <div class="control-group">
        <div class="ctrl-label">Sections</div>
        <ul class="section-legend">
          {#each sectionsInOrder as s}
            <li>
              <span class="sw" style="background:{colourMap.get(s)}"></span>
              <span class="sl">{s}</span>
            </li>
          {/each}
        </ul>
      </div>
    </aside>

    <div class="canvas-wrap">
      {#if layoutRunning}
        <div class="loading">Laying out {data.records.length} nodes…</div>
      {/if}
      <div bind:this={container} class="canvas"></div>
    </div>

    <aside class="side-panel" class:open={selectedRecord !== null}>
      {#if selectedRecord}
        {@const r = selectedRecord}
        {@const section = primarySection(r)}
        <div class="sp-head">
          <span class="sp-tier">T{r.tier}</span>
          <span class="sp-name">{r.name}</span>
          <button class="sp-close" onclick={() => { selectedId = null; clearHighlight(); }} aria-label="Close">×</button>
        </div>
        <div class="sp-section">
          <span class="sw" style="background:{colourMap.get(section)}"></span>
          {section}
        </div>
        {#if r.url}
          <a class="sp-url" href={r.url} target="_blank" rel="noopener">{r.url}</a>
        {/if}
        <dl class="sp-cells">
          <dt>Description</dt>
          <dd>{cellText(r, 'desc')}</dd>

          <dt>Claims</dt>
          <dd>{cellText(r, 'claims')}</dd>

          <dt>Performance</dt>
          <dd>{cellText(r, 'perf')}</dd>

          <dt>Citations</dt>
          <dd>{cellText(r, 'citations')}</dd>

          <dt>GitHub</dt>
          <dd>{cellText(r, 'gh')}</dd>
        </dl>
        <div class="sp-degree">
          {(degrees.get(r.id)?.in ?? 0)} inbound · {(degrees.get(r.id)?.out ?? 0)} outbound edges
        </div>
      {:else}
        <div class="sp-empty">
          Click a node to see details. Use the search box to highlight a node and its 1-hop neighbours.
        </div>
      {/if}
    </aside>
  </div>
</div>

<style>
  .wrap {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 8px 0 24px;
    color: #c9d1d9;
    height: calc(100vh - 16px);
    box-sizing: border-box;
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

  .layout {
    display: grid;
    grid-template-columns: 240px 1fr 320px;
    gap: 12px;
    flex: 1 1 auto;
    min-height: 0;
  }

  .controls {
    overflow-y: auto;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #0d1117;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    font-size: 0.78rem;
  }
  .control-group { display: flex; flex-direction: column; gap: 6px; }
  .ctrl-label {
    color: #8b949e;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
  }
  .controls input[type="search"] {
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 0.85rem;
    font-family: inherit;
  }
  .controls input[type="search"]:focus {
    outline: 1px solid #58a6ff;
    border-color: #58a6ff;
  }
  .reset {
    align-self: flex-start;
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.78rem;
    cursor: pointer;
  }
  .reset:hover { background: #21262d; }

  .edge-legend, .section-legend {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .edge-legend label {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    color: #c9d1d9;
  }
  .edge-swatch {
    display: inline-block;
    width: 22px;
    height: 0;
    border-top: 2px var(--ls, solid) var(--c, #8b949e);
    flex-shrink: 0;
  }
  .count {
    color: #6e7681;
    font-size: 0.7rem;
    margin-left: auto;
    font-variant-numeric: tabular-nums;
  }
  .section-legend li {
    display: flex;
    align-items: center;
    gap: 6px;
    line-height: 1.4;
  }
  .sw {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .sl {
    font-size: 0.74rem;
    color: #c9d1d9;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .canvas-wrap {
    position: relative;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #0d1117;
    overflow: hidden;
    min-height: 400px;
  }
  .canvas {
    position: absolute;
    inset: 0;
  }
  .loading {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #8b949e;
    font-size: 0.85rem;
    background: rgba(13, 17, 23, 0.85);
    z-index: 5;
  }

  .side-panel {
    overflow-y: auto;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #0d1117;
    padding: 12px;
    font-size: 0.82rem;
  }
  .sp-head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .sp-tier {
    background: #21262d;
    color: #8b949e;
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 0.7rem;
    font-weight: 600;
  }
  .sp-name {
    font-weight: 600;
    color: #f0f6fc;
    font-size: 0.95rem;
    flex: 1;
  }
  .sp-close {
    background: transparent;
    color: #8b949e;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    line-height: 1;
    padding: 0 4px;
  }
  .sp-close:hover { color: #f0f6fc; }
  .sp-section {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #8b949e;
    margin-bottom: 6px;
  }
  .sp-url {
    display: block;
    color: #58a6ff;
    font-size: 0.75rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 10px;
  }
  .sp-cells {
    display: grid;
    grid-template-columns: 1fr;
    gap: 6px;
    margin: 0;
  }
  .sp-cells dt {
    font-size: 0.7rem;
    text-transform: uppercase;
    color: #6e7681;
    letter-spacing: 0.05em;
    margin-top: 8px;
  }
  .sp-cells dd {
    margin: 0;
    color: #c9d1d9;
    line-height: 1.45;
  }
  .sp-degree {
    margin-top: 12px;
    padding-top: 8px;
    border-top: 1px solid #21262d;
    color: #8b949e;
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
  }
  .sp-empty {
    color: #6e7681;
    font-style: italic;
    font-size: 0.78rem;
  }
</style>
