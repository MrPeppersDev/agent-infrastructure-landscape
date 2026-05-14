// Prerendered loader for the benchmark-trust leaderboard (issue #42).
//
// Pure pivot of bundled landscape.json — no network in this view.

import { getRecords } from '$lib/data';

export const prerender = true;

export const load = () => ({
  records: getRecords()
});
