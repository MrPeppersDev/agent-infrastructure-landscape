// Shared section-name → URL-slug mapping used by both /category/* loaders
// and any cross-link that needs to point at a section landing page.
//
// Section names are stored in the data as title-case strings ("Dedicated
// memory layers") because that's how docs/SCHEMA.md spelled them. For
// URLs we lowercase, ASCII-fold non-alnum characters to hyphens, and
// collapse runs of hyphens. The reverse direction (slug → name) needs an
// O(n) scan of the records, so we expose a helper.

import { getRecords } from '$lib/data';

export function sectionToSlug(name: string): string {
  return name
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

let _sections: { name: string; slug: string }[] | null = null;

export function allSections(): { name: string; slug: string }[] {
  if (_sections) return _sections;
  const seen = new Map<string, string>();
  for (const r of getRecords()) {
    for (const s of r.sections) {
      if (!seen.has(s.section)) seen.set(s.section, sectionToSlug(s.section));
    }
  }
  _sections = [...seen.entries()]
    .map(([name, slug]) => ({ name, slug }))
    .sort((a, b) => a.name.localeCompare(b.name));
  return _sections;
}

export function sectionFromSlug(slug: string): string | null {
  return allSections().find((s) => s.slug === slug)?.name ?? null;
}
