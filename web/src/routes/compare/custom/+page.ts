// Client-side "compare any two systems" route (refs #134).
//
// 528 records → ~139k possible pairs, so prerendering every combination
// is a non-starter. This route opts out of prerendering entirely and is
// served by the adapter-static SPA fallback (build/404.html — GitHub
// Pages serves 404.html for unknown paths, which boots the client router
// and resolves this route in the browser). It is deliberately:
//   - excluded from sitemap.xml (no prerendered HTML file → the build-dir
//     walk in scripts/generate-sitemap.mjs never sees it)
//   - marked noindex in +page.svelte (thin/duplicative content)
//   - free of JSON-LD (the pre-computed /compare/[pair] pages keep the
//     SEO surface)
export const prerender = false;
export const ssr = false;

import { getRecords, getEdges } from '$lib/data';

export function load() {
  return {
    records: getRecords(),
    edges: getEdges()
  };
}
