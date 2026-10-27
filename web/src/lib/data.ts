// Data loaders. The two JSON files live at data/landscape.json and
// data/landscape.edges.json — the canonical standalone dataset, decoupled
// from this Svelte tree per issue #35 so the data outlives any rendering
// surface. We import them via Vite's relative-path JSON import so they are
// bundled at build time (same JSON shipped to all clients, no fetch
// round-trip at runtime).
//
// landscape.json is ~11 MB. Vite emits it as a hashed asset chunk; the
// landing page consumes counts so most of the bundle is tree-shaken there,
// and the table view loads the full set when it needs it.

import landscapeRaw from '../../../data/landscape.json';
import edgesRaw from '../../../data/landscape.edges.json';
import systemAliasesRaw from '../../../taxonomy/system-aliases.json';
import type { EdgesFile, LandscapeFile, LandscapeRecord, Edge } from './types';

const landscape = landscapeRaw as unknown as LandscapeFile;
const edges = edgesRaw as unknown as EdgesFile;

export function getLandscape(): LandscapeFile {
  return landscape;
}

export function getRecords(): LandscapeRecord[] {
  return landscape.records;
}

export function getEdges(): Edge[] {
  return edges.edges;
}

export function getRecordCount(): number {
  return landscape.records.length;
}

export function getEdgeCount(): number {
  return edges.edges.length;
}

/** Ids of records merged into another record (old id → kept id), from
 * taxonomy/system-aliases.json. Pages for old ids redirect to the kept one. */
export function getRedirects(): Record<string, string> {
  return ((systemAliasesRaw as { redirects?: Record<string, string> }).redirects) ?? {};
}
