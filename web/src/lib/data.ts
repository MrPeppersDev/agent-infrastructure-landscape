// Data loaders. The two JSON files live at web/landscape.json and
// web/landscape.edges.json — alongside this Svelte source tree, not inside
// src/lib/. We import them via Vite's relative-path JSON import so they are
// bundled at build time (they are content-addressed: the same JSON shipped
// to all clients, no fetch round-trip needed at runtime).
//
// landscape.json is ~6.4 MB. Vite will emit it as a hashed asset chunk; the
// landing page (issue #8) only consumes counts so most of the bundle gets
// tree-shaken on the landing page, and the table view (#9) will load the
// full set when it needs it.

import landscapeRaw from '../../landscape.json';
import edgesRaw from '../../landscape.edges.json';
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
