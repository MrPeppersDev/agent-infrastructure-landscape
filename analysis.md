# AI Memory Systems — Analysis (table-grounded)

This is the analytical layer over `landscape.json` (and its rendered
`landscape.html`). **Every numeric claim in this document is verifiable
in the catalog** — find the row, look at the cited column, follow the
`↗` source link. Findings new to the v2 refresh (2026-05) are marked
**✶ v2**.

## ✶ v2 Executive summary

Five things a reader should take away before scrolling further:

1. **The catalog is terminal.** 523 records × 67 columns; 41.6% of cells
   are `real-data`, 43.6% are justified `not-applicable`. Only ~15% of
   cells remain unfilled, all in deliberately depth-floored areas
   (private-company financials, pre-S2 papers, etc.).
2. **Mem0 still owns the integration layer.** Inbound integrations
   (`integrates-with` + `built-on` + `extends`, from
   `landscape.edges.json`) = **12** for Mem0; #2 is LangGraph
   Persistence at **5**, Pinecone / Qdrant / pgvector at **3–4** each.
   That's a network-effect moat at the substrate layer, not a marketing
   claim.
3. **The horizontal-substrate vs vertical-product valuation gap has
   held.** Coding agents and personal-AI now sit at $6.6B–$20B; the
   top dedicated-memory-layer (Mem0) is still at $150M. **66×
   minimum, 136× to Perplexity** — same as v1, with more data behind
   it (220 funding cells now vs 32 in v1).
4. **Lineage detection confirms 3 of the 4 originally-claimed
   families** as descent chains (RSSM world-model, Graph-RAG hierarchy,
   KV-cache eviction). The 4th — *files-as-memory* — does not have
   descent edges between members and is now modelled in `lineages.ts`
   as a **pattern**-kind lineage (parallel implementations of one
   idea), surfaced as a 3rd curated seed but rendered with dashed
   connectors rather than arrows. Auto-discovery surfaces **6 more**
   descent lineages (Mem0 ecosystem, JEPA, MCP-knowledge-graph,
   Hindsight, continual-learning / EWC, ReMEmbR-spatial) plus one
   giant influential-cite component (96 nodes) representing the
   research-paper backbone.
5. **Governance disclosure at the academic tier is no longer null.**
   v1's headline finding ("T3/T4 papers don't disclose governance,
   nulls 89% / 97.7%") has been overtaken by ingestion. T3 now =
   **72.7%** disclosed, T4 = **70.7%** disclosed. The old finding
   was a coverage gap in the tagging pass, not a structural property
   of academic publishing — **the *quality* of disclosure remains
   shallow** (see §11.3).

---

## Column references used

- **(Tax)** — Storage / Retrieval / Persistence / Update / Unit / Governance / Conflict taxonomy axes
- **(GitHub)** — Stars + 30-day velocity + language (cell `gh`)
- **(Created)** — Repo / org founding date (cell `created`)
- **(Funding)** — Total raised + latest valuation + latest round (cell `funding`)
- **(Customers)** — ARR + employees + named logos (cell `customers`)
- **(Performance)** — Benchmark scores; ⚠ marks disputed claims (cell `perf`)
- **(Mindshare)** — Inbound integrations + package downloads + jobs + press (cell `mindshare`)
- **(Citations)** — Total + per-year via Semantic Scholar (cell `citations`)
- **(Edges)** — `landscape.edges.json`, 247 edges (189 cites, 31 integrates-with, 21 built-on, 3 extends, 2 forks, 1 same-team-as)

### Cell population — what's "—" means: dash means "no public data," not "the system has zero."

✶ v2 coverage by column (much higher than v1 because ingestion has continued):

| Column | Populated (real-data) | Honest baseline |
|--------|-----------------------|-----------------|
| Tax-storage / retrieval / update / unit | ~100% primary axis (95% multi-value) | Most rows describe their architecture |
| Tax-governance | **T1 100%, T2 99%, T3 73%, T4 71%, T5 31%** | Backfilled since v1 |
| GitHub | 150 (every OSS row + some hybrids) | Non-OSS rows are blank by design |
| Funding | **220** (was 32 in v1) | Includes parent-company valuations on platform-provider rows |
| Customers | **175** (was 43) | 58% of commercial rows still have no public customer data |
| Performance | **103** (was 8) | Now includes per-system perf claims, not only public-leaderboard entries |
| Mindshare | **275** (was 49) | Many small / academic systems still aren't measurable |
| Citations | **209** (was 183) | Pre-print papers <1 year old typically have 0 |

---

## 1. The architecture map (from taxonomy columns)

### 1.1 Storage primitive distribution across 523 rows

Counted from the **Storage** column (taxonomy), all values (not just primary):

| Primitive | Count (any) | Count (primary) | Where it dominates |
|-----------|-------------|------------------|--------------------|
| `vector` | 206 | 157 | Default everywhere; only primitive without a domain |
| `graph` | 91 | 73 | Knowledge-graph products + Graph-RAG papers |
| `kv` | 66 | 54 | KV stores + voice-agent slot-filling |
| `file` | 61 | 55 | File-backed paradigms; coding agents; Karpathy thread |
| `parametric` | 50 | 48 | Knowledge-editing + continual-learning papers |
| `relational` | 47 | 28 | Pgvector / MongoDB / observability stack |
| `hybrid` | 42 | 42 | Multi-primitive products (Mem0, Memory³) |
| `kv-cache` | 33 | 29 | Transformer-internal compression papers |
| `n/a` | 28 | 28 | Benchmarks / theoretical / no-stored-state designs |
| `proprietary` | 8 | 8 | Closed platform-provider rows |

**Vector is the field's commodity primitive** (39% of any-value entries).
The next four primitives (`graph`, `kv`, `file`, `parametric`) split the
remainder roughly evenly — none is dominant. **The catalog is
architecturally pluralistic, not consolidated.**

### ✶ v2 1.1.a Section × storage concentration (from `section-stats.ts`)

| Section | Vector share | Graph share | Reads as |
|---------|--------------|-------------|----------|
| Vector-database infrastructure | 15/15 (100%) | 0% | Pure substrate |
| Knowledge-graph platforms | 0% | 17/17 (100%) | Pure substrate, opposite axis |
| Enterprise-search adjacencies | 7/9 (78%) | 0% | Glean / Coveo / Lucidworks all on vector |
| Retrieval-as-memory hybrids | 16/32 (50%) | 25% | Where Graph-RAG-lineage papers live |
| Vertical / domain AI | 28/64 (44%) | 17% | Pattern A dominates |
| Personal AI / PKM | 40% | 30% | Bi-temporal mix |
| Dedicated memory layers | 13/37 (35%) | 8/37 (22%) | Multi-primitive (`hybrid` also high) |
| Framework-embedded | 10/30 (33%) | 0% | KV-dominant (slot-filling for agent state) |
| Claude Code mechanisms | 6/19 (32%) | 7/19 (37%) | First section where **graph > vector** |
| File-backed / editor paradigms | 0% | 0% | `file` everywhere |
| Coding-agent memory | 0% | 27% | `file` dominant |

The Claude Code mechanisms section is the **only** section where graph
storage outnumbers vector — driven by the MCP-knowledge-graph plugin
ecosystem and Graphiti MCP integrations.

### ✶ v2 1.1.b Section-level median numerics (from `section-stats.ts`)

| Section | Rows | Med. citations | Med. funding | Med. GH stars |
|---------|------|----------------|--------------|----------------|
| Recent method papers — theorized | 171 | 35 | — | 427 |
| Vertical / domain AI | 64 | 67 | $82.0M | 331 |
| Dedicated memory layers | 37 | **1,000** | $10.0M | **12.3k** |
| Retrieval-as-memory hybrids | 32 | 97 | — | 1.2k |
| Framework-embedded memory | 30 | — | $35.0M | 27.8k |
| Coding-agent memory | 11 | — | **$394.5M** | 30.4k |
| Vector-database infrastructure | 15 | — | $73.0M | 24.4k |
| Knowledge-graph platforms | 17 | — | $12.5M | 484 |

Reads: **Dedicated memory layers carry the highest median GH-star
count of any product section (12.3k)** — the OSS-distribution channel
matters more than the funding scale (median funding $10M, far below
coding-agent $394.5M). **Coding-agent memory sits at $394.5M median
funding**, an order of magnitude above any other memory-adjacent
product section.

### 1.2 The patterns that recur across sections

Scanning the taxonomy columns for matching fingerprints (storage/
retrieval/update/unit) reveals **21 patterns that appear in 3+ catalog
sections.** The strongest:

#### Pattern A — Vector + similarity + extraction + fact / episode
Same architecture across:
- **Mem0** (Dedicated memory layers) — see Tax row: `vector + graph + kv` storage, `similarity + graph-traversal + extraction-pull` retrieval, `extraction` update, `fact + episode` unit
- **Memori, Memobase, Hindsight (Vectorize)** — same Tax fingerprint, same section
- **Spellbook Library, Harvey Memory** (Legal AI) — same fingerprint, different section
- **ChatGPT Study Mode** (Education AI) — same fingerprint when Memory is enabled

When a vendor says "we built memory for X domain" without naming
architecture, this is overwhelmingly what they built. **Domain value
lives in the corpus, not the memory primitive.**

#### Pattern B — Bi-temporal KG + auditable governance
- **Zep & Graphiti** (Dedicated layers) — Tax: `graph` storage, `graph-traversal` retrieval, `append-only` update, `auditable` governance
- **Graphiti MCP Server** (Claude Code mechanisms) — same Tax fingerprint
- **Zep — governance posture** (Memory governance) — same fingerprint, billed under three sections

The catalog lists Zep three times under three section headers. The Tax
columns reveal it's structurally one architecture; the auditability is
a property of the bi-temporal-KG storage primitive, not a separately
sold feature.

#### Pattern C — File + injection + overwrite + user-controllable
The entire **File-backed / editor paradigms** section (**13 rows** in
v2: CLAUDE.md, Cursor Rules, Windsurf Rules & Memories, AGENTS.md,
GitHub Copilot custom instructions, Cline .clinerules, Cline Memory
Bank, Roo Code .roorules, Continue.dev .continue/rules, Aider
CONVENTIONS.md, Sourcegraph Cody, Replit replit.md, Zed .rules) shares
the exact same Tax row.

Thirteen UIs, one architecture. Plus this same fingerprint appears in
**Anthropic Managed Agents Memory** (Platform-provider) and
**Karpathy LLM Wiki** (Theoretical/informal) — confirming
files-as-memory crosses three sections.

✶ v2 see §3.3: **Pattern C is *not* a descent lineage.** The 13 rows
share an architecture but do not cite or build on each other — each
editor team shipped its own.

#### Pattern D — Vector + similarity + append-only + episode (raw episodic capture)
- **Bee, Friend** (Voice-first / wearable)
- **Galileo** (Memory observability)
- **Generative Agents** (Method papers / Experiential)
- **MemMachine paper** (Method papers / Factual)
- **NVIDIA ReMEmbR** (Robotics)
- **Superpowers episodic-memory plugin** (Claude Code)

Six sections, one architecture: store the raw episode, retrieve by
similarity. The unit varies by vendor (a wearable conversation, an
agent reasoning trace, a robot's sensorimotor sequence) but the storage
primitive does not.

#### Pattern E — File + vector / extraction + similarity / append-only / document + episode (ambient capture + searchable timeline)
- **Limitless, Microsoft Recall** (Personal AI / PKM)
- **Otter.ai, Read.ai** (Voice-first)
- **Perplexity Comet** (Browser-agent)
- **Abridge** (Healthcare AI)

Same architecture across four domains: continuously capture artifacts
(audio / screen / tabs / clinical encounters), file + vector index,
support timeline search.

### 1.3 Patterns that *don't* cross over (genuinely domain-specific)

By inverse pivot — Tax fingerprints that appear in only **one** catalog
section with 3+ systems:

| Section | Fingerprint | Systems |
|---------|------------|---------|
| Knowledge-graph platforms | `graph+vector / graph-traversal+similarity / append-only+overwrite / fact` | Neptune, Dgraph, FalkorDB, Kuzu, Memgraph |
| Method papers / Experiential | `vector / similarity / extraction / skill` | CREATOR, MPO, PRINCIPLES, SkillWeaver, ToolMem |
| Method papers / World-model | `parametric / parametric-recall / parametric-edit / trajectory` | DIAMOND, Dreamer 4, DreamerV3, R2I, PWM |
| Memory observability | `relational / exact-match / append-only / episode` | AgentOps, LangSmith, Langfuse |

**Three observations from this:**
- **World-model RSSM is genuinely a separate architectural family.**
  Confirmed by lineage detection (§3.1).
- **Skill-extraction is mostly confined to research papers** — but
  **✶ v2** Interloom (T1, $16M Seed 2026-03) and LangMem (T2, OSS)
  have now adopted skill-unit memory. LinkedIn Cognitive Memory Agent
  (T1) is a third commercial entry. The §9.2 white-space is starting
  to fill.
- **The observability stack is its own architecture.** Three
  observability vendors with the same Tax fingerprint, no overlap with
  the memory products they observe.

---

## 2. Adoption — what is actually being used (from GitHub, Mindshare, Created columns)

### 2.1 ✶ v2 Top systems by GitHub stars (`leaderboards.ts` → mostStarred)

| Rank | Row | Stars | 30d Velocity | Language | Created |
|------|-----|-------|--------------|----------|---------|
| 1 | Official MCP Memory server | 85.1k | +4.8k/mo | TypeScript | 2024-11 |
| 2 | claude-mem | 72.7k | +9.1k/mo | TypeScript | 2025-08 |
| 3 | MetaGPT | 67.5k | +1.9k/mo | Python | 2023-06 |
| 4 | AutoGen Memory | 57.7k | +1.7k/mo | Python | 2023-09 |
| 5 | **Mem0** | **54.9k** | +1.6k/mo | Python | 2023-06 |
| 6 | **MemPalace** | **51.3k** | **+49.6k/mo** | Python | **2026-04** |
| 7 | CrewAI Memory | 50.7k | +1.6k/mo | Python | 2023-09 |
| 8 | LlamaIndex Memory | 49.2k | +1.1k/mo | Python | 2023-02 |
| 9 | Aider | 44.4k | — | Python | — |
| 10 | Milvus | 44.1k | +546/mo | Go | 2019-09 |

**✶ v2 correction:** v1 listed *Superpowers episodic-memory plugin* at
#1 with 179.8k stars. The current cell reads **372★ +10/mo TypeScript**
— v1's number conflated the parent `obra/superpowers` repo with the
specific plugin. The plugin itself never had that velocity.

MemPalace remains a multi-column anomaly: created 2026-04, 51.3k stars
in <1 month, 96.6% LMES with the ⚠ disputed flag still in the cell.

### 2.2 Stalled-but-high-stars (active research-paper-repo half-life)

Visible in GitHub col as `<span class="signal-warn">stalled</span>`:

Generative Agents (last commit 2024-08, 21.3k stars, 3,896 citations),
Reflexion (2025-01, 3,240 cites), HippoRAG (2025-09, 3.5k stars),
MemoRAG (2025-09), I-JEPA (2024-05, 3.4k stars), DreamerV3 (2025-09),
RAPTOR, NIAH benchmark, bolt.new (2024-12), Memary, Adaptive-RAG.

A research-paper repo's value is the paper's value; active
maintenance ends when the next paper ships. Citation counts (Citations
col) confirm these are widely cited, but the GitHub repos are no
longer evolving.

### 2.3 ✶ v2 Integration hubs (from edge graph — `leaderboards.ts` → mostIntegrated)

Computed directly from `landscape.edges.json` — counts inbound
`integrates-with` + `built-on` + `extends` edges per target. This is
the leaderboards page's "Highest inbound integrations" board.

| Hub | Inbound | Notes |
|-----|---------|-------|
| **Mem0** | **12** | 2.4× #2; the only commercial memory layer with double-digit inbound |
| LangGraph Persistence | 5 | Framework hub |
| Qdrant | 4 | Substrate |
| Pinecone | 3 | Substrate |
| pgvector | 3 | Substrate |
| Zep & Graphiti | 3 | Pattern B sole representative |
| Amazon Neptune Analytics | 3 | KG substrate |
| Cognee | 2 | |
| Hindsight (Vectorize) | 2 | |
| MongoDB Atlas Vector Search | 2 | |
| Chroma | 2 | |

**Mem0's 12 inbound is the highest in the field.** v1's claim of "12
inbound" verifies; the field around it has consolidated rather than
caught up. Letta = 0 inbound in the edge graph, Cognee = 2, Memobase =
0. **Network effect at the integration layer is real and concentrated.**

### 2.4 Package-level adoption (Mindshare col)

The Mindshare column also shows package downloads where applicable.
Top by monthly downloads:

| Row | Package | Monthly downloads |
|-----|---------|-------------------|
| Official MCP Memory server | `@modelcontextprotocol/sdk` | **138M** npm |
| Weaviate | `weaviate-client` | **109M** PyPI |
| Qdrant | `qdrant-client` | 23M PyPI |
| pgvector (PyPI wrapper) | `pgvector` | 21M PyPI |
| Chroma | `chromadb` | 14M PyPI |
| LlamaIndex Memory | `llama_index` | 10.4M PyPI |
| CrewAI Memory | `crewai` | 7.3M PyPI |
| LanceDB | `lancedb` | 7M PyPI |

**Two observations:**
- **Substrate dwarfs frameworks.** Weaviate / Qdrant / Chroma client
  downloads (cumulative >150M/mo) far exceed any agent-framework
  package (max ~10M/mo for LlamaIndex). The actual production-volume
  layer is the storage substrate, not the agent framework on top.
- **MCP transport is the highest-volume package in the entire catalog.**
  138M/mo. That's not memory-product adoption — it's the underlying
  transport everyone is wiring to.

### 2.5 Job postings (Mindshare col)

LinkedIn-keyword job-posting counts (with the noise caveat that a
generic name like "Friend" picks up unrelated postings):

- LangChain: **15,000+** (highest in catalog)
- Neo4j: 2,000+
- Replit Agent: 1,000+
- Glean: 660
- Qdrant: 674
- Pinecone: 433
- Otter.ai: 146
- Hippocratic AI: 76
- Weaviate: ~82
- Mem0, Letta, Zep: 7–8 each
- Inworld AI: 10

**Job postings are a workforce-demand proxy.** LangChain's 15k+
indicates the framework has already crossed into "skill mainstream"
status — companies are hiring people who know it. Memory-layer
products at 7–8 each tell you those teams are small (the postings are
mostly internal openings, not ecosystem demand).

---

## 3. ✶ v2 Lineages — the descent map (from `lineages.ts` + edges)

The KG now exposes 247 edges. Filtering to descent-only (`built-on`,
`extends`, `forks`, `succeeds`, and influential `cites`) yields 215
edges that imply "B was built from A." Lineage detection runs in two
passes: (1) curated seeds expanded by BFS depth-2, (2) union-find on
the remainder, keeping components of size ≥3.

`lineages.ts` distinguishes two **kinds** of lineage:
- **`descent`** — a parent → child chain in the structural-descent graph.
  Solid arrows in the /lineages view.
- **`pattern`** — a family that converged on the same architectural
  shape by parallel evolution. No descent edges between members; the
  page draws dashed "parallel-implementations" connectors instead.

### 3.1 Curated lineages (3)

| Lineage | Kind | Members | Composition |
|---------|------|---------|-------------|
| **RSSM / world-model family** | descent | 5 | DreamerV3 (anchor) → DIAMOND, PWM, R2I, Transformer-XL |
| **Graph-RAG hierarchy** | descent | 16 | GraphRAG (Microsoft, anchor) → LightRAG, LazyGraphRAG, PathRAG, RGMem, RouteRAG, StructRAG, HippoRAG / HippoRAG2, RAPTOR, ReadAgent, BGE-M3, SGMem, **Zep & Graphiti**, ComoRAG, CAM, GSW |
| **Files-as-memory thread** ✶ v2 | **pattern** | ~32 | CLAUDE.md (anchor) + all "File-backed / editor paradigms" rows + all "Claude Code memory mechanisms" rows — see §3.3 |

The Graph-RAG hierarchy is the largest descent-kind family in the
catalog and it pulls Zep & Graphiti in — confirming Pattern B (§1.2)
is the commercial endpoint of the Graph-RAG research lineage.

### 3.2 Auto-discovered lineages (descent kind; 6 within topN cap; 7 total ≥3)

| Lineage | Size | Anchor | What it represents |
|---------|------|--------|--------------------|
| Influential-cite backbone | **96** | A-MEM | The full research-paper sub-graph through influential cites — one giant component |
| Mem0 ecosystem | 10 | Agno (Phidata) Memory | Mem0 + Mem0 MCP + OpenMemory + Mem0 Security + Agno + Amazon Neptune Analytics + FalkorDB + pgvector + ... |
| Continual learning / EWC | 4 | EWC | EWC, FOREVER, WISE, CL of LLMs Survey |
| MCP knowledge-graph servers | 3 | Continue.dev Memory MCP | + mcp-knowledge-graph + Official MCP Memory server |
| Hindsight cluster | 3 | Hindsight (Vectorize) | + Hindsight MCP + Pydantic-AI + Hindsight |
| JEPA family | 3 | I-JEPA | + V-JEPA + V-JEPA 2 |
| ReMEmbR / spatial | 3 | Meta-Memory | + Milvus + NVIDIA ReMEmbR |

The "influential-cite backbone" component is **structural**: when 96
papers are within depth-2 of one another via influential cites, the
naive union-find collapses them into one mega-lineage. The page caps
this with the depth-limited BFS for curated seeds but otherwise reports
it honestly — this is what the descent graph actually looks like at
the research level.

### 3.3 ✶ v2 Insight: files-as-memory is a *pattern*, not a *descent*

v1 of `analysis.md` claimed *files-as-memory* as one of four lineages.
**The descent-edge auto-discovery does not find it — and that's the
correct behavior**, not a bug. CLAUDE.md, Cursor Rules, AGENTS.md,
etc. did not descend from one another. They emerged in parallel as
implementations of the same idea ("a markdown file the agent loads
into context"). There is no built-on / extends / cites edge between
them; each editor team shipped its own.

✶ v2 The lineages view solves this by introducing a **pattern**-kind
seed (`kind: 'pattern'` in `CURATED_SEEDS`). The Files-as-memory
thread is expanded by section membership rather than descent edges,
and rendered with dashed "parallel-implementations" connectors instead
of arrows. **The semantic distinction is now first-class in the UI**:
"X was built from Y" arrows for RSSM and Graph-RAG; "X and Y converged
on the same idea independently" dashes for files-as-memory.

The other three v1-claimed families (RSSM, Graph-RAG, KV-cache
eviction) *are* descent chains and *are* detected — RSSM and
Graph-RAG as curated seeds, KV-cache work shows up scattered through
the 96-node backbone via Transformer-XL → Compressive Transformer →
Infini-attention → H2O.

### 3.4 Sections vs lineages disagree by design

- The Mem0 ecosystem (lineage, 10 nodes) crosses 4 sections.
- Pattern C (13 file-backed rows, 1 section) is **not** a lineage —
  no descent edges.
- The Graph-RAG curated lineage (16 nodes) pulls Zep & Graphiti out
  of Dedicated memory layers and into the research-descent line.

**Sections are how people organize the field. Lineages are how the
work actually descended.** Use both.

---

## 4. Commercial signals — who's making money (from Funding, Customers cols)

### 4.1 ✶ v2 The valuation pyramid

| Tier | Row | Latest valuation |
|------|-----|------------------|
| Trillion-tier (parent vendors, not in catalog) | OpenAI / Anthropic / Google | ~$200B+ |
| Mega-cap | **Perplexity Memory** | **$20.0B** |
| | **Sierra** ✶ v2 | **$15.8B** |
| | **Devin (Cognition)** | **$10.2B** |
| | **Notion AI** | **$10.0B** (from 2021 round) |
| | **Replit Agent** | **$9.0B** (Series D, 2026-03) |
| | **Glean** ✶ v2 | **$7.2B** (Series F, 2025-06) |
| | **Lovable** | **$6.6B** |
| | **Granola** | **$1.5B** |
| | **LangChain (LangMem)** | **$1.2B** |
| Mid-cap | Augment Code | $977M |
| | Browserbase | $300M |
| Small-cap | **Mem0** | **$150M** |
| | **Letta / MemGPT** | **$70M** |
| Seed | Zep & Graphiti, Cognee, MemoraX, NeoCognition, Interloom, Nyne, Trace | $0.5M – $40M |

**✶ v2 The valuation gap has held, with more data behind it.** v1 cited
a 66× gap (Mem0 $150M ↔ Lovable $6.6B) and a 136× gap (Mem0 ↔
Perplexity $20B). Both still hold. The new Sierra row ($15.8B) and
Glean Series F ($7.2B) are additional data points on the
vertical-product side; no dedicated-memory-layer entry has crossed
$150M. **Memory is being priced as a feature of vertical agent products,
not as horizontal infrastructure.**

### 4.2 Customer traction (Customers col)

| Row | ARR | Customers | Employees |
|-----|-----|-----------|-----------|
| Notion AI | **$600M** | not enumerated | 1,000+ |
| Lovable | **$400M** | listed in coding | **146** ← striking |
| Perplexity Memory | $200M+ / $450M annualized | — | 1,200–1,500 |
| Replit Agent | $253M | — | 230–400 |
| **Glean** | **$200M** | **18+ named logos** (Booking, Comcast, eBay, Intuit, LinkedIn, Pinterest, Samsung, Zillow…) | 1,000+ |
| Devin (Cognition) | ~$150M | Goldman, Citi, Dell, Cisco, Ramp, Palantir, Nubank, Mercado Libre | hundreds |
| Otter.ai | $100M | — | 100–500 |
| AI21 Labs (Jamba) | $57.8M | — | 200+ |
| Tabnine | $27M | — | 100–500 |
| Augment Code | $20M | — | 100–500 |
| LangMem (LangChain) | $16M | — | 50–200 |
| Lindy AI Memory | $5.1M | — | 11–50 |
| **Letta / MemGPT** | **$1.4M** | — | 11–50 |

Two extreme observations:

- **Lovable's $400M ARR ÷ 146 employees = ~$2.7M ARR/employee.** That
  is the most striking revenue-per-employee ratio in the entire
  catalog. Vibe-coding agents that absorb memory as a feature are
  generating ~5–10× the revenue per head of horizontal memory layers.
- **Letta — UC Berkeley research spinout, $70M valuation — has $1.4M
  ARR.** The horizontal-memory-layer category isn't pre-product; it's
  pre-revenue. Mem0 doesn't disclose ARR; given developer-signup count
  (80k+, in their Customers cell) the field reads as enthusiast adoption
  without enterprise contract revenue.

This explains §4.1's valuation gap quantitatively. Capital flows where
revenue does.

### 4.3 Funding waves over time (Funding col)

The Funding col shows the latest round's date for each commercial row.
Aggregating mentally across the table:

- **Q4 2023 – Q1 2024** — Pre-LLM-hype foundations: Mem0 Seed, Letta
  Seed, Zep Pre-Seed.
- **Mid 2024** — Vector DB consolidation (Pinecone, Qdrant, Weaviate
  rounds).
- **Sep–Oct 2025** — Memory-layer A-rounds: Mem0 $20M Series A
  (2025-10) at $150M val. LangChain $125M Series B (2025-10) at $1.25B.
  Letta and Vectorize/Hindsight in this window.
- **Q1 2026** — **First multi-company memory-layer wave**: Cognee
  €7.5M (2026-02), Interloom $16.5M (2026-03), Nyne $5.3M (2026-03),
  MemoraX $10M (2026-03), NeoCognition $40M (2026-04). All Seed-stage
  except NeoCognition. **Five dedicated-layer companies raising in one
  quarter is the strongest "category is real" signal of the year.**

---

## 5. Performance — who's claiming what, and what's verifiable (Performance col)

The Performance col now has **103 entries** (was 8 in v1) — most are
per-system perf claims (latency, throughput, vendor-quoted accuracy)
rather than public-leaderboard appearances, so the headline read
stays: **the only widely-comparable scores are LongMemEval-S and
LoCoMo**.

### 5.1 LongMemEval-S leaderboard timeline

Per the Perf column on each row + the source-cited timeline:

| Date | Row | Score | Status |
|------|-----|-------|--------|
| Oct 2024 | LongMemEval paper itself | GPT-4o full-history: 60–64%; oracle: 87–92% | Reference |
| Jun 2025 | Emergence AI | 82.4% public / 86.0% internal | First post-oracle |
| Feb 2026 | **Mastra Memory** | **94.87%** (gpt-5-mini) | OSS |
| ~Feb 2026 | **OMEGA** | **95.4%** | Both claim #1 depending on framing |
| **Apr 2026** | **MemPalace** | **96.6%** | **⚠ Disputed: figure is recall_any@5 not QA accuracy** |

The MemPalace flag in the Perf col cross-references the same anomaly
visible in Created (`2026-04`) and GitHub (51k stars in 1 month). All
three columns flag the same row independently.

### 5.2 LoCoMo (the most disputed benchmark)

Visible in Perf col across multiple rows:

| Row | Score | Note |
|-----|-------|------|
| Mem0 | **91.6** (token-efficient) | Mem0-corrected score |
| MemMachine paper | 91.69 | Above Mem0 |
| Letta / MemGPT | 74.0 (file-based) | gpt-4o-mini |
| Zep & Graphiti | **75.14** (Zep's correction) / **58.44** (Mem0's correction) | ⚠ unresolved |
| ByteRover | 92.2–96.1 | Single-team self-report |

The Zep / Mem0 dispute is unresolved (`getzep/zep#405` documents
practitioner inability to reproduce either figure). **Self-reporting
bias is universal**: every score above is reported by the team whose
system is being benchmarked. **Mem0 vs Zep is the only adversarial
cross-check in the catalog.**

### 5.3 ConvoMem — the threshold finding

Salesforce Research, Nov 2025 (cited in Perf col on the ConvoMem row).
**Primary methodological result: under ~150 conversation interactions,
full-context long-context LLMs significantly outperform RAG-based
memory.** Mem0 hit 30–45% on preference / implicit-connection
categories where full-context hit 63–90%.

Implication: **dedicated memory layers add value past the
~150-interaction horizon; below it, longer context wins.** Visible in
the decision matrix (§8).

### 5.4 The backbone-attribution problem

Every score >90% on LongMemEval-S and LoCoMo uses gpt-4.1-mini or
gpt-5-mini as the backbone. **You cannot separate "better memory
system" from "better backbone LLM" from any published number.**

This is structural. If a memory layer publishes a number, ask which
backbone they used and whether they tested across backbones.
Currently, *no* memory layer in the catalog has tested across
multiple backbones publicly.

### 5.5 LongMemEval-M (the harder variant) is ignored

LongMemEval-M is ~1.5M tokens, 500 sessions. **Zero entries in the
Performance col cite a LongMemEval-M score.** The entire competitive
race is on the easier 115k-token variant.

First credible LongMemEval-M result is open white space (§9.5).

---

## 6. Citation impact — research velocity (Citations col)

### 6.1 ✶ v2 Top by total citations (T3/T4 — `leaderboards.ts` → mostCited)

| Row | Total cites | Year |
|-----|-------------|------|
| EWC (Elastic Weight Consolidation) | **9,600** | 2016 |
| Transformer-XL | **4,300** | 2019 |
| Generative Agents | **3,900** | 2023 |
| Toolformer | **3,600** | 2023 |
| Reflexion | **3,200** | 2023 |
| REALM | 2,900 | 2020 |
| RL Developer Memory | 2,026 | — |
| Self-RAG | 1,800 | 2023 |
| RETRO | 1,600 | 2021 |
| ToolLLM | 1,500 | 2023 |

✶ v2: Transformer-XL now appears at #2 (was ~3,000 in v1; now 4,300 —
S2 re-indexed). EWC at 9,600 is a temporal artifact — 10-year-old
foundational paper. The substantively important cluster — **the 2023
trio** (Generative Agents, Toolformer, Reflexion) — is unchanged.

### 6.2 Top by citations / year (the actively-cited cluster)

Visible in Citations col as "X/yr":

| Rank | Row | Cites/yr | Year |
|------|-----|----------|------|
| 1 | Generative Agents | **1,299/yr** | 2023 |
| 2 | Toolformer | 1,209/yr | 2023 |
| 3 | Reflexion | 1,080/yr | 2023 |
| 4 | NVIDIA Isaac GR00T N1.7 | 677/yr | 2025 |
| 5 | BGE-M3 | 620/yr | 2024 |
| 6 | Transformer-XL | 612/yr | 2019 |
| 7 | Self-RAG | 592/yr | 2023 |
| 8 | REALM | 488/yr | 2020 |
| 9 | ToolLLM | 485/yr | 2023 |
| 10 | A-MEM | 443/yr | 2025 |

**The 2023 cluster dominates** (3 of the top 4 by velocity, all 4 in
top 10 by total). This is the "post-ChatGPT inflection" that prior
data-2 analysis flagged at conference acceptance counts — visible here
again at the citation level.

A-MEM at #10 with a 2025 publication is the only newer paper in the
top 10. Suggests fast uptake of the Zettelkasten-style agent memory
pattern.

### ✶ v2 6.3 Top by inbound citations *within the catalog* (edges)

`leaderboards.ts` → `mostInboundCites`. This counts inbound `cites`
edges per target node in `landscape.edges.json`.

| Rank | Row | Inbound cites (in-catalog) |
|------|-----|----------------------------|
| 1 | LoCoMo | 9 |
| 1 | A-MEM | 9 |
| 3 | Compressive Transformer | 8 |
| 3 | GraphRAG (Microsoft) | 8 |
| 3 | Transformer-XL | 8 |
| 6 | Generative Agents | 6 |
| 7 | MemoryBank | 5 |
| 7 | Self-RAG | 5 |
| 7 | Atlas | 5 |
| 10 | Reflexion | 4 |

Inbound-cite count from the catalog is a different signal from total
S2 cites: it measures **how central a paper is *to other memory
work* in this catalog**, not how influential it is in absolute terms.
LoCoMo / A-MEM / GraphRAG dominate because they are the
most-frequently-built-on substrates in the memory subfield specifically.

### 6.4 Citations corroborate or contradict GitHub stalled-vs-active

Cross-cutting Citations against the GitHub col:

- **Generative Agents**: 21.3k stars, last commit 2024-08, **3,896
  cites**. Repo stalled but paper is alive.
- **HippoRAG**: 3.5k stars, last commit 2025-09, ~700 cites. Both stalled.
- **Reflexion**: 3.1k stars, last commit 2025-01, **3,240 cites**. Repo
  stalled but paper alive.
- **Transformer-XL**: low public visibility but 612 cites/yr.
  Foundational; everyone cites it.

Conclusion: **a stalled repo does not mean a dead idea.** It means the
paper has been absorbed; the next paper has moved on. The citation
column tells you which ideas are still being built upon.

---

## 7. The horizontal-substrate vs vertical-product question (re-argued from table data)

Previously framed in narrative; here it gets the quantitative grounding.

**The catalog organization implies horizontal infrastructure.** Sections
named "Dedicated memory layers," "Vector-database infrastructure,"
"Knowledge-graph platforms" — sounds like a substrate market.

**The table's commercial columns say differently.**

The cleanest single test: compare top valuation in each tier.

| Tier from §4.1 | Top valuation | Top ARR |
|---------------|---------------|---------|
| Vertical agent products | $20B (Perplexity) / $15.8B (Sierra ✶ v2) | $600M (Notion AI) |
| Coding-agent products | $10.2B (Cognition) | $400M (Lovable) |
| Enterprise search ✶ v2 | $7.2B (Glean) | $200M (Glean) |
| Frameworks | $1.2B (LangChain) | $16M |
| **Dedicated memory layers** | **$150M (Mem0)** | **$1.4M (Letta)** |

That's the data. **Dedicated memory layers are commercially
~60–130× smaller than the agent products that consume them.**

But the substrate columns also tell a different story:
- Mem0 = 12 inbound edges (highest in field; §2.3)
- Pinecone / Qdrant / pgvector = 3–4 each (commodity)
- Weaviate = 109M PyPI downloads/mo (massive)
- MCP transport = 138M/mo (universal)

**The synthesis:** memory is **horizontal at the integration / substrate
layer** (Mem0 has the network effect, vector DBs are commodity
substrate, MCP transport is universal). It is **vertical at the
value-capture layer** (Cognition, Replit, Lovable, Perplexity, Sierra
own the user relationships and the $1B+ valuations).

This is not a contradiction. It's the same pattern that played out in
storage:
- **Postgres / Redis / Cassandra** = horizontal commodity substrate.
  Foundational, integrated everywhere, small commercial owners.
- **Application companies built on top** (Stripe, Shopify, etc.) =
  where the IPO outcomes sat.

**Mem0's likely trajectory: become the Postgres of agent memory.**
Ubiquitous, integration-rich, commodity-priced; small commercial
vendor with integration revenue but never reaching coding-agent
valuations. The 60× gap is structural, not a market mispricing.

---

## 8. Decision matrix (table-grounded)

Combines Tax columns, the ConvoMem 150-interaction threshold, and Performance col scores where they exist.

| Problem | Recommended Tax fingerprint | Specific systems (cite their row) | Why |
|---------|----------------------------|---------------------------------------|-----|
| Personal AI / cross-session continuity, **>150 turns** | `vector + similarity + extraction + long-term + fact` | **Mem0** (Perf 91.6 LoCoMo), Letta (74 LoCoMo), Hindsight | ConvoMem threshold; Mem0's integration count signals proven adoption |
| Personal AI / cross-session continuity, **<150 turns** | Long-context LLM, no memory layer | gpt-5-mini, claude-sonnet-4-x | ConvoMem: full-context outperforms RAG-memory under ~150 |
| Per-project memory for coding agent | `file + injection + overwrite + user-controllable` | CLAUDE.md, Cursor Rules, Cline Memory Bank, AGENTS.md | Inspectable, git-versioned; Pattern C confirms |
| Customer-relationship memory with audit trail | `graph + graph-traversal + auditable` | **Zep & Graphiti** (Pattern B); Salesforce Agentforce | Bi-temporal KG = governance built into storage |
| Patient-longitudinal clinical AI | `vector + similarity + extraction + episode/document` | **Abridge** (Pattern E), DeepScribe; Nabla for single-encounter | Ambient capture + searchable timeline |
| Long-document research-agent working memory | Long-context LLM with `kv-cache + evict-oldest` | ShadowKV-style; built into the inference stack | Working memory is transformer-internals |
| Lifelong robot / embodied memory | `scene-graph + graph-traversal + parametric` | Figure Helix, π0.5, Sanctuary AI; SG-Nav for nav | Domain-specific (§1.3); flat vector won't work |
| Curated / governance-sensitive corpus | `file + injection + user-controllable` (highest trust) **or** bi-temporal KG (highest auditability) | CLAUDE.md, Karpathy LLM Wiki, Zep | Trade flexibility for inspectability |
| Voice-driven dialog with structured outcomes | `kv + injection + overwrite + fact` (slot-filling) | Vapi, Voiceflow, Replicant | Pattern that doesn't cross outside dialogue |
| Ambient capture + searchable timeline (any modality) | `file+vector / extraction-pull+similarity / append-only / document+episode` | Limitless, Recall, Otter.ai, Read.ai, Abridge | Pattern E confirms cross-domain reuse |
| Skill-augmented agent (procedure / tool memory) ✶ v2 | `vector + similarity + extraction + skill` | **Interloom** (T1, $16M Seed 2026-03), **LangMem**, LinkedIn Cognitive Memory Agent | v1 said "none at production scale yet"; v2 has ≥3 commercial entries |

---

## 9. Anti-patterns

Where the catalog reveals products mispositioning themselves.

### 9.1 "Memory" that is actually progress tracking
Quizlet's Memory Score, Khanmigo's mastery state, Synthesis Tutor's
micro-assessment state. Tax cols show these as `vector / similarity /
extraction / fact` — but the "memory" semantic is known-progress
tracking, not learner profile. Calling them memory products inflates
expectations.

### 9.2 "Long-term memory" that is session-scoped chat history
Many T2 PKM and personal AI products advertise persistence; ConvoMem
shows that under ~150 turns, full-context beats most RAG-memory
implementations. **If your "memory" is chat history, you may be doing
worse than just keeping the chat history in the prompt.**

### 9.3 Optimizing only the easy benchmark variant
LongMemEval-S has dozens of competitive results in the Performance col;
LongMemEval-M has zero. The field has implicitly agreed to compete on
the easy variant.

### 9.4 Single-vendor benchmark with no adversarial check
Mem0 vs Zep on LoCoMo (Perf col, ⚠ flag) is the only documented case
of one vendor publishing an adversarial recomputation of another's
benchmark. The dispute is unresolved. **The practice should be the
field's norm, not its exception.**

### 9.5 Vector-as-default when domain is structured
The commodity vector-extraction pattern (§1.2 A) appears across legal,
clinical, customer-support memory products. But these domains have
structured data (case histories, EMRs, ticket relationships) that fit
graph or relational memory better. **The default is vector because
vector is what the agent frameworks expose, not because vector is the
right choice for the domain.**

### 9.6 In-weights memory as production-readiness claim
T3/T4 papers in the parametric+latent sub-group (M+, MemoryLLM,
SELF-PARAM, EWC, etc.) claim production-grade in-weights memory. The
Funding col shows zero commercial deployments in this category. The
field's actual production deployments use external stores; in-weights
memory is research-active but not commercially proven.

### 9.7 Confusing memory with context
Karpathy's "context engineering" naming event (June 2025, T5 row)
corrected widespread sloppy usage of "memory" to mean "anything in the
prompt." Some T2 entries still elide the distinction.

### 9.8 MemPalace-style anomalies (multi-signal flags)
When a row shows simultaneous anomalies across **3+ columns** (Created
in last 30 days **AND** GitHub star velocity 5–10× any peer **AND**
Performance with ⚠ disputed flag), treat all of its claims as
unverified. This is what the multi-column structure is for.

---

## 10. White-space gaps — ✶ v2 revisited

v1 listed 5 gaps. Status as of 2026-05:

1. **`scene-graph` + non-robotics** — UNCHANGED. Still confined to
   embodied agents and a handful of world-model papers (SG-Nav, SGMem,
   Tesla FSD 4D, Meta-Memory). No personal-AI or legal-AI product has
   adopted scene-graph storage.
2. **`skill` + commercial memory layer** — ✶ **PARTIALLY FILLED.**
   v1: "research-only." v2: Interloom ($16M Seed 2026-03, T1) and
   LinkedIn Cognitive Memory Agent (T1) ship `skill`-unit memory.
   LangMem (T2) added skill as well. Still no horizontal play of
   the scale of Mem0; but the category is no longer empty. Decision
   matrix §8 row updated accordingly.
3. **Bi-temporal KG outside Zep** — UNCHANGED. A literal substring
   search across all 523 records shows "bi-temporal" *only* in the
   three Zep entries (Zep & Graphiti, Graphiti MCP Server, Zep
   governance posture). Largest moat in the catalog by structural
   uniqueness; healthcare, legal, scientific verticals all have
   temporal-correctness requirements and currently use
   vector-extraction.
4. **`auditable` governance + dedicated memory layer** — UNCHANGED at
   the dedicated-layer slice. T3/T4 governance disclosure improved
   broadly (§11.3) — most papers now claim `inspectable` — but Zep
   remains the only dedicated memory layer with
   auditable-by-construction.
5. **LongMemEval-M competitive results** — UNCHANGED. **Zero entries**
   in the Performance col cite a LongMemEval-M score (verified again
   via substring search). Easiest open white space.
6. **Cross-modal memory at production scale** — UNCHANGED.
   M3-Agent (ByteDance) is still the only multi-modal multi-memory
   entry in the Tax column and is closed. The JEPA family (lineage
   §3.2, I-JEPA + V-JEPA + V-JEPA 2) is the credible research thread.
7. **Memory observability for non-LangChain stacks** — UNCHANGED.
   Five-row observability section is all LangChain-coupled.

✶ v2 net status: 1 of 5 v1 gaps has partially filled (skill-unit);
the other 4 are unchanged. The 2 v1.5-added gaps are also unchanged.

---

## 11. ✶ v2 What the data says about itself

Things that became visible only after the data populated.

### 11.1 The catalog over-counts as a single product

Zep appears 3 times (Pattern B). MemMachine appears 2 times
(framework vs paper). Memvid appears 2 times (library vs Claude
Code plugin claude-brain). **Apparent breadth is inflated by ~3% from
triple/double-counting.**

### 11.2 Lineage-detection vs section-membership disagree (productively)

§3 shows that section labels and lineage groupings disagree by design:
- The Mem0 ecosystem (lineage, 10 nodes) crosses 4 sections.
- Pattern C (13 file-backed rows, 1 section) is **not** a lineage —
  no descent edges.
- The Graph-RAG curated lineage (16 nodes) pulls Zep & Graphiti out of
  Dedicated memory layers and into the research-descent line.

**Sections are how people organize the field. Lineages are how the
work actually descended.** Use both.

### 11.3 ✶ v2 Governance disclosure correction

v1 claimed academic-tier governance nulls of 89% (T3) / 97.7% (T4).
v2 has these at **27% / 29%** — most papers now have a governance
tag, almost always `inspectable` (most-common value) or `opaque`. The
v1 finding was a **coverage gap in the tagging pass, not a structural
property of academic publishing.**

| Tier | Governance disclosed | Null |
|------|---------------------|------|
| T1 (commercial) | 143 / 143 | **0.0%** |
| T2 (mature OSS) | 134 / 135 | 0.7% |
| T3 (peer-reviewed) | 72 / 99 | **27.3%** |
| T4 (preprint) | 94 / 133 | **29.3%** |
| T5 (informal) | 4 / 13 | 69.2% |

The corrected reading: **academic papers describe storage / retrieval
/ update axes consistently; they default to `inspectable` for
governance because the code is open source, but they rarely engage
with consent flows / provenance / audit-by-construction** — i.e. the
*quality* of governance disclosure is shallow even where the
*presence* is now near-complete. The field is producing memory designs
that *can* be audited (because OSS) without *building in* audit
guarantees.

### 11.4 The vocabulary-then-funding pattern (cross-pass corroboration)

- arxiv `factual_long_term` terminology crystallized **late Q3 2025**
- Funding col shows **Q1 2026 as the first multi-company-raise quarter**
  for dedicated memory layers (5 companies).
- ✶ v2: the Mem0 ecosystem lineage (auto-detected #2 by size) has its
  first auto-detected member outside Mem0's own properties appearing
  in **Q4 2025** (Hindsight integration).

That's a one-quarter vocabulary → funding lag with a one-quarter
funding → ecosystem-expansion lag. **Research vocabulary stabilizes →
category becomes legible to investors → funding wave follows →
integration network expands.** Worth tracking the next signal: when
does `world_model` (currently the bull arxiv category) cross from
research-dominant to commercially-funded. The RSSM curated lineage
(§3.1) is still 5 nodes, all academic.

---

## 12. ✶ v2 Forward-looking — what's growing, what's saturating

v1 asked "what's growing, what's saturating"; the citation graph and
lineage data now let us answer parts of it with data, not narrative.

### 12.1 Growing (data signal)

- **Mem0 ecosystem (lineage)** — 10-node component, still adding new
  integrators. Watch Q2 2026 for the next inbound.
- **Skill-as-memory in commercial** — was zero in v1, now 2–3 entries
  (Interloom, LangMem, LinkedIn Cognitive Memory Agent). Earliest-stage
  growth segment.
- **MCP-knowledge-graph servers (lineage)** — 3 nodes today; the
  Official MCP Memory server is the highest-volume package in the
  catalog (138M/mo). Likely to expand into 2026.
- **Graph storage in Claude Code mechanisms (§1.1.a)** — the only
  section where graph > vector. The MCP-KG plugins are the channel.

### 12.2 Saturating (data signal)

- **Vector-database substrate** — Pinecone, Qdrant, Weaviate, Chroma,
  pgvector are all at commodity-package volume (>100M/mo cumulative).
  No new entrants ranked.
- **Files-as-memory editor paradigm** — 13-row section (§1.2 C) is
  essentially closed; every major coding editor has shipped its version.
- **LongMemEval-S** — score ceiling at ~95%; race likely to stop
  before resolving the disputed MemPalace #1 spot.

### 12.3 Worth watching for category-creation

- **`world_model` arxiv vocabulary** — currently the bull research
  category. v1's prediction was that it would cross from
  research-dominant to commercially-funded; the RSSM lineage (§3.1)
  is 5 nodes, all academic. **Watch for the first commercial
  spinout.**
- **Bi-temporal KG** — Zep's moat is structural; if a healthcare or
  legal AI vendor were to acquire or recreate Pattern B, the
  white-space §10 item 3 would close fast.

---

## 13. Honest limitations

What this analysis cannot tell you, given the populated data:

1. **Coverage of non-public commercial data.** 12 companies in the
   Funding category have no public funding info; ARR disclosed for only
   14 of 52 commercial systems. Private companies don't share.
2. **Mention-volume noise.** Generic-name systems (Friend, Bee, Sierra,
   Lovable, Chroma, Granola, ELSA Speak) inflate HN / Reddit / press
   counts. The Mindshare col flags these inline.
3. **Citation lag.** Citations data is from Semantic Scholar; very
   recent (2026) papers have 0 cites by definition.
4. **Backbone-attribution (§5.4) is unsolvable** without per-backbone
   evaluations, which no vendor has published.
5. ✶ v2 **Lineage detection cap of topN=8** — the 7th auto-discovered
   lineage (ReMEmbR / spatial) is reported in §3.2 for completeness;
   the lineages page hides it by default.
6. ✶ v2 **Influential-cite backbone (96-node component)** is a real
   structural artifact, not a parameter glitch — but it makes
   "lineage size" a misleading metric for that one component.
7. ✶ v2 **Governance-disclosure depth.** §11.3: presence is now
   near-complete at T1/T2 and ~70% at T3/T4, but the value is
   overwhelmingly `inspectable` (default for OSS). Quality of
   governance engagement is shallow.

---

## Appendix — Source columns and files (✶ v2 updated)

| Column | Canonical source |
|--------|------------------|
| Taxonomy axes (storage / retrieval / persistence / update / unit / governance / conflict) | `landscape.json` records[*].taxonomy |
| GitHub, Created | `landscape.json` records[*].cells.gh / .created |
| Funding, Customers | `landscape.json` records[*].cells.funding / .customers |
| Performance | `landscape.json` records[*].cells.perf |
| Mindshare | `landscape.json` records[*].cells.mindshare |
| Citations | `landscape.json` records[*].cells.citations |
| Edges (cites / integrates-with / built-on / extends / forks / same-team-as) | `landscape.edges.json` (247 edges) |

App views that compute the figures above:

- `web/src/lib/leaderboards.ts` — top-N rankings (§2.1, §2.3, §6.1, §6.3)
- `web/src/lib/lineages.ts` — descent detection (§3)
- `web/src/lib/section-stats.ts` — per-section aggregates (§1.1.a, §1.1.b)
- `web/src/lib/timeline.ts` — created-date timeline used in §4.3, §11.4

Original CSV-bundle inputs (pre-Phase-1, retained for provenance):
- `.agent-results/data-1-github-adoption.csv` (GH + Created)
- `.agent-results/data-4-funding.csv` (funding rounds)
- `.agent-results/data-8-customers.csv` (ARR + named logos)
- `.agent-results/data-6-benchmark-leaderboards.csv` (perf)
- `.agent-results/data-5-cross-references.csv` (mindshare edges seed)
- `.agent-results/data-7-package-downloads.csv` (downloads)
- `.agent-results/data-9-mcp-jobs.csv` (jobs)
- `.agent-results/data-10-mindshare.csv` (HN/Reddit/press)
- `.agent-results/data-11-citations.csv` (S2)

Pre-computed pivots remain in `taxonomy/pivots.json` (21 cross-section
patterns, 9 single-section patterns, per-axis distributions).
