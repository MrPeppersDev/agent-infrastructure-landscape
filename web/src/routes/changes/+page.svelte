<script lang="ts">
  // /changes (#336): the catalog's lifecycle, price, release, funding and
  // licence changes, newest first, grouped by week. The Atom feed at
  // /changes.xml is the machine twin.
  import { base } from '$app/paths';
  import { page } from '$app/state';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import type { ChangeEntry, ChangeType } from './+page.server';
  import { REPO } from '$lib/history';

  let { data }: { data: { entries: ChangeEntry[]; families: { id: string; name: string }[] } } = $props();

  const TYPES: { id: ChangeType; label: string; plural: string }[] = [
    { id: 'acquired', label: 'Acquired', plural: 'acquisitions' },
    { id: 'dead', label: 'Shut down', plural: 'shutdowns' },
    { id: 'deprecated', label: 'Deprecated', plural: 'deprecations' },
    { id: 'archived', label: 'Archived', plural: 'archivals' },
    { id: 'renamed', label: 'Renamed', plural: 'renames' },
    { id: 'lifecycle', label: 'Lifecycle', plural: 'other lifecycle changes' },
    { id: 'price', label: 'Price change', plural: 'price changes' },
    { id: 'release', label: 'Release', plural: 'release updates' },
    { id: 'funding', label: 'Funding', plural: 'funding updates' },
    { id: 'license', label: 'Licence', plural: 'licence changes' },
    { id: 'new', label: 'New system', plural: 'new systems' },
    { id: 'fact', label: 'Fact update', plural: 'other fact updates' }
  ];
  const LABEL = Object.fromEntries(TYPES.map((t) => [t.id, t.label])) as Record<ChangeType, string>;
  const TONE: Partial<Record<ChangeType, string>> = { acquired: 'warn', dead: 'bad', deprecated: 'bad', archived: 'bad', renamed: 'info', lifecycle: 'info', new: 'ok' };

  let types = $state(new Set<ChangeType>());
  let family = $state('');
  const shown = $derived(
    data.entries.filter((e) => (types.size === 0 || types.has(e.type)) && (!family || e.family === family))
  );

  function toggle(t: ChangeType) {
    const next = new Set(types);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    types = next;
  }

  // Monday of the entry's ISO week.
  function weekOf(date: string): string {
    const d = new Date(date + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
    return d.toISOString().slice(0, 10);
  }
  const weeks = $derived.by(() => {
    const out: { week: string; entries: ChangeEntry[] }[] = [];
    for (const e of shown) {
      const w = weekOf(e.date);
      if (out.at(-1)?.week !== w) out.push({ week: w, entries: [] });
      out.at(-1)!.entries.push(e);
    }
    return out;
  });

  // The latest month with changes, counted per type, in a quotable line.
  const month = $derived(data.entries[0]?.date.slice(0, 7) ?? '');
  const monthName = $derived(
    month ? new Date(month + '-01T00:00:00Z').toLocaleString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' }) : ''
  );
  const monthCounts = $derived.by(() => {
    const n = new Map<ChangeType, number>();
    for (const e of data.entries) if (e.date.startsWith(month)) n.set(e.type, (n.get(e.type) ?? 0) + 1);
    return TYPES.filter((t) => n.get(t.id)).map((t) => ({ ...t, n: n.get(t.id)! }));
  });
  const counts = $derived.by(() => {
    const n = new Map<ChangeType, number>();
    for (const e of data.entries) if (!family || e.family === family) n.set(e.type, (n.get(e.type) ?? 0) + 1);
    return n;
  });
</script>

<SeoHead
  title="What changed in the AI agent stack — acquisitions, shutdowns, renames, price changes"
  description="Acquisitions, shutdowns, archivals, renames, price changes, releases and new systems across {page.data.stats.records.toLocaleString('en-US')} AI agent frameworks, models, memory layers and data stores, each with its source."
  path="/changes"
/>

<main class="page">
  <h1>What changed</h1>
  <p class="lede">
    Lifecycle events, price, release, funding and licence changes, and new systems across the catalog, newest first.
    Each entry links to its source and to the pull request that recorded it. Also as a feed:
    <a href="{base}/changes.xml">changes.xml (Atom)</a>, and per system on each system page.
  </p>

  {#if monthCounts.length}
    <section class="month" aria-label="This month">
      <h2>{monthName}</h2>
      <p>
        {#each monthCounts as c, i (c.id)}<strong>{c.n}</strong> {c.n === 1 ? c.label.toLowerCase() : c.plural}{i < monthCounts.length - 2 ? ', ' : i === monthCounts.length - 2 ? ' and ' : '.'}{/each}
      </p>
    </section>
  {/if}

  <div class="filters">
    <div class="chips" role="group" aria-label="Event type">
      {#each TYPES as t (t.id)}
        {#if counts.get(t.id)}
          <button type="button" class:on={types.has(t.id)} aria-pressed={types.has(t.id)} onclick={() => toggle(t.id)}>
            {t.label} <span>{counts.get(t.id)}</span>
          </button>
        {/if}
      {/each}
    </div>
    <label>
      Catalog
      <select bind:value={family}>
        <option value="">All</option>
        {#each data.families as f (f.id)}<option value={f.id}>{f.name}</option>{/each}
      </select>
    </label>
  </div>

  <p class="meta">{shown.length} change{shown.length === 1 ? '' : 's'}</p>

  {#each weeks as w (w.week)}
    <section class="week">
      <h2>Week of {w.week}</h2>
      <ul>
        {#each w.entries as e, i (e.id + e.type + e.date + i)}
          <li>
            <span class="date">{e.date}</span>
            <span class="type {TONE[e.type] ?? ''}">{LABEL[e.type]}</span>
            <a class="name" href="{base}/systems/{e.id}">{e.name}</a>
            <span class="note">{e.note}</span>
            {#if e.source}<a class="src" href={e.source} rel="nofollow noopener">source</a>{/if}
            {#if e.pr}<a class="src" href="{REPO}/pull/{e.pr}">#{e.pr}</a>{/if}
          </li>
        {/each}
      </ul>
    </section>
  {:else}
    <p class="meta">No changes match.</p>
  {/each}
</main>

<style>
  .page { max-width: 920px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; line-height: 1.55; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  h2 { font-size: 16px; color: #f0f6fc; margin: 24px 0 6px; }
  a { color: #58a6ff; }
  .lede, .meta { color: #8b949e; }
  .month { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 4px 16px 8px; margin: 16px 0; }
  .month h2 { margin-top: 10px; }
  .month p { margin: 0 0 6px; }
  .filters { display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: center; margin: 16px 0 4px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .chips button { font: inherit; font-size: 13px; padding: 3px 10px; border-radius: 999px; border: 1px solid #30363d; background: #161b22; color: #c9d1d9; cursor: pointer; }
  .chips button span { color: #8b949e; margin-left: 2px; }
  .chips button.on { border-color: #58a6ff; color: #f0f6fc; background: #1f2e3a; }
  label { font-size: 13px; color: #8b949e; }
  select { margin-left: 6px; font: inherit; color: #c9d1d9; background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 3px 6px; }
  .week ul { list-style: none; padding: 0; margin: 0; }
  .week li { padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 14px; }
  .date { color: #8b949e; font-variant-numeric: tabular-nums; margin-right: 6px; }
  .type { display: inline-block; font-size: 11px; padding: 0 6px; border-radius: 3px; border: 1px solid #30363d; color: #8b949e; margin-right: 6px; }
  .type.ok { color: #8fc99a; border-color: #2c5235; background: #1f3a26; }
  .type.info { color: #8fb3c9; border-color: #2c4253; background: #1f2e3a; }
  .type.warn { color: #d29922; border-color: #5d4720; background: #3a2e1f; }
  .type.bad { color: #f85149; border-color: #5d2a2a; background: #3a1f1f; }
  .name { font-weight: 600; margin-right: 6px; }
  .note { color: #c9d1d9; }
  .src { font-size: 12px; margin-left: 6px; color: #8b949e; }
</style>
