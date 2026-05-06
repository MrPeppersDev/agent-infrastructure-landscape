# Benchmark Coverage — AI Memory Systems Landscape

**Source:** `/Users/b.sayer/src/memory-analysis-program/landscape.html`
**Date produced:** 2026-05-06
**Rows in CSV:** 58 (system × benchmark triples with scores)

---

## What Was Found

The landscape covers roughly 240 entries. Of those, approximately 25 systems publish at
least one numeric benchmark score. The rest either claim qualitative improvements over
baselines ("outperforms X"), report latency/throughput metrics only, or have no public
evaluation at all. The benchmarks in the CSV fall into four groups by competitive density.

---

## Benchmark Competition — By Category

### Memory-specific benchmarks: active competition

**LongMemEval-S** is the most-contested single benchmark in the catalog. At least
nine systems report a score or claim: Letta (83.2%), Memoria/MatrixOrigin (88.78%),
Hindsight (91%), ByteRover (92.8%), EverMemOS (83.0%), OMEGA (95.4%), Mastra
Observational Memory (94.87% with gpt-5-mini, 84.23% with gpt-4o), MemMachine paper
(93.0%), MemPalace (96.6% — but disputed), and Supermemory (claims #1 overall). The
LongMemEval-S leaderboard is a vendor marketing battleground; four separate "highest ever"
claims appeared in 2025-2026 within months of each other. Two results are explicitly
disputed in the landscape: MemPalace's 96.6% is Recall@5 not QA accuracy (not
comparable), and MemPalace later inflated to 98.4% on held-out data after criticism.

**LoCoMo** (LOng-COnversation Memory) is the second major battleground. Published scores
range from Letta's 74.0%, SuperLocalMemory Mode A's 74.8% (zero LLM), ByteRover's 92.2%,
Zep's 84% (contested), Mem0's 91.6%, MemMachine paper's 0.9169 (composite), and
SuperLocalMemory Mode C's 87.7%. The LoCoMo score space is actively disputed: Zep published
a counter-analysis accusing Mem0 of misconfiguring the adversarial category to inflate their
score; Mem0 disputes this in return. EVOLVE-MEM claims 58.3% SOTA across five reasoning
categories at NeurIPS 2025 but this is below other vendors' self-reported scores, suggesting
different evaluation setups.

**ConvoMem** appears in the landscape but only with shallow coverage: Mem0 reports 30 (out of
what denominator is unclear) and Supermemory claims #1. No inter-system comparison exists
outside vendor claims.

**MemoryAgentBench** (ICLR 2026 main track) is notable for a meta-finding: agents that
achieve near-perfect LoCoMo scores fail badly on true agentic multi-session tasks. This
suggests the LoCoMo / LongMemEval-S competitive cluster may be measuring something
systematically different from what production agentic memory requires.

**ImplicitMemBench** (arxiv 2604.08064) is a new April 2026 benchmark targeting implicit
(procedural, priming, conditioning) memory. Results on 17 models: no model exceeds 66%.
Top performers DeepSeek-R1 (65.3%), Qwen3-32B (64.1%), GPT-5 (63.0%). This benchmark
has no inter-system competition yet — it is paper-side only.

**BAI-LAB MemoryOS** (EMNLP 2025 Oral) and **MemInsight** (EMNLP 2025 Main) report only
relative improvements over unspecified baselines on LoCoMo (+48.36% F1 and +34% recall
respectively), which makes direct inter-system comparison impossible.

### Long-context benchmarks: present but mostly paper-side

**RULER**, **LongBench**, and **NIAH** appear in the dataset primarily through ShadowKV
(ByteDance, ICML 2025 Spotlight), which validated no-accuracy-loss with 6x batch / 3.04x
throughput across Llama-3.1, GLM-4, Yi, Phi-3, Qwen2. ATLAS (arxiv 2505.23735) claims
+80% accuracy at 10M context on BABILong. GAM (arxiv 2511.18423) claims >90% on RULER
Multi-Hop Tracing vs competing methods below 60%. Engram (DeepSeek) reports Multi-Query
NIAH 84.2→97.0 vs an iso-FLOPs MoE baseline.

These are point claims from individual papers, not a shared leaderboard. No cross-system
RULER or BABILong leaderboard exists in the landscape.

### RAG/Retrieval benchmarks: sparse, relative-only

KAG reports +33.5% F1 on HotpotQA and +19.6% on 2WikiMultiHopQA (both relative, deployed
at Ant Group). LongRAG reports absolute scores: Recall@1 NQ 52→71%, EM 62.7%; Recall@2
HotpotQA 47→72%, EM 64.3%. Speculative RAG claims +12.97% on PubHealth and SOTA on
TriviaQA/MuSiQue/ARC-Challenge without publishing absolute numbers. RAFT claims
consistent improvements on PubMed and HotpotQA without specifics.

**BEIR, MTEB, KILT, MS MARCO, NaturalQuestions, HotpotQA as full leaderboards** are not
represented in the landscape's memory-system catalog — the landscape focuses on agent memory
rather than retrieval infrastructure, so pure retrieval benchmarks appear only as sub-results
within paper claims.

### Coding/embodied benchmarks: absent

**SWE-bench, HumanEval, MBPP, LiveCodeBench** — none of the memory systems in the landscape
report scores on coding benchmarks. ByteRover is described as coding-agent-focused but does
not publish SWE-bench numbers.

**ALFWorld and ScienceWorld** appear once: CDMem (NAACL 2025 Industry) reports 85.8% and
56.0% respectively. No other memory system in the catalog publishes embodied/robotic benchmark
results.

**MedQA/USMLE, LegalBench, AgentBench, ToolBench** — not present in the landscape's catalog
at all. The landscape covers memory layers, not domain-specialized assistants.

---

## Notable Findings

1. **The LongMemEval-S / LoCoMo axis is where all vendor competition concentrates.** These
   two benchmarks have effectively become marketing instruments — multiple systems claim SOTA
   with incompatible setups (different backbones, different adversarial-category inclusion,
   different score metrics). The MemPalace / Recall@5 vs QA accuracy confusion is the
   clearest example of score inflation via metric substitution.

2. **MemoryAgentBench (ICLR 2026) is the most important finding for the field.** It directly
   challenges the validity of LoCoMo as a proxy for production agentic memory — systems
   that saturate LoCoMo fail on true multi-step agentic tasks. This is a known benchmark
   validity problem the landscape has flagged but few vendors have responded to.

3. **Zero-LLM-dependency approaches are underrepresented.** SuperLocalMemory Mode A achieves
   74.8% LoCoMo with zero API calls, which is competitive with most LLM-dependent systems.
   This benchmark dimension (accuracy at zero inference cost) is not tracked by any leaderboard.

4. **Backbone model inflation is systematic.** Scores reported with gpt-5-mini or gpt-4.1-mini
   are not comparable to scores with gpt-4o-mini or Llama baselines. The landscape tags
   backbone where known, but most vendor claims omit this detail.

5. **ImplicitMemBench represents a genuine gap.** All current high-scoring systems are evaluated
   on explicit declarative recall. No system in the catalog has been evaluated on procedural or
   priming memory. The 65% ceiling on ImplicitMemBench across 17 models suggests this is a
   structural blind spot.
