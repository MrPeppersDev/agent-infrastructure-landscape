<script lang="ts">
  // Benchmark coverage matrix (issue #24). For every memory / agent
  // benchmark that any system has reported a score on, show which systems
  // have a score and what that score is. Reveals which benchmarks have
  // critical mass — and which memory papers chose domain-specific agent
  // benchmarks (GAIA, ALFWorld) over memory-specific ones (LongMemEval,
  // LoCoMo).
  //
  // All extraction is client-side from the bundled landscape.json — see
  // $lib/analyses/benchmarks.ts for the canonicalisation rules and the
  // perf-over-claims priority. The page is just rendering.

  import {
    extractScores,
    buildMatrix,
    benchmarkCoverage,
    systemCoverage,
    adoptionSplit,
    isMemoryBenchmark
  } from '$lib/analyses/benchmarks';
  import { base } from '$app/paths';
  import type { LandscapeRecord } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  const scores = $derived(extractScores(data.records));
  const matrix = $derived(buildMatrix(scores, 14));
  const coverage = $derived(benchmarkCoverage(scores));
  const sysCoverage = $derived(systemCoverage(scores));
  const split = $derived(adoptionSplit(scores));

  // Heat-color the score within a benchmark column. Parse the leading
  // numeric (`74.0%` → 74) and rank within column to map to a hue. Delta
  // scores like "+48%" are also parsed but are visually distinguished
  // (italic) because they're not comparable to absolute scores.
  function parseScoreNum(s: string): { n: number | null; isDelta: boolean } {
    if (!s) return { n: null, isDelta: false };
    const m = s.match(/^([+\-~])?(\d[\d.,]*)/);
    if (!m) return { n: null, isDelta: false };
    const n = parseFloat(m[2].replace(/,/g, ''));
    if (Number.isNaN(n)) return { n: null, isDelta: false };
    return { n, isDelta: m[1] === '+' || m[1] === '-' };
  }

  // Per-benchmark min/max of *absolute* (non-delta) scores. Used to map
  // each cell to a 0–1 strength within its column.
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
        m.set(b.name, {
          min: Math.min(...nums),
          max: Math.max(...nums),
          count: nums.length
        });
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
    // Cold → hot via two-stop interpolation through orange.
    // Low: muted slate; High: warm amber, the site's accent hue.
    const hue = 30; // warm amber
    const sat = 30 + Math.round(t * 50);
    const light = 18 + Math.round(t * 10);
    return `background: hsl(${hue} ${sat}% ${light}% / 0.85);`;
  }

  function tableHref(rid: string, name: string): string {
    return `${base}/?q=${encodeURIComponent(name)}`;
  }

  const totalSystemsWithScore = $derived(sysCoverage.length);
  const totalBenchmarks = $derived(coverage.length);
  const topBenchmark = $derived(coverage[0]?.benchmark ?? '—');
  const topSystems = $derived(sysCoverage.slice(0, 10));
</script>

<svelte:head>
  <title>Benchmark coverage matrix — Memory Landscape</title>
</svelte:head>

<main class="bench-page">
  <header class="bench-header">
    <p class="crumb"><a href="{base}/analyses">← Analyses</a></p>
    <h1>Benchmark coverage matrix</h1>
    <p class="bench-sub">
      Which memory and agent benchmarks each system has reported scores
      on. Rows are systems with at least one score in either the
      <code>perf</code> or <code>claims</code> cell. Columns are the
      {matrix.benchmarks.length} most-reported benchmarks across the
      catalog. Cell shading runs cold-to-warm with the absolute score
      within each column; <em>italic</em> deltas (<code>+18.7pp</code>,
      <code>-15.3%</code>) are shown unshaded because they aren't directly
      comparable. Parsing rules live in
      <code>web/src/lib/analyses/benchmarks.ts</code>.
    </p>
    <p class="bench-stats">
      <strong>{totalSystemsWithScore}</strong> systems with at least one
      score · <strong>{totalBenchmarks}</strong> distinct benchmarks
      tracked · most-reported: <strong>{topBenchmark}</strong>
      ({coverage[0]?.count ?? 0} systems)
    </p>
  </header>

  {#if matrix.systems.length === 0}
    <p class="empty">No benchmark scores parsed from the catalog.</p>
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
                title="{b.name} — reported by {b.count} systems"
              >
                <span class="bench-name">{b.name}</span>
                <span class="bench-count">{b.count}</span>
              </th>
            {/each}
            <th class="total-col" title="Number of in-matrix benchmarks this system reports">N</th>
          </tr>
        </thead>
        <tbody>
          {#each matrix.systems as s (s.id)}
            <tr>
              <td class="sys-col">
                <a href={tableHref(s.id, s.name)}>{s.name}</a>
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
                    title={`${b.name}: ${cell.score || '(presence only)'} — source: ${cell.source}`}
                  >
                    {cell.score || '✓'}
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

    <section class="insights">
      <article class="card">
        <h2>Per-benchmark coverage</h2>
        <p class="desc">How many distinct systems have reported a score on each benchmark (full population, not just the top-{matrix.benchmarks.length} shown above).</p>
        <ul class="bars">
          {#each coverage as row (row.benchmark)}
            <li>
              <span class="bar-label" class:memory={isMemoryBenchmark(row.benchmark)}>
                {row.benchmark}
                {#if isMemoryBenchmark(row.benchmark)}<span class="tag mem">memory</span>{:else}<span class="tag dom">domain</span>{/if}
              </span>
              <span class="bar-track">
                <span
                  class="bar-fill"
                  class:memory={isMemoryBenchmark(row.benchmark)}
                  style="width: {(row.count / (coverage[0]?.count || 1)) * 100}%;"
                ></span>
              </span>
              <span class="bar-value">{row.count}</span>
            </li>
          {/each}
        </ul>
      </article>

      <article class="card">
        <h2>Most-benchmarked systems</h2>
        <p class="desc">Top-10 systems by distinct benchmarks reported (all 25 benchmarks, not just the top-{matrix.benchmarks.length}).</p>
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

      <article class="card adoption">
        <h2>Memory-specific vs domain-specific adoption</h2>
        <p class="desc">
          Memory-specific benchmarks (LongMemEval, LoCoMo, BABILong,
          ConvoMem, RULER, MemoryAgentBench, ImplicitMemBench, PersonaBench,
          NIAH) versus generic agent / NLP benchmarks (GAIA, ALFWorld,
          SWE-bench, OSWorld, WebArena, etc.). A system counts in a
          category if it has reported at least one benchmark from it.
        </p>
        <div class="split-grid">
          <div class="split">
            <div class="big">{split.memorySpecificSystems}</div>
            <div class="lbl">systems on a memory-specific benchmark</div>
          </div>
          <div class="split">
            <div class="big">{split.domainSpecificSystems}</div>
            <div class="lbl">systems on a domain-specific benchmark</div>
          </div>
          <div class="split">
            <div class="big">{split.bothSystems}</div>
            <div class="lbl">systems on both</div>
          </div>
        </div>
        <p class="callout">
          Memory-only: {split.memoryOnlySystems} · Domain-only:
          {split.domainOnlySystems} · Both: {split.bothSystems}. The
          memory-specific benchmark family has effectively the same
          population as the agent-benchmark family, but the
          <em>overlap is small</em>: most memory papers pick one camp or
          the other rather than reporting on both. This matches the user's
          prior observation that papers proposing memory systems often
          benchmark on the domain they're optimising (web agents on
          WebArena, coding agents on SWE-bench) rather than on the
          memory-specific axes their architecture would seem to target.
        </p>
      </article>
    </section>
  {/if}

  <footer class="bench-footer">
    <a href="{base}/analyses">← Analyses hub</a>
    <span class="muted">
      Sources: <code>cells.perf</code> (primary), <code>cells.claims</code>
      (fallback). Canonicalisation rules in
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

  .bench-header {
    margin-bottom: 24px;
  }

  .crumb {
    margin: 0 0 8px 0;
    font-size: 13px;
  }
  .crumb a {
    color: #aaa;
    text-decoration: none;
  }
  .crumb a:hover {
    color: #e8e8e8;
  }

  .bench-header h1 {
    font-size: 28px;
    margin: 0 0 10px 0;
    letter-spacing: -0.01em;
  }

  .bench-sub {
    color: #aaa;
    max-width: 880px;
    margin: 0 0 12px 0;
    line-height: 1.55;
    font-size: 14px;
  }

  .bench-stats {
    color: #d4d4d4;
    margin: 0;
    font-size: 14px;
  }
  .bench-stats strong {
    color: #f0c894;
  }

  code {
    font-family: 'SF Mono', 'Menlo', Consolas, monospace;
    font-size: 12.5px;
    background: #1f1f1f;
    padding: 1px 5px;
    border-radius: 3px;
    color: #d4d4d4;
  }

  /* --- matrix --- */

  .matrix-wrap {
    overflow-x: auto;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    background: #181818;
    margin-bottom: 32px;
  }

  .matrix {
    border-collapse: collapse;
    font-size: 12.5px;
    min-width: 100%;
  }

  .matrix thead th {
    position: sticky;
    top: 0;
    background: #1d1d1d;
    border-bottom: 1px solid #333;
    padding: 8px 8px;
    text-align: left;
    font-weight: 600;
    color: #d4d4d4;
    white-space: nowrap;
  }

  .matrix thead th.bench-col {
    text-align: center;
    min-width: 78px;
  }
  .matrix thead th.bench-col.memory {
    color: #f0c894;
  }
  .bench-name {
    display: block;
    font-size: 12px;
  }
  .bench-count {
    display: block;
    font-size: 10.5px;
    color: #888;
    font-weight: 400;
    margin-top: 1px;
  }
  .matrix thead th.bench-col.memory .bench-count {
    color: #c9a26e;
  }

  .matrix thead th.sys-col {
    position: sticky;
    left: 0;
    z-index: 2;
    background: #1d1d1d;
    min-width: 220px;
  }
  .matrix thead th.total-col {
    text-align: center;
    min-width: 40px;
  }

  .matrix tbody td {
    border-bottom: 1px solid #232323;
    padding: 5px 8px;
    vertical-align: middle;
  }

  .matrix tbody td.sys-col {
    position: sticky;
    left: 0;
    background: #181818;
    border-right: 1px solid #2a2a2a;
    font-size: 13px;
    z-index: 1;
  }
  .matrix tbody td.sys-col a {
    color: #e8e8e8;
    text-decoration: none;
  }
  .matrix tbody td.sys-col a:hover {
    color: #f0c894;
  }
  .matrix tbody tr:hover td.sys-col {
    background: #1f1f1f;
  }
  .matrix tbody tr:hover td.cell {
    filter: brightness(1.18);
  }

  .matrix .cell {
    text-align: center;
    font-variant-numeric: tabular-nums;
    color: #f4e2cb;
    min-width: 64px;
    cursor: default;
  }
  .matrix .cell.empty-cell {
    background: transparent;
    color: #333;
  }
  .matrix .cell.delta {
    font-style: italic;
    color: #d4d4d4;
  }
  .matrix .cell.from-claims {
    border-left: 2px solid #5e8aa3;
  }
  .matrix .total-col {
    text-align: center;
  }
  .count-pill {
    display: inline-block;
    background: #2a2a2a;
    color: #f0c894;
    padding: 1px 7px;
    border-radius: 10px;
    font-size: 11.5px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  /* --- insights --- */

  .insights {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 24px;
  }
  .insights .card {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 16px 18px;
  }
  .insights .card.adoption {
    grid-column: 1 / -1;
  }

  .card h2 {
    margin: 0 0 6px 0;
    font-size: 15px;
    color: #e8e8e8;
  }
  .card .desc {
    margin: 0 0 14px 0;
    color: #888;
    font-size: 12.5px;
    line-height: 1.5;
  }

  /* coverage bar list */
  .bars {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 6px;
  }
  .bars li {
    display: grid;
    grid-template-columns: 180px 1fr 36px;
    gap: 10px;
    align-items: center;
    font-size: 12.5px;
  }
  .bar-label {
    color: #d4d4d4;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .bar-label.memory {
    color: #f0c894;
  }
  .tag {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 1px 5px;
    border-radius: 3px;
    margin-left: 4px;
    vertical-align: middle;
  }
  .tag.mem {
    background: #3a2c1d;
    color: #f0c894;
  }
  .tag.dom {
    background: #1f2a33;
    color: #9fc5e0;
  }
  .bar-track {
    background: #1f1f1f;
    height: 12px;
    border-radius: 6px;
    overflow: hidden;
    display: block;
  }
  .bar-fill {
    display: block;
    height: 100%;
    background: #5e8aa3;
    transition: width 200ms ease;
  }
  .bar-fill.memory {
    background: #c98a4e;
  }
  .bar-value {
    text-align: right;
    color: #d4d4d4;
    font-variant-numeric: tabular-nums;
    font-size: 12.5px;
  }

  /* ranked list */
  .ranked {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 8px;
  }
  .ranked li {
    display: grid;
    grid-template-columns: 22px 1fr auto;
    align-items: start;
    gap: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid #232323;
  }
  .ranked li:last-child {
    border-bottom: none;
  }
  .ranked .rank {
    color: #888;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    padding-top: 2px;
  }
  .ranked a {
    color: #e8e8e8;
    text-decoration: none;
    font-size: 13px;
    display: block;
    margin-bottom: 3px;
  }
  .ranked a:hover {
    color: #f0c894;
  }
  .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    grid-column: 2;
  }
  .badge {
    display: inline-block;
    background: #1f2a33;
    color: #9fc5e0;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10.5px;
  }
  .badge.mem {
    background: #3a2c1d;
    color: #f0c894;
  }

  /* adoption split */
  .split-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: 12px 0 16px;
  }
  .split {
    background: #1d1d1d;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 14px 16px;
    text-align: center;
  }
  .split .big {
    font-size: 28px;
    font-weight: 600;
    color: #f0c894;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }
  .split .lbl {
    color: #aaa;
    font-size: 12.5px;
    margin-top: 6px;
    line-height: 1.4;
  }
  .callout {
    color: #d4d4d4;
    font-size: 13px;
    line-height: 1.55;
    margin: 0;
    padding-top: 8px;
    border-top: 1px dashed #2a2a2a;
  }

  /* footer */
  .bench-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid #2a2a2a;
    color: #aaa;
    font-size: 13px;
  }
  .bench-footer a {
    color: #aaa;
    text-decoration: none;
  }
  .bench-footer a:hover {
    color: #e8e8e8;
  }
  .muted {
    color: #777;
    font-size: 12.5px;
  }
  .empty {
    color: #888;
    font-style: italic;
    padding: 24px;
    text-align: center;
  }

  @media (max-width: 900px) {
    .insights {
      grid-template-columns: 1fr;
    }
    .split-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
