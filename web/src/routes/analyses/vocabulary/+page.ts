// Build-time loader for /analyses/vocabulary (issue #26). Same pattern
// as /timeline: prerender, ship the full records array, let the page do
// all the term-matching and bucketing client-side. The site is static
// (adapter-static) so this runs once at build time.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => {
  return {
    records: getRecords()
  };
};
