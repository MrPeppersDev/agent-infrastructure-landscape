// Postbuild structured-data validator: walks build/*.html, extracts every
// `<script type="application/ld+json">` block, parses it as JSON, and runs
// a minimal schema.org validation pass. Fails the build on any invalid
// block so a regression like a missing `@type` or malformed
// BreadcrumbList doesn't reach the Pages deploy.
//
// We deliberately don't pull in a full schema.org validator (a few MB and
// constant churn). The checks below are the ones Google flags as errors
// in Search Console for our actual emitted types, plus generic JSON /
// shape correctness.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const BUILD_DIR = resolve(ROOT, 'build');

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) walk(full, out);
    else out.push(full);
  }
  return out;
}

const LD_RE = /<script\s+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi;

const errors = [];
let totalBlocks = 0;
const typesSeen = new Map();

function bump(t) {
  typesSeen.set(t, (typesSeen.get(t) ?? 0) + 1);
}

function checkBreadcrumbList(rel, obj) {
  const items = obj.itemListElement;
  if (!Array.isArray(items) || items.length === 0) {
    errors.push(`${rel}: BreadcrumbList missing itemListElement array`);
    return;
  }
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    if (it?.['@type'] !== 'ListItem') {
      errors.push(`${rel}: BreadcrumbList[${i}] not a ListItem`);
    }
    if (it?.position !== i + 1) {
      errors.push(`${rel}: BreadcrumbList[${i}] position should be ${i + 1}, got ${it?.position}`);
    }
    if (!it?.name) errors.push(`${rel}: BreadcrumbList[${i}] missing name`);
    if (!it?.item) errors.push(`${rel}: BreadcrumbList[${i}] missing item URL`);
  }
}

function checkFaqPage(rel, obj) {
  const qas = obj.mainEntity;
  if (!Array.isArray(qas) || qas.length === 0) {
    errors.push(`${rel}: FAQPage missing mainEntity array`);
    return;
  }
  for (let i = 0; i < qas.length; i++) {
    const q = qas[i];
    if (q?.['@type'] !== 'Question') {
      errors.push(`${rel}: FAQPage Q&A[${i}] not a Question`);
    }
    if (!q?.name) errors.push(`${rel}: FAQPage Q&A[${i}] missing question text (name)`);
    const ans = q?.acceptedAnswer;
    if (ans?.['@type'] !== 'Answer') {
      errors.push(`${rel}: FAQPage Q&A[${i}] acceptedAnswer not an Answer`);
    }
    if (!ans?.text) errors.push(`${rel}: FAQPage Q&A[${i}] missing answer text`);
  }
}

function checkItemList(rel, obj) {
  const items = obj.itemListElement;
  if (!Array.isArray(items) || items.length === 0) {
    errors.push(`${rel}: ItemList missing itemListElement array`);
    return;
  }
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    if (it?.['@type'] !== 'ListItem') {
      errors.push(`${rel}: ItemList[${i}] not a ListItem`);
    }
    if (typeof it?.position !== 'number') {
      errors.push(`${rel}: ItemList[${i}] missing position number`);
    }
  }
}

function checkArticle(rel, obj) {
  if (!obj.headline) errors.push(`${rel}: Article missing headline`);
  if (!obj.url) errors.push(`${rel}: Article missing url`);
}

function checkSoftwareApplication(rel, obj) {
  if (!obj.name) errors.push(`${rel}: SoftwareApplication missing name`);
  if (!obj.url) errors.push(`${rel}: SoftwareApplication missing url`);
}

function checkDataset(rel, obj) {
  if (!obj.name) errors.push(`${rel}: Dataset missing name`);
  if (!obj.url) errors.push(`${rel}: Dataset missing url`);
  if (!obj.license) errors.push(`${rel}: Dataset missing license`);
}

function checkWebSite(rel, obj) {
  if (!obj.url) errors.push(`${rel}: WebSite missing url`);
  if (!obj.name) errors.push(`${rel}: WebSite missing name`);
  if (obj.potentialAction) {
    const pa = obj.potentialAction;
    if (pa['@type'] !== 'SearchAction') {
      errors.push(`${rel}: WebSite potentialAction not a SearchAction`);
    }
    if (!pa['query-input']) {
      errors.push(`${rel}: WebSite SearchAction missing query-input`);
    }
    const tgt = pa.target;
    const tgtUrl =
      typeof tgt === 'string' ? tgt : tgt?.urlTemplate ?? null;
    if (!tgtUrl || !tgtUrl.includes('{search_term_string}')) {
      errors.push(`${rel}: WebSite SearchAction target missing {search_term_string} placeholder`);
    }
  }
}

function checkOrganization(rel, obj) {
  if (!obj.name) errors.push(`${rel}: Organization missing name`);
  if (!obj.url) errors.push(`${rel}: Organization missing url`);
}

const TYPE_CHECKERS = {
  BreadcrumbList: checkBreadcrumbList,
  FAQPage: checkFaqPage,
  ItemList: checkItemList,
  Article: checkArticle,
  SoftwareApplication: checkSoftwareApplication,
  Dataset: checkDataset,
  WebSite: checkWebSite,
  Organization: checkOrganization
};

function checkBlock(rel, obj) {
  if (!obj || typeof obj !== 'object') {
    errors.push(`${rel}: JSON-LD block not an object`);
    return;
  }
  if (obj['@context'] !== 'https://schema.org') {
    errors.push(`${rel}: missing or wrong @context (expected "https://schema.org")`);
  }
  const t = obj['@type'];
  if (!t) {
    errors.push(`${rel}: JSON-LD block missing @type`);
    return;
  }
  bump(t);
  const checker = TYPE_CHECKERS[t];
  if (checker) checker(rel, obj);
}

const files = walk(BUILD_DIR).filter((f) => f.endsWith('.html'));
for (const file of files) {
  const rel = file.slice(BUILD_DIR.length + 1);
  const html = readFileSync(file, 'utf8');
  let m;
  LD_RE.lastIndex = 0;
  while ((m = LD_RE.exec(html)) !== null) {
    totalBlocks++;
    let parsed;
    try {
      parsed = JSON.parse(m[1]);
    } catch (e) {
      errors.push(`${rel}: invalid JSON in JSON-LD block — ${e.message}`);
      continue;
    }
    if (Array.isArray(parsed)) {
      for (const item of parsed) checkBlock(rel, item);
    } else {
      checkBlock(rel, parsed);
    }
  }
}

if (errors.length) {
  const counts = new Map();
  for (const e of errors) counts.set(e, (counts.get(e) ?? 0) + 1);
  const unique = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  console.error(
    `validate-jsonld: ${errors.length} errors across ${files.length} files (${unique.length} unique)`
  );
  for (const [msg, n] of unique.slice(0, 50)) {
    console.error(`  [${n}×] ${msg}`);
  }
  if (unique.length > 50) {
    console.error(`  … and ${unique.length - 50} more unique errors`);
  }
  process.exit(1);
}

const summary = [...typesSeen.entries()]
  .sort((a, b) => b[1] - a[1])
  .map(([t, n]) => `${t}=${n}`)
  .join(', ');
console.log(
  `validate-jsonld: ${totalBlocks} JSON-LD blocks across ${files.length} files, 0 errors. Types: ${summary}`
);
