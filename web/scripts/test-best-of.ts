// Every /best/* page is scoped to a product family and lists only rows from
// it (issue #323). Run: npx tsx web/scripts/test-best-of.ts
import { readFileSync } from 'node:fs';
import { allBestOf } from '../src/lib/seo/best-of';
import { familyIdOf, getFamily } from '../src/lib/families';
import type { LandscapeRecord } from '../src/lib/types';

const records = JSON.parse(readFileSync(new URL('../../data/landscape.json', import.meta.url), 'utf-8')).records as LandscapeRecord[];
let failures = 0;
for (const p of allBestOf()) {
  if (!p.family || !getFamily(p.family)) {
    failures++;
    console.error(`FAIL ${p.slug}: no valid family scope (${p.family})`);
    continue;
  }
  const rows = records.filter(p.match);
  const leak = rows.filter((r) => familyIdOf(r) !== p.family);
  if (leak.length) {
    failures++;
    console.error(`FAIL ${p.slug}: ${leak.length} rows outside ${p.family}, e.g. ${leak.slice(0, 3).map((r) => r.name).join(', ')}`);
  }
  console.log(`${p.slug.padEnd(36)} ${rows.length}`);
}
if (failures) {
  console.error(`${failures} best-of test(s) failed`);
  process.exit(1);
}
console.log('all best-of tests passed');
