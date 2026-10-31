<script lang="ts">
  // /compatibility — pick 2–6 systems (say a framework, a memory layer and a
  // vector store) and see, for every pair, the catalog's evidence that they
  // integrate. "Not recorded" means the catalog has no source either way,
  // not that they're incompatible. Pick one system to list what it works with.
  import { base } from '$app/paths';
  import { browser } from '$app/environment';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import RecordPicker from '$lib/components/RecordPicker.svelte';
  import { verifiedStamp } from '$lib/compat';
  import type { CompatPair, CompatEvidence } from '$lib/compat';

  let { data }: { data: { links: CompatPair[]; options: { id: string; name: string; section: string; linked: boolean }[] } } = $props();

  const name = $derived(new Map(data.options.map((o) => [o.id, o.name])));
  const byKey = $derived(new Map(data.links.map((l) => [`${l.a}|${l.b}`, l])));
  const pairOf = (a: string, b: string): CompatPair =>
    byKey.get(`${a}|${b}`) ?? byKey.get(`${b}|${a}`) ?? { a, b, status: 'not-recorded', evidence: [] };

  const initial = browser ? (new URLSearchParams(location.search).get('ids') ?? '').split(',').filter(Boolean).slice(0, 6) : [];
  let ids = $state<string[]>(initial);
  let adding = $state('');
  $effect(() => {
    if (adding && !ids.includes(adding) && ids.length < 6) ids = [...ids, adding];
    if (adding) adding = '';
  });
  const remove = (id: string) => (ids = ids.filter((x) => x !== id));

  $effect(() => {
    const qs = ids.length ? `?ids=${ids.join(',')}` : '';
    if (location.search !== qs) history.replaceState({}, '', `${location.pathname}${qs}`);
  });

  const pairs = $derived(ids.flatMap((a, i) => ids.slice(i + 1).map((b) => pairOf(a, b))));
  const worksWith = $derived.by(() => {
    if (ids.length !== 1) return [];
    const id = ids[0];
    return data.links
      .filter((l) => (l.a === id || l.b === id) && l.status === 'documented')
      .map((l) => ({ other: l.a === id ? l.b : l.a, pair: l }))
      .sort((x, y) => y.pair.evidence.length - x.pair.evidence.length || (name.get(x.other) ?? '').localeCompare(name.get(y.other) ?? ''));
  });

  const EDGE: Record<string, string> = {
    'integrates-with': 'integrates with',
    'built-on': 'is built on',
    'runtime-dependency': 'depends at runtime on',
    extends: 'extends',
    forks: 'forks'
  };
  function evText(e: CompatEvidence): string {
    if (e.kind === 'edge') {
      const stamp = verifiedStamp(e);
      return `${name.get(e.from) ?? e.from} ${EDGE[e.type] ?? e.type} ${name.get(e.to) ?? e.to}${e.text ? `: ${e.text}` : ''}${stamp ? ` (${stamp})` : ''}`;
    }
    return `${name.get(e.in) ?? e.in}'s ${e.cell}: ${e.text}`;
  }
  const LABEL = { documented: 'Documented integration', mentioned: 'Mentioned together', 'not-recorded': 'Not recorded' } as const;

  const EXAMPLES = [
    { label: 'Mem0 + Qdrant + Neo4j', ids: ['mem0--mem0-ai', 'qdrant--qdrant-tech', 'neo4j--neo4j-com'] },
    { label: 'What works with pgvector?', ids: ['pgvector--gh-pgvector-pgvector'] }
  ].filter((e) => e.ids.every((id) => data.options.some((o) => o.id === id)));
</script>

<SeoHead
  title="AI stack compatibility — do these agent tools work together?"
  description="Pick an agent framework, memory layer, vector database or MCP server and see which of them have a documented integration, with the source for each."
  path="/compatibility"
/>

<main class="page">
  <h1>Do these work together?</h1>
  <p class="lede">
    Pick up to six systems, say a framework, a memory layer and a vector store. For every pair you'll see the catalog's
    evidence that they integrate, with its source. Pick a single system to list everything it's documented to work with.
    <strong>Not recorded</strong> means the catalog has no source either way, not that they're incompatible.
  </p>

  <div class="pick">
    <RecordPicker options={data.options} bind:value={adding} label="Add a system" placeholder={ids.length >= 6 ? 'Up to six systems' : 'Type to add a system…'} />
    {#if EXAMPLES.length}
      <p class="ex">
        Try:
        {#each EXAMPLES as e (e.label)}<button type="button" onclick={() => (ids = [...e.ids])}>{e.label}</button>{/each}
      </p>
    {/if}
  </div>

  {#if ids.length}
    <ul class="chips">
      {#each ids as id (id)}
        <li><a href="{base}/systems/{id}">{name.get(id)}</a> <button type="button" aria-label="Remove {name.get(id)}" onclick={() => remove(id)}>×</button></li>
      {/each}
    </ul>
  {/if}

  {#if pairs.length}
    <section>
      <h2>Pairs</h2>
      <ul class="pairs">
        {#each pairs as p (p.a + p.b)}
          <li class="st-{p.status}">
            <div class="head">
              <span class="badge">{LABEL[p.status]}</span>
              <strong>{name.get(p.a)}</strong> + <strong>{name.get(p.b)}</strong>
            </div>
            {#if p.evidence.length}
              <ul class="ev">
                {#each p.evidence as e, i (i)}
                  <li>{evText(e)} {#if e.citation}<a href={e.citation} rel="nofollow noopener">source</a>{/if}</li>
                {/each}
              </ul>
            {:else}
              <p class="none">The catalog has no source saying these integrate. Check both projects' docs, or <a href="{base}/systems/{p.a}">suggest a correction</a> if you know of one.</p>
            {/if}
          </li>
        {/each}
      </ul>
      <p class="meta"><a href="{base}/compare/many?ids={ids.join(',')}">Compare these side by side →</a></p>
    </section>
  {:else if ids.length === 1}
    <section>
      <h2>Documented to work with {name.get(ids[0])} ({worksWith.length})</h2>
      {#if worksWith.length}
        <ul class="pairs">
          {#each worksWith as w (w.other)}
            <li class="st-documented">
              <div class="head"><a href="{base}/systems/{w.other}">{name.get(w.other)}</a> <button class="add" type="button" onclick={() => (ids = [...ids, w.other])}>+ add to check</button></div>
              <ul class="ev">
                {#each w.pair.evidence.slice(0, 2) as e, i (i)}
                  <li>{evText(e)} {#if e.citation}<a href={e.citation} rel="nofollow noopener">source</a>{/if}</li>
                {/each}
              </ul>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="none">No documented integrations in the catalog yet.</p>
      {/if}
    </section>
  {/if}

  <p class="foot">
    Evidence comes from typed edges between records (integrates with, built on, runtime dependency) and from one system's
    backend-storage, adjacent-infrastructure, API, embedding-model, MCP and runtime cells naming the other. Mentions only in
    descriptions or claims count as "mentioned together". Also available as the MCP tool <code>check_compatibility</code>.
  </p>
</main>

<style>
  .page { max-width: 920px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; line-height: 1.55; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  h2 { font-size: 18px; color: #f0f6fc; margin: 24px 0 8px; }
  a { color: #58a6ff; }
  .lede, .foot, .meta { color: #8b949e; }
  .foot { font-size: 12px; }
  .pick { max-width: 520px; }
  .ex { font-size: 13px; color: #8b949e; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .ex button, .add { border: 1px solid #30363d; background: #161b22; color: #c9d1d9; border-radius: 999px; padding: 2px 10px; font: inherit; font-size: 12px; cursor: pointer; }
  .chips { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
  .chips li { border: 1px solid #30363d; border-radius: 999px; padding: 3px 6px 3px 12px; background: #161b22; font-size: 14px; }
  .chips button { background: none; border: none; color: #8b949e; cursor: pointer; font-size: 16px; }
  .pairs { list-style: none; padding: 0; display: grid; gap: 10px; }
  .pairs > li { border: 1px solid #30363d; border-radius: 10px; padding: 10px 14px; background: #0d1117; }
  .pairs > li.st-documented { border-color: #238636; }
  .pairs > li.st-mentioned { border-color: #9e6a03; }
  .head { display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline; }
  .badge { font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; border-radius: 4px; padding: 1px 6px; background: #21262d; }
  .st-documented .badge { background: #12361f; color: #3fb950; }
  .st-mentioned .badge { background: #2b2111; color: #d29922; }
  .ev { margin: 6px 0 0; padding-left: 18px; font-size: 13px; }
  .none { font-size: 13px; color: #8b949e; margin: 6px 0 0; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em; }
</style>
