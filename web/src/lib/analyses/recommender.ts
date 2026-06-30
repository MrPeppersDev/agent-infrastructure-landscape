// Pure ranking function shared by the /recommend surfaces (issue #96).
//
// Spec — PHASE_2_SPEC.html §4.1. The function answers two questions, on
// the same dispatch:
//
//   • Positioning (anchor mode): "between these two anchors on
//     cost/capability, what other rows live?"
//   • Constraint-matching (constraint mode): "what rows best satisfy
//     this ConstraintSet?"
//
// Both modes can be combined: anchors filter the pool, constraints
// score it. With neither, we return the top-k by raw capability.
//
// Architecture
// ------------
// `rankCandidates` is the public entry point. The MCP `recommender.ts`
// is a verbatim mirror of this file (different `types.ts` import path
// only). Same shape, same numbers — web / MCP / CLI all return
// byte-identical Candidate arrays for the same inputs because there is
// only one implementation of the scoring logic.
//
// Provenance gate (§3.4)
// ----------------------
// Every Phase 2 cell read for scoring is checked against
// `record._provenance[<slug>]`. If `source === "llm"` and
// `verified === false`, that cell is **excluded from the score** and a
// caveat is added to the candidate ("<slug> excluded from ranking —
// LLM-unverified"). This makes the entire Phase 4 LLM backfill
// non-load-bearing until a human review pass flips `verified: true` —
// which is the exact §3.4 contract.
//
// Staleness check
// ---------------
// `cost-last-verified` and `capability-last-verified` are compared
// against `options.today` (default `"2026-06-29"` — the Phase 4 fill
// date, so the default staleness math is stable). A caveat is added if
// either cell is older than `options.staleDays` (default 30). Staleness
// affects visibility, not score — same convention as validate.py gate 6.
//
// Determinism
// -----------
// No `Date.now()`, no `Math.random()`, no network. Tie-breaks use a
// locale-independent string comparison on record id. Same inputs ⇒ same
// Candidate array, bit-for-bit, across runtimes.

import type { LandscapeRecord } from '$lib/types';

// =========================================================================
// Public types
// =========================================================================

export interface ConstraintSet {
  /** OR-match against record's `use-case-tags`. */
  use_case_tags?: string[];
  /** Maximum acceptable per-Mtok input cost in USD. */
  cost_max_input_usd_per_mtok?: number;
  /** Maximum acceptable cost tier (cost rank ≤ this rank). */
  cost_tier_max?: CostTier;
  /** Minimum acceptable capability band (band rank ≥ this rank). */
  capability_band_min?: CapabilityBand;
}

export interface AnchorPair {
  /** Record id of the low-end positioning anchor. */
  low: string;
  /** Record id of the high-end positioning anchor. */
  high: string;
}

export interface Candidate {
  record: LandscapeRecord;
  /** Score in [0, 1]. Higher = better match. */
  score: number;
  /** One line per reason this row scored well. */
  rationale: string[];
  /** One line per warning — stale cells, LLM-unverified cells, anti-tags, etc. */
  caveats: string[];
}

export interface RankOptions {
  /** ISO date used as "today" for staleness math. Default `"2026-06-29"`. */
  today?: string;
  /** Days after which a `*-last-verified` cell triggers a staleness caveat. Default 30. */
  staleDays?: number;
}

// =========================================================================
// Constants
// =========================================================================

const DEFAULT_K = 5;
const DEFAULT_STALE_DAYS = 30;
// The Phase 4 LLM backfill stamped every populated `*-last-verified`
// cell with this date (PHASE_2_SPEC §3.5). Picking this as the default
// `today` keeps staleness math stable until a caller passes a real
// today — important for the cross-runtime determinism guarantee.
const DEFAULT_TODAY = '2026-06-29';

const COST_TIER_ORDER = ['free', 'budget', 'mid', 'premium'] as const;
const CAPABILITY_BAND_ORDER = ['entry', 'competent', 'frontier'] as const;

export type CostTier = (typeof COST_TIER_ORDER)[number];
export type CapabilityBand = (typeof CAPABILITY_BAND_ORDER)[number];

// =========================================================================
// Cell readers
// =========================================================================

function isNotApplicable(value: string | undefined | null): boolean {
  if (!value) return true;
  return /^\s*(not\s+applicable|n\/a)\b/i.test(value);
}

function cellValue(record: LandscapeRecord, slug: string): string | null {
  const cells = record.cells as Record<string, { value?: string } | undefined>;
  const cell = cells[slug];
  if (!cell || typeof cell.value !== 'string') return null;
  if (isNotApplicable(cell.value)) return null;
  return cell.value;
}

function isLlmUnverified(record: LandscapeRecord, slug: string): boolean {
  const prov = record._provenance?.[slug];
  return !!prov && prov.source === 'llm' && prov.verified === false;
}

// =========================================================================
// Value parsers
// =========================================================================

function parseNumber(s: string | null): number | null {
  if (s == null) return null;
  const n = Number(s.trim());
  return isFinite(n) ? n : null;
}

function parseTags(s: string | null): string[] {
  if (s == null) return [];
  return s
    .split(',')
    .map((t) => t.trim())
    .filter((t) => t.length > 0);
}

function parseTier(s: string | null): CostTier | null {
  if (s == null) return null;
  const v = s.trim().toLowerCase();
  return (COST_TIER_ORDER as readonly string[]).includes(v) ? (v as CostTier) : null;
}

function parseBand(s: string | null): CapabilityBand | null {
  if (s == null) return null;
  const v = s.trim().toLowerCase();
  return (CAPABILITY_BAND_ORDER as readonly string[]).includes(v) ? (v as CapabilityBand) : null;
}

/**
 * Day diff between two ISO YYYY-MM-DD strings, treated as UTC midnight.
 * Returns `today - then` in whole days; positive if `then` is in the past.
 * Returns NaN on parse failure (caller treats NaN as "no signal").
 */
function dateDiffDays(today: string, then: string): number {
  const tdy = Date.parse(today + 'T00:00:00Z');
  const thn = Date.parse(then + 'T00:00:00Z');
  if (!isFinite(tdy) || !isFinite(thn)) return NaN;
  return Math.floor((tdy - thn) / 86_400_000);
}

function clamp01(n: number): number {
  if (!isFinite(n)) return 0;
  if (n < 0) return 0;
  if (n > 1) return 1;
  return n;
}

/**
 * Locale-independent string compare for deterministic tie-breaks. We
 * cannot use `localeCompare` because it varies by host locale; same
 * convention as build_edges.py's record-id sort.
 */
function cmpId(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

// =========================================================================
// Derived per-record cell snapshot
// =========================================================================

interface DerivedRow {
  record: LandscapeRecord;
  costUsd: number | null;
  costUsdLlm: boolean;
  costTier: CostTier | null;
  costTierLlm: boolean;
  capScore: number | null;
  capScoreLlm: boolean;
  capBand: CapabilityBand | null;
  capBandLlm: boolean;
  tags: string[];
  tagsLlm: boolean;
  antiTags: string[];
  antiTagsLlm: boolean;
  costLastVerified: string | null;
  capLastVerified: string | null;
}

function derive(record: LandscapeRecord): DerivedRow {
  return {
    record,
    costUsd: parseNumber(cellValue(record, 'cost-input-usd-per-mtok')),
    costUsdLlm: isLlmUnverified(record, 'cost-input-usd-per-mtok'),
    costTier: parseTier(cellValue(record, 'cost-tier')),
    costTierLlm: isLlmUnverified(record, 'cost-tier'),
    capScore: parseNumber(cellValue(record, 'capability-composite-score')),
    capScoreLlm: isLlmUnverified(record, 'capability-composite-score'),
    capBand: parseBand(cellValue(record, 'capability-band')),
    capBandLlm: isLlmUnverified(record, 'capability-band'),
    tags: parseTags(cellValue(record, 'use-case-tags')),
    tagsLlm: isLlmUnverified(record, 'use-case-tags'),
    antiTags: parseTags(cellValue(record, 'use-case-anti-tags')),
    antiTagsLlm: isLlmUnverified(record, 'use-case-anti-tags'),
    costLastVerified: cellValue(record, 'cost-last-verified'),
    capLastVerified: cellValue(record, 'capability-last-verified')
  };
}

// =========================================================================
// Anchor-mode range helpers
// =========================================================================

function numRange(a: number | null, b: number | null): [number, number] | null {
  if (a == null || b == null) return null;
  return a <= b ? [a, b] : [b, a];
}

function inRange(x: number, [lo, hi]: [number, number]): boolean {
  return x >= lo && x <= hi;
}

// =========================================================================
// Scoring
// =========================================================================

function scoreOne(
  d: DerivedRow,
  c: ConstraintSet,
  today: string,
  staleDays: number,
  anchorMode: boolean
): Candidate {
  const rationale: string[] = [];
  const caveats: string[] = [];

  let base = 0;
  let weight = 0;

  // --- use-case tags (positive match) ------------------------------------
  if (c.use_case_tags && c.use_case_tags.length > 0) {
    if (d.tagsLlm) {
      caveats.push('use-case-tags excluded from ranking — LLM-unverified');
    } else {
      const matched = c.use_case_tags.filter((t) => d.tags.includes(t));
      const contribution = matched.length / c.use_case_tags.length;
      base += contribution;
      weight += 1;
      if (matched.length > 0) {
        const plural = matched.length > 1 ? 's' : '';
        rationale.push(`matches use-case tag${plural}: ${matched.join(', ')}`);
      }
    }

    // Anti-tag deduction (separate provenance gate from positive tags).
    if (d.antiTagsLlm) {
      caveats.push('use-case-anti-tags excluded from ranking — LLM-unverified');
    } else if (d.antiTags.length > 0) {
      const antiHits = c.use_case_tags.filter((t) => d.antiTags.includes(t));
      if (antiHits.length > 0) {
        base -= 0.5 * antiHits.length;
        caveats.push(`anti-tag match: ${antiHits.join(', ')}`);
      }
    }
  }

  // --- cost ceiling ($/Mtok input) ---------------------------------------
  if (c.cost_max_input_usd_per_mtok != null) {
    if (d.costUsdLlm) {
      caveats.push('cost-input-usd-per-mtok excluded from ranking — LLM-unverified');
    } else if (d.costUsd != null) {
      if (d.costUsd <= c.cost_max_input_usd_per_mtok) {
        base += 1;
        rationale.push(
          `cost within budget ($${d.costUsd}/Mtok ≤ $${c.cost_max_input_usd_per_mtok}/Mtok)`
        );
      } else {
        caveats.push(
          `cost exceeds budget ($${d.costUsd}/Mtok > $${c.cost_max_input_usd_per_mtok}/Mtok)`
        );
      }
      weight += 1;
    }
  }

  // --- cost tier ceiling -------------------------------------------------
  if (c.cost_tier_max != null) {
    if (d.costTierLlm) {
      caveats.push('cost-tier excluded from ranking — LLM-unverified');
    } else if (d.costTier != null) {
      const recRank = COST_TIER_ORDER.indexOf(d.costTier);
      const maxRank = COST_TIER_ORDER.indexOf(c.cost_tier_max);
      if (recRank <= maxRank) {
        base += 1;
        rationale.push(`cost-tier ${d.costTier} ≤ ${c.cost_tier_max}`);
      } else {
        caveats.push(`cost-tier ${d.costTier} > requested ${c.cost_tier_max}`);
      }
      weight += 1;
    }
  }

  // --- capability band floor ---------------------------------------------
  if (c.capability_band_min != null) {
    if (d.capBandLlm) {
      caveats.push('capability-band excluded from ranking — LLM-unverified');
    } else if (d.capBand != null) {
      const recRank = CAPABILITY_BAND_ORDER.indexOf(d.capBand);
      const minRank = CAPABILITY_BAND_ORDER.indexOf(c.capability_band_min);
      if (recRank >= minRank) {
        base += 1;
        rationale.push(`capability-band ${d.capBand} ≥ ${c.capability_band_min}`);
      } else {
        caveats.push(`capability-band ${d.capBand} < requested ${c.capability_band_min}`);
      }
      weight += 1;
    }
  }

  // --- staleness caveats (visibility-only) -------------------------------
  if (d.costLastVerified) {
    const age = dateDiffDays(today, d.costLastVerified);
    if (isFinite(age) && age > staleDays) {
      caveats.push(`cost data ${age}d stale (cost-last-verified ${d.costLastVerified})`);
    }
  }
  if (d.capLastVerified) {
    const age = dateDiffDays(today, d.capLastVerified);
    if (isFinite(age) && age > staleDays) {
      caveats.push(
        `capability data ${age}d stale (capability-last-verified ${d.capLastVerified})`
      );
    }
  }

  // --- final score -------------------------------------------------------
  // Constraint mode: average of per-constraint match strengths (anti-tag
  // penalty already folded into `base`), clamped to [0, 1].
  // Anchor-only mode (anchors with no scoring constraints): rank by raw
  // capability score so higher-capability candidates surface first inside
  // the positioning band.
  let scoreValue: number;
  if (weight === 0) {
    if (anchorMode && d.capScore != null && !d.capScoreLlm) {
      scoreValue = clamp01(d.capScore / 100);
    } else {
      scoreValue = anchorMode ? 0.5 : 0;
    }
  } else {
    scoreValue = clamp01(base / weight);
  }

  return {
    record: d.record,
    score: scoreValue,
    rationale,
    caveats
  };
}

// =========================================================================
// Public API
// =========================================================================

// =========================================================================
// Free-text & structured-form parsers (issue #98 — Gate 4)
// =========================================================================
//
// The recommender exposes two parsers so all three surfaces (web / MCP /
// CLI) translate user input into a `ConstraintSet` identically:
//
//   parseFreeTextConstraints("long-running multi-agent + offline")
//     → { use_case_tags: ['long-running-session', 'multi-agent-coordination', 'offline-capable'] }
//
//   structuredFormToConstraints({ deployment: 'offline', persistence: 'long-term' })
//     → { use_case_tags: ['long-running-session', 'offline-capable'] }
//
// The free-text parser is deterministic keyword/phrase matching against
// a synonym table — explicitly NOT an LLM (PHASE_2_SPEC §4 calls this
// out as a hard constraint: "keeps the recommender auditable and
// reproducible"). The synonym table lives next to the parser and grows
// by PR.

/** Result shape returned by `parseFreeTextConstraints`. */
export interface ParsedConstraints {
  constraints: ConstraintSet;
  /** Phrases the parser identified, in canonical (space-separated) form. */
  matched_terms: string[];
  /** Tokens the parser ignored — exposed so users can see what was dropped. */
  unmatched_terms: string[];
}

/** Structured-form shape for the `/recommend/by-constraints` UX. */
export interface StructuredForm {
  project_shape?: 'single-agent' | 'multi-agent' | 'chat' | 'pipeline';
  scale?: 'prototype' | 'production' | 'large-scale';
  /** Anything ≤ 1000ms triggers `latency-sensitive`. */
  latency_budget_ms?: number;
  persistence?: 'none' | 'session' | 'long-term';
  deployment?: 'cloud' | 'self-hosted' | 'offline';
  cost_ceiling_usd_per_mtok?: number;
}

/** The 8-tag controlled vocabulary (PHASE_2_SPEC §3.3). */
export const USE_CASE_TAGS = [
  'scoped-agentic',
  'long-running-session',
  'multi-agent-coordination',
  'memory-augmented-chat',
  'code-generation-focused',
  'analytical-summarization',
  'latency-sensitive',
  'offline-capable'
] as const;

export type UseCaseTag = (typeof USE_CASE_TAGS)[number];

// Synonym table — array of `[phrase, tag]` tuples. Phrases are stored
// lowercase, space-separated. The matcher normalises input
// (lowercase + hyphens/underscores → space + non-alphanumeric → space +
// collapse whitespace) before scanning, so users can write
// "long-running", "long_running", or "long running" and hit the same
// synonym.
//
// Adding a synonym: append `[phrase, tag]`. Phrases that share a prefix
// with a longer phrase do NOT need ordering — the matcher pre-sorts
// longest-first below.
const SYNONYM_TABLE: ReadonlyArray<[string, UseCaseTag]> = [
  // Canonical vocab keys (space-form).
  ['scoped agentic', 'scoped-agentic'],
  ['long running session', 'long-running-session'],
  ['multi agent coordination', 'multi-agent-coordination'],
  ['memory augmented chat', 'memory-augmented-chat'],
  ['code generation focused', 'code-generation-focused'],
  ['analytical summarization', 'analytical-summarization'],
  ['latency sensitive', 'latency-sensitive'],
  ['offline capable', 'offline-capable'],

  // scoped-agentic
  ['narrow agent', 'scoped-agentic'],
  ['scoped agent', 'scoped-agentic'],
  ['single agent', 'scoped-agentic'],

  // long-running-session
  ['long running', 'long-running-session'],
  ['long session', 'long-running-session'],
  ['long lived', 'long-running-session'],
  ['persistent session', 'long-running-session'],

  // multi-agent-coordination
  ['multi agent', 'multi-agent-coordination'],
  ['multiagent', 'multi-agent-coordination'],

  // memory-augmented-chat
  ['memory augmented', 'memory-augmented-chat'],
  ['chat memory', 'memory-augmented-chat'],
  ['chatbot', 'memory-augmented-chat'],

  // code-generation-focused
  ['code generation', 'code-generation-focused'],
  ['code completion', 'code-generation-focused'],
  ['codegen', 'code-generation-focused'],

  // analytical-summarization
  ['summarization', 'analytical-summarization'],
  ['summarisation', 'analytical-summarization'],
  ['summarizing', 'analytical-summarization'],
  ['summarising', 'analytical-summarization'],

  // latency-sensitive
  ['low latency', 'latency-sensitive'],
  ['real time', 'latency-sensitive'],
  ['realtime', 'latency-sensitive'],
  ['fast response', 'latency-sensitive'],

  // offline-capable
  ['offline', 'offline-capable'],
  ['airgap', 'offline-capable'],
  ['airgapped', 'offline-capable'],
  ['air gap', 'offline-capable'],
  ['air gapped', 'offline-capable'],
  ['on prem', 'offline-capable'],
  ['on premises', 'offline-capable']
];

// Pre-sorted longest-first so "long running session" wins over
// "long running" when both could match.
const SORTED_SYNONYMS: ReadonlyArray<[string, UseCaseTag]> = [...SYNONYM_TABLE].sort((a, b) => {
  const wa = a[0].split(' ').length;
  const wb = b[0].split(' ').length;
  if (wa !== wb) return wb - wa;
  if (b[0].length !== a[0].length) return b[0].length - a[0].length;
  return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0;
});

// Filler tokens dropped from `unmatched_terms` so users see substantive
// dropped words (e.g. a vendor name) rather than English connective tissue.
const STOPWORDS: ReadonlySet<string> = new Set([
  'a', 'an', 'the', 'and', 'or', 'but',
  'is', 'are', 'was', 'were', 'be', 'been', 'being',
  'with', 'without', 'for', 'to', 'of', 'in', 'on', 'at', 'by', 'as', 'from',
  'that', 'this', 'these', 'those', 'it', 'its',
  'system', 'systems', 'project', 'projects', 'app', 'apps', 'application', 'applications',
  'need', 'needs', 'needed', 'needing',
  'has', 'have', 'having', 'had',
  'requires', 'require', 'required', 'requiring',
  'use', 'using', 'used', 'usage',
  'we', 'i', 'you', 'they', 'our', 'my', 'your', 'their',
  'one', 'two', 'some', 'any', 'all', 'most', 'many',
  'can', 'should', 'would', 'could', 'must',
  'do', 'does', 'did',
  'capability', 'capabilities', 'support', 'supports', 'supporting', 'supported'
]);

function normaliseInput(text: string): string {
  return text
    .toLowerCase()
    .replace(/[-_]/g, ' ')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Parse free-text into a `ConstraintSet`. Deterministic — no LLM, no
 * network. Same input string ⇒ same parse on every runtime.
 *
 * Behaviour:
 *   • Matches whole-token phrases from `SYNONYM_TABLE` longest-first.
 *   • Each token belongs to at most one phrase (no overlap).
 *   • `matched_terms` reports the canonical phrase per match (insertion
 *     order, which is left-to-right sweep through the synonym table).
 *   • `unmatched_terms` reports tokens left un-claimed after filtering
 *     out stopwords.
 *   • `constraints.use_case_tags` is sorted alphabetically for stable
 *     downstream serialisation.
 */
export function parseFreeTextConstraints(text: string): ParsedConstraints {
  const normalised = normaliseInput(text);
  const tokens = normalised.length > 0 ? normalised.split(' ') : [];
  const claimed: boolean[] = new Array(tokens.length).fill(false);
  const tags = new Set<UseCaseTag>();
  const matched: string[] = [];

  for (const [phrase, tag] of SORTED_SYNONYMS) {
    const phraseTokens = phrase.split(' ');
    const n = phraseTokens.length;
    for (let i = 0; i + n <= tokens.length; i++) {
      let canClaim = true;
      for (let j = 0; j < n; j++) {
        if (claimed[i + j]) { canClaim = false; break; }
      }
      if (!canClaim) continue;
      let isMatch = true;
      for (let j = 0; j < n; j++) {
        if (tokens[i + j] !== phraseTokens[j]) { isMatch = false; break; }
      }
      if (!isMatch) continue;
      for (let j = 0; j < n; j++) claimed[i + j] = true;
      tags.add(tag);
      matched.push(phrase);
    }
  }

  const unmatched: string[] = [];
  for (let i = 0; i < tokens.length; i++) {
    if (claimed[i]) continue;
    const tok = tokens[i];
    if (tok.length === 0) continue;
    if (STOPWORDS.has(tok)) continue;
    unmatched.push(tok);
  }

  const constraints: ConstraintSet = {};
  if (tags.size > 0) {
    constraints.use_case_tags = Array.from(tags).sort();
  }
  return { constraints, matched_terms: matched, unmatched_terms: unmatched };
}

/**
 * Translate a structured-form shape into a `ConstraintSet`. Used by the
 * web `by-constraints` form and the CLI's `--shape`/`--scale`/... flags.
 *
 * Mapping rules (all deterministic, inline-tested by fixtures):
 *   • project_shape → tag (single-agent → scoped-agentic, ...)
 *   • persistence='long-term' → long-running-session
 *   • deployment='offline' → offline-capable
 *   • latency_budget_ms ≤ 1000 → latency-sensitive
 *   • scale='large-scale' → capability_band_min='frontier'
 *   • scale='production' → capability_band_min='competent'
 *   • cost_ceiling_usd_per_mtok → cost_max_input_usd_per_mtok (pass-through)
 */
export function structuredFormToConstraints(form: StructuredForm): ConstraintSet {
  const tags = new Set<UseCaseTag>();

  switch (form.project_shape) {
    case 'single-agent':
      tags.add('scoped-agentic');
      break;
    case 'multi-agent':
      tags.add('multi-agent-coordination');
      break;
    case 'chat':
      tags.add('memory-augmented-chat');
      break;
    case 'pipeline':
      tags.add('analytical-summarization');
      break;
  }

  if (form.persistence === 'long-term') tags.add('long-running-session');
  if (form.deployment === 'offline') tags.add('offline-capable');
  if (form.latency_budget_ms != null && form.latency_budget_ms <= 1000) {
    tags.add('latency-sensitive');
  }

  const constraints: ConstraintSet = {};
  if (tags.size > 0) constraints.use_case_tags = Array.from(tags).sort();
  if (form.cost_ceiling_usd_per_mtok != null) {
    constraints.cost_max_input_usd_per_mtok = form.cost_ceiling_usd_per_mtok;
  }
  if (form.scale === 'large-scale') constraints.capability_band_min = 'frontier';
  else if (form.scale === 'production') constraints.capability_band_min = 'competent';
  return constraints;
}

// =========================================================================
// recommend_for_project surface adapter (issue #98 — Gate 4)
// =========================================================================

export type RecommendCategory = 'memory' | 'harness' | 'model';

/** Snake-cased wire shape for `recommend_for_project` (MCP + CLI). */
export interface RecommendForProjectArgs {
  description?: string;
  structured?: StructuredForm;
  /** Default 5. */
  max_results?: number;
  /** Default `['memory', 'harness', 'model']`. */
  categories?: RecommendCategory[];
}

/** Output shape — `Candidate[]` per category plus the parsed input. */
export interface RecommendForProjectResult {
  parsed_constraints: ConstraintSet;
  matched_terms: string[];
  unmatched_terms: string[];
  candidates: Record<RecommendCategory, Candidate[]>;
}

const ALL_CATEGORIES: readonly RecommendCategory[] = ['memory', 'harness', 'model'];

/**
 * Classify a record into one of `memory`, `harness`, `model`, or `null`
 * (which means "don't surface in any category panel"). Heuristic only —
 * matches against the record's primary section names, in priority order
 * so a record like "Robotics foundation models & agent stacks" lands
 * in `model` and not `harness`.
 */
function categoryOf(record: LandscapeRecord): RecommendCategory | null {
  const sections = (record.sections ?? []).map((s) => s.section.toLowerCase());
  // Model first — "foundation models" beats anything else.
  if (sections.some((s) => s.includes('foundation model'))) return 'model';
  // Memory next — explicit "memory" in the section name.
  if (sections.some((s) => s.includes('memory'))) return 'memory';
  // Harness last — agent/framework/orchestration/IDE/sandbox.
  if (sections.some((s) =>
    s.includes('harness') ||
    s.includes('framework') ||
    s.includes('orchestration') ||
    s.includes('agent ides') ||
    s.includes('sandbox') ||
    s.includes('computer-use') ||
    s.includes('voice agent')
  )) return 'harness';
  return null;
}

/**
 * Surface adapter for the `/recommend/by-constraints` route, the
 * `recommend_for_project` MCP tool, and the `landscape recommend for`
 * CLI subcommand. Translates free-text or a structured form into a
 * `ConstraintSet`, ranks records inside each requested category, and
 * returns the parsed input alongside the ranked candidates so callers
 * can echo the interpretation ("I read your request as …").
 *
 * Determinism: identical args ⇒ byte-identical output. The structured
 * path wins if both `structured` and `description` are present, matching
 * the spec §4.3 contract.
 */
export function recommendForProject(
  records: LandscapeRecord[],
  args: RecommendForProjectArgs,
  options?: RankOptions
): RecommendForProjectResult {
  let constraints: ConstraintSet = {};
  let matched_terms: string[] = [];
  let unmatched_terms: string[] = [];

  if (args.structured) {
    constraints = structuredFormToConstraints(args.structured);
  } else if (args.description) {
    const parsed = parseFreeTextConstraints(args.description);
    constraints = parsed.constraints;
    matched_terms = parsed.matched_terms;
    unmatched_terms = parsed.unmatched_terms;
  }

  const k = Math.max(1, args.max_results ?? DEFAULT_K);
  const cats = args.categories && args.categories.length > 0 ? args.categories : ALL_CATEGORIES;

  const buckets: Record<RecommendCategory, LandscapeRecord[]> = {
    memory: [],
    harness: [],
    model: []
  };
  for (const r of records) {
    const c = categoryOf(r);
    if (c) buckets[c].push(r);
  }

  const candidates: Record<RecommendCategory, Candidate[]> = {
    memory: [],
    harness: [],
    model: []
  };
  for (const c of cats) {
    candidates[c] = rankCandidates(buckets[c], constraints, undefined, k, options);
  }

  return {
    parsed_constraints: constraints,
    matched_terms,
    unmatched_terms,
    candidates
  };
}

/**
 * Snake-cased argument shape for the MCP `between_models` tool and the
 * `landscape recommend between` CLI subcommand (issue #97). Surfaces
 * keep one wire shape so determinism tests can serialise a single set
 * of inputs across web / MCP / CLI.
 */
export interface BetweenModelsArgs {
  anchor_low_id: string;
  anchor_high_id: string;
  /** Single tag from the controlled vocabulary. Optional. */
  use_case?: string;
  /** Max candidates to return (default 5). */
  k?: number;
}

/**
 * Surface adapter around `rankCandidates`. Resolves anchor ids into an
 * `AnchorPair`, wraps an optional single `use_case` into a one-element
 * `ConstraintSet.use_case_tags`, and delegates ranking. Returns the
 * same `Candidate[]` shape — see `rankCandidates`.
 */
export function betweenModels(
  records: LandscapeRecord[],
  args: BetweenModelsArgs,
  options?: RankOptions
): Candidate[] {
  const constraints: ConstraintSet = args.use_case
    ? { use_case_tags: [args.use_case] }
    : {};
  const anchors: AnchorPair = {
    low: args.anchor_low_id,
    high: args.anchor_high_id
  };
  return rankCandidates(records, constraints, anchors, args.k, options);
}

/**
 * Rank catalog records against a constraint set and/or an anchor pair.
 * See the module docstring for behavioural contract.
 *
 * Returns at most `k` candidates (default 5), sorted by score desc with
 * locale-independent id tie-break.
 */
export function rankCandidates(
  records: LandscapeRecord[],
  constraints: ConstraintSet,
  anchors?: AnchorPair,
  k?: number,
  options?: RankOptions
): Candidate[] {
  const today = options?.today ?? DEFAULT_TODAY;
  const staleDays = options?.staleDays ?? DEFAULT_STALE_DAYS;
  const limit = Math.max(1, k ?? DEFAULT_K);

  const derived: DerivedRow[] = records.map(derive);

  let pool: DerivedRow[];
  if (anchors) {
    const low = derived.find((d) => d.record.id === anchors.low);
    const high = derived.find((d) => d.record.id === anchors.high);
    if (!low || !high) {
      // Caller passed an unknown anchor id — empty result (don't throw;
      // the surface layer renders the empty state).
      return [];
    }
    // Anchors are user-chosen *positioning* points; we read their raw
    // cell values regardless of provenance. They are not scored.
    const costRange = numRange(low.costUsd, high.costUsd);
    const capRange = numRange(low.capScore, high.capScore);
    pool = derived.filter((d) => {
      if (d.record.id === anchors.low || d.record.id === anchors.high) return false;
      if (costRange && d.costUsd != null && !inRange(d.costUsd, costRange)) return false;
      if (capRange && d.capScore != null && !inRange(d.capScore, capRange)) return false;
      // Need at least one dimension populated to be placeable.
      if (d.costUsd == null && d.capScore == null) return false;
      // If neither anchor dimension yielded a range (both anchors had
      // null cells), the anchor pair gives no positioning signal.
      if (!costRange && !capRange) return false;
      return true;
    });
  } else {
    pool = derived;
  }

  const candidates: Candidate[] = pool.map((d) =>
    scoreOne(d, constraints, today, staleDays, !!anchors)
  );

  candidates.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return cmpId(a.record.id, b.record.id);
  });

  return candidates.slice(0, limit);
}
