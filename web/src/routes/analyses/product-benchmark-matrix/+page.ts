// Prerendered loader for the product × benchmark coverage matrix (issue #43).
//
// All extraction + classification runs client-side from the bundled JSON;
// nothing here touches the network. We still expose +page.ts so the route
// is statically prerendered alongside the rest of /analyses/*.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords()
});
