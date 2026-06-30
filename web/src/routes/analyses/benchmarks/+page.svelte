<script lang="ts">
  import SeoHead from '$lib/components/SeoHead.svelte';

  // Benchmark coverage matrix (issue #24, Round 8 upgrade).
  //
  // For every memory / agent benchmark that any system has reported a score
  // on, show which systems have a score and what that score is. The new
  // parser (see $lib/analyses/benchmarks.ts) is HTML-aware, prefers
  // unit-suffixed scores over bare proximity numbers, and clips its search
  // window at neighbouring benchmark mentions — so each cell shows the
  // actual number (e.g. "92.2%") rather than a checkmark.
  //
  // Layout:
  //   1. Narrative header — what this view is for, what to look at
  //   2. Methodology callout — parser priority order + canonicalisation +
  //      parser-quality stats so the reader knows the trust level
  //   3. Tier filter row — restrict matrix to T1 / T2 / T3 / T4 / T5 systems
  //   4. Coverage-tier banner — well-covered vs emerging vs too-narrow
  //   5. The matrix with heat-coloured cells; click cell → main table
  //   6. Per-benchmark leaderboard cards (top-N by absolute score)
  //   7. Memory-vs-domain split as a stacked horizontal bar
  //   8. Per-system coverage + "so what" interpretation

  import {
    extractScores,
    buildMatrix,
    benchmarkCoverage,
    systemCoverage,
    adoptionSplit,
    isMemoryBenchmark,
    parseScoreNum,
    leaderboard,
    coverageTiers,
    parserStats,
    memDomainBuckets
  } from '$lib/analyses/benchmarks';
  import { base } from '$app/paths';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  // Tier filter — multi-select. Default: all tiers.
  let activeTiers = $state<Set<number>>(new Set([1, 2, 3, 4, 5]));

  function toggleTier(t: number) {
    const next = new Set(activeTiers);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    if (next.size === 0) next.add(t);
    activeTiers = next;
  }

  const allScores = $derived(extractScores(data.records));
  const scores = $derived(allScores.filter((s) => activeTiers.has(s.tier)));
  const matrix = $derived(buildMatrix(scores, 14));
  const coverage = $derived(benchmarkCoverage(scores));
  const sysCoverage = $derived(systemCoverage(scores));
  const split = $derived(adoptionSplit(scores));
  const stats = $derived(parserStats(allScores));
  const tiers = $derived(coverageTiers(allScores));
  const buckets = $derived(memDomainBuckets(scores));

  // Every matrix benchmark gets a leaderboard (so column-header links resolve).
  const featuredBenchmarks = ['LongMemEval', 'LoCoMo', 'BABILong', 'ConvoMem', 'GAIA'];
  const leaderboards = $derived.by(() => {
    const seen = new Set<string>();
    const out: { name: string; rows: ReturnType<typeof leaderboard>; featured: boolean }[] = [];
    for (const name of featuredBenchmarks) {
      seen.add(name);
      out.push({ name, rows: leaderboard(scores, name, 8), featured: true });
    }
    for (const b of matrix.benchmarks) {
      if (seen.has(b.name)) continue;
      seen.add(b.name);
      out.push({ name: b.name, rows: leaderboard(scores, b.name, 8), featured: false });
    }
    return out;
  });

  // Per-benchmark min/max of *absolute* scores (excludes deltas).
  const colStats = $derived.by(() => {
    const m = new Map<string, { min: number; max: number; count: number }>();
    for (const b of matrix.benchmarks) {
      const nums: number[] = [];
      for (const s of matrix.systems) {
        const c = matrix.cells.get(`${s.id}::${b.name}`);
        if (!c) continue;
        const { n, isDelta } = parseScoreNum(c.score);
        if (n !== null && !isDelta) nums.push(n);
      }
      if (nums.length >= 2) {
        m.set(b.name, { min: Math.min(...nums), max: Math.max(...nums), count: nums.length });
      }
    }
    return m;
  });

  function heatStyle(benchmark: string, score: string): string {
    const stats = colStats.get(benchmark);
    if (!stats || stats.count < 2) return '';
    const { n, isDelta } = parseScoreNum(score);
    if (n === null || isDelta) return '';
    const range = stats.max - stats.min;
    if (range === 0) return '';
    const t = (n - stats.min) / range;
    const hue = 30;
    const sat = 25 + Math.round(t * 55);
    const light = 16 + Math.round(t * 14);
    return `background: hsl(${hue} ${sat}% ${light}% / 0.92);`;
  }

  function tableHref(rid: string, name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  function scrollToLeaderboard(bench: string, e: Event) {
    e.preventDefault();
    const el = document.getElementById(`lb-${bench}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  const totalSystemsWithScore = $derived(sysCoverage.length);
  const totalBenchmarks = $derived(coverage.length);
  const topBenchmark = $derived(coverage[0]?.benchmark ?? '—');
  const topSystems = $derived(sysCoverage.slice(0, 10));

  const tierLabels: Record<number, string> = {
    1: 'commercial',
    2: 'productized',
    3: 'framework',
    4: 'research',
    5: 'informal'
  };

  function pct(n: number): string {
    return `${Math.round(n * 100)}%`;
  }

  const splitTotal = $derived(
    split.memoryOnlySystems + split.bothSystems + split.domainOnlySystems
  );
  function pctOf(n: number): number {
    return splitTotal === 0 ? 0 : (n / splitTotal) * 100;
  }
</script>

<svelte:head>
  <SeoHead
    title="AI Memory Benchmark Coverage Matrix"
    description="Product × benchmark coverage across the AI agent memory catalog — which benchmarks are reported by which products, and the empty cells that tell the real story."
    path="/analyses/benchmarks"
    ogType="article"
  />
</svelte:head>

<main class="bench-page">
  <header class="bench-header">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Benchmark coverage matrix</h1>
    <p class="bench-intro">
      Which memory and agent benchmarks each system has reported scores on,
      and how those scores compare. Memory papers split into two camps:
      a <em>memory-specific</em> bench family (LongMemEval, LoCoMo, BABILong,
      ConvoMem, RULER, MemoryAgentBench, NIAH) that tests recall across
      sessions and long contexts, and a <em>domain-specific</em> family
      (GAIA, SWE-bench, WebArena, OSWorld, AIME) that tests downstream
      task performance where memory is one ingredient among many.
      Coverage matters because a benchmark with only a handful of reporters
      can't drive head-to-head comparison — and the
      <strong>memory-specific family is genuinely under-adopted</strong>
      relative to its design intent.
    </p>
    <p class="bench-stats">
      <strong>{totalSystemsWithScore}</strong> systems with at least one
      score · <strong>{totalBenchmarks}</strong> distinct benchmarks
      tracked · most-reported: <strong>{topBenchmark}</strong>
      ({coverage[0]?.count ?? 0} systems)
    </p>
  </header>

  <aside class="methodology">
    <h2>How scores are extracted</h2>
    <ol class="method-steps">
      <li>
        <strong>Source priority:</strong> <code>cells.perf.value</code>
        first; <code>cells.claims.value</code> only when <code>perf</code>
        doesn't mention the benchmark. Cells marked as <code>no-data</code>
        or sentinels like <em>"no public benchmark scores found"</em> are
        skipped.
      </li>
      <li>
        <strong>Canonicalisation:</strong> aliases collapse to one name —
        <code>LMES</code>, <code>LME</code>, <code>LongMem-Eval</code>,
        <code>LongMemEval-S</code> all become <code>LongMemEval</code>;
        <code>SciWorld</code> becomes <code>ScienceWorld</code>;
        <code>BABI-Long</code> becomes <code>BABILong</code>.
      </li>
      <li>
        <strong>Score-shape priority (clipped at neighbouring benchmark mentions):</strong>
        (1) unit-suffixed in left window (<code>92.2%</code>,
        <code>+18.7pp</code>, <code>0.91 F1</code>);
        (2) unit-suffixed in right window;
        (3) bare decimal in perf only (<code>0.700 LoCoMo</code>);
        (4) short bare int adjacent in perf only (<code>30 ConvoMem</code>).
        Claims-mode skips bare numbers — they're usually pass@k,
        k-shot, or version-number noise.
      </li>
      <li>
        <strong>Parser self-report:</strong>
        <strong>{pct(stats.perfCoverage)}</strong> of perf mentions yielded
        a parseable score ({stats.perfWithScore}/{stats.perfMentions});
        <strong>{pct(stats.claimsCoverage)}</strong> of claims mentions did
        ({stats.claimsWithScore}/{stats.claimsMentions}). Cells without a
        score still get a presence ✓.
      </li>
    </ol>
  </aside>

  <section class="filter-row" aria-label="Filter by tier">
    <span class="filter-label">Show tiers:</span>
    {#each [1, 2, 3, 4, 5] as t}
      <button
        type="button"
        class="tier-btn"
        class:active={activeTiers.has(t)}
        onclick={() => toggleTier(t)}
        aria-pressed={activeTiers.has(t)}
      >
        T{t} <span class="tier-sub">{tierLabels[t]}</span>
      </button>
    {/each}
    <span class="filter-hint">click a cell or system name → main table filtered to that record</span>
  </section>

  <section class="coverage-tiers">
    {#each tiers as group (group.tier)}
      {#if group.benchmarks.length > 0}
        <div class="cov-group" data-tier={group.tier}>
          <div class="cov-head">
            <span class="cov-label">
              {#if group.tier === 'well-covered'}Well-covered (≥10 systems){/if}
              {#if group.tier === 'emerging'}Emerging (5–9 systems){/if}
              {#if group.tier === 'too-narrow'}Too narrow to compare (&lt;5 systems){/if}
            </span>
            <span class="cov-count">{group.benchmarks.length}</span>
          </div>
          <ul class="cov-chips">
            {#each group.benchmarks as b (b.benchmark)}
              <li class:memory={isMemoryBenchmark(b.benchmark)}>
                {b.benchmark} <span class="chip-n">{b.count}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    {/each}
  </section>

  {#if matrix.systems.length === 0}
    <p class="empty">No benchmark scores parsed from the catalog under the current filter.</p>
  {:else}
    <section class="matrix-wrap">
      <table class="matrix">
        <thead>
          <tr>
            <th class="sys-col">System</th>
            {#each matrix.benchmarks as b (b.name)}
              <th
                class="bench-col"
                class:memory={isMemoryBenchmark(b.name)}
                title="{b.name} — reported by {b.count} systems. Click for leaderboard."
              >
                <a class="bench-link" href="#lb-{b.name}" onclick={(e) => scrollToLeaderboard(b.name, e)}>
                  <span class="bench-name">{b.name}</span>
                  <span class="bench-count">{b.count}</span>
                </a>
              </th>
            {/each}
            <th class="total-col" title="Distinct in-matrix benchmarks this system reports">N</th>
          </tr>
        </thead>
        <tbody>
          {#each matrix.systems as s (s.id)}
            <tr>
              <td class="sys-col">
                <a href={tableHref(s.id, s.name)}>{s.name}</a>
                <span class="tier-pill" data-tier={s.tier}>T{s.tier}</span>
              </td>
              {#each matrix.benchmarks as b (b.name)}
                {@const cell = matrix.cells.get(`${s.id}::${b.name}`)}
                {#if cell}
                  {@const { isDelta } = parseScoreNum(cell.score)}
                  <td
                    class="cell"
                    class:from-claims={cell.source === 'claims'}
                    class:delta={isDelta}
                    style={heatStyle(b.name, cell.score)}
                    title={`${b.name}: ${cell.score || '(presence only)'} — source: ${cell.source}. Click → filter main table to ${s.name}.`}
                  >
                    <a class="cell-link" href={tableHref(s.id, s.name)}>
                      {cell.score || '✓'}
                    </a>
                  </td>
                {:else}
                  <td class="cell empty-cell"></td>
                {/if}
              {/each}
              <td class="total-col"><span class="count-pill">{s.count}</span></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>

    <section class="leaderboards" aria-label="Per-benchmark leaderboards">
      <h2 class="section-h">Per-benchmark leaderboards</h2>
      <p class="section-sub">
        Top systems on each benchmark, ranked by reported <em>absolute</em>
        score. Deltas (<code>+18.7pp</code>) are excluded — they aren't
        comparable across baselines. The tier pill marks the source
        record's tier (T1 commercial → T5 informal). Scores from
        <code>claims</code> rather than <code>perf</code> are marked with
        a small dot.
      </p>
      <div class="lb-grid">
        {#each leaderboards as lb (lb.name)}
          <article class="lb-card" id="lb-{lb.name}" class:featured={lb.featured}>
            <header class="lb-head">
              <h3 class:memory={isMemoryBenchmark(lb.name)}>{lb.name}</h3>
              <span class="lb-sub">
                {lb.rows.length} with absolute score
              </span>
            </header>
            {#if lb.rows.length === 0}
              <p class="lb-empty">No absolute scores parsed under the current filter.</p>
            {:else}
              <ol class="lb-list">
                {#each lb.rows as row, i (row.record_id)}
                  <li>
                    <span class="lb-rank">{i + 1}</span>
                    <a class="lb-name" href={tableHref(row.record_id, row.record_name)}>
                      {row.record_name}
                    </a>
                    <span class="tier-pill small" data-tier={row.tier}>T{row.tier}</span>
                    <span class="lb-score" class:from-claims={row.source === 'claims'}>
                      {row.score}{#if row.source === 'claims'}<span class="dot" title="from claims cell, not perf"></span>{/if}
                    </span>
                  </li>
                {/each}
              </ol>
            {/if}
          </article>
        {/each}
      </div>
    </section>

    <section class="split-section">
      <h2 class="section-h">Memory-specific vs domain-specific adoption</h2>
      <p class="section-sub">
        Each system is classified by which benchmark <em>family</em> it
        reports on. The stacked bar shows the population split; the three
        columns underneath list who falls into each bucket.
        <strong>So what:</strong> the "domain-only" fraction is the
        evidence for the recurring observation that memory papers
        default to the agent benchmark of their target domain rather
        than reporting on a memory-specific axis their architecture
        would seem to target.
      </p>

      <div class="stacked-bar">
        <div class="seg seg-mem" style="width: {pctOf(split.memoryOnlySystems)}%;" title="Memory-only: {split.memoryOnlySystems}">
          {#if pctOf(split.memoryOnlySystems) > 6}<span>Memory-only · {split.memoryOnlySystems}</span>{/if}
        </div>
        <div class="seg seg-both" style="width: {pctOf(split.bothSystems)}%;" title="Both: {split.bothSystems}">
          {#if pctOf(split.bothSystems) > 4}<span>Both · {split.bothSystems}</span>{/if}
        </div>
        <div class="seg seg-dom" style="width: {pctOf(split.domainOnlySystems)}%;" title="Domain-only: {split.domainOnlySystems}">
          {#if pctOf(split.domainOnlySystems) > 6}<span>Domain-only · {split.domainOnlySystems}</span>{/if}
        </div>
      </div>

      <div class="bucket-grid">
        {#each buckets as bucket (bucket.category)}
          <article class="bucket" data-cat={bucket.category}>
            <header>
              <h4>
                {#if bucket.category === 'memory-only'}Memory-only{/if}
                {#if bucket.category === 'both'}Both families{/if}
                {#if bucket.category === 'domain-only'}Domain-only{/if}
              </h4>
              <span class="bucket-n">{bucket.systems.length}</span>
            </header>
            <ul>
              {#each bucket.systems.slice(0, 20) as sys (sys.record_id)}
                <li>
                  <a href={tableHref(sys.record_id, sys.record_name)}>{sys.record_name}</a>
                  <span class="tier-pill small" data-tier={sys.tier}>T{sys.tier}</span>
                </li>
              {/each}
              {#if bucket.systems.length > 20}
                <li class="more">… {bucket.systems.length - 20} more</li>
              {/if}
            </ul>
          </article>
        {/each}
      </div>
    </section>

    <section class="insights">
      <article class="card">
        <h2>Most-benchmarked systems</h2>
        <p class="desc">Top-10 systems by distinct benchmarks reported under the current tier filter.</p>
        <ol class="ranked">
          {#each topSystems as s, i (s.record_id)}
            <li>
              <span class="rank">{i + 1}</span>
              <a href={tableHref(s.record_id, s.record_name)}>{s.record_name}</a>
              <span class="badges">
                {#each s.benchmarks as b}
                  <span class="badge" class:mem={isMemoryBenchmark(b)}>{b}</span>
                {/each}
              </span>
              <span class="count-pill">{s.count}</span>
            </li>
          {/each}
        </ol>
      </article>

      <article class="card">
        <h2>What to make of this</h2>
        <ul class="so-what">
          <li>
            <strong>LoCoMo and LongMemEval are the de-facto memory leaderboards.</strong>
            If you want to compare a new memory system head-to-head
            against shipping work, these are the two benchmarks you'd
            run first. T2 productized systems (MemPalace, OMEGA, Mastra,
            ByteRover) crowd the top of LongMemEval; T1 commercial
            (Mem0, Zep, Letta) cluster around 84-91% on LoCoMo.
          </li>
          <li>
            <strong>ConvoMem is under-adopted.</strong> Only ~2 systems
            report on it (Mem0 plus an opaque Supermemory mention), so
            it can't drive cross-system comparison — it's effectively
            a single-paper artefact. It shows up in the "too narrow"
            tier above.
          </li>
          <li>
            <strong>Memory papers benchmark on their target domain.</strong>
            A paper proposing a memory system for web agents (Mind2Web,
            WebArena) usually reports on its target domain rather than
            on a memory-specific axis. The "both families" bucket is
            small relative to "domain-only" — the user's recurring
            observation about evaluation discipline in the field.
          </li>
          <li>
            <strong>Filter to T1 only to see the commercial story directly.</strong>
            The commercial vendors converge on LoCoMo + LongMemEval as
            the comparison axis — that convergence is what makes those
            two benchmarks credible.
          </li>
        </ul>
      </article>
    </section>
  {/if}

  <footer class="bench-footer">
    <a href="{base}/analyses">← Analyses hub</a>
    <span class="muted">
      Sources: <code>cells.perf</code> (primary), <code>cells.claims</code>
      (fallback). Parser in
      <code>$lib/analyses/benchmarks.ts</code>.
    </span>
  </footer>
</main>

<style>
  .bench-page {
    max-width: 1500px;
    margin: 0 auto;
    padding: 24px 8px 64px;
    color: #e8e8e8;
  }
  .bench-header { margin-bottom: 18px; }
  .crumb { margin: 0 0 8px 0; font-size: 13px; }
  .crumb a { color: #aaa; text-decoration: none; }
  .crumb a:hover { color: #e8e8e8; }
  .bench-header h1 { font-size: 28px; margin: 0 0 10px 0; letter-spacing: -0.01em; }
  .bench-intro {
    color: #c9c9c9; max-width: 920px; margin: 0 0 12px 0;
    line-height: 1.6; font-size: 14px;
  }
  .bench-intro em { color: #f0c894; font-style: normal; }
  .bench-stats { color: #d4d4d4; margin: 0; font-size: 13.5px; }
  .bench-stats strong { color: #f0c894; }
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
    margin: 0 0 8px 0; font-size: 13px;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: #9fc5e0; font-weight: 600;
  }
  .method-steps {
    margin: 0; padding-left: 18px;
    color: #d0d0d0; font-size: 13px; line-height: 1.55;
  }
  .method-steps li { margin-bottom: 4px; }
  .method-steps strong { color: #e8e8e8; }
  .method-steps em { color: #9fc5e0; font-style: normal; }

  .filter-row {
    display: flex; align-items: center; flex-wrap: wrap;
    gap: 8px; margin: 0 0 14px 0;
    padding: 10px 12px;
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 6px;
  }
  .filter-label { color: #aaa; font-size: 12.5px; font-weight: 600; margin-right: 4px; }
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
  .tier-sub { color: inherit; opacity: 0.7; font-size: 11px; }
  .filter-hint {
    margin-left: auto; color: #777; font-size: 11.5px; font-style: italic;
  }

  .coverage-tiers {
    display: grid; grid-template-columns: 1.4fr 1fr 1fr;
    gap: 10px; margin: 0 0 20px 0;
  }
  .cov-group {
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 6px; padding: 10px 12px;
  }
  .cov-group[data-tier='well-covered'] { border-left: 3px solid #6b9a4a; }
  .cov-group[data-tier='emerging'] { border-left: 3px solid #c98a4e; }
  .cov-group[data-tier='too-narrow'] { border-left: 3px solid #8a4a4a; }
  .cov-head {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 8px;
  }
  .cov-label { color: #d4d4d4; font-size: 12.5px; font-weight: 600; }
  .cov-count {
    color: #888; font-size: 11px; font-variant-numeric: tabular-nums;
    background: #2a2a2a; padding: 1px 7px; border-radius: 8px;
  }
  .cov-chips {
    list-style: none; padding: 0; margin: 0;
    display: flex; flex-wrap: wrap; gap: 4px;
  }
  .cov-chips li {
    background: #1f2a33; color: #9fc5e0;
    padding: 2px 7px; border-radius: 3px;
    font-size: 11.5px; font-variant-numeric: tabular-nums;
  }
  .cov-chips li.memory { background: #3a2c1d; color: #f0c894; }
  .chip-n { color: inherit; opacity: 0.6; margin-left: 3px; font-size: 10.5px; }

  .matrix-wrap {
    overflow-x: auto; border: 1px solid #2a2a2a; border-radius: 8px;
    background: #181818; margin-bottom: 28px;
  }
  .matrix { border-collapse: collapse; font-size: 12.5px; min-width: 100%; }
  .matrix thead th {
    position: sticky; top: 0; background: #1d1d1d;
    border-bottom: 1px solid #333;
    padding: 8px 8px; text-align: left;
    font-weight: 600; color: #d4d4d4; white-space: nowrap;
  }
  .matrix thead th.bench-col { text-align: center; min-width: 80px; }
  .matrix thead th.bench-col.memory { color: #f0c894; }
  .bench-link { color: inherit; text-decoration: none; display: block; }
  .bench-link:hover .bench-name { text-decoration: underline; }
  .bench-name { display: block; font-size: 12px; }
  .bench-count {
    display: block; font-size: 10.5px; color: #888;
    font-weight: 400; margin-top: 1px;
  }
  .matrix thead th.bench-col.memory .bench-count { color: #c9a26e; }
  .matrix thead th.sys-col {
    position: sticky; left: 0; z-index: 2;
    background: #1d1d1d; min-width: 240px;
  }
  .matrix thead th.total-col { text-align: center; min-width: 40px; }
  .matrix tbody td {
    border-bottom: 1px solid #232323; padding: 5px 8px; vertical-align: middle;
  }
  .matrix tbody td.sys-col {
    position: sticky; left: 0; background: #181818;
    border-right: 1px solid #2a2a2a;
    font-size: 13px; z-index: 1;
    display: flex; align-items: center; gap: 6px;
  }
  .matrix tbody td.sys-col a {
    color: #e8e8e8; text-decoration: none; flex: 1;
  }
  .matrix tbody td.sys-col a:hover { color: #f0c894; }
  .matrix tbody tr:hover td.sys-col { background: #1f1f1f; }
  .matrix tbody tr:hover td.cell { filter: brightness(1.18); }
  .matrix .cell {
    text-align: center; font-variant-numeric: tabular-nums;
    color: #f4e2cb; min-width: 64px; cursor: pointer; padding: 0;
  }
  .cell-link {
    color: inherit; text-decoration: none; display: block;
    padding: 5px 8px;
  }
  .matrix .cell.empty-cell {
    background: transparent; color: #333; cursor: default;
  }
  .matrix .cell.delta .cell-link { font-style: italic; color: #d4d4d4; }
  .matrix .cell.from-claims { border-left: 2px solid #5e8aa3; }
  .matrix .total-col { text-align: center; }
  .count-pill {
    display: inline-block; background: #2a2a2a; color: #f0c894;
    padding: 1px 7px; border-radius: 10px;
    font-size: 11.5px; font-weight: 600; font-variant-numeric: tabular-nums;
  }

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

  .leaderboards { margin-bottom: 28px; }
  .section-h {
    margin: 0 0 6px 0; font-size: 18px;
    color: #e8e8e8; letter-spacing: -0.005em;
  }
  .section-sub {
    color: #aaa; font-size: 13px; margin: 0 0 14px 0;
    line-height: 1.55; max-width: 920px;
  }
  .lb-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }
  .lb-card {
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 6px; padding: 12px 14px;
  }
  .lb-card.featured { border-color: #3a2c1d; }
  .lb-head { border-bottom: 1px solid #232323; margin-bottom: 8px; padding-bottom: 6px; }
  .lb-head h3 { margin: 0; font-size: 14px; color: #d4d4d4; }
  .lb-head h3.memory { color: #f0c894; }
  .lb-sub { color: #888; font-size: 11px; }
  .lb-empty {
    color: #777; font-size: 12px; font-style: italic; margin: 4px 0 0;
  }
  .lb-list {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 4px;
  }
  .lb-list li {
    display: grid; grid-template-columns: 22px 1fr auto auto;
    align-items: center; gap: 6px;
    font-size: 12.5px; padding: 2px 0;
  }
  .lb-rank {
    color: #888; font-size: 11.5px;
    font-variant-numeric: tabular-nums;
    text-align: right; padding-right: 4px;
  }
  .lb-name {
    color: #e8e8e8; text-decoration: none;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .lb-name:hover { color: #f0c894; }
  .lb-score {
    color: #f4e2cb; font-variant-numeric: tabular-nums;
    font-weight: 600; font-size: 12px;
    display: inline-flex; align-items: center; gap: 4px;
  }
  .lb-score.from-claims { color: #cdb89c; }
  .lb-score .dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: #5e8aa3; display: inline-block;
  }

  .split-section { margin-bottom: 28px; }
  .stacked-bar {
    display: flex; height: 32px; border-radius: 6px; overflow: hidden;
    background: #181818; border: 1px solid #2a2a2a;
    margin-bottom: 14px;
  }
  .seg {
    display: flex; align-items: center; justify-content: center;
    color: #15110b; font-size: 12px; font-weight: 600;
    white-space: nowrap; transition: filter 120ms;
  }
  .seg:hover { filter: brightness(1.1); }
  .seg-mem { background: #c98a4e; }
  .seg-both { background: #9a7d56; }
  .seg-dom { background: #5e8aa3; color: #0b1418; }
  .seg span { padding: 0 8px; }

  .bucket-grid {
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;
  }
  .bucket {
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 6px; padding: 12px 14px;
  }
  .bucket[data-cat='memory-only'] { border-top: 2px solid #c98a4e; }
  .bucket[data-cat='both'] { border-top: 2px solid #9a7d56; }
  .bucket[data-cat='domain-only'] { border-top: 2px solid #5e8aa3; }
  .bucket header {
    display: flex; align-items: baseline; justify-content: space-between;
    margin-bottom: 8px;
  }
  .bucket h4 { margin: 0; font-size: 13px; color: #d4d4d4; }
  .bucket-n {
    color: #f0c894; font-size: 16px; font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .bucket ul {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 3px;
    max-height: 320px; overflow-y: auto;
  }
  .bucket li {
    font-size: 12px; display: flex; align-items: center; gap: 6px;
  }
  .bucket li a {
    color: #d4d4d4; text-decoration: none; flex: 1;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .bucket li a:hover { color: #f0c894; }
  .bucket li.more { color: #777; font-style: italic; font-size: 11px; }

  .insights {
    display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
    margin-bottom: 24px;
  }
  .insights .card {
    background: #181818; border: 1px solid #2a2a2a;
    border-radius: 6px; padding: 14px 16px;
  }
  .card h2 { margin: 0 0 6px 0; font-size: 15px; color: #e8e8e8; }
  .card .desc {
    margin: 0 0 12px 0; color: #888;
    font-size: 12.5px; line-height: 1.5;
  }
  .ranked {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 8px;
  }
  .ranked li {
    display: grid; grid-template-columns: 22px 1fr auto;
    align-items: start; gap: 8px;
    padding-bottom: 6px; border-bottom: 1px solid #232323;
  }
  .ranked li:last-child { border-bottom: none; }
  .ranked .rank {
    color: #888; font-size: 12px;
    font-variant-numeric: tabular-nums; padding-top: 2px;
  }
  .ranked a {
    color: #e8e8e8; text-decoration: none;
    font-size: 13px; display: block; margin-bottom: 3px;
  }
  .ranked a:hover { color: #f0c894; }
  .badges {
    display: flex; flex-wrap: wrap; gap: 4px; grid-column: 2;
  }
  .badge {
    display: inline-block; background: #1f2a33; color: #9fc5e0;
    padding: 1px 6px; border-radius: 3px; font-size: 10.5px;
  }
  .badge.mem { background: #3a2c1d; color: #f0c894; }

  .so-what {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 10px;
  }
  .so-what li {
    color: #c9c9c9; font-size: 12.5px; line-height: 1.55;
    padding-left: 12px; border-left: 2px solid #2a2a2a;
  }
  .so-what li strong { color: #f0c894; font-weight: 600; }

  .bench-footer {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 24px; padding-top: 16px;
    border-top: 1px solid #2a2a2a;
    color: #aaa; font-size: 13px;
  }
  .bench-footer a { color: #aaa; text-decoration: none; }
  .bench-footer a:hover { color: #e8e8e8; }
  .muted { color: #777; font-size: 12.5px; }
  .empty {
    color: #888; font-style: italic;
    padding: 24px; text-align: center;
  }

  @media (max-width: 1100px) {
    .coverage-tiers { grid-template-columns: 1fr; }
    .bucket-grid { grid-template-columns: 1fr; }
    .insights { grid-template-columns: 1fr; }
  }
</style>
