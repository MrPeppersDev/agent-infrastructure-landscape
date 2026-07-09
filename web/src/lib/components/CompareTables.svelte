<script lang="ts" module>
  // Shared side-by-side comparison rendering — extracted from
  // /compare/[pair]/+page.svelte so the client-side /compare/custom route
  // can reuse the exact same tables (refs #134). The pair page keeps its
  // own SEO surface (SeoHead, JsonLd, canonical); this component only
  // owns the Phase 2 block, "Where they differ", At-a-glance, Taxonomy,
  // and Pros & cons sections.
  import type { LandscapeRecord, Cell } from '$lib/types';

  export type SlimRecord = Pick<
    LandscapeRecord,
    'id' | 'name' | 'tier' | 'url' | 'last_verified_at' | 'sections' | 'taxonomy' | 'cells'
  >;

  export function cellText(c: Cell | undefined): string | null {
    const v = c?.value?.trim();
    if (!v) return null;
    if (/^\s*(not\s+applicable|n\/a)\b/i.test(v)) return null;
    return v;
  }

  export function primarySection(r: SlimRecord): string | null {
    return r.sections.find((s) => s.primary)?.section ?? null;
  }
</script>

<script lang="ts">
  import { base } from '$app/paths';
  import { sectionToSlug } from '$lib/seo/sections';

  let { left, right }: { left: SlimRecord; right: SlimRecord } = $props();

  type Axis = keyof LandscapeRecord['taxonomy'];
  function primaryTax(r: SlimRecord, axis: Axis): string | null {
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
</script>

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

<style>
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
</style>
