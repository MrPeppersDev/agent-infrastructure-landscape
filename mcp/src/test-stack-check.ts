// Tests for stack-check.ts. Run: npm run build && node dist/test-stack-check.js
// Uses the real data/stack-index.json, so expectations are about catalogued
// facts that are stable (Flowise archived, Mem0 active, …).

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkManifest, parseManifest, licenceBucket, vendorOf, pinnedVersion, type StackIndex } from './stack-check.js';

const here = dirname(fileURLToPath(import.meta.url));
function findIndex(): string {
  let dir = here;
  for (let i = 0; i < 6; i++) {
    for (const p of [join(dir, 'data', 'stack-index.json'), join(dir, 'stack-index.json')]) {
      try {
        readFileSync(p);
        return p;
      } catch {
        /* keep looking */
      }
    }
    dir = dirname(dir);
  }
  throw new Error('stack-index.json not found');
}
const index = JSON.parse(readFileSync(findIndex(), 'utf-8')) as StackIndex;

let failures = 0;
function check(name: string, cond: boolean, detail = '') {
  if (cond) console.log(`  PASS ${name}`);
  else {
    failures++;
    console.log(`  FAIL ${name} ${detail}`);
  }
}

// package.json
{
  const pj = JSON.stringify({
    dependencies: { flowise: '^3.0.0', mem0ai: '^2.1.0', 'left-pad': '1.0.0' },
    devDependencies: { '@modelcontextprotocol/server-memory': 'latest' },
  });
  const r = checkManifest(pj, index);
  check('package.json detected', r.format === 'package.json', r.format);
  const flowise = r.matched.find((f) => f.dependency.name === 'flowise');
  check('flowise matched + archived', flowise?.record.status === 'archived', JSON.stringify(flowise?.record.status));
  check('flowise needs attention', r.attention.some((f) => f.dependency.name === 'flowise'));
  check('mem0ai matched', r.matched.some((f) => f.dependency.name === 'mem0ai'));
  check('left-pad unmatched', r.unmatched.some((d) => d.name === 'left-pad'));
  check('attention sorted by severity', r.attention.every((f, i, a) => i === 0 || a[i - 1].record.severity >= f.record.severity));
}

// requirements.txt
{
  const req = 'mem0ai>=2.0\nautogen-agentchat==0.7.5  # agents\nlangchain[openai]\n-e git+https://github.com/FlowiseAI/Flowise.git#egg=x\nrequests\n';
  const r = checkManifest(req, index, { filename: 'requirements.txt' });
  check('requirements detected', r.format === 'requirements.txt', r.format);
  check('extras stripped (langchain)', r.matched.some((f) => f.dependency.name === 'langchain'));
  check('autogen-agentchat in maintenance', r.matched.find((f) => f.dependency.name === 'autogen-agentchat')?.record.status === 'maintenance');
  check('git URL matched via repo', r.matched.some((f) => f.matchedBy.startsWith('github:flowiseai/flowise')));
}

// pyproject.toml
{
  const py = `[project]\nname = "x"\ndependencies = [\n  "cognee>=1.6",\n  "graphiti-core",\n]\n[project.optional-dependencies]\ndev = ["pytest"]\n[tool.poetry.dependencies]\npython = "^3.11"\nletta = "^0.30"\n`;
  const r = checkManifest(py, index);
  check('pyproject detected', r.format === 'pyproject.toml', r.format);
  check('pyproject deps parsed', ['cognee', 'graphiti-core', 'pytest', 'letta'].every((n) => parseManifest(py).dependencies.some((d) => d.name === n)));
  check('python is not a dependency', !parseManifest(py).dependencies.some((d) => d.name === 'python'));
  check('graphiti-core matched', r.matched.some((f) => f.dependency.name === 'graphiti-core'));
}

// MCP config
{
  const mcp = JSON.stringify({
    mcpServers: {
      memory: { command: 'npx', args: ['-y', '@modelcontextprotocol/server-memory'] },
      mem0: { command: 'uvx', args: ['mem0-mcp'] },
      graph: { command: 'docker', args: ['run', '-i', '--rm', '-e', 'X=1', 'zepai/knowledge-graph-mcp:latest'] },
      remote: { url: 'https://example.com/mcp' },
    },
  });
  const { format, dependencies } = parseManifest(mcp);
  check('mcp config detected', format === 'mcp-config', format);
  check('npx package extracted', dependencies.some((d) => d.ecosystem === 'npm' && d.name === '@modelcontextprotocol/server-memory'));
  check('uvx package extracted', dependencies.some((d) => d.ecosystem === 'pypi' && d.name === 'mem0-mcp'));
  check('docker image extracted (tag kept for display)', dependencies.some((d) => d.ecosystem === 'docker' && d.name.startsWith('zepai/knowledge-graph-mcp')));
  check('remote url server ignored', dependencies.length === 3, String(dependencies.length));
  const r = checkManifest(mcp, index);
  check('mcp memory server matched', r.matched.some((f) => f.dependency.name === '@modelcontextprotocol/server-memory'));
  check('archived Mem0 MCP flagged', r.attention.some((f) => f.dependency.name === 'mem0-mcp'), JSON.stringify(r.matched.map((f) => [f.dependency.name, f.record.status])));
}

// plain list
{
  const r = checkManifest('npm:flowise\npypi:cognee\nmem0ai', index);
  check('plain list detected', r.format === 'list', r.format);
  check('plain list matched 3', r.matched.length === 3, String(r.matched.length));
}

// upgrade advisor: replacements that work with the rest of the manifest rank first
{
  const rec = (name: string, severity: number) => ({ name, family: 'x', section: 'x', url: null, license: '', llm_lock: '', status: severity >= 2 ? 'archived' : 'active', severity, note: '', context: '', evidence: null, last_commit: null });
  const idx = { generatedAt: 't', packages: {}, repos: {}, records: { old: rec('Old', 3), fw: rec('Framework', 0), db: rec('Store', 0) } } as unknown as StackIndex;
  const yml = 'version: 1\ncomponents:\n  memory: old\n  framework: fw\n  vectors: db\n';
  const replacements = { old: [{ id: 'a', name: 'A', why: ['similar'] }, { id: 'b', name: 'B', why: ['similar'] }, { id: 'c', name: 'C', why: [] }, { id: 'd', name: 'D', why: [] }] };
  const links = { b: ['db', 'fw'], d: ['fw'] };
  const r = checkManifest(yml, idx, { filename: 'stack.yml', replacements, links });
  const f = r.attention.find((x) => x.recordId === 'old');
  check('advisor ranks fitting replacements first', f?.replacements?.map((x) => x.id).join(',') === 'b,d,a', JSON.stringify(f?.replacements));
  check('advisor names what it fits with', f?.replacements?.[0].why[0] === 'works with Framework, Store in your stack' && f?.replacements?.[0].fits?.length === 2, JSON.stringify(f?.replacements?.[0]));
  const plain = checkManifest(yml, idx, { filename: 'stack.yml', replacements });
  check('without links, order is unchanged and capped at 3', plain.attention[0]?.replacements?.map((x) => x.id).join(',') === 'a,b,c');
}


// stack audit (#363): layers covered, layers missing, concentration, licences
{
  const pj = JSON.stringify({ dependencies: { '@mastra/core': '^1.0.0', mem0ai: '^2.2.0', chromadb: '^3.0.0' } });
  const r = checkManifest(pj, index, { filename: 'package.json' });
  const layers = r.audit.layers.map((l) => l.layer);
  check('audit detects framework, memory and vectors', ['framework', 'memory', 'vectors'].every((l) => layers.includes(l as never)), layers.join(','));
  const missing = r.audit.missing.map((m) => m.layer);
  check('audit lists observability and guardrails as not detected', missing.includes('observability') && missing.includes('guardrails'), missing.join(','));
  check('audit never reports a detected layer as missing', !missing.some((m) => layers.includes(m)));
  check('audit stack.yml names the memory layer', /components:\n(.*\n)*\s+memory: mem0--mem0-ai/.test(r.audit.stackYaml), r.audit.stackYaml);
  check('audit licence mix has an open-source bucket', r.audit.licences.some((b) => b.bucket === 'open-source' && b.systems.length >= 2), JSON.stringify(r.audit.licences.map((b) => [b.bucket, b.systems.length])));
  const one = checkManifest('mem0ai', index);
  check('a single dependency is not audited for missing layers', one.audit.missing.length === 0);
}
{
  const rec = (name: string, section: string, url: string, license: string) => ({ name, family: 'x', section, url, license, llm_lock: '', status: 'active', severity: 0, note: '', context: '', evidence: null, last_commit: null });
  const idx = {
    generatedAt: 't', packages: {}, repos: {},
    records: {
      fw: rec('Acme Agents', 'Agent frameworks (no first-party memory layer)', 'https://docs.acme.dev/agents', 'MIT'),
      obs: rec('Acme Trace', 'Evaluation & observability platforms', 'https://acme.dev/trace', 'Proprietary (SaaS)'),
      gw: rec('Acme Router', 'Inference platforms & gateways', 'https://acme.dev/router', 'BSL-1.1 (converts to Apache-2.0)'),
      srv: rec('Fast Serve', 'Inference platforms & gateways', 'https://github.com/fast/serve', 'AGPL-3.0')
    }
  } as unknown as StackIndex;
  const r = checkManifest('version: 1\ncomponents:\n  framework: fw\n  observability: obs\n  gateway: gw\n  serving: srv\n', idx, { filename: 'stack.yml' });
  const layers = Object.fromEntries(r.audit.layers.map((l) => [l.layer, l.systems.map((s) => s.id).join(',')]));
  check('gateway and serving are split by name within one section', layers.gateway === 'gw' && layers.serving === 'srv', JSON.stringify(layers));
  check('vendor concentration groups by registrable domain', r.audit.concentration[0]?.vendor === 'acme.dev' && r.audit.concentration[0].layers.length === 3, JSON.stringify(r.audit.concentration));
  const buckets = Object.fromEntries(r.audit.licences.map((b) => [b.bucket, b.systems.map((s) => s.id).join(',')]));
  check('licence buckets: open-source, source-available, proprietary', buckets['open-source'] === 'fw,srv' && buckets['source-available'] === 'gw' && buckets.proprietary === 'obs', JSON.stringify(buckets));
  check('copyleft flagged for AGPL', r.audit.licences.find((b) => b.bucket === 'open-source')?.systems.find((s) => s.id === 'srv')?.copyleft === true);
  check('licenceBucket: BSL-1.0 is Boost (open source), BSL-1.1 is source-available', licenceBucket('BSL-1.0').bucket === 'open-source' && licenceBucket('BSL-1.1').bucket === 'source-available');
  check('licenceBucket: Apache with source-available parts is open-source and mixed', licenceBucket('Apache-2.0 (core; ee/ dirs under source-available Enterprise License)').mixed === true);
  check('vendorOf: GitHub keeps the owner', vendorOf({ url: 'https://github.com/langchain-ai/langchain' }, 'x') === 'github.com/langchain-ai');
}

// version drift (#364)
{
  const pj = JSON.stringify({ dependencies: { mem0ai: '^1.0.0', chromadb: 'latest' } });
  const r = checkManifest(pj, index, { filename: 'package.json' });
  const d = r.drift.find((x) => x.recordId === 'mem0--mem0-ai');
  check('mem0ai ^1.0.0 is behind the catalog release (2.x)', d?.level === 'behind-major' && /^2\./.test(d.latest.version), JSON.stringify(r.drift));
  check('"latest" gets no drift verdict', !r.drift.some((x) => x.dependency.name === 'chromadb'));
  const open = checkManifest('mem0ai>=0.1\n', index, { filename: 'requirements.txt' });
  check('an open lower bound gets no drift verdict', open.drift.length === 0, JSON.stringify(open.drift));
  const exact = checkManifest('mem0ai==1.1.0\n', index, { filename: 'requirements.txt' });
  check('an exact old pin is behind-major', exact.drift[0]?.level === 'behind-major');
  check('pinnedVersion parses npm and PEP 440 specs',
    pinnedVersion('^2.2.0')?.major === 2 && pinnedVersion('~=1.4')?.major === 1 && pinnedVersion('>=0.3')?.unbounded === true &&
    pinnedVersion('>=1,<2')?.unbounded === false && pinnedVersion('0.3.*')?.minor === 3 && pinnedVersion('latest') === null && pinnedVersion('workspace:*') === null);
}
{
  const rec = (name: string, latest: { version: string; date: string | null } | null) => ({ name, family: 'x', section: 'Dedicated memory layers', url: null, license: 'MIT', llm_lock: '', status: 'active', severity: 0, note: '', context: '', evidence: null, last_commit: null, latest_release: latest });
  const idx = { generatedAt: 't', packages: { 'npm:zero': 'z', 'npm:nov': 'n' }, repos: {}, records: { z: rec('Zero', { version: '0.9.0', date: null }), n: rec('NoVersion', null) } } as unknown as StackIndex;
  const r = checkManifest(JSON.stringify({ dependencies: { zero: '^0.4.0', nov: '^1.0.0' } }), idx, { filename: 'package.json' });
  check('0.x minors count as drift', r.drift[0]?.level === 'behind-minor' && r.drift[0].recordId === 'z', JSON.stringify(r.drift));
  check('no release version → counted, not judged', r.noVersionData === 1 && !r.drift.some((x) => x.recordId === 'n'));
}
console.log(failures ? `\n${failures} failure(s)` : '\nall stack-check tests passed');
process.exit(failures ? 1 : 0);
