// Centralised site identity and URL helpers for SEO surfaces (canonical
// links, sitemap, JSON-LD, Open Graph). The Pages deploy lives at:
//   https://mrpeppersdev.github.io/agent-infrastructure-landscape
//
// We deliberately do NOT use `$app/paths.base` here: adapter-static rewrites
// `base` to a relative path ("." or "..") when generating each prerendered
// page so internal asset links resolve from any depth. That's correct for
// asset hrefs but wrong for canonical / OG / sitemap URLs, which must be
// resolvable absolute URLs regardless of which page they appear on. So we
// hardcode the production base path here.
//
// Mirror of these constants lives in web/scripts/generate-sitemap.mjs —
// the sitemap generator runs as a plain Node script outside SvelteKit so
// it cannot import this module. If any of SITE_ORIGIN / SITE_BASE_PATH
// changes, update both.

export const SITE_ORIGIN = 'https://mrpeppersdev.github.io';

export const SITE_BASE_PATH = '/agent-infrastructure-landscape';

export const SITE_URL = `${SITE_ORIGIN}${SITE_BASE_PATH}`;

export const SITE_NAME = 'AI Agent Infrastructure Landscape';

export const SITE_DESCRIPTION =
  'Comparative catalog of AI agent memory systems, frameworks, and research papers — with typed edges, lineages, and benchmark coverage.';

/**
 * Build a resolvable absolute URL from a SvelteKit route path. The path
 * should start with "/" and NOT include the base prefix; this helper
 * handles the stitching.
 *
 * Trailing-slash convention: landing ("/") keeps its slash; inner routes
 * don't — matches the in-app nav links and avoids canonical-URL splits.
 */
export function absoluteUrl(routePath: string): string {
  if (!routePath.startsWith('/')) routePath = `/${routePath}`;
  if (routePath === '/') return `${SITE_URL}/`;
  return `${SITE_URL}${routePath}`;
}

/**
 * Return the absolute URL of the per-route Open Graph SVG previewing
 * this page. The build emits one SVG per prerendered HTML at
 * `build/og/<routePath>.svg` (scripts/generate-og.mjs); the URL
 * convention matches so every page automatically gets a unique preview
 * without per-route wiring. The root path maps to /og/index.svg.
 */
export function ogImageUrl(routePath: string): string {
  if (!routePath.startsWith('/')) routePath = `/${routePath}`;
  const slug = routePath === '/' ? '/index' : routePath;
  return `${SITE_URL}/og${slug}.svg`;
}
