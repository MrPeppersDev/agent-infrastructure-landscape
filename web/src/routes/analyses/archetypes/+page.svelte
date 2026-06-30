<script lang="ts">
  import SeoHead from '$lib/components/SeoHead.svelte';

  // /analyses/archetypes — taxonomy archetypes, round-2 upgrade.
  //
  // Clusters all records by their 7-axis primary-only taxonomy fingerprint
  // and surfaces the recurring recipes. Round 2 (issue #25 follow-up):
  //
  //   - Exemplar-driven archetype names (`The Mem0 recipe`)
  //   - Near-archetype clustering for singletons (Hamming-1 absorption)
  //   - Section + tier multi-select filters for the card grid
  //   - Per-archetype value-prop + funding/citation medians
  //   - Gap-candidate prose (deterministic, 2-3 sentences, no LLM)
  //   - Drill-through links from every card / variant / gap → main table
  //
  // The page is still one Svelte file: every section is presentational and
  // reads from the same pure helpers in $lib/analyses/archetypes. No
  // charting library — all graphics are CSS or inline SVG.

  import { base } from '$app/paths';
  import type { Edge, LandscapeRecord } from '$lib/types';
  import {
    AXES,
    buildBundle,
    formatCount,
    formatFunding,
    parseFingerprint,
    valuePropFor,
    type Archetype
  } from '$lib/analyses/archetypes';

  let {
    data
  }: { data: { records: LandscapeRecord[]; edges: Edge[] } } = $props();

  const TOP_N = 12;

  const bundle = $derived(
    buildBundle(data.records, data.edges, {
      topN: TOP_N,
      nearThreshold: 1,
      gapFloor: 25,
      gapLimit: 8
    })
  );

  const archetypes = $derived(bundle.archetypes);
  const summary = $derived(bundle.summary);
  const topArchetypes = $derived(archetypes.slice(0, TOP_N));
  const recurringCount = $derived(
    archetypes.filter((a) => a.members.length >= 2).length
  );
  const recordById = $derived(
    new Map(data.records.map((r) => [r.id, r]))
  );

  // Effective long-tail count after near-archetype absorption.
  const absorbedSingletons = $derived(bundle.near.absorbed.length);
  const unattachedSingletons = $derived(bundle.near.unattached.length);
  const distinctShapesAfterAbsorb = $derived(
    recurringCount + unattachedSingletons
  );

  // --- Filters ----------------------------------------------------------

  let selectedTiers = $state<Set<number>>(new Set());
  let selectedSections = $state<Set<string>>(new Set());

  // Distinct section vocabulary observed across top archetypes — used to
  // populate the filter chip list. We use top-N here (not all sections in
  // the catalog) so the filter is contextual: it only offers sections that
  // actually appear in a top archetype.
  const sectionVocab = $derived.by(() => {
    const set = new Set<string>();
    for (const a of topArchetypes) {
      for (const s of a.sections.keys()) set.add(s);
    }
    return [...set].sort((a, b) => a.localeCompare(b));
  });

  function toggleTier(t: number) {
    const next = new Set(selectedTiers);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    selectedTiers = next;
  }
  function toggleSection(s: string) {
    const next = new Set(selectedSections);
    if (next.has(s)) next.delete(s);
    else next.add(s);
    selectedSections = next;
  }
  function clearFilters() {
    selectedTiers = new Set();
    selectedSections = new Set();
  }

  function archetypeMatches(a: Archetype): boolean {
    if (selectedTiers.size > 0) {
      let any = false;
      for (const t of selectedTiers) {
        if ((a.tiers.get(t) ?? 0) > 0) {
          any = true;
          break;
        }
      }
      if (!any) return false;
    }
    if (selectedSections.size > 0) {
      let any = false;
      for (const s of selectedSections) {
        if ((a.sections.get(s) ?? 0) > 0) {
          any = true;
          break;
        }
      }
      if (!any) return false;
    }
    return true;
  }

  const visibleArchetypes = $derived(
    topArchetypes.filter((a) => archetypeMatches(a))
  );

  // --- Drill-through link helpers ---------------------------------------

  /**
   * Build a /?fp=... link into the main table. We re-use the existing `q`
   * search parameter because the table's search-by-name already accepts
   * arbitrary strings; the user-visible chip will read the archetype's
   * exemplar name. If a future iteration of the table grows a real
   * fingerprint filter, this is the one helper to update.
   */
  function tableHrefForArchetype(a: Archetype): string {
    // The most-recognisable member is also the exemplar (usually).
    const ex = bundle.exemplars.get(a.fingerprint);
    const q = ex?.name ?? a.memberNames[0] ?? '';
    return `${base}/?q=${encodeURIComponent(q)}`;
  }
  function tableHrefForName(name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  // Tier colour scale — matches /sections + /leaderboards.
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

  // Stable colour per axis.
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
  <SeoHead
    title="Taxonomy Archetypes in AI Memory Systems"
    description="Recurring archetypes in AI agent memory — the dominant combinations of storage, retrieval, persistence, and update axes across the 912-system catalog."
    path="/analyses/archetypes"
    ogType="article"
  />
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
        <strong>{summary.total}</strong> systems; top
        <strong>{summary.topN}</strong> cover
        <strong>{(summary.topNCoverage * 100).toFixed(1)}%</strong> of the
        catalog. <strong>{recurringCount}</strong> recurring recipes
        ({summary.singletons} singletons in the long tail —
        {absorbedSingletons} absorb as near-variants of recurring archetypes,
        leaving {unattachedSingletons} genuinely bespoke designs).
      </p>
    </div>
    <nav class="nav">
      <a href="{base}/">Table</a>
      <a href="{base}/sections">Sections</a>
    </nav>
  </header>

  <!-- Narrative + methodology -->
  <section class="explain-grid">
    <article class="explain-card">
      <h2 class="ex-h">What is an archetype?</h2>
      <p>
        Every record's seven taxonomy axes —
        <code>storage</code> · <code>retrieval</code> ·
        <code>persistence</code> · <code>update</code> · <code>unit</code> ·
        <code>governance</code> · <code>conflict</code> — collapse to a
        single <em>fingerprint</em>: the primary value on each axis.
        Systems with the same fingerprint share a "recipe". Recipes that
        recur many times are the memory landscape's <em>archetypes</em>;
        fingerprints with only one member are bespoke designs.
      </p>
    </article>

    <article class="explain-card">
      <h2 class="ex-h">Methodology</h2>
      <p>
        We use the <em>primary</em> value on each axis, never the full
        array — multi-value axes legitimately exist (e.g. vector+graph
        storage) but hashing the full set would split the canonical
        recipe across half a dozen near-duplicates. Two systems are in
        the same archetype only when every one of the seven primary axis
        values matches; even one-axis disagreement
        (<code>graph + traversal</code> vs
        <code>graph + injection</code>) splits a recipe in two.
      </p>
      <p>
        The "Hamming distance" clustering takes singletons (recipes with
        one member) and attaches them to the closest recurring archetype
        if they differ on a single axis. This collapses
        <strong>{absorbedSingletons}</strong>
        of the {summary.singletons} singletons into
        "near-variants" of existing recipes.
      </p>
    </article>

    <article class="explain-card">
      <h2 class="ex-h">So what?</h2>
      <ul class="so-what">
        <li>
          <strong>Top archetypes</strong> are well-travelled recipes — low
          risk, lots of prior art. If your design lands in one of them,
          assume you're competing on execution, not invention.
        </li>
        <li>
          <strong>Singletons</strong> are either novel-and-interesting or
          one-off experiments. They become most actionable when paired
          with the
          <a href="{base}/analyses/influence">influence-vs-adoption</a>
          view: cited-but-not-adopted singletons are research bets the
          market hasn't followed.
        </li>
        <li>
          <strong>Gap candidates</strong> are the white-space: every axis
          value is mainstream, but nobody has built this specific
          combination twice. The most interesting are the ones with a
          credible Hamming-1 neighbour you could "fork".
        </li>
      </ul>
    </article>
  </section>

  <!-- Filters -->
  <section class="filters" aria-label="Filter archetype cards">
    <div class="filter-block">
      <span class="fb-h">Tier</span>
      <div class="chips">
        {#each [1, 2, 3, 4, 5] as t}
          <button
            type="button"
            class="chip"
            class:on={selectedTiers.has(t)}
            style="--c:{TIER_COLORS[t]}"
            onclick={() => toggleTier(t)}
            aria-pressed={selectedTiers.has(t)}
          >
            T{t}
          </button>
        {/each}
      </div>
    </div>
    <div class="filter-block grow">
      <span class="fb-h">Section</span>
      <div class="chips section-chips">
        {#each sectionVocab as s}
          <button
            type="button"
            class="chip section-chip"
            class:on={selectedSections.has(s)}
            onclick={() => toggleSection(s)}
            aria-pressed={selectedSections.has(s)}
            title={s}
          >
            {s}
          </button>
        {/each}
      </div>
    </div>
    {#if selectedTiers.size > 0 || selectedSections.size > 0}
      <button class="clear" type="button" onclick={clearFilters}>
        Clear ×
      </button>
    {/if}
  </section>

  {#if visibleArchetypes.length === 0}
    <p class="empty">
      No archetypes match the current filters. Try clearing one of the
      facets above.
    </p>
  {/if}

  <!-- Top-K archetype cards -->
  <section class="grid">
    {#each visibleArchetypes as a, idx (a.fingerprint)}
      {@const realIdx = topArchetypes.indexOf(a)}
      {@const parts = parseFingerprint(a.fingerprint)}
      {@const name = bundle.names.get(a.fingerprint) ?? a.fingerprint}
      {@const nums = bundle.numerics.get(a.fingerprint)}
      {@const variants = bundle.near.byAnchor.get(a.fingerprint) ?? []}
      {@const valueProp = valuePropFor(a.fingerprint)}
      {@const exemplar = bundle.exemplars.get(a.fingerprint)}
      <article class="card">
        <header class="card-hdr">
          <div class="card-title">
            <span class="rank">#{realIdx + 1}</span>
            <h2>{name}</h2>
          </div>
          <div class="card-counts">
            <span class="count">{a.members.length}</span>
            <span class="pctv">{pct(a.members.length, summary.total)}</span>
          </div>
        </header>

        <p class="value-prop">{valueProp}</p>

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

        <!-- Metrics row -->
        <div class="metrics">
          <div class="metric">
            <span class="metric-h">Median funding</span>
            <span class="metric-v">{formatFunding(nums?.funding.median ?? null)}</span>
            <span class="metric-sub">
              {nums?.funding.n ?? 0} of {a.members.length}
            </span>
          </div>
          <div class="metric">
            <span class="metric-h">Median citations</span>
            <span class="metric-v">{formatCount(nums?.citations.median ?? null)}</span>
            <span class="metric-sub">
              {nums?.citations.n ?? 0} of {a.members.length}
            </span>
          </div>
          {#if exemplar}
            <div class="metric metric-ex">
              <span class="metric-h">Exemplar</span>
              <a class="metric-v ex-link" href={tableHrefForName(exemplar.name)}>
                {exemplar.name}
              </a>
              <span class="metric-sub">T{exemplar.tier}</span>
            </div>
          {/if}
        </div>

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
                  href={tableHrefForName(nm)}
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

        <!-- Near-variants -->
        {#if variants.length > 0}
          <div class="rowblock variants">
            <span class="block-h">
              {variants.length} near-variant{variants.length > 1 ? 's' : ''}
              <span class="variant-sub">
                — differ on one axis from the canonical recipe
              </span>
            </span>
            <ul class="variant-list">
              {#each variants.slice(0, 5) as v}
                <li class="variant">
                  <a href={tableHrefForName(v.memberName)} class="v-name"
                    >{v.memberName}</a
                  >
                  {#if v.differingAxis}
                    <span class="v-axis">
                      <span class="v-axis-key">{v.differingAxis}:</span>
                      <span class="v-axis-old">{v.anchorValue}</span>
                      <span class="v-axis-arrow">→</span>
                      <span class="v-axis-new">{v.differingValue}</span>
                    </span>
                  {/if}
                </li>
              {/each}
              {#if variants.length > 5}
                <li class="variant-extra">
                  + {variants.length - 5} more
                </li>
              {/if}
            </ul>
          </div>
        {/if}

        <!-- Drill-through footer -->
        <div class="card-drill">
          <a class="drill-link" href={tableHrefForArchetype(a)}>
            Filter table to this archetype →
          </a>
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
      of the catalog. <strong>{summary.singletons}</strong> have only one
      member.
    </p>
    <p>
      After Hamming-1 absorption: <strong>{absorbedSingletons}</strong>
      singletons (<strong>{pct(absorbedSingletons, summary.singletons)}</strong>)
      attach to a recurring archetype as near-variants, leaving
      <strong>{unattachedSingletons}</strong> genuinely bespoke designs.
      The long tail collapses from {summary.distinct} distinct shapes to
      roughly <strong>{distinctShapesAfterAbsorb}</strong>
      (recurring archetypes + unattached singletons).
    </p>
    <p class="muted">
      Threshold = 1 because that's the most legible boundary: "this
      system is the canonical recipe except for one axis" is easy to
      describe; distance ≥ 2 starts being a genuinely different shape.
      Anchor set = every archetype with ≥ 2 members, not just the
      top-12, so distance-1 singletons can attach to small-but-not-tiny
      recipes further down the list.
    </p>
  </section>

  <!-- White-space gap panel with prose -->
  {#if bundle.gaps.length > 0}
    <section class="gaps">
      <h2>White-space candidates</h2>
      <p class="gap-explainer">
        Singletons whose individual axis values are common elsewhere — the
        building blocks exist in the literature, but this specific
        combination has never been built twice. The
        <em>min axis popularity</em>
        is the rarest axis value in the recipe, measured across the whole
        catalog; high min means every part is mainstream and what's
        missing is the assembly.
      </p>
      <div class="gap-cards">
        {#each bundle.gaps as g, gi}
          <article class="gap-card">
            <header class="gap-hdr">
              <span class="gap-rank">#{gi + 1}</span>
              <a class="gap-system" href={tableHrefForName(g.member)}>
                {g.member}
              </a>
              <span class="gap-pop">
                min&nbsp;{g.minAxisPopularity} · sum&nbsp;{g.sumAxisPopularity}
              </span>
            </header>
            <p class="gap-fp">{g.fingerprint}</p>
            <p class="gap-prose">{g.prose}</p>
            {#if g.closest.length > 0}
              <ul class="gap-closest">
                {#each g.closest as c}
                  <li>
                    <a href={tableHrefForName(c.name)}>{c.name}</a>
                    <span class="gap-diff">
                      differs on <code>{c.diffAxis}</code>
                    </span>
                  </li>
                {/each}
              </ul>
            {/if}
          </article>
        {/each}
      </div>
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
  .crumb a:hover {
    color: #58a6ff;
  }
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
    max-width: 880px;
    line-height: 1.5;
  }
  .sub strong {
    color: #f0f6fc;
    font-weight: 600;
  }
  .nav {
    display: flex;
    gap: 14px;
  }
  .nav a {
    color: #58a6ff;
    font-size: 0.85rem;
    text-decoration: none;
  }
  .nav a:hover {
    text-decoration: underline;
  }

  /* --- Explain grid (header narrative) --- */
  .explain-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
  }
  .explain-card {
    border: 1px solid #21262d;
    border-radius: 6px;
    background: #0d1117;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .ex-h {
    margin: 0 0 4px;
    font-size: 0.8rem;
    color: #d29922;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .explain-card p {
    margin: 0;
    color: #c9d1d9;
    font-size: 0.83rem;
    line-height: 1.55;
  }
  .explain-card p + p {
    margin-top: 4px;
  }
  .explain-card code {
    background: #161b22;
    padding: 1px 5px;
    border-radius: 3px;
    color: #d29922;
    font-size: 0.78rem;
  }
  .explain-card em {
    color: #f0f6fc;
    font-style: normal;
    font-weight: 600;
  }
  .so-what {
    margin: 0;
    padding: 0 0 0 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 0.83rem;
    color: #c9d1d9;
    line-height: 1.5;
  }
  .so-what strong {
    color: #f0f6fc;
  }
  .so-what a {
    color: #58a6ff;
    text-decoration: none;
  }
  .so-what a:hover {
    text-decoration: underline;
  }

  /* --- Filters --- */
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: flex-start;
    border: 1px solid #21262d;
    background: #0d1117;
    border-radius: 6px;
    padding: 10px 12px;
  }
  .filter-block {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .filter-block.grow {
    flex: 1 1 360px;
    min-width: 0;
  }
  .fb-h {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6e7681;
    font-weight: 600;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .section-chips {
    max-height: 84px;
    overflow-y: auto;
  }
  .chip {
    background: transparent;
    border: 1px solid #30363d;
    color: #c9d1d9;
    font-size: 0.78rem;
    padding: 3px 8px;
    border-radius: 999px;
    cursor: pointer;
    font-family: inherit;
    transition: background 100ms, border-color 100ms, color 100ms;
  }
  .chip:hover {
    border-color: #58a6ff;
  }
  .chip.on {
    background: var(--c, #58a6ff);
    border-color: var(--c, #58a6ff);
    color: #0d1117;
    font-weight: 600;
  }
  .section-chip {
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    --c: #58a6ff;
  }
  .clear {
    background: transparent;
    border: 1px solid #30363d;
    color: #8b949e;
    font-size: 0.78rem;
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    align-self: flex-end;
    font-family: inherit;
  }
  .clear:hover {
    color: #f0f6fc;
    border-color: #58a6ff;
  }

  .empty {
    color: #8b949e;
    font-size: 0.88rem;
    padding: 24px;
    text-align: center;
    border: 1px dashed #30363d;
    border-radius: 6px;
    margin: 0;
  }

  /* --- Grid of archetype cards --- */
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(440px, 1fr));
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

  .value-prop {
    margin: 0;
    color: #c9d1d9;
    font-size: 0.82rem;
    line-height: 1.5;
    border-left: 2px solid #d29922;
    padding: 2px 0 2px 10px;
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

  /* --- Metrics row --- */
  .metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    background: #161b22;
    border-radius: 4px;
    padding: 8px 10px;
  }
  .metric {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .metric-h {
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6e7681;
    font-weight: 600;
  }
  .metric-v {
    color: #f0f6fc;
    font-weight: 600;
    font-size: 0.85rem;
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .metric-sub {
    color: #6e7681;
    font-size: 0.7rem;
    margin-top: 1px;
  }
  .ex-link {
    color: #58a6ff !important;
    text-decoration: none;
  }
  .ex-link:hover {
    text-decoration: underline;
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
  .variant-sub {
    text-transform: none;
    letter-spacing: 0;
    color: #6e7681;
    font-weight: 400;
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
  .ex-list a:hover {
    text-decoration: underline;
  }
  .ex-list li:not(:last-child)::after {
    content: '·';
    color: #30363d;
    margin-left: 8px;
  }
  .ex-extra {
    color: #6e7681;
    font-style: italic;
  }

  /* --- Variant list (near-archetype) --- */
  .variants {
    border-top: 1px dashed #21262d;
    padding-top: 8px;
    margin-top: 4px;
  }
  .variant-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 0.78rem;
  }
  .variant {
    display: flex;
    align-items: baseline;
    gap: 8px;
    min-width: 0;
  }
  .v-name {
    color: #58a6ff;
    text-decoration: none;
    flex-shrink: 0;
  }
  .v-name:hover {
    text-decoration: underline;
  }
  .v-axis {
    color: #8b949e;
    font-size: 0.72rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .v-axis-key {
    color: #d29922;
  }
  .v-axis-old {
    color: #6e7681;
    text-decoration: line-through;
  }
  .v-axis-arrow {
    color: #6e7681;
    margin: 0 3px;
  }
  .v-axis-new {
    color: #c9d1d9;
    font-weight: 600;
  }
  .variant-extra {
    color: #6e7681;
    font-style: italic;
    font-size: 0.74rem;
  }

  /* --- Drill-through --- */
  .card-drill {
    border-top: 1px solid #21262d;
    margin-top: 4px;
    padding-top: 8px;
  }
  .drill-link {
    color: #58a6ff;
    font-size: 0.78rem;
    text-decoration: none;
  }
  .drill-link:hover {
    text-decoration: underline;
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
    max-width: 880px;
  }
  .longtail .muted {
    color: #8b949e;
    font-size: 0.82rem;
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
    margin: 0 0 12px;
    color: #8b949e;
    font-size: 0.82rem;
    line-height: 1.55;
    max-width: 880px;
  }
  .gap-explainer em {
    color: #c9d1d9;
    font-style: normal;
    font-weight: 600;
  }
  .gap-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 10px;
  }
  .gap-card {
    border: 1px solid #21262d;
    background: #0d1117;
    border-radius: 6px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
  }
  .gap-hdr {
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
  }
  .gap-rank {
    color: #6e7681;
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
  }
  .gap-system {
    color: #58a6ff;
    font-weight: 600;
    text-decoration: none;
    font-size: 0.92rem;
  }
  .gap-system:hover {
    text-decoration: underline;
  }
  .gap-pop {
    color: #6e7681;
    font-size: 0.72rem;
    font-variant-numeric: tabular-nums;
    margin-left: auto;
  }
  .gap-fp {
    margin: 0;
    color: #8b949e;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.72rem;
    word-break: break-word;
  }
  .gap-prose {
    margin: 0;
    color: #c9d1d9;
    font-size: 0.82rem;
    line-height: 1.55;
  }
  .gap-closest {
    list-style: none;
    margin: 0;
    padding: 6px 0 0;
    border-top: 1px dashed #21262d;
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 0.76rem;
  }
  .gap-closest a {
    color: #58a6ff;
    text-decoration: none;
  }
  .gap-closest a:hover {
    text-decoration: underline;
  }
  .gap-diff {
    color: #6e7681;
    margin-left: 6px;
  }
  .gap-diff code {
    color: #d29922;
    background: transparent;
    padding: 0;
    font-size: inherit;
  }
</style>
