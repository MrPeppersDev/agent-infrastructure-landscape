// Prerendered loader for the benchmark coverage matrix (issue #24).
//
// All extraction runs client-side from the bundled JSON; nothing here
// touches the network. We still expose +page.ts so the route is
// statically prerendered alongside the rest of /analyses/*.

import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => ({
  records: slimRecords(['claims', 'desc', 'perf'])
});
