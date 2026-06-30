<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { softwareLd } from '$lib/seo/jsonld';
  import { sectionToSlug } from '$lib/seo/sections';
  import { absoluteUrl } from '$lib/site';
  import type { LandscapeRecord, Edge, Cell } from '$lib/types';

  let {
    data
  }: {
    data: {
      record: LandscapeRecord;
      outgoing: Edge[];
      incoming: Edge[];
      relatedNames: Record<string, string>;
    };
  } = $props();

  const record = data.record;
  const primarySection = record.sections.find((s) => s.primary)?.section ?? null;
  const primarySectionSlug = primarySection ? sectionToSlug(primarySection) : null;
  const routePath = `/systems/${record.id}`;

  function cellText(c: Cell | undefined): string | null {
    if (!c) return null;
    const v = c.value?.trim();
    return v ? v : null;
  }

  const desc = cellText(record.cells.desc);
  const fallbackDesc = `${record.name}${primarySection ? ' — ' + primarySection : ''}. Tier ${record.tier} entry in the AI Agent Infrastructure Landscape: typed edges, citations, and benchmark coverage.`;
  const description = (desc ?? fallbackDesc).slice(0, 300);

  const title = `${record.name} — ${primarySection ?? 'AI agent memory'} | Landscape Profile`;

  // Headline facts gathered in render-order. nulls dropped at template time.
  const facts: { label: string; value: string | null; cite?: string | null; internal?: string }[] = [
    { label: 'Type', value: cellText(record.cells.type) },
    { label: 'Tier', value: `T${record.tier}` },
    {
      label: 'Section',
      value: primarySection,
      internal: primarySectionSlug ? `${base}/category/${primarySectionSlug}` : undefined
    },
    { label: 'Created', value: cellText(record.cells.created) },
    { label: 'Latest release', value: cellText(record.cells['latest-release']) },
    { label: 'License', value: cellText(record.cells.license) },
    {
      label: 'GitHub',
      value: cellText(record.cells.gh),
      cite: record.cells.gh?.citation ?? null
    },
    { label: 'Pricing', value: cellText(record.cells.pricing) },
    { label: 'Funding', value: cellText(record.cells.funding) }
  ];

  // Group primary taxonomy values by axis for the "at a glance" panel.
  type Axis = keyof LandscapeRecord['taxonomy'];
  const taxonomyAxes: Axis[] = [
    'storage',
    'retrieval',
    'persistence',
    'update',
    'unit',
    'governance',
    'conflict'
  ];

  function primaryTax(axis: Axis): string | null {
    const list = record.taxonomy[axis];
    if (!list || list.length === 0) return null;
    const p = list.find((v) => v.primary) ?? list[0];
    return p?.value ?? null;
  }

  // Edge-type display labels.
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

  function relUrl(id: string): string {
    return `${base}/systems/${id}`;
  }

  const ldData = softwareLd({
    name: record.name,
    description,
    url: absoluteUrl(routePath),
    category: primarySection ?? undefined
  });
</script>

<SeoHead {title} {description} path={routePath} ogType="article" />
<JsonLd data={ldData} />

<article class="system">
  <header class="system-header">
    <p class="breadcrumbs">
      <a href="{base}/">Catalog</a>
      <span aria-hidden="true">›</span>
      <a href="{base}/systems">Systems</a>
      {#if primarySection && primarySectionSlug}
        <span aria-hidden="true">›</span>
        <a href="{base}/category/{primarySectionSlug}">{primarySection}</a>
      {/if}
      <span aria-hidden="true">›</span>
      <span>{record.name}</span>
    </p>
    <h1>{record.name}</h1>
    {#if record.url}
      <p class="home"><a href={record.url} rel="nofollow noopener">{record.url}</a></p>
    {/if}
    <p class="lede">{desc ?? fallbackDesc}</p>
  </header>

  <section class="facts" aria-label="At a glance">
    <h2>At a glance</h2>
    <dl>
      {#each facts as f}
        {#if f.value}
          <div>
            <dt>{f.label}</dt>
            <dd>
              {#if f.internal}
                <a href={f.internal}>{f.value}</a>
              {:else if f.cite}
                <a href={f.cite} rel="nofollow noopener">{f.value}</a>
              {:else}
                {f.value}
              {/if}
            </dd>
          </div>
        {/if}
      {/each}
    </dl>
  </section>

  <section class="taxonomy">
    <h2>Taxonomy</h2>
    <dl>
      {#each taxonomyAxes as axis}
        {@const v = primaryTax(axis)}
        {#if v}
          <div>
            <dt>{axis}</dt>
            <dd>{v}</dd>
          </div>
        {/if}
      {/each}
    </dl>
  </section>

  {#if cellText(record.cells['optimised-for']) || cellText(record.cells['anti-fit'])}
    <section>
      <h2>When to use</h2>
      {#if cellText(record.cells['optimised-for'])}
        <p><strong>Optimised for:</strong> {cellText(record.cells['optimised-for'])}</p>
      {/if}
      {#if cellText(record.cells['anti-fit'])}
        <p><strong>Anti-fit:</strong> {cellText(record.cells['anti-fit'])}</p>
      {/if}
    </section>
  {/if}

  {#if cellText(record.cells.pros) || cellText(record.cells.cons)}
    <section class="proscons">
      <h2>Pros &amp; cons</h2>
      <div class="cols">
        {#if cellText(record.cells.pros)}
          <div>
            <h3>Pros</h3>
            <p>{cellText(record.cells.pros)}</p>
          </div>
        {/if}
        {#if cellText(record.cells.cons)}
          <div>
            <h3>Cons</h3>
            <p>{cellText(record.cells.cons)}</p>
          </div>
        {/if}
      </div>
    </section>
  {/if}

  {#if cellText(record.cells.claims)}
    <section>
      <h2>Claims &amp; capabilities</h2>
      <p>{cellText(record.cells.claims)}</p>
    </section>
  {/if}

  {#if cellText(record.cells['api-surface']) || cellText(record.cells['backend-storage']) || cellText(record.cells.deployment)}
    <section>
      <h2>Technical surface</h2>
      <dl>
        {#each [['api-surface', 'API surface'], ['backend-storage', 'Backend storage'], ['deployment', 'Deployment'], ['embedding-model', 'Embedding model'], ['multi-tenancy', 'Multi-tenancy'], ['mcp-support', 'MCP'], ['a2a-support', 'A2A'], ['otel', 'OpenTelemetry']] as [slug, label]}
          {@const v = cellText(record.cells[slug as keyof typeof record.cells])}
          {#if v}
            <div>
              <dt>{label}</dt>
              <dd>{v}</dd>
            </div>
          {/if}
        {/each}
      </dl>
    </section>
  {/if}

  {#if data.outgoing.length || data.incoming.length}
    <section class="edges">
      <h2>Related systems</h2>
      {#if data.outgoing.length}
        <h3>References ({data.outgoing.length})</h3>
        <ul>
          {#each data.outgoing as e}
            <li>
              <a href={relUrl(e.target)}>{data.relatedNames[e.target] ?? e.target}</a>
              <span class="rel">{edgeLabel[e.type] ?? e.type}</span>
              {#if e.evidence}<span class="ev">— {e.evidence}</span>{/if}
            </li>
          {/each}
        </ul>
      {/if}
      {#if data.incoming.length}
        <h3>Referenced by ({data.incoming.length})</h3>
        <ul>
          {#each data.incoming as e}
            <li>
              <a href={relUrl(e.source)}>{data.relatedNames[e.source] ?? e.source}</a>
              <span class="rel">{edgeLabel[e.type] ?? e.type}</span>
              {#if e.evidence}<span class="ev">— {e.evidence}</span>{/if}
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  {/if}

  <footer class="meta">
    <p>
      Row last verified {record.last_verified_at}. Catalog data is CC-BY-4.0 — see
      <a href="{base}/about">how to read this</a>.
    </p>
  </footer>
</article>

<style>
  .system {
    max-width: 760px;
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
    margin: 0 0 0.25rem;
    font-size: 1.8rem;
    color: #f0f0f0;
  }
  .home {
    margin: 0 0 1rem;
    font-size: 0.95rem;
  }
  .home a {
    color: #d4845f;
    text-decoration: none;
  }
  .home a:hover {
    text-decoration: underline;
  }
  .lede {
    font-size: 1.05rem;
    color: #c8c8c8;
    margin: 0 0 1.5rem;
  }
  h2 {
    font-size: 1.15rem;
    color: #e8e8e8;
    margin: 2rem 0 0.6rem;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.3rem;
  }
  h3 {
    font-size: 1rem;
    color: #d8d8d8;
    margin: 1.1rem 0 0.4rem;
  }
  dl {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 0.3rem 1rem;
    margin: 0;
  }
  dl > div {
    display: contents;
  }
  dt {
    color: #999;
    text-transform: lowercase;
    font-variant: small-caps;
  }
  dd {
    margin: 0;
    color: #ddd;
  }
  dd a {
    color: #d4845f;
    text-decoration: none;
  }
  dd a:hover {
    text-decoration: underline;
  }
  .proscons .cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }
  @media (max-width: 640px) {
    .proscons .cols {
      grid-template-columns: 1fr;
    }
    dl {
      grid-template-columns: 1fr;
    }
    dt {
      margin-top: 0.5rem;
    }
  }
  .edges ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .edges li {
    padding: 0.4rem 0;
    border-bottom: 1px solid #1f1f1f;
  }
  .edges a {
    color: #d4845f;
    text-decoration: none;
    font-weight: 500;
  }
  .edges a:hover {
    text-decoration: underline;
  }
  .edges .rel {
    color: #888;
    margin-left: 0.4rem;
    font-size: 0.9rem;
  }
  .edges .ev {
    color: #aaa;
    font-size: 0.9rem;
    display: block;
    margin-top: 0.15rem;
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
