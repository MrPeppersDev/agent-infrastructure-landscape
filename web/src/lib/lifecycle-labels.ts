// Display labels and tones for lifecycle statuses (#331). Client-safe:
// no data imports. The status itself comes from $lib/lifecycle on the server.

import type { StackStatus } from '../../../mcp/src/stack-check';

export const LIFECYCLE_ORDER: StackStatus[] = [
  'active',
  'maintenance',
  'research-code',
  'renamed',
  'acquired',
  'stale',
  'inactive',
  'deprecated',
  'archived',
  'dead'
];

export const LIFECYCLE_LABEL: Record<StackStatus, string> = {
  active: 'Active',
  maintenance: 'Maintenance',
  'research-code': 'Research code',
  renamed: 'Renamed',
  acquired: 'Acquired',
  stale: 'Stale',
  inactive: 'Inactive',
  deprecated: 'Deprecated',
  archived: 'Archived',
  dead: 'Shut down'
};

/** ok = nothing to do; info = worth knowing; warn = check before adopting; bad = plan a replacement. */
export type LifecycleTone = 'ok' | 'info' | 'warn' | 'bad';

export const LIFECYCLE_TONE: Record<StackStatus, LifecycleTone> = {
  active: 'ok',
  maintenance: 'info',
  'research-code': 'info',
  renamed: 'info',
  acquired: 'warn',
  stale: 'warn',
  inactive: 'warn',
  deprecated: 'bad',
  archived: 'bad',
  dead: 'bad'
};

/** Statuses that get a banner on the system page linking to alternatives. */
export const LIFECYCLE_BANNER: ReadonlySet<StackStatus> = new Set([
  'acquired',
  'archived',
  'renamed',
  'deprecated',
  'dead',
  'stale',
  'inactive'
]);
