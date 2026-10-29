// Prerendered loader for the benchmark-integrity view (issue #33).
//
// Companion to /analyses/benchmarks. All classification runs client-side
// from the bundled JSON; nothing here touches the network.

import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => ({
  records: slimRecords(['claims', 'perf'])
});
