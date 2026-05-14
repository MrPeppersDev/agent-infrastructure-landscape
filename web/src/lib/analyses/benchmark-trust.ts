// Pure helpers for the benchmark-trust leaderboard (issue #42).
//
// Companion to /analyses/benchmark-integrity. That view *classifies*
// every benchmark mention; this view *ranks* the benchmarks themselves
// by a single composite trust score so a reader can scan the leaderboard
// and immediately see "LoCoMo has 30% vendor-claimed mentions, treat the
// number with caution" without staring at five-column counts.
//
// This is a pure pivot of existing integrity classifications — no new
// data ingestion, no new columns, just an aggregation on top of
// classifyIntegrity().
//
// ---------------------------------------------------------------------------
// Composite trust score formula
// ---------------------------------------------------------------------------
//
// Let
//   pr  = peer-reviewed mentions of this benchmark
//   iv  = independently-verified mentions
//   vc  = vendor-claimed mentions
//   dp  = disputed mentions
//   tot = pr + iv + vc + dp   (sum of *evaluable* mentions; we exclude the
//                              "unverifiable" bucket from the denominator —
//                              missing-citation cells shouldn't punish a
//                              benchmark or rescue it).
//
// Percentages:
//   pr_pct = 100 * pr / tot      (0–100)
//   iv_pct = 100 * iv / tot
//   vc_pct = 100 * vc / tot
//   dp_pct = 100 * dp / tot
//
// Score:
//   score = pr_pct * 1.0
//         + iv_pct * 1.2      (modest bonus — independent verification is
//                              the gold-standard outside academia; we want
//                              "neutral leaderboard recorded the number"
//                              to count for *more* than the same number on
//                              a vendor's blog)
//         - dp_pct * 1.5      (penalty — a disputed mention is direct
//                              evidence the benchmark is contested. 1.5x
//                              not 1.0x because a *single* disputed row
//                              outweighs a vendor-claimed row in the
//                              reader's mind, and the score should match
//                              that intuition)
//         - vendor_only_orphan_penalty
//
//   vendor_only_orphan_penalty:
//     fires when (a) 100% of mentions are vendor-claimed AND
//                (b) total mentions ≥ 5
//     value: 0.3 * vc_pct  (i.e. 30 points off when vc_pct = 100)
//     rationale: a benchmark with no peer-reviewed or independent presence
//     and ≥5 vendor citations is almost certainly a vendor-driven
//     leaderboard. Single-vendor benchmarks under that threshold may just
//     be niche or new — we don't punish them.
//
//   final = clamp(score, 0, 100)
//
// ---------------------------------------------------------------------------
// Tier thresholds
// ---------------------------------------------------------------------------
//
//   high        score ≥ 70   — predominantly peer-reviewed or independent,
//                              few disputes. Safe to cite without caveat.
//   medium      40 ≤ s < 70  — mixed evidence base. Cite with the
//                              integrity-bucket breakdown alongside.
//   low         20 ≤ s < 40  — vendor-heavy or contested. Treat any
//                              headline number with skepticism.
//   compromised s < 20       — dominantly vendor-claimed AND/OR has
//                              disputes. Reader should not cite a
//                              headline score from this benchmark without
//                              independent corroboration.

import type { LandscapeRecord } from '../types';
import { classifyIntegrity, type IntegrityBucket, type IntegrityRow } from './benchmark-integrity';

export type TrustTier = 'high' | 'medium' | 'low' | 'compromised';

export type CitingIntegrity =
  | 'peer-reviewed'
  | 'independently-verified'
  | 'vendor-claimed'
  | 'disputed';

export interface CitingSystem {
  id: string;
  name: string;
  integrity: CitingIntegrity;
}

export interface BenchmarkTrust {
  benchmarkName: string;
  /** null when the benchmark is mentioned in cells but is not itself a catalog record. */
  benchmarkId: string | null;
  peerReviewedCount: number;
  independentlyVerifiedCount: number;
  vendorClaimedCount: number;
  disputedCount: number;
  /** Total of the four "evaluable" buckets above. Excludes unverifiable. */
  totalMentions: number;
  /** 0–100, computed by the formula at top of this file. */
  trustScore: number;
  trustTier: TrustTier;
  /** Months since this benchmark was first published. null when not dateable. */
  ageMonths: number | null;
  /** Per-record list — one entry per citing system. */
  citingSystems: CitingSystem[];
}

// ---------------------------------------------------------------------------
// Benchmark-name → catalog record id resolution
// ---------------------------------------------------------------------------
//
// Not every benchmark we track has its own record in the catalog (e.g.
// "AIME", "MMLU" are well-known but no row catalogues them as primary
// objects). For those, benchmarkId is null and ageMonths is null.

/**
 * Map a canonical benchmark name to its catalog record (if present). We
 * match on `record.name` rather than slug because the canonical names
 * are what's in the citations. Returns the *first* exact-or-prefix
 * match; the prefix branch lets "NIAH" pick up "NIAH (Needle in a
 * Haystack)".
 */
function resolveBenchmarkRecord(
  benchmarkName: string,
  records: LandscapeRecord[]
): LandscapeRecord | null {
  const target = benchmarkName.toLowerCase();
  for (const r of records) {
    if (r.name.toLowerCase() === target) return r;
  }
  for (const r of records) {
    const n = r.name.toLowerCase();
    if (
      n.startsWith(target + ' ') ||
      n.startsWith(target + '-') ||
      n.startsWith(target + '(') ||
      n.startsWith(target + ' (')
    ) {
      return r;
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Date parsing for ageMonths
// ---------------------------------------------------------------------------

/**
 * Extract the earliest YYYY-MM (or YYYY) anchor from a `created` cell
 * value. Cells often contain free-form prose like "2024-02 (BABILong;
 * Kuratov et al. arXiv 2406.10149)" — we want the structured prefix.
 * Returns months since epoch (a single integer we can subtract).
 */
function parseCreatedMonths(value: string | undefined | null): number | null {
  if (!value) return null;
  // YYYY-MM
  const ym = value.match(/\b(20\d\d|19\d\d)-(0[1-9]|1[0-2])\b/);
  if (ym) {
    const y = parseInt(ym[1], 10);
    const m = parseInt(ym[2], 10);
    return y * 12 + (m - 1);
  }
  // Just YYYY — pin to mid-year (June).
  const y = value.match(/\b(20\d\d|19\d\d)\b/);
  if (y) {
    return parseInt(y[1], 10) * 12 + 5;
  }
  return null;
}

function monthsToToday(months: number): number {
  const now = new Date();
  const todayMonths = now.getFullYear() * 12 + now.getMonth();
  return Math.max(0, todayMonths - months);
}

// ---------------------------------------------------------------------------
// Score computation
// ---------------------------------------------------------------------------

const ORPHAN_THRESHOLD = 5;
const ORPHAN_PENALTY_WEIGHT = 0.3;

function computeScore(
  pr: number,
  iv: number,
  vc: number,
  dp: number
): number {
  const total = pr + iv + vc + dp;
  if (total === 0) return 0;
  const prPct = (pr / total) * 100;
  const ivPct = (iv / total) * 100;
  const vcPct = (vc / total) * 100;
  const dpPct = (dp / total) * 100;

  let score = prPct * 1.0 + ivPct * 1.2 - dpPct * 1.5;

  // Vendor-only orphan penalty.
  if (total >= ORPHAN_THRESHOLD && vc === total) {
    score -= vcPct * ORPHAN_PENALTY_WEIGHT;
  }

  if (score < 0) return 0;
  if (score > 100) return 100;
  return score;
}

function tierFor(score: number): TrustTier {
  if (score >= 70) return 'high';
  if (score >= 40) return 'medium';
  if (score >= 20) return 'low';
  return 'compromised';
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Build the per-benchmark trust leaderboard from the landscape records.
 * Sorted by trustScore descending, then by name ascending for stability.
 */
export function buildBenchmarkTrust(records: LandscapeRecord[]): BenchmarkTrust[] {
  const rows = classifyIntegrity(records);

  // Bucket rows by benchmark name.
  const byBench = new Map<string, IntegrityRow[]>();
  for (const r of rows) {
    const arr = byBench.get(r.benchmark) ?? [];
    arr.push(r);
    byBench.set(r.benchmark, arr);
  }

  const result: BenchmarkTrust[] = [];

  for (const [benchmark, group] of byBench) {
    // Count the four evaluable buckets. We deliberately drop
    // unverifiable rows from the denominator — they're noise, not
    // signal.
    let pr = 0;
    let iv = 0;
    let vc = 0;
    let dp = 0;
    const citing: CitingSystem[] = [];

    for (const row of group) {
      let integrity: CitingIntegrity | null = null;
      const bucket: IntegrityBucket = row.bucket;
      if (bucket === 'peer-reviewed') {
        pr++;
        integrity = 'peer-reviewed';
      } else if (bucket === 'independently-verified') {
        iv++;
        integrity = 'independently-verified';
      } else if (bucket === 'vendor-claimed') {
        vc++;
        integrity = 'vendor-claimed';
      } else if (bucket === 'disputed') {
        dp++;
        integrity = 'disputed';
      }
      if (integrity) {
        citing.push({
          id: row.record_id,
          name: row.record_name,
          integrity
        });
      }
    }

    const total = pr + iv + vc + dp;
    if (total === 0) continue; // benchmark with no evaluable mentions — skip

    const score = computeScore(pr, iv, vc, dp);
    const tier = tierFor(score);

    const rec = resolveBenchmarkRecord(benchmark, records);
    let ageMonths: number | null = null;
    if (rec) {
      const created = rec.cells.created;
      if (created && created.status === 'real-data') {
        const m = parseCreatedMonths(created.value);
        if (m !== null) ageMonths = monthsToToday(m);
      }
    }

    // De-duplicate citingSystems by record id (keep the worst-case
    // integrity if a record has both a vendor-claim row and a peer-
    // reviewed row — the "worst" assignment tells the reader the
    // record is implicated as a vendor-claimer; the peer-reviewed
    // mention will surface in the breakdown). We rank
    // disputed > vendor-claimed > vendor-claimed shadow > peer-reviewed
    // worst-first so the per-record badge says "this record's worst
    // claim on this benchmark was X".
    const integrityRank: Record<CitingIntegrity, number> = {
      disputed: 0,
      'vendor-claimed': 1,
      'independently-verified': 2,
      'peer-reviewed': 3
    };
    const dedup = new Map<string, CitingSystem>();
    for (const c of citing) {
      const ex = dedup.get(c.id);
      if (!ex || integrityRank[c.integrity] < integrityRank[ex.integrity]) {
        dedup.set(c.id, c);
      }
    }
    const dedupedCiting = [...dedup.values()].sort(
      (a, b) =>
        integrityRank[a.integrity] - integrityRank[b.integrity] ||
        a.name.localeCompare(b.name)
    );

    result.push({
      benchmarkName: benchmark,
      benchmarkId: rec ? rec.id : null,
      peerReviewedCount: pr,
      independentlyVerifiedCount: iv,
      vendorClaimedCount: vc,
      disputedCount: dp,
      totalMentions: total,
      trustScore: score,
      trustTier: tier,
      ageMonths,
      citingSystems: dedupedCiting
    });
  }

  // Sort by score desc, then name asc for stability.
  result.sort(
    (a, b) =>
      b.trustScore - a.trustScore || a.benchmarkName.localeCompare(b.benchmarkName)
  );
  return result;
}

/** Convenience: top-N most-trusted benchmarks. */
export function mostTrusted(rows: BenchmarkTrust[], n = 5): BenchmarkTrust[] {
  return rows.slice(0, n);
}

/**
 * Convenience: bottom-N most-gamed benchmarks. Only includes benchmarks
 * with ≥5 vendor-claimed mentions — one-off vendor mentions of a niche
 * benchmark aren't "gaming", they're just data scarcity, and we don't
 * want to mislead the reader by ranking them.
 */
export function mostGamed(rows: BenchmarkTrust[], n = 5): BenchmarkTrust[] {
  const qualifying = rows
    .filter((r) => r.vendorClaimedCount >= 5)
    .slice() // copy before sort
    .sort(
      (a, b) =>
        a.trustScore - b.trustScore || a.benchmarkName.localeCompare(b.benchmarkName)
    );
  return qualifying.slice(0, n);
}

// Re-export for direct test access.
export { computeScore, tierFor };
