// Comparison-pair mining for /compare/[pair].
//
// Two sources of pairs:
//   1. Every "competes-with" edge in the catalog. The catalog explicitly
//      says these systems compete, so a comparison page is warranted.
//   2. Top-5 most-referenced T1 systems within each primary section,
//      then every pair among that top-5. Caps the universe at ~10 pairs
//      per section so we don't ship 1700+ near-duplicate pages, while
//      still covering the realistic high-intent queries (mem0 vs letta,
//      pinecone vs weaviate, langchain vs llamaindex, …).
//
// Each pair has a single canonical slug: `${a}--vs--${b}` with ids in
// lexicographic order, so the reverse lookup is always a single page.

import { getRecords, getEdges } from '$lib/data';
import type { LandscapeRecord } from '$lib/types';

export type Pair = { a: string; b: string; reason: 'competes-with' | 'top-in-section'; section?: string };

export function pairToSlug(a: string, b: string): string {
  const [x, y] = [a, b].sort();
  return `${x}--vs--${y}`;
}

export function pairFromSlug(slug: string): { a: string; b: string } | null {
  const parts = slug.split('--vs--');
  if (parts.length !== 2 || !parts[0] || !parts[1]) return null;
  const [a, b] = parts.sort();
  return { a, b };
}

let _pairs: Pair[] | null = null;

export function allPairs(): Pair[] {
  if (_pairs) return _pairs;
  const records = getRecords();
  const edges = getEdges();

  // Inbound-edge count is our cheap "do people reference this?" signal.
  const incoming = new Map<string, number>();
  for (const e of edges) incoming.set(e.target, (incoming.get(e.target) ?? 0) + 1);

  // Bucket T1 records by primary section.
  const bySection = new Map<string, LandscapeRecord[]>();
  for (const r of records) {
    if (r.tier !== 1) continue;
    const p = r.sections.find((s) => s.primary);
    if (!p) continue;
    if (!bySection.has(p.section)) bySection.set(p.section, []);
    bySection.get(p.section)!.push(r);
  }

  const seen = new Set<string>();
  const out: Pair[] = [];

  // Pass 1: top-in-section pairs.
  for (const [section, group] of bySection) {
    const ranked = [...group].sort((a, b) => {
      const da = incoming.get(b.id) ?? 0;
      const sa = incoming.get(a.id) ?? 0;
      if (da !== sa) return da - sa;
      return a.name.localeCompare(b.name);
    });
    const top = ranked.slice(0, 5);
    for (let i = 0; i < top.length; i++) {
      for (let j = i + 1; j < top.length; j++) {
        const slug = pairToSlug(top[i].id, top[j].id);
        if (seen.has(slug)) continue;
        seen.add(slug);
        const [a, b] = [top[i].id, top[j].id].sort();
        out.push({ a, b, reason: 'top-in-section', section });
      }
    }
  }

  // Pass 2: explicit competes-with edges.
  for (const e of edges) {
    if (e.type !== 'competes-with') continue;
    const slug = pairToSlug(e.source, e.target);
    if (seen.has(slug)) continue;
    seen.add(slug);
    const [a, b] = [e.source, e.target].sort();
    out.push({ a, b, reason: 'competes-with' });
  }

  _pairs = out;
  return out;
}
