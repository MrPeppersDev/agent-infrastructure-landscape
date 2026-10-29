// Build-time numbers for the findings' {tokens} (see findings.ts).
// Server/prerender only: it reads the full catalog.

import { getRecords } from './data';
import { buildProductBenchmarkMatrix, refusesCallout } from './analyses/product-benchmark-matrix';
import { findings, withLiveNumbers, type Finding } from './findings';

const n = (x: number) => x.toLocaleString('en-US');
const pct = (x: number) => `${x.toFixed(1)}%`;

export function liveFindings(): Finding[] {
  const records = getRecords();
  const m = buildProductBenchmarkMatrix(records);
  const c = refusesCallout(records, m);
  const count = (tier: string) => m.cells.filter((x) => x.integrity === tier).length;
  const possible = m.products.length * m.benchmarks.length;
  return withLiveNumbers(findings, {
    total: n(c.totalProducts),
    refusing: n(c.refusingProducts),
    refusingPct: pct(c.refusingPercent),
    products: n(m.products.length),
    benchmarks: n(m.benchmarks.length),
    filled: n(m.cells.length),
    possible: n(possible),
    emptyPct: pct(possible ? (1 - m.cells.length / possible) * 100 : 0),
    peer: n(count('peer-reviewed')),
    independent: n(count('independently-verified')),
    vendor: n(count('vendor-claimed')),
    disputed: n(count('disputed'))
  });
}
