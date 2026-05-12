# Data-gap audit summary

- Records scanned: **699**
- Cells scanned: **41,940**
- Gap rows (CSV): **296**
- High-priority queue (priority >= 10): **2**

## Counts by class

| Class | Count |
|---|---:|
| `fillable-and-missing` | 56 |
| `real-data-no-citation` | 106 |
| `shallow-prose` | 134 |
| `structurally-not-applicable` | 16,485 |
| `searched-not-found` | 10,933 |
| `terminal-real-data` | 14,226 |
| **sum** | **41,940** |

Sanity: 41,940 classified cells vs 41,940 non-name cells (match: **YES**).

## Top 10 most-gappy columns

| Column | Gaps | fillable | no-cite | shallow |
|---|---:|---:|---:|---:|
| `orchestration` | 58 | 0 | 0 | 58 |
| `schema-evolution` | 34 | 0 | 34 | 0 |
| `api-surface` | 27 | 0 | 0 | 27 |
| `namespace` | 26 | 0 | 26 | 0 |
| `import-export` | 22 | 4 | 0 | 18 |
| `forgetting` | 13 | 0 | 13 | 0 |
| `a2a-support` | 12 | 12 | 0 | 0 |
| `founders` | 11 | 11 | 0 | 0 |
| `validated-verticals` | 11 | 0 | 0 | 11 |
| `contradiction` | 10 | 0 | 10 | 0 |

## Top 10 most-gappy sections

| Section | Gaps | fillable | no-cite | shallow |
|---|---:|---:|---:|---:|
| Vertical / domain-specific AI memory | 103 | 1 | 101 | 1 |
| Dedicated memory layers | 52 | 0 | 0 | 52 |
| Framework-embedded memory | 38 | 0 | 0 | 38 |
| Memory governance, privacy & safety | 28 | 28 | 0 | 0 |
| Recent method papers — theorized, no distinct product | 16 | 11 | 5 | 0 |
| Research / specialised systems | 14 | 0 | 0 | 14 |
| Memory observability & monitoring | 8 | 8 | 0 | 0 |
| Claude Code memory mechanisms | 7 | 0 | 0 | 7 |
| Personal AI / PKM / lifelogging memory | 7 | 5 | 0 | 2 |
| Knowledge-graph platforms | 5 | 0 | 0 | 5 |

## Top 20 records by total gaps

| Record | Tier | Section | Gaps |
|---|:--:|---|---:|
| Acuvity (now Proofpoint) | T1 | Memory governance, privacy & safety | 5 |
| Enkrypt AI | T1 | Memory governance, privacy & safety | 5 |
| HiddenLayer AISec Platform 2.0 | T1 | Memory governance, privacy & safety | 5 |
| Microsoft Agent Governance Toolkit | T2 | Memory governance, privacy & safety | 5 |
| ResearchRabbit | T2 | Vertical / domain-specific AI memory | 5 |
| WISE | T3 | Recent method papers — theorized, no distinct product | 5 |
| Character.ai | T1 | Vertical / domain-specific AI memory | 4 |
| Charisma.ai | T1 | Vertical / domain-specific AI memory | 4 |
| Cognigy | T1 | Vertical / domain-specific AI memory | 4 |
| Convai (Mimir) | T1 | Vertical / domain-specific AI memory | 4 |
| Hebbia Matrix | T2 | Vertical / domain-specific AI memory | 4 |
| Inworld AI | T1 | Vertical / domain-specific AI memory | 4 |
| Khanmigo | T2 | Vertical / domain-specific AI memory | 4 |
| SchoolAI | T2 | Vertical / domain-specific AI memory | 4 |
| Spirit AI Character Engine | T2 | Vertical / domain-specific AI memory | 4 |
| ASAPP GenerativeAgent | T1 | Vertical / domain-specific AI memory | 3 |
| ChatGPT Study Mode | T3 | Vertical / domain-specific AI memory | 3 |
| Decagon | T1 | Vertical / domain-specific AI memory | 3 |
| GitHub Copilot custom instructions | T1 | File-backed / editor paradigms | 3 |
| Intercom Fin | T2 | Vertical / domain-specific AI memory | 3 |

## By category

| Category | Records | Total cells | Fillable gaps | NA-terminal | Terminal-filled | Gap rate |
|---|---:|---:|---:|---:|---:|---:|
| Round-7 sections (Training / Search / Frameworks / Inference / Embedding / Eval) | 146 | 8,760 | 0 | 1,724 | 1,033 | 0.0% |
| Original memory sections | 553 | 33,180 | 296 | 14,761 | 13,193 | 0.9% |
| Research papers / theory / benchmarks | 229 | 13,740 | 30 | 8,779 | 3,741 | 0.2% |

## Phase-2 effort estimate

- `fillable-and-missing`: 56
- `real-data-no-citation`: 106
- `shallow-prose`: 134

At ~5 min/cell to research-and-fill a fillable, ~1 min/cell to locate a citation for a no-cite real-data row, and ~3 min/cell to enrich shallow prose:

- Estimated phase-2 effort: **788 min ≈ 13 h**.

(Estimate is wall-clock for a single agent working serially; deep-fill rounds can parallelise across records.)
