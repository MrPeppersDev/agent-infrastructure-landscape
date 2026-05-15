// Build-time loader for /analyses/trajectory (issues #34, #47).
//
// Ships records + edges + detected lineages so the page can do the
// trajectory-bucket classification pass client-side. Also pre-computes
// the S-curve logistic fits at build time (issue #47 — BIMATEM-style)
// so the page doesn't pay the ~1s fit cost on every navigation. The
// forecast list feeds lineage-cadence into Panel 5.

import { getRecords, getEdges } from '$lib/data';
import { detectLineages } from '$lib/lineages';
import { forecastAll } from '$lib/analyses/forecast';
import { fitSCurves } from '$lib/analyses/s-curve';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const edges = getEdges();
  const lineages = detectLineages(records, edges);
  const forecasts = forecastAll(records, edges);
  const sCurveFits = fitSCurves(records);
  return { records, edges, lineages, forecasts, sCurveFits };
};
