// Prerendered loader for the cost-economics coverage view (issue #41, T1-3).
//
// Pure pivot of bundled landscape.json — no network in this view.

import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => ({
  records: slimRecords(['cost-batching', 'cost-input-usd-per-mtok', 'cost-last-verified', 'cost-model-routing', 'cost-observability-cost-attribution', 'cost-output-usd-per-mtok', 'cost-pricing-model', 'cost-prompt-caching', 'cost-semantic-caching', 'cost-streaming-only', 'cost-tier', 'cost-token-budget'])
});
