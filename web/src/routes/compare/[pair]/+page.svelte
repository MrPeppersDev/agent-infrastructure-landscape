<script lang="ts">
  import { base } from '$app/paths';
  import { goto } from '$app/navigation';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { articleLd, breadcrumbLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';
  import { pairToSlug } from '$lib/seo/compare';
  import { sectionToSlug } from '$lib/seo/sections';
  import type { LandscapeRecord, Cell, Edge } from '$lib/types';
  import type { SiblingPair } from './+page';

  type Slim = Pick<
    LandscapeRecord,
    'id' | 'name' | 'tier' | 'url' | 'last_verified_at' | 'sections' | 'taxonomy' | 'cells'
  >;

  let {
    data
  }: {
    data: {
      a: Slim;
      b: Slim;
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

  function cellText(c: Cell | undefined): string | null {
    const v = c?.value?.trim();
    if (!v) return null;
    if (/^\s*(not\s+applicable|n\/a)\b/i.test(v)) return null;
    return v;
  }

  function primarySection(r: Slim): string | null {
    return r.sections.find((s) => s.primary)?.section ?? null;
  }

  type Axis = keyof LandscapeRecord['taxonomy'];
  function primaryTax(r: Slim, axis: Axis): string | null {
    const list = r.taxonomy[axis];
    if (!list || list.length === 0) return null;
    const p = list.find((v) => v.primary) ?? list[0];
    return p?.value ?? null;
  }

  function humanizeTag(t: string): string {
    return t.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  // Comparison rows = [(label, valueA, valueB)]. Rendered only if either
  // side has a non-empty value so missing data doesn't pad the page.
  type Row = { label: string; left: string | null; right: string | null };

  // Phase 2 signals: what the model costs and how good it is. These are
  // the newest, most decision-relevant cells (#101 / #125) — surfaced up
  // top rather than buried in the general at-a-glance grid.
  const phase2Rows = $derived<Row[]>(
    (
      [
        { label: 'Capability band', left: cellText(left.cells['capability-band']), right: cellText(right.cells['capability-band']) },
        { label: 'Capability composite', left: cellText(left.cells['capability-composite-score']), right: cellText(right.cells['capability-composite-score']) },
        { label: 'Cost tier', left: cellText(left.cells['cost-tier']), right: cellText(right.cells['cost-tier']) },
        { label: '$/Mtok input', left: cellText(left.cells['cost-input-usd-per-mtok']), right: cellText(right.cells['cost-input-usd-per-mtok']) },
        { label: '$/Mtok output', left: cellText(left.cells['cost-output-usd-per-mtok']), right: cellText(right.cells['cost-output-usd-per-mtok']) },
        {
          label: 'Use cases',
          left: cellText(left.cells['use-case-tags'])?.split(',').map((s) => humanizeTag(s.trim())).filter(Boolean).join(', ') ?? null,
          right: cellText(right.cells['use-case-tags'])?.split(',').map((s) => humanizeTag(s.trim())).filter(Boolean).join(', ') ?? null
        }
      ] as Row[]
    ).filter((r) => r.left || r.right)
  );

  const rows = $derived<Row[]>(
    (
      [
        { label: 'Section', left: primarySection(left), right: primarySection(right) },
        { label: 'Tier', left: `T${left.tier}`, right: `T${right.tier}` },
        { label: 'Type', left: cellText(left.cells.type), right: cellText(right.cells.type) },
        { label: 'Created', left: cellText(left.cells.created), right: cellText(right.cells.created) },
        { label: 'Latest release', left: cellText(left.cells['latest-release']), right: cellText(right.cells['latest-release']) },
        { label: 'License', left: cellText(left.cells.license), right: cellText(right.cells.license) },
        { label: 'GitHub', left: cellText(left.cells.gh), right: cellText(right.cells.gh) },
        { label: 'Pricing', left: cellText(left.cells.pricing), right: cellText(right.cells.pricing) },
        { label: 'Funding', left: cellText(left.cells.funding), right: cellText(right.cells.funding) },
        { label: 'Backend storage', left: cellText(left.cells['backend-storage']), right: cellText(right.cells['backend-storage']) },
        { label: 'Deployment', left: cellText(left.cells.deployment), right: cellText(right.cells.deployment) },
        { label: 'API surface', left: cellText(left.cells['api-surface']), right: cellText(right.cells['api-surface']) },
        { label: 'Embedding', left: cellText(left.cells['embedding-model']), right: cellText(right.cells['embedding-model']) },
        { label: 'Multi-tenancy', left: cellText(left.cells['multi-tenancy']), right: cellText(right.cells['multi-tenancy']) },
        { label: 'MCP', left: cellText(left.cells['mcp-support']), right: cellText(right.cells['mcp-support']) },
        { label: 'A2A', left: cellText(left.cells['a2a-support']), right: cellText(right.cells['a2a-support']) },
        { label: 'OpenTelemetry', left: cellText(left.cells.otel), right: cellText(right.cells.otel) },
        { label: 'Optimised for', left: cellText(left.cells['optimised-for']), right: cellText(right.cells['optimised-for']) },
        { label: 'Anti-fit', left: cellText(left.cells['anti-fit']), right: cellText(right.cells['anti-fit']) }
      ] as Row[]
    ).filter((r) => r.left || r.right)
  );

  const taxAxes: Axis[] = ['storage', 'retrieval', 'persistence', 'update', 'unit', 'governance', 'conflict'];
  const taxRows = $derived<Row[]>(
    taxAxes
      .map((axis) => ({
        label: axis,
        left: primaryTax(left, axis),
        right: primaryTax(right, axis)
      }))
      .filter((r) => r.left || r.right)
  );

  // "Where they differ" — rows from the At-a-glance + Phase 2 tables where
  // both sides have data and the values disagree. Saves the user scanning
  // 25 rows to find the 5 that actually distinguish the systems.
  function normalize(v: string | null): string {
    return (v ?? '').toLowerCase().trim();
  }
  const diffRows = $derived<Row[]>(
    [...phase2Rows, ...rows].filter(
      (r) => r.left && r.right && normalize(r.left) !== normalize(r.right)
    )
  );

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

  {#if phase2Rows.length}
    <section class="phase2">
      <h2>Cost &amp; capability</h2>
      <table>
        <thead>
          <tr>
            <th></th>
            <th>{left.name}</th>
            <th>{right.name}</th>
          </tr>
        </thead>
        <tbody>
          {#each phase2Rows as r}
            <tr>
              <th scope="row">{r.label}</th>
              <td>{r.left ?? '—'}</td>
              <td>{r.right ?? '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}

  {#if diffRows.length}
    <section class="differ">
      <h2>Where they differ <span class="count">({diffRows.length})</span></h2>
      <p class="differ-hint">
        Rows where both sides have data and the values disagree — the shortlist
        of dimensions that actually distinguish these two systems.
      </p>
      <table>
        <thead>
          <tr>
            <th></th>
            <th>{left.name}</th>
            <th>{right.name}</th>
          </tr>
        </thead>
        <tbody>
          {#each diffRows as r}
            <tr>
              <th scope="row">{r.label}</th>
              <td>{r.left}</td>
              <td>{r.right}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}

  <section>
    <h2>At a glance</h2>
    <table>
      <thead>
        <tr>
          <th></th>
          <th>{left.name}</th>
          <th>{right.name}</th>
        </tr>
      </thead>
      <tbody>
        {#each rows as r}
          <tr>
            <th scope="row">{r.label}</th>
            {#if r.label === 'Section'}
              <td
                >{#if r.left}<a href="{base}/category/{sectionToSlug(r.left)}">{r.left}</a>{:else}—{/if}</td
              >
              <td
                >{#if r.right}<a href="{base}/category/{sectionToSlug(r.right)}">{r.right}</a>{:else}—{/if}</td
              >
            {:else}
              <td>{r.left ?? '—'}</td>
              <td>{r.right ?? '—'}</td>
            {/if}
          </tr>
        {/each}
      </tbody>
    </table>
  </section>

  {#if taxRows.length}
    <section>
      <h2>Taxonomy</h2>
      <table>
        <thead>
          <tr>
            <th>Axis</th>
            <th>{left.name}</th>
            <th>{right.name}</th>
          </tr>
        </thead>
        <tbody>
          {#each taxRows as r}
            <tr>
              <th scope="row">{r.label}</th>
              <td>{r.left ?? '—'}</td>
              <td>{r.right ?? '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}

  {#if cellText(left.cells.pros) || cellText(right.cells.pros) || cellText(left.cells.cons) || cellText(right.cells.cons)}
    <section class="proscons">
      <h2>Pros &amp; cons</h2>
      <div class="grid">
        <div>
          <h3>{left.name}</h3>
          {#if cellText(left.cells.pros)}<p><strong>Pros:</strong> {cellText(left.cells.pros)}</p>{/if}
          {#if cellText(left.cells.cons)}<p><strong>Cons:</strong> {cellText(left.cells.cons)}</p>{/if}
        </div>
        <div>
          <h3>{right.name}</h3>
          {#if cellText(right.cells.pros)}<p><strong>Pros:</strong> {cellText(right.cells.pros)}</p>{/if}
          {#if cellText(right.cells.cons)}<p><strong>Cons:</strong> {cellText(right.cells.cons)}</p>{/if}
        </div>
      </div>
    </section>
  {/if}

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
  .differ-hint {
    color: #999;
    font-size: 0.85rem;
    margin: -0.3rem 0 0.7rem;
  }
  .count {
    color: #888;
    font-size: 0.85rem;
    font-weight: normal;
  }
  h2 {
    color: #e8e8e8;
    font-size: 1.15rem;
    margin: 2rem 0 0.6rem;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.3rem;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95rem;
  }
  th,
  td {
    text-align: left;
    padding: 0.5rem 0.6rem;
    border-bottom: 1px solid #1f1f1f;
    vertical-align: top;
  }
  thead th {
    color: #d8d8d8;
    border-bottom: 1px solid #333;
  }
  th[scope='row'] {
    color: #999;
    text-transform: lowercase;
    font-variant: small-caps;
    width: 28%;
  }
  td {
    color: #d6d6d6;
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
  .proscons .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }
  .proscons h3 {
    font-size: 1rem;
    color: #e0e0e0;
    margin: 0 0 0.4rem;
  }
  .proscons p {
    margin: 0.3rem 0;
  }
  @media (max-width: 720px) {
    .proscons .grid {
      grid-template-columns: 1fr;
    }
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
