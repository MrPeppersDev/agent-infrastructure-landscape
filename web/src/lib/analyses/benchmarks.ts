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
  /** 'perf' or 'claims' — perf wins on conflict. */
  source: 'perf' | 'claims';
}

/**
 * Each entry is [canonical name, regex matching every alias].
 *
 * Order matters: the longer / more specific aliases come first so e.g.
 * "MemoryAgentBench" is matched before a hypothetical bare "MemoryBench"
 * substring, and "LongMemEval-S" before "LongMemEval".
 *
 * `\b` is used wherever the alias is purely alphabetic; benchmark names
 * with hyphens (SWE-bench, Mind2Web) need a manual boundary.
 */
const BENCHMARKS: { canonical: string; pattern: RegExp }[] = [
  // Memory-specific benchmarks (the headline targets of this analysis).
  { canonical: 'LongMemEval', pattern: /\b(?:LongMemEval(?:-[SML])?|LMES|LME(?![A-Za-z])|LongMem-Eval)\b/gi },
  { canonical: 'LoCoMo', pattern: /\bLo[-]?Co[-]?Mo\b/gi },
  { canonical: 'BABILong', pattern: /\bBABI[-]?Long\b/gi },
  { canonical: 'ConvoMem', pattern: /\bConvoMem\b/gi },
  { canonical: 'RULER', pattern: /\bRULER\b/g },
  { canonical: 'MemoryAgentBench', pattern: /\bMemoryAgentBench\b/gi },
  { canonical: 'ImplicitMemBench', pattern: /\bImplicitMemBench\b/gi },
  { canonical: 'PersonaBench', pattern: /\bPersonaBench\b/gi },
  { canonical: 'NIAH', pattern: /\bNIAH\b|Needle[-\s]?in[-\s]?a[-\s]?Haystack/gi },
  // Long-context / retrieval benchmarks that get cited alongside memory work.
  { canonical: 'LongBench', pattern: /\bLongBench\b/gi },
  { canonical: 'HotpotQA', pattern: /\bHotpotQA\b/gi },
  { canonical: 'TriviaQA', pattern: /\bTriviaQA\b/gi },
  { canonical: 'NaturalQuestions', pattern: /\bNatural[-\s]?Questions\b/gi },
  // Agent / coding / web benchmarks.
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

/**
 * Try to extract the score that's nearest a benchmark mention in `value`.
 *
 * Heuristic: look in a window of ±60 chars around the match for the
 * first token that looks like a score (number with %, x, pp, F1, or
 * standalone decimal). Returns '' if nothing fits — we still record the
 * mention but display it as a presence-only checkmark in the matrix.
 *
 * The corpus convention is "{score} {benchmark}" or "{benchmark} {score}",
 * with the score usually on the immediate left and the benchmark name
 * right after. We scan left first (window of 30) then right (window of 30).
 */
function scoreNearMatch(value: string, matchStart: number, matchEnd: number): string {
  const leftStart = Math.max(0, matchStart - 30);
  const left = value.slice(leftStart, matchStart);
  const rightEnd = Math.min(value.length, matchEnd + 30);
  const right = value.slice(matchEnd, rightEnd);

  // Number-with-suffix patterns we recognise as a score.
  const scoreRe = /[+\-~]?\d[\d.,]*\s*(?:%|pp|x|×|F1|EM|bpc|ppl|poi)?/g;

  // Prefer the rightmost score in the left window (closest to the
  // benchmark name).
  const lefts = [...left.matchAll(scoreRe)];
  if (lefts.length > 0) {
    const last = lefts[lefts.length - 1][0].trim();
    // Reject single tokens that are obviously not scores (year-looking, etc).
    if (/^\d{4}$/.test(last)) {
      // skip
    } else {
      return last;
    }
  }

  // Otherwise the leftmost score in the right window.
  const rights = [...right.matchAll(scoreRe)];
  if (rights.length > 0) {
    const first = rights[0][0].trim();
    if (!/^\d{4}$/.test(first)) return first;
  }

  return '';
}

function scanText(
  text: string,
  recordId: string,
  recordName: string,
  source: 'perf' | 'claims'
): BenchmarkScore[] {
  if (!text) return [];
  const out: BenchmarkScore[] = [];
  const seenForRecord = new Set<string>();
  for (const { canonical, pattern } of BENCHMARKS) {
    // Reset lastIndex because patterns are global.
    pattern.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = pattern.exec(text)) !== null) {
      if (seenForRecord.has(canonical)) {
        // Multiple mentions of the same benchmark in the same cell
        // collapse to one row (we keep the first score we found).
        break;
      }
      const score = scoreNearMatch(text, m.index, m.index + m[0].length);
      out.push({
        benchmark: canonical,
        score,
        record_id: recordId,
        record_name: recordName,
        source
      });
      seenForRecord.add(canonical);
    }
  }
  return out;
}

/**
 * Walk every record, pulling `(benchmark, score)` rows from the perf
 * cell and (if not already captured) the claims cell.
 *
 * Skips records whose perf cell is one of the corpus's "no data"
 * sentinels — these still mention benchmark names in `claims` (e.g. a
 * paper that *evaluates against* GAIA but didn't publish a top-line
 * score), and we don't want to misattribute presence in that case.
 */
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

    const perfScores = scanText(perfText, r.id, r.name, 'perf');
    out.push(...perfScores);

    // Claims is secondary — only contribute benchmarks not already
    // captured from perf for this record.
    const claimedBenchmarks = new Set(perfScores.map((s) => s.benchmark));
    const claimsText =
      claimsCell?.value && claimsCell.status === 'real-data' ? claimsCell.value : '';
    const claimsScores = scanText(claimsText, r.id, r.name, 'claims').filter(
      (s) => !claimedBenchmarks.has(s.benchmark)
    );
    out.push(...claimsScores);
  }
  return out;
}

export interface CoverageMatrix {
  /** Ordered system names (rows). Sorted by total benchmark coverage desc. */
  systems: { id: string; name: string; count: number }[];
  /** Ordered benchmarks (cols). Sorted by coverage desc, capped at topN. */
  benchmarks: { name: string; count: number }[];
  /** Cell lookup keyed by `${system_id}::${benchmark}`. */
  cells: Map<string, { score: string; source: 'perf' | 'claims' }>;
}

/**
 * Build a coverage matrix from raw scores.
 *
 *   - rows = every system with ≥1 score
 *   - cols = top-N benchmarks by coverage count
 *   - cell = score string for that (system, benchmark) pair, or absent
 */
export function buildMatrix(scores: BenchmarkScore[], topN = 14): CoverageMatrix {
  const benchmarkCounts = new Map<string, number>();
  const systemCounts = new Map<string, number>();
  const systemNames = new Map<string, string>();
  const cells = new Map<string, { score: string; source: 'perf' | 'claims' }>();

  for (const s of scores) {
    benchmarkCounts.set(s.benchmark, (benchmarkCounts.get(s.benchmark) ?? 0) + 1);
    const key = `${s.record_id}::${s.benchmark}`;
    if (!cells.has(key)) {
      cells.set(key, { score: s.score, source: s.source });
      systemCounts.set(s.record_id, (systemCounts.get(s.record_id) ?? 0) + 1);
      systemNames.set(s.record_id, s.record_name);
    }
  }

  const benchmarks = [...benchmarkCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([name, count]) => ({ name, count }));

  const benchmarkSet = new Set(benchmarks.map((b) => b.name));

  // Now re-count systems restricted to the visible benchmarks (so a
  // system with one obscure benchmark that didn't make the cut isn't a
  // row of empty cells).
  const visibleSystemCounts = new Map<string, number>();
  for (const [key, _] of cells) {
    const [id, bench] = key.split('::');
    if (!benchmarkSet.has(bench)) continue;
    visibleSystemCounts.set(id, (visibleSystemCounts.get(id) ?? 0) + 1);
  }

  const systems = [...visibleSystemCounts.entries()]
    .sort((a, b) => b[1] - a[1] || systemNames.get(a[0])!.localeCompare(systemNames.get(b[0])!))
    .map(([id, count]) => ({
      id,
      name: systemNames.get(id) ?? id,
      count
    }));

  return { systems, benchmarks, cells };
}

// --- Derived insights ----------------------------------------------------

export interface BenchmarkCount {
  benchmark: string;
  count: number;
}

/**
 * Per-benchmark coverage counts (full population, not capped at topN).
 */
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

/**
 * Per-system benchmark count (full population). Top-N caller decides
 * how to truncate.
 */
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

/**
 * The headline "are memory-specific benchmarks under-adopted?" stat.
 *
 * Memory-specific = LongMemEval, LoCoMo, BABILong, ConvoMem, RULER,
 * MemoryAgentBench, ImplicitMemBench, PersonaBench, NIAH.
 *
 * Domain-specific = everything else from BENCHMARKS (GAIA, ALFWorld,
 * SWE-bench, OSWorld, WebArena, AppWorld, ScienceWorld, Mind2Web,
 * BrowseComp, AIME, MT-Bench, MMLU, HotpotQA, TriviaQA, NaturalQuestions,
 * LongBench).
 *
 * "Unique systems" = a system counts once per category, regardless of
 * how many benchmarks in that category it reports on.
 */
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
