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
