// /choose/framework and /choose/data — agent-framework and data-store
// choosers (logic: mcp/src/chooser-infra.ts). Slim items only for the
// sections those choosers draw from.
import { error } from '@sveltejs/kit';
import { getRecords } from '$lib/data';
import { toItem, type StackStatusLite } from '$lib/chooser';
import { INFRA_SECTIONS, NEEDS, type InfraKind } from '../../../../../mcp/src/chooser-infra';
import stackIndex from '../../../../../data/stack-index.json';

export const prerender = true;

export function entries() {
  return [{ kind: 'framework' }, { kind: 'data' }];
}

export const load = ({ params }: { params: { kind: string } }) => {
  if (params.kind !== 'framework' && params.kind !== 'data') throw error(404, 'Unknown chooser');
  const kind = params.kind as InfraKind;
  const sections = new Set(NEEDS[kind].flatMap((n) => n.sections));
  const status = (stackIndex as unknown as { records: Record<string, StackStatusLite> }).records;
  const items = getRecords()
    .filter((r) => sections.has(r.sections.find((s) => s.primary)?.section ?? ''))
    .map((r) => {
      const s = status[r.id];
      return toItem(r, s ? { status: s.status, severity: s.severity, note: s.note } : undefined);
    });
  void INFRA_SECTIONS;
  return { kind, items };
};
