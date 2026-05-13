# Data-gap audit summary

- Records scanned: **772**
- Cells scanned: **46,320**
- Gap rows (CSV): **0**
- High-priority queue (priority >= 10): **0**

## Counts by class

| Class | Count |
|---|---:|
| `fillable-and-missing` | 0 |
| `real-data-no-citation` | 0 |
| `shallow-prose` | 0 |
| `structurally-not-applicable` | 17,825 |
| `searched-not-found` | 11,570 |
| `terminal-real-data` | 16,925 |
| **sum** | **46,320** |

Sanity: 46,320 classified cells vs 46,320 non-name cells (match: **YES**).

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
| Agent IDEs & coding harnesses | 0 | 0 | 0 | 0 |
| Agent frameworks (no first-party memory layer) | 0 | 0 | 0 | 0 |
| Browser-agent memory | 0 | 0 | 0 | 0 |
| Claude Code memory mechanisms | 0 | 0 | 0 | 0 |
| Coding-agent memory | 0 | 0 | 0 | 0 |
| Computer-use & desktop agents | 0 | 0 | 0 | 0 |
| Dedicated memory layers | 0 | 0 | 0 | 0 |
| Embedding & reranker services | 0 | 0 | 0 | 0 |
| Enterprise-search adjacencies | 0 | 0 | 0 | 0 |
| Evaluation & observability platforms | 0 | 0 | 0 | 0 |

## Top 20 records by total gaps

| Record | Tier | Section | Gaps |
|---|:--:|---|---:|

## By category

| Category | Records | Total cells | Fillable gaps | NA-terminal | Terminal-filled | Gap rate |
|---|---:|---:|---:|---:|---:|---:|
| Round-7 sections (Training / Search / Frameworks / Inference / Embedding / Eval) | 146 | 8,760 | 0 | 1,724 | 1,033 | 0.0% |
| Original memory sections | 553 | 33,180 | 0 | 14,763 | 13,465 | 0.0% |
| Research papers / theory / benchmarks | 229 | 13,740 | 0 | 8,779 | 3,771 | 0.0% |

## Phase-2 effort estimate

- `fillable-and-missing`: 0
- `real-data-no-citation`: 0
- `shallow-prose`: 0

At ~5 min/cell to research-and-fill a fillable, ~1 min/cell to locate a citation for a no-cite real-data row, and ~3 min/cell to enrich shallow prose:

- Estimated phase-2 effort: **0 min ≈ 0 h**.

(Estimate is wall-clock for a single agent working serially; deep-fill rounds can parallelise across records.)
