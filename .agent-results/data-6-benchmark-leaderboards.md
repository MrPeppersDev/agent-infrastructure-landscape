# Memory Benchmark Leaderboards: Chronological Leader History

**Methodology note.** No live leaderboard exists for most of these benchmarks. This reconstruction is derived from published papers, vendor blog posts, and GitHub issues. Dates are publication/announcement dates, not the date a score was first achieved. Vendor-published numbers are self-reported; independent reproducibility varies. Treat any single figure with caution.

---

## LongMemEval (ICLR 2025)

**Benchmark.** Wang et al., arXiv 2410.10813, accepted ICLR 2025. 500 questions, 5 memory abilities (information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention). Two variants: **LongMemEval-S** (~115k token histories, 30-40 sessions) and **LongMemEval-M** (~500 sessions, ~1.5M tokens). Most vendor benchmarks run on LongMemEval-S. The official leaderboard is maintained at the GitHub repo (xiaowu0162/LongMemEval); vendor claims are often published independently and not verified by the benchmark authors.

### Chronological leader history (LongMemEval-S unless noted)

| Date | System | Score | Notes |
|------|--------|-------|-------|
| Oct 2024 | GPT-4o (full-context, oracle) | ~87-92% | Original paper, oracle setting (only relevant sessions given). Published in arXiv preprint. |
| Oct 2024 | GPT-4o (full-context, full history) | ~60-64% | Original paper baseline. Phi-3-Medium 34-38%, Llama 3.1-8B 42-45%. |
| Late 2024 | LongMemEval authors' RAG framework | ~68% (estimated) | Paper's proposed three-stage system; exact number not independently confirmed in searched sources. |
| Jun 2025 | Emergence AI — EmergenceMem Simple | 82.4% | Public/reproducible config. Blog post June 2025. |
| Jun 2025 | Emergence AI — EmergenceMem Internal | 86.0% | Internal/non-reproducible config. Claimed SOTA at time of publication; surpassed oracle GPT-4o. |
| Feb 2026 | Mastra Observational Memory | 94.87% | Used gpt-5-mini backbone. Open-source. Published Feb 9, 2026. Claimed highest score at time. |
| ~Feb 2026 | OMEGA | 95.4% (466/500) | pip-installable local-first system. Timing relative to Mastra not fully clear; both claim #1 depending on metric framing. |
| ~Apr 2026 | MemPalace | 96.6% | Self-reported. Disputed: Vectorize and Gamgee reviews note the 96.6% figure is a retrieval-only metric (recall_any@5), not a QA accuracy score, making it non-comparable to the official leaderboard. See contested claims below. |

**Contested claims — MemPalace.** MemPalace initially claimed 100% (later revised to 96.6%). Independent reviews (Vectorize, Gamgee, GitHub issue #29) concluded the score measures retrieval recall only, without answer generation or LLM-as-judge evaluation, and is therefore not comparable to other entries on the LongMemEval leaderboard. The 96.6% figure should be read as "96.6% retrieval recall" not "96.6% QA accuracy."

**ByteRover** also published 92.8% on LongMemEval-S (announced as "top market accuracy"). This is a vendor blog claim; independent verification not found.

---

## LoCoMo (Long Conversation Memory)

**Benchmark.** Maharana et al., arXiv 2402.17753, ACL 2024. Published Feb 2024. 10 very long conversations, ~300 turns, ~9K tokens per conversation, up to 35 sessions. Tasks: QA (single-hop, multi-hop, temporal, open-domain), event summarization, multi-modal dialogue generation. Metric is primarily F1 for QA; some vendors report accuracy (J-score).

### Chronological leader history

| Date | System | Score | Notes |
|------|--------|-------|-------|
| Feb 2024 | GPT-4 (baseline) | F1 ~32.1 | Original paper. Human ceiling 87.9 F1. Mistral-7B: 13.9. |
| ~2024 | Long-context / RAG augmented variants | F1 ~37-42 | Original paper best augmented baselines. 22-66% improvement over vanilla but still 56 points below human. |
| ~Late 2024 | Zep | 84% (claimed) | Zep original blog/paper claim. Disputed — see below. |
| Apr 2025 | Mem0 (Mem0 Graph) | ~65% (J-score) | Mem0 paper arXiv 2504.19413, April 28 2025. Claimed SOTA; Zep disputed this. |
| Apr 2025 | Letta (file-based) | 74.0% | Letta blog post, gpt-4o-mini backbone. Simple file storage. |
| Sep 2025 | MemMachine v1 | 0.8487 overall | MemMachine blog Sep 2025. Claimed to outperform Mem0, Zep, Memobase. |
| Dec 2025 | MemMachine v0.2 | Not specified precisely | MemMachine blog Dec 2025, described as "industry-leading." |
| Mar 2026 | MemMachine (gpt-4.1-mini) | 0.9169 | MemMachine blog, gpt-4.1-mini backbone. Among strongest published. |
| 2026 | Mem0 (token-efficient algorithm) | 91.6 | Mem0 research page, gpt-4.1-mini backbone. |
| ~2026 | ByteRover 2.0 | 92.2% | ByteRover blog. Revised upward to 96.1% in later claim. |

### Contested: Mem0 vs Zep on LoCoMo

This is the most publicly documented benchmark dispute in the memory systems space.

**Zep's original claim (late 2024 / early 2025).** Zep published an 84% score on LoCoMo. The claim appeared in a blog post and associated paper repo (getzep/zep-papers).

**Mem0's counter (April 2025).** Mem0 published arXiv 2504.19413 claiming SOTA on LoCoMo. Simultaneously, via GitHub issue getzep/zep-papers #5 and a blog post, Mem0 argued Zep's 84% was inflated because it included the adversarial question category, which the LoCoMo benchmark specification explicitly excludes. Mem0's corrected evaluation of Zep yielded 58.44%. Mem0 also standardized the system prompt used for evaluation.

**Zep's counter-counter.** Zep responded (blog.getzep.com) that Mem0 had misconfigured Zep in their evaluation. Zep's own corrected number was 75.14% (±0.17 J-score), which they claimed was ~10% above Mem0's best configuration (Mem0 Graph).

**Status.** Unresolved. Independent practitioners (GitHub issue getzep/zep #405) reported inability to reproduce either set of published numbers when running the open-source benchmark locally. The dispute exposed that LoCoMo's adversarial category handling is ambiguous in the original evaluation spec, and that vendor-run benchmarks comparing their own product against a competitor's are structurally unreliable.

---

## ConvoMem

**Benchmark.** Salesforce Research, arXiv 2511.10523, November 2025. 75,336 QA pairs across six categories: User Facts, Assistant Facts, Abstention, Preferences, Changing Facts, Implicit Connections. Dataset available on HuggingFace (Salesforce/ConvoMem). Primary finding is methodological rather than a leaderboard: long-context approaches outperform RAG-based memory systems (like Mem0) for conversation histories under ~150 interactions.

No live leaderboard or chronological SOTA race found. The paper is a single-publication benchmark. Key results:

- Full-context achieves 70-82% on multi-message evidence cases
- Mem0 (RAG-based) achieves 30-45% on preferences and 25-45% on implicit connections vs 63-90% for long context in the same categories
- Mid-tier flash-class models are cost-optimal; larger models show diminishing returns

**Summary.** No external system has published a claimed #1 on ConvoMem. It functions as a research benchmark, not a competitive leaderboard.

---

## MemoryAgentBench

Paper: "Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions," Hu, Wang, McAuley, arXiv 2507.05257, ICLR 2026 (GitHub: HUST-AI-HYZ/MemoryAgentBench). Evaluates four competencies: accurate retrieval, test-time learning, long-range understanding, conflict resolution. No live leaderboard found; no external systems claiming #1. Functions as an academic evaluation framework.

---

## MemBench

Paper: "Towards More Comprehensive Evaluation on the Memory of LLM-based Agents," ACL 2025 Findings, arXiv 2506.21605. Evaluates effectiveness, efficiency, and capacity. No live leaderboard or competitive SOTA race found in searched sources.

---

## MemoryBench

Paper: arXiv 2510.17281, focused on memory and continual learning. No leaderboard or competitive claims found in searched sources.

---

## Cross-Benchmark Observations

1. **Self-reported vs independent.** Almost all high scores are self-reported by the system's own team. Independent reproduction is the exception, not the rule. The Mem0/Zep dispute is the only case where opposing teams publicly cross-checked each other's numbers.

2. **Model dependency.** Scores are not just system scores — they are (system + backbone LLM) scores. Mastra's 94.87% used gpt-5-mini; Emergence's best used an internal model. Scores are not portable across model generations.

3. **Benchmark version fragmentation.** Most vendors specify LongMemEval-S; almost none publish LongMemEval-M results. This means the leaderboard reflects a shorter-context version of the benchmark, not the hardest variant.

4. **Metric drift.** LoCoMo results appear in F1, accuracy, and J-score depending on the paper. These are not interchangeable. The Mem0/Zep dispute was partly a dispute about which metric and which question categories to use.

5. **Recency bias.** Scores above 90% on LongMemEval and LoCoMo are all post-2025 and use gpt-4.1-mini or gpt-5-mini. It is not possible to cleanly separate "better memory system" from "better backbone model."

