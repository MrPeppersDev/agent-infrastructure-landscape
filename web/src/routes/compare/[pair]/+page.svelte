<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { articleLd } from '$lib/seo/jsonld';
  import { absoluteUrl } from '$lib/site';
  import { pairToSlug } from '$lib/seo/compare';
  import type { LandscapeRecord, Cell, Edge } from '$lib/types';

  type Slim = Pick<
    LandscapeRecord,
    'id' | 'name' | 'tier' | 'url' | 'last_verified_at' | 'sections' | 'taxonomy' | 'cells'
  >;

  let {
    data
  }: { data: { a: Slim; b: Slim; between: Edge[] } } = $props();

  const a = data.a;
  const b = data.b;

  function cellText(c: Cell | undefined): string | null {
    const v = c?.value?.trim();
    return v ? v : null;
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

  // Comparison rows = [(label, valueA, valueB)]. Rendered only if either
  // side has a non-empty value so missing data doesn't pad the page.
  type Row = { label: string; a: string | null; b: string | null };

  const rows: Row[] = [
    { label: 'Section', a: primarySection(a), b: primarySection(b) },
    { label: 'Tier', a: `T${a.tier}`, b: `T${b.tier}` },
    { label: 'Type', a: cellText(a.cells.type), b: cellText(b.cells.type) },
    { label: 'Created', a: cellText(a.cells.created), b: cellText(b.cells.created) },
    { label: 'Latest release', a: cellText(a.cells['latest-release']), b: cellText(b.cells['latest-release']) },
    { label: 'License', a: cellText(a.cells.license), b: cellText(b.cells.license) },
    { label: 'GitHub', a: cellText(a.cells.gh), b: cellText(b.cells.gh) },
    { label: 'Pricing', a: cellText(a.cells.pricing), b: cellText(b.cells.pricing) },
    { label: 'Funding', a: cellText(a.cells.funding), b: cellText(b.cells.funding) },
    { label: 'Backend storage', a: cellText(a.cells['backend-storage']), b: cellText(b.cells['backend-storage']) },
    { label: 'Deployment', a: cellText(a.cells.deployment), b: cellText(b.cells.deployment) },
    { label: 'API surface', a: cellText(a.cells['api-surface']), b: cellText(b.cells['api-surface']) },
    { label: 'Embedding', a: cellText(a.cells['embedding-model']), b: cellText(b.cells['embedding-model']) },
    { label: 'Multi-tenancy', a: cellText(a.cells['multi-tenancy']), b: cellText(b.cells['multi-tenancy']) },
    { label: 'MCP', a: cellText(a.cells['mcp-support']), b: cellText(b.cells['mcp-support']) },
    { label: 'A2A', a: cellText(a.cells['a2a-support']), b: cellText(b.cells['a2a-support']) },
    { label: 'OpenTelemetry', a: cellText(a.cells.otel), b: cellText(b.cells.otel) },
    { label: 'Optimised for', a: cellText(a.cells['optimised-for']), b: cellText(b.cells['optimised-for']) },
    { label: 'Anti-fit', a: cellText(a.cells['anti-fit']), b: cellText(b.cells['anti-fit']) }
  ].filter((r) => r.a || r.b);

  const taxAxes: Axis[] = ['storage', 'retrieval', 'persistence', 'update', 'unit', 'governance', 'conflict'];
  const taxRows: Row[] = taxAxes
    .map((axis) => ({
      label: axis,
      a: primaryTax(a, axis),
      b: primaryTax(b, axis)
    }))
    .filter((r) => r.a || r.b);

  const slug = pairToSlug(a.id, b.id);
  const routePath = `/compare/${slug}`;
  const title = `${a.name} vs ${b.name} — Compared on 19 Dimensions`;
  const sameSection = primarySection(a) === primarySection(b);
  const description = sameSection
    ? `${a.name} vs ${b.name}: side-by-side comparison of two ${primarySection(a)?.toLowerCase()} systems — architecture, taxonomy, license, pricing, MCP/A2A support, and direct edges.`
    : `${a.name} (${primarySection(a)?.toLowerCase()}) vs ${b.name} (${primarySection(b)?.toLowerCase()}): cross-category comparison covering architecture, taxonomy, license, pricing, and direct edges.`;

  const ldData = articleLd({
    headline: title,
    description,
    url: absoluteUrl(routePath)
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

  <section>
    <h2>At a glance</h2>
    <table>
      <thead>
        <tr>
          <th></th>
          <th>{a.name}</th>
          <th>{b.name}</th>
        </tr>
      </thead>
      <tbody>
        {#each rows as r}
          <tr>
            <th scope="row">{r.label}</th>
            <td>{r.a ?? '—'}</td>
            <td>{r.b ?? '—'}</td>
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
            <th>{a.name}</th>
            <th>{b.name}</th>
          </tr>
        </thead>
        <tbody>
          {#each taxRows as r}
            <tr>
              <th scope="row">{r.label}</th>
              <td>{r.a ?? '—'}</td>
              <td>{r.b ?? '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}

  {#if cellText(a.cells.pros) || cellText(b.cells.pros) || cellText(a.cells.cons) || cellText(b.cells.cons)}
    <section class="proscons">
      <h2>Pros &amp; cons</h2>
      <div class="grid">
        <div>
          <h3>{a.name}</h3>
          {#if cellText(a.cells.pros)}<p><strong>Pros:</strong> {cellText(a.cells.pros)}</p>{/if}
          {#if cellText(a.cells.cons)}<p><strong>Cons:</strong> {cellText(a.cells.cons)}</p>{/if}
        </div>
        <div>
          <h3>{b.name}</h3>
          {#if cellText(b.cells.pros)}<p><strong>Pros:</strong> {cellText(b.cells.pros)}</p>{/if}
          {#if cellText(b.cells.cons)}<p><strong>Cons:</strong> {cellText(b.cells.cons)}</p>{/if}
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
    margin: 0 0 1.5rem;
    font-size: 0.95rem;
  }
  .sub a {
    color: #d4845f;
    text-decoration: none;
  }
  .sub a:hover {
    text-decoration: underline;
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
