// Prerendered loader for the eval-gap analysis view (issue #40, T1-2).
//
// Pure pivot of bundled landscape.json — no network in this view.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords()
});
