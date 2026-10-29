// Findings — the catalog's five publishable headlines. Shared
// between /findings (hub) and /findings/[slug] (per-finding article).
//
// Each entry's body is the long-form prose for the dedicated SEO page;
// cardSoWhat is the shorter version shown on the hub card. Source line
// cites the analysis.md section so a reader can audit the claim.
// Finding 2 is recomputed from the data at build time: its {tokens}
// are filled by withLiveNumbers().

export type Finding = {
  /** URL slug used by /findings/[slug]. */
  slug: string;
  /** Position on the hub (1..5). */
  n: number;
  /** Page headline / card title. */
  headline: string;
  /** Short SEO description (≤ 160 chars). */
  metaDescription: string;
  /** Tagline shown under the card title. */
  figure: string;
  /** Short prose for the hub card. */
  cardSoWhat: string;
  /** Long-form body, one paragraph per entry. Used on the dedicated page. */
  body: string[];
  /** Deep link to the analytical view that produced it. */
  link: { href: string; label: string };
  /** Citation tag. */
  source: string;
};

// hrefs are absolute (no base prefix); the Svelte pages prepend base.
export const findings: Finding[] = [
  {
    slug: 'semantic-caching-empty-market',
    n: 1,
    headline: 'Agent stacks leave semantic caching to the data layer',
    metaDescription:
      'Only 1 of 100 priority-cohort agent products ships a semantic cache. The capability is arriving from databases and gateways instead, such as Redis LangCache.',
    figure: '1 of 100 priority-cohort agent products',
    cardSoWhat:
      "Inside the agent stack, only LangChain's SemanticCache ships a true semantic-cache layer in the priority cohort. The capability exists, but it is being sold by the data and gateway layer (for example Redis LangCache), not by agent frameworks or model providers.",
    body: [
      "Across the catalog's 100-product priority cohort of agent frameworks, memory layers and model platforms, semantic caching shows up as a shipping feature in exactly one place: LangChain's SemanticCache. Every other entry that claims caching is token-level prompt caching (Anthropic, OpenAI), CDN-style response caching, or vector-store dedup.",
      "That is a gap in the agent stack, not in the market. Semantic caching is being productised one layer down: Redis ships LangCache as a managed semantic-caching service, and open-source libraries and AI gateways offer it as an add-on. An earlier version of this finding called semantic caching an empty market; that over-read the cohort and has been corrected.",
      "The practical takeaway for builders: if repeated or paraphrased prompts drive your costs, look at your database or gateway vendor rather than your agent framework. Prompt caching (now broadly adopted) only deduplicates exact-prefix repeats, while semantic caching catches reformulated repeats, which is where much of the long-tail LLM cost lives."
    ],
    link: { href: '/analyses/cost-economics', label: 'See the cost-economics matrix' },
    source: 'analysis.md §25.2'
  },
  {
    slug: 'no-peer-reviewed-benchmark',
    n: 2,
    headline: '{refusingPct} of catalogued products publish no peer-reviewed benchmark',
    metaDescription:
      '{refusing} of {total} AI agent memory products ship no peer-reviewed benchmark score. The product × benchmark matrix is empty cells, not full ones.',
    figure: '{refusing} of {total} products · only {independent} scores independently verified',
    cardSoWhat:
      'The product × benchmark matrix is {products} × {benchmarks} with {filled} filled cells — the story is the empty cells. Of the {filled} filled, the integrity split is {peer} peer-reviewed / {independent} independently-verified / {vendor} vendor-claimed / {disputed} disputed. Almost every claim is a paper or a vendor blog.',
    body: [
      "The product × benchmark matrix is a {products} × {benchmarks} grid with {filled} filled cells. Of the {possible} possible product-benchmark cells, {emptyPct} are empty. Of the {filled} filled cells, only {independent} are independently verified (a score a third party has reproduced or posted on a neutral leaderboard); {peer} are peer-reviewed paper claims, {vendor} are vendor blog or marketing numbers, and {disputed} are disputed (contested by a second source).",
      "If you widen from the {products} products on the benchmark matrix to all {total} records in the catalog, {refusing} ({refusingPct}) have no peer-reviewed benchmark score — meaning the product has shipped without a peer-reviewed result on any of the {benchmarks} benchmarks the catalog tracks (LoCoMo, LongMemEval, MTEB, GAIA, SWE-bench and the rest).",
      "The implication: the agent-memory field's reliability story is built almost entirely on vendor self-reporting and paper claims, with effectively no public, neutral, reproducible benchmark coverage. A vendor that posts honest leaderboard scores would have category-leading transparency-as-positioning — there is nobody to compete with for that ground."
    ],
    link: { href: '/analyses/product-benchmark-matrix', label: 'See the product × benchmark matrix' },
    source: 'Recomputed from the catalog at every build · method in analysis.md §24.2'
  },
  {
    slug: 'mcp-spec-third-substrate',
    n: 3,
    headline: "The MCP spec is the catalog's #3 inbound substrate",
    metaDescription:
      'Inbound runtime-dependency counts: Claude 62 · GPT 52 · MCP spec 34. A protocol spec ranks above every model except Claude and GPT.',
    figure: 'Inbound runtime-deps: Claude 62 · GPT 52 · MCP spec 34 · Gemini 22 · Qwen 16',
    cardSoWhat:
      "From the T2-1 runtime-dependency graph (212 edges of 'X depends on Y at runtime'). A protocol specification ranking #3 — ahead of every foundation model except Claude and GPT — is the finding that wasn't visible in citation-graph hubs. The MCP spec is becoming a substrate, not just a protocol.",
    body: [
      "The T2-1 runtime-dependency graph captures 212 edges of the form 'X depends on Y at runtime' (not 'X cites Y'). Counted by inbound edges — i.e. how many catalog entries treat the target as a runtime substrate — the top five are: Claude (62), GPT (52), the Model Context Protocol specification (34), Gemini (22), Qwen (16).",
      "A protocol specification ranking third — ahead of every foundation model except Claude and GPT — is the finding that wasn't visible in the citation-graph hubs. Citations measure scholarly influence; runtime dependencies measure adoption-as-substrate. The MCP spec is being adopted as substrate, not just as a wire format.",
      "This matters because it changes the competitive frame. If MCP is a substrate, then 'MCP server X' systems are not protocol-of-the-week experiments — they're load-bearing components of the agent stack with the same dependency surface as 'agent depends on GPT'. The implication is that MCP-server entries deserve substrate-grade ranking treatment (they currently rank lower than they should on adoption signal), and the spec itself is closer to a foundation-model-tier dependency than to a side feature."
    ],
    link: { href: '/graph?edges=runtime-dependency', label: 'See the runtime-dependency graph' },
    source: 'analysis.md §23'
  },
  {
    slug: 'graphiti-mcp-bridge-node',
    n: 4,
    headline: 'Graphiti MCP Server is the most under-acknowledged connector in the catalog',
    metaDescription:
      "Graphiti MCP Server has 0 inbound edges but 0.71 normalised betweenness — the catalog's most load-bearing low-citation bridge.",
    figure: '0 inbound edges · 0.71 normalised betweenness — highest non-trivial in the graph',
    cardSoWhat:
      'Sits on the shortest path between the MCP-spec substrate cluster and the Zep / Graphiti citation-anchor pair. A high-betweenness / low-inbound node is the structural definition of an under-acknowledged-but-load-bearing connector. Top-5 bridge-surprise: Graphiti MCP Server, MAGMA, Memformers, MemEvolve, RGMem.',
    body: [
      "Betweenness centrality measures how often a node sits on the shortest path between two other nodes. A node with high betweenness but low inbound-degree is, by definition, an under-acknowledged-but-load-bearing connector — nobody points at it, but the graph routes through it. The catalog's top such node is Graphiti MCP Server: 0 inbound edges, 0.71 normalised betweenness — the highest non-trivial value in the entire graph.",
      "Why it matters structurally: Graphiti MCP Server sits on the shortest path between the MCP-spec substrate cluster (Claude Desktop, Cursor, Windsurf, the MCP spec itself) and the Zep / Graphiti citation-anchor pair (Zep is the most-cited entry in the dedicated-memory-layer category; Graphiti is its open-source graph backend). If you removed Graphiti MCP Server from the graph, the MCP-tooling cluster and the dedicated-memory-graph cluster would disconnect from each other.",
      'The top-five bridge-surprise list is Graphiti MCP Server, MAGMA, Memformers, MemEvolve, RGMem. These are systems with high structural importance but very low explicit citation — the catalog finds them because the typed-edge graph surfaces structural roles that citation hubs miss.'
    ],
    link: { href: '/analyses/influence', label: 'See the bridge-surprises callout' },
    source: 'analysis.md §26.2'
  },
  {
    slug: 'fm-three-vendor-concentration',
    n: 5,
    headline: '77% of FM-dependent products lock onto three vendors',
    metaDescription:
      '108 of 140 FM-dependent products in the catalog name OpenAI, Anthropic, or Google. The substrate-dependency risk is on three labs.',
    figure: '108 of 140 FM-dependent rows depend on OpenAI / Anthropic / Google',
    cardSoWhat:
      'Of the 140 rows (~16% of non-FM rows) that name a foundation model, 77.1% sit on the OpenAI / Anthropic / Google single-vendor-risk tier. The long tail (Qwen 16, Mistral 12, Cohere 8, DeepSeek 6, Jamba 3, Grok 2, Nova 2) is sparse. The substrate-risk map is concentrated on three labs.',
    body: [
      "Of the catalog's non-FM rows, 140 explicitly name a foundation model in their llm-lock or runtime-dependency cells — about 16% of the non-FM population. Within that 140, 108 (77.1%) depend on OpenAI, Anthropic, or Google. The long tail is sparse: Qwen 16, Mistral 12, Cohere 8, DeepSeek 6, Jamba 3, Grok 2, Nova 2.",
      "The substrate-dependency-risk implication is that any TOS change, pricing change, or output-policy change at OpenAI, Anthropic, or Google ripples into roughly four-fifths of the named-FM dependency surface in the catalog. The other 32 FM-dependent rows are distributed across seven labs — meaning the diversification tail is too thin to absorb concentrated-vendor disruption.",
      'The strategic read: a vendor positioning as the "second source" for FM-dependent agent products (multi-model routing, model-agnostic memory, vendor-neutral abstractions) is selling into a market that has 108 willing buyers whenever single-vendor-risk anxiety spikes. Today the market mostly pretends single-vendor risk isn\'t there.'
    ],
    link: { href: '/analyses/trajectory', label: 'See the substrate-dependency risk panel' },
    source: 'analysis.md §19.5 + §21.3'
  }
];

export function findingBySlug(slug: string): Finding | null {
  return findings.find((f) => f.slug === slug) ?? null;
}

/** Numbers for the {tokens} in the findings, computed from the catalog. */
export type LiveNumbers = Record<string, string>;

/** The findings with every {token} filled from `live`. */
export function withLiveNumbers(list: Finding[], live: LiveNumbers): Finding[] {
  const fill = (t: string) => t.replace(/\{(\w+)\}/g, (m, k: string) => live[k] ?? m);
  return list.map((f) => ({ ...f, headline: fill(f.headline), metaDescription: fill(f.metaDescription), figure: fill(f.figure), cardSoWhat: fill(f.cardSoWhat), body: f.body.map(fill) }));
}
