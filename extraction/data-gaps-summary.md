# Data-gap audit summary

- Records scanned: **699**
- Cells scanned: **41,940**
- Gap rows (CSV): **8,592**
- High-priority queue (priority >= 10): **401**

## Counts by class

| Class | Count |
|---|---:|
| `fillable-and-missing` | 2,584 |
| `real-data-no-citation` | 5,865 |
| `shallow-prose` | 143 |
| `structurally-not-applicable` | 16,330 |
| `searched-not-found` | 9,024 |
| `terminal-real-data` | 7,994 |
| **sum** | **41,940** |

Sanity: 41,940 classified cells vs 41,940 non-name cells (match: **YES**).

## Top 10 most-gappy columns

| Column | Gaps | fillable | no-cite | shallow |
|---|---:|---:|---:|---:|
| `cons` | 515 | 0 | 515 | 0 |
| `desc` | 515 | 0 | 515 | 0 |
| `links` | 515 | 0 | 515 | 0 |
| `pros` | 515 | 0 | 515 | 0 |
| `type` | 515 | 0 | 515 | 0 |
| `schema-evolution` | 485 | 91 | 394 | 0 |
| `versioning` | 485 | 193 | 292 | 0 |
| `consistency` | 427 | 361 | 66 | 0 |
| `forgetting` | 413 | 184 | 229 | 0 |
| `tombstoning` | 403 | 253 | 150 | 0 |

## Top 10 most-gappy sections

| Section | Gaps | fillable | no-cite | shallow |
|---|---:|---:|---:|---:|
| Recent method papers — theorized, no distinct product | 2,116 | 644 | 1,462 | 10 |
| Vertical / domain-specific AI memory | 1,450 | 523 | 926 | 1 |
| Dedicated memory layers | 685 | 279 | 354 | 52 |
| Retrieval-as-memory hybrids | 528 | 109 | 419 | 0 |
| Framework-embedded memory | 500 | 180 | 282 | 38 |
| Personal AI / PKM / lifelogging memory | 448 | 135 | 311 | 2 |
| Claude Code memory mechanisms | 379 | 56 | 316 | 7 |
| Knowledge-graph platforms | 350 | 97 | 249 | 4 |
| Vector-database infrastructure | 264 | 61 | 200 | 3 |
| File-backed / editor paradigms | 236 | 17 | 219 | 0 |

## Top 20 records by total gaps

| Record | Tier | Section | Gaps |
|---|:--:|---|---:|
| SearchUnify | T1 | Enterprise-search adjacencies | 26 |
| ASAPP GenerativeAgent | T1 | Vertical / domain-specific AI memory | 25 |
| Convai (Mimir) | T1 | Vertical / domain-specific AI memory | 25 |
| Hebbia Matrix | T2 | Vertical / domain-specific AI memory | 25 |
| Personal.ai | T2 | Personal AI / PKM / lifelogging memory | 25 |
| Ratine | T2 | Memory observability & monitoring | 25 |
| Sanctuary AI Carbon (Phoenix Gen 7/8) | T1 | Vertical / domain-specific AI memory | 25 |
| Sandbar Stream | T2 | Voice-first / wearable AI memory | 25 |
| Spellbook Library | T1 | Vertical / domain-specific AI memory | 25 |
| Tencent ima.copilot | T1 | Personal AI / PKM / lifelogging memory | 25 |
| π0.5 (Physical Intelligence) | T1 | Vertical / domain-specific AI memory | 24 |
| Capacities | T2 | Personal AI / PKM / lifelogging memory | 24 |
| claude-mem | T1 | Claude Code memory mechanisms | 24 |
| Clio Duo / Manage AI | T2 | Vertical / domain-specific AI memory | 24 |
| CoCounsel Legal (Thomson Reuters) | T2 | Vertical / domain-specific AI memory | 24 |
| Cresta | T2 | Vertical / domain-specific AI memory | 24 |
| Decagon | T1 | Vertical / domain-specific AI memory | 24 |
| Figure Helix | T1 | Vertical / domain-specific AI memory | 24 |
| FutureHouse | T1 | Vertical / domain-specific AI memory | 24 |
| GraphRAG (Microsoft) | T1 | Retrieval-as-memory hybrids | 24 |

## By category

| Category | Records | Total cells | Fillable gaps | NA-terminal | Terminal-filled | Gap rate |
|---|---:|---:|---:|---:|---:|---:|
| Round-7 sections (Training / Search / Frameworks / Inference / Embedding / Eval) | 146 | 8,760 | 0 | 1,724 | 867 | 0.0% |
| Original memory sections | 553 | 33,180 | 8,592 | 14,606 | 7,127 | 25.9% |
| Research papers / theory / benchmarks | 229 | 13,740 | 2,524 | 8,731 | 1,835 | 18.4% |

## Phase-2 effort estimate

- `fillable-and-missing`: 2,584
- `real-data-no-citation`: 5,865
- `shallow-prose`: 143

At ~5 min/cell to research-and-fill a fillable, ~1 min/cell to locate a citation for a no-cite real-data row, and ~3 min/cell to enrich shallow prose:

- Estimated phase-2 effort: **19,214 min ≈ 320 h**.

(Estimate is wall-clock for a single agent working serially; deep-fill rounds can parallelise across records.)
