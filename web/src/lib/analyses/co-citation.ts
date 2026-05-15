// Pure helpers for the co-citation + bibliographic-coupling map (issue #45, T2-2).
//
// Bibliometric staple since Henry Small 1973 ("Co-Citation in the Scientific
// Literature: A New Measure of the Relationship between Two Documents"). Every
// serious tech-landscape uses it. The two operations are duals over the same
// edge set:
//
//   Co-citation        : count records X that cite BOTH A and B.
//                        High co-citation = community pairs A and B together.
//   Bibliographic-coupling : count records X that A AND B both cite.
//                        High coupling = A and B share intellectual lineage.
//
// Cosine-similarity normalises both by sqrt(degree(A) * degree(B)), so a
// frequently-cited paper doesn't dominate every pair it lands in.
//
// **Why this matters**: clustering by community-pairing instead of self-
// reported attributes catches mismatches between how the community thinks
// systems group and how the catalog's hand-built taxonomy groups them. We
// surface those mismatches as the headline finding — that's the novel
// signal no comparable catalog publishes.
//
// All exports are pure — no DOM, no Cytoscape — so the view file stays thin
// and the same numbers can be sanity-checked from `node -e` without Vite.
//
// Complexity: O(R^2) over records, but R ≈ 912 and most rows have zero
// citations, so the actual inner loop runs on ~250 source records and
// terminates well under 100ms. The result is capped at 500 pairs for
// Cytoscape rendering performance.

import type { Edge, LandscapeRecord } from '../types';
import { primarySection } from '../leaderboards';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface SimilarityPair {
  a: string;
  b: string;
  aName: string;
  bName: string;
  /** Cosine similarity in [0, 1]. */
  similarity: number;
  /** Raw count of shared neighbours used in the numerator. */
  sharedCount: number;
  aSection?: string;
  bSection?: string;
  /** True when both records sit in the same primary section. */
  taxonomyAgrees: boolean;
}

export type CoCitationMode = 'co-citation' | 'bibliographic-coupling';

/** Variant selector for the co-citation algorithm. */
export type CoCitationVariant = 'cites-only' | 'any-edge';

export interface CoCitationResult {
  mode: CoCitationMode;
  /** Variant selector — only meaningful for co-citation mode (kept on
   *  bib-coupling for symmetry). */
  variant: CoCitationVariant;
  /** All pairs that cleared the similarity threshold, capped at MAX_PAIRS. */
  pairs: SimilarityPair[];
  /** Top 20 pairs by similarity, all sections. */
  topPairs: SimilarityPair[];
  /** Pairs with similarity > DISAGREEMENT_SIM_THRESHOLD but different
   *  primary sections. This is the novel finding the view surfaces. */
  disagreementPairs: SimilarityPair[];
  /** Records that appear in at least one surviving pair. Useful for
   *  driving the Cytoscape node list. */
  nodes: Array<{ id: string; name: string; section: string }>;
  /** Total ordered pairs considered before the similarity filter. */
  consideredPairs: number;
}

// ---------------------------------------------------------------------------
// Tuning constants
// ---------------------------------------------------------------------------

/** Drop pairs below this similarity — otherwise the matrix is mostly noise.
 *  0.1 matches the issue spec; it filters ~99% of accidental single-overlap
 *  pairs while keeping every pair where the community signal is meaningful. */
export const SIMILARITY_THRESHOLD = 0.1;

/** Pairs above this are flagged as "community-close, taxonomy-far" when
 *  they sit in different primary sections. 0.5 is the cosine equivalent
 *  of "half the maximum possible overlap" — high enough that the pair is
 *  genuinely close, low enough that the disagreement signal isn't empty. */
export const DISAGREEMENT_SIM_THRESHOLD = 0.5;

/** Cap on pairs returned for visualisation. Cytoscape with fcose holds up
 *  fine to ~1000 edges; we cap at 500 to leave headroom and because the
 *  long-tail pairs add visual noise more than signal. */
export const MAX_PAIRS = 500;

/** Top-N list shown in the side panel. */
export const TOP_PAIRS_LIMIT = 20;

// ---------------------------------------------------------------------------
// Internal index builders
// ---------------------------------------------------------------------------

interface AdjacencyIndex {
  /** record-id → set of record-ids this row points TO (outbound). */
  outbound: Map<string, Set<string>>;
  /** record-id → set of record-ids that point TO this row (inbound). */
  inbound: Map<string, Set<string>>;
}

/**
 * Build outbound + inbound adjacency from a filtered edge list. We use Sets
 * (not arrays) so the set-intersection in the similarity inner loop is
 * O(min(|A|, |B|)) instead of O(|A| * |B|).
 */
function buildAdjacency(edges: Edge[]): AdjacencyIndex {
  const outbound = new Map<string, Set<string>>();
  const inbound = new Map<string, Set<string>>();
  const bump = (m: Map<string, Set<string>>, k: string, v: string) => {
    let s = m.get(k);
    if (!s) {
      s = new Set<string>();
      m.set(k, s);
    }
    s.add(v);
  };
  for (const e of edges) {
    // De-duplicate parallel edges of multiple types between the same pair —
    // for similarity computation we only care whether a relationship
    // exists, not how many distinct edge types declare it.
    bump(outbound, e.source, e.target);
    bump(inbound, e.target, e.source);
  }
  return { outbound, inbound };
}

/**
 * Intersection size between two sets. We iterate the smaller set and probe
 * the larger one — Set#has is O(1) amortised.
 */
function intersectSize(a: Set<string>, b: Set<string>): number {
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  let count = 0;
  for (const x of small) if (large.has(x)) count += 1;
  return count;
}

// ---------------------------------------------------------------------------
// Core: pairs from an adjacency map
// ---------------------------------------------------------------------------

/**
 * Compute similarity pairs from a single side of the adjacency map.
 *
 *   For co-citation:        pass `inbound`.   (Both targets share inbound
 *                                              edges = both are cited by
 *                                              the same record.)
 *   For bibliographic coupling: pass `outbound`. (Both sources point to
 *                                                 the same target = they
 *                                                 share an out-neighbour.)
 *
 * Returns all pairs above SIMILARITY_THRESHOLD, sorted descending by
 * similarity and capped at MAX_PAIRS.
 */
function pairsFromAdjacency(
  side: Map<string, Set<string>>,
  records: LandscapeRecord[]
): { pairs: SimilarityPair[]; consideredPairs: number } {
  // We only iterate records that actually appear on this side of the
  // adjacency — i.e. records with at least one relevant edge. The rest
  // contribute zero pairs and we'd just waste loop iterations on them.
  const candidates = records.filter((r) => (side.get(r.id)?.size ?? 0) > 0);
  const indexById = new Map<string, LandscapeRecord>();
  for (const r of records) indexById.set(r.id, r);

  const pairs: SimilarityPair[] = [];
  let considered = 0;
  for (let i = 0; i < candidates.length; i += 1) {
    const a = candidates[i];
    const aSet = side.get(a.id);
    if (!aSet || aSet.size === 0) continue;
    const aSection = primarySection(a);
    for (let j = i + 1; j < candidates.length; j += 1) {
      const b = candidates[j];
      const bSet = side.get(b.id);
      if (!bSet || bSet.size === 0) continue;
      considered += 1;
      const shared = intersectSize(aSet, bSet);
      if (shared === 0) continue;
      const denom = Math.sqrt(aSet.size * bSet.size);
      if (denom === 0) continue;
      const sim = shared / denom;
      if (sim < SIMILARITY_THRESHOLD) continue;
      const bSection = primarySection(b);
      pairs.push({
        a: a.id,
        b: b.id,
        aName: a.name,
        bName: b.name,
        similarity: sim,
        sharedCount: shared,
        aSection,
        bSection,
        taxonomyAgrees: aSection === bSection
      });
    }
  }

  // Sort descending by similarity, ties broken by sharedCount (more shared
  // neighbours = stronger evidence at the same cosine score), then alpha
  // for determinism so repeated builds produce identical output.
  pairs.sort((x, y) => {
    if (y.similarity !== x.similarity) return y.similarity - x.similarity;
    if (y.sharedCount !== x.sharedCount) return y.sharedCount - x.sharedCount;
    const ka = `${x.a}|${x.b}`;
    const kb = `${y.a}|${y.b}`;
    return ka.localeCompare(kb);
  });

  return { pairs: pairs.slice(0, MAX_PAIRS), consideredPairs: considered };
}

// ---------------------------------------------------------------------------
// Node list extraction
// ---------------------------------------------------------------------------

function nodesFromPairs(
  pairs: SimilarityPair[],
  records: LandscapeRecord[]
): Array<{ id: string; name: string; section: string }> {
  const present = new Set<string>();
  for (const p of pairs) {
    present.add(p.a);
    present.add(p.b);
  }
  const out: Array<{ id: string; name: string; section: string }> = [];
  for (const r of records) {
    if (!present.has(r.id)) continue;
    out.push({ id: r.id, name: r.name, section: primarySection(r) });
  }
  // Stable alpha sort so the Cytoscape element order matches between
  // identical builds (helps fcose's randomize seed produce a similar layout
  // after small data changes).
  out.sort((x, y) => x.name.localeCompare(y.name));
  return out;
}

function disagreements(pairs: SimilarityPair[]): SimilarityPair[] {
  return pairs.filter(
    (p) => !p.taxonomyAgrees && p.similarity > DISAGREEMENT_SIM_THRESHOLD
  );
}

// ---------------------------------------------------------------------------
// Public builders
// ---------------------------------------------------------------------------

/**
 * Co-citation. For each ordered pair (A, B), count records X where
 * (X → A) AND (X → B). cosine = shared / sqrt(inbound_A * inbound_B).
 *
 * Variant:
 *   - 'cites-only': only `cites` edges, the academic-style co-citation
 *      Henry Small originally defined.
 *   - 'any-edge':  ANY edge type counts as a "citation" in the loose sense.
 *      Useful because many of our community signals (built-on, integrates-
 *      with, runtime-dependency) carry the same "X groups A and B
 *      together" semantics.
 */
export function computeCoCitation(
  records: LandscapeRecord[],
  edges: Edge[],
  variant: CoCitationVariant = 'cites-only'
): CoCitationResult {
  const filtered = variant === 'cites-only' ? edges.filter((e) => e.type === 'cites') : edges;
  const idx = buildAdjacency(filtered);
  const { pairs, consideredPairs } = pairsFromAdjacency(idx.inbound, records);
  return {
    mode: 'co-citation',
    variant,
    pairs,
    topPairs: pairs.slice(0, TOP_PAIRS_LIMIT),
    disagreementPairs: disagreements(pairs),
    nodes: nodesFromPairs(pairs, records),
    consideredPairs
  };
}

/**
 * Bibliographic coupling. For each ordered pair (A, B), count records X
 * where (A → X) AND (B → X). cosine = shared / sqrt(outbound_A * outbound_B).
 *
 * Uses ANY edge type — bib-coupling is conceptually about shared lineage,
 * and our edge taxonomy is rich enough (built-on, cites, runtime-dep,
 * etc.) that restricting to `cites` would throw away too much signal.
 */
export function computeBibCoupling(
  records: LandscapeRecord[],
  edges: Edge[]
): CoCitationResult {
  const idx = buildAdjacency(edges);
  const { pairs, consideredPairs } = pairsFromAdjacency(idx.outbound, records);
  return {
    mode: 'bibliographic-coupling',
    variant: 'any-edge',
    pairs,
    topPairs: pairs.slice(0, TOP_PAIRS_LIMIT),
    disagreementPairs: disagreements(pairs),
    nodes: nodesFromPairs(pairs, records),
    consideredPairs
  };
}
