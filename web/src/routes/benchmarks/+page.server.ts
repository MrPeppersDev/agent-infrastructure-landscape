// /benchmarks — memory benchmark results. Two clearly separated parts:
//   1. our reproducible runs (bench/, same answer model + judge + data for
//      every system), read from bench/results/leaderboard.json when present;
//   2. vendor- and paper-reported scores catalogued in the data, labelled as
//      not reproduced.
import { getRecords } from '$lib/data';
import { familyForSection, primarySectionOf } from '$lib/families';

export const prerender = true;

type Row = {
  system: string; dataset: string; answer_model: string; judge_model: string; accuracy_macro: number | null;
  accuracy: number | null; abstention_accuracy: number | null; retrieve_ms_p50: number | null; version: string;
  run_id: string; finished_at: string; by_type: Record<string, { accuracy: number }>;
};

const boards = import.meta.glob('../../../../bench/results/leaderboard.json', { eager: true, import: 'default' });

// bench adapter name → catalog record name
const ADAPTER_RECORD: Record<string, string> = {
  mem0: 'Mem0', graphiti: 'Zep & Graphiti', zep: 'Zep & Graphiti', cognee: 'Cognee', supermemory: 'Supermemory',
  letta: 'Letta / MemGPT', honcho: 'Honcho'
};
const BENCH = /LongMemEval|LMES|LoCoMo|LOCOMO|ConvoMem|BEAM|\bDMR\b|MemoryAgentBench|MemBench/i;

export const load = () => {
  const rows = (Object.values(boards)[0] as Row[] | undefined) ?? [];
  const records = getRecords();
  const idByName = new Map(records.map((r) => [r.name, r.id]));
  const runs = rows.map((r) => ({ ...r, id: idByName.get(ADAPTER_RECORD[r.system] ?? '') ?? null }));

  const reported = records
    .map((r) => {
      const fam = familyForSection(primarySectionOf(r))?.id ?? 'other';
      for (const k of ['vendor-benchmarks', 'perf'] as const) {
        const c = r.cells[k as keyof typeof r.cells] as { value?: string; citation?: string | null; status?: string } | undefined;
        if (c?.value && c.status === 'real-data' && BENCH.test(c.value)) {
          return { id: r.id, name: r.name, family: fam, claim: c.value, citation: c.citation ?? null, kind: fam === 'memory-research' ? 'paper' : 'vendor' };
        }
      }
      return null;
    })
    .filter((x): x is NonNullable<typeof x> => !!x)
    .sort((a, b) => (a.kind === b.kind ? a.name.localeCompare(b.name) : a.kind === 'vendor' ? -1 : 1));
  return { runs, reported };
};
