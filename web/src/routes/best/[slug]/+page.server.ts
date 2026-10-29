// Build-time loader for /best/[slug] — long-tail landing pages that
// answer high-intent feature-based queries ("agent memory with MCP",
// "open-source agent memory", "HIPAA agent memory"). Refs #105.
//
// Each predicate from $lib/seo/best-of is a separate prerendered URL.
// The catalog data is the only input; we filter, sort by tier + inbound-
// edge count, cap to 80, and hand a typed projection to the page so the
// rendered HTML stays small.

import { error } from '@sveltejs/kit';
import { getRecords, getEdges } from '$lib/data';
import { allBestOf, bestOfBySlug } from '$lib/seo/best-of';

export const prerender = true;

export interface BestOfSystem {
  id: string;
  name: string;
  tier: 1 | 2 | 3 | 4 | 5;
  type: string | null;
  desc: string;
  inbound: number;
}

export function entries(): { slug: string }[] {
  return allBestOf().map((p) => ({ slug: p.slug }));
}

const MAX_SYSTEMS = 80;

export function load({ params }: { params: { slug: string } }): {
  slug: string;
  title: string;
  description: string;
  systems: BestOfSystem[];
  totalMatches: number;
} {
  const pred = bestOfBySlug(params.slug);
  if (!pred) throw error(404, `Best-of page "${params.slug}" not found`);

  // Inbound-edge count by target id — used as the secondary ranking
  // signal so heavily-cited systems float above siblings at the same
  // tier. Built once per load (cheap given ~3k edges).
  const inbound = new Map<string, number>();
  for (const e of getEdges()) {
    inbound.set(e.target, (inbound.get(e.target) ?? 0) + 1);
  }

  const matched = getRecords().filter(pred.match);
  const totalMatches = matched.length;

  const systems: BestOfSystem[] = matched
    .map((r) => {
      const desc = r.cells.desc?.value?.trim() ?? '';
      return {
        id: r.id,
        name: r.name,
        tier: r.tier,
        type: r.cells.type?.value?.trim() ?? null,
        desc: desc.length > 240 ? desc.slice(0, 237) + '…' : desc,
        inbound: inbound.get(r.id) ?? 0
      };
    })
    .sort((a, b) => {
      if (a.tier !== b.tier) return a.tier - b.tier;
      if (a.inbound !== b.inbound) return b.inbound - a.inbound;
      return a.name.localeCompare(b.name);
    })
    .slice(0, MAX_SYSTEMS);

  return {
    slug: pred.slug,
    title: pred.title,
    description: pred.description,
    systems,
    totalMatches
  };
}
