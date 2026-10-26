<script lang="ts">
  // /costs — what would a managed memory layer cost for my workload?
  // Published list prices only (data/pricing/memory.json); logic in
  // mcp/src/costs.ts. Beyond the largest published plan → "contact sales".
  import { base } from '$app/paths';
  import { browser } from '$app/environment';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import { estimateAll, DEFAULT_WORKLOAD, type Workload, type VendorPricing } from '../../../../mcp/src/costs';

  let { data }: { data: { pricing: { checked: string; vendors: VendorPricing[] }; ids: Record<string, string | null> } } = $props();

  function fromUrl(): Workload {
    const w = { ...DEFAULT_WORKLOAD };
    if (!browser) return w;
    const p = new URLSearchParams(location.search);
    for (const k of Object.keys(w) as (keyof Workload)[]) {
      const v = Number(p.get(k));
      if (p.get(k) !== null && Number.isFinite(v) && v >= 0) w[k] = v;
    }
    return w;
  }
  let w = $state<Workload>(fromUrl());
  $effect(() => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(w)) if (v !== (DEFAULT_WORKLOAD as unknown as Record<string, number>)[k]) p.set(k, String(v));
    const qs = p.toString() ? `?${p}` : '';
    if (location.search !== qs) history.replaceState({}, '', `${location.pathname}${qs}`);
  });
  const results = $derived(estimateAll(data.pricing.vendors, w));
  const usd = (n: number | null) => (n == null ? 'Contact sales' : n === 0 ? '$0' : `$${n >= 100 ? Math.round(n).toLocaleString('en-US') : n.toFixed(2)}`);
  const FIELDS: { k: keyof Workload; label: string; step: number; hint: string }[] = [
    { k: 'users', label: 'Monthly active users', step: 100, hint: 'people (or agents) whose memory you keep' },
    { k: 'messagesPerUser', label: 'Messages per user per month', step: 10, hint: 'turns written to memory' },
    { k: 'bytesPerMessage', label: 'Bytes per message', step: 100, hint: '~4 bytes per token; 600 ≈ a short paragraph' },
    { k: 'retrievalsPerMessage', label: 'Memory searches per message', step: 1, hint: 'usually 1' },
    { k: 'agentsPerUser', label: 'Agents per user', step: 1, hint: 'for per-agent pricing (Letta)' }
  ];
</script>

<SeoHead
  title="AI agent memory cost calculator — Mem0, Zep, Supermemory, Cognee, Letta"
  description="Estimate the monthly cost of managed agent memory layers for your workload, using each vendor's published list prices, with the working and the pricing page for every number."
  path="/costs"
/>

<main class="page">
  <h1>What will memory cost?</h1>
  <p class="lede">
    Enter your workload to see what each managed memory layer would charge on its <strong>published</strong> plans, with the
    arithmetic and the pricing page behind every number. Prices were checked on {data.pricing.checked}. When your usage is
    beyond a vendor's largest published plan, you'll see "Contact sales" instead of a guess. Self-hosting the open-source
    versions costs only your infrastructure, which isn't estimated here.
  </p>

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

  <p class="foot">
    Estimates assume one memory write per message and about 4 bytes per token. They cover the memory layer's own fees only;
    LLM calls your app makes are extra, and so are LLM calls the layer bills separately. Prices change, so confirm on the vendor's
    page before you commit. Missing a vendor, or found a price that changed? <a href="https://github.com/MrPeppersDev/agent-infrastructure-landscape/blob/main/data/pricing/memory.json">Edit the pricing file</a>.
    To pick a layer on features first, use the <a href="{base}/choose">chooser</a>.
  </p>
</main>

<style>
  .page { max-width: 900px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; line-height: 1.55; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  a { color: #58a6ff; }
  .lede, .foot { color: #8b949e; }
  .foot { font-size: 12px; margin-top: 20px; }
  .w { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; padding: 14px; border: 1px solid #30363d; border-radius: 10px; background: #0d1117; }
  .w label { display: grid; gap: 4px; font-size: 13px; }
  .w span { color: #f0f6fc; font-weight: 600; }
  .w input { background: #161b22; color: #f0f6fc; border: 1px solid #30363d; border-radius: 6px; padding: 6px 8px; font: inherit; font-size: 15px; font-variant-numeric: tabular-nums; }
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
