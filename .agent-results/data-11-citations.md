# AI Memory Systems — Citation Analysis

**Source:** Semantic Scholar API (queried 2026-05-06)
**Coverage:** 189 papers from T3/T4/T5 rows in landscape.html
**Method:** Bulk arXiv lookup via S2 `/paper/batch` endpoint. Citations-per-year computed as `total_citations / (2026 - year)`. For 2025 papers this is a single-year rate; for 2026 papers the count is essentially zero or very small (recency artifact, noted explicitly below). Semantic Scholar "influential citations" is S2's proprietary metric counting citations that substantially engage with a paper, not just cite it in passing.

---

## Top 20 Most-Cited Memory Papers

| # | Paper | Year | Total Citations | Influential | Tier |
|---|-------|------|-----------------|-------------|------|
| 1 | EWC (Elastic Weight Consolidation) | 2016 | 9,640 | 1,355 | T3 |
| 2 | Transformer-XL | 2019 | 4,287 | 437 | T3 |
| 3 | Generative Agents | 2023 | 3,896 | 255 | T3 |
| 4 | Toolformer | 2023 | 3,628 | 149 | T3 |
| 5 | Reflexion | 2023 | 3,240 | 272 | T3 |
| 6 | REALM | 2020 | 2,929 | 233 | T3 |
| 7 | Self-RAG | 2023 | 1,776 | 186 | T4 |
| 8 | RETRO | 2021 | 1,624 | 109 | T3 |
| 9 | ToolLLM | 2023 | 1,456 | 211 | T3 |
| 10 | BGE-M3 | 2024 | 1,241 | 122 | T4 |
| 11 | LongBench | 2023 | 1,198 | 304 | T3 |
| 12 | Atlas | 2022 | 1,187 | 83 | T3 |
| 13 | DreamerV3 | 2023 | 1,030 | 155 | T3 |
| 14 | Compressive Transformer | 2019 | 832 | 111 | T3 |
| 15 | RULER | 2024 | 820 | 204 | T3 |
| 16 | I-JEPA | 2023 | 773 | 90 | T3 |
| 17 | NVIDIA Isaac GR00T N1.7 | 2025 | 677 | 107 | T3 |
| 18 | HyDE | 2022 | 667 | 77 | T3 |
| 19 | FLARE | 2023 | 622 | 28 | T3 |
| 20 | Genie | 2024 | 511 | 45 | T3 |

**Observations.** The top-20 list is almost entirely T3 (established landmark papers). Only Self-RAG (T4) breaks into the top 10 as a non-T3 entry. EWC dominates on raw count because it has been accumulating citations since 2016 — its lead is a temporal artifact, not evidence of current primacy. The 2023 cohort (Generative Agents, Toolformer, Reflexion) are the most impactful recent additions, each accumulating 3,000+ citations in under three years.

LongBench stands out with 304 influential citations — the highest influential-citation count in the top 20 after EWC, suggesting it is heavily engaged-with rather than merely cited. RULER (204 influential) and ToolLLM (211) also punch above their weight on this metric.

---

## Top 10 by Citations Per Year — The Actively-Cited Cluster

This table filters to papers from 2019 onward with at least 50 total citations, then ranks by annual rate. Older papers' rates are diluted by their age; this view surfaces what the field is actually reading *now*.

| # | Paper | Year | Citations/Year | Total Citations | Tier |
|---|-------|------|---------------|-----------------|------|
| 1 | Generative Agents | 2023 | 1,299/yr | 3,896 | T3 |
| 2 | Toolformer | 2023 | 1,209/yr | 3,628 | T3 |
| 3 | Reflexion | 2023 | 1,080/yr | 3,240 | T3 |
| 4 | NVIDIA Isaac GR00T N1.7 | 2025 | 677/yr | 677 | T3 |
| 5 | BGE-M3 | 2024 | 620/yr | 1,241 | T4 |
| 6 | Transformer-XL | 2019 | 612/yr | 4,287 | T3 |
| 7 | Self-RAG | 2023 | 592/yr | 1,776 | T4 |
| 8 | REALM | 2020 | 488/yr | 2,929 | T3 |
| 9 | ToolLLM | 2023 | 485/yr | 1,456 | T3 |
| 10 | A-MEM | 2025 | 443/yr | 443 | T3 |

**Observations.** Three papers — Generative Agents, Toolformer, and Reflexion — form a clear leading cluster, each above 1,000 citations per year and all from 2023. This is the strongest concentration of recent citation velocity in the entire catalog. They represent the inflection point where memory became a first-class concern for LLM agent design rather than an infrastructure detail.

Transformer-XL (2019) at rank 6 is notable: a seven-year-old architecture paper still accumulating 612 citations per year, indicating it remains the foundational reference for recurrence-based context extension. BGE-M3 (2024) at rank 5 is the fastest-rising infrastructure paper — a multilingual embedding model that has become the de-facto retrieval backbone for memory-augmented systems.

A-MEM (2025, rank 10) at 443 citations in its first year is the fastest-rising 2025 entry, suggesting the Zettelkasten-style agent memory paradigm it introduces is being adopted quickly.

---

## Notes on Recency and Coverage

**2025 papers.** 102 of the 189 papers are from 2025. Their citations-per-year figures are single-year rates and should be read as early signals, not steady-state velocity. Papers with ≥50 citations in a single year (NVIDIA Isaac GR00T N1.7, A-MEM, V-JEPA 2 at 316, MemAgent at 119, MEM1 at 103) are already performing at a level comparable to mid-tier 2023 papers.

**2026 papers.** Eight papers show zero or near-zero citations: MemEvoBench, MIA, ImplicitMemBench, HeLa-Mem, Memory as Metabolism, RGMem, MMAG (all 2026). This is expected — Semantic Scholar's index lags by weeks to months and 2026 submissions have had minimal time to accumulate citations. These should not be read as low-impact; citation counts are simply not yet meaningful.

**Not in landscape.html.** Several oft-cited memory papers (MemGPT / OpenMemGPT, Cognitive Architectures for Language Agents, etc.) may appear in non-T3/T4/T5 rows and are therefore not in this dataset. The CSV covers only the 189 unique arxiv IDs extracted from T3/T4/T5 rows.

**Full data.** See `data-11-citations.csv` for all 189 papers with arxiv IDs, Semantic Scholar paper IDs, and computed annual rates.
