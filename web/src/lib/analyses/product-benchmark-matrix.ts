// Pure helpers for the product × benchmark coverage matrix (issue #43).
//
// Companion-and-pivot to the existing benchmark coverage matrix
// (`benchmarks.ts` + `benchmark-integrity.ts`). The existing
// `/analyses/benchmarks` view is benchmark-centric: rows are benchmarks,
// the lens is "is this benchmark adopted?". This view flips the matrix
// to product-centric: rows are products, the lens is "is this product
// reporting any peer-reviewed score?" — surfacing the population that
// refuses to publish on independently-verifiable terrain.
//
// We deliberately reuse:
//   - `extractScores` from `benchmarks.ts` for benchmark mention parsing
//     (canonical names, score extraction, perf-over-claims preference)
//   - `classifyIntegrity` from `benchmark-integrity.ts` for the five-bucket
//     integrity tier classification (peer-reviewed, independently-verified,
//     vendor-claimed, disputed, unverifiable) plus citation hosts
//
// The new wrinkle is a `no-mention` integrity cell — the empty cell in
// the product-centric matrix. Existing helpers only emit rows for
// (product, benchmark) pairs that DO have a mention; we synthesise the
// negative space here so the matrix renders as a full grid.
//
// Pure module: no DOM, no fetch.

import type { LandscapeRecord } from '../types';
import { classifyIntegrity, type IntegrityRow } from './benchmark-integrity';

export type IntegrityTier =
  | 'peer-reviewed'
  | 'independently-verified'
  | 'vendor-claimed'
  | 'disputed'
  | 'unverifiable'
  | 'no-mention';

export interface ProductBenchmarkCell {
  product: string; // product/system name
  productId: string; // landscape record id
  benchmark: string; // canonical benchmark name
  benchmarkId: string | null; // record id of the benchmark itself (if catalogued); null otherwise
  integrity: IntegrityTier;
  score?: string; // surfaced if a numeric / textual score is attached
  citation?: string; // citation URL if any
}

export interface ProductRow {
  id: string;
  name: string;
  section: string;
  tier: number;
  coverageCount: number;
  topIntegrity: IntegrityTier;
}

export interface BenchmarkColumn {
  id: string | null;
  name: string;
  mentionCount: number;
}

export interface ProductBenchmarkMatrix {
  products: ProductRow[];
  benchmarks: BenchmarkColumn[];
  cells: ProductBenchmarkCell[];
  /** Products with zero peer-reviewed mentions (the "refuses to publish" set). */
  refusesToPublish: Array<{ id: string; name: string }>;
}

// Headline benchmark order — these always show first, in this order.
// Anything else surfaces after them, sorted by mention count.
const HEADLINE_BENCHMARKS: string[] = [
  'LongMemEval',
  'LoCoMo',
  'BABILong',
  'ConvoMem',
  'RULER',
  'MemoryBench',
  'MemBench',
  'NIAH'
];

// The benchmark extractor canonicalises "MemoryBench" / "MemBench" to
// `MemoryAgentBench`. We accept either alias from the issue spec and
// resolve to whatever the extractor emits — so the headline column
// labelled `MemoryAgentBench` covers both.
const HEADLINE_ALIASES: Record<string, string> = {
  MemoryBench: 'MemoryAgentBench',
  MemBench: 'MemoryAgentBench'
};

/**
 * Section → coarse category used by the UI category filter. Sections
 * named here group into a small set of buckets so a user can ask
 * "show me frameworks only" without enumerating 30 sections.
 */
const SECTION_CATEGORY: Record<string, string> = {
  'Dedicated memory layers': 'Memory systems',
  'Framework-embedded memory': 'Frameworks',
  'Agent frameworks (no first-party memory layer)': 'Frameworks',
  'Platform-provider memory': 'Memory systems',
  'Retrieval-as-memory hybrids': 'Memory systems',
  'Knowledge-graph platforms': 'Memory systems',
  'Vector-database infrastructure': 'Infrastructure',
  'Embedding & reranker services': 'Infrastructure',
  'Inference platforms & gateways': 'Infrastructure',
  'Training infrastructure': 'Infrastructure',
  'AI sandbox & runtime environments': 'Infrastructure',
  'Agent IDEs & coding harnesses': 'Agents',
  'Claude Code memory mechanisms': 'Agents',
  'Coding-agent memory': 'Agents',
  'Browser-agent memory': 'Agents',
  'Computer-use & desktop agents': 'Agents',
  'Use-case-specific agent harnesses': 'Agents',
  'Multi-agent orchestration platforms': 'Agents',
  'Voice agent platforms': 'Agents',
  'Voice-first / wearable AI memory': 'Agents',
  'Robotics foundation models & agent stacks': 'Agents',
  'Personal AI / PKM / lifelogging memory': 'Vertical',
  'Vertical / domain-specific AI memory': 'Vertical',
  'Foundation models (substrate reference)': 'Foundation',
  'Memory benchmarks & evaluation': 'Benchmarks / eval',
  'Evaluation & observability platforms': 'Benchmarks / eval',
  'Memory observability & monitoring': 'Benchmarks / eval',
  'Memory governance, privacy & safety': 'Governance',
  'Search platforms (non-memory)': 'Search / adjacent',
  'Enterprise-search adjacencies': 'Search / adjacent',
  'File-backed / editor paradigms': 'Frameworks',
  'Recent method papers — theorized, no distinct product': 'Research',
  'Research / specialised systems': 'Research',
  'Theoretical / informal — ideas without a paper': 'Research'
};

export function categoryOf(section: string): string {
  return SECTION_CATEGORY[section] ?? 'Other';
}

export function uniqueCategories(records: LandscapeRecord[]): string[] {
  const set = new Set<string>();
  for (const r of records) {
    const sec = r.sections.find((s) => s.primary)?.section ?? r.sections[0]?.section;
    if (sec) set.add(categoryOf(sec));
  }
  return [...set].sort();
}

// Map benchmark canonical names to landscape record ids when the
// benchmark itself exists as its own catalogued record (the rows in
// the "Memory benchmarks & evaluation" section). We do a permissive
// substring match against record names so e.g. "LongMemEval" matches
// a record called "LongMemEval Benchmark".
function buildBenchmarkRecordIndex(records: LandscapeRecord[]): Map<string, string> {
  const out = new Map<string, string>();
  for (const r of records) {
    const primarySection = r.sections.find((s) => s.primary)?.section ?? r.sections[0]?.section;
    if (primarySection !== 'Memory benchmarks & evaluation') continue;
    const lower = r.name.toLowerCase();
    // Use the headline list + a few common extras as the canonical key set.
    const probe: string[] = [
      'LongMemEval',
      'LoCoMo',
      'BABILong',
      'ConvoMem',
      'RULER',
      'MemoryAgentBench',
      'ImplicitMemBench',
      'PersonaBench',
      'NIAH',
      'LongBench',
      'HotpotQA',
      'TriviaQA',
      'NaturalQuestions',
      'GAIA',
      'ALFWorld',
      'SWE-bench',
      'OSWorld',
      'WebArena',
      'AppWorld',
      'ScienceWorld',
      'Mind2Web',
      'BrowseComp',
      'AIME',
      'MT-Bench',
      'MMLU'
    ];
    for (const canon of probe) {
      const key = canon.toLowerCase().replace(/[-\s]/g, '');
      const flat = lower.replace(/[-\s]/g, '');
      if (flat.includes(key) && !out.has(canon)) {
        out.set(canon, r.id);
        break;
      }
    }
  }
  return out;
}

// "Top integrity" for a row — the strongest bucket reached by any of
// that product's cells. Used both for sorting and for an at-a-glance
// row pill.
const INTEGRITY_RANK: Record<IntegrityTier, number> = {
  'peer-reviewed': 5,
  'independently-verified': 4,
  'vendor-claimed': 3,
  disputed: 2,
  unverifiable: 1,
  'no-mention': 0
};

export function compareIntegrity(a: IntegrityTier, b: IntegrityTier): number {
  return INTEGRITY_RANK[b] - INTEGRITY_RANK[a];
}

/**
 * Build the product × benchmark matrix from the canonical landscape.
 *
 * - Rows: every record that has at least one benchmark mention.
 *   (Records with zero mentions never appear — a row of all blanks is
 *   not informative and would dwarf the signal.)
 * - Columns: headline benchmarks first (in the order specified), then
 *   any other benchmarks with at least one mention, sorted by mention
 *   count desc.
 * - Cells: one per (product, benchmark) intersection. Cells are only
 *   present in `cells` for intersections where the product actually
 *   mentions that benchmark; absent intersections are rendered by the
 *   page as empty / `no-mention`.
 */
export function buildProductBenchmarkMatrix(records: LandscapeRecord[]): ProductBenchmarkMatrix {
  const integrityRows: IntegrityRow[] = classifyIntegrity(records);
  const benchmarkRecordIndex = buildBenchmarkRecordIndex(records);

  // Best (product, benchmark) cell: if there are multiple mentions for
  // the same pair (e.g. one in perf, one in claims), keep the strongest
  // integrity tier; tiebreak by perf over claims.
  const cellByKey = new Map<string, ProductBenchmarkCell>();
  for (const r of integrityRows) {
    const key = `${r.record_id}::${r.benchmark}`;
    const tier: IntegrityTier = r.bucket;
    const existing = cellByKey.get(key);
    const candidate: ProductBenchmarkCell = {
      product: r.record_name,
      productId: r.record_id,
      benchmark: r.benchmark,
      benchmarkId: benchmarkRecordIndex.get(r.benchmark) ?? null,
      integrity: tier,
      score: r.score || undefined,
      citation: r.citation ?? undefined
    };
    if (!existing) {
      cellByKey.set(key, candidate);
      continue;
    }
    // Prefer stronger integrity; on tie, prefer the one with a score.
    if (compareIntegrity(candidate.integrity, existing.integrity) < 0) {
      cellByKey.set(key, candidate);
    } else if (
      INTEGRITY_RANK[candidate.integrity] === INTEGRITY_RANK[existing.integrity] &&
      candidate.score &&
      !existing.score
    ) {
      cellByKey.set(key, candidate);
    }
  }
  const cells = [...cellByKey.values()];

  // Per-product aggregations.
  const productMeta = new Map<string, { name: string; section: string; tier: number }>();
  for (const r of records) {
    const sec = r.sections.find((s) => s.primary)?.section ?? r.sections[0]?.section ?? 'Unknown';
    productMeta.set(r.id, { name: r.name, section: sec, tier: r.tier });
  }

  const productCells = new Map<string, ProductBenchmarkCell[]>();
  for (const c of cells) {
    const arr = productCells.get(c.productId) ?? [];
    arr.push(c);
    productCells.set(c.productId, arr);
  }

  const products: ProductRow[] = [];
  for (const [id, list] of productCells) {
    const meta = productMeta.get(id);
    if (!meta) continue;
    let top: IntegrityTier = 'no-mention';
    for (const c of list) {
      if (INTEGRITY_RANK[c.integrity] > INTEGRITY_RANK[top]) top = c.integrity;
    }
    products.push({
      id,
      name: meta.name,
      section: meta.section,
      tier: meta.tier,
      coverageCount: list.length,
      topIntegrity: top
    });
  }
  products.sort(
    (a, b) =>
      b.coverageCount - a.coverageCount ||
      INTEGRITY_RANK[b.topIntegrity] - INTEGRITY_RANK[a.topIntegrity] ||
      a.name.localeCompare(b.name)
  );

  // Per-benchmark mention counts.
  const benchmarkCount = new Map<string, number>();
  for (const c of cells) {
    benchmarkCount.set(c.benchmark, (benchmarkCount.get(c.benchmark) ?? 0) + 1);
  }

  // Order: headline benchmarks first (resolving aliases), then others
  // by mention count desc, then alphabetical.
  const seenColumns = new Set<string>();
  const benchmarks: BenchmarkColumn[] = [];
  for (const raw of HEADLINE_BENCHMARKS) {
    const resolved = HEADLINE_ALIASES[raw] ?? raw;
    if (seenColumns.has(resolved)) continue;
    seenColumns.add(resolved);
    benchmarks.push({
      id: benchmarkRecordIndex.get(resolved) ?? null,
      // Use the user-facing label from the headline list for the column;
      // the helper still uses the canonical key internally.
      name: resolved,
      mentionCount: benchmarkCount.get(resolved) ?? 0
    });
  }
  const rest: BenchmarkColumn[] = [];
  for (const [name, count] of benchmarkCount) {
    if (seenColumns.has(name)) continue;
    rest.push({
      id: benchmarkRecordIndex.get(name) ?? null,
      name,
      mentionCount: count
    });
  }
  rest.sort((a, b) => b.mentionCount - a.mentionCount || a.name.localeCompare(b.name));
  benchmarks.push(...rest);

  // Refuses-to-publish: products with at least one benchmark mention but
  // zero peer-reviewed mentions.
  const peerReviewedByProduct = new Map<string, number>();
  for (const c of cells) {
    if (c.integrity === 'peer-reviewed') {
      peerReviewedByProduct.set(c.productId, (peerReviewedByProduct.get(c.productId) ?? 0) + 1);
    }
  }
  const refusesToPublish: Array<{ id: string; name: string }> = [];
  for (const p of products) {
    if ((peerReviewedByProduct.get(p.id) ?? 0) === 0) {
      refusesToPublish.push({ id: p.id, name: p.name });
    }
  }

  return { products, benchmarks, cells, refusesToPublish };
}

/**
 * The "X% of catalogued products report zero peer-reviewed benchmark
 * scores" callout numerator/denominator. Denominator is every record
 * in the catalog — the callout calls out the absolute share of the
 * landscape (not just the share of products that benchmark at all),
 * because that's the more provocative framing per the issue spec.
 */
export interface RefusesCallout {
  totalProducts: number;
  refusingProducts: number;
  withPeerReviewed: number;
  withAnyMention: number;
  /** refusingProducts / totalProducts as a 0-100 percent. */
  refusingPercent: number;
}

export function refusesCallout(
  records: LandscapeRecord[],
  matrix: ProductBenchmarkMatrix
): RefusesCallout {
  const totalProducts = records.length;
  const peerReviewedIds = new Set<string>();
  for (const c of matrix.cells) {
    if (c.integrity === 'peer-reviewed') peerReviewedIds.add(c.productId);
  }
  const withAnyMention = matrix.products.length;
  const withPeerReviewed = peerReviewedIds.size;
  const refusingProducts = totalProducts - withPeerReviewed;
  return {
    totalProducts,
    refusingProducts,
    withPeerReviewed,
    withAnyMention,
    refusingPercent: totalProducts === 0 ? 0 : (refusingProducts / totalProducts) * 100
  };
}

/**
 * Look up a cell by (productId, benchmark). Returns undefined for the
 * negative-space `no-mention` cells — the consumer is expected to
 * render those as blank.
 */
export function cellLookup(matrix: ProductBenchmarkMatrix): Map<string, ProductBenchmarkCell> {
  const m = new Map<string, ProductBenchmarkCell>();
  for (const c of matrix.cells) {
    m.set(`${c.productId}::${c.benchmark}`, c);
  }
  return m;
}
