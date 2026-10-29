// URL slug helpers for section and comparison pages. Kept free of any
// catalog import so client components can use them without pulling the
// dataset into the browser bundle (issue #324).

export function sectionToSlug(name: string): string {
  return name
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

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
