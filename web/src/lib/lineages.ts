// Lineage detection for the /lineages view (issue #17).
//
// A "lineage" is a connected component in a sub-graph of the citation /
// build-on graph that follows *structural-descent* edges. Two well-known
// families (RSSM world-models, GraphRAG hierarchy) are pre-seeded with
// curated anchors; everything else is auto-discovered by union-find over
// the remaining structural-descent edges.
//
// Edge-type weighting (see docs/DECISIONS.md):
//   - Strong (definitely descent):  built-on, extends, forks, succeeds
//   - Weak   (descent if influential): cites with isInfluential === true
//   - Excluded: cites without isInfluential, integrates-with, competes-with,
//     inspired-by, same-team-as — these are not "X descends from Y".
//
// All functions in this module are pure: feed it records + edges, get back
// data. The page (`+page.svelte`) handles layout and rendering.
//
// Reused by Phase 5 (publish/share): the same connected-component logic
// will gate "show only nodes inside a named lineage" overlays on the
// graph (#16) and feed the "history of X" narrative blurbs we want to
// surface on share cards.

import type { Edge, EdgeType, LandscapeRecord } from '$lib/types';
import { parseCreatedDate } from '$lib/timeline';

/** Edge types that count as structural descent — i.e., "B was built from
 *  A" rather than "B is in the same neighbourhood as A". */
export const STRONG_DESCENT_TYPES: ReadonlySet<EdgeType> = new Set<EdgeType>([
  'built-on',
  'extends',
  'forks',
  'succeeds'
]);

/** `cites` with isInfluential = true is the weakest signal we still keep.
 *  Non-influential cites are too numerous and noisy to imply descent. */
export const WEAK_DESCENT_TYPE: EdgeType = 'cites';

/**
 * Lineage kind:
 *
 *  - `'descent'` — a parent→child chain in the structural-descent graph
 *    (built-on / extends / forks / succeeds / influential cites). The two
 *    seeded research-paper lineages (RSSM, Graph-RAG) and every
 *    auto-discovered lineage live in this bucket. Renders with solid
 *    arrows.
 *
 *  - `'pattern'` — a family that converged on the same architectural
 *    pattern by parallel evolution. Members have no descent edges between
 *    them; we surface the family anyway because the pattern is one of the
 *    dominant production memory shapes. Renders with dashed
 *    "parallel-implementations" links and a distinct track label.
 *
 *  Why the split: descent-lineage rendering uses bezier arrows that imply
 *  "B was built from A". Applying that visual to a pattern family
 *  (e.g. file-backed memory across Cursor / Claude Code / Aider) would
 *  miscommunicate the relationship. The kind field lets the rendering
 *  pass make the semantic distinction explicit.
 */
export type LineageKind = 'descent' | 'pattern';

export interface Lineage {
  id: string;
  /** Human-readable family name, derived from the anchor record. */
  name: string;
  /** Record id of the oldest (earliest `created`) member. */
  anchor: string;
  /** All record ids in the connected component, ordered by created date asc. */
  members: string[];
  /** Edges between members (subset of the input edges). Empty for
   *  pattern lineages (no real edges; the renderer draws virtual
   *  "parallel-implementations" links between consecutive members). */
  edges: Edge[];
  /** True if this lineage was hand-curated; false if auto-discovered. */
  curated: boolean;
  /** Descent (default) vs pattern (parallel implementations of an idea). */
  kind: LineageKind;
}

export interface DetectOptions {
  /** Max number of total lineages to return (curated + auto combined).
   *  Default: 8. */
  topN?: number;
  /** Minimum member count for an auto-detected lineage to qualify. Default: 3. */
  minSize?: number;
  /** BFS hop limit when expanding curated seeds. Default: 2. Caps the
   *  reach so the influential-cite backbone doesn't collapse two
   *  curated families into one giant component. */
  curatedMaxDepth?: number;
}

/** Curated lineage seeds. These two families are named in `analysis.md`
 *  and confirmed by issue #5 (S2 citation pull). We seed them with an
 *  anchor id and a display name; the actual member set is computed by
 *  BFS/union-find inside `detectLineages` so the curated bucket always
 *  matches the live data. */
interface CuratedSeed {
  id: string;
  name: string;
  /** Anchor record id — must exist in records. If missing we silently
   *  drop the seed (defensive: lineage IDs can churn). */
  anchorId: string;
  /** Default: 'descent'. Pattern seeds expand by section membership
   *  rather than by descent-edge BFS — see materialiseCuratedSeed(). */
  kind?: LineageKind;
  /** Pattern seeds only: catalog section names whose member records
   *  qualify for the lineage. Records in any of these sections (primary
   *  OR secondary placement) are included. */
  sections?: readonly string[];
  /** Pattern seeds only: explicit record-id list when section-membership
   *  doesn't cleanly carve out the pattern. Members may live across
   *  multiple sections (e.g. Specs-as-memory spans 'Agent IDEs & coding
   *  harnesses' and 'File-backed / editor paradigms'). When both
   *  `sections` and `explicitMembers` are set, the union is taken. */
  explicitMembers?: readonly string[];
}

const CURATED_SEEDS: CuratedSeed[] = [
  {
    id: 'rssm-world-model',
    name: 'RSSM / world-model family',
    anchorId: 'dreamerv3--arxiv-2301-04104',
    kind: 'descent'
  },
  {
    id: 'graph-rag-hierarchy',
    name: 'Graph-RAG hierarchy',
    anchorId: 'graphrag-microsoft--microsoft-com',
    kind: 'descent'
  },
  // Files-as-memory: parallel implementations of the "text file the model
  // reads at session start" pattern. Members have no descent edges; we
  // expand by section membership instead. Anchor on CLAUDE.md as the
  // canonical / most-referenced exemplar (Cursor / Aider predate it
  // chronologically but CLAUDE.md is the most-recognised name for the
  // pattern). The earliest member by created date becomes the
  // visual anchor at render time — see oldestMember(). The string anchorId
  // is the "preferred" anchor; if it's not the oldest, oldestMember()
  // overrides.
  {
    id: 'files-as-memory',
    name: 'Files-as-memory thread',
    anchorId: 'claude-md--docs-claude-com',
    kind: 'pattern',
    sections: [
      'File-backed / editor paradigms',
      'Claude Code memory mechanisms'
    ]
  },
  // Specs-as-memory: parallel convergence on durable structured workflow
  // files (Requirements / Design / Tasks, mode files, memory-bank
  // schemas) committed to source control as the agent's working memory.
  // Distinct from Files-as-memory (CLAUDE.md / Cursor Rules / AGENTS.md)
  // which is unstructured documentation — specs-as-memory rows expose
  // *structured* workflow stages with named files per stage. Anchor on
  // Kiro because it's the most-explicit "spec-driven" framing; Windsurf
  // Cascade is older but spec-driven was a posture-tightening rather
  // than the launch framing. Members live across multiple sections so
  // we enumerate explicitly rather than expand by section. Surfaced by
  // the Round-11 ingestion notes (extraction/round-11-ingestion.md
  // "Possible new lineages" section).
  {
    id: 'specs-as-memory',
    name: 'Specs-as-memory thread',
    anchorId: 'kiro--kiro-dev',
    kind: 'pattern',
    explicitMembers: [
      'kiro--kiro-dev',
      'windsurf-codeium-openai--windsurf-com',
      'cognition-devin-v2-spec-mode--cognition-ai',
      'cline-memory-bank--docs-cline-bot',
      'roo-code--roocode-com'
    ]
  },
  // State-space models: linear-time sequence models that converged on the
  // same architectural insight (selective SSMs / structured state-space
  // duality) by parallel evolution. Hyena seeded the long-convolution
  // framing in 2023; Mamba (2023) introduced selective SSMs; Mamba-2
  // (2024) unified them with attention via SSD; Jamba (2024) hybridised
  // SSM with transformer blocks; RWKV-7 (2024) is the linear-RNN sibling.
  // Members have no built-on edges between them — they're parallel
  // implementations of the linear-time-sequence-model pattern, hence
  // `kind: 'pattern'`. Anchor on Mamba as the most-recognised exemplar;
  // oldestMember() will override to Hyena if dates dictate.
  {
    id: 'ssm-state-space',
    name: 'State-space models',
    anchorId: 'mamba--arxiv-2312-00752',
    kind: 'pattern',
    explicitMembers: [
      'hyena--arxiv-2302-10866',
      'mamba--arxiv-2312-00752',
      'mamba-2-ssd--arxiv-2405-21060',
      'jamba-ai21--ai21-com',
      'rwkv-7--gh-blinkdl-rwkv-lm'
    ]
  }
];

/** Year used when a record has no parseable `created` date — pushes it
 *  to the end of the sort so the anchor is always a record with a real
 *  date when one exists in the component. */
const UNDATED_YEAR = 9999;

interface DatedRecord {
  id: string;
  year: number;
  quarterNum: number; // 1..4
}

function dateOf(r: LandscapeRecord): DatedRecord {
  const parsed = parseCreatedDate(r.cells.created?.value);
  if (!parsed) return { id: r.id, year: UNDATED_YEAR, quarterNum: 1 };
  return { id: r.id, year: parsed.year, quarterNum: parsed.quarter };
}

function dateKey(d: DatedRecord): number {
  return d.year * 10 + d.quarterNum;
}

/** Union-Find / Disjoint-Set with path compression + union by size. Pure
 *  data structure — no Svelte deps, easy to test. */
class DSU {
  private parent = new Map<string, string>();
  private size = new Map<string, number>();

  add(x: string): void {
    if (!this.parent.has(x)) {
      this.parent.set(x, x);
      this.size.set(x, 1);
    }
  }

  find(x: string): string {
    let r = this.parent.get(x) ?? x;
    if (!this.parent.has(x)) {
      this.add(x);
      return x;
    }
    // Path compression — walk to root, then re-point everyone.
    const path: string[] = [];
    while (r !== this.parent.get(r)) {
      path.push(r);
      r = this.parent.get(r)!;
    }
    for (const p of path) this.parent.set(p, r);
    return r;
  }

  union(a: string, b: string): void {
    const ra = this.find(a);
    const rb = this.find(b);
    if (ra === rb) return;
    const sa = this.size.get(ra) ?? 1;
    const sb = this.size.get(rb) ?? 1;
    if (sa < sb) {
      this.parent.set(ra, rb);
      this.size.set(rb, sa + sb);
    } else {
      this.parent.set(rb, ra);
      this.size.set(ra, sa + sb);
    }
  }

  /** Group all currently-known ids by root. */
  components(): Map<string, string[]> {
    const out = new Map<string, string[]>();
    for (const x of this.parent.keys()) {
      const r = this.find(x);
      const bucket = out.get(r) ?? [];
      bucket.push(x);
      out.set(r, bucket);
    }
    return out;
  }
}

/** True if this edge type counts as a descent signal for lineage detection. */
export function isDescentEdge(e: Edge): boolean {
  if (STRONG_DESCENT_TYPES.has(e.type)) return true;
  if (e.type === WEAK_DESCENT_TYPE && e.isInfluential === true) return true;
  return false;
}

/** Depth-limited BFS within a sub-graph reachable through descent edges
 *  from a seed. Used to materialise curated lineages.
 *
 *  Why depth-limited: the influential-cite edge is permissive enough that
 *  most of the research-paper sub-graph is one giant connected component
 *  (~120 nodes). Walking that unbounded would make every curated seed
 *  collapse into the same component. Capping depth (default 2 hops) keeps
 *  the curated lineage focused on the named family's immediate descendants
 *  while still picking up grand-children. */
function expandComponent(
  seed: string,
  adj: Map<string, Set<string>>,
  maxDepth: number
): Set<string> {
  const seen = new Map<string, number>([[seed, 0]]);
  const queue: Array<{ id: string; depth: number }> = [{ id: seed, depth: 0 }];
  while (queue.length > 0) {
    const { id, depth } = queue.shift()!;
    if (depth >= maxDepth) continue;
    const neighbours = adj.get(id);
    if (!neighbours) continue;
    for (const n of neighbours) {
      if (!seen.has(n)) {
        seen.set(n, depth + 1);
        queue.push({ id: n, depth: depth + 1 });
      }
    }
  }
  return new Set(seen.keys());
}

/** Build an undirected adjacency map from descent edges only. */
function buildAdj(edges: Edge[], validIds: Set<string>): Map<string, Set<string>> {
  const adj = new Map<string, Set<string>>();
  for (const e of edges) {
    if (!isDescentEdge(e)) continue;
    if (!validIds.has(e.source) || !validIds.has(e.target)) continue;
    if (!adj.has(e.source)) adj.set(e.source, new Set());
    if (!adj.has(e.target)) adj.set(e.target, new Set());
    adj.get(e.source)!.add(e.target);
    adj.get(e.target)!.add(e.source);
  }
  return adj;
}

/** Pick the oldest record in a set, breaking ties by lexicographic id. */
function oldestMember(memberIds: string[], byId: Map<string, LandscapeRecord>): string {
  let best: { id: string; key: number } | null = null;
  for (const id of memberIds) {
    const r = byId.get(id);
    if (!r) continue;
    const d = dateOf(r);
    const key = dateKey(d);
    if (!best || key < best.key || (key === best.key && id < best.id)) {
      best = { id, key };
    }
  }
  return best?.id ?? memberIds[0];
}

/** Collect the edges that lie entirely inside a given member set. */
function edgesWithin(memberSet: Set<string>, allEdges: Edge[]): Edge[] {
  return allEdges.filter(
    (e) =>
      isDescentEdge(e) && memberSet.has(e.source) && memberSet.has(e.target)
  );
}

/** Sort member ids by their record's created date ascending. */
function sortByDate(ids: string[], byId: Map<string, LandscapeRecord>): string[] {
  return [...ids].sort((a, b) => {
    const ra = byId.get(a);
    const rb = byId.get(b);
    const ka = ra ? dateKey(dateOf(ra)) : Infinity;
    const kb = rb ? dateKey(dateOf(rb)) : Infinity;
    if (ka !== kb) return ka - kb;
    return a.localeCompare(b);
  });
}

/**
 * Detect lineages. Returns curated seeds first (in declaration order),
 * then auto-discovered components by size desc, capped at `topN` total.
 */
export function detectLineages(
  records: LandscapeRecord[],
  edges: Edge[],
  options?: DetectOptions
): Lineage[] {
  const topN = options?.topN ?? 8;
  const minSize = options?.minSize ?? 3;
  const curatedMaxDepth = options?.curatedMaxDepth ?? 2;

  const byId = new Map<string, LandscapeRecord>();
  for (const r of records) byId.set(r.id, r);
  const validIds = new Set(byId.keys());

  // Undirected adjacency over descent edges only — shared by curated
  // BFS expansion and the union-find pass.
  const adj = buildAdj(edges, validIds);

  // 1. Curated seeds: descent seeds expand through the descent sub-graph
  //    via depth-limited BFS; pattern seeds expand by section membership
  //    (members converged on the pattern, no descent edges between them).
  const claimed = new Set<string>();
  const curatedLineages: Lineage[] = [];
  for (const seed of CURATED_SEEDS) {
    if (!byId.has(seed.anchorId)) continue;
    const kind: LineageKind = seed.kind ?? 'descent';
    let memberSet: Set<string>;
    let lineageEdges: Edge[];
    if (kind === 'pattern') {
      // Pattern lineage: gather records whose section memberships
      // intersect the seed's section list, plus any explicit members
      // listed by id. Either or both may be provided.
      const wantSections = new Set(seed.sections ?? []);
      const found = new Set<string>();
      if (wantSections.size > 0) {
        for (const r of records) {
          for (const s of r.sections) {
            if (wantSections.has(s.section)) {
              found.add(r.id);
              break;
            }
          }
        }
      }
      for (const id of seed.explicitMembers ?? []) {
        if (byId.has(id)) found.add(id);
      }
      memberSet = found;
      // No real descent edges between pattern members. The renderer
      // synthesises virtual "parallel-implementations" links at draw time.
      lineageEdges = [];
    } else {
      memberSet = expandComponent(seed.anchorId, adj, curatedMaxDepth);
      lineageEdges = edgesWithin(memberSet, edges);
    }
    const memberIds = sortByDate([...memberSet], byId);
    for (const id of memberIds) claimed.add(id);
    // Use the seed's preferred anchor when it's in the member set;
    // otherwise fall back to the oldest member.
    const anchor = memberSet.has(seed.anchorId)
      ? seed.anchorId
      : oldestMember(memberIds, byId);
    curatedLineages.push({
      id: seed.id,
      name: seed.name,
      anchor,
      members: memberIds,
      edges: lineageEdges,
      curated: true,
      kind
    });
  }

  // 2. Auto-discovery: union-find over remaining nodes (everything that
  //    wasn't claimed by a curated seed). We add every record so isolated
  //    nodes don't break the algorithm; they're filtered by minSize below.
  const dsu = new DSU();
  for (const r of records) {
    if (claimed.has(r.id)) continue;
    dsu.add(r.id);
  }
  for (const e of edges) {
    if (!isDescentEdge(e)) continue;
    if (claimed.has(e.source) || claimed.has(e.target)) continue;
    if (!validIds.has(e.source) || !validIds.has(e.target)) continue;
    dsu.union(e.source, e.target);
  }

  const auto: Lineage[] = [];
  for (const [root, members] of dsu.components()) {
    if (members.length < minSize) continue;
    const memberSet = new Set(members);
    const sorted = sortByDate(members, byId);
    const anchorId = oldestMember(sorted, byId);
    const anchorRec = byId.get(anchorId);
    auto.push({
      id: `auto-${root}`,
      name: anchorRec ? `${anchorRec.name} family` : `Lineage @ ${anchorId}`,
      anchor: anchorId,
      members: sorted,
      edges: edgesWithin(memberSet, edges),
      curated: false,
      kind: 'descent'
    });
  }
  // Sort auto-discovered lineages by size desc, then by anchor date asc.
  auto.sort((a, b) => {
    if (b.members.length !== a.members.length) {
      return b.members.length - a.members.length;
    }
    const ra = byId.get(a.anchor);
    const rb = byId.get(b.anchor);
    const ka = ra ? dateKey(dateOf(ra)) : Infinity;
    const kb = rb ? dateKey(dateOf(rb)) : Infinity;
    return ka - kb;
  });

  // 3. Combine curated (in order) + top auto-discovered, capped at topN.
  const out: Lineage[] = [...curatedLineages];
  for (const l of auto) {
    if (out.length >= topN) break;
    out.push(l);
  }
  return out;
}

/** Helper: get the (year, quarter, fractional) for plotting on a date
 *  axis. Returns null if the record's created cell is unparseable. */
export function plotDate(
  r: LandscapeRecord
): { year: number; quarter: 1 | 2 | 3 | 4; t: number } | null {
  const parsed = parseCreatedDate(r.cells.created?.value);
  if (!parsed) return null;
  // t = year + (quarter-1)/4 → continuous axis in years.
  return {
    year: parsed.year,
    quarter: parsed.quarter,
    t: parsed.year + (parsed.quarter - 1) / 4
  };
}
