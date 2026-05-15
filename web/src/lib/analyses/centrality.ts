// Pure helpers for graph-centrality measures on the in-catalog edge graph
// (issue #46). Upgrades the influence view from "raw inbound count" to a
// proper structural view: who BRIDGES clusters (betweenness) and who sits
// in the NUCLEUS (k-core).
//
// Both algorithms run in pure TypeScript so the centrality computation is
// part of the SvelteKit prerender pass — no Python pre-compute step needed.
// On the current 912-node / 528-edge graph the full computation finishes
// in well under a second; even a worst-case Brandes (O(V*E)) is ~480k ops,
// which is trivial for V8.
//
// --- Why undirected -------------------------------------------------------
//
// Graph-theory convention: betweenness is defined on undirected graphs by
// default — a shortest path between u and v is the same path regardless of
// which endpoint we start traversal from. Our edge types are a mix of
// directed semantics (A `cites` B, A `built-on` B) and bidirectional ones
// (A `competes-with` B). For the centrality view we collapse the edge set
// to its undirected projection: any record pair connected by any edge of
// any type counts as adjacent.
//
// This is the right call because the question the view answers — "who sits
// on the most shortest paths between clusters" — is about connectivity, not
// about citation lineage. The lineage view (`/analyses/forecast`) is where
// edge direction matters.
//
// --- K-core --------------------------------------------------------------
//
// The k-core of a graph is the maximal subgraph in which every node has
// degree ≥ k (in the subgraph). The "coreness" of a node is the largest k
// such that the node belongs to a k-core. Computed by the standard peeling
// algorithm of Batagelj & Zaversnik (2003): O(E) time.
//
// References:
//   - Brandes, U. (1986). "A faster algorithm for betweenness centrality."
//     J. Math. Sociol. 25 (2): 163–177.
//   - Seidman, S. (1983). "Network structure and minimum degree."
//     Social Networks 5 (3): 269–287.
//   - Batagelj, V. & Zaversnik, M. (2003). "An O(m) algorithm for cores
//     decomposition of networks." arXiv:cs/0310049.

import { primarySection } from '../leaderboards';
import type { Edge, LandscapeRecord } from '../types';

export interface CentralityResult {
  recordId: string;
  recordName: string;
  section: string;
  /** Raw inbound edge count (the existing metric — every edge type). */
  inboundCount: number;
  /** Brandes betweenness, normalised to [0, 1] by dividing by max in graph. */
  betweenness: number;
  /** K-core coreness number (largest k such that record sits in a k-core). */
  kCore: number;
  /** rank-by-inbound − rank-by-betweenness. Positive = bridge surprise. */
  bridgeSurprise: number;
}

export interface CentralityOutput {
  results: CentralityResult[];
  /** Top 10 by bridgeSurprise > 0, descending. The "bridges hiding in plain
   *  sight" list: high betweenness rank, comparatively low raw inbound. */
  topBridgeSurprises: CentralityResult[];
  /** Members of the highest k-core in the graph (the "nucleus"). */
  nucleus: CentralityResult[];
  /** The maximum coreness observed in the graph. */
  maxKCore: number;
  /** Distribution: kCore value → count of records at that level. */
  kCoreDistribution: Record<number, number>;
  /** Raw count of nodes considered (all records). */
  nodeCount: number;
  /** Raw count of UNIQUE undirected adjacencies. (Symmetric edges collapsed.) */
  undirectedEdgeCount: number;
}

// --------------------------------------------------------------------------
// Internal: build an undirected adjacency list keyed by record id. Self-loops
// and duplicate u↔v pairs are collapsed.
// --------------------------------------------------------------------------

function buildAdjacency(
  records: LandscapeRecord[],
  edges: Edge[]
): { adj: Map<string, Set<string>>; undirectedEdgeCount: number } {
  const idSet = new Set(records.map((r) => r.id));
  const adj = new Map<string, Set<string>>();
  for (const r of records) adj.set(r.id, new Set());
  for (const e of edges) {
    if (e.source === e.target) continue;
    if (!idSet.has(e.source) || !idSet.has(e.target)) continue;
    adj.get(e.source)!.add(e.target);
    adj.get(e.target)!.add(e.source);
  }
  // Count unique undirected pairs: sum of degrees / 2.
  let degSum = 0;
  for (const nbrs of adj.values()) degSum += nbrs.size;
  return { adj, undirectedEdgeCount: degSum / 2 };
}

// --------------------------------------------------------------------------
// Brandes' algorithm for betweenness centrality (undirected, unweighted).
//
// For each source s:
//   1. BFS from s, recording σ(v) = #shortest paths from s reaching v,
//      and predecessor lists Pred(v).
//   2. Stack-driven back-accumulation: δ(v) = Σ_{w: v ∈ Pred(w)}
//      (σ(v)/σ(w)) * (1 + δ(w)). For each v ≠ s, increment CB(v) by δ(v).
//
// We DOUBLE-COUNT (s,t) and (t,s) in the loop and at the end divide by 2
// — the standard undirected normalisation. Then we normalise to [0, 1] by
// dividing by the max betweenness in the graph (rather than the textbook
// (n-1)(n-2)/2 normalisation) because we want a visually useful score for
// the legend, not a graph-theoretic invariant.
// --------------------------------------------------------------------------

function computeBetweenness(
  nodes: string[],
  adj: Map<string, Set<string>>
): Map<string, number> {
  const cb = new Map<string, number>();
  for (const n of nodes) cb.set(n, 0);

  for (const s of nodes) {
    // Single-source shortest paths via BFS.
    const stack: string[] = [];
    const pred = new Map<string, string[]>();
    const sigma = new Map<string, number>();
    const dist = new Map<string, number>();
    for (const v of nodes) {
      pred.set(v, []);
      sigma.set(v, 0);
      dist.set(v, -1);
    }
    sigma.set(s, 1);
    dist.set(s, 0);
    const queue: string[] = [s];
    let head = 0;
    while (head < queue.length) {
      const v = queue[head++];
      stack.push(v);
      const dv = dist.get(v)!;
      const sv = sigma.get(v)!;
      const nbrs = adj.get(v)!;
      for (const w of nbrs) {
        // First time we reach w?
        if (dist.get(w) === -1) {
          dist.set(w, dv + 1);
          queue.push(w);
        }
        // Shortest path to w via v?
        if (dist.get(w) === dv + 1) {
          sigma.set(w, sigma.get(w)! + sv);
          pred.get(w)!.push(v);
        }
      }
    }

    // Back-accumulation.
    const delta = new Map<string, number>();
    for (const v of nodes) delta.set(v, 0);
    while (stack.length > 0) {
      const w = stack.pop()!;
      const sw = sigma.get(w)!;
      const dw = delta.get(w)!;
      for (const v of pred.get(w)!) {
        const contrib = (sigma.get(v)! / sw) * (1 + dw);
        delta.set(v, delta.get(v)! + contrib);
      }
      if (w !== s) cb.set(w, cb.get(w)! + dw);
    }
  }

  // Undirected: divide by 2 (we counted each (s,t) pair from both ends).
  for (const [k, v] of cb) cb.set(k, v / 2);
  return cb;
}

// --------------------------------------------------------------------------
// K-core peeling (Batagelj & Zaversnik). Repeatedly remove the lowest-degree
// node; its coreness is its degree at removal time. Subsequent removals can
// trigger cascading degree drops, so we maintain a degree map and a
// bucket-sort of nodes-by-degree to keep the inner loop O(1).
// --------------------------------------------------------------------------

function computeKCore(
  nodes: string[],
  adj: Map<string, Set<string>>
): Map<string, number> {
  const deg = new Map<string, number>();
  let maxDeg = 0;
  for (const v of nodes) {
    const d = adj.get(v)!.size;
    deg.set(v, d);
    if (d > maxDeg) maxDeg = d;
  }

  // Bucket b[d] = set of nodes whose current degree is d.
  const buckets: Set<string>[] = [];
  for (let i = 0; i <= maxDeg; i++) buckets.push(new Set());
  for (const v of nodes) buckets[deg.get(v)!].add(v);

  const coreness = new Map<string, number>();
  const removed = new Set<string>();

  // Track the running min so we can advance the cursor instead of rescanning
  // from 0 each iteration.
  let cursor = 0;
  let remaining = nodes.length;
  while (remaining > 0) {
    while (cursor <= maxDeg && buckets[cursor].size === 0) cursor++;
    if (cursor > maxDeg) break;
    const v = buckets[cursor].values().next().value as string;
    buckets[cursor].delete(v);
    coreness.set(v, cursor);
    removed.add(v);
    remaining--;
    // Decrement neighbours that haven't been removed yet.
    for (const w of adj.get(v)!) {
      if (removed.has(w)) continue;
      const dw = deg.get(w)!;
      // A removed-neighbour's effective degree dwʹ goes down by 1, BUT
      // it cannot drop below the cursor — once we've passed degree k,
      // anything still in the graph belongs to (k+1)-core or higher, so
      // floor at cursor.
      const dwNext = Math.max(cursor, dw - 1);
      if (dwNext !== dw) {
        buckets[dw].delete(w);
        buckets[dwNext].add(w);
        deg.set(w, dwNext);
      }
    }
  }
  // Any unreached node (shouldn't happen since we process all) defaults to 0.
  for (const v of nodes) if (!coreness.has(v)) coreness.set(v, 0);
  return coreness;
}

// --------------------------------------------------------------------------
// Rank helper: dense rank, highest value = rank 1. Ties share a rank.
// --------------------------------------------------------------------------

function denseRank(scores: Map<string, number>): Map<string, number> {
  const arr = [...scores.entries()].sort((a, b) => b[1] - a[1]);
  const rank = new Map<string, number>();
  let cur = 0;
  let prev = Number.POSITIVE_INFINITY;
  for (let i = 0; i < arr.length; i++) {
    const [k, v] = arr[i];
    if (v < prev) {
      cur = i + 1;
      prev = v;
    }
    rank.set(k, cur);
  }
  return rank;
}

// --------------------------------------------------------------------------
// Public entrypoint.
// --------------------------------------------------------------------------

/**
 * Compute betweenness, k-core, and bridge-surprise for every record in the
 * catalog. Pure function — same input, same output, no side effects.
 *
 * Performance: O(V*E) for Brandes, O(E) for k-core. On 912 nodes / 514
 * undirected edges this completes in <100ms on a modern laptop; the
 * dominant cost is the V BFS traversals in Brandes.
 */
export function computeCentrality(
  records: LandscapeRecord[],
  edges: Edge[]
): CentralityOutput {
  const { adj, undirectedEdgeCount } = buildAdjacency(records, edges);
  const nodes = records.map((r) => r.id);

  const betweenness = computeBetweenness(nodes, adj);
  const coreness = computeKCore(nodes, adj);

  // Normalise betweenness to [0, 1] by max-in-graph.
  let maxBw = 0;
  for (const v of betweenness.values()) if (v > maxBw) maxBw = v;
  const normBw = new Map<string, number>();
  for (const [k, v] of betweenness) normBw.set(k, maxBw > 0 ? v / maxBw : 0);

  // Raw inbound counts — keep parity with the original "influence" metric
  // by including ALL edge types (not just cites). This matches what the
  // user sees in the influence view tooltip ("citations in" + "integrations
  // in" + "runtime-deps in" — combined they are the inbound centrality).
  const inboundAll = new Map<string, number>();
  for (const e of edges) {
    if (e.source === e.target) continue;
    inboundAll.set(e.target, (inboundAll.get(e.target) ?? 0) + 1);
  }
  // Ensure every record id has an entry, even if 0, so ranking stays stable.
  for (const id of nodes) if (!inboundAll.has(id)) inboundAll.set(id, 0);

  const bwRank = denseRank(normBw);
  const inRank = denseRank(inboundAll);

  // Compose results. Map record id → record so we can decorate with name/section.
  const recById = new Map(records.map((r) => [r.id, r]));
  const results: CentralityResult[] = [];
  for (const id of nodes) {
    const r = recById.get(id)!;
    const bw = normBw.get(id) ?? 0;
    const kc = coreness.get(id) ?? 0;
    const ic = inboundAll.get(id) ?? 0;
    // bridgeSurprise: positive = sits on more shortest paths than raw
    // inbound count suggests = bridge between clusters. Inbound-rank minus
    // betweenness-rank (lower rank number = better, so a big betweenness
    // rank improvement over inbound rank yields a positive surprise).
    const surprise = (inRank.get(id) ?? 0) - (bwRank.get(id) ?? 0);
    results.push({
      recordId: id,
      recordName: r.name,
      section: primarySection(r),
      inboundCount: ic,
      betweenness: bw,
      kCore: kc,
      bridgeSurprise: surprise
    });
  }

  // Top bridge surprises: positive surprise only, must have non-zero
  // betweenness (otherwise it's just a low-inbound record with no
  // structural role — uninteresting). Sort by surprise desc, then by
  // betweenness desc as tiebreak.
  const topBridgeSurprises = results
    .filter((r) => r.bridgeSurprise > 0 && r.betweenness > 0)
    .sort((a, b) => {
      if (b.bridgeSurprise !== a.bridgeSurprise)
        return b.bridgeSurprise - a.bridgeSurprise;
      return b.betweenness - a.betweenness;
    })
    .slice(0, 10);

  // K-core distribution + nucleus.
  const kCoreDistribution: Record<number, number> = {};
  let maxKCore = 0;
  for (const r of results) {
    kCoreDistribution[r.kCore] = (kCoreDistribution[r.kCore] ?? 0) + 1;
    if (r.kCore > maxKCore) maxKCore = r.kCore;
  }
  const nucleus = results
    .filter((r) => r.kCore === maxKCore && maxKCore > 0)
    .sort((a, b) => b.betweenness - a.betweenness);

  return {
    results,
    topBridgeSurprises,
    nucleus,
    maxKCore,
    kCoreDistribution,
    nodeCount: nodes.length,
    undirectedEdgeCount
  };
}

// --------------------------------------------------------------------------
// Convenience: lookup a CentralityResult by record id from a results array.
// --------------------------------------------------------------------------

export function centralityById(
  results: CentralityResult[]
): Map<string, CentralityResult> {
  const m = new Map<string, CentralityResult>();
  for (const r of results) m.set(r.recordId, r);
  return m;
}

// --------------------------------------------------------------------------
// Colour ramp for k-core. We map [0, maxKCore] onto a blue → red spectrum
// so the periphery reads cool and the nucleus reads warm. Exposed as a
// pure function so the legend renders the same swatches as the markers.
// --------------------------------------------------------------------------

const K_CORE_RAMP = [
  '#3a5fa8', // blue (periphery)
  '#5f8fbf',
  '#7fb0c4',
  '#c0a878',
  '#d49765',
  '#d4754a',
  '#c44e3a',
  '#a83232' // deep red (nucleus)
];

export function kCoreColor(kCore: number, maxKCore: number): string {
  if (maxKCore <= 0) return K_CORE_RAMP[0];
  // Spread kCore values across ramp slots; clamp to last index.
  const idx = Math.min(
    K_CORE_RAMP.length - 1,
    Math.floor((kCore / maxKCore) * (K_CORE_RAMP.length - 1) + 0.0001)
  );
  return K_CORE_RAMP[Math.max(0, idx)];
}

/** Discrete colour swatches for the k-core legend, indexed 0..maxKCore. */
export function kCoreLegendSwatches(
  maxKCore: number
): Array<{ kCore: number; color: string }> {
  const out: Array<{ kCore: number; color: string }> = [];
  for (let k = 0; k <= maxKCore; k++) {
    out.push({ kCore: k, color: kCoreColor(k, maxKCore) });
  }
  return out;
}

// Re-export for type ergonomics in callers.
export type { Edge, LandscapeRecord };
