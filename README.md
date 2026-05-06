# Memory Analysis Program

A landscape catalog of AI memory systems, frameworks, papers, products, and theoretical
proposals — built as the foundation for downstream comparative and trend analysis.

## What's in here

- **`landscape.html`** — the main artifact. ~510+ entries across 22+ sections /
  sub-groups, with tier badges (T1 battle-tested → T5 theoretical / informal),
  sortable by tier within each section, with section explainers and source links.
  Open in a browser.
- **`PLAN.md`** — current state, deferred work, and the data we need to pull in
  before doing real trend / adoption analysis.

## Sections currently in the landscape

Production / commercial:
- Dedicated memory layers
- Framework-embedded memory
- Platform-provider memory
- Coding-agent memory
- Browser-agent memory
- Personal AI / PKM / lifelogging memory
- Voice-first / wearable AI memory
- Vertical / domain-specific AI memory (sub-groups: scientific, healthcare, legal,
  customer-support / voice, gaming / NPC, robotics / autonomous-driving / embodied)

Research / academic:
- Research / specialised systems
- Recent method papers (sub-groups: factual / experiential / working memory /
  parametric & latent / world-model / continual learning / memory-augmented RL /
  cognitive-architecture-inspired)
- Retrieval-as-memory hybrids

Adjacent / infrastructure:
- File-backed / editor paradigms
- Claude Code memory mechanisms (incl. MCP servers)
- Knowledge-graph platforms
- Vector-database infrastructure
- Enterprise-search adjacencies
- Memory benchmarks & evaluation
- Memory observability & monitoring
- Memory governance, privacy & safety

Speculative:
- Theoretical / informal — ideas without a paper

## Why this exists

Three distinct uses, in priority order:

1. **Cross-system comparison** — given a problem, what tools / techniques exist?
2. **Adoption signal** — what's actually being used in production vs. just published?
3. **Trend signal** — what's growing, what's saturating, what's being abandoned?

The landscape catalog is the substrate for (1). Adoption and trend analysis are
downstream uses that need additional data we haven't gathered yet — see `PLAN.md`.

## Methodology / provenance

Every entry was sourced from one of:
- Curated lists (Agent-Memory-Paper-List, Awesome-GraphMemory)
- Survey papers (`arxiv.org/abs/2512.13564`, `arxiv.org/abs/2508.10824`)
- Benchmark leaderboards (LongMemEval, LoCoMo, ConvoMem)
- Vendor websites and academic venue pages
- Targeted research-agent sweeps (~25 agents over multiple sessions)

URLs verified at time of entry. Claims (the right-hand column for many rows) are
vendor-stated unless otherwise marked. Some 2026 arxiv IDs were independently
verified by a paper-verification pass.

## Status

The catalog is comprehensive enough for use as a reference. Honest confidence on
landscape coverage: ~88-92% as of 2026-05-06. The known gaps and the plan to close
them are in `PLAN.md`.
