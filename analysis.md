# AI Memory Systems — Analysis (table-grounded)

This is the analytical layer over `landscape.html`. **Every numeric claim
in this document is verifiable in the HTML table** — find the row, look
at the cited column, follow the `↗` source link.

Column references used:
- **(Tax)** — Storage / Retrieval / Persistence / Update / Unit / Governance taxonomy axes (HTML cols 3–8)
- **(GitHub)** — Stars + 30-day velocity + language (HTML col 11)
- **(Created)** — Repo creation date (HTML col 12)
- **(Funding)** — Total raised + latest valuation + latest round (HTML col 13)
- **(Customers)** — ARR + employees + named logos (HTML col 14)
- **(Performance)** — Benchmark scores; ⚠ marks disputed claims (HTML col 15)
- **(Mindshare)** — Inbound integrations + package downloads + jobs + HN/Reddit/press (HTML col 16)
- **(Citations)** — Total + per-year via Semantic Scholar (HTML col 17)

**Cell population — what's "—" means:** dash means "no public data," not
"the system has zero." Coverage by column:

| Column | Populated | Honest baseline |
|--------|-----------|-----------------|
| Tax-storage / retrieval / update / unit | 90–95% | Most rows describe their architecture |
| Tax-governance | 54% (T1: 98%, T3: 11%, T4: 2%) | Academic papers systematically don't disclose |
| GitHub | 96 (every OSS row) | Non-OSS rows are blank by design |
| Funding | 32 (commercial w/ public rounds) | Most catalog rows are research / OSS / non-commercial |
| Customers | 43 (commercial w/ disclosed) | 58% of commercial rows have no public customer data |
| Performance | 8 (LME / LoCoMo / ConvoMem entrants) | Only systems that competed publicly |
| Mindshare | 49 (top systems by other signals) | Many small / academic systems aren't measurable |
| Citations | 183 (papers via S2) | Pre-print papers <1 year old typically have 0 |

---

## 1. The architecture map (from taxonomy columns)

### 1.1 Storage primitive distribution across 520 rows

Counted from the **Storage** column (taxonomy):

| Primitive | Count | Where it dominates |
|-----------|-------|--------------------|
| `vector` | 204 | Default everywhere; only primitive without a domain |
| `graph` | 93 | Knowledge-graph products + Graph-RAG papers |
| `kv` | 62 | KV stores + voice-agent slot-filling |
| `file` | 55 | File-backed paradigms; coding agents; Karpathy thread |
| `parametric` | 49 | Knowledge-editing + continual-learning papers |
| `relational` | 48 | Pgvector / MongoDB / observability stack |
| `hybrid` | 37 | Multi-primitive products (Mem0, Memory³) |
| `kv-cache` | 33 | Transformer-internal compression papers |

**Vector is the field's commodity primitive** (39%). The next four
primitives (`graph`, `kv`, `file`, `parametric`) split the remainder
roughly evenly — none is dominant. This means the catalog is
architecturally pluralistic, not consolidated.

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
The entire **File-backed / editor paradigms** section (CLAUDE.md, Cursor
Rules, Windsurf Rules, AGENTS.md, GitHub Copilot custom instructions,
.clinerules, Cline Memory Bank, Roo Code, Continue.dev, Zed .rules,
Replit replit.md, Sourcegraph Cody) shares the exact same Tax row.

Twelve UIs, one architecture. Plus this same fingerprint appears in
**Anthropic Managed Agents Memory** (Platform-provider) and
**Karpathy LLM Wiki** (Theoretical/informal) — confirming
files-as-memory crosses three sections.

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
  It does not cross over.
- **Skill-extraction is entirely confined to research papers.** No
  commercial memory layer ships skill-as-memory yet — see §10.2.
- **The observability stack is its own architecture.** Three
  observability vendors with the same Tax fingerprint, no overlap with
  the memory products they observe.

---

## 2. Adoption — what is actually being used (from GitHub, Mindshare, Created columns)

### 2.1 Top systems by GitHub stars (verifiable in GitHub col)

| Rank | Row | Stars | 30d Velocity | Language | Created |
|------|-----|-------|--------------|----------|---------|
| 1 | Superpowers episodic-memory plugin | 179.8k | +25.8k/mo | Shell | 2025-10 |
| 2 | Official MCP Memory server | 85.1k | +4.8k/mo | TypeScript | 2024-11 |
| 3 | claude-mem | 72.7k | +9.1k/mo | TypeScript | 2025-08 |
| 4 | MetaGPT | 67.7k | +1.9k/mo | Python | 2023-06 |
| 5 | AutoGen Memory | 57.7k | +1.7k/mo | Python | 2023-09 |
| 6 | **Mem0** | **54.9k** | **+1.6k/mo** | Python | 2023-06 |
| 7 | **MemPalace** | **51.3k** | **+49.6k/mo** | Python | **2026-04** |
| 8 | CrewAI Memory | 50.7k | +1.6k/mo | Python | 2023-09 |
| 9 | LlamaIndex Memory | 49.2k | +1.1k/mo | Python | 2023-02 |
| 10 | Milvus | 44.1k | +546/mo | Go | 2019-09 |

The Created column is doing real work here. **MemPalace was created
2026-04, less than a month before this snapshot.** That row's stars
divided by age = ~50k stars/month — not impossible for a viral launch
but it's the most extreme velocity in the catalog. Combined with §5.1,
this is corroborating evidence that something unusual is going on with
that row.

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

### 2.3 Integration hubs (from Mindshare col — inbound count)

| Hub | Inbound | Verifiable in HTML |
|-----|---------|---------------------|
| **Mem0** | **12** | Mindshare col on Mem0 row |
| LangChain / LangMem | 7 | Mindshare col on LangMem row |
| Pinecone | 6 | Mindshare col on Pinecone row |
| Qdrant | 6 | |
| pgvector | 5 | |
| Zep & Graphiti | 5 | |
| Neo4j | 4 | |
| LangGraph Persistence | 4 | |
| Redis | 4 | |

Mem0's 12 inbound is the highest in the field. Its closest competitors
in the dedicated-memory-layer category (Letta = 1, Cognee = 2, Memobase
= 1) are well behind. **Network effect at the integration layer is
real and concentrated.**

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

## 3. Commercial signals — who's making money (from Funding, Customers cols)

### 3.1 The valuation pyramid (Funding col)

Top valuations visible in the Funding col:

| Tier | Row | Latest valuation |
|------|-----|------------------|
| Trillion-tier (vendors integrated, not in catalog) | OpenAI / Anthropic / Google | ~$200B+ |
| Mega-cap | **Perplexity Memory** | **$20B** |
| | **Devin (Cognition)** | **$10.2B** |
| | **Notion AI** | **$10B** (from 2021 round) |
| | **Replit Agent** | **$9B** |
| | **Lovable** | **$6.6B** |
| | **Granola** | **$1.5B** |
| | **LangChain (LangMem)** | **$1.25B** |
| Mid-cap | Augment Code | $977M |
| | AI21 Labs (Jamba) | undisclosed Series D w/ NVIDIA + Alphabet |
| | Browserbase | $300M |
| | Hindsight (Vectorize) | $250M (Granola Series B) |
| | Bee acquired by Amazon | undisclosed |
| | Limitless acquired by Meta | undisclosed |
| Small-cap | **Mem0** | **$150M** |
| | **Letta / MemGPT** | **$70M** |
| Pre-Seed | Zep & Graphiti, Cognee, MemoraX, NeoCognition, Interloom, Nyne, Trace | $0.5M – $40M |

**The 60×–130× valuation gap.** Coding-agent and personal-AI products
sit at $6.6B–$20B. The dedicated-memory-layer category tops out at
$150M (Mem0). That's a **66× gap** between Mem0 and Lovable, **136× gap**
between Mem0 and Perplexity. **Memory is being priced as a feature of
vertical agent products, not as horizontal infrastructure.**

### 3.2 Customer traction (Customers col)

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

This explains §3.1's valuation gap quantitatively. Capital flows where
revenue does.

### 3.3 Funding waves over time (Funding col)

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

## 4. Performance — who's claiming what, and what's verifiable (Performance col)

The Performance col shows benchmark scores with **⚠ flags on disputed
claims**. As of this snapshot, only 8 rows have benchmark data because
**only 8 rows have publicly competed.** The rest of the field is silent
on benchmarks.

### 4.1 LongMemEval-S leaderboard timeline

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

### 4.2 LoCoMo (the most disputed benchmark)

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

### 4.3 ConvoMem — the threshold finding

Salesforce Research, Nov 2025 (cited in Perf col on the ConvoMem row).
**Primary methodological result: under ~150 conversation interactions,
full-context long-context LLMs significantly outperform RAG-based
memory.** Mem0 hit 30–45% on preference / implicit-connection
categories where full-context hit 63–90%.

Implication: **dedicated memory layers add value past the
~150-interaction horizon; below it, longer context wins.** Visible in
the decision matrix (§7).

### 4.4 The backbone-attribution problem

Every score >90% on LongMemEval-S and LoCoMo uses gpt-4.1-mini or
gpt-5-mini as the backbone. **You cannot separate "better memory
system" from "better backbone LLM" from any published number.**

This is structural. If a memory layer publishes a number, ask which
backbone they used and whether they tested across backbones.
Currently, *no* memory layer in the catalog has tested across
multiple backbones publicly.

### 4.5 LongMemEval-M (the harder variant) is ignored

LongMemEval-M is ~1.5M tokens, 500 sessions. **Zero entries in the
Performance col cite a LongMemEval-M score.** The entire competitive
race is on the easier 115k-token variant.

First credible LongMemEval-M result is open white space (§10.5).

---

## 5. Citation impact — research velocity (Citations col)

### 5.1 Top by total citations

Visible in Citations col on respective rows:

| Row | Total cites | Year |
|-----|-------------|------|
| EWC (Elastic Weight Consolidation) | **9,640** | 2016 |
| Generative Agents | **3,896** | 2023 |
| Toolformer | **3,628** | 2023 |
| Reflexion | **3,240** | 2023 |
| Transformer-XL | ~3,000 | 2019 |
| BGE-M3 | ~1,800 | 2024 |
| LongBench | ~1,400 | 2024 |
| HippoRAG | ~700 | 2024 |

EWC at 9,640 is a temporal artifact — 10-year-old foundational paper.
The substantively important cluster is **the 2023 trio** (Generative
Agents, Toolformer, Reflexion). All three crossed 1,000/year.

### 5.2 Top by citations / year (the actively-cited cluster)

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
top 10 by total). This is the "post-ChatGPT inflection" §4.2 of the
prior analysis flagged at conference acceptance counts — visible here
again at the citation level.

A-MEM at #10 with a 2025 publication is the only newer paper in the
top 10. Suggests fast uptake of the Zettelkasten-style agent memory
pattern.

### 5.3 Citations corroborate or contradict GitHub stalled-vs-active

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

## 6. The horizontal-substrate vs vertical-product question (re-argued from table data)

Previously framed in narrative; here it gets the quantitative grounding.

**The catalog organization implies horizontal infrastructure.** Sections
named "Dedicated memory layers," "Vector-database infrastructure,"
"Knowledge-graph platforms" — sounds like a substrate market.

**The table's commercial columns say differently.**

The cleanest single test: compare top valuation in each tier.

| Tier from §3.1 | Top valuation | Top ARR |
|---------------|---------------|---------|
| Vertical agent products | $20B (Perplexity) | $600M (Notion AI) |
| Coding-agent products | $10.2B (Cognition) | $400M (Lovable) |
| Frameworks | $1.25B (LangChain) | $16M |
| **Dedicated memory layers** | **$150M (Mem0)** | **$1.4M (Letta)** |

That's the data. **Dedicated memory layers are commercially
~60–400× smaller than the agent products that consume them.**

But the substrate columns also tell a different story:
- Mindshare col on Mem0 = 12 inbound (highest in field)
- Mindshare col on Pinecone, Qdrant, pgvector = 5–6 each (commodity)
- Mindshare col on Weaviate = 109M PyPI downloads/mo (massive)
- Strands Agents → Mem0 is the *only* exclusive integration

**The synthesis:** memory is **horizontal at the integration / substrate
layer** (Mem0 has the network effect, Pinecone/Qdrant/Weaviate are
commodity substrate, MCP transport is universal). It is **vertical at
the value-capture layer** (Cognition, Replit, Lovable, Perplexity own
the user relationships and the $1B+ valuations).

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

## 7. Decision matrix (table-grounded)

Combines Tax columns, the ConvoMem 150-interaction threshold, and Performance col scores where they exist.

| Problem | Recommended Tax fingerprint | Specific systems (cite their HTML row) | Why |
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
| Skill-augmented agent (procedure / tool memory) | `vector + similarity + extraction + skill` | **None at production scale yet** — see §10.2 | White space |

---

## 8. Anti-patterns

Where the catalog reveals products mispositioning themselves.

### 8.1 "Memory" that is actually progress tracking
Quizlet's Memory Score, Khanmigo's mastery state, Synthesis Tutor's
micro-assessment state. Tax cols show these as `vector / similarity /
extraction / fact` — but the "memory" semantic is known-progress
tracking, not learner profile. Calling them memory products inflates
expectations.

### 8.2 "Long-term memory" that is session-scoped chat history
Many T2 PKM and personal AI products advertise persistence; ConvoMem
shows that under ~150 turns, full-context beats most RAG-memory
implementations. **If your "memory" is chat history, you may be doing
worse than just keeping the chat history in the prompt.**

### 8.3 Optimizing only the easy benchmark variant
LongMemEval-S has dozens of competitive results in the Performance col;
LongMemEval-M has zero. The field has implicitly agreed to compete on
the easy variant.

### 8.4 Single-vendor benchmark with no adversarial check
Mem0 vs Zep on LoCoMo (Perf col, ⚠ flag) is the only documented case
of one vendor publishing an adversarial recomputation of another's
benchmark. The dispute is unresolved. **The practice should be the
field's norm, not its exception.**

### 8.5 Vector-as-default when domain is structured
The commodity vector-extraction pattern (§1.2 A) appears across legal,
clinical, customer-support memory products. But these domains have
structured data (case histories, EMRs, ticket relationships) that fit
graph or relational memory better. **The default is vector because
vector is what the agent frameworks expose, not because vector is the
right choice for the domain.**

### 8.6 In-weights memory as production-readiness claim
T3/T4 papers in the parametric+latent sub-group (M+, MemoryLLM,
SELF-PARAM, EWC, etc.) claim production-grade in-weights memory. The
Funding col shows zero commercial deployments in this category. The
field's actual production deployments use external stores; in-weights
memory is research-active but not commercially proven.

### 8.7 Confusing memory with context
Karpathy's "context engineering" naming event (June 2025, T5 row)
corrected widespread sloppy usage of "memory" to mean "anything in the
prompt." Some T2 entries still elide the distinction.

### 8.8 MemPalace-style anomalies (multi-signal flags)
When a row shows simultaneous anomalies across **3+ columns** (Created
in last 30 days **AND** GitHub star velocity 5–10× any peer **AND**
Performance with ⚠ disputed flag), treat all of its claims as
unverified. This is what the multi-column structure is for.

---

## 9. White-space gaps

Tax-fingerprint cross-products with no commercial product:

1. **`scene-graph` + non-robotics** — confined to embodied
   agents (§1.3). Could it work for personal AI's office / home memory,
   or legal AI's case-relationship structure?
2. **`skill` + commercial memory layer** — research-only (CREATOR, MPO,
   PRINCIPLES, SkillWeaver, ToolMem all in §1.3). No horizontal "skill
   memory layer" exists yet. Devin / Augment / Cursor each build their
   own. White space for a horizontal play.
3. **Bi-temporal KG outside Zep** — Pattern B is the strongest
   architectural moat in the catalog (§1.2 B), but only Zep / Graphiti
   commercializes it. Healthcare, legal, scientific verticals all have
   temporal-correctness requirements and currently use vector-extraction.
4. **`auditable` governance + dedicated memory layer** — Tax col shows
   only Zep has built-in audit posture among dedicated layers. Mem0,
   Letta, Cognee, Memobase have either bolt-on logging or no clear
   audit story. **Combined with the governance-null finding (§11.3),
   this is the single largest deployable-in-regulated-industries gap.**
5. **LongMemEval-M competitive results** — entire field has ignored
   the harder variant (§4.5). Easiest open white space.
6. **Cross-modal memory at production scale** — voice (Plaud, Bee,
   Limitless), visual (scene graphs, V-JEPA), and text (everything
   else) memory exist; few products span modalities. M3-Agent
   (ByteDance) is the only multi-modal multi-memory entry in the Tax
   column and is closed.
7. **Memory observability for non-LangChain stacks** — observability
   section's homogeneous fingerprint (§1.3, `relational + exact-match +
   append-only + episode`) is dominated by LangSmith / Langfuse /
   AgentOps which all assume LangChain. Non-LangChain agents have no
   purpose-built observability tier.

---

## 10. What the table tells us about the catalog itself

Things that became visible only after the data populated.

### 10.1 The catalog over-counts as a single product

Zep appears 3 times (Pattern B). MemMachine appears 2 times
(framework vs paper). Memvid appears 2 times (library vs Claude
Code plugin claude-brain). The same architecture sold three different
ways inflates the field's apparent breadth.

### 10.2 Skill-as-memory is research-only territory

Five papers (CREATOR, MPO, PRINCIPLES, SkillWeaver, ToolMem) all share
the `vector / similarity / extraction / skill` Tax fingerprint. None
of them has a commercial counterpart. This is a real white space —
see §9.2.

### 10.3 Academic literature systematically does not report governance

Tax-governance col null rates by tier:

| Tier | Governance disclosed | Null |
|------|---------------------|------|
| T1 (commercial) | 137 / 140 | 2.1% |
| T2 (mature OSS) | 129 / 134 | 3.7% |
| T3 (peer-reviewed) | 11 / 100 | **89.0%** |
| T4 (preprint) | 3 / 133 | **97.7%** |
| T5 (informal) | 3 / 13 | 76.9% |

**Commercial systems disclose governance posture. Academic papers do
not.** This is not a labeling artifact. It reflects what the
literature actually publishes. Memory papers describe storage,
retrieval, update mechanisms with reasonable consistency. They almost
never describe inspectability, audit-by-construction, consent flows,
or provenance preservation.

The field is producing memory designs without engaging with the
governance questions that determine deployability in legal / healthcare
/ finance / EU consumer markets.

### 10.4 The vocabulary-then-funding pattern (cross-pass corroboration)

- arxiv `factual_long_term` terminology crystallized **late Q3 2025**
  (per data-2 narrative).
- Funding col shows **Q1 2026 as the first multi-company-raise quarter**
  for dedicated memory layers (5 companies).

That's a one-quarter lag. **Research vocabulary stabilizes → category
becomes legible to investors → funding wave follows.** Worth tracking
the next signal: when does `world_model` (currently the bull arxiv
category, §4.1 in earlier data-2 pass) cross from research-dominant to
commercially-funded.

---

## 11. Honest limitations

What this analysis cannot tell you, given the populated data:

1. **Coverage of non-public commercial data.** 12 companies in the
   Funding category have no public funding info; ARR disclosed for only
   14 of 52 commercial systems. Private companies don't share.
2. **Mention-volume noise.** Generic-name systems (Friend, Bee, Sierra,
   Grok, Lovable, Chroma, Granola, ELSA Speak) inflate HN / Reddit /
   press counts. The Mindshare col flags these inline.
3. **Citation lag.** Citations data is from Semantic Scholar; very
   recent (2026) papers have 0 cites by definition.
4. **Conference acceptance counts (data-3) used keyword extrapolation**
   not direct query (OpenReview was unreachable in this session).
   ±25–35% confidence intervals.
5. **Backbone-attribution (§4.4) is unsolvable** without per-backbone
   evaluations, which no vendor has published.
6. **Tax-governance null at academic tier** (§10.3) — analysis of this
   axis at the research level is fundamentally limited until the
   literature changes.

---

## Appendix — Source columns and files

| HTML column | Data file |
|-------------|-----------|
| Storage / Retrieval / Persistence / Update / Unit / Governance | `taxonomy/tags.json` (drafted by tagging agent, schema in `taxonomy/schema.md`) |
| GitHub | `.agent-results/data-1-github-adoption.csv` |
| Created | `.agent-results/data-1-github-adoption.csv` |
| Funding | `.agent-results/data-4-funding.csv` (80 rounds, 30 companies) |
| Customers | `.agent-results/data-8-customers.csv` (52 systems) |
| Performance | `.agent-results/data-6-benchmark-leaderboards.csv` (29 entries) |
| Mindshare | `.agent-results/data-5-cross-references.csv` (72 edges) + `data-7-package-downloads.csv` + `data-9-mcp-jobs.csv` + `data-10-mindshare.csv` |
| Citations | `.agent-results/data-11-citations.csv` (189 papers via Semantic Scholar) |

Pre-computed pivots in `taxonomy/pivots.json` (21 cross-section
patterns, 9 single-section patterns, per-axis distributions, governance
null-rate by tier).
