<script lang="ts">
  import '../app.css';

  let { children } = $props();
</script>

<div class="page">
  {@render children?.()}
</div>

<style>
  .page {
    max-width: 880px;
    margin: 0 auto;
    padding: var(--space-5) var(--space-3);
  }
</style>
