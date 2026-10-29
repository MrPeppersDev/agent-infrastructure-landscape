// Route weight budget (issue #324): for each prerendered page, sum the
// JavaScript it preloads (<link rel="modulepreload">), uncompressed: that
// is what a phone has to parse. Fails when any page exceeds the budget, so
// a dataset import that leaks into the client bundle breaks the PR check
// instead of the live site. (Prerendered HTML is not counted: the catalog
// table on the home page is large HTML by design, and gzips well.)
//
//   node scripts/check-route-weight.mjs [--budget-mb 3] [--report]

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const BUILD = new URL('../build/', import.meta.url).pathname;

// Pages still known to ship the full dataset to the browser, being slimmed
// one route at a time (#324). Any other page over budget fails; a page in
// this list that comes in under budget fails too, so the list only shrinks.
const KNOWN_HEAVY = [
  'analyses/', 'recommend/', 'sections.html', 'graph.html', 'lineages.html', 'leaderboards.html', 'timeline.html'
];
const known = (page) => KNOWN_HEAVY.some((k) => (k.endsWith('/') ? page.startsWith(k) : page === k));
const args = process.argv.slice(2);
const budgetMb = Number(args[args.indexOf('--budget-mb') + 1]) || 3;
const report = args.includes('--report');

function* htmlFiles(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* htmlFiles(p);
    else if (name.endsWith('.html')) yield p;
  }
}

const sizeCache = new Map();
function sizeOf(file) {
  if (!sizeCache.has(file)) {
    try { sizeCache.set(file, statSync(file).size); } catch { sizeCache.set(file, 0); }
  }
  return sizeCache.get(file);
}

const rows = [];
const seenTemplates = new Set();
for (const file of htmlFiles(BUILD)) {
  const html = readFileSync(file, 'utf-8');
  const js = [...html.matchAll(/<link\b[^>]*>/g)]
    .map((m) => m[0])
    .filter((tag) => /rel="modulepreload"/.test(tag))
    .map((tag) => tag.match(/href="([^"]+)"/)?.[1] ?? '')
    .map((href) => href.replace(/^(\.\.?\/)+/, '').replace(/^\/?agent-infrastructure-landscape\//, ''))
    .filter(Boolean);
  // One page per distinct preload set is enough (e.g. ~950 /systems/* pages share one).
  const key = js.join('|');
  const bytes = js.reduce((n, href) => n + sizeOf(join(BUILD, href)), 0);
  if (seenTemplates.has(key) && bytes < budgetMb * 1e6) continue;
  seenTemplates.add(key);
  rows.push({ page: relative(BUILD, file), bytes });
}
rows.sort((a, b) => b.bytes - a.bytes);
const over = rows.filter((r) => r.bytes > budgetMb * 1e6 && !known(r.page));
const fixed = KNOWN_HEAVY.filter((k) => !rows.some((r) => (k.endsWith('/') ? r.page.startsWith(k) : r.page === k) && r.bytes > budgetMb * 1e6));
const stillHeavy = rows.filter((r) => r.bytes > budgetMb * 1e6 && known(r.page)).length;
const fmt = (b) => `${(b / 1e6).toFixed(2)} MB`;
if (report || over.length) for (const r of rows.slice(0, report ? 25 : over.length)) console.log(`${fmt(r.bytes).padStart(9)}  ${r.page}`);
if (over.length) {
  console.error(`route-weight: ${over.length} page(s) over the ${budgetMb} MB budget`);
  process.exit(1);
}
if (fixed.length) {
  console.error(`route-weight: now under budget, remove from KNOWN_HEAVY: ${fixed.join(', ')}`);
  process.exit(1);
}
const light = rows.filter((r) => !known(r.page));
console.log(`route-weight: every other page under ${budgetMb} MB (heaviest ${light[0]?.page}: ${fmt(light[0]?.bytes ?? 0)}); ${stillHeavy} known-heavy page(s) left (#324)`);
