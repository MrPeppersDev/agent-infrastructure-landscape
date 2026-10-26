// Curated, cited migration notes for archived / deprecated / acquired /
// maintenance-mode systems (data/migrations.json).
import raw from '../../../data/migrations.json';

export type Migration = {
  id: string;
  action: 'migrate' | 'none';
  summary: string;
  to: { name: string; id: string | null }[];
  steps: string[];
  sources: string[];
  verified_at: string;
};

const notes = (raw as unknown as { notes: Migration[] }).notes;
const byId = new Map(notes.map((n) => [n.id, n]));

export function migrationFor(id: string): Migration | null {
  return byId.get(id) ?? null;
}

export function migrationIds(): string[] {
  return notes.map((n) => n.id);
}
