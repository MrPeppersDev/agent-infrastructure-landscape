<script lang="ts">
  // Benchmark integrity view (issue #33).
  //
  // Companion to /analyses/benchmarks. That view answers "who benchmarks
  // on what?". This view answers the question the user actually wants
  // answered: "are the numbers trustworthy?". Each benchmark mention is
  // classified into one of five buckets — peer-reviewed,
  // independently-verified, vendor-claimed, disputed, unverifiable —
  // using citation host + score-divergence heuristics. The classification
  // rules are documented in docs/DECISIONS.md and live in the pure module
  // $lib/analyses/benchmark-integrity.ts.
  //
  // Layout:
  //   1. Header — what this view is for, what's different from /benchmarks
  //   2. Classification rules callout
  //   3. Filter row — tier × section
  //   4. Bucket-count strip — five large counters
  //   5. Per-benchmark breakdown table — colored stacked counts
  //   6. Validated-winners leaderboard — peer-reviewed scores only
  //   7. Gaming-patterns panel — three heuristic flags with row drilldowns
  //   8. Drill any row → main table filtered by record name

  import {
    classifyIntegrity,
    bucketCounts,
    perBenchmark,
    validatedLeaderboard,
    gamingFlags,
    uniqueSections,
    uniqueTiers,
    type IntegrityRow,
    type IntegrityBucket,
    type GamingFlag
  } from '$lib/analyses/benchmark-integrity';
  import { base } from '$app/paths';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  // Compute classification once on the full dataset; filter downstream
  // by tier and section using $derived so the user can slice freely.
  const allRows = $derived(classifyIntegrity(data.records));

  let activeTiers = $state<Set<number>>(new Set([1, 2, 3, 4, 5]));
  let activeSection = $state<string>('all');

  function toggleTier(t: number) {
    const next = new Set(activeTiers);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    if (next.size === 0) next.add(t);
    activeTiers = next;
  }

  const rows = $derived(
    allRows.filter(
      (r) =>
        activeTiers.has(r.tier) && (activeSection === 'all' || r.section === activeSection)
    )
  );

  const counts = $derived(bucketCounts(rows));
  const breakdown = $derived(perBenchmark(rows));
  const leaderboards = $derived(validatedLeaderboard(rows, 5));
  const flagRows = $derived(gamingFlags(rows));
  const sections = $derived(uniqueSections(allRows));
  const tiersPresent = $derived(uniqueTiers(allRows));

  const tierLabels: Record<number, string> = {
    1: 'commercial',
    2: 'productized',
    3: 'framework',
    4: 'research',
    5: 'informal'
  };

  const bucketLabels: Record<IntegrityBucket, string> = {
    'peer-reviewed': 'Peer-reviewed',
    'independently-verified': 'Independently verified',
    'vendor-claimed': 'Vendor-claimed',
    disputed: 'Disputed',
    unverifiable: 'Unverifiable'
  };

  const bucketBlurbs: Record<IntegrityBucket, string> = {
    'peer-reviewed':
      'Citation host is a peer-reviewed venue (arXiv, OpenReview, ACL Anthology, IEEE Xplore, ACM DL, PMLR).',
    'independently-verified':
      'Citation host is a non-vendor third party — neutral leaderboard, independent blog, or commodity publishing platform.',
    'vendor-claimed':
      'Citation host matches the vendor’s own domain. The vendor is making the claim about its own product.',
    disputed:
      'Another catalog row contradicts this number — either via in-cell dispute signal (⚠, "rebuttal") or score divergence > 7 absolute points on the same benchmark.',
    unverifiable: 'No citation that resolves to a host, sentinel value, or depth-floor-reached cell.'
  };

  const flagLabels: Record<GamingFlag, string> = {
    'vendor-self-defined': 'Vendor self-defined benchmark',
    'weak-baseline-comparison': 'Weak-baseline comparison',
    'single-sub-task-only': 'Single sub-task only'
  };

  const flagBlurbs: Record<GamingFlag, string> = {
    'vendor-self-defined':
      'Benchmark reported by exactly one record, and the citation is on that vendor’s own domain. No external corroboration exists.',
    'weak-baseline-comparison':
      'The only comparison in the cell is to a notoriously weak baseline (Full-Context, GPT-3.5, Llama-3.0, "vanilla", or "no-memory baseline").',
    'single-sub-task-only':
      'The cell explicitly mentions a single sub-task ("single-fact", "sub-task", "only on X") and does not also report an aggregate / overall score.'
  };

  function tableHref(name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  function pct(n: number, total: number): string {
    if (total === 0) return '0%';
    return `${Math.round((n / total) * 100)}%`;
  }

  // For the per-benchmark breakdown: total across rows so we can render
  // a percentage column.
  const grandTotal = $derived(rows.length);

  // For drill-down: clicking a benchmark cell scrolls to a per-row list.
  let drilledBucket = $state<{ benchmark: string; bucket: IntegrityBucket } | null>(null);

  function drillTo(benchmark: string, bucket: IntegrityBucket) {
    drilledBucket = { benchmark, bucket };
    queueMicrotask(() => {
      document.getElementById('drill-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  const drilledRows = $derived.by(() => {
    if (!drilledBucket) return [] as IntegrityRow[];
    const { benchmark, bucket } = drilledBucket;
    return rows.filter((r) => r.benchmark === benchmark && r.bucket === bucket);
  });

  const recordById = $derived.by(() => {
    const m = new Map<string, LandscapeRecord>();
    for (const r of data.records) m.set(r.id, r);
    return m;
  });

  function disputedByLabel(ids: string[]): string {
    return ids
      .map((id) => recordById.get(id)?.name ?? id)
      .slice(0, 3)
      .join(', ');
  }
</script>

<svelte:head>
  <title>Benchmark integrity — Memory Landscape</title>
</svelte:head>

<main class="bi-page">
  <header class="bi-header">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Benchmark integrity</h1>
    <p class="bi-intro">
      The companion to <a href="{base}/analyses/benchmarks">benchmark coverage</a>.
      That view answers <em>who benchmarks on what</em>. This view answers
      the next question: <strong>are the numbers trustworthy?</strong>
      Every benchmark mention in the catalog is classified by where the
      citation lives — peer-reviewed venue, neutral third party, the
      vendor’s own site — and cross-checked against contradicting
      claims from other catalog rows. The canonical disputed case
      (Mem0 vs Zep on LoCoMo) shows up directly in the LoCoMo row of the
      per-benchmark breakdown.
    </p>
    <p class="bi-stats">
      <strong>{allRows.length}</strong> classified benchmark mentions
      across the 894-record catalog ·
      <strong>{breakdown.length}</strong> distinct benchmarks tracked.
    </p>
  </header>

  <aside class="methodology">
    <h2>Classification rules</h2>
    <dl class="rules">
      {#each counts as c (c.bucket)}
        <div class="rule" data-bucket={c.bucket}>
          <dt>
            <span class="bucket-pill" data-bucket={c.bucket}>{bucketLabels[c.bucket]}</span>
          </dt>
          <dd>{bucketBlurbs[c.bucket]}</dd>
        </div>
      {/each}
    </dl>
    <p class="rules-note">
      A row can carry one or more <em>gaming flags</em> independent of
      its bucket — those surface specific gaming patterns (vendor
      self-defined, weak baseline, single sub-task). See the panel below.
    </p>
  </aside>

  <section class="filter-row" aria-label="Filters">
    <span class="filter-label">Tier:</span>
    {#each [1, 2, 3, 4, 5] as t}
      <button
        type="button"
        class="tier-btn"
        class:active={activeTiers.has(t)}
        class:absent={!tiersPresent.includes(t)}
        onclick={() => toggleTier(t)}
        aria-pressed={activeTiers.has(t)}
      >
        T{t} <span class="tier-sub">{tierLabels[t]}</span>
      </button>
    {/each}
    <span class="filter-label section-label">Section:</span>
    <select bind:value={activeSection} class="section-select">
      <option value="all">All sections</option>
      {#each sections as s}
        <option value={s}>{s}</option>
      {/each}
    </select>
    <span class="filter-hint">filter narrows every panel below</span>
  </section>

  <section class="bucket-strip" aria-label="Bucket totals">
    {#each counts as c (c.bucket)}
      <article class="bucket-card" data-bucket={c.bucket}>
        <div class="bucket-n">{c.count}</div>
        <div class="bucket-name">{bucketLabels[c.bucket]}</div>
        <div class="bucket-pct">{pct(c.count, grandTotal)} of mentions</div>
      </article>
    {/each}
  </section>

  <section class="breakdown" aria-label="Per-benchmark breakdown">
    <h2 class="section-h">Per-benchmark breakdown</h2>
    <p class="section-sub">
      For each benchmark, how many mentions fall into each integrity
      bucket. The cells are clickable — drill into a row to see
      which records are in that cell. <strong>LoCoMo</strong> is the
      canonical example: vendor-claimed scores from commercial vendors,
      peer-reviewed scores from research papers, and one disputed mention
      from the Mem0 ↔ Zep rebuttal.
    </p>
    {#if breakdown.length === 0}
      <p class="empty">No benchmark mentions under the current filter.</p>
    {:else}
      <div class="table-wrap">
        <table class="breakdown-table">
          <thead>
            <tr>
              <th class="bench-col">Benchmark</th>
              <th class="num">Total</th>
              <th class="num peer-reviewed">Peer-reviewed</th>
              <th class="num independently-verified">Independent</th>
              <th class="num vendor-claimed">Vendor-claimed</th>
              <th class="num disputed">Disputed</th>
              <th class="num unverifiable">Unverifiable</th>
            </tr>
          </thead>
          <tbody>
            {#each breakdown as b (b.benchmark)}
              <tr>
                <td class="bench-col">{b.benchmark}</td>
                <td class="num total-cell">{b.total}</td>
                {#each ['peer-reviewed', 'independently-verified', 'vendor-claimed', 'disputed', 'unverifiable'] as bucket}
                  {@const n = b.counts[bucket as IntegrityBucket]}
                  <td class="num {bucket}" class:zero={n === 0}>
                    {#if n > 0}
                      <button type="button" class="cell-btn" onclick={() => drillTo(b.benchmark, bucket as IntegrityBucket)}>
                        {n}
                      </button>
                    {:else}
                      <span class="dash">—</span>
                    {/if}
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>

  {#if drilledBucket}
    <section class="drill" id="drill-panel" aria-label="Drilldown">
      <header class="drill-head">
        <h3>
          {drilledBucket.benchmark} —
          <span class="bucket-pill" data-bucket={drilledBucket.bucket}>
            {bucketLabels[drilledBucket.bucket]}
          </span>
          <span class="drill-count">({drilledRows.length} mentions)</span>
        </h3>
        <button type="button" class="drill-close" onclick={() => (drilledBucket = null)}>Clear</button>
      </header>
      <table class="drill-table">
        <thead>
          <tr>
            <th>System</th>
            <th>Tier</th>
            <th>Score</th>
            <th>Source</th>
            <th>Citation</th>
            <th>Reason</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {#each drilledRows as r (r.record_id + '::' + r.benchmark)}
            <tr>
              <td>
                <a href={tableHref(r.record_name)}>{r.record_name}</a>
              </td>
              <td><span class="tier-pill" data-tier={r.tier}>T{r.tier}</span></td>
              <td class="num">{r.score || '—'}</td>
              <td class="source-cell">{r.source}</td>
              <td>
                {#if r.citation}
                  <a href={r.citation} target="_blank" rel="noopener" class="cit">{r.citationHost ?? r.citation}</a>
                {:else}
                  <span class="muted">no citation</span>
                {/if}
              </td>
              <td class="reason-cell">
                {r.reason}
                {#if r.disputedBy.length > 0}
                  <span class="disputed-by">— vs {disputedByLabel(r.disputedBy)}</span>
                {/if}
              </td>
              <td class="flags-cell">
                {#each r.flags as f}
                  <span class="flag-chip">{flagLabels[f]}</span>
                {/each}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}

  <section class="winners" aria-label="Validated winners">
    <h2 class="section-h">Leaderboard of validated winners</h2>
    <p class="section-sub">
      Top peer-reviewed scores per benchmark — vendor-claimed
      numbers are excluded entirely, so this is the leaderboard you can
      hand to a reviewer with the least caveat. If a benchmark has no
      peer-reviewed scores under the current filter it doesn’t appear
      here — by design.
    </p>
    {#if leaderboards.size === 0}
      <p class="empty">No peer-reviewed scores under the current filter.</p>
    {:else}
      <div class="winners-grid">
        {#each [...leaderboards.entries()] as [bench, lb] (bench)}
          {#if lb.length > 0}
            <article class="winner-card">
              <header>
                <h3>{bench}</h3>
                <span class="winner-sub">{lb.length} peer-reviewed</span>
              </header>
              <ol>
                {#each lb as row, i (row.record_id)}
                  <li>
                    <span class="rank">{i + 1}</span>
                    <a class="winner-name" href={tableHref(row.record_name)}>{row.record_name}</a>
                    <span class="tier-pill small" data-tier={row.tier}>T{row.tier}</span>
                    <span class="winner-score">{row.score}</span>
                    <span class="winner-host">{row.citationHost}</span>
                  </li>
                {/each}
              </ol>
            </article>
          {/if}
        {/each}
      </div>
    {/if}
  </section>

  <section class="gaming" aria-label="Gaming patterns">
    <h2 class="section-h">Gaming patterns</h2>
    <p class="section-sub">
      Heuristic flags surfaced from the prose of each cell. These don’t
      automatically demote a row to <em>disputed</em> — they’re
      shape-of-evidence signals that point at where vendors are
      benchmarking on terrain that favours them.
    </p>
    <div class="flag-grid">
      {#each flagRows as fr (fr.flag)}
        <article class="flag-card">
          <header>
            <h3>{flagLabels[fr.flag]}</h3>
            <span class="flag-n">{fr.rows.length}</span>
          </header>
          <p class="flag-blurb">{flagBlurbs[fr.flag]}</p>
          {#if fr.rows.length === 0}
            <p class="empty small">No matches under the current filter.</p>
          {:else}
            <ul class="flag-rows">
              {#each fr.rows.slice(0, 12) as r (r.record_id + '::' + r.benchmark + '::' + fr.flag)}
                <li>
                  <a href={tableHref(r.record_name)}>{r.record_name}</a>
                  <span class="bench-pill">{r.benchmark}</span>
                  <span class="tier-pill small" data-tier={r.tier}>T{r.tier}</span>
                </li>
              {/each}
              {#if fr.rows.length > 12}
                <li class="more">… {fr.rows.length - 12} more</li>
              {/if}
            </ul>
          {/if}
        </article>
      {/each}
    </div>
  </section>

  <footer class="bi-footer">
    <a href="{base}/analyses">← Analyses hub</a>
    <span class="muted">
      Sources: <code>cells.perf</code> + <code>cells.claims</code> citations.
      Classifier in <code>$lib/analyses/benchmark-integrity.ts</code>.
    </span>
  </footer>
</main>

<style>
  .bi-page {
    max-width: 1500px;
    margin: 0 auto;
    padding: 24px 8px 64px;
    color: #e8e8e8;
  }
  .bi-header { margin-bottom: 18px; }
  .crumb { margin: 0 0 8px 0; font-size: 13px; }
  .crumb a { color: #aaa; text-decoration: none; }
  .crumb a:hover { color: #e8e8e8; }
  .bi-header h1 {
    font-size: 28px; margin: 0 0 10px 0; letter-spacing: -0.01em;
  }
  .bi-intro {
    color: #c9c9c9; max-width: 920px; margin: 0 0 12px 0;
    line-height: 1.6; font-size: 14px;
  }
  .bi-intro em { color: #f0c894; font-style: normal; }
  .bi-intro strong { color: #e8e8e8; }
  .bi-intro a { color: #9fc5e0; }
  .bi-stats { color: #d4d4d4; margin: 0; font-size: 13.5px; }
  .bi-stats strong { color: #f0c894; }
  code {
    font-family: 'SF Mono', 'Menlo', Consolas, monospace;
    font-size: 12.5px; background: #1f1f1f;
    padding: 1px 5px; border-radius: 3px; color: #d4d4d4;
  }

  .methodology {
    background: #14191d;
    border: 1px solid #233038;
    border-left: 3px solid #5e8aa3;
    border-radius: 6px;
    padding: 14px 18px 12px;
    margin: 0 0 18px 0;
  }
  .methodology h2 {
    margin: 0 0 10px 0; font-size: 13px;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: #9fc5e0; font-weight: 600;
  }
  .rules {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 8px 18px; margin: 0;
  }
  .rule { display: flex; flex-direction: column; gap: 3px; }
  .rule dt { margin: 0; }
  .rule dd { margin: 0; color: #c0c0c0; font-size: 12.5px; line-height: 1.5; }
  .rules-note {
    color: #888; font-size: 12px; font-style: italic;
    margin: 8px 0 0 0;
  }
  .rules-note em { color: #c0c0c0; font-style: normal; }

  .filter-row {
    display: flex; align-items: center; flex-wrap: wrap;
    gap: 8px; margin: 0 0 14px 0;
    padding: 10px 12px;
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 6px;
  }
  .filter-label {
    color: #aaa; font-size: 12.5px; font-weight: 600; margin-right: 4px;
  }
  .filter-label.section-label { margin-left: 12px; }
  .tier-btn {
    background: #1f1f1f; border: 1px solid #2a2a2a; color: #aaa;
    padding: 5px 10px; border-radius: 4px; cursor: pointer;
    font-size: 12px; font-weight: 500; transition: all 120ms;
    display: inline-flex; align-items: center; gap: 4px;
  }
  .tier-btn:hover { color: #e8e8e8; border-color: #3a3a3a; }
  .tier-btn.active {
    background: #2a1f12; border-color: #6b4a26; color: #f0c894;
  }
  .tier-btn.absent { opacity: 0.4; }
  .tier-sub { color: inherit; opacity: 0.7; font-size: 11px; }
  .section-select {
    background: #1f1f1f; border: 1px solid #2a2a2a; color: #d4d4d4;
    padding: 4px 8px; border-radius: 4px; font-size: 12px;
    max-width: 320px;
  }
  .filter-hint {
    margin-left: auto; color: #777; font-size: 11.5px; font-style: italic;
  }

  .bucket-strip {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px; margin: 0 0 20px 0;
  }
  .bucket-card {
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 6px; padding: 14px 16px;
    position: relative; overflow: hidden;
  }
  .bucket-card[data-bucket='peer-reviewed'] { border-left: 3px solid #6b9a4a; }
  .bucket-card[data-bucket='independently-verified'] { border-left: 3px solid #5e8aa3; }
  .bucket-card[data-bucket='vendor-claimed'] { border-left: 3px solid #c98a4e; }
  .bucket-card[data-bucket='disputed'] { border-left: 3px solid #c04e4e; }
  .bucket-card[data-bucket='unverifiable'] { border-left: 3px solid #555; }
  .bucket-n {
    font-size: 28px; font-weight: 700; color: #e8e8e8;
    font-variant-numeric: tabular-nums; letter-spacing: -0.02em;
    line-height: 1;
  }
  .bucket-name {
    color: #d4d4d4; font-size: 12px; margin-top: 6px;
    font-weight: 600;
  }
  .bucket-pct { color: #888; font-size: 11px; margin-top: 2px; }

  .bucket-pill {
    display: inline-block; font-size: 10.5px; font-weight: 600;
    padding: 2px 7px; border-radius: 3px;
    background: #2a2a2a; color: #d4d4d4;
    letter-spacing: 0.02em;
  }
  .bucket-pill[data-bucket='peer-reviewed'] { background: #1d2a1d; color: #8ec99a; }
  .bucket-pill[data-bucket='independently-verified'] { background: #1d2530; color: #9fc5e0; }
  .bucket-pill[data-bucket='vendor-claimed'] { background: #2a1d10; color: #c9a26e; }
  .bucket-pill[data-bucket='disputed'] { background: #2a1414; color: #d4877a; }
  .bucket-pill[data-bucket='unverifiable'] { background: #232323; color: #999; }

  .section-h {
    margin: 0 0 6px 0; font-size: 18px;
    color: #e8e8e8; letter-spacing: -0.005em;
  }
  .section-sub {
    color: #aaa; font-size: 13px; margin: 0 0 14px 0;
    line-height: 1.55; max-width: 920px;
  }
  .section-sub strong { color: #f0c894; }
  .section-sub em { color: #c0c0c0; font-style: normal; }

  .breakdown { margin-bottom: 28px; }
  .table-wrap {
    overflow-x: auto; border: 1px solid #2a2a2a; border-radius: 8px;
    background: #181818;
  }
  .breakdown-table {
    border-collapse: collapse; font-size: 13px;
    min-width: 100%; width: 100%;
  }
  .breakdown-table thead th {
    position: sticky; top: 0; background: #1d1d1d;
    border-bottom: 1px solid #333;
    padding: 9px 12px; text-align: left;
    font-weight: 600; color: #d4d4d4; white-space: nowrap;
    font-size: 12px;
  }
  .breakdown-table th.num, .breakdown-table td.num {
    text-align: right; font-variant-numeric: tabular-nums;
  }
  .breakdown-table th.peer-reviewed { color: #8ec99a; }
  .breakdown-table th.independently-verified { color: #9fc5e0; }
  .breakdown-table th.vendor-claimed { color: #c9a26e; }
  .breakdown-table th.disputed { color: #d4877a; }
  .breakdown-table th.unverifiable { color: #999; }
  .breakdown-table tbody td {
    border-bottom: 1px solid #232323; padding: 5px 12px;
  }
  .breakdown-table tbody tr:last-child td { border-bottom: none; }
  .breakdown-table tbody tr:hover { background: #1c1c1c; }
  .breakdown-table .bench-col { font-weight: 500; color: #e8e8e8; }
  .total-cell { color: #d4d4d4; font-weight: 600; }
  .cell-btn {
    background: none; border: none; color: inherit; cursor: pointer;
    font: inherit; padding: 3px 6px; border-radius: 3px;
    transition: background 100ms;
  }
  .cell-btn:hover { background: #2a2a2a; }
  td.peer-reviewed .cell-btn { color: #8ec99a; }
  td.independently-verified .cell-btn { color: #9fc5e0; }
  td.vendor-claimed .cell-btn { color: #c9a26e; }
  td.disputed .cell-btn { color: #d4877a; font-weight: 600; }
  td.unverifiable .cell-btn { color: #999; }
  td.zero .dash { color: #444; }

  .drill {
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 8px; padding: 14px 16px;
    margin: 0 0 28px 0;
  }
  .drill-head {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 12px;
  }
  .drill-head h3 {
    margin: 0; font-size: 15px; color: #e8e8e8;
    display: flex; align-items: center; gap: 8px;
    flex-wrap: wrap;
  }
  .drill-count { color: #888; font-size: 12px; font-weight: 400; }
  .drill-close {
    background: #2a2a2a; border: 1px solid #3a3a3a;
    color: #d4d4d4; padding: 4px 10px; border-radius: 4px;
    cursor: pointer; font-size: 12px;
  }
  .drill-close:hover { background: #3a3a3a; }
  .drill-table {
    border-collapse: collapse; font-size: 12.5px;
    width: 100%;
  }
  .drill-table th, .drill-table td {
    padding: 6px 10px; border-bottom: 1px solid #232323;
    text-align: left; vertical-align: top;
  }
  .drill-table th {
    color: #aaa; font-weight: 600; font-size: 11.5px;
    text-transform: uppercase; letter-spacing: 0.05em;
  }
  .drill-table td a {
    color: #e8e8e8; text-decoration: none;
  }
  .drill-table td a:hover { color: #f0c894; }
  .drill-table .num { text-align: right; font-variant-numeric: tabular-nums; }
  .source-cell { color: #888; font-size: 11.5px; }
  .reason-cell { color: #c0c0c0; line-height: 1.45; }
  .disputed-by { color: #d4877a; font-style: italic; }
  .flags-cell { display: flex; flex-wrap: wrap; gap: 4px; padding-top: 6px; }
  .flag-chip {
    display: inline-block; background: #2a1d10; color: #c9a26e;
    padding: 1px 6px; border-radius: 3px; font-size: 10.5px;
  }
  .cit {
    color: #9fc5e0; text-decoration: none; font-size: 12px;
    word-break: break-all;
  }
  .cit:hover { text-decoration: underline; }

  .tier-pill {
    display: inline-block; font-size: 10px; font-weight: 600;
    padding: 1px 5px; border-radius: 3px;
    background: #2a2a2a; color: #aaa;
    font-variant-numeric: tabular-nums; flex-shrink: 0;
  }
  .tier-pill.small { font-size: 9.5px; padding: 0 4px; }
  .tier-pill[data-tier='1'] { background: #1a3a2a; color: #8ec99a; }
  .tier-pill[data-tier='2'] { background: #2a3a1a; color: #c9c98e; }
  .tier-pill[data-tier='3'] { background: #3a2a1a; color: #c9a28e; }
  .tier-pill[data-tier='4'] { background: #2a2030; color: #b59ad4; }
  .tier-pill[data-tier='5'] { background: #2a2a2a; color: #888; }

  .winners { margin-bottom: 28px; }
  .winners-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }
  .winner-card {
    background: #181818; border: 1px solid #2a2a2a;
    border-left: 3px solid #6b9a4a;
    border-radius: 6px; padding: 12px 14px;
  }
  .winner-card header {
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 1px solid #232323; margin-bottom: 8px; padding-bottom: 6px;
  }
  .winner-card h3 { margin: 0; font-size: 14px; color: #8ec99a; }
  .winner-sub { color: #888; font-size: 11px; }
  .winner-card ol {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 5px;
  }
  .winner-card li {
    display: grid; grid-template-columns: 18px 1fr auto auto;
    align-items: center; gap: 6px;
    font-size: 12px;
  }
  .winner-card li .rank {
    color: #888; font-variant-numeric: tabular-nums;
    text-align: right; padding-right: 2px;
  }
  .winner-name {
    color: #e8e8e8; text-decoration: none;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .winner-name:hover { color: #f0c894; }
  .winner-score {
    color: #f4e2cb; font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .winner-host {
    color: #888; font-size: 10.5px; grid-column: 2 / -1;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }

  .gaming { margin-bottom: 28px; }
  .flag-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 12px;
  }
  .flag-card {
    background: #181818; border: 1px solid #2a2a2a;
    border-left: 3px solid #c98a4e;
    border-radius: 6px; padding: 12px 14px;
  }
  .flag-card header {
    display: flex; align-items: baseline; justify-content: space-between;
    margin-bottom: 6px;
  }
  .flag-card h3 { margin: 0; font-size: 14px; color: #c9a26e; }
  .flag-n {
    color: #f0c894; font-size: 16px; font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .flag-blurb {
    color: #aaa; font-size: 12px; line-height: 1.5;
    margin: 0 0 10px 0;
  }
  .flag-rows {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 4px;
    max-height: 320px; overflow-y: auto;
  }
  .flag-rows li {
    display: flex; align-items: center; gap: 6px;
    font-size: 12px;
  }
  .flag-rows li a {
    color: #e8e8e8; text-decoration: none; flex: 1;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .flag-rows li a:hover { color: #f0c894; }
  .flag-rows li.more { color: #777; font-style: italic; font-size: 11px; }
  .bench-pill {
    display: inline-block; background: #1f2a33; color: #9fc5e0;
    padding: 1px 6px; border-radius: 3px; font-size: 10.5px;
  }

  .empty {
    color: #888; font-style: italic;
    padding: 16px; text-align: center;
  }
  .empty.small { padding: 8px; font-size: 12px; }

  .bi-footer {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 24px; padding-top: 16px;
    border-top: 1px solid #2a2a2a;
    color: #aaa; font-size: 13px;
  }
  .bi-footer a { color: #aaa; text-decoration: none; }
  .bi-footer a:hover { color: #e8e8e8; }
  .muted { color: #777; font-size: 12.5px; }

  @media (max-width: 1100px) {
    .bucket-strip { grid-template-columns: repeat(2, 1fr); }
  }
  @media (max-width: 700px) {
    .bucket-strip { grid-template-columns: 1fr; }
  }
</style>
