# Data-gap audit summary

- Records scanned: **699**
- Cells scanned: **41,940**
- Gap rows (CSV): **44**
- High-priority queue (priority >= 10): **0**

## Counts by class

| Class | Count |
|---|---:|
| `fillable-and-missing` | 0 |
| `real-data-no-citation` | 0 |
| `shallow-prose` | 44 |
| `structurally-not-applicable` | 16,487 |
| `searched-not-found` | 10,955 |
| `terminal-real-data` | 14,454 |
| **sum** | **41,940** |

Sanity: 41,940 classified cells vs 41,940 non-name cells (match: **YES**).

## Top 10 most-gappy columns

| Column | Gaps | fillable | no-cite | shallow |
|---|---:|---:|---:|---:|
| `orchestration` | 31 | 0 | 0 | 31 |
| `validated-verticals` | 11 | 0 | 0 | 11 |
| `api-surface` | 1 | 0 | 0 | 1 |
| `import-export` | 1 | 0 | 0 | 1 |
| `a2a-support` | 0 | 0 | 0 | 0 |
| `adjacent-infrastructure` | 0 | 0 | 0 | 0 |
| `agent-abstraction` | 0 | 0 | 0 | 0 |
| `anti-fit` | 0 | 0 | 0 | 0 |
| `backend-storage` | 0 | 0 | 0 | 0 |
| `citations` | 0 | 0 | 0 | 0 |

## Top 10 most-gappy sections

| Section | Gaps | fillable | no-cite | shallow |
|---|---:|---:|---:|---:|
| Dedicated memory layers | 26 | 0 | 0 | 26 |
| Research / specialised systems | 10 | 0 | 0 | 10 |
| Framework-embedded memory | 7 | 0 | 0 | 7 |
| Enterprise-search adjacencies | 1 | 0 | 0 | 1 |
| Agent frameworks (no first-party memory layer) | 0 | 0 | 0 | 0 |
| Browser-agent memory | 0 | 0 | 0 | 0 |
| Claude Code memory mechanisms | 0 | 0 | 0 | 0 |
| Coding-agent memory | 0 | 0 | 0 | 0 |
| Embedding & reranker services | 0 | 0 | 0 | 0 |
| Evaluation & observability platforms | 0 | 0 | 0 | 0 |

## Top 20 records by total gaps

| Record | Tier | Section | Gaps |
|---|:--:|---|---:|
| M3-Agent (ByteDance) | T2 | Dedicated memory layers | 2 |
| Pydantic-AI MemoryTool | T3 | Framework-embedded memory | 2 |
| A-MEM | T3 | Research / specialised systems | 1 |
| AI Singapore SEA-LION | T2 | Dedicated memory layers | 1 |
| Anda Hippocampus | T2 | Dedicated memory layers | 1 |
| AutoGLM (Zhipu AI) | T2 | Dedicated memory layers | 1 |
| Backboard | T2 | Dedicated memory layers | 1 |
| BAI-LAB MemoryOS | T3 | Research / specialised systems | 1 |
| Botpress LLMz | T1 | Framework-embedded memory | 1 |
| Cellon (Memory.inc) | T2 | Dedicated memory layers | 1 |
| DSPy History | T3 | Framework-embedded memory | 1 |
| EverMemOS | T4 | Research / specialised systems | 1 |
| EVOLVE-MEM | T3 | Research / specialised systems | 1 |
| Flowise Memory | T1 | Framework-embedded memory | 1 |
| Haystack Memory (deepset) | T3 | Framework-embedded memory | 1 |
| Hyperspell | T2 | Dedicated memory layers | 1 |
| Interloom | T1 | Dedicated memory layers | 1 |
| Jamba (AI21 Labs) | T1 | Dedicated memory layers | 1 |
| Krutrim Kruti (Ola) | T2 | Dedicated memory layers | 1 |
| LiCoMemory | T4 | Research / specialised systems | 1 |

## By category

| Category | Records | Total cells | Fillable gaps | NA-terminal | Terminal-filled | Gap rate |
|---|---:|---:|---:|---:|---:|---:|
| Round-7 sections (Training / Search / Frameworks / Inference / Embedding / Eval) | 146 | 8,760 | 0 | 1,724 | 1,033 | 0.0% |
| Original memory sections | 553 | 33,180 | 44 | 14,763 | 13,421 | 0.1% |
| Research papers / theory / benchmarks | 229 | 13,740 | 10 | 8,779 | 3,761 | 0.1% |

## Phase-2 effort estimate

- `fillable-and-missing`: 0
- `real-data-no-citation`: 0
- `shallow-prose`: 44

At ~5 min/cell to research-and-fill a fillable, ~1 min/cell to locate a citation for a no-cite real-data row, and ~3 min/cell to enrich shallow prose:

- Estimated phase-2 effort: **132 min ≈ 2 h**.

(Estimate is wall-clock for a single agent working serially; deep-fill rounds can parallelise across records.)
