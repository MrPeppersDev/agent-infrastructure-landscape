// Prerendered loader for the benchmark coverage matrix (issue #24).
//
// All extraction runs client-side from the bundled JSON; nothing here
// touches the network. We still expose +page.ts so the route is
// statically prerendered alongside the rest of /analyses/*.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords()
});
