<script lang="ts">
  // /alternatives/[id] — "<System> alternatives". Live systems that do what
  // this one does, ranked by shared memory design + must-haves (logic:
  // mcp/src/chooser.ts → alternatives()). Archived systems and other
  // packagings of the same product are excluded.
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import { clip, type ChooserItem, type Alternative, type Tri } from '$lib/chooser';
  import type { Migration } from '$lib/migrations';

  let { data }: { data: { target: ChooserItem; family: string; alts: (Alternative & { compare: string })[]; migration: Migration | null } } = $props();
  const m = $derived(data.migration);
  const host = (u: string) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return u; } };
  const t = $derived(data.target);
  const dead = $derived(t.status.severity >= 2);
  const tri = (v: Tri) => (v === 'yes' ? '✓' : v === 'no' ? '—' : '?');
  const fmt = (n: number | null) => (n == null ? '' : n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n));
</script>

<SeoHead
  title="{t.name} alternatives — {data.alts.length} live options compared"
  description="Alternatives to {t.name}: {data.alts.slice(0, 4).map((a) => a.name).join(', ')} and more, ranked by shared design (storage, retrieval, conflict handling), licence, hosting and MCP support. From the AI agent infrastructure catalog."
  path="/alternatives/{t.id}"
  ogType="article"
/>

<main class="page">
  <nav class="crumbs"><a href="{base}/alternatives">Alternatives</a> › {data.family}</nav>
  <h1>{t.name} alternatives</h1>

  {#if dead}
    <p class="banner">
      ⚠ <strong>{t.name}</strong> is <strong>{t.status.status}</strong>{t.status.note ? ` — ${t.status.note}` : ''}. These
      are live systems that cover the same ground.
    </p>
  {/if}
  <p class="lede">
    {#if t.desc}{t.desc}{/if}
    <a href="{base}/systems/{t.id}">Full {t.name} record →</a>
  </p>

  {#if m}
    <section class="migrate" id="migrate">
      {#if m.action === 'none'}
        <h2>Nothing to migrate</h2>
        <p>{m.summary}</p>
      {:else}
        <h2>{m.to.length ? 'Official migration path' : 'What the maintainers say'}</h2>
        <p>{m.summary}</p>
        {#if m.to.length}
          <p class="to">
            Move to:
            {#each m.to as t, i (t.name)}{#if t.id}<a href="{base}/systems/{t.id}">{t.name}</a>{:else}<strong>{t.name}</strong>{/if}{i < m.to.length - 1 ? ' or ' : ''}{/each}
          </p>
        {/if}
        {#if m.steps.length}
          <ol class="steps">
            {#each m.steps as s (s)}<li>{s}</li>{/each}
          </ol>
        {/if}
      {/if}
      <p class="src">
        Sources:
        {#each m.sources as u, i (u)}<a href={u} rel="nofollow noopener">{host(u)}</a>{i < m.sources.length - 1 ? ' · ' : ''}{/each}
        · checked {m.verified_at}
      </p>
    </section>
  {/if}

  {#if data.alts.length}
    {#if m}<h2 class="alth">Other live alternatives</h2>{/if}
    <ol class="alts">
      {#each data.alts as a, i (a.id)}
        <li>
          <div class="head">
            <span class="n">{i + 1}</span>
            <a class="name" href="{base}/systems/{a.id}">{a.name}</a>
            <span class="sec">{a.section}</span>
            {#if a.warning}<span class="warn">⚠ {a.warning}</span>{/if}
          </div>
          <p class="why">{a.why.join(' · ')}</p>
          <p class="facts">
            <span title="open source">OSS {tri(a.oss)}</span>
            <span title="self-hostable">Self-host {tri(a.selfHost)}</span>
            <span title="managed service">Managed {tri(a.managed)}</span>
            <span title="MCP support">MCP {tri(a.mcp)}</span>
            {#if a.stars}<span>★ {fmt(a.stars)}</span>{/if}
            {#if a.releaseDate}<span>released {a.releaseDate}</span>{/if}
            {#if a.license}<span class="lic" title={a.license}>{clip(a.license, 48)}</span>{/if}
            <a href="{base}{a.compare}">Compare with {t.name} →</a>
          </p>
        </li>
      {/each}
    </ol>
  {:else}
    <p>No close live alternatives in the catalog yet.</p>
  {/if}

  <p class="foot">
    Ranked by shared memory design (storage, retrieval, conflict handling, memory unit), same section and shared must-haves
    (open source, self-hosting, MCP), with adoption as a tie-breaker. ✓ confirmed · — no · ? not in the catalog yet.
    Want picks for your own requirements? <a href="{base}/choose">Use the chooser</a>. Checking a whole project?
    <a href="{base}/check">Check your stack</a>.
  </p>
</main>

<style>
  .migrate { border: 1px solid #238636; background: #0f1d14; border-radius: 10px; padding: 12px 16px; margin: 16px 0; }
  .migrate h2 { margin: 0 0 6px; font-size: 17px; color: #f0f6fc; }
  .migrate p { margin: 6px 0; line-height: 1.5; }
  .migrate a { color: #58a6ff; }
  .steps { margin: 8px 0; padding-left: 20px; line-height: 1.5; }
  .steps li { margin: 4px 0; }
  .src { font-size: 12px; color: #8b949e; }
  .alth { font-size: 17px; color: #f0f6fc; margin: 20px 0 0; }
  .page { max-width: 900px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; }
  .crumbs { font-size: 12px; color: #6e7681; margin-bottom: 6px; }
  .crumbs a, .lede a, .foot a, .facts a { color: #58a6ff; }
  h1 { margin: 0 0 10px; font-size: 28px; color: #f0f6fc; }
  .banner { border: 1px solid #d29922; background: #2b2111; color: #e3b341; border-radius: 8px; padding: 10px 14px; }
  .lede { color: #8b949e; line-height: 1.55; }
  .alts { list-style: none; padding: 0; display: grid; gap: 10px; margin: 18px 0; }
  .alts li { border: 1px solid #30363d; border-radius: 10px; padding: 12px 14px; background: #0d1117; }
  .head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; }
  .n { background: #21262d; border-radius: 999px; width: 22px; height: 22px; display: inline-grid; place-items: center; font-size: 12px; }
  .name { color: #58a6ff; font-weight: 600; font-size: 16px; }
  .sec { color: #6e7681; font-size: 12px; }
  .warn { color: #d29922; font-size: 12px; }
  .why { margin: 6px 0 0; font-size: 13px; }
  .facts { margin: 6px 0 0; display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: #8b949e; }
  .lic { color: #6e7681; }
  .foot { color: #6e7681; font-size: 12px; line-height: 1.5; }
</style>
