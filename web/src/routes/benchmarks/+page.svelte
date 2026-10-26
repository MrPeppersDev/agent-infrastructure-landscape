<script lang="ts">
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';

  type Run = {
    id: string | null; system: string; dataset: string; answer_model: string; judge_model: string; accuracy_macro: number | null;
    accuracy: number | null; abstention_accuracy: number | null; retrieve_ms_p50: number | null; version: string; run_id: string;
    by_type: Record<string, { accuracy: number }>;
  };
  type Rep = { id: string; name: string; family: string; claim: string; citation: string | null; kind: 'vendor' | 'paper' };
  let { data }: { data: { runs: Run[]; reported: Rep[] } } = $props();
  const REPO = 'https://github.com/MrPeppersDev/agent-infrastructure-landscape';

  const groups = $derived.by(() => {
    const g = new Map<string, Run[]>();
    for (const r of data.runs) {
      const k = `${r.dataset} — answer ${r.answer_model}, judge ${r.judge_model}`;
      g.set(k, [...(g.get(k) ?? []), r]);
    }
    return [...g.entries()].map(([k, rs]) => ({ k, rs, types: [...new Set(rs.flatMap((r) => Object.keys(r.by_type)))].sort() }));
  });
  const pct = (x: number | null) => (x == null ? '–' : x <= 1 ? `${(x * 100).toFixed(1)}%` : `${x}`);
  const host = (u: string) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return 'source'; } };
</script>

<SeoHead
  title="AI agent memory benchmarks — LongMemEval and LoCoMo, reproduced vs reported"
  description="Reproducible LongMemEval and LoCoMo runs of Mem0, Zep/Graphiti, Letta, Cognee, Supermemory and baselines with the same model and judge, next to vendor-reported scores labelled as not reproduced."
  path="/benchmarks"
/>

<main class="page">
  <h1>Memory benchmarks</h1>
  <p class="lede">
    Vendors' memory benchmark numbers aren't comparable: each picks its own answer model, judge, prompt and subset, and several
    have publicly disputed each other's results. This page keeps two things apart. First, <strong>our own runs</strong>, where every
    system gets the same data, answer model, judge and retrieval budget. Second, the <strong>scores vendors and papers report</strong>,
    shown with their sources and labelled as not reproduced.
  </p>

  <h2>Reproducible runs</h2>
  {#if groups.length}
    {#each groups as g (g.k)}
      <h3>{g.k}</h3>
      <div class="wrap">
        <table>
          <thead><tr><th>System</th><th class="num">Macro accuracy</th><th class="num">Overall</th>{#each g.types as t (t)}<th class="num">{t}</th>{/each}<th class="num">Abstention</th><th class="num">p50 retrieve</th><th>Version</th></tr></thead>
          <tbody>
            {#each g.rs as r (r.system)}
              <tr>
                <td>{#if r.id}<a href="{base}/systems/{r.id}">{r.system}</a>{:else}{r.system}{/if}</td>
                <td class="num"><strong>{pct(r.accuracy_macro)}</strong></td>
                <td class="num">{pct(r.accuracy)}</td>
                {#each g.types as t (t)}<td class="num">{pct(r.by_type[t]?.accuracy ?? null)}</td>{/each}
                <td class="num">{pct(r.abstention_accuracy)}</td>
                <td class="num">{r.retrieve_ms_p50 ?? '–'} ms</td>
                <td>{r.version}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/each}
  {:else}
    <div class="empty">
      <p><strong>No published runs yet.</strong> The harness is in the repo and tested offline. The first real run needs API keys,
        so it's waiting on the maintainer.</p>
      <ul>
        <li>Datasets: <a href="https://github.com/xiaowu0162/LongMemEval">LongMemEval</a> and <a href="https://github.com/snap-research/locomo">LoCoMo</a>.</li>
        <li>Systems: Mem0, Zep, Graphiti, Letta, Cognee, Supermemory and Honcho, plus full-context, BM25 and embedding-RAG baselines.</li>
        <li>Fixed for every system: answer model, judge model and prompt, top-k retrieval budget, and the same questions.</li>
        <li>Reproduce it yourself: <a href="{REPO}/tree/main/bench">bench/</a> (<code>python -m memory_bench.run</code>). Adapter notes are in <a href="{REPO}/blob/main/bench/ADAPTERS.md">ADAPTERS.md</a>.</li>
      </ul>
    </div>
  {/if}

  <h2>Reported scores (not reproduced) <span class="count">{data.reported.length}</span></h2>
  <p class="note">
    These are copied from vendor pages and papers. Setups differ, so don't rank systems by these numbers. Use them as leads, and check
    the source for the model, judge and subset used.
  </p>
  <div class="wrap">
    <table>
      <thead><tr><th>System</th><th>Who says so</th><th>Claim</th><th>Source</th></tr></thead>
      <tbody>
        {#each data.reported as r (r.id)}
          <tr>
            <td><a href="{base}/systems/{r.id}">{r.name}</a></td>
            <td>{r.kind === 'paper' ? 'paper' : 'vendor'}</td>
            <td class="claim">{r.claim}</td>
            <td>{#if r.citation}<a href={r.citation} rel="nofollow noopener">{host(r.citation)}</a>{/if}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <p class="foot">Related finding: <a href="{base}/findings/no-peer-reviewed-benchmark">most products publish no peer-reviewed benchmark</a>.</p>
</main>

<style>
  .page { max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; line-height: 1.55; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  h2 { font-size: 19px; color: #f0f6fc; margin: 28px 0 8px; }
  h3 { font-size: 14px; color: #8b949e; margin: 16px 0 6px; font-weight: 500; }
  .count { color: #6e7681; font-size: 13px; font-weight: 400; }
  a { color: #58a6ff; }
  .lede, .note, .foot { color: #8b949e; }
  .empty { border: 1px dashed #30363d; border-radius: 10px; padding: 12px 16px; background: #0d1117; }
  .wrap { overflow-x: auto; border: 1px solid #30363d; border-radius: 8px; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { text-align: left; vertical-align: top; padding: 6px 10px; border-bottom: 1px solid #21262d; }
  th { background: #161b22; color: #8b949e; font-weight: 600; }
  .num { text-align: right; white-space: nowrap; }
  .claim { max-width: 520px; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
</style>
