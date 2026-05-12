// Pure helpers for the /analyses/survivorship view (issue #23).
//
// Classifies every record into one of:
//   - 'active'     : freshness signal within last 12 months
//   - 'stale'      : freshness signal 12-24 months old
//   - 'abandoned'  : freshness signal >24 months old
//   - 'unknown'    : no parseable freshness signal
//   - 'research'   : research artefacts (Tier 3/4) — no "active dev" expectation
//
// Freshness signal is the LATEST date we can pull from, in priority order:
//   1. cells['latest-release'].value (e.g. "v1.5.9 2026-05-05")
//   2. cells['code-release'].value   (parsed "last commit YYYY-MM" pattern)
//   3. cells.created.value           (baseline; used last because it tells us
//      birthdate, not liveness — but a recently *created* thing has implicit
//      freshness even with no release yet)
//
// See docs/DECISIONS.md (2026-05-12 "Survivorship classification") for the
// rationale on the research-bucket separation and the relative-to-today
// snapshot date.

import type { LandscapeRecord } from '$lib/types';

export type Survivorship =
  | 'active'
  | 'stale'
  | 'abandoned'
  | 'unknown'
  | 'research';

export interface Classification {
  status: Survivorship;
  /** Short human-readable signal source, e.g. "latest-release 2026-04" or
   *  "code-release last commit 2024-09" or "research (Tier 4)". */
  signal: string;
  /** Months between today and the freshness signal. Null when no signal
   *  parsed (status === 'unknown' or 'research'). */
  age_months: number | null;
}

// Snapshot date used as "today" for age calculations. Hardcoded so the page
// renders the same way regardless of when it's loaded — survivorship is a
// point-in-time view, not a moving target.
export const TODAY = new Date('2026-05-12T00:00:00Z');

/** Bucket boundaries in whole months. */
export const ACTIVE_MAX_MONTHS = 12;
export const STALE_MAX_MONTHS = 24;

/**
 * Extract a YYYY-MM (or YYYY-MM-DD) date from a free-text string. Returns
 * a Date pinned to the 15th of the month when only year+month present, or
 * null if no plausible match. The 15th-of-month choice keeps age math
 * roughly centred (avoids off-by-one for end-of-month releases).
 *
 * Tolerates prose: "Announced 2026-04 (GTC)" parses as 2026-04. Picks the
 * LAST plausible date in the string (not the first) because "v1.0 2024-08;
 * v1.5 2025-12" should resolve to 2025-12 — releases listed in order, the
 * tail is the freshest.
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
  // Match all YYYY-MM[-DD] occurrences; keep the latest.
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

/**
 * Pull "last commit YYYY-MM" from a code-release cell. Iter 2's depth pass
 * added these tokens to many rows; the pattern is fairly consistent. We
 * accept "last commit 2024-09", "last-commit 2024-09", and (lower priority)
 * a "stale (last commit 2024-09)" wrapper.
 */
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

/**
 * Decide whether a record should be treated as a "research artefact"
 * (paper, technique, benchmark) rather than as a maintained product.
 *
 * Heuristic: Tier 3 and Tier 4 records are research-leaning by definition
 * of the tier system (T3 emerging / academic-adjacent, T4 research papers).
 * Tier 5 is theoretical and gets the same treatment. We DO NOT reroute T1/T2
 * to research even if they're old — those are products and their staleness
 * is a real signal.
 */
export function isResearch(record: LandscapeRecord): boolean {
  return record.tier === 3 || record.tier === 4 || record.tier === 5;
}

/**
 * Classify a single record. See module header for bucket definitions.
 */
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

  // Priority 3: created cell as a soft signal. Many closed-source T1/T2
  // products carry no release/code-release data (cells literally say
  // "not applicable — not OSS"). Their `created` cell sometimes contains
  // multiple dates (founding date plus acquisition/GA rollouts); we take
  // the LATEST such date. If it's within the active window, we count the
  // record as Active (a launch in the last 12 months IS recent activity).
  //
  // For older `created` dates with no release/commit evidence, we mark
  // Unknown — NOT abandoned. Absence of release data in the catalog isn't
  // evidence of abandonment for a closed-source product that might never
  // have published release notes. Calling Slack or Notion "abandoned"
  // because we can't parse their changelog would be wrong.
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
      return {
        status: 'unknown',
        signal: `created ${formatYearMonth(d)} (no release/commit signal — closed-source likely)`,
        age_months: null
      };
    }
  }

  return { status: 'unknown', signal: 'no parseable date', age_months: null };
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

/** Status colours — green / amber / red / grey / purple. Aligned with the
 *  tier palette so the page feels of-a-piece with /timeline. */
export const SURVIVORSHIP_COLOURS: Record<Survivorship, string> = {
  active: '#3fb950',
  stale: '#d29922',
  abandoned: '#f85149',
  unknown: '#8b949e',
  research: '#bc8cff'
};

/** Section + status counts for the per-section strip view.
 *  Returned sorted by total rows desc so big sections appear first. */
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

/**
 * Most-influential-but-abandoned. Surfaces the "dead-but-still-cited" rows.
 *
 * Influence score = inbound integrations * 3 + inbound citations. The 3x
 * weight on integrations reflects that an integration is a strong
 * commercial signal (someone shipped against the API) where a citation
 * can be a passing reference.
 *
 * Inclusion rule: status === 'abandoned' OR (status === 'research' AND
 * the code-release cell carries a "last commit" >24 months old). The
 * second clause exists because research artefacts are kept out of the
 * primary abandoned bucket (per docs/DECISIONS.md "Survivorship classification")
 * — but the user's intent here is to surface the dead-but-cited. A T3
 * paper whose repo went quiet two years ago and which still gets cited
 * eight times across the catalog is exactly the row this table is for.
 */
export interface InfluentialAbandoned {
  record: LandscapeRecord;
  cls: Classification;
  inboundIntegrations: number;
  inboundCitations: number;
  score: number;
  /** Effective bucket label for the table — 'abandoned' or 'research·stale-repo'. */
  effective: 'abandoned' | 'research·stale-repo';
}

export function influentialAbandoned(
  records: LandscapeRecord[],
  classifications: Map<string, Classification>,
  inboundIntegrations: Map<string, number>,
  inboundCitations: Map<string, number>
): InfluentialAbandoned[] {
  const out: InfluentialAbandoned[] = [];
  for (const r of records) {
    const cls = classifications.get(r.id);
    if (!cls) continue;

    let effective: 'abandoned' | 'research·stale-repo' | null = null;
    let signal = cls.signal;

    if (cls.status === 'abandoned') {
      effective = 'abandoned';
    } else if (cls.status === 'research') {
      // Research rows: include only if the repo has a known-stale last commit.
      const lastCommit = parseLastCommit(r.cells['code-release']?.value);
      if (lastCommit) {
        const age = monthsBetween(lastCommit, TODAY);
        if (age > STALE_MAX_MONTHS) {
          effective = 'research·stale-repo';
          signal = `last commit ${lastCommit.getUTCFullYear()}-${String(lastCommit.getUTCMonth() + 1).padStart(2, '0')} (${age}mo)`;
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
      effective
    });
  }
  return out.sort(
    (a, b) => b.score - a.score || a.record.name.localeCompare(b.record.name)
  );
}
