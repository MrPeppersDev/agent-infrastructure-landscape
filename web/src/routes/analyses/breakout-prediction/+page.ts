// Build-time loader for /analyses/breakout-prediction (issue #58).
//
// Fits the Wang-Song-Barabási log-normal citation model to every
// academic-paper row with a populated citation trajectory, plus a
// synthesised-trajectory fallback for paper rows with only a
// (total cites, cites/yr, publication date) signal.
//
// The fit + bootstrap CI pass is pure-CPU and runs in ~5-10 seconds at
// build time; we cache the result here so the page doesn't re-fit on
// every navigation. Deterministic input → output (grid search has no
// randomness; bootstrap RNG is seeded from each record's id) so the
// validate-pipeline determinism gate stays clean.

import { getRecords } from '$lib/data';
import {
  fitCitationCurves,
  fieldConstant
} from '$lib/analyses/citation-prediction';

export const prerender = true;

export const load = () => {
  const records = getRecords();
  const fits = fitCitationCurves(records);
  const m = fieldConstant(records);
  return { records, fits, fieldConstantM: m };
};
