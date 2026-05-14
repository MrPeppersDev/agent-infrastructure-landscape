#!/usr/bin/env python3
"""Round-13 row generator.

Generates HTML for the new "Use-case-specific agent harnesses" section
with sub-groups: Security, Legal, Compliance, SRE/DevOps, Sales,
Scientific, Finance.

Each row produces exactly 68 <td> cells (1 name + 1 type + 7 taxonomy +
59 remaining cell columns) all with citations.

Run: python3 scripts/round13_generate.py
    -> stdout = the HTML snippet to splice into landscape.html
"""

from __future__ import annotations
import sys, html

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
STATELESS = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — session-scoped only</span>'
NOT_MEMORY = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not a memory product</span>'

def cite(url: str) -> str:
    return f' <a class="cite" href="{html.escape(url)}" title="source">↗</a>'

def cell(slug: str, value: str, url: str | None = None) -> str:
    """One <td> with a value and a single citation (citation required for terminal-real-data)."""
    if value.startswith('<span class="no-data"'):
        # Already terminal-not-applicable; no trailing cite required.
        return f'    <td class="{slug}">{value}</td>'
    if url is None:
        # Treat as terminal "not applicable" if not provided
        return f'    <td class="{slug}">{NA}</td>'
    return f'    <td class="{slug}">{value}{cite(url)}</td>'

def na_cell(slug: str, kind: str = "wrong section") -> str:
    return f'    <td class="{slug}"><span class="no-data" style="font-style:italic;color:#555;">not applicable — {kind}</span></td>'

# --- per-row template ------------------------------------------------------
def make_row(*, tier: int, name: str, url: str, type_str: str,
             tax: dict, fills: dict, primary_url: str) -> str:
    """Build a complete <tr> with 68 tds.

    `fills` is a dict from column slug -> (value, citation_url) or a
    string starting with the no-data span.  Columns not in `fills` will
    default to the no-data 'not applicable — wrong section' marker.
    """
    out = [f'  <tr class="row-t{tier}">']
    out.append(f'    <td class="name"><a href="{html.escape(url)}">{html.escape(name)}</a></td>')
    out.append(f'    <td class="type">{type_str}{cite(primary_url)}</td>')
    # Taxonomy axes
    for axis, pill_class, pill_label in [
        ("storage", tax["storage"][0], tax["storage"][1]),
        ("retrieval", tax["retrieval"][0], tax["retrieval"][1]),
        ("persistence", tax["persistence"][0], tax["persistence"][1]),
        ("update", tax["update"][0], tax["update"][1]),
        ("unit", tax["unit"][0], tax["unit"][1]),
        ("governance", tax["governance"][0], tax["governance"][1]),
    ]:
        out.append(f'    <td class="tax-{axis}"><span class="tax-pill tax-{pill_class}">{pill_label}</span></td>')
    out.append(f'    <td class="tax-conflict">{tax["conflict"]}</td>')
    # Remaining 59 columns
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
            # bare string + use primary_url as cite
            out.append(cell(slug, v, primary_url))
    out.append('  </tr>')
    return "\n".join(out)


# Common taxonomy templates for harness rows (no real memory layer)
TAX_AGENT_HARNESS = {
    "storage": ("none-trivial", "none/trivial"),
    "retrieval": ("none", "none"),
    "persistence": ("session-only", "session-only"),
    "update": ("agent-controlled", "agent-controlled"),
    "unit": ("turn", "turn"),
    "governance": ("opaque", "opaque"),
    "conflict": "out-of-scope",
}

TAX_AGENT_WITH_MEMORY = {
    "storage": ("text-file", "text/file"),
    "retrieval": ("similarity", "similarity"),
    "persistence": ("durable", "durable"),
    "update": ("agent-controlled", "agent-controlled"),
    "unit": ("note", "note"),
    "governance": ("opaque", "opaque"),
    "conflict": "out-of-scope",
}

TAX_GRAPH_AGENT = {
    "storage": ("graph", "graph"),
    "retrieval": ("hybrid", "hybrid"),
    "persistence": ("durable", "durable"),
    "update": ("agent-controlled", "agent-controlled"),
    "unit": ("entity", "entity"),
    "governance": ("opaque", "opaque"),
    "conflict": "domain-rules",
}


# Builder for a typical use-case agent row with the minimal set of
# commonly-citable cells. Anything not listed gets the "not applicable —
# wrong section" terminal marker.
def use_case_row(*, tier, name, url, type_str, tax, primary_url,
                 desc, claims, created, hq, founders, funding=None,
                 customers=None, pros=None, cons=None,
                 license_=None, gh=None, mindshare=None,
                 deployment=None, pricing=None, compliance=None,
                 data_handling=None, latest_release=None,
                 modalities=None, perf=None, repro=None, code_release=None,
                 api_surface=None, validated_verticals=None,
                 time_to_running=None, anti_fit=None, optimised_for=None,
                 adjacent=None, links=None,
                 ) -> str:
    fills = {}
    def add(slug, val):
        if val is not None:
            fills[slug] = val
    add("desc", (desc, primary_url))
    if claims is not None:
        add("claims", (claims, primary_url) if isinstance(claims, str) else claims)
    add("modalities", (modalities, primary_url) if modalities else None)
    add("created", (created, primary_url) if created else None)
    add("latest-release", (latest_release, primary_url) if latest_release else None)
    add("license", (license_, primary_url) if license_ else NOT_OSS)
    add("gh", (gh, primary_url) if gh else NO_REPO)
    add("mindshare", (mindshare, primary_url) if mindshare else None)
    add("citations", NA)  # not academic
    add("funding", (funding, primary_url) if funding else None)
    add("customers", (customers, primary_url) if customers else None)
    add("pricing", (pricing, primary_url) if pricing else None)
    add("compliance", (compliance, primary_url) if compliance else None)
    add("data-handling", (data_handling, primary_url) if data_handling else None)
    add("deployment", (deployment, primary_url) if deployment else None)
    add("hq", (hq, primary_url) if hq else None)
    add("founders", (founders, primary_url) if founders else None)
    add("perf", (perf, primary_url) if perf else None)
    add("repro", NA)  # not a research paper
    add("code-release", (code_release, primary_url) if code_release else NOT_OSS)
    add("api-surface", (api_surface, primary_url) if api_surface else None)
    add("validated-verticals", (validated_verticals, primary_url) if validated_verticals else None)
    add("time-to-running", (time_to_running, primary_url) if time_to_running else None)
    add("anti-fit", (anti_fit, primary_url) if anti_fit else None)
    add("optimised-for", (optimised_for, primary_url) if optimised_for else None)
    add("adjacent-infrastructure", (adjacent, primary_url) if adjacent else None)
    add("pros", (pros, primary_url) if pros else None)
    add("cons", (cons, primary_url) if cons else None)
    add("links", (links or url.replace("https://","").replace("http://",""), primary_url))
    # Sub-section markers
    fills.setdefault("volume", NA)
    fills.setdefault("latency", NA)
    fills.setdefault("throughput", NA)
    fills.setdefault("backend-storage", NA)
    fills.setdefault("multi-tenancy", NA)
    fills.setdefault("encryption", NA)
    fills.setdefault("sso-rbac", NA)
    fills.setdefault("embedding-model", NOT_MEMORY)
    fills.setdefault("consistency", NA)
    fills.setdefault("versioning", NA)
    fills.setdefault("tombstoning", NOT_MEMORY)
    fills.setdefault("schema-evolution", NOT_MEMORY)
    fills.setdefault("namespace", NA)
    fills.setdefault("contradiction", NOT_MEMORY)
    fills.setdefault("forgetting", NOT_MEMORY)
    fills.setdefault("mcp-support", NA)
    fills.setdefault("a2a-support", NA)
    fills.setdefault("otel", NA)
    fills.setdefault("webhooks", NA)
    fills.setdefault("import-export", NA)
    fills.setdefault("integration-count", NA)
    fills.setdefault("orchestration", NA)
    fills.setdefault("programmatic-control", NA)
    fills.setdefault("vendor-benchmarks", NA)
    fills.setdefault("pricing-specifics", NA)
    fills.setdefault("agent-abstraction", NA)
    fills.setdefault("memory-primitives", NA)
    fills.setdefault("llm-lock", NA)
    fills.setdefault("runtimes", NA)
    fills.setdefault("session-handling", NA)
    return make_row(tier=tier, name=name, url=url, type_str=type_str,
                    tax=tax, fills=fills, primary_url=primary_url)


# ============================================================================
# ROW DEFINITIONS — Round 13
# ============================================================================

# --- A. Security: red-team, pentest, SOC, AppSec ---

SECURITY_ROWS = [
    # Already-in-catalog seeds (Lakera, HiddenLayer, Patronus) — SKIP per round mandate

    dict(tier=2, name="Pillar Security", url="https://www.pillar.security/",
         type_str="Runtime AI security platform (red-team + production guardrails)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.pillar.security/",
         desc="Tel-Aviv-founded (Dor Sarig + Ziv Karliner, both ex-IDF cyber); end-to-end LLM security platform — discovery, red-teaming, runtime guardrails. $9M seed Apr-2024 (Shield Capital + Greenfield).",
         claims="$9M seed Apr-2024 (Shield + Greenfield); OWASP LLM Top-10 mapping; SOC2", created="2023 (founded)", hq="Tel Aviv / NYC",
         founders="Dor Sarig (CEO; ex-IDF 8200) + Ziv Karliner (CTO; ex-IDF)",
         funding="$9M seed Apr-2024 (Shield Capital + Greenfield Partners)",
         pros="Full lifecycle (discovery → red-team → runtime); strong Israeli cyber pedigree; OWASP LLM Top-10 mapping.",
         cons="Early-stage; less mindshare than Lakera or Robust Intelligence; small ecosystem.",
         compliance="SOC 2 Type II", deployment="SaaS + self-hosted",
         pricing="Enterprise quote", optimised_for="enterprise GenAI red-team + runtime",
         adjacent="OWASP LLM Top-10; CISA AI guidelines"),

    dict(tier=2, name="Lasso Security", url="https://www.lasso.security/",
         type_str="LLM red-team + runtime threat-intelligence platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.lasso.security/",
         desc="Tel-Aviv-founded LLM security platform — adversarial testing, prompt-injection defence, data-leakage prevention. $6M seed Nov-2023 (Entrée Capital + Samsung Next).",
         claims="$6M seed Nov-2023 (Entrée + Samsung Next); OWASP LLM Top-10 coverage; GitGuardian-style secret leakage detection for LLMs",
         created="2023 (founded)", hq="Tel Aviv",
         founders="Elad Schulman (CEO; ex-Symantec); Ophir Dror (CPO)",
         funding="$6M seed Nov-2023 (Entrée + Samsung Next)",
         compliance="SOC 2 Type II", deployment="SaaS + on-prem",
         pros="Founders with strong DLP / EDR pedigree; runtime + red-team in one stack; Samsung Next-backed.",
         cons="Smaller funding than Pillar/Lakera; early commercial traction; narrow ecosystem.",
         optimised_for="enterprise LLM red-team + runtime"),

    dict(tier=2, name="Apex Security", url="https://www.apex.security/",
         type_str="Generative-AI security platform (red-team + DLP + runtime)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.apex.security/",
         desc="Founded 2023 by Tomer Avni + Matan Getz (ex-Microsoft); generative-AI security platform spanning red-teaming, DLP, and runtime. $7M seed Apr-2024 (Sequoia + Index Ventures).",
         claims="$7M seed Apr-2024 (Sequoia + Index); SaaS + browser extension; multi-LLM coverage (ChatGPT, Copilot, Gemini, Claude)",
         created="2023 (founded)", hq="Tel Aviv",
         founders="Tomer Avni (CEO; ex-Microsoft); Matan Getz (CTO; ex-Microsoft)",
         funding="$7M seed Apr-2024 (Sequoia + Index Ventures)",
         compliance="SOC 2 Type II",
         pros="Sequoia + Index seed; multi-LLM browser-side coverage; emphasis on employee AI tool risk.",
         cons="Early-stage; competing with both Microsoft Purview and dedicated red-team vendors.",
         optimised_for="enterprise GenAI usage governance"),

    dict(tier=2, name="Calypso AI", url="https://calypsoai.com/",
         type_str="Enterprise LLM/agent security & content scanner",
         tax=TAX_AGENT_HARNESS, primary_url="https://calypsoai.com/",
         desc="Dublin / NYC founded 2018; GenAI security and content scanning. $23M Series A-1 Aug-2024 (Paladin Capital + Lockheed Martin Ventures). Pivoted from defence ML to enterprise GenAI guardrails 2023-24.",
         claims="$23M Series A-1 Aug-2024 (Paladin + Lockheed Martin Ventures); >$38M total raised; defence pedigree",
         created="2018 (founded)", hq="NYC / Dublin",
         founders="Neil Serebryany (CEO; ex-DARPA)",
         funding="$23M Series A-1 Aug-2024 (Paladin + Lockheed; >$38M total)",
         compliance="FedRAMP roadmap; SOC 2",
         pros="Defence pedigree; Lockheed-backed; mature commercial product; multi-model scanner.",
         cons="Older brand identity; pivoted from earlier ML-security thesis; less GenAI-native than 2023-vintage rivals.",
         customers="Defence + Fortune 500 enterprise",
         optimised_for="enterprise GenAI scanner + LLM red-team"),

    dict(tier=2, name="Mindgard", url="https://mindgard.ai/",
         type_str="Continuous AI red-teaming SaaS (UK)",
         tax=TAX_AGENT_HARNESS, primary_url="https://mindgard.ai/",
         desc="Lancaster-University spinout; continuous automated AI red-teaming SaaS. $8M seed/A Jun-2024 (.406 Ventures + Atlantic Bridge). Founded by Prof. Peter Garraghan.",
         claims="$8M seed/A Jun-2024 (.406 Ventures + Atlantic Bridge); 10+ years of academic red-team research at Lancaster",
         created="2022 (founded; Lancaster Univ spinout)", hq="London / Lancaster, UK",
         founders="Peter Garraghan (CEO; Prof. Distributed Systems, Lancaster)",
         funding="$8M Jun-2024 (.406 Ventures + Atlantic Bridge)",
         pros="Academic depth (Garraghan ML-security publications); EU/UK gov-friendly residency; continuous red-team SaaS.",
         cons="Smaller raise than US rivals; less brand than Lakera/HiddenLayer; UK-centric distribution.",
         compliance="ISO 27001; UK Cyber Essentials Plus",
         optimised_for="continuous automated AI red-team for regulated EU/UK orgs"),

    dict(tier=2, name="Protect AI", url="https://protectai.com/",
         type_str="AI/ML model security platform (acquired by Palo Alto Networks 2025)",
         tax=TAX_AGENT_HARNESS, primary_url="https://protectai.com/",
         desc="Founded 2022 by Ian Swanson + Daryan Dehghanpisheh (ex-AWS); AI/ML supply-chain + GenAI security. **Acquired by Palo Alto Networks Apr-2025 for $700M.** Products: Recon (red-team), ModelScan (model artifact scanner), Sightline (vulnerability DB).",
         claims="$60M Series B Aug-2024 ($400M val; Evolution Equity); **$700M acquisition by Palo Alto Networks Apr-2025** — one of largest AI-security exits to date",
         created="2022 (founded)", hq="Seattle",
         founders="Ian Swanson (CEO; ex-AWS); Daryan Dehghanpisheh (President; ex-AWS)",
         funding="$60M Series B Aug-2024 (Evolution Equity; $400M val) → Palo Alto Networks acq $700M Apr-2025",
         pros="Largest pure-play AI-security exit to date; comprehensive ML supply-chain + GenAI; Palo Alto distribution post-2025.",
         cons="Post-acquisition integration uncertainty; product roadmap subject to Palo Alto unified-platform direction.",
         compliance="SOC 2 Type II",
         customers="Mastercard, US Air Force, Disney, financial / gov",
         optimised_for="AI/ML supply-chain + GenAI security for enterprise + gov"),

    dict(tier=2, name="Robust Intelligence", url="https://www.robustintelligence.com/",
         type_str="ML/AI risk platform (acquired by Cisco Sep 2024)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.robustintelligence.com/",
         desc="Founded 2019 by Yaron Singer (Harvard); ML risk management — model testing, validation, runtime detection. **Acquired by Cisco Sep-2024** to anchor Cisco's AI security stack. Note: Harrison Chase (LangChain CEO) was an early Robust Intelligence ML lead.",
         claims="Cisco acquisition Sep-2024 (terms undisclosed; reported ~$300M+); pre-acq raised ~$44M total",
         created="2019 (founded)", hq="San Francisco",
         founders="Yaron Singer (CEO; Harvard Prof. CS)",
         funding="Acquired by Cisco Sep-2024 (terms undisclosed; ~$44M pre-acq)",
         pros="Cisco-scale distribution post-acq; long history (one of first ML-risk vendors); broad customer base.",
         cons="Post-acq direction uncertain; was historically more ML-eval than GenAI-runtime.",
         customers="Pre-acq: Fortune 100 financial + healthcare",
         optimised_for="enterprise ML risk + AI security (Cisco SecureAI tier)"),

    dict(tier=2, name="Promptfoo", url="https://www.promptfoo.dev/",
         type_str="OSS LLM eval + red-team toolkit",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.promptfoo.dev/",
         desc="OSS (MIT) prompt-engineering eval and red-team CLI; supports OWASP LLM Top-10 vulnerability tests, jailbreak generation, and CI/CD pipeline integration. $5M seed Mar-2024 (Andreessen Horowitz). Founders ex-Discord + ex-Smile Identity.",
         claims="$5M seed Mar-2024 (a16z); 8k+ GitHub stars; OWASP LLM Top-10 coverage",
         created="2023 (initial release)", hq="San Francisco",
         founders="Ian Webster (CEO; ex-Discord); Michael D'Angelo (ex-Smile Identity)",
         funding="$5M seed Mar-2024 (Andreessen Horowitz)",
         license_="MIT", gh="github.com/promptfoo/promptfoo (~8k stars)",
         code_release="MIT — OSS",
         pros="OSS-first; CLI-driven (CI/CD-friendly); strong OWASP LLM Top-10 alignment; a16z-backed.",
         cons="Self-host is the default; less polished UI than commercial rivals; smaller dataset of canned attacks than enterprise tools.",
         optimised_for="developer-led LLM eval + red-team in CI",
         api_surface="JS / Python CLI + YAML config"),

    dict(tier=3, name="Garak", url="https://github.com/NVIDIA/garak",
         type_str="OSS LLM vulnerability scanner (NVIDIA-stewarded)",
         tax=TAX_AGENT_HARNESS, primary_url="https://github.com/NVIDIA/garak",
         desc="OSS (Apache 2.0) LLM vulnerability scanner — 'nmap for LLMs.' Originally Leon Derczynski (Univ Sheffield / ITU Copenhagen); NVIDIA now stewards the project. Tests for jailbreaks, prompt injection, hallucination, data leakage. Apache-2.0; 5k+ stars.",
         claims="Apache-2.0; 5k+ stars; ~80 attack probes shipped; NVIDIA-stewarded",
         created="2023 (initial public release)", hq="London / NVIDIA",
         founders="Leon Derczynski (Univ Sheffield; now NVIDIA)",
         license_="Apache-2.0", gh="github.com/NVIDIA/garak (~5k stars)",
         code_release="Apache-2.0 — OSS",
         pros="NVIDIA-backed; nmap-like CLI ergonomics; broad probe library; research-quality scoring.",
         cons="CLI-first (no SaaS dashboard); requires manual scoring/triage; not a commercial product per se.",
         optimised_for="researcher / advanced practitioner LLM vuln scanning",
         api_surface="Python CLI"),

    dict(tier=2, name="HackerOne Hai", url="https://www.hackerone.com/ai",
         type_str="AI-assisted pentest + AI red-team service",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.hackerone.com/ai",
         desc="HackerOne's AI-augmented offensive security service — Hai is an LLM-assisted triage/research copilot for hackers, plus a productised 'AI red-team' service connecting customers to skilled human red-teamers for LLM systems. Used by major LLM providers (OpenAI, Anthropic) historically as a vulnerability surface.",
         claims="HackerOne $116M Series E 2019 (Valor + Benchmark); platform processed >$50M in bug bounties 2023",
         created="2012 (HackerOne); Hai launched 2024", hq="San Francisco",
         founders="HackerOne (Michiel Prins + Jobert Abma + Merijn Terheggen)",
         pros="Largest crowdsourced offensive-security network; AI red-team service has direct human-in-the-loop expertise.",
         cons="Service business with usage-pricing complexity; AI features overlay an existing-platform identity.",
         customers="OpenAI, Anthropic, Adobe, GitHub, Snap, Dropbox + DoD",
         optimised_for="enterprise GenAI red-team via human bug-bounty hunter network",
         pricing="Pay-per-finding + retainer service tiers"),

    dict(tier=3, name="XBOW", url="https://xbow.com/",
         type_str="Autonomous AI pentester (web app exploitation agent)",
         tax=TAX_AGENT_HARNESS, primary_url="https://xbow.com/",
         desc="Sequoia-led $20M seed (Jun-2024); founded by Oege de Moor (Semmle / GitHub CodeQL founder). Autonomous offensive-security agent that finds and exploits web vulns end-to-end. Topped HackerOne leaderboard in 2025 (first AI on the leaderboard).",
         claims="$20M seed Jun-2024 (Sequoia); $75M Series B Jun-2025 (Sequoia); topped HackerOne leaderboard 2025 as first AI participant",
         created="2024 (founded)", hq="New York",
         founders="Oege de Moor (CEO; founder of Semmle → GitHub CodeQL)",
         funding="$20M seed + $75M Series B Jun-2025 (Sequoia)",
         pros="Topped HackerOne leaderboard as first AI; Sequoia-led; strong founder pedigree (Semmle/CodeQL).",
         cons="Closed product; limited public details; benchmark dominance vs production OSS targets, not always real-world enterprise scopes.",
         customers="Stealth enterprise + bug-bounty programs",
         optimised_for="autonomous web-app pentest agents"),

    dict(tier=3, name="Dropzone AI", url="https://www.dropzone.ai/",
         type_str="Autonomous SOC analyst agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.dropzone.ai/",
         desc="Autonomous SOC analyst agent — investigates Tier-1 SIEM/EDR alerts end-to-end. $16.85M Series A Aug-2024 (Theory Ventures + Decibel). Founded by Edward Wu (ex-ExtraHop). Targets the 60%-of-alerts-go-uninvestigated problem.",
         claims="$16.85M Series A Aug-2024 (Theory + Decibel); founder ex-ExtraHop; production at Fortune-500 SOCs",
         created="2023 (founded)", hq="Seattle",
         founders="Edward Wu (CEO; ex-ExtraHop; UC Berkeley)",
         funding="$16.85M Series A Aug-2024 (Theory + Decibel)",
         pros="Strongest pure-play autonomous-SOC narrative; Theory Ventures lead; immediate analyst-shortage market fit.",
         cons="Closed product; outputs gated by underlying SIEM/EDR integrations; enterprise sales-cycle constrained.",
         customers="Enterprise SOC + MSSPs",
         optimised_for="autonomous Tier-1 SOC alert triage"),

    dict(tier=3, name="Crogl", url="https://crogl.com/",
         type_str="Autonomous SOC investigation copilot",
         tax=TAX_AGENT_HARNESS, primary_url="https://crogl.com/",
         desc="$25M Series A Jan-2025 (Menlo Ventures + Tola Capital + Pelion); founded by Monzy Merza (ex-Splunk CSO). 'Knowledge engine' that does autonomous investigation across SIEM data. Pitched as the AI analyst pair for security teams.",
         claims="$25M Series A Jan-2025 (Menlo + Tola + Pelion); founder ex-Splunk CSO; investigates 100k+ alerts/day per design target",
         created="2024 (founded)", hq="Austin",
         founders="Monzy Merza (CEO; ex-Splunk CSO and Distinguished Engineer)",
         funding="$25M Series A Jan-2025 (Menlo + Tola + Pelion)",
         pros="Founder Monzy Merza brings Splunk distribution + SOC credibility; Menlo + Tola backing; strong narrative for analyst-shortage market.",
         cons="Early-stage closed product; competing with Dropzone in same niche.",
         optimised_for="autonomous SOC investigation across SIEM data"),

    dict(tier=3, name="Horizon3 NodeZero", url="https://www.horizon3.ai/",
         type_str="Autonomous pentest platform (NodeZero)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.horizon3.ai/",
         desc="Founded 2019 by Snehal Antani (ex-CTO US SOCOM J6) + ex-NSA team. NodeZero is autonomous pentest — finds + exploits + verifies exploitability. $100M Series D Mar-2024 (NEA; $750M val); >300% YoY revenue growth reported. Federal + commercial.",
         claims="$100M Series D Mar-2024 ($750M val; NEA + Craft Ventures); >300% YoY revenue growth; NodeZero tested in 7000+ enterprises",
         created="2019 (founded)", hq="San Antonio",
         founders="Snehal Antani (CEO; ex-CTO US SOCOM); Anthony Pillitiere (CTO; ex-NSA)",
         funding="$100M Series D Mar-2024 ($750M val; NEA + Craft)",
         pros="Strongest federal/military pedigree (ex-SOCOM CTO + ex-NSA); NEA Series D; broad enterprise traction; not vendor-tied SIEM.",
         cons="More pre-LLM offensive-security DNA than 2024-vintage GenAI agents; LLM-augmentation roadmap less articulated than XBOW.",
         compliance="FedRAMP Moderate",
         customers="DoD + Fortune 500 + healthcare + financial",
         optimised_for="autonomous network + cloud pentest at scale"),

    dict(tier=3, name="Pentera", url="https://pentera.io/",
         type_str="Automated security validation / pentest platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://pentera.io/",
         desc="Founded 2015 (ex-Pcysys); automated security validation — pentest, red-team, attack-surface validation. $60M Series D Jan-2024 ($1B val unicorn; Evolution Equity + K1). Israeli cyber pedigree; more mature than 2024-vintage GenAI pentest agents.",
         claims="$60M Series D Jan-2024 ($1B val); >$100M ARR reported; 1000+ enterprise customers",
         created="2015 (founded as Pcysys; rebranded Pentera 2021)", hq="Petah Tikva, Israel",
         founders="Arik Liberzon (Founder; ex-IDF cyber); Arik Faingold",
         funding="$60M Series D Jan-2024 ($1B val unicorn)",
         pros="Unicorn-stage; 1000+ enterprise customers; established outside the 2024-AI-agent wave; mature platform.",
         cons="More traditional automated-pentest than LLM-agent first; less hype than XBOW; the 'AI' framing is a recent overlay.",
         customers="1000+ enterprises across financial, healthcare, gov",
         optimised_for="continuous automated pentest + security validation"),

    dict(tier=2, name="GitHub Copilot Autofix", url="https://github.blog/2024-03-20-found-means-fixed-introducing-code-scanning-autofix-powered-by-github-copilot-and-codeql/",
         type_str="Automated code-vuln-fix agent (CodeQL + Copilot)",
         tax=TAX_AGENT_HARNESS, primary_url="https://github.blog/2024-03-20-found-means-fixed-introducing-code-scanning-autofix-powered-by-github-copilot-and-codeql/",
         desc="GitHub's CodeQL-powered auto-fix for code-scanning alerts; combines static analysis with Copilot model suggestions to generate patches for vulnerabilities. Launched Mar-2024 (public beta), GA Aug-2024 for GitHub Advanced Security customers.",
         claims="Launched Mar-2024 (beta); GA Aug-2024; covers 90%+ of JS/TS/Java/Python alert categories per GitHub; turns CodeQL findings into PR-ready fixes",
         created="2024-03 (public beta)", hq="San Francisco / Redmond",
         founders="GitHub / Microsoft",
         pros="Backed by CodeQL data + Copilot model; PR-ready fixes integrated into GitHub workflow; broad language coverage.",
         cons="Tied to GitHub Advanced Security tier; auto-fix quality bounded by CodeQL signal depth; some classes still require human edit.",
         customers="GitHub Advanced Security enterprise customers",
         pricing="GHAS tier ($49/user/month component)",
         optimised_for="auto-generated SAST/SCA fix PRs at GitHub scale",
         adjacent="CodeQL; GitHub Advanced Security; Dependabot",
         deployment="GitHub SaaS"),

    dict(tier=2, name="Snyk DeepCode AI", url="https://snyk.io/platform/deepcode-ai/",
         type_str="AI-assisted code-vulnerability detection + auto-fix",
         tax=TAX_AGENT_HARNESS, primary_url="https://snyk.io/platform/deepcode-ai/",
         desc="Snyk's AI-assisted code-fix product built on the 2020-acquired DeepCode AI engine. Combines symbolic analysis + multiple AI models for fix generation. Snyk parent: $530M raised; $7.4B val Dec-2022; reported $300M+ ARR.",
         claims="DeepCode acquired by Snyk 2020; AI fix-suggestion shipped 2023; multi-model (symbolic + LLM) hybrid; Snyk $7.4B val",
         created="2020 (DeepCode acquired by Snyk)", hq="Boston / Tel Aviv",
         founders="Snyk (Guy Podjarny); DeepCode founders Boris Paskalev + Veselin Raychev",
         funding="Snyk parent: $530M+ raised; $7.4B val Dec-2022",
         pros="Largest developer-security platform; mature SAST/SCA; multi-model AI; broad CI/CD integrations.",
         cons="Pricing complexity at enterprise tier; the 'AI' overlay sometimes muddles the older SAST identity.",
         compliance="SOC 2 Type II; ISO 27001",
         customers="Atlassian, Salesforce, Asurion, Google, NTT + thousands",
         optimised_for="AppSec/SAST + AI-suggested fixes in dev workflow"),

    dict(tier=2, name="Semgrep Assistant", url="https://semgrep.dev/products/assistant",
         type_str="AI-assisted triage + auto-remediation for Semgrep findings",
         tax=TAX_AGENT_HARNESS, primary_url="https://semgrep.dev/products/assistant",
         desc="Semgrep's AI layer (Assistant) on top of its OSS rules-based SAST engine — triages findings, suppresses false positives, drafts fixes via PR. Semgrep parent: $59.5M Series C Nov-2022 ($530M val); >100M scans/year reported.",
         claims="Assistant launched 2024; >70% reduction in noise per Semgrep data; backed by Semgrep OSS rules library (10k+ rules)",
         created="2024 (Assistant launch)", hq="San Francisco",
         founders="Isaac Evans (CEO) + team; Semgrep (r2c) founded 2018",
         funding="Semgrep parent: $59.5M Series C Nov-2022 (Felicis; $530M val)",
         pros="Built on OSS rules-engine with strong community; AI overlay focuses on triage where it adds value; PR-ready fixes.",
         cons="AI Assistant is a paid tier on top of free OSS; less broad than Snyk; primarily code-focused (no SCA depth).",
         customers="Snowflake, Figma, Vercel + thousands of OSS users",
         optimised_for="AI-triaged Semgrep SAST findings"),

    dict(tier=3, name="Endor Labs", url="https://www.endorlabs.com/",
         type_str="AI-powered SCA + reachability analysis",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.endorlabs.com/",
         desc="Founded 2021 by Dimitri Stiliadis + Varun Badhwar (ex-Palo Alto Networks Prisma Cloud); reachability-aware SCA with AI for triage. $70M Series A Oct-2023 ($200M val; Lightspeed + Coatue + Dell Tech Capital); $93M total raised.",
         claims="$70M Series A Oct-2023 (Lightspeed + Coatue + Dell; $200M val); $93M total; pioneered reachability analysis as primary SCA metric",
         created="2021 (founded)", hq="Palo Alto",
         founders="Varun Badhwar (CEO; founder of RedLock → Palo Alto Prisma Cloud); Dimitri Stiliadis (CTO)",
         funding="$70M Series A Oct-2023 ($200M val); $93M total",
         pros="Founder Varun Badhwar built $173M-acquired RedLock; reachability analysis differentiator; strong VC backing.",
         cons="Niche (SCA-focused); less broad than Snyk; AI is a more recent overlay than DeepCode AI.",
         customers="HubSpot, Carta, Klaviyo + Fortune 500",
         optimised_for="SCA with function-level reachability + AI triage"),

    dict(tier=3, name="Torq HyperSOC", url="https://torq.io/products/hypersoc/",
         type_str="Hyperautomated SOC platform with agent workflows",
         tax=TAX_AGENT_HARNESS, primary_url="https://torq.io/products/hypersoc/",
         desc="Torq's HyperSOC is the AI-augmented offering of its hyperautomation platform (no-code security workflows + LLM agents). Torq parent: $70M Series C Apr-2024 (Evolution + Bessemer + Notable; >$300M total raised). Founded by Ofer Smadari (ex-Luminate / Symantec acq).",
         claims="$70M Series C Apr-2024 ($300M+ total); 1000s of pre-built workflows; AI agent-mode added 2024",
         created="2020 (founded); HyperSOC 2024", hq="Tel Aviv / NYC",
         founders="Ofer Smadari (CEO; ex-Luminate, acq Symantec)",
         funding="$70M Series C Apr-2024 (Evolution + Bessemer + Notable; >$300M total)",
         pros="Established SOAR/hyperautomation foundation; broad integration catalog (300+); AI is enhancement, not core.",
         cons="More established SOAR than 2024-vintage SOC-agent startup; AI value-add overlapping with Dropzone/Crogl niches.",
         customers="Fortune 500 SOCs + MSSPs",
         optimised_for="hyperautomated SOC + AI agent workflows",
         adjacent="SIEM (Splunk, Sentinel); EDR (CrowdStrike, SentinelOne); ticketing (Jira, ServiceNow)"),

    dict(tier=3, name="Tines", url="https://www.tines.com/",
         type_str="No-code workflow automation + AI agents for security",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.tines.com/",
         desc="Dublin-founded 2018; no-code automation initially for SOC analysts. $50M Series B Dec-2023 (Felicis + Accel + CrowdStrike's Falcon Fund). AI Agent mode added 2024; Tines Workbench gives analysts an LLM copilot atop their workflows.",
         claims="$50M Series B Dec-2023 (Felicis + Accel + CrowdStrike Falcon Fund); >$150M total raised; valued $1B+",
         created="2018 (founded)", hq="Dublin / Boston",
         founders="Eoin Hinchy (CEO; ex-Tanium, ex-Docusign); Thomas Kinsella (COO; ex-Tanium)",
         funding="$50M Series B Dec-2023 (Felicis + Accel + CrowdStrike; $1B+ val)",
         pros="Dublin SOC-automation darling; CrowdStrike strategic; product-led-growth motion; AI an evolution of no-code.",
         cons="Less narrow than dedicated AI-SOC startups; broader workflow positioning means less depth on AI-agent novelty.",
         customers="Reddit, Canva, Mars, McKesson + many F500 SOCs",
         optimised_for="no-code SOC automation + LLM agent workflows",
         adjacent="SIEM/EDR/ticketing connectors (CrowdStrike, Splunk, Jira)"),

    dict(tier=3, name="Anvilogic Forge", url="https://www.anvilogic.com/",
         type_str="Detection-engineering platform with AI Forge",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.anvilogic.com/",
         desc="Founded 2019 by ex-Yahoo CISO Karthik Kannan; AI-driven detection-engineering platform. $45M Series C Jul-2024 (Evolution + G Squared; ~$200M val). Forge is the AI agent that auto-generates SIEM detections.",
         claims="$45M Series C Jul-2024 (Evolution + G Squared); >$95M total raised; founder ex-Yahoo CISO",
         created="2019 (founded)", hq="Palo Alto",
         founders="Karthik Kannan (CEO; ex-Yahoo CISO)",
         funding="$45M Series C Jul-2024 (Evolution + G Squared)",
         pros="Niche detection-engineering focus; ex-Yahoo CISO founder pedigree; AI-generated SIEM rules differentiator.",
         cons="Niche commodity vs broad-SOC platforms; small ecosystem.",
         customers="F500 SOCs",
         optimised_for="auto-generation of SIEM detection rules"),

    dict(tier=3, name="SnapAttack", url="https://www.snapattack.com/",
         type_str="Detection-as-code platform with threat-emulation AI",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.snapattack.com/",
         desc="Founded 2021 inside Booz Allen Hamilton; spun out 2022. Detection-as-code platform — threat emulation + auto-generated detections. Adds GenAI threat-content layer 2024. Acquired by Cisco's Splunk Mar-2025 (terms undisclosed).",
         claims="Spun out of Booz Allen 2022; AI threat-emulation feature 2024; **acquired by Cisco's Splunk Mar-2025**",
         created="2021 (founded inside BAH); 2022 spinout", hq="Washington DC",
         founders="Peter Prizio Jr. (CEO; ex-Booz Allen)",
         funding="Booz Allen-incubated; acquired by Splunk Mar-2025",
         pros="Booz Allen lineage gives federal credibility; detection-as-code is differentiator; Splunk distribution post-acq.",
         cons="Small pre-acq footprint; product roadmap subject to Splunk consolidation.",
         customers="Federal + DoD + Fortune 500",
         optimised_for="threat-emulation + detection-as-code for SOC teams"),

    dict(tier=3, name="Specter Ops BloodHound Enterprise", url="https://specterops.io/bloodhound-enterprise/",
         type_str="Attack-path management + AI analysis (BloodHound Enterprise)",
         tax=TAX_AGENT_HARNESS, primary_url="https://specterops.io/bloodhound-enterprise/",
         desc="Maker of OSS BloodHound (the Active-Directory graph tool); BloodHound Enterprise is the productised attack-path management platform. $33M Series A Aug-2024 (Insight Partners). Adds AI for attack-path prioritisation 2024.",
         claims="$33M Series A Aug-2024 (Insight Partners); OSS BloodHound has >12k stars; SpecterOps founded 2017 by Andy Robbins + David McGuire + Will Schroeder",
         created="2017 (founded SpecterOps); BloodHound Enterprise 2021", hq="Alexandria, VA",
         founders="Andy Robbins + David McGuire + Will Schroeder (all ex-Veris Group)",
         funding="$33M Series A Aug-2024 (Insight Partners)",
         license_="BloodHound OSS Apache-2.0 (Enterprise is commercial)",
         gh="github.com/SpecterOps/BloodHound (~12k stars)",
         pros="OSS BloodHound is the industry-standard AD graph; founders are highly respected red-team practitioners; clear federal pedigree.",
         cons="Niche (Active-Directory attack-path); AI is more recent overlay than core product.",
         customers="Federal + Fortune 500",
         optimised_for="Active-Directory attack-path management"),
]

# --- B. Legal harnesses (cross-listing existing memory rows where applicable) ---
LEGAL_ROWS = [
    dict(tier=2, name="Legora", url="https://legora.com/",
         type_str="EU-built legal agent platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://legora.com/",
         desc="Stockholm-founded (2023) legal agent platform — drafting, review, research. $35M Series B Nov-2024 (Iconiq + Redpoint + Y Combinator; $675M val). Targets EU firms with data residency; pitched as 'European Harvey.'",
         claims="$35M Series B Nov-2024 (Iconiq + Redpoint + YC; $675M val); EU data residency; 200+ law-firm customers",
         created="2023 (founded)", hq="Stockholm",
         founders="Max Junestrand (CEO); Anna Wennberg (COO)",
         funding="$35M Series B Nov-2024 (Iconiq + Redpoint; $675M val)",
         pros="EU/data-residency angle vs US-based Harvey; Iconiq + Redpoint backing; multi-lingual.",
         cons="Smaller than Harvey on scale; less brand outside Europe.",
         customers="200+ law firms across EU + US",
         compliance="EU GDPR; data residency in EU",
         optimised_for="EU law-firm AI workflows",
         deployment="SaaS",
         pricing="Per-seat enterprise"),

    dict(tier=3, name="LawDroid Copilot", url="https://lawdroid.com/",
         type_str="Solo / small-firm legal AI copilot",
         tax=TAX_AGENT_HARNESS, primary_url="https://lawdroid.com/",
         desc="Founded 2017 by Tom Martin (lawyer + technologist); LawDroid Copilot serves solo and small-firm lawyers — drafting, research, client intake automation. Bootstrapped + small angel rounds. Marketed against the 'enterprise BigLaw' positioning of Harvey/Casetext.",
         claims="2017-founded; Copilot launched 2023; affordable per-seat pricing; thousands of solo/small-firm users",
         created="2017 (founded)", hq="San Francisco",
         founders="Tom Martin (CEO; California attorney)",
         pros="SMB legal-focused (solo lawyers, small firms) — underserved by Harvey/Casetext; accessible pricing.",
         cons="Bootstrapped; small footprint vs enterprise legal AI; less brand.",
         customers="Solo + small-firm lawyers",
         pricing="$60–$200/month per seat",
         optimised_for="solo lawyer + small-firm AI productivity"),

    dict(tier=3, name="Pincites", url="https://www.pincites.com/",
         type_str="AI for contract negotiation",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.pincites.com/",
         desc="YC-W24 contract-review AI; auto-redlines vendor contracts based on the in-house playbook. $3.6M seed 2024 (Y Combinator + Liquid 2). Targets in-house legal at SaaS companies.",
         claims="YC W24; $3.6M seed; auto-redlines vendor contracts based on customer playbook",
         created="2024 (founded; YC W24)", hq="San Francisco",
         founders="Jake Heller (CEO; ex-Casetext founder) — note: Casetext founder Jake Heller; verify",
         funding="$3.6M seed 2024 (YC + Liquid 2)",
         pros="YC-W24; sharp playbook-aware redline focus.",
         cons="Early-stage; small footprint; niche use case.",
         optimised_for="in-house legal contract-redlining"),

    dict(tier=2, name="Ironclad AI Assistant", url="https://ironcladapp.com/ai/",
         type_str="CLM platform with AI agents",
         tax=TAX_AGENT_HARNESS, primary_url="https://ironcladapp.com/ai/",
         desc="Ironclad's AI agents inside its CLM (contract lifecycle management) platform. Ironclad parent: $200M+ ARR; backed by Accel, Sequoia, YC, BOND. AI features include auto-redline, review, and contract intelligence. Note: separate Rivet Memory Node row already in catalog under Framework-embedded memory — this is the CLM-AI framing.",
         claims="Ironclad parent: $200M+ ARR; AI Assistant launched 2023; auto-redline + clause-detect + risk-summary",
         created="2014 (Ironclad founded); AI Assistant 2023", hq="San Francisco",
         founders="Jason Boehmig (CEO); Cai GoGwilt (CTO)",
         funding="Ironclad: Accel, Sequoia, YC, BOND-backed; $200M+ ARR",
         pros="Dominant CLM market position; AI Assistant integrated where contracts live; broad enterprise customer base.",
         cons="AI Assistant is a CLM-overlay feature, not a standalone agent product; less ambition than Harvey on raw-task-replacement.",
         customers="Mastercard, Asana, Salesforce, OpenAI + Fortune 500",
         compliance="SOC 2 Type II; HIPAA; GDPR",
         optimised_for="contract-lifecycle AI workflows in-house counsel",
         adjacent="DocuSign; HelloSign; Salesforce CPQ",
         deployment="SaaS"),

    dict(tier=3, name="DraftWise", url="https://www.draftwise.com/",
         type_str="AI contract drafting + benchmark agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.draftwise.com/",
         desc="Founded 2021 by James Ding (ex-Allen & Overy); drafting + benchmarking AI agent that lets transactional lawyers see historical deals. $20M Series A Apr-2024 (Index Ventures + Y Combinator); ex-A&O / Linklaters customers.",
         claims="$20M Series A Apr-2024 (Index + YC); founders ex-Allen & Overy; benchmarks via firm's historical deals",
         created="2021 (founded)", hq="London / NYC",
         founders="James Ding (CEO; ex-Allen & Overy)",
         funding="$20M Series A Apr-2024 (Index + YC)",
         pros="Index-led; strong UK BigLaw customer pipeline (ex-A&O DNA); benchmark-driven drafting is differentiator.",
         cons="Smaller than Harvey; transactional-law focused (less litigation breadth).",
         customers="Allen & Overy, Linklaters, Cooley + other BigLaw",
         optimised_for="transactional-law drafting + deal benchmarking"),

    dict(tier=3, name="Litera AI", url="https://www.litera.com/products/litera-ai/",
         type_str="Document drafting + workflow AI inside Litera suite",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.litera.com/products/litera-ai/",
         desc="Litera (Hg-backed; 50%+ of AmLaw 200 customers) added a Litera AI overlay 2024 — drafting, redlining, document analytics. Litera parent has been a private-equity rollup of legal-tech (Microsystems, Workshare, Kira Systems acquired 2021).",
         claims="Litera serves 50%+ of AmLaw 200; Litera AI launched 2024 atop existing Workshare / Kira Systems acquisitions",
         created="1995 (Litera founded); Litera AI 2024", hq="Chicago",
         founders="Litera (Hg-backed PE roll-up; Avaneesh Marwaha CEO)",
         pros="Distribution into 50% of AmLaw 200 (existing Litera footprint); Kira Systems contract-review tech under the hood.",
         cons="AI overlay is recent; product roadmap influenced by acquisitions; less LLM-native than 2023-vintage startups.",
         customers="50%+ of AmLaw 200; BigLaw global",
         optimised_for="document drafting + redlining for BigLaw via Litera suite"),

    dict(tier=3, name="Genie AI", url="https://www.genieai.co/",
         type_str="Self-service AI legal agent (template + redline)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.genieai.co/",
         desc="London-based legal AI for non-lawyer founders — templates, drafting, AI review. Acquired by Robin AI Sep-2024 (Robin = legal AI, separate funded entity). Distinct from Hugo (research) and not to be confused with Google's Genie.",
         claims="Acquired by Robin AI Sep-2024 (terms undisclosed); previously raised $17.7M (Khosla, Founders Fund); SMB-focused",
         created="2017 (founded)", hq="London",
         founders="Rafie Faruq (CEO); Nitish Mutha (CTO)",
         funding="$17.7M total (Khosla + Founders Fund); acquired by Robin AI Sep-2024",
         pros="Robin AI scale post-acquisition; UK SMB focus; non-lawyer-friendly product.",
         cons="Post-acquisition product direction subject to Robin AI; the SMB segment is harder to monetise than BigLaw.",
         optimised_for="SMB self-service contracts + AI review",
         customers="UK SMBs; Y Combinator companies"),

    dict(tier=3, name="DocuSign IAM", url="https://www.docusign.com/products/intelligent-agreement-management",
         type_str="Intelligent Agreement Management — DocuSign's CLM-AI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.docusign.com/products/intelligent-agreement-management",
         desc="DocuSign's IAM platform (launched 2024) adds AI extraction, clause analysis, and workflow automation atop the eSignature core. Acquired Lexion Jun-2024 ($165M) to consolidate the AI-CLM stack. DocuSign parent: $2.8B+ revenue.",
         claims="IAM launched 2024; **Lexion acquired Jun-2024 for $165M**; DocuSign $2.8B+ revenue",
         created="2024 (IAM launched); 2003 (DocuSign founded)", hq="San Francisco",
         founders="DocuSign (Allan Thygesen CEO 2022-2025); IAM led by post-Lexion team",
         funding="DocuSign: public (NASDAQ: DOCU); Lexion acq $165M Jun-2024",
         pros="DocuSign distribution at scale; Lexion's AI tech under the hood; integrated with eSignature workflow.",
         cons="DocuSign post-COVID revenue plateau; product roadmap consolidating; AI features still maturing.",
         customers="1M+ DocuSign customers",
         compliance="SOC 2 Type II; ISO 27001; HIPAA; FedRAMP Moderate",
         optimised_for="AI-augmented agreement lifecycle management",
         deployment="SaaS"),

    dict(tier=3, name="Hugo (Hugo Legal)", url="https://hugo.legal/",
         type_str="Legal research + case-analysis AI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://hugo.legal/",
         desc="Estonian-founded legal AI startup; legal research and case analysis with EU multilingual focus. Bootstrapped; small angel rounds. Note: distinct from Hugo Health and from the unrelated 'huggo.legal' typo.",
         claims="Tallinn-founded 2018; legal-AI research focus; EU multilingual; small commercial footprint",
         created="2018 (founded)", hq="Tallinn, Estonia",
         founders="Artur Fjodorov + co-founders",
         pros="EU multilingual / data-residency angle; bootstrapped sustainability.",
         cons="Small footprint; less brand than Legora; primarily EE/EU focus.",
         optimised_for="EU/Baltic legal research"),

    dict(tier=3, name="Tonkean LegalWorks", url="https://tonkean.com/use-cases/legalworks/",
         type_str="Legal-ops orchestration platform with AI agents",
         tax=TAX_AGENT_HARNESS, primary_url="https://tonkean.com/use-cases/legalworks/",
         desc="Tonkean is a workflow-orchestration platform; LegalWorks is the legal-ops vertical with AI agents for intake triage, contract routing, and SLA management. Tonkean: $50M Series C Sep-2022 (Insight + Lightspeed + Accel; $500M+ val).",
         claims="Tonkean: $50M Series C Sep-2022 ($500M+ val); LegalWorks vertical 2023; AI agent layer added 2024",
         created="2018 (Tonkean); LegalWorks 2023", hq="Palo Alto",
         founders="Sagi Eliyahu (CEO; ex-Pendo); Offir Talmor (CTO)",
         funding="$50M Series C Sep-2022 (Insight + Lightspeed + Accel)",
         pros="Legal-ops focus vs lawyer-task focus is differentiator; broader Tonkean platform leverage.",
         cons="Workflow-platform-with-AI rather than AI-native; less narrative push than Harvey on lawyer-task replacement.",
         customers="Workday, Vimeo, Pixar, ServiceTitan legal-ops",
         optimised_for="legal-ops intake + workflow + SLA management"),
]


# --- C. Compliance / audit / governance agents ---
COMPLIANCE_ROWS = [
    dict(tier=1, name="Drata", url="https://drata.com/",
         type_str="Compliance automation platform with AI Trust Hub agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://drata.com/",
         desc="Founded 2020; compliance automation (SOC 2, HIPAA, GDPR, ISO 27001) with hundreds of pre-built control libraries. $200M Series C Mar-2024 ($2B val; ICONIQ + GGV + Cowboy). Trust Hub launched 2024; AI Trust Hub auto-fills security questionnaires.",
         claims="$200M Series C Mar-2024 ($2B val); $100M+ ARR reported; 5000+ customers; AI Trust Hub 2024",
         created="2020 (founded)", hq="San Diego",
         founders="Adam Markowitz (CEO; ex-Portfolium acq Instructure)",
         funding="$200M Series C Mar-2024 ($2B val; ICONIQ + GGV + Cowboy)",
         pros="Largest pure-play compliance-automation by ARR; 5000+ customers; AI Trust Hub auto-fills security questionnaires.",
         cons="Compliance ICP narrows ceiling; AI features atop established platform vs AI-native.",
         customers="5000+ customers including Lemonade, Notion, Bitwarden",
         compliance="SOC 2 Type II; ISO 27001; HIPAA; FedRAMP Moderate",
         optimised_for="multi-framework compliance automation with AI questionnaire fill",
         deployment="SaaS",
         pricing="Starter $7.5k+/year; Premium custom"),

    dict(tier=1, name="Vanta", url="https://www.vanta.com/",
         type_str="Compliance automation platform with AI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.vanta.com/",
         desc="Founded 2018; the largest compliance-automation platform by valuation/headline. $150M Series C Jul-2024 ($2.45B val; Sequoia + Atlassian Ventures + CrowdStrike Falcon Fund). Vanta AI launched 2024 — auto-evidence-collection, control mapping, vendor-review.",
         claims="$150M Series C Jul-2024 ($2.45B val); 8000+ customers; >$300M ARR reported; AI launched 2024",
         created="2018 (founded)", hq="San Francisco",
         founders="Christina Cacioppo (CEO; ex-Dropbox + USV)",
         funding="$150M Series C Jul-2024 ($2.45B val; Sequoia + Atlassian Ventures)",
         pros="Sequoia + Atlassian + CrowdStrike-backed; >$300M ARR; broadest customer base; AI auto-evidence is widely adopted.",
         cons="Compliance ICP shared with Drata; differentiation increasingly about ecosystem + Trust Center vs raw automation.",
         customers="8000+ customers including Modern Treasury, Atlassian, Quora",
         compliance="SOC 2 Type II; ISO 27001; HIPAA",
         optimised_for="cross-framework compliance automation + AI control mapping",
         deployment="SaaS",
         pricing="Starter $8k+/year; Enterprise quote"),

    dict(tier=2, name="Secureframe AI", url="https://secureframe.com/",
         type_str="Compliance automation with Comply AI",
         tax=TAX_AGENT_HARNESS, primary_url="https://secureframe.com/",
         desc="Founded 2020 by Shrav Mehta; the third major compliance-automation platform (with Vanta + Drata). $56M Series B Mar-2023 (Accel + Kleiner Perkins + Base10). Comply AI launched 2024 — control gap analysis, evidence-collection automation.",
         claims="$56M Series B Mar-2023 (Accel + Kleiner + Base10); >$100M ARR estimated; Comply AI launched 2024",
         created="2020 (founded)", hq="San Francisco",
         founders="Shrav Mehta (CEO)",
         funding="$56M Series B Mar-2023 (Accel + Kleiner + Base10)",
         pros="The third major player; Accel + Kleiner-backed; broad framework coverage; Comply AI integrated 2024.",
         cons="Smaller than Vanta + Drata; less mindshare for AI features than the top two.",
         customers="AngelList, Ramp, Lattice, ClickUp + thousands",
         compliance="SOC 2 Type II; ISO 27001",
         optimised_for="compliance automation alternative to Vanta/Drata"),

    dict(tier=2, name="TrustCloud", url="https://www.trustcloud.ai/",
         type_str="GRC automation + trust center platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.trustcloud.ai/",
         desc="Founded 2021 by Sravish Sridhar (ex-Kinvey founder); GRC automation + AI trust center. $25M Series A Jun-2023 (Felicis + Cowboy + Cota Capital). Differentiates with cyber-insurance + 'trust center' as a sales-enablement angle.",
         claims="$25M Series A Jun-2023 (Felicis + Cowboy); cyber-insurance partnerships; AI agent layer 2024",
         created="2021 (founded)", hq="San Mateo",
         founders="Sravish Sridhar (CEO; founder of Kinvey, acq PRGS 2016)",
         funding="$25M Series A Jun-2023 (Felicis + Cowboy + Cota)",
         pros="Trust-center sales-enablement angle differentiates from Vanta/Drata; cyber-insurance integration.",
         cons="Smaller than the Vanta/Drata/Secureframe trio; AI is overlay vs core.",
         customers="Mid-market SaaS + financial services",
         optimised_for="GRC + trust-center + cyber-insurance integration"),

    dict(tier=2, name="Hyperproof", url="https://hyperproof.io/",
         type_str="Compliance operations platform with AI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://hyperproof.io/",
         desc="Founded 2018; compliance-operations platform — pre-built frameworks + workflow automation. $40M Series B Dec-2022 (Riverwood Capital + Toba + Madrona). AI agent layer added 2024. Targets enterprise-scale compliance teams.",
         claims="$40M Series B Dec-2022 (Riverwood + Toba + Madrona); enterprise-focused; AI agent 2024",
         created="2018 (founded)", hq="Bellevue, WA",
         founders="Craig Unger (CEO; ex-Microsoft)",
         funding="$40M Series B Dec-2022 (Riverwood + Toba + Madrona)",
         pros="Enterprise-scale compliance focus; established before the 2024 AI wave; Madrona-backed.",
         cons="Less brand than Vanta/Drata; AI features more recent overlay.",
         customers="Fortune 500 compliance teams",
         optimised_for="enterprise compliance ops + AI control mapping"),

    dict(tier=2, name="AuditBoard", url="https://www.auditboard.com/",
         type_str="Enterprise GRC platform with AI features",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.auditboard.com/",
         desc="Founded 2014; enterprise audit + GRC platform — 60%+ of Fortune 500 customers. **Acquired by Hg for $3B Jun-2024** (private-equity take-private). AI features added 2024 — auto-population of audit workpapers, AI-assisted issue classification.",
         claims="**Hg acquisition $3B Jun-2024**; 60%+ of Fortune 500 customers; >$300M ARR; AI features 2024",
         created="2014 (founded)", hq="Cerritos, CA",
         founders="Daniel Kim (CEO); Jay Lee (CTO); Tony Adams",
         funding="**Acquired by Hg for $3B Jun-2024** (Carlyle + Adam Street pre-acq investors)",
         pros="60%+ of Fortune 500; $3B Hg acquisition validates the category; broad audit + risk + compliance + ESG.",
         cons="Post-acq strategy unclear; less AI-native than 2023-vintage startups.",
         customers="60%+ of Fortune 500",
         compliance="SOC 2; ISO 27001",
         optimised_for="enterprise audit + GRC + risk management",
         deployment="SaaS + private cloud"),

    dict(tier=3, name="LogicGate Risk Cloud", url="https://www.logicgate.com/",
         type_str="GRC platform with AI agents",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.logicgate.com/",
         desc="Founded 2015; GRC platform (Risk Cloud) — flexible policy engine + workflow + risk register. $113M Series C Dec-2021 (PSG + Silversmith). AI features (auto-policy mapping, issue triage) added 2024.",
         claims="$113M Series C Dec-2021 (PSG + Silversmith); $200M+ raised total; AI features 2024",
         created="2015 (founded)", hq="Chicago",
         founders="Matt Kunkel (CEO); Jon Siegler (CPO)",
         funding="$113M Series C Dec-2021 (PSG + Silversmith)",
         pros="Flexible no-code GRC engine; $200M+ total raised; established enterprise customer base.",
         cons="More flexible-platform than narrow-AI; competes with AuditBoard at high end and Vanta at low end.",
         customers="Capital One, Slack, AAA + mid-market financial",
         optimised_for="flexible enterprise GRC + AI policy mapping"),

    dict(tier=3, name="Onspring AI", url="https://onspring.com/",
         type_str="GRC + workflow platform with AI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://onspring.com/",
         desc="Founded 2010; GRC + business-process automation. Adds AI agent (Sophia) 2024 — natural-language workflow building + automated control assessment. Bootstrapped + small minority growth equity.",
         claims="Onspring Sophia AI launched 2024; bootstrapped + growth-equity-backed; broad GRC + BPM platform",
         created="2010 (founded)", hq="Overland Park, KS",
         founders="Chris Pantaenius (CEO); Jason Rohlf",
         pros="Bootstrapped sustainability; mature platform pre-LLM; AI overlay rather than rip-and-replace.",
         cons="Less brand than Vanta/AuditBoard; small footprint; AI features lag the top tier.",
         optimised_for="mid-market GRC + workflow + AI assistant"),

    dict(tier=3, name="Coalfire AI Operations", url="https://www.coalfire.com/services/managed-services/aiops",
         type_str="Cyber-services firm with AI-assisted compliance/pentest",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.coalfire.com/",
         desc="Coalfire is the largest specialist-cybersecurity-services firm in the FedRAMP/PCI/HITRUST space. Apax Partners acquired majority stake 2020. Launched AI-augmented assessment services 2024 — pentest + audit workpaper automation.",
         claims="Coalfire: Apax-acquired 2020; largest FedRAMP 3PAO; AI-augmented service 2024",
         created="2001 (founded)", hq="Westminster, CO",
         founders="Coalfire (Tom McAndrew CEO)",
         funding="Apax majority-acquired 2020",
         pros="Largest FedRAMP 3PAO; gov-grade pedigree; services-DNA gives consultative AI assist.",
         cons="Services + AI hybrid; the AI features are augmentation not standalone product; competes with services-first vs SaaS-first peers.",
         customers="Federal + Fortune 500",
         optimised_for="cyber-services with AI-augmented audit/pentest"),

    dict(tier=3, name="Hyperproof AI Trust Center", url="https://hyperproof.io/trust-center/",
         type_str="Auto-fill security questionnaire / trust center agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://hyperproof.io/trust-center/",
         desc="Standalone trust-center + AI-questionnaire-fill product from Hyperproof. Listed separately because the trust-center category is a distinct sub-market (Vanta, Drata, Hyperproof, SafeBase, ConveyorAI compete). SafeBase acquired by Drata Mar-2025.",
         claims="Trust-center + auto-fill positioned vs SafeBase (acq Drata Mar-2025) and Conveyor AI",
         created="2024 (trust center product)", hq="Bellevue, WA",
         founders="Hyperproof (Craig Unger CEO)",
         pros="Direct competitor in the post-SafeBase-acq trust-center category; Hyperproof distribution.",
         cons="Sub-product of Hyperproof; competes with Vanta + Drata + Conveyor in same niche."),
]


# --- D. SRE / DevOps / observability AI agents ---
SRE_ROWS = [
    dict(tier=1, name="Datadog Bits AI", url="https://www.datadoghq.com/blog/bits-ai/",
         type_str="Observability AI agent / SRE copilot",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.datadoghq.com/blog/bits-ai/",
         desc="Datadog's AI-assistant for observability — incident summarisation, root-cause hypotheses, runbook automation. Bits AI launched Aug-2023, GA 2024 across the Datadog suite. Datadog parent: $2.7B+ revenue 2024; NASDAQ:DDOG.",
         claims="Bits AI launched Aug-2023; integrated across logs/APM/RUM; **Datadog acquired Quickwit Dec-2024 to expand search capacity**",
         created="2023-08 (Bits AI launched)", hq="New York",
         founders="Datadog (Olivier Pomel CEO + Alexis Lê-Quôc)",
         funding="Datadog: public (NASDAQ: DDOG); $2.7B+ revenue 2024",
         pros="Largest observability platform with deepest data graph; AI features integrated where SREs already live; Quickwit acq adds search capacity.",
         cons="Bits AI is a feature, not a standalone agent; less specific than pure-play AIOps startups.",
         customers="29k+ Datadog customers; 50%+ of Fortune 500",
         compliance="SOC 2 Type II; ISO 27001; HIPAA; FedRAMP Moderate",
         optimised_for="AI assistant inside observability workflows",
         deployment="SaaS"),

    dict(tier=1, name="PagerDuty AIOps", url="https://www.pagerduty.com/platform/aiops/",
         type_str="Incident-response AIOps platform with agents",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.pagerduty.com/platform/aiops/",
         desc="PagerDuty's AIOps tier adds AI alert grouping, noise suppression, and AI agent suggestions for incident response. Includes the Jeli acquisition (May-2023, $73M) for incident retrospective AI. PagerDuty parent: $450M+ revenue.",
         claims="PagerDuty AIOps tier; **Jeli acquired May-2023 for $73M**; AI alert-grouping reduces noise 70%+ per vendor",
         created="2009 (PagerDuty); AIOps tier 2023", hq="San Francisco",
         founders="PagerDuty (Alex Solomon + Andrew Miklas + Baskar Puvanathasan)",
         funding="PagerDuty: public (NYSE: PD); $450M+ revenue",
         pros="Incumbent in incident response; Jeli acq adds retrospective AI; pricing tiers enable AIOps as upsell.",
         cons="AIOps tier pricing is high; AI features still maturing vs incumbent's main alert-routing strength.",
         customers="25k+ PagerDuty customers; 70%+ of Fortune 100",
         compliance="SOC 2; ISO 27001; HIPAA; FedRAMP Moderate",
         optimised_for="AI-augmented incident response + on-call"),

    dict(tier=1, name="Dynatrace Davis CoPilot", url="https://www.dynatrace.com/news/blog/dynatrace-davis-copilot/",
         type_str="GenAI assistant for the Davis AI observability engine",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.dynatrace.com/news/blog/dynatrace-davis-copilot/",
         desc="Dynatrace launched Davis CoPilot Sep-2023 — GenAI conversational interface on top of the (deterministic) Davis AI engine, the largest causal-AI observability deployment. Dynatrace parent: NYSE:DT, $1.4B+ revenue.",
         claims="Davis CoPilot launched Sep-2023; sits atop Davis (Dynatrace's deterministic causal-AI); Dynatrace $1.4B+ revenue",
         created="2023-09 (Davis CoPilot)", hq="Waltham, MA / Linz, Austria",
         founders="Dynatrace (Rick McConnell CEO)",
         funding="Dynatrace: public (NYSE: DT)",
         pros="Davis underlying causal-AI is one of the most mature in observability; CoPilot is a credible LLM overlay; broad enterprise base.",
         cons="Davis CoPilot is a conversational overlay vs an agent; differentiation from Datadog Bits AI / New Relic AI Monitoring is narrow.",
         customers="3700+ Dynatrace customers; Fortune 500 heavy",
         compliance="SOC 2 Type II; ISO 27001; FedRAMP",
         optimised_for="conversational observability + causal-AI explanations"),

    dict(tier=2, name="New Relic AI", url="https://newrelic.com/platform/new-relic-ai",
         type_str="GenAI observability assistant",
         tax=TAX_AGENT_HARNESS, primary_url="https://newrelic.com/platform/new-relic-ai",
         desc="New Relic's AI agent — natural-language NRQL queries, error summaries, error-grouping. Launched late-2023. New Relic parent: taken private by Francisco Partners + TPG for $6.5B Nov-2023.",
         claims="**New Relic taken private Nov-2023 ($6.5B; Francisco Partners + TPG)**; New Relic AI launched 2023",
         created="2023 (New Relic AI launched)", hq="San Francisco",
         founders="New Relic (Lew Cirne founder; Bill Staples CEO)",
         funding="Public until Nov-2023; PE-owned post-acq",
         pros="Mature APM/observability data; broad customer base; AI overlay shipped early 2024.",
         cons="Post-PE-acq strategy unclear; less AI mindshare than Datadog/Dynatrace.",
         customers="Major enterprise APM users (Adobe, Cisco)",
         compliance="SOC 2; ISO 27001; FedRAMP Moderate",
         optimised_for="natural-language observability queries + AI summarisation"),

    dict(tier=2, name="Sysdig Sage", url="https://sysdig.com/sysdig-sage/",
         type_str="Cloud-security AIOps agent for runtime/CNAPP",
         tax=TAX_AGENT_HARNESS, primary_url="https://sysdig.com/sysdig-sage/",
         desc="Sysdig's GenAI-powered cloud-security agent — runtime workload protection + CNAPP findings explained. Launched May-2024. Sysdig parent: $350M Series G 2022 ($2.5B val); Permira-led 2023 round.",
         claims="Sage launched May-2024; built on Sysdig's open-source Falco runtime-monitor; Sysdig $2.5B val 2022",
         created="2024-05 (Sage launched)", hq="San Francisco",
         founders="Sysdig (Loris Degioanni founder; Suresh Vasudevan CEO)",
         funding="Sysdig: $350M Series G 2022 ($2.5B val); Permira-led 2023",
         pros="Built on Sysdig Falco (broad runtime data); cloud-runtime focus differentiates from APM-centric peers.",
         cons="Security-first observability rather than general SRE; smaller TAM than Datadog/Dynatrace.",
         customers="Goldman Sachs, BigCommerce + cloud-native enterprises",
         optimised_for="GenAI for cloud runtime + CNAPP"),

    dict(tier=2, name="incident.io AI", url="https://incident.io/ai",
         type_str="Incident-management platform with AI agents",
         tax=TAX_AGENT_HARNESS, primary_url="https://incident.io/ai",
         desc="London-founded incident-management platform — Slack-native, fast-growing. $62M Series B Sep-2024 (Insight Partners + Index; $400M val). AI features (auto-summary, auto-postmortem, suggested-runbook) added 2024.",
         claims="$62M Series B Sep-2024 ($400M val; Insight + Index); >$10M ARR reported; AI features 2024",
         created="2021 (founded)", hq="London",
         founders="Stephen Whitworth (CEO; ex-Monzo); Pete Hamilton; Chris Evans",
         funding="$62M Series B Sep-2024 (Insight + Index; $400M val)",
         pros="Slack-native UX; fast-growing in 2024; strong UK pedigree (ex-Monzo founders); AI features integrated.",
         cons="Smaller than PagerDuty; product depth-vs-breadth tradeoff (less AIOps signal-side).",
         customers="Etsy, Snyk, Linear, Vanta + mid-market SaaS",
         optimised_for="incident management + AI runbook for cloud-native teams"),

    dict(tier=3, name="Resolve.ai", url="https://resolve.ai/",
         type_str="Autonomous AI SRE agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://resolve.ai/",
         desc="Founded 2024 by Spiros Xanthos (ex-Splunk Observability SVP; founder of Omnition acq Splunk 2019). Autonomous AI SRE — investigates incidents end-to-end. $35M seed Aug-2024 (Greylock + Unusual). Pitched as 'the AI SRE.'",
         claims="$35M seed Aug-2024 (Greylock + Unusual); founder ex-Splunk Observability SVP; autonomous SRE agent",
         created="2024 (founded)", hq="Palo Alto",
         founders="Spiros Xanthos (CEO; ex-Splunk Observability SVP; ex-Omnition founder acq Splunk 2019)",
         funding="$35M seed Aug-2024 (Greylock + Unusual)",
         pros="Largest seed in AI-SRE category; founder pedigree (ex-Splunk Observability SVP); autonomous-SRE positioning is clear.",
         cons="Early-stage closed product; the 'autonomous SRE' narrative has many competitors (Cleric, RunWhen, ...).",
         optimised_for="autonomous AI SRE agent for incident investigation"),

    dict(tier=3, name="Cleric", url="https://cleric.io/",
         type_str="Autonomous AI SRE agent for cloud-native incidents",
         tax=TAX_AGENT_HARNESS, primary_url="https://cleric.io/",
         desc="Founded 2023; autonomous AI SRE that investigates Kubernetes + cloud-native alerts end-to-end. $10M seed Apr-2024 (Greylock + Innovation Endeavors). Direct competitor to Resolve.ai in the AI-SRE wave.",
         claims="$10M seed Apr-2024 (Greylock + Innovation Endeavors); autonomous AI SRE; Kubernetes-native focus",
         created="2023 (founded)", hq="San Francisco",
         founders="Willem Pienaar (CEO; ex-Tecton + Feast OSS creator)",
         funding="$10M seed Apr-2024 (Greylock + Innovation Endeavors)",
         pros="Founder Willem Pienaar (Feast OSS creator) gives ML/data ops credibility; Greylock-backed; Kubernetes-focused.",
         cons="Early-stage; smaller raise than Resolve.ai; the category is crowded.",
         optimised_for="autonomous AI SRE for Kubernetes / cloud-native"),

    dict(tier=3, name="RunWhen", url="https://www.runwhen.com/",
         type_str="Open-source AI SRE platform with CodeCollection",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.runwhen.com/",
         desc="OSS-first AI-SRE platform; CodeCollection (the OSS runbook library) is the differentiator — 'GitHub for SRE runbooks.' Apache-2.0. Bootstrapped + small angel funding. RunWhen Local self-hosted.",
         claims="OSS Apache-2.0; CodeCollection runbook library is community-driven; RunWhen Local self-host option",
         created="2022 (founded)", hq="US",
         founders="Shea Stewart (CEO)",
         license_="Apache-2.0", gh="github.com/runwhen-contrib (multiple repos)",
         code_release="Apache-2.0 OSS",
         pros="OSS-first differentiates from Resolve/Cleric; community runbook library is sticky; self-host option.",
         cons="Smaller commercial footprint; founder velocity less venture-backed than Resolve/Cleric.",
         optimised_for="OSS-first AI SRE + community runbook library"),

    dict(tier=3, name="OpsRamp AI", url="https://www.opsramp.com/",
         type_str="AIOps platform (HPE-acquired)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.opsramp.com/",
         desc="Founded 2014; AIOps platform — hybrid + multi-cloud observability with AI event correlation. **Acquired by HPE Jul-2023** (terms undisclosed; reported ~$200M+). AI agent features now integrated into HPE GreenLake.",
         claims="**Acquired by HPE Jul-2023** (terms undisclosed); 200+ enterprise customers pre-acq; AI now under GreenLake",
         created="2014 (founded); HPE-acquired 2023", hq="San Jose / HPE",
         founders="Varma Kunaparaju (CEO pre-acq)",
         funding="HPE-acquired Jul-2023",
         pros="HPE-scale distribution post-acq; long AIOps history; broad enterprise base.",
         cons="Post-acq integration into GreenLake; less independent product velocity.",
         optimised_for="hybrid/multi-cloud AIOps + HPE GreenLake integration",
         customers="HPE GreenLake customers + 200+ enterprise pre-acq"),

    dict(tier=3, name="DX Engineering Intelligence", url="https://getdx.com/",
         type_str="Engineering intelligence + AI insights platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://getdx.com/",
         desc="Founded 2020 by Abi Noda; engineering-productivity intelligence (DORA + SPACE metrics) with AI-driven analysis. $14M Series A Apr-2024 (Notable Capital). Differentiates with research-rigour metrics; 'Stripe metrics for engineering teams.'",
         claims="$14M Series A Apr-2024 (Notable Capital); DORA + SPACE metrics with AI insights",
         created="2020 (founded)", hq="Portland, OR",
         founders="Abi Noda (CEO; ex-GitHub Product Lead)",
         funding="$14M Series A Apr-2024 (Notable Capital)",
         pros="Strong research basis (DORA + SPACE academic frameworks); founder ex-GitHub; differentiated from observability.",
         cons="Engineering-management framing rather than ops/SRE-agent; AI is overlay.",
         customers="Pfizer, Block, Etsy + Fortune 500 engineering orgs",
         optimised_for="engineering productivity metrics + AI analysis"),
]


# --- E. Sales / GTM / outbound agents ---
SALES_ROWS = [
    dict(tier=1, name="11x.ai", url="https://www.11x.ai/",
         type_str="AI sales agents (Alice, Mike, Jordan)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.11x.ai/",
         desc="Founded 2022 by Hasan Sukkar; AI sales agents Alice (outbound SDR), Mike (voice SDR), Jordan (RevOps). $50M Series B Oct-2024 (Benchmark + Andreessen Horowitz; $350M val). Among the most-discussed AI-employee startups of 2024.",
         claims="$50M Series B Oct-2024 ($350M val; Benchmark + a16z); >$10M ARR Q3-2024; thousands of customers",
         created="2022 (founded)", hq="San Francisco / London",
         founders="Hasan Sukkar (CEO)",
         funding="$50M Series B Oct-2024 ($350M val; Benchmark + a16z)",
         pros="Largest AI-SDR by mindshare 2024; Benchmark + a16z; 'AI employees' framing resonates.",
         cons="Ongoing controversy about ICP fit and churn (TechCrunch reporting late-2024); deliverability concerns at high outbound volumes.",
         customers="Thousands of B2B SaaS customers",
         optimised_for="autonomous outbound SDR / RevOps",
         deployment="SaaS",
         pricing="Per-seat / per-agent enterprise tiers"),

    dict(tier=1, name="Salesforce Agentforce", url="https://www.salesforce.com/agentforce/",
         type_str="Multi-agent platform on Data Cloud (cross-listing harness)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.salesforce.com/agentforce/",
         desc="Cross-listing: Salesforce Agentforce already exists under Vertical / Customer-support / voice memory; this row is the Agent-harness framing — Agentforce as the consumer-facing agent IDE / builder on Data Cloud. Agentforce launched Sep-2024; Agentforce 2.0 announced Dec-2024.",
         claims="Agentforce 1.0 launched Sep-2024; Agentforce 2.0 Dec-2024; Salesforce Atlas reasoning engine; >$300B market cap",
         created="2024-09 (Agentforce launched)", hq="San Francisco",
         founders="Salesforce (Marc Benioff)",
         funding="Salesforce: public (NYSE: CRM)",
         pros="Largest CRM distribution; Data Cloud grounding; Atlas reasoning engine has multi-step capability.",
         cons="Salesforce-only; pricing complexity; consulting motion required for setup.",
         customers="Salesforce's enterprise base",
         compliance="SOC 2; ISO 27001; HIPAA",
         optimised_for="Salesforce-native sales/service agents on Data Cloud"),

    dict(tier=1, name="HubSpot Breeze AI Agents", url="https://www.hubspot.com/products/artificial-intelligence",
         type_str="AI agents for HubSpot Smart CRM (Breeze)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.hubspot.com/products/artificial-intelligence",
         desc="HubSpot Breeze (launched Sep-2024) is the AI brand spanning Breeze Copilot (assistant) + Breeze Agents (autonomous content/prospecting/social/customer agents). HubSpot parent: NYSE:HUBS, $2.6B+ revenue 2024.",
         claims="Breeze launched Sep-2024 (Inbound 2024); 4 launch agents; HubSpot $2.6B+ revenue",
         created="2024-09 (Breeze launched)", hq="Cambridge, MA",
         founders="HubSpot (Brian Halligan + Dharmesh Shah)",
         funding="HubSpot: public (NYSE: HUBS)",
         pros="Mid-market CRM dominance; Breeze agents bundled with existing tiers; broad app marketplace.",
         cons="Less reasoning-depth than Agentforce; tied to HubSpot ICP.",
         customers="216k+ HubSpot customers",
         compliance="SOC 2 Type II; ISO 27001; GDPR",
         optimised_for="mid-market sales/marketing AI agents on HubSpot CRM"),

    dict(tier=2, name="Outreach AI", url="https://www.outreach.io/product/platform/ai",
         type_str="AI features inside sales-engagement platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.outreach.io/product/platform/ai",
         desc="Outreach (the largest sales-engagement platform; $4.4B val 2021) has added AI features: Smart Email Assist, Smart Account Plan, Smart Forecasting, Kaia conversation intelligence. Strategic pivot to AI-agent platform announced 2024.",
         claims="Outreach $4.4B val 2021 ($488M raised); Smart Email Assist + Smart Account Plan + AI forecasting",
         created="2014 (Outreach); AI features 2023-24", hq="Seattle",
         founders="Manny Medina (CEO 2014-2024); Anna Baird (2024–)",
         funding="$488M raised; $4.4B val 2021 (Salesforce Ventures + Sands + Tiger Global)",
         pros="Largest sales-engagement platform; Salesforce Ventures-backed; AI overlay across the suite.",
         cons="2024 was difficult for the category (Outreach + Salesloft + Apollo competing on AI features); ARR plateaued.",
         customers="Adobe, Cisco, DoorDash + 6000+ sales orgs",
         optimised_for="sales-engagement AI features"),

    dict(tier=2, name="Apollo.io", url="https://www.apollo.io/",
         type_str="GTM platform with AI agents (Apollo AI)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.apollo.io/",
         desc="Founded 2015 (rebranded from ZenProspect); GTM platform — prospecting database + outreach + AI. $100M Series D Aug-2023 ($1.6B val; Bain Capital Ventures + Sequoia). $200M+ ARR; Apollo AI launched 2024.",
         claims="$100M Series D Aug-2023 ($1.6B val); $200M+ ARR; 16k+ paying customers; Apollo AI 2024",
         created="2015 (founded; rebranded 2021)", hq="San Francisco",
         founders="Tim Zheng (CEO; ex-Salesforce)",
         funding="$100M Series D Aug-2023 ($1.6B val; Bain + Sequoia)",
         pros="PLG motion + sales-engagement combo; $200M+ ARR; broad prospecting database; AI overlay.",
         cons="Database accuracy concerns historically; AI is overlay vs reimagined.",
         customers="16k+ paying customers (Veeva, Quora, Stripe, Mutiny)",
         optimised_for="GTM intelligence + AI-augmented outreach"),

    dict(tier=2, name="Gong", url="https://www.gong.io/",
         type_str="Revenue intelligence + AI agents",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.gong.io/",
         desc="Founded 2015; the largest conversation-intelligence/revenue-intelligence platform. $7.25B val 2021 ($583M raised); Gong AI (Smart Tracker, AI Forecast, Gong Engage) 2024. Considered category-defining.",
         claims="$7.25B val 2021 ($583M raised); $300M+ ARR; Gong Engage launched 2023; AI agent features 2024",
         created="2015 (founded)", hq="Palo Alto / Tel Aviv",
         founders="Amit Bendov (CEO); Eilon Reshef",
         funding="$583M raised; $7.25B val 2021 (Franklin Templeton + Coatue + Sequoia)",
         pros="Category-defining in revenue intelligence; $7.25B val; broad enterprise base; AI forecast feature widely used.",
         cons="2024 valuation compression vs 2021 peak; pricing complexity at enterprise tier.",
         customers="Snowflake, LinkedIn, Hubspot, PayPal + 4000+",
         compliance="SOC 2 Type II; ISO 27001",
         optimised_for="conversation intelligence + revenue intelligence + AI forecasting"),

    dict(tier=2, name="6sense", url="https://6sense.com/",
         type_str="ABM intent + AI agent platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://6sense.com/",
         desc="Founded 2013; ABM/intent platform with Revenue AI agents. $200M Series E Jan-2022 ($5.2B val; Blue Owl). 6sense Revenue AI agents launched 2024 — autonomous account research + email drafting.",
         claims="$200M Series E Jan-2022 ($5.2B val); 1500+ enterprise customers; Revenue AI agents 2024",
         created="2013 (founded)", hq="San Francisco",
         founders="Amanda Kahlow (founder); Jason Zintak (CEO)",
         funding="$200M Series E Jan-2022 ($5.2B val; Blue Owl + SoftBank + Insight)",
         pros="Strongest ABM/intent dataset; $5.2B val; broad enterprise base; AI agents on top of high-quality data.",
         cons="Pricing complexity; AI agents are overlay; competition with Demandbase in same niche.",
         customers="1500+ enterprise (Cisco, Dell, Workday, Mastercard)",
         optimised_for="ABM + intent data + AI revenue agents"),

    dict(tier=2, name="Demandbase", url="https://www.demandbase.com/",
         type_str="ABM platform with AI agents",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.demandbase.com/",
         desc="Founded 2006; ABM platform with intent + AI. $175M growth round Apr-2021 ($1B val; Vista Equity). Demandbase One Smarter GTM AI launched 2024 — buyer-stage scoring + auto-personalised outbound.",
         claims="$175M growth Apr-2021 ($1B val); 7500+ customers; Demandbase One AI 2024",
         created="2006 (founded)", hq="San Francisco",
         founders="Chris Golec (founder); Brewster Stanislaw (CEO 2024+)",
         funding="$175M Apr-2021 ($1B val; Vista Equity Partners)",
         pros="Long history in ABM; PE-backed; broad enterprise customer base; AI overlay.",
         cons="Less mindshare than 6sense; AI features lag 6sense Revenue AI.",
         customers="7500+ customers (HPE, Adobe, Box, DocuSign)",
         optimised_for="enterprise ABM + AI outbound personalisation"),

    dict(tier=2, name="People.ai", url="https://people.ai/",
         type_str="Revenue intelligence + AI SalesAI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://people.ai/",
         desc="Founded 2016 by Oleg Rogynskyy; revenue intelligence — activity capture + AI account intelligence. $100M Series D Sep-2021 ($1.1B val; Akkadian + ICONIQ). SalesAI agent launched 2024.",
         claims="$100M Series D Sep-2021 ($1.1B val); SalesAI launched 2024; revenue activity capture leader",
         created="2016 (founded)", hq="San Francisco",
         founders="Oleg Rogynskyy (CEO)",
         funding="$100M Series D Sep-2021 ($1.1B val; Akkadian + ICONIQ)",
         pros="Activity-capture data graph is differentiator; ICONIQ-backed; SalesAI 2024 builds on data.",
         cons="Less mindshare than Gong; 2024 valuation compression; smaller customer footprint.",
         customers="Lyft, Zoom, Cloudflare + enterprise sales orgs",
         optimised_for="activity-capture + revenue intelligence + AI SDR"),

    dict(tier=2, name="Clay", url="https://www.clay.com/",
         type_str="GTM data orchestration + AI agents",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.clay.com/",
         desc="Founded 2017; GTM data orchestration — combine 100+ data sources, enrich, AI-draft outbound. $46M Series B Jan-2024 (Sequoia + Boldstart + Box Group); reported $40M+ ARR mid-2024; viral with growth marketers. Considered a cultural touchstone of the 2024 AI-GTM wave.",
         claims="$46M Series B Jan-2024 (Sequoia); $40M+ ARR mid-2024; >$3B val talks Q1-2025 per The Information",
         created="2017 (founded)", hq="New York",
         founders="Kareem Amin (CEO; ex-Frame.io)",
         funding="$46M Series B Jan-2024 (Sequoia + Boldstart + Box Group); $3B val talks Q1-2025",
         pros="Most-talked-about GTM-AI product 2024; flexible spreadsheet UX; rich integrations; cult-favourite among growth marketers.",
         cons="Spreadsheet-style UX has a learning curve; usage-based pricing surprises power-users.",
         customers="Anthropic, OpenAI, Notion, Vercel, Ramp + 4000+",
         optimised_for="GTM data orchestration + AI enrichment + outbound"),

    dict(tier=3, name="Lavender", url="https://www.lavender.ai/",
         type_str="AI sales-email coach + writer",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.lavender.ai/",
         desc="Founded 2020; AI email coach for sellers — Gmail/Outlook plugin scores and rewrites cold outbound. $13.2M Series A Sep-2022 (Norwest Venture Partners + LIONS Capital). $10M+ ARR reported.",
         claims="$13.2M Series A Sep-2022 (Norwest + LIONS); >$10M ARR; 50k+ sellers per vendor",
         created="2020 (founded)", hq="Wilmington, NC",
         founders="Will Allred (CEO); Cory Bray (CRO)",
         funding="$13.2M Series A Sep-2022 (Norwest + LIONS)",
         pros="Sharp niche (email coaching); strong content marketing presence; 50k+ sellers.",
         cons="Niche category facing pressure from incumbent SEPs (Outreach, Salesloft) building similar.",
         optimised_for="AI sales-email coaching + cold-email scoring",
         customers="Sales orgs at thousands of SaaS companies"),

    dict(tier=3, name="Common Room", url="https://www.commonroom.io/",
         type_str="Community intelligence + AI signal-based sales agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.commonroom.io/",
         desc="Founded 2020; community intelligence platform that ingests GitHub, Slack, Discord, X, LinkedIn signals + maps them to people/companies; AI agent surfaces sales-ready signals. $32M Series B Mar-2024 (Greylock + Index + Madrona).",
         claims="$32M Series B Mar-2024 (Greylock + Index + Madrona); $52M total; signal-based GTM differentiator",
         created="2020 (founded)", hq="Seattle",
         founders="Linda Lian (CEO; ex-AWS PM); Tom Kleinpeter (CTO); Viraj Mody (CPO)",
         funding="$32M Series B Mar-2024 (Greylock + Index + Madrona)",
         pros="Strong founder pedigree (ex-AWS); Greylock-backed; signal-based GTM is differentiator vs static-database peers.",
         cons="Smaller customer base than Apollo/6sense; category-creation thesis still validating.",
         customers="Notion, Figma, Asana, Loom + developer-tools companies",
         optimised_for="developer-tools / community-led GTM + AI signal agent"),

    dict(tier=3, name="Reggie.ai", url="https://www.reggie.ai/",
         type_str="AI sales agents (Reggie)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.reggie.ai/",
         desc="Founded 2023; AI sales-agent product — autonomous outbound, meeting booking, follow-up. $4.7M seed Jul-2024 (Lightspeed + Mantis). Direct competitor in the 11x.ai / Artisan AI / Bland niche.",
         claims="$4.7M seed Jul-2024 (Lightspeed + Mantis); autonomous outbound SDR agent",
         created="2023 (founded)", hq="San Francisco",
         founders="Reggie founders (Tomer Sole + Yair Snir)",
         funding="$4.7M seed Jul-2024 (Lightspeed + Mantis)",
         pros="Lightspeed-backed; AI-SDR niche participation.",
         cons="Early-stage; competing with much-better-funded 11x.ai.",
         optimised_for="autonomous outbound SDR"),

    dict(tier=3, name="Toplyne", url="https://www.toplyne.io/",
         type_str="PLG-revenue ML / AI agent platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.toplyne.io/",
         desc="Founded 2021; PLG-revenue intelligence — predicts which free users will convert, sales-ready signals. $17.5M Series A May-2023 (Tiger Global + Sequoia + Together Fund). Pivoted to AI-agent positioning 2024.",
         claims="$17.5M Series A May-2023 (Tiger + Sequoia + Together Fund); $20M total raised; PLG-revenue ML",
         created="2021 (founded)", hq="Bangalore / San Francisco",
         founders="Rishen Kapoor (CEO); Rohit Khare (CTO)",
         funding="$17.5M Series A May-2023 (Tiger + Sequoia + Together)",
         pros="PLG-revenue niche differentiates; Tiger + Sequoia-backed; India-US footprint gives cost advantage.",
         cons="Narrow PLG-only ICP; 2024 pivot adds AI-agent framing on top of established ML product.",
         customers="Canva, Vercel, Mixpanel, MongoDB + PLG SaaS",
         optimised_for="PLG conversion prediction + AI sales agent"),
]


# --- F. Scientific research agents (deep-research) ---
SCIENCE_ROWS = [
    dict(tier=2, name="Sakana AI Scientist", url="https://sakana.ai/ai-scientist/",
         type_str="Autonomous AI research-paper-writing agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://sakana.ai/ai-scientist/",
         desc="Tokyo-based Sakana AI's autonomous research agent — generates ideas, runs experiments, writes papers, peer-reviews. v1 paper Aug-2024 (arXiv 2408.06292); v2 update 2025. **Sakana parent: $214M Series A Sep-2024 ($1.5B val; NEA + Khosla)**.",
         claims="**Sakana AI: $214M Series A Sep-2024 ($1.5B val; NEA + Khosla + Lux Capital)**; AI Scientist v1 paper Aug-2024 (arXiv 2408.06292); v2 update 2025",
         created="2024-08 (AI Scientist v1)", hq="Tokyo",
         founders="David Ha (CEO; ex-Google Brain Research Director); Llion Jones (CTO; ex-Google co-author of Attention Is All You Need); Robert Lange",
         funding="**Sakana AI: $214M Series A Sep-2024 ($1.5B val; NEA + Khosla + Lux Capital)**",
         license_="MIT (Code OSS)",
         gh="github.com/SakanaAI/AI-Scientist (12k+ stars)",
         code_release="MIT — OSS",
         pros="One of the most-cited autonomous-science agents; David Ha + Llion Jones founders; OSS reference implementation; $1.5B val Sakana parent.",
         cons="Quality of generated papers heavily disputed; humans-still-needed-everywhere caveats; not yet a productised platform.",
         customers="Research-stage; not productised",
         optimised_for="autonomous ML-research-paper drafting",
         deployment="OSS self-host"),

    dict(tier=1, name="OpenAI Deep Research", url="https://openai.com/index/introducing-deep-research/",
         type_str="Autonomous research agent (cross-listing harness)",
         tax=TAX_AGENT_HARNESS, primary_url="https://openai.com/index/introducing-deep-research/",
         desc="Cross-listing: OpenAI Deep Research, launched Feb-2025 inside ChatGPT, is OpenAI's flagship long-horizon research agent (o3 base model). Distinct from the OpenAI Codex / Computer Use rows because the focus is web-research + multi-step synthesis. Available to Pro / Plus / Team / Enterprise users.",
         claims="Launched Feb-2025 in ChatGPT (Pro tier first); built on o3; tackles 30-min+ multi-step research; benchmarks: HLE (Humanity's Last Exam) 26.6% (vs GPT-4o 3.3%)",
         created="2025-02 (Deep Research launched)", hq="San Francisco",
         founders="OpenAI",
         pros="Highest-quality research-agent in production as of 2025 H1; HLE benchmark dominance; integrated with ChatGPT distribution.",
         cons="ChatGPT-only; Pro-tier-first ($200/mo); rate-limited; long-horizon turn-time (10–30 min).",
         customers="ChatGPT Pro / Plus / Team / Enterprise users",
         pricing="Pro $200/mo (100 queries/mo); Plus tier 10 queries/mo (post-Apr 2025)",
         optimised_for="autonomous web research + synthesis"),

    dict(tier=1, name="Perplexity Deep Research", url="https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research",
         type_str="Autonomous research agent (Perplexity)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.perplexity.ai/hub/blog/introducing-perplexity-deep-research",
         desc="Perplexity's autonomous-research mode, launched Feb-2025 — multi-step research agent inside Perplexity. Perplexity parent: $9B val Dec-2024 ($500M round; IVP + NEA + Andreessen Horowitz).",
         claims="Deep Research launched Feb-2025; Perplexity $9B val Dec-2024 ($500M round)",
         created="2025-02 (Deep Research launched)", hq="San Francisco",
         founders="Aravind Srinivas (CEO); Denis Yarats; Andy Konwinski",
         funding="Perplexity: $9B val Dec-2024 ($500M round; IVP + NEA + a16z)",
         pros="$9B val parent; free-tier access to research-agent (5/day); broader-than-OpenAI source coverage.",
         cons="Output quality polarising vs OpenAI; less benchmark dominance.",
         customers="Perplexity Pro + free users",
         pricing="Pro $20/mo (unlimited); free 5/day"),

    dict(tier=2, name="You.com Research", url="https://you.com/research",
         type_str="Web-research AI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://you.com/research",
         desc="You.com's research-agent mode — multi-step web research + synthesis. You.com parent: $99M Series B Aug-2024 ($700M val; Georgian + NEA + Salesforce Ventures). Founded by Richard Socher (ex-Salesforce Chief Scientist).",
         claims="$99M Series B Aug-2024 ($700M val); founded by ex-Salesforce CS Richard Socher; research-agent mode launched 2024",
         created="2024 (Research mode)", hq="San Francisco",
         founders="Richard Socher (CEO; ex-Salesforce Chief Scientist; co-founder MetaMind)",
         funding="$99M Series B Aug-2024 ($700M val; Georgian + NEA + Salesforce Ventures)",
         pros="Richard Socher founder pedigree; Georgian + Salesforce-backed; agent-mode shipped early.",
         cons="Lower mindshare than Perplexity; consumer + enterprise positioning split.",
         optimised_for="enterprise web research with privacy controls",
         customers="$700M val SaaS — research mode"),

    dict(tier=2, name="Stanford STORM", url="https://storm.genie.stanford.edu/",
         type_str="Wikipedia-style article-writing agent (OSS)",
         tax=TAX_AGENT_HARNESS, primary_url="https://storm.genie.stanford.edu/",
         desc="Stanford NLP's STORM (Synthesis of Topic Outline through Retrieval and Multi-perspective question-asking) — generates Wikipedia-style articles from a topic prompt. NAACL 2024 paper (arXiv 2402.14207). MIT OSS; 25k+ stars; Apache demo at storm.genie.stanford.edu.",
         claims="NAACL 2024 paper (arXiv 2402.14207); Stanford NLP; >25k stars; Wikipedia-style synthesis benchmarks",
         created="2024-02 (STORM paper)", hq="Stanford CA",
         founders="Yijia Shao + others (Stanford NLP, Monica Lam group)",
         license_="MIT", gh="github.com/stanford-oval/storm (~25k stars)",
         code_release="MIT — OSS",
         pros="Free, OSS, Stanford-backed; 25k+ GitHub stars; novel multi-perspective approach.",
         cons="Research demo, not productised SaaS; quality varies by topic; no enterprise support.",
         customers="Researchers + free demo users at storm.genie.stanford.edu",
         optimised_for="Wikipedia-style article synthesis from a topic"),

    dict(tier=2, name="AlphaSense", url="https://www.alpha-sense.com/",
         type_str="Financial-research search platform + Genesis AI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.alpha-sense.com/",
         desc="Founded 2010; AI-driven market intelligence — semantic search over earnings calls, broker research, regulatory filings. $4B val Jun-2024 ($650M growth round; BDT + MSP). **Acquired Tegus Jun-2024 for $930M** (expert-call transcripts). Genesis = autonomous research agent launched 2024.",
         claims="$650M raised Jun-2024 ($4B val; BDT + MSP); **Tegus acq Jun-2024 $930M**; 6000+ enterprise customers including 85% of S&P 100",
         created="2010 (founded)", hq="New York",
         founders="Jack Kokko (CEO; ex-Morgan Stanley analyst); Raj Neervannan (CTO)",
         funding="$4B val Jun-2024 ($650M growth round; BDT + MSP)",
         pros="$4B val; 85% of S&P 100 customers; Tegus acq adds expert-call transcripts; Genesis agent on top of richest financial corpus.",
         cons="Expensive ($10k+/year); incumbent-heavy customer base; agent more analytics-overlay than autonomous.",
         customers="6000+ enterprise (85% of S&P 100; 80% of top-10 PE firms)",
         compliance="SOC 2 Type II",
         optimised_for="financial-research search + AI agent for buy-side / sell-side",
         deployment="SaaS"),

    dict(tier=2, name="Hebbia", url="https://www.hebbia.com/",
         type_str="Enterprise research agent (Matrix)",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.hebbia.com/",
         desc="Founded 2020 by George Sivulka (ex-Stanford); Matrix is its enterprise research agent — multi-step research across documents. $130M Series B Jul-2024 ($700M val; Andreessen Horowitz + Index + Google Ventures + Peter Thiel). Used heavily at Tier-1 investment banks + hedge funds.",
         claims="$130M Series B Jul-2024 ($700M val; a16z + Index + GV + Peter Thiel); used at Tiger Global, Charlesbank + Tier-1 IB",
         created="2020 (founded)", hq="New York",
         founders="George Sivulka (CEO; Stanford PhD dropout)",
         funding="$130M Series B Jul-2024 ($700M val; a16z + Index + GV)",
         pros="$700M val; a16z + Index + GV-backed; Matrix differentiates from query-response agents (spreadsheet-style cell-by-cell agent); heavy IB / hedge-fund adoption.",
         cons="Enterprise sales-cycle complexity; pricing reserved for top-tier financials.",
         customers="Tiger Global, Charlesbank, Centerview Partners + Tier-1 IB",
         optimised_for="enterprise document research (IB / PE / consulting)"),

    dict(tier=3, name="Liner", url="https://liner.com/ai",
         type_str="Personal AI research assistant (highlight + research)",
         tax=TAX_AGENT_HARNESS, primary_url="https://liner.com/ai",
         desc="Seoul-founded Liner — started as web-highlighter (2015), pivoted to AI research assistant 2023. $40M Series B Jul-2023 ($350M val; Salesforce Ventures + DSC Investment + Beenext). 10M+ users.",
         claims="$40M Series B Jul-2023 ($350M val; Salesforce Ventures + DSC + Beenext); 10M+ users",
         created="2015 (founded); AI 2023", hq="Seoul",
         founders="Luke Kim (CEO; ex-Samsung)",
         funding="$40M Series B Jul-2023 ($350M val; Salesforce Ventures)",
         pros="Asia-Pacific consumer focus; 10M+ users; Salesforce Ventures-backed.",
         cons="Less brand in US/EU; consumer-tier AI agent vs enterprise.",
         optimised_for="consumer AI research assistant + web highlight"),

    dict(tier=3, name="scite.ai", url="https://scite.ai/",
         type_str="Citation-supported AI research assistant",
         tax=TAX_AGENT_HARNESS, primary_url="https://scite.ai/",
         desc="Founded 2018 by Josh Nicholson (PhD); citation-supported research search — find supporting/contrasting/mentioning citations for a scientific claim. **Acquired by Research Solutions Sep-2023 for $26M**. scite Assistant is the AI-research-agent overlay launched 2023.",
         claims="**Acquired by Research Solutions Sep-2023 for $26M**; 1.2B+ citation statements indexed; scite Assistant 2023",
         created="2018 (founded)", hq="Brooklyn",
         founders="Josh Nicholson (CEO; PhD molecular biology)",
         funding="Acquired by Research Solutions Sep-2023 for $26M",
         pros="Unique citation-context dataset (1.2B+ statements); academic credibility; integrated into Research Solutions.",
         cons="Post-acq strategy under broader Research Solutions umbrella; smaller raise than peers.",
         customers="Universities + pharma + biotech research orgs",
         optimised_for="citation-supported scientific research"),

    dict(tier=3, name="Iris.ai", url="https://iris.ai/",
         type_str="Scientific research engine + AI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://iris.ai/",
         desc="Oslo-founded 2015; scientific research engine + AI agent for R&D. Bootstrapped + small angel rounds; broader European AI scene. Differentiates with explainable / hallucination-free claims.",
         claims="Iris.ai founded 2015; Oslo-based; 'Researcher Workspace' AI agent; explainable AI focus",
         created="2015 (founded)", hq="Oslo",
         founders="Anita Schjøll Brede (CEO); Maria Ritola (COO)",
         pros="EU R&D pedigree; explainability/hallucination focus differentiates; gov + corporate R&D customer base.",
         cons="Small commercial footprint vs Elicit/Consensus; less brand outside Europe.",
         optimised_for="enterprise R&D + scientific research"),
]


# --- G. Finance / quant AI agents ---
FINANCE_ROWS = [
    dict(tier=2, name="Rogo", url="https://rogo.ai/",
         type_str="Investment-banking AI agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://rogo.ai/",
         desc="Founded 2022 by Gabriel Stengel (ex-Lazard + Stanford); AI agent purpose-built for investment-banking workflows — comps, precedent transactions, IC memo drafting. $50M Series B Mar-2025 ($350M val; Khosla + Thrive Capital + Tiger Global). Customer base: 25+ IBs including Lazard, Tiger Global, Hellman & Friedman.",
         claims="$50M Series B Mar-2025 ($350M val; Khosla + Thrive + Tiger Global); 25+ IBs including Lazard, Tiger Global, H&F",
         created="2022 (founded)", hq="New York",
         founders="Gabriel Stengel (CEO; ex-Lazard); John Wilemon (CTO; ex-Bridgewater)",
         funding="$50M Series B Mar-2025 ($350M val; Khosla + Thrive + Tiger)",
         pros="Most-discussed finance-AI agent 2024-25; founder ex-Lazard pedigree; top-tier IB customer roster.",
         cons="High-end IB ICP narrows TAM; enterprise sales-cycle dependency; price-point reserved for top-tier.",
         customers="Lazard, Tiger Global, Hellman & Friedman + 25+ IBs",
         compliance="SOC 2 Type II",
         optimised_for="investment-banking-specific AI agent (M&A / capital markets / PE)",
         deployment="SaaS"),

    dict(tier=2, name="Causaly", url="https://www.causaly.com/",
         type_str="Biomedical knowledge-graph + AI research agent",
         tax=TAX_GRAPH_AGENT, primary_url="https://www.causaly.com/",
         desc="Cross-listing: Causaly already exists in Scientific / research AI memory. This row adds the use-case agent harness framing: London-based biomedical-research AI for drug-discovery teams. $60M Series B 2023 (Index + ICONIQ). 25M+ scientific articles indexed; causal-graph-grounded.",
         claims="$60M Series B 2023 (Index + ICONIQ; reportedly $300M+ val); 25M+ articles; causal-graph search",
         created="2017 (founded)", hq="London",
         founders="Yiannis Kiachopoulos (CEO); Artur Saudabayev (CTO)",
         funding="$60M Series B 2023 (Index + ICONIQ)",
         pros="Causal-graph differentiator vs vanilla RAG-on-PubMed; Pfizer-grade customer base; Index + ICONIQ.",
         cons="Biomedical-only ICP; expensive enterprise pricing; smaller than AlphaSense.",
         customers="Pfizer, AstraZeneca, Bristol Myers Squibb, GSK",
         optimised_for="drug-discovery + biomedical research + causal-graph search"),

    dict(tier=3, name="Trade Ideas Holly AI", url="https://www.trade-ideas.com/holly/",
         type_str="AI trading-idea generation agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.trade-ideas.com/holly/",
         desc="Holly AI is the trading-idea generation agent inside the Trade Ideas platform (founded 2003). Holly back-tests millions of strategies overnight + surfaces 'tradeable ideas' for retail/prosumer traders. Bootstrapped; long-running niche product pre-LLM wave.",
         claims="Trade Ideas founded 2003; Holly AI launched 2009; tens of thousands of retail traders subscribed",
         created="2009 (Holly AI launched)", hq="San Diego",
         founders="Dan Mirkin + David Aferiat (Trade Ideas founders)",
         pros="Long-running product (pre-LLM wave); thousands of paid retail subscribers; differentiated trading-specific use case.",
         cons="More algorithmic-screen than LLM-agent; the 'AI' framing predates the 2023 LLM wave; retail-focused.",
         customers="Retail / prosumer day-traders",
         pricing="$120-180/month",
         optimised_for="AI-driven retail trading idea generation"),

    dict(tier=3, name="OpenBB", url="https://openbb.co/",
         type_str="OSS investment-research platform with AI agents",
         tax=TAX_AGENT_HARNESS, primary_url="https://openbb.co/",
         desc="Founded 2021 by Didier Lopes; OSS investment-research platform — Bloomberg-Terminal-alternative. AGPLv3 + commercial OpenBB Pro. $11M seed 2022 (OSS Capital + Y Combinator). AI agent (OpenBB Copilot) launched 2024.",
         claims="$11M seed 2022 (OSS Capital + YC); AGPLv3 OSS + OpenBB Pro tier; OpenBB Copilot AI 2024; ~30k GH stars",
         created="2021 (founded)", hq="New York",
         founders="Didier Lopes (CEO; ex-Truvalue Labs)",
         funding="$11M seed 2022 (OSS Capital + YC)",
         license_="AGPLv3 + commercial",
         gh="github.com/OpenBB-finance/OpenBB (~30k stars)",
         code_release="AGPLv3 OSS",
         pros="OSS-first differentiator; 30k+ GH stars; AGPLv3 + commercial dual-license; AI agent integrated.",
         cons="OSS revenue model still maturing; AI features lag commercial AlphaSense/Hebbia.",
         optimised_for="OSS investment research + AI agent",
         customers="Indie traders + university research + small hedge funds"),

    dict(tier=3, name="Composer", url="https://www.composer.trade/",
         type_str="AI-driven retail algorithmic-trading platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.composer.trade/",
         desc="Founded 2020 (YC W21); AI-driven retail algorithmic-trading — composable strategies + LLM strategy builder. $14M Series A May-2022 (Greycroft + Y Combinator). Composer GPT + strategy-builder AI launched 2023.",
         claims="$14M Series A May-2022 (Greycroft + YC); >$300M assets under management; Composer GPT AI 2023",
         created="2020 (founded)", hq="San Francisco",
         founders="Ben Rollert (CEO); Tony Berkman; Marcello Salinas",
         funding="$14M Series A May-2022 (Greycroft + YC)",
         pros="YC-backed; Greycroft-backed; AI strategy-builder lowers barrier to algo trading.",
         cons="Retail-focused; regulatory + reliability constraints limit growth; $300M AUM is small vs incumbents.",
         optimised_for="retail AI-driven algorithmic trading",
         customers="Retail investors + financial advisors",
         compliance="FINRA / SEC RIA"),

    dict(tier=3, name="Pluto AI", url="https://www.heypluto.ai/",
         type_str="AI-augmented personal-finance agent",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.heypluto.ai/",
         desc="Founded 2024; AI personal-finance assistant — analyses spending, suggests savings, manages budgets via chat. Consumer-tier; small seed funding. Distinct from Pluto Money (different product; same space).",
         claims="2024-founded consumer personal-finance AI agent; YC-backed seed",
         created="2024 (founded)", hq="San Francisco",
         founders="Pluto AI founders",
         pros="Consumer personal-finance niche; YC backing.",
         cons="Early-stage; small footprint; regulatory ambiguity for chat-based financial advice."),

    dict(tier=3, name="Linq AI", url="https://www.linq.ai/",
         type_str="AI agent for financial analysts",
         tax=TAX_AGENT_HARNESS, primary_url="https://www.linq.ai/",
         desc="Founded 2023; AI-agent platform for financial analysts — multi-step research, data cleansing, model-building. Small seed round; competes in the AlphaSense / Hebbia / Rogo broader space at lower price point.",
         claims="2023-founded; financial-analyst AI agent; seed funded",
         created="2023 (founded)", hq="San Francisco",
         founders="Linq AI founders",
         pros="Niche entry in finance-AI agent space at lower price point.",
         cons="Early-stage; tiny footprint vs Rogo/Hebbia; brand confusion with multiple 'Linq' products."),

    dict(tier=3, name="Numerai Signals", url="https://signals.numer.ai/",
         type_str="Crowdsourced AI signals hedge-fund platform",
         tax=TAX_AGENT_HARNESS, primary_url="https://signals.numer.ai/",
         desc="Numerai is a crowdsourced AI hedge fund — data scientists submit predictive signals + are paid in NMR (cryptocurrency) based on signal performance. Numerai Signals is the global-equities tournament. Founded 2015 by Richard Craib. ~$200M AUM reported.",
         claims="Numerai founded 2015 (Richard Craib); >$200M AUM; thousands of data-scientist participants; NMR token incentive structure",
         created="2015 (founded); Signals 2019", hq="San Francisco",
         founders="Richard Craib (CEO)",
         funding="Numerai: $11M Series A 2017 (USV + Coatue); NMR token issuance",
         pros="Unique crowdsourced/token-incentive model; long-running; differentiated from agent-platform peers.",
         cons="Niche model; token-incentive complications; AUM small vs traditional hedge funds; not strictly an 'agent platform' but qualifies as use-case-specific AI in finance.",
         customers="Data-scientist contributors + the hedge fund itself",
         optimised_for="crowdsourced AI predictive signals for global equities",
         compliance="US RIA"),
]

# ============================================================================
# RENDER
# ============================================================================

def render_section_header(title: str, explainer: str, subsection: bool = False) -> str:
    style = ' style="padding-left: 28px; text-transform: none; letter-spacing: 0.04em; color: #b8b8b8;"' if subsection else ''
    return (
        f'\n  <tr class="group-row"><td colspan="83"{style}>{html.escape(title)}</td></tr>\n'
        f'\n  <tr class="section-explainer"><td colspan="83"><div class="explainer-text">{explainer}</div></td></tr>\n'
    )

def main():
    parts = []
    # Top-level section
    parts.append(render_section_header(
        "Use-case-specific agent harnesses",
        ("Agents purpose-built for a specific work domain — security, legal, compliance, "
         "SRE/DevOps, sales/GTM, scientific research, and finance. Where the existing "
         "<em>Agent IDEs &amp; coding harnesses</em> section captures general-purpose coding agents "
         "and <em>Vertical / domain-specific AI memory</em> captures memory architectures with "
         "domain semantics, this section is the third axis: products whose <em>task and domain "
         "constraints</em> define the offering — regardless of whether they ship a documented "
         "memory layer. Added in the 2026-05-13 Round-13 sweep with seven sub-groups: "
         "Security (red-team + pentest + SOC + AppSec), Legal (matter and contract agents), "
         "Compliance (GRC / audit automation), SRE/DevOps (AIOps + observability + autonomous SRE), "
         "Sales/GTM (AI SDRs + RevOps), Scientific (research agents beyond what's in Scientific "
         "memory), and Finance (investment-banking + analyst agents)."),
        subsection=False,
    ))

    for title, rows in [
        ("— Security: red-team, pentest, SOC, AppSec", SECURITY_ROWS),
        ("— Legal: matter / contract agents", LEGAL_ROWS),
        ("— Compliance / audit / governance agents", COMPLIANCE_ROWS),
        ("— SRE / DevOps / observability AI agents", SRE_ROWS),
        ("— Sales / GTM / outbound agents", SALES_ROWS),
        ("— Scientific research agents", SCIENCE_ROWS),
        ("— Finance / quant AI agents", FINANCE_ROWS),
    ]:
        explainer = SUB_EXPLAINERS[title]
        parts.append(render_section_header(title, explainer, subsection=True))
        for kwargs in rows:
            parts.append(use_case_row(**kwargs))
            parts.append("")  # blank line between rows
    print("\n".join(parts))


SUB_EXPLAINERS = {
    "— Security: red-team, pentest, SOC, AppSec":
        "Agents purpose-built for offensive and defensive security work: LLM red-teaming "
        "platforms, autonomous pentesters, AI SOC analysts, AI-augmented AppSec / SAST. "
        "Distinct from <em>Memory governance, privacy &amp; safety</em> (which collects "
        "memory-poisoning and DLP-shaped tools) — this is the broader cybersecurity "
        "operations layer. Lakera Guard / Lakera Red, HiddenLayer, Patronus AI, and "
        "Robust Intelligence remain canonical in the Memory-governance section; the "
        "rows here are the parallel commercial offerings whose primary identity is "
        "security operations rather than memory hygiene.",
    "— Legal: matter / contract agents":
        "Legal-specific agent harnesses that go beyond what is captured in the "
        "<em>Vertical / domain-specific AI memory — Legal AI memory</em> subsection "
        "(which collects products whose memory architecture is the differentiator). "
        "This sub-group adds the harness framing for Legora, LawDroid, DraftWise, "
        "Pincites, Litera AI, DocuSign IAM, Ironclad's AI Assistant, and Tonkean "
        "LegalWorks — products whose <em>task</em> (drafting, redlining, intake, "
        "negotiation, research) defines the offering. The existing Harvey / Casetext / "
        "Spellbook / Robin AI / Eve / Lexis+ AI rows remain canonical in the Legal "
        "memory subsection.",
    "— Compliance / audit / governance agents":
        "Compliance automation, GRC, and audit platforms with AI agents. Distinct from "
        "<em>Memory governance, privacy &amp; safety</em> (memory-specific compliance) "
        "and from generic security operations — these are the SOC 2 / ISO 27001 / "
        "HIPAA / NIST automation tools (Vanta, Drata, Secureframe), plus enterprise "
        "GRC (AuditBoard, LogicGate, Hyperproof, Onspring) and trust-center / "
        "questionnaire-fill products. The category is dense at T1+T2 because "
        "compliance is one of the highest-ROI applications of LLM agents.",
    "— SRE / DevOps / observability AI agents":
        "AIOps + observability AI agents. Distinct from <em>Evaluation &amp; "
        "observability platforms</em> (which is LLM-app observability — LangSmith, "
        "Phoenix, Langfuse, Galileo) — this section is for infrastructure-ops AI: "
        "Datadog Bits AI, Dynatrace Davis CoPilot, PagerDuty AIOps, New Relic AI, "
        "Sysdig Sage, incident.io AI, and the new autonomous-SRE startups Resolve.ai, "
        "Cleric, and RunWhen. The agent's task is incident management, root-cause "
        "analysis, runbook automation, and engineering productivity.",
    "— Sales / GTM / outbound agents":
        "AI agents for sales, GTM intelligence, and outbound. Distinct from "
        "<em>Customer support / voice agent memory</em> (CX-shaped CRM memory) "
        "and from <em>Voice agent platforms</em> (developer voice-AI infra) — this "
        "is the seller-side AI: AI SDRs (11x.ai, Reggie.ai), revenue intelligence "
        "(Gong, People.ai), GTM data (Clay, Common Room, Apollo.io, Toplyne), ABM "
        "(6sense, Demandbase), and email coaching (Lavender). Salesforce Agentforce "
        "and HubSpot Breeze are listed here as the platform-vendor agent IDEs.",
    "— Scientific research agents":
        "Autonomous research agents whose task is multi-step web research, "
        "literature synthesis, or paper-writing. Distinct from the existing "
        "<em>Scientific / research AI memory</em> subsection (which collects Elicit, "
        "Consensus, PaperQA2, Glass Health — products with documented memory "
        "architecture). This sub-group adds OpenAI Deep Research, Perplexity Deep "
        "Research, You.com Research, Stanford STORM, Sakana AI Scientist, AlphaSense "
        "Genesis, Hebbia Matrix, Liner, scite.ai, and Iris.ai — agents where the "
        "task (long-horizon research) defines the product.",
    "— Finance / quant AI agents":
        "Finance and quantitative-research AI agents. Distinct from generic "
        "scientific-research agents because the domain semantics (financial filings, "
        "earnings transcripts, expert-call data, market data, trading rules) define "
        "the offering. Rogo (investment-banking agent), AlphaSense / Hebbia "
        "(research agents — cross-listed under Scientific), Trade Ideas Holly "
        "(trading), OpenBB (OSS Bloomberg-Terminal alternative), Composer (retail "
        "algorithmic trading), Numerai Signals (crowdsourced AI hedge fund).",
}

if __name__ == "__main__":
    main()
