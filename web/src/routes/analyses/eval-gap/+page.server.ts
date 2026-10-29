// Prerendered loader for the eval-gap analysis view (issue #40, T1-2).
//
// Pure pivot of bundled landscape.json — no network in this view.

import { slimRecords } from '$lib/slim';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => ({
  records: slimRecords(['eval-braintrust', 'eval-custom-test-harness', 'eval-helicone-evals', 'eval-human-loop', 'eval-langsmith-evals', 'eval-production-traffic-replay', 'eval-weights-and-biases-agent', 'obs-arize', 'obs-custom', 'obs-datadog', 'obs-helicone', 'obs-langfuse', 'obs-langsmith', 'obs-opentelemetry', 'obs-weave'])
});
