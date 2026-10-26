<script lang="ts">
  // /compare/many?ids=a,b,c — compare up to five systems side by side, every
  // value linked to its source. Linked from the chooser tables and the
  // compatibility page.
  import { base } from '$app/paths';
  import { browser } from '$app/environment';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import RecordPicker from '$lib/components/RecordPicker.svelte';

  type Cell = { value?: string; citation?: string | null; status?: string };
  type Sys = {
    id: string;
    name: string;
    url: string | null;
    section: string;
    tier: number;
    last_verified_at: string | null;
    lifecycle: { status: string; note: string | null };
    taxonomy: Record<string, { value: string }[]>;
    cells: Record<string, Cell>;
  };

  let { data }: { data: { options: { id: string; name: string; section: string }[] } } = $props();
  const MAX = 5;
  let ids = $state<string[]>(browser ? (new URLSearchParams(location.search).get('ids') ?? '').split(',').filter(Boolean).slice(0, MAX) : []);
  let adding = $state('');
  let loaded = $state<Record<string, Sys | 'error'>>({});

  $effect(() => {
    if (adding && !ids.includes(adding) && ids.length < MAX) ids = [...ids, adding];
    if (adding) adding = '';
  });
  $effect(() => {
    const qs = ids.length ? `?ids=${ids.join(',')}` : '';
    if (location.search !== qs) history.replaceState({}, '', `${location.pathname}${qs}`);
    for (const id of ids) {
      if (loaded[id]) continue;
      fetch(`${base}/api/systems/${id}.json`)
        .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
        .then((j: Sys) => (loaded = { ...loaded, [id]: j }))
        .catch(() => (loaded = { ...loaded, [id]: 'error' }));
    }
  });
  const systems = $derived(ids.map((id) => loaded[id]).filter((s): s is Sys => !!s && s !== 'error'));

  const EMPTY = new Set(['no-data', 'not-applicable', 'depth-floor-reached']);
  const ROWS: [string, string][] = [
    ['type', 'Type'], ['license', 'Licence'], ['deployment', 'Deployment'], ['pricing', 'Pricing'],
    ['latest-release', 'Latest release'], ['gh', 'GitHub'], ['mcp-support', 'MCP'], ['a2a-support', 'A2A'],
    ['runtimes', 'SDKs / runtimes'], ['api-surface', 'API surface'], ['backend-storage', 'Backend storage'],
    ['embedding-model', 'Embedding model'], ['multi-tenancy', 'Multi-tenancy'], ['compliance', 'Compliance'],
    ['contradiction', 'Contradictions'], ['forgetting', 'Forgetting'], ['optimised-for', 'Optimised for'],
    ['anti-fit', 'Anti-fit'], ['funding', 'Funding / ownership']
  ];
  const AXES = ['storage', 'retrieval', 'persistence', 'update', 'unit', 'governance', 'conflict'];
  const cell = (s: Sys, k: string): Cell | null => {
    const c = s.cells[k];
    return c && c.value && !EMPTY.has(c.status ?? '') ? c : null;
  };
  const rows = $derived(ROWS.filter(([k]) => systems.some((s) => cell(s, k))));
  const axes = $derived(AXES.filter((a) => systems.some((s) => s.taxonomy?.[a]?.length)));
</script>

<SeoHead
  title="Compare AI agent systems side by side"
  description="Compare up to five AI agent memory layers, frameworks, vector databases or tools side by side: licence, deployment, pricing, MCP support, storage and retrieval design, every value cited."
  path="/compare/many"
/>

<main class="page">
  <h1>Compare side by side</h1>
  <p class="lede">Up to five systems. Every value links to its source; empty means the catalog has no data. For two systems, the <a href="{base}/compare">head-to-head pages</a> add how they relate.</p>
  <div class="pick">
    <RecordPicker options={data.options} bind:value={adding} label="Add a system" placeholder={ids.length >= MAX ? `Up to ${MAX} systems` : 'Type to add a system…'} />
  </div>
  {#if ids.length}
    <ul class="chips">
      {#each ids as id (id)}
        <li>{data.options.find((o) => o.id === id)?.name ?? id} <button type="button" aria-label="Remove" onclick={() => (ids = ids.filter((x) => x !== id))}>×</button>{#if loaded[id] === 'error'} <span class="err">couldn't load</span>{/if}</li>
      {/each}
    </ul>
  {/if}

  {#if systems.length}
    <div class="wrap">
      <table>
        <thead>
          <tr><th></th>{#each systems as s (s.id)}<th><a href="{base}/systems/{s.id}">{s.name}</a><span class="sec">{s.section}</span></th>{/each}</tr>
        </thead>
        <tbody>
          <tr><th>Status</th>{#each systems as s (s.id)}<td class:warn={s.lifecycle.status !== 'active'}>{s.lifecycle.status}{s.lifecycle.note ? ` — ${s.lifecycle.note}` : ''}</td>{/each}</tr>
          <tr><th>Tier</th>{#each systems as s (s.id)}<td>T{s.tier}</td>{/each}</tr>
          {#each rows as [k, label] (k)}
            <tr>
              <th>{label}</th>
              {#each systems as s (s.id)}
                {@const c = cell(s, k)}
                <td>{#if c}{c.value}{#if c.citation} <a class="src" href={c.citation} rel="nofollow noopener">source</a>{/if}{/if}</td>
              {/each}
            </tr>
          {/each}
          {#each axes as a (a)}
            <tr><th>{a}</th>{#each systems as s (s.id)}<td>{(s.taxonomy?.[a] ?? []).map((v) => v.value).join(', ')}</td>{/each}</tr>
          {/each}
          <tr><th>Verified</th>{#each systems as s (s.id)}<td>{s.last_verified_at ?? ''}</td>{/each}</tr>
        </tbody>
      </table>
    </div>
    {#if systems.length >= 2}
      <p class="meta"><a href="{base}/compatibility?ids={ids.join(',')}">Do these work together? →</a></p>
    {/if}
  {:else if ids.length}
    <p class="meta">Loading…</p>
  {/if}
</main>

<style>
  .page { max-width: 1280px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  a { color: #58a6ff; }
  .lede, .meta { color: #8b949e; }
  .pick { max-width: 520px; }
  .chips { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
  .chips li { border: 1px solid #30363d; border-radius: 999px; padding: 3px 6px 3px 12px; background: #161b22; font-size: 14px; }
  .chips button { background: none; border: none; color: #8b949e; cursor: pointer; font-size: 16px; }
  .err { color: #f85149; font-size: 12px; }
  .wrap { overflow-x: auto; border: 1px solid #30363d; border-radius: 8px; margin-top: 12px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { text-align: left; vertical-align: top; padding: 8px 10px; border-bottom: 1px solid #21262d; min-width: 180px; }
  tbody th { color: #8b949e; font-weight: 500; min-width: 120px; position: sticky; left: 0; background: #0d1117; }
  thead th { color: #f0f6fc; }
  .sec { display: block; color: #6e7681; font-weight: 400; font-size: 11px; }
  .src { font-size: 11px; }
  .warn { color: #d29922; }
</style>
