// Prerendered loader for the observability coverage view (issue #39, T1-1).
//
// Pure pivot of bundled landscape.json — no network in this view.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords()
});
