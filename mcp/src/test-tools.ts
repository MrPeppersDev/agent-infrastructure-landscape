// Smoke test for the 9 MCP tools — exercises tools.ts directly without
// the MCP transport layer. Run after `npm run build` via:
//
//   node dist/test-tools.js
//
// Each tool is called with realistic sample args and a 1-3 line summary
// is printed. Failures throw and propagate (process exits non-zero).
//
// This is the smoke gate: if every tool returns a sensible result, the
// server should work — server.ts is a thin MCP wrapper around these
// same pure functions.

import { loadRecords, loadEdges, getMeta } from './data.js';
import {
  searchRecords,
  getRecord,
  findRelated,
  coverageSummary,
  compare,
  compareWithEdges,
  listSections,
  recentChanges,
  findEvalOrphans,
  findSubstrateRisk
} from './tools.js';

function banner(title: string) {
  console.log('\n' + '='.repeat(70));
  console.log(' ' + title);
  console.log('='.repeat(70));
}

function preview(value: unknown, lines = 4): string {
  const s =
    typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  const out = s.split('\n').slice(0, lines).join('\n');
  return out + (s.split('\n').length > lines ? '\n  ...' : '');
}

function main() {
  const records = loadRecords();
  const edges = loadEdges();
  const meta = getMeta();

  banner('Setup');
  console.log(`  records:        ${records.length}`);
  console.log(`  edges:          ${edges.length}`);
  console.log(`  schemaVersion:  ${meta.schemaVersion}`);
  console.log(`  generatedAt:    ${meta.generatedAt}`);

  // -----------------------------------------------------------------
  // 1. search_records
  // -----------------------------------------------------------------
  banner('1. search_records({ query: "memory", tier: 1, limit: 5 })');
  const search = searchRecords(records, {
    query: 'memory',
    tier: 1,
    limit: 5
  });
  console.log(`  totalMatches:   ${search.totalMatches}`);
  console.log(`  returned:       ${search.results.length}`);
  console.log(`  first hit:      ${search.results[0]?.name} (${search.results[0]?.id})`);
  if (search.results.length === 0) throw new Error('search_records returned no hits');

  // -----------------------------------------------------------------
  // 2. get_record
  // -----------------------------------------------------------------
  const sampleId = search.results[0]!.id;
  banner(`2. get_record({ id: "${sampleId}" })`);
  const record = getRecord(records, { id: sampleId });
  if (!record) throw new Error(`get_record failed for ${sampleId}`);
  console.log(`  name:           ${record.name}`);
  console.log(`  tier:           ${record.tier}`);
  console.log(`  section:        ${record.sections.find((s) => s.primary)?.section}`);
  console.log(`  cell count:     ${Object.keys(record.cells).length}`);

  // -----------------------------------------------------------------
  // 3. find_related
  // -----------------------------------------------------------------
  // Pick a record we know has edges — OpenAI GPT family is heavily linked.
  const hubId = 'openai-gpt-family-gpt-5-gpt-4o-o3-o4--openai-com';
  banner(`3. find_related({ id: "${hubId}", edge_type: "runtime-dependency" })`);
  const related = findRelated(records, edges, {
    id: hubId,
    edge_type: 'runtime-dependency'
  });
  console.log(`  totalEdges:     ${related.totalEdges}`);
  console.log(`  edgeTypes:      ${JSON.stringify(related.edgeTypes)}`);
  console.log(`  first related:  ${related.edges[0]?.related.name}`);

  // -----------------------------------------------------------------
  // 4. coverage_summary — observability
  // -----------------------------------------------------------------
  banner('4. coverage_summary({ dimension: "observability" })');
  const cov = coverageSummary(records, { dimension: 'observability' });
  console.log(`  totalRecords:   ${cov.totalRecords}`);
  console.log(`  analyzedCount:  ${cov.analyzedCount}`);
  console.log(`  features:       ${cov.features.length}`);
  for (const f of cov.features.slice(0, 3)) {
    console.log(
      `    ${f.label.padEnd(20)} yes=${f.yesCount}  no=${f.noCount}  pct=${f.supportedPct}%`
    );
  }

  // 4b. cost
  banner('4b. coverage_summary({ dimension: "cost" })');
  const costCov = coverageSummary(records, { dimension: 'cost' });
  console.log(`  analyzedCount:  ${costCov.analyzedCount}`);
  for (const f of costCov.features.slice(0, 3)) {
    console.log(`    ${f.label.padEnd(20)} yes=${f.yesCount}  pct=${f.supportedPct}%`);
  }

  // 4c. eval
  banner('4c. coverage_summary({ dimension: "eval" })');
  const evalCov = coverageSummary(records, { dimension: 'eval' });
  console.log(`  analyzedCount:  ${evalCov.analyzedCount}`);
  for (const f of evalCov.features.slice(0, 3)) {
    console.log(`    ${f.label.padEnd(20)} yes=${f.yesCount}  pct=${f.supportedPct}%`);
  }

  // 4d. benchmark
  banner('4d. coverage_summary({ dimension: "benchmark" })');
  const benchCov = coverageSummary(records, { dimension: 'benchmark' });
  console.log(`  sections:       ${benchCov.features.length}`);
  for (const f of benchCov.features) {
    console.log(`    ${f.label.padEnd(45)} count=${f.yesCount}`);
  }

  // -----------------------------------------------------------------
  // 5. compare
  // -----------------------------------------------------------------
  // Pick two memory products for comparison.
  const memRecords = records.filter((r) =>
    r.sections.some((s) => s.primary && s.section === 'Dedicated memory layers')
  );
  const idA = memRecords[0]?.id;
  const idB = memRecords[1]?.id;
  if (!idA || !idB) {
    console.warn('  skipped — no dedicated-memory records found');
  } else {
    banner(`5. compare({ id_a: "${idA}", id_b: "${idB}" })`);
    const cmp = compareWithEdges(records, edges, { id_a: idA, id_b: idB });
    const matching = cmp.cells.filter((c) => c.match).length;
    const both = cmp.cells.filter((c) => c.a && c.b).length;
    console.log(`  a:              ${cmp.a.name}`);
    console.log(`  b:              ${cmp.b.name}`);
    console.log(`  cells compared: ${cmp.cells.length}`);
    console.log(`  matching:       ${matching} of ${both} both-present`);
    console.log(`  directEdges:    ${cmp.directEdges.length}`);
  }

  // -----------------------------------------------------------------
  // 6. list_sections
  // -----------------------------------------------------------------
  banner('6. list_sections()');
  const sections = listSections(records);
  console.log(`  total sections: ${sections.length}`);
  console.log(`  first 3:        ${sections.slice(0, 3).join(' | ')}`);
  if (sections.length === 0) throw new Error('list_sections returned empty');

  // -----------------------------------------------------------------
  // 7. recent_changes
  // -----------------------------------------------------------------
  banner('7. recent_changes({ since: "2025-01-01" })');
  const recent = recentChanges(records, { since: '2025-01-01' });
  console.log(`  totalMatches:   ${recent.totalMatches}`);
  console.log(`  returned:       ${recent.records.length}`);
  console.log(`  newest:         ${recent.records[0]?.name} (${recent.records[0]?.latestRelease})`);

  // -----------------------------------------------------------------
  // 8. find_eval_orphans
  // -----------------------------------------------------------------
  banner('8. find_eval_orphans()');
  const orphans = findEvalOrphans(records);
  console.log(`  orphans found:  ${orphans.length}`);
  for (const o of orphans.slice(0, 3)) {
    console.log(`    - ${o.name.padEnd(40)} (${o.primarySection})`);
  }

  // -----------------------------------------------------------------
  // 9. find_substrate_risk
  // -----------------------------------------------------------------
  banner('9. find_substrate_risk({ substrate: "Anthropic" })');
  const substrate = findSubstrateRisk(records, edges, { substrate: 'Anthropic' });
  console.log(`  resolved to:    ${substrate.substrateRecord?.name ?? '(not found)'}`);
  console.log(`  dependents:     ${substrate.totalDependents}`);
  for (const d of substrate.dependents.slice(0, 3)) {
    console.log(`    - ${d.name}`);
  }

  // 9b: try OpenAI too
  banner('9b. find_substrate_risk({ substrate: "OpenAI" })');
  const openai = findSubstrateRisk(records, edges, { substrate: 'OpenAI' });
  console.log(`  resolved to:    ${openai.substrateRecord?.name ?? '(not found)'}`);
  console.log(`  dependents:     ${openai.totalDependents}`);

  banner('All 9 tools exercised successfully.');
  console.log('  Smoke test PASSED.');
}

try {
  main();
} catch (err) {
  console.error('\n[test-tools] FAILED:');
  console.error(err instanceof Error ? err.stack : err);
  process.exit(1);
}
