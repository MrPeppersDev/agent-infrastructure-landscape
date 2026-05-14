# Data-gap audit summary

- Records scanned: **912**
- Cells scanned: **54,720**
- Gap rows (CSV): **0**
- High-priority queue (priority >= 10): **0**

## Counts by class

| Class | Count |
|---|---:|
| `fillable-and-missing` | 0 |
| `real-data-no-citation` | 0 |
| `shallow-prose` | 0 |
| `structurally-not-applicable` | 23,955 |
| `searched-not-found` | 11,571 |
| `terminal-real-data` | 19,194 |
| **sum** | **54,720** |

Sanity: 54,720 classified cells vs 54,720 non-name cells (match: **YES**).

## Top 10 most-gappy columns

| Column | Gaps | fillable | no-cite | shallow |
|---|---:|---:|---:|---:|
| `a2a-support` | 0 | 0 | 0 | 0 |
| `adjacent-infrastructure` | 0 | 0 | 0 | 0 |
| `agent-abstraction` | 0 | 0 | 0 | 0 |
| `anti-fit` | 0 | 0 | 0 | 0 |
| `api-surface` | 0 | 0 | 0 | 0 |
| `backend-storage` | 0 | 0 | 0 | 0 |
| `citations` | 0 | 0 | 0 | 0 |
| `claims` | 0 | 0 | 0 | 0 |
| `code-release` | 0 | 0 | 0 | 0 |
| `compliance` | 0 | 0 | 0 | 0 |

## Top 10 most-gappy sections

| Section | Gaps | fillable | no-cite | shallow |
|---|---:|---:|---:|---:|
| AI sandbox & runtime environments | 0 | 0 | 0 | 0 |
| Agent IDEs & coding harnesses | 0 | 0 | 0 | 0 |
| Agent frameworks (no first-party memory layer) | 0 | 0 | 0 | 0 |
| Browser-agent memory | 0 | 0 | 0 | 0 |
| Claude Code memory mechanisms | 0 | 0 | 0 | 0 |
| Coding-agent memory | 0 | 0 | 0 | 0 |
| Computer-use & desktop agents | 0 | 0 | 0 | 0 |
| Dedicated memory layers | 0 | 0 | 0 | 0 |
| Embedding & reranker services | 0 | 0 | 0 | 0 |
| Enterprise-search adjacencies | 0 | 0 | 0 | 0 |

## Top 20 records by total gaps

| Record | Tier | Section | Gaps |
|---|:--:|---|---:|

## By category

| Category | Records | Total cells | Fillable gaps | NA-terminal | Terminal-filled | Gap rate |
|---|---:|---:|---:|---:|---:|---:|
| Round-7 sections (Training / Search / Frameworks / Inference / Embedding / Eval) | 146 | 8,760 | 0 | 1,724 | 1,033 | 0.0% |
| Original memory sections | 571 | 34,260 | 0 | 15,465 | 13,842 | 0.0% |
| Research papers / theory / benchmarks | 247 | 14,820 | 0 | 9,481 | 4,148 | 0.0% |

## Phase-2 effort estimate

- `fillable-and-missing`: 0
- `real-data-no-citation`: 0
- `shallow-prose`: 0

At ~5 min/cell to research-and-fill a fillable, ~1 min/cell to locate a citation for a no-cite real-data row, and ~3 min/cell to enrich shallow prose:

- Estimated phase-2 effort: **0 min ≈ 0 h**.

(Estimate is wall-clock for a single agent working serially; deep-fill rounds can parallelise across records.)
