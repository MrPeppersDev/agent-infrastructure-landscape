<script lang="ts">
  // /costs — what would a managed memory layer or vector store cost for my
  // workload? Published list prices only (data/pricing/memory.json and
  // vector.json); logic in mcp/src/costs.ts and mcp/src/vector-costs.ts.
  // Beyond the largest published plan → "contact sales"; no published rates
  // → "not published".
  import { base } from '$app/paths';
  import { browser } from '$app/environment';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import { estimateAll, DEFAULT_WORKLOAD, type Workload, type VendorPricing } from '../../../../mcp/src/costs';
  import { vectorEstimateAll, DEFAULT_VECTOR_WORKLOAD, type VectorWorkload, type VectorPricing } from '../../../../mcp/src/vector-costs';

  type Pricing<V> = { checked: string; vendors: V[] };
  let { data }: { data: { pricing: Pricing<VendorPricing>; vectorPricing: Pricing<VectorPricing>; ids: Record<string, string | null> } } = $props();

  type Tab = 'memory' | 'vector';
  const params = browser ? new URLSearchParams(location.search) : new URLSearchParams();
  function fromUrl<T extends object>(defaults: T): T {
    const w = { ...defaults } as Record<string, number>;
    for (const k of Object.keys(w)) {
      const v = Number(params.get(k));
      if (params.get(k) !== null && Number.isFinite(v) && v >= 0) w[k] = v;
    }
    return w as T;
  }
  let tab = $state<Tab>(params.get('tab') === 'vector' ? 'vector' : 'memory');
  let w = $state<Workload>(fromUrl(DEFAULT_WORKLOAD));
  let vw = $state<VectorWorkload>(fromUrl(DEFAULT_VECTOR_WORKLOAD));
  $effect(() => {
    const p = new URLSearchParams();
    const [cur, defaults] = tab === 'vector' ? [vw, DEFAULT_VECTOR_WORKLOAD] : [w, DEFAULT_WORKLOAD];
    if (tab === 'vector') p.set('tab', 'vector');
    for (const [k, v] of Object.entries(cur)) if (v !== (defaults as unknown as Record<string, number>)[k]) p.set(k, String(v));
    const qs = p.toString() ? `?${p}` : '';
    if (location.search !== qs) history.replaceState({}, '', `${location.pathname}${qs}`);
  });
  const results = $derived(estimateAll(data.pricing.vendors, w));
  const vresults = $derived(vectorEstimateAll(data.vectorPricing.vendors, vw));
  const usd = (n: number | null) => (n == null ? 'Contact sales' : n === 0 ? '$0' : `$${n >= 100 ? Math.round(n).toLocaleString('en-US') : n.toFixed(2)}`);
  const VFIELDS: { k: keyof VectorWorkload; label: string; step: number; hint: string }[] = [
    { k: 'vectors', label: 'Vectors stored', step: 100000, hint: 'chunks or memories in the index' },
    { k: 'dimensions', label: 'Dimensions', step: 128, hint: '1536 = OpenAI text-embedding-3-small' },
    { k: 'metadataBytes', label: 'Metadata bytes per vector', step: 100, hint: 'text and attributes stored alongside' },
    { k: 'writesPerMonth', label: 'Vectors written per month', step: 10000, hint: 'inserts and updates' },
    { k: 'queriesPerMonth', label: 'Queries per month', step: 100000, hint: 'similarity searches' },
    { k: 'batchSize', label: 'Vectors per write request', step: 10, hint: 'upsert batch size' }
  ];
  const FIELDS: { k: keyof Workload; label: string; step: number; hint: string }[] = [
    { k: 'users', label: 'Monthly active users', step: 100, hint: 'people (or agents) whose memory you keep' },
    { k: 'messagesPerUser', label: 'Messages per user per month', step: 10, hint: 'turns written to memory' },
    { k: 'bytesPerMessage', label: 'Bytes per message', step: 100, hint: '~4 bytes per token; 600 ≈ a short paragraph' },
    { k: 'retrievalsPerMessage', label: 'Memory searches per message', step: 1, hint: 'usually 1' },
    { k: 'agentsPerUser', label: 'Agents per user', step: 1, hint: 'for per-agent pricing (Letta)' }
  ];
</script>

<SeoHead
  title="AI agent memory & vector store cost calculator — Mem0, Zep, Honcho, Pinecone, Turbopuffer, Weaviate"
  description="Estimate the monthly cost of managed agent memory layers and vector stores for your workload, using each vendor's published list prices, with the working and the pricing page for every number."
  path="/costs"
/>

<main class="page">
  <h1>What will memory cost?</h1>
  <p class="lede">
    Enter your workload to see what each managed memory layer or vector store would charge on its <strong>published</strong>
    plans and rates, with the arithmetic and the pricing page behind every number. When your usage is beyond a vendor's
    largest published plan, you'll see "Contact sales"; when a vendor publishes no rates, "Not published". Never a guess.
    Self-hosting the open-source versions costs only your infrastructure, which isn't estimated here.
  </p>

  <div class="tabs" role="tablist">
    <button role="tab" aria-selected={tab === 'memory'} class:on={tab === 'memory'} onclick={() => (tab = 'memory')}>Memory layers</button>
    <button role="tab" aria-selected={tab === 'vector'} class:on={tab === 'vector'} onclick={() => (tab = 'vector')}>Vector stores</button>
  </div>

  {#if tab === 'memory'}
  <form class="w" onsubmit={(e) => e.preventDefault()}>
    {#each FIELDS as f (f.k)}
      <label>
        <span>{f.label}</span>
        <input type="number" min="0" step={f.step} bind:value={w[f.k]} />
        <small>{f.hint}</small>
      </label>
    {/each}
  </form>

  <ol class="res">
    {#each results as r (r.system)}
      <li class:contact={r.monthlyUsd == null}>
        <div class="head">
          <span class="usd">{usd(r.monthlyUsd)}<small>{r.monthlyUsd != null ? '/mo' : ''}</small></span>
          {#if data.ids[r.system]}<a class="name" href="{base}/systems/{data.ids[r.system]}">{r.system}</a>{:else}<span class="name">{r.system}</span>{/if}
          <span class="plan">{r.plan}</span>
        </div>
        <ul class="work">{#each r.working as x (x)}<li>{x}</li>{/each}</ul>
        {#if r.caveat}<p class="cav">{r.caveat}</p>{/if}
        <p class="src"><a href={r.source} rel="nofollow noopener">Pricing page</a> · checked {data.pricing.checked}</p>
      </li>
    {/each}
  </ol>
  {:else}
  <form class="w" onsubmit={(e) => e.preventDefault()}>
    {#each VFIELDS as f (f.k)}
      <label>
        <span>{f.label}</span>
        <input type="number" min="0" step={f.step} bind:value={vw[f.k]} />
        <small>{f.hint}</small>
      </label>
    {/each}
  </form>

  <ol class="res">
    {#each vresults as r (r.system)}
      <li class:contact={r.monthlyUsd == null}>
        <div class="head">
          <span class="usd">{#if r.monthlyUsd == null}Not published{:else}{r.atLeast && r.monthlyUsd > 0 ? 'from ' : ''}{usd(r.monthlyUsd)}<small>/mo</small>{/if}</span>
          {#if data.ids[r.system]}<a class="name" href="{base}/systems/{data.ids[r.system]}">{r.system}</a>{:else}<span class="name">{r.system}</span>{/if}
          <span class="plan">{r.plan}</span>
        </div>
        <ul class="work">{#each r.working as x (x)}<li>{x}</li>{/each}</ul>
        {#if r.caveat}<p class="cav">{r.caveat}</p>{/if}
        <p class="src"><a href={r.source} rel="nofollow noopener">Pricing page</a> · checked {data.vectorPricing.checked}</p>
      </li>
    {/each}
  </ol>
  {/if}

  <p class="foot">
    Estimates assume one memory write per message and about 4 bytes per token. They cover the memory layer's own fees only;
    LLM calls your app makes are extra, and so are LLM calls the layer bills separately. Prices change, so confirm on the vendor's
    page before you commit. Vector-store estimates assume one namespace / collection and 4 bytes per dimension. Missing a vendor,
    or found a price that changed? Edit the <a href="https://github.com/MrPeppersDev/agent-infrastructure-landscape/blob/main/data/pricing/memory.json">memory</a>
    or <a href="https://github.com/MrPeppersDev/agent-infrastructure-landscape/blob/main/data/pricing/vector.json">vector-store</a> pricing file.
    To pick a layer on features first, use the <a href="{base}/choose">chooser</a>.
  </p>
</main>

<style>
  .page { max-width: 900px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; line-height: 1.55; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  a { color: #58a6ff; }
  .lede, .foot { color: #8b949e; }
  .foot { font-size: 12px; margin-top: 20px; }
  .tabs { display: flex; gap: 6px; margin: 0 0 12px; }
  .tabs button { background: #161b22; color: #8b949e; border: 1px solid #30363d; border-radius: 999px; padding: 6px 14px; font: inherit; font-size: 14px; cursor: pointer; }
  .tabs button.on { color: #f0f6fc; border-color: #58a6ff; background: #0d1117; }
  .w { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; padding: 14px; border: 1px solid #30363d; border-radius: 10px; background: #0d1117; }
  .w label { display: grid; gap: 4px; font-size: 13px; min-width: 0; }
  .w span { color: #f0f6fc; font-weight: 600; }
  .w input { width: 100%; min-width: 0; box-sizing: border-box; background: #161b22; color: #f0f6fc; border: 1px solid #30363d; border-radius: 6px; padding: 6px 8px; font: inherit; font-size: 15px; font-variant-numeric: tabular-nums; }
  .w small { color: #6e7681; font-size: 11px; }
  .res { list-style: none; padding: 0; display: grid; gap: 10px; margin-top: 16px; }
  .res > li { border: 1px solid #30363d; border-radius: 10px; padding: 10px 14px; background: #0d1117; }
  .res > li.contact { border-style: dashed; }
  .head { display: flex; flex-wrap: wrap; gap: 10px; align-items: baseline; }
  .usd { font-size: 20px; font-weight: 700; color: #f0f6fc; font-variant-numeric: tabular-nums; min-width: 110px; }
  .usd small { font-size: 12px; color: #8b949e; font-weight: 400; }
  .contact .usd { font-size: 15px; color: #d29922; }
  .name { font-weight: 600; }
  .plan { color: #8b949e; font-size: 13px; }
  .work { margin: 6px 0 0; padding-left: 18px; font-size: 13px; color: #8b949e; }
  .cav { margin: 6px 0 0; font-size: 12px; color: #d29922; }
  .src { margin: 6px 0 0; font-size: 12px; color: #6e7681; }
</style>
