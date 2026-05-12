// Pure helpers for the benchmark coverage matrix (issue #24).
//
// We scan `cells.perf.value` (primary source) and `cells.claims.value`
// (secondary source) for occurrences of well-known memory and agent
// benchmark names, attaching the nearest numeric score we can find for
// each mention. The corpus is human-authored short-form text — there's
// no structured score field — so the extractor is deliberately tolerant.
//
// Canonicalisation rules (see docs/DECISIONS.md 2026-05-07 entry):
//   - "LongMemEval" / "LMES" / "LME" / "LongMem-Eval"  → LongMemEval
//   - "LoCoMo" / "Loco-Mo"                              → LoCoMo
//   - "BABILong" / "BABI-Long"                          → BABILong
//   - "ConvoMem"                                        → ConvoMem
//   - "RULER"                                           → RULER
//   - "MemoryBench" / "MemoryAgentBench"                → MemoryAgentBench
//   - plus agent benchmarks: GAIA, ALFWorld/AlfWorld, SWE-bench, OSWorld,
//     WebArena, AppWorld, HotpotQA, MMLU, BrowseComp, ScienceWorld,
//     Mind2Web, AIME, MT-Bench-101, NIAH, TriviaQA, NaturalQuestions,
//     LongBench, PersonaBench, ImplicitMemBench
//
// Priority. We prefer scores from `perf` over scores from `claims`. If
// both mention the same benchmark for the same system, the perf score
// wins (perf is the curated headline; claims is the marketing prose).
//
// Round 8 (#24 upgrade) parser improvements:
//   1. HTML-aware fallback: strips <span class="signal-num">…</span>,
//      <br>, and similar wrappers before scoring. (Current corpus is
//      already plain-text, but the parser is forward-compatible with
//      iter-level cells that still contain markup.)
//   2. Tiered score preference:
//      a. score with unit suffix (e.g. "92.2%", "+18.7pp", "84.2 F1") —
//         highest signal, used in both perf and claims modes.
//      b. bare decimal (e.g. "0.700 LoCoMo") — perf-mode only.
//      c. bare integer (e.g. "30 ConvoMem") — perf-mode only, ≤6 chars.
//   3. Benchmark-boundary clipping: in "30 ConvoMem 91.6 LoCoMo", the
//      ConvoMem search clips the right window past the next benchmark
//      mention AND drops the trailing score (which belongs to LoCoMo).
//   4. Year rejection (4-digit 19xx/20xx tokens).

import type { LandscapeRecord } from '../types';

export interface BenchmarkScore {
  /** Canonical benchmark name. */
  benchmark: string;
  /** Free-text score / delta as found near the mention. May be ''. */
  score: string;
  /** record id this score belongs to. */
  record_id: string;
  /** record name (denormalised for matrix display). */
  record_name: string;
  /** tier of the source record (1 = battle-tested, 5 = informal). */
  tier: number;
  /** 'perf' or 'claims' — perf wins on conflict. */
  source: 'perf' | 'claims';
}

const BENCHMARKS: { canonical: string; pattern: RegExp }[] = [
  { canonical: 'LongMemEval', pattern: /\b(?:LongMemEval(?:-[SML])?|LMES|LME(?![A-Za-z])|LongMem-Eval)\b/gi },
  { canonical: 'LoCoMo', pattern: /\bLo[-]?Co[-]?Mo\b/gi },
  { canonical: 'BABILong', pattern: /\bBABI[-]?Long\b/gi },
  { canonical: 'ConvoMem', pattern: /\bConvoMem\b/gi },
  { canonical: 'RULER', pattern: /\bRULER\b/g },
  { canonical: 'MemoryAgentBench', pattern: /\bMemoryAgentBench\b/gi },
  { canonical: 'ImplicitMemBench', pattern: /\bImplicitMemBench\b/gi },
  { canonical: 'PersonaBench', pattern: /\bPersonaBench\b/gi },
  { canonical: 'NIAH', pattern: /\bNIAH\b|Needle[-\s]?in[-\s]?a[-\s]?Haystack/gi },
  { canonical: 'LongBench', pattern: /\bLongBench\b/gi },
  { canonical: 'HotpotQA', pattern: /\bHotpotQA\b/gi },
  { canonical: 'TriviaQA', pattern: /\bTriviaQA\b/gi },
  { canonical: 'NaturalQuestions', pattern: /\bNatural[-\s]?Questions\b/gi },
  { canonical: 'GAIA', pattern: /\bGAIA\b/g },
  { canonical: 'ALFWorld', pattern: /\b(?:ALFWorld|AlfWorld)\b/gi },
  { canonical: 'SWE-bench', pattern: /SWE[-\s]?[Bb]ench(?:[-\s]?Verified)?/g },
  { canonical: 'OSWorld', pattern: /\bOSWorld\b/gi },
  { canonical: 'WebArena', pattern: /\bWebArena\b/gi },
  { canonical: 'AppWorld', pattern: /\bAppWorld\b/gi },
  { canonical: 'ScienceWorld', pattern: /\b(?:ScienceWorld|SciWorld)\b/gi },
  { canonical: 'Mind2Web', pattern: /\bMind2Web\b/gi },
  { canonical: 'BrowseComp', pattern: /\bBrowseComp(?:-ZH)?\b/gi },
  { canonical: 'AIME', pattern: /\bAIME(?:[-\s]?20\d\d)?\b/g },
  { canonical: 'MT-Bench', pattern: /MT[-\s]?Bench(?:-101)?/g },
  { canonical: 'MMLU', pattern: /\bMMLU\b|\bCMMLU\b/g }
];

const SCORE_WITH_UNIT_RE = /[+\-~]?\d[\d.,]*\s*(?:%|pp|F1|EM|bpc|ppl|poi)/g;
const SCORE_DECIMAL_RE = /[+\-~]?\d+\.\d+/g;
const SCORE_INT_RE = /[+\-~]?\d{1,3}\b/g;
const YEAR_RE = /^(?:19|20)\d{2}$/;

function stripHtml(s: string): string {
  if (!s || s.indexOf('<') === -1) return s;
  return s
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<\/?(?:span|em|strong|b|i|u|code|sup|sub)(?:\s[^>]*)?>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function isNoiseToken(token: string): boolean {
  return YEAR_RE.test(token.trim());
}

function nearestBenchmarkBoundary(s: string, fromRight: boolean): number {
  let best = fromRight ? s.length : 0;
  let found = false;
  for (const { pattern } of BENCHMARKS) {
    pattern.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = pattern.exec(s)) !== null) {
      if (fromRight) {
        if (!found || m.index < best) {
          best = m.index;
          found = true;
        }
      } else {
        const end = m.index + m[0].length;
        if (end > best) best = end;
      }
    }
  }
  return best;
}

function scoreNearMatch(
  value: string,
  matchStart: number,
  matchEnd: number,
  claimsMode: boolean
): string {
  const leftStart = Math.max(0, matchStart - 40);
  const leftRaw = value.slice(leftStart, matchStart);
  const rightEnd = Math.min(value.length, matchEnd + 40);
  const rightRaw = value.slice(matchEnd, rightEnd);

  const leftClipFrom = nearestBenchmarkBoundary(leftRaw, false);
  const rightClipTo = nearestBenchmarkBoundary(rightRaw, true);
  const left = leftRaw.slice(leftClipFrom);
  let right = rightRaw.slice(0, rightClipTo);

  // Drop trailing score in clipped right window — belongs to next benchmark.
  if (rightClipTo < rightRaw.length) {
    const lastScore = [...right.matchAll(/[+\-~]?\d[\d.,]*\s*(?:%|pp|F1|EM|bpc|ppl|poi)?/g)].pop();
    if (lastScore && lastScore.index !== undefined) {
      right = right.slice(0, lastScore.index);
    }
  }

  const leftUnit = [...left.matchAll(SCORE_WITH_UNIT_RE)];
  if (leftUnit.length > 0) {
    const cand = leftUnit[leftUnit.length - 1][0].trim();
    if (!isNoiseToken(cand)) return cand;
  }
  const rightUnit = [...right.matchAll(SCORE_WITH_UNIT_RE)];
  if (rightUnit.length > 0) {
    const cand = rightUnit[0][0].trim();
    if (!isNoiseToken(cand)) return cand;
  }

  if (claimsMode) return '';

  const leftDec = [...left.matchAll(SCORE_DECIMAL_RE)];
  if (leftDec.length > 0) {
    const cand = leftDec[leftDec.length - 1][0].trim();
    if (!isNoiseToken(cand)) return cand;
  }
  const rightDec = [...right.matchAll(SCORE_DECIMAL_RE)];
  if (rightDec.length > 0) {
    const cand = rightDec[0][0].trim();
    if (!isNoiseToken(cand)) return cand;
  }

  const tightLeft = value.slice(Math.max(0, matchStart - 6), matchStart);
  const tightRight = value.slice(matchEnd, Math.min(value.length, matchEnd + 6));
  const tightLeftInt = [...tightLeft.matchAll(SCORE_INT_RE)];
  if (tightLeftInt.length > 0) {
    const cand = tightLeftInt[tightLeftInt.length - 1][0].trim();
    if (!isNoiseToken(cand)) return cand;
  }
  const tightRightInt = [...tightRight.matchAll(SCORE_INT_RE)];
  if (tightRightInt.length > 0) {
    const cand = tightRightInt[0][0].trim();
    if (!isNoiseToken(cand)) return cand;
  }
  return '';
}

function scanText(
  text: string,
  recordId: string,
  recordName: string,
  tier: number,
  source: 'perf' | 'claims'
): BenchmarkScore[] {
  if (!text) return [];
  const cleaned = stripHtml(text);
  const out: BenchmarkScore[] = [];
  const seenForRecord = new Set<string>();
  for (const { canonical, pattern } of BENCHMARKS) {
    pattern.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = pattern.exec(cleaned)) !== null) {
      if (seenForRecord.has(canonical)) break;
      const score = scoreNearMatch(cleaned, m.index, m.index + m[0].length, source === 'claims');
      out.push({
        benchmark: canonical,
        score,
        record_id: recordId,
        record_name: recordName,
        tier,
        source
      });
      seenForRecord.add(canonical);
    }
  }
  return out;
}

export function extractScores(records: LandscapeRecord[]): BenchmarkScore[] {
  const out: BenchmarkScore[] = [];
  for (const r of records) {
    const perfCell = r.cells.perf;
    const claimsCell = r.cells.claims;

    const perfText =
      perfCell?.status === 'real-data' &&
      perfCell.value &&
      !/^no public benchmark scores found/i.test(perfCell.value)
        ? perfCell.value
        : '';

    const perfScores = scanText(perfText, r.id, r.name, r.tier, 'perf');
    out.push(...perfScores);

    const claimedBenchmarks = new Set(perfScores.map((s) => s.benchmark));
    const claimsText =
      claimsCell?.value && claimsCell.status === 'real-data' ? claimsCell.value : '';
    const claimsScores = scanText(claimsText, r.id, r.name, r.tier, 'claims').filter(
      (s) => !claimedBenchmarks.has(s.benchmark)
    );
    out.push(...claimsScores);
  }
  return out;
}

export interface CoverageMatrix {
  systems: { id: string; name: string; tier: number; count: number }[];
  benchmarks: { name: string; count: number }[];
  cells: Map<string, { score: string; source: 'perf' | 'claims' }>;
}

export function buildMatrix(scores: BenchmarkScore[], topN = 14): CoverageMatrix {
  const benchmarkCounts = new Map<string, number>();
  const systemCounts = new Map<string, number>();
  const systemNames = new Map<string, string>();
  const systemTiers = new Map<string, number>();
  const cells = new Map<string, { score: string; source: 'perf' | 'claims' }>();

  for (const s of scores) {
    benchmarkCounts.set(s.benchmark, (benchmarkCounts.get(s.benchmark) ?? 0) + 1);
    const key = `${s.record_id}::${s.benchmark}`;
    if (!cells.has(key)) {
      cells.set(key, { score: s.score, source: s.source });
      systemCounts.set(s.record_id, (systemCounts.get(s.record_id) ?? 0) + 1);
      systemNames.set(s.record_id, s.record_name);
      systemTiers.set(s.record_id, s.tier);
    }
  }

  const benchmarks = [...benchmarkCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([name, count]) => ({ name, count }));

  const benchmarkSet = new Set(benchmarks.map((b) => b.name));
  const visibleSystemCounts = new Map<string, number>();
  for (const [key] of cells) {
    const [id, bench] = key.split('::');
    if (!benchmarkSet.has(bench)) continue;
    visibleSystemCounts.set(id, (visibleSystemCounts.get(id) ?? 0) + 1);
  }

  const systems = [...visibleSystemCounts.entries()]
    .sort((a, b) => b[1] - a[1] || systemNames.get(a[0])!.localeCompare(systemNames.get(b[0])!))
    .map(([id, count]) => ({
      id,
      name: systemNames.get(id) ?? id,
      tier: systemTiers.get(id) ?? 4,
      count
    }));

  return { systems, benchmarks, cells };
}

export interface BenchmarkCount {
  benchmark: string;
  count: number;
}

export function benchmarkCoverage(scores: BenchmarkScore[]): BenchmarkCount[] {
  const counts = new Map<string, number>();
  const seen = new Set<string>();
  for (const s of scores) {
    const key = `${s.record_id}::${s.benchmark}`;
    if (seen.has(key)) continue;
    seen.add(key);
    counts.set(s.benchmark, (counts.get(s.benchmark) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([benchmark, count]) => ({ benchmark, count }))
    .sort((a, b) => b.count - a.count);
}

export interface SystemCount {
  record_id: string;
  record_name: string;
  count: number;
  benchmarks: string[];
}

export function systemCoverage(scores: BenchmarkScore[]): SystemCount[] {
  const m = new Map<string, { name: string; benchmarks: Set<string> }>();
  for (const s of scores) {
    const e = m.get(s.record_id) ?? { name: s.record_name, benchmarks: new Set<string>() };
    e.benchmarks.add(s.benchmark);
    m.set(s.record_id, e);
  }
  return [...m.entries()]
    .map(([record_id, { name, benchmarks }]) => ({
      record_id,
      record_name: name,
      count: benchmarks.size,
      benchmarks: [...benchmarks].sort()
    }))
    .sort((a, b) => b.count - a.count || a.record_name.localeCompare(b.record_name));
}

const MEMORY_BENCHMARKS = new Set([
  'LongMemEval',
  'LoCoMo',
  'BABILong',
  'ConvoMem',
  'RULER',
  'MemoryAgentBench',
  'ImplicitMemBench',
  'PersonaBench',
  'NIAH'
]);

export interface AdoptionSplit {
  memorySpecificSystems: number;
  domainSpecificSystems: number;
  bothSystems: number;
  memoryOnlySystems: number;
  domainOnlySystems: number;
}

export function adoptionSplit(scores: BenchmarkScore[]): AdoptionSplit {
  const perSystem = new Map<string, { memory: boolean; domain: boolean }>();
  for (const s of scores) {
    const e = perSystem.get(s.record_id) ?? { memory: false, domain: false };
    if (MEMORY_BENCHMARKS.has(s.benchmark)) e.memory = true;
    else e.domain = true;
    perSystem.set(s.record_id, e);
  }
  let mem = 0;
  let dom = 0;
  let both = 0;
  let memOnly = 0;
  let domOnly = 0;
  for (const v of perSystem.values()) {
    if (v.memory) mem++;
    if (v.domain) dom++;
    if (v.memory && v.domain) both++;
    else if (v.memory) memOnly++;
    else if (v.domain) domOnly++;
  }
  return {
    memorySpecificSystems: mem,
    domainSpecificSystems: dom,
    bothSystems: both,
    memoryOnlySystems: memOnly,
    domainOnlySystems: domOnly
  };
}

export function isMemoryBenchmark(name: string): boolean {
  return MEMORY_BENCHMARKS.has(name);
}

// --- Leaderboards, coverage tiers, parser-quality, mem/dom buckets ----------

export function parseScoreNum(s: string): { n: number | null; isDelta: boolean } {
  if (!s) return { n: null, isDelta: false };
  const m = s.match(/^([+\-~])?(\d[\d.,]*)/);
  if (!m) return { n: null, isDelta: false };
  const n = parseFloat(m[2].replace(/,/g, ''));
  if (Number.isNaN(n)) return { n: null, isDelta: false };
  const isDelta = m[1] === '+' || m[1] === '-';
  return { n, isDelta };
}

export interface LeaderRow {
  record_id: string;
  record_name: string;
  tier: number;
  score: string;
  scoreNum: number;
  source: 'perf' | 'claims';
}

export function leaderboard(
  scores: BenchmarkScore[],
  benchmark: string,
  topN = 10
): LeaderRow[] {
  const byRecord = new Map<string, BenchmarkScore>();
  for (const s of scores) {
    if (s.benchmark !== benchmark) continue;
    const existing = byRecord.get(s.record_id);
    if (!existing || (existing.source === 'claims' && s.source === 'perf')) {
      byRecord.set(s.record_id, s);
    }
  }
  const rows: LeaderRow[] = [];
  for (const s of byRecord.values()) {
    const { n, isDelta } = parseScoreNum(s.score);
    if (n === null || isDelta) continue;
    rows.push({
      record_id: s.record_id,
      record_name: s.record_name,
      tier: s.tier,
      score: s.score,
      scoreNum: n,
      source: s.source
    });
  }
  rows.sort((a, b) => b.scoreNum - a.scoreNum || a.tier - b.tier || a.record_name.localeCompare(b.record_name));
  return rows.slice(0, topN);
}

export interface CoverageTier {
  tier: 'well-covered' | 'emerging' | 'too-narrow';
  benchmarks: BenchmarkCount[];
}

export function coverageTiers(scores: BenchmarkScore[]): CoverageTier[] {
  const cov = benchmarkCoverage(scores);
  const wellCovered: BenchmarkCount[] = [];
  const emerging: BenchmarkCount[] = [];
  const tooNarrow: BenchmarkCount[] = [];
  for (const row of cov) {
    if (row.count >= 10) wellCovered.push(row);
    else if (row.count >= 5) emerging.push(row);
    else tooNarrow.push(row);
  }
  return [
    { tier: 'well-covered', benchmarks: wellCovered },
    { tier: 'emerging', benchmarks: emerging },
    { tier: 'too-narrow', benchmarks: tooNarrow }
  ];
}

export interface ParserStats {
  perfMentions: number;
  perfWithScore: number;
  claimsMentions: number;
  claimsWithScore: number;
  totalMentions: number;
  totalWithScore: number;
  perfCoverage: number;
  claimsCoverage: number;
  totalCoverage: number;
}

export function parserStats(scores: BenchmarkScore[]): ParserStats {
  let perfMentions = 0;
  let perfWithScore = 0;
  let claimsMentions = 0;
  let claimsWithScore = 0;
  for (const s of scores) {
    if (s.source === 'perf') {
      perfMentions++;
      if (s.score) perfWithScore++;
    } else {
      claimsMentions++;
      if (s.score) claimsWithScore++;
    }
  }
  const totalMentions = perfMentions + claimsMentions;
  const totalWithScore = perfWithScore + claimsWithScore;
  return {
    perfMentions,
    perfWithScore,
    claimsMentions,
    claimsWithScore,
    totalMentions,
    totalWithScore,
    perfCoverage: perfMentions === 0 ? 0 : perfWithScore / perfMentions,
    claimsCoverage: claimsMentions === 0 ? 0 : claimsWithScore / claimsMentions,
    totalCoverage: totalMentions === 0 ? 0 : totalWithScore / totalMentions
  };
}

export type MemDomainCategory = 'memory-only' | 'domain-only' | 'both';

export interface MemDomainBucket {
  category: MemDomainCategory;
  systems: { record_id: string; record_name: string; tier: number }[];
}

export function memDomainBuckets(scores: BenchmarkScore[]): MemDomainBucket[] {
  const perSystem = new Map<
    string,
    { name: string; tier: number; memory: boolean; domain: boolean }
  >();
  for (const s of scores) {
    const e =
      perSystem.get(s.record_id) ??
      { name: s.record_name, tier: s.tier, memory: false, domain: false };
    if (MEMORY_BENCHMARKS.has(s.benchmark)) e.memory = true;
    else e.domain = true;
    perSystem.set(s.record_id, e);
  }
  const memOnly: { record_id: string; record_name: string; tier: number }[] = [];
  const domOnly: { record_id: string; record_name: string; tier: number }[] = [];
  const both: { record_id: string; record_name: string; tier: number }[] = [];
  for (const [id, v] of perSystem) {
    const item = { record_id: id, record_name: v.name, tier: v.tier };
    if (v.memory && v.domain) both.push(item);
    else if (v.memory) memOnly.push(item);
    else if (v.domain) domOnly.push(item);
  }
  const sortFn = (a: { record_name: string; tier: number }, b: { record_name: string; tier: number }) =>
    a.tier - b.tier || a.record_name.localeCompare(b.record_name);
  memOnly.sort(sortFn);
  domOnly.sort(sortFn);
  both.sort(sortFn);
  return [
    { category: 'memory-only', systems: memOnly },
    { category: 'both', systems: both },
    { category: 'domain-only', systems: domOnly }
  ];
}
