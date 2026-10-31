// GENERATED from mcp/src/stack-check.ts by `make action` — do not edit.
// Stack checker — "is anything in my stack archived, acquired or stale?"
//
// Parses a project's dependency manifest and matches each dependency
// against data/stack-index.json (built by scripts/build_stack_index.py
// from the catalog). Pure and dependency-free so the same file serves
// the MCP server (`check_stack`), the CLI (`landscape check`) and the
// web page (/check), which imports it by relative path.
//
// Supported inputs (auto-detected; pass `format` to force one):
//   package.json             dependencies / devDependencies / peer / optional
//   requirements*.txt        PEP 508 lines, -e / git+https URLs
//   pyproject.toml           [project] dependencies + optional-dependencies,
//                            [tool.poetry.*dependencies]
//   MCP client config JSON   mcpServers.*: npx / uvx / pipx / docker args
//                            (Claude Desktop, Claude Code .mcp.json, Cursor)
//   plain list               one package per line, optional npm:/pypi: prefix
//   stack.yml                `components:` → `layer: record-id` lines, as
//                            written by the stack composer (composer.ts)
/** Thresholds for a low-health flag, documented in docs/DECISIONS.md (#365). */
export function healthConcerns(h, lastCommit) {
    const why = [];
    if (h.archived)
        why.push('repository archived');
    if (h.issues_90d >= 10 && h.responded_share !== null && h.responded_share < 0.3) {
        why.push(`${Math.round(h.responded_share * 100)}% of the ${h.issues_90d} issues opened in 90 days got a reply or were closed`);
    }
    if (h.releases_12mo === 0) {
        const m = lastCommit?.match(/^(\d{4})-(\d{2})/);
        const asOf = h.as_of.match(/^(\d{4})-(\d{2})/);
        const monthsQuiet = m && asOf ? (Number(asOf[1]) - Number(m[1])) * 12 + (Number(asOf[2]) - Number(m[2])) : null;
        if (monthsQuiet !== null && monthsQuiet >= 6)
            why.push(`no release in 12 months and no commit for ${monthsQuiet} months`);
    }
    if (h.bus_factor === 1 && (h.top_contributor_share ?? 0) >= 0.8)
        why.push(`one contributor wrote ${Math.round((h.top_contributor_share ?? 0) * 100)}% of sampled commits`);
    return why;
}
const LINK_TYPES = new Set(['integrates-with', 'built-on', 'runtime-dependency', 'extends']);
/** Build the integration-link map from catalog edges (served to the
 * GitHub Action as /api/integration-links.json). */
export function linksFromEdges(edges) {
    const m = new Map();
    const add = (a, b) => (m.get(a) ?? m.set(a, new Set()).get(a)).add(b);
    for (const e of edges) {
        if (!LINK_TYPES.has(e.type) || e.source === e.target)
            continue;
        add(e.source, e.target);
        add(e.target, e.source);
    }
    return Object.fromEntries([...m].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, [...v].sort()]));
}
// ---------------------------------------------------------------------------
// Normalisation
// ---------------------------------------------------------------------------
export function normalisePackage(eco, name) {
    let n = name.trim().toLowerCase();
    if (eco === 'pypi')
        n = n.replace(/[-_.]+/g, '-'); // PEP 503
    if (eco === 'docker')
        n = n.replace(/^docker\.io\//, '').replace(/^library\//, '').replace(/[:@].*$/, '');
    return `${eco}:${n}`;
}
function repoKey(url) {
    const m = url.match(/github\.com[/:]([\w.-]+)\/([\w.-]+?)(?:\.git)?(?:[#/@?].*)?$/i);
    return m ? `${m[1].toLowerCase()}/${m[2].toLowerCase()}` : null;
}
// ---------------------------------------------------------------------------
// Parsers
// ---------------------------------------------------------------------------
function parsePackageJson(obj) {
    const out = [];
    for (const field of ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']) {
        const deps = obj[field];
        if (!deps || typeof deps !== 'object')
            continue;
        for (const [name, spec] of Object.entries(deps)) {
            const s = String(spec ?? '');
            const repo = /github\.com|^github:|^[\w.-]+\/[\w.-]+(#.*)?$/.test(s) ? s : null;
            out.push({ ecosystem: 'npm', name, spec: s, source: field });
            if (repo) {
                const k = repo.startsWith('github:') ? repo.slice(7) : repo;
                out.push({ ecosystem: 'git', name: k.includes('github.com') ? k : `github.com/${k}`, spec: s, source: field });
            }
        }
    }
    return out;
}
const PEP508 = /^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)$/;
function parsePep508(line, source) {
    const l = line.replace(/\s+#.*$/, '').trim();
    if (!l || l.startsWith('#') || l.startsWith('-r') || l.startsWith('-c') || l.startsWith('--'))
        return null;
    const git = l.match(/(git\+)?https?:\/\/[^\s;]+/);
    if (git && /github\.com/i.test(git[0])) {
        return { ecosystem: 'git', name: git[0].replace(/^git\+/, ''), spec: l, source };
    }
    const e = l.replace(/^-e\s+/, '');
    const m = e.match(PEP508);
    if (!m)
        return null;
    const name = m[1].split('@')[0].trim();
    return { ecosystem: 'pypi', name, spec: (m[3] || '').trim() || undefined, source };
}
function parseRequirements(text) {
    return text
        .split(/\r?\n/)
        .map((l) => parsePep508(l, 'requirements'))
        .filter((d) => d !== null);
}
/** Minimal TOML reader: only the dependency tables we need. */
function parsePyproject(text) {
    const out = [];
    let table = '';
    const lines = text.split(/\r?\n/);
    for (let i = 0; i < lines.length; i++) {
        const raw = lines[i];
        const line = raw.replace(/\s+#.*$/, '').trim();
        const t = line.match(/^\[\[?([^\]]+)\]\]?$/);
        if (t) {
            table = t[1].trim();
            continue;
        }
        // [project] dependencies = [ ... ] and [project.optional-dependencies] x = [ ... ]
        const arr = line.match(/^([\w.-]+|"[^"]+")\s*=\s*\[(.*)$/);
        if (arr && (table === 'project' && arr[1] === 'dependencies' || table === 'project.optional-dependencies'
            || table === 'dependency-groups' || table === 'build-system' && arr[1] === 'requires')) {
            let body = arr[2];
            while (!body.includes(']') && i + 1 < lines.length)
                body += '\n' + lines[++i];
            body = body.slice(0, body.lastIndexOf(']'));
            for (const s of body.matchAll(/"([^"]+)"|'([^']+)'/g)) {
                const d = parsePep508(s[1] ?? s[2], `${table}.${arr[1]}`);
                if (d)
                    out.push(d);
            }
            continue;
        }
        // [tool.poetry.dependencies] name = "^1.0" / { version = ..., git = ... }
        if (/^tool\.poetry\.(group\.[\w-]+\.)?(dev-)?dependencies$/.test(table)) {
            const kv = line.match(/^([A-Za-z0-9._-]+)\s*=\s*(.+)$/);
            if (kv && kv[1].toLowerCase() !== 'python') {
                const git = kv[2].match(/git\s*=\s*"([^"]+)"/);
                out.push(git ? { ecosystem: 'git', name: git[1], spec: kv[2], source: table }
                    : { ecosystem: 'pypi', name: kv[1], spec: kv[2].replace(/^"|"$/g, ''), source: table });
            }
        }
    }
    return out;
}
/** Package launched by an MCP server entry: npx / uvx / pipx / docker. */
function parseMcpServer(name, cfg) {
    const cmd = String(cfg.command ?? '');
    const args = Array.isArray(cfg.args) ? cfg.args.map(String) : [];
    const source = `mcpServers.${name}`;
    const firstPositional = (xs, skipWithValue = []) => {
        for (let i = 0; i < xs.length; i++) {
            const a = xs[i];
            if (skipWithValue.includes(a)) {
                i++;
                continue;
            }
            if (a.startsWith('-'))
                continue;
            return a;
        }
        return undefined;
    };
    const base = cmd.split(/[\\/]/).pop() ?? cmd;
    const full = [base, ...args];
    const spec = full.join(' ');
    if (/^(npx|bunx|pnpx)$/.test(base) || (base === 'pnpm' && args[0] === 'dlx') || (base === 'npm' && args[0] === 'exec')) {
        const rest = base === 'pnpm' || base === 'npm' ? args.slice(1) : args;
        const pkg = firstPositional(rest, ['-p', '--package']);
        if (pkg) {
            if (pkg.startsWith('github:'))
                return [{ ecosystem: 'git', name: `github.com/${pkg.slice(7)}`, spec, source }];
            return [{ ecosystem: 'npm', name: pkg.replace(/(?<=.)@[^/@]*$/, ''), spec, source }];
        }
    }
    if (base === 'uvx' || (base === 'uv' && args[0] === 'tool' && args[1] === 'run') || (base === 'pipx' && args[0] === 'run')) {
        const rest = base === 'uvx' ? args : args.slice(base === 'uv' ? 2 : 1);
        const from = rest.indexOf('--from');
        const pkg = from >= 0 ? rest[from + 1] : firstPositional(rest, ['--python', '--with']);
        if (pkg) {
            const d = parsePep508(pkg.replace(/==.*$/, ''), source);
            if (d)
                return [{ ...d, spec, source }];
        }
    }
    if (base === 'docker' || base === 'podman') {
        const run = args.indexOf('run');
        if (run >= 0) {
            const image = firstPositional(args.slice(run + 1), ['-e', '--env', '-v', '--volume', '-p', '--name', '--network', '--env-file', '-w']);
            if (image)
                return [{ ecosystem: 'docker', name: image, spec, source }];
        }
    }
    const pyMod = base.startsWith('python') && args[0] === '-m' ? args[1] : undefined;
    if (pyMod)
        return [{ ecosystem: 'pypi', name: pyMod.replace(/_/g, '-'), spec, source }];
    // A bare command that is itself a package binary (e.g. "mcp-server-x").
    if (cmd && !/^(node|python3?|bash|sh|cmd|uv|deno|bun)$/.test(base) && !/[\\/]/.test(cmd)) {
        return [{ ecosystem: 'unknown', name: base, spec, source }];
    }
    return [];
}
function parseMcpConfig(obj) {
    const servers = (obj.mcpServers ?? obj.mcp?.servers ?? obj.servers);
    if (!servers || typeof servers !== 'object')
        return [];
    const out = [];
    for (const [name, cfg] of Object.entries(servers)) {
        if (cfg && typeof cfg === 'object')
            out.push(...parseMcpServer(name, cfg));
    }
    return out;
}
function parsePlainList(text) {
    const out = [];
    for (const raw of text.split(/[\r\n,]+/)) {
        const l = raw.trim();
        if (!l || l.startsWith('#'))
            continue;
        const pre = l.match(/^(npm|pypi|docker|git):(.+)$/i);
        if (pre) {
            out.push({ ecosystem: pre[1].toLowerCase(), name: pre[2].trim(), source: 'list' });
        }
        else if (/github\.com\//i.test(l)) {
            out.push({ ecosystem: 'git', name: l, source: 'list' });
        }
        else {
            out.push({ ecosystem: 'unknown', name: l.split(/[\s=<>~!;@]/)[0] || l, spec: l, source: 'list' });
        }
    }
    return out;
}
/** A stack file from the composer: catalog record ids under `components:`.
 * Only that block is read; everything else in the file is ignored. */
function parseStackFile(text) {
    const out = [];
    let inComponents = false;
    for (const raw of text.split(/\r?\n/)) {
        const line = raw.replace(/\s+#.*$/, '');
        if (!line.trim() || line.trim().startsWith('#'))
            continue;
        if (/^\S/.test(line)) {
            inComponents = /^components:\s*$/.test(line);
            continue;
        }
        if (!inComponents)
            continue;
        const m = line.match(/^\s+([\w-]+):\s*([\w.-]+)\s*$/);
        if (m)
            out.push({ ecosystem: 'record', name: m[2], source: `components.${m[1]}` });
    }
    return out;
}
export function parseManifest(text, opts = {}) {
    const fname = (opts.filename ?? '').toLowerCase();
    let format = opts.format;
    let json = null;
    const trimmed = text.trim();
    if (!format || format === 'package.json' || format === 'mcp-config') {
        if (trimmed.startsWith('{')) {
            try {
                json = JSON.parse(trimmed.replace(/^﻿/, ''));
            }
            catch {
                json = null;
            }
        }
    }
    if (!format) {
        if (json && (json.mcpServers || json.mcp?.servers || json.servers))
            format = 'mcp-config';
        else if (json)
            format = 'package.json';
        else if (/(^|\/)stack\.ya?ml$/.test(fname) || (/^components:\s*$/m.test(text) && /^version:\s*1\s*$/m.test(text)))
            format = 'stack.yml';
        else if (fname.endsWith('.toml') || /^\s*\[(project|tool\.poetry|build-system)/m.test(text))
            format = 'pyproject.toml';
        else if (fname.includes('requirements') || /^[A-Za-z0-9._-]+(\[[^\]]*\])?\s*(==|>=|<=|~=|!=|<|>)/m.test(text))
            format = 'requirements.txt';
        else
            format = 'list';
    }
    let deps = [];
    if (format === 'mcp-config' && json)
        deps = parseMcpConfig(json);
    else if (format === 'package.json' && json)
        deps = parsePackageJson(json);
    else if (format === 'pyproject.toml')
        deps = parsePyproject(text);
    else if (format === 'requirements.txt')
        deps = parseRequirements(text);
    else if (format === 'stack.yml')
        deps = parseStackFile(text);
    else
        deps = parsePlainList(text);
    // de-duplicate on ecosystem + name
    const seen = new Set();
    deps = deps.filter((d) => {
        const k = `${d.ecosystem}:${d.name.toLowerCase()}`;
        if (seen.has(k))
            return false;
        seen.add(k);
        return true;
    });
    return { format, dependencies: deps };
}
// ---------------------------------------------------------------------------
// Matching
// ---------------------------------------------------------------------------
function lookup(dep, index) {
    const tryKey = (k, by) => (index.packages[k] ? { id: index.packages[k], by } : null);
    if (dep.ecosystem === 'record')
        return index.records[dep.name] ? { id: dep.name, by: 'record id' } : null;
    if (dep.ecosystem === 'git') {
        const rk = repoKey(dep.name);
        return rk && index.repos[rk] ? { id: index.repos[rk], by: `github:${rk}` } : null;
    }
    if (dep.ecosystem === 'unknown') {
        return tryKey(normalisePackage('npm', dep.name), 'npm') ?? tryKey(normalisePackage('pypi', dep.name), 'pypi');
    }
    const direct = tryKey(normalisePackage(dep.ecosystem, dep.name), dep.ecosystem);
    if (direct)
        return direct;
    if (dep.ecosystem === 'docker') {
        // ghcr.io/owner/repo → GitHub repo
        const m = dep.name.match(/^ghcr\.io\/([\w.-]+)\/([\w.-]+)/i);
        if (m && index.repos[`${m[1].toLowerCase()}/${m[2].toLowerCase()}`]) {
            return { id: index.repos[`${m[1].toLowerCase()}/${m[2].toLowerCase()}`], by: 'ghcr' };
        }
    }
    return null;
}
const ALL_STATUSES = ['dead', 'archived', 'deprecated', 'maintenance', 'inactive', 'stale',
    'acquired', 'renamed', 'research-code', 'active'];
export function checkStack(deps, index, format = 'list', opts = {}) {
    const matched = [];
    const unmatched = [];
    for (const d of deps) {
        const hit = lookup(d, index);
        const rec = hit ? index.records[hit.id] : undefined;
        if (hit && rec) {
            const f = { dependency: d, matchedBy: hit.by, recordId: hit.id, record: rec };
            const alts = rec.severity >= 2 ? opts.replacements?.[hit.id] : undefined;
            // Up to six candidates arrive; the advisor re-ranks them, then three are kept.
            if (alts?.length)
                f.replacements = alts.slice(0, opts.links ? 6 : 3).map(({ id, name, why }) => ({ id, name, why }));
            matched.push(f);
        }
        else
            unmatched.push(d);
    }
    if (opts.links)
        adviseUpgrades(matched, opts.links);
    matched.sort((a, b) => b.record.severity - a.record.severity || a.record.name.localeCompare(b.record.name));
    const summary = Object.fromEntries(ALL_STATUSES.map((s) => [s, 0]));
    for (const f of matched)
        summary[f.record.status]++;
    return {
        format,
        dependencyCount: deps.length,
        matched,
        attention: matched.filter((f) => f.record.severity >= 2),
        unmatched,
        summary,
        indexGeneratedAt: index.generatedAt,
        audit: auditStack(matched),
        ...versionDrift(matched),
    };
}
/** Upgrade advisor: for each flagged dependency, prefer replacements with
 * a documented integration with the other matched dependencies, say which,
 * and keep the top three. */
function adviseUpgrades(matched, links) {
    for (const f of matched) {
        if (!f.replacements?.length)
            continue;
        const ranked = f.replacements.map((r, i) => {
            // In the stack's own order, each system once.
            const linked = new Set(links[r.id] ?? []);
            const fits = [...new Set(matched.filter((m) => m.recordId !== f.recordId && linked.has(m.recordId)).map((m) => m.record.name))];
            return { r: fits.length ? { ...r, fits, why: [`works with ${fits.slice(0, 3).join(', ')} in your stack`, ...r.why] } : r, n: fits.length, i };
        });
        ranked.sort((a, b) => b.n - a.n || a.i - b.i);
        f.replacements = ranked.slice(0, 3).map((x) => x.r);
    }
}
/** Order matters: the first definition whose section (and name pattern)
 * matches wins, so `gateway` sits before `serving`. Mirrors the layers of
 * the stack composer (composer.ts) using only what the stack index holds. */
export const AUDIT_LAYERS = [
    { id: 'framework', label: 'Agent framework', role: 'Defines agents, tool calls and control flow in code.', sections: ['Agent frameworks (no first-party memory layer)', 'Multi-agent orchestration platforms'], choose: '/choose/framework' },
    { id: 'orchestration', label: 'Durable execution', role: 'Keeps long-running and multi-agent workflows alive across failures and restarts.', sections: ['Durable execution & workflow engines'], choose: '/choose/framework' },
    { id: 'model', label: 'Foundation model', role: 'The LLM the agents reason with.', sections: ['Foundation models (substrate reference)'], choose: '/build' },
    { id: 'gateway', label: 'Model gateway', role: 'One API in front of every model: routing, fallbacks, caching, budgets and rate limits.', sections: ['Inference platforms & gateways'], match: /gateway|proxy|router|litellm|portkey|openrouter|universal|multi-provider/i, choose: '/build' },
    { id: 'serving', label: 'Model serving', role: 'Runs open-weight models on your own GPUs or a GPU cloud.', sections: ['Inference platforms & gateways'], choose: '/build' },
    { id: 'memory', label: 'Memory layer', role: 'Remembers users, facts and past sessions across conversations.', sections: ['Dedicated memory layers', 'Framework-embedded memory', 'Retrieval-as-memory hybrids', 'Coding-agent memory', 'Platform-provider memory', 'Claude Code memory mechanisms', 'File-backed / editor paradigms', 'Browser-agent memory', 'Personal AI / PKM / lifelogging memory', 'Voice-first / wearable AI memory', 'Vertical / domain-specific AI memory'], choose: '/choose' },
    { id: 'vectors', label: 'Vector store', role: 'Stores embeddings for retrieval (RAG) and semantic search.', sections: ['Vector-database infrastructure', 'Search platforms (non-memory)', 'Enterprise-search adjacencies'], choose: '/choose/data' },
    { id: 'graph', label: 'Knowledge graph', role: 'Stores entities and relationships for graph retrieval.', sections: ['Knowledge-graph platforms'], choose: '/choose/data' },
    { id: 'embeddings', label: 'Embeddings / reranker', role: 'Turns text into vectors and reranks retrieved results.', sections: ['Embedding & reranker services'], choose: '/choose/data' },
    { id: 'tools', label: 'Tools, auth and MCP', role: 'Gives agents authenticated access to external apps and APIs, scoped per user.', sections: ['Agent identity & auth', 'MCP gateways & registries'], choose: '/choose/framework' },
    { id: 'sandbox', label: 'Code sandbox', role: 'Runs agent-generated code in isolation.', sections: ['AI sandbox & runtime environments'], choose: '/choose/framework' },
    { id: 'browser', label: 'Browser / computer use', role: 'Lets agents browse the web or operate a desktop.', sections: ['Computer-use & desktop agents'], choose: '/build' },
    { id: 'voice', label: 'Voice runtime', role: 'Real-time speech in and out: transport, STT, TTS, turn-taking.', sections: ['Voice agent platforms'], choose: '/build' },
    { id: 'observability', label: 'Evals & observability', role: 'Traces every step, runs evaluations, catches regressions.', sections: ['Evaluation & observability platforms', 'Memory observability & monitoring', 'Memory benchmarks & evaluation'], choose: '/build' },
    { id: 'guardrails', label: 'Guardrails & security', role: 'Screens inputs and outputs for prompt injection, data leaks and unsafe actions.', sections: ['Guardrails & AI security', 'Memory governance, privacy & safety'], choose: '/build' }
];
export const AUDIT_LAYER_BY_ID = Object.fromEntries(AUDIT_LAYERS.map((l) => [l.id, l]));
/** Layers every agent product is expected to have; a group counts as
 * covered when any of its layers is present. */
const CORE_LAYERS = [['framework'], ['model', 'gateway', 'serving'], ['memory'], ['tools'], ['observability'], ['guardrails']];
export function auditLayerOf(rec) {
    for (const l of AUDIT_LAYERS) {
        if (!l.sections.includes(rec.section))
            continue;
        if (l.match && !l.match.test(rec.name))
            continue;
        return l.id;
    }
    return 'other';
}
export const LICENCE_LABEL = {
    'open-source': 'Open source',
    'source-available': 'Source-available',
    proprietary: 'Proprietary',
    unknown: 'Licence not recorded'
};
const OSI_RE = /\b(MIT|Apache|BSD|MPL|LGPL|AGPL|GPL|ISC|Unlicense|CC0|CC[- ]BY|PostgreSQL|EPL|Artistic|Zlib|BSL-1\.0)\b/i;
const SOURCE_AVAILABLE_RE = /\b(BSL|Business Source|SSPL|Elastic[- ]?(License|2\.0)|ELv2|FSL|Functional Source|RSAL|Commons Clause|source[- ]available|PolyForm|Server Side Public)\b/i;
const PROPRIETARY_RE = /proprietary|closed|commercial|not open|no public|not OSS|SaaS|custom licen[cs]e|model licen[cs]e|terms of service|all rights reserved/i;
/** Classify a licence cell by its first clause (before ";" or "("); the
 * rest of the cell often lists exceptions. BSL-1.0 is the Boost licence
 * (OSI), not Business Source, so it is tested first. */
export function licenceBucket(licence) {
    const full = (licence ?? '').trim();
    if (!full)
        return { bucket: 'unknown', copyleft: false, mixed: false };
    const first = full.split(/[;(]/)[0].trim();
    const open = OSI_RE.test(first) && !/^\s*(SSPL|BSL(?!-1\.0))/i.test(first);
    const bucket = SOURCE_AVAILABLE_RE.test(first) && !/BSL-1\.0/.test(first)
        ? 'source-available'
        : open
            ? 'open-source'
            : PROPRIETARY_RE.test(first) || PROPRIETARY_RE.test(full)
                ? 'proprietary'
                : 'unknown';
    const rest = full.slice(first.length);
    const mixed = bucket === 'open-source' && (SOURCE_AVAILABLE_RE.test(rest) || PROPRIETARY_RE.test(rest));
    return { bucket, copyleft: /\b(AGPL|GPL|SSPL)\b/i.test(first) && !/\bLGPL\b/i.test(first), mixed };
}
/** Vendor key for concentration: the registrable domain of the record's
 * URL (docs.langchain.com → langchain.com); for code hosts, host + owner. */
export function vendorOf(rec, fallback) {
    const m = (rec.url ?? '').match(/^https?:\/\/(?:www\.)?([^/?#]+)(\/[^/?#]+)?/i);
    if (!m)
        return fallback;
    const host = m[1].toLowerCase();
    if (/^(github\.com|gitlab\.com|huggingface\.co|bitbucket\.org)$/.test(host))
        return host + (m[2] ?? '').toLowerCase();
    const parts = host.split('.');
    return parts.length > 2 ? parts.slice(-2).join('.') : host;
}
export function auditStack(matched) {
    // One entry per system (a manifest can name the same package twice).
    const seen = new Set();
    const systems = matched.filter((f) => (seen.has(f.recordId) ? false : (seen.add(f.recordId), true)));
    const byLayer = new Map();
    for (const f of systems) {
        const layer = auditLayerOf(f.record);
        const row = byLayer.get(layer) ?? { layer, label: AUDIT_LAYER_BY_ID[layer]?.label ?? 'Other catalogued systems', systems: [] };
        row.systems.push({ id: f.recordId, name: f.record.name, status: f.record.status });
        byLayer.set(layer, row);
    }
    const order = [...AUDIT_LAYERS.map((l) => l.id), 'other'];
    const layers = order.filter((l) => byLayer.has(l)).map((l) => byLayer.get(l));
    const have = new Set(layers.map((l) => l.layer));
    const missing = systems.length >= 2
        ? CORE_LAYERS.filter((group) => !group.some((l) => have.has(l))).map((group) => {
            const d = AUDIT_LAYER_BY_ID[group[0]];
            return { layer: d.id, label: group.length > 1 ? 'Model, gateway or serving' : d.label, role: d.role, choose: d.choose };
        })
        : [];
    const vendors = new Map();
    for (const f of systems) {
        const layer = auditLayerOf(f.record);
        if (layer === 'other')
            continue;
        const v = vendorOf(f.record, f.recordId);
        const row = vendors.get(v) ?? { layers: new Set(), systems: [] };
        row.layers.add(layer);
        row.systems.push(f.record.name);
        vendors.set(v, row);
    }
    const concentration = [...vendors]
        .filter(([, v]) => v.layers.size >= 2)
        .map(([vendor, v]) => ({ vendor, layers: order.filter((l) => v.layers.has(l)), systems: v.systems }))
        .sort((a, b) => b.layers.length - a.layers.length || a.vendor.localeCompare(b.vendor));
    const buckets = new Map();
    for (const f of systems) {
        const lb = licenceBucket(f.record.license);
        const row = buckets.get(lb.bucket) ?? { bucket: lb.bucket, systems: [] };
        row.systems.push({ id: f.recordId, name: f.record.name, licence: f.record.license, copyleft: lb.copyleft, mixed: lb.mixed });
        buckets.set(lb.bucket, row);
    }
    const bucketOrder = ['open-source', 'source-available', 'proprietary', 'unknown'];
    const licences = bucketOrder.filter((b) => buckets.has(b)).map((b) => buckets.get(b));
    const yaml = [
        '# Stack detected from your manifest by the AI Agent Infrastructure Landscape (stack audit).',
        '# Check it any time: npx landscape check stack.yml, or the "AI stack check" GitHub Action.',
        'version: 1',
        'components:'
    ];
    for (const l of layers) {
        if (l.layer === 'other')
            continue;
        const [first, ...rest] = l.systems;
        yaml.push(`  ${l.layer}: ${first.id}  # ${first.name.replace(/#/g, '')}`);
        for (const r of rest)
            yaml.push(`  # also ${l.layer}: ${r.id}  # ${r.name.replace(/#/g, '')}`);
    }
    const health = [];
    let healthUnknown = 0;
    for (const f of systems) {
        const h = f.record.health;
        if (!h) {
            healthUnknown++;
            continue;
        }
        const why = healthConcerns(h, f.record.last_commit);
        if (why.length)
            health.push({ id: f.recordId, name: f.record.name, asOf: h.as_of, why });
    }
    return { layers, missing, concentration, licences, stackYaml: yaml.join('\n') + '\n', health, healthUnknown };
}
export function pinnedVersion(spec) {
    const s = (spec ?? '').trim();
    if (!s || /^(latest|\*|x|next|workspace:|file:|link:|git\+|https?:)/i.test(s))
        return null;
    // Take the first clause of a range ("^1.2 || ^2.0", ">=1,<2").
    const first = s.split(/\s*(?:\|\||,)\s*/)[0];
    const m = first.match(/(\d+)(?:\.(\d+|x|\*))?(?:\.(\d+|x|\*))?/);
    if (!m)
        return null;
    const num = (x) => (x === undefined || x === 'x' || x === '*' ? null : Number(x));
    const op = first.slice(0, m.index).trim();
    const unbounded = /^(>=?|!=)$/.test(op) && !/<|==|~=|\^|~/.test(s);
    return { major: Number(m[1]), minor: num(m[2]), patch: num(m[3]), unbounded };
}
function versionDrift(matched) {
    const drift = [];
    let noVersionData = 0;
    for (const f of matched) {
        if (f.dependency.ecosystem !== 'npm' && f.dependency.ecosystem !== 'pypi')
            continue;
        const latest = f.record.latest_release;
        if (!latest) {
            noVersionData++;
            continue;
        }
        const pinned = pinnedVersion(f.dependency.spec);
        if (!pinned || pinned.unbounded)
            continue;
        const lm = latest.version.match(/^(\d+)\.(\d+)/);
        if (!lm)
            continue;
        const lMajor = Number(lm[1]), lMinor = Number(lm[2]);
        const when = latest.date ? ` (${latest.date})` : '';
        if (pinned.major < lMajor) {
            drift.push({ dependency: f.dependency, recordId: f.recordId, name: f.record.name, pinned, latest, level: 'behind-major',
                note: `pinned to ${pinned.major}.x; the catalog's latest release is ${latest.version}${when}` });
        }
        else if (pinned.major === 0 && lMajor === 0 && pinned.minor !== null && pinned.minor < lMinor) {
            drift.push({ dependency: f.dependency, recordId: f.recordId, name: f.record.name, pinned, latest, level: 'behind-minor',
                note: `pinned to 0.${pinned.minor}; on a 0.x line every minor can break, and the catalog's latest release is ${latest.version}${when}` });
        }
    }
    drift.sort((a, b) => (a.level === b.level ? a.name.localeCompare(b.name) : a.level === 'behind-major' ? -1 : 1));
    return { drift, noVersionData };
}
export function checkManifest(text, index, opts = {}) {
    const { format, dependencies } = parseManifest(text, opts);
    return checkStack(dependencies, index, format, opts);
}
/** Record ids in the index that need attention (severity >= 2) — the ones
 * worth precomputing replacements for. */
export function attentionIds(index) {
    return Object.entries(index.records).filter(([, r]) => r.severity >= 2).map(([id]) => id);
}
export const STATUS_LABEL = {
    dead: 'Shut down',
    archived: 'Archived',
    deprecated: 'Deprecated',
    maintenance: 'Maintenance mode',
    inactive: 'Inactive',
    stale: 'Stale (no commits in 12+ months)',
    acquired: 'Acquired',
    renamed: 'Renamed',
    'research-code': 'Research code',
    active: 'Active',
};
