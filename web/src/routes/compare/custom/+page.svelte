<script lang="ts">
  // /compare/custom — compare ANY two catalog systems, client-side (#134).
  //
  // The pre-computed /compare/[pair] pages only cover competes-with edges
  // + top-in-section pairs. This route lets users pick any two of the
  // catalog's records; state lives in ?a=&b= so comparisons are shareable.
  // Same hydration pattern as /recommend/between: read
  // window.location.search once in a browser-only $effect guarded by a
  // hydrated flag (page.url.searchParams breaks prerendered layouts),
  // write back via history.replaceState.
  import { base } from '$app/paths';
  import CompareTables, {
    primarySection,
    type SlimRecord
  } from '$lib/components/CompareTables.svelte';
  import RecordPicker from '$lib/components/RecordPicker.svelte';
  import { pairToSlug, allPairs } from '$lib/seo/compare';
  import type { LandscapeRecord, Edge } from '$lib/types';

  let { data }: { data: { records: LandscapeRecord[]; edges: Edge[] } } = $props();

  const options = $derived(
    data.records
      .map((r) => ({ id: r.id, name: r.name, section: primarySection(r) }))
      .sort((x, y) => x.name.localeCompare(y.name))
  );

  let aId = $state('');
  let bId = $state('');
  let hydrated = $state(false);

  // Hydrate once from the URL in the browser.
  $effect(() => {
    if (hydrated) return;
    hydrated = true;
    const p = new URLSearchParams(window.location.search);
    const qa = p.get('a') ?? '';
    const qb = p.get('b') ?? '';
    if (data.records.some((r) => r.id === qa)) aId = qa;
    if (data.records.some((r) => r.id === qb)) bId = qb;
  });

  // Push current state back to the URL (replaceState — don't spam history).
  $effect(() => {
    if (!hydrated) return;
    const sp = new URLSearchParams();
    if (aId) sp.set('a', aId);
    if (bId) sp.set('b', bId);
    const qs = sp.toString();
    const current = window.location.search.replace(/^\?/, '');
    if (current !== qs) {
      window.history.replaceState({}, '', qs ? `?${qs}` : window.location.pathname);
    }
  });

  const a = $derived<SlimRecord | null>(data.records.find((r) => r.id === aId) ?? null);
  const b = $derived<SlimRecord | null>(data.records.find((r) => r.id === bId) ?? null);

  function swap() {
    const t = aId;
    aId = bId;
    bId = t;
  }

  // Direct edges between the two — same "How they relate" block as the
  // pre-computed pair pages.
  const between = $derived<Edge[]>(
    a && b
      ? data.edges.filter(
          (e) =>
            (e.source === a.id && e.target === b.id) ||
            (e.source === b.id && e.target === a.id)
        )
      : []
  );

  // If this pair has a pre-computed page, point at it — that's the
  // canonical, indexable version of the comparison.
  const precomputedSlug = $derived.by(() => {
    if (!a || !b) return null;
    const slug = pairToSlug(a.id, b.id);
    return allPairs().some((p) => pairToSlug(p.a, p.b) === slug) ? slug : null;
  });

  const edgeLabel: Record<string, string> = {
    'built-on': 'builds on',
    'runtime-dependency': 'depends on at runtime',
    extends: 'extends',
    forks: 'forks',
    'integrates-with': 'integrates with',
    'competes-with': 'competes with',
    'inspired-by': 'inspired by',
    cites: 'cites',
    'same-team-as': 'same team as',
    succeeds: 'succeeds'
  };
</script>

<svelte:head>
  <title>Compare Any Two Systems · AI Agent Infrastructure Landscape</title>
  <!-- Client-only, query-driven comparisons — thin/duplicative content
       that must not compete with the prerendered /compare/[pair] pages. -->
  <meta name="robots" content="noindex" />
</svelte:head>

<article class="cmp">
  <header>
    <p class="breadcrumbs">
      <a href="{base}/">Catalog</a>
      <span aria-hidden="true">›</span>
      <a href="{base}/compare">Comparisons</a>
      <span aria-hidden="true">›</span>
      <span>Custom</span>
    </p>
    <h1>Compare any two systems</h1>
    <p class="lede">
      Pick any two of the catalog's {data.records.length} systems for a
      side-by-side comparison — cost &amp; capability, architecture, taxonomy,
      license, pricing, and any direct edges between them. Comparisons are
      shareable via the URL.
    </p>
    <div class="controls" aria-label="System pickers">
      <RecordPicker {options} bind:value={aId} label="System A" />
      <RecordPicker {options} bind:value={bId} label="System B" />
      {#if a && b}
        <button type="button" class="control-btn" onclick={swap} title="Reverse which column is which">
          ⇄ Swap
        </button>
      {/if}
    </div>
    {#if a && b && a.id === b.id}
      <p class="hint">Pick two different systems to compare.</p>
    {:else if !a || !b}
      <p class="hint">
        Pick both systems to see the comparison. Looking for a curated
        head-to-head instead? Browse the
        <a href="{base}/compare">pre-computed comparison pages</a>.
      </p>
    {/if}
  </header>

  {#if a && b && a.id !== b.id}
    {#if precomputedSlug}
      <p class="canonical-note">
        This pair has a dedicated page:
        <a href="{base}/compare/{precomputedSlug}">{a.name} vs {b.name} →</a>
      </p>
    {/if}

    {#if between.length}
      <section class="between">
        <h2>How they relate</h2>
        <ul>
          {#each between as e}
            {@const fromA = e.source === a.id}
            <li>
              <strong>{fromA ? a.name : b.name}</strong>
              {edgeLabel[e.type] ?? e.type}
              <strong>{fromA ? b.name : a.name}</strong>
              {#if e.evidence}<span class="ev">— {e.evidence}</span>{/if}
            </li>
          {/each}
        </ul>
      </section>
    {/if}

    <CompareTables left={a} right={b} />

    <footer class="meta">
      <p>
        Rows last verified {a.last_verified_at} / {b.last_verified_at}. Data is
        CC-BY-4.0 — see <a href="{base}/about">how to read this</a>.
      </p>
    </footer>
  {/if}
</article>

<style>
  .cmp {
    max-width: 920px;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    color: #d6d6d6;
    line-height: 1.55;
  }
  .breadcrumbs {
    font-size: 0.85rem;
    color: #888;
    margin: 0 0 0.5rem;
  }
  .breadcrumbs a {
    color: #b0b0b0;
    text-decoration: none;
  }
  .breadcrumbs a:hover {
    text-decoration: underline;
  }
  .breadcrumbs span {
    margin: 0 0.35rem;
  }
  h1 {
    margin: 0 0 0.5rem;
    color: #f0f0f0;
    font-size: 1.7rem;
  }
  .lede {
    color: #c0c0c0;
    margin: 0 0 0.9rem;
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 0.6rem 0.9rem;
    margin: 0 0 0.9rem;
    padding: 0.75rem 0.9rem;
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
  }
  .control-btn {
    background: #202020;
    color: #d6d6d6;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 0.88rem;
    font-family: inherit;
    cursor: pointer;
  }
  .control-btn:hover {
    background: #262626;
    color: #f0f0f0;
  }
  .hint {
    color: #999;
    font-size: 0.9rem;
    margin: 0 0 1.2rem;
  }
  .hint a {
    color: #d4845f;
  }
  .canonical-note {
    font-size: 0.88rem;
    color: #999;
    margin: 0 0 1rem;
    padding: 0.5rem 0.8rem;
    background: #161616;
    border-left: 2px solid #d4845f;
    border-radius: 0 6px 6px 0;
  }
  .canonical-note a {
    color: #d4845f;
    text-decoration: none;
  }
  .canonical-note a:hover {
    text-decoration: underline;
  }
  h2 {
    color: #e8e8e8;
    font-size: 1.15rem;
    margin: 2rem 0 0.6rem;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.3rem;
  }
  .between ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .between li {
    padding: 0.45rem 0;
    border-bottom: 1px solid #1f1f1f;
    color: #ccc;
  }
  .between strong {
    color: #d4845f;
  }
  .between .ev {
    color: #aaa;
  }
  .meta {
    margin-top: 3rem;
    color: #777;
    font-size: 0.85rem;
    border-top: 1px solid #2a2a2a;
    padding-top: 1rem;
  }
  .meta a {
    color: #b0b0b0;
  }
</style>
