// Postbuild step: emit /feed.xml — an Atom feed of the 50 most-recently-
// verified systems in the catalog. Lets RSS readers and AI agents
// (ChatGPT, Perplexity, etc.) subscribe to catalog motion.
//
// The freshness signal is record.last_verified_at — written by the
// staleness check and updated whenever a row is re-confirmed. New
// systems show up here on their first verification; re-verified systems
// re-surface in the feed.
//
// Emitted as Atom 1.0 (not RSS 2.0) because Atom's spec for entry IDs,
// updated timestamps, and self-links is unambiguous — better for the
// "feed → embedding → recall" pipeline modern AI readers use.

import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const buildDir = resolve(__dirname, '..', 'build');
const dataFile = resolve(__dirname, '..', '..', 'data', 'landscape.json');

const SITE_ORIGIN = 'https://mrpeppersdev.github.io';
const basePath = process.env.BASE_PATH ?? '';
const baseUrl = `${SITE_ORIGIN}${basePath}`;
const FEED_SIZE = 50;

const landscape = JSON.parse(readFileSync(dataFile, 'utf8'));
const records = landscape.records ?? [];

function cellValue(record, key) {
  const cell = record.cells?.[key];
  if (!cell || typeof cell !== 'object') return '';
  const v = cell.value;
  return typeof v === 'string' ? v : '';
}

function primarySectionOf(record) {
  if (record.primary_section) return record.primary_section;
  const s = (record.sections ?? []).find((s) => s.primary) ?? record.sections?.[0];
  return s?.section ?? '';
}

function xmlEntity(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c])
  );
}

function isoFromDate(d) {
  // last_verified_at is YYYY-MM-DD; widen to a full RFC 3339 stamp.
  if (!d) return '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(d)) return `${d}T00:00:00Z`;
  return d;
}

const ranked = [...records]
  .filter((r) => r.last_verified_at)
  .sort((a, b) => String(b.last_verified_at).localeCompare(String(a.last_verified_at)))
  .slice(0, FEED_SIZE);

const feedUpdated = isoFromDate(ranked[0]?.last_verified_at) || new Date().toISOString();

const entries = ranked
  .map((r) => {
    const url = `${baseUrl}/systems/${r.id}`;
    const updated = isoFromDate(r.last_verified_at);
    const type = cellValue(r, 'type').slice(0, 200);
    const desc = cellValue(r, 'desc').slice(0, 500);
    const section = primarySectionOf(r);
    const summary = [type, section, desc].filter(Boolean).join(' · ');
    return `  <entry>
    <title>${xmlEntity(r.name)}</title>
    <link href="${xmlEntity(url)}" />
    <id>${xmlEntity(url)}</id>
    <updated>${updated}</updated>
    <summary>${xmlEntity(summary)}</summary>
  </entry>`;
  })
  .join('\n');

const feedUrl = `${baseUrl}/feed.xml`;
const xml = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>AI Agent Infrastructure Landscape — recent activity</title>
  <subtitle>The 50 most-recently verified systems in the v6 catalog.</subtitle>
  <link href="${xmlEntity(feedUrl)}" rel="self" />
  <link href="${xmlEntity(baseUrl + '/')}" />
  <id>${xmlEntity(feedUrl)}</id>
  <updated>${feedUpdated}</updated>
  <author><name>Mr. Peppers</name></author>
${entries}
</feed>
`;

const outFile = resolve(buildDir, 'feed.xml');
writeFileSync(outFile, xml);

console.log(`generate-feed: wrote ${ranked.length} entries to ${outFile}`);
