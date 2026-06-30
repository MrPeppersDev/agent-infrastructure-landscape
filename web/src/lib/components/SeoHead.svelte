<script lang="ts">
  // Reusable per-route SEO head block. Each route renders this once with
  // its own title/description/path; the component emits the canonical
  // link, Open Graph, and Twitter Card tags so the routes stay terse.
  // JSON-LD is emitted by a sibling <JsonLd> component so routes can mix
  // in zero or more structured-data blocks independently.

  import { absoluteUrl, ogImageUrl, SITE_NAME } from '$lib/site';

  type Props = {
    /** Full <title> for the page. Include a short site suffix yourself,
     * e.g. "Findings — AI Agent Memory Landscape". */
    title: string;
    /** Meta description, 50–160 chars for best CTR in SERPs. */
    description: string;
    /** Route path without base prefix, e.g. "/findings" or "/systems/mem0". */
    path: string;
    /** Optional Open Graph image absolute URL. Defaults to the per-route
     * SVG emitted by scripts/generate-og.mjs. */
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
  // Every prerendered route gets a matching /og/<path>.svg via the build
  // pipeline, so default the OG image to that convention. Callers can
  // still override (e.g. to point at a hand-authored image).
  const ogImage = $derived(image ?? ogImageUrl(path));
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
  <meta property="og:image" content={ogImage} />
  <meta property="og:image:type" content="image/svg+xml" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content={title} />
  <meta name="twitter:description" content={description} />
  <meta name="twitter:image" content={ogImage} />
</svelte:head>
