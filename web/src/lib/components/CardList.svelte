<script lang="ts">
  // The catalog on a phone (#335): one card per system instead of the wide
  // table. Name, status, tier, section and a one-line description; the
  // card opens the system page. Shows 40 at a time.
  import { base } from '$app/paths';
  import type { LandscapeRecord } from '$lib/types';
  import { primarySectionOf } from '$lib/families';
  import { LIFECYCLE_LABEL, LIFECYCLE_TONE } from '$lib/lifecycle-labels';

  let { records }: { records: LandscapeRecord[] } = $props();

  const PAGE = 40;
  let shown = $state(PAGE);
  $effect(() => {
    records;
    shown = PAGE;
  });

  function oneLine(html: string | undefined): string {
    const text = (html ?? '').replace(/<[^>]*>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
    return text.length > 140 ? text.slice(0, 138).replace(/\s+\S*$/, '') + '…' : text;
  }
</script>

<ul class="cards">
  {#each records.slice(0, shown) as r (r.id)}
    {@const life = r.lifecycle ?? 'active'}
    {@const desc = r.cells.desc?.status === 'real-data' ? oneLine(r.cells.desc.value) : ''}
    <li>
      <a href="{base}/systems/{r.id}">
        <span class="top">
          <span class="name">{r.name}</span>
          <span class="life {LIFECYCLE_TONE[life]}">{LIFECYCLE_LABEL[life]}</span>
        </span>
        <span class="meta">T{r.tier} · {primarySectionOf(r)}</span>
        {#if desc}<span class="desc">{desc}</span>{/if}
      </a>
    </li>
  {/each}
</ul>
{#if records.length > shown}
  <button type="button" class="more" onclick={() => (shown += PAGE)}>
    Show more ({records.length - shown} left)
  </button>
{:else if records.length === 0}
  <p class="none">No systems match. Clear a filter or the search.</p>
{/if}

<style>
  .cards { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
  .cards a {
    display: block;
    padding: 10px 12px;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    color: #c9d1d9;
    text-decoration: none;
  }
  .cards a:active, .cards a:hover { border-color: #58a6ff; }
  .top { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
  .name { font-weight: 600; color: #d4845f; overflow-wrap: anywhere; }
  .meta { display: block; margin-top: 2px; font-size: 12px; color: #8b949e; }
  .desc { display: block; margin-top: 4px; font-size: 13px; line-height: 1.45; }
  .life { flex: none; padding: 0 6px; border-radius: 3px; border: 1px solid; font-size: 10.5px; font-weight: 600; line-height: 1.6; }
  .life.ok { background: #1f3a26; color: #8fc99a; border-color: #2c5235; }
  .life.info { background: #1f2e3a; color: #8fb3c9; border-color: #2c4253; }
  .life.warn { background: #3a2e1f; color: #d29922; border-color: #5d4720; }
  .life.bad { background: #3a1f1f; color: #f85149; border-color: #5d2a2a; }
  .more { display: block; width: 100%; margin: 10px 0 24px; padding: 10px; font: inherit; color: #c9d1d9; background: #161b22; border: 1px solid #30363d; border-radius: 8px; }
  .none { color: #8b949e; }
</style>
