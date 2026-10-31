<script lang="ts">
  // /choose/framework, /choose/data — a few answers in, three cited picks
  // out, plus a comparison table. Same honesty rules as the memory chooser.
  import { base } from '$app/paths';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import ChooserTabs from '$lib/components/ChooserTabs.svelte';
  import CompareBar from '$lib/components/CompareBar.svelte';
  import { clip, type ChooserItem, type Scored, type Tri } from '$lib/chooser';
  import {
    chooseInfra,
    languageTri,
    inNeed,
    infraToParams,
    paramsToInfra,
    DEFAULT_INFRA,
    NEEDS,
    type InfraAnswers,
    type InfraKind
  } from '../../../../../mcp/src/chooser-infra';

  let { data }: { data: { kind: InfraKind; items: ChooserItem[] } } = $props();
  const kind = $derived(data.kind);

  let answers = $state<InfraAnswers>(browser ? paramsToInfra(data.kind, new URLSearchParams(window.location.search)) : { ...DEFAULT_INFRA[data.kind] });
  // Tabs between /choose/framework and /choose/data reuse this component.
  let shownKind = $state(data.kind);
  $effect(() => {
    if (data.kind !== shownKind) {
      shownKind = data.kind;
      answers = { ...DEFAULT_INFRA[data.kind] };
      picked = [];
    }
  });
  const result = $derived(chooseInfra(data.items, answers.kind === data.kind ? answers : DEFAULT_INFRA[data.kind]));

  $effect(() => {
    if (!browser) return;
    const qs = new URLSearchParams(infraToParams(answers)).toString();
    if (window.location.search !== (qs ? `?${qs}` : '')) goto(qs ? `?${qs}` : window.location.pathname, { replaceState: true, noScroll: true, keepFocus: true });
  });

  const TITLE: Record<InfraKind, { h1: string; seo: string; desc: string; lede: string }> = {
    framework: {
      h1: 'Which agent framework should I use?',
      seo: 'Which AI agent framework should I use? — chooser',
      desc: 'Answer a few questions and get three cited agent-framework picks (LangGraph, CrewAI, Mastra, OpenAI Agents SDK, Pydantic AI and more), plus a side-by-side table.',
      lede: 'agent frameworks, orchestration platforms and code sandboxes'
    },
    data: {
      h1: 'Which vector or graph database should I use?',
      seo: 'Which vector database should I use for AI agents? — chooser',
      desc: 'Answer a few questions and get three cited picks among vector databases, knowledge-graph stores and embedding services (Qdrant, pgvector, Weaviate, Milvus, Neo4j and more).',
      lede: 'vector databases, graph stores, search engines and embedding services'
    }
  };
  const t = $derived(TITLE[kind]);
  const triLabel = (x: Tri) => (x === 'yes' ? '✓' : x === 'no' ? '—' : '?');
  const fmt = (n: number | null) => (n == null ? '' : n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n));

  let onlyMatching = $state(true);
  let picked = $state<string[]>([]);
  const togglePick = (id: string) => (picked = picked.includes(id) ? picked.filter((x) => x !== id) : picked.length < 5 ? [...picked, id] : picked);
  const need = $derived(NEEDS[kind].find((n) => n.value === answers.need) ?? NEEDS[kind][0]);
  const fit = $derived(new Map(result.fitIds.map((id, i) => [id, i])));
  const rows = $derived(
    data.items
      .filter((i) => inNeed(i, need) && (!onlyMatching || fit.has(i.id)))
      .sort((a, b) => (fit.get(a.id) ?? 1e6) - (fit.get(b.id) ?? 1e6) || (b.stars ?? 0) - (a.stars ?? 0))
  );
</script>

<SeoHead title={t.seo} description={t.desc} path="/choose/{kind}" />

<main class="page">
  <header>
    <ChooserTabs active={kind} />
    <h1>{t.h1}</h1>
    <p class="lede">
      Answer a few questions and get three picks from {data.items.length} catalogued {t.lede}. Every reason is a catalogued
      fact with its source. Picks are ranked on fit; GitHub stars only break ties. Archived and shut-down systems are left out, and only one product per vendor is recommended. Where
      the catalog can't confirm a must-have, the system goes under <em>might fit</em>.
    </p>
  </header>

  <section class="questions" aria-label="Your requirements">
    <fieldset>
      <legend>What do you need?</legend>
      <div class="opts">
        {#each NEEDS[kind] as o (o.value)}
          <label class:on={answers.need === o.value}><input type="radio" bind:group={answers.need} value={o.value} />{o.label}</label>
        {/each}
      </div>
    </fieldset>
    <fieldset>
      <legend>Language</legend>
      <div class="opts">
        {#each [['any', "Doesn't matter"], ['python', 'Python'], ['typescript', 'TypeScript / JavaScript']] as [v, l] (v)}
          <label class:on={answers.language === v}><input type="radio" bind:group={answers.language} value={v} />{l}</label>
        {/each}
      </div>
    </fieldset>
    <fieldset>
      <legend>Where should it run?</legend>
      <div class="opts">
        {#each [['any', "Doesn't matter"], ['self', 'Self-hosted / on my infra'], ['managed', 'Managed service']] as [v, l] (v)}
          <label class:on={answers.hosting === v}><input type="radio" bind:group={answers.hosting} value={v} />{l}</label>
        {/each}
      </div>
    </fieldset>
    <fieldset>
      <legend>Must-haves</legend>
      <div class="opts">
        <label class:on={answers.oss}><input type="checkbox" bind:checked={answers.oss} />Open-source licence</label>
        <label class:on={answers.mcp}><input type="checkbox" bind:checked={answers.mcp} />MCP support</label>
        {#if kind === 'data'}
          <label class:on={answers.existing} title="Postgres, MongoDB, Elasticsearch/OpenSearch, Redis, Supabase…"><input type="checkbox" bind:checked={answers.existing} />Prefer a database I may already run</label>
        {/if}
      </div>
    </fieldset>
    <button type="button" class="reset" onclick={() => (answers = { ...DEFAULT_INFRA[kind] })}>Reset</button>
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
          <li>{r.text}{#if r.citation} <a class="cite" href={r.citation} target="_blank" rel="noopener noreferrer" title="source">↗</a>{/if}</li>
        {/each}
      </ul>
      {#if s.unconfirmed.length}<p class="unconf">Not confirmed in the catalog: {s.unconfirmed.join(', ')}</p>{/if}
      <p class="more"><a href="{base}/alternatives/{s.item.id}">Alternatives</a> · <a href="{base}/compatibility?ids={s.item.id}">What it works with</a></p>
    </article>
  {/snippet}

  <section class="results" aria-live="polite">
    {#if result.picks.length}
      <h2>Top picks</h2>
      <div class="picks">
        {#each result.picks as s, i (s.item.id)}{@render card(s, i + 1)}{/each}
      </div>
    {:else}
      <p class="none">No catalogued system confirms all of those must-haves. {#if result.unconfirmed.length}The ones below might fit.{:else}Try relaxing a must-have.{/if}</p>
    {/if}
    {#if result.alsoConsider.length}
      <h3>Also consider</h3>
      <ul class="also">
        {#each result.alsoConsider as s (s.item.id)}<li><a href="{base}/systems/{s.item.id}">{s.item.name}</a>{#if s.warning} <span class="warn-inline">⚠ {s.warning}</span>{/if}</li>{/each}
      </ul>
    {/if}
    {#if result.unconfirmed.length}
      <details class="maybe">
        <summary>Might fit — {result.unconfirmed.length} systems where the catalog can't confirm a must-have</summary>
        <div class="maybe-grid">{#each result.unconfirmed as s (s.item.id)}{@render card(s, null)}{/each}</div>
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
            <th class="cmp">Compare</th><th>System</th><th>Self-host</th><th>Managed</th><th>Open source</th><th>MCP</th>
            {#if answers.language !== 'any'}<th>{answers.language === 'python' ? 'Python' : 'TS / JS'}</th>{/if}
            <th class="num">GitHub ★</th><th>Latest release</th><th>Licence</th>
          </tr>
        </thead>
        <tbody>
          {#each rows as i (i.id)}
            <tr class:dim={i.status.severity >= 3}>
              <td class="cmp"><input type="checkbox" checked={picked.includes(i.id)} disabled={!picked.includes(i.id) && picked.length >= 5} onchange={() => togglePick(i.id)} aria-label="Compare {i.name}" /></td>
              <td><a href="{base}/systems/{i.id}">{i.name}</a>{#if i.status.severity >= 2}<span class="tag">{i.status.status}</span>{/if}</td>
              <td class="tri tri-{i.selfHost}" title={i.facts.deployment.value}>{triLabel(i.selfHost)}</td>
              <td class="tri tri-{i.managed}" title={i.facts.deployment.value}>{triLabel(i.managed)}</td>
              <td class="tri tri-{i.oss}" title={i.facts.license.value}>{triLabel(i.oss)}</td>
              <td class="tri tri-{i.mcp}" title={i.facts.mcp.value}>{triLabel(i.mcp)}</td>
              {#if answers.language !== 'any'}{@const l = languageTri(i, answers.language)}<td class="tri tri-{l.tri}" title={l.fact.value}>{triLabel(l.tri)}</td>{/if}
              <td class="num">{fmt(i.stars)}</td>
              <td>{i.releaseDate ?? ''}</td>
              <td class="lic" title={i.facts.license.value}>{clip(i.facts.license.value, 32)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <CompareBar ids={picked} names={data.items} onclear={() => (picked = [])} />
    <p class="meta">✓ confirmed · — no · ? not in the catalog yet. Hover a cell for the catalogued text. Already using some of these? <a href="{base}/check">Check your stack</a>.</p>
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
  .cite, .more a, .also a, .meta a, td a { color: #58a6ff; text-decoration: none; }
  .more { font-size: 12px; margin: 8px 0 0; }
  .warn { color: #d29922; font-size: 13px; margin: 6px 0 0; }
  .warn-inline { color: #d29922; font-size: 12px; }
  .unconf { color: #6e7681; font-size: 12px; margin: 8px 0 0; }
  .none { color: #d29922; }
  .also { display: flex; flex-wrap: wrap; gap: 6px 14px; list-style: none; padding: 0; margin: 0; font-size: 14px; }
  .maybe { margin-top: 18px; font-size: 14px; }
  .maybe summary { cursor: pointer; color: #8b949e; }
  .maybe-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; margin-top: 10px; }
  .meta { color: #6e7681; font-size: 12px; margin-top: 12px; }
  .compare-head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; }
  .compare-head label { font-size: 13px; color: #8b949e; }
  .table-wrap { overflow-x: auto; border: 1px solid #30363d; border-radius: 8px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { padding: 6px 10px; border-bottom: 1px solid #21262d; text-align: left; white-space: nowrap; }
  th { background: #161b22; color: #8b949e; font-weight: 600; }
  td.num, th.num { text-align: right; }
  .cmp { text-align: center; width: 1%; }
  .tri { text-align: center; }
  .tri-yes { color: #3fb950; }
  .tri-no { color: #6e7681; }
  .tri-unknown { color: #d29922; }
  .lic { color: #8b949e; }
  tr.dim td { opacity: 0.5; }
  .tag { margin-left: 6px; font-size: 11px; color: #d29922; border: 1px solid #d29922; border-radius: 999px; padding: 0 6px; }
</style>
