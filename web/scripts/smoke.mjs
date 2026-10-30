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

  await go('/build?product=coding-agent&language=typescript');
  const layers = await texts('.layer h2');
  check('/build shows the coding-agent layers', layers.length >= 7 && layers.some((l) => /sandbox/i.test(l)), JSON.stringify(layers));
  check('/build has picks and a stack.yml', (await texts('.layer .name')).length >= 6 && /components:/.test((await texts('pre.yaml'))[0] ?? ''));
  check('/build maps OWASP risks', (await texts('td.st')).length === 10);

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

  await go('/costs?tab=vector');
  const vusd = await texts('.res .usd');
  check('/costs vector tab prices published vendors', vusd.filter((t) => t.startsWith('$') || t.startsWith('from')).length >= 4, JSON.stringify(vusd));

  await go('/systems/mem0--mem0-ai');
  check('system page has change log', (await page.locator('#changes li').count()) > 0);
  check('system page has correction link', (await page.locator('a[href*="template=correction.yml"]').count()) > 0);

  // Pages fed by slimmed records (#324): they must still render their data.
  await go('/leaderboards');
  check('/leaderboards renders boards', (await page.locator('tbody tr').count()) >= 30);
  await go('/timeline');
  check('/timeline draws bars', (await page.locator('svg rect').count()) >= 50);
  await go('/lineages');
  check('/lineages lists lineages', (await page.locator('li').count()) >= 10);
  await go('/graph');
  await page.waitForTimeout(1500);
  check('/graph mounts the canvas', (await page.locator('canvas').count()) >= 1);

  await go('/');
  await page.locator('nav.topnav summary').click();
  check('Research menu opens', await page.locator('nav.topnav .menu').isVisible());
  await page.evaluate(() => document.body.dispatchEvent(new MouseEvent('click', { bubbles: true })));
  check('Research menu closes on an outside click (#328)', !(await page.locator('nav.topnav .menu').isVisible()));

  // #328: layout at desktop width.
  await page.setViewportSize({ width: 1440, height: 900 });
  await go('/costs');
  const overflow = await page.evaluate(() => [...document.querySelectorAll('form.w label')].filter((l) => {
    const i = l.querySelector('input'); return i && i.getBoundingClientRect().right > l.getBoundingClientRect().right + 1;
  }).length);
  check('/costs inputs stay inside their fields at 1440px', overflow === 0, `${overflow} overflowing`);
  await go('/?view=full');
  const sticky = await page.evaluate(() => {
    const sc = [...document.querySelectorAll('*')].find((e) => e.scrollWidth > e.clientWidth + 50 && ['auto', 'scroll'].includes(getComputedStyle(e).overflowX));
    if (sc) sc.scrollLeft = 700;
    const td = document.querySelector('.row td.sticky-col');
    return td ? getComputedStyle(td).backgroundColor : 'none';
  });
  await page.locator('.row td.sticky-col').first().hover();
  const hoverBg = await page.evaluate(() => getComputedStyle(document.querySelector('.row td.sticky-col')).backgroundColor);
  const opaque = (c) => !/rgba\([^)]*,\s*0?\.\d+\)|transparent/.test(c);
  check('sticky name column stays opaque when scrolled and hovered', opaque(sticky) && opaque(hoverBg), `${sticky} / ${hoverBg}`);
  // #330: the memory taxonomy shows on memory rows only.
  const taxCells = () => page.evaluate(() => {
    const cells = [...document.querySelectorAll('.row td[data-col="tax:storage"]')];
    return { pills: cells.filter((td) => td.querySelector('.tax-pill')).length, na: cells.filter((td) => td.querySelector('.na')).length };
  });
  const memTax = await taxCells();
  await go('/?product=agents&view=full');
  await page.locator('.row').first().waitFor();
  const agentTax = await taxCells();
  check('taxonomy columns: pills on memory rows, n/a on framework rows', memTax.pills > 0 && agentTax.pills === 0 && agentTax.na > 0, JSON.stringify({ memTax, agentTax }));

  // #331: compact default view, lifecycle column and filter, system-page banner.
  await page.setViewportSize({ width: 1440, height: 900 });
  await go('/');
  const rowH = await page.evaluate(() => document.querySelector('.row')?.getBoundingClientRect().height ?? 0);
  check('compact rows fit about 20 to a 900px screen', rowH > 0 && rowH <= 40, `${rowH}px`);
  check('compact view has a Status column', (await page.locator('.row td[data-col="lifecycle"] .life').count()) > 0);
  await go('/?lifecycle=archived');
  const lives = await texts('.row td[data-col="lifecycle"]');
  check('?lifecycle=archived shows only archived rows', lives.length > 0 && lives.every((t) => t === 'Archived'), lives.slice(0, 3).join(', '));
  await go('/systems/bytebot--bytebot-ai');
  check('archived system page shows the lifecycle banner', (await page.locator('.life-banner').count()) === 1);
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
