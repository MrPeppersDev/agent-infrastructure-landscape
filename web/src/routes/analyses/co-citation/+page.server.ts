// Loader for the co-citation + bibliographic-coupling map (issue #45, T2-2).
//
// Pure pivot over bundled records + edges — no network in this view.
// Cytoscape is client-only (touches the DOM during construction), so we
// skip SSR and let the component guard its mount on `browser`. We still
// prerender the page shell so the route is reachable as
// /analyses/co-citation/index.html via adapter-static.

import { getEdges } from '$lib/data';
import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.
export const ssr = false;

export const load = () => ({
  records: slimRecords(['citations', 'funding', 'gh', 'integration-count', 'mindshare']),
  edges: getEdges()
});
