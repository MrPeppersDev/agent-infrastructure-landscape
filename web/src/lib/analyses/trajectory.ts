// Pure helpers for the /analyses/trajectory view (issue #34).
//
// Combines multiple per-record signals (funding cadence, release recency,
// GH stars, mindshare/citations, inbound edges, lineage membership) into
// a single trajectory bucket per record:
//
//   - 'accelerating'  velocity signal positive (recent funding round
//                     within 12mo OR newest member of an active lineage
//                     OR strong star/release velocity)
//   - 'steady'        funded or shipped previously, still cited, still
//                     maintained — no recent acceleration, no decay
//   - 'decelerating'  no funding event in 18+mo, low recent citation
//                     pickup, stale repo — the slope is down but not
//                     yet flatlined
//   - 'dead'          cross-references survivorship.ts — Abandoned (or
//                     research+stale-repo) routes here so the cohort
//                     table doesn't double-count
//   - 'unknown'       not enough signal to score
//
// Heuristic — openly speculative. The five panels below all carry
// confidence labels in the page layer; the underlying rules are documented
// in docs/DECISIONS.md under "2026-05-13: Trajectory view heuristics".

import type { Edge, LandscapeRecord } from '$lib/types';
import type { Lineage } from '$lib/lineages';
import { parseDateLatest, parseLastCommit, monthsBetween, TODAY } from './survivorship';

// --- Trajectory bucket -------------------------------------------------

export type Trajectory =
  | 'accelerating'
  | 'steady'
  | 'decelerating'
  | 'dead'
  | 'unknown';

export const TRAJECTORY_ORDER: Trajectory[] = [
  'accelerating',
  'steady',
  'decelerating',
  'dead',
  'unknown'
];

export const TRAJECTORY_LABELS: Record<Trajectory, string> = {
  accelerating: 'Accelerating',
  steady: 'Steady',
  decelerating: 'Decelerating',
  dead: 'Dead / abandoned',
  unknown: 'Unknown'
};

export const TRAJECTORY_COLOURS: Record<Trajectory, string> = {
  accelerating: '#3fb950',
  steady: '#79c0ff',
  decelerating: '#d29922',
  dead: '#f85149',
  unknown: '#8b949e'
};

/** Thresholds (months). */
export const RECENT_FUNDING_MAX_MONTHS = 12;
export const STALE_FUNDING_MIN_MONTHS = 18;
export const STALE_RELEASE_MIN_MONTHS = 18;
export const DEAD_AGE_MONTHS = 24;

// --- Per-record signal pack -------------------------------------------

export interface TrajectorySignals {
  /** Months since the most recent funding round, or null when unknown. */
  fundingAgeMonths: number | null;
  /** Funding amount text (free-form e.g. "$100M Series B") if extractable. */
  fundingNote: string | null;
  /** Months since latest-release, or null. */
  releaseAgeMonths: number | null;
  /** Months since the parsed last commit (code-release cell), or null. */
  commitAgeMonths: number | null;
  /** GitHub stars (integer) if extractable. */
  stars: number | null;
  /** Mindshare score (integer) if extractable. */
  mindshare: number | null;
  /** Citation count if extractable. */
  citations: number | null;
  /** Inbound integration edge count. */
  inboundIntegrations: number;
  /** Inbound citation edge count. */
  inboundCitations: number;
  /** Lineage name when the record is the newest member of one of the
   *  detected lineages, else null. The "newest member" status is the
   *  velocity-boost referenced in the issue. */
  leadingEdgeOfLineage: string | null;
  /** Substrate dependency string (e.g. "Claude", "GPT-5"), or null. */
  substrate: string | null;
}

export interface TrajectoryClassification {
  trajectory: Trajectory;
  /** Human-readable summary of the dominant reason. */
  reason: string;
  /** Confidence label (low / medium / high). High = multiple signals agree. */
  confidence: 'low' | 'medium' | 'high';
  signals: TrajectorySignals;
}

// --- Signal extractors -------------------------------------------------

/** Pull stars from a `gh` cell. Looks for "12.5k stars", "1,234 stars". */
export function parseStars(raw: string | null | undefined): number | null {
  if (!raw) return null;
  const v = raw.toLowerCase();
  const km = v.match(/(\d+(?:\.\d+)?)\s*k\s*(?:gh\s*)?stars?/);
  if (km) return Math.round(Number(km[1]) * 1000);
  const num = v.match(/(\d{1,3}(?:,\d{3})+|\d+)\s*(?:gh\s*)?stars?/);
  if (num) return Number(num[1].replace(/,/g, ''));
  return null;
}

/** Pull a mindshare integer ("score: 42", "mindshare 87/100"). */
export function parseMindshare(raw: string | null | undefined): number | null {
  if (!raw) return null;
  const v = raw.toLowerCase();
  const m = v.match(/(?:score|index|mindshare)[^0-9]{0,8}(\d{1,4})/);
  if (m) return Number(m[1]);
  // Fall back to a bare leading integer ("42 — strong adoption ...").
  const lead = v.match(/^\s*(\d{1,4})\b/);
  if (lead) return Number(lead[1]);
  return null;
}

/** Pull citations count. Handles "1,234 citations", "287 Semantic Scholar". */
export function parseCitations(raw: string | null | undefined): number | null {
  if (!raw) return null;
  const v = raw.toLowerCase();
  const km = v.match(/(\d+(?:\.\d+)?)\s*k\s*(?:citations?|cites?)/);
  if (km) return Math.round(Number(km[1]) * 1000);
  const num = v.match(/(\d{1,3}(?:,\d{3})+|\d+)\s*(?:citations?|cites?)/);
  if (num) return Number(num[1].replace(/,/g, ''));
  return null;
}

/** Pull the latest funding-round date and a short note. */
export function parseFunding(
  raw: string | null | undefined
): { date: Date | null; note: string | null } {
  if (!raw) return { date: null, note: null };
  const date = parseDateLatest(raw);
  // Extract round label + amount when visible.
  const round = raw.match(
    /(seed|pre-seed|series\s+[a-h]|grant|acquired|acquisition|ipo|secondary)/i
  );
  const amount = raw.match(/\$\s?\d+(?:\.\d+)?\s*[mb]/i);
  const note = [round?.[0], amount?.[0]].filter(Boolean).join(' · ') || null;
  return { date, note };
}

/** Find a foundation-model substrate mentioned in claims/desc/cells. */
const SUBSTRATES = [
  'Claude',
  'GPT-5',
  'GPT-4',
  'GPT-4o',
  'GPT-3.5',
  'Gemini',
  'Llama',
  'Mistral',
  'DeepSeek',
  'Qwen',
  'Grok',
  'o1',
  'o3'
];

export function findSubstrate(record: LandscapeRecord): string | null {
  const haystacks: string[] = [];
  for (const slug of ['desc', 'claims', 'llm-lock', 'embedding-model'] as const) {
    const c = record.cells[slug];
    if (c?.value) haystacks.push(c.value);
  }
  const hay = haystacks.join(' · ').toLowerCase();
  if (!hay) return null;
  // Multi-FM agnostic detection.
  const hits: string[] = [];
  for (const s of SUBSTRATES) {
    if (hay.includes(s.toLowerCase())) hits.push(s);
  }
  if (hits.length === 0) return null;
  // Multi-FM agnostic gets its own label so the panel can group.
  if (hits.length >= 3) return 'multi-FM';
  if (hits.length === 2) return hits.join(' + ');
  return hits[0];
}

// --- Lineage helpers ---------------------------------------------------

/** Map each record id → the lineage name it's the newest (latest-created)
 *  member of, if any. Used to gate the "newest in active lineage" boost. */
export function leadingEdgeByLineage(lineages: Lineage[]): Map<string, string> {
  const m = new Map<string, string>();
  for (const l of lineages) {
    if (l.members.length === 0) continue;
    // members are pre-sorted by created date ascending — last is newest.
    const newest = l.members[l.members.length - 1];
    m.set(newest, l.name);
  }
  return m;
}

// --- Per-record signal extraction --------------------------------------

export function extractSignals(
  record: LandscapeRecord,
  inboundIntegrations: Map<string, number>,
  inboundCitations: Map<string, number>,
  leadingEdge: Map<string, string>
): TrajectorySignals {
  const funding = parseFunding(record.cells.funding?.value);
  const fundingAge = funding.date ? monthsBetween(funding.date, TODAY) : null;

  const releaseDate = parseDateLatest(record.cells['latest-release']?.value);
  const releaseAge = releaseDate ? monthsBetween(releaseDate, TODAY) : null;

  const commitDate = parseLastCommit(record.cells['code-release']?.value);
  const commitAge = commitDate ? monthsBetween(commitDate, TODAY) : null;

  return {
    fundingAgeMonths: fundingAge,
    fundingNote: funding.note,
    releaseAgeMonths: releaseAge,
    commitAgeMonths: commitAge,
    stars: parseStars(record.cells.gh?.value),
    mindshare: parseMindshare(record.cells.mindshare?.value),
    citations: parseCitations(record.cells.citations?.value),
    inboundIntegrations: inboundIntegrations.get(record.id) ?? 0,
    inboundCitations: inboundCitations.get(record.id) ?? 0,
    leadingEdgeOfLineage: leadingEdge.get(record.id) ?? null,
    substrate: findSubstrate(record)
  };
}

// --- Classification rules ---------------------------------------------

export function classify(
  record: LandscapeRecord,
  signals: TrajectorySignals,
  survivorshipDead: boolean
): TrajectoryClassification {
  // Dead overrides everything else — survivorship has higher confidence
  // than our trajectory heuristics for the dead bucket.
  if (survivorshipDead) {
    return {
      trajectory: 'dead',
      reason: 'No release/commit signal in 24+ months (per survivorship)',
      confidence: 'high',
      signals
    };
  }

  const accelerationReasons: string[] = [];
  const decelerationReasons: string[] = [];

  if (
    signals.fundingAgeMonths !== null &&
    signals.fundingAgeMonths <= RECENT_FUNDING_MAX_MONTHS
  ) {
    accelerationReasons.push(
      `funded ${signals.fundingAgeMonths}mo ago${signals.fundingNote ? ' (' + signals.fundingNote + ')' : ''}`
    );
  }
  if (signals.leadingEdgeOfLineage) {
    accelerationReasons.push(
      `newest member of "${signals.leadingEdgeOfLineage}" lineage`
    );
  }
  if (signals.stars !== null && signals.stars >= 10000) {
    accelerationReasons.push(`${signals.stars.toLocaleString()} GH stars`);
  }
  if (signals.mindshare !== null && signals.mindshare >= 70) {
    accelerationReasons.push(`mindshare ${signals.mindshare}`);
  }

  if (
    signals.fundingAgeMonths !== null &&
    signals.fundingAgeMonths >= STALE_FUNDING_MIN_MONTHS
  ) {
    decelerationReasons.push(
      `last funding ${signals.fundingAgeMonths}mo ago`
    );
  }
  if (
    signals.releaseAgeMonths !== null &&
    signals.releaseAgeMonths >= STALE_RELEASE_MIN_MONTHS
  ) {
    decelerationReasons.push(
      `last release ${signals.releaseAgeMonths}mo ago`
    );
  }
  if (
    signals.commitAgeMonths !== null &&
    signals.commitAgeMonths >= STALE_RELEASE_MIN_MONTHS
  ) {
    decelerationReasons.push(
      `last commit ${signals.commitAgeMonths}mo ago`
    );
  }

  // Acceleration wins when there is ANY recent positive signal — the
  // intent of this view is "what's moving" not "what's perfect".
  if (accelerationReasons.length > 0) {
    return {
      trajectory: 'accelerating',
      reason: accelerationReasons.join(' · '),
      confidence: accelerationReasons.length >= 2 ? 'high' : 'medium',
      signals
    };
  }

  if (decelerationReasons.length >= 2) {
    return {
      trajectory: 'decelerating',
      reason: decelerationReasons.join(' · '),
      confidence: 'medium',
      signals
    };
  }

  // Steady = some positive evidence (cited / integrated / not stale)
  // without any acceleration signal.
  const hasAnySignal =
    signals.inboundIntegrations > 0 ||
    signals.inboundCitations > 0 ||
    signals.releaseAgeMonths !== null ||
    signals.commitAgeMonths !== null ||
    signals.fundingAgeMonths !== null;
  if (hasAnySignal) {
    const bits: string[] = [];
    if (signals.inboundIntegrations > 0)
      bits.push(`${signals.inboundIntegrations} integrations`);
    if (signals.inboundCitations > 0)
      bits.push(`${signals.inboundCitations} citations`);
    if (signals.fundingAgeMonths !== null)
      bits.push(`funded ${signals.fundingAgeMonths}mo ago`);
    return {
      trajectory: 'steady',
      reason: bits.join(' · ') || 'still cited and maintained',
      confidence: 'low',
      signals
    };
  }

  return {
    trajectory: 'unknown',
    reason: 'no usable signals in cells',
    confidence: 'low',
    signals
  };
}

// --- Bulk classification ----------------------------------------------

export interface TrajectoryRow {
  record: LandscapeRecord;
  classification: TrajectoryClassification;
}

export function classifyAll(
  records: LandscapeRecord[],
  edges: Edge[],
  lineages: Lineage[],
  survivorshipDead: Set<string>
): Map<string, TrajectoryClassification> {
  const inboundIntegrations = new Map<string, number>();
  const inboundCitations = new Map<string, number>();
  for (const e of edges) {
    if (e.type === 'integrates-with' || e.type === 'built-on') {
      inboundIntegrations.set(e.target, (inboundIntegrations.get(e.target) ?? 0) + 1);
    } else if (e.type === 'cites') {
      inboundCitations.set(e.target, (inboundCitations.get(e.target) ?? 0) + 1);
    }
  }
  const leading = leadingEdgeByLineage(lineages);
  const out = new Map<string, TrajectoryClassification>();
  for (const r of records) {
    const signals = extractSignals(r, inboundIntegrations, inboundCitations, leading);
    const cls = classify(r, signals, survivorshipDead.has(r.id));
    out.set(r.id, cls);
  }
  return out;
}

export interface BucketCounts {
  accelerating: number;
  steady: number;
  decelerating: number;
  dead: number;
  unknown: number;
  total: number;
}

export function countBuckets(
  classifications: Map<string, TrajectoryClassification>
): BucketCounts {
  const c: BucketCounts = {
    accelerating: 0,
    steady: 0,
    decelerating: 0,
    dead: 0,
    unknown: 0,
    total: 0
  };
  for (const v of classifications.values()) {
    c[v.trajectory] += 1;
    c.total += 1;
  }
  return c;
}

// --- Panel 2: substrate dependency risk -------------------------------

export interface SubstrateDependency {
  substrate: string;
  members: { record: LandscapeRecord; cls: TrajectoryClassification }[];
  singleVendorRisk: boolean;
}

export function substrateDependencies(
  records: LandscapeRecord[],
  classifications: Map<string, TrajectoryClassification>
): SubstrateDependency[] {
  const groups = new Map<string, SubstrateDependency>();
  for (const r of records) {
    const cls = classifications.get(r.id);
    if (!cls) continue;
    const sub = cls.signals.substrate;
    if (!sub) continue;
    let g = groups.get(sub);
    if (!g) {
      g = {
        substrate: sub,
        members: [],
        singleVendorRisk: sub !== 'multi-FM' && !sub.includes('+')
      };
      groups.set(sub, g);
    }
    g.members.push({ record: r, cls });
  }
  return [...groups.values()].sort((a, b) => b.members.length - a.members.length);
}

// --- Panel 3: consolidation candidates --------------------------------

/** Predicted consolidation categories with seeded recent precedents. The
 *  signal model: small-but-real funding presence + high inbound integration
 *  edges + tier (T1/T2) + matching keywords in section / desc. */
export interface ConsolidationCategory {
  id: string;
  label: string;
  precedent: string;
  /** Keyword fragments to test (lowercase) against record sections / desc. */
  keywords: string[];
  candidates: ConsolidationCandidate[];
}

export interface ConsolidationCandidate {
  record: LandscapeRecord;
  cls: TrajectoryClassification;
  score: number;
  reason: string;
}

const CONSOLIDATION_CATEGORIES: Omit<ConsolidationCategory, 'candidates'>[] = [
  {
    id: 'embedding',
    label: 'Embedding-vendor consolidation',
    precedent: 'Voyage → MongoDB (Feb 2025)',
    keywords: ['embedding', 'embed model', 'embedding model', 'retrieval embedding']
  },
  {
    id: 'inference',
    label: 'Inference-platform consolidation',
    precedent: 'Quickwit → Datadog (Dec 2024) · OctoAI → NVIDIA (Oct 2024)',
    keywords: ['inference', 'serving', 'gpu cloud', 'model hosting']
  },
  {
    id: 'vector-db',
    label: 'Vector-DB consolidation',
    precedent: 'Pinecone serverless pivot',
    keywords: ['vector database', 'vector db', 'vector store', 'vector search']
  }
];

function matchKeyword(record: LandscapeRecord, kws: string[]): boolean {
  const haystacks: string[] = [];
  haystacks.push(record.name.toLowerCase());
  const desc = record.cells.desc?.value?.toLowerCase() ?? '';
  haystacks.push(desc);
  for (const sec of record.sections) {
    haystacks.push(sec.section.toLowerCase());
    if (sec.subsection) haystacks.push(sec.subsection.toLowerCase());
  }
  const joined = haystacks.join(' | ');
  return kws.some((k) => joined.includes(k));
}

export function consolidationCandidates(
  records: LandscapeRecord[],
  classifications: Map<string, TrajectoryClassification>
): ConsolidationCategory[] {
  const out: ConsolidationCategory[] = [];
  for (const cat of CONSOLIDATION_CATEGORIES) {
    const candidates: ConsolidationCandidate[] = [];
    for (const r of records) {
      const cls = classifications.get(r.id);
      if (!cls) continue;
      if (cls.trajectory === 'dead' || cls.trajectory === 'unknown') continue;
      if (!matchKeyword(r, cat.keywords)) continue;

      // Score = inbound integrations (strongest M&A signal — buyers want
      // existing customer pipes) + small bonus for T1/T2 + funding bonus.
      let score = cls.signals.inboundIntegrations * 3;
      score += cls.signals.inboundCitations;
      if (r.tier === 1) score += 4;
      else if (r.tier === 2) score += 2;
      if (
        cls.signals.fundingAgeMonths !== null &&
        cls.signals.fundingAgeMonths <= 24
      ) {
        score += 2;
      }
      if (score <= 0) continue;
      const reasonBits: string[] = [];
      if (cls.signals.inboundIntegrations > 0)
        reasonBits.push(`${cls.signals.inboundIntegrations} integrations`);
      if (cls.signals.fundingAgeMonths !== null)
        reasonBits.push(`funded ${cls.signals.fundingAgeMonths}mo ago`);
      reasonBits.push(`T${r.tier}`);
      candidates.push({
        record: r,
        cls,
        score,
        reason: reasonBits.join(' · ')
      });
    }
    candidates.sort(
      (a, b) => b.score - a.score || a.record.name.localeCompare(b.record.name)
    );
    out.push({ ...cat, candidates: candidates.slice(0, 3) });
  }
  return out;
}

// --- Panel 4: billion-$ valuation candidates --------------------------

export interface ValuationCandidate {
  record: LandscapeRecord;
  cls: TrajectoryClassification;
  score: number;
  reason: string;
  confidence: 'low' | 'medium' | 'high';
}

export function billionDollarCandidates(
  records: LandscapeRecord[],
  classifications: Map<string, TrajectoryClassification>
): ValuationCandidate[] {
  const out: ValuationCandidate[] = [];
  for (const r of records) {
    const cls = classifications.get(r.id);
    if (!cls) continue;
    if (cls.trajectory !== 'accelerating' && cls.trajectory !== 'steady') continue;
    const s = cls.signals;

    let score = 0;
    const reasons: string[] = [];

    if (s.fundingAgeMonths !== null && s.fundingAgeMonths <= 12) {
      score += 4;
      reasons.push(
        `recent funding (${s.fundingAgeMonths}mo${s.fundingNote ? ' · ' + s.fundingNote : ''})`
      );
    }
    if (s.stars !== null) {
      if (s.stars >= 30000) {
        score += 4;
        reasons.push(`${(s.stars / 1000).toFixed(0)}k stars`);
      } else if (s.stars >= 10000) {
        score += 2;
        reasons.push(`${(s.stars / 1000).toFixed(0)}k stars`);
      }
    }
    if (s.inboundIntegrations >= 5) {
      score += 3;
      reasons.push(`${s.inboundIntegrations} integrations`);
    } else if (s.inboundIntegrations >= 2) {
      score += 1;
      reasons.push(`${s.inboundIntegrations} integrations`);
    }
    if (s.mindshare !== null && s.mindshare >= 70) {
      score += 2;
      reasons.push(`mindshare ${s.mindshare}`);
    }
    if (r.tier === 1) score += 1;
    if (score < 5) continue;

    const confidence: 'low' | 'medium' | 'high' =
      score >= 10 ? 'high' : score >= 7 ? 'medium' : 'low';
    out.push({
      record: r,
      cls,
      score,
      reason: reasons.join(' · '),
      confidence
    });
  }
  return out
    .sort((a, b) => b.score - a.score || a.record.name.localeCompare(b.record.name))
    .slice(0, 10);
}

// --- Panel 5: categories likely to die --------------------------------

export interface DyingCandidate {
  record: LandscapeRecord;
  cls: TrajectoryClassification;
  score: number;
  reason: string;
  confidence: 'low' | 'medium' | 'high';
}

export function dyingCandidates(
  records: LandscapeRecord[],
  classifications: Map<string, TrajectoryClassification>,
  lineageCadenceByMember: Map<string, number>
): DyingCandidate[] {
  const out: DyingCandidate[] = [];
  for (const r of records) {
    const cls = classifications.get(r.id);
    if (!cls) continue;
    // Already-dead doesn't belong on the "likely to die" list — those are
    // gone, not dying. We want the slope-down rows.
    if (cls.trajectory !== 'decelerating' && cls.trajectory !== 'unknown') continue;

    const s = cls.signals;
    let score = 0;
    const reasons: string[] = [];

    if (s.inboundIntegrations === 0) {
      score += 2;
      reasons.push('0 integrations');
    }
    if (s.inboundCitations === 0) {
      score += 1;
      reasons.push('0 citations');
    }
    if (s.fundingAgeMonths === null) {
      score += 1;
      reasons.push('no parseable funding signal');
    } else if (s.fundingAgeMonths >= 24) {
      score += 2;
      reasons.push(`last funding ${s.fundingAgeMonths}mo ago`);
    }
    if (s.releaseAgeMonths !== null && s.releaseAgeMonths >= 18) {
      score += 2;
      reasons.push(`last release ${s.releaseAgeMonths}mo ago`);
    }
    // Slow lineage cadence (>4 quarters between drops) AND member → bonus.
    const cadence = lineageCadenceByMember.get(r.id);
    if (cadence !== undefined && cadence > 4) {
      score += 1;
      reasons.push(`lineage cadence ${cadence.toFixed(1)} quarters`);
    }
    if (score < 4) continue;

    const confidence: 'low' | 'medium' | 'high' =
      score >= 7 ? 'high' : score >= 5 ? 'medium' : 'low';
    out.push({
      record: r,
      cls,
      score,
      reason: reasons.join(' · '),
      confidence
    });
  }
  return out
    .sort((a, b) => b.score - a.score || a.record.name.localeCompare(b.record.name))
    .slice(0, 10);
}

/** Build a map record-id → average lineage cadence in quarters. Needed by
 *  `dyingCandidates` to surface slow-cadence families.  */
export function lineageCadenceByMember(
  lineages: Lineage[],
  cadenceByLineageId: Map<string, number>
): Map<string, number> {
  const out = new Map<string, number>();
  for (const l of lineages) {
    const cadence = cadenceByLineageId.get(l.id);
    if (cadence === undefined || !isFinite(cadence)) continue;
    for (const id of l.members) out.set(id, cadence);
  }
  return out;
}
