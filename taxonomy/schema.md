# Memory-system taxonomy schema

Six axes capturing how a memory system is built and operates. Each row in
`landscape.html` gets one set of tags written to `taxonomy/tags.json`,
keyed by the system's display name.

Multi-value tags allowed where a system genuinely spans values (e.g.,
hybrid storage primitive). Use the most specific applicable tags only.

---

## Axis 1 — Storage primitive

Where memory physically lives.

- `vector` — vector index / embedding store (Pinecone, Weaviate, Qdrant)
- `graph` — knowledge graph, property or RDF (Neo4j, Zep, GraphRAG)
- `kv` — key-value store (Redis-like, Mem0 KV layer)
- `kv-cache` — transformer KV cache (ShadowKV, SnapKV, H2O, RazorAttention)
- `file` — filesystem / markdown / plain-text (CLAUDE.md, Anthropic Managed Agents)
- `parametric` — in model weights (MemoryLLM, M+, SELF-PARAM, EWC)
- `relational` — SQL / Postgres (pgvector, MongoDB Atlas)
- `column` — columnar / lakehouse (Snowflake Cortex, Databricks Vector, LanceDB)
- `cache` — prefill / token cache (CAG, infini-attention compressed memory)
- `proprietary` — closed-format vendor store (Apple Notes, Microsoft Recall)
- `hybrid` — explicitly mixes two or more above (Mem0 = vector+graph+kv;
  Memory³ = parametric+kv-cache+external)

## Axis 2 — Retrieval method

How memory is recalled when needed.

- `similarity` — vector cosine / dot-product similarity
- `graph-traversal` — graph queries, multi-hop, PageRank-style walks
- `exact-match` — keyword / ID / path lookup
- `attention` — transformer attention is the recall mechanism
- `cache-lookup` — KV-cache reuse / prefill cache reuse
- `parametric-recall` — model emits memory from weights, no external read
- `hybrid-rerank` — multiple retrievers + rerank step
- `extraction-pull` — LLM extracts on demand from raw store
- `injection` — file-as-context injection at session start (no retrieval)
- `agentic` — agent decides when, what, and how to retrieve

## Axis 3 — Persistence horizon

How long memory is designed to live.

- `ephemeral` — current turn / context window only
- `session` — within current session, lost after
- `cross-session` — persists across sessions for the same agent or user
- `long-term` — designed for multi-session, multi-month
- `lifelong` — designed for indefinite / years-scale persistence
- `parametric-permanent` — encoded in model weights (effectively permanent
  unless retrained)

## Axis 4 — Update mechanism

How memory contents change over time.

- `append-only` — write new, never modify or delete (Memvid, MemMachine paper)
- `extraction` — LLM extracts facts from raw input and writes structured form
  (Mem0, Zep)
- `overwrite` — replace entries on update (most file-backed)
- `parametric-edit` — model weights updated (knowledge editing, ROME, AlphaEdit)
- `consolidation` — explicit merge / compress phase (Auto Dream, Letta tier promotion)
- `evict-oldest` — append + LRU or attention-importance eviction (KV-cache pruning,
  ShadowKV)
- `read-only` — never updated after construction (REALM-style pretrained corpora,
  benchmark datasets)
- `agent-controlled` — agent self-decides when and what to write/read
  (Memory as Action, Self-RAG)

## Axis 5 — Memory unit

What a single "thing" in memory is.

- `fact` — discrete claim / triple / atomic fact
- `document` — full document or page
- `episode` — conversation turn / interaction event / trajectory step
- `skill` — procedure / tool-use pattern / plan template
- `profile` — user model / persona / preferences
- `scene-graph` — spatial scene representation (robotics, embodied)
- `kv-token` — transformer KV-cache token entry
- `file` — file content or file path (file-as-memory pattern)
- `weight` — parameter delta / LoRA / adapter
- `trajectory` — full agent action sequence
- `chunk` — passage / paragraph (RAG-style)
- `summary` — condensed / abstracted form

## Axis 6 — Governance posture

How inspectable, auditable, or controllable the memory is.

- `opaque` — closed system, no inspect or edit (most consumer chat products)
- `inspectable` — can read but not edit programmatically
- `editable` — user can read and edit
- `auditable` — full provenance / audit log per write
- `deterministic` — explicit rules, predictable behavior, no LLM in the
  governance path
- `user-controllable` — explicit user consent / opt-out / data residency
