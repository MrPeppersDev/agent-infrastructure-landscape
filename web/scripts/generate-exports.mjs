// Postbuild: machine-readable exports and change feeds.
//
//   /api/index.json                 every system: id, name, family, section, status, JSON url
//   /api/systems/<id>.json          one record: cells + citations, taxonomy, edges, history, lifecycle
//   /api/catalogs/<family>.json     one product family, flattened (one object per system)
//   /api/catalogs/<family>.csv      the same as CSV
//   /api/stack-index.json           the stack checker's package → system index
//   /feeds/<id>.xml                 Atom feed of one system's recorded changes
//   /changes.xml                    Atom feed of the latest 100 changes catalog-wide
//   /llms.txt                       regenerated with live counts and the endpoints above
//
// Everything is static and derived from data/*.json, so agents and other
// sites can consume one system or one catalog without cloning the full
// 11 MB landscape.json. Licence: CC-BY-4.0 (data).

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const buildDir = resolve(__dirname, '..', 'build');
const dataDir = resolve(__dirname, '..', '..', 'data');
const read = (f) => JSON.parse(readFileSync(resolve(dataDir, f), 'utf8'));

const SITE_ORIGIN = 'https://mrpeppersdev.github.io';
const basePath = process.env.BASE_PATH ?? '';
const baseUrl = `${SITE_ORIGIN}${basePath}`;
const PUBLIC = `${SITE_ORIGIN}/agent-infrastructure-landscape`; // canonical, for llms.txt
const REPO = 'https://github.com/MrPeppersDev/agent-infrastructure-landscape';

const landscape = read('landscape.json');
const edges = read('landscape.edges.json').edges ?? [];
const stack = read('stack-index.json');
let history = { baseline: '', records: {} };
try { history = read('history.json'); } catch { /* optional */ }
const families = JSON.parse(readFileSync(resolve(__dirname, '..', '..', 'taxonomy', 'families.json'), 'utf8')).families;
const famOf = new Map();
for (const f of families) for (const s of f.sections) famOf.set(s, f.id);

const records = landscape.records ?? [];
const primary = (r) => (r.sections.find((s) => s.primary) ?? r.sections[0])?.section ?? '';
const cv = (r, k) => {
  const c = r.cells?.[k];
  return c && typeof c.value === 'string' && !['no-data', 'not-applicable'].includes(c.status) ? c.value : '';
};
const tax = (r, axis) => (r.taxonomy?.[axis] ?? []).map((v) => v.value).join('|');
const statusOf = (id) => {
  const s = stack.records?.[id];
  return s ? { status: s.status, severity: s.severity, note: s.note || null } : { status: 'active', severity: 0, note: null };
};
const write = (rel, text) => {
  const p = resolve(buildDir, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, text);
};
const xml = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[c]);

// ---- per-system JSON -------------------------------------------------------
const outE = new Map(), inE = new Map();
for (const e of edges) {
  (outE.get(e.source) ?? outE.set(e.source, []).get(e.source)).push(e);
  (inE.get(e.target) ?? inE.set(e.target, []).get(e.target)).push(e);
}
const index = [];
for (const r of records) {
  const sec = primary(r);
  const fam = famOf.get(sec) ?? 'other';
  const doc = {
    id: r.id,
    name: r.name,
    url: r.url ?? null,
    page: `${baseUrl}/systems/${r.id}`,
    family: fam,
    section: sec,
    sections: r.sections.map((s) => s.section),
    tier: r.tier,
    last_verified_at: r.last_verified_at ?? null,
    lifecycle: statusOf(r.id),
    taxonomy: r.taxonomy,
    cells: r.cells,
    edges: { outgoing: outE.get(r.id) ?? [], incoming: inE.get(r.id) ?? [] },
    history: history.records?.[r.id] ?? [],
    license: 'CC-BY-4.0',
    source: `${REPO}/blob/main/data/landscape.json`
  };
  write(`api/systems/${r.id}.json`, JSON.stringify(doc));
  index.push({ id: r.id, name: r.name, family: fam, section: sec, tier: r.tier, status: doc.lifecycle.status, json: `${baseUrl}/api/systems/${r.id}.json` });
}
// Merged-away ids (taxonomy/system-aliases.json `redirects`) keep a stub that
// points at the record they were folded into.
const redirects = JSON.parse(readFileSync(resolve(__dirname, '..', '..', 'taxonomy', 'system-aliases.json'), 'utf8')).redirects ?? {};
for (const [from, to] of Object.entries(redirects)) {
  write(`api/systems/${from}.json`, JSON.stringify({ id: from, merged_into: to, json: `${baseUrl}/api/systems/${to}.json`, page: `${baseUrl}/systems/${to}` }));
}
write('api/index.json', JSON.stringify({ generatedAt: landscape.generatedAt ?? null, count: index.length, systems: index }));
write('api/stack-index.json', JSON.stringify(stack));

// ---- per-catalog flattened JSON + CSV --------------------------------------
const COLS = [
  ['id', (r) => r.id], ['name', (r) => r.name], ['url', (r) => r.url ?? ''], ['section', primary], ['tier', (r) => r.tier],
  ['status', (r) => statusOf(r.id).status], ['last_verified_at', (r) => r.last_verified_at ?? ''],
  ['type', (r) => cv(r, 'type')], ['license', (r) => cv(r, 'license')], ['latest_release', (r) => cv(r, 'latest-release')],
  ['deployment', (r) => cv(r, 'deployment')], ['pricing', (r) => cv(r, 'pricing')], ['mcp_support', (r) => cv(r, 'mcp-support')],
  ['a2a_support', (r) => cv(r, 'a2a-support')], ['backend_storage', (r) => cv(r, 'backend-storage')], ['llm_lock', (r) => cv(r, 'llm-lock')],
  ['github', (r) => cv(r, 'gh')], ['storage', (r) => tax(r, 'storage')], ['retrieval', (r) => tax(r, 'retrieval')],
  ['persistence', (r) => tax(r, 'persistence')], ['update', (r) => tax(r, 'update')], ['unit', (r) => tax(r, 'unit')],
  ['governance', (r) => tax(r, 'governance')], ['conflict', (r) => tax(r, 'conflict')], ['description', (r) => cv(r, 'desc')],
  ['page', (r) => `${baseUrl}/systems/${r.id}`]
];
const csvCell = (v) => {
  const s = String(v ?? '');
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
const catalogs = [];
for (const f of [...families, { id: 'all', name: 'Full catalog', sections: null }]) {
  const rows = records.filter((r) => f.id === 'all' || famOf.get(primary(r)) === f.id);
  const objs = rows.map((r) => Object.fromEntries(COLS.map(([k, fn]) => [k, fn(r)])));
  write(`api/catalogs/${f.id}.json`, JSON.stringify({ family: f.id, name: f.name, count: objs.length, license: 'CC-BY-4.0', systems: objs }));
  write(`api/catalogs/${f.id}.csv`, [COLS.map(([k]) => k).join(','), ...objs.map((o) => COLS.map(([k]) => csvCell(o[k])).join(','))].join('\n') + '\n');
  catalogs.push({ id: f.id, name: f.name, count: objs.length });
}

// ---- change feeds -----------------------------------------------------------
const byId = new Map(records.map((r) => [r.id, r]));
const iso = (d) => (/^\d{4}-\d{2}-\d{2}$/.test(d) ? `${d}T00:00:00Z` : d);
function describe(ev) {
  if (ev.kind === 'added') return 'Added to the catalog.';
  if (ev.kind === 'removed') return 'Removed from the catalog.';
  return ev.changes
    .map((c) => (c.first ? `${c.label} first recorded as “${c.to}”.` : !c.to ? `${c.label} cleared (was “${c.from}”).` : `${c.label}: “${c.from}” → “${c.to}”.`))
    .join(' ');
}
function entry(id, ev) {
  const r = byId.get(id);
  const name = r?.name ?? id;
  const link = `${baseUrl}/systems/${id}#changes`;
  const title = ev.kind === 'lifecycle' || ev.kind === 'added' || ev.kind === 'removed'
    ? `${name}: ${ev.kind === 'lifecycle' ? 'lifecycle change' : ev.kind}`
    : `${name}: ${ev.changes.map((c) => c.label.toLowerCase()).join(', ')} updated`;
  const ref = ev.pr ? `${REPO}/pull/${ev.pr}` : `${REPO}/commit/${ev.commit}`;
  return `  <entry>
    <title>${xml(title)}</title>
    <link href="${xml(link)}" />
    <id>${xml(`${baseUrl}/systems/${id}#${ev.date}-${ev.commit}`)}</id>
    <updated>${iso(ev.date)}</updated>
    <summary>${xml(describe(ev) + ` Source change: ${ref}`)}</summary>
  </entry>`;
}
function feed({ title, subtitle, self, alt, updated, entries }) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>${xml(title)}</title>
  <subtitle>${xml(subtitle)}</subtitle>
  <link href="${xml(self)}" rel="self" />
  <link href="${xml(alt)}" />
  <id>${xml(self)}</id>
  <updated>${updated}</updated>
  <author><name>AI Agent Infrastructure Landscape</name></author>
${entries.join('\n')}
</feed>
`;
}
for (const r of records) {
  const evs = history.records?.[r.id] ?? [];
  const self = `${baseUrl}/feeds/${r.id}.xml`;
  write(`feeds/${r.id}.xml`, feed({
    title: `${r.name} — catalog changes`,
    subtitle: `Lifecycle, licence, release, pricing and hosting changes to ${r.name} in the AI Agent Infrastructure Landscape.`,
    self, alt: `${baseUrl}/systems/${r.id}`,
    updated: iso(evs[0]?.date ?? r.last_verified_at ?? history.baseline ?? '2026-01-01'),
    entries: evs.map((ev) => entry(r.id, ev))
  }));
}
const all = Object.entries(history.records ?? {})
  .flatMap(([id, evs]) => evs.map((ev) => ({ id, ev })))
  .sort((a, b) => b.ev.date.localeCompare(a.ev.date) || a.id.localeCompare(b.id))
  .slice(0, 100);
write('changes.xml', feed({
  title: 'AI Agent Infrastructure Landscape — changes',
  subtitle: 'The latest 100 lifecycle, licence, release, pricing and hosting changes across the catalog.',
  self: `${baseUrl}/changes.xml`, alt: `${baseUrl}/`,
  updated: iso(all[0]?.ev.date ?? '2026-01-01'),
  entries: all.map(({ id, ev }) => entry(id, ev))
}));

// ---- llms.txt ----------------------------------------------------------------
const famLines = catalogs.filter((c) => c.id !== 'all')
  .map((c) => `- [${c.name}](${PUBLIC}/api/catalogs/${c.id}.json) (${c.count} systems; [CSV](${PUBLIC}/api/catalogs/${c.id}.csv))`).join('\n');
write('llms.txt', `# AI Agent Infrastructure Landscape

> Open, citation-backed catalog of ${records.length} AI agent systems: memory layers, agent frameworks, vector and graph stores, models and ops tooling. Every cell links to its source and carries a verifiability tier. ${edges.length} typed edges connect the systems. Data is CC-BY-4.0.

## Answer a builder's question

- [Choose a memory layer](${PUBLIC}/choose), [an agent framework](${PUBLIC}/choose/framework) or [a vector / graph database](${PUBLIC}/choose/data): a few questions → three cited picks.
- [Check a stack](${PUBLIC}/check): paste package.json / requirements.txt / pyproject.toml / MCP config → archived, acquired or stale dependencies and replacements.
- [Alternatives](${PUBLIC}/alternatives): live alternatives to any memory layer, framework or data store.
- [Ask the catalog](${PUBLIC}/search): plain-language search with requirement checking.
- [Memory cost calculator](${PUBLIC}/costs): monthly cost of managed memory layers from published prices.
- [Benchmarks](${PUBLIC}/benchmarks): reproducible memory benchmark runs vs vendor-reported scores.
- [Compatibility](${PUBLIC}/compatibility): do these systems work together? Integration evidence for every pair, with sources.
- [Compare](${PUBLIC}/compare): head-to-head pages; [compare up to five](${PUBLIC}/compare/many).
- [Findings](${PUBLIC}/findings): headline findings from the catalog.

## Machine-readable data (static JSON, no auth)

- [System index](${PUBLIC}/api/index.json): every system with id, family, section, lifecycle status and a link to its JSON.
- One system: \`${PUBLIC}/api/systems/<id>.json\` — every cell with value, citation, status and tier; taxonomy; edges; change history; lifecycle.
${famLines}
- [Full catalog, flattened](${PUBLIC}/api/catalogs/all.json) ([CSV](${PUBLIC}/api/catalogs/all.csv)); canonical source: [landscape.json](${REPO}/raw/main/data/landscape.json), [edges](${REPO}/raw/main/data/landscape.edges.json).
- [Stack-checker index](${PUBLIC}/api/stack-index.json): npm / PyPI / Docker package and GitHub repo → system and lifecycle status.

## Change feeds

- [All changes (Atom)](${PUBLIC}/changes.xml); one system: \`${PUBLIC}/feeds/<id>.xml\`.
- [Recently verified (Atom)](${PUBLIC}/feed.xml).

## Tools

- [MCP server](${REPO}/tree/main/mcp): ask_catalog, choose_memory_layer, choose_framework_or_store, check_stack, check_compatibility, find_alternatives, system_history, estimate_memory_cost, search_records, compare, recent_changes and more.
- [CLI](${REPO}/tree/main/cli): \`landscape check package.json --fail-on-attention\` for CI.
- [GitHub Action](${REPO}/tree/main/action): \`uses: MrPeppersDev/agent-infrastructure-landscape@main\` flags archived, acquired or stale AI dependencies on pull requests.
- [Hosted MCP endpoint](${REPO}/tree/main/worker): remote, read-only MCP server (Streamable HTTP).

## Optional

- [About: how to read a record](${PUBLIC}/about)
- [Data & API docs](${PUBLIC}/data)
- [Submit a system](${PUBLIC}/submit) · [Correct a record](${REPO}/issues/new?template=correction.yml)
- [Sitemap](${PUBLIC}/sitemap.xml)
`);

console.log(`generate-exports: ${records.length} system JSON + feeds, ${catalogs.length} catalogs, ${all.length} catalog-wide changes, llms.txt`);
