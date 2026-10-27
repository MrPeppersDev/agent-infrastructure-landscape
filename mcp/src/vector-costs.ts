// Vector-store cost estimator: published list prices (data/pricing/vector.json)
// applied to a workload (vectors stored × dimensions, writes, queries).
//
// Same honesty rules as costs.ts: only rates the vendor publishes are used;
// a vendor that publishes no unit rates is shown as "not published", never
// guessed; a component whose rate isn't published is left out and the
// result is marked as a lower bound. Every result shows its arithmetic and
// links the pricing page.
//
// Pure and dependency-free.

export interface VectorWorkload {
  /** Vectors kept in the index. */
  vectors: number;
  dimensions: number;
  /** Metadata / attribute bytes stored with each vector. */
  metadataBytes: number;
  /** Vectors written (inserted or updated) per month. */
  writesPerMonth: number;
  queriesPerMonth: number;
  /** Vectors per write request (upserts are usually batched). */
  batchSize: number;
}

export const DEFAULT_VECTOR_WORKLOAD: VectorWorkload = {
  vectors: 1_000_000,
  dimensions: 1536,
  metadataBytes: 500,
  writesPerMonth: 100_000,
  queriesPerMonth: 1_000_000,
  batchSize: 100
};

type Plan = Record<string, number | string | undefined> & { name: string };
export interface VectorPricing {
  system: string;
  model: 'pinecone' | 'turbopuffer' | 'weaviate' | 'zilliz' | 'unpublished';
  source: string;
  units?: string;
  plans?: Plan[];
  rates?: Record<string, number>;
  unit_rules?: Record<string, number>;
  notes?: string;
  not_published?: string[];
}

export interface VectorEstimate {
  system: string;
  /** null: the vendor publishes no usable rates. */
  monthlyUsd: number | null;
  /** True when a cost component's rate isn't published and was left out. */
  atLeast: boolean;
  plan: string;
  working: string[];
  caveat: string | null;
  source: string;
}

const num = (n: number) => Math.round(n).toLocaleString('en-US');
const gb = (n: number) => (n >= 10 ? Math.round(n).toLocaleString('en-US') : n.toFixed(2));
const usd = (n: number) => `$${n >= 100 ? Math.round(n).toLocaleString('en-US') : n.toFixed(2)}`;
const cents = (n: number) => Math.round(n * 100) / 100;

export function vectorEstimate(v: VectorPricing, w: VectorWorkload): VectorEstimate {
  const bytesPerVector = 4 * w.dimensions + w.metadataBytes;
  const storageGb = (w.vectors * bytesPerVector) / 1e9;
  const requests = Math.ceil(w.writesPerMonth / Math.max(1, w.batchSize));
  const requestKb = (Math.min(w.batchSize, w.writesPerMonth || w.batchSize) * bytesPerVector) / 1024;
  const size = `${num(w.vectors)} vectors × ${num(bytesPerVector)} bytes (${w.dimensions} dims × 4 + ${w.metadataBytes} metadata) ≈ ${gb(storageGb)} GB stored`;
  const base = { system: v.system, source: v.source, atLeast: false };
  const plans = v.plans ?? [];
  const r = v.unit_rules ?? {};

  switch (v.model) {
    case 'pinecone': {
      const wuPerRequest = Math.max(r.min_write_units_per_request, Math.ceil(requestKb * r.write_units_per_kb));
      const wu = requests * wuPerRequest;
      const ruPerQuery = Math.max(r.min_read_units_per_query, storageGb * r.read_units_per_gb_queried);
      const ru = w.queriesPerMonth * ruPerQuery;
      const working = [
        size,
        `${num(requests)} write requests × ${num(wuPerRequest)} write units (1 per KB, min ${r.min_write_units_per_request}) = ${num(wu)} WU`,
        `${num(w.queriesPerMonth)} queries × ${ruPerQuery.toFixed(2)} read units (1 per GB of namespace, min ${r.min_read_units_per_query}) = ${num(ru)} RU`
      ];
      const free = plans.find((p) => p.usd !== undefined && storageGb <= Number(p.storage_gb) && wu <= Number(p.write_units) && ru <= Number(p.read_units));
      if (free) return { ...base, monthlyUsd: Number(free.usd), plan: free.name, caveat: null, working: [...working, `${free.name} plan includes ${p(free.storage_gb)} GB, ${p(free.write_units)} WU and ${p(free.read_units)} RU`] };
      const s = plans.find((p) => p.minimum_usd !== undefined)!;
      const usage = storageGb * Number(s.storage_gb_month) + (wu / 1e6) * Number(s.per_m_write_units) + (ru / 1e6) * Number(s.per_m_read_units);
      return {
        ...base, monthlyUsd: cents(Math.max(Number(s.minimum_usd), usage)), plan: s.name,
        caveat: 'One namespace assumed (queries are billed on namespace size). Write and read rates are the low end of the published regional range.',
        working: [...working, `${s.name}: ${gb(storageGb)} GB × $${s.storage_gb_month} + ${num(wu)} WU × $${s.per_m_write_units}/1M + ${num(ru)} RU × $${s.per_m_read_units}/1M = ${usd(usage)}, $${s.minimum_usd} monthly minimum`]
      };
    }
    case 'turbopuffer': {
      const rate = v.rates ?? {};
      const kb = Math.max(r.min_write_kb, requestKb);
      const discount = Math.min(0.5, Math.max(0, 0.2 * (Math.log10(kb) - 1)));
      const writeGb = (requests * kb * 1024) / 1e9;
      const writes = writeGb * rate.write_per_gb * (1 - discount);
      const ns = Math.max(r.min_query_gb, storageGb);
      const billedGb = Math.min(ns, 32) + (1 - r.query_discount_32_128_gb) * Math.min(Math.max(ns - 32, 0), 96) + (1 - r.query_discount_over_128_gb) * Math.max(ns - 128, 0);
      const queries = ((w.queriesPerMonth * billedGb) / 1e6) * rate.query_per_pb;
      const storage = storageGb * rate.storage_gb_month;
      const usage = storage + writes + queries;
      const launch = plans[0];
      return {
        ...base, monthlyUsd: cents(Math.max(Number(launch.minimum_usd), usage)), plan: launch.name,
        caveat: 'Turbopuffer publishes these rates as upper bounds and also bills data returned by queries per GB (rate not published as text), so treat this as approximate.',
        working: [
          size,
          `storage ${gb(storageGb)} GB × $${rate.storage_gb_month} = ${usd(storage)}`,
          `writes ${num(requests)} requests × ${gb(kb)} KB = ${gb(writeGb)} GB × $${rate.write_per_gb}${discount > 0 ? ` − ${Math.round(discount * 100)}% batch discount` : ''} = ${usd(writes)}`,
          `queries ${num(w.queriesPerMonth)} × ${gb(billedGb)} GB billed (namespace size, min ${r.min_query_gb} GB, volume discounts) × $${rate.query_per_pb}/PB = ${usd(queries)}`,
          `${launch.name}: ${usd(usage)} of usage, $${launch.minimum_usd} monthly minimum`
        ]
      };
    }
    case 'weaviate': {
      const f = plans[0];
      const dims = (w.vectors * w.dimensions) / 1e6;
      const gib = (w.vectors * bytesPerVector) / 2 ** 30;
      const usage = dims * Number(f.per_m_dimensions) + gib * Number(f.storage_gib_month) + gib * Number(f.backup_gib_month);
      return {
        ...base, monthlyUsd: cents(Math.max(Number(f.minimum_usd), usage)), plan: f.name,
        caveat: "Published as 'from' prices; queries and writes are not metered. Storage and backup sized as vectors plus metadata.",
        working: [
          size,
          `${num(dims)}M vector dimensions × $${f.per_m_dimensions} + ${gb(gib)} GiB storage × $${f.storage_gib_month} + ${gb(gib)} GiB backup × $${f.backup_gib_month} = ${usd(usage)}`,
          `${f.name}: $${f.minimum_usd} monthly minimum`
        ]
      };
    }
    case 'zilliz': {
      const insert = (w.writesPerMonth * bytesPerVector / 1024) * r.insert_vcus_per_kb;
      const read = w.queriesPerMonth * r.min_read_vcus_per_query;
      const vcus = insert + read;
      const working = [
        size,
        `writes ${num(w.writesPerMonth)} vectors × ${gb(bytesPerVector / 1024)} KB × ${r.insert_vcus_per_kb} vCU/KB = ${num(insert)} vCU`,
        `queries ${num(w.queriesPerMonth)} × at least ${r.min_read_vcus_per_query} vCU = ${num(read)} vCU`
      ];
      const free = plans.find((p) => p.usd !== undefined && storageGb <= Number(p.storage_gb) && vcus <= Number(p.vcus));
      if (free) return { ...base, monthlyUsd: 0, atLeast: true, plan: free.name, caveat: 'Read vCUs use the published 6 vCU minimum per query.', working: [...working, `${free.name} tier includes ${p(free.storage_gb)} GB and ${p(free.vcus)} vCU`] };
      const s = plans.find((p) => p.per_m_vcus !== undefined)!;
      const compute = (vcus / 1e6) * Number(s.per_m_vcus);
      return {
        ...base, monthlyUsd: cents(compute), atLeast: true, plan: s.name,
        caveat: 'Serverless storage per GB-month is not published, so storage is left out; read vCUs use the published 6 vCU minimum per query. A lower bound.',
        working: [...working, `${s.name}: ${num(vcus)} vCU × $${s.per_m_vcus}/1M = ${usd(compute)} + storage (rate not published)`]
      };
    }
    case 'unpublished':
      return { ...base, monthlyUsd: null, plan: 'Rates not published', caveat: v.notes ?? null, working: [size] };
  }
}

function p(x: unknown): string {
  return num(Number(x));
}

export function vectorEstimateAll(vendors: VectorPricing[], w: VectorWorkload): VectorEstimate[] {
  return vendors
    .map((v) => vectorEstimate(v, w))
    .sort((a, b) => (a.monthlyUsd ?? Infinity) - (b.monthlyUsd ?? Infinity) || a.system.localeCompare(b.system));
}
