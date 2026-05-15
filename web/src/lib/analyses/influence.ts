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
  /** Inbound `runtime-dependency` edges (issue #44). Surfaced as a tooltip
   * value and prose annotation; not used for axis placement to preserve
   * the original two-axis "academic vs commercial" framing. Substrates
   * with high runtime-dependency counts but low cites/integrations are the
   * "production graph" view of the same corpus. */
  runtimeDepsIn: number;
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
  const runtimeDeps = inboundEdgeCounts(edges, ['runtime-dependency']);
  const out: InfluencePoint[] = [];
  for (const r of records) {
    out.push({
      id: r.id,
      name: r.name,
      tier: r.tier,
      section: primarySection(r),
      citesIn: cites.get(r.id) ?? 0,
      integrationsIn: integ.get(r.id) ?? 0,
      runtimeDepsIn: runtimeDeps.get(r.id) ?? 0
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

// ---------------------------------------------------------------------------
// Upgrade additions (round 7) — filters, hex-bin density, interpretation
// copy. Kept pure and free of Svelte/DOM concerns so node -e harness checks
// keep working.

/**
 * Apply tier + section filters to the points list. An empty Set means
 * "include all" for that dimension (the chart default at first render).
 * Both Sets must independently admit the point for it to survive.
 */
export function filterPoints(
  points: InfluencePoint[],
  tiers: Set<Tier>,
  sections: Set<string>
): InfluencePoint[] {
  const allTiers = tiers.size === 0;
  const allSections = sections.size === 0;
  if (allTiers && allSections) return points;
  return points.filter(
    (p) =>
      (allTiers || tiers.has(p.tier)) &&
      (allSections || sections.has(p.section))
  );
}

/**
 * Static, hand-tuned interpretation copy for each quadrant. Kept here rather
 * than in the component so the same blurbs can be reused if we ever export
 * a static summary card / share image. The "soWhat" field intentionally
 * frames each cell as an action the reader can take, not a passive
 * observation — these views exist to drive curation decisions, not to be
 * read as a paper.
 */
export interface QuadrantInterpretation {
  name: string;
  short: string;
  interpretation: string;
  soWhat: string;
}

export const QUADRANT_COPY: Record<Quadrant, QuadrantInterpretation> = {
  both: {
    name: 'Both (cited + adopted)',
    short: 'cited AND adopted',
    interpretation:
      "Systems above the median on both axes — academia cites them and " +
      'engineers integrate against them. These are the rare nodes that ' +
      'have crossed from research result into production substrate.',
    soWhat:
      'Treat this as the watch list. If your system lives here, it has ' +
      'durability signal from two independent communities; protect the ' +
      'API surface and resist breaking changes. If a system you depend ' +
      'on is here, the bus factor is probably fine.'
  },
  engineering: {
    name: 'Engineering wins (adopted, not cited)',
    short: 'adopted, not cited',
    interpretation:
      'High inbound integration but low (or zero) inbound citations. ' +
      "Working code that downstream teams build on — but that hasn't " +
      'been picked up by the literature, often because it predates the ' +
      "current research wave or because it's industry-led infrastructure.",
    soWhat:
      'If your system is here, the open question is whether academic ' +
      'study should catch up — papers citing real production systems ' +
      'are more reproducible than papers citing only other papers. ' +
      'Worth seeding a benchmark / case study.'
  },
  orphan: {
    name: 'Research orphans (cited, not adopted)',
    short: 'cited, not adopted',
    interpretation:
      'High citation count, low integration count. The paper is in the ' +
      'air but nothing in the catalog has been built on top of it yet. ' +
      "That's a normal phase for recent work — adoption lags citation " +
      'by 12–24 months — but persistent orphans suggest a result that ' +
      "doesn't translate to a usable artefact.",
    soWhat:
      'Track these for adoption signals: a research orphan that picks ' +
      'up its first `built-on` edge is the strongest leading indicator ' +
      'we have for a paper crossing over. If your system is here, ship ' +
      'a reference implementation.'
  },
  tail: {
    name: 'Long tail',
    short: 'no centrality yet',
    interpretation:
      "Records with zero or below-median inbound edges on both axes. " +
      "Most of the corpus lives here. That isn't a failure — most " +
      'recent work simply has not had time to accumulate graph ' +
      'centrality, and many entries are products with no academic ' +
      'reach by design.',
    soWhat:
      "Don't over-read absence. Re-check this quadrant after the next " +
      'two extraction rounds — anything that moves out of the tail ' +
      'is a candidate for closer review.'
  }
};

/**
 * Headline observation about the diagonal pattern, foregrounded in the
 * narrative header. From the v1 analysis: the cited-and-adopted corner is
 * sparsely populated relative to either single-axis corner, which is the
 * "orthogonal" finding — academic citation and commercial adoption are
 * essentially independent at this corpus stage.
 */
export const HEADLINE_FINDING =
  'Academic citation and commercial integration are essentially ' +
  'orthogonal at the current corpus stage: the "Both" corner stays ' +
  'sparse even as either single-axis quadrant fills. Papers and ' +
  'production code are not yet on the same lineage.';

// ---------------------------------------------------------------------------
// Hex-bin density (pure). We hand-roll a flat-top hex grid because we
// already pay for d3 nowhere else in the bundle and the math is short.
//
// Approach:
//   1. Project each input point to (px, py) via the supplied projection
//      functions (the route already has projX/projY; we accept them as
//      callbacks so this stays decoupled from layout constants).
//   2. Bin into flat-top hexes of pixel radius `r`. Hex center math from
//      https://www.redblobgames.com/grids/hexagons/ ("pointy-top vs
//      flat-top, axial coords"). We use flat-top because the scatter is
//      wider than tall.
//   3. Return one HexBin per non-empty cell with its center in pixels and
//      its count, so the caller can render <polygon> elements directly.

export interface HexBin {
  cx: number;
  cy: number;
  count: number;
}

/**
 * Bin pixel-projected points into flat-top hexes of the given radius.
 *
 * Why flat-top vs square bins:
 *   - Hexes tile without the orthogonal-grid artefacts that make square
 *     bins look like a Minecraft screenshot at low counts.
 *   - The aspect ratio of one cell is closer to a circle, so the density
 *     blob you see corresponds to the eye's natural sense of "near".
 *
 * Why we accept already-projected coords:
 *   - Keeps this function trivially testable (no projection scaffolding).
 *   - Lets the caller decide whether to bin in screen space or data space.
 */
export function hexBin(
  pts: Array<{ x: number; y: number }>,
  r: number
): HexBin[] {
  if (r <= 0 || pts.length === 0) return [];
  // Flat-top hex dimensions:
  //   width  = 2 * r
  //   height = sqrt(3) * r
  //   horizontal spacing of column centers = 1.5 * r
  //   vertical spacing of row centers      = sqrt(3) * r (offset every other column)
  const sqrt3 = Math.sqrt(3);
  const colW = 1.5 * r;
  const rowH = sqrt3 * r;
  const cells = new Map<string, HexBin>();
  for (const p of pts) {
    // Find the candidate hex by snapping to the nearest column, then the
    // nearest row in that column. This isn't the textbook axial-rounding
    // method but it's correct to within one cell at the spacing we use
    // and is much shorter.
    const col = Math.round(p.x / colW);
    const yShift = col % 2 === 0 ? 0 : rowH / 2;
    const row = Math.round((p.y - yShift) / rowH);
    const cx = col * colW;
    const cy = row * rowH + yShift;
    const key = `${col}:${row}`;
    const existing = cells.get(key);
    if (existing) {
      existing.count += 1;
    } else {
      cells.set(key, { cx, cy, count: 1 });
    }
  }
  return [...cells.values()];
}

/**
 * Build the six SVG vertex points for a flat-top hex centered at (cx, cy)
 * with radius r. Returned as a "x1,y1 x2,y2 ..." string ready to drop into
 * a <polygon points={...}>.
 */
export function hexPolygonPoints(cx: number, cy: number, r: number): string {
  const pts: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i; // flat-top: 0, 60, 120, ...
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    pts.push(`${x.toFixed(2)},${y.toFixed(2)}`);
  }
  return pts.join(' ');
}
