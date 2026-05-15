<script lang="ts">
  // Trajectory view (issues #34, #47). "What's used today vs what's
  // growing/dying", upgraded with empirical S-curve maturity fits.
  //
  // Six panels:
  //   1. Growth-decline cohort table (every record bucketed)
  //   2. Substrate dependency risk (Claude / GPT-5 / Gemini etc.)
  //   3. Next-likely consolidation candidates (embedding / inference / vector-DB)
  //   4. Next billion-$ valuation candidates
  //   5. Categories likely to die
  //   6. S-curve maturity fit (BIMATEM-style logistic fit per row)
  //
  // Panels 1-5 are heuristic with confidence labels (methodology in
  // docs/DECISIONS.md under "2026-05-13: Trajectory view heuristics").
  // Panel 6 is quantitative — logistic L/k/t0 with R² and inflection-date
  // prediction; the math is in web/src/lib/analyses/s-curve.ts and the
  // methodology footer at the bottom of this page.

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
  import {
    countPhases,
    medianR2,
    formatInflectionAsQuarter,
    PHASE_ORDER,
    PHASE_LABELS,
    PHASE_COLOURS,
    PHASE_DESCRIPTION,
    type SCurveFit,
    type SCurvePhase
  } from '$lib/analyses/s-curve';

  let {
    data
  }: {
    data: {
      records: LandscapeRecord[];
      edges: Edge[];
      lineages: Lineage[];
      forecasts: LineageForecast[];
      sCurveFits: SCurveFit[];
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

  // --- Panel 6: S-curve fits ------------------------------------------
  // Build a fast lookup so the filtered-records pass below is O(1) per row.
  const fitsById = $derived.by(() => {
    const m = new Map<string, SCurveFit>();
    for (const f of data.sCurveFits) m.set(f.recordId, f);
    return m;
  });
  const filteredFits = $derived(
    filteredRecords
      .map((r) => fitsById.get(r.id))
      .filter((f): f is SCurveFit => f !== undefined)
  );
  const phaseCounts = $derived(countPhases(filteredFits));
  const overallMedianR2 = $derived(medianR2(filteredFits));

  let scurvePhaseFilter = $state<SCurvePhase | 'all'>('all');
  type SCurveSortKey = 'name' | 'phase' | 'r2' | 'k' | 'inflection' | 'points';
  let scurveSortKey = $state<SCurveSortKey>('r2');
  let scurveSortDir = $state<'asc' | 'desc'>('desc');

  const phaseRank: Record<SCurvePhase, number> = {
    'pre-growth': 0,
    growth: 1,
    saturation: 2,
    decline: 3,
    'insufficient-data': 4
  };

  const scurveRows = $derived.by(() => {
    const filtered = filteredFits.filter(
      (f) => scurvePhaseFilter === 'all' || f.phase === scurvePhaseFilter
    );
    const dir = scurveSortDir === 'asc' ? 1 : -1;
    return filtered.slice().sort((a, b) => {
      let cmp = 0;
      switch (scurveSortKey) {
        case 'name':
          cmp = a.recordName.localeCompare(b.recordName);
          break;
        case 'phase':
          cmp = phaseRank[a.phase] - phaseRank[b.phase];
          break;
        case 'r2':
          cmp =
            (isFinite(a.fitR2) ? a.fitR2 : -1) -
            (isFinite(b.fitR2) ? b.fitR2 : -1);
          break;
        case 'k':
          cmp =
            (isFinite(a.growthRate) ? a.growthRate : -1) -
            (isFinite(b.growthRate) ? b.growthRate : -1);
          break;
        case 'inflection':
          cmp = (a.inflectionDate ?? '').localeCompare(b.inflectionDate ?? '');
          break;
        case 'points':
          cmp = a.dataPoints - b.dataPoints;
          break;
      }
      return cmp * dir;
    });
  });

  function setScurveSort(k: SCurveSortKey) {
    if (scurveSortKey === k) {
      scurveSortDir = scurveSortDir === 'asc' ? 'desc' : 'asc';
    } else {
      scurveSortKey = k;
      scurveSortDir = k === 'name' || k === 'inflection' ? 'asc' : 'desc';
    }
  }

  // Sparkline geometry. Tiny chart fits in a single table cell.
  const SPARK_W = 96;
  const SPARK_H = 28;
  const SPARK_PAD = 2;

  function sparklinePaths(
    fit: SCurveFit
  ): { observed: string; predicted: string } {
    if (fit.series.length === 0) return { observed: '', predicted: '' };
    const xs = [...fit.series, ...fit.predictedSeries];
    if (xs.length === 0) return { observed: '', predicted: '' };
    const ts = xs.map((p) => Date.parse(p.date));
    const ys = xs.map((p) => p.value);
    const tMin = Math.min(...ts);
    const tMax = Math.max(...ts);
    const yMin = Math.min(...ys);
    const yMax = Math.max(...ys);
    const tRange = Math.max(1, tMax - tMin);
    const yRange = Math.max(1e-9, yMax - yMin);

    function xy(d: { date: string; value: number }): [number, number] {
      const x =
        SPARK_PAD + ((Date.parse(d.date) - tMin) / tRange) * (SPARK_W - 2 * SPARK_PAD);
      const y =
        SPARK_H -
        SPARK_PAD -
        ((d.value - yMin) / yRange) * (SPARK_H - 2 * SPARK_PAD);
      return [x, y];
    }

    let observed = '';
    fit.series.forEach((p, i) => {
      const [x, y] = xy(p);
      observed += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)} `;
    });
    let predicted = '';
    fit.predictedSeries.forEach((p, i) => {
      const [x, y] = xy(p);
      predicted += `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)} `;
    });
    return { observed: observed.trim(), predicted: predicted.trim() };
  }

  function r2Label(r2: number): string {
    if (!isFinite(r2)) return '—';
    return r2.toFixed(2);
  }

  function kLabel(k: number): string {
    if (!isFinite(k)) return '—';
    if (k >= 1) return k.toFixed(2);
    return k.toFixed(3);
  }

  function inflectionLabel(fit: SCurveFit): string {
    if (fit.phase === 'insufficient-data') return '—';
    const q = formatInflectionAsQuarter(fit.inflectionDate);
    if (!q) return '—';
    if (fit.phase === 'growth') return `saturation expected ~${q}`;
    if (fit.phase === 'pre-growth') return `growth expected ~${q}`;
    if (fit.phase === 'saturation') return `inflection passed ${q}`;
    return q;
  }

  function capacityLabel(fit: SCurveFit): string {
    if (!isFinite(fit.carryingCapacity)) return '—';
    const L = fit.carryingCapacity;
    if (L >= 10000) return `${(L / 1000).toFixed(0)}k`;
    if (L >= 1000) return `${(L / 1000).toFixed(1)}k`;
    return L.toFixed(0);
  }

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
    Six panels. The first five combine funding cadence, release
    recency, GitHub stars, mindshare/citations, inbound integration
    edges, and lineage membership into a heuristic velocity story per
    record — confidence labels are surfaced everywhere so a reader can
    weigh each callout. The sixth fits a BIMATEM-style logistic
    S-curve to every row with enough temporal signal and reads
    pre-growth / growth / saturation / decline straight off the
    inflection — quantitative complement to the heuristic buckets, and
    the math the Gartner Hype Cycle waves at without ever publishing.
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

<!-- Panel 6: S-curve maturity fit (issue #47) -------------------------- -->
<section class="panel scurve">
  <header class="panel-header">
    <h2>Panel 6 — S-curve maturity fit</h2>
    <p>
      Quantitative complement to Panels 1-5. For every row we fit a
      3-parameter logistic — y = L / (1 + exp(-k·(t-t<sub>0</sub>))) —
      to its cumulative temporal series (citations / dated milestones /
      OSS stars). The inflection date t<sub>0</sub> divides growth from
      saturation; the fitted k tells us how steep the transition is.
      This is the math Gartner's Hype Cycle waves at without ever
      publishing — ours has the math.
    </p>
  </header>

  <div class="scurve-counters">
    {#each PHASE_ORDER as ph}
      {@const n = phaseCounts[ph]}
      <button
        type="button"
        class="counter"
        class:active={scurvePhaseFilter === ph}
        style:--c={PHASE_COLOURS[ph]}
        onclick={() => (scurvePhaseFilter = scurvePhaseFilter === ph ? 'all' : ph)}
        aria-pressed={scurvePhaseFilter === ph}
        title={PHASE_DESCRIPTION[ph]}
      >
        <span class="counter-dot" aria-hidden="true"></span>
        <span class="counter-n">{n}</span>
        <span class="counter-label">{PHASE_LABELS[ph]}</span>
        <span class="counter-pct">{pct(n, phaseCounts.total)}</span>
      </button>
    {/each}
  </div>

  <p class="scurve-summary">
    {filteredFits.filter((f) => f.phase !== 'insufficient-data').length}
    rows fit · median R² =
    <strong>{isFinite(overallMedianR2) ? overallMedianR2.toFixed(2) : '—'}</strong>
    · click a counter to filter the table below.
  </p>

  <div class="table-wrap">
    <table class="scurve-table">
      <thead>
        <tr>
          <th><button type="button" onclick={() => setScurveSort('name')}>Record</button></th>
          <th>Section</th>
          <th><button type="button" onclick={() => setScurveSort('phase')}>Phase</button></th>
          <th>Curve</th>
          <th>
            <button
              type="button"
              onclick={() => setScurveSort('r2')}
              title="Coefficient of determination — higher = tighter fit"
            >R²</button>
          </th>
          <th>
            <button
              type="button"
              onclick={() => setScurveSort('k')}
              title="Logistic growth rate — higher = steeper transition"
            >k</button>
          </th>
          <th title="Estimated carrying capacity (L)">L</th>
          <th>
            <button type="button" onclick={() => setScurveSort('inflection')}>
              Inflection
            </button>
          </th>
          <th>
            <button type="button" onclick={() => setScurveSort('points')}>
              Points
            </button>
          </th>
          <th>Signal</th>
        </tr>
      </thead>
      <tbody>
        {#each scurveRows.slice(0, 250) as fit}
          {@const paths = sparklinePaths(fit)}
          <tr>
            <td>
              <a href={tableHref(fit.recordName)} class="row-link">{fit.recordName}</a>
            </td>
            <td class="sec">{fit.section}</td>
            <td>
              <span class="badge" style:--c={PHASE_COLOURS[fit.phase]}>
                {PHASE_LABELS[fit.phase]}
              </span>
            </td>
            <td class="spark-cell">
              {#if fit.phase === 'insufficient-data' || paths.observed === ''}
                <span class="dashes">—</span>
              {:else}
                <svg
                  viewBox="0 0 {SPARK_W} {SPARK_H}"
                  width={SPARK_W}
                  height={SPARK_H}
                  role="img"
                  aria-label="Cumulative observations and fitted logistic curve"
                >
                  {#if paths.predicted}
                    <path
                      d={paths.predicted}
                      fill="none"
                      stroke={PHASE_COLOURS[fit.phase]}
                      stroke-width="1.4"
                      stroke-dasharray="2 2"
                      opacity="0.85"
                    />
                  {/if}
                  {#if paths.observed}
                    <path
                      d={paths.observed}
                      fill="none"
                      stroke="#e8e8e8"
                      stroke-width="1.1"
                      opacity="0.9"
                    />
                  {/if}
                </svg>
              {/if}
            </td>
            <td>{r2Label(fit.fitR2)}</td>
            <td>{kLabel(fit.growthRate)}</td>
            <td>{capacityLabel(fit)}</td>
            <td class="inflection">{inflectionLabel(fit)}</td>
            <td>{fit.dataPoints || '—'}</td>
            <td class="signal">{fit.source}</td>
          </tr>
        {/each}
      </tbody>
    </table>
    {#if scurveRows.length > 250}
      <p class="more-note">
        Showing first 250 of {scurveRows.length} rows. Narrow filters above
        or click a phase counter to focus.
      </p>
    {/if}
  </div>
</section>

<!-- Methodology footer (Panel 6 detail) -------------------------------- -->
<aside class="method method-bottom">
  <h2>Panel 6 methodology — BIMATEM-style logistic fit</h2>
  <p>
    For each row with at least 5 dated observation points spanning at
    least 12 months, we fit the logistic
    <code>y = L / (1 + exp(-k · (t − t<sub>0</sub>)))</code>
    via coarse grid search over (L, k, t<sub>0</sub>) followed by three
    local refinement passes. The framework follows the BIMATEM
    bibliometric tradition (Bengisu &amp; Nekhili 2006 onwards) and the
    citation-trajectory work in Wang, Song &amp; Barabási
    <em>Science</em> 2013 — both fit a 3-parameter logistic to
    cumulative event counts and read maturity off the inflection point.
  </p>
  <dl>
    <div>
      <dt>Pre-growth</dt>
      <dd>
        Observation time below t<sub>0</sub> − 2σ where σ = 2/k. Below
        ~12% of estimated carrying capacity.
      </dd>
    </div>
    <div>
      <dt>Growth</dt>
      <dd>
        t<sub>0</sub> − 2σ ≤ t &lt; t<sub>0</sub>. Steepest part of the
        ramp; saturation date predicted as t<sub>0</sub>.
      </dd>
    </div>
    <div>
      <dt>Saturation</dt>
      <dd>
        t<sub>0</sub> ≤ t &lt; t<sub>0</sub> + 2σ. Post-inflection;
        rate is slowing toward the plateau.
      </dd>
    </div>
    <div>
      <dt>Decline</dt>
      <dd>
        Past saturation AND the most-recent 2-of-3 observations sit
        below 95 % of the fitted curve — distinguishes a real fall-off
        from a long plateau tail.
      </dd>
    </div>
    <div>
      <dt>Insufficient data</dt>
      <dd>
        Fewer than 5 distinct cumulative-count anchors or under 12
        months of observable history. We refuse to force a 3-parameter
        fit on too little signal; the bias toward this bucket is a
        property of catalog-level data, not the underlying technology.
      </dd>
    </div>
    <div>
      <dt>Signal sources</dt>
      <dd>
        Priority: (1) <strong>commit trajectory</strong> — real monthly
        cumulative commit counts from the GitHub Commits API, populated
        by <code>make refresh-commit-trajectories</code> (T3-prep-1 /
        issue #50; the strongest signal we have for product / OSS rows
        because it is real per-month data, not a synthesised piecewise
        reconstruction); (2) <strong>citation trajectory</strong> —
        real yearly cumulative within-catalog inbound-citation counts
        bucketed offline from the S2 reference cache by
        <code>make bucket-citations</code> (T3-prep-2 / issue #51; the
        strongest signal we have for academic-paper rows when ≥3 distinct
        years of inbound citations exist); (3) citations + per-year rate
        — synthesised piecewise fallback for paper rows without a
        citation-trajectory cell; (4) dated milestones across created /
        latest-release / funding / claims / customers / api-surface /
        compliance / pricing / deployment cells for products; (5)
        star-growth on OSS repos with +N/mo metadata. Implementation
        in <code>web/src/lib/analyses/s-curve.ts</code>.
      </dd>
    </div>
  </dl>
</aside>

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

  /* --- Panel 6: S-curve fits ---------------------------------------- */
  .scurve {
    max-width: 1280px;
  }
  .scurve-counters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 8px;
    margin: 0 0 12px;
  }
  .scurve-summary {
    margin: 0 0 10px;
    color: #888;
    font-size: 0.85rem;
  }
  .scurve-summary strong {
    color: #e8e8e8;
  }
  .scurve-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
  }
  .scurve-table thead {
    background: #161616;
  }
  .scurve-table th {
    text-align: left;
    padding: 8px 10px;
    color: #aaa;
    font-weight: 600;
    border-bottom: 1px solid #2a2a2a;
    white-space: nowrap;
  }
  .scurve-table th button {
    background: transparent;
    border: none;
    color: inherit;
    font: inherit;
    cursor: pointer;
    padding: 0;
  }
  .scurve-table th button:hover {
    color: #d4845f;
  }
  .scurve-table td {
    padding: 5px 10px;
    border-bottom: 1px solid #1f1f1f;
    color: #ccc;
    vertical-align: middle;
  }
  .scurve-table tbody tr:hover {
    background: #161616;
  }
  .scurve-table .sec {
    color: #888;
    font-size: 0.78rem;
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .scurve-table .spark-cell {
    padding: 2px 8px;
    line-height: 0;
  }
  .scurve-table .spark-cell svg {
    display: block;
  }
  .scurve-table .dashes {
    color: #555;
  }
  .scurve-table .inflection {
    color: #aaa;
    font-size: 0.78rem;
    white-space: nowrap;
  }
  .scurve-table .signal {
    color: #777;
    font-size: 0.75rem;
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .method-bottom {
    margin-top: 24px;
    max-width: 1100px;
  }
  .method-bottom p {
    margin: 0 0 12px;
    color: #aaa;
    line-height: 1.5;
    font-size: 0.88rem;
  }
  .method-bottom code {
    background: #0f0f0f;
    border: 1px solid #262626;
    border-radius: 3px;
    padding: 1px 5px;
    font-family: 'JetBrains Mono', 'SF Mono', Menlo, monospace;
    font-size: 0.82em;
    color: #d29922;
  }
</style>
