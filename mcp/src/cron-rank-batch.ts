// Batch runner that wraps `rankCandidates()` for the recommendation-drift cron.
//
// Phase 2 / Gate 6 (issue #100). The drift workflow replays
// `docs/canonical-questions.yml` (55 entries) through the recommender every
// 24 hours. Python is the orchestrator (it owns the YAML parse, the snapshot
// diffing, and the gh-issue side-effects); TypeScript owns the ranking math
// (single source of truth in `recommender.ts`). This file is the thin bridge.
//
// Contract
// --------
//
// stdin / argv:
//   node mcp/dist/cron-rank-batch.js <input.json>
//
//   <input.json> is an array of question objects:
//     [
//       {
//         "id": "kimi-vs-opus-scoped-agentic",
//         "anchors": {"low": "...", "high": "..."} | null,
//         "constraints": { ... ConstraintSet fields ... },
//         "k": 5
//       },
//       ...
//     ]
//
// stdout (single JSON document):
//   [
//     {"id": "kimi-vs-opus-scoped-agentic", "candidates": [Candidate, ...]},
//     ...
//   ]
//
// Errors per-entry are surfaced as
//   {"id": "...", "candidates": [], "error": "..."}
// so a single bad question doesn't fail the whole batch — the drift script
// can still snapshot the rest.

import { readFileSync } from 'node:fs';
import { loadRecords } from './data.js';
import { rankCandidates } from './recommender.js';
import type { AnchorPair, Candidate, ConstraintSet } from './recommender.js';

interface BatchInputEntry {
  id: string;
  anchors?: AnchorPair | null;
  constraints?: Record<string, unknown>;
  k?: number;
}

interface BatchOutputEntry {
  id: string;
  candidates: Candidate[];
  error?: string;
}

// Keys we accept in `constraints`. Anything else is silently dropped (defensive
// against future schema additions in canonical-questions.yml).
const CONSTRAINT_KEYS: ReadonlySet<string> = new Set([
  'use_case_tags',
  'cost_max_input_usd_per_mtok',
  'cost_tier_max',
  'capability_band_min'
]);

function sanitizeConstraints(input: Record<string, unknown> | undefined): ConstraintSet {
  if (!input) return {};
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(input)) {
    if (!CONSTRAINT_KEYS.has(k)) continue;
    out[k] = v;
  }
  return out as ConstraintSet;
}

function main(): void {
  const path = process.argv[2];
  if (!path) {
    process.stderr.write('usage: cron-rank-batch <input.json>\n');
    process.exit(2);
  }

  let entries: BatchInputEntry[];
  try {
    const raw = readFileSync(path, 'utf-8');
    entries = JSON.parse(raw);
  } catch (e) {
    process.stderr.write(`failed to read ${path}: ${(e as Error).message}\n`);
    process.exit(1);
  }
  if (!Array.isArray(entries)) {
    process.stderr.write(`expected JSON array at top level of ${path}\n`);
    process.exit(1);
  }

  const records = loadRecords();
  const out: BatchOutputEntry[] = [];

  for (const entry of entries) {
    if (!entry || typeof entry.id !== 'string') {
      out.push({ id: '<unknown>', candidates: [], error: 'missing id' });
      continue;
    }
    try {
      const constraints = sanitizeConstraints(entry.constraints);
      const anchors: AnchorPair | undefined =
        entry.anchors && entry.anchors.low && entry.anchors.high
          ? { low: entry.anchors.low, high: entry.anchors.high }
          : undefined;
      const k = typeof entry.k === 'number' && entry.k > 0 ? entry.k : 5;
      const candidates = rankCandidates(records, constraints, anchors, k);
      out.push({ id: entry.id, candidates });
    } catch (e) {
      out.push({ id: entry.id, candidates: [], error: (e as Error).message });
    }
  }

  process.stdout.write(JSON.stringify(out, null, 2) + '\n');
}

main();
