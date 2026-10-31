// Tests for composer.ts (whole-stack composer) and the stack.yml path in
// stack-check.ts, against the real catalog. Assertions are invariants
// (honesty rules, requirements, round-trips), not specific picks, so they
// hold as the catalog changes.
// Run: npm run build && node dist/test-composer.js
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { toItem, type ChooserItem } from './chooser.js';
import { setAliases } from './compat.js';
import { planStack, slimPlan, toOpml, PRODUCTS, LAYER_BY_ID, type ProductType, type StackAnswers } from './composer.js';
import { checkManifest, parseManifest } from './stack-check.js';

const here = dirname(fileURLToPath(import.meta.url));
function find(name: string): string {
  let dir = here;
  for (let i = 0; i < 6; i++) {
    for (const p of [join(dir, 'data', name), join(dir, name), join(dir, 'taxonomy', name)]) {
      try { readFileSync(p); return p; } catch { /* next */ }
    }
    dir = dirname(dir);
  }
  throw new Error(`${name} not found`);
}
const L = JSON.parse(readFileSync(find('landscape.json'), 'utf-8'));
const E = JSON.parse(readFileSync(find('landscape.edges.json'), 'utf-8')).edges;
const INDEX = JSON.parse(readFileSync(find('stack-index.json'), 'utf-8'));
setAliases(JSON.parse(readFileSync(find('system-aliases.json'), 'utf-8')).aliases);
const items: ChooserItem[] = L.records.map((r: Parameters<typeof toItem>[0]) => toItem(r, INDEX.records[r.id]));
const ctx = { items, records: L.records, edges: E };

let failures = 0;
function ok(cond: unknown, msg: string): void {
  if (!cond) {
    failures++;
    console.error(`FAIL: ${msg}`);
  }
}

// --- every product type composes, with honest picks ----------------------
for (const product of Object.keys(PRODUCTS) as ProductType[]) {
  const p = planStack(ctx, { product } as StackAnswers);
  ok(p.layers.length === PRODUCTS[product].layers.length, `${product}: one result per preset layer`);
  for (const l of p.layers) {
    if (!l.pick) continue;
    ok(l.pick.item.status.severity < 3, `${product}/${l.layer}: never picks archived or shut-down systems (${l.pick.item.name})`);
    for (const w of l.whyNot) ok(w.because.length > 0, `${product}/${l.layer}: why-not for ${w.name} gives a reason`);
    ok(!l.whyNot.some((w) => w.id === l.pick!.item.id), `${product}/${l.layer}: the pick is not its own runner-up`);
  }
  ok(p.security.items.length === 10 && p.security.items[0].id === 'LLM01', `${product}: OWASP LLM Top 10 mapped`);
  ok(p.risk.level === (p.risk.score < 3 ? 'low' : p.risk.score < 6 ? 'medium' : 'high'), `${product}: risk level follows the score`);
  ok(p.risk.factors.every((f) => f.points > 0 && f.detail), `${product}: every risk factor has points and a detail`);
  ok(p.evals.benchmarks.every((b) => items.find((i) => i.id === b.id)), `${product}: benchmarks are catalog records`);

  // switching cost (#362): every exit path with a fallback says what moving costs
  for (const l of p.layers) {
    if (!l.exit?.fallback) continue;
    const sw = l.exit.switching;
    ok(!!sw && sw.to?.id === l.exit.fallback.id && typeof sw.deltaNote === 'string' && sw.deltaNote.length > 0, `${product}/${l.layer}: switching names the fallback and a cost note`);
    ok(!!sw && sw.sharedIntegrations === sw.sharedWith.length && !sw.sharedWith.includes(l.pick!.item.name), `${product}/${l.layer}: shared integrations count other picks only`);
  }
  if (p.cost?.range) ok(p.cost.range.lowUsd >= p.cost.knownMonthlyUsd && p.cost.range.highUsd >= p.cost.range.lowUsd, `${product}: cost range brackets the published total`);

  // stack.yml round-trips through the stack checker
  const parsed = parseManifest(p.stackYaml, { filename: 'stack.yml' });
  ok(parsed.format === 'stack.yml', `${product}: stack.yml detected by filename`);
  ok(parseManifest(p.stackYaml).format === 'stack.yml', `${product}: stack.yml detected by content`);
  const picks = p.layers.filter((l) => l.pick).length;
  ok(parsed.dependencies.length === picks, `${product}: every pick is in stack.yml (${parsed.dependencies.length}/${picks})`);
  const report = checkManifest(p.stackYaml, INDEX, { filename: 'stack.yml' });
  ok(report.unmatched.length === 0, `${product}: every stack.yml component is in the stack index (${report.unmatched.map((d) => d.name).join(', ')})`);
}

// --- requirements are respected -------------------------------------------
{
  const p = planStack(ctx, { product: 'support-agent', oss: true } as StackAnswers);
  for (const l of p.layers) {
    if (!l.pick || l.pickUnconfirmed) continue;
    ok(l.pick.item.oss === 'yes', `oss: ${l.layer} pick ${l.pick.item.name} is open source`);
  }
}
{
  const p = planStack(ctx, { product: 'rag-copilot', hosting: 'self' } as StackAnswers);
  ok(p.layers.some((l) => l.layer === 'serving'), 'self-hosting adds a model-serving layer');
  for (const l of p.layers) {
    if (!l.pick || l.pickUnconfirmed) continue;
    ok(l.pick.item.selfHost === 'yes', `self: ${l.layer} pick ${l.pick.item.name} is self-hostable`);
  }
}
{
  const p = planStack(ctx, { product: 'coding-agent', language: 'typescript' } as StackAnswers);
  const fw = p.layers.find((l) => l.layer === 'framework');
  ok(fw?.pick && !fw.pick.unconfirmed.includes('TypeScript / JavaScript SDK') ? fw.pick.reasons.some((r) => /TypeScript/.test(r.text)) : true, 'typescript: framework pick shows the TypeScript fact');
}

// --- pin, avoid, add ---------------------------------------------------------
{
  const base = planStack(ctx, { product: 'support-agent' } as StackAnswers);
  const vec = base.layers.find((l) => l.layer === 'vectors')!.pick!.item.id;
  const avoided = planStack(ctx, { product: 'support-agent', avoid: [vec] } as StackAnswers);
  ok(avoided.layers.find((l) => l.layer === 'vectors')?.pick?.item.id !== vec, 'avoid: an avoided id is never picked');
  const pinId = base.layers.find((l) => l.layer === 'vectors')!.whyNot[0]?.id;
  if (pinId) {
    const pinned = planStack(ctx, { product: 'support-agent', pin: { vectors: pinId } } as StackAnswers);
    const pv = pinned.layers.find((l) => l.layer === 'vectors')!.pick!;
    ok(pv.item.id === pinId && pv.pinned, 'pin: the pinned id is used');
  }
  const voice = planStack(ctx, { product: 'support-agent', add: ['voice'] } as StackAnswers);
  ok(voice.layers.some((l) => l.layer === 'voice'), 'add: extra layer included');
  ok(LAYER_BY_ID.voice.label === 'Voice runtime', 'layer labels exported');
}

// --- compliance must-haves --------------------------------------------------
{
  const p = planStack(ctx, { product: 'support-agent', compliance: ['soc2-type2'] } as StackAnswers);
  for (const l of p.layers) {
    const c = l.pick?.item.facts.compliance?.value ?? '';
    if (l.pick && c && !l.pick.pinned) ok(c.split(',').includes('soc2-type2'), `compliance: ${l.layer} pick ${l.pick.item.name} publishes soc2-type2 (${c})`);
  }
}

// --- watch feed + slim output ---------------------------------------------
{
  const p = planStack(ctx, { product: 'rag-copilot' } as StackAnswers);
  const opml = toOpml(p.answers, p.layers, 'https://example.org');
  const picks = p.layers.filter((l) => l.pick);
  ok((opml.match(/type="rss"/g) ?? []).length === picks.length, 'OPML has one feed per pick');
  ok(picks.every((l) => opml.includes(`https://example.org/feeds/${l.pick!.item.id}.xml`)), 'OPML feed URLs point at /feeds/<id>.xml');
  const slim = slimPlan(p);
  ok(slim.layers.every((l) => !l.pick || (l.pick.page.includes('/systems/') && l.pick.feed.endsWith('.xml'))), 'slim plan links each pick and its feed');
}

// --- committed blueprints stay valid ---------------------------------------
{
  const dir = join(dirname(find('landscape.json')), '..', 'blueprints');
  let files: string[] = [];
  try {
    files = readdirSync(dir).flatMap((d) => ['stack.yml', 'stack.self-hosted.yml'].map((f) => join(dir, d, f))).filter((f) => { try { readFileSync(f); return true; } catch { return false; } });
  } catch { /* npm tarball: no blueprints/ */ }
  for (const f of files) {
    const r = checkManifest(readFileSync(f, 'utf-8'), INDEX, { filename: 'stack.yml' });
    ok(r.unmatched.length === 0, `${f}: every component is a catalog record`);
    ok(r.matched.every((m) => m.record.severity < 3), `${f}: no archived or shut-down component (run make blueprints)`);
  }
}

// --- integration evidence is cited ----------------------------------------
{
  const p = planStack(ctx, { product: 'support-agent' } as StackAnswers);
  for (const l of p.layers) for (const r of l.pick?.reasons ?? []) {
    if (r.text.startsWith('Works with')) ok(r.citation === null || /^https?:/.test(r.citation ?? ''), `integration reason cites a URL: ${r.text}`);
  }
  ok(p.pairs.every((x) => ['documented', 'mentioned', 'not-recorded'].includes(x.status)), 'pair statuses are never "incompatible"');
}

if (failures) {
  console.error(`${failures} composer test(s) failed`);
  process.exit(1);
}
console.log('all composer tests passed');
