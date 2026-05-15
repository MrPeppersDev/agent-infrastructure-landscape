// Loader for the co-citation + bibliographic-coupling map (issue #45, T2-2).
//
// Pure pivot over bundled records + edges — no network in this view.
// Cytoscape is client-only (touches the DOM during construction), so we
// skip SSR and let the component guard its mount on `browser`. We still
// prerender the page shell so the route is reachable as
// /analyses/co-citation/index.html via adapter-static.

import { getEdges, getRecords } from '$lib/data';

export const prerender = true;
export const ssr = false;

export const load = () => ({
  records: getRecords(),
  edges: getEdges()
});
