<script lang="ts">
  // Co-citation + bibliographic-coupling map (issue #45, T2-2).
  //
  // Bibliometric staple since Small 1973. Two operations over the same
  // 528-edge graph:
  //
  //   Co-citation  — record X cites both A and B → community pairs them
  //   Bib coupling — A and B both cite X        → shared lineage
  //
  // The visualisation is a Cytoscape force-directed map where node
  // colour matches the catalog's primary-section palette and edges are
  // similarity links. The same palette is used everywhere a section
  // colour appears in the app, so cross-view recognition is preserved.
  //
  // The headline finding is the disagreement panel: pairs where the
  // community signal puts two systems in the same neighbourhood but our
  // hand-built taxonomy puts them in different sections. That is
  // bibliometrically the most interesting cell of the table.
  //
  // Why client-only: Cytoscape touches the DOM during construction; the
  // route's +page.ts sets ssr = false. We also guard the mount on
  // `browser` and dynamic-import the library so the (~430KB) chunk only
  // ships when this route is visited.

  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import { base } from '$app/paths';
  import type { Edge, LandscapeRecord } from '$lib/types';
  import { sectionColourMap } from '$lib/graph';
  import {
    computeCoCitation,
    computeBibCoupling,
    type CoCitationMode,
    type CoCitationVariant,
    type CoCitationResult,
    type SimilarityPair,
    DISAGREEMENT_SIM_THRESHOLD,
    SIMILARITY_THRESHOLD,
    MAX_PAIRS,
    TOP_PAIRS_LIMIT
  } from '$lib/analyses/co-citation';

  let { data }: { data: { records: LandscapeRecord[]; edges: Edge[] } } = $props();

  const records = data.records;
  const edges = data.edges;

  // --- Mode + variant -----------------------------------------------------
  let mode = $state<CoCitationMode>('co-citation');
  let variant = $state<CoCitationVariant>('cites-only');

  // Recompute on every mode/variant change. With ~250 source nodes the
  // inner loop runs in ~30ms — well under the perceptual budget for an
  // interactive control. $derived caches between identical input changes.
  const result: CoCitationResult = $derived.by(() => {
    if (mode === 'co-citation') return computeCoCitation(records, edges, variant);
    return computeBibCoupling(records, edges);
  });

  // Palette: same section colours used by /graph so a node "Cognee" looks
  // the same colour here and in the main force-directed view.
  const colourMap = sectionColourMap(records);

  // --- Cytoscape -----------------------------------------------------------
  let container: HTMLDivElement;
  // Held as a plain (non-reactive) ref — cytoscape's internal === identity
  // checks trip on Svelte proxies.
  let cy: any = null;
  let layoutRunning = $state(true);
  let cyReady = $state(false);

  function buildStyle(): any[] {
    const sectionRules = [...colourMap.keys()].map((section) => ({
      selector: `node[section = "${cssEscape(section)}"]`,
      style: { 'background-color': colourMap.get(section) ?? '#8b949e' }
    }));
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
          // Node size scales by degree in the similarity graph itself,
          // not the underlying citation graph. A node with many similar
          // peers should look central.
          'width': 'mapData(degree, 0, 30, 8, 28)',
          'height': 'mapData(degree, 0, 30, 8, 28)',
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
          'opacity': 0.1,
          'text-opacity': 0,
          'background-color': '#30363d'
        }
      },
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'opacity': 0.45,
          'line-color': '#6e7681',
          // Edge thickness scales with similarity score. mapData maps
          // similarity ∈ [SIMILARITY_THRESHOLD, 1] → thickness ∈ [0.6, 4].
          'width': 'mapData(similarity, 0.1, 1, 0.6, 4)'
        }
      },
      {
        selector: 'edge.disagreement',
        style: {
          // Burnt-orange highlight matches the .ce-coverage-note callout
          // used elsewhere — cross-view colour recognition.
          'line-color': '#d4845f',
          'opacity': 0.85,
          'line-style': 'dashed'
        }
      },
      {
        selector: 'edge.faded',
        style: { 'opacity': 0.04 }
      },
      {
        selector: 'edge.highlighted',
        style: { 'opacity': 0.95 }
      }
    ];
  }

  function cssEscape(s: string): string {
    return s.replace(/["\\]/g, '');
  }

  // Build elements from a result. Computes a per-node degree (number of
  // similarity edges that touch the node) so the stylesheet's mapData
  // expression can scale node size meaningfully.
  function buildElements(r: CoCitationResult): any[] {
    const degree = new Map<string, number>();
    for (const p of r.pairs) {
      degree.set(p.a, (degree.get(p.a) ?? 0) + 1);
      degree.set(p.b, (degree.get(p.b) ?? 0) + 1);
    }
    const nodes = r.nodes.map((n) => ({
      group: 'nodes',
      data: {
        id: n.id,
        label: n.name,
        section: n.section,
        degree: degree.get(n.id) ?? 0
      }
    }));
    const cyEdges = r.pairs.map((p) => ({
      group: 'edges',
      data: {
        id: `${p.a}|${p.b}`,
        source: p.a,
        target: p.b,
        similarity: p.similarity,
        sharedCount: p.sharedCount,
        agrees: p.taxonomyAgrees
      },
      classes:
        !p.taxonomyAgrees && p.similarity > DISAGREEMENT_SIM_THRESHOLD
          ? 'disagreement'
          : ''
    }));
    return [...nodes, ...cyEdges];
  }

  onMount(async () => {
    if (!browser) return;
    const cytoscapeMod = await import('cytoscape');
    const fcoseMod: any = await import('cytoscape-fcose' as any);
    const cytoscape = cytoscapeMod.default;
    const fcose = fcoseMod.default;
    cytoscape.use(fcose);

    cy = cytoscape({
      container,
      elements: buildElements(result),
      style: buildStyle() as any,
      layout: {
        name: 'fcose',
        quality: 'default',
        animate: false,
        randomize: true,
        // Tighter cluster than /graph — the similarity graph is denser
        // and clustered communities are the visual point of the view.
        nodeRepulsion: 5000,
        idealEdgeLength: 60,
        edgeElasticity: 0.55,
        gravity: 0.3,
        numIter: 2500,
        tile: true,
        nodeSeparation: 60
      } as any,
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
      if (evt.target === cy) {
        selectedId = null;
        clearHighlight();
      }
    });
    cy.one('layoutstop', () => { layoutRunning = false; });
    setTimeout(() => { layoutRunning = false; }, 5000);
    cyReady = true;
  });

  onDestroy(() => {
    if (cy) {
      cy.destroy();
      cy = null;
    }
  });

  // When mode / variant changes, swap the elements + run a fresh layout.
  // We rebuild from scratch (rather than diff) because the node and edge
  // sets diverge meaningfully between modes — diffing wouldn't be cheaper.
  $effect(() => {
    if (!cy || !cyReady) return;
    layoutRunning = true;
    selectedId = null;
    cy.elements().remove();
    cy.add(buildElements(result));
    const layout = cy.layout({
      name: 'fcose',
      quality: 'default',
      animate: false,
      randomize: true,
      nodeRepulsion: 5000,
      idealEdgeLength: 60,
      edgeElasticity: 0.55,
      gravity: 0.3,
      numIter: 2500,
      tile: true,
      nodeSeparation: 60
    });
    layout.one('layoutstop', () => { layoutRunning = false; });
    layout.run();
  });

  // --- Highlight ----------------------------------------------------------
  let selectedId = $state<string | null>(null);

  function applyHighlight(id: string) {
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass('highlighted faded');
      cy.elements().addClass('faded');
      const sel = cy.$id(id);
      sel.removeClass('faded').addClass('highlighted');
      sel.connectedEdges().forEach((e: any) => {
        e.removeClass('faded').addClass('highlighted');
        e.connectedNodes().removeClass('faded').addClass('highlighted');
      });
    });
  }

  function clearHighlight() {
    if (!cy) return;
    cy.elements().removeClass('faded highlighted');
  }

  // --- Counters for the prose summary -------------------------------------
  const total = $derived(result.pairs.length);
  const disagreementCount = $derived(result.disagreementPairs.length);
  const topPair = $derived<SimilarityPair | null>(result.topPairs[0] ?? null);

  // Selection helpers
  const selectedPairs = $derived.by(() => {
    if (!selectedId) return [] as SimilarityPair[];
    return result.pairs
      .filter((p) => p.a === selectedId || p.b === selectedId)
      .slice(0, 12);
  });
  const selectedName = $derived.by(() => {
    if (!selectedId) return null;
    const r = records.find((x) => x.id === selectedId);
    return r?.name ?? null;
  });

  function tableHref(name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  function fmtSim(s: number): string {
    return s.toFixed(3);
  }

  function modeBlurb(m: CoCitationMode): string {
    if (m === 'co-citation') {
      return 'Two systems are "co-cited" when a third party cites both of them — high co-citation means the community pairs them together.';
    }
    return 'Two systems are "bibliographically coupled" when they both cite (or depend on, or build on) the same things — high coupling means shared intellectual lineage.';
  }
</script>

<svelte:head>
  <title>Co-citation map · Memory Landscape</title>
</svelte:head>

<main class="cc-page">
  <header class="cc-header">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Co-citation and bibliographic coupling</h1>
    <p class="cc-intro">
      Bibliometric staple since
      <a href="https://onlinelibrary.wiley.com/doi/10.1002/asi.4630240406" target="_blank" rel="noopener noreferrer">Henry
        Small 1973</a> — which systems does the <em>community</em>
      cluster together, and how does that compare to the catalog's
      hand-built taxonomy? When the two disagree, that&apos;s signal:
      the community sees a pairing the taxonomy missed.
    </p>
    <p class="cc-intro cc-callout">
      <strong>{total} pairs</strong> cleared the similarity threshold of
      {SIMILARITY_THRESHOLD}.
      <strong>{disagreementCount} of them</strong> sit in different
      taxonomy sections at similarity &gt; {DISAGREEMENT_SIM_THRESHOLD}
      — the disagreement panel is the headline finding.
      {#if topPair}
        Top pair: <strong>{topPair.aName}</strong> ↔
        <strong>{topPair.bName}</strong>
        (similarity {fmtSim(topPair.similarity)},
        {topPair.sharedCount} shared).
      {/if}
    </p>
    <p class="cc-intro cc-scope-note">
      {modeBlurb(mode)}
      Pairs below similarity {SIMILARITY_THRESHOLD} are dropped as noise;
      results are capped at {MAX_PAIRS} pairs for visualisation
      performance. Cosine similarity is computed as <code>shared / √(deg_A · deg_B)</code>.
    </p>
  </header>

  <section class="controls" aria-label="Mode and variant controls">
    <div class="ctrl-row">
      <div class="ctrl-group">
        <span class="ctrl-label">Mode</span>
        <div class="chip-row" role="radiogroup" aria-label="Similarity mode">
          <button
            class="chip"
            class:on={mode === 'co-citation'}
            role="radio"
            aria-checked={mode === 'co-citation'}
            onclick={() => { mode = 'co-citation'; }}
          >Co-citation</button>
          <button
            class="chip"
            class:on={mode === 'bibliographic-coupling'}
            role="radio"
            aria-checked={mode === 'bibliographic-coupling'}
            onclick={() => { mode = 'bibliographic-coupling'; }}
          >Bibliographic coupling</button>
        </div>
      </div>
      <div class="ctrl-group" class:dim={mode !== 'co-citation'}>
        <span class="ctrl-label">Co-citation edge set</span>
        <div class="chip-row" role="radiogroup" aria-label="Co-citation variant">
          <button
            class="chip"
            class:on={variant === 'cites-only'}
            role="radio"
            aria-checked={variant === 'cites-only'}
            disabled={mode !== 'co-citation'}
            onclick={() => { variant = 'cites-only'; }}
            title="Academic-style co-citation — only `cites` edges count (Small 1973's original definition)"
          >Cites only</button>
          <button
            class="chip"
            class:on={variant === 'any-edge'}
            role="radio"
            aria-checked={variant === 'any-edge'}
            disabled={mode !== 'co-citation'}
            onclick={() => { variant = 'any-edge'; }}
            title="Any inbound edge (cites, integrates-with, built-on, runtime-dependency, etc.) counts as a 'citation' in the loose sense"
          >Any edge</button>
        </div>
      </div>
    </div>
  </section>

  <div class="layout">
    <section class="canvas-wrap" aria-label="Similarity network">
      {#if layoutRunning}
        <div class="loading">Computing force-directed layout…</div>
      {/if}
      <div class="canvas" bind:this={container}></div>
      <div class="legend-overlay" aria-label="Legend">
        <div class="legend-item">
          <span class="legend-line" style="background:#6e7681"></span>
          Similarity edge
        </div>
        <div class="legend-item">
          <span class="legend-line dash" style="background:#d4845f"></span>
          Cross-section disagreement
        </div>
        <div class="legend-item">
          <span class="legend-note">node colour = section · size = similarity-degree · edge width = score</span>
        </div>
      </div>
    </section>

    <aside class="side">
      {#if selectedId && selectedName}
        <div class="panel">
          <h2 class="panel-h">
            <span class="panel-name">{selectedName}</span>
            <button class="panel-close" aria-label="Clear selection"
              onclick={() => { selectedId = null; clearHighlight(); }}>×</button>
          </h2>
          <p class="panel-sub">
            <a href={tableHref(selectedName)}>↗ open in table</a>
          </p>
          <h3 class="panel-sub-h">Nearest neighbours</h3>
          {#if selectedPairs.length === 0}
            <p class="muted">No similarity pairs touch this record at the current threshold.</p>
          {:else}
            <ol class="pair-list">
              {#each selectedPairs as p}
                {@const otherName = p.a === selectedId ? p.bName : p.aName}
                {@const otherSection = p.a === selectedId ? p.bSection : p.aSection}
                <li class:disagree={!p.taxonomyAgrees && p.similarity > DISAGREEMENT_SIM_THRESHOLD}>
                  <span class="pair-name">{otherName}</span>
                  <span class="pair-meta">
                    <span class="pair-sim">sim {fmtSim(p.similarity)}</span>
                    <span class="pair-shared">· {p.sharedCount} shared</span>
                  </span>
                  <span class="pair-section">{otherSection}</span>
                </li>
              {/each}
            </ol>
          {/if}
        </div>
      {:else}
        <div class="panel">
          <h2 class="panel-h">Top {Math.min(TOP_PAIRS_LIMIT, result.topPairs.length)} pairs by similarity</h2>
          <p class="panel-sub">
            {mode === 'co-citation'
              ? variant === 'cites-only'
                ? '(academic-style — cites only)'
                : '(any-edge co-citation)'
              : '(bibliographic coupling — shared out-neighbours)'}
          </p>
          {#if result.topPairs.length === 0}
            <p class="muted">No pairs cleared the threshold for this mode.</p>
          {:else}
            <ol class="pair-list">
              {#each result.topPairs as p}
                <li class:disagree={!p.taxonomyAgrees && p.similarity > DISAGREEMENT_SIM_THRESHOLD}>
                  <span class="pair-name">
                    <strong>{p.aName}</strong> ↔ <strong>{p.bName}</strong>
                  </span>
                  <span class="pair-meta">
                    <span class="pair-sim">sim {fmtSim(p.similarity)}</span>
                    <span class="pair-shared">· {p.sharedCount} shared</span>
                  </span>
                  <span class="pair-section" class:disagree-text={!p.taxonomyAgrees}>
                    {p.taxonomyAgrees ? p.aSection : `${p.aSection} ⤬ ${p.bSection}`}
                  </span>
                </li>
              {/each}
            </ol>
          {/if}
        </div>
      {/if}
    </aside>
  </div>

  <section class="disagreement-section" aria-label="Taxonomy disagreements">
    <h2 class="disagree-h">
      Disagreement panel
      <span class="disagree-sub">
        community-close but taxonomy-far · {disagreementCount} pairs · similarity &gt; {DISAGREEMENT_SIM_THRESHOLD}
      </span>
    </h2>
    <p class="disagree-prose">
      These are pairs the community pairs tightly together
      (co-citation or shared lineage) <em>despite</em> our hand-built
      taxonomy placing them in different sections. Each row is a
      candidate for either a taxonomy refinement (the catalog missed a
      cluster), or a research question (why does the community pair
      them?).
    </p>
    {#if disagreementCount === 0}
      <p class="muted">No cross-section pairs cleared the {DISAGREEMENT_SIM_THRESHOLD} threshold for this mode.</p>
    {:else}
      <div class="disagree-table-wrap">
        <table class="disagree-table">
          <thead>
            <tr>
              <th>Pair A</th>
              <th>Section A</th>
              <th>Pair B</th>
              <th>Section B</th>
              <th class="num">Similarity</th>
              <th class="num">Shared</th>
            </tr>
          </thead>
          <tbody>
            {#each result.disagreementPairs.slice(0, 50) as p}
              <tr>
                <td><a href={tableHref(p.aName)}>{p.aName}</a></td>
                <td class="section-cell">{p.aSection}</td>
                <td><a href={tableHref(p.bName)}>{p.bName}</a></td>
                <td class="section-cell">{p.bSection}</td>
                <td class="num">{fmtSim(p.similarity)}</td>
                <td class="num">{p.sharedCount}</td>
              </tr>
            {/each}
          </tbody>
        </table>
        {#if result.disagreementPairs.length > 50}
          <p class="muted disagree-foot">
            Showing top 50 of {disagreementCount}.
          </p>
        {/if}
      </div>
    {/if}
  </section>

  <footer class="cc-footer">
    <a href="{base}/analyses">← Analyses hub</a>
    <span class="muted">
      Bibliometric pivot of <code>data/landscape.edges.json</code>. Helper in
      <code>$lib/analyses/co-citation.ts</code>. See issue #45 for spec.
    </span>
  </footer>
</main>

<style>
  .cc-page {
    max-width: 1600px;
    margin: 0 auto;
    padding: 24px 12px 64px;
    color: #e8e8e8;
  }
  .cc-header { margin-bottom: 18px; }
  .crumb { margin: 0 0 8px 0; font-size: 13px; }
  .crumb a { color: #aaa; text-decoration: none; }
  .crumb a:hover { color: #e8e8e8; }
  .cc-header h1 {
    font-size: 28px;
    margin: 0 0 10px 0;
    letter-spacing: -0.01em;
  }
  .cc-intro {
    color: #c9c9c9;
    max-width: 920px;
    margin: 0 0 12px 0;
    line-height: 1.6;
    font-size: 14px;
  }
  .cc-intro strong { color: #e8e8e8; }
  .cc-intro em { color: #c0c0c0; font-style: italic; }
  .cc-intro a { color: #d4845f; }
  .cc-callout {
    background: #14191d;
    border-left: 3px solid #d4845f;
    padding: 10px 14px;
    border-radius: 0 4px 4px 0;
  }
  .cc-scope-note {
    color: #999;
    font-size: 13px;
  }
  code {
    font-family: 'SF Mono', 'Menlo', Consolas, monospace;
    font-size: 12.5px;
    background: #1f1f1f;
    padding: 1px 5px;
    border-radius: 3px;
    color: #d4d4d4;
  }

  .controls {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 0 0 14px 0;
  }
  .ctrl-row {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    align-items: center;
  }
  .ctrl-group {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .ctrl-group.dim {
    opacity: 0.45;
  }
  .ctrl-label {
    color: #aaa;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .chip-row {
    display: flex;
    gap: 4px;
  }
  .chip {
    background: #1d1d1d;
    color: #c9d1d9;
    border: 1px solid #333;
    border-radius: 999px;
    padding: 4px 12px;
    font-size: 12.5px;
    cursor: pointer;
    font-family: inherit;
  }
  .chip:hover:not(:disabled) {
    border-color: #d4845f;
    color: #d4845f;
  }
  .chip.on {
    background: #2a1f17;
    border-color: #d4845f;
    color: #e8c4ad;
  }
  .chip:disabled {
    cursor: not-allowed;
    color: #6e7681;
  }

  .layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 12px;
    margin: 0 0 24px 0;
    min-height: 560px;
  }
  .canvas-wrap {
    position: relative;
    border: 1px solid #21262d;
    border-radius: 8px;
    background: #0d1117;
    overflow: hidden;
    min-height: 560px;
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
  .legend-overlay {
    position: absolute;
    top: 10px;
    right: 10px;
    background: rgba(13, 17, 23, 0.85);
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 11px;
    color: #c9d1d9;
    z-index: 4;
    pointer-events: none;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .legend-line {
    display: inline-block;
    width: 18px;
    height: 2px;
    border-radius: 1px;
  }
  .legend-line.dash {
    background: repeating-linear-gradient(
      to right,
      #d4845f 0 4px,
      transparent 4px 7px
    ) !important;
    height: 2px;
  }
  .legend-note {
    color: #6e7681;
    font-size: 10.5px;
    font-style: italic;
  }

  .side {
    overflow-y: auto;
    max-height: 700px;
  }
  .panel {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 14px 16px;
  }
  .panel-h {
    margin: 0 0 4px 0;
    font-size: 15px;
    color: #e8e8e8;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .panel-name {
    flex: 1;
    font-weight: 600;
  }
  .panel-close {
    background: transparent;
    color: #8b949e;
    border: none;
    font-size: 1.2rem;
    cursor: pointer;
    line-height: 1;
    padding: 0 4px;
  }
  .panel-close:hover { color: #f0f6fc; }
  .panel-sub {
    color: #888;
    font-size: 12px;
    margin: 0 0 12px 0;
  }
  .panel-sub a {
    color: #d4845f;
    text-decoration: none;
  }
  .panel-sub a:hover { text-decoration: underline; }
  .panel-sub-h {
    margin: 12px 0 6px 0;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #8b949e;
  }
  .pair-list {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .pair-list li {
    background: #1d1d1d;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 12.5px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .pair-list li.disagree {
    border-left: 3px solid #d4845f;
  }
  .pair-name {
    color: #e8e8e8;
    line-height: 1.4;
  }
  .pair-name strong { font-weight: 600; }
  .pair-meta {
    color: #c89a5a;
    font-size: 11.5px;
    font-variant-numeric: tabular-nums;
  }
  .pair-shared { color: #888; }
  .pair-section {
    color: #8b949e;
    font-size: 11px;
    font-style: italic;
  }
  .disagree-text { color: #d4845f; font-style: normal; }

  .disagreement-section {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-left: 3px solid #d4845f;
    border-radius: 8px;
    padding: 16px 18px;
    margin: 0 0 24px 0;
  }
  .disagree-h {
    margin: 0 0 6px 0;
    font-size: 15px;
    color: #e8c4ad;
    font-weight: 600;
  }
  .disagree-sub {
    color: #888;
    font-size: 12px;
    font-weight: 400;
    margin-left: 6px;
  }
  .disagree-prose {
    color: #c9c9c9;
    font-size: 13px;
    line-height: 1.6;
    margin: 0 0 14px 0;
    max-width: 880px;
  }
  .disagree-prose em { color: #c0c0c0; font-style: italic; }
  .disagree-table-wrap {
    overflow-x: auto;
    border: 1px solid #232323;
    border-radius: 6px;
  }
  .disagree-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
    background: #161616;
  }
  .disagree-table th {
    text-align: left;
    background: #1f1f1f;
    color: #aaa;
    padding: 7px 10px;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.03em;
    border-bottom: 1px solid #2a2a2a;
  }
  .disagree-table td {
    padding: 7px 10px;
    border-top: 1px solid #1f1f1f;
    vertical-align: top;
    color: #d4d4d4;
  }
  .disagree-table tr:hover td {
    background: #1d1d1d;
  }
  .disagree-table a {
    color: #d4845f;
    text-decoration: none;
  }
  .disagree-table a:hover { text-decoration: underline; }
  .section-cell {
    color: #8b949e;
    font-style: italic;
    font-size: 12px;
  }
  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    color: #c89a5a;
  }
  .disagree-foot {
    padding: 8px 10px;
    margin: 0;
    background: #161616;
    border-top: 1px solid #232323;
  }

  .cc-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    padding-top: 18px;
    border-top: 1px solid #232323;
    font-size: 12.5px;
  }
  .cc-footer a {
    color: #d4845f;
    text-decoration: none;
  }
  .cc-footer a:hover { text-decoration: underline; }
  .muted {
    color: #777;
  }

  @media (max-width: 960px) {
    .layout {
      grid-template-columns: 1fr;
    }
    .side {
      max-height: none;
    }
  }
</style>
