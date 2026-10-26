<script lang="ts">
  // Tabs across the three choosers: memory layer, agent framework, data store.
  import { base } from '$app/paths';
  let { active }: { active: 'memory' | 'framework' | 'data' } = $props();
  const tabs = [
    { id: 'memory', label: 'Memory layer', href: '/choose' },
    { id: 'framework', label: 'Agent framework', href: '/choose/framework' },
    { id: 'data', label: 'Vector or graph database', href: '/choose/data' }
  ] as const;
</script>

<nav class="tabs" aria-label="What are you choosing?">
  {#each tabs as t (t.id)}
    <a href="{base}{t.href}" class:on={t.id === active} aria-current={t.id === active ? 'page' : undefined}>{t.label}</a>
  {/each}
</nav>

<style>
  .tabs { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 14px; }
  .tabs a { border: 1px solid #30363d; border-radius: 999px; padding: 5px 14px; font-size: 13px; color: #c9d1d9; text-decoration: none; background: #161b22; }
  .tabs a.on { background: #f0f6fc; color: #0d1117; border-color: #f0f6fc; font-weight: 600; }
  .tabs a:hover:not(.on) { border-color: #58a6ff; }
</style>
