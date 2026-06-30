// Postbuild step: scan web/build/ for prerendered .html files and emit
// sitemap.xml at the build root so sync-to-docs.mjs picks it up.
//
// Single-source-of-truth approach: rather than enumerate routes by hand
// (which drifts as new parametric routes are added), we walk the actual
// vite-built output. Anything SvelteKit prerendered shows up in the
// sitemap; anything that 404s does not.
//
// BASE_PATH is read from env (matches pages.yml). For local dev (no
// BASE_PATH) URLs go to the bare origin; the sitemap is mostly consumed
// in production so that's fine.
//
// Mirror of SITE_ORIGIN lives in web/src/lib/site.ts — keep in sync.

import { readdirSync, writeFileSync, statSync } from 'node:fs';
import { resolve, dirname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const buildDir = resolve(__dirname, '..', 'build');

const SITE_ORIGIN = 'https://mrpeppersdev.github.io';
const basePath = process.env.BASE_PATH ?? '';
const baseUrl = `${SITE_ORIGIN}${basePath}`;
const today = new Date().toISOString().slice(0, 10);

function* walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    // Skip Vite/SvelteKit internals — _app contains hashed JS/CSS, not routes.
    if (entry.name === '_app') continue;
    if (entry.name.startsWith('.')) continue;
    const full = resolve(dir, entry.name);
    if (entry.isDirectory()) {
      yield* walk(full);
    } else if (entry.name.endsWith('.html')) {
      yield full;
    }
  }
}

const htmlFiles = [...walk(buildDir)];

const routes = htmlFiles
  .map((f) => {
    let rel = f.slice(buildDir.length);
    if (sep !== '/') rel = rel.replaceAll(sep, '/');
    // adapter-static (trailingSlash: 'never') emits "/about.html" for
    // leaf routes and "/findings/index.html" for routes with children.
    // Both must collapse to the clean form used by SeoHead's canonical.
    rel = rel.replace(/\/index\.html$/, '').replace(/\.html$/, '');
    return rel || '/';
  })
  .sort();

function xmlEntity(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c])
  );
}

const urlEntries = routes
  .map((path) => {
    const fullUrl = `${baseUrl}${path}`;
    return `  <url>
    <loc>${xmlEntity(fullUrl)}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>weekly</changefreq>
  </url>`;
  })
  .join('\n');

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urlEntries}
</urlset>
`;

const outFile = resolve(buildDir, 'sitemap.xml');
writeFileSync(outFile, xml);

console.log(`generate-sitemap: wrote ${routes.length} URLs to ${outFile}`);
