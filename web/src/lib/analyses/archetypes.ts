// Issue #25 — Taxonomy archetypes (co-occurrence clustering).
//
// Cluster every record by its 7-axis primary-only taxonomy fingerprint.
// Recurring fingerprints are "archetypes" — recipes that recur across
// many systems. Singleton fingerprints are the "everyone's doing
// something custom" long tail.
//
// Pure helpers only — no Svelte, no DOM. The route renders these.
//
// Design notes:
//   - We use the *primary* value on each axis, never the full array.
//     Multi-value axes legitimately exist (a system can be both
//     vector+graph), but if we hashed the full sorted set we would
//     either (a) split the canonical "vector-similarity-long-term"
//     archetype across half a dozen near-duplicates or (b) collapse
//     genuinely different secondary patterns. Primary-only matches
//     how /sections and the filter rail already collapse a row to a
//     single axis value (see DECISIONS.md 2026-05-08: always-array
//     for taxonomy → primary flag is exactly the disambiguator).
//   - Fingerprint string format: `${storage}|${retrieval}|${persistence}|
//     ${update}|${unit}|${governance}|${conflict}`. Pipe is a safe
//     separator because no taxonomy term contains a `|`.
//   - Section / tier distributions are stored as Maps so consumers can
//     iterate in insertion-order-by-frequency without re-sorting.
//
// Round-2 upgrades (May 2026, issue #25 follow-up):
//   - Exemplar-driven names: each archetype with ≥5 members gets a name
//     derived from its most-prominent member ("The Mem0 recipe"). The
//     prominence score combines inbound integrations, inbound cites,
//     funding, and tier so we pick a name a reader will recognise even
//     when the most-integrated row is unfamiliar.
//   - Near-archetype clustering: for every singleton we compute its
//     Hamming distance to the recurring archetypes (n≥2). Distance-1
//     singletons attach to their closest archetype as "near-variants",
//     collapsing the long tail.
//   - Gap-candidate prose: each white-space candidate gets a
//     deterministic 2-3 sentence description naming the axes that make
//     it unusual and the closest existing system at Hamming-1.

import type {
  Edge,
  EdgeType,
  LandscapeRecord,
  Tier,
  TaxonomyValue
} from '../types';
import { extractNumber } from '../leaderboards';

export const AXES = [
  'storage',
  'retrieval',
  'persistence',
  'update',
  'unit',
  'governance',
  'conflict'
] as const;

export type Axis = (typeof AXES)[number];

/** Primary value on a taxonomy axis, or `'unspecified'` if absent. */
export function primaryValue(values: TaxonomyValue[] | undefined): string {
  if (!values || values.length === 0) return 'unspecified';
  const p = values.find((v) => v.primary);
  return p?.value ?? values[0].value;
}

/** Build the 7-axis fingerprint string for a record. */
export function fingerprintOf(record: LandscapeRecord): string {
  return AXES.map((a) => primaryValue(record.taxonomy[a])).join('|');
}

/** Parse a fingerprint string back into a {axis → value} record. */
export function parseFingerprint(fp: string): Record<Axis, string> {
  const parts = fp.split('|');
  const out = {} as Record<Axis, string>;
  AXES.forEach((axis, i) => {
    out[axis] = parts[i] ?? 'unspecified';
  });
  return out;
}

/**
 * Hamming distance between two fingerprints — number of axes whose
 * primary value differs. Both must be 7-tuple `|`-joined strings.
 */
export function fingerprintHamming(a: string, b: string): number {
  const ap = a.split('|');
  const bp = b.split('|');
  let d = 0;
  for (let i = 0; i < AXES.length; i++) {
    if ((ap[i] ?? '') !== (bp[i] ?? '')) d++;
  }
  return d;
}

export interface Archetype {
  /** The 7-axis fingerprint joined by `|`. */
  fingerprint: string;
  /** Record ids (slugs) that share this fingerprint. */
  members: string[];
  /** Record display names — convenience, in members order. */
  memberNames: string[];
  /** Map of primary section → count of members in it. */
  sections: Map<string, number>;
  /** Map of tier (1..5) → count of members in it. */
  tiers: Map<number, number>;
}

function primarySection(r: LandscapeRecord): string {
  const p = r.sections.find((s) => s.primary);
  return p?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

/**
 * Cluster records by their 7-axis fingerprint. Returns archetypes sorted
 * by member count desc, then fingerprint asc (stable tiebreak).
 */
export function clusterByFingerprint(records: LandscapeRecord[]): Archetype[] {
  const buckets = new Map<string, LandscapeRecord[]>();
  for (const r of records) {
    const fp = fingerprintOf(r);
    let b = buckets.get(fp);
    if (!b) {
      b = [];
      buckets.set(fp, b);
    }
    b.push(r);
  }

  const archetypes: Archetype[] = [];
  for (const [fp, recs] of buckets.entries()) {
    const sections = new Map<string, number>();
    const tiers = new Map<number, number>();
    for (const r of recs) {
      const s = primarySection(r);
      sections.set(s, (sections.get(s) ?? 0) + 1);
      tiers.set(r.tier, (tiers.get(r.tier) ?? 0) + 1);
    }
    const sortedSections = new Map(
      [...sections.entries()].sort(
        (a, b) => b[1] - a[1] || a[0].localeCompare(b[0])
      )
    );
    const sortedTiers = new Map(
      [...tiers.entries()].sort((a, b) => a[0] - b[0])
    );
    archetypes.push({
      fingerprint: fp,
      members: recs.map((r) => r.id),
      memberNames: recs.map((r) => r.name),
      sections: sortedSections,
      tiers: sortedTiers
    });
  }

  archetypes.sort(
    (a, b) =>
      b.members.length - a.members.length ||
      a.fingerprint.localeCompare(b.fingerprint)
  );
  return archetypes;
}

// --- Inbound edge counts (per record id) ------------------------------
//
// Tiny inline duplicate of leaderboards.inboundEdgeCounts to avoid
// pulling Edge typing into every consumer that only needs records.

function inboundEdgeCounts(
  edges: Edge[],
  types: EdgeType[]
): Map<string, number> {
  const set = new Set(types);
  const counts = new Map<string, number>();
  for (const e of edges) {
    if (!set.has(e.type)) continue;
    counts.set(e.target, (counts.get(e.target) ?? 0) + 1);
  }
  return counts;
}

// --- Exemplar selection ------------------------------------------------
//
// For each archetype with enough members, pick the "exemplar" — the
// system whose name most readers would recognise as the canonical
// representative of the recipe.
//
// Score (descending priority):
//   1. Inbound integrations + built-on  (×100_000)
//   2. Inbound cites                    (×10_000)
//   3. log10(funding $)                 (×1_000)   — commercial weight
//   4. (6 − tier)                       (×100)     — tier 1 > tier 5
//   5. Alphabetical name                — stable tiebreak

interface ExemplarContext {
  intCount: Map<string, number>;
  citeCount: Map<string, number>;
}

function buildExemplarContext(edges: Edge[]): ExemplarContext {
  return {
    intCount: inboundEdgeCounts(edges, ['integrates-with', 'built-on']),
    citeCount: inboundEdgeCounts(edges, ['cites'])
  };
}

function fundingNumeric(r: LandscapeRecord): number {
  const cell = r.cells.funding;
  if (!cell || cell.status !== 'real-data') return 0;
  return extractNumber(cell.value) ?? 0;
}

function exemplarScore(r: LandscapeRecord, ctx: ExemplarContext): number {
  const i = ctx.intCount.get(r.id) ?? 0;
  const c = ctx.citeCount.get(r.id) ?? 0;
  const fund = fundingNumeric(r);
  const tierBonus = (6 - r.tier) * 100;
  return (
    i * 100_000 + c * 10_000 + Math.log10(fund + 1) * 1_000 + tierBonus
  );
}

/**
 * Return the member of the archetype with the highest exemplar score.
 * Falls back to alphabetical first on ties.
 */
export function pickExemplar(
  arch: Archetype,
  recordById: Map<string, LandscapeRecord>,
  ctx: ExemplarContext
): LandscapeRecord | null {
  const members = arch.members
    .map((id) => recordById.get(id))
    .filter((r): r is LandscapeRecord => !!r);
  if (members.length === 0) return null;
  let best = members[0];
  let bestScore = exemplarScore(best, ctx);
  for (let i = 1; i < members.length; i++) {
    const s = exemplarScore(members[i], ctx);
    if (s > bestScore || (s === bestScore && members[i].name < best.name)) {
      best = members[i];
      bestScore = s;
    }
  }
  return best;
}

// --- Archetype naming --------------------------------------------------
//
// Three-tier algorithm:
//   (a) Pattern archetypes whose fingerprint is dominated by `n/a` axes
//       (benchmarks, surveys, no-memory frameworks) get a section-name
//       label — the section is what gives them their identity, not a
//       single product.
//   (b) Archetypes with ≥5 members get an exemplar-driven name:
//       "The {exemplar.name} recipe".
//   (c) Smaller archetypes (or anything without a clear exemplar) get a
//       synthesised "axis1 + axis2 + axis3 recipe" label.
//
// The hand-curated NAMED_ARCHETYPES table from round 1 is kept as the
// *primary* lookup so the well-known recipes (Mem0, CLAUDE.md, …) keep
// their human-recognisable labels even on small populations.

const NAMED_ARCHETYPES: { match: string[]; name: string }[] = [
  {
    match: ['vector|similarity|long-term|extraction|fact'],
    name: 'The Mem0 recipe (extracted-fact vector memory)'
  },
  {
    match: ['kv|injection|long-term|extraction|fact'],
    name: 'The ChatGPT-Memory recipe (KV facts injected at prompt)'
  },
  {
    match: ['vector|similarity|long-term|overwrite|chunk'],
    name: 'The Qdrant recipe (vector chunk index)'
  },
  {
    match: ['vector|similarity|long-term|read-only|chunk'],
    name: 'The static-RAG recipe (read-only chunk retrieval)'
  },
  {
    match: ['graph|graph-traversal|long-term|overwrite|fact'],
    name: 'The knowledge-graph recipe (fact graph, overwrite update)'
  },
  {
    // Graph KG with LLM-driven extraction + arbitration — the Zep /
    // A-MEM / HippoRAG family. Same shape as the canonical KG recipe
    // except the update path is `extraction` and conflicts go to the
    // LLM rather than last-writer-wins.
    match: ['graph|graph-traversal|long-term|extraction|fact'],
    name: 'The Zep recipe (extracted-fact knowledge graph)'
  },
  {
    match: ['graph|graph-traversal|long-term|overwrite|document'],
    name: 'The PKG-notes recipe (document graph, user-curated)'
  },
  {
    match: ['file|injection|cross-session|overwrite|document'],
    name: 'The CLAUDE.md recipe (file-backed agent memory)'
  },
  {
    match: ['hybrid|similarity|long-term|read-only|chunk'],
    name: 'The hybrid-RAG recipe (BM25 + dense, read-only)'
  },
  {
    // Episodic learning agents (ExpeL / Reflexion / CrewAI Memory family).
    // We allow either `long-term` or `cross-session` on the persistence
    // axis because the catalog uses both for episode-based agent memory.
    match: [
      'vector|similarity|cross-session|extraction|episode',
      'vector|similarity|long-term|extraction|episode'
    ],
    name: 'The ExpeL recipe (episodic agent memory)'
  },
  {
    match: ['kv|similarity|session|replacement|token'],
    name: 'The state-space recipe (token-level KV with replacement)'
  },
  {
    match: ['n/a|n/a|n/a|n/a|n/a|n/a|n/a'],
    name: 'The no-taxonomy bucket (survey / event / meta record)'
  },
  {
    match: ['n/a|n/a|n/a|read-only|n/a|n/a|n/a'],
    name: 'The benchmark recipe (no memory of its own)'
  }
];

function dominantSection(arch: Archetype): string | null {
  const first = [...arch.sections.entries()][0];
  return first ? first[0] : null;
}

/**
 * Suggest a human-readable name for an archetype. Uses the curated
 * table first, then exemplar-driven naming when an edge graph is
 * available, then a synthesised axis-label fallback.
 *
 * @param fp        the 7-axis fingerprint
 * @param archetype optional — the full Archetype object so we can size-
 *                  gate exemplar naming on ≥5 members
 * @param exemplar  optional — the pre-picked exemplar record
 */
export function suggestArchetypeName(
  fp: string,
  archetype?: Archetype,
  exemplar?: LandscapeRecord | null
): string {
  // (a) Curated overrides win.
  for (const { match, name } of NAMED_ARCHETYPES) {
    if (match.some((m) => fp.startsWith(m))) return name;
  }

  const parts = parseFingerprint(fp);
  const naCount = AXES.filter((a) => parts[a] === 'n/a').length;

  // (b1) Mostly-n/a fingerprints — pattern archetypes whose identity
  // comes from the section they cluster in.
  if (naCount >= 5 && archetype) {
    const sec = dominantSection(archetype);
    if (sec) return `The ${sec} pattern`;
  }

  // (b2) ≥5 members and an exemplar exists → exemplar-driven name.
  if (archetype && archetype.members.length >= 5 && exemplar) {
    return `The ${exemplar.name} recipe`;
  }

  // (c) Synthesised label from the most-informative axes.
  const interesting = AXES.map((a) => parts[a]).filter(
    (v) => v && v !== 'n/a' && v !== 'unspecified'
  );
  if (interesting.length === 0) return 'Untaxonomised record';
  if (interesting.length <= 2) {
    return `${interesting.join(' + ')} recipe`;
  }
  return `${interesting.slice(0, 3).join(' + ')} recipe`;
}

// --- Coverage / summary helpers ----------------------------------------

export interface ArchetypeSummary {
  total: number;
  distinct: number;
  topN: number;
  topNCoverage: number; // 0..1
  singletons: number;
}

export function summarise(
  archetypes: Archetype[],
  topN: number
): ArchetypeSummary {
  const total = archetypes.reduce((acc, a) => acc + a.members.length, 0);
  const topCount = archetypes
    .slice(0, topN)
    .reduce((acc, a) => acc + a.members.length, 0);
  const singletons = archetypes.filter((a) => a.members.length === 1).length;
  return {
    total,
    distinct: archetypes.length,
    topN,
    topNCoverage: total > 0 ? topCount / total : 0,
    singletons
  };
}

// --- Near-archetype clustering -----------------------------------------
//
// For each singleton fingerprint, find the closest recurring archetype
// (n≥2) by Hamming distance. Singletons within `threshold` (default 1)
// of an anchor are "absorbed" — they're variants of the canonical
// recipe differing on a single axis. We use threshold=1 because that's
// the most legible boundary: "this system is the canonical recipe
// except for one axis" is easy to describe; distance ≥ 2 starts being a
// genuinely different shape.
//
// Anchors are *all* recurring archetypes, not just the top-N, because
// many singletons are distance-1 from a small-but-not-tiny archetype
// further down the list. The route component slices the result by
// archetype so the top-N cards show only their own absorbed neighbours.

export interface NearVariant {
  /** The singleton fingerprint that was absorbed. */
  fingerprint: string;
  /** The anchor archetype's fingerprint. */
  anchor: string;
  /** Axis on which the singleton differs from the anchor (or null when
   *  the singleton equals the anchor — should never happen here, but
   *  the type leaves room for stricter thresholds). */
  differingAxis: Axis | null;
  /** Value the singleton has on that axis. */
  differingValue: string;
  /** Value the anchor has on that axis. */
  anchorValue: string;
  /** The single record's id and name (singleton has exactly one member). */
  memberId: string;
  memberName: string;
}

export interface NearClusterResult {
  /** Singletons absorbed at Hamming-`threshold` to some anchor. */
  absorbed: NearVariant[];
  /** Singletons still unattached (distance > threshold to every anchor). */
  unattached: Archetype[];
  /** Convenience: anchor fp → list of near-variants attached to it. */
  byAnchor: Map<string, NearVariant[]>;
  /** Number of singletons in the input (for ratio reporting). */
  singletonCount: number;
  /** Hamming threshold used. */
  threshold: number;
}

export function clusterNearArchetypes(
  archetypes: Archetype[],
  recordById: Map<string, LandscapeRecord>,
  opts: { threshold?: number } = {}
): NearClusterResult {
  const threshold = opts.threshold ?? 1;
  const anchors = archetypes.filter((a) => a.members.length >= 2);
  const singletons = archetypes.filter((a) => a.members.length === 1);

  const absorbed: NearVariant[] = [];
  const unattached: Archetype[] = [];
  const byAnchor = new Map<string, NearVariant[]>();

  for (const s of singletons) {
    let bestAnchor: Archetype | null = null;
    let bestD = Infinity;
    for (const a of anchors) {
      const d = fingerprintHamming(s.fingerprint, a.fingerprint);
      if (d < bestD) {
        bestD = d;
        bestAnchor = a;
        if (bestD === 0) break; // can't get closer
      }
    }
    if (bestAnchor && bestD > 0 && bestD <= threshold) {
      const sParts = s.fingerprint.split('|');
      const aParts = bestAnchor.fingerprint.split('|');
      let diffAxis: Axis | null = null;
      let diffVal = '';
      let anchorVal = '';
      for (let i = 0; i < AXES.length; i++) {
        if (sParts[i] !== aParts[i]) {
          diffAxis = AXES[i];
          diffVal = sParts[i] ?? '';
          anchorVal = aParts[i] ?? '';
          break;
        }
      }
      const id = s.members[0];
      const rec = recordById.get(id);
      const variant: NearVariant = {
        fingerprint: s.fingerprint,
        anchor: bestAnchor.fingerprint,
        differingAxis: diffAxis,
        differingValue: diffVal,
        anchorValue: anchorVal,
        memberId: id,
        memberName: rec?.name ?? id
      };
      absorbed.push(variant);
      let list = byAnchor.get(bestAnchor.fingerprint);
      if (!list) {
        list = [];
        byAnchor.set(bestAnchor.fingerprint, list);
      }
      list.push(variant);
    } else {
      unattached.push(s);
    }
  }

  return {
    absorbed,
    unattached,
    byAnchor,
    singletonCount: singletons.length,
    threshold
  };
}

// --- White-space detection ---------------------------------------------
//
// A "gap candidate" is a fingerprint with <2 members whose individual
// axis values are all common in the catalog (each value appears in many
// other records) yet this specific combination has never been built
// twice. Intuition: the building blocks exist; nobody has assembled them
// in this exact way.
//
// Implementation:
//   1. Count how many records use each (axis, value) pair (the
//      "popularity" of that axis value across the catalog).
//   2. For each singleton fingerprint, compute the min popularity across
//      its 7 axes. If that minimum is high (the rarest of its axes is
//      still common), it's a gap candidate.
//   3. Rank by min popularity desc, then by sum-popularity desc.
//
// Round 2 addition: each candidate carries a `prose` field — a
// deterministic 2-3 sentence description naming the closest existing
// system at Hamming-1 and the axes the missing product would mix.

export interface GapCandidate {
  fingerprint: string;
  member: string; // the single record's name
  memberId: string;
  minAxisPopularity: number;
  sumAxisPopularity: number;
  /** Deterministic prose describing the gap. */
  prose: string;
  /** Up to 3 closest existing systems (Hamming-1), with the axis they
   *  differ on, for "see also" rendering. */
  closest: { name: string; id: string; diffAxis: Axis; diffValue: string }[];
}

export function detectGapCandidates(
  records: LandscapeRecord[],
  archetypes: Archetype[],
  opts: { minAxisFloor?: number; limit?: number } = {}
): GapCandidate[] {
  const minAxisFloor = opts.minAxisFloor ?? 20;
  const limit = opts.limit ?? 10;

  // axis-value popularity table
  const pop = new Map<string, Map<string, number>>();
  for (const axis of AXES) pop.set(axis, new Map());
  for (const r of records) {
    for (const axis of AXES) {
      const v = primaryValue(r.taxonomy[axis]);
      const m = pop.get(axis)!;
      m.set(v, (m.get(v) ?? 0) + 1);
    }
  }

  const recordById = new Map(records.map((r) => [r.id, r]));

  // For closest-system lookup, build a quick (fp → first-record) index
  // over recurring archetypes plus arbitrary records — we only ever
  // search for Hamming-1 neighbours, so iterating records once per
  // candidate is acceptable (699 × 8 = ~5.6k comparisons per gap).

  const out: GapCandidate[] = [];
  for (const a of archetypes) {
    if (a.members.length >= 2) continue;
    const parts = parseFingerprint(a.fingerprint);
    let min = Infinity;
    let sum = 0;
    let hasNA = false;
    for (const axis of AXES) {
      const v = parts[axis];
      if (v === 'n/a' || v === 'unspecified') {
        hasNA = true;
        break;
      }
      const p = pop.get(axis)!.get(v) ?? 0;
      min = Math.min(min, p);
      sum += p;
    }
    if (hasNA) continue;
    if (min < minAxisFloor) continue;
    const rec = recordById.get(a.members[0]);
    if (!rec) continue;

    // Closest existing systems at Hamming-1, excluding self.
    const closest: GapCandidate['closest'] = [];
    for (const other of records) {
      if (other.id === rec.id) continue;
      const ofp = fingerprintOf(other);
      const d = fingerprintHamming(a.fingerprint, ofp);
      if (d !== 1) continue;
      const oparts = parseFingerprint(ofp);
      let diffAxis: Axis = AXES[0];
      let diffValue = '';
      for (const axis of AXES) {
        if (oparts[axis] !== parts[axis]) {
          diffAxis = axis;
          diffValue = parts[axis];
          break;
        }
      }
      closest.push({
        name: other.name,
        id: other.id,
        diffAxis,
        diffValue
      });
      if (closest.length >= 3) break;
    }

    out.push({
      fingerprint: a.fingerprint,
      member: rec.name,
      memberId: rec.id,
      minAxisPopularity: min,
      sumAxisPopularity: sum,
      prose: composeGapProse(parts, rec.name, closest),
      closest
    });
  }

  out.sort(
    (a, b) =>
      b.minAxisPopularity - a.minAxisPopularity ||
      b.sumAxisPopularity - a.sumAxisPopularity
  );
  return out.slice(0, limit);
}

/**
 * Compose a deterministic 2-3 sentence description of a gap candidate.
 * No randomness, no LLM — just template-driven prose so the same gaps
 * always produce the same text (good for diffing the analyses page
 * over time).
 */
function composeGapProse(
  parts: Record<Axis, string>,
  selfName: string,
  closest: GapCandidate['closest']
): string {
  const recipe = AXES.map((a) => parts[a]).join(' · ');
  let prose = `The ${recipe} fingerprint has 0 members other than ${selfName}; every individual axis value is mainstream but this specific combination has not been built twice.`;
  if (closest.length > 0) {
    const c0 = closest[0];
    prose += ` Closest existing: ${c0.name} at Hamming-1 (differs on ${c0.diffAxis}).`;
    if (closest.length > 1) {
      const more = closest
        .slice(1)
        .map((c) => `${c.name} (${c.diffAxis})`)
        .join(', ');
      prose += ` Also nearby: ${more}.`;
    }
    prose += ` A product filling this gap could be framed as "${c0.name} with ${parts[c0.diffAxis]} on the ${c0.diffAxis} axis".`;
  } else {
    prose += ` No other system in the catalog sits within one axis of this combination — the surrounding region is empty.`;
  }
  return prose;
}

// --- Numeric aggregates over an archetype ------------------------------
//
// Funding and citations are the two columns most useful for "is this
// archetype well-funded? well-cited?" signals. We compute the median
// (not the mean) because both distributions are heavy-tailed — a single
// Anthropic-scale funding round would swamp the mean of a 5-member
// archetype.

export interface ArchetypeNumerics {
  funding: { median: number | null; n: number };
  citations: { median: number | null; n: number };
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 === 0 ? (s[mid - 1] + s[mid]) / 2 : s[mid];
}

export function archetypeNumerics(
  arch: Archetype,
  recordById: Map<string, LandscapeRecord>
): ArchetypeNumerics {
  const funding: number[] = [];
  const citations: number[] = [];
  for (const id of arch.members) {
    const r = recordById.get(id);
    if (!r) continue;
    const f = r.cells.funding;
    if (f && f.status === 'real-data') {
      const n = extractNumber(f.value);
      if (n !== null && n > 0) funding.push(n);
    }
    const c = r.cells.citations;
    if (c && c.status === 'real-data') {
      const n = extractNumber(c.value);
      if (n !== null && n > 0) citations.push(n);
    }
  }
  return {
    funding: { median: median(funding), n: funding.length },
    citations: { median: median(citations), n: citations.length }
  };
}

/**
 * Render a funding number ($420M → "$420M", $2.5B → "$2.5B"). Returns
 * "—" for null. We keep the units coarse because the median is a
 * directional signal, not a precision figure.
 */
export function formatFunding(n: number | null): string {
  if (n === null) return '—';
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${Math.round(n / 1e6)}M`;
  if (n >= 1e3) return `$${Math.round(n / 1e3)}k`;
  return `$${Math.round(n)}`;
}

export function formatCount(n: number | null): string {
  if (n === null) return '—';
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}k`;
  return `${Math.round(n)}`;
}

// --- Value-prop phrases ------------------------------------------------
//
// A one-sentence "what distinguishes this archetype" line. The phrasing
// is deterministic and driven by the fingerprint axes. Curated overrides
// for a handful of canonical recipes keep the prose readable; everything
// else falls back to a template.

const VALUE_PROPS: { match: string[]; prop: string }[] = [
  {
    match: ['vector|similarity|long-term|extraction|fact'],
    prop:
      'LLM-extracted facts persisted as embedded chunks — the "give the assistant a memory of its user" pattern.'
  },
  {
    match: ['kv|injection|long-term|extraction|fact'],
    prop:
      'Closed-shop conversational assistants: facts extracted server-side and injected at prompt time. No retrieval API.'
  },
  {
    match: ['vector|similarity|long-term|overwrite|chunk'],
    prop:
      'Index everything, retrieve by similarity, overwrite on re-ingest — the workhorse vector store.'
  },
  {
    match: ['vector|similarity|long-term|read-only|chunk'],
    prop:
      'Research RAG: build the index, query it, never write back. The retrieval layer is treated as a static substrate.'
  },
  {
    match: ['graph|graph-traversal|long-term|overwrite|fact'],
    prop:
      'Facts as triples, queries as graph traversals — the knowledge-graph stack, optimised for relationship questions.'
  },
  {
    match: ['graph|graph-traversal|long-term|extraction|fact'],
    prop:
      'Knowledge graph built by LLM extraction: temporal episodes get distilled into entity-relation triples, with LLM-arbitrated merges on conflict.'
  },
  {
    match: ['file|injection|cross-session|overwrite|document'],
    prop:
      'Files are the memory. Versioned in git, edited by humans and agents alike, no database in the loop.'
  },
  {
    match: ['kv|similarity|session|replacement|token'],
    prop:
      'Token-level KV in the attention path — what state-space and KV-compression methods do, not user-facing memory.'
  },
  {
    match: ['n/a|n/a|n/a|n/a|n/a|n/a|n/a'],
    prop:
      'Non-memory records — frameworks, surveys, infrastructure that the catalog tracks for context but has no memory taxonomy of its own.'
  },
  {
    match: ['n/a|n/a|n/a|read-only|n/a|n/a|n/a'],
    prop:
      'Benchmarks — they measure other systems and have no memory taxonomy of their own.'
  }
];

export function valuePropFor(fp: string): string {
  for (const { match, prop } of VALUE_PROPS) {
    if (match.some((m) => fp.startsWith(m))) return prop;
  }
  const parts = parseFingerprint(fp);
  const ax = AXES.filter((a) => parts[a] !== 'n/a' && parts[a] !== 'unspecified');
  if (ax.length === 0) return 'No taxonomy axes set — context record.';
  // Generic template.
  const phrase = `${parts.storage} storage, ${parts.retrieval} retrieval, ${parts.persistence} persistence; ${parts.update} updates with ${parts.governance} governance.`;
  return phrase[0].toUpperCase() + phrase.slice(1);
}

// --- Convenience: build everything in one pass -------------------------
//
// The route component wants archetypes + summary + exemplars + numerics
// + near-cluster + gaps. Doing this in one helper keeps the .svelte
// short and means tests can sanity-check the whole pipeline against a
// fixture in one call.

export interface ArchetypeBundle {
  archetypes: Archetype[];
  summary: ArchetypeSummary;
  exemplars: Map<string, LandscapeRecord | null>; // archetype fp → exemplar
  names: Map<string, string>; // archetype fp → human name
  numerics: Map<string, ArchetypeNumerics>;
  near: NearClusterResult;
  gaps: GapCandidate[];
}

export function buildBundle(
  records: LandscapeRecord[],
  edges: Edge[],
  opts: {
    topN?: number;
    nearThreshold?: number;
    gapFloor?: number;
    gapLimit?: number;
  } = {}
): ArchetypeBundle {
  const topN = opts.topN ?? 12;
  const archetypes = clusterByFingerprint(records);
  const summary = summarise(archetypes, topN);
  const recordById = new Map(records.map((r) => [r.id, r]));
  const ctx = buildExemplarContext(edges);

  const exemplars = new Map<string, LandscapeRecord | null>();
  const names = new Map<string, string>();
  const numerics = new Map<string, ArchetypeNumerics>();
  for (const a of archetypes) {
    const ex = pickExemplar(a, recordById, ctx);
    exemplars.set(a.fingerprint, ex);
    names.set(a.fingerprint, suggestArchetypeName(a.fingerprint, a, ex));
    numerics.set(a.fingerprint, archetypeNumerics(a, recordById));
  }

  const near = clusterNearArchetypes(archetypes, recordById, {
    threshold: opts.nearThreshold ?? 1
  });
  const gaps = detectGapCandidates(records, archetypes, {
    minAxisFloor: opts.gapFloor ?? 25,
    limit: opts.gapLimit ?? 8
  });

  return { archetypes, summary, exemplars, names, numerics, near, gaps };
}

// --- Re-exports for tests / consumers ----------------------------------

export type { LandscapeRecord, Tier };
