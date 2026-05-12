<script lang="ts">
  import { onMount } from 'svelte';
  import { searchQuery } from '$lib/stores/search';

  let {
    matchCount,
    totalCount
  }: { matchCount: number; totalCount: number } = $props();

  let inputEl: HTMLInputElement | null = $state(null);

  const hasQuery = $derived($searchQuery.trim().length > 0);
  const zeroMatches = $derived(hasQuery && matchCount === 0);

  function clear() {
    $searchQuery = '';
    inputEl?.focus();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && hasQuery) {
      e.preventDefault();
      clear();
    }
  }

  // Global "/" focuses the box, like GitHub / Slack / etc. Ignored when the
  // user is already typing in another input/textarea or has a modifier held.
  function handleGlobalKeydown(e: KeyboardEvent) {
    if (e.key !== '/') return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const t = e.target as HTMLElement | null;
    const tag = t?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || t?.isContentEditable) return;
    e.preventDefault();
    inputEl?.focus();
    inputEl?.select();
  }

  onMount(() => {
    window.addEventListener('keydown', handleGlobalKeydown);
    return () => window.removeEventListener('keydown', handleGlobalKeydown);
  });
</script>

<div class="search-box">
  <div class="input-wrap" class:zero={zeroMatches}>
    <input
      bind:this={inputEl}
      bind:value={$searchQuery}
      onkeydown={handleKeydown}
      type="search"
      placeholder="Search systems (press / to focus)"
      aria-label="Search systems by name, description, or claims"
      spellcheck="false"
      autocomplete="off"
    />
    {#if hasQuery}
      <button type="button" class="clear-btn" onclick={clear} aria-label="Clear search">
        Esc
      </button>
    {/if}
  </div>

  {#if hasQuery}
    <div class="status" aria-live="polite">
      {#if zeroMatches}
        <span class="zero-text">No matches.</span>
        <button type="button" class="clear-link" onclick={clear}>Clear search</button>
      {:else}
        <span class="count">
          <strong>{matchCount.toLocaleString()}</strong> of {totalCount.toLocaleString()} systems match
        </span>
      {/if}
    </div>
  {/if}
</div>

<style>
  .search-box {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .input-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }
  input[type='search'] {
    width: 320px;
    max-width: 100%;
    padding: 6px 10px;
    padding-right: 44px;
    font: inherit;
    font-size: 0.9rem;
    color: #c9d1d9;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    outline: none;
    transition: border-color 120ms ease, box-shadow 120ms ease;
  }
  input[type='search']::placeholder {
    color: #6e7681;
  }
  input[type='search']:focus {
    border-color: #58a6ff;
    box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.25);
  }
  .input-wrap.zero input[type='search'] {
    border-color: #da3633;
  }
  /* Hide the native clear "X" in WebKit; we render our own affordance. */
  input[type='search']::-webkit-search-cancel-button {
    -webkit-appearance: none;
    appearance: none;
  }
  .clear-btn {
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    padding: 1px 6px;
    font-size: 0.7rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    color: #8b949e;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    cursor: pointer;
    line-height: 1.4;
  }
  .clear-btn:hover {
    color: #c9d1d9;
    border-color: #58a6ff;
  }
  .status {
    font-size: 0.8rem;
    color: #8b949e;
    font-variant-numeric: tabular-nums;
  }
  .count strong {
    color: #c9d1d9;
    font-weight: 600;
  }
  .zero-text {
    color: #f85149;
    margin-right: 6px;
  }
  .clear-link {
    background: none;
    border: none;
    padding: 0;
    color: #58a6ff;
    font: inherit;
    font-size: 0.8rem;
    cursor: pointer;
    text-decoration: underline;
  }
  .clear-link:hover {
    color: #79c0ff;
  }
</style>
