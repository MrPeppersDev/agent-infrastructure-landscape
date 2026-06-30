<script lang="ts">
  // /recommend/by-constraints — constraint-matching recommender (Phase 2 / Gate 4, #98).
  //
  // Two input modes (free-text textarea OR a structured form). Both run
  // through the shared deterministic parser in $lib/analyses/recommender,
  // so the ranked output is byte-identical to the MCP `recommend_for_project`
  // tool and the `landscape recommend for` CLI subcommand.

  import {
    recommendForProject,
    type RecommendForProjectResult,
    type RecommendCategory,
    type StructuredForm
  } from '$lib/analyses/recommender';
  import type { LandscapeRecord, CellProvenance, ColumnSlug } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[] } } = $props();

  // ---------------------------------------------------------------------------
  // User-driven state
  // ---------------------------------------------------------------------------
  let mode = $state<'free-text' | 'structured'>('free-text');
  let description = $state(
    'long-running multi-agent system that needs offline capability'
  );

  let projectShape = $state<StructuredForm['project_shape'] | ''>('');
  let scale = $state<StructuredForm['scale'] | ''>('');
  let latencyMs = $state<number | ''>('');
  let persistence = $state<StructuredForm['persistence'] | ''>('');
  let deployment = $state<StructuredForm['deployment'] | ''>('');
  let costCeiling = $state<number | ''>('');
  let k = $state(5);

  // ---------------------------------------------------------------------------
  // Adapter call
  // ---------------------------------------------------------------------------
  const result = $derived.by<RecommendForProjectResult>(() => {
    if (mode === 'structured') {
      const structured: StructuredForm = {};
      if (projectShape) structured.project_shape = projectShape;
      if (scale) structured.scale = scale;
      if (latencyMs !== '' && Number.isFinite(latencyMs)) {
        structured.latency_budget_ms = Number(latencyMs);
      }
      if (persistence) structured.persistence = persistence;
      if (deployment) structured.deployment = deployment;
      if (costCeiling !== '' && Number.isFinite(costCeiling)) {
        structured.cost_ceiling_usd_per_mtok = Number(costCeiling);
      }
      return recommendForProject(data.records, { structured, max_results: k });
    }
    return recommendForProject(data.records, {
      description,
      max_results: k
    });
  });

  const categories: RecommendCategory[] = ['memory', 'harness', 'model'];
  const categoryLabel: Record<RecommendCategory, string> = {
    memory: 'Memory',
    harness: 'Harness',
    model: 'Model'
  };

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
</script>

<svelte:head>
  <title>Recommend / By constraints · Memory Landscape</title>
</svelte:head>

<section class="mode-tabs" role="tablist" aria-label="Input mode">
  <button
    type="button"
    role="tab"
    aria-selected={mode === 'free-text'}
    class:active={mode === 'free-text'}
    onclick={() => (mode = 'free-text')}>
    Free text
  </button>
  <button
    type="button"
    role="tab"
    aria-selected={mode === 'structured'}
    class:active={mode === 'structured'}
    onclick={() => (mode = 'structured')}>
    Structured form
  </button>
</section>

{#if mode === 'free-text'}
  <section class="input-block">
    <label for="desc">Project description</label>
    <textarea
      id="desc"
      rows="3"
      bind:value={description}
      placeholder="Describe the project in your own words. Keywords matched against the controlled vocabulary."
    ></textarea>
    <p class="hint">
      Deterministic keyword/synonym matching — no LLM, so the same description
      always parses to the same constraints (Phase 2 §4).
    </p>
  </section>
{:else}
  <section class="input-block structured">
    <div class="field">
      <label for="shape">Project shape</label>
      <select id="shape" bind:value={projectShape}>
        <option value="">— any —</option>
        <option value="single-agent">single-agent</option>
        <option value="multi-agent">multi-agent</option>
        <option value="chat">chat</option>
        <option value="pipeline">pipeline</option>
      </select>
    </div>
    <div class="field">
      <label for="scale">Scale</label>
      <select id="scale" bind:value={scale}>
        <option value="">— any —</option>
        <option value="prototype">prototype</option>
        <option value="production">production</option>
        <option value="large-scale">large-scale</option>
      </select>
    </div>
    <div class="field">
      <label for="lat">Latency budget (ms)</label>
      <input id="lat" type="number" min="0" bind:value={latencyMs} placeholder="any" />
    </div>
    <div class="field">
      <label for="pers">Persistence</label>
      <select id="pers" bind:value={persistence}>
        <option value="">— any —</option>
        <option value="none">none</option>
        <option value="session">session</option>
        <option value="long-term">long-term</option>
      </select>
    </div>
    <div class="field">
      <label for="dep">Deployment</label>
      <select id="dep" bind:value={deployment}>
        <option value="">— any —</option>
        <option value="cloud">cloud</option>
        <option value="self-hosted">self-hosted</option>
        <option value="offline">offline</option>
      </select>
    </div>
    <div class="field">
      <label for="cost">Cost ceiling ($/Mtok)</label>
      <input id="cost" type="number" min="0" step="0.01" bind:value={costCeiling} placeholder="any" />
    </div>
  </section>
{/if}

<section class="k-control">
  <div class="field">
    <label for="k">Max results per category</label>
    <input id="k" type="number" min="1" max="25" bind:value={k} />
  </div>
</section>

<section class="parsed" aria-label="How the input was interpreted">
  <h2>Parsed as</h2>
  <dl>
    {#if result.parsed_constraints.use_case_tags && result.parsed_constraints.use_case_tags.length > 0}
      <dt>use-case-tags</dt>
      <dd>{result.parsed_constraints.use_case_tags.join(', ')}</dd>
    {/if}
    {#if result.parsed_constraints.cost_max_input_usd_per_mtok != null}
      <dt>cost ceiling</dt>
      <dd>$ {result.parsed_constraints.cost_max_input_usd_per_mtok} / Mtok input</dd>
    {/if}
    {#if result.parsed_constraints.capability_band_min}
      <dt>capability ≥</dt>
      <dd>{result.parsed_constraints.capability_band_min}</dd>
    {/if}
    {#if !result.parsed_constraints.use_case_tags && result.parsed_constraints.cost_max_input_usd_per_mtok == null && !result.parsed_constraints.capability_band_min}
      <dt>(empty)</dt>
      <dd class="muted">no constraints matched — falling back to all records</dd>
    {/if}
  </dl>

  {#if mode === 'free-text'}
    <div class="terms">
      <div>
        <span class="terms-label">matched:</span>
        {#if result.matched_terms.length > 0}
          {#each result.matched_terms as t, i}<span class="chip">{t}</span>{#if i < result.matched_terms.length - 1}<span class="sep"></span>{/if}{/each}
        {:else}
          <span class="muted">none</span>
        {/if}
      </div>
      <div>
        <span class="terms-label">unmatched:</span>
        {#if result.unmatched_terms.length > 0}
          {#each result.unmatched_terms as t, i}<span class="chip dropped">{t}</span>{#if i < result.unmatched_terms.length - 1}<span class="sep"></span>{/if}{/each}
        {:else}
          <span class="muted">none</span>
        {/if}
      </div>
    </div>
  {/if}
</section>

<section class="results">
  {#each categories as cat (cat)}
    {@const list = result.candidates[cat]}
    <article class="cat-block">
      <h2>
        {categoryLabel[cat]}
        <span class="muted">— {list.length} candidate{list.length === 1 ? '' : 's'}</span>
      </h2>
      {#if list.length === 0}
        <p class="muted">No candidates in this category for the parsed constraints.</p>
      {:else}
        <ul class="cards">
          {#each list as cand (cand.record.id)}
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
      {/if}
    </article>
  {/each}
</section>

<style>
  .mode-tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 14px;
  }
  .mode-tabs button {
    background: #181818;
    color: #aaa;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 0.92rem;
    cursor: pointer;
  }
  .mode-tabs button:hover {
    color: #e8e8e8;
    background: #202020;
  }
  .mode-tabs button.active {
    color: #e8e8e8;
    background: #242424;
    border-color: #3a3a3a;
  }

  .input-block {
    max-width: 1100px;
    margin: 0 0 16px;
  }
  .input-block label {
    display: block;
    font-size: 0.8rem;
    color: #aaa;
    margin-bottom: 4px;
    letter-spacing: 0.01em;
  }
  .input-block textarea {
    width: 100%;
    background: #181818;
    color: #e8e8e8;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 0.92rem;
    font-family: inherit;
    resize: vertical;
    box-sizing: border-box;
  }
  .input-block .hint {
    margin: 6px 0 0;
    font-size: 0.78rem;
    color: #777;
  }
  .input-block.structured {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .field label {
    font-size: 0.8rem;
    color: #aaa;
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

  .k-control {
    max-width: 1100px;
    margin: 0 0 20px;
    display: grid;
    grid-template-columns: minmax(200px, 240px);
  }

  .parsed {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 24px;
    max-width: 1100px;
  }
  .parsed h2 {
    margin: 0 0 8px;
    font-size: 0.95rem;
    color: #cfcfcf;
    font-weight: 600;
  }
  .parsed dl {
    margin: 0 0 8px;
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 4px 14px;
    font-size: 0.88rem;
  }
  .parsed dt {
    color: #888;
  }
  .parsed dd {
    margin: 0;
    color: #cfcfcf;
  }
  .terms {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 0.82rem;
  }
  .terms-label {
    color: #888;
    margin-right: 6px;
  }
  .chip {
    display: inline-block;
    background: #1f2a1f;
    color: #8fc488;
    border: 1px solid #2d402d;
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 0.78rem;
  }
  .chip.dropped {
    background: #2a2620;
    color: #c8a06a;
    border-color: #3d3424;
  }
  .sep {
    display: inline-block;
    width: 4px;
  }
  .muted {
    color: #777;
    font-weight: 400;
    font-size: 0.9rem;
  }

  .results {
    max-width: 1100px;
  }
  .cat-block {
    margin: 0 0 28px;
  }
  .cat-block h2 {
    margin: 0 0 12px;
    color: #e8e8e8;
    font-size: 1.1rem;
    font-weight: 600;
  }
  .cards {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 14px;
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
