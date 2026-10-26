// Loads + caches the canonical landscape catalog and edge graph.
//
// Both files are bundled with the repo (data/landscape.json and
// data/landscape.edges.json) and are loaded lazily on first use.
// Path resolution walks up from the running script location so the
// server works whether invoked from the repo root, from mcp/dist/, or
// installed globally via `npm i -g landscape-mcp` (in which case the
// data must be co-located via the npm pack).
//
// Read-only: this module never writes to either file. All MCP tools
// run against the in-memory snapshot taken at process start.

import { readFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { LandscapeFile, LandscapeRecord, EdgesFile, Edge } from './types.js';
import type { StackIndex, Replacement } from './stack-check.js';
import { alternativesFor, toItem, type ChooserItem } from './chooser.js';
import { attentionIds } from './stack-check.js';

let cachedRecords: LandscapeRecord[] | null = null;
let cachedEdges: Edge[] | null = null;
let cachedMeta: { generatedAt: string; schemaVersion: string } | null = null;

/**
 * Locate data/landscape.json by walking up from this module's directory
 * to the nearest ancestor that contains a `data/landscape.json`. This
 * makes the server portable across local dev (mcp/dist/data.js next to
 * ../data/), global install, and the npm tarball layout.
 */
function findDataDir(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  let dir = resolve(here);
  for (let i = 0; i < 10; i++) {
    const candidate = join(dir, 'data', 'landscape.json');
    if (existsSync(candidate)) {
      return join(dir, 'data');
    }
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  // Fallback: assume mcp/dist/ → repo-root/data/
  return resolve(here, '..', '..', 'data');
}

const DATA_DIR = findDataDir();
const LANDSCAPE_PATH = join(DATA_DIR, 'landscape.json');
const EDGES_PATH = join(DATA_DIR, 'landscape.edges.json');

export function loadRecords(): LandscapeRecord[] {
  if (cachedRecords) return cachedRecords;
  const raw = readFileSync(LANDSCAPE_PATH, 'utf-8');
  const parsed = JSON.parse(raw) as LandscapeFile;
  cachedRecords = parsed.records;
  cachedMeta = {
    generatedAt: parsed.generatedAt,
    schemaVersion: parsed.schemaVersion
  };
  return cachedRecords;
}

export function loadEdges(): Edge[] {
  if (cachedEdges) return cachedEdges;
  if (!existsSync(EDGES_PATH)) {
    cachedEdges = [];
    return cachedEdges;
  }
  const raw = readFileSync(EDGES_PATH, 'utf-8');
  const parsed = JSON.parse(raw) as EdgesFile;
  cachedEdges = parsed.edges;
  return cachedEdges;
}

export function getMeta(): { generatedAt: string; schemaVersion: string } {
  if (!cachedMeta) loadRecords();
  return cachedMeta!;
}

export function getDataPaths(): { landscape: string; edges: string } {
  return { landscape: LANDSCAPE_PATH, edges: EDGES_PATH };
}

// ---------------------------------------------------------------------------
// Product families (taxonomy/families.json): the top-level split of the
// catalog into five sub-catalogs. In the repo the file lives in
// taxonomy/; the npm tarball ships a copy at data/families.json.
// ---------------------------------------------------------------------------

export interface Family {
  id: string;
  name: string;
  tagline: string;
  audience: string;
  sections: string[];
}

let cachedFamilies: Family[] | null = null;

export function loadFamilies(): Family[] {
  if (cachedFamilies) return cachedFamilies;
  const candidates = [
    join(DATA_DIR, 'families.json'),
    join(DATA_DIR, '..', 'taxonomy', 'families.json')
  ];
  for (const path of candidates) {
    if (existsSync(path)) {
      const parsed = JSON.parse(readFileSync(path, 'utf-8')) as { families: Family[] };
      cachedFamilies = parsed.families;
      return cachedFamilies;
    }
  }
  cachedFamilies = [];
  return cachedFamilies;
}

/** Family id for a primary section name, or 'other'. */
export function familyIdForSection(section: string): string {
  for (const f of loadFamilies()) if (f.sections.includes(section)) return f.id;
  return 'other';
}

// ---------------------------------------------------------------------------
// Stack-checker index (data/stack-index.json, built by
// scripts/build_stack_index.py). Shipped next to landscape.json.
// ---------------------------------------------------------------------------


let cachedStackIndex: StackIndex | null = null;

export function loadStackIndex(): StackIndex {
  if (cachedStackIndex) return cachedStackIndex;
  cachedStackIndex = JSON.parse(readFileSync(join(DATA_DIR, 'stack-index.json'), 'utf-8')) as StackIndex;
  return cachedStackIndex;
}

let cachedReplacements: Record<string, Replacement[]> | null = null;

/** Live alternatives for every dependency the stack index flags. */
export function loadReplacements(): Record<string, Replacement[]> {
  if (cachedReplacements) return cachedReplacements;
  const index = loadStackIndex();
  cachedReplacements = alternativesFor(
    loadRecords() as unknown as Parameters<typeof alternativesFor>[0],
    attentionIds(index),
    familyIdForSection,
    index.records,
    3
  );
  return cachedReplacements;
}

let cachedItems: ChooserItem[] | null = null;

/** Every record as a chooser item (with stack-index lifecycle status). */
export function loadChooserItems(): ChooserItem[] {
  if (cachedItems) return cachedItems;
  const status = loadStackIndex().records;
  cachedItems = loadRecords().map((r) =>
    toItem(r as unknown as Parameters<typeof toItem>[0], status[r.id])
  );
  return cachedItems;
}

// ---------------------------------------------------------------------------
// Optional sidecar files: migration notes, change history, system aliases.
// Missing files load as empty so older data bundles keep working.
// ---------------------------------------------------------------------------

function readOptional<T>(names: string[], fallback: T): T {
  for (const n of names) {
    for (const p of [join(DATA_DIR, n), join(DATA_DIR, '..', 'taxonomy', n)]) {
      if (existsSync(p)) return JSON.parse(readFileSync(p, 'utf-8')) as T;
    }
  }
  return fallback;
}

export interface MigrationNote {
  id: string;
  action: 'migrate' | 'none';
  summary: string;
  to: { name: string; id: string | null }[];
  steps: string[];
  sources: string[];
  verified_at: string;
}

let cachedMigrations: Map<string, MigrationNote> | null = null;
export function loadMigrations(): Map<string, MigrationNote> {
  if (cachedMigrations) return cachedMigrations;
  const raw = readOptional<{ notes: MigrationNote[] }>(['migrations.json'], { notes: [] });
  cachedMigrations = new Map(raw.notes.map((n) => [n.id, n]));
  return cachedMigrations;
}

export interface HistoryEvent {
  date: string;
  commit: string;
  pr: number | null;
  kind: string;
  changes: { field: string; label: string; from: string; to: string; source?: string; first?: boolean }[];
}

let cachedHistory: Record<string, HistoryEvent[]> | null = null;
export function loadHistory(): Record<string, HistoryEvent[]> {
  if (cachedHistory) return cachedHistory;
  cachedHistory = readOptional<{ records: Record<string, HistoryEvent[]> }>(['history.json'], { records: {} }).records;
  return cachedHistory;
}

export function loadSystemAliases(): Record<string, string[]> {
  return readOptional<{ aliases: Record<string, string[]> }>(['system-aliases.json'], { aliases: {} }).aliases;
}
