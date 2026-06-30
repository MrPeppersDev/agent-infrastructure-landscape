<script lang="ts">
  // Survivorship map (issue #23). Classifies every record into
  // active / stale / abandoned / unknown by freshness signal, with research
  // artefacts (T3+T4+T5) split into their own bucket because "active dev" is
  // not the right frame for a paper.
  //
  // Round 23 upgrade (this revision):
  //   - Narrative header + methodology callout (was a thin lede).
  //   - "So-what" interpretation panel per bucket.
  //   - Tier + section multi-select filters that recompute every count.
  //   - Unknown bucket subdivided into 4 sub-buckets with a stacked breakdown.
  //   - "Abandoned but cited" promoted to a card grid with lineage labels.
  //   - Per-section status bar (proportions, sortable by aging score).
  //   - Active-cohort created-quarter histogram.
  //   - Drill links to main table + /analyses/influence per row.
  //
  // All compute is pure helpers in $lib/analyses/survivorship.

  import SeoHead from '$lib/components/SeoHead.svelte';
  import { base } from '$app/paths';
  import type { LandscapeRecord, Edge, Tier } from '$lib/types';
  import type { Lineage } from '$lib/lineages';
  import {
    classifyAll,
    countBuckets,
    countUnknownSubs,
    bySection,
    sectionAgingScore,
    influentialAbandoned,
    activeCohortHistogram,
    buildInboundMaps,
    SURVIVORSHIP_ORDER,
    SURVIVORSHIP_LABELS,
    SURVIVORSHIP_COLOURS,
    UNKNOWN_SUB_ORDER,
    UNKNOWN_SUB_LABELS,
    UNKNOWN_SUB_SHORT,
    UNKNOWN_SUB_COLOURS,
    UNKNOWN_SUB_INTERPRETATION,
    type Survivorship
  } from '$lib/analyses/survivorship';

  let {
    data
  }: {
    data: { records: LandscapeRecord[]; edges: Edge[]; lineages: Lineage[] };
  } = $props();

  // --- Filter state -----------------------------------------------------
  // Multi-select; empty = no constraint.
  let selectedTiers = $state<Set<Tier>>(new Set());
  let selectedSections = $state<Set<string>>(new Set());

  const allSections = $derived.by(() => {
    const set = new Set<string>();
    for (const r of data.records) {
      const p = r.sections.find((s) => s.primary);
      set.add(p?.section ?? r.sections[0]?.section ?? 'Uncategorised');
    }
    return [...set].sort();
  });

  function recordPasses(r: LandscapeRecord): boolean {
    if (selectedTiers.size > 0 && !selectedTiers.has(r.tier)) return false;
    if (selectedSections.size > 0) {
      const p = r.sections.find((s) => s.primary);
      const sec = p?.section ?? r.sections[0]?.section ?? 'Uncategorised';
      if (!selectedSections.has(sec)) return false;
    }
    return true;
  }

  const filteredRecords = $derived(data.records.filter(recordPasses));

  function toggleTier(t: Tier) {
    const next = new Set(selectedTiers);
    next.has(t) ? next.delete(t) : next.add(t);
    selectedTiers = next;
  }
  function toggleSection(s: string) {
    const next = new Set(selectedSections);
    next.has(s) ? next.delete(s) : next.add(s);
    selectedSections = next;
  }
  function clearFilters() {
    selectedTiers = new Set();
    selectedSections = new Set();
  }

  // --- Classification pass (over filtered records) ---------------------
  const classifications = $derived(classifyAll(filteredRecords));
  const counts = $derived(countBuckets(classifications));
  const unknownSubs = $derived(countUnknownSubs(classifications));
  const sections = $derived(bySection(filteredRecords, classifications));

  // --- Inbound edge maps + lineage index --------------------------------
  // Inbound counts are computed over the FULL edge set (filtering shouldn't
  // erase the fact that record X is cited by Y if Y is filtered out — the
  // citation still exists; the user's filter just affects which abandoned
  // records we display).
  const inbound = $derived(buildInboundMaps(data.edges));
  const lineageByMember = $derived.by(() => {
    const m = new Map<string, string>();
    for (const l of data.lineages) {
      for (const id of l.members) m.set(id, l.name);
    }
    return m;
  });

  const influential = $derived(
    influentialAbandoned(
      filteredRecords,
      classifications,
      inbound.integrations,
      inbound.citations,
      lineageByMember
    )
  );

  // --- Per-section view: limit to sections with >= 2 rows --------------
  const visibleSections = $derived(sections.filter((s) => s.total >= 2));

  // --- Active cohort timeline -------------------------------------------
  const activeCohort = $derived(activeCohortHistogram(filteredRecords, classifications));
  const activeCohortMax = $derived(
    activeCohort.reduce((m, b) => Math.max(m, b.count), 0)
  );

  // --- Highlight toggle (counter -> dim non-status dots) ---------------
  let highlight = $state<Survivorship | null>(null);

  function tooltip(rec: LandscapeRecord, statusLabel: string, signal: string): string {
    return `${rec.name} — ${statusLabel}\n${signal}`;
  }

  function pct(n: number, total: number): string {
    if (total === 0) return '0%';
    return `${Math.round((n / total) * 100)}%`;
  }

  function tableHref(name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  function influenceHref(name: string): string {
    // /analyses/influence is a faceted view — the page will resolve
    // hover/highlight from the search param if present.
    return `${base}/analyses/influence?focus=${encodeURIComponent(name)}`;
  }

  // Interpretation copy for the "so what" panel. Kept here (not in the
  // lib module) because it's view-layer prose, not classification logic.
  const BUCKET_SO_WHAT: Record<Survivorship, { title: string; body: string }> = {
    active: {
      title: 'Active',
      body:
        'A release or commit in the last 12 months. Use confidently — the project is shipping. The Active cohort is the working answer to "what is alive in this space right now".'
    },
    stale: {
      title: 'Stale',
      body:
        'Last signal 12–24 months ago. Re-verify the README, changelog, and recent issues before recommending. A stale row is often a project on a slow cadence rather than a dead one, but the burden of proof is on the catalog user.'
    },
    abandoned: {
      title: 'Abandoned',
      body:
        'No signal in 24+ months. Treat as historical: it shipped, it influenced things, but production deployments should not depend on it being maintained. The "Abandoned but cited" card below surfaces the abandoned rows the rest of the catalog still builds on.'
    },
    unknown: {
      title: 'Unknown',
      body:
        'No parseable freshness signal in our cells — most often because the record is a closed-source product that does not publish a changelog. This is a limit of our signal, not a property of the system. The breakdown below shows the structure.'
    },
    research: {
      title: 'Research',
      body:
        'Tier 3–5: papers, techniques, theoretical proposals. "Active development" is the wrong frame — these contribute ideas, not maintained codebases. Where a research record has a stale public repo AND is still cited, it surfaces in the "Abandoned but cited" card.'
    }
  };

  // Per-section aging — sort by aging score desc so the most-aged section
  // surfaces first when the user opens the section breakdown.
  const sectionsByAging = $derived(
    [...visibleSections]
      .map((s) => ({ section: s, aging: sectionAgingScore(s) }))
      .sort((a, b) => b.aging - a.aging || b.section.total - a.section.total)
  );
</script>

<svelte:head>
  <SeoHead
    title="Survivorship & Staleness Map: Is Your AI Memory System Still Maintained?"
    description="Classify every system into active, stale, abandoned, or unknown by freshness signals. Spot dead-but-cited systems."
    path="/analyses/survivorship"
    ogType="article"
  />
</svelte:head>

<header class="page-header">
  <p class="breadcrumb">
    <a href="{base}/analyses">Analyses</a> · Survivorship map
  </p>
  <h1>Survivorship / staleness map</h1>
  <p class="lede">
    "Is this project still alive?" — answered per row, across the whole
    catalog. Every record is classified by the freshness of the most
    recent date we could parse from its cells. Use this view to size the
    fraction of the field that is actively shipping versus historical,
    and to spot dead-but-still-cited systems whose ideas remain load-bearing.
  </p>
</header>

<!-- Methodology callout ------------------------------------------------- -->
<aside class="method">
  <h2>How rows are classified</h2>
  <dl>
    <div>
      <dt>Signal source (in priority order)</dt>
      <dd>
        <code>latest-release</code> cell → <code>code-release</code>
        "last commit YYYY-MM" → <code>created</code> cell (as a soft signal,
        when nothing else is available).
      </dd>
    </div>
    <div>
      <dt>Thresholds</dt>
      <dd>
        Active ≤ 12mo · Stale 12–24mo · Abandoned > 24mo, measured against
        a fixed snapshot date (2026-05-12) so this view doesn't drift over time.
      </dd>
    </div>
    <div>
      <dt>Research split</dt>
      <dd>
        Tier 3–5 rows route to the Research bucket regardless of date.
        "Maintained" is the wrong axis for a published paper — but if a
        research row has a stale public repo AND inbound citations, it
        surfaces in the "Abandoned but cited" card below.
      </dd>
    </div>
    <div>
      <dt>Unknown subdivision</dt>
      <dd>
        The Unknown bucket is split four ways so its structure is visible:
        closed-source · OSS with weak signal · newly-created · N/A.
        Most Unknown rows are closed-source products that don't publish
        changelogs — this is a limit of the catalog signal, not evidence
        of abandonment.
      </dd>
    </div>
  </dl>
</aside>

<!-- Filters ------------------------------------------------------------- -->
<section class="filters" aria-label="Filter records by tier and section">
  <div class="filter-row">
    <span class="filter-label">Tier</span>
    {#each [1, 2, 3, 4, 5] as t}
      {@const on = selectedTiers.has(t as Tier)}
      <label class="chip" class:on>
        <input
          type="checkbox"
          checked={on}
          onchange={() => toggleTier(t as Tier)}
        />
        T{t}
      </label>
    {/each}
  </div>
  <div class="filter-row">
    <span class="filter-label">Section</span>
    <div class="section-chips">
      {#each allSections as s}
        {@const on = selectedSections.has(s)}
        <label class="chip" class:on>
          <input
            type="checkbox"
            checked={on}
            onchange={() => toggleSection(s)}
          />
          {s}
        </label>
      {/each}
    </div>
  </div>
  <div class="filter-row filter-summary">
    <span class="filter-count">
      Showing <strong>{filteredRecords.length}</strong> /
      {data.records.length} records
    </span>
    {#if selectedTiers.size + selectedSections.size > 0}
      <button class="clear-btn" type="button" onclick={clearFilters}>
        Clear filters
      </button>
    {/if}
  </div>
</section>

<!-- Top-row counters ---------------------------------------------------- -->
<section class="counters">
  {#each SURVIVORSHIP_ORDER as status}
    {@const n = counts[status]}
    <button
      type="button"
      class="counter"
      class:active={highlight === status}
      style:--c={SURVIVORSHIP_COLOURS[status]}
      onclick={() => (highlight = highlight === status ? null : status)}
      aria-pressed={highlight === status}
      title="Click to highlight {SURVIVORSHIP_LABELS[status]} dots below"
    >
      <span class="counter-dot" aria-hidden="true"></span>
      <span class="counter-n">{n}</span>
      <span class="counter-label">{SURVIVORSHIP_LABELS[status]}</span>
      <span class="counter-pct">{pct(n, counts.total)}</span>
    </button>
  {/each}
</section>

<!-- "So what" interpretation panel -------------------------------------- -->
<section class="so-what">
  <h2>What each bucket means for a reader</h2>
  <div class="so-what-grid">
    {#each SURVIVORSHIP_ORDER as status}
      <article
        class="so-what-card"
        style:--c={SURVIVORSHIP_COLOURS[status]}
      >
        <header>
          <span class="sw-dot" aria-hidden="true"></span>
          <h3>{BUCKET_SO_WHAT[status].title}</h3>
          <span class="sw-n">{counts[status]}</span>
        </header>
        <p>{BUCKET_SO_WHAT[status].body}</p>
      </article>
    {/each}
  </div>
</section>

<!-- Unknown-bucket subdivision ----------------------------------------- -->
<section class="unknown-sub">
  <header>
    <h2>Unknown bucket — what's actually in there?</h2>
    <p>
      The Unknown bucket dominates the catalog ({counts.unknown} /
      {counts.total} rows). Most of that is structural — closed-source
      products with no public release cadence — not evidence of abandonment.
      The breakdown below makes that structure visible.
    </p>
  </header>
  {#if unknownSubs.total === 0}
    <p class="empty">No Unknown records in the current filter.</p>
  {:else}
    <div
      class="stacked-bar"
      role="img"
      aria-label="Stacked breakdown of the Unknown bucket"
    >
      {#each UNKNOWN_SUB_ORDER as sub}
        {@const n = unknownSubs[sub]}
        {#if n > 0}
          <span
            class="stacked-seg"
            style:flex={n}
            style:background={UNKNOWN_SUB_COLOURS[sub]}
            title="{UNKNOWN_SUB_LABELS[sub]}: {n}"
          >
            {#if n / unknownSubs.total >= 0.08}
              <span class="seg-label">{UNKNOWN_SUB_SHORT[sub]} · {n}</span>
            {/if}
          </span>
        {/if}
      {/each}
    </div>
    <ul class="sub-legend">
      {#each UNKNOWN_SUB_ORDER as sub}
        {@const n = unknownSubs[sub]}
        <li>
          <span
            class="legend-dot"
            style:background={UNKNOWN_SUB_COLOURS[sub]}
            aria-hidden="true"
          ></span>
          <div class="legend-text">
            <strong>{UNKNOWN_SUB_LABELS[sub]}</strong>
            <span class="legend-n">{n} · {pct(n, unknownSubs.total)} of Unknown</span>
            <p>{UNKNOWN_SUB_INTERPRETATION[sub]}</p>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<!-- Abandoned but cited (foregrounded) --------------------------------- -->
<section class="influential">
  <header>
    <h2>Abandoned but still cited</h2>
    <p>
      The most actionable finding of this view. These rows show as
      Abandoned (or as research with a stale public repo) yet remain
      load-bearing in the catalog — other systems still cite them, build
      on them, or integrate against them. Re-verify before any new work
      depends on them; consider the lineage and the active siblings.
      Score = inbound integrations × 3 + inbound citations.
    </p>
  </header>
  {#if influential.length === 0}
    <p class="empty">
      No abandoned record has inbound integrations or citations under the
      current filter.
    </p>
  {:else}
    <div class="card-grid">
      {#each influential.slice(0, 12) as row, i}
        {@const primary = row.record.sections.find((s) => s.primary)?.section ??
          row.record.sections[0]?.section ??
          '—'}
        <article
          class="abandoned-card"
          style:--c={row.effective === 'abandoned' ? '#f85149' : '#bc8cff'}
        >
          <header>
            <span class="rank">#{i + 1}</span>
            <a class="card-name" href={tableHref(row.record.name)}>
              {row.record.name}
            </a>
            <span class="tier">T{row.record.tier}</span>
          </header>
          <p class="card-section">{primary}</p>
          {#if row.lineageName}
            <p class="card-lineage">
              <span class="lineage-tag">lineage</span>
              {row.lineageName}
            </p>
          {/if}
          <dl class="card-stats">
            <div>
              <dt>Score</dt>
              <dd><strong>{row.score}</strong></dd>
            </div>
            <div>
              <dt>Integrations</dt>
              <dd>{row.inboundIntegrations}</dd>
            </div>
            <div>
              <dt>Citations</dt>
              <dd>{row.inboundCitations}</dd>
            </div>
            <div>
              <dt>Last signal</dt>
              <dd class="signal">
                {row.lastSignalAgeMonths !== null
                  ? `${row.lastSignalAgeMonths}mo ago`
                  : '—'}
              </dd>
            </div>
          </dl>
          <p class="card-signal">{row.cls.signal}</p>
          <footer class="card-actions">
            <span
              class="bucket-pill"
              style:--c={row.effective === 'abandoned'
                ? '#f85149'
                : '#bc8cff'}
            >{row.effective}</span>
            <a class="link" href={tableHref(row.record.name)}>Table</a>
            <a class="link" href={influenceHref(row.record.name)}>Influence</a>
          </footer>
        </article>
      {/each}
    </div>
  {/if}
</section>

<!-- Per-section breakdown with status bars ----------------------------- -->
<section class="strips">
  <header class="strips-header">
    <h2>Per-section survivorship</h2>
    <p>
      Each row shows one section. The proportion bar gives the status mix
      at a glance; the dot strip below shows the individual records. Rows
      are ordered by aging score (stale + abandoned share, excluding
      research) — so the section with the most-quiet maintained surface
      surfaces first.
    </p>
  </header>
  {#each sectionsByAging as { section: s, aging }}
    <article class="strip">
      <header>
        <h3>{s.section}</h3>
        <span class="strip-total">{s.total} rows</span>
        <span class="strip-aging" title="(stale + abandoned) / non-research">
          aging {Math.round(aging * 100)}%
        </span>
        <span class="strip-mix">
          {#each SURVIVORSHIP_ORDER as st}
            {#if s.byStatus[st] > 0}
              <span
                class="mix-pill"
                style:--c={SURVIVORSHIP_COLOURS[st]}
                title="{s.byStatus[st]} {SURVIVORSHIP_LABELS[st].toLowerCase()}"
              >
                <span class="mix-dot" aria-hidden="true"></span>
                {s.byStatus[st]}
              </span>
            {/if}
          {/each}
        </span>
      </header>

      <!-- Proportion bar -->
      <div
        class="status-bar"
        role="img"
        aria-label="Status proportion for {s.section}"
      >
        {#each SURVIVORSHIP_ORDER as st}
          {#if s.byStatus[st] > 0}
            <span
              class="status-seg"
              style:flex={s.byStatus[st]}
              style:background={SURVIVORSHIP_COLOURS[st]}
              title="{SURVIVORSHIP_LABELS[st]}: {s.byStatus[st]}"
            ></span>
          {/if}
        {/each}
      </div>

      <!-- Per-record dot strip -->
      <div class="dots">
        {#each s.rows as { record, cls }}
          <a
            class="dot"
            class:dim={highlight !== null && highlight !== cls.status}
            href={tableHref(record.name)}
            style:--c={SURVIVORSHIP_COLOURS[cls.status]}
            title={tooltip(record, SURVIVORSHIP_LABELS[cls.status], cls.signal)}
            aria-label="{record.name}: {SURVIVORSHIP_LABELS[cls.status]} — {cls.signal}"
          ></a>
        {/each}
      </div>
    </article>
  {/each}
  {#if visibleSections.length === 0}
    <p class="empty">
      No section has ≥ 2 records under the current filter.
    </p>
  {/if}
</section>

<!-- Active-cohort timeline -------------------------------------------- -->
<section class="cohort">
  <header>
    <h2>Active cohort — when were the alive systems born?</h2>
    <p>
      Histogram of the Active bucket's <code>created</code> dates, bucketed
      by year-quarter. Shows the age distribution of the alive systems:
      a back-loaded shape means the field is fresh (most live systems are
      young); a front-loaded shape means the field has mature winners that
      keep shipping.
    </p>
  </header>
  {#if activeCohort.length === 0}
    <p class="empty">No active records with parseable created dates under this filter.</p>
  {:else}
    <div class="cohort-chart">
      {#each activeCohort as b}
        <div
          class="cohort-bar-wrap"
          title="{b.key}: {b.count} active record{b.count === 1 ? '' : 's'}"
        >
          <span
            class="cohort-bar"
            style:height="{activeCohortMax === 0 ? 0 : (b.count / activeCohortMax) * 100}%"
          >
            {#if b.count > 0}
              <span class="cohort-n">{b.count}</span>
            {/if}
          </span>
          <span class="cohort-tick">{b.key}</span>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .page-header {
    max-width: 760px;
    margin: 24px 0 24px;
  }
  .breadcrumb {
    margin: 0 0 8px;
    font-size: 0.85rem;
    color: #888;
  }
  .breadcrumb a {
    color: #aaa;
    text-decoration: none;
  }
  .breadcrumb a:hover {
    color: #d4845f;
  }
  h1 {
    margin: 0 0 12px;
    font-size: 1.6rem;
    color: #e8e8e8;
    letter-spacing: -0.01em;
  }
  .lede {
    margin: 0;
    color: #aaa;
    line-height: 1.55;
    font-size: 0.95rem;
  }

  /* Methodology callout --------------------------------------- */
  .method {
    background: #131822;
    border: 1px solid #21304a;
    border-left: 3px solid #58a6ff;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 0 0 28px;
    max-width: 1100px;
  }
  .method h2 {
    margin: 0 0 10px;
    font-size: 0.95rem;
    color: #d8e3f1;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }
  .method dl {
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px 24px;
  }
  .method dt {
    color: #8fa3c1;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 3px;
  }
  .method dd {
    margin: 0;
    color: #c8cdd6;
    font-size: 0.84rem;
    line-height: 1.5;
  }
  .method code {
    background: #0c1118;
    border: 1px solid #1f2a3a;
    border-radius: 3px;
    padding: 0 4px;
    font-size: 0.78rem;
    color: #79c0ff;
  }

  /* Filters ----------------------------------------------------- */
  .filters {
    background: #141414;
    border: 1px solid #222;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 0 0 24px;
    max-width: 1100px;
  }
  .filter-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    padding: 6px 0;
  }
  .filter-row + .filter-row {
    border-top: 1px solid #1f1f1f;
    margin-top: 2px;
  }
  .filter-label {
    color: #888;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    min-width: 60px;
  }
  .section-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #1c1c1c;
    border: 1px solid #2a2a2a;
    border-radius: 14px;
    padding: 3px 10px;
    color: #bbb;
    font-size: 0.78rem;
    cursor: pointer;
    user-select: none;
    transition: background 0.12s, border-color 0.12s, color 0.12s;
  }
  .chip:hover {
    background: #232323;
    color: #e8e8e8;
  }
  .chip.on {
    background: #2a221c;
    border-color: #d4845f;
    color: #f0c8b0;
  }
  .chip input {
    display: none;
  }
  .filter-summary {
    color: #888;
    font-size: 0.8rem;
  }
  .filter-count strong {
    color: #e8e8e8;
  }
  .clear-btn {
    margin-left: auto;
    background: transparent;
    border: 1px solid #2a2a2a;
    color: #aaa;
    font: inherit;
    font-size: 0.78rem;
    padding: 3px 10px;
    border-radius: 4px;
    cursor: pointer;
  }
  .clear-btn:hover {
    border-color: #d4845f;
    color: #d4845f;
  }

  /* Counters --------------------------------------------------- */
  .counters {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 12px;
    max-width: 1100px;
    margin: 0 0 28px;
  }
  .counter {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    column-gap: 12px;
    align-items: center;
    background: #181818;
    border: 1px solid #2a2a2a;
    border-left: 3px solid var(--c);
    border-radius: 8px;
    padding: 14px 16px;
    color: #e8e8e8;
    font: inherit;
    cursor: pointer;
    text-align: left;
    transition: border-color 0.15s, background 0.15s;
  }
  .counter:hover {
    background: #1f1f1f;
  }
  .counter.active {
    background: #1f1f1f;
    border-color: var(--c);
    box-shadow: inset 0 0 0 1px var(--c);
  }
  .counter-dot {
    grid-row: 1 / span 2;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--c);
  }
  .counter-n {
    font-size: 1.55rem;
    font-weight: 600;
    line-height: 1;
  }
  .counter-label {
    color: #aaa;
    font-size: 0.85rem;
  }
  .counter-pct {
    grid-column: 2;
    color: #777;
    font-size: 0.75rem;
    margin-top: 2px;
  }

  /* So-what panel ---------------------------------------------- */
  .so-what {
    margin: 0 0 36px;
    max-width: 1100px;
  }
  .so-what h2 {
    margin: 0 0 12px;
    font-size: 1.05rem;
    color: #e8e8e8;
  }
  .so-what-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 10px;
  }
  .so-what-card {
    background: #141414;
    border: 1px solid #222;
    border-top: 3px solid var(--c);
    border-radius: 6px;
    padding: 12px 14px;
  }
  .so-what-card header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .sw-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--c);
  }
  .so-what-card h3 {
    margin: 0;
    font-size: 0.88rem;
    color: #e8e8e8;
  }
  .sw-n {
    margin-left: auto;
    color: #888;
    font-size: 0.8rem;
    font-variant-numeric: tabular-nums;
  }
  .so-what-card p {
    margin: 0;
    color: #aaa;
    font-size: 0.82rem;
    line-height: 1.5;
  }

  /* Unknown subdivision ---------------------------------------- */
  .unknown-sub {
    margin: 0 0 36px;
    max-width: 1100px;
  }
  .unknown-sub header h2 {
    margin: 0 0 6px;
    font-size: 1.05rem;
    color: #e8e8e8;
  }
  .unknown-sub header p {
    margin: 0 0 14px;
    color: #888;
    font-size: 0.88rem;
    line-height: 1.5;
    max-width: 760px;
  }
  .stacked-bar {
    display: flex;
    height: 28px;
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid #222;
    margin-bottom: 16px;
  }
  .stacked-seg {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #0d1117;
    font-size: 0.72rem;
    font-weight: 600;
    transition: filter 0.15s;
  }
  .stacked-seg:hover {
    filter: brightness(1.15);
  }
  .seg-label {
    padding: 0 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sub-legend {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 10px;
  }
  .sub-legend li {
    display: flex;
    gap: 10px;
    background: #141414;
    border: 1px solid #222;
    border-radius: 5px;
    padding: 10px 12px;
  }
  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-top: 5px;
    flex: none;
  }
  .legend-text {
    flex: 1;
    min-width: 0;
  }
  .legend-text strong {
    display: block;
    color: #e8e8e8;
    font-size: 0.84rem;
  }
  .legend-n {
    color: #888;
    font-size: 0.74rem;
    font-variant-numeric: tabular-nums;
  }
  .legend-text p {
    margin: 4px 0 0;
    color: #aaa;
    font-size: 0.78rem;
    line-height: 1.5;
  }

  /* Strips ----------------------------------------------------- */
  .strips {
    max-width: 1100px;
    margin: 0 0 40px;
  }
  .strips-header {
    max-width: 760px;
    margin: 0 0 16px;
  }
  .strips-header h2 {
    margin: 0 0 6px;
    font-size: 1.05rem;
    color: #e8e8e8;
  }
  .strips-header p {
    margin: 0;
    color: #888;
    font-size: 0.88rem;
    line-height: 1.5;
  }
  .strip {
    background: #141414;
    border: 1px solid #222;
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 10px;
  }
  .strip header {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 6px;
    flex-wrap: wrap;
  }
  .strip h3 {
    margin: 0;
    font-size: 0.9rem;
    font-weight: 600;
    color: #e8e8e8;
  }
  .strip-total {
    color: #888;
    font-size: 0.8rem;
  }
  .strip-aging {
    color: #d29922;
    font-size: 0.74rem;
    font-variant-numeric: tabular-nums;
    background: rgba(210, 153, 34, 0.08);
    border: 1px solid rgba(210, 153, 34, 0.25);
    border-radius: 3px;
    padding: 1px 6px;
  }
  .strip-mix {
    display: inline-flex;
    gap: 6px;
    margin-left: auto;
    flex-wrap: wrap;
  }
  .mix-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #1c1c1c;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 1px 7px;
    color: #bbb;
    font-size: 0.72rem;
    font-variant-numeric: tabular-nums;
  }
  .mix-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--c);
  }
  .status-bar {
    display: flex;
    height: 6px;
    border-radius: 3px;
    overflow: hidden;
    margin: 6px 0 8px;
    background: #1c1c1c;
  }
  .status-seg {
    height: 100%;
    transition: filter 0.15s;
  }
  .status-seg:hover {
    filter: brightness(1.2);
  }
  .dots {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--c);
    display: inline-block;
    border: 1px solid rgba(0, 0, 0, 0.4);
    transition: transform 0.1s, opacity 0.15s;
    cursor: pointer;
  }
  .dot:hover {
    transform: scale(1.4);
    z-index: 2;
  }
  .dot.dim {
    opacity: 0.15;
  }

  /* Abandoned-but-cited card grid ------------------------------ */
  .influential {
    margin: 0 0 48px;
    max-width: 1100px;
  }
  .influential header {
    max-width: 760px;
    margin-bottom: 14px;
  }
  .influential h2 {
    margin: 0 0 6px;
    font-size: 1.15rem;
    color: #e8e8e8;
  }
  .influential header p {
    margin: 0;
    color: #888;
    font-size: 0.9rem;
    line-height: 1.55;
  }
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 12px;
  }
  .abandoned-card {
    background: #141414;
    border: 1px solid #222;
    border-left: 3px solid var(--c);
    border-radius: 6px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .abandoned-card header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
  }
  .rank {
    color: #666;
    font-size: 0.78rem;
    font-variant-numeric: tabular-nums;
    font-weight: 600;
  }
  .card-name {
    color: #e8e8e8;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.95rem;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .card-name:hover {
    color: #d4845f;
  }
  .tier {
    display: inline-block;
    padding: 1px 5px;
    border-radius: 3px;
    background: #222;
    color: #888;
    font-size: 0.7rem;
    font-weight: 600;
  }
  .card-section {
    margin: 0;
    color: #888;
    font-size: 0.78rem;
  }
  .card-lineage {
    margin: 0;
    color: #bc8cff;
    font-size: 0.78rem;
  }
  .lineage-tag {
    display: inline-block;
    background: rgba(188, 140, 255, 0.1);
    border: 1px solid rgba(188, 140, 255, 0.25);
    border-radius: 3px;
    padding: 0 5px;
    margin-right: 4px;
    font-size: 0.68rem;
    color: #bc8cff;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .card-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
    margin: 0;
  }
  .card-stats > div {
    text-align: center;
    background: #181818;
    border: 1px solid #1f1f1f;
    border-radius: 3px;
    padding: 4px 2px;
  }
  .card-stats dt {
    color: #777;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .card-stats dd {
    margin: 2px 0 0;
    color: #ddd;
    font-size: 0.85rem;
    font-variant-numeric: tabular-nums;
  }
  .card-stats dd.signal {
    font-size: 0.72rem;
    color: #aaa;
  }
  .card-stats strong {
    color: #e8e8e8;
  }
  .card-signal {
    margin: 0;
    color: #888;
    font-size: 0.74rem;
    line-height: 1.4;
  }
  .card-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: auto;
  }
  .bucket-pill {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    color: var(--c);
    border: 1px solid var(--c);
    background: rgba(0, 0, 0, 0.2);
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-size: 0.7rem;
  }
  .link {
    color: #58a6ff;
    text-decoration: none;
    font-size: 0.78rem;
    border: 1px solid #1f2a3a;
    border-radius: 3px;
    padding: 1px 7px;
    background: #0f1620;
  }
  .link:hover {
    border-color: #58a6ff;
    color: #79c0ff;
  }

  /* Active cohort histogram ------------------------------------ */
  .cohort {
    max-width: 1100px;
    margin: 0 0 64px;
  }
  .cohort header {
    max-width: 760px;
    margin-bottom: 12px;
  }
  .cohort h2 {
    margin: 0 0 6px;
    font-size: 1.05rem;
    color: #e8e8e8;
  }
  .cohort header p {
    margin: 0;
    color: #888;
    font-size: 0.88rem;
    line-height: 1.55;
  }
  .cohort-chart {
    display: flex;
    align-items: flex-end;
    gap: 4px;
    height: 180px;
    padding: 12px;
    background: #141414;
    border: 1px solid #222;
    border-radius: 6px;
    overflow-x: auto;
  }
  .cohort-bar-wrap {
    flex: 1 0 36px;
    min-width: 36px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    height: 100%;
    position: relative;
  }
  .cohort-bar {
    width: 100%;
    background: #3fb950;
    border-radius: 2px 2px 0 0;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 2px;
    min-height: 1px;
    color: #0d1117;
    font-size: 0.7rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    transition: filter 0.15s;
  }
  .cohort-bar:hover {
    filter: brightness(1.15);
  }
  .cohort-n {
    position: relative;
    top: -14px;
    color: #c0e0c0;
    text-shadow: 0 0 4px #0d1117;
  }
  .cohort-tick {
    color: #777;
    font-size: 0.65rem;
    margin-top: 4px;
    transform: rotate(-45deg);
    transform-origin: top center;
    white-space: nowrap;
  }

  .empty {
    color: #888;
    font-style: italic;
    padding: 12px 0;
  }

  @media (max-width: 720px) {
    .counters {
      grid-template-columns: repeat(2, 1fr);
    }
    .so-what-grid {
      grid-template-columns: 1fr;
    }
    .card-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
