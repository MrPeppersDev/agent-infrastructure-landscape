// Pure helpers for the /graph view (issue #16).
//
// Cytoscape consumes a flat "elements" array of `{ data: {...} }` objects;
// this module shapes our records + edges into that form and computes the
// connectivity / palette metadata the view uses for filtering, search-
// highlight, and the hub-view toggle.
//
// All exports are pure — no Cytoscape, no DOM — so the view file can stay
// thin and any future export (PNG / GraphML) can reuse the same shaping.

import type { Edge, EdgeType, LandscapeRecord, Tier } from './types';
import { primarySection, inboundEdgeCounts } from './leaderboards';

// --- Node / edge element shapes ----------------------------------------

export interface GraphNodeData {
  id: string;
  label: string;
  tier: Tier;
  section: string;
  /** Outbound + inbound edges for the hub-view sort. */
  degree: number;
  inDegree: number;
  outDegree: number;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
}

export interface CyNode { data: GraphNodeData }
export interface CyEdge { data: GraphEdgeData }

// --- Palette -----------------------------------------------------------
//
// 20-section categorical palette. We hand-pick HSL anchors with high
// chroma and rotate the hue circle so adjacent sections in the legend
// don't sit next to each other on the colour wheel — which would make
// neighbouring nodes indistinguishable when the graph clusters along
// section boundaries (which it does, because fcose pulls connected
// components together).
//
// Chosen for legibility on the dark background (#0d1117). Each colour
// pairs with white text for the side-panel chip.
export const SECTION_PALETTE: string[] = [
  '#58a6ff', // azure
  '#3fb950', // green
  '#d29922', // amber
  '#bc8cff', // purple
  '#ff7b72', // coral
  '#39d0d8', // teal
  '#f778ba', // pink
  '#a371f7', // violet
  '#7ee787', // mint
  '#ffa657', // tangerine
  '#79c0ff', // sky
  '#f0883e', // orange
  '#56d364', // lime
  '#db61a2', // magenta
  '#e3b341', // gold
  '#4c8eda', // steel
  '#6e7681', // slate
  '#c38000', // ochre
  '#8957e5', // indigo
  '#1f6feb'  // royal
];

/**
 * Assign each section a stable colour from the palette. Sections are
 * sorted by record count (desc) so the most-populous gets palette[0] —
 * the eye lands on the busiest cluster first.
 */
export function sectionColourMap(records: LandscapeRecord[]): Map<string, string> {
  const counts = new Map<string, number>();
  for (const r of records) {
    const s = primarySection(r);
    counts.set(s, (counts.get(s) ?? 0) + 1);
  }
  const ordered = [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([s]) => s);
  const map = new Map<string, string>();
  ordered.forEach((s, i) => {
    map.set(s, SECTION_PALETTE[i % SECTION_PALETTE.length]);
  });
  return map;
}

// --- Edge styling ------------------------------------------------------
//
// Edge types are styled by a triple: hex colour, dash pattern, default
// width. The dash pattern is what makes the legend toggle land visually
// even for users who don't pick up on subtle hue differences (~8% of
// male users have red/green deficiency). Six visible types in the
// corpus today: cites, integrates-with, built-on, extends, forks,
// same-team-as. competes-with / inspired-by / succeeds defined in the
// type but absent from the data; we still register style so future
// data lands sensibly.

export interface EdgeStyle {
  colour: string;
  /** Cytoscape line-style: 'solid' | 'dashed' | 'dotted'. */
  lineStyle: 'solid' | 'dashed' | 'dotted';
  width: number;
  /** Display label for the legend. */
  label: string;
}

export const EDGE_STYLES: Record<EdgeType, EdgeStyle> = {
  'built-on':        { colour: '#bc8cff', lineStyle: 'solid',  width: 2,   label: 'built-on' },
  'extends':         { colour: '#7ee787', lineStyle: 'solid',  width: 1.6, label: 'extends' },
  'forks':           { colour: '#ffa657', lineStyle: 'dashed', width: 1.6, label: 'forks' },
  'integrates-with': { colour: '#39d0d8', lineStyle: 'solid',  width: 1.2, label: 'integrates-with' },
  'competes-with':   { colour: '#ff7b72', lineStyle: 'dashed', width: 1.2, label: 'competes-with' },
  'inspired-by':     { colour: '#d29922', lineStyle: 'dotted', width: 1.2, label: 'inspired-by' },
  'cites':           { colour: '#6e7681', lineStyle: 'solid',  width: 0.6, label: 'cites' },
  'same-team-as':    { colour: '#f778ba', lineStyle: 'dotted', width: 1.6, label: 'same-team-as' },
  'succeeds':        { colour: '#79c0ff', lineStyle: 'dashed', width: 1.6, label: 'succeeds' }
};

// --- Element shaping ---------------------------------------------------

/**
 * Compute degree (in + out + total) for every record id so we can both
 * size nodes by connectivity in the stylesheet and offer a hub-view
 * toggle without recomputing on every keystroke. O(E).
 */
export function degreeMap(edges: Edge[]): Map<string, { in: number; out: number; total: number }> {
  const m = new Map<string, { in: number; out: number; total: number }>();
  const bump = (id: string, dir: 'in' | 'out') => {
    let v = m.get(id);
    if (!v) {
      v = { in: 0, out: 0, total: 0 };
      m.set(id, v);
    }
    v[dir] += 1;
    v.total += 1;
  };
  for (const e of edges) {
    bump(e.source, 'out');
    bump(e.target, 'in');
  }
  return m;
}

export function recordsToNodes(records: LandscapeRecord[], degrees: Map<string, { in: number; out: number; total: number }>): CyNode[] {
  return records.map((r) => {
    const d = degrees.get(r.id) ?? { in: 0, out: 0, total: 0 };
    return {
      data: {
        id: r.id,
        label: r.name,
        tier: r.tier,
        section: primarySection(r),
        degree: d.total,
        inDegree: d.in,
        outDegree: d.out
      }
    };
  });
}

export function edgesToCytoscape(edges: Edge[], nodeIds: Set<string>): CyEdge[] {
  // We drop edges whose source or target aren't in the node set. Cytoscape
  // throws if a dangling endpoint shows up, and the data isn't guaranteed
  // to have 100% referential integrity (older edges may reference renamed
  // record ids until #1's normaliser catches up).
  const out: CyEdge[] = [];
  for (const e of edges) {
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) continue;
    out.push({
      data: {
        id: `${e.source}->${e.target}:${e.type}`,
        source: e.source,
        target: e.target,
        type: e.type
      }
    });
  }
  return out;
}

// --- Neighbour index (for search-highlight) ----------------------------
//
// Pre-computed adjacency so highlighting a node + its 1-hop ring is
// O(degree) per keystroke instead of O(E). For 247 edges this is
// micro-optimisation, but the same index also powers the hub-view's
// "show top-N nodes plus the edges between them" filter.

export interface Neighbourhood {
  /** id → set of neighbour ids (undirected — includes both ends). */
  byId: Map<string, Set<string>>;
}

export function neighbourhoodIndex(edges: Edge[]): Neighbourhood {
  const byId = new Map<string, Set<string>>();
  const link = (a: string, b: string) => {
    let s = byId.get(a);
    if (!s) {
      s = new Set<string>();
      byId.set(a, s);
    }
    s.add(b);
  };
  for (const e of edges) {
    link(e.source, e.target);
    link(e.target, e.source);
  }
  return { byId };
}

// --- Hub selection -----------------------------------------------------
//
// "Hub view" = the top-N most-connected nodes. We rank by total degree
// (in + out) so a paper that's cited 30 times and a platform that
// integrates with 30 things both surface. Inbound-only ranking would
// hide platforms; outbound-only would hide foundational papers.

export function topHubIds(records: LandscapeRecord[], edges: Edge[], n: number): Set<string> {
  const d = degreeMap(edges);
  const ranked = records
    .map((r) => ({ id: r.id, total: d.get(r.id)?.total ?? 0 }))
    .filter((r) => r.total > 0)
    .sort((a, b) => b.total - a.total)
    .slice(0, n);
  return new Set(ranked.map((r) => r.id));
}

// --- Side-panel record lookup -----------------------------------------

export function recordById(records: LandscapeRecord[]): Map<string, LandscapeRecord> {
  const m = new Map<string, LandscapeRecord>();
  for (const r of records) m.set(r.id, r);
  return m;
}

// Re-export so consumers don't need two imports.
export { primarySection, inboundEdgeCounts };
