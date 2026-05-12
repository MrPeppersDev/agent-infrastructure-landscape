// Build-time loader for /graph (issue #16).
//
// Cytoscape is a client-only library — we can't render the graph during
// SSR. We still prerender the page shell (so the route is reachable as
// /graph/index.html via adapter-static) and gate the cytoscape mount on
// `browser` inside the component.
//
// Why ship records + edges from load() rather than re-importing in the
// component: keeps the data path identical to /timeline and /sections,
// and SvelteKit's data inlining means we don't double-fetch.

import { getEdges, getRecords } from '$lib/data';

export const prerender = true;
// Skip SSR for this route — cytoscape touches the DOM during construction
// and we don't render the canvas server-side anyway. The component still
// guards on `browser` for the actual mount, but `ssr = false` saves the
// SvelteKit runtime from trying to render the (large) graph state on
// the server pass.
export const ssr = false;

export const load = () => {
  return {
    records: getRecords(),
    edges: getEdges()
  };
};
