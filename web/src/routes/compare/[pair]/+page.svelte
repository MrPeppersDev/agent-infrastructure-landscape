<script lang="ts">
  import { base } from '$app/paths';
  import { goto } from '$app/navigation';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import CompareTables, {
    cellText,
    primarySection,
    type SlimRecord
  } from '$lib/components/CompareTables.svelte';
  import { articleLd, breadcrumbLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';
  import { pairToSlug } from '$lib/seo/compare';
  import type { Edge } from '$lib/types';
  import type { SiblingPair } from './+page';

  let {
    data
  }: {
    data: {
      a: SlimRecord;
      b: SlimRecord;
      between: Edge[];
      siblingsForA: SiblingPair[];
      siblingsForB: SiblingPair[];
    };
  } = $props();

  // Left/right columns are the display axis; the underlying records don't
  // move. `swapped` reverses which record renders on the left so users can
  // compare in either direction without back-navigating.
  let swapped = $state(false);
  const left = $derived(swapped ? data.b : data.a);
  const right = $derived(swapped ? data.a : data.b);
  // Canonical A/B kept for JSON-LD / SEO — those stay stable across swaps.
  const a = data.a;
  const b = data.b;

  // Cross-link to /recommend/between if both sides have cost + capability
  // data — that's when the positioning recommender can actually run.
  const canRecommendBetween = $derived(
    !!cellText(a.cells['cost-input-usd-per-mtok']) &&
      !!cellText(b.cells['cost-input-usd-per-mtok']) &&
      !!cellText(a.cells['capability-composite-score']) &&
      !!cellText(b.cells['capability-composite-score'])
  );

  // Pickers: keep one endpoint, swap the other. Selecting an option
  // navigates to the corresponding pre-computed pair slug.
  let changeAId = $state('');
  let changeBId = $state('');
  function onChangeA() {
    const opt = data.siblingsForB.find((s) => s.id === changeAId);
    if (opt) goto(`${base}/compare/${opt.slug}`);
  }
  function onChangeB() {
    const opt = data.siblingsForA.find((s) => s.id === changeBId);
    if (opt) goto(`${base}/compare/${opt.slug}`);
  }

  const slug = pairToSlug(a.id, b.id);
  const routePath = `/compare/${slug}`;
  const title = `${a.name} vs ${b.name} — Compared on 19 Dimensions`;
  const sameSection = primarySection(a) === primarySection(b);
  const description = sameSection
    ? `${a.name} vs ${b.name}: side-by-side comparison of two ${primarySection(a)?.toLowerCase()} systems — architecture, taxonomy, license, pricing, MCP/A2A support, and direct edges.`
    : `${a.name} (${primarySection(a)?.toLowerCase()}) vs ${b.name} (${primarySection(b)?.toLowerCase()}): cross-category comparison covering architecture, taxonomy, license, pricing, and direct edges.`;

  const ldData = [
    articleLd({
      headline: title,
      description,
      url: absoluteUrl(routePath)
    }),
    breadcrumbLd({
      items: [
        { name: 'Catalog', url: absoluteUrl('/') },
        { name: 'Comparisons', url: absoluteUrl('/compare') },
        { name: `${a.name} vs ${b.name}`, url: absoluteUrl(routePath) }
      ]
    })
  ];

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

<SeoHead {title} {description} path={routePath} ogType="article" />
<JsonLd data={ldData} />

<article class="cmp">
  <header>
    <p class="breadcrumbs">
      <a href="{base}/">Catalog</a>
      <span aria-hidden="true">›</span>
      <a href="{base}/compare">Comparisons</a>
      <span aria-hidden="true">›</span>
      <span>{a.name} vs {b.name}</span>
    </p>
    <h1>{a.name} vs {b.name}</h1>
    <p class="lede">{description}</p>
    <p class="sub">
      <a href="{base}/systems/{a.id}">{a.name}</a> · <a href="{base}/systems/{b.id}"
        >{b.name}</a
      >
    </p>
    <div class="controls" aria-label="Comparison controls">
      <button type="button" class="control-btn" onclick={() => (swapped = !swapped)} title="Reverse which column is which">
        ⇄ Swap columns
      </button>
      {#if data.siblingsForA.length > 0}
        <label class="control-picker">
          <span class="picker-label">Compare {a.name} with…</span>
          <select bind:value={changeBId} onchange={onChangeB}>
            <option value="" disabled>— pick a system —</option>
            {#each data.siblingsForA as s (s.id)}
              <option value={s.id}>{s.name}</option>
            {/each}
          </select>
        </label>
      {/if}
      {#if data.siblingsForB.length > 0}
        <label class="control-picker">
          <span class="picker-label">Compare {b.name} with…</span>
          <select bind:value={changeAId} onchange={onChangeA}>
            <option value="" disabled>— pick a system —</option>
            {#each data.siblingsForB as s (s.id)}
              <option value={s.id}>{s.name}</option>
            {/each}
          </select>
        </label>
      {/if}
      <a
        class="control-btn"
        href="{base}/compare/custom?a={a.id}&b={b.id}"
        title="Open the client-side picker to compare any two catalog systems">
        Compare any two systems →
      </a>
      {#if canRecommendBetween}
        <a
          class="control-btn cross-link"
          href="{base}/recommend/between?low={a.id}&high={b.id}"
          title="See catalog systems positioned between these two on cost/capability">
          Recommend between these two →
        </a>
      {/if}
    </div>
  </header>

  {#if data.between.length}
    <section class="between">
      <h2>How they relate</h2>
      <ul>
        {#each data.between as e}
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

  <CompareTables {left} {right} />

  <footer class="meta">
    <p>
      Rows last verified {a.last_verified_at} / {b.last_verified_at}. Data is
      CC-BY-4.0 — see <a href="{base}/about">how to read this</a>.
    </p>
  </footer>
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
    margin: 0 0 0.4rem;
  }
  .sub {
    margin: 0 0 0.9rem;
    font-size: 0.95rem;
  }
  .sub a {
    color: #d4845f;
    text-decoration: none;
  }
  .sub a:hover {
    text-decoration: underline;
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    gap: 0.6rem 0.9rem;
    margin: 0 0 1.5rem;
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
    text-decoration: none;
    display: inline-block;
  }
  .control-btn:hover {
    background: #262626;
    color: #f0f0f0;
  }
  .control-btn.cross-link {
    background: #2a1e14;
    color: #e8a868;
    border-color: #4a3420;
  }
  .control-btn.cross-link:hover {
    background: #35271a;
    color: #f0b878;
  }
  .control-picker {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 0.82rem;
  }
  .picker-label {
    color: #888;
  }
  .control-picker select {
    background: #181818;
    color: #e8e8e8;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 0.88rem;
    font-family: inherit;
    min-width: 180px;
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
