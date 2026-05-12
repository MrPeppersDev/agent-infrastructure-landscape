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

import type { LandscapeRecord, Tier, TaxonomyValue } from '../types';

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
    // Sort the maps by count desc for stable display order.
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

// --- Naming heuristic --------------------------------------------------
//
// A handful of fingerprints have well-known names in the literature /
// product space. We hand-name the ones with obvious anchors; everything
// else gets a synthesized description ("vector + similarity recipe").
//
// Keys are partial-match patterns: any fingerprint that begins-with or
// contains the key prefix is matched. First match wins (order matters).
// Patterns use the same `|`-separated form as fingerprints, but a
// trailing `*` means "any value tolerated for axes beyond this point".

const NAMED_ARCHETYPES: { match: string[]; name: string }[] = [
  {
    // Mem0-style: extraction-update, fact unit, vector backend.
    match: ['vector|similarity|long-term|extraction|fact'],
    name: 'Mem0 recipe (extracted-fact vector memory)'
  },
  {
    // Conversational assistant memory (ChatGPT / Gemini / Grok / Meta AI).
    match: ['kv|injection|long-term|extraction|fact'],
    name: 'Assistant-memory recipe (KV facts injected at prompt)'
  },
  {
    // Plain RAG over chunks — Chroma / LanceDB / Pinecone shape.
    match: ['vector|similarity|long-term|overwrite|chunk'],
    name: 'Vector-store recipe (chunk index)'
  },
  {
    // Read-only retrieval — RAG research papers without write-back.
    match: ['vector|similarity|long-term|read-only|chunk'],
    name: 'Static-RAG recipe (read-only chunk retrieval)'
  },
  {
    // Graph DB / knowledge graph products.
    match: ['graph|graph-traversal|long-term|overwrite|fact'],
    name: 'Knowledge-graph recipe (fact graph, overwrite update)'
  },
  {
    // Personal-knowledge-graph note tools (Obsidian / Logseq family).
    match: ['graph|graph-traversal|long-term|overwrite|document'],
    name: 'PKG-notes recipe (document graph, user-curated)'
  },
  {
    // CLAUDE.md / AGENTS.md / Aider — files-as-memory.
    match: ['file|injection|cross-session|overwrite|document'],
    name: 'CLAUDE.md recipe (file-backed agent memory)'
  },
  {
    // Hybrid retrieval (BM25 + vector).
    match: ['hybrid|similarity|long-term|read-only|chunk'],
    name: 'Hybrid-RAG recipe (BM25 + dense, read-only)'
  },
  {
    // Episodic learning agents (ExpeL / Reflexion family).
    match: ['vector|similarity|cross-session|extraction|episode'],
    name: 'ExpeL recipe (episodic agent memory)'
  },
  {
    // Benchmarks: most axes degenerate to n/a.
    match: ['n/a|n/a|n/a|n/a|n/a|n/a|n/a'],
    name: 'No-taxonomy (survey / event / meta record)'
  },
  {
    match: ['n/a|n/a|n/a|read-only|n/a|n/a|n/a'],
    name: 'Benchmark recipe (no memory of its own)'
  }
];

/**
 * Suggest a human-readable name for an archetype fingerprint. Falls back
 * to a synthesised "storage + retrieval recipe" string.
 */
export function suggestArchetypeName(fp: string): string {
  for (const { match, name } of NAMED_ARCHETYPES) {
    if (match.some((m) => fp.startsWith(m))) return name;
  }
  const parts = parseFingerprint(fp);
  // Drop n/a / unspecified axes from the synthesised label so the name
  // stays compact.
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

export interface GapCandidate {
  fingerprint: string;
  member: string; // the single record's name
  memberId: string;
  minAxisPopularity: number;
  sumAxisPopularity: number;
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
    out.push({
      fingerprint: a.fingerprint,
      member: rec?.name ?? a.members[0],
      memberId: a.members[0],
      minAxisPopularity: min,
      sumAxisPopularity: sum
    });
  }

  out.sort(
    (a, b) =>
      b.minAxisPopularity - a.minAxisPopularity ||
      b.sumAxisPopularity - a.sumAxisPopularity
  );
  return out.slice(0, limit);
}

// --- Re-exports for tests / consumers ----------------------------------

export type { LandscapeRecord, Tier };
