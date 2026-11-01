<script lang="ts">
  // /status: when each of the catalog's bots last ran and last succeeded.
  import SeoHead from '$lib/components/SeoHead.svelte';
  import type { BotStatus, Bot } from './+page.server';

  let { data }: { data: { status: BotStatus } } = $props();
  const REPO = 'https://github.com/MrPeppersDev/agent-infrastructure-landscape';

  const day = (iso: string | undefined) => (iso ? iso.slice(0, 10) : '—');
  function health(b: Bot): { tone: string; label: string } {
    if (!b.lastRun) return { tone: 'muted', label: 'never run' };
    if (b.lastRun.conclusion === 'failure') return { tone: 'bad', label: 'last run failed' };
    if (b.recentFailures > b.recentRuns / 2) return { tone: 'warn', label: 'often failing' };
    if (b.lastRun.status !== 'completed') return { tone: 'info', label: 'running' };
    return { tone: 'ok', label: b.lastRun.conclusion ?? 'ok' };
  }
</script>

<SeoHead
  title="Bot status — when the catalog's bots last ran"
  description="When each of the AI Agent Infrastructure Landscape's bots (re-verification, intake, staleness, release and price watch, rebaselines, deploys) last ran and last succeeded."
  path="/status"
/>

<main class="page">
  <h1>Bot status</h1>
  <p class="lede">
    The catalog is kept fresh by GitHub Actions workflows: weekly section audits, intake research, staleness, release
    and price watches, rebaselines, and the deploys. This page shows when each last ran and last succeeded, so you
    can tell how current the data behind a page is. Every change they make still goes through a pull request.
  </p>

  {#if data.status.available}
    <p class="meta">As of {data.status.generatedAt.replace('T', ' ').slice(0, 16)} UTC, from the GitHub Actions API.</p>
    <table>
      <thead><tr><th>Workflow</th><th>Health</th><th>Last run</th><th>Last success</th><th class="num">Failures in the last {20} runs</th></tr></thead>
      <tbody>
        {#each data.status.workflows as b (b.file)}
          {@const h = health(b)}
          <tr>
            <td><a href={b.url} rel="noopener">{b.name}</a></td>
            <td><span class="dot {h.tone}"></span>{h.label}</td>
            <td>{#if b.lastRun}<a href={b.lastRun.url} rel="noopener">{day(b.lastRun.at)}</a> <span class="ev">{b.lastRun.event}</span>{:else}—{/if}</td>
            <td>{#if b.lastSuccess}<a href={b.lastSuccess.url} rel="noopener">{day(b.lastSuccess.at)}</a>{:else}never{/if}</td>
            <td class="num">{b.recentFailures} of {b.recentRuns}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {:else}
    <p class="none">
      Bot status isn't available in this build ({data.status.reason ?? 'no data'}). The live site generates it on every
      deploy; meanwhile see <a href="{REPO}/actions">the repository's Actions tab</a>.
    </p>
  {/if}
</main>

<style>
  .page { max-width: 960px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; line-height: 1.55; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  a { color: #58a6ff; }
  .lede, .meta, .none { color: #8b949e; }
  table { border-collapse: collapse; width: 100%; font-size: 14px; margin-top: 12px; }
  th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #21262d; }
  th { color: #8b949e; font-weight: 500; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .ev { color: #6e7681; font-size: 12px; }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; background: #6e7681; }
  .dot.ok { background: #3fb950; }
  .dot.info { background: #58a6ff; }
  .dot.warn { background: #d29922; }
  .dot.bad { background: #f85149; }
</style>
