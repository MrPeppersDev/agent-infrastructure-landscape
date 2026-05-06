# Batch 3 — Wave-4 + industrial-lab papers (11 NEW; 5 ALREADY PRESENT; 1 UNRESOLVABLE)

Returned by background research agent on 2026-05-06.

## ALREADY PRESENT (skip — verified by agent at these line ranges):
- MemoryBench (Tsinghua THUIR) — lines 1948–1954, 4685
- MemR³ — line 1959
- Engram (DeepSeek) — lines 1937–1943
- AutoGLM (Zhipu) — lines 587–593
- M3-Agent (ByteDance) — line 576

## UNRESOLVABLE — needs exact paper ID from user:
- "NAVER trajectory memory" — could not be pinned to a specific NAVER paper. Closest candidate is RANa (arxiv 2504.03524, robot-navigation episodic retrieval, NAVER Labs Europe). Recommend user supply exact title/arxiv ID. Skipping to avoid misattribution.

## NEW — to integrate:

### 1. Sakana CTM — Continuous Thought Machines (T2) — method papers / parametric & latent
- URL: https://arxiv.org/abs/2505.05522
- Project: https://pub.sakana.ai/ctm/
- GitHub: https://github.com/SakanaAI/continuous-thought-machines
- Memory model: Neuron-synchronization recurrent thought state
- What it does: Each neuron maintains its own history of incoming activations via private per-neuron weight parameters; the model operates along a self-generated "thought step" timeline rather than the input sequence timeline. Neural synchronization across neurons is used directly as a latent representation. Distinct from Sakana NAMM (evolutionary attention memory) — CTM is an architectural rethink of the recurrent state itself.
- Claims: Strong performance on ImageNet-1K, 2D maze solving, sorting, parity, QA, RL tasks without domain-specific tuning.
- Pros: Architecture-agnostic over data modality — can apply sequential "thought" to static inputs (images, graphs) that lack inherent sequence.
- Cons: Research prototype; no production deployment; eval set is narrow and does not include long-document or multi-session memory tasks comparable to RAG or KV-cache work.

### 2. NAVER Provence + PISCO (T2) — method papers / parametric & latent (or new context-compression sub-group)
- Provence URL: https://arxiv.org/abs/2501.16214
- PISCO URL: https://arxiv.org/abs/2501.16075
- Memory model: RAG context pruning and soft compression
- What it does: Provence fine-tunes a DeBERTa model as a sequence labeler to dynamically detect needed pruning amount per query and mask irrelevant context spans before generation — unifying pruning with reranking. PISCO is a complementary distillation-only approach (no annotated data, no pretraining) that trains an LLM to decode from a 16x-compressed document representation.
- Claims: PISCO achieves 16x document compression with 0–3% accuracy drop on RAG-QA and 5.7x inference speed-up; fine-tuning under 48h on a single A100.
- Pros: PISCO requires no labeled data or pretraining — distillation from open-ended questions only, cheap to adapt to new domains.
- Cons: Provence relies on a separately-trained DeBERTa ranker (extra pipeline component); PISCO requires fine-tuning the target LLM, so doesn't apply zero-shot to arbitrary models.

### 3. RIKEN Tensor Decomposition Memory-Efficient Incremental Learning (T3) — method papers / continual learning
- URL: https://icml.cc/virtual/2025/poster/44196
- Memory model: Tensor-decomposed exemplar compression for incremental learning
- What it does: Uses tensor decomposition to exploit low intrinsic dimensionality and pixel correlation of stored exemplar images, achieving high compression while preserving discriminative information for class-incremental learning. Compresses replay buffer used in catastrophic-forgetting prevention.
- Claims: ICML 2025; compression without proportional accuracy loss vs full-exemplar replay.
- Pros: Principled mathematical basis (tensor low-rank structure) rather than heuristic pruning; applies to any replay-based continual learning setup.
- Cons: Targets image classification exemplar buffers specifically; applicability to language model continual learning is indirect.

### 4. Mistral Agents API memory (T1) — Platform-provider memory
- URL: https://docs.mistral.ai/studio-api/agents/introduction
- Launch: https://mistral.ai/news/agents-api
- Memory model: Platform-managed stateful conversation memory
- What it does: Agents API provides persistent conversation state across turns and sessions; runtime maintains branching conversation trees. Memory is implicit in the stateful session model rather than a separate store.
- Claims: Vendor-reported seamless multi-step workflow support; agents can handle complex task sequences across multiple sessions.
- Pros: Fully managed — developers need no external state store for session continuity; branching conversations allow parallel reasoning paths.
- Cons: Closed infrastructure; no published architecture detail on memory storage/retrieval/eviction; no peer-reviewed evaluation of memory accuracy or long-term drift.

### 5. IBM Meta-Tokens (T2) — method papers / parametric & latent
- URL: https://arxiv.org/abs/2506.00307
- Memory model: LZ77-style lossless context compression via learned token placeholders
- What it does: Meta-tokens are learned vocabulary entries that act as placeholders for recurring token subsequences; the model is fine-tuned to understand compressed input where meta-tokens stand in for their corresponding subsequences without information loss. Mathematically lossless and reversible.
- Claims: 27% and 18% average sequence-length reduction on two evaluation tasks; 47% and 33% less encoding compute due to quadratic attention cost.
- Pros: True losslessness — no semantic degradation by construction; compression decision can be made at inference time with no model change.
- Cons: Compression ratio is modest compared to soft methods (16x for PISCO vs ~1.2–1.4x here); requires fine-tuning on the specific compression format.

### 6. NVIDIA Nemotron 3 (T1) — method papers / parametric & latent
- URL: https://arxiv.org/abs/2512.20856
- Product: https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/
- HF: https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8
- Memory model: Hybrid constant-state Mamba + sparse KV-cache with 1M-token context
- What it does: Interleaves sparse MoE layers with Mamba-2 layers; Mamba layers maintain a fixed-size recurrent state (constant memory during generation) rather than a growing KV cache. Attention layers use GQA with only 2 KV heads. Two parallel memory systems: explicit small KV cache + implicit compressed Mamba state.
- Claims: Nemotron 3 Nano (31.6B total, 3.2B active) supports 1M-token context; hybrid architecture sustains high throughput at long contexts; multi-environment RL post-training enables agentic reasoning.
- Pros: Constant-memory Mamba state eliminates KV-cache explosion for the majority of layers, enabling genuinely long-context inference without proportional memory growth.
- Cons: Mamba state is a lossy compressed summary — information not captured is lost; memory-relevant properties not benchmarked against dedicated memory-augmented LLMs on QA/agent tasks.

### 7. Anthropic Circuit Tracing (T2) — method papers / parametric & latent
- Methods: https://transformer-circuits.pub/2025/attribution-graphs/methods.html
- Blog: https://www.anthropic.com/research/tracing-thoughts-language-model
- Open source: https://www.anthropic.com/research/open-source-circuit-tracing
- Memory model: Mechanistic interpretability of parametric knowledge storage via attribution graphs
- What it does: Replaces MLP layers with sparse cross-layer transcoders to produce "replacement models" where activations correspond to interpretable features; traces attribution graphs showing causal feature → output influence. Includes case studies on factual recall.
- Claims: Successfully traced computational circuits for factual recall, planning, and multi-step reasoning in Claude 3.5 Haiku; open-source library released.
- Pros: Only published tool that makes parametric (weight-level) memory storage mechanistically interpretable rather than behaviorally probed; attribution graphs are auditable per-prompt.
- Cons: Not a memory system — it studies memory; findings are descriptive, not prescriptive; scalability to full production Claude models is limited.

### 8. MemoryLLM (original) (T2) — method papers / parametric & latent
- URL: https://arxiv.org/abs/2402.04624
- Memory model: Fixed-size in-weights memory pool with online self-update
- What it does: Augments a transformer with a fixed-size 1B-parameter memory pool distributed across all layers; new knowledge is injected by updating the pool parameters during inference, not via context extension. Distinct from M+ (already in landscape) which extends with scalable long-term storage.
- Claims: Effective on model editing benchmarks and long-context tests; stable after ~1M sequential updates.
- Pros: No external retrieval store needed — memory is entirely parametric and intrinsic to the model.
- Cons: Fixed pool capacity creates a hard ceiling on storable knowledge; no dynamic growth path without M+ extension; pool update is sequential.

### 9. SELF-PARAM (T2) — method papers / parametric & latent
- URL: https://arxiv.org/abs/2410.00487
- Memory model: KL-distillation experience internalization into existing parameters
- What it does: Encodes new experiences directly into the LLM's existing parameters by minimizing KL divergence between a teacher model (with context access) and a student model (without). Generates diverse QA pairs from new knowledge as the distillation signal.
- Claims: Outperforms existing continual learning and memory injection methods on QA and conversational recommendation, even vs methods with nonzero storage cost.
- Pros: Zero-parameter overhead — no new layers, stores, or pools added; computationally accessible (fine-tuning only).
- Cons: Internalization is a form of fine-tuning and risks catastrophic forgetting; updating is slow vs fast in-context or retrieval-based methods.

### 10. ShadowKV (ByteDance, ICML 2025 Spotlight) (T2) — method papers / parametric & latent
- URL: https://arxiv.org/abs/2410.21465
- GitHub: https://github.com/bytedance/ShadowKV
- Memory model: Low-rank CPU-offloaded KV cache with sparse on-device reconstruction
- What it does: During prefill, value caches are offloaded to CPU; only low-rank pre-RoPE keys + compressed landmarks + outliers stay on GPU. During decoding, landmarks select chunk indices for key reconstruction and value fetching from CPU. Effectively unlimited context without GPU memory blowup.
- Claims: Up to 6x larger batch sizes and 3.04x throughput on A100 without accuracy loss; validated on RULER, LongBench, NIAH across Llama-3.1, GLM-4, Yi, Phi-3, Qwen2.
- Pros: Validated on six diverse model families with no accuracy degradation; ICML 2025 Spotlight; open-source.
- Cons: Requires CPU-GPU data transfer during decoding (PCIe-bandwidth-sensitive latency); low-rank key approximation may miss precise token-level distinctions in adversarial retrieval.

### 11. Tencent ima.copilot (T1) — Personal AI / PKM
- URL: https://ima.qq.com (Chinese) / https://www.hkmu.edu.hk/oetools/imacopilot/ (English guide)
- Coverage: https://phemex.com/news/article/tencent-ima-unveils-agent-mode-copilot-with-advanced-memory-system-77195
- Memory model: Four-module self-evolving personal memory (soul/user/memory/skills)
- What it does: Tencent's knowledge-management productivity AI, powered by Hunyuan. Copilot mode adds a four-module persistent memory architecture: Soul (persona), User (profile), Memory (long-term declarative), Agent (learned skills/task experience). Memory persists across devices and sessions.
- Claims: Tencent ima.copilot 2.0 (Oct 2025) introduces Task Mode with report and podcast generation; high-accuracy recall of prior context.
- Pros: Deeply integrated with Chinese ecosystem (WeChat, QQ, Tencent cloud); four-module decomposition cleanly separates persona, user model, episodic memory, procedural memory.
- Cons: Primarily Chinese-market product; Hunyuan model and memory infrastructure are closed; no peer-reviewed benchmark results; limited English documentation.
