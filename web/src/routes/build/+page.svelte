<script lang="ts">
  // /build — answer once, get a whole agent stack: one cited pick per
  // layer, why-not, exit paths, integrations, risk, OWASP coverage, evals
  // and a stack.yml. Logic: mcp/src/composer.ts (shared with the MCP
  // server's plan_stack and the CLI's `landscape stack`).
  import { base } from '$app/paths';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import '$lib/compat';
  import type { ChooserItem, RecordLike } from '$lib/chooser';
  import { planStack, PRODUCTS, LAYERS, DEFAULT_STACK, type StackAnswers, type LayerId, type ProductType } from '../../../../mcp/src/composer';
  import type { CompatEdge } from '../../../../mcp/src/compat';

  let { data }: { data: { items: ChooserItem[]; records: RecordLike[]; edges: CompatEdge[]; migrations: { id: string; summary: string; sources: string[] }[] } } = $props();

  const OPTIONAL: LayerId[] = ['voice', 'browser', 'sandbox', 'graph', 'orchestration', 'tools', 'memory'];

  function fromParams(p: URLSearchParams): StackAnswers {
    const a: StackAnswers = { ...DEFAULT_STACK };
    const product = p.get('product');
    if (product && product in PRODUCTS) a.product = product as ProductType;
    const lang = p.get('language');
    if (lang === 'python' || lang === 'typescript') a.language = lang;
    const h = p.get('hosting');
    if (h === 'self' || h === 'managed') a.hosting = h;
    a.oss = p.get('oss') === 'true';
    a.mcp = p.get('mcp') === 'true';
    const add = (p.get('add') ?? '').split(',').filter((x) => LAYERS.some((l) => l.id === x)) as LayerId[];
    if (add.length) a.add = add;
    return a;
  }
  function toParams(a: StackAnswers): string {
    const p = new URLSearchParams();
    if (a.product !== DEFAULT_STACK.product) p.set('product', a.product);
    if (a.language !== 'any') p.set('language', a.language);
    if (a.hosting !== 'any') p.set('hosting', a.hosting);
    if (a.oss) p.set('oss', 'true');
    if (a.mcp) p.set('mcp', 'true');
    if (a.add?.length) p.set('add', a.add.join(','));
    return p.toString();
  }

  let answers = $state<StackAnswers>(browser ? fromParams(new URLSearchParams(window.location.search)) : { ...DEFAULT_STACK });
  const ctx = $derived({ items: data.items, records: data.records, edges: data.edges, migrations: new Map(data.migrations.map((m) => [m.id, m])) });
  const plan = $derived(planStack(ctx, { ...answers, add: answers.add?.filter((l) => !PRODUCTS[answers.product].layers.includes(l)) }));

  $effect(() => {
    if (!browser) return;
    const qs = toParams(answers);
    if (window.location.search !== (qs ? `?${qs}` : '')) goto(qs ? `?${qs}` : window.location.pathname, { replaceState: true, noScroll: true, keepFocus: true });
  });

  const extras = $derived(OPTIONAL.filter((l) => !PRODUCTS[answers.product].layers.includes(l)));
  const toggleAdd = (l: LayerId) => {
    const cur = answers.add ?? [];
    answers.add = cur.includes(l) ? cur.filter((x) => x !== l) : [...cur, l];
  };
  const nameOf = $derived(new Map(data.items.map((i) => [i.id, i.name])));
  const documented = $derived(plan.pairs.filter((p) => p.status === 'documented'));
  let copied = $state(false);
  async function copyYaml() {
    try {
      await navigator.clipboard.writeText(plan.stackYaml);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch {
      copied = false;
    }
  }
  const yamlHref = $derived(`data:text/yaml;charset=utf-8,${encodeURIComponent(plan.stackYaml)}`);
  const triLabel = (t: string) => (t === 'yes' ? 'yes' : t === 'no' ? 'no' : 'unknown');
</script>

<SeoHead
  title="Build an AI agent stack — framework, model, memory, vector DB, evals, guardrails"
  description="Answer once and get a whole AI agent stack: one cited pick per layer, why not the runners-up, exit paths, documented integrations, a risk score, OWASP LLM Top 10 coverage and a stack.yml."
  path="/build"
/>

<main class="page">
  <header>
    <h1>Build an agent stack</h1>
    <p class="lede">
      Answer once and get one pick per layer of an AI agent product, from {data.items.length} catalogued systems. Every reason is a
      catalogued fact with its source; later layers prefer systems with a recorded integration with earlier picks. Archived and
      shut-down systems are never picked. A pair with no recorded integration is <em>not recorded</em>, not incompatible.
    </p>
  </header>

  <section class="questions" aria-label="Your product">
    <fieldset>
      <legend>What are you building?</legend>
      <div class="opts">
        {#each Object.entries(PRODUCTS) as [v, p] (v)}
          <label class:on={answers.product === v}><input type="radio" bind:group={answers.product} value={v} />{p.label}</label>
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
        {#each [['any', "Doesn't matter"], ['self', 'All self-hosted (adds model serving)'], ['managed', 'Prefer managed services']] as [v, l] (v)}
          <label class:on={answers.hosting === v}><input type="radio" bind:group={answers.hosting} value={v} />{l}</label>
        {/each}
      </div>
    </fieldset>
    <fieldset>
      <legend>Must-haves</legend>
      <div class="opts">
        <label class:on={answers.oss}><input type="checkbox" bind:checked={answers.oss} />Open-source licences</label>
        <label class:on={answers.mcp}><input type="checkbox" bind:checked={answers.mcp} />MCP support</label>
      </div>
    </fieldset>
    {#if extras.length}
      <fieldset>
        <legend>Also include</legend>
        <div class="opts">
          {#each extras as l (l)}
            <label class:on={answers.add?.includes(l)}><input type="checkbox" checked={answers.add?.includes(l)} onchange={() => toggleAdd(l)} />{LAYERS.find((x) => x.id === l)?.label}</label>
          {/each}
        </div>
      </fieldset>
    {/if}
    <button type="button" class="reset" onclick={() => (answers = { ...DEFAULT_STACK })}>Reset</button>
  </section>

  <section class="summary" aria-live="polite">
    <div class="risk risk-{plan.risk.level}">
      <span class="k">Risk</span> <strong>{plan.risk.level}</strong> <span class="score">({plan.risk.score})</span>
    </div>
    <div><span class="k">Integrations documented</span> <strong>{documented.length}</strong> of {plan.pairs.length} pairs</div>
    <div><span class="k">OWASP risks addressed</span> <strong>{plan.security.items.filter((s) => s.status === 'addressed').length}</strong> of 10</div>
  </section>

  <section class="layers">
    {#each plan.layers as l (l.layer)}
      <article class="layer" class:empty={!l.pick}>
        <header>
          <h2>{l.label}</h2>
          <p class="role">{l.role}</p>
        </header>
        {#if l.pick}
          <p class="pickline">
            <a class="name" href="{base}/systems/{l.pick.item.id}">{l.pick.item.name}</a>
            {#if l.pickUnconfirmed}<span class="tag" title="Every option left has a must-have the catalog can't confirm">unconfirmed</span>{/if}
          </p>
          {#if l.pick.warning}<p class="warn">⚠ {l.pick.warning}</p>{/if}
          <ul class="reasons">
            {#each l.pick.reasons.slice(0, 5) as r (r.text)}
              <li>{r.text}{#if r.citation} <a class="cite" href={r.citation} target="_blank" rel="noopener noreferrer" title="source">↗</a>{/if}</li>
            {/each}
          </ul>
          {#if l.pick.unconfirmed.length}<p class="unconf">Not confirmed in the catalog: {l.pick.unconfirmed.join(', ')}</p>{/if}
          {#if l.whyNot.length}
            <details class="whynot">
              <summary>Why not {l.whyNot.map((w) => w.name).join(', ')}?</summary>
              <ul>
                {#each l.whyNot as w (w.id)}
                  <li>
                    <a href="{base}/systems/{w.id}">{w.name}</a>:
                    {#each w.because as b, i (i)}{i ? '; ' : ''}{b.text}{#if b.citation} <a class="cite" href={b.citation} target="_blank" rel="noopener noreferrer">↗</a>{/if}{/each}
                  </li>
                {/each}
              </ul>
            </details>
          {/if}
          {#if l.exit}
            <p class="exit">
              Exit path: self-host {triLabel(l.exit.selfHost.tri)}, open source {triLabel(l.exit.openSource.tri)}{#if l.exit.fallback}; fallback <a href="{base}/systems/{l.exit.fallback.id}">{l.exit.fallback.name}</a>{/if}{#if l.exit.migration}; <a href={l.exit.migration.sources[0]} target="_blank" rel="noopener noreferrer">migration notes</a>{/if}
            </p>
          {/if}
        {:else}
          <p class="none">Nothing in the catalog meets these requirements for this layer.</p>
        {/if}
      </article>
    {/each}
  </section>

  <section>
    <h2>Do the picks work together?</h2>
    {#if documented.length}
      <ul class="pairs">
        {#each documented as p (p.a + p.b)}
          <li>
            <strong>{nameOf.get(p.a)}</strong> + <strong>{nameOf.get(p.b)}</strong>
            {#if p.evidence[0]}— {p.evidence[0].text}{#if p.evidence[0].citation} <a class="cite" href={p.evidence[0].citation} target="_blank" rel="noopener noreferrer">↗</a>{/if}{/if}
          </li>
        {/each}
      </ul>
    {:else}
      <p class="muted">No documented integrations between these picks yet.</p>
    {/if}
    <p class="meta">
      Check any set on the <a href="{base}/compatibility?ids={plan.layers.filter((l) => l.pick).map((l) => l.pick!.item.id).join(',')}">compatibility page</a>.
    </p>
  </section>

  <section>
    <h2>Risk: {plan.risk.level} ({plan.risk.score})</h2>
    <p class="muted">Only cited facts add points: lifecycle status, several layers from one vendor, low contributor count (OpenDigger), source-available or changed licences, integrations the catalog can't confirm, and layers with no option.</p>
    {#if plan.risk.factors.length}
      <ul class="factors">
        {#each plan.risk.factors as f, i (i)}
          <li><span class="pts">+{f.points}</span> {f.detail}{#if f.citation} <a class="cite" href={f.citation} target="_blank" rel="noopener noreferrer">↗</a>{/if}</li>
        {/each}
      </ul>
    {:else}
      <p>No risk factors recorded.</p>
    {/if}
  </section>

  <section>
    <h2>Security coverage — OWASP Top 10 for LLM applications</h2>
    <p class="muted"><em>Addressed</em> means the stack has a component aimed at the risk, not that it's mitigated. <a href={plan.security.source} target="_blank" rel="noopener noreferrer">OWASP list ↗</a></p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Risk</th><th>Status</th><th>By</th><th>What to do</th></tr></thead>
        <tbody>
          {#each plan.security.items as s (s.id)}
            <tr>
              <td>{s.id} {s.risk}</td>
              <td class="st st-{s.status}">{s.status}</td>
              <td>{s.by.join(', ')}</td>
              <td class="note">{s.note}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Evaluation plan</h2>
    <p>
      {#if plan.evals.observability}Trace and evaluate with <a href="{base}/systems/{plan.evals.observability.id}">{plan.evals.observability.name}</a>.{:else}Add an evals &amp; observability layer.{/if}
      {#if plan.evals.benchmarks.length}
        Benchmarks that fit this product:
        {#each plan.evals.benchmarks as b, i (b.id)}{i ? ', ' : ''}<a href="{base}/systems/{b.id}">{b.name}</a>{/each}.
      {/if}
    </p>
  </section>

  <section>
    <h2>stack.yml</h2>
    <p class="muted">Save this next to your code. <code>npx landscape check stack.yml</code>, the <a href="{base}/check">stack check</a> and the "AI stack check" GitHub Action flag any component that is later archived, acquired or goes stale.</p>
    <pre class="yaml">{plan.stackYaml}</pre>
    <p class="actions">
      <button type="button" onclick={copyYaml}>{copied ? 'Copied' : 'Copy'}</button>
      <a class="dl" href={yamlHref} download="stack.yml">Download</a>
    </p>
  </section>
</main>

<style>
  .page { max-width: 1080px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  h2 { font-size: 18px; color: #f0f6fc; margin: 28px 0 10px; }
  .layer h2 { margin: 0; font-size: 15px; }
  .lede, .muted { color: #8b949e; line-height: 1.55; max-width: 780px; }
  .lede { margin: 0 0 20px; }
  .questions { display: grid; gap: 14px; padding: 16px; border: 1px solid #30363d; border-radius: 10px; background: #0d1117; }
  fieldset { border: 0; margin: 0; padding: 0; }
  legend { font-weight: 600; color: #f0f6fc; margin-bottom: 8px; font-size: 14px; }
  .opts { display: flex; flex-wrap: wrap; gap: 8px; }
  .opts label { border: 1px solid #30363d; border-radius: 999px; padding: 6px 12px; font-size: 13px; cursor: pointer; background: #161b22; }
  .opts label.on { background: #1f6feb; border-color: #1f6feb; color: #fff; }
  .opts input { position: absolute; opacity: 0; width: 1px; height: 1px; }
  .opts label:focus-within { outline: 2px solid #58a6ff; outline-offset: 2px; }
  .reset { justify-self: start; background: none; border: 1px solid #30363d; color: #8b949e; border-radius: 6px; padding: 4px 10px; font: inherit; font-size: 12px; cursor: pointer; }
  .summary { display: flex; flex-wrap: wrap; gap: 10px 28px; margin: 18px 0 6px; font-size: 14px; }
  .summary .k { color: #8b949e; margin-right: 4px; }
  .risk-low strong { color: #3fb950; }
  .risk-medium strong { color: #d29922; }
  .risk-high strong { color: #f85149; }
  .score { color: #6e7681; }
  .layers { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; margin-top: 14px; }
  .layer { border: 1px solid #30363d; border-radius: 10px; padding: 14px; background: #0d1117; min-width: 0; }
  .layer.empty { border-style: dashed; }
  .role { color: #6e7681; font-size: 12px; margin: 2px 0 8px; }
  .pickline { margin: 0; }
  .name { color: #58a6ff; font-weight: 600; font-size: 16px; text-decoration: none; }
  .reasons { margin: 8px 0 0; padding-left: 18px; font-size: 13px; line-height: 1.5; overflow-wrap: anywhere; }
  .cite, .layer a, .pairs a, .factors a, .meta a, .muted a, p a { color: #58a6ff; text-decoration: none; }
  .warn { color: #d29922; font-size: 13px; margin: 6px 0 0; }
  .unconf, .exit { color: #8b949e; font-size: 12px; margin: 8px 0 0; }
  .none { color: #d29922; font-size: 13px; }
  .tag { margin-left: 6px; font-size: 11px; color: #d29922; border: 1px solid #d29922; border-radius: 999px; padding: 0 6px; }
  .whynot { margin-top: 8px; font-size: 12px; color: #8b949e; }
  .whynot summary { cursor: pointer; }
  .whynot ul { padding-left: 18px; margin: 6px 0 0; line-height: 1.5; overflow-wrap: anywhere; }
  .pairs, .factors { padding-left: 18px; font-size: 13px; line-height: 1.6; overflow-wrap: anywhere; }
  .pts { color: #d29922; font-variant-numeric: tabular-nums; }
  .meta { color: #6e7681; font-size: 12px; }
  .table-wrap { overflow-x: auto; border: 1px solid #30363d; border-radius: 8px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { padding: 6px 10px; border-bottom: 1px solid #21262d; text-align: left; vertical-align: top; }
  th { background: #161b22; color: #8b949e; font-weight: 600; }
  td.note { color: #8b949e; min-width: 260px; }
  .st-addressed { color: #3fb950; }
  .st-gap { color: #f85149; }
  .st-practice { color: #d29922; }
  .yaml { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; font-size: 12px; overflow-x: auto; color: #c9d1d9; }
  .actions { display: flex; gap: 10px; align-items: center; }
  .actions button, .dl { background: #21262d; border: 1px solid #30363d; color: #c9d1d9; border-radius: 6px; padding: 5px 12px; font: inherit; font-size: 13px; cursor: pointer; text-decoration: none; }
  code { background: #161b22; padding: 1px 5px; border-radius: 4px; font-size: 12px; }
</style>
