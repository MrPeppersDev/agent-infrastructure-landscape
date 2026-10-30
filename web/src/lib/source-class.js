// Source class of a citation (#333): who published the page a cell cites.
// Derived at build time from the citation URL and the record, never stored
// in landscape.json. Plain JS so the exports script (node) and the site
// (TypeScript) share one implementation.
//
//   vendor       the system's own site or docs (its domain, a domain named
//                after it or its GitHub org, or a listed alias)
//   repo         a code host (GitHub, GitLab, Bitbucket)
//   registry     a package or model registry (PyPI, npm, Hugging Face, …)
//   paper        a paper index (arXiv, ACL Anthology, OpenReview, …)
//   third-party  anything else: press, analysts, other vendors, wikis
//   catalog      this catalog's own pages (derived cells); not a source

/** @typedef {'vendor' | 'repo' | 'registry' | 'paper' | 'third-party' | 'catalog'} SourceClass */

/** @type {SourceClass[]} */
export const SOURCE_CLASSES = ['vendor', 'repo', 'registry', 'paper', 'third-party', 'catalog'];

/** @type {Record<SourceClass, string>} */
export const SOURCE_LABEL = {
  vendor: 'vendor',
  repo: 'repo',
  registry: 'registry',
  paper: 'paper',
  'third-party': 'third-party',
  catalog: 'catalog'
};

/** @type {Record<SourceClass, string>} */
export const SOURCE_TITLE = {
  vendor: "The system's own site or docs: a vendor-stated claim",
  repo: 'A code repository (usually the project’s own)',
  registry: 'A package or model registry listing',
  paper: 'A paper or paper index',
  'third-party': 'A source not published by the vendor: press, analysts, other vendors',
  catalog: 'Derived by this catalog'
};

const REPO = ['github.com', 'raw.githubusercontent.com', 'gist.github.com', 'gitlab.com', 'bitbucket.org', 'codeberg.org'];
const REGISTRY = ['pypi.org', 'npmjs.com', 'huggingface.co', 'crates.io', 'pkg.go.dev', 'rubygems.org', 'nuget.org', 'hub.docker.com', 'mvnrepository.com', 'central.sonatype.com', 'marketplace.visualstudio.com', 'registry.modelcontextprotocol.io'];
const PAPER = ['arxiv.org', 'aclanthology.org', 'openreview.net', 'semanticscholar.org', 'proceedings.neurips.cc', 'proceedings.mlr.press', 'papers.nips.cc', 'dl.acm.org', 'ieeexplore.ieee.org', 'nature.com', 'science.org', 'biorxiv.org', 'medrxiv.org', 'ssrn.com', 'doi.org', 'paperswithcode.com', 'scholar.google.com'];
const CATALOG = ['mrpeppersdev.github.io'];

// Vendors that publish under several unrelated domains. A citation on any
// domain in a group counts as vendor for a record on any other.
const ALIASES = [
  ['anthropic.com', 'claude.com', 'claude.ai'],
  ['openai.com', 'chatgpt.com'],
  ['google.com', 'google', 'blog.google', 'deepmind.google', 'google.dev', 'googleblog.com', 'withgoogle.com', 'googleapis.com'],
  ['microsoft.com', 'azure.com', 'office.com', 'bing.com'],
  ['amazon.com', 'aws.dev', 'amazon.science'],
  ['meta.com', 'facebook.com', 'llama.com'],
  ['x.ai', 'grok.com']
];

const TWO_PART_SUFFIX = /^(co|com|ac|org|net|gov|edu)\.[a-z]{2}$/;

/** @param {string} host */
function registrable(host) {
  const parts = host.split('.');
  const last2 = parts.slice(-2).join('.');
  return TWO_PART_SUFFIX.test(last2) ? parts.slice(-3).join('.') : last2;
}

/** @param {string} host @param {string[]} list */
function onList(host, list) {
  return list.some((d) => host === d || host.endsWith('.' + d));
}

/** @param {string} s */
const squash = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');

/**
 * The URL a citation points at: its first token, when that is an http(s)
 * URL with a dotted host. Some citations carry a note after the URL
 * ("https://github.com/x/y (inbound: …)"); a few are not URLs at all.
 * @param {string | null | undefined} citation
 * @returns {string | null}
 */
export function citationUrl(citation) {
  const first = String(citation ?? '').trim().split(/\s+/)[0];
  if (!/^https?:\/\//.test(first)) return null;
  try {
    return new URL(first).hostname.includes('.') ? first : null;
  } catch {
    return null;
  }
}

/** @param {string | null | undefined} url */
function parse(url) {
  const href = citationUrl(url);
  if (!href) return null;
  const u = new URL(href);
  return { host: u.hostname.toLowerCase().replace(/^www\./, ''), path: u.pathname };
}

/**
 * Words that identify the vendor: the record name's words, its domain's
 * name and, for a GitHub URL, the org.
 * @param {{ name: string; url: string | null }} record
 */
function vendorKeys(record) {
  const words = record.name
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
  const keys = new Set(words.filter((w) => w.length >= 3));
  // Adjacent words joined: "Roo Code" → roocode, "Physical Intelligence".
  for (let i = 0; i < words.length; i++) {
    for (let n = 2; n <= 3 && i + n <= words.length; n++) keys.add(words.slice(i, i + n).join(''));
  }
  const u = parse(record.url);
  if (u) {
    if (onList(u.host, REPO)) {
      const org = squash(u.path.split('/')[1] ?? '');
      if (org) {
        keys.add(org);
        // All-Hands-AI → allhands, RooCodeInc → roocode.
        keys.add(org.replace(/(ai|inc|hq|labs|dev|io|org|team)$/, ''));
      }
    } else {
      keys.add(squash(registrable(u.host).split('.')[0]));
    }
  }
  keys.delete('');
  return keys;
}

/**
 * @param {string | null | undefined} citation
 * @param {{ name: string; url: string | null }} record
 * @returns {SourceClass | null} null when the citation is not a URL
 */
export function sourceClass(citation, record) {
  const c = parse(citation);
  if (!c) return null;
  const host = c.host;
  if (onList(host, CATALOG)) return 'catalog';
  const rec = parse(record.url);
  const recHost = rec && !onList(rec.host, REPO) ? registrable(rec.host) : null;
  const domain = registrable(host);
  if (recHost && domain === recHost) return 'vendor';
  if (onList(host, REPO)) return 'repo';
  if (onList(host, REGISTRY)) return 'registry';
  if (onList(host, PAPER)) return 'paper';
  for (const group of ALIASES) {
    if (recHost && onList(recHost, group) && onList(host, group)) return 'vendor';
  }
  // A domain named after the system or its GitHub org (mem0.ai for
  // github.com/mem0ai, claude.com for "Anthropic Claude Memory").
  const keys = vendorKeys(record);
  const label = domain.split('.')[0];
  if (keys.has(squash(label)) || keys.has(squash(domain))) return 'vendor';
  // A project site on a code host's pages domain (openai.github.io).
  if (host.endsWith('.github.io') && keys.has(squash(host.split('.')[0]))) return 'vendor';
  return 'third-party';
}

/**
 * Cited real-data cells and how many cite a third-party source.
 * @param {{ name: string; url: string | null; cells: Record<string, { status?: string; citation?: string | null } | undefined> }} record
 */
export function corroboration(record) {
  let cited = 0;
  let thirdParty = 0;
  for (const cell of Object.values(record.cells)) {
    if (!cell || cell.status !== 'real-data') continue;
    const cls = sourceClass(cell.citation, record);
    if (!cls || cls === 'catalog') continue;
    cited++;
    if (cls === 'third-party') thirdParty++;
  }
  return { cited, thirdParty };
}
