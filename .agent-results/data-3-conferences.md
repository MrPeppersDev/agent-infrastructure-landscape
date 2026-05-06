# Memory-Related Papers at Major ML/NLP Venues, 2022–2026

**Methodology note up front.** No single source provides keyword-filtered accepted-paper counts for these venues. OpenReview's API (the most direct route) was not accessible in this session. The counts below are estimates derived by: (1) confirming total accepted-paper counts from official fact sheets and Paper Copilot where available, then (2) applying keyword-rate extrapolation based on spot-check sampling of accepted-paper lists and prior-venue survey papers that categorise memory-related work. Confidence intervals are wide (+/-25–35%) and the estimates should be treated as order-of-magnitude. The one verifiable data point at the workshop level is the ICLR 2026 MemAgents workshop, which is the first dedicated memory-for-agents workshop at a major ML venue and was confirmed accepted as part of ICLR 2026's 40-workshop slate.

---

## Venue-by-Venue Findings

### NeurIPS

Total main-track acceptances: 2,672 (2022) → 3,218 (2023) → 4,037 (2024) → 5,290 (2025).

Estimated memory-related main-track papers: ~55 (2022) → ~130 (2023) → ~250 (2024) → ~390 (2025). This represents a rough share climb from ~2% to ~7% of the main track over four years. The 2023 inflection is sharp: "Augmenting Language Models with Long-Term Memory" (NeurIPS 2023, oral) is a landmark paper that framed external-memory augmentation as a first-class LLM capability. By 2024, the cluster had disaggregated into sub-areas—RAG systems (HippoRAG, RankRAG, xRAG), lifelong model editing (WISE), agent memory (AGENTPOISON, Optimus-1), and long-context compression. NeurIPS 2024 had at least 4 memory-adjacent workshops; NeurIPS 2025 added more agent-memory and benchmark-track entries.

### ICLR

Total main-track acceptances: ~1,095 (2022) → 1,574 (2023) → 2,260 (2024) → 3,684 (2025) → 5,355 (2026).

Estimated memory-related main-track papers: ~30 (2022) → ~65 (2023) → ~130 (2024) → ~260 (2025) → ~410 (2026). Share climbs from ~3% to ~7-8%. ICLR 2026 is the standout: MemAgent received an Oral designation (the conference's top tier) and the MemAgents workshop became the first dedicated memory-for-LLM-agents workshop accepted at a major ML conference. The workshop bridges reinforcement learning, retrieval augmentation, and neuroscience-inspired memory design. The convergence of RAG and reasoning into iterative retrieval pipelines is a pronounced 2026 trend at ICLR.

### EMNLP

Total main-track acceptances: 829 (2022) → 1,048 (2023) → 1,271 (2024). EMNLP 2025 data not yet confirmed.

Estimated memory-related main-track papers: ~50 (2022) → ~85 (2023) → ~120 (2024). As an NLP venue, EMNLP carries a structurally higher density of memory-adjacent work than ML-general venues because knowledge-intensive NLP, open-domain QA, and retrieval-augmented generation are core EMNLP topics. The estimated share (~6-9% of main track) is higher than at NeurIPS or ICLR on a percentage basis. EMNLP 2024 confirmed 1,271 main-track and 1,029 Findings acceptances; memory/RAG papers appear in both tracks.

### ACL

Total main-track acceptances: 701 (2022) → ~750 (2023) → 940 (2024).

Estimated memory-related main-track papers: ~35 (2022) → ~70 (2023) → ~95 (2024). ACL's share (~5-10%) is comparable to EMNLP; knowledge editing, long-context understanding, and RAG are recurring ACL tracks. The EasyEdit framework (ACL 2024) became a community standard for knowledge-editing evaluation. ACL 2024 also hosted a KnowledgeNLP workshop explicitly covering knowledge editing and memory in LLMs.

### AAAI

Total main-track acceptances: ~1,349 (2022) → 1,721 (2023) → 2,342 (2024) → ~2,600 (2025, est.).

Estimated memory-related main-track papers: ~45 (2022) → ~70 (2023) → ~100 (2024) → ~155 (2025). AAAI's memory-paper share (~3-6%) lags NeurIPS and ICLR in 2022-2023 but catches up by 2025 as agent memory and continual learning migrate from research labs to deployed systems. MemoryBank (AAAI 2024) is a notable landmark: a long-term memory system for LLMs evaluated over multi-session conversations. AAAI's broader systems orientation means more practitioner-facing memory work appears here.

---

## Cross-Venue Trends

**Fastest-growing share: ICLR.** Between 2022 and 2026, ICLR's memory-paper share roughly tripled (3% to 8%) while its total papers grew 5x. The absolute count growth is the largest of any single venue. The MemAgents workshop (2026) confirms that memory is now a mature enough subfield to warrant a dedicated ICLR venue.

**Most consistent density: EMNLP and ACL.** NLP venues have carried higher memory-paper density throughout the period because retrieval, QA, and knowledge-augmented generation are native to NLP. The growth rate is slower than at ML venues but the baseline is higher.

**Clearest inflection point: 2023.** Across all five venues, 2022→2023 shows the largest percentage jump in estimated memory-paper counts. This matches the post-ChatGPT wave: the community pivoted from studying parametric knowledge in models to asking how external memory and retrieval could extend model capability. By 2024, the questions had shifted again—from "can we augment LLMs with memory?" to "how do we evaluate, benchmark, and scale agent memory systems?"

**2025-2026 consolidation.** The 2025-2026 papers suggest the field is now differentiating: RAG+reasoning feedback loops, RL-based memory management, hierarchical and episodic memory for agents, and memory privacy/security (AgentPoison) are distinct tracks within the broader cluster.

**Workshop signal.** Dedicated memory workshops went from zero at any major venue in 2022 to NeurIPS having 4-5 adjacent workshops, ICLR hosting its first dedicated workshop (MemAgents 2026), and ACL/EMNLP adding knowledge-editing workshops. This is a reliable leading indicator that a subfield has reached critical mass.

---

## Notable Papers by Year

| Year | Paper | Venue | Significance |
|------|-------|-------|--------------|
| 2022 | Memory Efficient Continual Learning with Transformers | NeurIPS | Early memory+transformer integration |
| 2023 | Augmenting Language Models with Long-Term Memory | NeurIPS (oral) | First major LLM external-memory framing |
| 2024 | HippoRAG | NeurIPS | Neurobiologically-inspired long-term RAG |
| 2024 | WISE: Lifelong Model Editing | NeurIPS | Dual parametric memory for knowledge editing |
| 2024 | EasyEdit | ACL | Community standard for KE evaluation |
| 2024 | MemoryBank | AAAI | Multi-session LLM memory, practitioner-oriented |
| 2025 | Human-Inspired Episodic Memory for Infinite Context LLMs | ICLR | Episodic framing for unbounded context |
| 2026 | MemAgent (Oral) | ICLR | RL-based memory agent, 8K→3.5M context extrapolation |

---

## Confidence and Limitations

The main-track counts are estimates with ±25-35% uncertainty. The methodology cannot distinguish papers that use "memory" as a minor implementation detail from papers where memory is the central contribution. OpenReview API access would allow exact keyword-title/abstract counts; absent that, these figures should be used for trend direction and order-of-magnitude comparison, not precise citation.

The workshop counts (2-5 per major venue per year) are also estimates; only the ICLR 2026 MemAgents workshop was confirmed as a dedicated memory-focused workshop from primary sources.
