// /changes (#336): what changed in the catalog, for people. Built from
// data/history.json (scripts/build_history.py, from git) with lifecycle
// notes and evidence from data/stack-index.json. No hand-edited input.

import { getRecords, getRedirects } from '$lib/data';
import { allEvents } from '$lib/history';
import { familyIdOf, getFamilies } from '$lib/families';
import { lifecycleOf } from '$lib/lifecycle';

export const prerender = true;

export type ChangeType =
  | 'acquired'
  | 'archived'
  | 'deprecated'
  | 'dead'
  | 'renamed'
  | 'lifecycle'
  | 'price'
  | 'release'
  | 'funding'
  | 'license'
  | 'new'
  | 'fact';

export type ChangeEntry = {
  date: string;
  id: string;
  name: string;
  family: string;
  type: ChangeType;
  note: string;
  source: string | null;
  pr: number | null;
};

// decay_cause values → event type. Anything else is a generic lifecycle note.
const DECAY: Record<string, ChangeType> = {
  acquired: 'acquired',
  'acquired-and-shut-down': 'acquired',
  archived: 'archived',
  deprecated: 'deprecated',
  sunset: 'deprecated',
  'shut-down': 'dead',
  dead: 'dead',
  renamed: 'renamed',
  rebranded: 'renamed'
};
const FIELD: Record<string, ChangeType> = {
  pricing: 'price',
  'latest-release': 'release',
  funding: 'funding',
  license: 'license',
  name: 'renamed'
};

// Not news: a paper whose code is done, or an unknown cause.
const QUIET = new Set(['research-complete', 'unknown']);

// A fact change that announces a lifecycle event in its own words.
function announced(from: string, to: string): ChangeType | null {
  const tests: [RegExp, ChangeType][] = [
    [/\bacquired by\b|\bacquisition\b|\bnow part of\b/i, 'acquired'],
    [/\bshut(ting)? down\b|\bshutdown\b|\bdiscontinued\b|\bend of life\b/i, 'dead'],
    [/\bdeprecated\b|\bsunset\b/i, 'deprecated'],
    [/\barchived\b/i, 'archived'],
    [/\(now [^)]+\)|\brenamed\b|\brebranded\b/i, 'renamed']
  ];
  for (const [re, type] of tests) if (re.test(to) && !re.test(from)) return type;
  return null;
}

const clip = (s: string, n = 160) => {
  const t = s.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  return t.length > n ? t.slice(0, n - 1).replace(/\s+\S*$/, '') + '…' : t;
};

export function load() {
  const records = getRecords();
  const byId = new Map(records.map((r) => [r.id, r]));
  const redirects = getRedirects();
  const entries: ChangeEntry[] = [];
  for (const e of allEvents()) {
    const r = byId.get(e.id) ?? byId.get(redirects[e.id] ?? '');
    if (!r) continue;
    const base = { date: e.date, id: r.id, name: r.name, family: familyIdOf(r), pr: e.pr };
    if (e.kind === 'added') {
      entries.push({ ...base, type: 'new', note: 'Added to the catalog.', source: r.url });
      continue;
    }
    for (const c of e.changes) {
      if (c.field === 'decay_cause') {
        if (QUIET.has(c.to)) continue;
        const type = DECAY[c.to] ?? 'lifecycle';
        const life = lifecycleOf(r.id);
        const note = life.note ? clip(life.note) : `Lifecycle: ${c.to.replace(/-/g, ' ')}.`;
        entries.push({ ...base, type, note, source: life.evidence?.startsWith('http') ? life.evidence : (c.source ?? null) });
        continue;
      }
      if (c.field === 'url') continue; // a homepage move rides with its rename
      const type = announced(c.from ?? '', c.to ?? '') ?? FIELD[c.field] ?? 'fact';
      const note = c.first || !c.from ? `${c.label}: ${clip(c.to)}` : `${c.label}: ${clip(c.from, 70)} → ${clip(c.to, 90)}`;
      entries.push({ ...base, type, note, source: c.source ?? null });
    }
  }
  // Within a day, lifecycle news before routine fact updates.
  const RANK: ChangeType[] = ['acquired', 'dead', 'deprecated', 'archived', 'renamed', 'lifecycle', 'new', 'price', 'license', 'release', 'funding', 'fact'];
  entries.sort(
    (a, b) => b.date.localeCompare(a.date) || RANK.indexOf(a.type) - RANK.indexOf(b.type) || a.name.localeCompare(b.name)
  );
  return {
    entries,
    families: getFamilies().map((f) => ({ id: f.id, name: f.name }))
  };
}
