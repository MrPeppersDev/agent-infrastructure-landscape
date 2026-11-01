// Golden stack questions (product review, 2026-10-30): twenty plan_stack
// queries whose picks are recorded in golden-stacks.json. For each layer
// the file keeps the pick and the two runners-up at the time it was
// reviewed; the test fails when a pick falls outside that set, so a
// ranking or data change that moves a stack is seen and reviewed instead
// of slipping through. Re-record after reviewing with
//   node dist/golden-stacks.js --update
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { planStack, type StackAnswers } from './composer.js';
import { loadChooserItems, loadRecords, loadEdges, loadMigrations } from './data.js';

export const QUESTIONS: { id: string; answers: StackAnswers }[] = [
  { id: 'support-default', answers: { product: 'support-agent' } as StackAnswers },
  { id: 'support-ts-self-soc2', answers: { product: 'support-agent', language: 'typescript', hosting: 'self', compliance: ['soc2-type2'] } as StackAnswers },
  { id: 'support-python-managed', answers: { product: 'support-agent', language: 'python', hosting: 'managed' } as StackAnswers },
  { id: 'support-hipaa', answers: { product: 'support-agent', compliance: ['hipaa'] } as StackAnswers },
  { id: 'coding-default', answers: { product: 'coding-agent' } as StackAnswers },
  { id: 'coding-ts-oss', answers: { product: 'coding-agent', language: 'typescript', oss: true } as StackAnswers },
  { id: 'coding-self', answers: { product: 'coding-agent', hosting: 'self' } as StackAnswers },
  { id: 'research-default', answers: { product: 'research-agent' } as StackAnswers },
  { id: 'research-python-oss', answers: { product: 'research-agent', language: 'python', oss: true } as StackAnswers },
  { id: 'voice-default', answers: { product: 'voice-agent' } as StackAnswers },
  { id: 'voice-managed', answers: { product: 'voice-agent', hosting: 'managed' } as StackAnswers },
  { id: 'multi-default', answers: { product: 'multi-agent-workflow' } as StackAnswers },
  { id: 'multi-ts', answers: { product: 'multi-agent-workflow', language: 'typescript' } as StackAnswers },
  { id: 'multi-self-oss', answers: { product: 'multi-agent-workflow', hosting: 'self', oss: true } as StackAnswers },
  { id: 'rag-default', answers: { product: 'rag-copilot' } as StackAnswers },
  { id: 'rag-self', answers: { product: 'rag-copilot', hosting: 'self' } as StackAnswers },
  { id: 'rag-mcp', answers: { product: 'rag-copilot', mcp: true } as StackAnswers },
  { id: 'rag-gdpr', answers: { product: 'rag-copilot', compliance: ['gdpr'] } as StackAnswers },
  { id: 'support-browser-sandbox', answers: { product: 'support-agent', add: ['browser', 'sandbox'] } as StackAnswers },
  { id: 'coding-iso27001', answers: { product: 'coding-agent', compliance: ['iso27001'] } as StackAnswers }
];

type Golden = Record<string, Record<string, { pick: string; accept: string[] }>>;

const here = dirname(fileURLToPath(import.meta.url));
const FILE = join(here, '..', 'src', 'golden-stacks.json');

export function runGolden(): Golden {
  const ctx = { items: loadChooserItems(), records: loadRecords() as never, edges: loadEdges() as never, migrations: loadMigrations() as never };
  const out: Golden = {};
  for (const q of QUESTIONS) {
    const plan = planStack(ctx, q.answers);
    out[q.id] = {};
    for (const l of plan.layers) {
      if (!l.pick) continue;
      out[q.id][l.layer] = { pick: l.pick.item.id, accept: [l.pick.item.id, ...l.whyNot.filter((w) => !w.because.some((b) => b.text.startsWith('Ruled out'))).slice(0, 2).map((w) => w.id)] };
    }
  }
  return out;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const now = runGolden();
  if (process.argv.includes('--update')) {
    writeFileSync(FILE, JSON.stringify(now, null, 1) + '\n');
    // A table to review the recorded picks by eye.
    const names = new Map(loadRecords().map((r) => [r.id, r.name]));
    const md = ['# Golden stacks', '', 'Recorded picks for the twenty golden plan_stack questions (`mcp/src/golden-stacks.ts`). CI fails when a pick leaves its accepted set (the pick and its two runners-up). Review this table when re-recording.', ''];
    for (const q of QUESTIONS) {
      md.push(`## ${q.id}`, '', `\`${JSON.stringify(q.answers)}\``, '', '| Layer | Pick | Also accepted |', '|---|---|---|');
      for (const [layer, g] of Object.entries(now[q.id])) md.push(`| ${layer} | ${names.get(g.pick) ?? g.pick} | ${g.accept.slice(1).map((id) => names.get(id) ?? id).join(', ')} |`);
      md.push('');
    }
    writeFileSync(join(here, '..', 'src', 'golden-stacks.md'), md.join('\n'));
    console.log(`recorded ${Object.keys(now).length} golden stacks → ${FILE} (review table: golden-stacks.md)`);
  } else {
    const golden = JSON.parse(readFileSync(FILE, 'utf-8')) as Golden;
    const fails: string[] = [];
    for (const [q, layers] of Object.entries(golden)) {
      for (const [layer, g] of Object.entries(layers)) {
        const got = now[q]?.[layer]?.pick;
        if (!got) fails.push(`${q}/${layer}: no pick (golden ${g.pick})`);
        else if (!g.accept.includes(got)) fails.push(`${q}/${layer}: picks ${got}, golden ${g.pick} (accepts ${g.accept.join(', ')})`);
      }
    }
    if (fails.length) {
      console.error(fails.map((f) => `FAIL: ${f}`).join('\n'));
      console.error(`${fails.length} golden stack pick(s) moved. If the change is intended, review the new picks and re-record: cd mcp && npm run build && node dist/golden-stacks.js --update`);
      process.exit(1);
    }
    console.log(`all ${Object.keys(golden).length} golden stacks hold`);
  }
}
