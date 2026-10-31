// Lifecycle status per system (#331), from data/stack-index.json, which
// scripts/build_stack_index.py derives from the cited lifecycle cells.
// The labels and tones are client-safe; `lifecycleOf` imports the index,
// so call it from server loaders only and pass the status through.

import stackIndex from '../../../data/stack-index.json';
import { healthConcerns } from '../../../mcp/src/stack-check';
import type { StackStatus, RepoHealth } from '../../../mcp/src/stack-check';

export type Lifecycle = StackStatus;

export interface LifecycleInfo {
  status: Lifecycle;
  note: string;
  evidence: string;
}

const RECORDS = (stackIndex as unknown as { records: Record<string, { status: Lifecycle; note?: string; evidence?: string; last_commit?: string | null; health?: RepoHealth | null }> }).records;

export function lifecycleOf(id: string): LifecycleInfo {
  const r = RECORDS[id];
  return { status: r?.status ?? 'active', note: r?.note ?? '', evidence: r?.evidence ?? '' };
}

/** Maintainer-health signals for a record (#365), or null until the
 * repo-health bot has covered its repo. */
export function healthOf(id: string): { health: RepoHealth; concerns: string[] } | null {
  const r = RECORDS[id];
  if (!r?.health) return null;
  return { health: r.health, concerns: healthConcerns(r.health, r.last_commit ?? null) };
}
