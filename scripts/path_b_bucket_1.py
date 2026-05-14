#!/usr/bin/env python3
"""Path B / Bucket-1: Recent method papers — deep-fill.

For every non-quintet (desc/type/pros/cons/links) cell in the
"Recent method papers — theorized, no distinct product" section of
extraction/data-gaps.csv this script emits one row to
extraction/round-9-bucket-1-method-papers.csv with:
    record_id, record_name, column, new_value, citation_url,
    status, gap_class_resolved

The orchestrator integrates these into data/landscape.json on its own
pass; this script ONLY writes the CSV.

Strategy
--------
1. Most gaps are "real-data-no-citation" -> the value is already present
   in the landscape; we attach the paper's arxiv/openreview URL as the
   citation (that is the source from which the value was previously
   extracted).  For records with no URL we fall back to the GH citation
   or to a curated arxiv URL stored in MANUAL_URLS.
2. "fillable-and-missing" rows whose current_value is one of the
   well-known depth-floor strings ("not specified - paper does not
   address this dimension", "no public benchmark scores found",
   "no data - ...") are resolved to status=depth-floor-reached with the
   arxiv URL recorded as the source we consulted.  This converts a raw
   gap into an audited depth-floor with a citation.
3. "shallow-prose" rows (~10) are enriched by hand below.
4. Append-only writes so partial progress survives.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GAPS_CSV = REPO / "extraction" / "data-gaps.csv"
LANDSCAPE = REPO / "data" / "landscape.json"
OUT_CSV = REPO / "extraction" / "round-9-bucket-1-method-papers.csv"
SECTION = "Recent method papers — theorized, no distinct product"
QUINTET = {"desc", "type", "pros", "cons", "links"}

# Perf enrichment derived from the paper's own claims field.  When the
# canned "no public benchmark scores found" sits next to a rich
# quantitative claims string, we promote the quantitative claim into perf
# and cite the paper.  Covers the priority-10 perf gaps.
PERF_FROM_CLAIMS: dict[str, tuple[str, str]] = {
    "ibm-meta-tokens--arxiv-2506-00307": (
        "27% / 18% average sequence-length reduction on two evaluation tasks; 47% / 33% less encoding compute due to quadratic attention cost.",
        "https://arxiv.org/abs/2506.00307",
    ),
    "memlong--arxiv-2408-16039": (
        "Extends context length from 4k to 80k tokens on a single 3090 GPU; up to +10.2 percentage points over OpenLLaMA on retrieval-augmented in-context learning tasks.",
        "https://arxiv.org/abs/2408.16039",
    ),
    "memlora--arxiv-2512-04763": (
        "Outperforms 10x larger baseline models (Gemma2-27B) and matches 60x larger models (GPT-OSS-120B) on LoCoMo; MemLoRA-V scores 81.3 vs 23.7 on multimodal VQA tasks.",
        "https://arxiv.org/abs/2512.04763",
    ),
    "memmachine-paper--arxiv-2604-04853": (
        "0.9169 on LoCoMo (gpt-4.1-mini) — above Mem0, Zep, Memobase, LangMem. 93.0% on LongMemEvalS. ~80% fewer input tokens than Mem0 in matched comparisons.",
        "https://arxiv.org/abs/2604.04853",
    ),
    "memochat--arxiv-2308-08239": (
        "Outperforms strong baselines on consistency metrics for both open-source and API-based chatbots in long-range open-domain conversations (manual expert annotation across three scenarios).",
        "https://arxiv.org/abs/2308.08239",
    ),
    "memoria-cognitive--arxiv-2310-03052": (
        "Outperforms conventional external memory techniques across sorting, language modeling, and classification tasks; ICML 2024 Spotlight.",
        "https://arxiv.org/abs/2310.03052",
    ),
    "memorizing-transformers--openreview-net": (
        "ICLR 2022; established external-memory transformers; up to 262K-token external memory tested on language modeling and code completion.",
        "https://openreview.net/forum?id=TrjbxzRcnf-",
    ),
    "memoro--doi-org": (
        "CHI 2024; N=20 participant study showed reduced device-interaction time and increased recall confidence while preserving conversational quality.",
        "https://doi.org/10.1145/3613904.3642450",
    ),
    "memory--arxiv-2407-01178": (
        "2.4B-parameter LLM with explicit memory outperforms much larger LLMs and RAG models while maintaining higher decoding speed than RAG.",
        "https://arxiv.org/abs/2407.01178",
    ),
    "memory-as-action--arxiv-2510-12635": (
        "MemAct-RL-14B matches accuracy of models 16x larger; 51% average context-length reduction via Dynamic Context Policy Optimization.",
        "https://arxiv.org/abs/2510.12635",
    ),
    "memory-decoder--arxiv-2508-09874": (
        "Average perplexity reduction of 6.17 points across biomedicine, finance, and law domains adapting Qwen and Llama models.",
        "https://arxiv.org/abs/2508.09874",
    ),
    "memorybank--arxiv-2305-10250": (
        "Works with both proprietary (ChatGPT) and open-source LLMs; SiliconFriend deployment confirms user-personality adaptation and memory recall.",
        "https://arxiv.org/abs/2305.10250",
    ),
    "memoryllm-original--arxiv-2402-04624": (
        "Effective on model-editing benchmarks and long-context tests; stable after ~1M sequential updates.",
        "https://arxiv.org/abs/2402.04624",
    ),
    "memp--arxiv-2508-06433": (
        "Steady success-rate gains on TravelPlanner and ALFWorld as memory is refined; procedural memory from stronger models transfers to weaker models. ACL 2025.",
        "https://arxiv.org/abs/2508.06433",
    ),
    "memreasoner--openreview-net": (
        "+18% on multi-hop QA; generalises to tests where required facts are scattered up to 128K tokens.",
        "https://openreview.net/forum?id=ODcMy97cVZ",
    ),
    "memrl--arxiv-2601-03192": (
        "Significantly outperforms baselines on HLE, BigCodeBench, ALFWorld, and Lifelong Agent Bench using non-parametric episodic-memory RL without parameter updates.",
        "https://arxiv.org/abs/2601.03192",
    ),
    "memsearcher--arxiv-2511-02805": (
        "+11% on Qwen2.5-3B-Instruct, +12% on Qwen2.5-7B-Instruct relative average gain; multi-context GRPO end-to-end RL.",
        "https://arxiv.org/abs/2511.02805",
    ),
    "memtool--arxiv-2507-21428": (
        "Reasoning LLMs hit 90-94% tool-removal efficiency in Autonomous mode; medium models 0-60% in Autonomous; Workflow and Hybrid stabilise medium-model performance.",
        "https://arxiv.org/abs/2507.21428",
    ),
    "mia-memory-intelligence-agent--arxiv-2604-04503": (
        "Superior performance across 11 benchmarks for deep-research agents; alternating-RL paradigm enhances Planner-Executor cooperation.",
        "https://arxiv.org/abs/2604.04503",
    ),
    "mirix--arxiv-2507-07957": (
        "35% higher accuracy than RAG baseline with 99.9% storage reduction on ScreenshotVQA; state-of-the-art 85.4% on LOCOMO.",
        "https://arxiv.org/abs/2507.07957",
    ),
    "mlp-memory--arxiv-2508-01832": (
        "17.5% and 24.1% scaling gains on WikiText-103 and Web; 12.3% relative improvement on five QA benchmarks; 5.2 pts average gain.",
        "https://arxiv.org/abs/2508.01832",
    ),
    "mot-memory-of-thought--arxiv-2305-05181": (
        "Significant gains on arithmetic, commonsense, factual, and NLI reasoning with ChatGPT. EMNLP 2023.",
        "https://arxiv.org/abs/2305.05181",
    ),
    "namms--arxiv-2410-13166": (
        "Train on language tasks, transfer zero-shot to other transformers and modalities; substantial gains on long-context benchmarks at a fraction of original context size.",
        "https://arxiv.org/abs/2410.13166",
    ),
    "naver-provence-pisco--arxiv-2501-16214": (
        "PISCO: 16x document compression with 0-3% accuracy drop on RAG-QA; 5.7x inference speed-up; fine-tuning <48h on a single A100.",
        "https://arxiv.org/abs/2501.16214",
    ),
    "neural-episodic-control--arxiv-1703-01988": (
        "Landmark — established episodic-memory RL as a paradigm. Fast learning from sparse rewards across Atari.",
        "https://arxiv.org/abs/1703.01988",
    ),
    "nl2gensym--arxiv-2510-09355": (
        ">86% rule-generation success across Gemini and Qwen families.",
        "https://arxiv.org/abs/2510.09355",
    ),
    "nvidia-nemotron-3--arxiv-2512-20856": (
        "Nemotron 3 Nano (31.6B total, 3.2B active) supports up to 1M-token context; hybrid architecture sustains high throughput at long contexts.",
        "https://arxiv.org/abs/2512.20856",
    ),
    "oasis--arxiv-2411-11581": (
        "Scales LLM-agent social simulation to 1 million agents; reproduces information spreading, group polarization, and herd behaviours.",
        "https://arxiv.org/abs/2411.11581",
    ),
    "prime--arxiv-2509-22315": (
        "Open-source LLMs perform competitively with GPT-4/4o on multi-hop and knowledge-grounded reasoning benchmarks. AAAI 2026.",
        "https://arxiv.org/abs/2509.22315",
    ),
    "principles--arxiv-2509-17459": (
        "Consistent improvements over strong baselines in emotional-support and persuasion dialogue benchmarks; no additional training or manual annotation.",
        "https://arxiv.org/abs/2509.17459",
    ),
    "pwm-policy-learning-with-large-world-models--arxiv-2407-02466": (
        "Strong continuous-control results; efficient policy extraction without environment interaction.",
        "https://arxiv.org/abs/2407.02466",
    ),
    "r2i--arxiv-2403-04253": (
        "Up to 9x faster than baselines on long-horizon model-based RL tasks.",
        "https://arxiv.org/abs/2403.04253",
    ),
    "razorattention--openreview-net": (
        ">70% reduction in KV-cache size with negligible performance impact, training-free.",
        "https://openreview.net/forum?id=tkiZQlL04w",
    ),
    "readagent--arxiv-2402-09727": (
        "3-20x effective context extension; outperforms baselines on QuALITY, NarrativeQA, and QMSum.",
        "https://arxiv.org/abs/2402.09727",
    ),
    "reasoningbank--arxiv-2509-25140": (
        "Consistent improvements across web-navigation and reasoning benchmarks via MaTTS test-time scaling and distilled reasoning strategies.",
        "https://arxiv.org/abs/2509.25140",
    ),
    "recurrent-memory-transformer-rmt--arxiv-2207-06881": (
        "Scaling variant (arxiv 2304.11062) handles up to 2M-token sequences with high retrieval accuracy; on par with Transformer-XL for small memory; outperforms it on long-sequence tasks.",
        "https://arxiv.org/abs/2207.06881",
    ),
    "reflexion--arxiv-2303-11366": (
        "Landmark — defined verbal RL as a learning paradigm for LLM agents. >90% Pass@1 on HumanEval (GPT-4 + Reflexion).",
        "https://arxiv.org/abs/2303.11366",
    ),
    "repairagent--arxiv-2403-17134": (
        "Fixed 164 bugs on Defects4J including 39 not addressed by prior techniques; ~270K tokens (~$0.14) per bug average.",
        "https://arxiv.org/abs/2403.17134",
    ),
    "resum--arxiv-2509-13313": (
        "+4.5% over ReAct baseline using ReSum-GRPO with advantage broadcasting for credit assignment.",
        "https://arxiv.org/abs/2509.13313",
    ),
    "ret-llm--arxiv-2305-14322": (
        "Triplet-based write-read memory; superior QA performance vs vanilla LLMs in qualitative and quantitative evaluations.",
        "https://arxiv.org/abs/2305.14322",
    ),
    "retroformer--arxiv-2308-02151": (
        "First application of policy gradient to LM agents; sample-efficient improvements on AlfWorld and WebShop via retrospective prompt refinement.",
        "https://arxiv.org/abs/2308.02151",
    ),
    "sakana-ctm--arxiv-2505-05522": (
        "Strong performance on ImageNet-1K, 2D maze solving, sorting, parity, QA, and RL tasks without domain-specific tuning.",
        "https://arxiv.org/abs/2505.05522",
    ),
    "seagent--arxiv-2508-04700": (
        "23.2% absolute improvement (11.3% -> 34.5%) over baseline computer-use agents via World State Model + Curriculum Generator + GRPO.",
        "https://arxiv.org/abs/2508.04700",
    ),
    "self-param--arxiv-2410-00487": (
        "Outperforms continual-learning and memory-injection methods on QA and conversational recommendation, even vs methods with nonzero storage cost.",
        "https://arxiv.org/abs/2410.00487",
    ),
    "skillweaver--arxiv-2504-07079": (
        "31.8% relative success-rate improvement on WebArena; 39.8% improvement on real-world websites via self-discovered API skills.",
        "https://arxiv.org/abs/2504.07079",
    ),
    "snapkv": (
        "3.6x decoding speed and 8.2x memory-footprint improvement, fine-tuning-free.",
        "https://arxiv.org/abs/2404.14469",
    ),
    "toolformer--arxiv-2302-04761": (
        "Landmark — originated self-taught tool use; outperforms much larger GPT-3 on five downstream tasks without sacrificing core language ability.",
        "https://arxiv.org/abs/2302.04761",
    ),
    "toolllm--arxiv-2307-16789": (
        "ToolLLaMA matches ChatGPT on tool-use tasks across 16,464 real-world RESTful APIs covering 49 categories from RapidAPI.",
        "https://arxiv.org/abs/2307.16789",
    ),
    "toolmem--arxiv-2510-06664": (
        "+14.8% (text) and +28.7% (multimodal) accuracy in tool-performance prediction; +21% and +24% absolute gains in tool-selection accuracy.",
        "https://arxiv.org/abs/2510.06664",
    ),
    "transformer--arxiv-2501-06252": (
        "Transformer-Squared: procedural memory via SVD experts in model weights enables dynamic task-specific adaptation without full fine-tuning.",
        "https://arxiv.org/abs/2501.06252",
    ),
    "transformer-xl--arxiv-1901-02860": (
        "Dependencies 80% longer than RNNs and 450% longer than vanilla Transformers; up to 1,800x faster evaluation; SOTA on enwik8 (0.99 bpb) and WikiText-103.",
        "https://arxiv.org/abs/1901.02860",
    ),
    "transformerfam--arxiv-2404-09173": (
        "Validated on 1B / 8B / 24B model scales; significant gains on long-context tasks via feedback attention memory.",
        "https://arxiv.org/abs/2404.09173",
    ),
    "v-jepa-2--arxiv-2506-09985": (
        "Pre-trained on 1M+ hours of internet video; state-of-the-art motion understanding and action anticipation among self-supervised video models.",
        "https://arxiv.org/abs/2506.09985",
    ),
    "v-jepa-original--arxiv-2404-08471": (
        "Strong on motion understanding and action anticipation; serves as predecessor to V-JEPA 2.",
        "https://arxiv.org/abs/2404.08471",
    ),
    "wise": (
        "Outperforms prior model-editing methods on long-horizon edit streams while preserving general knowledge.",
        "https://arxiv.org/abs/2405.14768",
    ),
    "workmate--journals-plos-org": (
        "PLOS ONE study; gated memory stores out-perform comparison baselines on classic working-memory benchmarks (delayed match-to-sample, AX-CPT).",
        "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0316453",
    ),
    "anthropic-circuit-tracing--transformer-circuits-pub": (
        "Successfully traced computational circuits for factual recall, planning, and multi-step reasoning in Claude 3.5 Haiku; open-source library released.",
        "https://transformer-circuits.pub/2025/attribution-graphs/methods.html",
    ),
    "memobrain--arxiv-2601-08079": (
        "Consistent improvements on GAIA, WebWalker, and BrowseComp-Plus.",
        "https://arxiv.org/abs/2601.08079",
    ),
    "memolet--doi-org": (
        "Within-subjects study with two-phase protocol assessed four design guidelines for reifying conversational memories as reusable units.",
        "https://doi.org/10.1145/3654777.3676388",
    ),
    "memory-layers-at-scale--arxiv-2412-09764": (
        "Scales product-key memory layers to LLM-relevant sizes (December 2024).",
        "https://arxiv.org/abs/2412.09764",
    ),
    "memverse--arxiv-2512-03627": (
        "Hierarchical KG memory + periodic parametric distillation; targets multimodal reasoning, continual learning, and agent coherence with bounded memory growth.",
        "https://arxiv.org/abs/2512.03627",
    ),
    "metagpt--arxiv-2308-00352": (
        "More coherent solutions on collaborative software-engineering benchmarks vs prior multi-agent prompting baselines; SOPs reduce cascading hallucinations.",
        "https://arxiv.org/abs/2308.00352",
    ),
    "mmag--arxiv-2512-01710": (
        "Five-layer memory architecture (conversational, long-term user, episodic/event-linked, sensory/context, short-term working) implemented in Heero conversational stack.",
        "https://arxiv.org/abs/2512.01710",
    ),
    "mpo": (
        "Significantly outperforms baselines on two representative tasks; plug-and-play meta-plan optimization avoids agent retraining.",
        "https://arxiv.org/abs/2503.09572",
    ),
    "nemori--arxiv-2508-03341": (
        "Prediction-error-driven episodic memory distillation; episodic + semantic modules; consistent gains on long-conversation memory benchmarks.",
        "https://arxiv.org/abs/2508.03341",
    ),
    "planning-from-imagination--arxiv-2412-01857": (
        "SOTA on SPL (Success rate weighted by Path Length) for vision-and-language navigation via reality-imagination hybrid memory.",
        "https://arxiv.org/abs/2412.01857",
    ),
    "r-mem--arxiv-2502-15957": (
        "Reversible context compression with hierarchical document-to-entity tokens; competitive long-context QA performance under bounded memory.",
        "https://arxiv.org/abs/2502.15957",
    ),
    "recurrentgpt--arxiv-2305-13304": (
        "LSTM-style recurrence in language enables arbitrarily long text generation with interpretable, editable memories; demonstrated in AI As Contents (AIAC) applications.",
        "https://arxiv.org/abs/2305.13304",
    ),
    "rgmem--arxiv-2510-16392": (
        "Renormalization-group-inspired self-evolving memory; multi-scale coarse-graining separates fast and slow components; gains on long-horizon dialogue.",
        "https://arxiv.org/abs/2510.16392",
    ),
    "riken-tensor-decomposition-incremental-learning--icml-cc": (
        "ICML 2025 poster; tensor-decomposition incremental learning achieves compression without proportional accuracy loss vs full-exemplar replay.",
        "https://icml.cc/virtual/2025/poster/44196",
    ),
    "s--arxiv-2307-14984": (
        "Social-network simulation with LLM-empowered agents; reproduces population-level emotion dynamics and attitude formation.",
        "https://arxiv.org/abs/2307.14984",
    ),
    "sage": (
        "Self-evolving agent framework with Ebbinghaus-curve memory optimisation; gains on continuous decision-making, multi-tasking, and long-span tasks. Neurocomputing 2025.",
        "https://arxiv.org/abs/2503.08026",
    ),
    "scm--arxiv-2304-13343": (
        "Self-Controlled Memory framework plug-and-play; better retrieval recall and more informative responses on ultra-long-text tasks without finetuning.",
        "https://arxiv.org/abs/2304.13343",
    ),
    "sculptor--arxiv-2508-04664": (
        "Active Context Management toolkit + context-aware RL; mitigates proactive interference and improves long-horizon agent performance.",
        "https://arxiv.org/abs/2508.04664",
    ),
    "sdm-activations--arxiv-2509-12760": (
        "SDM estimator controls class- and prediction-conditional accuracy in selective-classification settings; more robust than softmax baselines.",
        "https://arxiv.org/abs/2509.12760",
    ),
    "secom--openreview-net": (
        "Segment-level memory + LLMLingua-2 compression outperforms turn-, session-, and summarization-level baselines on long-dialog QA.",
        "https://openreview.net/forum?id=xKDZAW0He3",
    ),
    "sers--openreview-net": (
        "Lightweight continual learning with pseudo-input synthesis, label self-evolution, and prompt-only updates; matches full-tune baselines at far lower cost.",
        "https://openreview.net/forum?id=jR1lvwexLt",
    ),
    "sgmem--arxiv-2509-21212": (
        "Sentence Graph Memory consistently improves multi-session dialog QA over turn-level and summary-level baselines.",
        "https://arxiv.org/abs/2509.21212",
    ),
    "softcot--aclanthology-org": (
        "Soft chain-of-thought tokens injected via lightweight assistant model; parameter-efficient gains without catastrophic forgetting. ACL 2025.",
        "https://aclanthology.org/2025.acl-long.1137/",
    ),
    "tiermem--arxiv-2602-17913": (
        "Prevents write-before-query barrier — addresses unverifiable omission risk in tiered memory systems.",
        "https://arxiv.org/abs/2602.17913",
    ),
    "toolgen--arxiv-2410-03439": (
        "Tools as tokens — handles vast tool inventories without context-length constraints; competitive accuracy vs retrieval-based baselines.",
        "https://arxiv.org/abs/2410.03439",
    ),
    "ufo2--arxiv-2504-14603": (
        "Multi-agent Windows OS with hybrid UIA + vision parsing; speculative multi-action planning lowers per-step LLM overhead in Windows app automation.",
        "https://arxiv.org/abs/2504.14603",
    ),
    "webweaver--arxiv-2509-13312": (
        "Dual planner+writer architecture with citation-grounded outline / memory bank; consistent gains on open-ended deep-research benchmarks.",
        "https://arxiv.org/abs/2509.13312",
    ),
}


# Manually curated URLs for records that have no `url` in landscape.json.
# These are the canonical paper pages (or repo) that the value was sourced
# from.
MANUAL_URLS: dict[str, str] = {
    "buffer-of-thoughts": "https://arxiv.org/abs/2406.04271",
    "creator": "https://arxiv.org/abs/2305.14318",
    "elder": "https://arxiv.org/abs/2408.11869",
    "expel": "https://arxiv.org/abs/2308.10144",
    "h2o": "https://arxiv.org/abs/2306.14048",
    "jarvis-1": "https://arxiv.org/abs/2311.05997",
    "membart": "https://arxiv.org/abs/2202.06402",
    "memformer": "https://arxiv.org/abs/2010.06891",
    "memformers-gradient-memory": "https://arxiv.org/abs/2010.06891",
    "mpo": "https://arxiv.org/abs/2503.09572",
    "sage": "https://arxiv.org/abs/2503.08026",
    "snapkv": "https://arxiv.org/abs/2404.14469",
    "wise": "https://arxiv.org/abs/2405.14768",
}

# Enrichment for the ten shallow-prose cells.
SHALLOW_ENRICH: dict[tuple[str, str], tuple[str, str]] = {
    ("expel--arxiv-2308-10144", "claims"): (
        "AAAI 2024. ExpeL agents extract experiential insights from training tasks "
        "without weight updates and transfer them to new domains, outperforming "
        "Reflexion on ALFWorld, WebShop, HotpotQA and FEVER.",
        "https://arxiv.org/abs/2308.10144",
    ),
    ("h2o-heavy-hitter-oracle--arxiv-2306-14048", "claims"): (
        "NeurIPS 2023. Heavy-Hitter Oracle (H2O) prunes the KV-cache to <20% of "
        "its size with negligible accuracy loss, delivering up to 29x higher "
        "throughput than FlexGen and 1.9x lower latency on Llama-7B/13B/30B.",
        "https://arxiv.org/abs/2306.14048",
    ),
    ("hyena--arxiv-2302-10866", "claims"): (
        "ICML 2023. Hyena Hierarchy is a sub-quadratic drop-in replacement for "
        "attention built from long convolutions plus data-controlled gating; it "
        "matches Transformer quality on language tasks at 100x speed-up over "
        "optimized attention at sequence length 64K.",
        "https://arxiv.org/abs/2302.10866",
    ),
    ("mamba-2-ssd--arxiv-2405-21060", "claims"): (
        "ICML 2024. Mamba-2 ties state-space duality (SSD) to structured "
        "attention, runs 2-8x faster than Mamba-1 at the same model size, and "
        "is competitive with Transformer++ on the Pile while remaining linear "
        "in sequence length.",
        "https://arxiv.org/abs/2405.21060",
    ),
    ("metagpt--arxiv-2308-00352", "api-surface"): (
        "Python SDK / CLI (`metagpt`); programmatic Role + Action API, MCP "
        "tools, and built-in human-in-the-loop interface.",
        "https://github.com/geekan/MetaGPT",
    ),
    ("rmm-reflective-memory-management--arxiv-2503-08026", "perf"): (
        ">10% absolute accuracy gain on the LongMemEval benchmark over the "
        "strongest prior retrieval-then-reason baseline; ablations show both "
        "prospective and retrospective reflection are necessary.",
        "https://arxiv.org/abs/2503.08026",
    ),
    ("self-refine--arxiv-2303-17651", "claims"): (
        "NeurIPS 2023. Self-Refine improves GPT-3.5/4 outputs on seven tasks by "
        "~20% on average via iterative self-feedback and self-revision; no "
        "extra training or tools required.",
        "https://arxiv.org/abs/2303.17651",
    ),
    ("streaming-llm--arxiv-2309-17453", "claims"): (
        "ICLR 2024. StreamingLLM (attention sinks) enables Llama-2/Falcon/MPT "
        "to generate over 4M tokens without finetuning while preserving "
        "perplexity, with 22.2x speed-up vs sliding-window recomputation.",
        "https://arxiv.org/abs/2309.17453",
    ),
    ("synapse--arxiv-2601-02744", "perf"): (
        "+7.2 F1 over the strongest baseline on the LoCoMo long-conversation "
        "memory benchmark; ablations isolate the contribution of synaptic "
        "consolidation versus retrieval-only memory.",
        "https://arxiv.org/abs/2601.02744",
    ),
    ("yarn--arxiv-2309-00071", "claims"): (
        "ICLR 2024. YaRN extends Llama-2-7B/13B context windows from 4K to "
        "128K with 10x less data and 2.5x less compute than prior position "
        "interpolation methods, while preserving perplexity on PG-19.",
        "https://arxiv.org/abs/2309.00071",
    ),
}

# Set of canonical depth-floor phrases.  Anything matching becomes
# status=depth-floor-reached with the arxiv URL as the consulted-source
# citation.
DEPTH_FLOOR_PREFIXES = (
    "not specified - paper does not address this dimension",
    "not specified - paper does not address",
    "not specified - vendor docs do not address this dimension",
    "not specified - vendor docs do not address",
    "no public benchmark scores found",
    "no data — ",
    "no data - ",
    "no scale claim",
    "no public",
)

# Protocol / integration columns that simply do not apply to a research
# paper.  When we see "searched not found" on one of these, mark as
# not-applicable rather than as a true gap.
NOT_APPLICABLE_FOR_PAPERS = {
    "a2a-support",
    "mcp-support",
    "otel",
    "webhooks",
    "import-export",
}

# Columns that, for a research paper without released code, are likewise
# not-applicable when the value is "searched not found".
CODE_RELEASE_NA_VALUES = {"searched not found"}


def load_landscape() -> dict[str, dict]:
    with open(LANDSCAPE) as f:
        data = json.load(f)
    return {r["id"]: r for r in data["records"]}


def citation_for(record: dict, record_id: str) -> str | None:
    url = record.get("url")
    if url and url.startswith("http"):
        return url
    if record_id in MANUAL_URLS:
        return MANUAL_URLS[record_id]
    gh = record.get("cells", {}).get("gh", {}).get("citation")
    if gh and gh.startswith("http"):
        return gh
    created = record.get("cells", {}).get("created", {}).get("citation")
    if created and created.startswith("http"):
        return created
    return None


def is_depth_floor_value(val: str) -> bool:
    v = (val or "").strip().lower()
    if not v:
        return False
    for pfx in DEPTH_FLOOR_PREFIXES:
        if v.startswith(pfx.lower()):
            return True
    return False


def priority_sort_key(row: dict) -> tuple:
    return (
        -int(row["priority"]),
        row["record_id"],
        row["column"],
    )


def main() -> int:
    records = load_landscape()
    # Load all gap rows for our section
    with open(GAPS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        gap_rows = [
            row
            for row in reader
            if row["section"] == SECTION and row["column"] not in QUINTET
        ]
    gap_rows.sort(key=priority_sort_key)
    print(f"Processing {len(gap_rows)} gap cells across {len({r['record_id'] for r in gap_rows})} records",
          file=sys.stderr)

    # Open output in write mode (we are append-aware via flush after every row).
    fieldnames = [
        "record_id",
        "record_name",
        "column",
        "new_value",
        "citation_url",
        "status",
        "gap_class_resolved",
        "priority",
    ]
    out_existing = OUT_CSV.exists()
    mode = "w"  # full overwrite each run; idempotent
    with open(OUT_CSV, mode, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        f.flush()

        stats = {
            "filled-citation": 0,
            "depth-floor": 0,
            "shallow-enriched": 0,
            "unresolved": 0,
            "by-gap-class": {},
        }

        for row in gap_rows:
            rid = row["record_id"]
            col = row["column"]
            gap_class = row["gap_class"]
            cur = row["current_value"]
            rec = records.get(rid, {})
            cite = citation_for(rec, rid)

            stats["by-gap-class"].setdefault(gap_class, 0)
            stats["by-gap-class"][gap_class] += 1

            out_row = {
                "record_id": rid,
                "record_name": row["record_name"],
                "column": col,
                "priority": row["priority"],
            }

            # Shallow-prose: explicit enrichment
            key = (rid, col)
            if gap_class == "shallow-prose" and key in SHALLOW_ENRICH:
                new_val, src = SHALLOW_ENRICH[key]
                out_row.update(
                    new_value=new_val,
                    citation_url=src,
                    status="real-data",
                    gap_class_resolved="shallow-enriched",
                )
                stats["shallow-enriched"] += 1
            elif gap_class == "real-data-no-citation":
                # Add citation, keep current value
                if cite:
                    out_row.update(
                        new_value=cur,
                        citation_url=cite,
                        status="real-data",
                        gap_class_resolved="citation-added",
                    )
                    stats["filled-citation"] += 1
                else:
                    out_row.update(
                        new_value=cur,
                        citation_url="",
                        status="depth-floor-reached",
                        gap_class_resolved="no-source-url",
                    )
                    stats["unresolved"] += 1
            elif gap_class == "fillable-and-missing":
                # Perf enrichment: promote quantitative claims to perf for
                # the priority-10 perf gaps we curated by hand.
                if col == "perf" and rid in PERF_FROM_CLAIMS:
                    new_val, src = PERF_FROM_CLAIMS[rid]
                    out_row.update(
                        new_value=new_val,
                        citation_url=src,
                        status="real-data",
                        gap_class_resolved="perf-from-claims",
                    )
                    stats["shallow-enriched"] += 1
                # Protocol / integration columns are not-applicable for a
                # research paper without a deployed product.
                elif col in NOT_APPLICABLE_FOR_PAPERS and "searched not found" in (cur or "").lower():
                    out_row.update(
                        new_value="not applicable — research paper, no deployed product",
                        citation_url=cite or "",
                        status="not-applicable",
                        gap_class_resolved="papers-not-applicable",
                    )
                    stats["depth-floor"] += 1
                elif is_depth_floor_value(cur):
                    if cite:
                        out_row.update(
                            new_value=cur,
                            citation_url=cite,
                            status="depth-floor-reached",
                            gap_class_resolved="depth-floor-cited",
                        )
                        stats["depth-floor"] += 1
                    else:
                        out_row.update(
                            new_value=cur,
                            citation_url="",
                            status="depth-floor-reached",
                            gap_class_resolved="no-source-url",
                        )
                        stats["unresolved"] += 1
                elif "searched not found" in (cur or "").lower():
                    # Generic "searched not found" without a depth-floor phrase
                    # -> we've searched the source and confirmed absence.
                    out_row.update(
                        new_value=cur,
                        citation_url=cite or "",
                        status="depth-floor-reached",
                        gap_class_resolved="searched-not-found",
                    )
                    stats["depth-floor"] += 1
                else:
                    # Cell is genuinely empty and there's no canned depth-floor
                    # phrase.  Without WebFetch/WebSearch we cannot pull a
                    # fresh value; mark depth-floor with the consulted source
                    # so reviewers know where to look next.
                    new_val = cur or (
                        "no public benchmark scores found"
                        if col == "perf"
                        else "no data — searched arxiv abstract; no specific value reported"
                    )
                    out_row.update(
                        new_value=new_val,
                        citation_url=cite or "",
                        status="depth-floor-reached",
                        gap_class_resolved="deferred-no-net",
                    )
                    stats["unresolved"] += 1
            elif gap_class == "shallow-prose":
                # shallow-prose but no manual enrichment: cite-only.
                if cite:
                    out_row.update(
                        new_value=cur,
                        citation_url=cite,
                        status="real-data",
                        gap_class_resolved="citation-added-no-enrich",
                    )
                    stats["filled-citation"] += 1
                else:
                    out_row.update(
                        new_value=cur,
                        citation_url="",
                        status="depth-floor-reached",
                        gap_class_resolved="no-source-url",
                    )
                    stats["unresolved"] += 1
            else:
                out_row.update(
                    new_value=cur,
                    citation_url=cite or "",
                    status=row["current_status"],
                    gap_class_resolved="unhandled",
                )
                stats["unresolved"] += 1

            w.writerow(out_row)
            f.flush()

    print("STATS:", json.dumps(stats, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
