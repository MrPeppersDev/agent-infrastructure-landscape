// Pure helpers for the /analyses/survivorship view (issue #23).
//
// Classifies every record into one of:
//   - 'active'     : freshness signal within last 12 months
//   - 'stale'      : freshness signal 12-24 months old
//   - 'abandoned'  : freshness signal >24 months old
//   - 'unknown'    : no parseable freshness signal
//   - 'research'   : research artefacts (Tier 3/4/5) — no "active dev" expectation
//
// Freshness signal is the LATEST date we can pull from, in priority order:
//   1. cells['latest-release'].value (e.g. "v1.5.9 2026-05-05")
//   2. cells['code-release'].value   (parsed "last commit YYYY-MM" pattern)
//   3. cells.created.value           (baseline; used last because it tells us
//      birthdate, not liveness — but a recently *created* thing has implicit
//      freshness even with no release yet)
//
// Round 23 upgrade: the Unknown bucket is now SUBDIVIDED into four
// sub-buckets so users can see structure rather than a single grey blob.
// The subdivision rules and rationale are in docs/DECISIONS.md under
// "2026-05-07: Survivorship Unknown-bucket subdivision".

import type { LandscapeRecord, Edge } from '$lib/types';
import { parseCreatedDate } from '$lib/timeline';

export type Survivorship =
  | 'active'
  | 'stale'
  | 'abandoned'
  | 'unknown'
  | 'research';

/** Sub-categories within the Unknown bucket. */
export type UnknownSubBucket =
  | 'closed-source'   // proprietary product, no public release cadence
  | 'oss-weak-signal' // OSS (has GitHub) but no parseable last-commit
  | 'newly-created'   // record.created < 6 months ago — too new to assess
  | 'na';             // research/benchmark-only artefact (rare here; Tier 3+
                      // already routes to 'research', so 'na' fires for the
                      // unusual T1/T2 record that has truly no signal).

export interface Classification {
  status: Survivorship;
  /** Short human-readable signal source. */
  signal: string;
  /** Months between today and the freshness signal. Null when no signal
   *  parsed (status === 'unknown' or 'research'). */
  age_months: number | null;
  /** Only populated when status === 'unknown'. */
  unknownSub?: UnknownSubBucket;
}

// Snapshot date used as "today" for age calculations.
export const TODAY = new Date('2026-05-12T00:00:00Z');

/** Bucket boundaries in whole months. */
export const ACTIVE_MAX_MONTHS = 12;
export const STALE_MAX_MONTHS = 24;

/** "Newly created" cutoff for the Unknown-bucket subdivision. */
export const NEWLY_CREATED_MAX_MONTHS = 6;

/**
 * Extract the LATEST YYYY-MM(-DD) date from a free-text string.
 * 15th-of-month pin keeps age math centred when only year+month known.
 */
export function parseDateLatest(raw: string | null | undefined): Date | null {
  if (!raw) return null;
  const v = raw.trim();
  if (!v) return null;
  const lower = v.toLowerCase();
  if (
    lower === 'no-release no-release' ||
    lower.startsWith('no-release') ||
    lower === 'no data' ||
    lower === 'searched not found' ||
    lower.includes('pre-existing')
  ) {
    return null;
  }
  const re = /(\d{4})-(\d{1,2})(?:-(\d{1,2}))?/g;
  let latest: Date | null = null;
  let m: RegExpExecArray | null;
  while ((m = re.exec(v)) !== null) {
    const year = Number(m[1]);
    const month = Number(m[2]);
    const day = m[3] ? Number(m[3]) : 15;
    if (
      year < 1900 ||
      year > 2099 ||
      month < 1 ||
      month > 12 ||
      day < 1 ||
      day > 31
    ) {
      continue;
    }
    const d = new Date(Date.UTC(year, month - 1, day));
    if (!latest || d > latest) latest = d;
  }
  return latest;
}

/** Pull "last commit YYYY-MM" from a code-release cell. */
export function parseLastCommit(raw: string | null | undefined): Date | null {
  if (!raw) return null;
  const lower = raw.toLowerCase();
  const m = lower.match(/last[- ]commit\s+(\d{4})-(\d{1,2})/);
  if (!m) return null;
  const year = Number(m[1]);
  const month = Number(m[2]);
  if (year < 1900 || year > 2099 || month < 1 || month > 12) return null;
  return new Date(Date.UTC(year, month - 1, 15));
}

/** Month difference (signed; negative if `to` is before `from`). Rounded. */
export function monthsBetween(from: Date, to: Date): number {
  const ms = to.getTime() - from.getTime();
  const days = ms / (1000 * 60 * 60 * 24);
  return Math.round(days / 30.4375);
}

/** Tier 3/4/5 == research artefact (paper/technique/theory). */
export function isResearch(record: LandscapeRecord): boolean {
  return record.tier === 3 || record.tier === 4 || record.tier === 5;
}

/** Heuristic: does this record have a usable GitHub/code presence? Used
 *  to distinguish "OSS with weak last-commit signal" from "closed-source,
 *  internal status unknown" inside the Unknown bucket subdivision. */
export function hasGitHubPresence(record: LandscapeRecord): boolean {
  const gh = record.cells.gh;
  if (gh && gh.status === 'real-data' && gh.value) {
    const lower = gh.value.toLowerCase();
    if (lower.includes('github.com') || lower.includes('gitlab')) return true;
    // "stars=12k" style summaries also imply a repo exists.
    if (/\d+\s*(stars?|k\s*stars?|forks?)/.test(lower)) return true;
  }
  const cr = record.cells['code-release'];
  if (cr && cr.status === 'real-data' && cr.value) {
    const lower = cr.value.toLowerCase();
    if (
      lower.includes('github') ||
      lower.includes('gitlab') ||
      lower.includes('repo')
    ) {
      return true;
    }
  }
  const license = record.cells.license;
  if (license && license.status === 'real-data' && license.value) {
    const lower = license.value.toLowerCase();
    if (
      lower.includes('apache') ||
      lower.includes('mit') ||
      lower.includes('bsd') ||
      lower.includes('gpl') ||
      lower.includes('mpl') ||
      lower.includes('agpl') ||
      lower.includes('open source') ||
      lower.includes('open-source')
    ) {
      return true;
    }
  }
  return false;
}

/** Classify a single record. */
export function classify(record: LandscapeRecord): Classification {
  if (isResearch(record)) {
    return {
      status: 'research',
      signal: `research (Tier ${record.tier})`,
      age_months: null
    };
  }

  // Priority 1: latest-release.
  const lr = record.cells['latest-release'];
  if (lr && lr.status === 'real-data') {
    const d = parseDateLatest(lr.value);
    if (d) {
      const age = monthsBetween(d, TODAY);
      return {
        status: bucketFromAge(age),
        signal: `latest-release ${formatYearMonth(d)}`,
        age_months: age
      };
    }
  }

  // Priority 2: code-release "last commit YYYY-MM" parse.
  const cr = record.cells['code-release'];
  if (cr && cr.value) {
    const d = parseLastCommit(cr.value);
    if (d) {
      const age = monthsBetween(d, TODAY);
      return {
        status: bucketFromAge(age),
        signal: `code-release last commit ${formatYearMonth(d)}`,
        age_months: age
      };
    }
  }

  // Priority 3: created cell as a soft signal.
  const created = record.cells.created;
  if (created && created.value) {
    const d = parseDateLatest(created.value);
    if (d) {
      const age = monthsBetween(d, TODAY);
      if (age <= ACTIVE_MAX_MONTHS) {
        return {
          status: 'active',
          signal: `created cell ${formatYearMonth(d)} (no release/commit signal)`,
          age_months: age
        };
      }
      // Unknown-bucket subdivision (round 23).
      const sub = subdivideUnknown(record, age);
      return {
        status: 'unknown',
        signal: subSignal(record, d, age, sub),
        age_months: null,
        unknownSub: sub
      };
    }
  }

  // Truly no parseable date — closed-source vs N/A split on OSS presence.
  const sub: UnknownSubBucket = hasGitHubPresence(record) ? 'oss-weak-signal' : 'closed-source';
  return {
    status: 'unknown',
    signal: 'no parseable date',
    age_months: null,
    unknownSub: sub
  };
}

/**
 * Within the Unknown bucket, route a record to one of the four
 * sub-buckets. Order of checks matters and reflects priority:
 *
 *   1. newly-created    — overrides everything when age < 6mo. A brand-new
 *                         system has nothing to be "stale" about; the right
 *                         framing for a user is "wait and see".
 *   2. na               — Tier 3+ already filters to 'research', so this
 *                         fires only for the rare T1/T2 row with no real
 *                         signal at all (typically benchmarks tagged as
 *                         products by mistake). Kept for completeness.
 *   3. oss-weak-signal  — has a GitHub presence but we couldn't parse a
 *                         last-commit. The catalog gap is the problem here,
 *                         not the project.
 *   4. closed-source    — default. Proprietary product, no public release
 *                         cadence. The signal limitation is structural.
 */
function subdivideUnknown(
  record: LandscapeRecord,
  createdAgeMonths: number
): UnknownSubBucket {
  if (createdAgeMonths >= 0 && createdAgeMonths <= NEWLY_CREATED_MAX_MONTHS) {
    return 'newly-created';
  }
  if (hasGitHubPresence(record)) {
    return 'oss-weak-signal';
  }
  return 'closed-source';
}

function subSignal(
  record: LandscapeRecord,
  createdDate: Date,
  ageMonths: number,
  sub: UnknownSubBucket
): string {
  const ym = formatYearMonth(createdDate);
  switch (sub) {
    case 'newly-created':
      return `created ${ym} (${ageMonths}mo ago — too new to assess)`;
    case 'oss-weak-signal':
      return `created ${ym}, OSS but no last-commit signal in catalog`;
    case 'na':
      return `created ${ym} (treated as N/A — no operational signal expected)`;
    case 'closed-source':
    default:
      return `created ${ym} (no release/commit signal — closed-source likely)`;
  }
}

function bucketFromAge(age: number): Survivorship {
  if (age <= ACTIVE_MAX_MONTHS) return 'active';
  if (age <= STALE_MAX_MONTHS) return 'stale';
  return 'abandoned';
}

function formatYearMonth(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  return `${y}-${m}`;
}

/** Run `classify` over every record, keyed by record id. */
export function classifyAll(
  records: LandscapeRecord[]
): Map<string, Classification> {
  const out = new Map<string, Classification>();
  for (const r of records) {
    out.set(r.id, classify(r));
  }
  return out;
}

/** Bucket counts for the top-row counters. */
export interface BucketCounts {
  active: number;
  stale: number;
  abandoned: number;
  unknown: number;
  research: number;
  total: number;
}

export function countBuckets(
  classifications: Map<string, Classification>
): BucketCounts {
  const out: BucketCounts = {
    active: 0,
    stale: 0,
    abandoned: 0,
    unknown: 0,
    research: 0,
    total: 0
  };
  for (const c of classifications.values()) {
    out[c.status] += 1;
    out.total += 1;
  }
  return out;
}

/** Counts inside the Unknown sub-buckets. */
export interface UnknownSubCounts {
  'closed-source': number;
  'oss-weak-signal': number;
  'newly-created': number;
  na: number;
  total: number;
}

export function countUnknownSubs(
  classifications: Map<string, Classification>
): UnknownSubCounts {
  const out: UnknownSubCounts = {
    'closed-source': 0,
    'oss-weak-signal': 0,
    'newly-created': 0,
    na: 0,
    total: 0
  };
  for (const c of classifications.values()) {
    if (c.status !== 'unknown' || !c.unknownSub) continue;
    out[c.unknownSub] += 1;
    out.total += 1;
  }
  return out;
}

/** Stable display order for buckets. */
export const SURVIVORSHIP_ORDER: Survivorship[] = [
  'active',
  'stale',
  'abandoned',
  'unknown',
  'research'
];

export const SURVIVORSHIP_LABELS: Record<Survivorship, string> = {
  active: 'Active',
  stale: 'Stale',
  abandoned: 'Abandoned',
  unknown: 'Unknown',
  research: 'Research'
};

export const SURVIVORSHIP_COLOURS: Record<Survivorship, string> = {
  active: '#3fb950',
  stale: '#d29922',
  abandoned: '#f85149',
  unknown: '#8b949e',
  research: '#bc8cff'
};

export const UNKNOWN_SUB_ORDER: UnknownSubBucket[] = [
  'closed-source',
  'oss-weak-signal',
  'newly-created',
  'na'
];

export const UNKNOWN_SUB_LABELS: Record<UnknownSubBucket, string> = {
  'closed-source': 'Closed-source, internal status unknown',
  'oss-weak-signal': 'OSS but signal-too-weak',
  'newly-created': 'Newly created (< 6mo)',
  na: 'N/A (research/benchmark-only)'
};

export const UNKNOWN_SUB_SHORT: Record<UnknownSubBucket, string> = {
  'closed-source': 'Closed-source',
  'oss-weak-signal': 'OSS weak-signal',
  'newly-created': 'Newly created',
  na: 'N/A'
};

/** Sub-bucket palette — kept in the grey family so it still reads as
 *  "this is all the Unknown bucket" but distinguishable. */
export const UNKNOWN_SUB_COLOURS: Record<UnknownSubBucket, string> = {
  'closed-source': '#6e7681',
  'oss-weak-signal': '#a1a8b3',
  'newly-created': '#79c0ff',
  na: '#484f58'
};

export const UNKNOWN_SUB_INTERPRETATION: Record<UnknownSubBucket, string> = {
  'closed-source':
    'Proprietary products with no public release cadence. Common for T1 commercial vendors. The catalog cannot observe their internal status — this is a limit of our signal, not a property of the system.',
  'oss-weak-signal':
    'Has a GitHub presence but we did not capture a parseable "last commit" date in the cell. Fixable by deeper data collection on these specific rows.',
  'newly-created':
    'Created in the last 6 months. Too new to assess freshness — re-check at the next snapshot.',
  na: 'Genuinely not applicable: benchmark or evaluation harness mislabelled as a product, or a record that explicitly carries no operational signal.'
};

/** Section + status counts for the per-section strip view. */
export interface SectionStrip {
  section: string;
  total: number;
  byStatus: Record<Survivorship, number>;
  rows: { record: LandscapeRecord; cls: Classification }[];
}

function primarySection(r: LandscapeRecord): string {
  const p = r.sections.find((s) => s.primary);
  return p?.section ?? r.sections[0]?.section ?? 'Uncategorised';
}

export function bySection(
  records: LandscapeRecord[],
  classifications: Map<string, Classification>
): SectionStrip[] {
  const map = new Map<string, SectionStrip>();
  for (const r of records) {
    const sec = primarySection(r);
    let s = map.get(sec);
    if (!s) {
      s = {
        section: sec,
        total: 0,
        byStatus: {
          active: 0,
          stale: 0,
          abandoned: 0,
          unknown: 0,
          research: 0
        },
        rows: []
      };
      map.set(sec, s);
    }
    const cls = classifications.get(r.id);
    if (!cls) continue;
    s.total += 1;
    s.byStatus[cls.status] += 1;
    s.rows.push({ record: r, cls });
  }
  return [...map.values()].sort((a, b) => b.total - a.total);
}

/** Aging score per section: (stale + abandoned) / (total - research).
 *  Higher = more of the maintained surface has gone quiet. Returns 0 if
 *  the section has no non-research members. */
export function sectionAgingScore(s: SectionStrip): number {
  const denom = s.total - s.byStatus.research;
  if (denom <= 0) return 0;
  return (s.byStatus.stale + s.byStatus.abandoned) / denom;
}

/** Most-influential-but-abandoned. */
export interface InfluentialAbandoned {
  record: LandscapeRecord;
  cls: Classification;
  inboundIntegrations: number;
  inboundCitations: number;
  score: number;
  effective: 'abandoned' | 'research·stale-repo';
  /** Last-commit/release age in months, when known. */
  lastSignalAgeMonths: number | null;
  /** Lineage name if the record is a member of a detected lineage. */
  lineageName: string | null;
}

export function influentialAbandoned(
  records: LandscapeRecord[],
  classifications: Map<string, Classification>,
  inboundIntegrations: Map<string, number>,
  inboundCitations: Map<string, number>,
  lineageByMember?: Map<string, string>
): InfluentialAbandoned[] {
  const out: InfluentialAbandoned[] = [];
  for (const r of records) {
    const cls = classifications.get(r.id);
    if (!cls) continue;

    let effective: 'abandoned' | 'research·stale-repo' | null = null;
    let signal = cls.signal;
    let ageMonths: number | null = cls.age_months;

    if (cls.status === 'abandoned') {
      effective = 'abandoned';
    } else if (cls.status === 'research') {
      const lastCommit = parseLastCommit(r.cells['code-release']?.value);
      if (lastCommit) {
        const age = monthsBetween(lastCommit, TODAY);
        if (age > STALE_MAX_MONTHS) {
          effective = 'research·stale-repo';
          signal = `last commit ${formatYearMonth(lastCommit)} (${age}mo)`;
          ageMonths = age;
        }
      }
    }

    if (!effective) continue;

    const intg = inboundIntegrations.get(r.id) ?? 0;
    const cite = inboundCitations.get(r.id) ?? 0;
    const score = intg * 3 + cite;
    if (score === 0) continue;
    out.push({
      record: r,
      cls: { ...cls, signal },
      inboundIntegrations: intg,
      inboundCitations: cite,
      score,
      effective,
      lastSignalAgeMonths: ageMonths,
      lineageName: lineageByMember?.get(r.id) ?? null
    });
  }
  return out.sort(
    (a, b) => b.score - a.score || a.record.name.localeCompare(b.record.name)
  );
}

/** Active-cohort created-date histogram. Returns year-quarter buckets in
 *  chronological order with only the Active records counted. */
export interface ActiveCohortBucket {
  key: string;
  year: number;
  quarter: 1 | 2 | 3 | 4;
  count: number;
}

export function activeCohortHistogram(
  records: LandscapeRecord[],
  classifications: Map<string, Classification>
): ActiveCohortBucket[] {
  const counts = new Map<string, ActiveCohortBucket>();
  for (const r of records) {
    const cls = classifications.get(r.id);
    if (!cls || cls.status !== 'active') continue;
    const created = parseCreatedDate(r.cells.created?.value);
    if (!created) continue;
    const key = `${created.year}-Q${created.quarter}`;
    const existing = counts.get(key);
    if (existing) {
      existing.count += 1;
    } else {
      counts.set(key, {
        key,
        year: created.year,
        quarter: created.quarter,
        count: 1
      });
    }
  }
  const list = [...counts.values()];
  if (list.length === 0) return [];
  // Fill empty quarters between min/max so the X-axis is continuous.
  list.sort((a, b) =>
    a.year !== b.year ? a.year - b.year : a.quarter - b.quarter
  );
  const first = list[0];
  const last = list[list.length - 1];
  const out: ActiveCohortBucket[] = [];
  const existing = new Map(list.map((b) => [b.key, b]));
  for (let y = first.year; y <= last.year; y++) {
    const qStart = y === first.year ? first.quarter : 1;
    const qEnd = y === last.year ? last.quarter : 4;
    for (let q = qStart; q <= qEnd; q++) {
      const key = `${y}-Q${q}`;
      out.push(
        existing.get(key) ?? {
          key,
          year: y,
          quarter: q as 1 | 2 | 3 | 4,
          count: 0
        }
      );
    }
  }
  return out;
}

/** Helper: build inbound edge maps from a flat edge list. */
export function buildInboundMaps(edges: Edge[]): {
  integrations: Map<string, number>;
  citations: Map<string, number>;
} {
  const integrations = new Map<string, number>();
  const citations = new Map<string, number>();
  for (const e of edges) {
    if (e.type === 'integrates-with' || e.type === 'built-on') {
      integrations.set(e.target, (integrations.get(e.target) ?? 0) + 1);
    } else if (e.type === 'cites') {
      citations.set(e.target, (citations.get(e.target) ?? 0) + 1);
    }
  }
  return { integrations, citations };
}
