// Postbuild link validator: walks build/*.html, extracts href values, and
// reports broken internal links or links to bare hosts. The point is to
// fail the build before a regression like the broken `https://github.com/`
// (no path) ships to GitHub Pages.
//
// What we check:
//   1. Internal links — every `/agent-infrastructure-landscape/...` href must
//      resolve to a real file in build/.
//   2. Bare-host externals on multi-tenant hosts — e.g. `https://github.com/`
//      with no path. For these hosts the path identifies the resource, so an
//      empty path is always a regression. Vendor homepages like
//      `https://www.01.ai/` are intentional and are NOT flagged.
//
// Exits non-zero on any failure so CI catches it.

import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const BUILD_DIR = resolve(ROOT, 'build');
const BASE_PATH = process.env.BASE_PATH ?? '/agent-infrastructure-landscape';

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) walk(full, out);
    else out.push(full);
  }
  return out;
}

function stripQueryHash(p) {
  const hashIdx = p.indexOf('#');
  if (hashIdx >= 0) p = p.slice(0, hashIdx);
  const qIdx = p.indexOf('?');
  if (qIdx >= 0) p = p.slice(0, qIdx);
  return p;
}

function checkBuildPath(relPath) {
  // SvelteKit prerender emits either `<route>.html` or `<route>/index.html`.
  // Also accept exact asset matches (sitemap.xml, feed.xml, etc.).
  if (relPath === '' || relPath === '/') {
    return existsSync(join(BUILD_DIR, 'index.html'));
  }
  if (relPath.endsWith('/')) relPath = relPath.slice(0, -1);

  if (/\.[a-z0-9]+$/i.test(relPath)) {
    return existsSync(join(BUILD_DIR, relPath));
  }
  return (
    existsSync(join(BUILD_DIR, `${relPath}.html`)) ||
    existsSync(join(BUILD_DIR, relPath, 'index.html'))
  );
}

function resolveInternal(href, fromFile) {
  // Returns: true (resolves), false (broken), null (out of scope — skip).
  let path = stripQueryHash(href);
  if (path === '') return null;

  // Absolute URL — check whether it's our own site and resolve into build/.
  if (/^https?:\/\//i.test(path)) {
    return null; // handled by the external-link path
  }

  if (path.startsWith('/')) {
    // Absolute path. Must be under BASE_PATH to be ours.
    if (!path.startsWith(BASE_PATH)) return null;
    let rel = path.slice(BASE_PATH.length);
    if (rel.startsWith('/')) rel = rel.slice(1);
    return checkBuildPath(rel);
  }

  // Relative path — resolve against the directory of the file containing it.
  const fromDir = dirname(fromFile);
  const abs = resolve(fromDir, path);
  if (!abs.startsWith(BUILD_DIR)) return false; // escaped the build dir
  let rel = abs.slice(BUILD_DIR.length);
  if (rel.startsWith('/')) rel = rel.slice(1);
  return checkBuildPath(rel);
}

const HREF_RE = /href\s*=\s*"([^"]+)"/gi;

// Hosts where the path identifies the resource — an empty path is always a
// bug. Vendor homepages live elsewhere; flagging those would be noise.
const MULTI_TENANT_HOSTS = new Set([
  'github.com',
  'www.github.com',
  'gitlab.com',
  'www.gitlab.com',
  'bitbucket.org',
  'npmjs.com',
  'www.npmjs.com',
  'pypi.org',
  'huggingface.co',
  'hf.co',
  'arxiv.org',
  'twitter.com',
  'x.com',
  'linkedin.com',
  'www.linkedin.com',
  'medium.com',
  'dev.to',
  'news.ycombinator.com'
]);

const errors = [];
let totalLinks = 0;
let totalInternal = 0;

const files = walk(BUILD_DIR).filter((f) => f.endsWith('.html'));
for (const file of files) {
  const rel = file.slice(BUILD_DIR.length + 1);
  // 404.html is hand-authored; its links are still useful to validate but
  // it isn't reachable via crawl. We validate it like the others.
  const html = readFileSync(file, 'utf8');
  let m;
  HREF_RE.lastIndex = 0;
  while ((m = HREF_RE.exec(html)) !== null) {
    const href = m[1].trim();
    totalLinks++;

    // Skip non-resolvable schemes and anchor-only links.
    if (
      href.startsWith('mailto:') ||
      href.startsWith('tel:') ||
      href.startsWith('javascript:') ||
      href.startsWith('data:') ||
      href.startsWith('#')
    ) {
      continue;
    }

    // Bare-host externals on multi-tenant hosts: e.g. `https://github.com/`
    // with no path is always a regression because the path identifies the
    // resource. Vendor homepages with empty paths are intentional and not
    // flagged.
    if (/^https?:\/\//i.test(href)) {
      try {
        const u = new URL(href);
        if (
          MULTI_TENANT_HOSTS.has(u.hostname.toLowerCase()) &&
          (u.pathname === '/' || u.pathname === '')
        ) {
          errors.push(`${rel}: bare-host link "${href}" on multi-tenant host (no resource path)`);
        }
      } catch {
        errors.push(`${rel}: malformed URL "${href}"`);
      }
      continue;
    }

    // Anything else is internal — relative or absolute path. Resolve and
    // check whether the target exists in build/.
    totalInternal++;
    const ok = resolveInternal(href, file);
    if (ok === false) {
      errors.push(`${rel}: broken internal link "${href}"`);
    } else if (ok === null && href.startsWith('/')) {
      // Absolute path that doesn't start with BASE_PATH — usually a bug.
      errors.push(`${rel}: absolute link "${href}" outside BASE_PATH ${BASE_PATH}`);
    }
  }
}

if (errors.length) {
  // Collapse duplicates (a bad link in the layout appears on every page).
  const counts = new Map();
  for (const e of errors) counts.set(e, (counts.get(e) ?? 0) + 1);
  const unique = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  console.error(
    `validate-links: ${errors.length} broken hrefs across ${files.length} files (${unique.length} unique)`
  );
  for (const [msg, n] of unique.slice(0, 50)) {
    console.error(`  [${n}×] ${msg}`);
  }
  if (unique.length > 50) {
    console.error(`  … and ${unique.length - 50} more unique errors`);
  }
  process.exit(1);
}

console.log(
  `validate-links: ${totalLinks} hrefs scanned, ${totalInternal} internal, ${files.length} HTML files, 0 broken`
);
