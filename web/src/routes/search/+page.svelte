<script lang="ts">
  // /search — ask the catalog in plain words. Phrases like "self-hosted",
  // "open source", "with MCP", "python" become must-haves checked against
  // catalogued facts; the rest is ranked with BM25 (mcp/src/search.ts).
  // Runs in the browser over /api/search-docs.json; the query is never sent anywhere.
  import { base } from '$app/paths';
  import { browser } from '$app/environment';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import { buildIndex, search, type SearchDoc, type SearchIndex } from '../../../../mcp/src/search';

  let q = $state(browser ? (new URLSearchParams(location.search).get('q') ?? '') : '');
  let index = $state<SearchIndex | null>(null);
  let failed = $state(false);

  $effect(() => {
    if (!browser || index) return;
    fetch(`${base}/api/search-docs.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((docs: SearchDoc[]) => (index = buildIndex(docs)))
      .catch(() => (failed = true));
  });
  $effect(() => {
    const qs = q.trim() ? `?q=${encodeURIComponent(q.trim())}` : '';
    if (location.search !== qs) history.replaceState({}, '', `${location.pathname}${qs}`);
  });

  const result = $derived(index && q.trim() ? search(index, q, 25) : null);
  const EXAMPLES = [
    'memory that handles contradictions and runs on postgres',
    'self-hosted vector db with MCP, python',
    'open source graph memory with temporal history',
    'sandbox for running agent code',
    'managed voice agent platform',
    'durable execution typescript'
  ];
  const FAMILY: Record<string, string> = { memory: 'Agent Memory', 'memory-research': 'Research', agents: 'Agents', data: 'Data', 'models-ops': 'Models & Ops' };
</script>

<SeoHead
  title="Ask the AI agent infrastructure catalog"
  description="Search agent frameworks, models, memory layers, vector databases, gateways and tools in plain words: 'self-hosted vector db with MCP, python' or 'memory that handles contradictions on Postgres'."
  path="/search"
/>

<main class="page">
  <h1>Ask the catalog</h1>
  <p class="lede">
    Describe what you need in plain words. Requirements like <em>self-hosted</em>, <em>managed</em>, <em>open source</em>,
    <em>with MCP</em>, <em>Python</em> or <em>TypeScript</em> are checked against catalogued facts. The rest of your words rank
    the results. It runs in your browser, and nothing you type is sent anywhere.
  </p>
  <!-- svelte-ignore a11y_autofocus -->
  <input class="q" type="search" bind:value={q} placeholder="e.g. self-hosted vector db with MCP, python" aria-label="Describe what you need" autofocus />
  <p class="ex">
    {#each EXAMPLES as e (e)}<button type="button" onclick={() => (q = e)}>{e}</button>{/each}
  </p>

  {#if failed}
    <p class="none">Couldn't load the search index. Try the <a href="{base}/">catalog table</a> filters instead.</p>
  {:else if !index && q.trim()}
    <p class="meta">Loading the catalog…</p>
  {:else if result}
    <p class="meta">
      {#if result.constraints.length}Must-haves: {#each result.constraints as c, i (c.label)}<strong>{c.label}</strong>{i < result.constraints.length - 1 ? ', ' : ''}{/each}. {/if}
      {#if result.terms.length}Ranking by: {result.terms.join(', ')}. {/if}
      {result.hits.length} of {result.considered} systems shown.
    </p>
    {#if result.hits.length}
      <ol class="hits">
        {#each result.hits as h (h.id)}
          <li>
            <div class="head">
              <a class="name" href="{base}/systems/{h.id}">{h.name}</a>
              <span class="sec">{FAMILY[h.family] ?? h.family} · {h.section}</span>
              {#if h.warning}<span class="warn">⚠ {h.warning}</span>{/if}
            </div>
            {#if h.desc}<p class="desc">{h.desc}</p>{/if}
            <p class="why">
              {#if h.confirmed.length}<span class="ok">✓ {h.confirmed.join(' · ')}</span>{/if}
              {#if h.unconfirmed.length}<span class="unk">? not confirmed: {h.unconfirmed.join(', ')}</span>{/if}
              {#if h.matched.length}<span>matches: {h.matched.join(', ')}</span>{/if}
              <a href="{base}/alternatives/{h.id}">alternatives</a>
            </p>
          </li>
        {/each}
      </ol>
    {:else}
      <p class="none">Nothing matches all of that. Drop a requirement, or try the <a href="{base}/choose">chooser</a>.</p>
    {/if}
  {/if}
  <p class="foot">
    Keyword ranking (BM25) over names, types, descriptions, claims and design facts, with synonyms for catalog terms
    ("contradictions" → conflict handling, "postgres" → pgvector). Also available as the MCP tool <code>ask_catalog</code>.
    For a guided pick, use the <a href="{base}/choose">memory</a>, <a href="{base}/choose/framework">framework</a> or
    <a href="{base}/choose/data">data-store</a> chooser.
  </p>
</main>

<style>
  .page { max-width: 900px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; line-height: 1.55; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  a { color: #58a6ff; }
  .lede, .meta, .foot { color: #8b949e; }
  .foot { font-size: 12px; margin-top: 24px; }
  .q { width: 100%; box-sizing: border-box; font-size: 17px; padding: 12px 14px; background: #0d1117; color: #f0f6fc; border: 1px solid #30363d; border-radius: 10px; }
  .q:focus { outline: 2px solid #1f6feb; border-color: #1f6feb; }
  .ex { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0; }
  .ex button { border: 1px solid #30363d; background: #161b22; color: #c9d1d9; border-radius: 999px; padding: 3px 10px; font: inherit; font-size: 12px; cursor: pointer; }
  .hits { list-style: none; padding: 0; display: grid; gap: 10px; }
  .hits li { border: 1px solid #30363d; border-radius: 10px; padding: 10px 14px; background: #0d1117; }
  .head { display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline; }
  .name { font-weight: 600; font-size: 16px; }
  .sec { color: #6e7681; font-size: 12px; }
  .warn { color: #d29922; font-size: 12px; }
  .desc { margin: 6px 0 0; font-size: 13px; color: #8b949e; }
  .why { margin: 6px 0 0; font-size: 12px; display: flex; flex-wrap: wrap; gap: 12px; color: #8b949e; }
  .ok { color: #3fb950; }
  .unk { color: #d29922; }
  .none { color: #d29922; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
</style>
