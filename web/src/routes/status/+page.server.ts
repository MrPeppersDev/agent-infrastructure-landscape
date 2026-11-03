// /status: the catalog's bots (product review, 2026-10-30). data/bot-status.json
// is written at deploy by scripts/bot_status.py from the GitHub Actions API;
// local and PR builds have no token, and the page says the status isn't
// available there.
// The file is optional, so it's read with a glob: an empty match when it isn't there.
const files = import.meta.glob('../../../../data/bot-status.json', { eager: true, import: 'default' });

export const prerender = true;

export type BotRun = { at: string; event?: string; status?: string; conclusion?: string | null; url: string };
export type Bot = { name: string; file: string; url: string; lastRun: BotRun | null; lastSuccess: BotRun | null; recentRuns: number; recentFailures: number };
export type Usage = { npmPackage: string; npmLastWeek: number | null; npmLastMonth: number | null; stars: number | null; forks: number | null };
export type BotStatus = ({ available: true; generatedAt: string; repo: string; workflows: Bot[] } | { available: false; reason?: string }) & { usage?: Usage };

export function load(): { status: BotStatus } {
  const data = Object.values(files)[0] as BotStatus | undefined;
  return { status: data ?? { available: false, reason: 'not generated in this build' } };
}
