# ArXiv Memory Research Volume by Category — 2023-01 through 2026-05

## Methodology

Queries were issued to the arxiv API (`export.arxiv.org/api/query`) using title-field (`ti:`) exact-phrase searches combined with AND constraints for relevant terms (LLM, transformer, agent, reinforcement). This avoids the noise of full-text matching while staying more representative than abstract matching alone. Results were sorted by submission date (ascending) and filtered to 2023-01 through 2026-05.

**Limitations to note:**

- Title-field queries are precise but may undercounting work where authors use different terminology (e.g. "memory-augmented neural network" vs "memory-augmented transformer").
- Counts represent matched paper *mentions* per query, not deduplicated papers. A paper matching two queries in the same category is counted twice. All counts should be read as relative volume indicators, not exact paper tallies.
- For queries where total results exceeded 200 (the API cap per call): `knowledge_editing` (154 total — within cap), `JEPA` (68 — within cap), `world model agent` (93 — within cap), `continual learning + language model` (70 — within cap). No query hit the ceiling, so sample coverage is complete for the returned totals.
- The arxiv API returned HTTP 429 (rate limit) during initial attempts; a 10-second per-query delay resolved this.
- `factual_long_term` shows almost no entries before 2025, which reflects that the exact phrases "agent memory" and "personalized memory" became dominant terminology around 2024–2025. Earlier work used different framing.

---

## Category Totals (2023-01 to 2026-05)

| Category | Total Hits | Trend |
|---|---|---|
| world_model | 176 | Strong growth |
| parametric_latent | 174 | Peak 2024, plateauing |
| continual_learning | 117 | Stable, elevated |
| factual_long_term | 102 | Explosive late-2025 surge |
| working_memory | 65 | Steady, moderate growth |
| benchmarks | 12 | Emerging 2025+ |
| experiential | 9 | Nascent, sparse |
| cognitive_architecture | 10 | Flat/marginal |
| memory_augmented_rl | 3 | Near-absent |

---

## Where Research Is Concentrated

### Growing Fast

**factual_long_term** (agent memory, long-term memory + LLM, personalized memory) shows the most dramatic recent surge. Nearly invisible before mid-2025 (total 6 hits in all of 2023, 2 in 2024), the category exploded: 27 hits in 2025, then 67 hits in just the first five months of 2026. The January 2026 spike alone accounts for 19 hits — roughly equal to the entire prior two years. The inflection point is late Q3 2025.

**world_model** (world model + agent, JEPA, imagination + RL) shows the most sustained multi-year growth across the period. From 13 hits in 2023 to 36 in 2024, 65 in 2025, and already 62 in the first five months of 2026, the trajectory is consistent and steep. February 2026 peaked at 25 hits — the single highest monthly count in the entire dataset. World modeling tied to agents is clearly a dominant research frontier.

### Elevated But Plateauing

**parametric_latent** (knowledge editing, memory-augmented transformers, parametric memory) was the early leader in 2024: 73 hits vs. 16 in 2023. But the half-year breakdown shows a plateau: H1-2024 (40), H2-2024 (33), H1-2025 (37), H2-2025 (29), H1-2026 (19). This category peaked around mid-2024 and is now declining in relative prominence, likely because knowledge editing as a discrete research agenda has matured and is being absorbed into broader capability work.

**continual_learning** (continual learning + LLM, catastrophic forgetting + LLM) shows a stable elevated level with no clear directional trend: 9 hits in 2023, 36 in 2024, 48 in 2025, 24 in the first five months of 2026 (on pace for ~57 annualized). The research agenda is mature and persistent but not accelerating. Q1 2024 saw a notable cluster (7 hits in March 2024), possibly driven by benchmark releases or a survey paper drawing follow-on work.

### Steady but Moderate

**working_memory** (long context + transformer, context compression + LLM, working memory + LLM) shows consistent, modest growth: 7 in 2023 rising to 17 in 2024 and 21 in 2025, with 2026 on roughly the same trajectory. This category shows no dramatic inflection — context window research is a steady technical problem rather than a flash point.

### Sparse or Marginal

**benchmarks** (memory benchmark, long-context benchmark) is nascent: zero hits before 2024, 2 hits in H1-2024, then gradually building to 7 hits in all of 2025. Still small in absolute terms but directionally increasing — benchmarking infrastructure for memory is a 2025+ phenomenon.

**experiential** (agent self-improvement, experiential learning + agent, skill learning + LLM) and **cognitive_architecture** (cognitive architecture + LLM, ACT-R + LLM) both show flat, low-count profiles. Experiential learning as a labeled research agenda is sparse; the concepts exist in the literature under other names (RLHF, tool-using agents, self-play). Cognitive architecture work with LLMs is genuinely marginal in the arxiv corpus.

**memory_augmented_rl** (episodic memory + reinforcement) registers only 3 hits across the full period. RL research in this space appears to use different terminology ("replay buffer," "memory replay," "episodic control") that this query did not capture.

---

## Key Inflection Points

- **Late Q3 2025**: factual_long_term activates sharply — "agent memory" and "personalized memory" become viable search terms, reflecting a terminology crystallization in the field.
- **February 2026**: world_model peaks at 25 monthly hits — the highest single month across all categories and periods.
- **2024 overall**: parametric_latent and continual_learning both surge in 2024 relative to 2023, then level off — suggesting 2024 was the year LLM-specific framing overtook domain-general framing in these research areas.
- **Q1 2024 for parametric_latent**: February (11) and June (12) and October (13) 2024 are high-water months, suggesting conference submission cycles driving knowledge editing paper clusters.

