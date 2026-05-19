# Findings — AI agent infrastructure landscape

Five publishable headlines from the v6 catalog (912 records × 68 columns
across 34 sections, 528 typed edges). Each finding cites the catalog
machinery that produced it; full derivations live in
[`analysis.md`](../analysis.md).

This page is the "what's interesting in the dataset" entry point. If you
came here from a link, the [README](../README.md) explains the project;
the [dataset README](../data/README.md) explains the schema; the
[MCP server](../mcp/) lets you query the catalog from Claude.

---

## 1. Semantic caching is an empty market

Of the 100-row priority cohort, **exactly one product ships a semantic
cache** — LangChain's SemanticCache. Helicone has cached completion
features but not semantic ones; GPTCache exists as a library but isn't
shipped as a vendor default. The cost-economics view headlines this
finding explicitly: the cleanest product gap in the v6 catalog is a
missing semantic-cache layer. A product that adds Anthropic / OpenAI
semantic caching with cross-model similarity would have no direct
competitor in the priority cohort.

Source: [`analysis.md` §25.2](../analysis.md), commit `f2b95c1`.

## 2. 91.3% of catalogued products publish no peer-reviewed benchmark

**833 of 912 products report zero peer-reviewed benchmark scores.**
Only 79 products (≈8.7%) carry a peer-reviewed score anywhere in their
`perf` cells. The product × benchmark matrix has 119 products × 25
benchmarks × 169 filled cells; the dominant story is the empty cells,
not the filled ones — the matrix is mostly white-space. Of the 169
that *are* filled, the integrity classification is 111 peer-reviewed /
2 independently-verified / 52 vendor-claimed / 4 disputed — meaning
**only 2 scores live on a neutral third-party leaderboard**. Almost
every claim is either a paper or a vendor blog.

Source: [`analysis.md` §24.2](../analysis.md), commit `ea70f89`
(T1-5 product-benchmark matrix).

## 3. The MCP spec is the catalog's #3 inbound substrate

The T2-1 runtime-dependency mining pass produced a 212-edge graph of
"X depends on Y at runtime." The substrate ranking by inbound count
is **Anthropic Claude 62, OpenAI GPT 52, MCP spec 34, Google Gemini
22, Alibaba Qwen 16**. A protocol specification ranking #3 — ahead
of every foundation model except Claude and GPT — is the v6 finding
that wasn't visible in citation-graph hubs. **The MCP spec is
becoming a substrate, not just a protocol.** Citation hubs (Mem0,
GraphRAG) and runtime-dep hubs are different sets of anchors asking
different questions.

Source: [`analysis.md` §23](../analysis.md), commit `ddb26c7`
(T2-1 runtime-dependency edges).

## 4. Graphiti MCP Server is the most under-acknowledged connector in the catalog

The v6 centrality view computes Brandes betweenness on the full
528-edge graph at prerender time. **Graphiti MCP Server has zero
inbound edges yet the highest non-trivial betweenness in the graph
(0.71 normalised).** It sits on the shortest path between the MCP-spec
substrate cluster and the Zep / Graphiti citation-anchor pair. A
high-betweenness / low-inbound node is the structural definition of
an under-acknowledged-but-load-bearing connector. The top-5
"bridge-surprise" leaderboard (Graphiti MCP Server, MAGMA, Memformers,
MemEvolve, RGMem) flags five records that probably deserve a higher
prose treatment than the catalog currently gives them.

Source: [`analysis.md` §26.2](../analysis.md), v6 centrality view.

## 5. 77% of FM-dependent products lock onto three vendors

**140 catalog rows (~16% of non-FM rows) name at least one foundation
model in their cells.** Of those 140, **108 (77.1%) depend on OpenAI /
Anthropic / Google** — the single-vendor-risk tier. The full
substrate-reference distribution: OpenAI GPT 52, Anthropic Claude 52,
Google Gemini 22, Alibaba Qwen 16, Mistral 12, Cohere Command 8,
DeepSeek 6, AI21 Jamba 3, xAI Grok 2, Amazon Nova 2. The rest of the
catalog characterises architecture without a backbone reference at
all. The substrate-risk map is concentrated on three labs.

Source: [`analysis.md` §19.5 + §21.3](../analysis.md), v5/v6 FM
substrate-reference mining.

---

## Using the dataset

Three consumption surfaces, same underlying `data/landscape.json`:

| Surface | Best for | How |
|---|---|---|
| [Web app](https://mrpeppersdev.github.io/agent-infrastructure-landscape/) | Browsing, charts, analytical views | Open the link |
| [MCP server](../mcp/) (`npx -y landscape-mcp`) | Querying from Claude Code / Desktop | Add to your MCP config |
| [`landscape` CLI](../cli/) | Local scripting / pipelines | Clone + `npm i -g ./cli` |
| Raw JSON | Anything else | `data/landscape.json`, CC-BY-4.0 |

The dataset is its own product: tagged `data-vX.Y.Z` on GitHub
Releases, licensed CC-BY-4.0, decoupled from the web app per
[issue #35](https://github.com/MrPeppersDev/agent-infrastructure-landscape/issues/35).

## Where to go next

- **Full v6 analysis** (~3700 lines, all numbers traced to commits):
  [`analysis.md`](../analysis.md).
- **Schema** (cell-shape, tier ladder, citation requirements):
  [`docs/SCHEMA.md`](SCHEMA.md).
- **How rows get added** (auto-research intake): [`docs/INTAKE.md`](INTAKE.md).
- **How rows stay fresh** (section-audit rotation): [`docs/AUDIT.md`](AUDIT.md).
- **Why decisions were made the way they were**:
  [`docs/DECISIONS.md`](DECISIONS.md).
