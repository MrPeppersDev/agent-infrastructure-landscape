<script lang="ts">
  // Renders the taxonomy axis cell — a list of pills, primary first.

  import type { TaxonomyValue } from '$lib/types';

  let { values }: { values: TaxonomyValue[] } = $props();

  // Sort: primary first, then alphabetical for stability.
  const sorted = $derived(
    [...values].sort((a, b) => {
      if (a.primary && !b.primary) return -1;
      if (!a.primary && b.primary) return 1;
      return a.value.localeCompare(b.value);
    })
  );
</script>

{#each sorted as v}
  <span class="tax-pill tax-{v.value}" title={v.reason ?? ''}>{v.value}</span>
{/each}

<style>
  .tax-pill {
    display: inline-block;
    padding: 1px 6px;
    margin: 1px 2px 1px 0;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.02em;
    line-height: 1.5;
    background: #2a2a2a;
    border: 1px solid #3a3a3a;
    color: #c8c8c8;
    white-space: nowrap;
  }
  .tax-pill.tax-vector {
    background: #1f2a3a;
    color: #8fb3c9;
    border-color: #2c4253;
  }
  .tax-pill.tax-graph {
    background: #1f3a26;
    color: #8fc99a;
    border-color: #2c5235;
  }
  .tax-pill.tax-kv,
  .tax-pill.tax-kv-cache {
    background: #3a2e1f;
    color: #c9a98f;
    border-color: #53432c;
  }
  .tax-pill.tax-file {
    background: #2a2a2a;
    color: #c8c8c8;
    border-color: #3a3a3a;
  }
  .tax-pill.tax-parametric,
  .tax-pill.tax-parametric-recall,
  .tax-pill.tax-parametric-edit {
    background: #321f3a;
    color: #b58fc9;
    border-color: #492c53;
  }
  .tax-pill.tax-relational,
  .tax-pill.tax-column {
    background: #3a1f26;
    color: #c98f9a;
    border-color: #532c35;
  }
  .tax-pill.tax-hybrid {
    background: #2a3a2a;
    color: #a8c4a4;
    border-color: #3a532c;
  }
</style>
