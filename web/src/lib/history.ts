// Per-system change history (data/history.json, built from git by
// scripts/build_history.py). Newest event first per record.
import historyRaw from '../../../data/history.json';

export type HistoryChange = { field: string; label: string; from: string; to: string; source?: string; first?: boolean };
export type HistoryEvent = {
  date: string;
  commit: string;
  pr: number | null;
  kind: 'added' | 'update' | 'lifecycle' | 'removed';
  changes: HistoryChange[];
};
type HistoryFile = { baseline: string; records: Record<string, HistoryEvent[]> };

const history = historyRaw as unknown as HistoryFile;

export const REPO = 'https://github.com/MrPeppersDev/agent-infrastructure-landscape';

export function historyFor(id: string): HistoryEvent[] {
  return history.records[id] ?? [];
}

export function historyBaseline(): string {
  return history.baseline;
}

/** Every event across the catalog, newest first. */
export function allEvents(): (HistoryEvent & { id: string })[] {
  const out: (HistoryEvent & { id: string })[] = [];
  for (const [id, evs] of Object.entries(history.records)) for (const e of evs) out.push({ ...e, id });
  return out.sort((a, b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id));
}

/** Pre-filled "Correct a record" issue (.github/ISSUE_TEMPLATE/correction.yml). */
export function correctionUrl(id: string, field = '', current = ''): string {
  const q = new URLSearchParams({ template: 'correction.yml', title: `Correction: ${id}${field ? ` ${field}` : ''}`, record: id });
  if (field) q.set('field', field);
  if (current) q.set('current', current.slice(0, 600));
  return `${REPO}/issues/new?${q.toString()}`;
}
