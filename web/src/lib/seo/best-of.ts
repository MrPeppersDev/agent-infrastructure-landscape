// Long-tail "best of" landing pages — refs #105.
//
// Each predicate becomes a crawlable /best/<slug> page that ranks systems
// satisfying the predicate by tier (lower is better) and inbound-edge
// count. The catalog already has section / category landing pages; these
// are the orthogonal "filter by a feature people search for" axis. The
// queries we're targeting are things like "agent memory with MCP",
// "open-source agent memory", "HIPAA agent memory" — high intent, narrow
// audience, and the catalog is one of very few sources that can answer
// them comprehensively.
//
// Free-text cell values are noisy ("native (first-party — Claude Code
// built on MCP)", "no MCP support advertised — vertical product"), so
// predicates lean on a small `isPositive` classifier that pattern-matches
// the negative-leader phrases used by the extractor. Tuned conservatively
// — false positives are worse than false negatives here.
//
// Pages cap to 80 systems to keep the rendered HTML small. The cap is
// applied AFTER sorting, so the production-grade entries always make the
// page.
//
// IMPORTANT: this is a build-time table — adding a predicate adds a
// prerendered URL to the sitemap. Don't add predicates that resolve to
// fewer than ~15 systems; sparse landing pages dilute crawl signal.

import type { LandscapeRecord } from '$lib/types';

export interface BestOfPredicate {
  slug: string;
  /** <title> tag, also h1. Keep under 60 chars including the count suffix. */
  title: string;
  /** 1-2 sentences. Used as meta description and on-page lede. */
  description: string;
  /** Filter: returns true if the record belongs on this page. */
  match: (r: LandscapeRecord) => boolean;
  /**
   * Optional secondary sort key — applied after tier asc. Smaller is
   * better. Defaults to a stable name-asc.
   */
  rank?: (r: LandscapeRecord) => number;
}

/**
 * Free-text cell-value classifier. Returns true if the value reads as
 * an affirmative claim of support, false for negatives, unknowns, and
 * "searched not found" / "no data" markers. The extractor uses a small
 * set of negative-leader phrases consistently, so prefix matching the
 * leader is the right test (no risk of "no SOC 2" → positive).
 */
function isPositive(v: string | null | undefined): boolean {
  if (!v) return false;
  const s = v.trim().toLowerCase();
  if (s.length < 2) return false;
  if (
    /^(no|not|none|n\/a|never|searched not found|no data|depth-floor|no first-party|no mcp|no a2a|no opentelemetry|no langsmith|no helicone|no datadog|no native|planned|tbd|tba|coming soon|in development|under development|on the roadmap|roadmap)\b/.test(
      s
    )
  ) {
    return false;
  }
  if (
    /^(unsupported|missing|absent|undocumented|not documented|not supported|not advertised)\b/.test(
      s
    )
  ) {
    return false;
  }
  return true;
}

function cellHas(r: LandscapeRecord, slug: string, pat: RegExp): boolean {
  const v = r.cells[slug as keyof typeof r.cells]?.value;
  return !!v && pat.test(v);
}

function cellPositive(r: LandscapeRecord, slug: string): boolean {
  const c = r.cells[slug as keyof typeof r.cells];
  if (!c) return false;
  if (c.status === 'not-applicable' || c.status === 'no-data') return false;
  return isPositive(c.value);
}

/**
 * OSS license families that count as "open source" for these pages.
 * Elastic 2.0 and SSPL are deliberately excluded — they fail the OSI
 * definition and including them would mislead users searching for
 * "open-source agent memory".
 */
const OSS_LICENSE_RE = /\b(apache|mit|bsd|agpl|gpl|lgpl|mpl|mozilla|isc|cc-by|cc0|unlicense)/i;

function isOpenSource(r: LandscapeRecord): boolean {
  const v = r.cells.license?.value;
  if (!v) return false;
  return OSS_LICENSE_RE.test(v);
}

/**
 * "Self-hostable" deployment: any deployment cell that advertises an
 * on-prem, hybrid, or "both" cloud + on-prem option. Excludes managed-
 * only / SaaS-only systems even when the cell is positive.
 */
function isSelfHostable(r: LandscapeRecord): boolean {
  const v = r.cells.deployment?.value;
  if (!v) return false;
  if (/saas only|managed only/i.test(v)) return false;
  return /self-?host|on-?prem|hybrid|\bboth\b/i.test(v);
}

export const PREDICATES: BestOfPredicate[] = [
  {
    slug: 'agent-memory-with-mcp',
    title: 'Agent memory systems with MCP support',
    description:
      'Agent memory systems that integrate with the Model Context Protocol (MCP) — first-party MCP servers, official adapters, and native MCP clients. Ranked by maturity tier.',
    match: (r) => cellPositive(r, 'mcp-support')
  },
  {
    slug: 'agent-memory-with-a2a',
    title: 'Agent memory systems with A2A protocol support',
    description:
      'Agent memory systems that support the Agent2Agent (A2A) protocol for cross-agent communication. Ranked by maturity tier.',
    match: (r) => cellPositive(r, 'a2a-support')
  },
  {
    slug: 'open-source-agent-memory',
    title: 'Open-source agent memory systems',
    description:
      'Agent memory systems published under an OSI-approved open-source license (Apache, MIT, BSD, GPL family, MPL). Ranked by maturity tier — production-grade entries first.',
    match: isOpenSource
  },
  {
    slug: 'self-hostable-agent-memory',
    title: 'Self-hostable agent memory systems',
    description:
      'Agent memory systems that can be deployed on-prem or in your own cloud account — no managed-SaaS lock-in. Ranked by maturity tier.',
    match: isSelfHostable
  },
  {
    slug: 'soc2-compliant-agent-memory',
    title: 'SOC 2 compliant agent memory systems',
    description:
      'Agent memory systems that hold a SOC 2 Type I or Type II attestation. Ranked by maturity tier.',
    match: (r) => cellHas(r, 'compliance', /\bSOC ?2\b/i)
  },
  {
    slug: 'hipaa-compliant-agent-memory',
    title: 'HIPAA compliant agent memory systems',
    description:
      'Agent memory systems suitable for protected health information workloads — HIPAA-aware vendors that sign BAAs. Ranked by maturity tier.',
    match: (r) => cellHas(r, 'compliance', /\bHIPAA\b/i)
  },
  {
    slug: 'gdpr-compliant-agent-memory',
    title: 'GDPR compliant agent memory systems',
    description:
      'Agent memory systems that document GDPR compliance for EU and EEA data subjects. Ranked by maturity tier.',
    match: (r) => cellHas(r, 'compliance', /\bGDPR\b/i)
  },
  {
    slug: 'iso-27001-agent-memory',
    title: 'ISO 27001 certified agent memory systems',
    description:
      'Agent memory systems with an ISO/IEC 27001 information security certification. Ranked by maturity tier.',
    match: (r) => cellHas(r, 'compliance', /\bISO ?27001\b/i)
  },
  {
    slug: 'agent-memory-with-opentelemetry',
    title: 'Agent memory systems with OpenTelemetry support',
    description:
      'Agent memory systems that emit OpenTelemetry traces and spans — open-standard observability that plugs into Tempo, Jaeger, Honeycomb, or any OTel backend. Ranked by maturity tier.',
    match: (r) => cellPositive(r, 'obs-opentelemetry')
  },
  {
    slug: 'agent-memory-with-langsmith',
    title: 'Agent memory systems with LangSmith integration',
    description:
      'Agent memory systems with first-class LangSmith trace export for agent observability. Ranked by maturity tier.',
    match: (r) => cellPositive(r, 'obs-langsmith')
  },
  {
    slug: 'agent-memory-with-datadog',
    title: 'Agent memory systems with Datadog integration',
    description:
      'Agent memory systems with native Datadog integration for production observability. Ranked by maturity tier.',
    match: (r) => cellPositive(r, 'obs-datadog')
  },
  {
    slug: 'agent-memory-with-langfuse',
    title: 'Agent memory systems with Langfuse integration',
    description:
      'Agent memory systems with Langfuse trace and prompt-management integration. Ranked by maturity tier.',
    match: (r) => cellPositive(r, 'obs-langfuse')
  }
];

const BY_SLUG = new Map(PREDICATES.map((p) => [p.slug, p]));

export function bestOfBySlug(slug: string): BestOfPredicate | undefined {
  return BY_SLUG.get(slug);
}

export function allBestOf(): BestOfPredicate[] {
  return PREDICATES;
}
