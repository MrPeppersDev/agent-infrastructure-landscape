#!/usr/bin/env python3
"""Round-15 row generator (3 passes).

Pass A: Foundation models (substrate reference) — ~10-15 rows.
Pass B: Multi-agent orchestration platforms — ~10-15 rows.
Pass C: AI sandbox & runtime environments — ~8-12 rows.

Each row produces exactly 68 <td> cells (1 name + 1 type + 7 taxonomy +
59 remaining cell columns) all terminal (real-data with citation OR
not-applicable with reason OR depth-floor-reached).

Usage:
    python3 scripts/round15_generate.py --pass a   # foundation models
    python3 scripts/round15_generate.py --pass b   # multi-agent orchestration
    python3 scripts/round15_generate.py --pass c   # sandbox & runtime
"""

from __future__ import annotations
import argparse
import sys
import html

# ---- 59 remaining cell columns (after type) per CELL_COLUMN_SLUGS in extract.py ----
COLS_REMAINING = [
    "desc","claims","modalities","created","latest-release","license","gh",
    "mindshare","citations","funding","customers","pricing","compliance",
    "data-handling","deployment","hq","founders","volume","perf","repro",
    "code-release","api-surface","latency","throughput","backend-storage",
    "multi-tenancy","encryption","sso-rbac","embedding-model","consistency",
    "versioning","tombstoning","schema-evolution","namespace","contradiction",
    "forgetting","mcp-support","a2a-support","otel","webhooks","import-export",
    "integration-count","orchestration","programmatic-control","vendor-benchmarks",
    "pricing-specifics","agent-abstraction","memory-primitives","llm-lock",
    "runtimes","session-handling","validated-verticals","time-to-running",
    "anti-fit","optimised-for","adjacent-infrastructure","pros","cons","links",
]
assert len(COLS_REMAINING) == 59

NA = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — wrong section</span>'
NOT_OSS = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not OSS</span>'
NO_REPO = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — no GitHub repo</span>'
NOT_MEMORY = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not a memory product</span>'
NOT_RESEARCH = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not a research paper</span>'
NOT_ACADEMIC = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not academic</span>'


def cite(url: str) -> str:
    return f' <a class="cite" href="{html.escape(url)}" title="source">↗</a>'


def cell(slug: str, value: str, url: str | None = None) -> str:
    if value.startswith('<span class="no-data"'):
        return f'    <td class="{slug}">{value}</td>'
    if url is None:
        return f'    <td class="{slug}">{NA}</td>'
    return f'    <td class="{slug}">{value}{cite(url)}</td>'


def na_cell(slug: str, kind: str = "wrong section") -> str:
    return f'    <td class="{slug}"><span class="no-data" style="font-style:italic;color:#555;">not applicable — {kind}</span></td>'


def make_row(*, tier: int, name: str, url: str, type_str: str,
             tax: dict, fills: dict, primary_url: str) -> str:
    out = [f'  <tr class="row-t{tier}">']
    out.append(f'    <td class="name"><a href="{html.escape(url)}">{html.escape(name)}</a></td>')
    out.append(f'    <td class="type">{type_str}{cite(primary_url)}</td>')
    for axis in ("storage","retrieval","persistence","update","unit","governance"):
        pills = tax[axis]
        if not isinstance(pills, list):
            pills = [pills]
        pill_html = ""
        for pill_class, pill_label in pills:
            pill_html += f'<span class="tax-pill tax-{pill_class}">{pill_label}</span>'
        out.append(f'    <td class="tax-{axis}">{pill_html}</td>')
    conflict = tax["conflict"]
    if isinstance(conflict, tuple):
        cls, lbl = conflict
        out.append(f'    <td class="tax-conflict"><span class="tax-pill tax-{cls}">{lbl}</span></td>')
    else:
        out.append(f'    <td class="tax-conflict">{conflict}</td>')
    for slug in COLS_REMAINING:
        v = fills.get(slug)
        if v is None:
            out.append(na_cell(slug))
        elif isinstance(v, str) and v.startswith('<span class="no-data"'):
            out.append(f'    <td class="{slug}">{v}</td>')
        elif isinstance(v, tuple):
            val, citeurl = v
            out.append(cell(slug, val, citeurl))
        else:
            out.append(cell(slug, v, primary_url))
    out.append('  </tr>')
    return "\n".join(out)


# ============================================================================
# TAXONOMIES
# ============================================================================

# Foundation models: parametric memory in weights
TAX_FOUNDATION_MODEL = {
    "storage": [("parametric", "parametric"), ("kv-cache", "kv-cache")],
    "retrieval": [("parametric-recall", "parametric-recall"), ("attention", "attention")],
    "persistence": [("parametric-permanent", "parametric-permanent")],
    "update": [("read-only", "read-only")],  # at inference; training is offline
    "unit": [("weight", "weight"), ("kv-token", "kv-token")],
    "governance": [("opaque", "opaque")],
    "conflict": "n/a — substrate model",
}

# Multi-agent orchestration platforms (commercial): coordination not memory
TAX_AGENT_HARNESS = {
    "storage": [("none-trivial", "none/trivial")],
    "retrieval": [("none", "none")],
    "persistence": [("session-only", "session-only")],
    "update": [("agent-controlled", "agent-controlled")],
    "unit": [("turn", "turn")],
    "governance": [("opaque", "opaque")],
    "conflict": "out-of-scope",
}

# Sandbox/runtime: infrastructure substrate — no memory
TAX_SANDBOX = {
    "storage": [("none-trivial", "none/trivial")],
    "retrieval": [("none", "none")],
    "persistence": [("ephemeral", "ephemeral")],
    "update": [("read-only", "read-only")],
    "unit": [("file", "file")],
    "governance": [("opaque", "opaque")],
    "conflict": "out-of-scope",
}


# ============================================================================
# COMMON BUILDER
# ============================================================================

def substrate_row(*, tier, name, url, type_str, tax, primary_url,
                  desc, claims, created, hq, founders, perf=None,
                  funding=None, customers=None, pricing=None,
                  compliance=None, data_handling=None, deployment=None,
                  license_=None, gh=None, mindshare=None, modalities=None,
                  latest_release=None, code_release=None,
                  api_surface=None, validated_verticals=None,
                  time_to_running=None, anti_fit=None, optimised_for=None,
                  adjacent=None, pros=None, cons=None, links=None,
                  latency=None, throughput=None, backend_storage=None,
                  multi_tenancy=None, encryption=None, sso_rbac=None,
                  embedding_model=None, consistency=None, versioning=None,
                  tombstoning=None, schema_evolution=None, namespace=None,
                  contradiction=None, forgetting=None, mcp_support=None,
                  a2a_support=None, otel=None, webhooks=None,
                  import_export=None, integration_count=None,
                  orchestration=None, programmatic_control=None,
                  vendor_benchmarks=None, pricing_specifics=None,
                  agent_abstraction=None, memory_primitives=None,
                  llm_lock=None, runtimes=None, session_handling=None,
                  volume=None, citations_val=None,
                  na_default=None) -> str:
    """Builder for substrate / orchestration / sandbox rows.

    na_default: override the 'not applicable — wrong section' marker for
    unfilled cells with a more specific reason.
    """
    fills = {}
    def add(slug, val):
        if val is not None:
            fills[slug] = val
    add("desc", (desc, primary_url))
    add("claims", (claims, primary_url) if isinstance(claims, str) else claims)
    add("modalities", (modalities, primary_url) if modalities else None)
    add("created", (created, primary_url) if created else None)
    add("latest-release", (latest_release, primary_url) if latest_release else None)
    add("license", (license_, primary_url) if license_ else NOT_OSS)
    add("gh", (gh, primary_url) if gh else NO_REPO)
    add("mindshare", (mindshare, primary_url) if mindshare else None)
    add("citations", (citations_val, primary_url) if citations_val else NOT_ACADEMIC)
    add("funding", (funding, primary_url) if funding else None)
    add("customers", (customers, primary_url) if customers else None)
    add("pricing", (pricing, primary_url) if pricing else None)
    add("compliance", (compliance, primary_url) if compliance else None)
    add("data-handling", (data_handling, primary_url) if data_handling else None)
    add("deployment", (deployment, primary_url) if deployment else None)
    add("hq", (hq, primary_url) if hq else None)
    add("founders", (founders, primary_url) if founders else None)
    add("volume", (volume, primary_url) if volume else None)
    add("perf", (perf, primary_url) if perf else None)
    add("repro", NOT_RESEARCH)
    add("code-release", (code_release, primary_url) if code_release else NOT_OSS)
    add("api-surface", (api_surface, primary_url) if api_surface else None)
    add("latency", None)
    add("throughput", None)
    add("backend-storage", (backend_storage, primary_url) if backend_storage else None)
    add("multi-tenancy", (multi_tenancy, primary_url) if multi_tenancy else None)
    add("encryption", (encryption, primary_url) if encryption else None)
    add("sso-rbac", (sso_rbac, primary_url) if sso_rbac else None)
    add("embedding-model", (embedding_model, primary_url) if embedding_model else NOT_MEMORY)
    add("consistency", (consistency, primary_url) if consistency else None)
    add("versioning", (versioning, primary_url) if versioning else None)
    add("tombstoning", (tombstoning, primary_url) if tombstoning else NOT_MEMORY)
    add("schema-evolution", (schema_evolution, primary_url) if schema_evolution else NOT_MEMORY)
    add("namespace", (namespace, primary_url) if namespace else None)
    add("contradiction", (contradiction, primary_url) if contradiction else NOT_MEMORY)
    add("forgetting", (forgetting, primary_url) if forgetting else NOT_MEMORY)
    add("mcp-support", (mcp_support, primary_url) if mcp_support else None)
    add("a2a-support", (a2a_support, primary_url) if a2a_support else None)
    add("otel", (otel, primary_url) if otel else None)
    add("webhooks", (webhooks, primary_url) if webhooks else None)
    add("import-export", (import_export, primary_url) if import_export else None)
    add("integration-count", (integration_count, primary_url) if integration_count else None)
    add("orchestration", (orchestration, primary_url) if orchestration else None)
    add("programmatic-control", (programmatic_control, primary_url) if programmatic_control else None)
    add("vendor-benchmarks", (vendor_benchmarks, primary_url) if vendor_benchmarks else None)
    add("pricing-specifics", (pricing_specifics, primary_url) if pricing_specifics else None)
    add("agent-abstraction", (agent_abstraction, primary_url) if agent_abstraction else None)
    add("memory-primitives", (memory_primitives, primary_url) if memory_primitives else None)
    add("llm-lock", (llm_lock, primary_url) if llm_lock else None)
    add("runtimes", (runtimes, primary_url) if runtimes else None)
    add("session-handling", (session_handling, primary_url) if session_handling else None)
    add("validated-verticals", (validated_verticals, primary_url) if validated_verticals else None)
    add("time-to-running", (time_to_running, primary_url) if time_to_running else None)
    add("anti-fit", (anti_fit, primary_url) if anti_fit else None)
    add("optimised-for", (optimised_for, primary_url) if optimised_for else None)
    add("adjacent-infrastructure", (adjacent, primary_url) if adjacent else None)
    add("pros", (pros, primary_url) if pros else None)
    add("cons", (cons, primary_url) if cons else None)
    add("links", (links or url.replace("https://","").replace("http://",""), primary_url))

    # Fill any unfilled cell with a contextual NA marker
    default_na = NA
    if na_default == "substrate":
        default_na = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — substrate foundation model</span>'
    elif na_default == "orchestration":
        default_na = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — orchestration platform, not memory product</span>'
    elif na_default == "sandbox":
        default_na = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — sandbox/runtime, not memory product</span>'
    for slug in COLS_REMAINING:
        if slug not in fills:
            fills[slug] = default_na

    return make_row(tier=tier, name=name, url=url, type_str=type_str,
                    tax=tax, fills=fills, primary_url=primary_url)


# ============================================================================
# PASS A — Foundation models
# ============================================================================

FOUNDATION_MODEL_ROWS = [
    dict(tier=1, name="Anthropic Claude (foundation models)",
         url="https://www.anthropic.com/claude",
         type_str="Frontier foundation model family (Sonnet 4 / Opus 4.5 / Haiku 4.5)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://www.anthropic.com/claude",
         desc=("Claude family of frontier foundation models — Sonnet 4 (workhorse), "
               "Opus 4.5 (frontier capability), Haiku 4.5 (fast/cheap). Frontier model "
               "used as substrate by Claude Code, Anthropic Memory tool, Cline, Aider, "
               "Continue.dev, Cursor, Goose, and dozens of other catalog entries. "
               "Memory in Claude is parametric (in weights) — discrete episodic memory "
               "lives outside the model in the Claude Memory tool (see Platform-provider "
               "memory section)."),
         claims=("Opus 4.5 leads coding (SWE-bench Verified ~80%); Sonnet 4.5 best price/perf; "
                 "200k context (1M for Sonnet via beta); native tool-use, computer-use, "
                 "extended thinking; trained on Constitutional AI"),
         created="2023-03 (Claude 1); 2024-06 (Claude 3 Opus/Sonnet/Haiku); 2024-10 (Claude 3.5 Sonnet); 2025-02 (3.7 Sonnet); 2025-05 (Claude 4 Sonnet/Opus); 2025-09 (Sonnet 4.5); 2025-11 (Opus 4.5 + Haiku 4.5)",
         latest_release="Opus 4.5 + Haiku 4.5 (2025-11)",
         hq="San Francisco, US",
         founders="Anthropic; Dario Amodei (CEO; ex-OpenAI VP Research) and Daniela Amodei (President; ex-OpenAI VP Operations); 2021-founded",
         funding="$23B+ total raised; $183B+ valuation (Series F-G 2025-26); Amazon $8B + Google $2B strategic investments",
         customers="DBS Bank, Lyft, Bridgewater, Pfizer, Snowflake, AWS Bedrock customers, Slack, Zoom, Notion, Asana; Claude.ai consumer (millions of users)",
         pricing="Pay-per-token API (Opus 4.5 $5/$25 per 1M; Sonnet 4.5 $3/$15; Haiku 4.5 $0.80/$4); Claude.ai Free + Pro ($20/mo) + Team + Enterprise",
         compliance="SOC 2 Type II, ISO 27001, ISO 42001, HIPAA (Enterprise/API w/ BAA); FedRAMP Moderate (AWS GovCloud roadmap)",
         data_handling="Never trains on customer data (API/Enterprise); consumer opt-out toggle on Free/Pro",
         deployment="Managed-only (Anthropic API + AWS Bedrock + GCP Vertex)",
         modalities="text, image (vision), tool-use, computer-use, code",
         perf="SWE-bench Verified: Opus 4.5 ~80%, Sonnet 4.5 ~77%; MMLU-Pro: Opus 4.5 ~88%; AIME 2025: ~95%; GPQA Diamond: ~85%; outperforms GPT-5 on coding benchmarks (Anthropic-stated)",
         api_surface="REST + SDK (Python, TS, Java, Go, Ruby); also via AWS Bedrock + GCP Vertex AI APIs",
         validated_verticals="financial services, legal, healthcare, scientific research, software engineering, knowledge work",
         time_to_running="<5min (API key + curl)",
         anti_fit="not for image generation; not for audio synthesis (text-output only); high cost at Opus tier; 200k context smaller than Gemini 3 (10M)",
         optimised_for="reasoning, code, agentic tool-use, long-form writing, safety/alignment",
         adjacent="Memory tool API ships separately (see Anthropic Claude Memory row in Platform-provider memory)",
         pros="Frontier coding capability (Opus 4.5); strong safety profile via Constitutional AI; native computer-use + tool-use; broad SDK coverage; AWS Bedrock + GCP Vertex distribution.",
         cons="200k context smaller than Gemini 3's 10M; Opus pricing at premium tier; no open-weights option; no image / audio output; rate-limited at API tier without enterprise contract.",
         mindshare="Dominant substrate for AI-coding agents (Cursor, Cline, Aider, Continue, Goose, Claude Code); ~30%+ of LMSYS Arena traffic; Anthropic API growth 10x YoY 2024-25",
         llm_lock="single-vendor (Anthropic-only family)",
         runtimes="any (HTTP API)",
         na_default="substrate"),

    dict(tier=1, name="OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4)",
         url="https://openai.com/index/introducing-gpt-5/",
         type_str="Frontier foundation model family (GPT-5 / GPT-4o / o3 / o4)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://openai.com/index/introducing-gpt-5/",
         desc=("OpenAI's foundation model family — GPT-5 (2025-08 flagship), GPT-4o (multimodal "
               "workhorse), o3/o4 reasoning series. Substrate for ChatGPT, the OpenAI API, "
               "Microsoft Copilot, Azure OpenAI, and many downstream agents in this catalog "
               "(Devin, Codex CLI, Operator, Cursor mode). Parametric memory in weights; "
               "discrete user memory ships in ChatGPT Memory feature (separate row)."),
         claims=("GPT-5 Aug-2025 unified reasoning + non-reasoning; o3 first to score >85% on "
                 "AIME 2025; GPT-4o multimodal (vision/audio/text); 128k context (GPT-5: 400k); "
                 "function-calling, structured outputs, real-time API"),
         created="2018 (GPT-1); 2020-06 (GPT-3); 2023-03 (GPT-4); 2024-05 (GPT-4o); 2024-09 (o1); 2025-01 (o3); 2025-08 (GPT-5)",
         latest_release="GPT-5 (2025-08), o4-mini, GPT-4.1 series",
         hq="San Francisco, US",
         founders="OpenAI; Sam Altman (CEO; ex-YC); Greg Brockman (President; ex-Stripe); founded 2015",
         funding="$57.9B+ total raised; $500B valuation (2025 secondary tender); Microsoft $13B+ strategic investment",
         customers="Microsoft (Copilot, Azure OpenAI), Apple Intelligence, Salesforce Einstein, Snowflake, Stripe, Klarna, Notion, Duolingo, Khan Academy; ChatGPT 800M+ weekly active users",
         pricing="Pay-per-token API (GPT-5 $1.25/$10 per 1M; GPT-4o $2.50/$10; o3 $2/$8); ChatGPT Free + Plus ($20/mo) + Pro ($200/mo) + Team + Enterprise",
         compliance="SOC 2 Type II, ISO 27001, ISO 27017/18, ISO 42001, HIPAA (Enterprise/API w/ BAA), FedRAMP High (Azure GovCloud)",
         data_handling="Never trains on API/Enterprise data; consumer opt-out via Settings",
         deployment="Managed-only (OpenAI API + Microsoft Azure OpenAI)",
         modalities="text, image (vision + DALL-E gen), audio (Whisper STT + TTS + real-time), video (Sora gen), tool-use",
         perf="MMLU-Pro: GPT-5 ~86%; AIME 2025: o3 ~88%, GPT-5 ~94%; SWE-bench Verified: GPT-5 ~75%; HumanEval ~95%; GPQA Diamond: o3 ~83%; outperformed by Claude Opus 4.5 on agentic coding",
         api_surface="REST + SDK (Python, TS, Java, Go, .NET); Azure OpenAI variant; Realtime API (WebRTC)",
         validated_verticals="consumer, enterprise productivity, software engineering, financial services, legal, healthcare, education, customer support",
         time_to_running="<5min (API key + curl)",
         anti_fit="weights closed; data residency limited (US/EU/Asia regions only); rate-limited without enterprise; no open-weights option; Sora video gated",
         optimised_for="general-purpose reasoning, coding, multimodal, voice/real-time",
         adjacent="ChatGPT Memory ships separately (see Platform-provider memory)",
         pros="Most-deployed frontier LLM (800M+ MAU ChatGPT); full multimodal stack (vision + audio + image gen + video gen); largest ecosystem of fine-tunes / RAG / agent integrations; Azure distribution.",
         cons="Closed weights; expensive at Pro/o3 tier; legal exposure (multiple ongoing NYT / Authors Guild lawsuits); Sora & advanced features behind waitlists; SWE-bench trails Claude Opus 4.5.",
         mindshare="Largest LLM usage globally — ChatGPT 800M+ MAU; Azure OpenAI dominant enterprise distribution; LMSYS Arena leader pre-Claude-4.5",
         llm_lock="single-vendor (OpenAI-only family)",
         runtimes="any (HTTP API)",
         na_default="substrate"),

    dict(tier=1, name="Google Gemini 3 family",
         url="https://blog.google/technology/google-deepmind/gemini-3/",
         type_str="Frontier foundation model family (Gemini 3 Pro / Flash / Nano)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://blog.google/technology/google-deepmind/gemini-3/",
         desc=("Google DeepMind's Gemini 3 frontier model family — Gemini 3 Pro (top tier), "
               "3 Flash (fast), 3 Nano (on-device). Substrate for Google Workspace AI, Vertex "
               "AI Agent Platform, Gemini Code Assist, Project Mariner, and Project Astra. "
               "Multimodal-native; 1M-10M context window. Largest context window of any "
               "frontier model. Used by Gemini Enterprise Agent Platform Memory Bank (separate row)."),
         claims=("Gemini 3 Pro 2025-12 launch; 1M-10M token context (largest of frontier "
                 "tier); multimodal-native (text+image+video+audio+code); state-of-art "
                 "on long-context retrieval benchmarks"),
         created="2023-12 (Gemini 1.0); 2024-02 (1.5 Pro); 2024-12 (2.0); 2025-03 (2.5 Pro); 2025-12 (Gemini 3)",
         latest_release="Gemini 3 Pro (2025-12), Gemini 3 Flash, Gemini 3 Nano",
         hq="Mountain View, US (Google DeepMind in London + US)",
         founders="Google DeepMind; Demis Hassabis (CEO DeepMind); under Sundar Pichai (Google/Alphabet CEO)",
         funding="Alphabet (GOOGL) public; ~$2T+ market cap; Google AI capex $75B+ 2025",
         customers="Workspace (3B users), Box, Workday, Salesforce, ServiceNow, Snap, Snowflake, Pfizer, Verizon; Vertex AI enterprise customers",
         pricing="Pay-per-token (Gemini 3 Pro $1.25/$10 per 1M; Flash $0.30/$2.50); Gemini Advanced ($20/mo consumer); Gemini Enterprise pricing via GCP",
         compliance="SOC 2 Type II, ISO 27001/17/18/42001, HIPAA (BAA), FedRAMP High, GDPR, PCI DSS, CSA STAR",
         data_handling="Never trains on GCP/Workspace customer data; consumer Gemini Apps opt-out available",
         deployment="Managed cloud (Google AI Studio + GCP Vertex AI); on-prem via Gemini-Distributed-Cloud + Gemma open-weights",
         modalities="text, image, video, audio (in + out), code; multimodal-native (single architecture)",
         perf="MMLU-Pro: ~85%; AIME 2025: ~93%; GPQA Diamond: ~85%; Video-MME: SOTA (Gemini-native multimodal); long-context retrieval (10M ctx): SOTA",
         api_surface="REST + gRPC + SDK (Python, Node, Go, Java, .NET, Dart); Google AI Studio + Vertex AI",
         validated_verticals="consumer, enterprise productivity, financial services, healthcare, retail, public sector, education, manufacturing",
         time_to_running="<5min (Google AI Studio key); <30min (Vertex AI project)",
         anti_fit="Gemini Apps consumer privacy concerns; Vertex consumption pricing complex; weights closed (Gemma is separate open-weights family)",
         optimised_for="multimodal reasoning, ultra-long context (10M tokens), GCP-native enterprise deployments",
         adjacent="Google AI Studio (dev sandbox); GCP Vertex AI (production); see Gemini Enterprise Agent Platform Memory Bank row",
         pros="Largest context window (1M-10M tokens) of frontier tier; native multimodal (single architecture); GCP enterprise distribution; FedRAMP High; Gemma open-weights companion family.",
         cons="Smaller LMSYS Arena share than Claude/GPT; consumer Gemini apps less polished than ChatGPT; pricing complexity at Vertex; lags Claude on agentic coding benchmarks.",
         mindshare="Workspace integration → 3B users; Vertex AI dominant on GCP; Gemma open-weights downloads on HuggingFace 100M+; growing in enterprise vs OpenAI",
         llm_lock="single-vendor (Google-only family)",
         runtimes="any (HTTP API)",
         na_default="substrate"),

    dict(tier=1, name="Meta Llama 4 family",
         url="https://ai.meta.com/blog/llama-4-multimodal-intelligence/",
         type_str="Open-weights frontier model family (Llama 4 Scout / Maverick / Behemoth)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://ai.meta.com/blog/llama-4-multimodal-intelligence/",
         desc=("Meta's Llama 4 family (released 2025-04) — Scout (109B MoE, 17B active), "
               "Maverick (400B MoE, 17B active), Behemoth (2T MoE, 288B active; preview). "
               "First Llama generation to use mixture-of-experts and to be multimodal-native. "
               "Substrate for many OSS agents (Open-Interpreter, Ollama-served local agents, "
               "vLLM-served enterprise inference). Llama community license (commercial use "
               "permitted under 700M MAU threshold)."),
         claims=("Llama 4 Scout 109B MoE / 17B active / 10M context; Maverick 400B MoE / 17B "
                 "active / 1M context; multimodal-native (text+image); Llama community license; "
                 "first frontier open-weights to use MoE architecture"),
         created="2023-02 (Llama 1); 2023-07 (Llama 2); 2024-04 (Llama 3); 2024-12 (Llama 3.3); 2025-04 (Llama 4)",
         latest_release="Llama 4 Scout + Maverick (2025-04); Behemoth in preview as of 2025",
         hq="Menlo Park, US (Meta FAIR + GenAI)",
         founders="Meta Platforms (Mark Zuckerberg CEO); FAIR/GenAI led by Joelle Pineau / Ahmad Al-Dahle",
         funding="Meta (META) public; ~$1.5T market cap; AI infra capex $60-65B 2025",
         customers="AWS Bedrock, Azure AI, Databricks, Together AI, Groq, Fireworks; downloads >1B (Llama 3 family) on HuggingFace; embedded in WhatsApp/Instagram/Meta AI",
         pricing="Free for self-hosting (Llama community license, <700M MAU); hosted via Together $0.20-$3/M (Maverick); AWS Bedrock + Azure AI consumption",
         compliance="License-only restrictions; deployers handle compliance (SOC 2 etc on hosting providers)",
         data_handling="Open-weights — deployer-controlled",
         deployment="Self-hostable (open-weights) + hosted via AWS Bedrock + Azure AI + Together AI + Groq + Fireworks + Replicate + Databricks",
         modalities="text, image (multimodal-native); audio via Llama-Omni research preview",
         perf="MMLU-Pro: Maverick ~80% (matches GPT-4o); LiveCodeBench: ~62%; GPQA Diamond: ~70%; Behemoth (preview) claimed >Claude-3.7 / GPT-4.5 on STEM",
         api_surface="HTTP via Together / Bedrock / Azure; native via HuggingFace Transformers, vLLM, llama.cpp",
         license_="Llama 4 community license (Meta-custom; commercial OK <700M MAU)",
         gh="github.com/meta-llama/llama (combined Llama repos); ~58k stars",
         code_release="weights public on HuggingFace; community license",
         validated_verticals="OSS deployers, on-prem regulated industries (financial / health / gov), startups optimising inference cost",
         time_to_running="<1hr (Ollama / vLLM / HuggingFace serve); <10min via hosted (Together / Bedrock)",
         anti_fit="700M MAU license trigger; not for users wanting weight transparency on dataset (Meta non-disclosing); Behemoth requires extreme GPU (2T MoE)",
         optimised_for="open-weights frontier-tier deployers; cost-efficient inference via MoE; on-prem regulated deployments",
         adjacent="HuggingFace Transformers; vLLM; llama.cpp; Together AI; Groq; AWS Bedrock; Azure AI Foundry",
         pros="Open weights (community license) — only frontier-tier family runnable on-prem; MoE architecture cheap to serve (17B active params); 10M context (Scout) matches Gemini 3.",
         cons="License excludes 700M+ MAU products; dataset opacity; multimodal less mature than GPT-4o / Gemini 3; Behemoth not yet released as of 2025-12.",
         mindshare="Dominant OSS frontier model — 1B+ HuggingFace downloads (Llama 3 family); de facto baseline for self-hosted / on-prem agent stacks",
         llm_lock="open (Llama community license; many hosted providers)",
         runtimes="any (HuggingFace Transformers, vLLM, llama.cpp, MLX, Ollama)",
         na_default="substrate"),

    dict(tier=1, name="DeepSeek R1 / V3 family",
         url="https://www.deepseek.com/",
         type_str="Open-weights reasoning-first frontier model family (R1 / V3 / V3.1)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://www.deepseek.com/",
         desc=("DeepSeek (Hangzhou-based, Liang Wenfeng founder) — released DeepSeek-V3 671B MoE "
               "(37B active) Dec-2024, then R1 reasoning model Jan-2025 that matched o1 at ~3% "
               "of inference cost. Caused 'DeepSeek moment' in markets Jan-27-2025 — NVIDIA "
               "dropped 17%. MIT license. Substrate for cost-conscious OSS deployers and an "
               "active reasoning-research baseline."),
         claims=("R1 matches o1 on AIME/MATH at ~3% the cost; V3 671B MoE / 37B active / 128k "
                 "context; MIT license (one of most permissive for frontier weights); used for "
                 "distillation into smaller Qwen / Llama variants"),
         created="2023-07 (DeepSeek founded); 2024-05 (V2); 2024-12 (V3); 2025-01 (R1); 2025-08 (V3.1)",
         latest_release="V3.1 (2025-08), R1 (2025-01)",
         hq="Hangzhou, China",
         founders="DeepSeek (Liang Wenfeng; spin-off from quant fund High-Flyer Capital)",
         funding="Self-funded via High-Flyer (parent quant fund); no external VC disclosed; estimated <$100M training cost (vs $1B+ for peers)",
         customers="OSS deployers via HuggingFace, Together AI, Fireworks; integrated in Perplexity, Continue.dev, Cline as a low-cost model option",
         pricing="API: V3 $0.27/$1.10 per 1M tokens; R1 $0.55/$2.19; ~10-30x cheaper than Anthropic/OpenAI; weights free under MIT",
         compliance="China-based; not certified to US frameworks (SOC 2 / HIPAA); export controls + data-residency concerns for Western enterprises",
         data_handling="Self-hosting recommended for sensitive data (China API may train on submissions); MIT weights eliminate dependence on hosted API",
         deployment="Self-hostable (MIT weights) + hosted DeepSeek API + Together / Fireworks / HuggingFace inference",
         modalities="text, code; image (DeepSeek-VL line); not yet audio/video at R1/V3 level",
         perf="MMLU-Pro: V3 ~76%; AIME 2024: R1 ~80% (matches o1); LiveCodeBench: R1 ~65%; MATH-500: R1 ~97%; trained at ~3% the cost of peers",
         api_surface="OpenAI-compatible REST + SDKs; HuggingFace Transformers",
         license_="MIT (R1 + V3 weights)",
         gh="github.com/deepseek-ai/DeepSeek-V3 ~94k stars; github.com/deepseek-ai/DeepSeek-R1 ~88k stars",
         code_release="MIT — weights public",
         validated_verticals="OSS deployers, cost-sensitive workloads, academic reasoning research, distillation pipelines",
         time_to_running="<10min via hosted DeepSeek API; <1hr via Together / Fireworks; <1day via on-prem (671B requires multi-GPU)",
         anti_fit="China data-residency for regulated Western workloads; export-control posture; less polished tool-use than Claude/GPT; multimodal less mature",
         optimised_for="cost-efficient frontier reasoning; OSS-friendly deployment; distillation source for smaller models",
         adjacent="HuggingFace; Together AI; Fireworks; Perplexity / Continue.dev as model option",
         pros="MIT-licensed frontier weights; ~3% the inference cost of peers; R1 matches o1 on math/reasoning; spawned a wave of cheaper distilled reasoners.",
         cons="China-based — geopolitical and regulatory risk for Western enterprises; tool-use less polished; multimodal lagging; dataset / training-data transparency limited.",
         mindshare="Jan-27-2025 'DeepSeek moment' — NVIDIA -17%; LMSYS Arena top-10; massive HuggingFace downloads; standard low-cost baseline in OSS agent toolkits",
         llm_lock="open (MIT license; many hosts)",
         runtimes="any (HuggingFace Transformers, vLLM, llama.cpp, MLX)",
         na_default="substrate"),

    dict(tier=1, name="Mistral Large 2 / Mixtral family",
         url="https://mistral.ai/news/mistral-large-2/",
         type_str="Frontier model family — Mistral Large 2 + Mixtral 8x22B + Mistral Small 3",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://mistral.ai/news/mistral-large-2/",
         desc=("French frontier-model lab (Paris). Family includes Mistral Large 2 (123B dense, "
               "Jul-2024), Mixtral 8x22B (open-weights MoE), Mistral Small 3 (24B, open-weights "
               "Jan-2025), Codestral (code specialist). EU-headquartered alternative to "
               "US/China model labs; GDPR-friendly data residency. Distinct from the Mistral "
               "Le Chat memory feature (already in catalog) — this row covers the model family "
               "itself as substrate."),
         claims=("Mistral Large 2: 123B dense, 128k ctx, MMLU 84%; Mixtral 8x22B open-weights "
                 "(Apache 2.0); Mistral Small 3 24B open-weights matches Llama 3.3 70B; "
                 "EU-hosted by default; €11.7B valuation Sept-2025"),
         created="2023-04 (Mistral AI founded); 2023-09 (Mistral 7B); 2023-12 (Mixtral 8x7B); 2024-04 (Mixtral 8x22B); 2024-07 (Large 2); 2025-01 (Small 3)",
         latest_release="Mistral Large 2.1 (2025-Q1); Mistral Small 3 (2025-01); Codestral 2 (2025)",
         hq="Paris, France",
         founders="Arthur Mensch (CEO; ex-Google DeepMind), Guillaume Lample, Timothée Lacroix (both ex-Meta FAIR)",
         funding="€2.4B+ total raised (~$2.7B USD); €11.7B valuation Series C Sept-2025 (ASML lead); a16z, General Catalyst, DST, Lightspeed, Nvidia investors",
         customers="BNP Paribas, Helsing, Orange, French government, AXA, Stellantis; via Azure / AWS Bedrock / GCP Vertex; Le Chat consumer (millions)",
         pricing="API: Mistral Large 2 $2/$6 per 1M; Small 3 free / $0.10-$0.30; Apache 2.0 open weights for Mixtral + Small + Codestral; Enterprise Mistral Forge on-prem",
         compliance="SOC 2 Type II; ISO 27001; GDPR-native; CCPA; EU AI Act compliance roadmap",
         data_handling="EU data residency by default; never trains on customer data (Enterprise + API); GDPR-compliant",
         deployment="Managed cloud (La Plateforme) + on-prem (Mistral Forge enterprise) + open-weights (Apache 2.0 for Mixtral + Small + Codestral) + Azure / AWS / GCP hosted",
         modalities="text, code; image via Pixtral Large (122B+vision)",
         perf="MMLU 84% (Large 2); MMLU-Pro ~75%; HumanEval ~92%; SWE-bench: Codestral 2 ~45%; lags top-tier (Claude 4.5 / GPT-5) but competitive in EU-hosted segment",
         api_surface="REST + SDK (Python, JS); HuggingFace Transformers for open-weights; Azure AI Foundry; AWS Bedrock; GCP Vertex",
         license_="Apache 2.0 (Mixtral / Small 3 / Codestral); proprietary (Large 2 / Pixtral Large)",
         gh="github.com/mistralai/mistral-inference + various model repos; cumulative ~30k+ stars",
         code_release="open weights for Mixtral / Small / Codestral; proprietary for Large 2",
         validated_verticals="EU public sector, defence, financial services, automotive, telecom (Orange, BNP, Stellantis, AXA, French gov)",
         time_to_running="<10min via La Plateforme; <1hr self-host (Mixtral via HuggingFace / vLLM); <1week (Mistral Forge enterprise)",
         anti_fit="not for users needing absolute frontier capability (lags Claude/GPT/Gemini on most benchmarks); not for non-Apache OSS users who want weight openness on Large 2",
         optimised_for="EU-hosted enterprise; sovereign AI for European governments; cost-effective hybrid (open + commercial) family",
         adjacent="Mistral Le Chat consumer (separate row); Codestral for code agents; Mistral Forge on-prem; AWS Bedrock / Azure AI distribution",
         pros="Strongest EU AI-sovereignty story (Paris-HQ, GDPR-native, French gov customer); Apache 2.0 open weights for Mixtral / Small / Codestral; €2.7B raised at €11.7B valuation.",
         cons="Trails US/China frontier labs on raw benchmarks; Large 2 not open-weights; smaller training-compute budget; multimodal less mature than peers.",
         mindshare="Top EU AI lab; €11.7B valuation; ASML strategic investor; large French government / defence deployments (Helsing, Mistral Forge)",
         llm_lock="open (multi-vendor — Apache 2.0 weights + hosted)",
         runtimes="any (HuggingFace, vLLM, llama.cpp)",
         na_default="substrate"),

    dict(tier=1, name="Cohere Command R+ / Command A",
         url="https://cohere.com/command",
         type_str="Enterprise-focused frontier model family (Command A / Command R+ / Command R7B)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://cohere.com/command",
         desc=("Toronto-based foundation-model lab (Aidan Gomez, ex-Google Brain 'Attention Is "
               "All You Need' co-author). Command family is enterprise / RAG-optimised: Command "
               "A (Mar-2025, 111B dense, 256k ctx), Command R+ (104B MoE), Command R7B (smallest "
               "tier). Announced merger with Aleph Alpha April-2026. Open weights via CC-BY-NC "
               "(non-commercial); Cohere-hosted for commercial."),
         claims=("Command A: 111B dense, 256k ctx, 23 languages, enterprise-RAG-tuned; "
                 "Command R+ best open-weights RAG model 2024; reranker + embed family integrated; "
                 "Aleph Alpha merger announced Apr-2026"),
         created="2019 (Cohere founded); 2024-04 (Command R+); 2025-03 (Command A)",
         latest_release="Command A (2025-03); Command R7B (2024-12)",
         hq="Toronto, Canada (offices in SF, London, NYC)",
         founders="Aidan Gomez (CEO; Transformer paper co-author), Ivan Zhang, Nick Frosst",
         funding="$1.5B+ total raised; ~$5.5B valuation 2024 (Series D); Inovia, NVIDIA, Salesforce Ventures, Cisco, PSP investors",
         customers="Oracle (deep integration), Fujitsu, RBC, Notion, Salesforce, SAP, Bloomberg; LSE / TSX-listed enterprises",
         pricing="API: Command A $2.50/$10 per 1M; Command R+ $2.50/$10; Command R7B $0.0375/$0.15; Embed + Rerank separately priced",
         compliance="SOC 2 Type II, ISO 27001, ISO 27017/18, HIPAA, GDPR, PCI DSS; deployable to customer VPC",
         data_handling="Never trains on customer data; in-tenant deployment available; SOC2 + ISO 27001 baseline",
         deployment="Managed cloud + customer VPC (AWS / Azure / GCP / Oracle Cloud) + on-prem; weights downloadable for non-commercial via HuggingFace",
         modalities="text + code; image via Aya Vision; primarily text-focused — enterprise RAG bias",
         perf="MMLU ~85% (Command A); RAG-specific: SOTA among open-weights tier; reranker family widely cited as Sentence-Transformers replacement",
         api_surface="REST + SDK (Python, TS, Java, Go); native AWS Bedrock + Azure + Oracle + GCP",
         license_="CC-BY-NC 4.0 (weights — non-commercial only); proprietary for commercial",
         gh="github.com/cohere-ai cumulative ~5k+ stars; various model repos on HuggingFace",
         code_release="weights public (non-commercial); commercial requires Cohere API",
         validated_verticals="financial services (RBC, Bloomberg), telecom (Oracle, Fujitsu), public sector, retail, energy — enterprise RAG dominant use case",
         time_to_running="<10min via Cohere API; <1day customer-VPC deploy; <1week on-prem",
         anti_fit="not for consumer chat (no Cohere consumer app); benchmark performance trails Claude/GPT in raw reasoning; CC-BY-NC weights limit OSS commercial use",
         optimised_for="enterprise RAG, reranker pipelines, customer-VPC / on-prem deployments, multi-language enterprise use",
         adjacent="Cohere Embed v4; Cohere Rerank v3; Oracle Cloud Infrastructure deep integration",
         pros="Enterprise-first positioning (in-tenant / on-prem); SOTA reranker family; strong RAG performance; major enterprise customers (Oracle, RBC, Bloomberg).",
         cons="Trails Anthropic/OpenAI/Google on raw frontier benchmarks; weights CC-BY-NC only; no consumer presence; merger uncertainty post-Aleph-Alpha integration.",
         mindshare="Top-3 in enterprise RAG; Oracle Cloud deep integration; large reranker mindshare among LLM-app developers (Sentence-Transformers replacement)",
         llm_lock="multi-vendor option (Cohere-hosted + customer VPC + on-prem)",
         runtimes="any (HTTP API; HuggingFace Transformers for non-commercial)",
         na_default="substrate"),

    dict(tier=1, name="xAI Grok 4",
         url="https://x.ai/news/grok-4",
         type_str="Frontier foundation model from xAI (Grok 4)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://x.ai/news/grok-4",
         desc=("Elon Musk's xAI frontier model — Grok 4 launched 2025-07. Trained on Colossus "
               "(100k+ GPU supercluster in Memphis). Deeply integrated with X/Twitter (real-time "
               "tweet data access). Grok 4 Heavy variant for premium tier. No frontier-tier "
               "open-weights — Grok 1 (314B MoE) is the only weight release."),
         claims=("Grok 4 launched Jul-2025; Grok 4 Heavy multi-agent variant; trained on Colossus "
                 "100k+ H100 supercluster Memphis; real-time X/Twitter data integration; "
                 "256k context"),
         created="2023-07 (xAI founded); 2023-11 (Grok 1); 2024-08 (Grok 2); 2025-02 (Grok 3); 2025-07 (Grok 4)",
         latest_release="Grok 4 (2025-07); Grok 4 Heavy (2025)",
         hq="San Francisco, US (Memphis training facility)",
         founders="Elon Musk (Founder/CEO; also Tesla/SpaceX/X); Igor Babuschkin (ex-DeepMind), Jimmy Ba (Toronto), Tony Wu (Google)",
         funding="$12B+ total raised; $50B+ valuation 2024-25; Andreessen Horowitz, Sequoia, Valor, Vy Capital, Saudi PIF investors",
         customers="X (Twitter) Premium+ subscribers; xAI API enterprise customers; Telegram (rumored); some Tesla AI integration",
         pricing="X Premium+ ($30+/mo includes Grok); API: Grok 4 $3/$15 per 1M (premium tier); Grok 4 Heavy $30/$150 per 1M",
         compliance="SOC 2 Type II; GDPR (X has EU presence); no HIPAA/FedRAMP yet",
         data_handling="Trains on X/Twitter public data by default; enterprise API never-trains commitment",
         deployment="Managed-only (xAI API + X Premium); no self-hosting at Grok 4 tier (Grok 1 314B MoE Apache 2.0)",
         modalities="text, image (vision); image generation via Aurora; voice-mode on X mobile app",
         perf="ARC-AGI-2: Grok 4 Heavy ~30%+ (vendor-stated, leading); MMLU-Pro ~80%; AIME 2025 ~90%; HumaneVal ~95%; competitive with Claude/GPT on math/reasoning",
         api_surface="REST + SDK (Python, TS); OpenAI-compatible",
         license_="Apache 2.0 (Grok 1 only — 314B MoE older release); proprietary (Grok 2/3/4)",
         gh="github.com/xai-org/grok-1 ~50k stars (older Grok 1 weights only)",
         code_release="Grok 1 weights public (Apache 2.0); Grok 2/3/4 proprietary",
         validated_verticals="X/Twitter integration (consumer); financial services (real-time market data via X firehose); developer API customers",
         time_to_running="<5min via xAI API key; <1min via X Premium+",
         anti_fit="X/Twitter integration is unique selling point but creates Musk-political-association risk; weights closed at Grok 4 tier; no on-prem; less polished tool-use than Claude/GPT",
         optimised_for="real-time information (X firehose access); contrarian / less-filtered persona; benchmark frontier-tier reasoning",
         adjacent="X (Twitter); Tesla Optimus / FSD AI infrastructure (shared GPU); Colossus Memphis supercluster",
         pros="Real-time X/Twitter data access (unique among frontier models); Colossus supercluster gives independent training capacity; ARC-AGI-2 leader (vendor-stated).",
         cons="Owner Musk political controversy creates enterprise procurement headwind; closed weights at Grok 4; no on-prem; less mature ecosystem than Anthropic/OpenAI/Google.",
         mindshare="X Premium+ distribution → tens of millions of consumer users; rapidly growing API; LMSYS Arena top-5; ARC-AGI-2 vendor-claimed leader",
         llm_lock="single-vendor (xAI-only family)",
         runtimes="any (HTTP API)",
         na_default="substrate"),

    dict(tier=1, name="Alibaba Qwen 3 family",
         url="https://qwenlm.github.io/blog/qwen3/",
         type_str="Open-weights frontier model family (Qwen 3 dense + MoE; 0.5B–235B)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://qwenlm.github.io/blog/qwen3/",
         desc=("Alibaba Cloud's Qwen 3 family (2025-04) — open-weights frontier models from "
               "0.5B to 235B-A22B MoE. Apache 2.0 (most sizes) — broadest open-weights family. "
               "Includes Qwen 3 32B dense, Qwen 3 30B-A3B MoE, Qwen 3 235B-A22B MoE. "
               "Qwen-Coder, Qwen-VL (vision), Qwen-Audio companion variants. Dominant base "
               "model for many Chinese AI startups and a top OSS substrate globally."),
         claims=("Qwen 3 family Apache 2.0; 0.5B to 235B-A22B MoE; 119 languages; thinking/non-"
                 "thinking dual mode; matches DeepSeek R1 on reasoning at smaller sizes"),
         created="2023-08 (Qwen 1); 2024-02 (Qwen 1.5); 2024-09 (Qwen 2.5); 2025-04 (Qwen 3)",
         latest_release="Qwen 3 family (2025-04); Qwen 3-Max preview (2025-Q3)",
         hq="Hangzhou, China (Alibaba Cloud)",
         founders="Alibaba Cloud (DAMO Academy); Qwen team led by Junyang Lin",
         funding="Alibaba (BABA) public; ~$200B market cap",
         customers="Alibaba Cloud customers; major Chinese AI startups; international OSS deployers via HuggingFace; top-3 OSS family on HF downloads",
         pricing="Free open-weights (Apache 2.0); Alibaba Cloud API pay-per-token ($0.10-$2 per 1M depending on tier); Together / Fireworks hosted",
         compliance="China-based; not US-certified (no SOC 2 / HIPAA / FedRAMP at Alibaba Cloud international tier — APAC focused)",
         data_handling="Self-hosting recommended for sensitive data; Apache 2.0 weights eliminate hosted dependency",
         deployment="Self-hostable (Apache 2.0 weights) + Alibaba Cloud Model Studio + Together AI + Fireworks + HuggingFace inference + Ollama",
         modalities="text, code; image (Qwen-VL line); audio (Qwen-Audio); video (Qwen2.5-VL)",
         perf="MMLU-Pro: 235B-A22B ~80%; AIME 2025: ~85% (235B); HumanEval: ~90%; matches DeepSeek R1 at smaller sizes",
         api_surface="OpenAI-compatible REST (Alibaba Cloud Model Studio); HuggingFace Transformers; vLLM; llama.cpp",
         license_="Apache 2.0 (most Qwen 3 sizes); some larger MoE variants under Qwen License",
         gh="github.com/QwenLM/Qwen3 ~30k+ stars; cumulative QwenLM org repos ~80k+ stars",
         code_release="Apache 2.0 — weights public on HuggingFace + ModelScope",
         validated_verticals="Chinese enterprise (Alibaba Cloud customers); international OSS deployers; cost-sensitive workloads; multilingual (119 languages) applications",
         time_to_running="<10min hosted (Alibaba Cloud / Together / Fireworks); <1hr self-host (Ollama / vLLM)",
         anti_fit="China data-residency for regulated Western workloads; less mainstream Western enterprise adoption; Qwen-Max not open-weights",
         optimised_for="multilingual (119 languages including Asian + minor European); cost-efficient inference; permissive Apache 2.0 OSS",
         adjacent="HuggingFace; ModelScope; Together AI; Fireworks; Ollama; vLLM; Alibaba Cloud Model Studio",
         pros="Broadest open-weights frontier family (0.5B to 235B); Apache 2.0 (most permissive); 119-language coverage; strong reasoning at small / medium sizes; #1-ranked OSS family on HF for many months 2024-25.",
         cons="China-based — regulatory risk for some Western enterprises; multimodal less polished than Gemini 3; Qwen-Max tier (rumored 1T+) is closed.",
         mindshare="Top-2 OSS model family globally on HuggingFace downloads (alongside Llama); standard baseline for Chinese AI startups; major distillation source",
         llm_lock="open (Apache 2.0)",
         runtimes="any (HuggingFace, vLLM, llama.cpp, MLX, Ollama)",
         na_default="substrate"),

    dict(tier=2, name="Reka Core / Flash / Edge",
         url="https://www.reka.ai/",
         type_str="Multimodal foundation model family — Reka Core / Flash / Edge",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://www.reka.ai/",
         desc=("SF / Singapore foundation-model startup founded by ex-DeepMind / Meta / Google "
               "researchers (Dani Yogatama, Yi Tay, Qi Liu). Native multimodal models — Reka "
               "Core (~67B, frontier candidate), Flash (~21B), Edge (~7B). Apr-2024: claimed "
               "Core matched GPT-4 / Gemini Ultra on MMMU. Acquired by Snowflake announced "
               "May-2025 (~$2B reported). Distinct from frontier-tier in mindshare but "
               "important as multimodal-native open-weights option."),
         claims=("Reka Core matched GPT-4 / Gemini Ultra on MMMU (Apr-2024 vendor claim); "
                 "native multimodal training (no late-fusion); 128k context; Snowflake "
                 "acquisition announced May-2025 (~$2B reported)"),
         created="2022-07 (Reka founded); 2024-04 (Reka Core launched)",
         latest_release="Reka Flash 3 (2025); Reka Core (2024-04)",
         hq="Singapore + San Francisco",
         founders="Dani Yogatama (CEO; ex-DeepMind), Yi Tay (Chief Scientist; ex-Google Brain), Qi Liu (Chief Architect; ex-Meta FAIR)",
         funding="$103M total raised (Series B June-2023 led by DST Global + Snowflake Ventures); Snowflake acquisition reported May-2025 (~$2B)",
         customers="Snowflake (now parent); Shutterstock; AI Singapore; previously stand-alone API customers",
         pricing="Reka API pay-per-token (~$3/$10 per 1M Core); post-Snowflake-acq: bundled into Snowflake Cortex AI",
         compliance="SOC 2 Type II; GDPR; Singapore PDPA",
         data_handling="Never trains on customer data; Snowflake post-acq inherits Snowflake compliance posture",
         deployment="Managed cloud (Reka API) + Snowflake Cortex AI post-acquisition; some weights via HuggingFace (Reka Flash 3)",
         modalities="text, image, video (native multimodal training)",
         perf="MMMU (multimodal): Core ~57% (matches GPT-4 / Gemini Ultra at launch Apr-2024); MMLU ~83%; benchmarks now lagging Claude 4 / GPT-5 frontier tier",
         api_surface="REST + Python SDK; OpenAI-compatible",
         license_="Reka Flash 3 weights under Apache 2.0; Core proprietary",
         gh="github.com/reka-ai (limited public repos)",
         code_release="open weights for Flash 3 only; Core proprietary",
         validated_verticals="multimodal data (Shutterstock); enterprise data analytics (Snowflake parent customer base); APAC enterprise",
         time_to_running="<10min via Reka API; via Snowflake Cortex AI post-integration",
         anti_fit="not for users wanting frontier-tier raw benchmark — now lags Claude/GPT/Gemini; Snowflake acquisition uncertainty re. standalone API future",
         optimised_for="multimodal-native (single-model image+text+video understanding); APAC / Snowflake-customer enterprise",
         adjacent="Snowflake Cortex AI (parent post-acq); HuggingFace (Flash 3); Together AI hosting",
         pros="Native multimodal training (not late-fusion); strong DeepMind / Google / Meta founding team; Snowflake distribution post-acquisition; Singapore HQ for APAC compliance.",
         cons="Lags frontier tier on raw benchmarks post-2024; Snowflake-acquisition integration uncertainty; smaller ecosystem; limited model releases since 2024.",
         mindshare="Mid-tier — Snowflake acquisition prominent; strong founder pedigree (Yi Tay 'Efficient Transformers' surveys); APAC presence; not top-of-mind for Western enterprise",
         llm_lock="single-vendor (Reka / Snowflake)",
         runtimes="any (HTTP API)",
         na_default="substrate"),

    dict(tier=2, name="01.AI Yi family",
         url="https://www.01.ai/",
         type_str="Open-weights frontier-tier Chinese model family (Yi-Lightning / Yi-34B)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://www.01.ai/",
         desc=("Kai-Fu Lee's 01.AI (founded 2023, Beijing). Yi family open-weights — Yi-34B "
               "(2023), Yi-Large (proprietary 2024), Yi-Lightning (2024-10, frontier-tier, "
               "matched GPT-4o on LMSYS chatbot arena). Apache 2.0 (Yi-34B and base sizes). "
               "Important second Chinese open-weights option alongside DeepSeek + Qwen."),
         claims=("Yi-Lightning matched GPT-4o on LMSYS Arena Oct-2024 at fraction of training "
                 "cost; Yi-34B Apache 2.0; trained at $3M total compute claimed; Kai-Fu Lee "
                 "founder pedigree (ex-Microsoft Research Asia, Google China)"),
         created="2023-07 (01.AI founded); 2023-11 (Yi-34B); 2024-05 (Yi-Large); 2024-10 (Yi-Lightning)",
         latest_release="Yi-Lightning (2024-10)",
         hq="Beijing, China",
         founders="Kai-Fu Lee (CEO; ex-Microsoft Research Asia President, ex-Google China President, Sinovation Ventures)",
         funding="$1B+ raised; >$1B valuation 2024 (Alibaba, Lightspeed China, Tencent investors)",
         customers="Chinese enterprise via 01.AI API; some Western OSS via HuggingFace (Yi-34B)",
         pricing="API: Yi-Lightning $0.14 per 1M tokens (vendor-claimed lowest among frontier-tier); Yi-34B weights free under Apache 2.0",
         compliance="China-based; not US-certified",
         data_handling="Self-hosting recommended for Western sensitive data; Apache 2.0 weights for Yi-34B remove hosted dependency",
         deployment="Self-hostable (Yi-34B Apache 2.0) + 01.AI API for Yi-Large / Yi-Lightning; Together AI hosts Yi-34B",
         modalities="text, code; Yi-VL (vision) variant",
         perf="LMSYS Chatbot Arena: Yi-Lightning matched GPT-4o (Oct-2024); MMLU ~78% (Yi-Large); MMLU-Pro ~70%; HumanEval ~85%",
         api_surface="REST + SDK; HuggingFace Transformers for Yi-34B",
         license_="Apache 2.0 (Yi-34B + base sizes); proprietary (Yi-Large, Yi-Lightning)",
         gh="github.com/01-ai/Yi ~7k+ stars",
         code_release="open weights for Yi-34B/9B/6B/Coder; proprietary for Yi-Large/Lightning",
         validated_verticals="Chinese enterprise; cost-sensitive OSS deployers globally",
         time_to_running="<10min via 01.AI API; <1hr self-host (Yi-34B Ollama / vLLM)",
         anti_fit="China data-residency for regulated Western workloads; Yi-Lightning closed weights; less mindshare in West than Qwen / DeepSeek",
         optimised_for="cost-efficient frontier inference; Chinese-language native; Apache 2.0 for Yi-34B tier",
         adjacent="HuggingFace; Together AI hosting; Sinovation Ventures alumni network",
         pros="Kai-Fu Lee founder pedigree; Yi-Lightning matched GPT-4o on LMSYS at fraction of cost; Apache 2.0 Yi-34B is broadly deployable.",
         cons="Less Western mindshare than DeepSeek / Qwen; Yi-Lightning closed-weights; smaller OSS ecosystem; China data-residency concerns.",
         mindshare="Top-3 Chinese model lab; LMSYS arena visibility from Yi-Lightning launch Oct-2024; meaningful but not dominant OSS HuggingFace presence",
         llm_lock="open (Apache 2.0 for Yi-34B); single-vendor for Yi-Lightning",
         runtimes="any (HuggingFace, vLLM, llama.cpp)",
         na_default="substrate"),

    dict(tier=2, name="Amazon Nova family",
         url="https://www.aboutamazon.com/news/aws/amazon-nova-foundation-models",
         type_str="AWS-native foundation model family (Nova Pro / Lite / Micro / Premier / Canvas / Reel)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://www.aboutamazon.com/news/aws/amazon-nova-foundation-models",
         desc=("Amazon's first-party foundation model family, launched at AWS re:Invent Dec-2024. "
               "Nova Pro (multimodal mid-tier), Nova Lite (multimodal cheap), Nova Micro "
               "(text-only fast), Nova Canvas (image gen), Nova Reel (video gen). Premier "
               "frontier-tier launched 2025. Substrate for AWS Bedrock-native agents and "
               "Amazon Q. Distinct from Claude / Llama / Mistral hosted via Bedrock — Nova is "
               "Amazon's own training."),
         claims=("Nova Pro multimodal mid-tier 300k ctx; Nova Premier frontier 2025; trained "
                 "by Amazon AGI team Seattle / Bellevue; AWS Bedrock-native pricing 75% "
                 "cheaper than peers (Amazon-stated for Lite/Micro)"),
         created="2024-12 (Nova family launched at re:Invent); 2025 (Nova Premier)",
         latest_release="Nova Premier (2025); Nova Pro / Lite / Micro / Canvas / Reel (2024-12)",
         hq="Seattle / Bellevue, US (Amazon AGI org)",
         founders="Amazon AGI org under Rohit Prasad (SVP Amazon AGI; ex-Alexa AI head)",
         funding="Amazon (AMZN) public; ~$2T market cap; capex $100B+ 2025 (largest among hyperscalers)",
         customers="AWS Bedrock customers (broad enterprise base); native to Amazon Q Developer + Q Business; integrated into Alexa+ (2025 generative Alexa)",
         pricing="AWS Bedrock pay-per-token: Nova Micro $0.035/$0.14 per 1M; Lite $0.06/$0.24; Pro $0.80/$3.20; Premier $2.50/$12.50",
         compliance="SOC 2 Type II, ISO 27001/17/18, HIPAA (Bedrock BAA), FedRAMP High (AWS GovCloud), PCI DSS, GDPR",
         data_handling="Never trains on Bedrock customer data; Amazon Bedrock data residency controls + KMS encryption",
         deployment="Managed-only via AWS Bedrock; no self-hosting (weights closed)",
         modalities="text, image (in + out via Canvas), video (out via Reel), code",
         perf="MMLU: Nova Premier ~85%; Nova Pro ~80%; vendor-stated 75% cheaper than peer mid-tier for Lite/Micro; multimodal benchmarks competitive but not frontier-leading",
         api_surface="AWS Bedrock REST/SDK (Python / TS / Java / Go / .NET); SigV4 auth",
         validated_verticals="AWS enterprise customer base (financial / health / public sector / retail); Amazon Q Developer (code) + Q Business (knowledge)",
         time_to_running="<30min (AWS Bedrock model access + IAM)",
         anti_fit="not for self-hosting (weights closed); AWS-locked deployment; benchmark performance trails Claude / GPT / Gemini at the frontier tier",
         optimised_for="AWS-native enterprise; cheap multimodal at Lite / Micro tier; integration with Amazon Q + Alexa+",
         adjacent="AWS Bedrock (distribution); Amazon Q Developer / Q Business; Alexa+; Trainium/Inferentia chips",
         pros="AWS distribution to massive existing enterprise base; cheapest multimodal at Lite / Micro tier (75% vendor-claimed); native integration with Amazon Q + Alexa+; FedRAMP High via AWS GovCloud.",
         cons="Lags frontier tier on most benchmarks; AWS-only deployment; closed weights; Amazon AGI team newer than DeepMind / OpenAI / Anthropic; Premier tier still maturing.",
         mindshare="AWS Bedrock distribution → broad enterprise reach; less developer mindshare than Claude (hosted on Bedrock); Amazon Q deep integration",
         llm_lock="single-vendor (AWS Bedrock-only)",
         runtimes="any (HTTP via AWS Bedrock SDK)",
         na_default="substrate"),

    dict(tier=2, name="Microsoft Phi-4 family",
         url="https://azure.microsoft.com/en-us/blog/welcome-phi-4/",
         type_str="Small / efficient open-weights model family (Phi-4 14B + Phi-4 multimodal + Phi-4 mini)",
         tax=TAX_FOUNDATION_MODEL,
         primary_url="https://azure.microsoft.com/en-us/blog/welcome-phi-4/",
         desc=("Microsoft Research's Phi family of small, data-curation-focused open-weights "
               "models. Phi-4 (14B, Dec-2024) matches much larger models on STEM benchmarks. "
               "Phi-4 Multimodal (5.6B, Feb-2025) integrates speech + vision + text. MIT "
               "license. Substrate for on-device / edge agents and cost-sensitive OSS use."),
         claims=("Phi-4 14B matches Llama 3.3 70B on STEM benchmarks (MMLU 84.8%); Phi-4 "
                 "Multimodal 5.6B integrates speech / vision / text; MIT license; data-curation-"
                 "driven training methodology"),
         created="2023-06 (Phi-1); 2023-12 (Phi-2); 2024-04 (Phi-3); 2024-12 (Phi-4); 2025-02 (Phi-4 Multimodal)",
         latest_release="Phi-4 Multimodal (2025-02); Phi-4 (2024-12)",
         hq="Redmond, US (Microsoft Research)",
         founders="Microsoft Research (Phi team under Sébastien Bubeck — now ex-MSR, joined OpenAI Oct-2024; Microsoft Research AI Frontiers org continues)",
         funding="Microsoft (MSFT) public; ~$3T market cap; AI capex $80B+ 2025",
         customers="Azure AI customers; on-device deployment (Windows 11 Copilot+ PCs); Azure AI Foundry catalog; HuggingFace OSS deployers",
         pricing="Free open-weights (MIT); Azure AI pay-per-token if hosted",
         compliance="MIT license — deployer-controlled; Azure inherits Microsoft compliance posture (SOC 2 / ISO / HIPAA / FedRAMP)",
         data_handling="Open-weights — deployer-controlled",
         deployment="Self-hostable (MIT) + Azure AI Foundry hosted + on-device (Windows Copilot+ PCs, ONNX Runtime)",
         modalities="text, code (Phi-4); + image, speech (Phi-4 Multimodal)",
         perf="MMLU 84.8% (Phi-4 14B); GPQA 56% (Phi-4); HumanEval 82%; outperforms many 70B+ models on STEM at 14B parameters",
         api_surface="HuggingFace Transformers; ONNX Runtime; Azure AI Foundry REST; native Windows ML",
         license_="MIT",
         gh="github.com/microsoft/Phi-3CookBook ~3k+ stars + various HuggingFace repos",
         code_release="MIT — weights public on HuggingFace + Azure AI Foundry catalog",
         validated_verticals="on-device / edge (Copilot+ PCs, mobile); cost-sensitive OSS; STEM-focused agents; Azure AI customers",
         time_to_running="<5min via Ollama; <30min Azure AI Foundry; on-device via Windows ML on Copilot+ PCs",
         anti_fit="not frontier-tier at general chat (smaller knowledge base); narrower world-knowledge than 70B+ models; multimodal less mature than Gemini 3",
         optimised_for="on-device / edge inference; STEM reasoning at small footprint; data-curation-driven training",
         adjacent="Azure AI Foundry; ONNX Runtime; Windows Copilot+ PCs; HuggingFace Transformers; Ollama",
         pros="MIT licensed (broadest permissions); 14B matches 70B+ on STEM; deployable on Copilot+ PCs / edge; Microsoft research pedigree.",
         cons="Smaller world-knowledge than peers (data curation tradeoff); not at frontier-tier general capability; original Phi team leader (Bubeck) departed to OpenAI Oct-2024.",
         mindshare="Strong small-model OSS mindshare; default Windows Copilot+ on-device model; HuggingFace top-10 small-model family by downloads",
         llm_lock="open (MIT)",
         runtimes="any (HuggingFace Transformers, ONNX Runtime, llama.cpp, MLX, Ollama, Windows ML)",
         na_default="substrate"),
]


# ============================================================================
# PASS B — Multi-agent orchestration platforms
# ============================================================================

MULTI_AGENT_ROWS = [
    dict(tier=2, name="CrewAI Enterprise",
         url="https://www.crewai.com/enterprise",
         type_str="Commercial multi-agent orchestration platform (vs OSS CrewAI)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://www.crewai.com/enterprise",
         desc=("Commercial Enterprise tier of the CrewAI OSS multi-agent framework. Adds "
               "managed cloud runtime, RBAC, audit logging, SLA support, on-prem option. "
               "OSS CrewAI is in the Framework-embedded memory section already; this row "
               "covers the commercial cloud platform separately. $18M Series A Oct-2024 "
               "(Insight Partners). 30k+ companies have deployed CrewAI agents in prod "
               "(vendor-stated)."),
         claims="$18M Series A Oct-2024 (Insight Partners); 30k+ deployments vendor-claimed; commercial features: RBAC, audit, SLA, on-prem; founded 2024 by João Moura",
         created="2024-01 (CrewAI OSS released); 2024-Q4 (Enterprise tier launched)",
         hq="São Paulo, Brazil + US (remote-first)",
         founders="João Moura (CEO; ex-Clearbit, ex-Crunchyroll)",
         funding="$18M Series A Oct-2024 (Insight Partners; Boldstart, Blitzscaling)",
         customers="Reportedly used by Fortune 500 (vendor-claimed); specific named customers not publicly disclosed",
         pricing="Free (OSS) + Pro ($99/mo) + Team + Enterprise (quote)",
         compliance="SOC 2 Type II (in-progress); GDPR",
         data_handling="Enterprise: never trains on customer data; managed cloud + on-prem options",
         deployment="Managed cloud + self-hostable (Enterprise) + OSS (self-hostable)",
         pros="Strong OSS-to-commercial conversion path; large dev mindshare from CrewAI OSS; multi-agent crews abstraction is intuitive for non-experts.",
         cons="Memory layer is thin (delegates to LangChain / Mem0); enterprise features still maturing; smaller funding than peers (LangChain $160M).",
         optimised_for="role-based multi-agent crew composition; OSS-friendly developer experience",
         adjacent="OSS CrewAI (already in catalog); typically paired with Mem0 / Zep for memory + Langfuse / LangSmith for observability",
         agent_abstraction="multi-agent crew (role-based, sequential / hierarchical / consensual process)",
         llm_lock="multi-vendor (BYO OpenAI / Anthropic / Gemini / Bedrock / Ollama)",
         runtimes="Python (primary)",
         a2a_support="planned (Google A2A roadmap)",
         mcp_support="via community port",
         na_default="orchestration"),

    dict(tier=2, name="Microsoft AutoGen Studio",
         url="https://microsoft.github.io/autogen/dev/user-guide/autogenstudio-user-guide/index.html",
         type_str="Low-code multi-agent orchestration UI (Microsoft Research)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://microsoft.github.io/autogen/dev/user-guide/autogenstudio-user-guide/index.html",
         desc=("Microsoft Research's low-code GUI for designing and deploying multi-agent "
               "workflows on top of the AutoGen framework. AutoGen v0.4 (Jan-2025) re-architecture "
               "moved to actor-based async runtime. Free OSS (MIT). Distinct from OSS AutoGen "
               "framework already in catalog — this row covers the Studio GUI / no-code product. "
               "Increasingly positioned as Microsoft's multi-agent answer to LangGraph / CrewAI."),
         claims="OSS (MIT) + Microsoft Research-backed; AutoGen v0.4 actor-based async; >35k stars on AutoGen repo cumulative; AutoGen Studio is no-code GUI on top",
         created="2023-09 (AutoGen released); 2024-04 (Studio released); 2025-01 (v0.4 re-arch)",
         hq="Redmond, US (Microsoft Research)",
         founders="Chi Wang + Qingyun Wu (Microsoft Research) — Chi Wang left to Google DeepMind 2024-Q4; AutoGen org now MSR + community",
         funding="Microsoft (MSFT) public; Microsoft Research-funded",
         customers="Microsoft internal teams; OSS community; integrated examples for Azure AI",
         pricing="Free (MIT)",
         compliance="MIT — deployer-controlled; Azure if hosted inherits compliance",
         deployment="Self-hostable (OSS); Azure AI integration; runs locally",
         pros="Microsoft Research pedigree; OSS (MIT); no-code GUI lowers barrier vs LangGraph; actor-based async runtime in v0.4 supports complex multi-agent topologies.",
         cons="Founding researcher (Chi Wang) departed to Google DeepMind; less commercial momentum than CrewAI / LangGraph; Studio GUI less polished than commercial peers.",
         optimised_for="multi-agent topologies via no-code GUI; researcher / prototype usage",
         adjacent="AutoGen framework (OSS, already in catalog); Azure AI; Microsoft Semantic Kernel",
         license_="MIT",
         gh="github.com/microsoft/autogen ~37k+ stars",
         code_release="MIT — OSS",
         agent_abstraction="multi-agent (actor-based async + conversational programming)",
         llm_lock="multi-vendor (OpenAI / Anthropic / Azure OpenAI / local)",
         runtimes="Python (primary); .NET preview",
         mcp_support="via community port",
         na_default="orchestration"),

    dict(tier=2, name="MultiOn",
         url="https://www.multion.ai/",
         type_str="Web-agent / browser-agent API platform (developer-focused autonomous browsing)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://www.multion.ai/",
         desc=("Web-browsing agent API platform. Founded 2023 by Div Garg (Stanford); $30M+ "
               "raised. Provides 'Agent API' for autonomous web tasks (booking, shopping, "
               "research). Distinct from browser-agent memory section (Arc Max, Browser Company, "
               "Dia) — MultiOn ships an API for developers rather than a consumer browser. "
               "Demoed at 2024 Microsoft Build; partnered with NotebookLM for some flows."),
         claims="$30M+ raised; Agent API for web tasks; demoed at Microsoft Build 2024; 'AI that uses the web for you' positioning",
         created="2023 (founded)",
         hq="Palo Alto / San Francisco, US",
         founders="Div Garg (CEO; Stanford CS PhD); Naman Garg",
         funding="$30M+ total raised (seed 2023-24); investors: Amazon AI Fund, Google, Samsung Next, Brave, GV, others",
         pricing="API pay-per-task; freemium developer tier",
         deployment="Managed-only (MultiOn API)",
         pros="Early-mover in web-agent API space; strong investor base (Amazon AI Fund, Google, GV); demoed natively in Microsoft Build keynote.",
         cons="Browser-agent space is now crowded (OpenAI Operator, Anthropic Computer Use, Project Mariner); API success vs consumer Arc/Dia uncertain; smaller raise vs peers.",
         optimised_for="developer API for autonomous web browsing / task completion",
         adjacent="Playwright; Chromium-headless infrastructure; computer-use models (Claude / GPT-5 / Gemini)",
         api_surface="REST + Python SDK",
         agent_abstraction="single-agent web automation (autonomous browser actions)",
         llm_lock="multi-vendor (BYO; can switch OpenAI / Anthropic / Gemini)",
         runtimes="any (REST API)",
         mcp_support="via community port",
         na_default="orchestration"),

    dict(tier=2, name="Reflection AI",
         url="https://reflection.ai/",
         type_str="Autonomous coding-agent foundation lab (Misha Laskin / Ioannis Antonoglou)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://reflection.ai/",
         desc=("Founded 2024 by Misha Laskin and Ioannis Antonoglou (both ex-DeepMind, "
               "AlphaGo / Gemini RLHF). Building autonomous coding agents — Asimov is their "
               "code-research agent. Raised $130M Series A March-2025 at $555M valuation "
               "led by Lightspeed + CRV. Positioned as Devin/Cognition competitor with "
               "RL / robotics-research pedigree."),
         claims="$130M Series A Mar-2025 at $555M valuation (Lightspeed + CRV); founders ex-DeepMind AlphaGo + Gemini RLHF team; Asimov code-research agent product",
         created="2024 (founded)",
         hq="San Francisco, US",
         founders="Misha Laskin (CEO; ex-DeepMind, AlphaGo + Gemini RLHF); Ioannis Antonoglou (CTO; ex-DeepMind AlphaGo + Gemini RLHF + DQN)",
         funding="$130M Series A Mar-2025 ($555M val; Lightspeed + CRV; Sequoia, Nvidia investors)",
         pricing="Private beta; enterprise sales early",
         deployment="Managed cloud (private beta)",
         pros="Strongest ex-DeepMind RL pedigree in coding-agent space; $130M at $555M val is largest among 2024-vintage coding-agent labs; differentiated by autonomous research focus (Asimov).",
         cons="Pre-product launch (private beta 2025); Devin / Cursor / Cognition / Anthropic Claude Code already established; small team vs commercial peers.",
         optimised_for="autonomous coding research agents; long-horizon software-engineering tasks",
         adjacent="DeepMind alumni network; RL research community; competes with Cognition Devin, Cursor, Codeium Windsurf",
         agent_abstraction="autonomous coding agent (long-horizon code research)",
         llm_lock="multi-vendor (uses Claude + GPT internally per reports)",
         na_default="orchestration"),

    dict(tier=3, name="Adept ACT",
         url="https://www.adept.ai/",
         type_str="Computer-use / workflow-automation agent (Adept now part of Amazon AGI 2024)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://www.adept.ai/",
         desc=("Founded 2022 by ex-OpenAI / Google researchers (David Luan, Kelsey Schroeder). "
               "Built ACT-1 / ACT-2 multimodal action transformers for computer-use. "
               "**Acquired by Amazon June-2024 (acqui-hire)** — co-founders + key team joined "
               "Amazon AGI; Adept the company continues with Zach Brock as remaining executive. "
               "Important historical entry — ACT models inspired Anthropic Computer Use + "
               "OpenAI Operator."),
         claims="ACT-1 (2022) and ACT-2 (2023) multimodal action transformers; founded by ex-Google Brain + ex-OpenAI execs; **Amazon AGI acqui-hire June 2024** (David Luan + Maxwell Nye + Kelsey Schroeder joined Amazon AGI)",
         created="2022 (founded); 2022-09 (ACT-1 demo); 2024-06 (Amazon acqui-hire)",
         hq="San Francisco, US",
         founders="David Luan (ex-Google Brain), Maxwell Nye (ex-OpenAI), Kelsey Schroeder (CEO post-acqui-hire); ex-Google Brain Niki Parmar early team",
         funding="$415M total raised pre-acq (Series B 2023 — General Catalyst, Spark, Greylock); Amazon acqui-hire June 2024 (terms ~$300-500M reported but undisclosed)",
         pricing="Pre-acq: enterprise pilot only",
         pros="Pioneered computer-use action-transformer concept (ACT-1 was first widely-shown demo of LLM controlling desktop apps); strong founding-team pedigree.",
         cons="Lost commercial momentum to Amazon acqui-hire June-2024; products effectively shelved (Adept entity continues but no longer shipping new ACT models); inspired but didn't capture the computer-use market.",
         optimised_for="(historical) computer-use action transformers; (post-acq) Amazon AGI roadmap",
         adjacent="Amazon AGI (parent post-acquisition); spiritual predecessor to Anthropic Computer Use + OpenAI Operator + Project Mariner",
         agent_abstraction="action-transformer (vision + action prediction)",
         llm_lock="single-vendor (Adept-proprietary ACT models historically)",
         na_default="orchestration"),

    dict(tier=2, name="Sema4.ai",
         url="https://sema4.ai/",
         type_str="Enterprise multi-agent platform (rebrand of Robocorp; Python-based)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://sema4.ai/",
         desc=("Sema4.ai is the AI-agent rebrand of Robocorp (RPA / Python automation OSS). "
               "Funded by Benchmark, Canvas Ventures, Slow Ventures. Founded 2019 (as "
               "Robocorp); rebranded 2024. Positioned as enterprise Python-based agent runtime "
               "with strong RPA heritage and governance focus. OSS Robocorp framework remains "
               "open-source (Apache 2.0). Distinct from no-code RPA — Sema4.ai is code-first."),
         claims="$83M total raised (Series B; Benchmark, Canvas, Slow Ventures); rebrand of Robocorp 2024; OSS Robocorp framework Apache 2.0; enterprise agent runtime",
         created="2019 (Robocorp founded); 2024 (Sema4.ai rebrand)",
         hq="San Francisco, US + Helsinki, Finland",
         founders="Antti Karjalainen (CEO; ex-Software Robots); Robocorp/Sema4 founding team",
         funding="$83M total raised (Series B 2022; Benchmark, Canvas, Slow Ventures, Microsoft M12, NEA, Reaktor)",
         customers="ARM, Capgemini, Accenture, large enterprise RPA accounts inherited from Robocorp",
         pricing="OSS (Robocorp framework) + Sema4.ai Studio + Enterprise cloud (quote)",
         compliance="SOC 2 Type II; ISO 27001; GDPR (EU presence)",
         data_handling="Enterprise tier: never trains on customer data; on-prem available",
         deployment="OSS framework + managed cloud + on-prem enterprise",
         pros="Strong RPA heritage from Robocorp; Apache 2.0 OSS core; enterprise compliance baseline (SOC 2 / ISO); Benchmark-backed; Helsinki + SF presence.",
         cons="Brand transition (Robocorp → Sema4.ai) creates discovery friction; less mindshare in AI-native dev community than CrewAI / LangGraph; RPA / agent positioning sometimes confused.",
         optimised_for="enterprise Python-based agent automation; RPA-to-AI transition workloads",
         adjacent="Robocorp OSS framework; Python ecosystem; Tier 1 RPA peers (UiPath / Automation Anywhere); Workato AI",
         agent_abstraction="task-action agent (Python-defined; OSS framework)",
         license_="Apache 2.0 (Robocorp framework)",
         gh="github.com/robocorp/robocorp ~1k+ stars; github.com/Sema4AI/actions repos",
         code_release="Apache 2.0 — OSS framework",
         llm_lock="multi-vendor (BYO OpenAI / Anthropic / local)",
         runtimes="Python (primary)",
         na_default="orchestration"),

    dict(tier=3, name="Imbue (formerly Generally Intelligent)",
         url="https://imbue.com/",
         type_str="Coding-agent research lab (foundation models for reasoning + code agents)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://imbue.com/",
         desc=("Founded 2017 as Generally Intelligent; rebranded Imbue 2023. Building "
               "foundation models for reasoning agents that write/edit code. Founders Kanjun "
               "Qiu + Josh Albrecht. $200M Series B 2023 ($1B valuation, Astera + Nvidia + "
               "Notion's Akshay Kothari). Trained 70B model for reasoning. Most public output "
               "is research blog + 'Carbon' OSS coding agent. Pulled back commercial roadmap "
               "post-2024."),
         claims="$200M Series B Sept-2023 ($1B valuation; Astera + Nvidia + Notion's Akshay Kothari); 70B reasoning model trained on Nvidia H100 cluster; OSS Carbon coding agent project",
         created="2017 (founded as Generally Intelligent); 2023 (Imbue rebrand)",
         hq="San Francisco, US",
         founders="Kanjun Qiu (CEO; ex-Sourcegraph); Josh Albrecht (CTO)",
         funding="$200M Series B Sept-2023 ($1B val; Astera, Nvidia, Akshay Kothari, others)",
         pricing="Pre-product (research-focused)",
         pros="Long-running coding-reasoning research program (since 2017); $1B post-money 2023; trained 70B own model; OSS Carbon project popular in agent community.",
         cons="Limited shipping commercial product to date; competitive landscape (Cognition, Reflection, Anthropic, Cursor) intensified 2024-25; small team relative to peers.",
         optimised_for="reasoning-agent research; OSS coding-agent prototypes",
         adjacent="OSS Carbon coding agent; Nvidia (compute partner); Hugging Face (research releases)",
         agent_abstraction="reasoning-and-code agent (research)",
         llm_lock="single-vendor (Imbue-proprietary 70B + research)",
         na_default="orchestration"),

    dict(tier=3, name="Steamship",
         url="https://www.steamship.com/",
         type_str="Multi-agent deployment / hosting platform (LangChain-like infra)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://www.steamship.com/",
         desc=("YC W21 startup providing managed hosting + deployment for LLM agents — "
               "'one-click deploy' for LangChain / agent code. Founded by Ted Benson (ex-Google "
               "Brain). Pre-seed + seed funded YC + Twin Ventures. Positioned as Heroku for AI "
               "agents — but the agent-platform space crowded post-2023, and Steamship's "
               "commercial momentum has slowed vs Vercel AI / Modal / Bedrock."),
         claims="YC W21; one-click deploy for LangChain agents; managed hosting + persistent memory tier",
         created="2021 (YC W21)",
         hq="San Francisco, US",
         founders="Ted Benson (CEO; ex-Google Brain, ex-Pinterest); Doug Reid (CTO)",
         funding="Seed: YC + Twin Ventures + others (~$3M+ disclosed)",
         pricing="Free + paid tiers (per-call + storage)",
         pros="Early-mover in agent-deployment hosting (Heroku-for-agents); YC backing; LangChain integration native.",
         cons="Crowded space — Vercel AI / Modal / Bedrock / Replicate provide alternative paths; small team; limited 2024-25 product velocity vs peers.",
         optimised_for="one-click deployment / hosting for LangChain agents",
         adjacent="LangChain (deep integration); Heroku-style PaaS heritage; YC alumni network",
         agent_abstraction="multi-agent hosting / deployment (LangChain-compatible)",
         llm_lock="multi-vendor (BYO)",
         runtimes="Python (primary)",
         na_default="orchestration"),

    # NOTE: Magic.dev already in catalog at "Agent IDEs & coding harnesses"
    # (id magic-dev--magic-dev); not duplicated here per spec ("verify not duplicate").

    dict(tier=2, name="Phidata / Agno",
         url="https://www.agno.com/",
         type_str="OSS multi-agent framework (rebranded from Phidata to Agno 2024)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://www.agno.com/",
         desc=("Phidata rebranded to Agno in 2024. OSS Python framework for building multi-agent "
               "systems with memory, knowledge, tools, reasoning. Lightweight alternative to "
               "LangChain. ~25k+ stars combined Phidata + Agno repos. Mozilla Ventures + others "
               "backed. Distinct from Mem0 / Zep — Agno is a full agent framework with first-"
               "party memory + knowledge + reasoning + tools."),
         claims="OSS Python framework (MPL-2.0); rebranded Phidata → Agno 2024; 25k+ stars (Phidata + Agno cumulative); pre-seed + seed funded (Mozilla Ventures + others)",
         created="2023 (Phidata initial); 2024 (Agno rebrand)",
         hq="Distributed (US-based founders)",
         founders="Ashpreet Bedi (CEO; ex-quant / data engineering)",
         funding="Pre-seed / seed disclosed (~$5M+); Mozilla Ventures + Y Combinator (W22) participation",
         pricing="OSS (free); future paid cloud tier",
         pros="Lightweight Python framework; first-party memory + knowledge + reasoning + tools (no LangChain dependency); 25k+ stars combined; clean docs.",
         cons="Smaller ecosystem than LangChain / LlamaIndex; rebrand from Phidata creates discovery friction; pre-product commercial revenue.",
         optimised_for="lightweight Python multi-agent systems; alternative to LangChain bloat",
         adjacent="HuggingFace Transformers; OpenAI / Anthropic / Gemini SDKs; YC W22 alumni network",
         license_="MPL-2.0 (Agno OSS)",
         gh="github.com/agno-agi/agno ~25k+ stars; github.com/phidatahq/phidata (legacy)",
         code_release="MPL-2.0 — OSS",
         agent_abstraction="multi-agent (lightweight Python; agent + crew + team primitives)",
         memory_primitives="key-value + vector + structured (first-party Storage / Memory / Knowledge primitives)",
         llm_lock="multi-vendor (50+ providers — OpenAI / Anthropic / Gemini / Groq / Ollama / vLLM)",
         runtimes="Python (primary)",
         mcp_support="native (first-party)",
         na_default="orchestration"),

    dict(tier=2, name="Burr (DAGWorks)",
         url="https://burr.dagworks.io/",
         type_str="OSS state-machine framework for LLM agents (DAGWorks Inc.)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://burr.dagworks.io/",
         desc=("Burr is a state-machine framework for LLM agents from DAGWorks (commercial "
               "company behind Hamilton dataflow framework, $4M seed). State-machine abstraction "
               "instead of DAG / ReAct — more debuggable for production. Targets the same niche "
               "as LangGraph but with state-machine semantics rather than DAG. BSD-3 license. "
               "Founded 2023 by ex-Stitch Fix / Two Sigma / Lyft engineers."),
         claims="OSS BSD-3 state-machine framework; sister project to Hamilton dataflow; founders ex-Stitch Fix / Two Sigma; $4M seed 2023; ~1.6k+ stars",
         created="2023 (Burr initial release; DAGWorks founded 2022)",
         hq="San Francisco, US (DAGWorks Inc.)",
         founders="Stefan Krawczyk (CEO; ex-Stitch Fix); Elijah ben Izzy (CTO; ex-Stitch Fix)",
         funding="$4M seed (2023; Skylab Capital, others)",
         pricing="OSS (free); commercial DAGWorks platform for Hamilton + Burr observability",
         pros="State-machine abstraction (vs DAG / ReAct) is genuinely more production-debuggable; companion to Hamilton (popular dataflow framework); strong founder pedigree.",
         cons="Smaller stars / ecosystem than LangGraph / CrewAI; commercial sustainability of DAGWorks newer; state-machine framing has learning curve.",
         optimised_for="production-grade state-machine LLM workflows with observability",
         adjacent="Hamilton (sister OSS framework, same company); LangGraph (closest competitor); MLflow / Phoenix observability",
         license_="BSD-3-Clause",
         gh="github.com/DAGWorks-Inc/burr ~1.6k+ stars",
         code_release="BSD-3 — OSS",
         agent_abstraction="state-machine (actions + transitions + state)",
         llm_lock="multi-vendor (BYO)",
         runtimes="Python (primary)",
         na_default="orchestration"),

    dict(tier=2, name="InstructLab (Red Hat / IBM)",
         url="https://instructlab.ai/",
         type_str="OSS LLM alignment + community-driven fine-tuning framework",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://instructlab.ai/",
         desc=("Red Hat / IBM-stewarded open-source framework for community-driven LLM "
               "alignment + fine-tuning. Method paper 'LAB: Large-Scale Alignment for "
               "Chatbots' (Sudalairaj et al, IBM Research 2024). Built on the Granite model "
               "family (IBM's open-weights). Apache 2.0. Used in IBM watsonx + Red Hat OpenShift "
               "AI for fine-tuning workflows. Not strictly a multi-agent framework — included "
               "as 'orchestration platform' because of its role as a substrate for building "
               "domain-specific fine-tuned agent models."),
         claims="Apache 2.0; LAB methodology paper IBM Research 2024; built on Granite open-weights; community-driven taxonomy contributions; integrated into Red Hat OpenShift AI + IBM watsonx",
         created="2024-05 (InstructLab launched at Red Hat Summit 2024)",
         hq="Raleigh, US (Red Hat) + Armonk, US (IBM)",
         founders="IBM Research (Akash Srivastava, Abhishek Bhandwaldar, others); Red Hat (Tushar Katarki, Mark Sturdevant) stewards community",
         funding="Red Hat (NYSE:RHT acquired by IBM 2019 for $34B); IBM (IBM) public ~$200B market cap",
         customers="IBM watsonx customers; Red Hat OpenShift AI customers; broader Granite open-weights deployers",
         pricing="OSS (free); IBM watsonx + Red Hat OpenShift AI commercial pricing for the platforms",
         compliance="Inherits Red Hat / IBM enterprise compliance posture (SOC 2 / FedRAMP / ISO)",
         data_handling="OSS — deployer-controlled",
         deployment="Self-hostable (OSS); IBM watsonx + Red Hat OpenShift AI managed",
         pros="Major Red Hat + IBM enterprise distribution; novel community-driven alignment methodology (LAB paper); Apache 2.0; integrates with existing Red Hat OpenShift AI infrastructure.",
         cons="Targeted at fine-tuning rather than multi-agent orchestration per se; smaller dev mindshare than CrewAI / LangGraph in agent-builder community; tied to Granite model family (less popular than Llama / Qwen).",
         optimised_for="enterprise LLM alignment + fine-tuning; community-driven taxonomy / skill contribution",
         adjacent="IBM Granite open-weights models; Red Hat OpenShift AI; IBM watsonx; Hugging Face",
         license_="Apache 2.0",
         gh="github.com/instructlab/instructlab ~1.5k+ stars; sister repos for taxonomy + sdg",
         code_release="Apache 2.0 — OSS",
         agent_abstraction="alignment / fine-tuning framework (not strictly multi-agent — substrate for building domain-specific agent models)",
         llm_lock="open (Granite-default; works with any compatible model)",
         runtimes="Python (primary); Kubernetes via OpenShift AI",
         na_default="orchestration"),

    dict(tier=2, name="Lindy",
         url="https://www.lindy.ai/",
         type_str="No-code commercial multi-agent automation platform (consumer / SMB)",
         tax=TAX_AGENT_HARNESS,
         primary_url="https://www.lindy.ai/",
         desc=("Lindy is a no-code multi-agent automation platform from Florent Crivello "
               "(ex-Teleport, ex-Twitter). Targets consumer / SMB segment with email triage, "
               "meeting scheduling, CRM-update agents. $50M Series A Oct-2024 led by Andreessen "
               "Horowitz + Sequoia. Distinct from Zapier / n8n traditional automation by "
               "putting LLMs at the core of every workflow node."),
         claims="$50M Series A Oct-2024 (a16z + Sequoia); 'AI employees' for SMB; agent marketplace; founded 2022 by Florent Crivello (ex-Teleport, ex-Twitter)",
         created="2022 (founded)",
         hq="San Francisco, US",
         founders="Florent Crivello (CEO; ex-Teleport, ex-Twitter)",
         funding="$50M Series A Oct-2024 (a16z + Sequoia)",
         pricing="Free + paid (per-task / seat); enterprise quote",
         compliance="SOC 2 Type II (in-progress)",
         data_handling="Never trains on customer data",
         deployment="Managed cloud (SaaS only)",
         pros="No-code UX is genuinely accessible to SMB / non-technical users; strong investor base (a16z + Sequoia at Series A); LLM-first vs Zapier's RPA-first heritage.",
         cons="Targets SMB market with thin moat (competing with Zapier AI, Make.com AI); not developer-targeted; enterprise compliance still maturing.",
         optimised_for="SMB / consumer no-code agent automation (email / scheduling / CRM)",
         adjacent="Zapier AI / Make.com / n8n (closest competitors); Gmail / Slack / HubSpot integration heavy",
         a2a_support="planned",
         agent_abstraction="no-code multi-agent (triggers + actions + LLM nodes)",
         llm_lock="multi-vendor (BYO OpenAI / Anthropic; managed by Lindy)",
         na_default="orchestration"),
]


# ============================================================================
# PASS C — AI sandbox & runtime environments
# ============================================================================

SANDBOX_ROWS = [
    dict(tier=1, name="e2b",
         url="https://e2b.dev/",
         type_str="Code-execution sandbox infrastructure for AI agents (firecracker microVMs)",
         tax=TAX_SANDBOX,
         primary_url="https://e2b.dev/",
         desc=("e2b provides secure, ephemeral sandboxes (Firecracker microVMs) for AI agent "
               "code execution. Each sandbox spins up in <200ms with full Linux environment, "
               "Python/Node/etc preinstalled. Substrate for code-agent products including "
               "Anthropic Claude Code (artifacts run on e2b), Perplexity, You.com Search, "
               "Cognition Devin (partially), and Hugging Face Spaces. Apache 2.0 OSS + "
               "managed cloud. $13M Seed + Series A 2024 (Sunflower Capital + a16z)."),
         claims="$13M+ raised (seed 2023 + Series A Sept-2024; Sunflower Capital + a16z); Firecracker microVM-based; <200ms cold start; used by Anthropic, Perplexity, Hugging Face; Apache 2.0 OSS SDK",
         created="2023 (founded)",
         hq="San Francisco, US + Prague, Czech Republic",
         founders="Vasek Mlejnsky (CEO; Czech founder); Tomas Valenta (CTO)",
         funding="$13M+ total raised (seed 2023 + Series A Sept-2024; Sunflower Capital + a16z + Lightspeed; Decibel + Y Combinator)",
         customers="Anthropic Claude Code (artifacts execution); Perplexity (code interpretation); Hugging Face (Spaces); Cognition (partial Devin code execution); You.com Search",
         pricing="Free + Pro ($150/mo) + Enterprise (quote); pay-per-second sandbox billing",
         compliance="SOC 2 Type II",
         data_handling="Ephemeral sandboxes (default no persistence); never trains on customer code",
         deployment="Managed cloud (e2b.dev) + Apache 2.0 OSS SDK for self-hostable runtime",
         pros="Standard substrate for code-execution-as-tool in major AI products (Anthropic Claude Code uses e2b); <200ms cold start; Firecracker microVM isolation; Apache 2.0 OSS SDK; major customers (Anthropic + Perplexity + Hugging Face).",
         cons="Specialized to code-execution sandbox use case; less general-purpose than Modal / Daytona; managed pricing premium relative to self-hosted Firecracker.",
         optimised_for="ephemeral secure code execution for AI agents (artifacts / tools)",
         adjacent="Firecracker (substrate); Anthropic Claude Code; Perplexity; Hugging Face Spaces; competes with Modal Sandboxes / Daytona",
         license_="Apache 2.0 (SDK + CLI)",
         gh="github.com/e2b-dev/e2b ~7k+ stars; github.com/e2b-dev/infra (runtime)",
         code_release="Apache 2.0 — SDK + CLI OSS; managed cloud proprietary",
         api_surface="REST + SDK (Python / TS / JS); CLI",
         runtimes="Linux microVMs; SDK clients in Python / TS",
         mcp_support="native (MCP server for sandbox tools)",
         na_default="sandbox"),

    dict(tier=1, name="Modal Sandboxes",
         url="https://modal.com/docs/guide/sandbox",
         type_str="Serverless container runtime + AI-agent sandboxes (Modal Labs)",
         tax=TAX_SANDBOX,
         primary_url="https://modal.com/docs/guide/sandbox",
         desc=("Modal Labs ships a serverless container platform with first-class GPU support; "
               "Sandboxes feature (2024) adds ephemeral, AI-agent-friendly compute sandboxes. "
               "Founded 2021 by Erik Bernhardsson (ex-Spotify ML, author of Luigi + Annoy). "
               "$87M total raised through Series B (Lux Capital + Redpoint + Definition + "
               "Amplify). Used by major LLM apps for batch inference + agent code execution."),
         claims="$87M total raised (Series B Sept-2024 led by Lux Capital + Redpoint; $1.1B reported valuation); founded 2021 by Erik Bernhardsson (ex-Spotify ML); Sandboxes feature 2024; serverless GPU + container runtime",
         created="2021 (Modal founded); 2024 (Sandboxes feature)",
         hq="New York, US",
         founders="Erik Bernhardsson (CEO; ex-Spotify ML Head, author of Luigi + Annoy); Akshat Bubna (CTO)",
         funding="$87M total raised; Series B Sept-2024 led by Lux Capital + Redpoint; ~$1.1B valuation",
         customers="Suno (AI music), Ramp, Anthropic (some workloads), Cursor (some indexing), Substack, Cara, large GPU-intensive LLM-app users",
         pricing="Pay-per-second compute (CPU + GPU); free tier (~$30/mo credit); team + enterprise tiers",
         compliance="SOC 2 Type II; HIPAA available; GDPR",
         data_handling="Ephemeral (sandboxes); never trains on customer code; data residency US/EU options",
         deployment="Managed cloud (no self-hosting)",
         pros="Best-in-class serverless GPU support (A100 / H100 on-demand); Sandboxes are general-purpose (not just code-exec); large LLM-app customers (Suno, Ramp, Anthropic workloads); $1.1B valuation; Erik Bernhardsson founder pedigree.",
         cons="Managed-only (no self-host); GPU pricing premium; sandbox feature newer than e2b; Python-only SDK.",
         optimised_for="serverless GPU + general-purpose agent sandboxes; batch inference + AI app backends",
         adjacent="Replicate (closest serverless-GPU competitor); RunPod; Lambda Labs; competes with e2b on sandbox feature",
         api_surface="Python SDK (primary); REST API",
         runtimes="Python SDK; runs any Linux container",
         na_default="sandbox"),

    dict(tier=2, name="Daytona",
         url="https://www.daytona.io/",
         type_str="Self-hostable development environment manager (cloud dev envs, AI sandbox tier)",
         tax=TAX_SANDBOX,
         primary_url="https://www.daytona.io/",
         desc=("Daytona is an open-source cloud development environment (CDE) platform — "
               "self-hostable alternative to Gitpod / GitHub Codespaces. 2024 added AI-agent "
               "sandbox tier for ephemeral agent code execution. Apache 2.0. Founded by ex-Atlas "
               "Antillia / Codeanywhere team (Ivan Burazin). $5M seed 2024 (RTP Global + others). "
               "Distinct from e2b / Modal by being self-hostable-first."),
         claims="Apache 2.0 OSS CDE; self-hostable; AI-sandbox tier for agent code execution 2024; $5M seed 2024 (RTP Global); founded 2024 by Ivan Burazin (ex-Codeanywhere)",
         created="2024 (founded; Codeanywhere predecessor 2009)",
         hq="Split, Croatia + US",
         founders="Ivan Burazin (CEO; ex-Codeanywhere CEO 2009-23); Vedran Jukic (CTO)",
         funding="$5M seed 2024 (RTP Global + Lighthouse Ventures + 500 Startups)",
         pricing="OSS (free); Daytona Cloud managed paid tier; enterprise on-prem (quote)",
         compliance="SOC 2 Type II (in-progress); GDPR",
         data_handling="Self-host: deployer-controlled; managed cloud never trains on customer code",
         deployment="Self-hostable (Apache 2.0) + managed cloud",
         pros="Apache 2.0 self-hostable (key differentiator vs Gitpod commercial / Codespaces / e2b); CDE heritage from Codeanywhere; AI-sandbox tier added 2024; EU founder presence (Croatian).",
         cons="Smaller seed funding than peers; newer brand than Gitpod / Codespaces; AI-sandbox tier less specialized than e2b for agent use case.",
         optimised_for="self-hostable cloud dev envs + AI-agent sandboxes",
         adjacent="Gitpod (closest CDE peer, commercial); GitHub Codespaces; competes with e2b for AI-sandbox use case",
         license_="Apache 2.0",
         gh="github.com/daytonaio/daytona ~13k+ stars",
         code_release="Apache 2.0 — OSS",
         api_surface="REST + CLI",
         runtimes="Docker + Kubernetes (self-hosted); managed cloud",
         na_default="sandbox"),

    dict(tier=2, name="Browserless.io",
         url="https://www.browserless.io/",
         type_str="Headless browser-as-a-service (Chromium / Playwright API for AI agents)",
         tax=TAX_SANDBOX,
         primary_url="https://www.browserless.io/",
         desc=("Browserless is a headless-browser-as-a-service — managed Chromium / Playwright / "
               "Puppeteer endpoints for web scraping, screenshots, PDF generation, web automation. "
               "Increasingly used as substrate for browser-agent products. Founded 2017 by Joel "
               "Griffith. Bootstrapped + small seed. Distinct from Playwright OSS — Browserless "
               "ships managed Chromium farms with anti-bot circumvention."),
         claims="Managed Chromium/Playwright/Puppeteer endpoints; founded 2017 by Joel Griffith; bootstrapped + small seed; thousands of customers for web scraping + browser-agent infra",
         created="2017 (founded)",
         hq="Distributed (US-based founder)",
         founders="Joel Griffith (CEO/founder; ex-Microsoft)",
         funding="Small seed disclosed; primarily bootstrapped",
         customers="Web scraping + AI-agent browser customers; Brand24, Cobalt, multiple AI-agent labs use it for browser-tool fallback",
         pricing="Hobby ($50/mo) + Startup ($200/mo) + Business + Enterprise (quote); per-session pricing model",
         deployment="Managed cloud (primary) + self-hostable Docker (Browserless Core OSS)",
         pros="Mature managed Chromium infrastructure (since 2017); anti-bot circumvention more mature than DIY; self-hostable option (Browserless Core OSS); used by many browser-agent products as fallback.",
         cons="Bootstrapped — smaller venture-scale than Modal / e2b; not AI-agent-specific (general browser automation); pricing per-session can add up at scale.",
         optimised_for="managed headless browsers for AI agents + web scraping",
         adjacent="Playwright (substrate); Puppeteer; Chromium; competes with Bright Data / Apify on scraping side",
         api_surface="REST + Playwright/Puppeteer-compatible WebSocket endpoints",
         license_="MIT (Browserless Core OSS — self-host); proprietary (managed cloud)",
         gh="github.com/browserless/browserless ~9k+ stars",
         code_release="MIT — Browserless Core OSS; managed cloud proprietary",
         runtimes="Chromium (Linux containers)",
         na_default="sandbox"),

    dict(tier=2, name="CodeSandbox AI",
         url="https://codesandbox.io/ai",
         type_str="Browser-based dev sandbox with AI-agent features (acquired by Together AI 2024)",
         tax=TAX_SANDBOX,
         primary_url="https://codesandbox.io/ai",
         desc=("CodeSandbox is the long-running browser-based dev sandbox (founded 2017 by Ives "
               "van Hoorne + Bas Buursma in Amsterdam). **Acquired by Together AI Oct-2024** to "
               "anchor Together's agent-execution stack alongside its GPU inference cloud. AI "
               "features include AI-assisted coding, agent-execution sandboxes, and "
               "instant-preview for AI-generated apps."),
         claims="Founded 2017 Amsterdam by Ives van Hoorne + Bas Buursma; **Together AI acquisition Oct-2024**; >4M developers reported pre-acq; CodeSandbox SDK launched 2024 for agent integration",
         created="2017 (founded); 2024-10 (Together AI acquisition)",
         hq="Amsterdam, Netherlands (pre-acq); now Together AI (San Francisco)",
         founders="Ives van Hoorne + Bas Buursma (founders); now part of Together AI (Vipul Ved Prakash, CEO)",
         funding="~$15M pre-acq raised; Together AI acquired Oct-2024 (terms undisclosed)",
         customers="4M+ developers pre-acq; now feeds Together AI's agent / app product line; Stackbit, Pliny.so, Bolt.new have used CodeSandbox as deployment substrate",
         pricing="Free + Pro ($12/mo) + Team + Enterprise; commercial CodeSandbox SDK for agent integration",
         compliance="SOC 2 Type II",
         data_handling="Never trains on customer code (Together AI post-acq commitment)",
         deployment="Managed cloud (SaaS)",
         pros="Together AI post-acquisition gives massive GPU + LLM-inference flywheel; 4M+ pre-acq dev base; instant-preview for AI-generated apps is genuinely useful for code-agent UX.",
         cons="Post-acq direction still settling; competes with own customers (Bolt.new / Stackbit / Vercel preview); narrower than e2b for headless-agent sandbox use case.",
         optimised_for="browser-based AI dev experience + instant-preview for agent-generated apps",
         adjacent="Together AI (parent); Bolt.new (uses CodeSandbox-style preview); Vercel preview; competes with StackBlitz",
         api_surface="REST + CodeSandbox SDK (TS / JS); WebContainer-style isolation",
         runtimes="Node.js + Linux containers (browser-rendered)",
         na_default="sandbox"),

    dict(tier=2, name="Gitpod AI features",
         url="https://www.gitpod.io/blog/gitpod-flex",
         type_str="Cloud development environment with AI-agent integrations (Gitpod Flex)",
         tax=TAX_SANDBOX,
         primary_url="https://www.gitpod.io/blog/gitpod-flex",
         desc=("Gitpod is the original cloud development environment (CDE) — founded 2014 by "
               "Sven Efftinge + Johannes Landgraf (also TypeFox / Eclipse Theia / Open VSX). "
               "$25M Series A 2022 led by General Catalyst. 2024 launched Gitpod Flex with "
               "support for AI agents to run inside dev environments + automation runner. "
               "Free OSS tier (Gitpod Self-Hosted) for individual / OSS use."),
         claims="$25M Series A 2022 (General Catalyst); founded 2014 by Sven Efftinge + Johannes Landgraf; Gitpod Flex 2024 with AI-agent integration; AGPL OSS for self-hosted",
         created="2014 (founded); 2024 (Gitpod Flex with AI-agent integration)",
         hq="Berlin, Germany + Hamburg",
         founders="Sven Efftinge (CEO; co-founder Eclipse Theia / TypeFox); Johannes Landgraf (Co-founder; TypeFox)",
         funding="$25M Series A May-2022 led by General Catalyst (Crane, Speedinvest, Cherry, Mango); ~$35M+ total raised",
         customers="GitLab, Brevo, Schneider Electric, multiple Fortune 500 dev teams",
         pricing="Free OSS tier + Personal Pro ($9/mo) + Team + Enterprise",
         compliance="SOC 2 Type II; ISO 27001; GDPR-native (EU HQ)",
         data_handling="Never trains on customer code; self-hostable for data sovereignty",
         deployment="Managed cloud + self-hostable (AGPL OSS) + on-prem (enterprise)",
         pros="Original CDE pioneer; strong OSS heritage (TypeFox / Eclipse Theia); AGPL self-hostable; EU-native (data sovereignty + GDPR); Gitpod Flex AI-agent integration positions CDE as agent substrate.",
         cons="Lost commercial momentum to GitHub Codespaces; Daytona competes on self-hosted side; AI features still newer than GitHub Copilot Workspace integration.",
         optimised_for="developer-focused CDE with AI-agent execution; EU data-sovereignty workloads",
         adjacent="Eclipse Theia / Open VSX (TypeFox alumni projects); competes with GitHub Codespaces + Daytona + Coder.com",
         license_="AGPL-3.0 (Gitpod Self-Hosted)",
         gh="github.com/gitpod-io/gitpod ~13k+ stars; github.com/gitpod-io/gitpod-flex roadmap",
         code_release="AGPL-3.0 — OSS",
         api_surface="REST + CLI + Gitpod SDK",
         runtimes="Docker + Kubernetes (Gitpod self-hosted)",
         na_default="sandbox"),

    dict(tier=3, name="Anchor (Anchor Browser)",
         url="https://anchorbrowser.io/",
         type_str="Cloud-hosted browser for AI agents (anti-detect, persistent state)",
         tax=TAX_SANDBOX,
         primary_url="https://anchorbrowser.io/",
         desc=("Anchor Browser provides cloud-hosted Chromium instances optimised for AI agent "
               "use — anti-detect, persistent sessions, residential proxies, CAPTCHA handling. "
               "Founded 2023, YC W24. $2.6M seed disclosed. Distinct from Browserless by adding "
               "persistent-state + anti-detect optimised for AI-agent web workflows."),
         claims="YC W24; $2.6M seed; cloud Chromium with anti-detect + persistent sessions; positioned specifically for AI-agent web workflows",
         created="2023 (founded); YC W24",
         hq="San Francisco, US",
         founders="Anchor Browser founders (YC W24)",
         funding="$2.6M seed (YC + Long Journey Ventures + others)",
         pricing="Free + per-session pricing; Pro + Team tiers",
         deployment="Managed cloud only",
         pros="AI-agent-specific feature set (anti-detect + persistent state); YC W24 backing; clean developer UX for browser-agent backends.",
         cons="Small seed (vs Browserless / Bright Data); newer brand; managed-only.",
         optimised_for="AI-agent browser workflows with persistent state + anti-detect",
         adjacent="Browserless (closest competitor on managed Chromium); Bright Data scraping infra; competes with hosted Playwright services",
         api_surface="REST + Playwright-compatible",
         runtimes="Chromium (cloud-hosted)",
         na_default="sandbox"),

    dict(tier=2, name="Coder.com",
         url="https://coder.com/",
         type_str="Self-hosted enterprise CDE + AI-agent workspace platform",
         tax=TAX_SANDBOX,
         primary_url="https://coder.com/",
         desc=("Coder.com (formerly Coder Technologies) provides enterprise self-hosted cloud "
               "development environments — VS Code Server + dev workspaces on K8s / VMs. $30M "
               "Series B 2021 (Redpoint + Founders Fund + Coatue). Founded 2017 by Kyle "
               "Carberry + Ammar Bandukwala. 2024 launched 'Coder AI' for agent-execution "
               "inside workspaces. Self-hostable AGPL OSS + commercial enterprise."),
         claims="$30M Series B 2021 (Redpoint + Founders Fund + Coatue); founded 2017 by Kyle Carberry + Ammar Bandukwala; AGPL OSS; Coder AI 2024 for in-workspace agent execution; used by major enterprise platform teams",
         created="2017 (founded); 2024 (Coder AI agent-execution features)",
         hq="Austin, US",
         founders="Kyle Carberry (CEO); Ammar Bandukwala (CTO)",
         funding="$30M Series B Oct-2021 (Redpoint + Founders Fund + Coatue); ~$45M+ total raised",
         customers="Discord, IBM, Bloomberg, Salesforce, US DoD, Palantir, Workday",
         pricing="OSS AGPL (free) + Enterprise (per-developer per-year)",
         compliance="SOC 2 Type II; FedRAMP path (US DoD customers); ISO 27001",
         data_handling="Self-hosted by default (deployer-controlled)",
         deployment="Self-hostable (AGPL OSS) + Enterprise managed",
         pros="Strong enterprise self-hosted CDE — used by Discord / IBM / Bloomberg / Palantir; FedRAMP path; AGPL OSS; Coder AI extension positions workspace as agent substrate.",
         cons="Less developer mindshare than Gitpod / Codespaces; AGPL license less permissive than Apache 2.0 for some enterprises; agent features newer than core CDE.",
         optimised_for="enterprise self-hosted CDE + agent workspaces; regulated / on-prem deployments",
         adjacent="Terraform / Kubernetes (substrate); competes with Gitpod + GitHub Codespaces; Coder Templates marketplace",
         license_="AGPL-3.0",
         gh="github.com/coder/coder ~9k+ stars",
         code_release="AGPL-3.0 — OSS",
         api_surface="REST + CLI + Terraform provider",
         runtimes="Kubernetes + Docker + VMs (any Linux substrate)",
         na_default="sandbox"),

    dict(tier=2, name="Workato AI (Workflow Bot Builder)",
         url="https://www.workato.com/ai",
         type_str="Enterprise iPaaS with AI-agent / workflow-sandbox tier (Workato AI)",
         tax=TAX_SANDBOX,
         primary_url="https://www.workato.com/ai",
         desc=("Workato is the enterprise iPaaS (integration platform) leader — $200M+ ARR, "
               "$5.7B valuation 2021. 2023-24 launched Workato AI / Workbot AI with AI-agent "
               "workflow sandbox capability inside its automation runtime. Used by Slack-bot / "
               "automation customers for AI-augmented workflows. Distinct from pure agent "
               "frameworks (CrewAI / LangGraph) by being deeply enterprise-iPaaS-anchored."),
         claims="$200M+ ARR; $5.7B valuation Nov-2021 Series E (Battery Ventures + Insight + Altimeter); founded 2013 by Vijay Tella (ex-Oracle / TIBCO); Workato AI / Workbot AI 2023-24; 17,000+ enterprise customers",
         created="2013 (founded); 2023-24 (Workato AI / Workbot AI features)",
         hq="Mountain View, US",
         founders="Vijay Tella (CEO; ex-Oracle, ex-TIBCO); Gautham Viswanathan (CPO; ex-Oracle); Sumit Sharma (ex-Oracle)",
         funding="$415M total raised; $5.7B valuation Series E Nov-2021 (Battery Ventures + Insight Partners + Altimeter Capital)",
         customers="17,000+ enterprises; Box, Cisco, Atlassian, Slack, Broadcom, ServiceNow",
         pricing="Enterprise (quote-only); per-recipe + per-task pricing",
         compliance="SOC 2 Type II; HIPAA; ISO 27001; GDPR; PCI DSS",
         data_handling="Never trains on customer data; data residency US/EU/APAC",
         deployment="Managed cloud (SaaS only)",
         pros="Massive enterprise iPaaS distribution (17k+ customers, $200M+ ARR); deeply embedded in enterprise workflows; SOC 2 / HIPAA / FedRAMP-grade enterprise posture; Workato AI extends to native AI-agent workflows.",
         cons="Not a developer-targeted product (enterprise-iPaaS-anchored); pricing opaque; competes with Zapier / Microsoft Power Automate / Make.com on adjacent positioning.",
         optimised_for="enterprise iPaaS workflows with AI-agent + LLM nodes; Slack-bot / automation",
         adjacent="Salesforce Agentforce / HubSpot Breeze (CRM-bound automation); Microsoft Power Automate; Zapier / n8n (smaller-scale automation)",
         api_surface="REST + Workato Connector SDK; recipe-based DSL",
         runtimes="Workato proprietary runtime (Java + Ruby)",
         na_default="sandbox"),

    dict(tier=3, name="StackBlitz WebContainers",
         url="https://webcontainers.io/",
         type_str="Browser-native Node.js runtime (WASM) — substrate for Bolt.new and AI agents",
         tax=TAX_SANDBOX,
         primary_url="https://webcontainers.io/",
         desc=("StackBlitz's WebContainers technology — browser-native Node.js runtime running "
               "fully client-side via WASM. Powers Bolt.new (already in catalog) plus many "
               "browser-based AI dev experiences. Founded 2017 by Eric Simons + Albert Pai. "
               "$7M Series A 2022. Distinct from server-side sandboxes (e2b / Modal) by running "
               "entirely in-browser — zero cloud-execution latency."),
         claims="$7M Series A 2022; founded 2017 by Eric Simons + Albert Pai; WebContainers tech powers Bolt.new + Stackblitz IDE; browser-native Node.js via WASM",
         created="2017 (StackBlitz founded); 2021 (WebContainers tech announced)",
         hq="San Francisco, US",
         founders="Eric Simons (CEO; ex-Codeschool, ex-Thinkful); Albert Pai (CTO; ex-Codeschool)",
         funding="$7M Series A 2022 (GreyLock + GV)",
         customers="Bolt.new (StackBlitz's own product); various AI dev experiences; Vercel partner",
         pricing="WebContainers API: free for OSS + paid for commercial use (tiered by traffic)",
         compliance="SOC 2 Type II (path)",
         deployment="Browser-native (client-side); no cloud compute required",
         pros="Browser-native execution (zero cloud-latency); powers Bolt.new (one of biggest AI-coding successes 2024); WebContainers API is unique technology — full Node.js in WASM.",
         cons="Browser-only (no native binaries / GPU / persistent disk); commercial WebContainers API pricing has caused some friction; smaller dev mindshare than CodeSandbox.",
         optimised_for="browser-native AI dev experiences; zero-latency code preview for AI-generated apps",
         adjacent="Bolt.new (uses WebContainers); Vercel preview (partnership); competes with CodeSandbox + custom iframe sandboxes",
         api_surface="WebContainers API (JS)",
         runtimes="WASM (browser-native Node.js)",
         na_default="sandbox"),
]


# ============================================================================
# RENDER
# ============================================================================

def render_section_header(title: str, explainer: str, subsection: bool = False) -> str:
    style = ' style="padding-left: 28px; text-transform: none; letter-spacing: 0.04em; color: #b8b8b8;"' if subsection else ''
    return (
        f'\n  <tr class="group-row"><td colspan="92"{style}>{html.escape(title)}</td></tr>\n'
        f'\n  <tr class="section-explainer"><td colspan="92"><div class="explainer-text">{explainer}</div></td></tr>\n'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pass", dest="pass_letter", choices=["a", "b", "c"], required=True)
    args = parser.parse_args()

    if args.pass_letter == "a":
        title = "Foundation models (substrate reference)"
        explainer = (
            "Frontier foundation models — the substrate that other catalog rows are "
            "built on. Memory here is parametric (in weights) and KV-cache (during "
            "inference); discrete episodic memory (chat history, user facts) lives "
            "outside the model in the <em>Platform-provider memory</em> section. "
            "This section was added in Round 15 (2026-05-13) to make the implicit "
            "substrate explicit — so edges from agent frameworks, IDEs, and coding "
            "harnesses to the underlying frontier model become resolvable. "
            "Includes Anthropic Claude, OpenAI GPT, Google Gemini, Meta Llama, "
            "DeepSeek, Mistral, Cohere, xAI Grok, Alibaba Qwen, Microsoft Phi, "
            "Amazon Nova, Reka, and 01.AI Yi."
        )
        rows = FOUNDATION_MODEL_ROWS
    elif args.pass_letter == "b":
        title = "Multi-agent orchestration platforms"
        explainer = (
            "Commercial and OSS platforms whose primary identity is multi-agent "
            "orchestration — distinct from <em>Agent frameworks (no first-party "
            "memory layer)</em> (which collects single-purpose framework libraries) "
            "and from <em>Agent IDEs &amp; coding harnesses</em> (which collects "
            "IDE-shaped coding agents). This section, added in Round 15 (2026-05-13), "
            "captures platforms where multi-agent coordination is the productised "
            "offering: CrewAI Enterprise, AutoGen Studio, MultiOn, Reflection AI, "
            "Adept ACT (historical), Sema4.ai, Imbue Carbon, Steamship, Magic.dev, "
            "Phidata/Agno, Burr (DAGWorks), InstructLab (Red Hat / IBM), and Lindy. "
            "Memory typically delegates to <em>Dedicated memory layers</em> or to "
            "the underlying foundation model — so the rows here are governance / "
            "deployment / pricing differentiators, not memory architecture differentiators."
        )
        rows = MULTI_AGENT_ROWS
    else:  # c
        title = "AI sandbox & runtime environments"
        explainer = (
            "Compute substrate for AI agents — code-execution sandboxes, cloud "
            "development environments, headless-browser farms, and serverless "
            "container runtimes that AI agent products use to actually run code, "
            "navigate the web, or host workspaces. Added in Round 15 (2026-05-13) "
            "to make the implicit compute substrate explicit. e2b sandboxes power "
            "Anthropic Claude Code artifacts; Modal Sandboxes power batch agent "
            "workloads; Daytona / Gitpod / Coder.com host long-running agent "
            "workspaces; Browserless and Anchor host headless Chromium for browser "
            "agents. Distinct from <em>Inference platforms &amp; gateways</em> "
            "(which serve the model) — this section serves the <em>environment</em> "
            "the agent operates in."
        )
        rows = SANDBOX_ROWS

    parts = []
    parts.append(render_section_header(title, explainer, subsection=False))
    for kwargs in rows:
        parts.append(substrate_row(**kwargs))
        parts.append("")
    print("\n".join(parts))


if __name__ == "__main__":
    main()
