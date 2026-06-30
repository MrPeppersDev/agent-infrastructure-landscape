// Build-time loader for per-finding article pages. Refs #105.
// Each of the five findings becomes its own crawlable, citable page.

import { error } from '@sveltejs/kit';
import { findings, findingBySlug, type Finding } from '$lib/findings';
import { getRecords } from '$lib/data';
import { buildNameIndex, linkifyParagraph, type LinkifySegment } from '$lib/seo/linkify';

export const prerender = true;

export function entries(): { slug: string }[] {
  return findings.map((f) => ({ slug: f.slug }));
}

export function load({ params }: { params: { slug: string } }): {
  finding: Finding;
  body: LinkifySegment[][];
  others: Finding[];
} {
  const finding = findingBySlug(params.slug);
  if (!finding) throw error(404, `Finding "${params.slug}" not found`);

  // Build the name index from the full catalog, then linkify each
  // paragraph at load time so the prerendered HTML carries real anchor
  // tags (no client JS, no hydration cost). Each linked system name
  // becomes a free internal link the SEO graph will count.
  const index = buildNameIndex(getRecords());
  const body = finding.body.map((para) => linkifyParagraph(para, index));

  // Sibling findings for the "more findings" footer; keeps the in-section
  // linking graph tight.
  const others = findings.filter((f) => f.slug !== finding.slug);

  return { finding, body, others };
}
