<script lang="ts">
  // /alternatives — index of every "<System> alternatives" page.
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';

  let { data }: { data: { groups: Record<string, { id: string; name: string; flagged: boolean }[]>; count: number } } = $props();
  let q = $state('');
  const filtered = $derived(
    Object.entries(data.groups).map(
      ([g, xs]) => [g, q ? xs.filter((x) => x.name.toLowerCase().includes(q.toLowerCase())) : xs] as const
    )
  );
</script>

<SeoHead
  title="Alternatives to memory layers, agent frameworks and vector stores"
  description="Find live alternatives to {data.count} AI agent systems — memory layers (Mem0, Zep, Letta…), agent frameworks and retrieval infrastructure — ranked by shared design, licence, hosting and MCP support."
  path="/alternatives"
/>

<main class="page">
  <h1>Alternatives</h1>
  <p class="lede">
    Pick a system to see live options that do the same job, ranked by shared design and must-haves. Systems marked ⚠
    are archived, deprecated, acquired or stale. Prefer to start from requirements? <a href="{base}/choose">Use the chooser</a>.
  </p>
  <input class="search" type="search" placeholder="Filter by name…" bind:value={q} aria-label="Filter systems" />
  {#each filtered as [group, xs] (group)}
    {#if xs.length}
      <section>
        <h2>{group} <span class="count">{xs.length}</span></h2>
        <ul>
          {#each xs as x (x.id)}
            <li><a href="{base}/alternatives/{x.id}">{x.name}</a>{#if x.flagged} <span class="warn" title="archived, deprecated, acquired or stale">⚠</span>{/if}</li>
          {/each}
        </ul>
      </section>
    {/if}
  {/each}
</main>

<style>
  .page { max-width: 1000px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  h2 { font-size: 18px; color: #f0f6fc; margin: 24px 0 8px; }
  .count { color: #6e7681; font-size: 13px; font-weight: 400; }
  .lede { color: #8b949e; line-height: 1.55; }
  .lede a, li a { color: #58a6ff; }
  .search { width: 100%; max-width: 360px; box-sizing: border-box; background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 8px 10px; margin: 8px 0; }
  ul { columns: 3 220px; list-style: none; padding: 0; margin: 0; font-size: 14px; }
  li { break-inside: avoid; margin: 2px 0; }
  .warn { color: #d29922; }
</style>
