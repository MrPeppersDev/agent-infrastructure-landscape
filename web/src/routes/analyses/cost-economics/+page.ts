// Prerendered loader for the cost-economics coverage view (issue #41, T1-3).
//
// Pure pivot of bundled landscape.json — no network in this view.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords()
});
