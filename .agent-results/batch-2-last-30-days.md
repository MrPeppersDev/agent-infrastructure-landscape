# Batch 2 — Last-30-days launches (10 entries, all NEW)

Returned by background research agent on 2026-05-06. All 10 verified absent from landscape.html. Distributed across multiple sections.

## 1. Anthropic Managed Agents Memory (T3) — Platform-provider memory
- URL: https://platform.claude.com/docs/en/managed-agents/overview
- Memory model: Filesystem-backed cross-session persistent memory for managed agents
- What it does: Mounts memory as files on a managed filesystem; Claude reads/writes via the same bash/code-execution tools used for agentic tasks. Unit of storage is a file — inspectable, editable, exportable. Full audit log per session.
- Claims: Rakuten reported 97% fewer first-pass errors, 27% lower cost, 34% lower latency. Memory beta launched April 23, 2026 (two weeks after Managed Agents launched April 8).
- Pros: Filesystem metaphor aligns with Claude's existing tool-use primitives; no separate embedding pipeline; human-auditable without special tooling.
- Cons: Memory granularity and eviction policy not yet documented publicly; filesystem-as-memory has known scalability limits at large knowledge volumes; beta status means API surface may change.
- Links: platform.claude.com docs · Techzine · TestingCatalog

## 2. MemMachine paper (T4) — method papers / experiential
- URL: https://arxiv.org/abs/2604.04853
- Memory model: Ground-truth-preserving episodic + profile memory with cluster-expansion retrieval
- What it does: Stores raw conversational episodes without LLM-driven extraction, indexing at sentence level; retrieval expands nucleus matches into neighboring-context clusters to address embedding-dissimilarity in dialogue data. Retrieval Agent routes queries across direct, parallel-decomposition, or iterative chain-of-query strategies.
- Claims: 0.9169 on LoCoMo (gpt-4.1-mini) — above Mem0, Zep, Memobase, LangMem; 93.0% on LongMemEvalS; ~80% fewer input tokens than Mem0 in matched comparisons.
- Pros: Ground-truth preservation avoids factual hallucination risk of extraction-based condensation; cluster-expansion retrieval directly targets the embedding-dissimilarity gap.
- Cons: Storing raw episodes grows storage linearly with conversation length; no published evaluation on months-scale interactions.
- Links: arxiv 2604.04853

NOTE: Distinct from existing "MemMachine" framework entry on github.com/MemMachine/MemMachine. The paper and framework are separate items.

## 3. MIA — Memory Intelligence Agent (T4) — method papers / experiential
- URL: https://arxiv.org/abs/2604.04503
- Memory model: Manager-Planner-Executor with bidirectional parametric/non-parametric memory loop
- What it does: Manager stores compressed non-parametric search trajectories; Planner is a parametric memory agent producing search plans; Executor acts on plans. Planner evolves via test-time learning (on-the-fly weight updates during inference), creating bidirectional conversion between parametric and non-parametric memory.
- Claims: Superior performance across 11 benchmarks for deep research agents (DRAs); alternating RL paradigm enhances Planner-Executor cooperation.
- Pros: Test-time parametric learning means the Planner genuinely improves within a session without fine-tuning infra; bidirectional loop is novel vs read-only RAG or write-only episodic stores.
- Cons: Test-time weight updates raise inference cost significantly; eval is research-oriented tasks — generalization to conversational/tool-use agents not yet demonstrated.
- Links: arxiv 2604.04503

## 4. From Human Memory to AI Memory survey (T4) — Theoretical / informal
- URL: https://arxiv.org/abs/2504.15965
- Memory model: Three-dimensional taxonomy (object × form × time) mapping human memory types to LLM mechanisms
- What it does: Eight-quadrant classification grid across personal/system, parametric/non-parametric, short-term/long-term axes. Bridges cognitive science memory taxonomy to LLM architecture choices.
- Claims: 26-page survey covering encoding/storage/retrieval; v2 revision April 23, 2025.
- Pros: 3D taxonomy provides orthogonal categorization axes that cut across existing framework-centric surveys; cognitive-science grounding enables comparison with neuroscience literature.
- Cons: Submitted April 2025 — coverage of 2026 methods is limited; positions itself as a survey, not a method.
- Links: arxiv 2504.15965

NOTE: The user's original target was "Memory in the LLM Era" — this is the closest April-window match. Title contains "in the Era of LLMs."

## 5. ImplicitMemBench (T3) — Memory benchmarks
- URL: https://arxiv.org/abs/2604.08064
- Memory model: Benchmark for implicit/procedural memory — procedural learning, priming, classical conditioning
- What it does: 300 items across procedural memory, priming, and classical conditioning paradigms. Unified learning-interference-test protocol with first-attempt scoring to isolate automatized behavior — distinct from explicit-recall benchmarks.
- Claims: 17 models evaluated; no model exceeds 66% overall. Top: DeepSeek-R1 65.3%, Qwen3-32B 64.1%, GPT-5 63.0%. Reveals dramatic asymmetries (inhibition 17.6% vs preference 75.0%).
- Pros: First benchmark targeting implicit (non-declarative) memory in LLMs; exposes a category of memory failure invisible to all existing explicit-memory benchmarks.
- Cons: 300 items is small; "classical conditioning" in LLMs is contested mechanistically — operationalization may reflect prompt-following rather than true conditioning.
- Links: arxiv 2604.08064

## 6. MemEvoBench (T4) — Memory benchmarks
- URL: https://arxiv.org/abs/2604.15774
- Memory model: Safety-oriented benchmark for adversarial memory evolution across multi-round interactions
- What it does: QA tasks across 7 domains / 36 risk types + workflow tasks adapted from 20 Agent-SafetyBench environments with noisy tool returns; mixed benign-and-misleading memory pools in multi-round interactions. Targets memory evolution safety, not recall accuracy.
- Claims: Substantial safety degradation under biased memory updates; static prompt defenses insufficient (April 17, 2026).
- Pros: Addresses an unexamined attack surface — adversarial memory injection into agents with evolving long-term stores — rather than standard retrieval accuracy.
- Cons: Too new for independent replication; 36 risk types lack a formal threat-model taxonomy; no comparison against known memory-safety defenses.
- Links: arxiv 2604.15774

## 7. Memory as Metabolism (T5) — Theoretical / informal
- URL: https://arxiv.org/abs/2604.12034
- Memory model: Five-operation metabolic governance cycle (TRIAGE, DECAY, CONTEXTUALIZE, CONSOLIDATE, AUDIT) with gravity and minority-hypothesis retention
- What it does: Argues companion AI knowledge systems must treat memory as a continuous metabolic process. Proposes three-tier store (raw buffer, active wiki, cold memory) governed by five operations, memory gravity (recency/frequency), and explicit minority-hypothesis retention to counter worldview entrenchment.
- Claims: Normative framework with testable conformance invariants; positioned within the 2026 governance-proposals cluster (Context Cartography, MemOS). No empirical evaluation.
- Pros: Addresses companion-specific ossification and paradigm-reinforcement — failure modes not modeled by performance-oriented benchmarks; includes conformance-testable invariants.
- Cons: Entirely theoretical/design; no implementation, benchmark, or ablation; conformance invariants are not formally specified in the preprint.
- Links: arxiv 2604.12034 · memorypapers.org

## 8. Era Computer (T5) — Voice-first / wearable
- URL: https://techcrunch.com/2026/04/23/era-computer-raises-11m-to-build-a-software-platform-for-ai-gadgets/
- Memory model: User-sovereign pluggable memory layer for AI wearable OS
- What it does: Software platform / OS layer for AI wearables (glasses, rings, pendants, speakers) that abstracts hardware from AI orchestration. Users choose their own memory and model providers in a privacy-preserving way; supports 130+ LLMs from 14+ providers.
- Claims: $11M raised April 23, 2026 ($9M seed Abstract Ventures + BoxGroup; $2M pre-seed Topology + Betaworks). Founded 2025 by ex-Humane team.
- Pros: Addresses the vendor lock-in problem for wearable memory directly; neutral OS positioning means memory sovereignty is a first-class design constraint.
- Cons: No shipping product described; memory architecture is high-level positioning, not a published technical design; category is highly competitive (Apple, Meta, Google).
- Links: TechCrunch funding · TechFundingNews

## 9. ICLR 2026 MemAgents Workshop (T2) — Memory benchmarks
- URL: https://sites.google.com/view/memagent-iclr26/
- Memory model: Workshop venue bridging RL, cognitive psychology, and LLM memory architectures
- What it does: Full-day hybrid workshop held April 27, 2026, Rio de Janeiro. Scope spans episodic/semantic/working/parametric memory, KGs, vector DBs, retrieval pipelines, context management, long-context utilization, temporal credit assignment.
- Claims: Accepted papers include MemoryAgentBench (ICLR 2026 main track), CraniMem, MemAgent oral. Submission deadline February 2026.
- Pros: Only dedicated memory-for-agents venue at a top-tier ML conference in 2026; neuroscience/RL bridge differentiates from purely engineering-oriented workshops.
- Cons: Workshop proceedings not yet indexed in major databases; paper acceptance criteria/review quality vary across workshop tracks.
- Links: workshop site · OpenReview · ICLR virtual page

## 10. Externalization in LLM Agents (T4) — Theoretical / informal
- URL: https://arxiv.org/abs/2604.08224
- Memory model: Externalization framework — memory as state externalisation across time, coupled with skills and protocols in a harness layer
- What it does: Traces shift from weights-as-capability to harness-as-capability; analyzes memory, skills, and protocols as three coupled forms of externalization. Memory specifically defined as externalization of state across time. Covers self-evolving harnesses and shared agent infrastructure.
- Claims: No empirical evaluation; positions as a unifying conceptual review across memory/skills/protocol triad that most papers treat separately.
- Pros: Unified framework makes the coupling between memory, skills, and protocols explicit — absent from most memory-only surveys; harness-engineering layer is underexamined.
- Cons: Conceptual/review paper only; no new method, no benchmarks; assessment of "open challenges" is speculative given the field's pace.
- Links: arxiv 2604.08224
