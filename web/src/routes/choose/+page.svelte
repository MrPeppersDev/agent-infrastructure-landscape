<script lang="ts">
  // /choose — "Which memory layer should I use?" A few answers in, three
  // cited picks out, plus a side-by-side table of the whole pool. Logic in
  // $lib/chooser.ts. Answers sync to the URL so a result is shareable.

  import { base } from '$app/paths';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import ChooserTabs from '$lib/components/ChooserTabs.svelte';
  import CompareBar from '$lib/components/CompareBar.svelte';
  import {
    choose,
    clip,
    answersToParams,
    paramsToAnswers,
    DEFAULT_ANSWERS,
    POOLS,
    type Answers,
    type ChooserItem,
    type Scored,
    type Tri
  } from '$lib/chooser';

  let { data }: { data: { items: ChooserItem[] } } = $props();

  let answers = $state<Answers>(browser ? paramsToAnswers(new URLSearchParams(window.location.search)) : { ...DEFAULT_ANSWERS });

  const result = $derived(choose(data.items, answers));

  $effect(() => {
    if (!browser) return;
    const qs = new URLSearchParams(answersToParams(answers)).toString();
    const target = qs ? `?${qs}` : window.location.pathname;
    if (window.location.search !== (qs ? `?${qs}` : '')) {
      goto(target, { replaceState: true, noScroll: true, keepFocus: true });
    }
  });

  type Opt<T> = { value: T; label: string; hint?: string };
  const Q_BUILDING: Opt<Answers['building']>[] = [
    { value: 'app', label: 'An app or agent that remembers its users' },
    { value: 'coding', label: 'A coding agent or developer tool' }
  ];
  const Q_HOSTING: Opt<Answers['hosting']>[] = [
    { value: 'any', label: "Doesn't matter" },
    { value: 'self', label: 'Self-hosted / on my infra' },
    { value: 'managed', label: 'Managed service' }
  ];
  const Q_CONFLICT: Opt<Answers['conflict']>[] = [
    { value: 'any', label: "Doesn't matter" },
    { value: 'history', label: 'Keep history', hint: 'old facts invalidated, not deleted (bi-temporal / versioned)' },
    { value: 'latest', label: 'Latest wins', hint: 'new value overwrites the old' },
    { value: 'llm', label: 'Let an LLM decide', hint: 'add / update / delete chosen by a model' }
  ];
  const Q_SHAPE: Opt<Answers['shape']>[] = [
    { value: 'any', label: "Doesn't matter" },
    { value: 'facts', label: 'User facts & preferences' },
    { value: 'conversations', label: 'Conversation history' },
    { value: 'documents', label: 'Documents & knowledge' },
    { value: 'relationships', label: 'Relationships (graph)' }
  ];

  // ---- comparison table ---------------------------------------------------
  type SortKey = 'fit' | 'name' | 'stars' | 'release' | 'tier';
  let sortKey = $state<SortKey>('fit');
  let sortDir = $state<1 | -1>(-1);
  let onlyMatching = $state(true);
  let picked = $state<string[]>([]);
  const togglePick = (id: string) => (picked = picked.includes(id) ? picked.filter((x) => x !== id) : picked.length < 5 ? [...picked, id] : picked);

  const matchIds = $derived(new Set(result.fitIds));
  const fitRank = $derived(new Map(result.fitIds.map((id, i) => [id, i])));
  const tableRows = $derived.by(() => {
    const pool = data.items.filter((i) => POOLS[answers.building].includes(i.section) && (!onlyMatching || matchIds.has(i.id)));
    const val = (i: ChooserItem): string | number =>
      sortKey === 'fit' ? -(fitRank.get(i.id) ?? 1e6) : sortKey === 'name' ? i.name.toLowerCase() : sortKey === 'stars' ? i.stars ?? -1 : sortKey === 'release' ? i.releaseDate ?? '' : -i.tier;
    return [...pool].sort((a, b) => {
      const x = val(a), y = val(b);
      return (x < y ? -1 : x > y ? 1 : 0) * sortDir;
    });
  });
  function sortBy(k: SortKey) {
    if (sortKey === k) sortDir = sortDir === 1 ? -1 : 1;
    else {
      sortKey = k;
      sortDir = k === 'name' ? 1 : -1;
    }
  }
  const triLabel = (t: Tri) => (t === 'yes' ? '✓' : t === 'no' ? '—' : '?');

  function fmtStars(n: number | null) {
    return n == null ? '' : n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n);
  }
</script>

<SeoHead
  title="Which AI agent memory layer should I use? — chooser"
  description="Answer a few questions about what you're building and get three cited memory-layer recommendations (Mem0, Zep/Graphiti, Letta, Cognee, Supermemory and more), plus a side-by-side comparison."
  path="/choose"
/>

<main class="page">
  <header>
    <ChooserTabs active="memory" />
    <h1>Which memory layer should I use?</h1>
    <p class="lede">
      Answer a few questions and get three picks from {data.items.length} catalogued memory systems. Every reason is a
      catalogued fact with its source. Picks are ranked on fit; GitHub stars only break ties. Archived and shut-down systems are left out. Where the catalog can't confirm a
      requirement, the system goes under <em>might fit</em> instead of being recommended.
    </p>
  </header>

  <section class="questions" aria-label="Your requirements">
    <fieldset>
      <legend>What are you building?</legend>
      <div class="opts">
        {#each Q_BUILDING as o (o.value)}
          <label class:on={answers.building === o.value}><input type="radio" bind:group={answers.building} value={o.value} />{o.label}</label>
        {/each}
      </div>
    </fieldset>
    <fieldset>
      <legend>Where should it run?</legend>
      <div class="opts">
        {#each Q_HOSTING as o (o.value)}
          <label class:on={answers.hosting === o.value}><input type="radio" bind:group={answers.hosting} value={o.value} />{o.label}</label>
        {/each}
      </div>
    </fieldset>
    <fieldset>
      <legend>When a fact changes ("I moved to Hong Kong"), what should memory do?</legend>
      <div class="opts">
        {#each Q_CONFLICT as o (o.value)}
          <label class:on={answers.conflict === o.value} title={o.hint}><input type="radio" bind:group={answers.conflict} value={o.value} />{o.label}</label>
        {/each}
      </div>
    </fieldset>
    <fieldset>
      <legend>What will it mostly remember?</legend>
      <div class="opts">
        {#each Q_SHAPE as o (o.value)}
          <label class:on={answers.shape === o.value}><input type="radio" bind:group={answers.shape} value={o.value} />{o.label}</label>
        {/each}
      </div>
    </fieldset>
    <fieldset>
      <legend>Must-haves</legend>
      <div class="opts">
        <label class:on={answers.oss}><input type="checkbox" bind:checked={answers.oss} />Open-source licence</label>
        <label class:on={answers.mcp}><input type="checkbox" bind:checked={answers.mcp} />MCP support</label>
      </div>
    </fieldset>
    <button type="button" class="reset" onclick={() => (answers = { ...DEFAULT_ANSWERS })}>Reset</button>
  </section>

  {#snippet card(s: Scored, rank: number | null)}
    <article class="card" class:pick={rank !== null}>
      <header class="card-head">
        {#if rank !== null}<span class="rank">{rank}</span>{/if}
        <a class="name" href="{base}/systems/{s.item.id}">{s.item.name}</a>
        <span class="section">{s.item.section}</span>
      </header>
      {#if s.warning}<p class="warn">⚠ {s.warning}</p>{/if}
      {#if s.item.desc}<p class="desc">{s.item.desc}</p>{/if}
      <ul class="reasons">
        {#each s.reasons as r (r.text)}
          <li>
            {r.text}
            {#if r.citation}<a class="cite" href={r.citation} target="_blank" rel="noopener noreferrer" title="source">↗</a>{/if}
          </li>
        {/each}
      </ul>
      {#if s.unconfirmed.length}
        <p class="unconf">Not confirmed in the catalog: {s.unconfirmed.join(', ')}</p>
      {/if}
    </article>
  {/snippet}

  <section class="results" aria-live="polite">
    {#if result.picks.length}
      <h2>Top picks</h2>
      <div class="picks">
        {#each result.picks as s, i (s.item.id)}
          {@render card(s, i + 1)}
        {/each}
      </div>
    {:else}
      <p class="none">
        No catalogued system confirms all of those must-haves.
        {#if result.unconfirmed.length}The ones below might fit; the catalog just can't confirm every requirement.{:else}Try relaxing a must-have.{/if}
      </p>
    {/if}

    {#if result.alsoConsider.length}
      <h3>Also consider</h3>
      <ul class="also">
        {#each result.alsoConsider as s (s.item.id)}
          <li><a href="{base}/systems/{s.item.id}">{s.item.name}</a>{#if s.warning} <span class="warn-inline">⚠ {s.warning}</span>{/if}</li>
        {/each}
      </ul>
    {/if}

    {#if result.unconfirmed.length}
      <details class="maybe">
        <summary>Might fit — {result.unconfirmed.length} systems where the catalog can't confirm a must-have</summary>
        <div class="maybe-grid">
          {#each result.unconfirmed as s (s.item.id)}
            {@render card(s, null)}
          {/each}
        </div>
        <p class="hint">Know the missing fact for one of these? Open its page from the name and suggest a correction via <a href="{base}/submit">the submit form</a>.</p>
      </details>
    {/if}
    <p class="meta">{result.poolSize} systems considered · {result.excludedCount} ruled out by your must-haves or because they're archived / shut down.</p>
  </section>

  <section class="compare">
    <div class="compare-head">
      <h2>Compare side by side</h2>
      <label><input type="checkbox" bind:checked={onlyMatching} /> Only systems that fit my answers</label>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="cmp" title="Tick up to five to compare">Compare</th>
            <th><button type="button" onclick={() => sortBy('fit')} title="Sort by how well it fits your answers">Fit</button> · <button type="button" onclick={() => sortBy('name')}>System</button></th>
            <th>Self-host</th>
            <th>Managed</th>
            <th>Open source</th>
            <th>MCP</th>
            <th>Conflict handling</th>
            <th>Memory model</th>
            <th class="num"><button type="button" onclick={() => sortBy('stars')}>GitHub ★</button></th>
            <th><button type="button" onclick={() => sortBy('release')}>Latest release</button></th>
            <th>Licence</th>
          </tr>
        </thead>
        <tbody>
          {#each tableRows as i (i.id)}
            <tr class:dim={i.status.severity >= 3}>
              <td class="cmp"><input type="checkbox" checked={picked.includes(i.id)} disabled={!picked.includes(i.id) && picked.length >= 5} onchange={() => togglePick(i.id)} aria-label="Compare {i.name}" /></td>
              <td><a href="{base}/systems/{i.id}">{i.name}</a>{#if i.status.severity >= 2}<span class="tag">{i.status.status}</span>{/if}</td>
              <td class="tri tri-{i.selfHost}" title={i.facts.deployment.value}>{triLabel(i.selfHost)}</td>
              <td class="tri tri-{i.managed}" title={i.facts.deployment.value}>{triLabel(i.managed)}</td>
              <td class="tri tri-{i.oss}" title={i.facts.license.value}>{triLabel(i.oss)}</td>
              <td class="tri tri-{i.mcp}" title={i.facts.mcp.value}>{triLabel(i.mcp)}</td>
              <td>{i.conflict.join(', ')}</td>
              <td>{[...new Set([...i.storage, ...i.unit])].slice(0, 3).join(', ')}</td>
              <td class="num">{fmtStars(i.stars)}</td>
              <td>{i.releaseDate ?? ''}</td>
              <td class="lic" title={i.facts.license.value}>{clip(i.facts.license.value, 32)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <CompareBar ids={picked} names={data.items} onclear={() => (picked = [])} />
    <p class="meta">✓ confirmed · — no · ? not in the catalog yet. Hover a cell for the catalogued text. Already using some of these? <a href="{base}/check">Check your stack</a> for archived or acquired dependencies.</p>
  </section>
</main>

<style>
  .page { max-width: 1080px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  h2 { font-size: 20px; color: #f0f6fc; margin: 28px 0 12px; }
  h3 { font-size: 15px; color: #f0f6fc; margin: 20px 0 8px; }
  .lede { color: #8b949e; line-height: 1.55; margin: 0 0 20px; max-width: 760px; }
  .questions { display: grid; gap: 14px; padding: 16px; border: 1px solid #30363d; border-radius: 10px; background: #0d1117; }
  fieldset { border: 0; margin: 0; padding: 0; }
  legend { font-weight: 600; color: #f0f6fc; margin-bottom: 8px; font-size: 14px; }
  .opts { display: flex; flex-wrap: wrap; gap: 8px; }
  .opts label { border: 1px solid #30363d; border-radius: 999px; padding: 6px 12px; font-size: 13px; cursor: pointer; background: #161b22; }
  .opts label.on { background: #1f6feb; border-color: #1f6feb; color: #fff; }
  .opts input { position: absolute; opacity: 0; width: 1px; height: 1px; }
  .opts label:focus-within { outline: 2px solid #58a6ff; outline-offset: 2px; }
  .reset { justify-self: start; background: none; border: 1px solid #30363d; color: #8b949e; border-radius: 6px; padding: 4px 10px; font: inherit; font-size: 12px; cursor: pointer; }
  .picks { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
  .card { border: 1px solid #30363d; border-radius: 10px; padding: 14px; background: #0d1117; }
  .card.pick { border-color: #1f6feb; }
  .card-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; }
  .rank { background: #1f6feb; color: #fff; border-radius: 999px; width: 22px; height: 22px; display: inline-grid; place-items: center; font-size: 12px; font-weight: 700; }
  .name { color: #58a6ff; font-weight: 600; font-size: 16px; }
  .section { color: #6e7681; font-size: 12px; }
  .desc { color: #8b949e; font-size: 13px; line-height: 1.5; margin: 8px 0; }
  .reasons { margin: 8px 0 0; padding-left: 18px; font-size: 13px; line-height: 1.5; }
  .reasons li { margin: 2px 0; }
  .cite { color: #58a6ff; text-decoration: none; margin-left: 2px; }
  .warn { color: #d29922; font-size: 13px; margin: 6px 0 0; }
  .warn-inline { color: #d29922; font-size: 12px; }
  .unconf { color: #6e7681; font-size: 12px; margin: 8px 0 0; }
  .none { color: #d29922; }
  .also { display: flex; flex-wrap: wrap; gap: 6px 14px; list-style: none; padding: 0; margin: 0; font-size: 14px; }
  .also a, .meta a, .hint a, td a { color: #58a6ff; }
  .maybe { margin-top: 18px; font-size: 14px; }
  .maybe summary { cursor: pointer; color: #8b949e; }
  .maybe-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; margin-top: 10px; }
  .meta, .hint { color: #6e7681; font-size: 12px; margin-top: 12px; }
  .compare-head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; }
  .compare-head label { font-size: 13px; color: #8b949e; }
  .table-wrap { overflow-x: auto; border: 1px solid #30363d; border-radius: 8px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { padding: 6px 10px; border-bottom: 1px solid #21262d; text-align: left; white-space: nowrap; }
  th { background: #161b22; color: #8b949e; font-weight: 600; position: sticky; top: 0; }
  th button { background: none; border: 0; color: inherit; font: inherit; cursor: pointer; padding: 0; text-decoration: underline dotted; }
  td.num, th.num { text-align: right; }
  .tri { text-align: center; }
  .tri-yes { color: #3fb950; }
  .tri-no { color: #6e7681; }
  .tri-unknown { color: #d29922; }
  .lic { color: #8b949e; }
  tr.dim td { opacity: 0.5; }
  .cmp { text-align: center; width: 1%; }
  .tag { margin-left: 6px; font-size: 11px; color: #d29922; border: 1px solid #d29922; border-radius: 999px; padding: 0 6px; }
</style>
