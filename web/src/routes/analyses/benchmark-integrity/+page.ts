// Prerendered loader for the benchmark-integrity view (issue #33).
//
// Companion to /analyses/benchmarks. All classification runs client-side
// from the bundled JSON; nothing here touches the network.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords()
});
