// Pure helpers for the influence-vs-adoption matrix view (issue #22).
//
// X-axis: inbound `cites` edges (academic influence in-catalog).
// Y-axis: inbound `integrates-with` + `built-on` edges (commercial adoption).
//
// We deliberately compute thresholds here, in pure functions, so the route
// component stays presentational and so the same numbers can be sanity-
// checked by a test harness (or by node -e at the CLI) without spinning up
// Vite. The threshold choice is documented in docs/DECISIONS.md.

import { inboundEdgeCounts, primarySection } from '../leaderboards';
import type { Edge, LandscapeRecord, Tier } from '../types';

export type InfluencePoint = {
  id: string;
  name: string;
  tier: Tier;
  section: string;
  citesIn: number;
  integrationsIn: number;
};

export type Quadrant = 'both' | 'engineering' | 'orphan' | 'tail';

/**
 * Builds one point per record. Records with zero inbound edges of either
 * kind are kept — they're the bulk of the "long tail" quadrant and matter
 * for visual context (showing the reader that most of the corpus has not
 * yet accumulated graph centrality is itself the point of the chart).
 */
export function buildPoints(
  records: LandscapeRecord[],
  edges: Edge[]
): InfluencePoint[] {
  const cites = inboundEdgeCounts(edges, ['cites']);
  const integ = inboundEdgeCounts(edges, ['integrates-with', 'built-on']);
  const out: InfluencePoint[] = [];
  for (const r of records) {
    out.push({
      id: r.id,
      name: r.name,
      tier: r.tier,
      section: primarySection(r),
      citesIn: cites.get(r.id) ?? 0,
      integrationsIn: integ.get(r.id) ?? 0
    });
  }
  return out;
}

/**
 * Classify a point into one of four quadrants relative to (citesCut,
 * integCut). A point with citesIn === 0 and integrationsIn === 0 always
 * lands in 'tail' regardless of cutoffs.
 *
 * We use STRICT greater-than for the high side so a record sitting
 * exactly on the cutoff (e.g. citesIn === 1 with cut === 1) stays in the
 * tail; that matches the visual intent — being above the threshold
 * means demonstrably above-median, not tied.
 */
export function classifyQuadrant(
  p: InfluencePoint,
  citesCut: number,
  integCut: number
): Quadrant {
  const highCites = p.citesIn > citesCut;
  const highInteg = p.integrationsIn > integCut;
  if (highCites && highInteg) return 'both';
  if (highInteg) return 'engineering';
  if (highCites) return 'orphan';
  return 'tail';
}

/**
 * Median of the non-zero subset on a given axis. We use the non-zero
 * subset because most of the 523 records have zero inbound edges and
 * the population median would always be 0, putting the cutoff line
 * touching the axis. Median-of-non-zero gives a more interesting
 * partition: "above median among the records that have any signal at
 * all". Empirically: cites→2, integrations→2 at the time of writing.
 *
 * Falls back to 0 when the non-zero subset is empty.
 */
export function nonZeroMedian(values: number[]): number {
  const nz = values.filter((v) => v > 0).sort((a, b) => a - b);
  if (nz.length === 0) return 0;
  const mid = Math.floor(nz.length / 2);
  return nz.length % 2 === 0 ? (nz[mid - 1] + nz[mid]) / 2 : nz[mid];
}

/**
 * Tier → marker radius (px). T1 biggest, T5 smallest. Linear scale because
 * tiers are an ordinal 1..5 with no log meaning.
 */
export function tierRadius(tier: Tier): number {
  switch (tier) {
    case 1:
      return 7;
    case 2:
      return 6;
    case 3:
      return 5;
    case 4:
      return 4;
    case 5:
      return 3;
  }
}

/**
 * Stable section → colour. Hash the section name to one of 10 distinguishable
 * hues. Pure function so server/client render the same colour.
 */
const SECTION_PALETTE = [
  '#d4845f', // warm orange (matches site accent)
  '#5fa8d4', // sky
  '#9b6fd4', // violet
  '#d4c25f', // mustard
  '#5fd49b', // mint
  '#d45f9b', // pink
  '#5fd4c2', // teal
  '#d4655f', // coral
  '#7fd45f', // lime
  '#5f7fd4'  // royal blue
];

export function sectionColor(section: string): string {
  let h = 0;
  for (let i = 0; i < section.length; i++) {
    h = (h * 31 + section.charCodeAt(i)) >>> 0;
  }
  return SECTION_PALETTE[h % SECTION_PALETTE.length];
}

/**
 * Returns the top-K points in a given quadrant, ranked by combined
 * (citesIn + integrationsIn) score, descending. Used to choose which
 * points get a text annotation on the chart.
 */
export function topInQuadrant(
  points: InfluencePoint[],
  citesCut: number,
  integCut: number,
  quadrant: Quadrant,
  k: number
): InfluencePoint[] {
  return points
    .filter((p) => classifyQuadrant(p, citesCut, integCut) === quadrant)
    .sort((a, b) => {
      const ds = b.citesIn + b.integrationsIn - (a.citesIn + a.integrationsIn);
      if (ds !== 0) return ds;
      // tie-break by the axis the quadrant favours, then by name
      if (quadrant === 'engineering') return b.integrationsIn - a.integrationsIn;
      if (quadrant === 'orphan') return b.citesIn - a.citesIn;
      return a.name.localeCompare(b.name);
    })
    .slice(0, k);
}

/**
 * Aggregate quadrant counts for the page footer + commit message.
 */
export function quadrantCounts(
  points: InfluencePoint[],
  citesCut: number,
  integCut: number
): Record<Quadrant, number> {
  const out: Record<Quadrant, number> = {
    both: 0,
    engineering: 0,
    orphan: 0,
    tail: 0
  };
  for (const p of points) {
    out[classifyQuadrant(p, citesCut, integCut)] += 1;
  }
  return out;
}
