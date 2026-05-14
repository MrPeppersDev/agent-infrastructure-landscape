// submit-issue.ts — pure function that builds a GitHub Issue URL from
// the /submit form's state. Per issue #28 (2026-05-13 Option A decision),
// new-system intake is routed through a pre-filled GitHub Issue rather
// than a backend, keeping the web app fully static.
//
// Design constraints:
// - Pure: no DOM, no fetch, no Svelte. The form passes a plain object
//   in and gets back { url, markdown } where `markdown` is exactly the
//   body that the URL will pre-fill (so the review step can render it
//   verbatim without re-deriving anything).
// - No deps: validation is hand-rolled. The form (and tests) consume
//   `validateSubmission` directly.
// - Stable section list: the 33-section catalog is mirrored here so the
//   form does not have to load `landscape.json` just to populate the
//   dropdown. If sections drift, update SECTION_OPTIONS — the source of
//   truth is still `web/landscape.json`.
//
// Reversal cost: low. Pure file; deleting it and the /submit route
// removes the feature with no data dependency.

export type SystemType =
  | 'product'
  | 'framework'
  | 'paper'
  | 'benchmark'
  | 'harness'
  | 'substrate';

export type TierGuess = '' | 'T1' | 'T2' | 'T3' | 'T4' | 'T5';

export interface SubmissionFormState {
  name: string;
  url: string;
  section: string;
  subsection: string;
  type: SystemType | '';
  tierGuess: TierGuess;
  description: string;
  claims: string;
  funding: string;
  customers: string;
  license: string;
  githubUrl: string;
  arxivUrl: string;
  notes: string;
}

export const EMPTY_FORM: SubmissionFormState = {
  name: '',
  url: '',
  section: '',
  subsection: '',
  type: '',
  tierGuess: '',
  description: '',
  claims: '',
  funding: '',
  customers: '',
  license: '',
  githubUrl: '',
  arxivUrl: '',
  notes: ''
};

// Mirrored from web/landscape.json @ Round-6 terminal state. The
// "other / new section" sentinel is appended at the end so authors
// can propose a new top-level bucket via the Subsection field.
export const SECTION_OPTIONS: readonly string[] = [
  'AI sandbox & runtime environments',
  'Agent IDEs & coding harnesses',
  'Agent frameworks (no first-party memory layer)',
  'Browser-agent memory',
  'Claude Code memory mechanisms',
  'Coding-agent memory',
  'Computer-use & desktop agents',
  'Dedicated memory layers',
  'Embedding & reranker services',
  'Enterprise-search adjacencies',
  'Evaluation & observability platforms',
  'File-backed / editor paradigms',
  'Foundation models (substrate reference)',
  'Framework-embedded memory',
  'Inference platforms & gateways',
  'Knowledge-graph platforms',
  'Memory benchmarks & evaluation',
  'Memory governance, privacy & safety',
  'Memory observability & monitoring',
  'Multi-agent orchestration platforms',
  'Personal AI / PKM / lifelogging memory',
  'Platform-provider memory',
  'Recent method papers — theorized, no distinct product',
  'Research / specialised systems',
  'Retrieval-as-memory hybrids',
  'Robotics foundation models & agent stacks',
  'Search platforms (non-memory)',
  'Theoretical / informal — ideas without a paper',
  'Training infrastructure',
  'Use-case-specific agent harnesses',
  'Vector-database infrastructure',
  'Vertical / domain-specific AI memory',
  'Voice agent platforms',
  'Voice-first / wearable AI memory',
  'other / new section'
] as const;

export const TYPE_OPTIONS: ReadonlyArray<{ value: SystemType; label: string }> = [
  { value: 'product', label: 'product (commercial / hosted SaaS)' },
  { value: 'framework', label: 'framework (library / SDK / OSS package)' },
  { value: 'paper', label: 'paper (academic / preprint)' },
  { value: 'benchmark', label: 'benchmark (eval suite / leaderboard)' },
  { value: 'harness', label: 'harness (agent runtime / scaffolding)' },
  { value: 'substrate', label: 'substrate (foundation model / infra primitive)' }
] as const;

export const TIER_OPTIONS: ReadonlyArray<{ value: TierGuess; label: string }> = [
  { value: '', label: '— skip (curators will tier) —' },
  { value: 'T1', label: 'T1 — battle-tested, commercial / mature OSS with real customers' },
  { value: 'T2', label: 'T2 — established / mature OSS, significant traction' },
  { value: 'T3', label: 'T3 — peer-reviewed (ACL/EMNLP/NeurIPS/ICLR/…) with code' },
  { value: 'T4', label: 'T4 — preprint / unpublished, arXiv with implementation' },
  { value: 'T5', label: 'T5 — theoretical / informal, idea-stage, no code' }
] as const;

export const LICENSE_OPTIONS: readonly string[] = [
  '',
  'Apache-2.0',
  'MIT',
  'BSD-3-Clause',
  'BSD-2-Clause',
  'MPL-2.0',
  'GPL-3.0',
  'AGPL-3.0',
  'LGPL-3.0',
  'Elastic-2.0',
  'SSPL-1.0',
  'BSL-1.1',
  'CC-BY-4.0',
  'CC-BY-SA-4.0',
  'Proprietary / closed source',
  'Other (specify in notes)'
] as const;

// --- Validation ---------------------------------------------------------

export interface ValidationResult {
  ok: boolean;
  errors: Partial<Record<keyof SubmissionFormState, string>>;
}

// RFC-loose URL check: scheme + host + at least one dot. We intentionally
// don't use the URL constructor here because we want explicit messages
// per field, and `new URL()` throws are noisy.
const URL_RE = /^https?:\/\/[^\s/$.?#].[^\s]*$/i;

export function validateSubmission(s: SubmissionFormState): ValidationResult {
  const errors: ValidationResult['errors'] = {};

  if (!s.name.trim()) errors.name = 'Required.';
  if (!s.url.trim()) errors.url = 'Required.';
  else if (!URL_RE.test(s.url.trim())) errors.url = 'Must be http(s)://… with a hostname.';

  if (!s.section.trim()) errors.section = 'Required.';
  if (!s.type) errors.type = 'Required.';

  const desc = s.description.trim();
  if (!desc) errors.description = 'Required.';
  else if (desc.length > 240) errors.description = `Keep it under 240 chars (currently ${desc.length}).`;

  if (s.githubUrl.trim() && !URL_RE.test(s.githubUrl.trim())) {
    errors.githubUrl = 'Must be http(s)://… or leave blank.';
  }
  if (s.arxivUrl.trim() && !URL_RE.test(s.arxivUrl.trim())) {
    errors.arxivUrl = 'Must be http(s)://… or leave blank.';
  }

  return { ok: Object.keys(errors).length === 0, errors };
}

// --- Markdown body ------------------------------------------------------
//
// The body that lands in the issue. Format is intentionally a structured
// "Field: value" table-of-sorts so the periodic intake agent (#30) can
// regex-parse it. Empty fields are emitted as `_(not provided)_` so the
// renderer is stable and the human reviewer can see what was skipped.

function field(label: string, value: string): string {
  const v = value.trim();
  return `**${label}:** ${v ? v : '_(not provided)_'}`;
}

function block(label: string, value: string): string {
  const v = value.trim();
  if (!v) return `**${label}:** _(not provided)_`;
  return `**${label}:**\n\n${v}`;
}

export function buildIssueMarkdown(s: SubmissionFormState): string {
  const lines: string[] = [];

  lines.push('## System submission');
  lines.push('');
  lines.push(
    '_Auto-generated by the in-app /submit form. The catalog curator will'
    + ' verify, normalise, and slot this into the next Round-N+1 ingestion.'
    + ' See issues #28 / #30 for the intake pipeline._'
  );
  lines.push('');

  lines.push('### Identity');
  lines.push('');
  lines.push(field('Name', s.name));
  lines.push('');
  lines.push(field('URL', s.url));
  lines.push('');
  lines.push(field('Type', s.type));
  lines.push('');

  lines.push('### Placement');
  lines.push('');
  lines.push(field('Section', s.section));
  lines.push('');
  lines.push(field('Subsection', s.subsection));
  lines.push('');
  lines.push(field('Tier guess', s.tierGuess));
  lines.push('');

  lines.push('### Description');
  lines.push('');
  lines.push(block('Brief description', s.description));
  lines.push('');
  lines.push(block('Claims / pitch', s.claims));
  lines.push('');

  lines.push('### Signals');
  lines.push('');
  lines.push(field('Known funding', s.funding));
  lines.push('');
  lines.push(field('Known customers', s.customers));
  lines.push('');
  lines.push(field('License', s.license));
  lines.push('');
  lines.push(field('GitHub URL', s.githubUrl));
  lines.push('');
  lines.push(field('Arxiv URL', s.arxivUrl));
  lines.push('');

  lines.push('### Submitter notes');
  lines.push('');
  lines.push(block('Notes', s.notes));
  lines.push('');

  lines.push('---');
  lines.push('');
  lines.push('<sub>Submitted via the web-app /submit route. Label: `intake`.</sub>');

  return lines.join('\n');
}

// --- URL assembly -------------------------------------------------------
//
// GitHub's "new issue" URL accepts `title=`, `body=`, and `labels=` (CSV)
// as query params. We URI-encode each independently and assemble.
// GitHub's URL parser caps the body at ~8 KB before truncating; the form
// fields combined are nowhere near that, but if the spec grows, callers
// should consider switching to the Issue Forms API.

export interface BuiltIssue {
  url: string;
  title: string;
  markdown: string;
}

const REPO_NEW_ISSUE_URL =
  'https://github.com/MrPeppersDev/memory-analysis-program/issues/new';

export function buildIssueUrl(
  s: SubmissionFormState,
  opts: { repoUrl?: string } = {}
): BuiltIssue {
  const base = opts.repoUrl ?? REPO_NEW_ISSUE_URL;
  const name = s.name.trim() || '(unnamed)';
  const title = `Intake: ${name}`;
  const markdown = buildIssueMarkdown(s);

  const params = new URLSearchParams();
  params.set('title', title);
  params.set('body', markdown);
  params.set('labels', 'intake');

  // URLSearchParams uses `+` for spaces; GitHub accepts that, but we
  // prefer `%20` for readability when the link is copy-pasted. Swap.
  const query = params.toString().replace(/\+/g, '%20');

  return {
    url: `${base}?${query}`,
    title,
    markdown
  };
}
