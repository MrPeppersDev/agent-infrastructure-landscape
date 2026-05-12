<script lang="ts">
  // Survivorship map (issue #23). Classifies every record into
  // active / stale / abandoned / unknown by freshness signal, with research
  // artefacts (T3+T4+T5) split into their own bucket because "active dev" is
  // not the right frame for a paper.
  //
  // Layout:
  //   1. Top row of counters (active / stale / abandoned / unknown + research)
  //   2. Per-section dot strip: each row is a section, each dot is a record
  //      coloured by survivorship status
  //   3. "Most-influential-but-abandoned" list at the bottom
  //
  // All compute is pure helpers in $lib/analyses/survivorship.

  import { base } from '$app/paths';
  import type { LandscapeRecord, Edge } from '$lib/types';
  import {
    classifyAll,
    countBuckets,
    bySection,
    influentialAbandoned,
    SURVIVORSHIP_ORDER,
    SURVIVORSHIP_LABELS,
    SURVIVORSHIP_COLOURS,
    type Survivorship
  } from '$lib/analyses/survivorship';

  let { data }: { data: { records: LandscapeRecord[]; edges: Edge[] } } =
    $props();

  // --- Classification pass ----------------------------------------------
  const classifications = $derived(classifyAll(data.records));
  const counts = $derived(countBuckets(classifications));
  const sections = $derived(bySection(data.records, classifications));

  // --- Inbound edge counts for the influential-abandoned table ---------
  const inboundIntegrations = $derived.by(() => {
    const m = new Map<string, number>();
    for (const e of data.edges) {
      if (e.type === 'integrates-with' || e.type === 'built-on') {
        m.set(e.target, (m.get(e.target) ?? 0) + 1);
      }
    }
    return m;
  });
  const inboundCitations = $derived.by(() => {
    const m = new Map<string, number>();
    for (const e of data.edges) {
      if (e.type === 'cites') {
        m.set(e.target, (m.get(e.target) ?? 0) + 1);
      }
    }
    return m;
  });

  const influential = $derived(
    influentialAbandoned(
      data.records,
      classifications,
      inboundIntegrations,
      inboundCitations
    )
  );

  // Section strip: limit to sections with >=2 rows so we don't render a
  // dozen single-dot rows. Below that the dot strip carries no information.
  const visibleSections = $derived(sections.filter((s) => s.total >= 2));

  // Filter for "show only $status" on the strip view. null = show all.
  let highlight = $state<Survivorship | null>(null);

  function tooltip(rec: LandscapeRecord, statusLabel: string, signal: string): string {
    return `${rec.name} — ${statusLabel}\n${signal}`;
  }

  function pct(n: number, total: number): string {
    if (total === 0) return '0%';
    return `${Math.round((n / total) * 100)}%`;
  }
</script>

<svelte:head>
  <title>Survivorship map · Analyses · Memory Landscape</title>
</svelte:head>

<header class="page-header">
  <p class="breadcrumb">
    <a href="{base}/analyses">Analyses</a> · Survivorship map
  </p>
  <h1>Survivorship / staleness map</h1>
  <p class="lede">
    Every record classified by freshness signal. Active (within last 12mo),
    Stale (12-24mo), Abandoned (>24mo), Unknown (no parseable signal).
    Research artefacts (Tier 3-5 papers and techniques) are surfaced
    separately — "abandonment" is the wrong frame for a published paper.
    Snapshot date: 2026-05-12.
  </p>
</header>

<!-- Top-row counters -->
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

<!-- Per-section dot strip -->
<section class="strips">
  <header class="strips-header">
    <h2>By section</h2>
    <p>
      Each dot is one record, coloured by status. Click a counter above to
      highlight one bucket. Hover any dot for the record + freshness signal.
    </p>
  </header>
  {#each visibleSections as s}
    <article class="strip">
      <header>
        <h3>{s.section}</h3>
        <span class="strip-total">{s.total} rows</span>
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
      <div class="dots">
        {#each s.rows as { record, cls }}
          <a
            class="dot"
            class:dim={highlight !== null && highlight !== cls.status}
            href={record.url ?? `${base}/?search=${encodeURIComponent(record.name)}`}
            style:--c={SURVIVORSHIP_COLOURS[cls.status]}
            title={tooltip(record, SURVIVORSHIP_LABELS[cls.status], cls.signal)}
            target={record.url ? '_blank' : '_self'}
            rel={record.url ? 'noopener noreferrer' : null}
            aria-label="{record.name}: {SURVIVORSHIP_LABELS[cls.status]} — {cls.signal}"
          ></a>
        {/each}
      </div>
    </article>
  {/each}
</section>

<!-- Most-influential-but-abandoned -->
<section class="influential">
  <header>
    <h2>Most-influential-but-abandoned</h2>
    <p>
      Dead-but-still-cited. Ranked by inbound integration links × 3 +
      inbound citations. Includes abandoned products (no freshness signal
      in 24+ months) plus research rows whose code repo has a known last
      commit older than 24 months — research papers stay in their own
      bucket above, but the table here surfaces the ones the rest of the
      catalog still builds on.
    </p>
  </header>
  {#if influential.length === 0}
    <p class="empty">No abandoned product has inbound integrations or citations in the catalog.</p>
  {:else}
    <table>
      <thead>
        <tr>
          <th class="num">#</th>
          <th>Record</th>
          <th>Section</th>
          <th>Bucket</th>
          <th class="num">Inbound integrations</th>
          <th class="num">Inbound citations</th>
          <th class="num">Score</th>
          <th>Last signal</th>
        </tr>
      </thead>
      <tbody>
        {#each influential.slice(0, 25) as row, i}
          <tr>
            <td class="num">{i + 1}</td>
            <td>
              <a
                href="{base}/?search={encodeURIComponent(row.record.name)}"
                title="Open in table"
              >{row.record.name}</a>
              <span class="tier">T{row.record.tier}</span>
            </td>
            <td class="section-cell">
              {row.record.sections.find((s) => s.primary)?.section ??
                row.record.sections[0]?.section ??
                '—'}
            </td>
            <td class="bucket-cell">
              <span
                class="bucket-pill"
                style:--c={row.effective === 'abandoned'
                  ? '#f85149'
                  : '#bc8cff'}
              >{row.effective}</span>
            </td>
            <td class="num">{row.inboundIntegrations}</td>
            <td class="num">{row.inboundCitations}</td>
            <td class="num"><strong>{row.score}</strong></td>
            <td class="signal">{row.cls.signal}</td>
          </tr>
        {/each}
      </tbody>
    </table>
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

  /* Counters --------------------------------------------------- */
  .counters {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 12px;
    max-width: 1100px;
    margin: 0 0 36px;
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

  /* Strips ----------------------------------------------------- */
  .strips-header {
    max-width: 760px;
    margin: 0 0 16px;
  }
  .strips-header h2 {
    margin: 0 0 6px;
    font-size: 1.1rem;
    color: #e8e8e8;
  }
  .strips-header p {
    margin: 0;
    color: #888;
    font-size: 0.9rem;
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

  /* Influential table ------------------------------------------ */
  .influential {
    margin: 40px 0 64px;
    max-width: 1100px;
  }
  .influential header {
    max-width: 760px;
    margin-bottom: 12px;
  }
  .influential h2 {
    margin: 0 0 6px;
    font-size: 1.1rem;
    color: #e8e8e8;
  }
  .influential header p {
    margin: 0;
    color: #888;
    font-size: 0.9rem;
    line-height: 1.5;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    background: #141414;
    border: 1px solid #222;
    border-radius: 6px;
    overflow: hidden;
    font-size: 0.88rem;
  }
  th,
  td {
    text-align: left;
    padding: 8px 12px;
    border-bottom: 1px solid #1f1f1f;
    color: #ddd;
    vertical-align: top;
  }
  th {
    background: #181818;
    color: #bbb;
    font-weight: 600;
    font-size: 0.8rem;
    letter-spacing: 0.01em;
  }
  tr:last-child td {
    border-bottom: none;
  }
  td.num,
  th.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  td a {
    color: #e8e8e8;
    text-decoration: none;
  }
  td a:hover {
    color: #d4845f;
  }
  .tier {
    display: inline-block;
    margin-left: 6px;
    padding: 1px 5px;
    border-radius: 3px;
    background: #222;
    color: #888;
    font-size: 0.7rem;
    font-weight: 600;
  }
  .section-cell {
    color: #888;
    font-size: 0.82rem;
  }
  .bucket-cell {
    font-size: 0.78rem;
  }
  .bucket-pill {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    color: var(--c);
    border: 1px solid var(--c);
    background: rgba(0, 0, 0, 0.2);
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-size: 0.72rem;
  }
  .signal {
    color: #888;
    font-size: 0.82rem;
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
  }
</style>
