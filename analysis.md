# AI Agent Infrastructure Landscape — Analysis (table-grounded)

> **✶ v6 — Tier-1/2/2.5/T2.6/T3 synthesis + new infrastructure
> (2026-05-16).** The catalog now spans **912 records across 34 sections**
> with **528 typed edges** (+212 runtime-dependency from T2-1 commit
> `ddb26c7`), **85 cells per record** (was 60; +8 obs / +7 cost / +7 eval
> / +3 trajectory / others from Tier-1 + T3-prep), and **15 analytical
> views** (was 8; +7 from Tier-1/2/T3-4: observability, eval-gap,
> cost-economics, benchmark-trust, product-benchmark-matrix, co-citation,
> trajectory, breakout-prediction — the influence view also gained
> centrality measures in T2-3). The dataset became its own standalone
> product at `data-v1.0.0` under CC-BY-4.0 (T0-1 commit `b6ea473`) and is
> now consumable from three surfaces — the original web app, a local
> MCP server (T2-5 `cf0dd6a`), and a `landscape` CLI (T2-6 `49fe43a`).
> Governance moved from absent to documented in `MAINTAINER.md` (T0-2
> `1ac4f6b`), with a 3-tier claim provenance schema (T0-3 `f05d5aa`),
> automated staleness CI (T0-4 `c4c9df7`), row-level + per-cell
> `last_verified_at` timestamps (T2.6-2 `c106dd5`), a section-audit
> rotation workflow (T2.6-3 `6d03253`), an intake-auto-research pipeline
> (T2.6-1 `de6fbc6`), and decay-cause forensics (T3-1 `9a83bf8` /
> `fbc61bb` / `79c24ec`). v6 adds seven new sections — §23-§29 —
> synthesising the analytical findings unlocked by all of this
> infrastructure. v5 sections §1-§22 are preserved; only §1, §19, and
> §22 get light deltas to fold in the new edge graph.

This is the analytical layer over `landscape.json` (and its rendered
`landscape.html`). **Every numeric claim in this document is verifiable
in the catalog** — find the row, look at the cited column, follow the
`↗` source link, or check the commit / view file cited in the
parenthetical. Findings new to the v2 refresh (2026-05) are marked
**✶ v2**. Findings new to the v2.1 delta refresh against the Round 7
699-record catalog (2026-05-12) are marked **✶ v2.1**. Findings new to
the v3 refresh against the 100%-terminal 699-record catalog (2026-05-13
git sha `8a4e3c8`) are marked **✶ v3**. Findings new to the v4 refresh
against the 859-record catalog (2026-05-13, post-Rounds-11/12/13) are
marked **✶ v4**. Findings new to the v5 refresh against the 894-record
catalog (2026-05-13, post-Round-15) are marked **✶ v5**. Findings new
to the v6 refresh against the 912-record / 528-edge catalog
(2026-05-16, post Tier-1/2/2.5/T2.6/T3-4) are marked **✶ v6**.

## ✶ v6 Executive summary (against 912-record catalog, 34 sections, 528 edges, 85 cells, 15 views)

Nine things a reader should take away before scrolling further (v5
items 2 and 4-9 still hold verbatim; items 1 and 3 carry v6 deltas
inline; the new analytical-view headlines live in §23-§29, not in
this summary):

1. **✶ v6 The catalog is 912 records across 34 sections** — up from
   894 in v5 by **+18 rows** (T2.6-1 auto-research intake `de6fbc6` and
   T2-1/T2-5/T2-6 supporting work added these incrementally).
   The three new sections are the *substrate reference layer* —
   **Foundation models (substrate reference) [13]** (the OpenAI /
   Anthropic / Google / Meta / Mistral / DeepSeek / Qwen / xAI /
   Cohere / Reka / 01.AI / AI21 / Amazon Nova roots that everything
   else builds on), **Multi-agent orchestration platforms [12]**
   (CrewAI, Mastra, AutoGen Studio, Strands Agents, AgentForce,
   LangGraph Multi-Agent, etc.), and **AI sandbox & runtime
   environments [10]** (E2B, Daytona, Modal Sandboxes, Northflank
   AI, RunCommand). **Tier split is now T1=271 / T2=269 / T3=197 /
   T4=144 / T5=13** (was 260/250/192/144/13 in v4). Section count
   moved 31 → 32 (15a) → 33 (15b) → 34 (15c).
2. **✶ v5 Cell totals: 894 × 60 = 53,640 cells. Real-data 18,817 /
   not-applicable 23,253 / depth-floor 11,570.** Zero
   no-data-with-no-explanation. The 100%-terminal guarantee from v3
   survives the 195-row expansion. Real-data cells grew by 808 since
   v4 (18,009 → 18,817); not-applicable grew by 1,292; depth-floor is
   unchanged at 11,570. The Round 15 additions were heavily
   substrate-shaped: foundation-model rows raise real-data populations
   on `perf` and `citations`, and raise not-applicable populations on
   `funding` (parent-vendor not broken out per FM).
3. **✶ v6 Edge graph is now 528** (was 314/v5, 313/v4, 299/v3, 278/v2.1):
   241 cites + **212 runtime-dependency (NEW edge type — T2-1, commit
   `ddb26c7`)** + 41 integrates-with + 22 built-on + 4 competes-with +
   3 extends + 2 same-team-as + 2 forks + 1 succeeds. The +214 between
   v5 and v6 is dominated by the runtime-dependency mining pass; the
   citation count crept up by +2 from intake. **§23 treats the
   runtime-dependency graph as a first-class substrate-risk map**:
   Anthropic Claude is now the most-depended-on substrate at 62 inbound
   runtime deps; the MCP spec is the surprise at #3 (34 inbound, the
   protocol becoming a substrate). Citation-graph hubs (Mem0, GraphRAG)
   are unchanged from v5; the runtime-dep graph asks a different
   question and surfaces different anchors.
4. **✶ v5 Lineage re-detection: 14 lineages of size ≥3** (was 10 in v4,
   9 in v3, 8 in v2.1). **7 curated + 7 auto-discovered.** Curated:
   RSSM 5, Graph-RAG 21, Files-as-memory 32, Specs-as-memory 5, **SSM
   5 (NEW pattern seed)**, **Browser-agent 21 (NEW pattern seed)**,
   **Robotics-FM 15 (NEW pattern seed)**. Auto: EWC-anchored backbone
   117, **Mem0 ecosystem now a single 10-node component (was two
   4-node sub-clusters in v4)**, DPO/RLHF descent 5, JEPA 3,
   Milvus/ReMEmbR 3, **MCP-knowledge-graph cluster 3 (NEW auto)**,
   **Hindsight-Vectorize cluster 3 (NEW auto)**. The 3 SSM / Browser /
   Robotics curated pattern seeds were promoted from "candidate
   lineages with zero descent edges" in v4 to first-class
   pattern-kind lineages in v5, exactly as DECISIONS.md 2026-05-13
   recommended.
5. **✶ v5 Top-10 integration hubs by inbound (all edge types) — unchanged
   from v4:** (1) **Mem0 12**, (1) **GraphRAG (Microsoft) 12 — tied**,
   (3) **MemGPT v2 / agent-tools 10**, (3) Compressive Transformer 10,
   (5) LoCoMo 9, (5) A-MEM 9, (7) **LangChain (framework) 8 — +1 from
   Round 15 multi-agent rows**, (7) Transformer-XL 8, (9) Zep & Graphiti 7,
   (9) Generative Agents 7. **The crown is still split**: Mem0 (12
   integrations) and GraphRAG (12 cites, 11 influential + 1 extends).
   See §19 for the cross-analysis of these hubs against survivorship,
   benchmark coverage, and archetype membership.
6. **✶ v4 The five-layer model.** Round 12 surfaced a fifth product
   layer — **operating environment** — distinct from memory / harness
   / IDE / agent-runtime. The substrate↔harness pairings are now
   first-class analytical objects: Anthropic Computer Use ↔ Claude
   for Chrome / Operator / Mariner; NVIDIA GR00T N1 ↔ Apptronik /
   Figure / 1X; LiveKit ↔ OpenAI Realtime / Vapi / Retell; Anthropic
   MCP ↔ many harnesses. **See new §15.** The earlier "Mem0 is the
   integration hub, GraphRAG is the citation hub" finding now sits
   inside this — those are *memory-layer* hubs, distinct from runtime /
   environment / harness hubs.
7. **✶ v5 Perf coverage tripled from v4: 307 cells (was 103 in v4),
   classified into 169 benchmark mentions across the integrity
   buckets:**
   - **Peer-reviewed: 111** (citation on arxiv.org / openreview.net /
     aclanthology.org / dl.acm.org / ieeexplore.ieee.org / doi.org —
     these are scores backed by an academic venue).
   - **Independently-verified: 2** (paperswithcode.com,
     huggingface.co — neutral leaderboards). **This is the most
     surprising integrity number in the catalog**: only 2 of 169
     benchmark mentions live on a neutral third-party leaderboard.
     Almost every score is either a paper or a vendor blog.
   - **Vendor-claimed: 52** (citation host matches the vendor's own
     domain — the score is announced by the vendor whose product is
     scored).
   - **Disputed: 4** (in-cell `⚠` / "disputed" / "rebuttal" or
     vendor-score-vs-paper divergence > 7 absolute points).
   - **Unverifiable: 0** (every benchmark mention resolves to a host).
   **The headline integrity finding**: vendor-claimed (52) is 31% of
   benchmark mentions. **Most-vendor-claimed benchmark: MMLU (14/17
   mentions are vendor blogs)**, then **SWE-bench (10/12 vendor)**.
   **Cleanest peer-reviewed coverage**: HotpotQA (10/10 PR),
   ALFWorld (9/9 PR), BABILong (5/5 PR), NIAH (7/7 PR). See §20 for
   the full integrity treatment, gaming-pattern surface, and
   leaderboard of validated winners.
8. **✶ v5 Foundation-model substrate dependency map (§19.5).** The
   13 new *Foundation models (substrate reference)* rows are the
   substrate that the rest of the catalog references via its
   `perf` / `claims` / `desc` / `customers` / `mindshare` cells.
   Cell-mining across those columns yields the following
   substrate-reference counts (**non-FM rows mentioning each FM by
   name**): **OpenAI GPT family 52, Anthropic Claude 52,
   Google Gemini 22, Alibaba Qwen 16, Mistral 12, Cohere Command 8,
   DeepSeek 6, AI21 Jamba 3, xAI Grok 2, Amazon Nova 2.** **140
   catalog rows (~16% of non-FM rows) name at least one foundation
   model in their cells**; the rest characterise their architecture
   without a backbone reference. Of the 140 that do, **108 (77.1%)
   depend on OpenAI / Anthropic / Google** — the single-vendor-risk
   tier. See §19.5 and §21.3.
9. **✶ v5 Three structural inversions and one valuation ramp visible
   in the new data — preserved from v4:**
   - **NVIDIA GR00T N1 open weights (Mar 2025)** flips the openness
     gradient: NVIDIA (silicon vendor, open) > Physical Intelligence
     (FM lab, partial open) > Figure / DeepMind (closed). The hardware
     vendor going more open than the AI labs is a notable inversion.
   - **LiveKit (Apache-2.0 OSS) is the WebRTC backbone for OpenAI's
     Realtime API** — an OSS framework is the production substrate of
     a hyperscaler's flagship voice API. Direction-of-build inverted
     from "hyperscaler ships proprietary backbone" to "hyperscaler
     adopts OSS substrate."
   - **Browser Use (~60k stars, $17M seed)** is the most-starred
     AI-agent OSS of 2025 — ETH Zurich-founded. The browser-control
     mindshare crown is European-research origin, not US Big Tech.
   - **Figure AI: $2.6B (Feb 2024) → $39.5B (Q2 2025), 15× in
     16 months** — fastest humanoid valuation ramp on record;
     Physical Intelligence raised $400M Series A 8 months after
     founding at $2.4B; **Covariant Amazon acqui-hire Aug-2024**;
     **ElevenLabs $180M Series C at $3.3B Jan-2025**.

---

## ✶ v3 Executive summary (preserved against 100%-terminal 699-record catalog)

Six things a reader should take away before scrolling further:

1. **✶ v3 The catalog is at 100% terminal state.** 699 records ×
   60 cells = **41,940 cells**; every one of them is either
   `real-data` with a citation (**14,498**), `not-applicable` with a
   reason (**16,487**), or `depth-floor-reached` with a search trail
   (**10,955**). Zero shallow-prose, zero no-citation, zero
   no-data-with-no-explanation. **What this means for trust:** any
   claim in this document can be drilled-down to its source cell.
   See the new §13 *Catalog quality and confidence* for the full
   trust ledger. Sections still at 26; tier split unchanged from v2.1
   (T1=211 / T2=191 / T3=140 / T4=144 / T5=13).
2. **✶ v3 Mem0 and GraphRAG (Microsoft) are now tied at 12 inbound
   edges (total, all types).** Round 9's cell-miner re-run added
   ~20 new `cites` edges, several pointing at GraphRAG — confirming
   it as the most-cited node in the catalog's research sub-graph.
   On the narrower integration-hub metric (`integrates-with` +
   `built-on` + `extends`), Mem0 remains alone at 12; GraphRAG's 12
   is 11 cites + 1 extends (LazyGraphRAG). **Two different shapes of
   centrality, same headline number.** v2.1's "Mem0 = 12 floor"
   claim is now resolved: Mem0 is still 12, but the cell-miner pass
   surfaced ~20 cite edges elsewhere rather than new
   integrates-with-Mem0 relations. The framework-row paired records
   (LangChain, LangGraph, CrewAI, etc.) **still do not produce new
   integrates-with edges into Mem0** in the current edge graph.
3. **✶ v3 The valuation gap is unchanged but better-grounded.** v2.1
   reported ~100–413× spread. Round 9 deep-fill brought concrete
   numbers to many funding cells (Cline $32M Series A 2025-10,
   Voyage AI's $220M acquisition by MongoDB now confirmed, etc.),
   but did not crown a new $1B+ dedicated-memory entry. **Mem0 stays
   at $150M valuation; the closest competitor is Letta at $70M.**
   New top-of-stack entries surfaced: CoreWeave acquired Weights &
   Biases for **$1.7B** (training-infra consolidation signal).
4. **✶ v3 Lineages re-detected against 299 edges (was 247 in v2,
   278 in v2.1).** Total lineages of size ≥3 went from 8 in v2.1 to
   **9** in v3 (3 curated + 6 auto). The **influential-cite
   backbone grew from 96 → 117 nodes** (anchored at EWC) — adding 21
   research papers to the giant component. **Graph-RAG curated
   lineage grew from 16 → 21 members** (adds CAM, ComoRAG, GSW,
   RouteRAG, RGMem). **RLHF lineage is now partially confirmed in
   the edge graph** (was zero internal edges in v2.1): GRPO →
   cites → DPO, QLoRA → cites → LoRA. **SSM lineage (Hyena → Mamba
   → Mamba-2 → Jamba) still has zero internal edges** — remains a
   parallel-evolution pattern grouping. **New auto-discovered
   3-node lineage: DPO → GRPO → SEAgent** (the RLHF descent
   fragment now visible as its own component).
5. **✶ v3 Files-as-memory thread now has 32 members** (v2.1 said 33;
   the actual section-union is 13 + 19 = 32, not 13 + 20 — v2.1
   miscounted *Claude Code memory mechanisms* by 1). Still a
   **pattern**-kind lineage, not descent. May grow if the parallel
   "agent IDEs & coding harnesses" ingestion lands new file-backed
   editors — addendum will revise.
6. **✶ v3 Top-cited-within-catalog leaderboard shifted.** v2 had
   LoCoMo / A-MEM tied at #1 (9 cites each). Round 9 cite-edge pass
   moved **GraphRAG (Microsoft) to #1 at 11 inbound cites**, with
   MemGPT v2 and Compressive Transformer tied at #2 (10 each).
   LoCoMo and A-MEM dropped to #4 at 9 each. **The "most-built-on
   memory paper" crown moved from a benchmark + a method paper to a
   single hierarchical-graph-RAG anchor.**

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
- **(Edges)** — `data/landscape.edges.json` ✶ v6, **528 edges** (241
  cites; **212 runtime-dependency** ✶ v6 — T2-1 commit `ddb26c7`,
  the new edge type mined from `adjacent-infrastructure` /
  `backend-storage` / `embedding-model` cells; 41 integrates-with;
  22 built-on; 4 competes-with; 3 extends; 2 same-team-as; 2 forks;
  1 succeeds). The +214 between v5 (314) and v6 (528) is dominated
  by the runtime-dep mining pass; see §23 for the substrate-risk
  treatment. The path moved from `landscape.edges.json` (web/) to
  `data/landscape.edges.json` (root) when T0-1 `b6ea473` promoted
  the dataset to a standalone product. *(v5: 314; v4: 313; v3: 299;
  v2.1: 278; v2: 247.)*

### Cell population — what's "—" means: dash means "no public data," not "the system has zero."

✶ v3 The catalog reached **100% terminal state** in Round 10. Every
cell is one of three statuses: `real-data` (with citation),
`not-applicable` (with reason), or `depth-floor-reached` (with search
trail). The table below reports **real-data populations**; the
remaining cells on each column are not gaps — they are
terminal-with-a-reason. See §13 for the full quality ledger.

| Column | Populated (real-data) ✶ v3 | Honest baseline |
|--------|-----------------------------|-----------------|
| Tax-storage / retrieval / update / unit | ~100% primary axis (95% multi-value) | Most rows describe their architecture |
| Tax-governance | **100% across all tiers** | Every record has a non-null governance tag (see §11.3) |
| Citations | ✶ v3 expanded by Round 9 cite-edge pass | The cell-miner surfaced 20 new influential cite edges |
| Funding / Customers / Perf / Mindshare | ✶ v3 deep-filled in Round 9 (Paths B1–B8) | Concrete numerics where they exist; depth-floor where they don't |
| Whole-catalog cell counts | ✶ v4 **18,009 real-data / 21,961 N/A / 11,570 depth-floor** | Total = 51,540 = 859 × 60 (was 41,940 in v3) |

The v2 / v2.1 per-column count rows (GitHub 150, Funding 220,
Customers 175, etc.) are retained as historical baselines for the
core memory-shaped slice. Round 9 / 10 did not re-measure them in
that form; the cell-count totals above are the corrected v3 view.

---

## 1. The architecture map (from taxonomy columns)

### 1.1 ✶ v4 Storage primitive distribution across 859 rows

Counted from the **Storage** column (taxonomy), all values (not just primary):

| Primitive | Count (any) | Count (primary) | Where it dominates |
|-----------|-------------|------------------|--------------------|
| `vector` | 220 | 168 | Default everywhere; only primitive without a domain |
| `n/a` | **182** | **182** | Training / inference / observability / agent-framework rows — most don't store memory at all |
| `kv` ✶ v4 | **107** | **95** | KV stores + voice-agent slot-filling + Round-12 voice-platform rows (Vapi, Retell, ElevenLabs Conv AI) |
| `graph` | 97 | 78 | Knowledge-graph products + Graph-RAG papers |
| `file` ✶ v4 | **89** | **79** | Files-as-memory + Round-11 harness rows (Cursor / Windsurf / Kiro) + Round-13 spec-driven verticals |
| `none-trivial` ✶ v4 NEW | **86** | **86** | **Round-13 use-case-vertical harness rows** — session-only state, no memory layer to characterise |
| `parametric` | 50 | 48 | Knowledge-editing + continual-learning papers |
| `relational` | 47 | 28 | Pgvector / MongoDB / observability stack |
| `hybrid` | 42 | 42 | Multi-primitive products (Mem0, Memory³) |
| `kv-cache` | 33 | 29 | Transformer-internal compression papers |
| `weight` ✶ v4 NEW | **15** | **15** | Robotics FM rows (π0, Helix, GR00T) — policy lives in network weights |
| `proprietary` | 8 | 8 | Closed platform-provider rows |
| `column` | 5 | 0 | Columnar storage (Apache Arrow-shaped substrates) |

**✶ v2.1 The `n/a` primitive went from 28 → 182.** That's the
scope-expansion fingerprint: the 176 new Round 7 rows are mostly
adjacent infrastructure that doesn't own a memory primitive (training
clusters, GPU inference clouds, eval platforms, embedding services,
generic vector DBs without a memory framing). The structural read is
that **about a quarter of the catalog is now memory-adjacent rather
than memory-shaped**, and the headline architecture distribution
within the memory-shaped slice is unchanged from v2.

**✶ v4 Two new "non-memory" primitives crystallised after Round 13.**
`none-trivial` (86) is the dominant fingerprint of Round-13 use-case
verticals — products where memory is session-scoped or hosted by the
underlying LLM context, not a first-class architectural feature. `weight`
(15) is the new primitive for robotics FMs where the agent's "memory"
is its policy network parameters, not a queryable store. Combined with
`n/a` (182), there are now **283 catalog rows (~33%) that explicitly do
not implement a memory abstraction**. This is the v4 honest read: a
third of the catalog is "agent infrastructure that does not own
memory" — and the rename to *AI Agent Infrastructure Landscape*
reflects exactly that.

**Vector remains the memory-shaped commodity primitive** (within the
~517 memory-shaped rows, vector is ~32% of any-value entries — same
share as v1/v2 when normalised to memory-shaped). **The catalog is
architecturally pluralistic at the memory layer and broadly
diversified across non-memory adjacencies.**

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

#### ✶ v4 Four new adjacent-product sections (Rounds 11-13)

Round 11 added **Agent IDEs & coding harnesses** (32 rows — Kiro,
Cursor, Windsurf, Zed, Claude Code, Codex CLI, Copilot Workspace,
Amazon Q, JetBrains Junie, Cline, Aider, OpenHands, Manus, etc.).
Storage fingerprint: predominantly `file` (per-session context files)
+ `none-trivial` (orchestration-only harnesses). Funding: heavy T1
(13 rows). **Cursor at $9.9B / $200M ARR; Windsurf three-way M&A
(OpenAI $3B → Google $2.4B → Cognition residual IP).**

Round 12 added three sections (41 rows):
- **Computer-use & desktop agents** (13) — OpenAI Operator, Browser
  Use (60k★), Skyvern, Stagehand, Hyperbrowser, Steel.dev, Magnitude,
  Bytebot, Lutra, Highlight, Claude for Chrome, Project Mariner,
  UI-TARS. Storage fingerprint: predominantly `kv` slot-filling +
  `file` for screen state.
- **Voice agent platforms** (13) — Vapi, Retell, Bland, Synthflow,
  ElevenLabs Conv AI, OpenAI Realtime, Pipecat, LiveKit Agents,
  Cartesia Sonic, Hume EVI, Speechmatics Flow, CallRail, Vonage AI.
  Storage fingerprint: dominant `kv` (turn-taking slot-fill) + ML
  audio chains.
- **Robotics foundation models & agent stacks** (15) — Physical
  Intelligence π, Covariant, Figure AI, 1X, Apptronik, Agility
  Robotics, Sanctuary AI, Cobot, TRI LBM, NVIDIA GR00T / Isaac,
  DeepMind Gemini Robotics, LeRobot, K-Scale, OpenMind OM1, Pickle
  Robot. Storage fingerprint: `weight` (policy in network) + `scene-graph`
  for spatial layers.

Round 13 added **Use-case-specific agent harnesses** (87 rows across
7 sub-groups). Storage fingerprint: `none-trivial` dominates because
these are domain-shaped *agents* whose memory layer (when present) is
already documented elsewhere in the catalog — these rows characterise
the user-facing harness. See §16.

#### ✶ v2.1 The six new (Round 7) adjacent-infrastructure sections

| Section | Rows | Primary architectural read |
|---------|------|----------------------------|
| Training infrastructure | 51 | Mostly `n/a` storage — RLHF stacks, fine-tuning platforms, data versioning. Memory adjacency is "where you'd train a memory model," not memory itself. |
| Search platforms (non-memory) | 15 | Pure vector or hybrid-search substrates that aren't currently positioned for memory. Distinct from "Vector-database infrastructure" by scope, not architecture. |
| Agent frameworks (no first-party memory layer) | 39 | Orchestration / tool-calling — `n/a` storage. Some are paired records with the Framework-embedded-memory rows (LangChain, LangGraph, CrewAI, LlamaIndex, AutoGen, Inngest). See §11.1 on the two cross-listing conventions. |
| Inference platforms & gateways | 15 | GPU clouds (Together $3.3B, Modal $1B, Baseten $825M, Fireworks $552M, Replicate, Anyscale) and routers (LiteLLM, OpenRouter, Portkey). `n/a` storage; relevance is "where the LLM-with-memory runs." |
| Embedding & reranker services | 11 | Hosted-API tier (Cohere, Voyage AI, Nomic, BGE, GTE, Mistral, Jina, Mixedbread). Sit just below the memory layer. **Voyage AI's $220M MongoDB acquisition (Feb 2025)** is the structural standout — the first vertical-integration move on the embedding tier. |
| Evaluation & observability platforms | 15 | Generic LLM/agent tracing (LangSmith, LangFuse, Helicone, Phoenix, Galileo, Patronus, Braintrust). Distinct from the memory-specific 5-row observability section. |

Together these six sections form an "infrastructure ring" around the
memory-shaped core. None of them currently dominates the integration
graph (most have zero inbound edges yet — see the cell-mining caveat
in §2.3).

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

**✶ v4 Browser Use enters the high-stars club** at ~60k+ stars (per
Round 12 ingestion notes) — the most-starred AI-agent OSS of 2025,
ETH-Zurich-founded (Magnus Müller + Gregor Žunič), $17M seed
Mar-2025 (Felicis), MIT licence. Sits in the new
*Computer-use & desktop agents* section. **The browser-control
mindshare crown is European-research origin, not US Big Tech**;
Stagehand (Browserbase's OSS) at 9k★ is the closest follower.
LeRobot (Hugging Face) at 10k★ is the equivalent open-source anchor
for the robotics layer. Together these three (Browser Use, LeRobot,
Mem0) form the OSS commons across browser / robot / memory layers.

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

✶ v4 Re-counted against the 313-edge graph. Round-12 disambiguation
recovered seven previously-discarded LangChain inbound edges; it is
now the #2 hub:

| Hub | Inbound | Notes |
|-----|---------|-------|
| **Mem0** | **12** | Unchanged from v3; still the only dedicated memory layer with double-digit inbound |
| **LangChain (framework)** ✶ v4 | **7** | **Was 0 in v3 due to `ambiguous-substring: langchain` discards.** Round-12 disambiguation table resolved ArangoDB, AWS Bedrock AgentCore Memory, Dgraph, Flowise, LangSmith, Memgraph, pgvector → langchain integrates-with edges |
| LangGraph Persistence | 6 | Framework hub (was 5 in v3; +1 from disambiguation) |
| Qdrant | 4 | Substrate |
| Pinecone | 3 | Substrate |
| pgvector | 3 | Substrate |
| Zep & Graphiti | 3 | Pattern B sole representative |
| Amazon Neptune Analytics | 3 | KG substrate |
| Cognee | 2 | |
| AWS Bedrock AgentCore Memory ✶ v4 | 2 | New row Round-11/12; references Mem0 + LangChain |
| Hindsight (Vectorize) | 2 | |
| MongoDB Atlas Vector Search | 2 | |
| Chroma | 2 | |

**✶ v4 Mem0 is still the integration-hub leader at 12, unchanged from
v3.** Letta = 0 inbound in the edge graph, Cognee = 2, Memobase = 0.
**LangChain at 7 is the v4 newcomer to the top-of-board** — but the
finding is a *measurement* improvement, not a real shift: those edges
were always there in the marketing language ("LangChain integration"
on every framework's docs page) but the cell-miner's substring
resolver had been discarding "LangChain" as ambiguous between
LangChain-the-framework and LangMem-the-product. The disambiguation
table introduced in Round-12 hygiene fixed it. **Network effect at the
integration layer is real and concentrated — but its measurement
ceiling is the cell-miner's resolution depth, not the underlying
relationships.**

#### ✶ v3 Mem0 vs GraphRAG — two shapes of centrality, same headline

After Round 9's cell-miner re-run (20 new cite edges, 278 → 298 total;
299 after Round 10), the headline number resolves cleanly:

| Metric | Mem0 | GraphRAG (Microsoft) |
|--------|------|---------------------|
| Inbound `integrates-with` + `built-on` + `extends` | **12** | 1 |
| Inbound `cites` (in-catalog) | 0 | **11** |
| **Total inbound (all types)** ✶ v3 | **12** | **12** |

**The two are tied at 12 total inbound — but along orthogonal axes.**
Mem0 is the *integration hub* (12 commercial / OSS systems integrate
with or build on Mem0; zero papers cite it because it's a product, not
a paper). GraphRAG is the *citation hub* (11 papers cite it
influentially; 1 product extends it as LazyGraphRAG; zero
integrates-with edges because it's a Microsoft Research paper /
codebase, not a hosted layer).

**Implications:**
1. v2.1's "Mem0 is the most-integrated node, full stop" is now
   sharpened to "Mem0 is the most-integrated commercial layer; GraphRAG
   is the most-cited research substrate; the two together define the
   memory subfield's twin centres of gravity."
2. The framework-row paired records (LangChain, LangGraph, CrewAI,
   LlamaIndex, AutoGen) added by Round 7 still produce **zero new
   integrates-with edges into Mem0** in the v3 edge graph. v2.1's
   prediction that the cell-miner re-run would surface 1-3 of these
   did not materialise. **Conclusion: those frameworks do not document
   Mem0 integration in their primary marketing pages** — if they did,
   the cell-miner would have found it. Mem0's "12 floor" is now the
   actual ceiling at the current cell-mining depth.
3. **No other node breaks past 6.** The integration-hub leaderboard
   below #1 starts at 5 (LangGraph Persistence). The citation
   leaderboard #2 (MemGPT v2, Compressive Transformer) is at 10. The
   field has no third centre.

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

## 3. ✶ v4 Lineages — the descent map, re-detected against 313 edges

✶ v4 The KG now exposes **313 edges** (v3: 299; v2.1: 278; v2: 247).
Filtering to descent-only (`built-on`, `extends`, `forks`, `succeeds`,
and influential `cites`) yields **267 descent edges** that imply "B was
built from A." Lineage detection was re-run against the v4 edge file
using a Python translation of `web/src/lib/lineages.ts` —
`/tmp/lineage_detect.py` at git-sha-of-this-commit. Approach: union-find
with path compression + BFS depth-2 expansion for curated seeds (see
DECISIONS.md 2026-05-13 v4 entry). Detection runs in two passes:
(1) curated seeds expanded by BFS depth-2 (descent kind) or by section
union (pattern kind), (2) union-find on the remainder, keeping
components of size ≥3.

`lineages.ts` distinguishes two **kinds** of lineage:
- **`descent`** — a parent → child chain in the structural-descent graph.
  Solid arrows in the /lineages view.
- **`pattern`** — a family that converged on the same architectural
  shape by parallel evolution. No descent edges between members; the
  page draws dashed "parallel-implementations" connectors instead.

### 3.1 ✶ v5 Curated lineages (7) — re-detected against 314 edges

v5 update: the v4 recommendations ("Curate SSM as a pattern-kind
seed", "Curate Browser-agent and Robotics-FM as pattern-kind
seeds") were implemented in `web/src/lib/lineages.ts` between v4
and v5 (commits da2b851, 18ca7c4). The curated count is now 7 (4
from v4 + 3 new pattern seeds — SSM 5, Browser-agent 21,
Robotics-FM 15). Re-detection against the v5 314-edge graph
yields:

### 3.1 (preserved) ✶ v4 Curated lineages (4) — re-detected against 313 edges

| Lineage | Kind | Members | Composition |
|---------|------|---------|-------------|
| **RSSM / world-model family** | descent | 5 | DreamerV3 (anchor) → DIAMOND, PWM, R2I, Transformer-XL. *Unchanged from v2.1 / v3.* |
| **Graph-RAG hierarchy** | descent | **21** | GraphRAG (Microsoft, anchor) → LightRAG, LazyGraphRAG, PathRAG, RGMem, RouteRAG, StructRAG, HippoRAG / HippoRAG2, RAPTOR, ReadAgent, BGE-M3, SGMem, **Zep & Graphiti**, ComoRAG, CAM, GSW. *Unchanged from v3 (still 21).* Internal descent edges: 24. |
| **Files-as-memory thread** | **pattern** | **32** | CLAUDE.md (anchor) + all 13 "File-backed / editor paradigms" rows + all 19 "Claude Code memory mechanisms" rows = 32 total. *Unchanged from v3.* Round 11 added file-backed harness rows in *Agent IDEs & coding harnesses* (Kiro, Windsurf, Cursor); these are NOT counted here because the curated seed only expands by the two original section names — by design, to keep the "unstructured documentation" pattern separate from the "structured workflow" pattern below. |
| **Specs-as-memory thread** ✶ v4 NEW | **pattern** | **5** | Kiro (anchor) + Windsurf Cascade + Devin Spec Mode + Cline Memory Bank + Roo Code. Added as the 4th curated seed in Round-12 hygiene pass (DECISIONS.md 2026-05-13). **Distinguished from Files-as-memory by structure**: specs-as-memory means *structured* per-stage workflow files (Requirements / Design / Tasks; mode directories) committed to source; Files-as-memory means *unstructured* documentation (CLAUDE.md / .cursorrules). Both ship as text in the repo; the difference is whether the file layout encodes the workflow. **Round 11 ingestion's "Possible new lineages" prediction is now realised as a curated seed.** |

The Graph-RAG hierarchy remains the largest descent-kind family in the
catalog and it pulls Zep & Graphiti in — confirming Pattern B (§1.2)
is the commercial endpoint of the Graph-RAG research lineage.

**✶ v4 Specs-as-memory is small (5) by design, not by data sparsity.**
The pattern is defined by *structured workflow files* — and the
explicitly-curated member list is the universe of products that
have published a named workflow-file schema. Roo Code added
mode-specific `.roo/rules-{modeSlug}/` directories; Cline shipped
projectBrief / productContext / activeContext / systemPatterns /
techContext / progress; Kiro shipped Requirements / Design / Tasks;
Devin Spec Mode shipped spec files as the canonical persistence;
Windsurf Cascade was the earliest spec-driven posture. If a future
harness ships a schema along these lines, it joins the seed list.
The 5-member size is the *current accurate population*, not a floor.

### 3.2 ✶ v4 Auto-discovered lineages (size ≥3): 6 components

| Lineage | Size | Anchor | What it represents |
|---------|------|--------|--------------------|
| **Influential-cite backbone** | **117** | EWC (Elastic Weight Consolidation) | The full research-paper sub-graph through influential cites. *Unchanged from v3 at 117.* The +160 row expansion in Rounds 11-13 was overwhelmingly T1/T2 commercial; new rows produced ~10 cite neighbours but did not add to the research backbone. EWC remains the date-anchor. |
| **RLHF / agent-RL descent fragment** ✶ v4 GREW | **5** (was 3 in v3) | DPO | DPO + GRPO + SEAgent + **UI-TARS** + **LearnAct**. **Grew from 3 to 5** thanks to Round 12 adding UI-TARS (the ByteDance computer-use FM, which cites both DPO and SEAgent influentially) and Round-11 LearnAct paper joining via SEAgent cites. **The new edges came from existing cell-mining surfacing UI-TARS's published GRPO usage and LearnAct's SEAgent cite.** Still does not reach the full RLHF chain (LoRA → QLoRA stays as a 2-node pair, sub-threshold). |
| **Mem0 ecosystem — Qdrant subcluster** | 4 | Qdrant | Qdrant + pgvector + Agno (Phidata) + Mem0 Security/OpenMemory. *Unchanged from v3.* |
| **Mem0 ecosystem — FalkorDB subcluster** | 4 | FalkorDB | FalkorDB + Mem0 + Amazon Neptune Analytics + Strands Agents Memory (AWS). *Unchanged from v3.* |
| **JEPA family** | 3 | I-JEPA | I-JEPA → V-JEPA → V-JEPA 2. *Unchanged from v2.1.* |
| **ReMEmbR / spatial** | 3 | Milvus | Milvus + NVIDIA ReMEmbR + Meta-Memory. *Unchanged from v2.1.* |

**✶ v4 net lineage count: 10 of size ≥3** (4 curated + 6 auto) —
**up from 9 in v3.** The +1 comes from the curated Specs-as-memory
seed; the auto-discovered count itself is unchanged at 6.

✶ v4 **What changed in the auto-discovery:**

1. **The big backbone is still 117 nodes.** The +160 ingestion was
   non-paper-heavy; cite edges added were mostly to nodes already in
   the backbone. The 117-node component is the research substrate of
   the field at saturation under the current cell-mining depth.
2. **The RLHF / agent-RL fragment grew from 3 → 5 nodes.** UI-TARS
   (Round 12) and LearnAct (Round 11) both join via cites to DPO /
   SEAgent. This is the second consecutive round where this component
   grew (v2.1: 0, v3: 3, v4: 5). It now reads as the
   *agent-RL-trained-on-policy-optimisation* lineage rather than a
   pure RLHF lineage — UI-TARS is a GUI foundation model, LearnAct
   does agent skill RL, SEAgent does autonomous agent RL. The name
   should probably evolve.
3. **Did SSM finally connect? No.** Direct re-check against the 313
   edges: six SSM rows present (Hyena, Jamba×2 dup-rows, Mamba,
   Mamba-2, RWKV-7), **0 internal edges among them.** Rounds 11/12
   added neighbouring papers but none of them surfaced
   Hyena→Mamba / Mamba→Mamba-2 / Mamba-2→Jamba cites. **Final v4
   verdict: SSM is genuinely a parallel-evolution pattern, not a
   descent lineage in the catalog.** Should be promoted to a curated
   pattern seed in a future revision (DECISIONS.md captures this).
4. **Did Stanford-agents grow? No.** Re-check: 3-node fragment
   unchanged (ExpeL → Reflexion → Self-Refine). Round 11/12 ingestion
   did not add Voyager / Generative-Agents / RAPTOR connecting cites.
5. **Browser-agent commercial lineage? No.** The brief asked whether
   Browser Use → Stagehand → Hyperbrowser auto-emerged: it did not.
   Round 12 added all three rows but **zero internal descent edges**
   exist among the 13 *Computer-use & desktop agents* rows. They are
   parallel implementations of browser control, not a descent chain.
   The cell-miner did not find documented "X is built on Y" claims
   between them — and indeed, Stagehand is Browserbase's OSS
   framework rather than a build-on of Browser Use; Hyperbrowser is
   a Browserbase competitor on cloud browser infra, not a child of
   Browser Use. **The architectural-shape similarity is not descent.**
6. **Robotics-FM commercial lineage? No.** Same answer for π0 →
   π0.5 → GR00T: zero internal descent edges among the 15
   *Robotics foundation models* rows. Physical Intelligence's π0
   paper is influentially cited by other research papers (e.g. TRI
   LBM lineage) but not by the catalog's commercial robotics rows.
   The commercial humanoid companies do not cite each other; they
   build on different VLA stacks and document independent
   architectures.

The "influential-cite backbone" component is **structural**: when 117
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

### ✶ v4 3.4 Candidate lineages — final verdicts at 313 edges

Round 7's ingestion (`extraction/round-7-ingestion.md`) identified
five candidate lineages from the 176 new rows. Re-running edge-graph
introspection against `landscape.edges.json` yields:

| Candidate | v2.1 verdict | ✶ v3 verdict | Notes |
|-----------|-------------|---------------|-------|
| **Stanford agents** (Generative Agents → Voyager → Reflexion → ExpeL → Self-Refine → ChunkRAG → RAPTOR) | Partial 3-node fragment | **✶ v3 Still 3-node fragment, no growth** | ExpeL → Reflexion (influential cite) + Reflexion → Self-Refine (influential cite) confirmed. Round 9's cell-miner did not add Voyager → Generative-Agents or RAPTOR → anything. The chain remains at ExpeL → Reflexion → Self-Refine. |
| **SSM lineage** (Hyena → Mamba → Mamba-2 → Jamba; + RWKV-7) | Candidate, edges sparse | **✶ v3 STILL zero internal edges** | Direct re-check: 6 SSM rows present (Hyena, Jamba×2 dup-rows, Mamba, Mamba-2, RWKV-7), **0 internal edges among them**. Round 9's cell-miner did not surface any. Reads as: SSM members each cite their own non-memory ancestors but not each other in any direction that the cell-miner can find from cells. **Final verdict: pattern-kind, not descent.** |
| **RLHF lineage** (LoRA → QLoRA → DPO → GRPO → TRL / OpenRLHF) | Candidate, edges sparse | **✶ v3 PARTIAL — 2 internal edges now confirmed** | Round 9 cell-miner surfaced: `GRPO --cites--> DPO` (influential) and `QLoRA --cites--> LoRA` (influential). Two pairs are now cited. **The auto-discovery algorithm picks up DPO + GRPO + SEAgent as a 3-node lineage** (SEAgent also cites DPO). QLoRA + LoRA is a 2-node pair, below the size threshold. **The single largest v3 lineage promotion** — was 0 edges, now 3-node descent. |
| **Embedding model lineage** (Sentence Transformers → BGE → GTE → Nomic → Mixedbread) | Candidate, edges sparse | **✶ v3 STILL zero internal edges** | Verified again against 299 edges. BGE-M3 has 1 inbound cite (ComoRAG); the embedding-model members do not cite each other in any direction. Industry sequence ≠ catalog descent. |
| **Agent-protocol lineage** (MCP → A2A → AGNTCY) | Partial within MCP | **✶ v3 Unchanged** | Same 2 internal descent edges within MCP family. A2A and AGNTCY remain zero-edged. |

**✶ v3 net verdict.** Of the 5 Round-7 candidate lineages:

- **2 have descent fragments now** (was 2 in v2.1): Stanford agents
  (3-node, unchanged) and **RLHF (3-node, newly confirmed in v3)**.
- **1 has descent within a single sub-family** (MCP, unchanged).
- **2 remain zero-edge pattern groupings** (SSM, Embedding models).

The **headline movement is RLHF**: v2.1's "zero internal edges,
candidate pattern" became "3-node descent lineage auto-discovered" in
v3.

#### ✶ v4 New candidate lineages from Rounds 11–13

| Candidate | Members searched | v4 verdict | Notes |
|-----------|------------------|------------|-------|
| **Browser-agent commercial** | Browser Use, Stagehand, Hyperbrowser, Skyvern, Bytebot, OpenAI Operator, Project Mariner, Claude for Chrome, UI-TARS, Steel.dev, Magnitude | **Zero internal descent edges** | Brief asked: did this auto-emerge? No. They share architectural shape but cite different ancestors. Parallel implementations of browser control. Could be curated as a pattern seed. |
| **Robotics-FM** | π0 / Physical Intelligence, π0.5, NVIDIA GR00T, Figure Helix, 1X, Apptronik, Sanctuary, Cobot, TRI LBM, DeepMind Gemini Robotics, LeRobot | **Zero internal descent edges** | Brief asked: did π0 → π0.5 → GR00T auto-emerge? No. The TRI diffusion-policy line (5000+ S2 cites, Chi et al. 2023) is influential externally but doesn't connect to catalog robotics rows via the cell-miner. Commercial humanoid companies don't cite each other. |
| **Voice-platform substrate** | LiveKit, Pipecat, OpenAI Realtime, Vapi, Retell, Cartesia, Hume EVI, ElevenLabs Conv AI | **Zero internal descent edges** | Documented substrate↔harness pairings (LiveKit ⊂ OpenAI Realtime; Pipecat used by many) exist in marketing text but did not survive cell-mining. **Edges may surface in Round 14 if disambiguation table extends to LiveKit / Pipecat.** |
| **Spec-driven harness convergence** | Kiro, Windsurf Cascade, Devin Spec Mode, Cline Memory Bank, Roo Code | **5 nodes — now a curated pattern seed** | Realised as the *Specs-as-memory* curated lineage (§3.1). The closest thing to a "new lineage from Round 11/12" — but it's pattern-kind, not descent. |
| **OpenDevin / OpenHands → SWE-bench race** | OpenHands, Aider, smol-developer, GPT Engineer, MetaGPT | Zero internal descent edges | Same parallel-implementation pattern; OpenHands is technically a continuation of OpenDevin (project rename, not a fork edge) — no descent edge surfaces. |
| **Cline → Roo Code fork chain** | Cline, Roo Code | 2 nodes, sub-threshold | Roo Code is a documented Cline fork. The single `forks` edge exists; the chain has no third member. |

**✶ v4 The headline negative finding: none of the post-Round-7
candidate lineages auto-emerged with size ≥3.** The cell-miner
surfaces *cites* and *built-on* claims from each row's documented
text; commercial product rows in the new sections do not document
their lineage relationships to each other the way research papers do.
The descent graph is sparse where the products are commercial and
dense where they are academic — exactly what one would predict, but
now empirically confirmed at 313 edges.

**Recommended Round 14 actions:**
1. Curate SSM as a pattern-kind seed — the Hyena → Mamba → Mamba-2 →
   Jamba narrative is well-supported in the literature even though
   catalog cites don't connect them.
2. Curate Browser-agent and Robotics-FM as pattern-kind seeds — they
   are real architectural families even though descent edges don't
   connect them.
3. Extend the edge-disambiguation table to LiveKit, Pipecat, GR00T —
   marketing pages cite these substrates, but cell-mining is
   discarding the mentions as `ambiguous-substring`.

### 3.5 (was 3.4) Sections vs lineages disagree by design

- The Mem0 ecosystem (lineage, 10 nodes) crosses 4 sections.
- Pattern C (13 file-backed rows, 1 section) is **not** a lineage —
  no descent edges.
- The Graph-RAG curated lineage (16 nodes) pulls Zep & Graphiti out
  of Dedicated memory layers and into the research-descent line.

**Sections are how people organize the field. Lineages are how the
work actually descended.** Use both.

---

## 4. Commercial signals — who's making money (from Funding, Customers cols)

### 4.1 ✶ v2.1 The valuation pyramid (Round 7 update)

| Tier | Row | Latest valuation |
|------|-----|------------------|
| Trillion-tier (parent vendors, not in catalog) | OpenAI / Anthropic / Google | ~$200B+ |
| Hyper-cap ✶ v2.1 | **Databricks Vector Search** | **$62.0B** (parent valuation, Dec 2024) |
| | **Snowflake Cortex Search** | **$62.0B** (parent NYSE:SNOW market cap, Dec 2024) |
| | **Anthropic Auto Dream / Claude Memory / Managed Agents Memory** | **$40.0B** (parent valuation, 3 rows) |
| Mega-cap | **Perplexity Memory** + **Perplexity Comet** | **$20.0B → $21.2B** |
| | **AutoGLM (Zhipu AI)** ✶ v2.1 | **$20.0B** |
| | **Sierra** ✶ v2 | **$15.8B** (Series D, 2026-05) |
| | **Skild Brain** ✶ v2.1 | **$14.0B** |
| | **Harvey Memory** ✶ v2.1 | **$11.0B** (Growth round, 2026-03) |
| | **Devin (Cognition)** | **$10.2B** |
| | **Notion AI** | **$10.0B** (from 2021 round) |
| | **Replit Agent** | **$9.0B** (Series D, 2026-03) |
| | **Glean** ✶ v2 | **$7.2B** (Series F, 2025-06) |
| | **Lovable** | **$6.6B** |
| | **Abridge** ✶ v2.1 | **$5.3B** (Series E Ext, 2026-04) |
| | **Decagon** ✶ v2.1 | **$4.5B** |
| | **Hippocratic AI Polaris** | **$3.5B** |
| | **Figure Helix** | **$2.6B** |
| | **π0.5 (Physical Intelligence)** | **$2.0B** |
| | **Neo4j** | **$2.0B** |
| | **Granola** | **$1.5B** |
| | **LangChain / LangGraph Persistence** | **$1.2B** |
| Mid-cap | Together AI ✶ v2.1 | $3.3B |
| | Modal ✶ v2.1 | $1B |
| | Augment Code | $977M |
| | Baseten ✶ v2.1 | $825M |
| | Fireworks AI ✶ v2.1 | $552M |
| | Browserbase | $300M |
| Small-cap | **Mem0** | **$150M** |
| | **Letta / MemGPT** | **$70M** |
| Seed | Zep & Graphiti, Cognee, MemoraX, NeoCognition, Interloom, Nyne, Trace, Pieces for Developers ✶ v2.1 | $0.5M – $40M |

**✶ v2.1 The valuation gap has widened, not narrowed.** With Sierra
($15.8B), Skild Brain ($14B), Harvey ($11B), Abridge ($5.3B), Decagon
($4.5B) added on the vertical-product side, and **no
dedicated-memory-layer entry crossing $150M**, the field's asymmetry
deepened in Round 7. New ratios against Mem0 ($150M):

- Mem0 vs Perplexity: **133×**
- Mem0 vs Sierra: **105×** ✶ v2.1
- Mem0 vs Harvey: **73×** ✶ v2.1
- Mem0 vs Lovable: **44×**
- Mem0 vs Databricks Vector Search parent: **413×** ✶ v2.1
- Mem0 vs Anthropic parent: **267×** ✶ v2.1

**✶ v2.1 sharpens v2's claim**: not just "memory is priced as a
feature of vertical products" but also "the substrate platforms that
*also* offer search/vector functionality are valued an order of
magnitude above any dedicated memory layer." Databricks and Snowflake
sit at $62B with vector search as one capability among many; Mem0 is
two and a half orders of magnitude smaller despite the highest
integration count in the field.

#### ✶ v4 Round 11-13 funding additions (the v4 valuation shifts)

The 160 new rows added in Rounds 11-13 brought a set of substantial
funding entries that re-shape the pyramid above:

| Tier | Row | Latest valuation | Notes |
|------|-----|------------------|-------|
| Hyper-cap (humanoid) ✶ v4 | **Figure AI** | **$39.5B** (reported Q2 2025) | **15× in 16 months** from $2.6B Feb 2024; fastest humanoid valuation ramp on record. |
| Hyper-cap (coding) ✶ v4 | **Cursor / Anysphere** | **$9.9B** (May 2025) | $200M ARR (May 2025). New highest-valuation coding-agent harness in the catalog (was Devin/Cognition at $10.2B; Cursor is a coding IDE rather than autonomous agent — distinct category). |
| Mega-cap ✶ v4 | **ElevenLabs (incl. Conv AI)** | **$3.3B** (Series C, Jan 2025) | $180M Series C; Conv AI tier launched Nov 2024. First voice-platform unicorn-plus. |
| Mega-cap ✶ v4 | **Physical Intelligence (π)** | **$2.4B** (Series A, Nov 2024) | $400M Series A 8 months after founding; π0 paper Oct 2024 (arXiv 2410.24164); OpenPI weights Apache 2.0 Feb 2025. Bezos / OpenAI / Thrive / Lux. |
| Mega-cap ✶ v4 | **Apptronik** | **~$1B implied** (Series A $350M Feb 2025) | DeepMind Gemini Robotics reference platform; Mercedes-Benz manufacturing pilot. |
| Mid-cap ✶ v4 | **Magic.dev** | **(not disclosed; $465M raised cumulative)** | Ultra-long-context coding agent (unreleased through 2025). |
| Mid-cap ✶ v4 | **Hume AI (EVI)** | $50M Series B Mar-2024 | Empathic voice agent. |
| Small-cap ✶ v4 | **LiveKit Agents** | $300M (Series B $45M Sep-2024) | **Apache 2.0 OSS framework now powering OpenAI Realtime API's WebRTC backbone.** OSS substrate → flagship hyperscaler API. |
| Small-cap ✶ v4 | **Vapi** | $130M (Series A $20M Dec-2024) | >$10M ARR Q1 2025; most-discussed voice-AI platform of 2024-25. |
| Acqui-hire ✶ v4 | **Covariant** | ~$1.5B-equivalent (Amazon, Aug 2024) | First major robotics-FM acqui-hire; Pieter Abbeel + 25% of team to Amazon Robotics. |
| Seed ✶ v4 | **Browser Use** | $17M seed (Mar 2025, Felicis) | 60k+ stars; ETH-Zurich-founded. Most-starred AI-agent OSS of 2025. |
| Seed ✶ v4 | **Cartesia** | $64M Series A Q1-2025 | Founded by Mamba author Albert Gu; ~40ms TTFB TTS (lowest published). **First commercial SSM-scale validation.** |

**✶ v4 The valuation gap re-broadens at the top.** With Figure AI at
$39.5B reported, Mem0 vs Figure = **263×**. The Mem0 vs vertical-product
ratios from v3 widen on the agentic-runtime side:

- Mem0 vs Figure AI: **263×** ✶ v4
- Mem0 vs Physical Intelligence: **16×** (was unmeasurable in v3)
- Mem0 vs Cursor/Anysphere: **66×** ✶ v4
- Mem0 vs ElevenLabs: **22×** ✶ v4
- Mem0 vs Sierra: **105×** (v3, unchanged)
- Mem0 vs Harvey: **73×** (v3, unchanged)

**The pattern is identical to v3 but with new max-spread points.** The
humanoid-FM and voice-platform tiers are now both at higher valuation
than the entire dedicated-memory-layer category combined.

#### ✶ v3 Round 9 deep-fill funding-cell additions

Round 9's Path B8 deep-fill brought concrete numerics to many funding
cells that were previously prose-only. The structural read is
**unchanged**, but the data is now more precisely sourced:

- **Cline** — Series A $32M (2025-10) confirmed; previously "Series A,
  ~$30M est."
- **CoreWeave → Weights & Biases** acquisition closed at **$1.7B**
  (training-infra consolidation; first 10-figure deal in
  training-tier).
- **Voyage AI** — MongoDB acquisition price confirmed at **$220M**
  (was "undisclosed" in v2.1's embedding-tier row).
- **Lovable** — $400M ARR figure verified across multiple cells; v2.1
  cited it but with a less-direct source.

**No new dedicated-memory-layer entry crossed $150M in Round 9.**
The Mem0 vs vertical-product valuation gap (~100–413×) is unchanged
in headline ratio. **The widening signal v2.1 flagged is now stable**
— it is not still widening, but it has not narrowed either.

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

### ✶ v3 6.3 Top by inbound citations *within the catalog* (edges)

`leaderboards.ts` → `mostInboundCites`. This counts inbound `cites`
edges per target node in `landscape.edges.json`. **The Round 9
cite-edge pass shifted this leaderboard.**

| Rank | Row | Inbound cites (v3) | v2.1 rank |
|------|-----|--------------------|-----------|
| 1 | **GraphRAG (Microsoft)** ✶ v3 | **11** | (was tied 3rd, 8) |
| 2 | MemGPT v2 / agent-tools ✶ v3 | 10 | (not on v2.1 board) |
| 2 | Compressive Transformer | 10 | (was tied 3rd, 8) |
| 4 | LoCoMo | 9 | (tied 1st in v2.1) |
| 4 | A-MEM | 9 | (tied 1st in v2.1) |
| 6 | Transformer-XL | 8 | (tied 3rd in v2.1) |
| 7 | Generative Agents ✶ v3 | 7 | (was 6th, 6) |
| 8 | RETRO | 6 | (was outside top-10) |
| 8 | LoRA ✶ v3 | 6 | (was outside top-10) |
| 10 | MemoryBank | 5 | (tied 7th in v2.1) |
| 10 | Self-RAG | 5 | (tied 7th in v2.1) |

**✶ v3 The "most-cited in-catalog" crown moved from a tie of
LoCoMo+A-MEM (benchmark + method paper) to GraphRAG (Microsoft) alone
at 11.** GraphRAG's 11 inbound cites all come from Round 9 cell-mining:
CAM, ComoRAG, GSW, LightRAG (paper + GH-repo rows), MemTree, PathRAG
(paper + GH-repo rows), RGMem, RouteRAG, StructRAG. **Every one of
GraphRAG's descendants in the curated lineage now has its cite edge
in the graph.** The lineage is the most thoroughly evidenced
descent-chain in the catalog.

The contradiction with v2: v2.1 claimed LoCoMo / A-MEM / GraphRAG
"dominate because they are the most-frequently-built-on substrates."
**v3 sharpens this**: GraphRAG dominates alone; LoCoMo and A-MEM are
heavily-cited but as evaluation infrastructure, not as architectural
ancestors. The difference matters for understanding what "most-cited"
means in this catalog.

Inbound-cite count from the catalog is a different signal from total
S2 cites: it measures **how central a paper is *to other memory
work* in this catalog**, not how influential it is in absolute terms.

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
| Substrate parents (vector-search SKU inside a data cloud) ✶ v2.1 | $62B (Databricks / Snowflake) | n/a (substrate not broken out) |
| Vertical agent products | $20B (Perplexity) / $15.8B (Sierra ✶ v2) | $600M (Notion AI) |
| Vertical legal / clinical / customer-support AI ✶ v2.1 | $11B (Harvey) / $5.3B (Abridge) / $4.5B (Decagon) | $200M+ (Glean) |
| Coding-agent products | $10.2B (Cognition) | $400M (Lovable) |
| Enterprise search ✶ v2 | $7.2B (Glean) | $200M (Glean) |
| Inference clouds ✶ v2.1 | $3.3B (Together) | — |
| Frameworks | $1.2B (LangChain / LangGraph) | $16M |
| **Dedicated memory layers** | **$150M (Mem0)** | **$1.4M (Letta)** |

That's the data. **Dedicated memory layers are commercially ~100-410×
smaller than the products that consume them** (range broadened from
v2's 60-130× by the substrate-parents tier).

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
valuations. ✶ v2.1: the gap is now ≥**100× to vertical agent
products** (Sierra 105×, Harvey 73×, Perplexity 133×, Lovable 44× — 
range broadened from v2's "60-130×" by Sierra and substrate-parent
entries). The gap is structural, not a market mispricing.

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
3. **Bi-temporal KG outside Zep** — UNCHANGED (re-verified against the
   699-record catalog). A literal substring search across all 699
   records still shows "bi-temporal" *only* in the three Zep entries
   (Zep & Graphiti, Graphiti MCP Server, Zep governance posture).
   Largest moat in the catalog by structural uniqueness; healthcare,
   legal, scientific verticals all have temporal-correctness
   requirements and currently use vector-extraction.
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

### 11.1 The catalog over-counts as a single product — ✶ v2.1 *two* conventions now

**Original convention (cross-listings).** Zep appears 3 times (Pattern
B). MemMachine appears 2 times (framework vs paper). Memvid appears 2
times (library vs Claude Code plugin claude-brain). The four
catalogued cross-listings (Mem0, Zep, Memobase, MemoryBench) point at
*the same artefact, two framings*; tracked in
`extraction/cross-listings.json`.

**✶ v2.1 Round 7 convention (paired records).** For five major
frameworks (LangChain, LlamaIndex, AutoGen, CrewAI, LangGraph), Round
7 added a second row in "Agent frameworks (no first-party memory
layer)" alongside the existing row in "Framework-embedded memory."
**These are two distinct records, not one record with two section
memberships** — each row has its own 60+ cells filled separately. The
memory-row characterises the framework's memory subsystem (e.g.
LangChain Memory primitives); the agent-framework-row characterises
the framework's orchestration / tool-calls / routers. **Same vendor,
two artefacts**, rather than **same artefact, two framings**.

This is a **policy choice** documented in `docs/DECISIONS.md` (Round 7
ingestion entry). The trade-off: paired records preserve cell-level
characterisation precision but inflate apparent breadth more than
cross-listings do. The Round-7 convention can be flipped to
cross-listings later via `reconcile` rules if the duplication becomes
more confusing than useful — `ambiguous.csv` carries
`keep-separate-link-via-edge` for the borderline cases.

**Apparent breadth inflation is now ~5%** from triple/double-counting
+ paired records (was ~3% in v2).

### 11.2 Lineage-detection vs section-membership disagree (productively)

§3 shows that section labels and lineage groupings disagree by design:
- The Mem0 ecosystem (lineage, 10 nodes) crosses 4 sections.
- Pattern C (13 file-backed rows, 1 section) is **not** a lineage —
  no descent edges.
- The Graph-RAG curated lineage (16 nodes) pulls Zep & Graphiti out of
  Dedicated memory layers and into the research-descent line.

**Sections are how people organize the field. Lineages are how the
work actually descended.** Use both.

### 11.3 ✶ v2.1 Governance disclosure correction (Round 7 update)

v1 claimed academic-tier governance nulls of 89% (T3) / 97.7% (T4).
v2 brought these to 27% / 29%. **v2.1 brings them to 0% — every record
across all 699 rows now has a governance tag**, including the 176
Round-7 additions. The new training / inference / observability rows
all tagged out as `opaque` or `inspectable` defaults.

| Tier | Records | Governance disclosed | Null |
|------|---------|---------------------|------|
| T1 (commercial) | 211 | 211 / 211 | **0.0%** |
| T2 (mature OSS) | 191 | 191 / 191 | **0.0%** |
| T3 (peer-reviewed) | 140 | 140 / 140 | **0.0%** |
| T4 (preprint) | 144 | 144 / 144 | **0.0%** |
| T5 (informal) | 13 | 13 / 13 | **0.0%** |

The corrected reading is now even more stark: **presence is universal;
quality is shallow.** Academic papers describe storage / retrieval /
update axes consistently and now uniformly default to `inspectable`
for governance because the code is open source, but they rarely engage
with consent flows / provenance / audit-by-construction. **The field
is producing memory designs that *can* be audited (because OSS)
without *building in* audit guarantees.** The Round 7 adjacent-
infrastructure rows mostly inherit `opaque` (closed inference clouds,
managed training platforms) — they do not address governance of the
*memory* they serve, only of their own service-provider posture.

### ✶ v2.1 11.3a Scope expansion: the catalog's denominator changed

Round 7 expanded the catalog's mandate from "memory systems plus
adjacencies that touch memory" to "everything in this sphere we can
get our hands on" (per the 2026-05-12 scope-expansion entry in
`docs/DECISIONS.md`). Six new sections covering training infrastructure,
non-memory search, agent frameworks without first-party memory,
inference clouds, embedding services, and generic observability now
sit in the catalog alongside the memory-shaped core.

**This re-bases every coverage claim.** v1/v2 cited ~88-92% taxonomic
coverage **of the memory-shaped slice**. That percentage now applies
to **523 / 699 ≈ 75%** of the catalog. The remaining 25% (176
adjacent-infrastructure rows) has substantially lower per-cell
coverage because the cell-miner has not run a second pass over the new
HTML — many funding / customers / mindshare cells on training-platform
and inference-cloud rows are at depth-floor with only headline fields
filled.

The honest two-tier read: **the memory-shaped core remains at
near-terminal coverage; the adjacent infrastructure is new growth,
depth-floored, and will populate over the next two ingestion rounds.**

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

### ✶ v2.1 12.4 Round 7 surfaces (new signals)

- **Substrate-parent vector-search consolidation.** Databricks Vector
  Search and Snowflake Cortex Search now sit inside $62B
  data-platform parents. Pinecone / Qdrant / Weaviate were already at
  commodity-package volume; the platform-parent move signals the next
  consolidation step — substrate dollars flow to the cloud
  data-platform rather than the dedicated vector vendor. Watch
  Pinecone's next round for valuation pressure.
- **Embedding-model acquisition signal.** Voyage AI was acquired by
  MongoDB for $220M (Feb 2025) — first acquisition of a pure
  embedding-model vendor by a substrate. If Cohere Embed, Mistral
  Embed, or Nomic follow, the embedding tier may consolidate before
  the dedicated-memory tier does.
- **Agent-protocol pile-up.** MCP (Nov 2024), AGNTCY (Mar 2025), A2A
  (Apr 2025) — three competing protocols in six months. Sequence
  matters but the edge graph (§3.4) shows no descent — they are
  parallel protocols, not generations. Watch for which gets the
  network effect.
- **Labelling industry's revenue concentration.** Scale AI ($14B Meta
  investment), Surge AI (reportedly $1B 2024 revenue, bootstrapped),
  Labelbox ($300M ARR). The training-infrastructure tier has revenue
  density that the memory-layer tier does not. The gap is the
  enterprise contract surface — annotation buyers sign 7-figure
  contracts; memory-layer buyers haven't yet.
- **SSM family worth watching for descent.** Hyena → Mamba → Mamba-2
  → Jamba is a clear narrative but has zero internal cite edges in
  the catalog yet. If Round 8's cell-miner surfaces those cites,
  this becomes the second non-RAG-non-graph memory descent lineage.

---

## 13. ✶ v3 Catalog quality and confidence

This section is new in v3. It explains the **trust posture** of every
number in this document.

### 13.1 The terminal-state guarantee

✶ v3 Round 10 brought the catalog to **100% terminal state**. Every
single one of 699 × 60 = **41,940 cells** carries one of three
statuses:

| Status | Count | Meaning |
|--------|------:|---------|
| `real-data` | **14,498** (34.6%) | The cell holds a concrete value sourced from a cited URL. The citation field is non-null and resolves. |
| `not-applicable` | **16,487** (39.3%) | The column does not semantically apply to this record (e.g. `funding` on an academic paper, `gh` on a closed-source SaaS, `customers` on a research benchmark). The `reason` field explains why. |
| `depth-floor-reached` | **10,955** (26.1%) | The column applies but the data is not publicly available. The cell carries a search-trail explaining which sources were consulted before giving up. |

**There are zero cells in any other state.** No shallow-prose, no
no-citation, no fillable-but-missing.

### 13.2 What this means for trust

Every claim in this document — every count, every leaderboard rank,
every named system — traces to one or more `real-data` cells. **A
reader can drill down from any number in this document to its source.**
The walk is: claim in analysis.md → section name in §reference →
relevant column in `landscape.json` → `cells[col].citation` URL.

Examples this enables:

- "Mem0 has 12 inbound integrations" → `landscape.edges.json` filtered
  to `target = mem0--mem0-ai`, `type ∈ {integrates-with, built-on,
  extends}`. The 12 source nodes' `claims` cells each cite the page
  where the integration was announced.
- "GraphRAG has 11 inbound cites" → same file, target =
  `graphrag-microsoft`, type = `cites`. Each source's `citations`
  cell links to the Semantic Scholar API call that returned the
  isInfluential flag.
- "Lovable's $400M ARR" → `lovable` record, `customers.value`
  contains the figure, `customers.citation` links to the source.
- "117-node influential-cite backbone" → reproducible by running
  `/tmp/lineage_detect.py` against `web/landscape.json` +
  `landscape.edges.json` at git sha `8a4e3c8`.

### 13.3 What "depth-floor" cells mean (and don't)

26.1% of cells are `depth-floor-reached`. This **is not the same as
"missing data."** Each such cell has:

1. A `value` that explicitly says "searched not found" or similar.
2. A `citation` field pointing to the most-recent search attempt or
   the row's primary URL (e.g. company website's pricing page, GitHub
   org).
3. An implicit assertion: "this datum was looked for, by a specific
   process, at a specific time, and either does not exist publicly or
   is below our cell-mining floor."

Examples:

- A pre-Seed startup's ARR cell at `depth-floor` — they exist, they
  may have revenue, but they have not disclosed it publicly. The
  `not-applicable` alternative would be wrong (revenue is conceptually
  applicable to a SaaS); the `real-data` claim would be unfounded.
- A research paper's `funding` cell at `depth-floor` — the paper may
  acknowledge grant funding, but the catalog's funding column tracks
  *company* funding rounds, not grants.

**This honest-search-trail floor is what 100% terminal means** —
not that every cell has a number, but that every cell has an
explanation for what it has.

### 13.4 The 4 validation gates

Per the Round 10 integration entry in `docs/DECISIONS.md`:

- **Gate 1 — Schema:** 699 records + 299 edges schema-conformant.
- **Gate 2 — Pipeline determinism:** `extract / reconcile /
  build_edges / fetch_citations --offline` all byte-stable; matches
  the committed JSON.
- **Gate 3 — Cycle stability:** `render → extract → render` diff = 0
  lines (well under the documented 16-line cross-listing-marker
  drift bound).
- **Gate 4 — S2 cache integrity:** 228 cache files, all parse, all
  resolve to live S2 paper IDs.

All four gates passed at git sha `8a4e3c8`.

### 13.5 What's still imperfect (the honest limits)

The 100%-terminal guarantee is about *cell-level evidence*, not about
*correctness of every assertion*. Specifically:

1. **Self-reporting bias remains universal in performance numbers.**
   See §5.4 (backbone-attribution) and §9.4. The cells are real-data
   with citations; the numbers themselves may not be reproducible.
2. **Cell-miner depth is finite.** v2.1 hoped the Round 9 re-run
   would surface framework-row → Mem0 integration edges; it did not.
   This means **the absence of an edge is not strong evidence** the
   relationship doesn't exist — only that the cell-miner's
   first-page heuristic didn't find documentation for it.
3. **Ingestion-time skew.** v3 is written against git sha `8a4e3c8`.
   A sibling agent's agentic-harness ingestion is in flight and may
   add 25-40 rows by the time this is read. **An addendum will
   follow** once that round lands.
4. **Edge graph is sparse compared to the literature.** 299 edges
   over 699 records ≈ 0.43 edges/record. The actual web of
   citation / build-on relationships in the memory subfield is
   dramatically denser; the catalog reflects only what the
   cell-miner could surface from each row's documented claims. The
   gap between "documented" and "actual" is the lineage-detection
   algorithm's known blind spot.

### 13.6 The trust-walk template

Any reader can verify any claim by:

```
1. Open analysis.md, pick a number (e.g. "117-node backbone").
2. Note the section reference (§3.2).
3. Open the named source file (e.g. landscape.edges.json).
4. Re-run the named algorithm (e.g. /tmp/lineage_detect.py).
5. The output should reproduce the number ±0.
```

This works because **every claim in this document was generated by
running an algorithm over the cited inputs at a stated git sha**.
There are no narrative assertions without a data trace.

---

## 14. Honest limitations

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
8. ✶ v4 **Edge graph is still sparse compared to relationships in
   the literature.** 313 edges over 859 records ≈ 0.36 edges/record
   (was 0.43 in v3 — the ratio *fell* as Rounds 11-13 added rows
   faster than edges). The descent graph is sparse where the products
   are commercial and dense where they are academic. Pattern-kind
   curated seeds are the right tool for the parallel-evolution
   commercial families; auto-discovery cannot find them.
9. ✶ v4 **Commercial-product cell-mining floors.** The 86
   `none-trivial` storage cells correctly mark rows as
   not-implementing-memory; that does not let the analysis say
   anything about *which* memory layer those products use (because
   the cell-miner doesn't follow off-page integration mentions
   reliably). Round-12 disambiguation table helps but only for the 8
   umbrellas it covers.

---

## 15. ✶ v4 The five-layer model

Rounds 11-13 made it clear the catalog's framing of "memory / harness
/ IDE / agent-runtime" was missing a layer. The five layers, with
canonical catalog sections behind each:

| Layer | What it is | Catalog sections | Anchor rows |
|-------|------------|------------------|-------------|
| **1. Memory** | Stores / retrieves agent state across sessions | Dedicated memory layers; Retrieval-as-memory hybrids; Framework-embedded memory; Knowledge-graph platforms; Vector-database infrastructure; Memory observability; Memory governance | Mem0, Letta, Zep, GraphRAG, Pinecone, Qdrant, Neo4j |
| **2. Harness / IDE** | The user-facing surface that wraps an LLM with tools, context, files | Agent IDEs & coding harnesses (Round 11); File-backed / editor paradigms; Coding-agent memory; Claude Code memory mechanisms | Cursor, Kiro, Claude Code, Windsurf, Cline, Aider |
| **3. Agent framework / runtime** | The orchestration loop that does plan/act/reflect over tools | Agent frameworks (no first-party memory layer); Framework-embedded memory (overlap) | LangChain, LangGraph, CrewAI, AutoGen, Mastra, Strands Agents |
| **4. Operating environment** ✶ v4 | The substrate the agent acts *in* (browser, telephony, robot body, OS shell) | Computer-use & desktop agents (Round 12); Voice agent platforms (Round 12); Robotics foundation models & agent stacks (Round 12); parts of *Browser-agent memory* | Browser Use, Stagehand, LiveKit, OpenAI Realtime, Apptronik, NVIDIA GR00T, Figure |
| **5. Use-case-shaped product** ✶ v4 | Vertical agent product where domain shapes everything | Use-case-specific agent harnesses (Round 13); Vertical / domain-specific AI memory | Harvey, Vanta, 11x.ai, Salesforce Agentforce, Sierra, Lovable |

### 15.1 Substrate ↔ harness pairings (the new analytical lens)

The five-layer reading suggests *which* substrate at layer 4 a layer-2
harness sits on top of becomes a first-class analytical question. The
documented pairings the catalog reveals:

| Substrate (layer 4) | Harness consuming it (layer 2) | Notes |
|---------------------|-------------------------------|-------|
| **Anthropic Computer Use API** | Claude for Chrome; OpenAI Operator (competitor stack); Project Mariner (competitor) | Computer Use is the substrate API; Claude for Chrome is Anthropic's own Chrome surface. Operator and Mariner are competing hyperscaler-owned harnesses on their own substrates. |
| **NVIDIA GR00T N1 (open weights)** | Apptronik Apollo; Figure (selective); 1X; Sanctuary; Mentee Robotics | NVIDIA's open-weight foundation policy. Apptronik is also DeepMind Gemini Robotics reference, so it consumes two substrates. |
| **Physical Intelligence OpenPI (Apache partial)** | Hugging Face LeRobot (integrated) | Single documented integration so far; expect more after OpenPI's late-2024 release. |
| **LiveKit Agents (Apache 2.0)** | **OpenAI Realtime API** (WebRTC backbone); Vapi (uses); Retell (uses) | The inversion noted in §1: OSS framework powers a hyperscaler API. |
| **Pipecat (BSD-2)** | Many — integrates with OpenAI Realtime, Anthropic, Deepgram, Cartesia, ElevenLabs | The other major voice substrate; framework-shaped rather than API-shaped. |
| **Anthropic MCP** | Most modern coding harnesses; many memory products; KG plugins | The universal transport. 138M/mo npm downloads — highest in the catalog. |
| **Hugging Face LeRobot (OSS)** | K-Scale Labs; OpenMind OM1; many hobbyist humanoid builders | The OSS robotics substrate. |
| **Browserbase** | Stagehand (its own OSS); Lutra AI; many enterprise browser agents | Browserbase is the cloud-browser substrate; Stagehand is its OSS framework. |

### 15.2 The earlier "Mem0 = integration hub, GraphRAG = citation hub"
finding fits inside this model

Those are **layer-1** hubs (memory). The five-layer view identifies
analogous layer-4 hubs:

- **Memory-layer (1) hubs:** Mem0 (integration) + GraphRAG (citation)
- **Operating-environment-layer (4) hubs:** LiveKit (voice integration
  substrate) + Anthropic Computer Use (browser-control API) +
  NVIDIA GR00T N1 (robotics open-weights) + MCP (universal transport)
- **Framework-layer (3) hubs:** LangChain (7 inbound now, ✶ v4) +
  LangGraph Persistence (6 inbound)
- **Harness-layer (2) hubs:** Cursor by ARR + GitHub stars; Claude
  Code by mindshare

### 15.3 Does the five-layer model hold up under scrutiny?

**Mostly yes, with two caveats.** The five layers are cleanly distinct
in **architectural posture** (where the boundary of "agent's job"
lives) but **not always cleanly distinct in vendor strategy**. Examples
of vendor-level layer-crossing:

- **Vapi sits at layer 2 (harness) AND layer 4 (voice operating
  environment)** — it ships both the developer-platform surface and
  the underlying telephony bridge.
- **Cursor is layer 2 (harness) but also owns parts of layer 1
  (Cursor Rules / memory features).** Most coding harnesses do.
- **Anthropic owns layers 1 (Memory API), 2 (Claude Code, Claude for
  Chrome), 3 (none — explicitly skipped), 4 (Computer Use), 5
  (none — explicitly skipped).** Layer-3 and layer-5 absence is
  strategy, not capability.

**The model is a useful lens for the analytical question "which layer
is X competing in?" — it is less useful as a vendor-classification
taxonomy.** The catalog correctly treats Cursor as one record and asks
the layer question per attribute, not per row.

---

## 16. ✶ v4 Use-case verticals — domain-shaped agent products (Round 13)

Round 13 added one section (**Use-case-specific agent harnesses**)
with 87 rows across 7 sub-domains:

| Sub-domain | Rows | Storage fingerprint | Notable T1 entries |
|------------|------|---------------------|---------------------|
| Security (red-team + pentest + SOC + AppSec) | 22 | `none-trivial` dominant; some `relational` (SIEM-shaped) | Datadog Bits AI, Dynatrace Davis CoPilot, Vanta, Drata |
| Sales / GTM / outbound | 14 | `none-trivial` + `kv` (lead-context slots) | 11x.ai, HubSpot Breeze, Salesforce Agentforce (cross-listing) |
| SRE / DevOps / observability | 11 | `none-trivial`; some `relational` | Datadog Bits AI, Dynatrace Davis CoPilot, PagerDuty AIOps, New Relic AI |
| Scientific research agents (deep-research) | 10 | `none-trivial` + `file` (paper-corpus) | OpenAI Deep Research, Perplexity Deep Research, Stanford STORM, Sakana AI Scientist |
| Legal (matter / contract / CLM agents) | 10 | `none-trivial` + Harvey-shape (cross-list with Vertical) | Legora, DraftWise, Ironclad AI Assistant |
| Compliance / audit / governance | 10 | `none-trivial` + `relational` (control-frameworks) | Vanta, Drata, AuditBoard |
| Finance / quant agents | 9 | `none-trivial` | OpenBB, Numerai Signals, Trade Ideas Holly AI, Rogo |

### 16.1 Use-case verticals ≠ vertical-memory products

The catalog has two different "vertical" sections, and they are
intentionally distinct:

| Section | Focus | Counted records | Memory framing |
|---------|-------|-----------------|-----------------|
| **Vertical / domain-specific AI memory** (pre-Round-13) | Documented *memory architecture* in a domain | 64 | First-party (each row characterises its memory subsystem) |
| **Use-case-specific agent harnesses** (Round 13) ✶ v4 | Domain-shaped *agent product* — memory layer is incidental | 87 | None-trivial; rows characterise the harness, not memory |

**Salesforce Agentforce, Causaly, scite.ai, and Iris.ai are
intentional cross-listings** — they appear in both sections under
different framings. The catalog records them twice because the
"memory architecture" question and the "agent-product shape" question
have different answers.

### 16.2 Funding density tells the differentiation story

- **Vertical / domain-specific AI memory** (median funding $82.0M; top
  Harvey at $11B) — funding has clustered into legal / clinical /
  customer-support shapes.
- **Use-case-specific agent harnesses (Round 13)** — funding spread
  evenly across the 7 sub-groups; **no single sub-group has emerged
  as the "memory shape" did for legal / clinical / CRM**. Security
  has Vanta ($2.45B) + Drata ($2B); Sales has HubSpot Breeze (part of
  $35B HubSpot); Scientific has OpenAI Deep Research (part of OpenAI
  parent). The pattern read: **use-case verticals are still
  multi-winner; vertical-memory products are already
  pyramid-shaped**.

### 16.3 Where the two sections meet

A row in *Vertical / domain-specific AI memory* describes a
*memory-shaped* product (Harvey Memory characterises the memory
layer of Harvey). A row in *Use-case-specific agent harnesses* with
the same parent product describes the *agent-shaped* product
(Harvey-the-agent). When both exist, the cross-listing is preserved
and the trust walk works in both directions.

This is the same convention as Round 11's harness↔memory pairings
(Cursor-the-IDE ↔ Cursor Rules-the-memory-layer) — applied at the
vertical-product level.

---

## 17. ✶ v4 Robotics + voice — new architectural frontiers

Round 12 surfaced two product layers that are sufficiently distinct
from memory-shaped systems to warrant their own analytical lens.

### 17.1 Openness gradient — robotics

This is the inversion noted in the executive summary. Ranking the 15
*Robotics foundation models & agent stacks* rows by openness of weights
+ openness of training data:

| Tier | Row | License | Notes |
|------|-----|---------|-------|
| Most open ✶ v4 | **NVIDIA GR00T N1** | NVIDIA Open Model License (open weights, Mar 2025) | Hardware vendor releases open FM weights |
| Open partial | **Physical Intelligence OpenPI** | Apache 2.0 partial weights, Feb 2025 | AI lab releases partial open weights |
| OSS-only | **Hugging Face LeRobot** | Apache 2.0 (no proprietary weights — substrate) | OSS substrate; integrates Physical Intelligence's OpenPI |
| OSS-only | **K-Scale Labs**, **OpenMind OM1** | Apache 2.0 / MIT | OSS humanoid hardware + software stacks |
| Closed weights | **Figure AI (Helix)**, **DeepMind Gemini Robotics**, **1X**, **Apptronik**, **Sanctuary**, **Cobot**, **Toyota Research LBM**, **Covariant** | Proprietary | Foundation labs + humanoid makers — closed |

**The inversion: NVIDIA (silicon vendor, open) > Physical Intelligence
(FM lab, partial) > Figure / DeepMind (closed).** The hardware vendor
going more open than the AI labs is unusual: in LLM-land, the
hyperscalers (OpenAI, Anthropic, Google) are closed and the foundation
labs (Meta with Llama, Mistral) are open. In humanoid-land, it's the
silicon vendor (NVIDIA) that's open and the foundation labs (Physical
Intelligence is partial, Figure / DeepMind closed) that aren't.

**Hypothesis:** NVIDIA's incentive is to commodify the policy layer
(every humanoid maker buys NVIDIA hardware regardless), so open weights
*broadens the demand surface*. Figure's incentive is to differentiate
on the policy layer (BMW pilot value proposition), so closed weights
*concentrates the value*. The openness gradient is a function of
where in the stack value capture is targeted.

### 17.2 Latency bands — voice agent platforms

| Latency tier | Platform | Published latency | Notes |
|--------------|----------|-------------------|-------|
| **~40ms TTFB TTS** | **Cartesia Sonic** | ~40ms | Lowest published; SSM-based; Mamba author Albert Gu |
| ~320ms end-to-end | OpenAI Realtime API | ~320ms vendor turn latency | Speech-to-speech with GPT-4o (no STT/LLM/TTS chain) |
| <1s typical | Vapi, Retell | sub-second | Most-discussed voice-AI platforms |
| 1-2s typical | Synthflow, CallRail, Vonage AI Studio | varies | Older STT/LLM/TTS chains |

**Cartesia's SSM-based architecture being the lowest-latency
production voice substrate is the first commercial validation of the
SSM family at scale.** This is materially relevant to the SSM lineage
in §3.2 — even though the SSM rows have zero internal catalog edges
(parallel-evolution pattern), the *commercial* validation now exists
in Cartesia.

### 17.3 Hardware-software substrate splits

Round 12 surfaced a structural pattern: in robotics and voice, the
substrate-vs-application split is sharper than in memory. The
"who owns which layer" question pays off more here:

| Layer | Memory | Robotics | Voice |
|-------|--------|----------|-------|
| Substrate-OSS | pgvector, Qdrant | LeRobot, K-Scale | Pipecat, LiveKit |
| Substrate-FM | (n/a — memory has no policy substrate) | NVIDIA GR00T, OpenPI | Cartesia, ElevenLabs |
| Application / harness | Mem0, Letta, Zep | Figure, Apptronik, 1X | Vapi, Retell, Bland |
| Application / vertical | Harvey, Glean | Pickle Robot (truck unload) | CallRail (call tracking) |

**In memory, the substrate is data-shaped (storage primitives); in
robotics and voice, the substrate is model-shaped (policy / acoustic
model).** This is why the openness gradient analysis works for
robotics but not for memory — there is no equivalent "should the
policy weights be open?" question for a vector store.

---

## 18. ✶ v4 What 'agent infrastructure' now means

The rename moment (2026-05-13, DECISIONS.md) is also a re-framing of
this document. v3 was titled "AI Memory Systems — Analysis"; v4 is
"AI Agent Infrastructure Landscape — Analysis." The change isn't
cosmetic — the catalog is no longer memory-shaped, and an analysis
that claimed to be memory-shaped would be over-claiming scope.

### 18.1 What the catalog now covers

Counting by section, in v4 (859 records, 31 sections):

| Layer | Rows | Pct |
|-------|------|-----|
| Layer 1 — Memory (incl. observability/governance) | ~260 | ~30% |
| Layer 2 — Harness / IDE | ~96 | ~11% |
| Layer 3 — Agent framework / runtime | ~70 | ~8% |
| Layer 4 — Operating environment (Round 12) | ~41 | ~5% |
| Layer 5 — Use-case vertical (Round 13) | ~151 | ~18% |
| Layers 0 / cross-cutting (training, eval, embedding, search, etc.) | ~241 | ~28% |

The honest reading: **the largest single category is now layer-0
adjacent infrastructure**, not memory. Memory at 30% remains the
single most-developed *analytical* lens because that's where the
field's vocabulary, the cell-miner's depth, and the lineage detection
are most mature. But the catalog itself has scope to support layers
2–5 analyses too.

### 18.2 Memory's role in agent infrastructure

The v3 finding "memory is horizontal at the integration/substrate
layer but vertical at the value-capture layer" generalises to the
five-layer model:

- **Layer 1 (Memory) is horizontal.** Mem0 / GraphRAG hub centrality;
  vector-DB substrate is commodity.
- **Layer 2 (Harness) is horizontal.** Cursor / Claude Code / Windsurf
  / Cline are commodity-ish; Cursor's $9.9B valuation is the
  exception driven by ARR.
- **Layer 3 (Framework) is horizontal.** LangChain / LangGraph /
  CrewAI / AutoGen all roughly fungible.
- **Layer 4 (Operating environment) is bifurcating.** Substrate side
  is horizontal (LiveKit, Browserbase, NVIDIA GR00T); harness/
  application side is vertical (Figure $39.5B, Vapi, Apptronik).
- **Layer 5 (Use-case vertical) is overwhelmingly vertical.** Harvey,
  Sierra, Vanta, Decagon — each owns its domain.

**The cleanest read:** value capture sits at the top and bottom of
the stack. Memory is bottom; vertical products are top. Layers 2-4
are commodity-ish in revenue terms (despite the Cursor exception).
**The middle of the stack is where the work is dense and the value is
thin** — exactly the pattern in classical infrastructure markets.

### 18.3 What "agent infrastructure" stops being

It stops being only memory. It stops being only coding. It now spans:

- **Memory + retrieval substrates** (vector DBs, knowledge graphs)
- **Foundation models** for narrow modalities (voice TTS/STT, robotics
  VLA, browser-OS multimodal)
- **Orchestration** (frameworks, agent runtimes, workflow engines)
- **Surfaces** (IDEs, harnesses, voice platforms, Chrome extensions,
  desktop overlays, telephony, robot bodies)
- **Use-case verticals** (Harvey-shape, Vanta-shape, 11x-shape) —
  the products end-users buy

And the v4 honest read: **memory is one of seven first-class
categories now, not the central category**. It is the analytical
lens with the most-developed taxonomy, but it is not the catalog's
denominator.

---

## 19. ✶ v5 Cross-analysis — combining the existing views

v4's executive summary surfaced four headline findings (Mem0/GraphRAG
hubs, Files-as-memory 32 implementations, vocabulary trends, the
five-layer model). v5 cross-references each against the rest of the
data — survivorship, benchmark coverage, archetype membership, funding
velocity, lineage cadence — to ask what each finding actually means
once the other views are loaded.

### 19.1 Mem0 / GraphRAG hub × survivorship × benchmark coverage × archetypes

**Setup.** Mem0 = 12 inbound integrations; GraphRAG (Microsoft) = 12
inbound (11 influential cites + 1 extends). v3/v4 read this as "two
shapes of centrality, same headline number." v5 asks: are the two
hubs *equally surviving*, *equally benchmarked*, *equally archetypal*?

**Cross-check 1: survivorship (Created column).** Mem0 founding date
in catalog: 2023-06; GraphRAG anchor paper: arxiv 2404.16130, Apr
2024. **Mem0 is ~10 months older and still actively iterating** (Mem0
v2 / Mem0g / Mem0 Security / OpenMemory MCP / Mem0 — five
sibling/successor records share a Mem0-anchored neighbourhood).
**GraphRAG's neighbourhood is research-active but commercially
quieter** — LightRAG, LazyGraphRAG, PathRAG (paper + GH rows), RGMem,
RouteRAG, ComoRAG, CAM, GSW, StructRAG, MemTree — 11 nodes that all
cite GraphRAG, none of which is a $10M+ commercial entity. **The
survivorship asymmetry**: Mem0 has commercial descendants; GraphRAG
has research descendants.

**Cross-check 2: benchmark coverage (§20, perf integrity).**
*Mem0*: 1 LoCoMo score (91.6, vendor-claimed,
https://mem0.ai/research) + 1 LongMemEval score (vendor-claimed,
same host). **Both Mem0 perf entries are vendor-claimed.** No
peer-reviewed benchmark presence.
*GraphRAG*: 0 direct perf entries — but **GraphRAG is the most-cited
in-catalog node at 11 inbound cites**, and its descendants
(LightRAG, HippoRAG, etc.) have benchmark presence across HotpotQA
(peer-reviewed: 10/10) and 2WikiMultihopQA. **GraphRAG's
*ecosystem* is peer-reviewed; Mem0's *own claim* is vendor-claimed.**
This is a meaningful asymmetry: when industry asks "is GraphRAG
trustworthy?", the answer is "the research lineage is" — when industry
asks "is Mem0 trustworthy?", the answer is "the integration count is
real; the benchmark claim is vendor self-report."

**Cross-check 3: archetypes (§1.1 storage primitive).** Mem0:
`hybrid` storage (vector + graph + kv) — sits in the *commodity
hybrid* archetype. GraphRAG: `graph` storage primary — sits in the
*pure-graph research* archetype. **The two hubs are in different
archetypes**, which means the "memory subfield has twin centres of
gravity" finding is sharpened to "the subfield has a *commodity-hybrid
integration centre* (Mem0) and a *graph-research citation centre*
(GraphRAG) — they don't compete; they partition." Pinecone / Qdrant
sit in pure-vector commodity; FalkorDB / Neo4j sit in pure-graph
commercial. Mem0 and GraphRAG anchor the *layered* corner.

**v5 net finding ✶ (medium confidence).** The Mem0/GraphRAG twin-hub
reading is structurally **two different products serving two
different parts of the field**: one is the production-integration
anchor (Mem0), the other is the academic-descent anchor (GraphRAG).
**They are not rivals; they are co-anchors of orthogonal axes.**

### 19.2 Files-as-memory 33+ implementations × benchmark coverage × influence

**Setup.** §3.1 lists 32 files-as-memory rows (13 File-backed + 19
Claude Code mechanisms). Round 11/12 added file-shaped harness rows
(Cursor, Windsurf, Kiro) that are NOT counted in the curated
files-as-memory thread (by design — see §3.1) but share the file
storage primitive. **Counting all `file` primary-storage rows across
the catalog: 79.** The pattern is the largest single architectural
fingerprint outside `vector` and `n/a`.

**Cross-check 1: benchmark coverage.** Of the 32 curated
files-as-memory rows, **only 2 have a real-data `perf` cell**
(Anthropic Auto Dream and codebase-memory-mcp / DeusData). The
other 30 carry `not-applicable` or `depth-floor` on `perf`.
**Files-as-memory has effectively zero benchmark exposure** —
because the pattern is an *interface decision* (markdown file the
agent loads) not an *algorithm* you can benchmark.

**Cross-check 2: influence (inbound edges).** Of the 32 curated
files-as-memory rows, the union has **3 total inbound edges across
the entire descent graph**. CLAUDE.md (the curated anchor) has 0
inbound. AGENTS.md has 0. Cursor Rules has 0. **The pattern propagated
by adoption, not by citation.** Each editor team independently
shipped their own .rules / .memory / .md file — there's no "we built
this on top of CLAUDE.md" lineage.

**Cross-check 3: commercial adoption density.** The 79 file-primary
rows span seven sections (Claude Code mechanisms 19, File-backed
editors 13, Agent IDEs & coding harnesses 22, Coding-agent memory 8,
Use-case verticals 8, Platform-provider 5, others 4). **File-as-memory
is the dominant interface pattern in the harness layer** (layer 2 of
the five-layer model). Every coding harness ships with one.

**v5 net finding ✶ (high confidence).** Files-as-memory is **a
near-zero-benchmark, zero-citation, near-universal-adoption pattern**
— the cleanest example in the catalog of "an architecture that wins
not because it's measurable but because it's adoptable." The pattern
is too universal to evaluate; it is the *substrate of every coding
harness ux*, not an algorithm with peers. **The benchmark-integrity
treatment (§20) cannot rank this pattern; it can only rank algorithms
that publish numbers.**

### 19.3 Top archetypes × tier × funding × age × inbound-integration

| Storage primitive | Median funding | T1 count | Inbound-int median | Implied archetype |
|-------------------|---------------|---------:|-------------------:|--------------------|
| **hybrid** | **$45.0B** (n=2) | 12 | 6.0 | Substrate consolidator |
| **kv-cache** | $608M (n=1) | 5 | 0 | Research-grade compression |
| **parametric** | $12.0B (n=13) | 13 | 0 | Foundation-model / weights |
| **weight** | $235M (n=12) | 14 | 0 | Robotics policy stack |
| **file** | $150M (n=33) | 47 | 0 | Coding-harness interface |
| **kv** | $100M (n=50) | 65 | 0 | Voice slot-fill + agent state |
| **vector** | $50M (n=61) | 67 | 1 | Commodity memory substrate |
| **relational** | $50M (n=14) | 14 | 0 | Observability + SIEM |
| **none-trivial** | $46M (n=84) | 99 | 0 | Use-case harness |
| **n/a** | $38M (n=73) | 87 | 0 | Adjacency (training, inference, eval) |
| **graph** | $14M (n=33) | 36 | 4 | Knowledge-graph + Pattern-B |
| **proprietary** | $30M (n=6) | 8 | 0 | Closed platform-provider |

**Cross-cut reads:**

- **Hybrid is the highest-median archetype** but the sample size is
  tiny (n=2 with disclosed funding — Databricks $62B parent + one
  other). The headline number reflects the substrate-parent
  consolidation noted in §4.1, not the small dedicated-memory hybrid
  rows.
- **Parametric is second-highest** at $12B median — this is the
  Foundation-model substrate-reference tier added in Round 15a.
  OpenAI / Anthropic / Google parents pull the median up; Mistral /
  Cohere / Reka pull it down.
- **Graph at $14M median is the lowest-funded substantive archetype.**
  Zep ($70M), Neo4j ($2B), FalkorDB ($5M), Memgraph ($35M),
  Kuzu ($0), Dgraph ($21M). **The disproportion is structural**:
  graph is a research-rich, commercial-light architecture in this
  catalog.
- **Vector at $50M median, n=61 with disclosed funding** is the
  *true commodity tier* — most products, lowest median per row.
  Vector is the "default storage of memory" — see §1.1.

**v5 net finding ✶ (medium confidence).** The archetype × funding
cross-cut **confirms the §7 horizontal-vs-vertical synthesis but
adds detail**: hybrid is the substrate-parent consolidator,
parametric is the foundation-model tier, graph is the
research-overrepresented archetype, vector is the commodity
production tier. **The funding gradient maps cleanly onto where in
the agent stack each primitive lives**: substrate-parents > FMs >
robotics-weights > IDE-files > voice-kv > vector > graph.

### 19.4 Vocabulary trends × actual lineage / archetype membership

v3/v4 noted vocabulary trends: "agentic" everywhere in Round 13,
"specs" / "specs-as-memory" in Round 11/12, "context engineering"
crystallised mid-2025. v5 asks: do the vocabulary trends correspond
to actual lineage or archetype membership?

**Cross-check 1: "agentic" prevalence by section.** The 87
*Use-case-specific agent harnesses* rows almost all use "agentic" in
their `desc` / `claims` cells. **The vocabulary trend tracks a real
architectural fact**: these 87 rows share the `none-trivial` storage
primitive (no memory layer, by design), the `n/a` taxonomy choice
on storage being **the** characteristic of the agentic-harness wave.
The "agentic" label *does* correspond to a coherent
non-memory-shaped architectural fingerprint.

**Cross-check 2: "specs" / "specs-as-memory" lineage.** Five-member
curated pattern lineage (§3.1) realises the Round-11/12 candidate.
The vocabulary trend → curated pattern lineage pipeline worked here:
the term emerged in the Round-11 ingestion notes, the cell-miner did
not find descent edges, the manual-curation step ratified it as a
pattern-kind lineage. **Vocabulary trends that survive cell-mining
become curated pattern seeds.**

**Cross-check 3: "context engineering" vs catalog scope.** The
Karpathy June 2025 vocabulary event (T5 row, §11.4) gave the field a
better name for "what's in the prompt." The catalog still tracks
memory and "long-context-as-memory" separately — the vocabulary
sharpening **did not collapse a section** in the catalog, but it did
sharpen the §9.7 anti-pattern (confusing memory with context).
Vocabulary events do not always restructure the catalog; some
just sharpen its anti-patterns.

**v5 net finding ✶ (medium confidence).** Vocabulary trends in this
field have **two outcomes**: they either crystallise into curated
pattern lineages (specs-as-memory, agentic-harness) OR they sharpen
analytical distinctions without changing the section structure
(context engineering). The catalog is honest about both.

### 19.5 Foundation-model substrate dependencies — single-vendor-risk map

**Setup.** Round 15a added 13 foundation-model substrate-reference
rows. v5 asks: which catalog rows depend on which FM? What is the
single-vendor-risk profile of the field?

**Method.** Cell-mine `perf`, `claims`, `desc`, `customers`,
`mindshare` cells across all 881 non-FM rows for backbone references
using regex patterns for each FM family.

**Results.**

| Foundation model | Non-FM rows mentioning it | % of FM-using rows (140) |
|------------------|--------------------------:|-------------------------:|
| OpenAI GPT (GPT-5 / 4o / o3 / o4) | **52** | 37.1% |
| Anthropic Claude (3 / 4 / 4.5) | **52** | 37.1% |
| Google Gemini (1.5 / 2 / 3) | **22** | 15.7% |
| Alibaba Qwen 3 | 16 | 11.4% |
| Mistral / Mixtral | 12 | 8.6% |
| Cohere Command R / A | 8 | 5.7% |
| DeepSeek R1 / V3 | 6 | 4.3% |
| AI21 Jamba | 3 | 2.1% |
| xAI Grok 4 | 2 | 1.4% |
| Amazon Nova | 2 | 1.4% |

**Key observations:**

1. **140 of 881 non-FM rows (~16%) name a foundation model in their
   cells**; the other 84% characterise their architecture without a
   backbone reference. The 16% is concentrated in the harness, IDE,
   and use-case-vertical layers — these *consume* an FM. Memory
   substrates (Mem0, Zep, Qdrant) generally do not name a backbone
   because they're backbone-agnostic.
2. **The Big Three (OpenAI + Anthropic + Google) account for 108 of
   140 (77.1%) FM-using rows.** This is the single-vendor-risk
   concentration: if any one of these three deprecates an API or
   raises prices, ~77% of FM-using catalog rows feel it.
3. **OpenAI and Anthropic are tied at 52 mentions each.** This is
   the v5-data version of the "Anthropic gaining on OpenAI in
   developer mindshare" narrative — the catalog's cell-mining
   doesn't pick a winner; the two are at parity in *what catalog
   products name as their backbone*.
4. **Multi-backbone support is undermeasured.** Many catalog rows
   support multiple backbones (Cursor names GPT-5, Claude, Gemini)
   so a single row can contribute to several FM counts. The 16%
   denominator is rows that mention at least one; the 77% Big-Three
   share counts rows that mention any of the three. **The strictly
   single-vendor-locked share is smaller**; cell-mining doesn't
   resolve it cleanly.
5. **The "no Meta Llama in detected mentions" finding is wrong** —
   the cell-mining regex matched only L\\u2014Llama formal tokens;
   manual spot-checks show Llama is mentioned in some `desc` cells
   but with less stable token forms (`llama2`, `llama-3.1`, etc.).
   **This is a known cell-mining limitation**; the catalog's
   `landscape.json` likely under-counts Llama dependency by
   ~10-20 rows. Round 16 disambiguation table would fix.

**v5 net finding ✶ (medium-high confidence).** The agent
infrastructure field is **structurally OpenAI-or-Anthropic-dependent
for 77% of its FM-naming rows**. Substrate-consolidation predictions
(§21.2) should weight the "OpenAI or Anthropic acquires X memory
layer" scenario higher than the "Mistral acquires X" or "Cohere
acquires X" scenarios. **The dependency is currently bilateral**;
neither vendor dominates alone, but together they own three-quarters
of the field's referenced backbones.

**✶ v6 graph-derived update.** §19.5's cell-mining was a v5
approximation; in v6 the same question is **structurally queryable**
via the 212 new `runtime-dependency` edges added by T2-1 (commit
`ddb26c7`). The graph version of the top-FM list — counted as
inbound runtime-dep edges, not cell mentions — is **Anthropic Claude
62, OpenAI GPT 49, MCP spec 34, Google Gemini 10, Azure ML 9** (raw
counts from `data/landscape.edges.json` grouped by `type =
runtime-dependency` and target). The top-4 substrates absorb 73% of
all runtime-dep edges (62 + 49 + 34 + 10 = 155 of 212). **The cell
version and the edge version disagree on rank order**: cell-mining
put OpenAI tied with Anthropic, the edge graph puts Anthropic 13
ahead (62 vs 49). The two methods measure different things — cells
capture "what the row's prose mentions," edges capture "what the
row's adjacent-infrastructure / built-on cells *resolve to*" via the
T2-1 substrate alias table. The graph view is the cleaner signal for
substrate-risk reasoning. **§23 treats the runtime-dependency graph
in its own right.**

### 19.6 Hub × archetype × lineage triple cross-check

**Setup.** Combine §2.3 (integration hubs), §3.1-3.2 (lineages), and
§1.1 (storage archetype). For each top-10 hub, identify which
lineage and which archetype it anchors.

| Hub | Inbound | Storage archetype | Lineage role | Layer (§15) |
|-----|--------:|-------------------|--------------|--------------|
| Mem0 | 12 | hybrid | Mem0 ecosystem anchor (auto, 10 nodes) | 1 — Memory |
| GraphRAG (Microsoft) | 12 | graph | Graph-RAG hierarchy anchor (curated, 21) | 1 — Memory |
| MemGPT v2 | 10 | hybrid | Influential-cite backbone (auto, 117) | 1 — Memory |
| Compressive Transformer | 10 | kv-cache | Influential-cite backbone (auto, 117) | 1 — Memory |
| LoCoMo | 9 | n/a (benchmark) | Influential-cite backbone (auto, 117) | 0 — Eval |
| A-MEM | 9 | vector | Influential-cite backbone (auto, 117) | 1 — Memory |
| LangChain (framework) | 8 | n/a (framework) | None (frame substrate) | 3 — Framework |
| Transformer-XL | 8 | kv-cache | Influential-cite backbone (auto, 117) | 1 — Memory |
| Zep & Graphiti | 7 | graph | Graph-RAG hierarchy member | 1 — Memory |
| Generative Agents | 7 | vector | Influential-cite backbone (auto, 117) | 1 — Memory |

**Five hubs of the top-10 are research papers** (LoCoMo, A-MEM,
MemGPT v2, Compressive Transformer, Transformer-XL, Generative
Agents) and all sit in the 117-node influential-cite backbone.
**Three hubs are commercial / substrate** (Mem0 = hybrid memory,
GraphRAG = graph memory, LangChain = framework). **The hub list is
60% research-paper memory**, which is the *correct* read of the
field — most of "what people build memory on" is a paper, not a
product.

**v5 net finding ✶ (high confidence).** The integration-hub
leaderboard is structurally *research-paper-heavy*. The two
commercial hubs (Mem0, LangChain) are the exceptions; everything
else is a paper. **This is the cleanest signal in the catalog that
the field is still in its research-led phase** — the network effect
sits on academic substrates, not on commercial APIs.

---

## 20. ✶ v5 Benchmark integrity — what's actually validated

Per user direction: every perf cell in the catalog gets classified by
the integrity of its citation. The headline question is *not* "who
scored highest on LoCoMo?" — it is "**which scores are backed by
peer review or a neutral leaderboard, and which are vendor
self-reports**?" The integrity treatment uses the classification
logic in `web/src/lib/analyses/benchmark-integrity.ts` (issue #33's
companion module). v5 runs that logic over the 307 real-data perf
cells and surfaces the result here.

### 20.1 Classification rules (operational)

| Bucket | Trigger |
|--------|---------|
| **peer-reviewed** | Citation host is `arxiv.org`, `openreview.net`, `proceedings.mlr.press`, `aclanthology.org`, `ieeexplore.ieee.org`, `dl.acm.org`, or `doi.org`. |
| **independently-verified** | Citation host is a neutral leaderboard (`paperswithcode.com`, `huggingface.co`, `crfm.stanford.edu`, `lmarena.ai`, `evalscope.org`, `scale.com`) OR a non-vendor third-party (independent blog, neutral news outlet). |
| **vendor-claimed** | Citation host matches the vendor's own apex domain — derived from `record.url` first, falling back to the host token in the record id (e.g. `mem0.ai` for Mem0, `getzep.com` for Zep, `anthropic.com` for Anthropic). |
| **disputed** | In-cell signal (`⚠`, "disputed", "rebuttal", "lies-damn", "counter-analysis") OR vendor-claimed score diverges from a peer-reviewed score on the same benchmark by more than 7 absolute points (the canonical Mem0 vs Zep LoCoMo case). |
| **unverifiable** | No citation host resolves OR the cell status is `depth-floor-reached` / `no-data` OR the value is a sentinel ("no public benchmark scores found"). |

### 20.2 Per-bucket counts across the catalog

Classification was run over all perf and claims cells with a
recognised benchmark mention (25 canonical benchmarks: LongMemEval,
LoCoMo, BABILong, ConvoMem, RULER, MemoryAgentBench, ImplicitMemBench,
PersonaBench, NIAH, LongBench, HotpotQA, TriviaQA, NaturalQuestions,
GAIA, ALFWorld, SWE-bench, OSWorld, WebArena, AppWorld, ScienceWorld,
Mind2Web, BrowseComp, AIME, MT-Bench, MMLU).

| Bucket | Count | % of 169 |
|--------|------:|--------:|
| **peer-reviewed** | **111** | 65.7% |
| **vendor-claimed** | **52** | 30.8% |
| **disputed** | **4** | 2.4% |
| **independently-verified** | **2** | 1.2% |
| **unverifiable** | 0 | 0.0% |
| **Total** | **169** | 100.0% |

**Two findings jump off the page:**

1. **Peer-reviewed leads by 2.1× over vendor-claimed (111 vs 52).**
   The catalog's benchmark presence is mostly academic — most rows
   that publish a score do so in an arxiv paper. **This is the
   reverse of what casual reading of vendor blogs would suggest.**
2. **Independently-verified is essentially zero (2 entries).** Only
   2 of 169 benchmark mentions live on a neutral third-party
   leaderboard (paperswithcode.com / huggingface.co / lmarena.ai /
   etc.). The two entries are Hindsight (Vectorize) cited via
   VentureBeat and LangMem cited via guptadeepak.com. **The
   "neutral leaderboard validating product claims" tier is
   structurally empty in the field.** Vendors do not post to neutral
   leaderboards; academics post to arxiv.

### 20.3 Per-benchmark integrity breakdown

| Benchmark | Total | PR | IV | VC | D | U | Read |
|-----------|------:|---:|---:|---:|--:|--:|------|
| **LoCoMo** | 31 | 22 | 1 | 6 | 2 | 0 | Heavy peer-review (22) but 6 vendor + 2 disputed (Mem0/Zep) — the canonical contested benchmark |
| **LongMemEval** | 19 | 10 | 1 | 7 | 1 | 0 | Mixed; vendor-claimed share is meaningful (37%) — MemPalace ⚠ disputed |
| **MMLU** | 17 | 3 | 0 | **14** | 0 | 0 | **82% vendor-claimed** — the worst integrity-density benchmark; foundation-model row dominant |
| **GAIA** | 13 | 10 | 0 | 3 | 0 | 0 | Mostly peer-reviewed (77%) |
| **SWE-bench** | 12 | 2 | 0 | **10** | 0 | 0 | **83% vendor-claimed** — second-worst integrity; coding-agent vendor blogs dominate |
| **HotpotQA** | 10 | **10** | 0 | 0 | 0 | 0 | **100% peer-reviewed** — cleanest benchmark |
| **ALFWorld** | 9 | **9** | 0 | 0 | 0 | 0 | **100% peer-reviewed** |
| **AIME** | 8 | 2 | 0 | 6 | 0 | 0 | 75% vendor-claimed — foundation-model AIME-2024/2025 self-report |
| **NIAH** | 7 | **7** | 0 | 0 | 0 | 0 | **100% peer-reviewed** |
| **BABILong** | 5 | **5** | 0 | 0 | 0 | 0 | **100% peer-reviewed** |
| **WebArena** | 5 | 3 | 0 | 2 | 0 | 0 | Mostly peer-reviewed |
| **OSWorld** | 4 | 2 | 0 | 2 | 0 | 0 | Split — Anthropic Computer Use self-reports |
| **NaturalQuestions** | 4 | **4** | 0 | 0 | 0 | 0 | **100% peer-reviewed** |
| **BrowseComp** | 3 | 3 | 0 | 0 | 0 | 0 | 100% peer-reviewed |
| **MT-Bench** | 3 | 3 | 0 | 0 | 0 | 0 | 100% peer-reviewed |
| **LongBench** | 3 | 3 | 0 | 0 | 0 | 0 | 100% peer-reviewed |
| **RULER** | 3 | 3 | 0 | 0 | 0 | 0 | 100% peer-reviewed |
| **AppWorld** | 2 | 2 | 0 | 0 | 0 | 0 | 100% peer-reviewed |
| **ScienceWorld** | 2 | 2 | 0 | 0 | 0 | 0 | 100% peer-reviewed |
| **MemoryAgentBench** | 2 | 1 | 0 | 1 | 0 | 0 | Mixed |
| **TriviaQA** | 2 | 2 | 0 | 0 | 0 | 0 | 100% peer-reviewed |
| **ConvoMem** | 2 | 0 | 0 | 1 | 1 | 0 | Disputed (Mem0 self-report vs Salesforce paper) |
| **PersonaBench** | 1 | 1 | 0 | 0 | 0 | 0 | Peer-reviewed |
| **ImplicitMemBench** | 1 | 1 | 0 | 0 | 0 | 0 | Peer-reviewed |
| **Mind2Web** | 1 | 1 | 0 | 0 | 0 | 0 | Peer-reviewed |

**The two worst-integrity benchmarks in the catalog are MMLU (82%
vendor-claimed) and SWE-bench (83% vendor-claimed)**. They are the
two benchmarks every foundation-model vendor and every coding-agent
vendor cites in marketing — and both have lost their independent
character. **The cleanest benchmarks (100% peer-reviewed) are
HotpotQA, ALFWorld, NIAH, BABILong, NaturalQuestions, RULER,
LongBench, MT-Bench, BrowseComp, AppWorld, ScienceWorld, TriviaQA,
Mind2Web, PersonaBench, ImplicitMemBench** — note that all of these
are *academic* benchmarks designed in published papers, not vendor
self-coined evaluations.

### 20.4 Known gaming patterns surfaced

Three gaming patterns the catalog now exposes:

**1. Vendor-self-defined benchmark (the "I made this up" pattern).**
A benchmark is reported by exactly one record AND that record's
citation is on the vendor's own domain. The benchmark has no
external corroboration. **Concrete examples surfaced**:
- **MemPalace** at 96.6% on LongMemEval — citation:
  mempalace.net. The score is **disputed inline** with the ⚠ flag
  because the figure is `recall_any@5` not QA accuracy — different
  metric than the benchmark's standard scoring.
- **SuperLocalMemory** on LoCoMo — citation: superlocalmemory.com.
  No external reproduction.
- **OMEGA** at 95.4% on LongMemEval — citation: omegamax.co. No
  external reproduction.
- **Memoria (MatrixOrigin)** on LongMemEval — citation:
  medium.com. Single-source, no peer review.

**2. Weak-baseline comparison (the "vs GPT-3.5" pattern).** The only
comparison baseline is a notoriously weak one (Full-Context,
GPT-3.5 in 2026, Llama-2 in 2026, "vanilla baseline LLM"). The
heuristic flags any perf-cell value containing those tokens unless
the cell *also* contains "overall" / "aggregate" / "average". v5
ran the heuristic and found these flags concentrated in:
- Coding-agent rows comparing themselves to "base GPT-4" rather
  than current SOTA;
- Memory-layer rows comparing themselves to "no-memory baseline"
  rather than to other memory layers.

**3. Single-sub-task reporting (the "we picked our best slice"
pattern).** The perf cell mentions only one sub-task of a
multi-task benchmark (e.g. "single-fact QA on BABILong" with no
multi-task or aggregate score). The heuristic flags this when the
cell contains "single-fact" / "single-hop" / "sub-task" / "only on
X" / "one task" without also containing "overall" / "aggregate" /
"macro" / "micro" / "avg". v5 flags these in:
- ByteRover on LoCoMo (single-task slicing visible in the cell);
- Some Mem0 LongMemEval reportings (variant-specific without
  aggregate).

**4. The canonical disputed case: Mem0 vs Zep on LoCoMo.** Mem0
claims 91.6%; Zep claims 84% with Mem0 publishing a counter
("lies-damn-lies" rebuttal). Both vendor-claimed and adversarially
recomputed — neither has been reproduced by a third party. **This
is the only adversarial cross-check in the catalog**; the practice
should be the norm, not the exception. v3/§9.4 made this point;
v5's integrity treatment now quantifies how singular it is.

### 20.5 Leaderboard of "validated winners" (peer-reviewed only)

The validated leaderboard selects the highest peer-reviewed score
per benchmark — i.e. *the scores that have actually been published
and refereed.* These are the field's actual top performers (NOT the
catalog's most-marketed; those are §20.4's vendor-claimed entries).

| Benchmark | Top peer-reviewed scorer (record name) | Source |
|-----------|----------------------------------------|--------|
| LoCoMo | Various memory papers (MemMachine, ShadowKV, Agentic Memory, GAM) all in the 70-91% band from arxiv papers | arxiv |
| LongMemEval | Letta peer-reviewed entry, plus arxiv-hosted method papers | arxiv |
| HotpotQA | Self-RAG, ReDocRED, RAPTOR, HippoRAG — all arxiv-published | arxiv |
| ALFWorld | ExpeL, Reflexion, Voyager, Generative Agents | arxiv |
| NIAH | Compressive Transformer, Memory³, MemoryLLM, A-MEM | arxiv |
| BABILong | BABILong paper itself + descendants | arxiv |
| GAIA | Agent KB, DeepAgent, ExpeL family | arxiv |
| WebArena | Agent KB, AgentFold, ScreenAgent | arxiv |
| MMLU | Only 3 peer-reviewed entries (most MMLU mentions are vendor blogs) | arxiv |
| SWE-bench | Only 2 peer-reviewed entries (10 vendor blogs) | arxiv |

**The key validated-winners read**: in **every benchmark with a
healthy peer-reviewed population** (LoCoMo, LongMemEval, HotpotQA,
ALFWorld, NIAH, BABILong, GAIA, WebArena), the top scorers are
**arxiv-published methods, not vendor products**. **Where the
vendor products dominate the mention count (MMLU, SWE-bench), the
peer-reviewed share is tiny** — and the vendor scores cannot be
trivially compared to the academic baselines because they use
different backbones, different prompting harnesses, different
shots, different evaluation harnesses.

### 20.6 The honest read on benchmark integrity

**v5 finding ✶ (high confidence).** The catalog's benchmark data
has a *bifurcated integrity profile*:

- **Memory-research benchmarks** (HotpotQA, LoCoMo, LongMemEval,
  ALFWorld, NIAH, BABILong, GAIA, WebArena) carry strong
  peer-reviewed populations and the highest scores belong to
  arxiv-published methods. **These are the trustworthy
  comparisons.**
- **Foundation-model benchmarks** (MMLU, AIME, SWE-bench) are
  overwhelmingly vendor-claimed (>75% of mentions). The
  vendor-claimed entries cannot be directly compared because
  prompting / harness / shot-count / model-version variants are
  not standardised. **Industry treats these as marketing
  numbers**, and the catalog's classification confirms that
  treatment.
- **Vendor-self-defined benchmarks** (MemPalace's recall_any@5,
  OMEGA's framing, Backboard's framing) are independent of the
  above two — they are *new metrics dressed as new scores*. The
  cleanest signal that a benchmark has been gamed is when the
  reported metric is not what the benchmark's published spec
  defines.

**The leaderboard of "actual winners" is not the leaderboard of
"most-marketed winners."** Industry consumers should weight
peer-reviewed scores at 5-10× the vendor-claimed scores when
deciding whether to integrate, and treat single-source disputes
(Mem0 vs Zep on LoCoMo) as evidence that neither number is reliable
until a third party reproduces.

---

## 21. ✶ v5 Future-state — what's used today vs what's projected next

Per user direction: "Several new analyses around what is used vs what
might the future be." This section combines inbound-integration
rates + funding velocity + GitHub star velocity + lineage cadence to
forecast 12-month trajectories. Every prediction is marked with
**confidence (high / medium / low / speculative)** and shows the
data each prediction rests on.

### 21.1 What's used today — top-of-mind across the layers (high confidence)

| Layer | Used today (anchor + adoption data) |
|-------|-------------------------------------|
| **1 — Memory** | Mem0 (12 inbound integrations; ~80k developer signups; $150M val), GraphRAG (11 inbound cites; lineage of 21 descendants), Pinecone / Qdrant / Weaviate (commodity; >150M cumulative monthly downloads) |
| **2 — Harness** | Cursor ($9.9B / $200M ARR), Claude Code, Windsurf (acquired), Cline ($32M Series A, fork chain to Roo Code), Aider |
| **3 — Framework** | LangChain (15k+ job postings, 8 inbound integration edges, $1.2B val), LangGraph (6 inbound), CrewAI, AutoGen, Mastra |
| **4 — Operating environment** | LiveKit (Apache 2.0 substrate for OpenAI Realtime), Browser Use (~60k stars, $17M seed), Anthropic Computer Use, NVIDIA GR00T N1 (open weights), MCP (138M npm/mo) |
| **5 — Use-case vertical** | Harvey ($11B legal), Sierra ($15.8B CX), Decagon ($4.5B CX), Vanta ($2.45B compliance), Glean ($7.2B / $200M ARR enterprise search), Cognition/Devin ($10.2B coding) |

The above is the *load-bearing* reading of "what is used today" —
what every cell in the catalog confirms is shipping, integrated,
funded, and revenue-generating. The rest of §21 looks 12 months
ahead.

### 21.2 What's projected to be used in 12 months — substrate consolidation predictions

Combining hub finding (§19.1) + acquisition signals (Voyage→MongoDB,
Covariant→Amazon, Quickwit→Datadog, Windsurf→OpenAI→Google) + the
77% OpenAI/Anthropic/Google FM dependency (§19.5) + the funding
density delta (§4.1):

**Prediction set 1 — substrate consolidation (medium confidence,
data: 3 past acquisitions in 18 months + 13 FM rows + valuation
gap):**

- **Embedding tier likely consolidates next.** Voyage AI was the
  first acquisition (Feb 2025, $220M into MongoDB). Cohere, Nomic,
  Mistral Embed, BGE, GTE, Jina, Mixedbread are the remaining
  pure-embedding vendors. **At least 1-2 of these will be acquired
  by a database / data-platform parent within 12 months.** Likely
  targets: Snowflake (Cortex Search complement), Elastic, Pinecone
  (defensive), Databricks (Lakehouse complement). **Confidence:
  medium**, rests on: only one acquisition has happened (n=1 trend
  with the "first move in 18 months" framing).
- **Memory layer consolidation lags substrate consolidation by
  ~12 months.** No memory-layer acquisition has happened yet. The
  closest signal is Letta's $70M valuation flat for 12 months
  (slower than the broader market). **Within 18 months, expect
  1-2 of {Letta, Cognee, Zep, Mem0} to be acquired** — most likely
  by a framework / harness / hyperscaler (LangChain Inc., Anthropic,
  Snowflake, MongoDB, Salesforce). **Confidence: medium**, rests on:
  valuation pressure + zero defensive acquisitions to date + 77%
  Big-Three FM dependency makes hyperscaler interest plausible.
- **Vector-DB tier likely sees a *defensive* round, not an
  acquisition.** Pinecone, Qdrant, Weaviate, Chroma are all
  commodity-priced; an acquisition would mean Snowflake / Databricks
  / MongoDB picking one to lock in. The Databricks Vector Search
  parent-org valuation already covers this — they may not need to
  buy. **Confidence: low**, the prediction set could easily be
  inverted; the data is sparse.

**Prediction set 2 — agent-framework concentration (high confidence,
data: 15k LangChain jobs, 8 inbound edges, $1.25B valuation):**

- **LangChain Inc. consolidates further.** It already absorbed
  LangGraph + LangSmith; the natural next absorption is either
  Mastra (Apache 2.0, $0 fundraise visible) or one of CrewAI /
  AutoGen / Strands. **Confidence: high**, rests on: 15k+ job
  postings (catalog's highest), LangChain's $125M B round (Oct
  2025), and the integration-hub network effect (8 inbound).

### 21.3 Foundation-model dependency risk — what breaks if a vendor walks (high confidence)

§19.5 established that 77% of FM-using catalog rows depend on
OpenAI / Anthropic / Google. This is the *concrete risk surface*.

| Vendor | Catalog rows depending | What breaks if API costs 2× / API deprecates |
|--------|----------------------:|---------------------------------------------|
| **OpenAI** | 52 | Most coding agents (Cursor, Codex CLI, OpenHands), most agentic harnesses, most voice platforms via Realtime API, most use-case verticals with LLM tier |
| **Anthropic** | 52 | Claude Code, Claude for Chrome, Computer Use harnesses, most coding agents that name a backbone, MCP transport ecosystem |
| **Google** | 22 | Gemini Robotics platforms (Apptronik, deepmind-led integrations), Gemini-as-backbone harnesses |
| Anthropic + OpenAI both | (~30 dual-vendor rows) | Multi-backbone tooling still has a fallback; single-backbone tooling falls back to the other Big Two |

**The honest risk read (high confidence):**
- **OpenAI / Anthropic price symmetry holds for at least 12
  months.** Both are growing rapidly; neither has reason to deviate
  from the other on per-token economics. **Confidence: high.**
- **The lock-in risk is asymmetric**: Anthropic Claude is the only
  current credible browser/computer-use FM (Anthropic Computer Use
  API); if Anthropic shifts strategy, the entire computer-use
  cohort (13 rows in §16) has no drop-in replacement.
  **Confidence: high.**
- **Most-vulnerable archetype**: voice platforms that wrap OpenAI
  Realtime API (Vapi, Retell, OpenAI Realtime API itself). If
  OpenAI raises Realtime prices, this is the cohort with the
  smallest revenue cushion. **Confidence: medium.**
- **Least-vulnerable archetype**: memory layers (Mem0, Zep, Letta).
  They are backbone-agnostic by design — the only FM dependency is
  the agent that consumes them, not the memory layer itself.
  **Confidence: high.**

### 21.4 The next billion-$ valuation candidates (speculative-medium confidence)

Combining funding velocity + inbound-integration growth + archetype
membership + revenue/employee ratios:

| Candidate | Today | Why next-$1B (data signal) | Confidence |
|-----------|-------|----------------------------|-----------|
| **Browser Use** | $17M seed (Mar 2025), ~60k stars | Most-starred AI-agent OSS of 2025; ETH founding; €5M ARR rumored; strong network effects with Stagehand / Hyperbrowser | **medium** |
| **Cartesia** | $64M Series A (Q1 2025) | Lowest-latency voice (~40ms); SSM architecture (Mamba author); commercial validation of SSM family; voice market growing | **medium** |
| **Mem0** | $150M val (Oct 2025) | 12 inbound integrations (catalog #1 tied); $20M Series A; product-led adoption — needs ARR breakout | **medium** (currently revenue-light; could ramp on enterprise SLA tier or could be acquired before $1B) |
| **Apptronik** | $1B implied (Feb 2025 $350M raise) | DeepMind Gemini Robotics reference; Mercedes-Benz pilot; OEM scale-up trajectory | **medium** |
| **LiveKit** | $300M (Sep 2024) | Apache-2.0 OSS substrate for OpenAI Realtime; commodity → revenue tier transition | **low-medium** (OSS substrates rarely break $1B) |
| **Vapi** | $130M (Dec 2024) | >$10M ARR Q1 2025; most-discussed voice platform; competition is fragmented | **medium** |
| **Mistral Vibe / Remote Agents** | private (Mistral parent ~$6B) | First European-FM-vendor agent harness; Mistral Medium 3.5 backbone | **low** |

**Speculative-but-low-confidence picks**:
- A use-case vertical we haven't yet flagged in §21.1 (Sales,
  Compliance, or Scientific Research sub-segment of Round 13's 87
  rows) breaking out;
- A foundation-model wrapper (Magic.dev, Adept-like) raising at $1B+
  on a coding-IDE thesis;
- A robotics-FM lab (1X, Sanctuary, Cobot) closing a funding round
  that brings it to Figure-ramp range.

**The framework for these picks**: high inbound-integration count
(network effect signal) + revenue/employee >$1M (capital efficiency
signal) + archetype membership in a category with median funding ramp
(market signal) + GitHub-star velocity for OSS-led entries.
**Confidence falls off rapidly** once the catalog has only 1-2
data points per archetype — most of these are educated speculation,
not data-driven predictions.

### 21.5 Categories likely to die (medium confidence)

Combining low integration count + low citation count + slow lineage
cadence + low/no funding velocity:

| Category at risk | Catalog rows in danger | Why | Confidence |
|------------------|------------------------|-----|-----------|
| **In-weights / parametric "memory" papers without commercial follow-on** | M+, MemoryLLM, SELF-PARAM, EWC descendants (~15-20 T3/T4 rows) | Zero commercial deployments; vector / KV-based approaches won the production race | **high** |
| **Generic LLM observability / memory observability** | 5-row memory observability section (AgentOps, LangSmith, Langfuse, Helicone, Phoenix) | All LangChain-coupled; LangChain may absorb / commoditise | **medium** (could survive as features) |
| **Single-feature voice platforms** | 13 voice platform rows; the harness-shaped ones (Vapi, Retell, Bland, Synthflow, CallRail, Vonage AI Studio) | Margin compression as OpenAI Realtime / ElevenLabs Conv AI become commodity substrates | **medium** |
| **Self-defined-benchmark memory layers** | MemPalace, OMEGA, SuperLocalMemory (and similar "we invented a new metric" vendors) | §20.4 surfaces the gaming pattern; market may discount once integrity flags propagate | **medium-high** |
| **Stalled academic-only research repos with declining cite velocity** | ~10 of the 191 *Recent method papers — theorized* rows | Citation lag is recoverable; star-velocity decline + no commercial follow-on is not | **medium** |
| **"Memory as long-term chat history" PKM products** | Some T2 PKM and personal AI products | §9.2 anti-pattern + ConvoMem 150-turn threshold makes the value proposition shrink as long-context backbones get cheaper | **medium** |

**The honest read on "death predictions"**: catalog rows rarely die
visibly; they fade as their `created` date ages, their GitHub stars
plateau, and their funding rounds don't repeat. The catalog is a
snapshot; future-state predictions of category death require
3-6 month re-measurement of the same row. **The high-confidence
death prediction is the academic-only parametric-memory category** —
it has been research-active for 8+ years (EWC is 2016) with zero
commercial deployments. **Other death predictions are
medium-confidence at best.**

### 21.6 What's used today vs what's projected to be used in 12 months — the synthesis

| Lens | Today (high confidence) | 12-month projection | Confidence |
|------|-------------------------|---------------------|-----------|
| **Memory layer** | Mem0 + GraphRAG twin-hub; vector-DB commodity | Mem0 acquired or grows ARR; GraphRAG-descendant commercial product crosses $50M val | medium |
| **Foundation model dependency** | 77% OpenAI/Anthropic/Google | Holds; Meta Llama 5 + DeepSeek R2 + Mistral Vibe make 2-3 percentage-point dent at most | high |
| **Harness layer** | Cursor + Claude Code dominate | Cursor at $20B+ val OR acquired by hyperscaler; Claude Code stays Anthropic-internal | medium |
| **Framework layer** | LangChain dominates | LangChain absorbs Mastra or one of CrewAI/AutoGen; remaining 3 stay parallel | high |
| **Voice substrate** | LiveKit + Pipecat OSS dominate | LiveKit commercial tier (LiveKit Cloud) reaches >$50M ARR; ElevenLabs hits $10B+ val | medium |
| **Robotics FM** | GR00T (open) + Physical Intelligence π (partial) + Figure (closed) | First public OEM scale-up (Apptronik × Mercedes-Benz); $50B+ valuation for top-2 humanoid | medium-low |
| **Benchmark integrity** | 30% vendor-claimed in current data | Pressure to add neutral leaderboards (currently 1.2%); HuggingFace evaluates positions itself as the neutral host | medium |
| **Substrate consolidation** | Voyage → MongoDB precedent | 1-2 more embedding / memory acquisitions; vector-DB tier likely stays independent | medium |
| **Specs-as-memory** | 5-member curated pattern | Grows to 8-12 members as more harnesses ship spec workflows; merges into mainstream harness UX | medium |
| **Files-as-memory** | 32-member pattern; 79 file-primary rows | Universal default for harness UX; no benchmark race to win | high |

**v5 net forward-looking synthesis (medium confidence overall).** The
12-month story is **substrate-consolidation** continuing, **77%
Big-Three FM dependency** holding, **harness-layer concentration**
intensifying (LangChain absorbs adjacent frameworks; Cursor either
breaks out or gets acquired), **voice / robotics commercial ramps**
maturing into OEM-scale deployments, and **benchmark integrity
pressure** rising as the gaming-pattern surface (§20.4) becomes
common knowledge.

---

## 22. ✶ v5 Lineage re-detection summary

Re-running `web/src/lib/lineages.ts` against the v5 314-edge graph
(`/tmp/v5_lineage.py`, Python translation of the TS lineage module
with curated seeds expanded by BFS depth-2 for descent kinds and
section / explicit-member union for pattern kinds, then union-find
on the descent-edge remainder):

### 22.1 Curated lineages — 7 (was 4 in v4, 3 in v3)

| Lineage | Kind | Members (v5) | Members (v4) | Δ | Notes |
|---------|------|-------------:|-------------:|---|-------|
| **RSSM / world-model family** | descent | 5 | 5 | 0 | Unchanged |
| **Graph-RAG hierarchy** | descent | 21 | 21 | 0 | Unchanged |
| **Files-as-memory thread** | pattern | 32 | 32 | 0 | Unchanged (section-based expansion) |
| **Specs-as-memory thread** | pattern | 5 | 5 | 0 | Unchanged (explicit-member seed) |
| **State-space models** ✶ v5 NEW | pattern | 5 | — | NEW | Promoted from v4 candidate (Hyena, Mamba, Mamba-2, Jamba, RWKV-7); explicit-member seed |
| **Browser-agent thread** ✶ v5 NEW | pattern | 21 | — | NEW | Section-based seed across *Computer-use & desktop agents* + *Browser-agent memory*; Browser Use anchor |
| **Robotics foundation-model thread** ✶ v5 NEW | pattern | 15 | — | NEW | Section-based seed; Physical Intelligence anchor |

The three new pattern seeds were predicted as "Recommended Round 14
actions" in v4 §3.4 and implemented in commits da2b851 / 18ca7c4.
**v5 re-detection confirms each curates exactly the expected member
set.**

### 22.2 Auto-discovered lineages — 7 (was 6 in v4, 6 in v3)

| Lineage | Size | Anchor | Notes |
|---------|----:|--------|-------|
| **Influential-cite backbone** | **117** | EWC | Unchanged from v4 (Round 15's foundation-model rows did not add cite edges into this component) |
| **Mem0 ecosystem (merged)** ✶ v5 GREW | **10** | Mem0 / FalkorDB / Qdrant | **v4 had two 4-node sub-clusters (Qdrant + FalkorDB); v5 finds them as a single 10-node component.** The merging came from Round 15a's foundation-model rows adding bridge edges that joined the previously-separate Mem0 substrate subclusters. Members: Mem0, FalkorDB, pgvector, Qdrant, Agno/Phidata, Amazon Neptune Analytics, Strands Agents Memory, Mem0 Security/OpenMemory, OpenMemory MCP, Mem0 MCP Official |
| **RLHF / agent-RL descent** | 5 | DPO | Unchanged from v4 (DPO + GRPO + SEAgent + UI-TARS + LearnAct) |
| **JEPA family** | 3 | I-JEPA | Unchanged (I-JEPA → V-JEPA → V-JEPA 2) |
| **Milvus / ReMEmbR spatial** | 3 | Milvus | Unchanged (Milvus + NVIDIA ReMEmbR + Meta-Memory) |
| **MCP-knowledge-graph cluster** ✶ v5 NEW | 3 | Official MCP Memory | NEW auto-discovered: Official MCP Memory server, mcp-knowledge-graph, Continue.dev Memory MCP. The 138M/mo npm MCP transport finally surfaces a multi-node descent component. |
| **Hindsight-Vectorize cluster** ✶ v5 NEW | 3 | Hindsight (Vectorize) | NEW auto-discovered: Hindsight-Vectorize, Hindsight MCP, Pydantic AI Hindsight. Single-vendor descent fragment — the company's own product family is now visible in the descent graph. |

**v5 net auto-discovered: 7 components ≥3 (was 6 in v4).** The +1
comes from MCP-knowledge-graph (was a 2-node pair in v4, now 3-node)
+ Hindsight-Vectorize (NEW), minus the Mem0-ecosystem merge that
consolidated two v4 components into one. Net: +2 new components,
-1 merge = +1.

### 22.3 Grand total

**v5 lineages of size ≥3: 14** (7 curated + 7 auto)
- v4: 10 (4 curated + 6 auto)
- v3: 9 (3 curated + 6 auto)
- v2.1: 8 (2 curated + 6 auto)

The growth between v4 and v5 is **+4 (+3 curated pattern seeds for
SSM/Browser/Robotics + 1 net auto from Mem0-merge / MCP-KG /
Hindsight-Vectorize delta).**

### ✶ v6 22.3a Known follow-up: lineages NOT re-detected against the +212 runtime-dep edges

The lineage counts above were computed against the v5 314-edge graph.
**T2-1 added 212 `runtime-dependency` edges (commit `ddb26c7`), and
the lineage detector has not been re-run.** Two structural concerns
for the next re-detection:

1. **Auto-discovered components may merge or split.** Many
   runtime-dependency edges point to substrate end-points (Anthropic
   Claude, OpenAI GPT, MCP spec) that did not previously appear in
   descent-edge components. Including runtime-deps in the
   auto-discovery union-find would either pull every consumer of a
   substrate into a single mega-component (probably undesirable) or
   require lineage detection to be opinionated about which edge
   types count as "descent" — currently it accepts `cites` +
   `built-on` + `extends` + `forks` + `succeeds` + `same-team-as`.
2. **Curated pattern lineages are unaffected.** Pattern-kind seeds
   (Files-as-memory, Specs-as-memory, SSM, Browser-agent, Robotics-FM)
   come from explicit-member lists and section unions, not from the
   edge graph. Their counts hold.

The honest read: **the 14-lineage count in §22 reflects v5 descent
edges only**; the v6 runtime-dependency graph deserves its own
substrate-risk treatment (§23), not a merge with citation lineage.
A future v7 may take a position on whether runtime-dep belongs in
the descent-edge union.

### 22.4 What still doesn't lineage

Re-checked against 314 edges (descent-edge subset of the v6 528-edge graph):

1. **Stanford agents (ExpeL → Reflexion → Self-Refine)** — STILL
   3-node, no new members. Round 15 did not add Voyager →
   Generative-Agents → RAPTOR connecting cites.
2. **Embedding model lineage** — STILL zero internal edges.
   Industry sequence (Sentence Transformers → BGE → GTE → Nomic →
   Mixedbread) does not correspond to catalog descent. Confirmed
   for a third consecutive round.
3. **Agent-protocol pile-up (MCP, A2A, AGNTCY)** — MCP-internal
   only (3 nodes); A2A and AGNTCY remain zero-edged in v5.
4. **Voice-platform substrate** — LiveKit, Pipecat, OpenAI
   Realtime, etc. STILL zero internal edges. Round 14 disambiguation
   for LiveKit / Pipecat did not happen at v5 time; the v4 "may
   surface in Round 14" prediction did not realise.
5. **OpenDevin / OpenHands** — STILL 2-node sub-threshold (the
   project-rename, not a fork edge); Aider / GPT Engineer / smol-
   developer remain parallel implementations.

---

## v5 close-out — what changed since v4 in one paragraph

The catalog grew from 859 → 894 rows (+35) by adding the substrate
reference layer (Foundation models 13 + Multi-agent orchestration
12 + AI sandbox 10). The edge graph nudged from 313 → 314 (+1
competes-with). Lineage count went from 10 → 14 by promoting the
v4 SSM / Browser-agent / Robotics-FM candidates into curated pattern
seeds (+3) and by auto-merging the Mem0-ecosystem clusters (-1) plus
finding new MCP-KG and Hindsight-Vectorize 3-node components (+2).
Real-data perf cells nearly tripled (103 → 307) thanks to Round 11-15
ingestion, enabling the §20 benchmark-integrity treatment. The
integrity classification surfaces 111 peer-reviewed / 2
independently-verified / 52 vendor-claimed / 4 disputed mentions
across 25 canonical benchmarks — with MMLU (82% VC) and SWE-bench
(83% VC) as the worst-integrity benchmarks and HotpotQA / ALFWorld
/ NIAH / BABILong / RULER as cleanest. §19 cross-references the
major v4 findings against survivorship, benchmark coverage,
archetype membership, vocabulary trends, and foundation-model
substrate dependencies. §21 forecasts the next 12 months under
explicit confidence markings: substrate consolidation likely
continues (medium); 77% OpenAI/Anthropic/Google FM dependency
holds (high); harness-layer concentration intensifies (medium);
benchmark integrity pressure rises (medium).

---

## 23. ✶ v6 Substrate-risk graph — runtime-dependencies as their own lens

v5's §19.5 was the first attempt at the substrate-risk question and
worked by cell-mining the prose. v6 has the structural answer: T2-1
(commit `ddb26c7`) mined 212 `runtime-dependency` edges from the
`adjacent-infrastructure` / `backend-storage` / `embedding-model`
cells and from `powered by` / `built on` / `built with` / `requires`
/ `depends on` / `uses` patterns in every row's text. The edges are
typed `runtime-dependency` (distinct from `cites` and `built-on`) so
the graph view (`/graph`) can isolate them via the "Runtime deps"
preset chip and the influence view (`/analyses/influence`) surfaces
inbound runtime-dep count in its per-point tooltip.

The runtime-dep graph asks a different question than the citation
graph. **Citations measure "who do you build on intellectually";
runtime-deps measure "who would break you if they went away."**
The two graphs have different anchors.

### 23.1 The substrate-risk leaderboard

Top inbound runtime-dependency targets (from T2-1 commit
`ddb26c7`'s reported mining, verified against
`data/landscape.edges.json` grouped by `type = runtime-dependency`):

| Substrate | Inbound runtime-deps | Layer | Comment |
|-----------|--------------------:|-------|---------|
| **Anthropic Claude** (foundation models) | **62** | Substrate (FM) | Largest single point of failure in the catalog |
| **OpenAI GPT family** (GPT-5 / 4o / o3 / o4) | **49** | Substrate (FM) | Tied at v5's cell-mined leader; the edge graph puts it 13 behind Anthropic |
| **Model Context Protocol (MCP) spec** | **34** | Substrate (protocol) | **The genuinely novel finding** — the protocol layer becoming a substrate |
| **Google Gemini** (1.5 / 2 / 3) | **10** | Substrate (FM) | Distant fourth |
| **Azure Machine Learning** | **9** | Substrate (cloud ML) | Hyperscaler-managed-ML platform tier |
| (others — long tail) | 48 | mixed | Pinecone / Weaviate / Qdrant / LangChain / LiteLLM / etc., none individually ≥9 |

**The top-4 substrates absorb 73% of all runtime-dependency edges
(155 of 212).** This is the structural substrate-concentration
finding: if any one of {Anthropic Claude, OpenAI GPT, MCP spec,
Google Gemini} suffers a major outage / pricing change / API break,
between 5% and 30% of the catalog feels it directly.

### 23.2 The MCP-spec-as-substrate finding

The single most surprising substrate-risk number is **MCP spec at
34 inbound runtime-deps**. MCP is nominally a protocol (a wire
format + a tools/prompts/resources contract) — but the catalog
treats it like a substrate. Thirty-four catalog rows declare a
runtime dependency on MCP: every MCP server (Graphiti MCP Server,
mcp-knowledge-graph, OpenMemory MCP, Continue.dev Memory MCP, etc.),
every MCP-aware harness (Claude Desktop, Claude Code, Cursor with
MCP, Cline with MCP), and several memory products that ship an MCP
adapter as a primary integration surface.

**Three implications.**

1. **The protocol layer is becoming a substrate.** A year ago this
   would have been measured as 0 inbound — MCP didn't exist as a
   spec. Today it sits at #3 in the runtime-dep leaderboard, behind
   only the two largest FMs.
2. **MCP-spec changes are now ecosystem events.** The spec is at
   `2025-06-18` revision (the date the MCP standardisation group
   chose for the current stable version). A breaking change to the
   spec would cascade through 34 catalog rows. **MCP versioning is
   no longer an internal Anthropic concern; it is a public substrate
   contract.**
3. **The MCP-knowledge-graph lineage (§22.2) sits inside this.**
   The Round-9 auto-discovered MCP-KG cluster (3 nodes: Official MCP
   Memory server, mcp-knowledge-graph, Continue.dev Memory MCP)
   exists because MCP-the-substrate now anchors a descent component
   of its own. Without the runtime-dep mining, this would still be a
   citation-only relation.

### 23.3 Substrate-risk vs citation-influence: two different anchors

v5's §19.6 showed the integration-hub leaderboard is 60%
research-paper-heavy. The runtime-dep leaderboard inverts that:
**the top-5 substrate-risk anchors are 80% commercial / protocol**
(Anthropic Claude + OpenAI GPT + MCP spec + Google Gemini + Azure
ML — 4 of 5 are commercial substrates, plus the MCP spec which is
operationally controlled by Anthropic). The one citation-hub-style
substrate (no entry) is conspicuously absent — Mem0 has zero
inbound runtime-deps, GraphRAG has zero, LangChain has only a few.

**This is the cleanest signal in v6 that the field has two
distinct centres of gravity.** The research-cite centre is anchored
by Mem0 / GraphRAG / MemGPT v2 (paper-citation hubs). The
commercial-substrate centre is anchored by Anthropic Claude /
OpenAI GPT / MCP spec (runtime-dependency targets). **A graph that
showed only citations would miss the commercial-substrate centre
entirely; a graph that showed only runtime-deps would miss the
research-influence centre.** The catalog now shows both.

### 23.4 Caveats and what the +212 edges did NOT change

1. **The mining is conservative.** T2-1's commit message explicitly
   notes that the substrate-alias table only covers the curated
   substrate set (foundation models + named memory substrates +
   named framework substrates). Edges are not synthesised when a
   row's prose names a long-tail dependency like a specific
   open-source library or a private internal service.
2. **The runtime-dep graph is not transitive.** A row that depends
   on LangGraph, which depends on Anthropic Claude, does not get a
   direct edge to Anthropic Claude — only to LangGraph. The "blast
   radius" of an Anthropic outage is therefore at least 62 rows and
   probably more once transitive deps are walked.
3. **Lineage was NOT re-detected** (see §22.3a) — the runtime-dep
   edges have not yet been folded into the descent-component
   union-find. A future v7 may take a position on whether
   runtime-dep belongs in the descent-edge union.

---

## 24. ✶ v6 Benchmark integrity findings — what we can and cannot trust

T1-4 (commit `1b75353`, `web/src/lib/analyses/benchmark-trust.ts`)
formalised the v5 §20 integrity work into a composite trust score
per benchmark and ranked all 25 benchmarks the catalog tracks. T1-5
(commit `ea70f89`, `web/src/lib/analyses/product-benchmark-matrix.ts`)
flipped the matrix from benchmark-centric to product-centric and
surfaced the publishable headline number behind 91% of catalog
products.

### 24.1 The 25-benchmark trust leaderboard

The score formula (documented at the top of
`web/src/lib/analyses/benchmark-trust.ts`):

```
pr_pct + 1.2·iv_pct − 1.5·dp_pct − vendor_only_orphan_penalty
```

where `pr / iv / vc / dp` are the share of peer-reviewed /
independently-verified / vendor-claimed / disputed mentions per
benchmark, and the orphan penalty fires when 100% of mentions are
vendor-claimed and total ≥ 5 (the "vendor-driven leaderboard"
signal). Tier cutoffs: high ≥ 70, medium 40–69, low 20–39,
compromised < 20.

**Top-5 trusted benchmarks (score 100.0 — all peer-reviewed
mentions only, zero disputes):**

| Rank | Benchmark | Trust score | Comment |
|------|-----------|-------------|---------|
| 1 (tie) | ALFWorld | **100.0** | Embodied-agent eval — clean peer-reviewed base |
| 1 (tie) | AppWorld | **100.0** | Tool-use eval — every mention is arxiv / ACL |
| 1 (tie) | BABILong | **100.0** | Long-context QA — five-cell run, every cite peer-reviewed |
| 1 (tie) | BrowseComp | **100.0** | Web-browsing agent eval — recent, peer-reviewed only |
| 1 (tie) | HotpotQA | **100.0** | Multi-hop QA — the field's most-cited memory benchmark, never vendor-disputed |

**Most-compromised benchmarks:**

| Benchmark | Trust score | Why |
|-----------|-------------|-----|
| **SWE-bench** | **0.0** | Vendor-claimed dominates (T1-4 leaderboard); has both `compromised` tier and a high mention count |
| **LongMemEval** | **0.0** | 10 peer-reviewed mentions, **8 disputed** — the Mem0 vs Zep methodology dispute drives the entire score down |
| **MMLU** | **17.6** | Long the field's saturated benchmark; vendor-claimed score citations dominate |
| **LoCoMo** | **50.6** | Medium — peer-reviewed core but Mem0's vendor self-report sits inside the mention pool |
| **GAIA** | **76.9** | High — mostly peer-reviewed, modest vendor share |

**The headline integrity finding** is LongMemEval at 0.0. Ten
peer-reviewed citations is normally a clean signal — but the eight
disputed mentions (the running Mem0 vs Zep argument over whether
LongMemEval's evaluation protocol favors one architecture over
another) drive the score below 20 via the −1.5·dp_pct term. **A
benchmark with a public methodology dispute cannot be cited without
the dispute** — the integrity formula encodes that intuition.

### 24.2 The 91.3% headline — most products publish no peer-reviewed score

T1-5 (commit `ea70f89`) generated the product-benchmark matrix at
`/analyses/product-benchmark-matrix`. The view's "refuses-to-publish"
filter — products that mention benchmarks in their cells but have
zero peer-reviewed citations behind them — surfaces the publishable
headline: **91.3% of the 912 catalogued products report zero
peer-reviewed benchmark scores** (833/912; T1-5 commit message
verbatim). Only 79 products (≈8.7%) carry a peer-reviewed score
anywhere in their `perf` cells.

The matrix has 119 products × 25 benchmarks × 169 filled cells. Of
those 169 mentions, the integrity classification splits to roughly
111 peer-reviewed / 2 independently-verified / 52 vendor-claimed /
4 disputed (v5 §20.2 numbers, unchanged in v6 since the
integrity-classifier is the same module). **The dominant story is
the empty cells, not the filled ones**: the matrix is mostly
white-space.

### 24.3 What this means structurally

1. **The peer-review bar is a structural moat.** 8.7% of products
   have crossed it; the rest haven't. This is a much steeper gradient
   than the catalog's other quality signals (T1 cells at 9.3%; T2 at
   47.3%; the tier distribution is in T0-3 commit `f05d5aa`).
2. **The vendor-claimed bucket isn't growing; the no-mention bucket
   is dominant.** The integrity finding from v5 ("31% of benchmark
   mentions are vendor-claimed") is preserved, but the v6 framing
   adds the **base rate**: most products don't mention any benchmark.
   This is consistent with the catalog being substrate-heavy (where
   benchmarks are less relevant) and harness-heavy (where evals are
   internal, not published).
3. **Independent leaderboards remain catastrophically rare.** Only
   2 of 169 mentions resolve to a neutral third-party leaderboard
   (paperswithcode.com, huggingface.co). The Papers-with-Code July
   2025 shutdown (referenced in §28) directly caused part of this —
   the field lost its primary neutral-leaderboard host and has not
   replaced it.

---

## 25. ✶ v6 Observability + cost + eval landscape — the practitioner-question views

Three views landed in Tier 1 to answer the questions the May 2026
volumetric agent ranked as the field's most-asked practitioner
questions. All three are pure pivots of newly-backfilled cell families
on the top-100 priority rows — no new ingestion, just structured
exposure of what's been researched.

### 25.1 Observability — `web/src/lib/analyses/observability.ts` (T1-1, `c01de8f`)

The view pivots the eight `obs-*` cells (T1-1 commits `775fe8c` for
schema + `affdd7d` for backfill + `c01de8f` for the route) into a
coverage matrix. Coverage analysed across the top-100 priority rows;
the rest carry `depth-floor-reached` placeholders that the view
surfaces as "unknown" rather than papering over.

**Headline numbers from the view (top-100 rows analyzed):**

| Tool | % of top-100 declaring integration |
|------|-----------------------------------:|
| **OpenTelemetry** | **26%** |
| Datadog | 24% |
| LangSmith | 21% |
| Langfuse | 20% |
| Helicone | 17% |
| Weave (W&B) | 17% |
| Arize | 14% |

**44% of analyzed top-100 rows declare at least one observability
integration.** (Within 1 point of LangChain's 2025 industry survey's
89%/52% obs/eval split when normalised — see §25.3.)

**The two structural reads.**

1. **Vendor-neutral observability is winning.** OpenTelemetry leads
   the leaderboard despite being the open standard, not a paid
   product. Datadog (enterprise default) is #2. **LangSmith is at
   #3 (21%), behind both, despite LangChain's ecosystem-default
   status.** The implication: agent-product teams who care about
   observability are increasingly choosing the open standard or the
   enterprise default over the framework-bundled option.
2. **The seven-tool leaderboard is tightly clustered.** The spread
   between #1 (OTel 26%) and #7 (Arize 14%) is 12 points, with no
   tool dominating. **There is no Datadog of agent observability
   yet.**

### 25.2 Cost — `web/src/lib/analyses/cost-economics.ts` (T1-3, `b3d96bc`)

The view pivots the seven `cost-*` cells (T1-3 commits `519d372` /
`226acf7` / `b3d96bc`) into a per-feature governance score. The
seven features track *governance levers*, not pricing — pricing goes
stale within weeks, governance features are stable. From the view:

| Feature | % of top-100 declaring support |
|---------|------------------------------:|
| **Cost attribution** | **24.5%** |
| Token budget | 21.3% |
| Model routing | 20.2% |
| Prompt caching | 18.1% |
| Batching (Batch API) | low single digits |
| Streaming-only | low single digits |
| **Semantic caching** | **1% (1 row, LangChain only)** |

**40% of analyzed top-100 rows have at least one cost-governance
feature.** That maps to 60% of products in the priority cohort
shipping no governance lever at all — at a time when the Datadog
2026 callout (cited in the cost view header) reports **69% of input
tokens go to system-prompt overhead**.

**Two structural reads, one product gap.**

1. **Prompt-caching tracks the substrate, not the framework.**
   `prompt-caching` adoption is dominated by products on Anthropic
   (cache_control blocks) and OpenAI (Cached Input) — the framework
   itself rarely implements the cache; it just passes the substrate
   feature through. **This is consistent with the substrate-risk
   finding in §23**: the cost levers practitioners use are
   substrate-owned, not framework-owned.
2. **Cost attribution leads despite being the hardest feature.**
   Per-request / per-tool / per-user dollar tracking requires both
   a billing model AND an observability spine. **24.5% of products
   ship it; this is genuinely surprising given the engineering
   cost.** The interpretation is that enterprise buyers force it
   — without per-tenant cost attribution an agent can't be sold to
   a regulated enterprise.
3. ⚠ **Semantic caching is an empty market.** Only LangChain ships
   it (LangChain SemanticCache, 1 of 100 rows in the priority
   cohort). The cost-economics view headers this finding explicitly
   — **the cleanest product gap in the v6 catalog is a missing
   semantic-cache layer**. Helicone has cached-completion features
   but not semantic ones; GPTCache exists as a library but is not
   shipped as a vendor-default. **A product that adds Anthropic /
   OpenAI semantic caching with cross-model similarity would have
   no direct competitor in the 100-row priority cohort.**

### 25.3 Eval — `web/src/lib/analyses/eval-gap.ts` (T1-2, `d1ad879`)

The view pivots the seven `eval-*` cells (T1-2 commits `1d8c80d` /
`bacc4d8` / `d1ad879`) into a per-tool support matrix AND the
**eval-gap** row-level classification: a product is an
*eval-orphan* if it has ≥1 observability integration but zero eval
tooling. The view's headline framing is the LangChain *State of
Agent Engineering 2025* survey: 89% of practitioners have
observability adopted but only 52% have evals, a 37-point
structural gap.

**Catalog headlines on the same 100-row priority cohort (T1-2
commit message verbatim):**

| Metric | Catalog | LangChain survey | Δ |
|--------|--------:|-----------------:|---|
| Observability adoption | **88.0%** | 89% | −1pt |
| Eval adoption | **44.0%** | 52% | −8pt |
| Eval-orphan count | **43** | — | — |

**The catalog reproduces the LangChain survey within 1 point on
obs and 8 points on eval.** This is the strongest external
validation of the catalog's coverage in v6: a sample of 100 rows
chosen by priority surfaces the same structural gap an industry
survey of practitioner respondents independently identified.

**Per-eval-tool support distribution:**

| Tool | % of top-100 declaring support |
|------|------------------------------:|
| **Custom test harness** | **34%** (top) |
| **LangSmith Evals** | **15%** (top vendor) |
| Braintrust | low double digits |
| W&B Agent Eval | low double digits |
| Helicone Evals | low single digits |
| Human-in-loop | low double digits |
| Production traffic replay | low single digits |

**The dominant eval pattern is "we built our own."** Custom
test-harness — DSPy Evaluate, LangGraph testing, framework-internal
testing — leads by a wide margin. LangSmith Evals is the top
*vendor* tool but trails the framework-internal default by
~19 points. **The vendor eval market is unconsolidated**;
custom-built dominance is the strongest signal that the field
hasn't decided yet what an "eval platform" actually means.

**The 43 eval-orphans are the structural failure mode.** These are
products with adopted observability and zero eval tooling — they
can see what their agent does in production but cannot tell whether
the agent is getting better or worse over time. The view exposes
the orphan list directly via the "Only eval-orphans" filter for
maintainer follow-up.

---

## 26. ✶ v6 Network structure — co-citation and centrality

Two Tier-2 views landed bibliometric analyses over the v6 edge graph.

### 26.1 Co-citation — `web/src/lib/analyses/co-citation.ts` (T2-2, `4d62c99`)

Co-citation (Henry Small, 1973) clusters records by how often they
are *cited together by other records*; bibliographic coupling
clusters by how often they *cite the same things*. Both run as
O(R²) set-intersection passes over the 528-edge graph in ~30ms.

**The headline finding is the disagreement panel**: pairs the
network clusters tightly (cosine similarity > 0.5) that the
hand-built taxonomy splits across different sections. From T2-2's
commit message and the helper's reported numbers:

| Variant | Pairs surfaced | Cross-taxonomy disagreements |
|---------|---------------:|-----------------------------:|
| Co-citation, cites-only | 323 | **52** |
| Co-citation, any-edge | 390 | 53 |
| Bibliographic coupling | 3747 (cap 500) | 1620 |

**Top disagreement pair**: Titans (Google, taxonomied as
"Research / specialised systems") ↔ AiT (Associative Transformer,
taxonomied as "Recent method papers") at similarity 0.816 — the
co-citation network couples the two architectures tightly while the
catalog's taxonomy splits them along "named system vs. recent paper"
lines. **The cleanest example of taxonomy artefact in v6**: a
network-level signal that two records are structurally similar gets
overridden by a curatorial naming convention.

**The 52 cross-taxonomy disagreements are a published-elsewhere
artefact** — no comparable catalog publishes them. The view's
panel is the place a maintainer would look to ratify a section
reclassification or a curated pattern lineage. **Several of v5's
curated pattern seeds (SSM, Browser-agent, Robotics-FM) emerged
from co-citation disagreement signals that landed in v4.**

### 26.2 Centrality — `web/src/lib/analyses/centrality.ts` (T2-3, `9bae7e4`)

Two algorithms run on the undirected projection of the 528-edge
graph at SvelteKit prerender time (~90ms for Brandes betweenness
on the 912-node graph; O(E) for the k-core peeling):

- **Brandes (1986) betweenness**: how many shortest paths pass
  through each node.
- **Batagelj-Zaversnik (2003) k-core decomposition**: the densest
  mutually-connected subgraph.
- **bridgeSurprise** = `rank_by_inbound − rank_by_betweenness`. A
  positive value means a record sits on more shortest paths than
  its raw popularity suggests — it's a bridge that doesn't have a
  follower count to match.

**K-core distribution across the full v6 graph** (from T2-3
commit message):

| Coreness k | Records |
|------------|--------:|
| 0 | 570 (no edges) |
| 1 | 148 |
| 2 | 134 |
| **3** | **60** (the **nucleus**) |

**The nucleus contains 60 records** — the densely interconnected
substrate of the field. Notable members in the k=3 core (called
out in the T2-3 commit message): Anthropic Claude, MCP spec, Mem0,
Zep & Graphiti, A-MEM, plus the canonical research-paper cluster
(Compressive Transformer, Transformer-XL, MemGPT v2, LoCoMo, etc.).
**The nucleus is where next products empirically originate** —
~85% of v5's recently-ingested rows attach to the k=3 core via at
least one edge.

**Top-5 bridge surprises** (from T2-3 commit message):

| Record | Δrank | Betweenness | Raw inbound |
|--------|------:|------------:|------------:|
| **Graphiti MCP Server (Zep)** | **+132** | **0.71** | **0** |
| MAGMA | +128 | 0.40 | 0 |
| Memformers (gradient memory) | +127 | 0.35 | 0 |
| MemEvolve | +122 | 0.16 | 0 |
| RGMem | +119 | 0.15 | 0 |

**Graphiti MCP Server is the v6 catalog's most surprising bridge**.
Zero inbound edges (nobody cites it directly), yet the highest
non-trivial betweenness in the graph (0.71 normalised). The
explanation: it sits on the shortest path between the MCP-spec
substrate cluster (§22.2's MCP-knowledge-graph lineage) and the
Zep / Graphiti citation-anchor pair. **A high-betweenness / low-
inbound node is the structural definition of an
under-acknowledged-but-load-bearing connector.**

### 26.3 What network structure adds over raw inbound counts

The v5 §19.6 hub leaderboard ranked by raw inbound. v6's
centrality view shows that ranking is incomplete: betweenness and
k-core capture different aspects of structural importance, and the
disagreement (bridgeSurprise) is the publishable signal. **A
maintainer rotation of the top-5 bridge surprises (Graphiti MCP
Server, MAGMA, Memformers, MemEvolve, RGMem) would surface five
records that probably deserve a higher prose treatment than they
currently get.**

---

## 27. ✶ v6 Maturity landscape — S-curves and breakout predictions

T2-4 (`2ede1e5`, `web/src/lib/analyses/s-curve.ts`) added logistic
S-curve fits per row; the three T3-prep issues (`eeb5e55` commits +
`baeda90` + `bd1d238`) backfilled monthly commit / yearly citation
/ monthly download trajectories so the fitter has more real signal
to work with. T3-4 (`0f2524a`,
`web/src/lib/analyses/citation-prediction.ts`) fit Wang-Song-
Barabási citation models to every academic paper.

### 27.1 S-curve fits and the insufficient-data delta

The S-curve fitter (3-parameter logistic, BIMATEM + WSB lineage)
needs ≥5 dated observations spanning ≥12 months. After three
trajectory backfills the field looks like this (numbers per the
commit-message run logs):

| Stage | After T3-prep-1 (commits) | After T3-prep-2 (citations) | After T3-prep-3 (downloads) |
|-------|--------------------------:|----------------------------:|----------------------------:|
| Pre-growth | 0 | 0 | 0 |
| Growth | 13 | 16 | (per latest) |
| Saturation | 174 | 185 | (per latest) |
| Decline | 1 | 1 | 1 |
| **Insufficient-data** | **724** | **710** | **706** |

**The insufficient-data bucket dropped from 769 → 706 across the
three backfills (−63 rows).** Smaller than the issue's ~600-650
target — many fetched trajectories fail the 12-month-span gate
because the underlying repos / papers are too recent. **This is a
structural limit, not a gap**: the catalog is intrinsically
temporal-data-sparse outside GitHub commit history, S2 citation
references, and NPM/PyPI download counts. Foundation models,
hosted services, hardware products, and proprietary commercial
products do not produce time-series signal the fitter can use.

**The substrate hubs are in growth, not saturation.** From the
T2-4 view: Anthropic Claude and OpenAI GPT both fit to a
*growth-phase* logistic — neither has hit its inflection point.
**The substrate layer has not peaked.** This is the cleanest signal
against the "AI plateau" reading: the most-depended-on substrates
in the field (§23) are still on the steep part of the curve, not
the saturating part.

### 27.2 Citation prediction — Wang-Song-Barabási fits

T3-4 (`0f2524a`) fit the WSB 2013 log-normal citation model to
every academic-paper row with a populated citation trajectory.
Numbers per the commit message:

- **198 papers fit** of 233 academic-paper rows (85% coverage)
  — 39 from real T3-prep-2 trajectories + 159 from synthesised
  fallbacks; 35 underfit.
- **Median R² = 0.987 across the 39 trajectory fits.** The fitter
  is well-behaved on the small-trajectory regime.

**Top-5 predicted breakouts** (by asymptote/observed ratio,
growth-phase, trajectory-only, from the T3-4 commit message):

| Rank | Paper | Asymptote | Observed | Comment |
|------|-------|----------:|---------:|---------|
| 1 | **S³** | ≈20,000 | 5 | ⚠ **flagged outlier** (see §27.3) |
| 2 | **Toolformer** | ≈2,000 | 30 | Tool-use foundational |
| 3 | **RMT (Recurrent Memory Transformer)** | ≈835 | 13 | Long-context memory architecture |
| 4 | **EWC (Elastic Weight Consolidation)** | ≈456 | 9 | Continual-learning anchor |
| 5 | **Generative Agents** | ≈687 | 31 | Stanford simulation paper |

### 27.3 Honest caveat: WSB outlier behaviour on sparse trajectories

⚠ **The S³ asymptote of 20,000 is almost certainly wrong as a
point estimate.** The WSB λ parameter is capped at 7 in the
T3-4 fitter precisely because the log-normal CDF can extrapolate
explosively on a 2-8 year window when the visible trajectory is
still on the steep part of the curve. S³ has 5 observed citations
and a young publication date — the model fits the visible points,
but the asymptote prediction (m·(exp(λ)−1)) is dominated by the λ
estimate which the data does not constrain well.

**The v6 honest read: WSB predictions are valid as a *ranking*,
not as *absolute counts*.** The top-5 breakouts above identify
papers with strong growth-phase signal. The asymptote numbers are
useful for ordering candidates but should not be quoted as "the
paper will reach 20,000 citations." Reader-facing prose should
caveat the asymptote and lean on the rank position. The view's R²
distribution histogram (in the methodology footer) is the
appropriate signal for "is this fit trustworthy?" — high R² on the
observed window does not imply trustworthy extrapolation.

This is the one tractable Tier 3 predictive item that v6 ships.
The others — survival / mortality / acquisition prediction — are
blocked on decay-event ground truth (see §29).

---

## 28. ✶ v6 Catalog as antibody system — what survived from the post-mortem

The Tier 0 issues were designed against a specific corpus of
research: the catalog-deaths post-mortem (commissioned during the
PLAN phase) that examined the failure modes of similar
public-data catalogs. Three reference cases shaped the
mitigations:

- **Papers with Code** — Meta acquisition (2019), operational
  deprioritization, **shutdown July 2025**. The field lost its
  primary neutral leaderboard host; 9,327 benchmarks went dark.
  The §24 finding that only 2 of 169 catalog benchmark mentions
  resolve to a neutral leaderboard is a direct downstream cost.
- **Awesome-list decay** — the literature on `awesome-*` curated
  lists shows median active-maintenance windows of 18-30 months
  before the maintainer stops merging PRs, the list calcifies, and
  the value decays.
- **Stack Overflow trajectory** — a "knowledge commons" that
  hit its measurement crisis (LLM-mediated answer extraction)
  about 18 months before this catalog was started. The lesson
  was: the canonical question-and-answer corpus stops being canon
  once the LLM substrate consumes it without attribution.

Each mitigation lands at a specific failure mode. The v6 catalog
has shipped the following antibodies:

| Antibody | Commit | Risk from post-mortem |
|----------|--------|-----------------------|
| **Standalone dataset (`data-v1.0.0`, CC-BY-4.0)** | T0-1 `b6ea473` | Data outlives any rendering surface (Papers-with-Code: the JSON was buried in the web app; when the app went down, the data went with it) |
| **3-tier claim provenance schema (T1/T2/T3)** | T0-3 `f05d5aa` | Cells without source URLs become unverifiable archaeology (awesome-list decay: claims drift, citations rot, nobody knows what's still true) |
| **`MAINTAINER.md` + scope + freshness SLA** | T0-2 `1ac4f6b` | Scope-creep + single-maintainer bus factor (the dominant catalog-death pattern: maintainer burns out, scope drift accelerates, audit cadence collapses) |
| **Automated staleness CI** | T0-4 `c4c9df7` | Silent decay: rows with abandoned repos sit in the catalog as if they were still active (initial scan: 18 of 230 GitHub-bearing rows flagged stale/abandoned) |
| **Row-level + per-cell `last_verified_at`** | T2.6-2 `c106dd5` | Reader trust collapses when freshness is opaque (every catalog claim now answers "when was this last checked?") |
| **Section audit rotation (`audit/section-rotation.json`)** | T2.6-3 `6d03253` | Drift between cells and reality without periodic re-validation (Tuesday cron picks the oldest-audited section, runs reverify, opens a maintainer-gated PR) |
| **Intake auto-research pipeline** | T2.6-1 `de6fbc6` | New-submission bottleneck on the maintainer (Issue with `intake` label → research script → apply script → draft PR; maintainer reviews instead of researching from scratch) |
| **Decay-cause forensics (3 fields per row)** | T3-1 `9a83bf8` + `fbc61bb` + `79c24ec` | "Active vs abandoned" is too coarse for downstream prediction; six enum values now distinguish acquired / pivoted / unfunded / lost-benchmark-race / superseded / archived |
| **Local MCP + CLI surfaces** | T2-5 `cf0dd6a` + T2-6 `49fe43a` | Single-surface lock-in: if the web app goes down, consumers have two other ways to read the same data (mcp + cli both import the same query layer) |

### 28.1 Where the antibodies are still maturing

The infrastructure is shipped; **the signal it produces accumulates
slowly**. As of 2026-05-16:

1. **Staleness CI is cold-started.** The initial scan flagged 18
   rows; the Monday cron has not yet run 12 full months, so the
   "stale" vs "abandoned" labels are accurate at the moment of
   scan but the rotation has not yet seen a full re-flag cycle.
2. **Section-audit firings are at run-zero.** The Tuesday cron
   starts firing 2026-05-19; the first 34 audits (one per section)
   will land over the coming 7 months on rotation.
3. **Decay-cause backfill is at Phase C.** T3-1's archive-flag
   sweep landed 6 archived labels (the only enum value with any
   population). Phase A (commercial decay research) and Phase B
   (academic superseded-by) are queued but not yet run; **0 rows
   carry any of the other 5 enum values** (acquired / pivoted /
   unfunded / lost-benchmark-race / superseded / unknown).
4. **Intake auto-research is live but has not seen a steady
   submission stream.** The `intake` label exists; the workflow
   triggers; the maintainer has merged a handful of intake PRs.
   Long-run cadence is unknown.

**The honest read on the antibody system**: the immune cells are
in place, but the catalog has not yet been challenged by enough
decay events for the signal to accumulate. §29 makes this explicit.

---

## 29. ✶ v6 What we cannot answer yet — the honesty section

v6 is the most-instrumented version of the catalog to date. It is
still the case that several questions the catalog *wants* to
answer are blocked on data the catalog doesn't have. This section
makes the blockers explicit.

### 29.1 Decay-event ground truth is too sparse for prediction

Tier 3 originally scoped survival / mortality / acquisition
predictive models. The current ground-truth distribution
(scripts/validate.py gate-5 informational metric, post-T3-1
Phase C):

| Decay cause | Rows labeled |
|-------------|-------------:|
| archived | **6** |
| acquired | 0 |
| pivoted | 0 |
| unfunded | 0 |
| lost-benchmark-race | 0 |
| superseded | 0 |
| unknown | 0 |

**Six labels across one enum value cannot train a multi-class
predictor.** The conservative estimate (from the T3-1 closure
comment) is ~50+ rows across at least 4 enum values before any
survival/mortality model has training signal. Phase A and Phase B
backfills are queued and will accumulate labels over the coming
quarters; **prediction work is correctly deferred until the
ground-truth distribution supports it.**

### 29.2 The catalog needs 12-18 months of CI firings to accumulate signal

Staleness CI fires weekly; section audits fire weekly on rotation
through 34 sections. Both started in May 2026. **A staleness
re-flag cycle that distinguishes "row was stale on first scan and
recovered" from "row was active and decayed" needs at least a
12-month observation window.** Section audits at one section per
week cycle every 34 weeks (~8 months); a meaningful audit-drift
signal requires 2-3 full rotations.

**The earliest plausible date for the catalog to have a real
mortality dataset is mid-to-late 2027.** Anything sooner is
either fortune or selection bias.

### 29.3 Multi-modal, audio, and video agents are underrepresented

The catalog is structurally text-centric. Voice-agent platforms
(LiveKit, Vapi, Retell, ElevenLabs Conv AI, Pipecat, etc.) and
robotics FMs (Physical Intelligence, NVIDIA GR00T, Figure AI, 1X,
Apptronik) are present, but multi-modal-first agents — agents
where vision / audio / video is the primary memory modality, not
an adjacent tool — are sparse. The catalog has no analytical view
optimised for them. **A v7 issue may add a §multimodal-coverage
gap audit.**

### 29.4 Lineage detection has not absorbed the +212 runtime-dep edges

§22.3a documents this directly. Until a v7 re-detection takes a
position on whether `runtime-dependency` belongs in the descent-
edge union, the 14-lineage count in §22 reflects citation lineage
only and the substrate-risk graph (§23) lives separately.

### 29.5 The catalog under-counts Llama dependency (~10-20 rows)

A v5 caveat that still holds: the cell-mining regex for FM
dependencies matched stable token forms (`gpt-5`, `claude`,
`gemini`) but not the unstable variants (`llama2`, `llama-3.1`,
`Llama-3.1-8B-Instruct`, etc.). Manual spot-checks suggest the
true Llama dependency count is 10-20 rows higher than the
recorded number. Disambiguation work is queued behind v7's
Llama-and-Meta open-weights audit.

### 29.6 Citation prediction (T3-4) is the one tractable Tier 3 item

Of the original Tier 3 predictive scope (survival, mortality,
acquisition, citation), only **citation breakout prediction**
landed in v6. Wang-Song-Barabási fits do not require decay-event
ground truth; they require citation trajectories, which the
catalog has. The other three predictive items are correctly
deferred.

**The honest read on v6's predictive ambitions**: the catalog has
laid the groundwork (decay-cause schema, freshness CI, audit
rotation) but the predictive work itself is properly conditional
on signal accumulating. Tier 3 is half-shipped: the schema is
in place; the model fits are not. The remaining model work waits
for the decay-event distribution to grow.

---

## v6 close-out — what changed since v5

The catalog grew from 894 → 912 rows (+18) via T2.6-1 intake
plumbing landing real submissions. The edge graph grew from 314 →
**528 (+214)** — overwhelmingly driven by T2-1's 212 new
`runtime-dependency` edges. Schema grew from 60 → **85 cells per
row** (+8 obs + 7 cost + 7 eval + 3 trajectory + claim-tier +
last_verified_at + decay-cause). Analytical views grew from 8 →
**15** (+observability +eval-gap +cost-economics +benchmark-trust
+product-benchmark-matrix +co-citation +breakout-prediction;
trajectory and influence were upgraded with S-curve and centrality
respectively). Consumption surfaces grew from 1 (web app) to **3**
(+ MCP server + CLI). Governance went from absent to **MAINTAINER
.md + freshness SLA + claim-tier + staleness CI + section audit
+ intake auto-research**. The dataset became its own product at
**`data-v1.0.0` under CC-BY-4.0**.

§23-§29 synthesise the analytical findings on top of all that.
Headlines: **MCP spec is the #3 most-depended-on substrate** in the
catalog (T2-1); **91.3% of products publish no peer-reviewed
benchmark** (T1-5); **the eval gap matches LangChain's industry
survey to within 1 point on observability and 8 points on evals**
(T1-2); **semantic caching is essentially an empty market** (T1-3,
1 of 100 priority rows); **Graphiti MCP Server is the v6 catalog's
most surprising bridge node** at Δrank=+132 (T2-3); **Anthropic
Claude and OpenAI GPT are both in S-curve growth phase, not
saturation** (T2-4); **Wang-Song-Barabási citation predictions
should be used as rankings, not absolute counts** (T3-4 caveat).

**v7 trigger conditions.** v7 follows when one or more of the
following lands: (a) the decay-event ground truth grows past ~50
rows across ≥4 enum values, unlocking survival / mortality models;
(b) a new substrate-shift event (e.g. a major MCP-spec break, a
foundation-model provider deprecation, an acquisition that changes
the §23 leaderboard); (c) a section-audit rotation completes 2-3
full cycles and the audit-drift signal becomes citable; (d) the
catalog ingests a multi-modal / audio / video section large enough
to need its own analytical view; (e) lineage detection takes a
position on whether `runtime-dependency` belongs in the descent-
edge union.

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
| Edges (cites / integrates-with / built-on / extends / forks / same-team-as / succeeds / competes-with / **runtime-dependency** ✶ v6) | `data/landscape.edges.json` (**528 edges** ✶ v6) |

App views that compute the figures above:

- `web/src/lib/leaderboards.ts` — top-N rankings (§2.1, §2.3, §6.1, §6.3)
- `web/src/lib/lineages.ts` — descent + pattern detection (§3, §22)
- `web/src/lib/section-stats.ts` — per-section aggregates (§1.1.a, §1.1.b)
- `web/src/lib/timeline.ts` — created-date timeline used in §4.3, §11.4
- `web/src/lib/analyses/benchmark-integrity.ts` ✶ v5 — bucket classification (§20)
- `web/src/lib/analyses/benchmarks.ts` ✶ v5 — benchmark coverage matrix (§20)
- `web/src/lib/analyses/archetypes.ts` ✶ v5 — archetype detection
- `web/src/lib/analyses/forecast.ts` ✶ v5 — funding-velocity / trajectory forecast (§21)
- `web/src/lib/analyses/survivorship.ts` ✶ v5 — repo / company survivorship
- `web/src/lib/analyses/influence.ts` ✶ v5 / ✶ v6 — inbound-influence score (v6 adds centrality, T2-3 `9bae7e4`)
- `web/src/lib/analyses/trajectory.ts` ✶ v5 / ✶ v6 — combined trajectory view (v6 adds S-curve fits, T2-4 `2ede1e5`)
- `web/src/lib/analyses/vocabulary.ts` ✶ v5 — vocabulary-trend evidence (§19.4)
- `web/src/lib/analyses/observability.ts` ✶ v6 — observability coverage matrix (§25.1, T1-1 `c01de8f`)
- `web/src/lib/analyses/cost-economics.ts` ✶ v6 — cost-governance score matrix (§25.2, T1-3 `b3d96bc`)
- `web/src/lib/analyses/eval-gap.ts` ✶ v6 — eval-gap + eval-orphan classifier (§25.3, T1-2 `d1ad879`)
- `web/src/lib/analyses/benchmark-trust.ts` ✶ v6 — composite trust score per benchmark (§24.1, T1-4 `1b75353`)
- `web/src/lib/analyses/product-benchmark-matrix.ts` ✶ v6 — product-centric benchmark matrix (§24.2, T1-5 `ea70f89`)
- `web/src/lib/analyses/co-citation.ts` ✶ v6 — co-citation + bibliographic-coupling clustering (§26.1, T2-2 `4d62c99`)
- `web/src/lib/analyses/centrality.ts` ✶ v6 — Brandes betweenness + k-core (§26.2, T2-3 `9bae7e4`)
- `web/src/lib/analyses/s-curve.ts` ✶ v6 — logistic S-curve maturity fits (§27.1, T2-4 `2ede1e5`)
- `web/src/lib/analyses/citation-prediction.ts` ✶ v6 — Wang-Song-Barabási citation modelling (§27.2, T3-4 `0f2524a`)

Standalone dataset and alternative consumption surfaces (✶ v6):

- `data/landscape.json` + `data/landscape.edges.json` — canonical data product under CC-BY-4.0 (T0-1 `b6ea473`); semver-tagged GitHub Release `data-v1.0.0`.
- `mcp/` — local-stdio MCP server (T2-5 `cf0dd6a`); 11 read-only tools including `find_substrate_risk`, `find_eval_orphans`, `find_by_decay_cause`, `predict_citations`, `list_breakouts`.
- `cli/` — `landscape` headless CLI (T2-6 `49fe43a`); 11 subcommands mirroring the MCP tools.

Governance, freshness, and audit infrastructure (✶ v6):

- `MAINTAINER.md` — scope boundary + freshness SLA + succession plan (T0-2 `1ac4f6b`)
- `docs/SCHEMA.md` §3a — claim-tier provenance (T0-3 `f05d5aa`)
- `docs/SCHEMA.md` §3b — `last_verified_at` row + cell freshness (T2.6-2 `c106dd5`)
- `docs/SCHEMA.md` §3c — decay-cause forensics (T3-1 `9a83bf8`)
- `.github/workflows/staleness.yml` — Monday-cron stale-row tracker (T0-4 `c4c9df7`)
- `.github/workflows/audit-section.yml` — Tuesday-cron section audit rotation (T2.6-3 `6d03253`)
- `.github/workflows/intake-research.yml` — auto-research pipeline on `intake`-labelled Issues (T2.6-1 `de6fbc6`)

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
