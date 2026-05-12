// Transient selected-record set for the compare panel (issue #18).
//
// Why a store rather than URL-sync: this is an in-session, two-step
// interaction (shift-click rows, then hit "Compare"). The URL is already
// busy mirroring search/filters/sort and adding another array param
// would bloat shareable links for what is fundamentally an ephemeral UI
// state. If a user wants to share a compare view in the future, we can
// re-introduce URL sync at that point — recorded in DECISIONS.md.
//
// Cap at 4 because the compare panel renders 2-4 columns; more than 4
// cards stops fitting horizontally on typical viewports.

import { writable } from 'svelte/store';

export const MAX_COMPARE = 4;

export const selectedIds = writable<Set<string>>(new Set());

/** Toggle a record id in the set. Returns the new size for callers that
 *  want to react (e.g. show a toast when the cap is hit). */
export function toggleSelected(id: string): number {
  let nextSize = 0;
  selectedIds.update((s) => {
    if (s.has(id)) {
      s.delete(id);
    } else if (s.size < MAX_COMPARE) {
      s.add(id);
    }
    // If at cap and trying to add: silently no-op. The toolbar can read
    // the size and tell the user, but at the data layer we don't throw.
    nextSize = s.size;
    return s;
  });
  return nextSize;
}

export function clearSelection(): void {
  selectedIds.set(new Set());
}

export function removeSelected(id: string): void {
  selectedIds.update((s) => {
    s.delete(id);
    return s;
  });
}
