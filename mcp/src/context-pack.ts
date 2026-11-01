// Context pack for coding agents (#398, roadmap 3.2): a short Markdown
// section to keep in AGENTS.md or CLAUDE.md, so an agent working in the
// repo knows which system fills each layer of the stack, how they connect,
// what to watch and where to ask. Pure and dependency-free so the MCP
// server, the hosted worker, the CLI and /build return the same text.

import { PRODUCTS, LAYER_BY_ID, type StackAnswers, type StackPlan, type LayerId, type ProductType } from './composer.js';

/**
 * Answers that reproduce a stack.yml: its product and requirements, and
 * every component pinned to its layer.
 */
export function answersFromStackYaml(text: string): StackAnswers {
  const a: Record<string, unknown> = {};
  const pin: Record<string, string> = {};
  let block = '';
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/\s+#.*$/, '');
    if (!line.trim() || line.trim().startsWith('#')) continue;
    const top = line.match(/^(\w[\w-]*):\s*(.*)$/);
    if (top) {
      block = top[1];
      if (block === 'product' && top[2] in PRODUCTS) a.product = top[2] as ProductType;
      continue;
    }
    const kv = line.match(/^\s+([\w-]+):\s*([\w.-]+)\s*$/);
    if (!kv) continue;
    if (block === 'requirements') {
      if (kv[1] === 'language' || kv[1] === 'hosting') a[kv[1]] = kv[2];
      if (kv[1] === 'oss' || kv[1] === 'mcp') a[kv[1]] = kv[2] === 'true';
    } else if (block === 'components' && kv[1] in LAYER_BY_ID) {
      pin[kv[1]] = kv[2];
    }
  }
  const layers = Object.keys(pin) as LayerId[];
  return { ...a, pin, ...(layers.length ? { layers } : {}) } as StackAnswers;
}

/** packages: the stack index's package → record id map ("npm:mem0ai" → "mem0--mem0-ai"). */
export function contextPack(plan: StackPlan, packages: Record<string, string>, site: string, today: string = new Date().toISOString().slice(0, 10)): string {
  const byRecord = new Map<string, string[]>();
  for (const [pkg, id] of Object.entries(packages)) (byRecord.get(id) ?? byRecord.set(id, []).get(id)!).push(pkg);
  const name = new Map(plan.layers.filter((l) => l.pick).map((l) => [l.pick!.item.id, l.pick!.item.name]));
  const a = plan.answers;
  const out: string[] = [
    '## AI agent stack',
    '',
    `Generated ${today} by the [AI Agent Infrastructure Landscape](${site}) for a ${plan.product.toLowerCase()} ` +
      `(language: ${a.language}, hosting: ${a.hosting}${a.oss ? ', open source only' : ''}${a.mcp ? ', MCP required' : ''}${a.compliance?.length ? `, attestations: ${a.compliance.join(', ')}` : ''}). ` +
      'Every fact below links to the catalog page that cites its source.',
    '',
    '### Components',
    ''
  ];
  for (const l of plan.layers) {
    if (!l.pick) {
      out.push(`- **${l.label}:** none chosen (nothing in the catalog met the requirements).`);
      continue;
    }
    const i = l.pick.item;
    const pk = (byRecord.get(i.id) ?? []).sort().slice(0, 4);
    out.push(
      `- **${l.label}: [${i.name}](${site}/systems/${i.id})** (\`${i.id}\`)` +
        (pk.length ? `. Packages: ${pk.map((p) => `\`${p}\``).join(', ')}` : '') +
        (i.url ? `. Docs: ${i.url}` : '')
    );
    if (l.pick.warning) out.push(`  - Lifecycle: ${l.pick.warning}. Plan a replacement before building more on it.`);
    const e = l.exit;
    if (e?.migration) out.push(`  - Migration notes: ${e.migration.summary} (${e.migration.sources[0]})`);
    else if (e?.fallback) out.push(`  - Fallback if it has to go: [${e.fallback.name}](${site}/systems/${e.fallback.id})`);
  }
  const documented = plan.pairs.filter((p) => p.status === 'documented');
  const unrecorded = plan.pairs.filter((p) => p.status === 'not-recorded');
  if (documented.length) {
    out.push('', '### Documented integrations', '');
    for (const p of documented) {
      const ev = p.evidence[0];
      out.push(`- ${name.get(p.a) ?? p.a} + ${name.get(p.b) ?? p.b}${ev?.citation ? `: ${ev.citation}` : ''}`);
    }
  }
  if (unrecorded.length) {
    const shown = unrecorded.slice(0, 6).map((p) => `${name.get(p.a) ?? p.a} + ${name.get(p.b) ?? p.b}`);
    const more = unrecorded.length - shown.length;
    out.push('', `No integration is recorded between: ${shown.join('; ')}${more > 0 ? `; and ${more} more pair${more === 1 ? '' : 's'}` : ''}. That means unknown, not incompatible; check their docs before wiring them together.`);
  }
  out.push(
    '',
    '### Working rules',
    '',
    '- Use the component above for its layer. Ask before adding a second system for a layer that is already covered.',
    '- Before adding or upgrading an AI dependency, run `npx landscape check package.json` (or `requirements.txt`, `pyproject.toml`, `stack.yml`), or call `check_stack` on the landscape MCP server. It flags archived, acquired, deprecated and stale systems and version drift.',
    `- For a fact about a system (licence, pricing, deployment, MCP support, attestations), call \`get_record\` / \`get_system\` or open its catalog page. Don't rely on memory: the catalog dates and cites every value.`,
    `- To re-plan or compare: ${site}/build or the \`plan_stack\` tool.`,
    ''
  );
  return out.join('\n');
}
