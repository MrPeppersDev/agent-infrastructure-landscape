<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import JsonLd from '$lib/components/JsonLd.svelte';
  import { softwareLd, breadcrumbLd } from '$lib/seo/jsonld';
  import { sectionToSlug } from '$lib/seo/slugs';
  import { absoluteUrl } from '$lib/site';
  import type { LandscapeRecord, Edge, Cell } from '$lib/types';
  import { hasMemoryTaxonomy, memoryTaxonomyOf } from '$lib/families';
  import type { LifecycleInfo } from '$lib/lifecycle';
  import { LIFECYCLE_LABEL, LIFECYCLE_TONE, LIFECYCLE_BANNER } from '$lib/lifecycle-labels';
  import { correctionUrl, REPO, type HistoryEvent } from '$lib/history';

  type RelatedPair = { slug: string; otherId: string; otherName: string };
  type SimilarSystem = {
    id: string;
    name: string;
    tier: 1 | 2 | 3 | 4 | 5;
    desc: string | null;
  };

  let {
    data
  }: {
    data: {
      record: LandscapeRecord;
      outgoing: (Edge & { types: Edge['type'][] })[];
      incoming: (Edge & { types: Edge['type'][] })[];
      relatedNames: Record<string, string>;
      relatedPairs: RelatedPair[];
      similar: SimilarSystem[];
      hasAlternatives: boolean;
      history: HistoryEvent[];
      citedCells: number;
      lifecycle: LifecycleInfo;
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

  // v1.1.0 cells (#150 / #166): shown only once a backfill has filled them.
  function v11Text(c: Cell | undefined): string | null {
    if (!c || (c.status !== 'real-data' && c.status !== 'estimate')) return null;
    const v = c.value?.trim();
    if (!v) return null;
    return c.status === 'estimate' ? `${v} (estimate)` : v;
  }
  function opendiggerText(c: Cell | undefined): string | null {
    if (!c || c.status !== 'real-data') return null;
    try {
      const o = JSON.parse(c.value);
      const parts = [`OpenRank ${o.openrank_current} (12-mo avg ${o.openrank_12mo})`];
      if (o.participants != null) parts.push(`${o.participants} participants`);
      return `${parts.join(' · ')} — ${o.as_of}`;
    } catch {
      return null;
    }
  }
  const freshness = v11Text(record.cells['freshness-date']);

  const desc = cellText(record.cells.desc);
  const fallbackDesc = `${record.name}${primarySection ? ' — ' + primarySection : ''}. Tier ${record.tier} entry in the AI Agent Infrastructure Landscape: typed edges, citations, and benchmark coverage.`;
  const description = (desc ?? fallbackDesc).slice(0, 300);

  const title = `${record.name} — ${primarySection ?? 'AI agent stack'} | Landscape Profile`;

  // Headline facts gathered in render-order. nulls dropped at template time.
  const facts: { label: string; value: string | null; cite?: string | null; internal?: string; slug?: string }[] = [
    { label: 'Type', value: cellText(record.cells.type), slug: 'type' },
    { label: 'Tier', value: `T${record.tier}` },
    {
      label: 'Section',
      value: primarySection,
      internal: primarySectionSlug ? `${base}/category/${primarySectionSlug}` : undefined
    },
    { label: 'Created', value: cellText(record.cells.created), slug: 'created' },
    { label: 'Latest release', value: cellText(record.cells['latest-release']), slug: 'latest-release' },
    { label: 'License', value: cellText(record.cells.license), slug: 'license' },
    {
      label: 'GitHub',
      value: cellText(record.cells.gh),
      cite: record.cells.gh?.citation ?? null,
      slug: 'gh'
    },
    { label: 'Pricing', value: cellText(record.cells.pricing), slug: 'pricing' },
    { label: 'Funding', value: cellText(record.cells.funding), slug: 'funding' },
    { label: 'Freshness', value: freshness, cite: record.cells['freshness-date']?.citation ?? null, slug: 'freshness-date' },
    { label: 'Layer', value: v11Text(record.cells['taxonomy-three-layer-rollup']), slug: 'taxonomy-three-layer-rollup' },
    { label: 'Licensing', value: v11Text(record.cells['licensing-bucket']), slug: 'licensing-bucket' },
    { label: 'Deployment locus', value: v11Text(record.cells['architecture-deployment-locus']), slug: 'architecture-deployment-locus' },
    { label: 'Platform vs product', value: v11Text(record.cells['positioning-platform-vs-product']), slug: 'positioning-platform-vs-product' },
    { label: 'Accelerator', value: v11Text(record.cells['adoption-accelerator']), slug: 'adoption-accelerator' },
    { label: 'Maturity', value: v11Text(record.cells['maturity']), slug: 'maturity' },
    { label: 'SDK languages', value: v11Text(record.cells['sdk-languages'])?.replaceAll(',', ', ') ?? null, slug: 'sdk-languages' },
    { label: 'Protocols', value: v11Text(record.cells['protocol-support'])?.replaceAll(',', ', ') ?? null, slug: 'protocol-support' },
    { label: 'Compliance', value: v11Text(record.cells['compliance-certifications'])?.replaceAll(',', ', ') ?? null, slug: 'compliance-certifications' },
    {
      label: 'Developer activity',
      value: opendiggerText(record.cells['developer-activity-opendigger']),
      cite: record.cells['developer-activity-opendigger']?.citation ?? null,
      slug: 'developer-activity-opendigger'
    }
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
    const list = memoryTaxonomyOf(record)[axis];
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

  const ldData = [
    softwareLd({
      name: record.name,
      description,
      url: absoluteUrl(routePath),
      category: primarySection ?? undefined
    }),
    breadcrumbLd({
      items: [
        { name: 'Catalog', url: absoluteUrl('/') },
        { name: 'Systems', url: absoluteUrl('/systems') },
        ...(primarySection && primarySectionSlug
          ? [{ name: primarySection, url: absoluteUrl(`/category/${primarySectionSlug}`) }]
          : []),
        { name: record.name, url: absoluteUrl(routePath) }
      ]
    })
  ];
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
    {#if LIFECYCLE_BANNER.has(data.lifecycle.status)}
      <div class="life-banner {LIFECYCLE_TONE[data.lifecycle.status]}" role="note">
        <strong>{LIFECYCLE_LABEL[data.lifecycle.status]}.</strong>
        {#if data.lifecycle.note}{data.lifecycle.note}{/if}
        {#if data.lifecycle.evidence?.startsWith('http')}<a href={data.lifecycle.evidence} rel="nofollow noopener">Source</a>{/if}
        {#if data.hasAlternatives}· <a href="{base}/alternatives/{record.id}">Alternatives and migration notes →</a>{/if}
      </div>
    {/if}
    <p class="fresh">
      <span class="life {LIFECYCLE_TONE[data.lifecycle.status]}">{LIFECYCLE_LABEL[data.lifecycle.status]}</span>
      · Verified <strong>{record.last_verified_at ?? 'not yet'}</strong>
      {#if freshness}· fresh as of <strong>{freshness}</strong>{/if}
      · {data.citedCells} cited facts
      {#if data.history.length}· <a href="#changes">{data.history.length} recorded change{data.history.length === 1 ? '' : 's'}</a>{/if}
      · <a href={correctionUrl(record.id)} rel="noopener">Suggest a correction</a>
    </p>
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
              {#if f.slug}<a class="fix" href={correctionUrl(record.id, f.slug, f.value ?? '')} rel="noopener" title="Suggest a correction to {f.label.toLowerCase()}">fix</a>{/if}
            </dd>
          </div>
        {/if}
      {/each}
    </dl>
  </section>

  {#if hasMemoryTaxonomy(record)}
  <section class="taxonomy">
    <h2>Memory taxonomy</h2>
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
  {/if}

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

  {#if data.relatedPairs.length}
    <section class="compare-list">
      <h2>Compare {record.name} with…</h2>
      <ul>
        {#each data.relatedPairs as p}
          <li>
            <a href="{base}/compare/{p.slug}">{record.name} vs {p.otherName}</a>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  {#if data.hasAlternatives}
    <p class="alt-link">
      <a href="{base}/alternatives/{record.id}">Alternatives to {record.name} →</a>
      <span>live options ranked by shared design, licence, hosting and MCP support</span>
    </p>
  {/if}

  {#if data.similar.length}
    <section class="similar">
      <h2>Similar systems</h2>
      <p class="similar-lede">
        Other {primarySection ? primarySection.toLowerCase() : 'systems'} in the catalog,
        ranked by inbound references.
      </p>
      <ul>
        {#each data.similar as s}
          <li>
            <a href="{base}/systems/{s.id}">{s.name}</a>
            <span class="tier">T{s.tier}</span>
            {#if s.desc}<p>{s.desc}</p>{/if}
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  {#if data.history.length}
    <section class="changes" id="changes">
      <h2>What changed</h2>
      <p class="similar-lede">
        Changes to this record's lifecycle, licence, release, pricing and hosting facts, from the catalog's git history.
        <a href="{base}/feeds/{record.id}.xml">Subscribe (Atom)</a>
      </p>
      <ol>
        {#each data.history as ev}
          <li>
            <span class="when">{ev.date}</span>
            {#if ev.kind === 'added'}
              <span>Added to the catalog</span>
            {:else if ev.kind === 'removed'}
              <span>Removed from the catalog</span>
            {:else}
              <ul>
                {#each ev.changes as c}
                  <li>
                    <strong>{c.label}</strong>
                    {#if c.first}
                      first recorded as “{c.to}”
                    {:else if !c.to}
                      cleared (was “{c.from}”)
                    {:else}
                      “{c.from}” → “{c.to}”
                    {/if}
                    {#if c.source}<a href={c.source} rel="nofollow noopener">source</a>{/if}
                  </li>
                {/each}
              </ul>
            {/if}
            {#if ev.pr}<a class="pr" href="{REPO}/pull/{ev.pr}">#{ev.pr}</a>{:else}<a class="pr" href="{REPO}/commit/{ev.commit}">{ev.commit.slice(0, 7)}</a>{/if}
          </li>
        {/each}
      </ol>
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
              <span class="rel">{e.types.map((t) => edgeLabel[t] ?? t).join(' · ')}</span>
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
              <span class="rel">{e.types.map((t) => edgeLabel[t] ?? t).join(' · ')}</span>
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
      <a href="{base}/about">how to read this</a>. Raw record:
      <a href="{base}/api/systems/{record.id}.json">JSON</a>. Something wrong?
      <a href={correctionUrl(record.id)} rel="noopener">Suggest a correction</a>.
    </p>
  </footer>
</article>

<style>
  .fresh { font-size: 0.85rem; color: #8b949e; margin: -0.25rem 0 1rem; }
  .fresh a, .changes a { color: #58a6ff; }
  .life { display: inline-block; padding: 0 6px; border-radius: 3px; border: 1px solid; font-size: 0.78rem; font-weight: 600; }
  .life.ok { background: #1f3a26; color: #8fc99a; border-color: #2c5235; }
  .life.info { background: #1f2e3a; color: #8fb3c9; border-color: #2c4253; }
  .life.warn { background: #3a2e1f; color: #d29922; border-color: #5d4720; }
  .life.bad { background: #3a1f1f; color: #f85149; border-color: #5d2a2a; }
  .life-banner { margin: 0 0 0.75rem; padding: 0.6rem 0.8rem; border-radius: 6px; border: 1px solid; font-size: 0.9rem; line-height: 1.5; }
  .life-banner a { color: #58a6ff; }
  .life-banner.info { background: #161f29; border-color: #2c4253; color: #c9d1d9; }
  .life-banner.warn { background: #241d12; border-color: #5d4720; color: #e3c27a; }
  .life-banner.bad { background: #2a1515; border-color: #5d2a2a; color: #f0a8a3; }
  .fix { margin-left: 0.5rem; font-size: 0.72rem; color: #6e7681 !important; text-decoration: none; }
  .fix:hover { color: #58a6ff !important; text-decoration: underline; }
  .changes ol { list-style: none; padding: 0; margin: 0.5rem 0; }
  .changes > ol > li { border-left: 2px solid #30363d; padding: 0.25rem 0 0.5rem 0.75rem; margin-bottom: 0.25rem; font-size: 0.9rem; }
  .changes .when { color: #8b949e; font-variant-numeric: tabular-nums; margin-right: 0.5rem; }
  .changes ul { margin: 0.25rem 0 0; padding-left: 1rem; }
  .changes .pr { font-size: 0.75rem; margin-left: 0.25rem; }
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
  .alt-link {
    margin: 20px 0 0;
    font-size: 14px;
  }
  .alt-link a {
    color: #58a6ff;
    font-weight: 600;
  }
  .alt-link span {
    color: #6e7681;
    font-size: 12px;
    margin-left: 8px;
  }
  .compare-list ul,
  .similar ul,
  .edges ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .compare-list li {
    padding: 0.4rem 0;
    border-bottom: 1px solid #1f1f1f;
  }
  .compare-list a {
    color: #d4845f;
    text-decoration: none;
    font-weight: 500;
  }
  .compare-list a:hover {
    text-decoration: underline;
  }
  .similar-lede {
    color: #a0a0a0;
    margin: 0 0 0.8rem;
    font-size: 0.92rem;
  }
  .similar li {
    padding: 0.6rem 0;
    border-bottom: 1px solid #1f1f1f;
  }
  .similar a {
    color: #d4845f;
    text-decoration: none;
    font-weight: 500;
  }
  .similar a:hover {
    text-decoration: underline;
  }
  .similar .tier {
    margin-left: 0.5rem;
    color: #888;
    font-size: 0.85rem;
  }
  .similar li p {
    margin: 0.25rem 0 0;
    color: #aaa;
    font-size: 0.9rem;
    line-height: 1.45;
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
