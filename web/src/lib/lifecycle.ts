// Lifecycle status per system (#331), from data/stack-index.json, which
// scripts/build_stack_index.py derives from the cited lifecycle cells.
// The labels and tones are client-safe; `lifecycleOf` imports the index,
// so call it from server loaders only and pass the status through.

import stackIndex from '../../../data/stack-index.json';
import type { StackStatus } from '../../../mcp/src/stack-check';

export type Lifecycle = StackStatus;

export interface LifecycleInfo {
  status: Lifecycle;
  note: string;
  evidence: string;
}

const RECORDS = (stackIndex as unknown as { records: Record<string, { status: Lifecycle; note?: string; evidence?: string }> }).records;

export function lifecycleOf(id: string): LifecycleInfo {
  const r = RECORDS[id];
  return { status: r?.status ?? 'active', note: r?.note ?? '', evidence: r?.evidence ?? '' };
}
