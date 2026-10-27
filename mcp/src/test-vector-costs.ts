// Tests for vector-costs.ts against data/pricing/vector.json.
// Run: npm run build && node dist/test-vector-costs.js
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { vectorEstimateAll, DEFAULT_VECTOR_WORKLOAD, type VectorPricing } from './vector-costs.js';

const here = dirname(fileURLToPath(import.meta.url));
function find(name: string): string {
  let dir = here;
  for (let i = 0; i < 6; i++) {
    const p = join(dir, 'data', 'pricing', name);
    try { readFileSync(p); return p; } catch { /* next */ }
    dir = dirname(dir);
  }
  throw new Error(`${name} not found`);
}
const V = JSON.parse(readFileSync(find('vector.json'), 'utf-8')).vendors as VectorPricing[];

let failures = 0;
function check(name: string, ok: boolean, detail?: unknown) {
  console.log(`  ${ok ? 'PASS' : 'FAIL'} ${name}${ok ? '' : `  (${String(detail)})`}`);
  if (!ok) failures++;
}
const near = (a: number | null, b: number) => a != null && Math.abs(a - b) < 0.05;

console.log('vector costs (default workload: 1M × 1536-dim vectors, 100k writes, 1M queries)');
{
  const r = Object.fromEntries(vectorEstimateAll(V, DEFAULT_VECTOR_WORKLOAD).map((e) => [e.system, e]));
  check('Pinecone Standard ≈ $111.09', near(r['Pinecone'].monthlyUsd, 111.09) && r['Pinecone'].plan === 'Standard', r['Pinecone'].monthlyUsd);
  check('Turbopuffer at its $16 minimum', r['Turbopuffer'].monthlyUsd === 16, r['Turbopuffer'].monthlyUsd);
  check('Weaviate at its $45 minimum', r['Weaviate Cloud'].monthlyUsd === 45, r['Weaviate Cloud'].monthlyUsd);
  check('Zilliz is a lower bound ≈ $24.65', near(r['Zilliz Cloud'].monthlyUsd, 24.65) && r['Zilliz Cloud'].atLeast, r['Zilliz Cloud'].monthlyUsd);
  check('unpublished vendors are not priced', r['Qdrant Cloud'].monthlyUsd === null && r['LanceDB Cloud'].monthlyUsd === null);
  check('every estimate shows its working', Object.values(r).every((e) => e.working.length > 0 && e.source.startsWith('https://')));
}
{
  const small = vectorEstimateAll(V, { ...DEFAULT_VECTOR_WORKLOAD, vectors: 10_000, writesPerMonth: 1_000, queriesPerMonth: 10_000 });
  const pc = small.find((e) => e.system === 'Pinecone')!;
  check('small workload fits Pinecone Starter', pc.monthlyUsd === 0 && pc.plan === 'Starter', `${pc.plan} ${pc.monthlyUsd}`);
}

if (failures) {
  console.error(`${failures} failure(s)`);
  process.exit(1);
}
console.log('all vector-cost tests passed');
