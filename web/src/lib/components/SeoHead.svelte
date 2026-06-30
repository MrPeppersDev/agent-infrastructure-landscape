<script lang="ts">
  // Reusable per-route SEO head block. Each route renders this once with
  // its own title/description/path; the component emits the canonical
  // link, Open Graph, and Twitter Card tags so the routes stay terse.
  // JSON-LD is emitted by a sibling <JsonLd> component so routes can mix
  // in zero or more structured-data blocks independently.

  import { absoluteUrl, SITE_NAME } from '$lib/site';

  type Props = {
    /** Full <title> for the page. Include a short site suffix yourself,
     * e.g. "Findings — AI Agent Memory Landscape". */
    title: string;
    /** Meta description, 50–160 chars for best CTR in SERPs. */
    description: string;
    /** Route path without base prefix, e.g. "/findings" or "/systems/mem0". */
    path: string;
    /** Optional Open Graph image absolute URL. Falls back to social preview. */
    image?: string;
    /** OG type. "article" for finding/system pages, "website" for hubs. */
    ogType?: 'website' | 'article';
  };

  let {
    title,
    description,
    path,
    image,
    ogType = 'website'
  }: Props = $props();

  const canonical = $derived(absoluteUrl(path));
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={description} />
  <link rel="canonical" href={canonical} />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:url" content={canonical} />
  <meta property="og:type" content={ogType} />
  <meta property="og:site_name" content={SITE_NAME} />
  {#if image}
    <meta property="og:image" content={image} />
  {/if}
  <meta name="twitter:card" content={image ? 'summary_large_image' : 'summary'} />
  <meta name="twitter:title" content={title} />
  <meta name="twitter:description" content={description} />
  {#if image}
    <meta name="twitter:image" content={image} />
  {/if}
</svelte:head>
