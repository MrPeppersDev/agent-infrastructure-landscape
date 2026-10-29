#!/usr/bin/env node
// GitHub Action entrypoint: check a repo's AI dependencies against the
// AI Agent Infrastructure Landscape (archived, deprecated, acquired,
// maintenance-mode, renamed or stale systems) and suggest replacements.
//
// Zero dependencies (Node 20+). Inputs arrive as INPUT_* env vars (see
// ../action.yml). Writes a job summary, file annotations, optional PR
// comment, optional shields.io badge JSON, and step outputs.

import { readFileSync, writeFileSync, existsSync, readdirSync, statSync, appendFileSync, mkdirSync } from 'node:fs';
import { join, relative, basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { checkManifest, STATUS_LABEL } from './dist/stack-check.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = 'https://mrpeppersdev.github.io/agent-infrastructure-landscape';
const input = (name, def = '') => (process.env[`INPUT_${name.replace(/ /g, '_').toUpperCase()}`] ?? def).trim() || def;
const workspace = process.env.GITHUB_WORKSPACE || process.cwd();

const MANIFEST_NAMES = /^(package\.json|requirements[\w.-]*\.txt|pyproject\.toml|\.mcp\.json|mcp\.json|claude_desktop_config\.json|stack\.ya?ml)$/i;
const SKIP_DIRS = new Set(['node_modules', '.git', 'dist', 'build', '.venv', 'venv', '__pycache__', '.next', 'vendor', 'site-packages']);

function findManifests(root, depth = 0, out = []) {
  if (depth > 6) return out;
  for (const name of readdirSync(root)) {
    const p = join(root, name);
    let st;
    try { st = statSync(p); } catch { continue; }
    if (st.isDirectory()) {
      if (!SKIP_DIRS.has(name) && !name.startsWith('.') || name === '.cursor' || name === '.vscode') findManifests(p, depth + 1, out);
    } else if (MANIFEST_NAMES.test(name)) out.push(p);
  }
  return out;
}

async function fetchJson(url) {
  const r = await fetch(url, { headers: { 'user-agent': 'ai-stack-check-action' } });
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json();
}

async function loadIndex() {
  const src = input('index-url', `${SITE}/api/stack-index.json`);
  try {
    return { index: await fetchJson(src), from: src };
  } catch (e) {
    const local = resolve(here, '..', 'data', 'stack-index.json');
    console.log(`::warning title=AI stack check::Couldn't fetch the latest index (${e.message}); using the copy bundled with this action version.`);
    return { index: JSON.parse(readFileSync(local, 'utf8')), from: 'bundled' };
  }
}

async function loadReplacements() {
  try {
    return await fetchJson(input('replacements-url', `${SITE}/api/replacements.json`));
  } catch {
    return {};
  }
}

const esc = (s) => String(s).replace(/%/g, '%25').replace(/\r/g, '%0D').replace(/\n/g, '%0A');
const escProp = (s) => esc(s).replace(/:/g, '%3A').replace(/,/g, '%2C');

function lineOf(text, name) {
  const i = text.toLowerCase().indexOf(name.toLowerCase());
  return i < 0 ? 1 : text.slice(0, i).split('\n').length;
}

function setOutput(k, v) {
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `${k}=${v}\n`);
}

async function upsertComment(body) {
  const token = input('github-token');
  const eventPath = process.env.GITHUB_EVENT_PATH;
  const repo = process.env.GITHUB_REPOSITORY;
  if (!token || !eventPath || !repo) return;
  const ev = JSON.parse(readFileSync(eventPath, 'utf8'));
  const pr = ev.pull_request?.number;
  if (!pr) return;
  const api = process.env.GITHUB_API_URL || 'https://api.github.com';
  const h = { authorization: `Bearer ${token}`, accept: 'application/vnd.github+json', 'user-agent': 'ai-stack-check-action' };
  const marker = '<!-- ai-stack-check -->';
  const list = await fetch(`${api}/repos/${repo}/issues/${pr}/comments?per_page=100`, { headers: h }).then((r) => (r.ok ? r.json() : []));
  const mine = Array.isArray(list) ? list.find((c) => c.body?.includes(marker)) : null;
  const payload = JSON.stringify({ body: `${marker}\n${body}` });
  const res = mine
    ? await fetch(`${api}/repos/${repo}/issues/comments/${mine.id}`, { method: 'PATCH', headers: h, body: payload })
    : await fetch(`${api}/repos/${repo}/issues/${pr}/comments`, { method: 'POST', headers: h, body: payload });
  if (!res.ok) console.log(`::warning title=AI stack check::Couldn't post the PR comment (HTTP ${res.status}). Give the job \`pull-requests: write\`.`);
}

async function main() {
  const paths = input('manifests')
    ? input('manifests').split(/[\n,]+/).map((p) => p.trim()).filter(Boolean).map((p) => resolve(workspace, p))
    : findManifests(workspace);
  const { index, from } = await loadIndex();
  const replacements = await loadReplacements();
  const failOn = input('fail-on', 'none'); // none | attention | archived
  const reports = [];
  for (const p of paths) {
    if (!existsSync(p)) {
      console.log(`::warning title=AI stack check::${relative(workspace, p)} not found`);
      continue;
    }
    const text = readFileSync(p, 'utf8');
    try {
      const report = checkManifest(text, index, { filename: basename(p), replacements });
      reports.push({ path: relative(workspace, p) || basename(p), text, report });
    } catch (e) {
      console.log(`::warning file=${escProp(relative(workspace, p))},title=AI stack check::Couldn't parse: ${esc(e.message)}`);
    }
  }

  const findings = reports.flatMap((r) => r.report.attention.map((f) => ({ ...f, path: r.path, text: r.text })));
  const matched = reports.reduce((n, r) => n + r.report.matched.length, 0);
  const severe = findings.filter((f) => f.record.severity >= 3);

  for (const f of findings) {
    const alts = (f.replacements ?? []).map((a) => a.name).join(', ');
    const msg = `${f.dependency.name} → ${f.record.name}: ${STATUS_LABEL[f.record.status]}${f.record.note ? ` (${f.record.note})` : ''}.${alts ? ` Consider: ${alts}.` : ''} ${SITE}/alternatives/${f.recordId}`;
    const level = f.record.severity >= 3 ? 'error' : 'warning';
    const lvl = level === 'error' && failOn === 'none' ? 'warning' : level;
    console.log(`::${lvl} file=${escProp(f.path)},line=${lineOf(f.text, f.dependency.name)},title=${escProp(`${f.record.name} is ${STATUS_LABEL[f.record.status].toLowerCase()}`)}::${esc(msg)}`);
  }

  const site = SITE;
  const lines = [
    `### AI stack check`,
    '',
    findings.length
      ? `**${findings.length}** of ${matched} catalogued AI dependencies need attention (${reports.length} manifest${reports.length === 1 ? '' : 's'} checked).`
      : `✅ No archived, deprecated, acquired or stale systems among ${matched} catalogued AI dependencies (${reports.length} manifest${reports.length === 1 ? '' : 's'} checked).`,
    ''
  ];
  if (findings.length) {
    lines.push('| Dependency | System | Status | Consider instead | File |', '|---|---|---|---|---|');
    for (const f of findings) {
      const alts = (f.replacements ?? []).map((a) => `[${a.name}](${site}/systems/${a.id})`).join(', ') || `[see alternatives](${site}/alternatives/${f.recordId})`;
      const ev = f.record.evidence ? ` ([evidence](${f.record.evidence}))` : '';
      lines.push(`| \`${f.dependency.name}\` | [${f.record.name}](${site}/systems/${f.recordId}) | **${STATUS_LABEL[f.record.status]}**${f.record.note ? ` — ${f.record.note}` : ''}${ev} | ${alts} | \`${f.path}\` |`);
    }
    lines.push('');
  }
  lines.push(`<sub>From the [AI Agent Infrastructure Landscape](${site}) · index ${index.generatedAt ?? ''} (${from === 'bundled' ? 'bundled' : 'live'}) · [check a stack in the browser](${site}/check)</sub>`);
  const md = lines.join('\n');
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, md + '\n');
  console.log(md);

  const comment = input('comment', 'auto');
  if (comment === 'always' || (comment === 'auto' && findings.length)) await upsertComment(md);

  const badgePath = input('badge-path');
  if (badgePath) {
    const p = resolve(workspace, badgePath);
    mkdirSync(dirname(p), { recursive: true });
    writeFileSync(p, JSON.stringify({
      schemaVersion: 1,
      label: 'AI stack',
      message: findings.length ? `${findings.length} flagged` : `${matched} checked, 0 flagged`,
      color: severe.length ? 'red' : findings.length ? 'yellow' : 'brightgreen'
    }) + '\n');
  }

  setOutput('attention-count', String(findings.length));
  setOutput('matched-count', String(matched));
  setOutput('manifests', String(reports.length));

  if ((failOn === 'attention' && findings.length) || (failOn === 'archived' && severe.length)) {
    console.log(`::error title=AI stack check::${failOn === 'archived' ? severe.length : findings.length} dependencies flagged (fail-on: ${failOn})`);
    process.exit(1);
  }
}

main().catch((e) => {
  console.log(`::error title=AI stack check::${esc(e.stack || e.message)}`);
  process.exit(1);
});
