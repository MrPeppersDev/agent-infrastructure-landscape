<script lang="ts">
  // Emits one or more application/ld+json blocks in the page head. Accepts
  // a single schema object or an array. Uses @html so any stray closing
  // tag inside a JSON string can be escaped against injection.

  type Props = { data: unknown };
  let { data }: Props = $props();

  const items = $derived(Array.isArray(data) ? data : [data]);

  function serialize(obj: unknown): string {
    // Escape "</" so a stray "</script" inside a string field can't break
    // out of the surrounding <script> tag.
    return JSON.stringify(obj).replace(/<\/script/gi, '<\\/script');
  }
</script>

<svelte:head>
  {#each items as ld}
    {@html `<script type="application/ld+json">${serialize(ld)}</script>`}
  {/each}
</svelte:head>
