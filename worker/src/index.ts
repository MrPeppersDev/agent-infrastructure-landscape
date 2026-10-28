// Cloudflare Worker entry: data files come from the repo's main branch
// (raw.githubusercontent.com), cached at the edge for an hour.
import { createHandler } from './handler.js';

interface Env {
  DATA_BASE?: string;
}

const FILES: Record<string, string> = {
  'landscape.json': 'data/landscape.json',
  'landscape.edges.json': 'data/landscape.edges.json',
  'stack-index.json': 'data/stack-index.json',
  'families.json': 'taxonomy/families.json',
  'migrations.json': 'data/migrations.json',
  'history.json': 'data/history.json',
  'system-aliases.json': 'taxonomy/system-aliases.json',
  'pricing-memory.json': 'data/pricing/memory.json',
  'pricing-vector.json': 'data/pricing/vector.json'
};

let handler: ((r: Request) => Promise<Response>) | null = null;

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const base = env.DATA_BASE ?? 'https://raw.githubusercontent.com/MrPeppersDev/agent-infrastructure-landscape/main/';
    handler ??= createHandler(async (file) => {
      const r = await fetch(base + FILES[file], { cf: { cacheTtl: 3600, cacheEverything: true } } as RequestInit);
      if (!r.ok) throw new Error(`${file}: HTTP ${r.status}`);
      return r.json();
    });
    return handler(req);
  }
};
