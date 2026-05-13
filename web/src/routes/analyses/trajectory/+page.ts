// Build-time loader for /analyses/trajectory (issue #34). Same shape as
// the sibling analytical views: ship records + edges + detected lineages,
// let the page do the classification pass client-side. We also include
// the lineage forecasts so we can pull cadence-by-lineage for Panel 5.

import { getRecords, getEdges } from '$lib/data';
import { detectLineages } from '$lib/lineages';
import { forecastAll } from '$lib/analyses/forecast';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const edges = getEdges();
  const lineages = detectLineages(records, edges);
  const forecasts = forecastAll(records, edges);
  return { records, edges, lineages, forecasts };
};
