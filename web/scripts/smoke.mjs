// Browser smoke test for the interactive pages: serves web/build over HTTP
// (honouring BASE_PATH) and drives each page in headless Chromium, failing
// on uncaught page errors or on missing results. Run after `npm run build`:
//   BASE_PATH=/agent-infrastructure-landscape node scripts/smoke.mjs
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const BUILD = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'build');
const BASE = process.env.BASE_PATH ?? '';
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.xml': 'application/xml', '.svg': 'image/svg+xml', '.png': 'image/png', '.csv': 'text/csv', '.txt': 'text/plain' };

const server = createServer(async (req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (BASE && p.startsWith(BASE)) p = p.slice(BASE.length) || '/';
  const tries = [join(BUILD, p), join(BUILD, p + '.html'), join(BUILD, p, 'index.html')];
  for (const f of tries) {
    try {
      if ((await stat(f)).isFile()) {
        res.writeHead(200, { 'content-type': TYPES[extname(f)] ?? 'application/octet-stream' });
        return res.end(await readFile(f));
      }
    } catch { /* next */ }
  }
  res.writeHead(404, { 'content-type': 'text/html' });
  res.end(await readFile(join(BUILD, '404.html')).catch(() => 'not found'));
});
await new Promise((r) => server.listen(0, r));
const ORIGIN = `http://127.0.0.1:${server.address().port}${BASE}`;

let failures = 0;
const check = (name, ok, detail = '') => {
  console.log(`  ${ok ? 'PASS' : 'FAIL'} ${name}${ok ? '' : ' — ' + detail}`);
  if (!ok) failures++;
};

const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(`${page.url()}: ${e.message}`));
const go = async (path) => {
  await page.goto(ORIGIN + path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
};
const texts = async (sel) => (await page.locator(sel).allTextContents()).map((s) => s.replace(/\s+/g, ' ').trim());

try {
  await go('/search?q=' + encodeURIComponent('self-hosted vector db with MCP, python'));
  await page.waitForSelector('.hits li', { timeout: 15000 }).catch(() => {});
  const hits = await texts('.hits li .name');
  check('/search returns ranked hits', hits.length > 0, JSON.stringify(hits));

  await go('/compatibility?ids=mem0--mem0-ai,qdrant--qdrant-tech,neo4j--neo4j-com');
  const pairs = await texts('.pairs > li .head');
  check('/compatibility shows 3 pairs', pairs.length === 3, JSON.stringify(pairs));
  check('/compatibility: Mem0 + Qdrant documented', pairs.some((p) => /Documented/.test(p) && /Mem0/.test(p) && /Qdrant/.test(p)), JSON.stringify(pairs));

  await go('/compare/many?ids=mem0--mem0-ai,qdrant--qdrant-tech');
  await page.waitForSelector('thead th a', { timeout: 15000 }).catch(() => {});
  check('/compare/many loads both systems', (await texts('thead th a')).length === 2);

  await go('/check#deps=npm:flowise,pypi:mem0ai,pypi:kuzu');
  const findings = await texts('.finding .head');
  check('/check permalink restores the result', findings.length >= 2, JSON.stringify(findings));
  check('/check links migration notes', (await page.locator('a[href*="#migrate"]').count()) > 0);

  await go('/choose/framework');
  check('/choose/framework has picks', (await texts('.picks .name')).length > 0);
  await go('/choose/data?existing=true');
  const dataPicks = await texts('.picks .name');
  check('/choose/data honours ?existing', dataPicks.length > 0 && /pgvector|postgres|mongo|elastic|redis|supabase/i.test(dataPicks[0]), JSON.stringify(dataPicks));
  await page.locator('nav.tabs a', { hasText: 'Agent framework' }).click();
  await page.waitForTimeout(500);
  check('chooser tabs switch kind', /framework/.test(page.url()) && (await texts('h1'))[0]?.includes('framework'));

  await go('/choose');
  const boxes = page.locator('td.cmp input');
  await boxes.nth(0).check();
  await boxes.nth(1).check();
  check('/choose compare bar appears', (await page.locator('.bar a.go').count()) === 1);

  await go('/costs?users=50');
  const usd = await texts('.res .usd');
  check('/costs estimates every vendor', usd.length >= 5, JSON.stringify(usd));

  await go('/systems/mem0--mem0-ai');
  check('system page has change log', (await page.locator('#changes li').count()) > 0);
  check('system page has correction link', (await page.locator('a[href*="template=correction.yml"]').count()) > 0);

  await go('/');
  await page.locator('nav.topnav summary').click();
  check('Research menu opens', await page.locator('nav.topnav .menu').isVisible());
} finally {
  await browser.close();
  server.close();
}
check('no uncaught page errors', errors.length === 0, errors.slice(0, 5).join(' | '));
if (failures) {
  console.error(`smoke: ${failures} failure(s)`);
  process.exit(1);
}
console.log('smoke: all passed');
