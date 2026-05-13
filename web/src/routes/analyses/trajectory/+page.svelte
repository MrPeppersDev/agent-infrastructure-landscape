<script lang="ts">
  // Trajectory view (issue #34). "What's used today vs what's growing/dying."
  //
  // Five panels:
  //   1. Growth-decline cohort table (every record bucketed)
  //   2. Substrate dependency risk (Claude / GPT-5 / Gemini etc.)
  //   3. Next-likely consolidation candidates (embedding / inference / vector-DB)
  //   4. Next billion-$ valuation candidates
  //   5. Categories likely to die
  //
  // Heuristic confidence labels live next to each callout. Methodology
  // is documented in docs/DECISIONS.md under
  // "2026-05-13: Trajectory view heuristics".

  import { base } from '$app/paths';
  import type { LandscapeRecord, Edge, Tier } from '$lib/types';
  import type { Lineage } from '$lib/lineages';
  import type { LineageForecast } from '$lib/analyses/forecast';
  import { classify as classifySurvivorship } from '$lib/analyses/survivorship';
  import {
    classifyAll,
    countBuckets,
    substrateDependencies,
    consolidationCandidates,
    billionDollarCandidates,
    dyingCandidates,
    lineageCadenceByMember,
    TRAJECTORY_ORDER,
    TRAJECTORY_LABELS,
    TRAJECTORY_COLOURS,
    type Trajectory,
    type TrajectoryClassification
  } from '$lib/analyses/trajectory';

  let {
    data
  }: {
    data: {
      records: LandscapeRecord[];
      edges: Edge[];
      lineages: Lineage[];
      forecasts: LineageForecast[];
    };
  } = $props();

  // --- Filter state ----------------------------------------------------
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

  // --- Survivorship "dead" set (cross-reference) -----------------------
  const survivorshipDead = $derived.by(() => {
    const s = new Set<string>();
    for (const r of filteredRecords) {
      const cls = classifySurvivorship(r);
      if (cls.status === 'abandoned') s.add(r.id);
    }
    return s;
  });

  // --- Trajectory classifications --------------------------------------
  const classifications = $derived(
    classifyAll(filteredRecords, data.edges, data.lineages, survivorshipDead)
  );
  const counts = $derived(countBuckets(classifications));

  // --- Sort + filter the main cohort table -----------------------------
  let cohortBucket = $state<Trajectory | 'all'>('all');
  type SortKey = 'name' | 'trajectory' | 'tier' | 'confidence' | 'reason';
  let sortKey = $state<SortKey>('trajectory');
  let sortDir = $state<'asc' | 'desc'>('asc');

  const confidenceRank: Record<'low' | 'medium' | 'high', number> = {
    low: 0,
    medium: 1,
    high: 2
  };
  const trajectoryRank: Record<Trajectory, number> = {
    accelerating: 0,
    steady: 1,
    decelerating: 2,
    dead: 3,
    unknown: 4
  };

  const cohortRows = $derived.by(() => {
    type Row = {
      record: LandscapeRecord;
      cls: TrajectoryClassification;
    };
    const out: Row[] = [];
    for (const r of filteredRecords) {
      const cls = classifications.get(r.id);
      if (!cls) continue;
      if (cohortBucket !== 'all' && cls.trajectory !== cohortBucket) continue;
      out.push({ record: r, cls });
    }
    out.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'name':
          cmp = a.record.name.localeCompare(b.record.name);
          break;
        case 'tier':
          cmp = a.record.tier - b.record.tier;
          break;
        case 'trajectory':
          cmp =
            trajectoryRank[a.cls.trajectory] -
            trajectoryRank[b.cls.trajectory];
          break;
        case 'confidence':
          cmp = confidenceRank[a.cls.confidence] - confidenceRank[b.cls.confidence];
          break;
        case 'reason':
          cmp = a.cls.reason.localeCompare(b.cls.reason);
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return out;
  });

  function setSort(k: SortKey) {
    if (sortKey === k) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      sortKey = k;
      sortDir = 'asc';
    }
  }

  // --- Panels 2-5 ------------------------------------------------------
  const substrates = $derived(substrateDependencies(filteredRecords, classifications));
  const consolidation = $derived(
    consolidationCandidates(filteredRecords, classifications)
  );
  const billion = $derived(
    billionDollarCandidates(filteredRecords, classifications)
  );

  const cadenceByLineageId = $derived.by(() => {
    const m = new Map<string, number>();
    for (const f of data.forecasts) {
      if (isFinite(f.cadence_quarters)) m.set(f.lineage_id, f.cadence_quarters);
    }
    return m;
  });
  const cadenceByMember = $derived(
    lineageCadenceByMember(data.lineages, cadenceByLineageId)
  );
  const dying = $derived(
    dyingCandidates(filteredRecords, classifications, cadenceByMember)
  );

  // --- Helpers ---------------------------------------------------------
  function pct(n: number, total: number): string {
    if (total === 0) return '0%';
    return `${Math.round((n / total) * 100)}%`;
  }

  function tableHref(name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  function primarySection(r: LandscapeRecord): string {
    const p = r.sections.find((s) => s.primary);
    return p?.section ?? r.sections[0]?.section ?? 'Uncategorised';
  }
</script>

<svelte:head>
  <title>Trajectory · Analyses · Memory Landscape</title>
</svelte:head>

<header class="page-header">
  <p class="breadcrumb">
    <a href="{base}/analyses">Analyses</a> · Trajectory
  </p>
  <h1>Trajectory — what's used today vs what's growing or dying</h1>
  <p class="lede">
    Combines funding cadence, release recency, GitHub stars,
    mindshare/citations, inbound integration edges, and lineage
    membership into a single velocity story per record. Buckets are
    heuristic — confidence labels are surfaced everywhere so a reader
    can weigh each callout. This view answers the "what is used vs
    what might the future be" question that motivated the catalog.
  </p>
</header>

<!-- Methodology callout ----------------------------------------------- -->
<aside class="method">
  <h2>How rows are bucketed</h2>
  <dl>
    <div>
      <dt>Accelerating</dt>
      <dd>
        Recent funding (≤12mo) <em>or</em> newest member of a detected
        lineage <em>or</em> ≥10k GH stars <em>or</em> mindshare ≥70.
      </dd>
    </div>
    <div>
      <dt>Steady</dt>
      <dd>
        Inbound integrations/citations present and no decay signal —
        cited and maintained but not currently accelerating.
      </dd>
    </div>
    <div>
      <dt>Decelerating</dt>
      <dd>
        Two of: funding ≥18mo old · last release ≥18mo old · last commit
        ≥18mo old. Slope down but not yet flatlined.
      </dd>
    </div>
    <div>
      <dt>Dead</dt>
      <dd>
        Cross-references survivorship: any record the survivorship view
        labels Abandoned (no release/commit in 24+mo) routes here.
      </dd>
    </div>
    <div>
      <dt>Confidence</dt>
      <dd>
        <strong>High</strong> = ≥2 corroborating signals.
        <strong>Medium</strong> = exactly one strong signal.
        <strong>Low</strong> = ambiguous or single weak signal.
      </dd>
    </div>
  </dl>
</aside>

<!-- Filters ----------------------------------------------------------- -->
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

<!-- Top counters ------------------------------------------------------- -->
<section class="counters">
  {#each TRAJECTORY_ORDER as status}
    {@const n = counts[status]}
    <button
      type="button"
      class="counter"
      class:active={cohortBucket === status}
      style:--c={TRAJECTORY_COLOURS[status]}
      onclick={() => (cohortBucket = cohortBucket === status ? 'all' : status)}
      aria-pressed={cohortBucket === status}
      title="Filter cohort table to {TRAJECTORY_LABELS[status]}"
    >
      <span class="counter-dot" aria-hidden="true"></span>
      <span class="counter-n">{n}</span>
      <span class="counter-label">{TRAJECTORY_LABELS[status]}</span>
      <span class="counter-pct">{pct(n, counts.total)}</span>
    </button>
  {/each}
</section>

<!-- Panel 1: cohort table ---------------------------------------------- -->
<section class="panel">
  <header class="panel-header">
    <h2>Panel 1 — Growth-decline cohort</h2>
    <p>
      Every record bucketed. Click a counter above to filter to one
      bucket; sort by clicking column headers. Each row drills to the
      main catalog table.
    </p>
  </header>
  <div class="table-wrap">
    <table class="cohort">
      <thead>
        <tr>
          <th><button type="button" onclick={() => setSort('name')}>Name</button></th>
          <th><button type="button" onclick={() => setSort('tier')}>Tier</button></th>
          <th>Section</th>
          <th>
            <button type="button" onclick={() => setSort('trajectory')}>Trajectory</button>
          </th>
          <th>
            <button type="button" onclick={() => setSort('confidence')}>Confidence</button>
          </th>
          <th>
            <button type="button" onclick={() => setSort('reason')}>Reason</button>
          </th>
        </tr>
      </thead>
      <tbody>
        {#each cohortRows.slice(0, 250) as { record, cls }}
          <tr>
            <td>
              <a href={tableHref(record.name)} class="row-link">{record.name}</a>
            </td>
            <td>T{record.tier}</td>
            <td>{primarySection(record)}</td>
            <td>
              <span
                class="badge"
                style:--c={TRAJECTORY_COLOURS[cls.trajectory]}
              >
                {TRAJECTORY_LABELS[cls.trajectory]}
              </span>
            </td>
            <td>
              <span class="conf conf-{cls.confidence}">{cls.confidence}</span>
            </td>
            <td class="reason">{cls.reason}</td>
          </tr>
        {/each}
      </tbody>
    </table>
    {#if cohortRows.length > 250}
      <p class="more-note">
        Showing first 250 of {cohortRows.length} rows. Narrow the filters
        above to focus the view.
      </p>
    {/if}
  </div>
</section>

<!-- Panel 2: substrate dependency risk --------------------------------- -->
<section class="panel">
  <header class="panel-header">
    <h2>Panel 2 — Substrate dependency risk</h2>
    <p>
      For records that name a foundation-model substrate (in claims /
      desc / llm-lock / embedding-model cells), who depends on what.
      Single-vendor exposure is flagged: if the substrate disappears or
      restricts access, every member here feels it on the same day.
    </p>
  </header>
  <div class="substrate-grid">
    {#each substrates as group}
      <article class="substrate-card" class:risk={group.singleVendorRisk}>
        <header>
          <h3>{group.substrate}</h3>
          <span class="count-pill">{group.members.length}</span>
          {#if group.singleVendorRisk}
            <span class="risk-tag" title="All members tied to a single FM vendor">
              single-vendor risk
            </span>
          {/if}
        </header>
        <ul>
          {#each group.members.slice(0, 8) as m}
            <li>
              <a href={tableHref(m.record.name)}>{m.record.name}</a>
              <span
                class="dot"
                style:--c={TRAJECTORY_COLOURS[m.cls.trajectory]}
                title={TRAJECTORY_LABELS[m.cls.trajectory]}
                aria-label={TRAJECTORY_LABELS[m.cls.trajectory]}
              ></span>
            </li>
          {/each}
          {#if group.members.length > 8}
            <li class="more">+{group.members.length - 8} more</li>
          {/if}
        </ul>
      </article>
    {/each}
  </div>
</section>

<!-- Panel 3: consolidation candidates ---------------------------------- -->
<section class="panel">
  <header class="panel-header">
    <h2>Panel 3 — Next-likely consolidation candidates</h2>
    <p>
      Predicted M&amp;A categories with recent precedents. Top 3
      candidates per category, scored by inbound integrations + tier +
      funding recency. Speculative — labels match the issue's seed
      framing, not Anthropic guidance.
    </p>
  </header>
  <div class="consolidation-grid">
    {#each consolidation as cat}
      <article class="consolidation-card">
        <header>
          <h3>{cat.label}</h3>
          <p class="precedent">Precedent: {cat.precedent}</p>
        </header>
        {#if cat.candidates.length === 0}
          <p class="empty">No matching records under current filters.</p>
        {:else}
          <ol>
            {#each cat.candidates as c}
              <li>
                <a href={tableHref(c.record.name)} class="cand-name">
                  {c.record.name}
                </a>
                <span class="cand-reason">{c.reason}</span>
                <span
                  class="dot"
                  style:--c={TRAJECTORY_COLOURS[c.cls.trajectory]}
                  title={TRAJECTORY_LABELS[c.cls.trajectory]}
                  aria-label={TRAJECTORY_LABELS[c.cls.trajectory]}
                ></span>
              </li>
            {/each}
          </ol>
        {/if}
      </article>
    {/each}
  </div>
</section>

<!-- Panel 4: billion-$ candidates -------------------------------------- -->
<section class="panel">
  <header class="panel-header">
    <h2>Panel 4 — Next billion-$ valuation candidates</h2>
    <p>
      Combining recent funding rounds, climbing GitHub stars, integration
      adoptions, and mindshare. Confidence labels reflect how many
      signals agree. Speculative — calibrated against precedent rather
      than insider data.
    </p>
  </header>
  {#if billion.length === 0}
    <p class="empty">No candidates clear the bar under current filters.</p>
  {:else}
    <ol class="billion">
      {#each billion as b}
        <li>
          <div class="b-head">
            <a href={tableHref(b.record.name)} class="b-name">{b.record.name}</a>
            <span class="b-tier">T{b.record.tier}</span>
            <span class="conf conf-{b.confidence}">{b.confidence}</span>
          </div>
          <p class="b-reason">{b.reason}</p>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<!-- Panel 5: dying candidates ------------------------------------------ -->
<section class="panel">
  <header class="panel-header">
    <h2>Panel 5 — Categories likely to die</h2>
    <p>
      Low integration count + low citation rate + slow lineage cadence +
      no/declining funding. The "dead" rows from Panel 1 are excluded
      here — those are already gone. This list is the slope-down rows
      that haven't flatlined yet.
    </p>
  </header>
  {#if dying.length === 0}
    <p class="empty">No declining candidates clear the bar under current filters.</p>
  {:else}
    <ol class="dying">
      {#each dying as d}
        <li>
          <div class="d-head">
            <a href={tableHref(d.record.name)} class="d-name">{d.record.name}</a>
            <span class="d-tier">T{d.record.tier}</span>
            <span class="conf conf-{d.confidence}">{d.confidence}</span>
          </div>
          <p class="d-reason">{d.reason}</p>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  .page-header {
    max-width: 820px;
    margin: 24px 0 16px;
  }
  .breadcrumb {
    margin: 0 0 8px;
    color: #888;
    font-size: 0.85rem;
  }
  .breadcrumb a {
    color: #aaa;
    text-decoration: none;
  }
  .breadcrumb a:hover {
    color: #d4845f;
  }
  .page-header h1 {
    margin: 0 0 12px;
    font-size: 1.6rem;
    color: #e8e8e8;
    letter-spacing: -0.01em;
  }
  .lede {
    margin: 0;
    color: #aaa;
    line-height: 1.55;
  }
  .method {
    background: #161616;
    border: 1px solid #262626;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 16px 0 24px;
    max-width: 980px;
  }
  .method h2 {
    margin: 0 0 8px;
    font-size: 0.95rem;
    color: #e8e8e8;
    font-weight: 600;
  }
  .method dl {
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 8px 20px;
  }
  .method dt {
    color: #d4845f;
    font-weight: 600;
    font-size: 0.85rem;
    margin-top: 4px;
  }
  .method dd {
    margin: 0 0 4px;
    color: #aaa;
    font-size: 0.85rem;
    line-height: 1.5;
  }
  .filters {
    margin: 0 0 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .filter-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .filter-label {
    color: #888;
    font-size: 0.85rem;
    min-width: 60px;
  }
  .section-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip {
    background: #181818;
    border: 1px solid #2a2a2a;
    color: #aaa;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 0.8rem;
    cursor: pointer;
    user-select: none;
  }
  .chip input {
    display: none;
  }
  .chip.on {
    background: #2a1a12;
    border-color: #d4845f;
    color: #e8e8e8;
  }
  .filter-summary {
    margin-top: 4px;
  }
  .filter-count {
    color: #888;
    font-size: 0.85rem;
  }
  .clear-btn {
    background: transparent;
    border: 1px solid #333;
    color: #aaa;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 0.8rem;
    cursor: pointer;
  }
  .clear-btn:hover {
    border-color: #d4845f;
    color: #d4845f;
  }
  .counters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 8px;
    margin: 0 0 24px;
    max-width: 980px;
  }
  .counter {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 10px 12px;
    text-align: left;
    cursor: pointer;
    color: #e8e8e8;
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: baseline;
    gap: 6px;
  }
  .counter.active {
    border-color: var(--c);
  }
  .counter-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--c);
    grid-row: span 2;
    align-self: center;
  }
  .counter-n {
    font-size: 1.4rem;
    font-weight: 600;
  }
  .counter-pct {
    color: #888;
    font-size: 0.8rem;
  }
  .counter-label {
    grid-column: 2 / 4;
    color: #aaa;
    font-size: 0.8rem;
  }
  .panel {
    margin: 0 0 32px;
    max-width: 1100px;
  }
  .panel-header {
    margin: 0 0 12px;
  }
  .panel-header h2 {
    margin: 0 0 6px;
    font-size: 1.1rem;
    color: #e8e8e8;
    font-weight: 600;
  }
  .panel-header p {
    margin: 0;
    color: #888;
    font-size: 0.9rem;
    line-height: 1.5;
    max-width: 760px;
  }
  .table-wrap {
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    overflow: hidden;
  }
  .cohort {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }
  .cohort thead {
    background: #161616;
  }
  .cohort th {
    text-align: left;
    padding: 8px 10px;
    color: #aaa;
    font-weight: 600;
    border-bottom: 1px solid #2a2a2a;
  }
  .cohort th button {
    background: transparent;
    border: none;
    color: inherit;
    font: inherit;
    cursor: pointer;
    padding: 0;
  }
  .cohort th button:hover {
    color: #d4845f;
  }
  .cohort td {
    padding: 6px 10px;
    border-bottom: 1px solid #1f1f1f;
    color: #cccccc;
    vertical-align: top;
  }
  .cohort tbody tr:hover {
    background: #161616;
  }
  .row-link {
    color: #e8e8e8;
    text-decoration: none;
  }
  .row-link:hover {
    color: #d4845f;
  }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    background: color-mix(in srgb, var(--c) 18%, transparent);
    color: var(--c);
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
  }
  .conf {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    font-weight: 600;
  }
  .conf-low {
    background: #1f1f1f;
    color: #888;
  }
  .conf-medium {
    background: #2a2419;
    color: #d29922;
  }
  .conf-high {
    background: #142e1c;
    color: #3fb950;
  }
  .reason {
    color: #888;
    font-size: 0.8rem;
    max-width: 420px;
  }
  .more-note {
    padding: 10px;
    margin: 0;
    color: #888;
    font-size: 0.8rem;
    background: #161616;
  }
  .substrate-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }
  .substrate-card {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 14px 16px;
  }
  .substrate-card.risk {
    border-color: #d29922;
  }
  .substrate-card header {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }
  .substrate-card h3 {
    margin: 0;
    font-size: 1rem;
    color: #e8e8e8;
  }
  .count-pill {
    background: #222;
    border-radius: 999px;
    padding: 1px 8px;
    font-size: 0.75rem;
    color: #aaa;
  }
  .risk-tag {
    background: #2a2419;
    color: #d29922;
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }
  .substrate-card ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .substrate-card li {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #aaa;
    font-size: 0.85rem;
  }
  .substrate-card li.more {
    color: #666;
    font-style: italic;
  }
  .substrate-card a {
    color: #e8e8e8;
    text-decoration: none;
  }
  .substrate-card a:hover {
    color: #d4845f;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--c);
    flex-shrink: 0;
  }
  .consolidation-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 12px;
  }
  .consolidation-card {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 14px 16px;
  }
  .consolidation-card h3 {
    margin: 0 0 4px;
    font-size: 1rem;
    color: #e8e8e8;
  }
  .precedent {
    margin: 0 0 10px;
    color: #888;
    font-size: 0.8rem;
  }
  .consolidation-card ol {
    list-style: none;
    margin: 0;
    padding: 0;
    counter-reset: cand;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .consolidation-card li {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: baseline;
    gap: 6px;
    counter-increment: cand;
  }
  .consolidation-card li::before {
    content: counter(cand) '.';
    color: #666;
    font-size: 0.8rem;
  }
  .cand-name {
    color: #e8e8e8;
    text-decoration: none;
    font-size: 0.9rem;
  }
  .cand-name:hover {
    color: #d4845f;
  }
  .cand-reason {
    color: #888;
    font-size: 0.75rem;
    grid-column: 2 / 4;
  }
  .empty {
    margin: 0;
    padding: 14px 16px;
    color: #666;
    font-size: 0.85rem;
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    font-style: italic;
  }
  .billion,
  .dying {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 10px;
  }
  .billion li,
  .dying li {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 12px 14px;
  }
  .b-head,
  .d-head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }
  .b-name,
  .d-name {
    color: #e8e8e8;
    text-decoration: none;
    font-weight: 600;
  }
  .b-name:hover,
  .d-name:hover {
    color: #d4845f;
  }
  .b-tier,
  .d-tier {
    color: #888;
    font-size: 0.75rem;
  }
  .b-reason,
  .d-reason {
    margin: 0;
    color: #aaa;
    font-size: 0.8rem;
    line-height: 1.45;
  }
</style>
