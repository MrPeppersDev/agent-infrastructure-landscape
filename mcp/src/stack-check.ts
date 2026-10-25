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

export type Ecosystem = 'npm' | 'pypi' | 'docker' | 'git' | 'unknown';

export interface Dependency {
  ecosystem: Ecosystem;
  name: string;
  /** Version spec or command as written, for display. */
  spec?: string;
  /** Where in the manifest it came from (e.g. "devDependencies", "mcpServers.memory"). */
  source?: string;
}

export type StackStatus =
  | 'dead'
  | 'archived'
  | 'deprecated'
  | 'maintenance'
  | 'inactive'
  | 'stale'
  | 'acquired'
  | 'renamed'
  | 'research-code'
  | 'active';

export interface IndexRecord {
  name: string;
  family: string;
  section: string;
  url: string | null;
  license: string;
  llm_lock: string;
  status: StackStatus;
  severity: number;
  note: string;
  context: string;
  evidence: string | null;
  last_commit: string | null;
}

export interface StackIndex {
  generatedAt: string;
  packages: Record<string, string>;
  repos: Record<string, string>;
  records: Record<string, IndexRecord>;
}

/** A suggested replacement (computed by chooser.alternatives). */
export interface Replacement {
  id: string;
  name: string;
  why: string[];
}

export interface Finding {
  dependency: Dependency;
  matchedBy: string;
  recordId: string;
  record: IndexRecord;
  /** Live alternatives, for dependencies that need attention. */
  replacements?: Replacement[];
}

export interface CheckOptions {
  /** recordId → suggested replacements (see chooser.alternativesFor). */
  replacements?: Record<string, Replacement[]>;
}

export interface StackReport {
  format: string;
  dependencyCount: number;
  matched: Finding[];
  /** Matched with severity >= 2 (needs attention), most severe first. */
  attention: Finding[];
  unmatched: Dependency[];
  summary: Record<StackStatus, number>;
  indexGeneratedAt: string;
}

// ---------------------------------------------------------------------------
// Normalisation
// ---------------------------------------------------------------------------

export function normalisePackage(eco: Ecosystem, name: string): string {
  let n = name.trim().toLowerCase();
  if (eco === 'pypi') n = n.replace(/[-_.]+/g, '-'); // PEP 503
  if (eco === 'docker') n = n.replace(/^docker\.io\//, '').replace(/^library\//, '').replace(/[:@].*$/, '');
  return `${eco}:${n}`;
}

function repoKey(url: string): string | null {
  const m = url.match(/github\.com[/:]([\w.-]+)\/([\w.-]+?)(?:\.git)?(?:[#/@?].*)?$/i);
  return m ? `${m[1].toLowerCase()}/${m[2].toLowerCase()}` : null;
}

// ---------------------------------------------------------------------------
// Parsers
// ---------------------------------------------------------------------------

function parsePackageJson(obj: Record<string, unknown>): Dependency[] {
  const out: Dependency[] = [];
  for (const field of ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']) {
    const deps = obj[field];
    if (!deps || typeof deps !== 'object') continue;
    for (const [name, spec] of Object.entries(deps as Record<string, unknown>)) {
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

function parsePep508(line: string, source: string): Dependency | null {
  const l = line.replace(/\s+#.*$/, '').trim();
  if (!l || l.startsWith('#') || l.startsWith('-r') || l.startsWith('-c') || l.startsWith('--')) return null;
  const git = l.match(/(git\+)?https?:\/\/[^\s;]+/);
  if (git && /github\.com/i.test(git[0])) {
    return { ecosystem: 'git', name: git[0].replace(/^git\+/, ''), spec: l, source };
  }
  const e = l.replace(/^-e\s+/, '');
  const m = e.match(PEP508);
  if (!m) return null;
  const name = m[1].split('@')[0].trim();
  return { ecosystem: 'pypi', name, spec: (m[3] || '').trim() || undefined, source };
}

function parseRequirements(text: string): Dependency[] {
  return text
    .split(/\r?\n/)
    .map((l) => parsePep508(l, 'requirements'))
    .filter((d): d is Dependency => d !== null);
}

/** Minimal TOML reader: only the dependency tables we need. */
function parsePyproject(text: string): Dependency[] {
  const out: Dependency[] = [];
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
      while (!body.includes(']') && i + 1 < lines.length) body += '\n' + lines[++i];
      body = body.slice(0, body.lastIndexOf(']'));
      for (const s of body.matchAll(/"([^"]+)"|'([^']+)'/g)) {
        const d = parsePep508(s[1] ?? s[2], `${table}.${arr[1]}`);
        if (d) out.push(d);
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
function parseMcpServer(name: string, cfg: Record<string, unknown>): Dependency[] {
  const cmd = String(cfg.command ?? '');
  const args = Array.isArray(cfg.args) ? cfg.args.map(String) : [];
  const source = `mcpServers.${name}`;
  const firstPositional = (xs: string[], skipWithValue: string[] = []) => {
    for (let i = 0; i < xs.length; i++) {
      const a = xs[i];
      if (skipWithValue.includes(a)) { i++; continue; }
      if (a.startsWith('-')) continue;
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
      if (pkg.startsWith('github:')) return [{ ecosystem: 'git', name: `github.com/${pkg.slice(7)}`, spec, source }];
      return [{ ecosystem: 'npm', name: pkg.replace(/(?<=.)@[^/@]*$/, ''), spec, source }];
    }
  }
  if (base === 'uvx' || (base === 'uv' && args[0] === 'tool' && args[1] === 'run') || (base === 'pipx' && args[0] === 'run')) {
    const rest = base === 'uvx' ? args : args.slice(base === 'uv' ? 2 : 1);
    const from = rest.indexOf('--from');
    const pkg = from >= 0 ? rest[from + 1] : firstPositional(rest, ['--python', '--with']);
    if (pkg) {
      const d = parsePep508(pkg.replace(/==.*$/, ''), source);
      if (d) return [{ ...d, spec, source }];
    }
  }
  if (base === 'docker' || base === 'podman') {
    const run = args.indexOf('run');
    if (run >= 0) {
      const image = firstPositional(args.slice(run + 1), ['-e', '--env', '-v', '--volume', '-p', '--name', '--network', '--env-file', '-w']);
      if (image) return [{ ecosystem: 'docker', name: image, spec, source }];
    }
  }
  const pyMod = base.startsWith('python') && args[0] === '-m' ? args[1] : undefined;
  if (pyMod) return [{ ecosystem: 'pypi', name: pyMod.replace(/_/g, '-'), spec, source }];
  // A bare command that is itself a package binary (e.g. "mcp-server-x").
  if (cmd && !/^(node|python3?|bash|sh|cmd|uv|deno|bun)$/.test(base) && !/[\\/]/.test(cmd)) {
    return [{ ecosystem: 'unknown', name: base, spec, source }];
  }
  return [];
}

function parseMcpConfig(obj: Record<string, unknown>): Dependency[] {
  const servers = (obj.mcpServers ?? (obj.mcp as Record<string, unknown> | undefined)?.servers ?? obj.servers) as
    | Record<string, unknown>
    | undefined;
  if (!servers || typeof servers !== 'object') return [];
  const out: Dependency[] = [];
  for (const [name, cfg] of Object.entries(servers)) {
    if (cfg && typeof cfg === 'object') out.push(...parseMcpServer(name, cfg as Record<string, unknown>));
  }
  return out;
}

function parsePlainList(text: string): Dependency[] {
  const out: Dependency[] = [];
  for (const raw of text.split(/[\r\n,]+/)) {
    const l = raw.trim();
    if (!l || l.startsWith('#')) continue;
    const pre = l.match(/^(npm|pypi|docker|git):(.+)$/i);
    if (pre) {
      out.push({ ecosystem: pre[1].toLowerCase() as Ecosystem, name: pre[2].trim(), source: 'list' });
    } else if (/github\.com\//i.test(l)) {
      out.push({ ecosystem: 'git', name: l, source: 'list' });
    } else {
      out.push({ ecosystem: 'unknown', name: l.split(/[\s=<>~!;@]/)[0] || l, spec: l, source: 'list' });
    }
  }
  return out;
}

export type ManifestFormat = 'package.json' | 'requirements.txt' | 'pyproject.toml' | 'mcp-config' | 'list';

export function parseManifest(text: string, opts: { filename?: string; format?: ManifestFormat } = {}): {
  format: ManifestFormat;
  dependencies: Dependency[];
} {
  const fname = (opts.filename ?? '').toLowerCase();
  let format = opts.format;
  let json: Record<string, unknown> | null = null;
  const trimmed = text.trim();
  if (!format || format === 'package.json' || format === 'mcp-config') {
    if (trimmed.startsWith('{')) {
      try {
        json = JSON.parse(trimmed.replace(/^﻿/, ''));
      } catch {
        json = null;
      }
    }
  }
  if (!format) {
    if (json && (json.mcpServers || (json.mcp as Record<string, unknown> | undefined)?.servers || json.servers)) format = 'mcp-config';
    else if (json) format = 'package.json';
    else if (fname.endsWith('.toml') || /^\s*\[(project|tool\.poetry|build-system)/m.test(text)) format = 'pyproject.toml';
    else if (fname.includes('requirements') || /^[A-Za-z0-9._-]+(\[[^\]]*\])?\s*(==|>=|<=|~=|!=|<|>)/m.test(text)) format = 'requirements.txt';
    else format = 'list';
  }
  let deps: Dependency[] = [];
  if (format === 'mcp-config' && json) deps = parseMcpConfig(json);
  else if (format === 'package.json' && json) deps = parsePackageJson(json);
  else if (format === 'pyproject.toml') deps = parsePyproject(text);
  else if (format === 'requirements.txt') deps = parseRequirements(text);
  else deps = parsePlainList(text);
  // de-duplicate on ecosystem + name
  const seen = new Set<string>();
  deps = deps.filter((d) => {
    const k = `${d.ecosystem}:${d.name.toLowerCase()}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  return { format, dependencies: deps };
}

// ---------------------------------------------------------------------------
// Matching
// ---------------------------------------------------------------------------

function lookup(dep: Dependency, index: StackIndex): { id: string; by: string } | null {
  const tryKey = (k: string, by: string) => (index.packages[k] ? { id: index.packages[k], by } : null);
  if (dep.ecosystem === 'git') {
    const rk = repoKey(dep.name);
    return rk && index.repos[rk] ? { id: index.repos[rk], by: `github:${rk}` } : null;
  }
  if (dep.ecosystem === 'unknown') {
    return tryKey(normalisePackage('npm', dep.name), 'npm') ?? tryKey(normalisePackage('pypi', dep.name), 'pypi');
  }
  const direct = tryKey(normalisePackage(dep.ecosystem, dep.name), dep.ecosystem);
  if (direct) return direct;
  if (dep.ecosystem === 'docker') {
    // ghcr.io/owner/repo → GitHub repo
    const m = dep.name.match(/^ghcr\.io\/([\w.-]+)\/([\w.-]+)/i);
    if (m && index.repos[`${m[1].toLowerCase()}/${m[2].toLowerCase()}`]) {
      return { id: index.repos[`${m[1].toLowerCase()}/${m[2].toLowerCase()}`], by: 'ghcr' };
    }
  }
  return null;
}

const ALL_STATUSES: StackStatus[] = ['dead', 'archived', 'deprecated', 'maintenance', 'inactive', 'stale',
  'acquired', 'renamed', 'research-code', 'active'];

export function checkStack(deps: Dependency[], index: StackIndex, format = 'list', opts: CheckOptions = {}): StackReport {
  const matched: Finding[] = [];
  const unmatched: Dependency[] = [];
  for (const d of deps) {
    const hit = lookup(d, index);
    const rec = hit ? index.records[hit.id] : undefined;
    if (hit && rec) {
      const f: Finding = { dependency: d, matchedBy: hit.by, recordId: hit.id, record: rec };
      const alts = rec.severity >= 2 ? opts.replacements?.[hit.id] : undefined;
      if (alts?.length) f.replacements = alts.map(({ id, name, why }) => ({ id, name, why }));
      matched.push(f);
    }
    else unmatched.push(d);
  }
  matched.sort((a, b) => b.record.severity - a.record.severity || a.record.name.localeCompare(b.record.name));
  const summary = Object.fromEntries(ALL_STATUSES.map((s) => [s, 0])) as Record<StackStatus, number>;
  for (const f of matched) summary[f.record.status]++;
  return {
    format,
    dependencyCount: deps.length,
    matched,
    attention: matched.filter((f) => f.record.severity >= 2),
    unmatched,
    summary,
    indexGeneratedAt: index.generatedAt,
  };
}

export function checkManifest(
  text: string,
  index: StackIndex,
  opts: { filename?: string; format?: ManifestFormat } & CheckOptions = {}
): StackReport {
  const { format, dependencies } = parseManifest(text, opts);
  return checkStack(dependencies, index, format, opts);
}

/** Record ids in the index that need attention (severity >= 2) — the ones
 * worth precomputing replacements for. */
export function attentionIds(index: StackIndex): string[] {
  return Object.entries(index.records).filter(([, r]) => r.severity >= 2).map(([id]) => id);
}

export const STATUS_LABEL: Record<StackStatus, string> = {
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
