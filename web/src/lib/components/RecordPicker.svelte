<script lang="ts">
  // Searchable single-record picker for the client-side compare route
  // (refs #134). A filterable text input with a bounded results dropdown —
  // NOT a 528-option <select>. Emits the selected record id via the
  // bindable `value` prop.

  type Option = { id: string; name: string; section: string | null };

  let {
    options,
    value = $bindable(''),
    label,
    placeholder = 'Type to search systems…'
  }: {
    options: Option[];
    value?: string;
    label: string;
    placeholder?: string;
  } = $props();

  let query = $state('');
  let open = $state(false);
  let root: HTMLElement | undefined = $state();

  const selected = $derived(options.find((o) => o.id === value) ?? null);

  const MAX_RESULTS = 15;
  const matches = $derived.by(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options.slice(0, MAX_RESULTS);
    // Name-prefix matches first, then substring on name/id/section.
    const starts: Option[] = [];
    const rest: Option[] = [];
    for (const o of options) {
      const name = o.name.toLowerCase();
      if (name.startsWith(q)) starts.push(o);
      else if (
        name.includes(q) ||
        o.id.toLowerCase().includes(q) ||
        (o.section?.toLowerCase().includes(q) ?? false)
      ) {
        rest.push(o);
      }
      if (starts.length >= MAX_RESULTS) break;
    }
    return [...starts, ...rest].slice(0, MAX_RESULTS);
  });

  function pick(o: Option) {
    value = o.id;
    query = '';
    open = false;
  }

  function clear() {
    value = '';
    query = '';
    open = true;
  }

  // Close the dropdown on outside clicks.
  function onDocClick(e: MouseEvent) {
    if (root && !root.contains(e.target as Node)) open = false;
  }
</script>

<svelte:document onclick={onDocClick} />

<div class="picker-field" bind:this={root}>
  <span class="picker-label" id="label-{label.replace(/\s+/g, '-')}">{label}</span>
  {#if selected}
    <div class="chosen">
      <span class="chosen-name" title={selected.id}>{selected.name}</span>
      <button type="button" class="change" onclick={clear}>change</button>
    </div>
  {:else}
    <input
      type="search"
      {placeholder}
      bind:value={query}
      onfocus={() => (open = true)}
      oninput={() => (open = true)}
      aria-labelledby="label-{label.replace(/\s+/g, '-')}"
      autocomplete="off" />
    {#if open}
      <ul class="results" role="listbox">
        {#each matches as o (o.id)}
          <li>
            <button type="button" role="option" aria-selected="false" onclick={() => pick(o)}>
              <span class="name">{o.name}</span>
              {#if o.section}<span class="section">{o.section}</span>{/if}
            </button>
          </li>
        {:else}
          <li class="empty">No systems match “{query.trim()}”.</li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>

<style>
  .picker-field {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 260px;
    flex: 1;
  }
  .picker-label {
    font-size: 0.8rem;
    color: #aaa;
    letter-spacing: 0.01em;
  }
  input {
    background: #181818;
    color: #e8e8e8;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 0.92rem;
    font-family: inherit;
  }
  input:focus {
    outline: none;
    border-color: #4a4a4a;
    background: #1c1c1c;
  }
  .chosen {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    background: #181818;
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 0.92rem;
  }
  .chosen-name {
    color: #e8e8e8;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .change {
    background: none;
    border: none;
    color: #d4845f;
    font-size: 0.8rem;
    font-family: inherit;
    cursor: pointer;
    padding: 0;
    flex-shrink: 0;
  }
  .change:hover {
    text-decoration: underline;
  }
  .results {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 20;
    margin: 4px 0 0;
    padding: 4px;
    list-style: none;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 6px;
    max-height: 320px;
    overflow-y: auto;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  }
  .results li {
    margin: 0;
  }
  .results button {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 1px;
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    border-radius: 4px;
    padding: 6px 8px;
    cursor: pointer;
    font-family: inherit;
  }
  .results button:hover {
    background: #262626;
  }
  .results .name {
    color: #e8e8e8;
    font-size: 0.9rem;
  }
  .results .section {
    color: #888;
    font-size: 0.75rem;
  }
  .empty {
    color: #888;
    font-size: 0.85rem;
    font-style: italic;
    padding: 6px 8px;
  }
</style>
