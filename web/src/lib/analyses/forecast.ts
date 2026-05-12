// Pure helpers for the lineage forward-projection view (issue #27).
//
// For each detected lineage, project where the next paper/product is
// likely to come from. The projection is openly speculative — we frame
// the output as a "watch list" rather than a prediction (see
// docs/DECISIONS.md for the framing rationale).
//
// Inputs: records + edges. We do not re-implement lineage detection here;
// we call detectLineages() from $lib/lineages and consume the result.
//
// Outputs: one LineageForecast per lineage with cadence, next-expected
// drop date (year-quarter), leading-edge member ids, and a tiny themes
// list extracted from the leading edge's claims / cons cells.

import type { Edge, LandscapeRecord } from '$lib/types';
import { parseCreatedDate } from '$lib/timeline';
import { detectLineages, type Lineage } from '$lib/lineages';

export type LineageForecast = {
  lineage_id: string;
  lineage_name: string;
  kind: 'descent' | 'pattern';
  curated: boolean;
  members_total: number;
  /** Earliest member's year-quarter label, e.g. "2020-Q1". */
  earliest: string;
  /** Latest member's year-quarter label. */
  latest: string;
  /** Average gap between consecutive members in quarters. NaN if <2 members. */
  cadence_quarters: number;
  /** Next-expected year-quarter label, e.g. "2026-Q3". Empty if uncomputable. */
  next_expected: string;
  /** The 3 most-recent member ids (latest first). */
  leading_edge: string[];
  /** Display names of leading-edge members in same order. */
  leading_edge_names: string[];
  /** Up to ~8 themes (keywords) extracted from leading edge's claims + cons. */
  themes: string[];
  /** Adjacent lineages — other lineages this one shares members with or has
   *  edges to. Surfaces cross-pollination potential. */
  adjacent: string[];
  /** Arxiv listings the user could subscribe to. Heuristic: derived from
   *  the leading edge records' arxiv-id-shaped ids. */
  watch_links: WatchLink[];
};

export type WatchLink = {
  label: string;
  url: string;
};

/** Quarter index = year * 4 + (quarter - 1). Lets us subtract two dates
 *  in quarter units without month arithmetic. */
function quarterIndex(year: number, quarter: number): number {
  return year * 4 + (quarter - 1);
}

/** Convert a quarter index back to a "YYYY-Qn" label. */
function indexToLabel(idx: number): string {
  const year = Math.floor(idx / 4);
  const q = (idx % 4) + 1;
  return `${year}-Q${q}`;
}

/** Get the (year, quarter, idx) for a record, or null if unparseable. */
function recordQuarterIndex(r: LandscapeRecord): number | null {
  const parsed = parseCreatedDate(r.cells.created?.value);
  if (!parsed) return null;
  return quarterIndex(parsed.year, parsed.quarter);
}

/**
 * Common stopwords for theme keyword extraction. We're casting a small
 * net: domain-meaningful words like "memory", "retrieval", "graph"
 * should survive. Numbers and very short tokens (<= 3 chars) are
 * filtered separately.
 */
const STOPWORDS = new Set<string>([
  'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'being', 'but',
  'by', 'can', 'do', 'does', 'for', 'from', 'has', 'have', 'in', 'into',
  'is', 'it', 'its', 'of', 'on', 'or', 'over', 'than', 'that', 'the',
  'their', 'them', 'this', 'to', 'up', 'was', 'we', 'were', 'when',
  'which', 'while', 'with', 'without', 'will', 'would', 'use', 'used',
  'using', 'via', 'such', 'these', 'those', 'also', 'across', 'each',
  'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
  'ten', 'new', 'more', 'most', 'less', 'least', 'how', 'why', 'what',
  'who', 'where', 'all', 'any', 'some', 'other', 'no', 'not', 'only',
  'same', 'first', 'last', 'next', 'about', 'after', 'before', 'between',
  'both', 'either', 'neither', 'paper', 'papers', 'system', 'systems',
  'method', 'methods', 'model', 'models', 'approach', 'approaches',
  'work', 'works', 'task', 'tasks', 'baseline', 'baselines', 'headline',
  'show', 'shows', 'shown', 'still', 'specific', 'specifically', 'time',
  'times', 'data', 'dataset', 'datasets'
]);

/**
 * Pull a small set of theme keywords from a chunk of text. We keep words
 * with length > 3, drop stopwords, lowercase, and keep the most-frequent
 * surviving tokens. Frequency-based — not TF-IDF — because the input is
 * tiny (~3 cells) and we just want the recurring vocabulary.
 */
export function extractThemes(text: string, max = 8): string[] {
  if (!text) return [];
  const tokens = text
    .toLowerCase()
    // Keep alphanumerics + hyphen so "world-model" / "long-context" survive.
    .replace(/[^a-z0-9\-\s]/g, ' ')
    .split(/\s+/)
    .filter((t) => t.length > 3 && !STOPWORDS.has(t) && !/^\d+$/.test(t));
  const freq = new Map<string, number>();
  for (const t of tokens) freq.set(t, (freq.get(t) ?? 0) + 1);
  return [...freq.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, max)
    .map(([w]) => w);
}

/**
 * Sort lineage member ids by their `created` date descending (most-recent
 * first). Members without a parseable date sink to the end. Returns ids
 * that successfully parsed plus a separate list of undated ids — the
 * forecast cares mainly about the dated subset.
 */
function membersByDateDesc(
  members: string[],
  byId: Map<string, LandscapeRecord>
): { dated: Array<{ id: string; idx: number }>; undated: string[] } {
  const dated: Array<{ id: string; idx: number }> = [];
  const undated: string[] = [];
  for (const id of members) {
    const r = byId.get(id);
    if (!r) continue;
    const idx = recordQuarterIndex(r);
    if (idx === null) {
      undated.push(id);
      continue;
    }
    dated.push({ id, idx });
  }
  dated.sort((a, b) => b.idx - a.idx);
  return { dated, undated };
}

/**
 * Compute the average gap (in quarters) between consecutive dated
 * members of a lineage. The input must be sorted descending by date.
 * Returns NaN if fewer than 2 dated members. We collapse zero-gaps
 * (multiple members in same quarter) into a half-quarter so cadence
 * doesn't go to 0 for clustered lineages — interpreting "two systems
 * dropped same quarter" as "0-month cadence" would predict the next
 * one tomorrow, which is silly.
 */
export function computeCadence(datedDesc: Array<{ idx: number }>): number {
  if (datedDesc.length < 2) return NaN;
  let total = 0;
  let n = 0;
  for (let i = 0; i < datedDesc.length - 1; i++) {
    const gap = datedDesc[i].idx - datedDesc[i + 1].idx;
    // Floor at 0.5 quarters so clustered releases don't crash cadence.
    total += Math.max(gap, 0.5);
    n += 1;
  }
  return n === 0 ? NaN : total / n;
}

/**
 * Build a watch list of arxiv URLs from leading-edge member ids. Our
 * ids encode the arxiv reference for research-paper records (e.g.
 * `dreamerv3--arxiv-2301-04104`); we extract the arxiv id and emit a
 * link to the abstract page. Product records use a different id
 * format (e.g. `graphrag-microsoft--microsoft-com`) and produce no
 * arxiv link — we fall back to a category-listing URL for the lineage
 * as a whole.
 */
function buildWatchLinks(
  leading: Array<{ id: string; record: LandscapeRecord }>,
  lineage: Lineage
): WatchLink[] {
  const out: WatchLink[] = [];
  const seen = new Set<string>();
  for (const { id, record } of leading) {
    // Pattern: <slug>--arxiv-<YYMM>-<NNNNN>
    const m = id.match(/--arxiv-(\d{4})-(\d{4,5})/);
    if (m) {
      const arxivId = `${m[1]}.${m[2]}`;
      const url = `https://arxiv.org/abs/${arxivId}`;
      if (!seen.has(url)) {
        seen.add(url);
        out.push({ label: `arXiv:${arxivId} (${record.name})`, url });
      }
    }
  }
  // Always include a generic arxiv listing for AI/ML so the user has a
  // "subscribe to the firehose" option even when no leading-edge member
  // has an arxiv id.
  if (out.length === 0 || lineage.kind === 'descent') {
    const listingUrl = 'https://arxiv.org/list/cs.AI/recent';
    if (!seen.has(listingUrl)) {
      out.push({ label: 'arXiv cs.AI new listings', url: listingUrl });
    }
  }
  return out.slice(0, 3);
}

/**
 * Identify lineages adjacent to `target` by either shared members or
 * any descent edge whose endpoints cross lineage boundaries. The
 * union-find pass in detectLineages won't put two records in the same
 * lineage unless they're connected via descent edges, but curated
 * pattern lineages can overlap (a record may also have descent
 * relations). Cross-edges between auto-detected lineages are rare but
 * surface "this family is talking to that family" cross-pollination.
 */
export function findAdjacent(
  target: Lineage,
  all: Lineage[],
  edges: Edge[]
): string[] {
  const targetMembers = new Set(target.members);
  const memberToLineage = new Map<string, string>();
  for (const l of all) {
    if (l.id === target.id) continue;
    for (const m of l.members) {
      // First-write-wins; curated lineages emit first so they win ties.
      if (!memberToLineage.has(m)) memberToLineage.set(m, l.id);
    }
  }
  const adjacent = new Set<string>();
  // (a) shared members
  for (const l of all) {
    if (l.id === target.id) continue;
    for (const m of l.members) {
      if (targetMembers.has(m)) {
        adjacent.add(l.id);
        break;
      }
    }
  }
  // (b) cross-edges
  for (const e of edges) {
    const sIn = targetMembers.has(e.source);
    const tIn = targetMembers.has(e.target);
    if (sIn && !tIn) {
      const other = memberToLineage.get(e.target);
      if (other) adjacent.add(other);
    } else if (tIn && !sIn) {
      const other = memberToLineage.get(e.source);
      if (other) adjacent.add(other);
    }
  }
  return [...adjacent];
}

/**
 * Main entry. Detect lineages from (records, edges) and return a
 * forecast per lineage. Top 8 lineages by default — matching the
 * /lineages timeline view so the two pages tell the same story.
 */
export function forecastAll(
  records: LandscapeRecord[],
  edges: Edge[]
): LineageForecast[] {
  const lineages = detectLineages(records, edges, { topN: 8, minSize: 3 });
  const byId = new Map<string, LandscapeRecord>();
  for (const r of records) byId.set(r.id, r);

  const out: LineageForecast[] = [];
  for (const l of lineages) {
    const { dated } = membersByDateDesc(l.members, byId);
    const cadence = computeCadence(dated);
    const earliest = dated.length > 0 ? indexToLabel(dated[dated.length - 1].idx) : '';
    const latest = dated.length > 0 ? indexToLabel(dated[0].idx) : '';

    let nextExpected = '';
    if (dated.length >= 2 && isFinite(cadence)) {
      const projectedIdx = Math.round(dated[0].idx + cadence);
      nextExpected = indexToLabel(projectedIdx);
    } else if (dated.length === 1) {
      // No cadence signal; nudge one quarter forward as the floor.
      nextExpected = indexToLabel(dated[0].idx + 1);
    }

    const leadingDated = dated.slice(0, 3);
    const leadingRecords = leadingDated
      .map(({ id }) => ({ id, record: byId.get(id) }))
      .filter((x): x is { id: string; record: LandscapeRecord } => !!x.record);

    // Themes: claims + cons for the leading edge, glued together.
    const themeText = leadingRecords
      .map(({ record }) => {
        const claims = record.cells.claims?.value ?? '';
        const cons = record.cells.cons?.value ?? '';
        return `${claims} ${cons}`;
      })
      .join(' ');
    const themes = extractThemes(themeText, 8);

    const watchLinks = buildWatchLinks(leadingRecords, l);
    const adjacent = findAdjacent(l, lineages, edges);

    out.push({
      lineage_id: l.id,
      lineage_name: l.name,
      kind: l.kind,
      curated: l.curated,
      members_total: l.members.length,
      earliest,
      latest,
      cadence_quarters: cadence,
      next_expected: nextExpected,
      leading_edge: leadingRecords.map((x) => x.id),
      leading_edge_names: leadingRecords.map((x) => x.record.name),
      themes,
      adjacent,
      watch_links: watchLinks
    });
  }

  return out;
}

/**
 * Helper: human label for a cadence value in months. NaN/inf → "—".
 * Quarters * 3 = months. Round to nearest month for readability.
 */
export function cadenceMonths(cadenceQuarters: number): string {
  if (!isFinite(cadenceQuarters)) return '—';
  const months = Math.round(cadenceQuarters * 3);
  return `${months}mo`;
}
