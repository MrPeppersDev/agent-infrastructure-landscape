// Linkify catalog-system names mentioned in long-form prose so that
// findings (and similar narrative pages) gain "for free" internal links
// to /systems/[slug] without anyone hand-curating them.
//
// Used by the per-finding page (refs #105). The matching policy is
// conservative on purpose — false-positive links hurt CTR and look
// spammy:
//
//   - Match catalog NAMES, not slugs.
//   - Names shorter than 4 chars are skipped (avoids "GPT", "MCP" — too
//     generic to disambiguate).
//   - Whole-word matches only (no substrings).
//   - Case-insensitive but case-preserving (the linked text matches the
//     original casing in the prose).
//   - Sorted-by-length-desc so the longest match wins ("Graphiti MCP
//     Server" beats "Graphiti", and the substring is consumed).
//   - At most one link per system per paragraph, so popular names like
//     "Claude" don't get linked five times in the same paragraph.

import type { LandscapeRecord } from '$lib/types';

export type LinkifySegment =
  | { kind: 'text'; text: string }
  | { kind: 'link'; text: string; href: string };

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Strip parenthetical or em-dash-trailing qualifier from a catalog name so
 * prose mentions match. The catalog uses "Cursor (IDE)" or
 * "Graphiti MCP Server (Zep)" for disambiguation, but the finding bodies
 * say "Cursor" / "Graphiti MCP Server" — without cleaning, those would
 * never link.
 */
function cleanName(name: string): string {
  let n = name.replace(/\s*\([^)]*\)\s*$/, '').trim();
  n = n.replace(/\s*[—–]\s*.+$/, '').trim();
  return n;
}

/**
 * Build a reusable name → id index, sorted by candidate length descending
 * so the longest match always runs first. Both the raw catalog name and
 * its cleaned form (parenthetical/em-dash stripped) become candidates so
 * prose mentions in either style get linked.
 *
 * Cleaned names that collide (two records cleaning to the same string)
 * are dropped — we'd link to one and silently miss the other, which is
 * worse than not linking at all.
 */
export function buildNameIndex(
  records: LandscapeRecord[],
  minLen = 4
): { name: string; id: string; re: RegExp }[] {
  // First pass: collect every candidate (raw + cleaned) per record, then
  // count how many records each cleaned candidate resolves to.
  const candidatesByRecord: { id: string; cands: string[] }[] = [];
  const cleanedCounts = new Map<string, number>();

  for (const r of records) {
    const raw = r.name?.trim();
    if (!raw) continue;
    const cleaned = cleanName(raw);
    const cands: string[] = [];
    if (raw.length >= minLen) cands.push(raw);
    if (cleaned !== raw && cleaned.length >= minLen) cands.push(cleaned);
    if (cands.length) candidatesByRecord.push({ id: r.id, cands });
    if (cleaned !== raw && cleaned.length >= minLen) {
      cleanedCounts.set(cleaned.toLowerCase(), (cleanedCounts.get(cleaned.toLowerCase()) ?? 0) + 1);
    }
  }

  // Second pass: emit each candidate, dropping cleaned forms that collide
  // across records to keep linking unambiguous.
  const seen = new Set<string>();
  const out: { name: string; id: string; re: RegExp }[] = [];
  for (const { id, cands } of candidatesByRecord) {
    for (const c of cands) {
      const key = c.toLowerCase();
      if (seen.has(key)) continue;
      if ((cleanedCounts.get(key) ?? 0) > 1) continue;
      seen.add(key);
      out.push({
        name: c,
        id,
        // \b doesn't play well with names that include punctuation (e.g.
        // "11x.ai"), so we use lookarounds anchored to non-word boundaries.
        re: new RegExp(`(?<![\\w-])${escapeRegex(c)}(?![\\w-])`, 'i')
      });
    }
  }
  return out.sort((a, b) => b.name.length - a.name.length);
}

/**
 * Linkify a single paragraph. Returns an ordered list of segments where
 * link segments carry an internal href (no base prefix — the caller
 * prepends it).
 */
export function linkifyParagraph(
  text: string,
  index: { name: string; id: string; re: RegExp }[]
): LinkifySegment[] {
  // Internal representation is a mix of strings and emitted links.
  // Each name walks the current token list once, splitting strings on
  // its first match, and is then removed from contention for the rest
  // of this paragraph (one-link-per-name policy).
  let tokens: LinkifySegment[] = [{ kind: 'text', text }];

  for (const { id, re } of index) {
    const next: LinkifySegment[] = [];
    let matched = false;
    for (const tok of tokens) {
      if (matched || tok.kind !== 'text') {
        next.push(tok);
        continue;
      }
      const m = tok.text.match(re);
      if (!m || m.index === undefined) {
        next.push(tok);
        continue;
      }
      matched = true;
      if (m.index > 0) {
        next.push({ kind: 'text', text: tok.text.slice(0, m.index) });
      }
      next.push({
        kind: 'link',
        text: m[0],
        href: `/systems/${id}`
      });
      const rest = tok.text.slice(m.index + m[0].length);
      if (rest) next.push({ kind: 'text', text: rest });
    }
    tokens = next;
  }
  return tokens;
}
