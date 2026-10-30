<script lang="ts">
  // Front-door banner on the main table: the questions most visitors arrive
  // with (what should my stack be, which component, is my stack healthy),
  // answered by the decision tools (#330). Hidden once the visitor is
  // already filtering/searching, and dismissible (remembered per browser).
  import { base } from '$app/paths';
  import { browser } from '$app/environment';

  let { hidden = false }: { hidden?: boolean } = $props();
  const KEY = 'landscape.startHere.dismissed';
  let dismissed = $state(false);
  if (browser) {
    try {
      dismissed = localStorage.getItem(KEY) === '1';
    } catch {
      /* storage unavailable — show the banner */
    }
  }
  function dismiss() {
    dismissed = true;
    try {
      localStorage.setItem(KEY, '1');
    } catch {
      /* ignore */
    }
  }
</script>

{#if !hidden && !dismissed}
  <section class="start" aria-label="Start here">
    <a class="tile" href="{base}/build">
      <strong>What should my agent stack be?</strong>
      <span>Describe what you're building and get one cited pick per layer, the runners-up, risk, cost and a stack.yml.</span>
    </a>
    <a class="tile" href="{base}/choose">
      <strong>Which framework, memory layer or database?</strong>
      <span>Answer a few questions about one layer, get three cited picks and a side-by-side comparison.</span>
    </a>
    <a class="tile" href="{base}/check">
      <strong>Is anything in my stack dead?</strong>
      <span>Paste a package.json, requirements.txt or MCP config to find archived, acquired or stale dependencies.</span>
    </a>
    <button type="button" class="close" onclick={dismiss} aria-label="Hide these shortcuts">×</button>
  </section>
{/if}

<style>
  .start {
    position: relative;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 10px;
    padding: 10px 40px 4px 12px;
  }
  .tile {
    display: grid;
    gap: 2px;
    padding: 10px 14px;
    border: 1px solid #1f6feb;
    border-radius: 10px;
    background: #0d1117;
    color: #c9d1d9;
    text-decoration: none;
  }
  .tile:hover {
    background: #161b22;
  }
  .tile strong {
    color: #58a6ff;
    font-size: 14px;
  }
  .tile span {
    font-size: 12px;
    color: #8b949e;
  }
  .close {
    position: absolute;
    top: 8px;
    right: 10px;
    background: none;
    border: 0;
    color: #6e7681;
    font-size: 18px;
    cursor: pointer;
  }
</style>
