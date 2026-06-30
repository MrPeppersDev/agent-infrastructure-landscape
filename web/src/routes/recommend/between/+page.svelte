<script lang="ts">
  // /recommend/between — positioning recommender (Phase 2 / Gate 3, #97).
  //
  // Two anchor pickers + optional use-case filter. Calls the shared
  // `betweenModels` adapter from $lib/analyses/recommender so the ranked
  // output is byte-identical to the MCP `between_models` tool and the
  // `landscape recommend between` CLI subcommand. The scatter plot draws
  // every record with both cost + capability cells; anchors and
  // candidates are highlighted on top of that backdrop.

  import {
    betweenModels,
    type Candidate
  } from '$lib/analyses/recommender';
  import type { LandscapeRecord, CellProvenance, ColumnSlug } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  // ---------------------------------------------------------------------------
  // Controlled vocabulary (matches PHASE_2_SPEC.html §4.2)
  // ---------------------------------------------------------------------------
  const USE_CASE_TAGS = [
    'scoped-agentic',
    'long-running-session',
    'multi-agent-coordination',
    'memory-augmented-chat',
    'code-generation-focused',
    'analytical-summarization',
    'latency-sensitive',
    'offline-capable'
  ] as const;
  type UseCaseTag = (typeof USE_CASE_TAGS)[number];

  // ---------------------------------------------------------------------------
  // Pickable anchor pool — only records with both cost + capability cells
  // ---------------------------------------------------------------------------
  function readNumber(r: LandscapeRecord, slug: string): number | null {
    const cells = r.cells as Record<string, { value?: string } | undefined>;
    const v = cells[slug]?.value;
    if (!v) return null;
    const n = Number(v);
    return isFinite(n) ? n : null;
  }

  const anchorPool = $derived(
    data.records
      .filter(
        (r) =>
          readNumber(r, 'cost-input-usd-per-mtok') != null &&
          readNumber(r, 'capability-composite-score') != null
      )
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name))
  );

  // Default to the cheapest and priciest anchors so the user can see a
  // result on first render without picking.
  const defaultLow = $derived(
    anchorPool
      .slice()
      .sort(
        (a, b) =>
          (readNumber(a, 'cost-input-usd-per-mtok') ?? 0) -
          (readNumber(b, 'cost-input-usd-per-mtok') ?? 0)
      )[0]?.id ?? ''
  );
  const defaultHigh = $derived(
    anchorPool
      .slice()
      .sort(
        (a, b) =>
          (readNumber(b, 'cost-input-usd-per-mtok') ?? 0) -
          (readNumber(a, 'cost-input-usd-per-mtok') ?? 0)
      )[0]?.id ?? ''
  );

  // ---------------------------------------------------------------------------
  // User-driven state
  // ---------------------------------------------------------------------------
  let lowId = $state('');
  let highId = $state('');
  let useCase = $state<UseCaseTag | ''>('');
  let k = $state(5);

  // Hydrate defaults once anchorPool is computed.
  $effect(() => {
    if (!lowId && defaultLow) lowId = defaultLow;
    if (!highId && defaultHigh) highId = defaultHigh;
  });

  // ---------------------------------------------------------------------------
  // Ranked candidates — derived from inputs
  // ---------------------------------------------------------------------------
  const candidates = $derived.by<Candidate[]>(() => {
    if (!lowId || !highId || lowId === highId) return [];
    return betweenModels(data.records, {
      anchor_low_id: lowId,
      anchor_high_id: highId,
      use_case: useCase || undefined,
      k
    });
  });

  // ---------------------------------------------------------------------------
  // Helpers for cell rendering with provenance badges (§3.4)
  // ---------------------------------------------------------------------------
  const PHASE_2_DISPLAY_SLUGS: ColumnSlug[] = [
    'cost-input-usd-per-mtok',
    'cost-tier',
    'capability-composite-score',
    'capability-band',
    'use-case-tags'
  ];

  const PHASE_2_LABEL: Record<string, string> = {
    'cost-input-usd-per-mtok': '$/Mtok in',
    'cost-tier': 'cost tier',
    'capability-composite-score': 'cap score',
    'capability-band': 'cap band',
    'use-case-tags': 'use-case tags'
  };

  function readCell(r: LandscapeRecord, slug: string): string | null {
    const cells = r.cells as Record<string, { value?: string } | undefined>;
    const v = cells[slug]?.value;
    if (!v) return null;
    if (/^\s*(not\s+applicable|n\/a)\b/i.test(v)) return null;
    return v;
  }

  function provenance(r: LandscapeRecord, slug: string): CellProvenance | null {
    return r._provenance?.[slug] ?? null;
  }

  function isLlmUnverified(r: LandscapeRecord, slug: string): boolean {
    const p = provenance(r, slug);
    return !!p && p.source === 'llm' && p.verified === false;
  }

  // ---------------------------------------------------------------------------
  // Scatter plot geometry
  // ---------------------------------------------------------------------------
  const W = 720;
  const H = 360;
  const PAD = { top: 24, right: 24, bottom: 48, left: 56 };

  const plotRecords = $derived(
    data.records
      .map((r) => ({
        r,
        x: readNumber(r, 'cost-input-usd-per-mtok'),
        y: readNumber(r, 'capability-composite-score')
      }))
      .filter((p): p is { r: LandscapeRecord; x: number; y: number } =>
        p.x != null && p.y != null && p.x > 0
      )
  );

  // Log-scale on cost — span is two orders of magnitude in real data.
  const xDomain = $derived.by(() => {
    if (plotRecords.length === 0) return { lo: 0.01, hi: 100 };
    const xs = plotRecords.map((p) => p.x);
    return { lo: Math.min(...xs), hi: Math.max(...xs) };
  });
  const yDomain = $derived.by(() => {
    if (plotRecords.length === 0) return { lo: 0, hi: 100 };
    const ys = plotRecords.map((p) => p.y);
    return { lo: Math.min(...ys), hi: Math.max(...ys) };
  });

  function xScale(x: number): number {
    const lo = Math.log10(Math.max(xDomain.lo, 0.001));
    const hi = Math.log10(Math.max(xDomain.hi, lo + 0.1));
    const t = (Math.log10(Math.max(x, 0.001)) - lo) / (hi - lo);
    return PAD.left + t * (W - PAD.left - PAD.right);
  }
  function yScale(y: number): number {
    const t = (y - yDomain.lo) / Math.max(1, yDomain.hi - yDomain.lo);
    return H - PAD.bottom - t * (H - PAD.top - PAD.bottom);
  }

  const candidateIds = $derived(new Set(candidates.map((c) => c.record.id)));
</script>

<svelte:head>
  <title>Recommend / Between · Memory Landscape</title>
</svelte:head>

<section class="picker">
  <div class="field">
    <label for="low">Low anchor</label>
    <select id="low" bind:value={lowId}>
      <option value="" disabled>— pick a record —</option>
      {#each anchorPool as r}
        <option value={r.id}>{r.name}</option>
      {/each}
    </select>
  </div>

  <div class="field">
    <label for="high">High anchor</label>
    <select id="high" bind:value={highId}>
      <option value="" disabled>— pick a record —</option>
      {#each anchorPool as r}
        <option value={r.id}>{r.name}</option>
      {/each}
    </select>
  </div>

  <div class="field">
    <label for="use">Use case (optional)</label>
    <select id="use" bind:value={useCase}>
      <option value="">— none —</option>
      {#each USE_CASE_TAGS as t}
        <option value={t}>{t}</option>
      {/each}
    </select>
  </div>

  <div class="field">
    <label for="k">Max results</label>
    <input id="k" type="number" min="1" max="25" bind:value={k} />
  </div>
</section>

<section class="plot-wrap" aria-label="Cost vs capability scatter">
  <svg viewBox="0 0 {W} {H}" role="img" aria-label="Scatter: cost ($/Mtok input, log scale) vs capability composite score">
    <!-- backdrop -->
    {#each plotRecords as p}
      <circle
        cx={xScale(p.x)}
        cy={yScale(p.y)}
        r={candidateIds.has(p.r.id) ? 5 : 2.5}
        fill={p.r.id === lowId
          ? '#5fa9d4'
          : p.r.id === highId
            ? '#d4845f'
            : candidateIds.has(p.r.id)
              ? '#7fbf78'
              : '#3a3a3a'}
        stroke={p.r.id === lowId || p.r.id === highId
          ? '#fff'
          : 'none'}
        stroke-width="1" />
    {/each}

    <!-- candidate labels -->
    {#each plotRecords as p}
      {#if candidateIds.has(p.r.id) || p.r.id === lowId || p.r.id === highId}
        <text
          x={xScale(p.x) + 8}
          y={yScale(p.y) + 4}
          font-size="10"
          fill={p.r.id === lowId
            ? '#9bc7e0'
            : p.r.id === highId
              ? '#e0a78b'
              : '#a8d4a3'}>{p.r.name}</text>
      {/if}
    {/each}

    <!-- axes -->
    <line
      x1={PAD.left}
      y1={H - PAD.bottom}
      x2={W - PAD.right}
      y2={H - PAD.bottom}
      stroke="#666"
      stroke-width="1" />
    <line
      x1={PAD.left}
      y1={PAD.top}
      x2={PAD.left}
      y2={H - PAD.bottom}
      stroke="#666"
      stroke-width="1" />

    <text x={W / 2} y={H - 12} text-anchor="middle" fill="#aaa" font-size="11">
      cost-input ($/Mtok, log)
    </text>
    <text
      x={-H / 2}
      y={16}
      transform="rotate(-90)"
      text-anchor="middle"
      fill="#aaa"
      font-size="11">
      capability-composite-score
    </text>
  </svg>
</section>

<section class="results">
  <h2>
    {candidates.length} candidate{candidates.length === 1 ? '' : 's'}
    {#if !lowId || !highId}
      <span class="muted">— pick both anchors</span>
    {:else if lowId === highId}
      <span class="muted">— anchors must differ</span>
    {/if}
  </h2>

  {#if candidates.length === 0 && lowId && highId && lowId !== highId}
    <p class="muted">
      No candidates in the positioning band. The anchors may share the same
      cost or capability, or their cells may not parse as numeric.
    </p>
  {/if}

  <ul class="cards">
    {#each candidates as cand (cand.record.id)}
      <li class="card">
        <header>
          <h3>{cand.record.name}</h3>
          <span class="score">score {cand.score.toFixed(3)}</span>
        </header>
        <p class="id">{cand.record.id}</p>

        <dl class="cells">
          {#each PHASE_2_DISPLAY_SLUGS as slug}
            {@const v = readCell(cand.record, slug)}
            {#if v}
              <dt>{PHASE_2_LABEL[slug]}</dt>
              <dd>
                {v}
                {#if isLlmUnverified(cand.record, slug)}
                  <span
                    class="badge llm"
                    title="Excluded from ranking score. Verify before citing.">
                    LLM, unverified
                  </span>
                {/if}
              </dd>
            {/if}
          {/each}
        </dl>

        {#if cand.rationale.length > 0}
          <ul class="rationale">
            {#each cand.rationale as r}
              <li>{r}</li>
            {/each}
          </ul>
        {/if}

        {#if cand.caveats.length > 0}
          <ul class="caveats">
            {#each cand.caveats as cv}
              <li>{cv}</li>
            {/each}
          </ul>
        {/if}
      </li>
    {/each}
  </ul>
</section>

<style>
  .picker {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    max-width: 1100px;
    margin: 0 0 20px;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field label {
    font-size: 0.8rem;
    color: #aaa;
    letter-spacing: 0.01em;
  }
  .field select,
  .field input {
    background: #181818;
    color: #e8e8e8;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 0.92rem;
  }

  .plot-wrap {
    max-width: 1100px;
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 8px;
    margin-bottom: 24px;
  }
  .plot-wrap svg {
    display: block;
    width: 100%;
    height: auto;
  }

  .results h2 {
    margin: 0 0 12px;
    color: #e8e8e8;
    font-size: 1.15rem;
    font-weight: 600;
  }
  .muted {
    color: #888;
    font-weight: 400;
    font-size: 0.92rem;
  }
  .cards {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 14px;
    max-width: 1100px;
  }
  .card {
    background: #181818;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 14px 16px;
  }
  .card header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
  }
  .card h3 {
    margin: 0 0 4px;
    font-size: 1rem;
    color: #e8e8e8;
  }
  .score {
    color: #aaa;
    font-size: 0.82rem;
    white-space: nowrap;
  }
  .id {
    margin: 0 0 10px;
    color: #777;
    font-size: 0.78rem;
    word-break: break-all;
  }
  dl.cells {
    margin: 0 0 10px;
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 4px 12px;
    font-size: 0.85rem;
  }
  dl.cells dt {
    color: #888;
  }
  dl.cells dd {
    margin: 0;
    color: #cfcfcf;
  }
  .badge {
    display: inline-block;
    margin-left: 6px;
    padding: 1px 6px;
    font-size: 0.7rem;
    border-radius: 4px;
    vertical-align: 1px;
  }
  .badge.llm {
    background: #3a2a18;
    color: #e8a868;
    border: 1px solid #5a3c20;
  }
  ul.rationale,
  ul.caveats {
    margin: 6px 0 0;
    padding-left: 18px;
    font-size: 0.82rem;
    line-height: 1.45;
  }
  ul.rationale li {
    color: #8fc488;
  }
  ul.caveats li {
    color: #d4a55f;
  }
</style>
