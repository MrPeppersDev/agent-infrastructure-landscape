<script lang="ts">
  // Benchmark trust leaderboard (issue #42).
  //
  // Companion to /analyses/benchmark-integrity. That view classifies
  // every benchmark mention into one of five integrity buckets; this
  // view turns those classifications into a single composite trust
  // score per benchmark so a reader can rank them at a glance. Pure
  // pivot — no new ingestion. The score formula lives in
  // $lib/analyses/benchmark-trust.ts (documented at top of file).

  import { base } from '$app/paths';
  import {
    buildBenchmarkTrust,
    mostTrusted,
    mostGamed,
    type BenchmarkTrust,
    type TrustTier,
    type CitingIntegrity
  } from '$lib/analyses/benchmark-trust';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  const rows = $derived(buildBenchmarkTrust(data.records));

  const topTrusted = $derived(mostTrusted(rows, 5));
  const topGamed = $derived(mostGamed(rows, 5));

  // Sorting state.
  type SortKey =
    | 'benchmarkName'
    | 'trustScore'
    | 'peerReviewedCount'
    | 'independentlyVerifiedCount'
    | 'vendorClaimedCount'
    | 'disputedCount'
    | 'totalMentions'
    | 'trustTier';
  let sortKey = $state<SortKey>('trustScore');
  let sortDir = $state<'asc' | 'desc'>('desc');

  function sortBy(key: SortKey) {
    if (sortKey === key) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      sortKey = key;
      // Default direction per column: name asc, everything else desc.
      sortDir = key === 'benchmarkName' ? 'asc' : 'desc';
    }
  }

  const tierOrder: Record<TrustTier, number> = {
    high: 0,
    medium: 1,
    low: 2,
    compromised: 3
  };

  const sortedRows = $derived.by(() => {
    const out = rows.slice();
    out.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'benchmarkName':
          cmp = a.benchmarkName.localeCompare(b.benchmarkName);
          break;
        case 'trustTier':
          cmp = tierOrder[a.trustTier] - tierOrder[b.trustTier];
          break;
        default:
          cmp = (a[sortKey] as number) - (b[sortKey] as number);
      }
      if (cmp === 0) {
        // Stable secondary sort: by name asc.
        cmp = a.benchmarkName.localeCompare(b.benchmarkName);
      } else if (sortDir === 'desc') {
        cmp = -cmp;
      }
      return cmp;
    });
    return out;
  });

  // Inline drilldown — one expanded row at a time keeps the leaderboard
  // readable. Click toggles.
  let expanded = $state<string | null>(null);
  function toggleExpand(benchmarkName: string) {
    expanded = expanded === benchmarkName ? null : benchmarkName;
  }

  function tableHref(name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  function fmtScore(n: number): string {
    return n.toFixed(1);
  }

  function fmtAge(months: number | null): string {
    if (months === null) return '—';
    if (months < 12) return `${months}mo`;
    const y = Math.floor(months / 12);
    const m = months % 12;
    return m === 0 ? `${y}y` : `${y}y ${m}mo`;
  }

  const tierLabel: Record<TrustTier, string> = {
    high: 'High',
    medium: 'Medium',
    low: 'Low',
    compromised: 'Compromised'
  };

  const integrityLabel: Record<CitingIntegrity, string> = {
    'peer-reviewed': 'Peer-reviewed',
    'independently-verified': 'Independent',
    'vendor-claimed': 'Vendor-claimed',
    disputed: 'Disputed'
  };

  function sortArrow(key: SortKey): string {
    if (sortKey !== key) return '';
    return sortDir === 'asc' ? ' ↑' : ' ↓';
  }
</script>

<svelte:head>
  <title>Benchmark trust leaderboard — Memory Landscape</title>
</svelte:head>

<main class="bt-page">
  <header class="bt-header">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Benchmark trust leaderboard</h1>
    <p class="bt-intro">
      Every benchmark in the catalog ranked by a composite <strong>trust score</strong>
      derived from the integrity classifications already mined in
      <a href="{base}/analyses/benchmark-integrity">benchmark integrity</a>.
      Peer-reviewed mentions raise the score, independently-verified
      mentions raise it a little more, disputed mentions push it down,
      and an all-vendor-claimed benchmark with ≥5 citations takes an
      orphan penalty on top. This is derived data — not an opinion —
      and the per-benchmark drilldown shows you exactly which systems
      contributed to each bucket.
    </p>
    <p class="bt-stats">
      <strong>{rows.length}</strong> benchmarks ranked ·
      formula in <code>$lib/analyses/benchmark-trust.ts</code>.
    </p>
  </header>

  <aside class="formula">
    <h2>How the score is computed</h2>
    <pre class="formula-body">score = pr% · 1.0  +  iv% · 1.2  −  disputed% · 1.5  −  vendor_orphan_penalty
        clamped to [0, 100]</pre>
    <p class="formula-note">
      Where <code>pr%</code> is the share of <em>peer-reviewed</em> mentions and
      <code>iv%</code> is the share of <em>independently-verified</em> mentions
      out of the four evaluable buckets (the "unverifiable" bucket is
      excluded from the denominator — missing citations shouldn't punish
      or rescue a benchmark). The vendor-orphan penalty fires when
      100% of mentions are vendor-claimed and there are ≥5 mentions —
      i.e. the benchmark exists only in vendor blog posts.
    </p>
    <ul class="tier-legend">
      <li><span class="tier-badge" data-tier="high">High</span> ≥ 70 — cite without caveat</li>
      <li><span class="tier-badge" data-tier="medium">Medium</span> 40 ≤ s &lt; 70 — show the integrity breakdown alongside</li>
      <li><span class="tier-badge" data-tier="low">Low</span> 20 ≤ s &lt; 40 — vendor-heavy or contested</li>
      <li><span class="tier-badge" data-tier="compromised">Compromised</span> &lt; 20 — needs independent corroboration</li>
    </ul>
  </aside>

  <section class="callouts" aria-label="Top-5 callouts">
    <article class="callout most-trusted">
      <header>
        <h2>Most trusted (top 5)</h2>
        <span class="callout-sub">highest composite scores</span>
      </header>
      {#if topTrusted.length === 0}
        <p class="empty">No benchmarks to rank.</p>
      {:else}
        <ol>
          {#each topTrusted as r, i (r.benchmarkName)}
            <li>
              <span class="rank">{i + 1}</span>
              <span class="bm-name">{r.benchmarkName}</span>
              <span class="bm-score">{fmtScore(r.trustScore)}</span>
              <span class="tier-badge" data-tier={r.trustTier}>{tierLabel[r.trustTier]}</span>
              <span class="bm-detail">
                {r.peerReviewedCount} peer-reviewed · {r.totalMentions} total
              </span>
            </li>
          {/each}
        </ol>
      {/if}
    </article>

    <article class="callout most-gamed">
      <header>
        <h2>Most gamed (bottom 5)</h2>
        <span class="callout-sub">≥5 vendor-claimed mentions only</span>
      </header>
      {#if topGamed.length === 0}
        <p class="empty">No benchmarks meet the ≥5 vendor-claimed threshold.</p>
      {:else}
        <ol>
          {#each topGamed as r, i (r.benchmarkName)}
            <li>
              <span class="rank">{i + 1}</span>
              <span class="bm-name">{r.benchmarkName}</span>
              <span class="bm-score">{fmtScore(r.trustScore)}</span>
              <span class="tier-badge" data-tier={r.trustTier}>{tierLabel[r.trustTier]}</span>
              <span class="bm-detail">
                {r.vendorClaimedCount} vendor-claimed · {r.disputedCount} disputed
              </span>
            </li>
          {/each}
        </ol>
      {/if}
    </article>
  </section>

  <section class="board" aria-label="Trust leaderboard">
    <h2 class="section-h">Full leaderboard</h2>
    <p class="section-sub">
      Click any column header to sort. Click a row to expand its list of
      citing systems with each system's integrity classification.
    </p>
    <div class="table-wrap">
      <table class="board-table">
        <thead>
          <tr>
            <th class="bench-col">
              <button type="button" onclick={() => sortBy('benchmarkName')}>
                Benchmark{sortArrow('benchmarkName')}
              </button>
            </th>
            <th class="num">
              <button type="button" onclick={() => sortBy('trustScore')}>
                Trust score{sortArrow('trustScore')}
              </button>
            </th>
            <th class="num peer-reviewed">
              <button type="button" onclick={() => sortBy('peerReviewedCount')}>
                Peer-reviewed{sortArrow('peerReviewedCount')}
              </button>
            </th>
            <th class="num independently-verified">
              <button type="button" onclick={() => sortBy('independentlyVerifiedCount')}>
                Verified{sortArrow('independentlyVerifiedCount')}
              </button>
            </th>
            <th class="num vendor-claimed">
              <button type="button" onclick={() => sortBy('vendorClaimedCount')}>
                Vendor-claimed{sortArrow('vendorClaimedCount')}
              </button>
            </th>
            <th class="num disputed">
              <button type="button" onclick={() => sortBy('disputedCount')}>
                Disputed{sortArrow('disputedCount')}
              </button>
            </th>
            <th class="num">
              <button type="button" onclick={() => sortBy('totalMentions')}>
                Total{sortArrow('totalMentions')}
              </button>
            </th>
            <th>
              <button type="button" onclick={() => sortBy('trustTier')}>
                Tier{sortArrow('trustTier')}
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {#each sortedRows as r (r.benchmarkName)}
            {@const isOpen = expanded === r.benchmarkName}
            <tr class="row" class:open={isOpen} onclick={() => toggleExpand(r.benchmarkName)}>
              <td class="bench-col">
                <span class="caret" aria-hidden="true">{isOpen ? '▾' : '▸'}</span>
                {#if r.benchmarkId}
                  <a
                    href={tableHref(r.benchmarkName)}
                    onclick={(e) => e.stopPropagation()}
                    class="bench-link"
                  >{r.benchmarkName}</a>
                {:else}
                  <span class="bench-text">{r.benchmarkName}</span>
                  <span class="muted-tag" title="Not catalogued as its own record">mentions-only</span>
                {/if}
                {#if r.ageMonths !== null}
                  <span class="age-pill">{fmtAge(r.ageMonths)}</span>
                {/if}
              </td>
              <td class="num score-cell">
                <span class="score-num">{fmtScore(r.trustScore)}</span>
                <span class="score-bar-wrap" aria-hidden="true">
                  <span class="score-bar" data-tier={r.trustTier} style:width="{r.trustScore}%"></span>
                </span>
              </td>
              <td class="num peer-reviewed">{r.peerReviewedCount || '—'}</td>
              <td class="num independently-verified">{r.independentlyVerifiedCount || '—'}</td>
              <td class="num vendor-claimed">{r.vendorClaimedCount || '—'}</td>
              <td class="num disputed">{r.disputedCount || '—'}</td>
              <td class="num total-cell">{r.totalMentions}</td>
              <td>
                <span class="tier-badge" data-tier={r.trustTier}>{tierLabel[r.trustTier]}</span>
              </td>
            </tr>
            {#if isOpen}
              <tr class="drill-row">
                <td colspan="8">
                  <div class="drill-body">
                    <h3>
                      {r.benchmarkName}
                      <span class="drill-sub">
                        {r.citingSystems.length} citing system{r.citingSystems.length === 1 ? '' : 's'}
                        · trust score {fmtScore(r.trustScore)}
                      </span>
                    </h3>
                    {#if r.citingSystems.length === 0}
                      <p class="empty">No catalogued citing systems for this benchmark.</p>
                    {:else}
                      <ul class="citing-list">
                        {#each r.citingSystems as c (c.id)}
                          <li>
                            <a href={tableHref(c.name)}>{c.name}</a>
                            <span class="integrity-pill" data-integrity={c.integrity}>
                              {integrityLabel[c.integrity]}
                            </span>
                          </li>
                        {/each}
                      </ul>
                    {/if}
                  </div>
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <footer class="bt-footer">
    <a href="{base}/analyses">← Analyses hub</a>
    <span class="muted">
      Derived from integrity classifications in
      <code>$lib/analyses/benchmark-integrity.ts</code>.
      Score formula in <code>$lib/analyses/benchmark-trust.ts</code>.
    </span>
  </footer>
</main>

<style>
  .bt-page {
    max-width: 1500px;
    margin: 0 auto;
    padding: 24px 8px 64px;
    color: #e8e8e8;
  }
  .bt-header { margin-bottom: 18px; }
  .crumb { margin: 0 0 8px 0; font-size: 13px; }
  .crumb a { color: #aaa; text-decoration: none; }
  .crumb a:hover { color: #e8e8e8; }
  .bt-header h1 {
    font-size: 28px; margin: 0 0 10px 0; letter-spacing: -0.01em;
  }
  .bt-intro {
    color: #c9c9c9; max-width: 920px; margin: 0 0 12px 0;
    line-height: 1.6; font-size: 14px;
  }
  .bt-intro strong { color: #e8e8e8; }
  .bt-intro a { color: #d4845f; }
  .bt-stats { color: #d4d4d4; margin: 0; font-size: 13.5px; }
  .bt-stats strong { color: #d4845f; }
  code {
    font-family: 'SF Mono', 'Menlo', Consolas, monospace;
    font-size: 12.5px; background: #1f1f1f;
    padding: 1px 5px; border-radius: 3px; color: #d4d4d4;
  }

  .formula {
    background: #14191d;
    border: 1px solid #233038;
    border-left: 3px solid #d4845f;
    border-radius: 6px;
    padding: 14px 18px 12px;
    margin: 0 0 18px 0;
  }
  .formula h2 {
    margin: 0 0 10px 0; font-size: 13px;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: #d4845f; font-weight: 600;
  }
  .formula-body {
    margin: 0 0 8px 0; padding: 8px 12px;
    background: #0e1115; border: 1px solid #232323;
    border-radius: 4px;
    font-family: 'SF Mono', 'Menlo', Consolas, monospace;
    font-size: 12.5px; color: #f4e2cb; line-height: 1.5;
    white-space: pre-wrap;
  }
  .formula-note {
    color: #aaa; font-size: 12.5px; line-height: 1.55;
    margin: 0 0 10px 0; max-width: 880px;
  }
  .formula-note em { color: #c0c0c0; font-style: normal; }
  .tier-legend {
    list-style: none; margin: 0; padding: 0;
    display: flex; flex-wrap: wrap; gap: 10px 18px;
    font-size: 12px; color: #aaa;
  }
  .tier-legend li {
    display: inline-flex; align-items: center; gap: 6px;
  }

  .tier-badge {
    display: inline-block; font-size: 11px; font-weight: 600;
    padding: 2px 8px; border-radius: 3px;
    background: #2a2a2a; color: #d4d4d4;
    letter-spacing: 0.02em; line-height: 1.3;
    flex-shrink: 0;
  }
  .tier-badge[data-tier='high'] { background: #1a3a2a; color: #8ec99a; }
  .tier-badge[data-tier='medium'] { background: #2a2a14; color: #d8c870; }
  .tier-badge[data-tier='low'] { background: #2a1f10; color: #c98a4e; }
  .tier-badge[data-tier='compromised'] { background: #2a1414; color: #d4877a; }

  .callouts {
    display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
    margin: 0 0 20px 0;
  }
  .callout {
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 8px; padding: 14px 18px 12px;
  }
  .callout.most-trusted { border-left: 3px solid #6b9a4a; }
  .callout.most-gamed { border-left: 3px solid #c04e4e; }
  .callout header {
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 1px solid #232323; margin-bottom: 10px; padding-bottom: 6px;
  }
  .callout h2 { margin: 0; font-size: 14px; color: #e8e8e8; }
  .callout.most-trusted h2 { color: #8ec99a; }
  .callout.most-gamed h2 { color: #d4877a; }
  .callout-sub { color: #888; font-size: 11.5px; }
  .callout ol {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 6px;
  }
  .callout li {
    display: grid;
    grid-template-columns: 18px 1fr auto auto;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }
  .callout li .rank {
    color: #888; font-variant-numeric: tabular-nums;
    text-align: right;
  }
  .bm-name {
    color: #e8e8e8; font-weight: 500;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .bm-score {
    color: #f4e2cb; font-weight: 600;
    font-variant-numeric: tabular-nums;
    font-size: 13px;
  }
  .bm-detail {
    grid-column: 2 / -1;
    color: #888; font-size: 11.5px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }

  .section-h {
    margin: 0 0 6px 0; font-size: 18px;
    color: #e8e8e8; letter-spacing: -0.005em;
  }
  .section-sub {
    color: #aaa; font-size: 13px; margin: 0 0 14px 0;
    line-height: 1.55; max-width: 920px;
  }

  .board { margin-bottom: 28px; }
  .table-wrap {
    overflow-x: auto; border: 1px solid #2a2a2a; border-radius: 8px;
    background: #181818;
  }
  .board-table {
    border-collapse: collapse; font-size: 13px;
    min-width: 100%; width: 100%;
  }
  .board-table thead th {
    position: sticky; top: 0; background: #1d1d1d;
    border-bottom: 1px solid #333;
    padding: 0; text-align: left;
    font-weight: 600; color: #d4d4d4; white-space: nowrap;
    font-size: 12px;
  }
  .board-table thead th button {
    background: none; border: none; cursor: pointer;
    color: inherit; font: inherit; font-weight: 600;
    padding: 9px 12px; width: 100%;
    text-align: inherit;
    letter-spacing: 0.02em;
    transition: background 100ms;
  }
  .board-table thead th button:hover { background: #232323; color: #e8e8e8; }
  .board-table th.num button { text-align: right; }
  .board-table th.peer-reviewed button { color: #8ec99a; }
  .board-table th.independently-verified button { color: #9fc5e0; }
  .board-table th.vendor-claimed button { color: #c9a26e; }
  .board-table th.disputed button { color: #d4877a; }
  .board-table th.num, .board-table td.num {
    text-align: right; font-variant-numeric: tabular-nums;
  }
  .board-table tbody td {
    border-bottom: 1px solid #232323; padding: 7px 12px;
    vertical-align: middle;
  }
  .board-table tbody tr.row {
    cursor: pointer; transition: background 80ms;
  }
  .board-table tbody tr.row:hover { background: #1c1c1c; }
  .board-table tbody tr.row.open { background: #1f1d1a; }
  .board-table tbody tr.row.open td { border-bottom-color: #1f1d1a; }
  .bench-col {
    color: #e8e8e8; font-weight: 500;
    display: flex; align-items: center; gap: 8px;
  }
  .caret {
    color: #777; font-size: 11px;
    width: 12px; flex-shrink: 0;
  }
  .bench-link {
    color: #e8e8e8; text-decoration: none;
  }
  .bench-link:hover { color: #d4845f; }
  .bench-text { color: #e8e8e8; }
  .muted-tag {
    display: inline-block; background: #232323; color: #888;
    padding: 1px 6px; border-radius: 3px; font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .age-pill {
    display: inline-block; background: #1f2a33; color: #9fc5e0;
    padding: 1px 6px; border-radius: 3px; font-size: 10.5px;
    font-variant-numeric: tabular-nums;
  }

  .score-cell {
    min-width: 140px;
    display: flex; align-items: center; gap: 8px;
    justify-content: flex-end;
  }
  .score-num {
    color: #f4e2cb; font-weight: 600;
    font-variant-numeric: tabular-nums;
    min-width: 38px; text-align: right;
  }
  .score-bar-wrap {
    flex: 1; min-width: 60px; max-width: 100px;
    height: 6px; background: #232323;
    border-radius: 3px; overflow: hidden;
    display: inline-block;
  }
  .score-bar {
    display: block; height: 100%;
    border-radius: 3px; transition: width 200ms;
  }
  .score-bar[data-tier='high'] { background: #6b9a4a; }
  .score-bar[data-tier='medium'] { background: #b8a040; }
  .score-bar[data-tier='low'] { background: #c98a4e; }
  .score-bar[data-tier='compromised'] { background: #c04e4e; }

  .board-table td.peer-reviewed { color: #8ec99a; }
  .board-table td.independently-verified { color: #9fc5e0; }
  .board-table td.vendor-claimed { color: #c9a26e; }
  .board-table td.disputed { color: #d4877a; }
  .total-cell { color: #d4d4d4; font-weight: 600; }

  .drill-row {
    background: #1a1815;
  }
  .drill-row td {
    padding: 12px 18px 16px !important;
    border-bottom: 1px solid #2a2a2a !important;
  }
  .drill-body h3 {
    margin: 0 0 10px 0; font-size: 14px; color: #f4e2cb;
    font-weight: 600;
  }
  .drill-sub {
    color: #888; font-size: 12px; font-weight: 400;
    margin-left: 8px;
  }
  .citing-list {
    list-style: none; margin: 0; padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 6px 14px;
  }
  .citing-list li {
    display: flex; align-items: center; gap: 8px;
    font-size: 12.5px;
    padding: 3px 0;
  }
  .citing-list li a {
    color: #e8e8e8; text-decoration: none;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    flex: 1; min-width: 0;
  }
  .citing-list li a:hover { color: #d4845f; }

  .integrity-pill {
    display: inline-block; font-size: 10.5px; font-weight: 600;
    padding: 1px 6px; border-radius: 3px;
    background: #2a2a2a; color: #d4d4d4;
    letter-spacing: 0.02em; flex-shrink: 0;
  }
  .integrity-pill[data-integrity='peer-reviewed'] { background: #1d2a1d; color: #8ec99a; }
  .integrity-pill[data-integrity='independently-verified'] { background: #1d2530; color: #9fc5e0; }
  .integrity-pill[data-integrity='vendor-claimed'] { background: #2a1d10; color: #c9a26e; }
  .integrity-pill[data-integrity='disputed'] { background: #2a1414; color: #d4877a; }

  .empty {
    color: #888; font-style: italic;
    padding: 12px; text-align: center;
  }

  .bt-footer {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 24px; padding-top: 16px;
    border-top: 1px solid #2a2a2a;
    color: #aaa; font-size: 13px;
    flex-wrap: wrap; gap: 8px;
  }
  .bt-footer a { color: #aaa; text-decoration: none; }
  .bt-footer a:hover { color: #e8e8e8; }
  .muted { color: #777; font-size: 12.5px; }

  @media (max-width: 900px) {
    .callouts { grid-template-columns: 1fr; }
  }
</style>
