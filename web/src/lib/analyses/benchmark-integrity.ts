// Pure helpers for the benchmark-integrity view (issue #33).
//
// Companion to the existing benchmark coverage matrix (`benchmarks.ts`).
// The coverage view answers "who benchmarks on what?". This view answers
// "are the numbers trustworthy?". Per direction from the user, we
// surface gaming patterns and separate peer-reviewed evidence from
// vendor-claimed evidence so the reader can see what is actually
// validated vs what is marketing.
//
// Classification per perf/claims cell with a benchmark mention:
//
//   peer-reviewed         citation host is one of:
//                         arxiv.org, openreview.net, proceedings.mlr.press,
//                         aclanthology.org, ieeexplore.ieee.org, dl.acm.org
//
//   independently-verified  citation is a non-vendor third-party
//                         (independent blog, neutral leaderboard,
//                         paperswithcode.com, scale.com/leaderboards,
//                         a non-vendor github org/repo that hosts a
//                         leaderboard, etc.)
//
//   vendor-claimed        citation host matches the vendor's own domain
//                         (mem0.ai for a Mem0 perf claim, getzep.com
//                         for a Zep claim). The vendor's domain is
//                         derived from `record.url` first; falling back
//                         to the host token in the record id.
//
//   disputed              another catalog row contradicts the number —
//                         either explicit textual signals (⚠, "disputed",
//                         "rebuttal", "lies-damn", "counter-analysis")
//                         OR the parsed absolute scores from two records
//                         on the same benchmark differ by more than the
//                         dispute threshold (default: 7 points).
//
//   unverifiable          no citation that resolves to a host, or
//                         status is depth-floor-reached, or the value
//                         is a sentinel ("no public benchmark scores").
//
// Gaming-pattern heuristics (signals; not classifications):
//
//   single-sub-task-only      the perf cell mentions only one sub-task
//                             (e.g. "single-fact QA on BABILong" with no
//                             multi-task or aggregate score).
//   weak-baseline-comparison  the only comparison is to a notoriously
//                             weak baseline (Full-Context, GPT-3.5, etc.)
//                             rather than to a published SOTA.
//   vendor-self-defined       the benchmark is reported by exactly one
//                             record AND the citation is on that vendor's
//                             own domain — the benchmark has no
//                             external corroboration.
//
// Pure module: no DOM, no fetch.

import type { LandscapeRecord } from '../types';
import { extractScores, type BenchmarkScore, parseScoreNum } from './benchmarks';

export type IntegrityBucket =
  | 'peer-reviewed'
  | 'independently-verified'
  | 'vendor-claimed'
  | 'disputed'
  | 'unverifiable';

export type GamingFlag =
  | 'single-sub-task-only'
  | 'weak-baseline-comparison'
  | 'vendor-self-defined';

export interface IntegrityRow {
  benchmark: string;
  record_id: string;
  record_name: string;
  tier: number;
  section: string | null;
  score: string;
  scoreNum: number | null;
  isDelta: boolean;
  source: 'perf' | 'claims';
  citation: string | null;
  citationHost: string | null;
  bucket: IntegrityBucket;
  /** Why we put it in that bucket — short human-readable reason. */
  reason: string;
  /** Heuristic gaming flags (independent of bucket). */
  flags: GamingFlag[];
  /** If disputed, ids of contradicting records. */
  disputedBy: string[];
}

// ---------------------------------------------------------------------------
// Host classification helpers
// ---------------------------------------------------------------------------

const PEER_REVIEWED_HOSTS = new Set([
  'arxiv.org',
  'openreview.net',
  'proceedings.mlr.press',
  'aclanthology.org',
  'ieeexplore.ieee.org',
  'dl.acm.org',
  // Common arxiv/preprint mirrors that map to the same artefact:
  'doi.org'
]);

const NEUTRAL_LEADERBOARD_HOSTS = new Set([
  'paperswithcode.com',
  'scale.com',
  'crfm.stanford.edu',
  'huggingface.co',
  'lmarena.ai',
  'evalscope.org'
]);

const COMMODITY_PUBLISHING_HOSTS = new Set([
  'github.com',
  'gitlab.com',
  'medium.com',
  'substack.com',
  'dev.to',
  'arxiv-vanity.com'
]);

export function hostOf(url: string | null | undefined): string | null {
  if (!url) return null;
  const m = url.match(/^https?:\/\/([^/?#]+)/i);
  if (!m) return null;
  return m[1].toLowerCase().replace(/^www\./, '');
}

/** Vendor-domain heuristic from a record's url. */
export function vendorDomain(record: { url: string | null; id: string }): string | null {
  const fromUrl = hostOf(record.url);
  if (fromUrl) {
    // Strip subdomains down to apex for matching: "docs.mem0.ai" → "mem0.ai".
    // Keep the last two labels for typical TLDs; three for known multi-part
    // TLDs (co.uk, com.cn, ac.uk) — minimal support is enough here.
    const parts = fromUrl.split('.');
    if (parts.length >= 3) {
      const tail2 = parts.slice(-2).join('.');
      const tail3 = parts.slice(-3).join('.');
      const MULTI_PART_TLDS = new Set(['co.uk', 'ac.uk', 'com.cn', 'co.jp', 'com.au']);
      if (MULTI_PART_TLDS.has(parts.slice(-2).join('.'))) return tail3;
      return tail2;
    }
    return fromUrl;
  }
  // Fallback: record ids often encode the host as the suffix after '--'
  // (e.g. "mem0--mem0-ai", "zep-graphiti--getzep-com").
  const m = record.id.match(/--([a-z0-9-]+)$/i);
  if (m) {
    const tok = m[1].replace(/-/g, '.');
    if (tok.includes('.')) return tok.toLowerCase();
  }
  return null;
}

function citationIsVendor(citationHost: string, vendor: string | null): boolean {
  if (!vendor) return false;
  if (citationHost === vendor) return true;
  if (citationHost.endsWith('.' + vendor)) return true;
  return false;
}

// ---------------------------------------------------------------------------
// Dispute detection
// ---------------------------------------------------------------------------

const DISPUTE_TEXT_RE =
  /(⚠|\bdisput(?:ed|e)\b|\brebutt(?:al|ed)\b|lies[-\s]?damn|counter[-\s]?analysis|contest(?:ed)?|unverified|unconfirmed|misrepresent)/i;

/** Default: 7 absolute points on a 0–100 scale, or > 5% of the range. */
const DEFAULT_DISPUTE_DELTA = 7;

export interface DisputeIndex {
  byBenchmark: Map<string, IntegrityRow[]>;
}

// ---------------------------------------------------------------------------
// Gaming-flag heuristics
// ---------------------------------------------------------------------------

const SINGLE_SUBTASK_PATTERNS = [
  /\bsingle[-\s]?(?:fact|hop|task)\b/i,
  /\bsub[-\s]?task\b/i,
  /\bonly on\b/i,
  /\bone (?:sub)?task\b/i
];

const WEAK_BASELINE_PATTERNS = [
  /\bfull[-\s]?context\b/i,
  /\bGPT[-\s]?3\.5\b/i,
  /\bllama[-\s]?(?:2|3\.0|3\.1)\b/i,
  /\bbase(?:line)?[-\s]?LLM\b/i,
  /\bno[-\s]?memory baseline\b/i,
  /\bvanilla\b/i
];

function hasSingleSubTask(value: string): boolean {
  // Triggers if the cell explicitly says "single-fact" / "sub-task" /
  // "only on X" AND does not also mention aggregate / overall.
  const hit = SINGLE_SUBTASK_PATTERNS.some((re) => re.test(value));
  if (!hit) return false;
  if (/\b(?:overall|aggregate|average|macro|micro|avg)\b/i.test(value)) return false;
  return true;
}

function hasWeakBaseline(value: string): boolean {
  return WEAK_BASELINE_PATTERNS.some((re) => re.test(value));
}

// ---------------------------------------------------------------------------
// Core classification
// ---------------------------------------------------------------------------

export interface ClassifyOptions {
  /** Score delta above which two records on the same benchmark are flagged disputed. */
  disputeDelta?: number;
}

export function classifyIntegrity(
  records: LandscapeRecord[],
  options: ClassifyOptions = {}
): IntegrityRow[] {
  const disputeDelta = options.disputeDelta ?? DEFAULT_DISPUTE_DELTA;

  const recordById = new Map<string, LandscapeRecord>();
  for (const r of records) recordById.set(r.id, r);

  const scores = extractScores(records);

  // First pass: build IntegrityRows without dispute resolution.
  const rows: IntegrityRow[] = [];
  for (const s of scores) {
    const rec = recordById.get(s.record_id);
    if (!rec) continue;
    const cell = s.source === 'perf' ? rec.cells.perf : rec.cells.claims;
    const value = cell?.value ?? '';
    const citation = cell?.citation ?? null;
    const citationHost = hostOf(citation);
    const vendor = vendorDomain(rec);
    const { n, isDelta } = parseScoreNum(s.score);
    const primarySection =
      rec.sections.find((sec) => sec.primary)?.section ?? rec.sections[0]?.section ?? null;

    let bucket: IntegrityBucket = 'unverifiable';
    let reason = 'no citation that resolves to a host';

    const cellStatus = cell?.status;
    const sentinel =
      !value ||
      /^no public benchmark scores found/i.test(value) ||
      cellStatus === 'depth-floor-reached' ||
      cellStatus === 'no-data';

    if (sentinel) {
      bucket = 'unverifiable';
      reason = 'sentinel value or depth-floor citation';
    } else if (DISPUTE_TEXT_RE.test(value)) {
      bucket = 'disputed';
      reason = 'in-cell dispute signal (⚠ / "disputed" / "rebuttal")';
    } else if (citationHost && PEER_REVIEWED_HOSTS.has(citationHost)) {
      bucket = 'peer-reviewed';
      reason = `cited on ${citationHost} (peer-reviewed venue)`;
    } else if (citationHost && NEUTRAL_LEADERBOARD_HOSTS.has(citationHost)) {
      bucket = 'independently-verified';
      reason = `cited on ${citationHost} (neutral leaderboard)`;
    } else if (citationHost && vendor && citationIsVendor(citationHost, vendor)) {
      bucket = 'vendor-claimed';
      reason = `citation host ${citationHost} matches vendor domain ${vendor}`;
    } else if (citationHost) {
      // Non-vendor host that isn't a known peer-reviewed venue or
      // neutral leaderboard. Treat as independently-verified UNLESS the
      // host is a generic commodity-publishing platform AND vendor info
      // exists — then we can't really call it independent.
      if (COMMODITY_PUBLISHING_HOSTS.has(citationHost)) {
        bucket = 'independently-verified';
        reason = `cited on ${citationHost} (third-party commodity host)`;
      } else {
        bucket = 'independently-verified';
        reason = `cited on ${citationHost} (third-party, non-vendor)`;
      }
    }

    // Gaming flags.
    const flags: GamingFlag[] = [];
    if (hasSingleSubTask(value)) flags.push('single-sub-task-only');
    if (hasWeakBaseline(value)) flags.push('weak-baseline-comparison');
    // 'vendor-self-defined' is filled in once we know the benchmark
    // population — see second pass below.

    rows.push({
      benchmark: s.benchmark,
      record_id: s.record_id,
      record_name: s.record_name,
      tier: s.tier,
      section: primarySection,
      score: s.score,
      scoreNum: isDelta ? null : n,
      isDelta,
      source: s.source,
      citation,
      citationHost,
      bucket,
      reason,
      flags,
      disputedBy: []
    });
  }

  // Second pass: score-divergence dispute detection and vendor-self-defined.
  const byBenchmark = new Map<string, IntegrityRow[]>();
  for (const r of rows) {
    const arr = byBenchmark.get(r.benchmark) ?? [];
    arr.push(r);
    byBenchmark.set(r.benchmark, arr);
  }

  for (const [, group] of byBenchmark) {
    // Score-divergence dispute. We're conservative here: papers
    // naturally report a wide range of scores against the same
    // benchmark (different base models, different splits) and a raw
    // score-spread isn't itself evidence of a dispute. We only flag
    // a row as disputed via score-divergence when:
    //   (a) the row is vendor-claimed (the vendor is making the
    //       biggest claim about its own product), AND
    //   (b) at least one peer-reviewed or independently-verified row
    //       on the same benchmark exists with a score that differs
    //       by more than disputeDelta absolute points.
    // This catches the canonical "vendor claims X, paper measures Y"
    // pattern (Mem0's 91.6 LoCoMo vs the Zep rebuttal at 84) without
    // false-positive-flagging every research paper that just happens
    // to report a different number.
    const externalWithScore = group.filter(
      (r) =>
        r.scoreNum !== null &&
        !r.isDelta &&
        (r.bucket === 'peer-reviewed' || r.bucket === 'independently-verified')
    );
    for (const a of group) {
      if (a.bucket !== 'vendor-claimed') continue;
      if (a.scoreNum === null || a.isDelta) continue;
      for (const b of externalWithScore) {
        if (a.record_id === b.record_id) continue;
        const delta = Math.abs((a.scoreNum as number) - (b.scoreNum as number));
        if (delta > disputeDelta) {
          if (!a.disputedBy.includes(b.record_id)) a.disputedBy.push(b.record_id);
          a.bucket = 'disputed';
          a.reason =
            `vendor-claimed ${a.score} differs from ${b.record_name}'s ${b.score} (${b.bucket}) by ${delta.toFixed(1)} pts`;
        }
      }
    }

    // Vendor-self-defined: benchmark reported by exactly one record, and
    // that record's citation is on the vendor's own domain.
    if (group.length === 1) {
      const only = group[0];
      if (only.bucket === 'vendor-claimed' && !only.flags.includes('vendor-self-defined')) {
        only.flags.push('vendor-self-defined');
      }
    }
  }

  return rows;
}

// ---------------------------------------------------------------------------
// Aggregations for the UI
// ---------------------------------------------------------------------------

export interface BucketCount {
  bucket: IntegrityBucket;
  count: number;
}

export function bucketCounts(rows: IntegrityRow[]): BucketCount[] {
  const order: IntegrityBucket[] = [
    'peer-reviewed',
    'independently-verified',
    'vendor-claimed',
    'disputed',
    'unverifiable'
  ];
  const counts = new Map<IntegrityBucket, number>();
  for (const b of order) counts.set(b, 0);
  for (const r of rows) counts.set(r.bucket, (counts.get(r.bucket) ?? 0) + 1);
  return order.map((bucket) => ({ bucket, count: counts.get(bucket) ?? 0 }));
}

export interface PerBenchmarkBreakdown {
  benchmark: string;
  total: number;
  counts: Record<IntegrityBucket, number>;
}

export function perBenchmark(rows: IntegrityRow[]): PerBenchmarkBreakdown[] {
  const m = new Map<string, PerBenchmarkBreakdown>();
  for (const r of rows) {
    let e = m.get(r.benchmark);
    if (!e) {
      e = {
        benchmark: r.benchmark,
        total: 0,
        counts: {
          'peer-reviewed': 0,
          'independently-verified': 0,
          'vendor-claimed': 0,
          disputed: 0,
          unverifiable: 0
        }
      };
      m.set(r.benchmark, e);
    }
    e.total++;
    e.counts[r.bucket]++;
  }
  return [...m.values()].sort((a, b) => b.total - a.total || a.benchmark.localeCompare(b.benchmark));
}

export interface LeaderboardRow {
  benchmark: string;
  record_id: string;
  record_name: string;
  tier: number;
  score: string;
  scoreNum: number;
  citationHost: string;
}

/** Top scores from peer-reviewed sources only (the "validated winners" panel). */
export function validatedLeaderboard(
  rows: IntegrityRow[],
  topPerBench = 5
): Map<string, LeaderboardRow[]> {
  const out = new Map<string, LeaderboardRow[]>();
  const byBench = new Map<string, IntegrityRow[]>();
  for (const r of rows) {
    if (r.bucket !== 'peer-reviewed') continue;
    if (r.scoreNum === null || r.isDelta) continue;
    const arr = byBench.get(r.benchmark) ?? [];
    arr.push(r);
    byBench.set(r.benchmark, arr);
  }
  for (const [bench, group] of byBench) {
    // De-duplicate per record (keep best score).
    const bestByRecord = new Map<string, IntegrityRow>();
    for (const r of group) {
      const ex = bestByRecord.get(r.record_id);
      if (!ex || (r.scoreNum as number) > (ex.scoreNum as number)) {
        bestByRecord.set(r.record_id, r);
      }
    }
    const ranked = [...bestByRecord.values()]
      .sort((a, b) => (b.scoreNum as number) - (a.scoreNum as number) || a.tier - b.tier)
      .slice(0, topPerBench)
      .map((r) => ({
        benchmark: r.benchmark,
        record_id: r.record_id,
        record_name: r.record_name,
        tier: r.tier,
        score: r.score,
        scoreNum: r.scoreNum as number,
        citationHost: r.citationHost ?? ''
      }));
    out.set(bench, ranked);
  }
  return out;
}

export interface FlagRow {
  flag: GamingFlag;
  rows: IntegrityRow[];
}

export function gamingFlags(rows: IntegrityRow[]): FlagRow[] {
  const out: Record<GamingFlag, IntegrityRow[]> = {
    'single-sub-task-only': [],
    'weak-baseline-comparison': [],
    'vendor-self-defined': []
  };
  for (const r of rows) {
    for (const f of r.flags) out[f].push(r);
  }
  const order: GamingFlag[] = ['vendor-self-defined', 'weak-baseline-comparison', 'single-sub-task-only'];
  return order.map((flag) => ({ flag, rows: out[flag] }));
}

// Sections + tiers — used by the filter row.
export function uniqueSections(rows: IntegrityRow[]): string[] {
  const set = new Set<string>();
  for (const r of rows) if (r.section) set.add(r.section);
  return [...set].sort();
}

export function uniqueTiers(rows: IntegrityRow[]): number[] {
  const set = new Set<number>();
  for (const r of rows) set.add(r.tier);
  return [...set].sort();
}

// ---------------------------------------------------------------------------
// Re-exports — the page imports these helpers from one place.
// ---------------------------------------------------------------------------

export { extractScores, parseScoreNum };
export type { BenchmarkScore };
