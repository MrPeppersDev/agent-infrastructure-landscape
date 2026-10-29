// Build-time loader for /analyses/trajectory (issues #34, #47).
//
// Ships records + edges + detected lineages so the page can do the
// trajectory-bucket classification pass client-side. Also pre-computes
// the S-curve logistic fits at build time (issue #47 — BIMATEM-style)
// so the page doesn't pay the ~1s fit cost on every navigation. The
// forecast list feeds lineage-cadence into Panel 5.

import { getEdges } from '$lib/data';
import { slimRecords } from '$lib/slim';
import { detectLineages } from '$lib/lineages';
import { forecastAll } from '$lib/analyses/forecast';
import { fitSCurves } from '$lib/analyses/s-curve';

export const prerender = true;

// Only the cells this page reads (#324). The list is every cell slug the page
// and the modules it imports name; add a slug here before reading a new one.

export const load = () => {
  const records = slimRecords(['api-surface', 'citation-trajectory', 'citations', 'claims', 'code-release', 'commit-trajectory', 'compliance', 'created', 'customers', 'deployment', 'desc', 'download-trajectory', 'embedding-model', 'funding', 'gh', 'latest-release', 'license', 'llm-lock', 'mindshare', 'pricing']);
  const edges = getEdges();
  const lineages = detectLineages(records, edges);
  const forecasts = forecastAll(records, edges);
  const sCurveFits = fitSCurves(records);
  return { records, edges, lineages, forecasts, sCurveFits };
};
