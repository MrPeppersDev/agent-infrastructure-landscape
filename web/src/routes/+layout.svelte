<script lang="ts">
  import '../app.css';

  let { children } = $props();
</script>

<div class="page">
  {@render children?.()}
</div>

<style>
  /* Full-bleed page for the table view. The narrow centered look from
     the landing page (#8) doesn't fit a 67-column scrollable table —
     we want every available pixel for the data. */
  .page {
    width: 100%;
    padding: 16px 16px 0;
  }
</style>
