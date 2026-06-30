// Build-time loader for per-finding article pages. Refs #105.
// Each of the five findings becomes its own crawlable, citable page.

import { error } from '@sveltejs/kit';
import { findings, findingBySlug } from '$lib/findings';

export const prerender = true;

export function entries(): { slug: string }[] {
  return findings.map((f) => ({ slug: f.slug }));
}

export function load({ params }: { params: { slug: string } }) {
  const finding = findingBySlug(params.slug);
  if (!finding) throw error(404, `Finding "${params.slug}" not found`);

  // Sibling findings for the "more findings" footer; keeps the in-section
  // linking graph tight.
  const others = findings.filter((f) => f.slug !== finding.slug);

  return { finding, others };
}
