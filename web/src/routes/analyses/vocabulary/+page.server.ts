// Build-time loader for /analyses/vocabulary (issue #26). Same pattern
// as /timeline: prerender, ship the full records array, let the page do
// all the term-matching and bucketing client-side. The site is static
// (adapter-static) so this runs once at build time.

import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => {
  return {
    records: slimRecords(['claims', 'created', 'desc'])
  };
};
