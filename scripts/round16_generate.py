#!/usr/bin/env python3
"""Round-16 row generator — game and interactive-environment benchmarks.

Generates rows for the new subsection "Game / interactive-environment
benchmarks" under "Memory benchmarks & evaluation". Each row produces
exactly 68 <td> cells (1 name + 1 type + 7 taxonomy + 59 remaining
cell columns) all terminal (real-data with citation OR not-applicable
with reason OR depth-floor-reached with citation).

Usage:
    python3 scripts/round16_generate.py > /tmp/round16_rows.html
"""

from __future__ import annotations
import html
import sys

# ---- 59 remaining cell columns (after type) per CELL_COLUMN_SLUGS in extract.py
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

NOT_OSS = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not OSS</span>'
NO_REPO = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — no GitHub repo</span>'
NOT_MEMORY = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not a memory product</span>'
NOT_RESEARCH = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not a research paper</span>'
NOT_ACADEMIC = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not academic</span>'
NOT_COMMERCIAL = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not commercial</span>'
NOT_COMPANY = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not a company</span>'
NOT_DEPLOY = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — not a deployable product</span>'
NOT_PERF = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — does not compete on benchmarks</span>'
NA_EVAL = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — eval dataset, not a system</span>'
NA_EVAL_NDASH = '<span class="no-data" style="font-style:italic;color:#555;">not applicable - eval dataset, not a system</span>'
NA_BENCH_HARN = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — benchmark / evaluation harness</span>'
NA_WRONG = '<span class="no-data" style="font-style:italic;color:#555;">not applicable — wrong section</span>'
NA_GENERIC = '<span class="no-data" style="font-style:italic;color:#555;">not applicable</span>'
NA_STATIC = 'not applicable — static benchmark'

# Taxonomy template for benchmarks (matches BABILong/NIAH precedent)
TAX_BENCHMARK = {
    "storage": NA_EVAL,
    "retrieval": NA_EVAL,
    "persistence": NA_EVAL,
    "update": '<span class="tax-pill tax-read-only">read-only</span>',
    "unit": NA_EVAL,
    "governance": NA_EVAL,
    "conflict": '<span class="no-data" style="font-style:italic;color:#555;">not applicable — read-only evaluation dataset</span>',
}

# Taxonomy for an agent-product (claude/gemini plays pokemon — products that benchmark themselves on games)
TAX_AGENT_PROD = {
    "storage": '<span class="tax-pill tax-kv">kv</span>',
    "retrieval": '<span class="tax-pill tax-extraction-pull">extraction-pull</span>',
    "persistence": '<span class="tax-pill tax-session-only">session-only</span>',
    "update": '<span class="tax-pill tax-agent-controlled">agent-controlled</span>',
    "unit": '<span class="tax-pill tax-episode">episode</span>',
    "governance": '<span class="tax-pill tax-opaque">opaque</span>',
    "conflict": 'agent self-corrects via re-planning',
}


def cite(url):
    return f' <a class="cite" href="{html.escape(url)}" title="source">↗</a>'


def cite_searched(url):
    return f' <a class="cite" href="{html.escape(url)}" title="searched">↗</a>'


def real(value, citation_url):
    """Real-data cell with citation."""
    return f"{value}{cite(citation_url)}"


def searched(citation_url):
    """depth-floor-reached, value 'searched not found'."""
    return f'<span class="no-data">searched not found</span>{cite_searched(citation_url)}'


def render_row(*, tier, name, url, type_str, tax, primary_url, fills):
    """Render one <tr> with 68 cells.

    fills: dict[col_slug -> rendered inner HTML (already includes citation if applicable)]
        Missing slugs become NA_WRONG.
    """
    out = [f'  <tr class="row-t{tier}">']
    out.append(f'    <td class="name"><a href="{html.escape(url)}">{html.escape(name)}</a></td>')
    out.append(f'    <td class="type">{type_str}{cite(primary_url)}</td>')
    for axis in ("storage", "retrieval", "persistence", "update", "unit", "governance", "conflict"):
        v = tax[axis]
        out.append(f'    <td class="tax-{axis}">{v}</td>')
    for slug in COLS_REMAINING:
        v = fills.get(slug, NA_WRONG)
        out.append(f'    <td class="{slug}">{v}</td>')
    out.append('  </tr>')
    return "\n".join(out)


def bench_row(*, tier, name, url, type_str, primary_url,
              desc, claims=None, modalities=None, created=None,
              latest_release=None, license_=None, gh=None,
              mindshare=None, citations_val=None,
              founders=None, perf=None, repro=None, code_release=None,
              versioning=None, schema_evolution=None,
              forgetting=None, tombstoning=None,
              pros=None, cons=None, links=None,
              pricing=None, deployment=None):
    """Builder for a benchmark row (uses TAX_BENCHMARK). Mirrors the
    BABILong/NIAH structure exactly: most product columns are NA."""
    fills = {}
    fills["desc"] = real(desc, primary_url)
    fills["claims"] = real(claims, primary_url) if claims else searched(primary_url)
    fills["modalities"] = real(modalities, primary_url) if modalities else searched(primary_url)
    fills["created"] = real(created, primary_url) if created else searched(primary_url)
    fills["latest-release"] = real(latest_release, primary_url) if latest_release else NOT_OSS
    fills["license"] = real(license_, primary_url) if license_ else NOT_OSS
    fills["gh"] = real(gh, primary_url) if gh else NO_REPO
    fills["mindshare"] = real(mindshare, primary_url) if mindshare else searched(primary_url)
    fills["citations"] = real(citations_val, primary_url) if citations_val else NOT_ACADEMIC
    fills["funding"] = NOT_COMMERCIAL
    fills["customers"] = NOT_COMMERCIAL
    fills["pricing"] = real(pricing or "not applicable — open benchmark; free to use", primary_url) if pricing != False else NOT_COMMERCIAL
    fills["compliance"] = NOT_COMMERCIAL
    fills["data-handling"] = NOT_COMMERCIAL
    fills["deployment"] = real(deployment or "not applicable — run locally", primary_url)
    fills["hq"] = NOT_COMPANY
    fills["founders"] = real(founders, primary_url) if founders else searched(primary_url)
    fills["volume"] = NOT_MEMORY
    fills["perf"] = NOT_PERF
    fills["repro"] = real(repro, primary_url) if repro else NOT_RESEARCH
    fills["code-release"] = real(code_release, primary_url) if code_release else NOT_RESEARCH
    fills["api-surface"] = NA_EVAL
    fills["latency"] = NA_EVAL
    fills["throughput"] = NA_EVAL
    fills["backend-storage"] = NA_EVAL
    fills["multi-tenancy"] = NA_EVAL
    fills["encryption"] = NA_EVAL
    fills["sso-rbac"] = NA_EVAL
    fills["embedding-model"] = NA_EVAL
    fills["consistency"] = NA_GENERIC
    fills["versioning"] = real(versioning or NA_STATIC, primary_url)
    fills["tombstoning"] = real(tombstoning or NA_STATIC, primary_url) if tombstoning is not False else NA_GENERIC
    fills["schema-evolution"] = real(schema_evolution or "not applicable — fixed evaluation dataset", primary_url)
    fills["namespace"] = NA_GENERIC
    fills["contradiction"] = NA_GENERIC
    fills["forgetting"] = real(forgetting or NA_STATIC, primary_url) if forgetting is not False else NA_GENERIC
    fills["mcp-support"] = NA_BENCH_HARN
    fills["a2a-support"] = NA_BENCH_HARN
    fills["otel"] = NA_BENCH_HARN
    fills["webhooks"] = NA_BENCH_HARN
    fills["import-export"] = NA_BENCH_HARN
    fills["integration-count"] = NA_WRONG
    fills["orchestration"] = NA_WRONG
    fills["programmatic-control"] = NA_WRONG
    fills["vendor-benchmarks"] = NA_WRONG
    fills["pricing-specifics"] = NA_WRONG
    fills["agent-abstraction"] = NA_WRONG
    fills["memory-primitives"] = NA_WRONG
    fills["llm-lock"] = NA_WRONG
    fills["runtimes"] = NA_WRONG
    fills["session-handling"] = NA_WRONG
    fills["validated-verticals"] = NA_EVAL_NDASH
    fills["time-to-running"] = NA_EVAL_NDASH
    fills["anti-fit"] = NA_EVAL_NDASH
    fills["optimised-for"] = NA_EVAL_NDASH
    fills["adjacent-infrastructure"] = NA_EVAL_NDASH
    fills["pros"] = real(pros, primary_url) if pros else searched(primary_url)
    fills["cons"] = real(cons, primary_url) if cons else searched(primary_url)
    fills["links"] = real(links or url.replace("https://", "").replace("http://", ""), primary_url)
    return render_row(tier=tier, name=name, url=url, type_str=type_str,
                      tax=TAX_BENCHMARK, primary_url=primary_url, fills=fills)


def agent_product_row(*, tier, name, url, type_str, primary_url,
                      desc, claims=None, modalities=None, created=None,
                      mindshare=None, founders=None, perf=None,
                      pros=None, cons=None, links=None,
                      latest_release=None, license_=None, gh=None,
                      hq=None, funding=None, customers=None,
                      pricing=None):
    """For agent-products that PLAY game benchmarks (e.g. ClaudePlaysPokemon).
    Uses TAX_AGENT_PROD — these are agentic systems with session-only memory."""
    fills = {}
    fills["desc"] = real(desc, primary_url)
    fills["claims"] = real(claims, primary_url) if claims else searched(primary_url)
    fills["modalities"] = real(modalities, primary_url) if modalities else searched(primary_url)
    fills["created"] = real(created, primary_url) if created else searched(primary_url)
    fills["latest-release"] = real(latest_release, primary_url) if latest_release else searched(primary_url)
    fills["license"] = real(license_, primary_url) if license_ else NOT_OSS
    fills["gh"] = real(gh, primary_url) if gh else NO_REPO
    fills["mindshare"] = real(mindshare, primary_url) if mindshare else searched(primary_url)
    fills["citations"] = NOT_ACADEMIC
    fills["funding"] = real(funding, primary_url) if funding else NOT_COMMERCIAL
    fills["customers"] = real(customers, primary_url) if customers else NOT_COMMERCIAL
    fills["pricing"] = real(pricing or "not applicable — research demo / community project", primary_url)
    fills["compliance"] = NOT_COMMERCIAL
    fills["data-handling"] = NOT_COMMERCIAL
    fills["deployment"] = real("not applicable — research demo", primary_url)
    fills["hq"] = real(hq, primary_url) if hq else NOT_COMPANY
    fills["founders"] = real(founders, primary_url) if founders else searched(primary_url)
    fills["volume"] = NOT_MEMORY
    fills["perf"] = real(perf, primary_url) if perf else searched(primary_url)
    fills["repro"] = real("Twitch live-stream playthrough provides timestamped reproducibility evidence", primary_url)
    fills["code-release"] = real(license_ if license_ else "Source not released — Twitch livestream + Anthropic blog only", primary_url)
    fills["api-surface"] = NA_EVAL
    fills["latency"] = NA_EVAL
    fills["throughput"] = NA_EVAL
    fills["backend-storage"] = NA_EVAL
    fills["multi-tenancy"] = NA_EVAL
    fills["encryption"] = NA_EVAL
    fills["sso-rbac"] = NA_EVAL
    fills["embedding-model"] = NA_EVAL
    fills["consistency"] = NA_GENERIC
    fills["versioning"] = real("model-version-pinned (e.g. Claude 3.5 Sonnet runs distinct from Claude 4)", primary_url)
    fills["tombstoning"] = NA_GENERIC
    fills["schema-evolution"] = real("not applicable — agent demo, not data product", primary_url)
    fills["namespace"] = NA_GENERIC
    fills["contradiction"] = NA_GENERIC
    fills["forgetting"] = real("session-only — context reset each run", primary_url)
    fills["mcp-support"] = NA_BENCH_HARN
    fills["a2a-support"] = NA_BENCH_HARN
    fills["otel"] = NA_BENCH_HARN
    fills["webhooks"] = NA_BENCH_HARN
    fills["import-export"] = NA_BENCH_HARN
    fills["integration-count"] = NA_WRONG
    fills["orchestration"] = NA_WRONG
    fills["programmatic-control"] = NA_WRONG
    fills["vendor-benchmarks"] = NA_WRONG
    fills["pricing-specifics"] = NA_WRONG
    fills["agent-abstraction"] = NA_WRONG
    fills["memory-primitives"] = NA_WRONG
    fills["llm-lock"] = NA_WRONG
    fills["runtimes"] = NA_WRONG
    fills["session-handling"] = NA_WRONG
    fills["validated-verticals"] = real("agentic gameplay benchmarking", primary_url)
    fills["time-to-running"] = NA_EVAL_NDASH
    fills["anti-fit"] = NA_EVAL_NDASH
    fills["optimised-for"] = real("benchmarking long-horizon agentic capability via game play", primary_url)
    fills["adjacent-infrastructure"] = real("game emulator + screen capture + LLM API", primary_url)
    fills["pros"] = real(pros, primary_url) if pros else searched(primary_url)
    fills["cons"] = real(cons, primary_url) if cons else searched(primary_url)
    fills["links"] = real(links or url.replace("https://", "").replace("http://", ""), primary_url)
    return render_row(tier=tier, name=name, url=url, type_str=type_str,
                      tax=TAX_AGENT_PROD, primary_url=primary_url, fills=fills)


# ============================================================================
# ROW DEFINITIONS — 18 rows
# ============================================================================

ROWS = []

# 1. OSRS Bench — Old School RuneScape agent benchmark
ROWS.append(bench_row(
    tier=4,
    name="OSRS Bench (Old School RuneScape agent benchmark)",
    url="https://github.com/grahamannett/osrs-bench",
    type_str="Long-horizon MMO agent benchmark — Old School RuneScape",
    primary_url="https://github.com/grahamannett/osrs-bench",
    desc=("Community benchmark suite for LLM agents playing Old School RuneScape, a sandbox MMORPG "
          "with deep partial-observability, skill-grinding loops, and economy interaction. Tests "
          "long-horizon planning (hour-to-day quests), tool inventory management, and visual UI "
          "comprehension. Community-built; not affiliated with Jagex."),
    claims=("Used by community as exemplar long-horizon agent task — quest completion times measured "
            "in hours; full account progression measured in months of agent runtime"),
    modalities="visual (game screen) + text (chat / interface)",
    created="2024 (community project)",
    license_="MIT (assumed — community repo, no explicit LICENSE file checked)",
    gh="small community repo (<50★), Python",
    founders="Graham Annett (osrs-bench GitHub author); community contributors",
    pros="One of the few long-horizon (multi-hour to multi-day) agentic benchmarks built around a real, deeply-engineered game world; high partial-observability and economic loops.",
    cons="Niche community benchmark with no standardized leaderboard; reproducibility hampered by Jagex anti-bot policies (RuneScape EULA forbids automation); not peer-reviewed.",
    links="github.com/grahamannett/osrs-bench",
))

# 2. NetHack Learning Environment (NLE)
ROWS.append(bench_row(
    tier=2,
    name="NetHack Learning Environment (NLE)",
    url="https://github.com/heiner/nle",
    type_str="Roguelike RL benchmark — NetHack as agent environment",
    primary_url="https://github.com/heiner/nle",
    desc=("DeepMind / FAIR's NetHack Learning Environment — a Gym-compatible interface to NetHack, "
          "the canonical roguelike. Massive procedural state space, permadeath, deep item / skill "
          "interactions, ASCII partial-observability. Released at NeurIPS 2020; canonical "
          "long-horizon partial-observability RL benchmark."),
    claims=("NeurIPS 2020 paper; >1k stars on GitHub; NetHack Challenge run at NeurIPS 2021. "
            "After 4 years still considered unsolved at expert-human level by autonomous agents."),
    modalities="text/ASCII glyph grid + numeric stats",
    created="2020-06 (Küttler et al. NeurIPS 2020)",
    latest_release="v0.9.x series (active as of 2024)",
    license_="NetHack General Public License",
    gh="1.0k★ Python/C",
    mindshare="canonical roguelike RL benchmark; cited by Dreamer, MuZero, IMPALA follow-ups",
    citations_val="200+ cites — NeurIPS 2020 paper",
    founders="Heinrich Küttler, Nantas Nardelli, Alexander H. Miller, Roberta Raileanu, Marco Selvatici, Edward Grefenstette, Tim Rocktäschel (FAIR / DeepMind)",
    repro="Independently reproduced — community NetHack Challenge 2021",
    code_release="Code public + game-engine source open",
    pros="Massive (10^48+) state space + long horizon (10^4-10^5 steps) makes it one of the hardest RL benchmarks; ASCII representation is interpretable; procedural so memorisation cannot solve it.",
    cons="Sparse reward + dense procedural complexity → RL still hard-stuck at sub-human levels; ASCII-only modality limits transfer to multimodal agents.",
    links="github.com/heiner/nle NeurIPS 2020 paper",
))

# 3. MineRL / Minecraft Diamond Challenge
ROWS.append(bench_row(
    tier=2,
    name="MineRL Diamond Challenge",
    url="https://minerl.io/",
    type_str="Minecraft RL benchmark — obtain a diamond",
    primary_url="https://minerl.io/",
    desc=("MineRL is a research project / competition series using Minecraft as a long-horizon RL "
          "environment. The flagship Diamond Challenge tasks an agent with obtaining a diamond from "
          "raw world — requires deep tech-tree planning across thousands of steps. DreamerV3 (DeepMind, "
          "2023-12) famously became the first to solve it from scratch without human data."),
    claims=("NeurIPS 2019/2020/2021 competitions; DreamerV3 first to solve from scratch (2023-12); "
            "remains a canonical world-model benchmark"),
    modalities="visual (Minecraft screen) + inventory state",
    created="2019 (Guss et al. IJCAI 2019)",
    license_="MIT",
    gh="~700★ Python",
    mindshare="Foundational Minecraft RL benchmark cited by DreamerV3, VPT, Voyager, MineDojo papers",
    citations_val="500+ cites — MineRL paper + Diamond Challenge papers",
    founders="William H. Guss et al. (CMU); MineRL Labs / OpenAI / Microsoft Research collaborators",
    repro="Independently reproduced — DreamerV3 (DeepMind 2023), VPT (OpenAI 2022)",
    code_release="Code public + Minecraft proprietary",
    pros="Real, complex, long-horizon environment; competition history with public leaderboards; visual modality forces realistic perception.",
    cons="Minecraft proprietary licensing complicates redistribution; rewards extremely sparse (~24k steps to first diamond); legacy versions of MC mod required.",
    links="minerl.io GitHub minerllabs/minerl",
))

# 4. MineDojo
ROWS.append(bench_row(
    tier=3,
    name="MineDojo",
    url="https://minedojo.org/",
    type_str="Open-ended Minecraft agent benchmark + knowledge base",
    primary_url="https://minedojo.org/",
    desc=("NVIDIA + Caltech open-ended embodied-agent benchmark on Minecraft. 3000+ programmatic + "
          "creative tasks across survival / harvest / tech-tree / combat / creative. Includes an "
          "internet-scale knowledge base (730K YouTube videos, 7K wiki pages, 340K Reddit posts) "
          "for grounding. Released at NeurIPS 2022 (outstanding paper award)."),
    claims=("NeurIPS 2022 outstanding paper; 3000+ tasks; 730K YouTube videos in knowledge base; "
            "Voyager (2023) built on MineDojo and Reflexion ideas"),
    modalities="visual + text instruction + internet-scale video/wiki knowledge",
    created="2022-06 (Fan et al. NeurIPS 2022)",
    license_="MIT (env wrapper); Mojang EULA on Minecraft",
    gh="2.4k★ Python",
    mindshare="Cited by Voyager (auto-curriculum agent), VPT, GITM; canonical Minecraft open-ended benchmark",
    citations_val="600+ cites — Fan et al. NeurIPS 2022 outstanding paper",
    founders="Linxi 'Jim' Fan, Guanzhi Wang, Yunfan Jiang, Ajay Mandlekar, Yuncong Yang, Haoyi Zhu, Andrew Tang, De-An Huang, Yuke Zhu, Anima Anandkumar (NVIDIA, Caltech, Stanford, UT Austin)",
    repro="Independently reproduced — Voyager (Wang et al. 2023), GITM",
    code_release="Code public + Minecraft proprietary + knowledge base public",
    pros="Open-ended task space (3000+ tasks) rather than single objective; bundled internet-scale knowledge base; outstanding-paper recognition at NeurIPS 2022.",
    cons="Built on Malmo (older Minecraft interface) — limits transfer to current MC versions; knowledge base quality is web-scrape level.",
    links="minedojo.org GitHub MineDojo/MineDojo NeurIPS 2022 paper",
))

# 5. Crafter (Hafner)
ROWS.append(bench_row(
    tier=3,
    name="Crafter",
    url="https://github.com/danijar/crafter",
    type_str="Minecraft-inspired 2D RL benchmark with 22 achievements",
    primary_url="https://github.com/danijar/crafter",
    desc=("Danijar Hafner's 2D Minecraft-inspired benchmark — open-world survival with 22 hierarchical "
          "achievements (collect wood → make pickaxe → mine stone → ... → collect diamond). "
          "Procedurally-generated 64x64 grid world; tests long-horizon planning, exploration, "
          "credit assignment. Lightweight (single Python file) — designed as 'inner-loop Minecraft' "
          "for fast iteration. Used as flagship benchmark for DreamerV2/V3."),
    claims=("Authored by DreamerV3's Hafner; canonical companion benchmark for world-model RL; "
            "lightweight enough to run on a single GPU."),
    modalities="visual (64x64 RGB grid)",
    created="2021-09 (Hafner arXiv 2109.06780)",
    license_="MIT",
    gh="500★ Python",
    mindshare="Companion benchmark to DreamerV2/V3; used widely in world-model RL research",
    citations_val="200+ cites — Crafter benchmark paper",
    founders="Danijar Hafner (DeepMind / Toronto)",
    repro="Independently reproduced — used in DreamerV3, IRIS, TWM papers",
    code_release="Code public + game-engine source open",
    pros="Lightweight enough to iterate fast (minutes per agent run); 22-achievement hierarchy gives interpretable progress signal; canonical for world-model RL research.",
    cons="2D + small grid limits transfer to richer environments; only 22 achievements caps task ceiling; less brand recognition than 3D Minecraft benchmarks.",
    links="github.com/danijar/crafter arxiv 2109.06780",
))

# 6. TextWorld (Microsoft)
ROWS.append(bench_row(
    tier=3,
    name="TextWorld",
    url="https://github.com/microsoft/TextWorld",
    type_str="Text-adventure RL benchmark — procedurally-generated IF games",
    primary_url="https://github.com/microsoft/TextWorld",
    desc=("Microsoft Research's TextWorld — a sandbox for training and evaluating RL agents on "
          "text-based games. Procedurally generates interactive-fiction games of tunable difficulty "
          "(map size, quest length, ingredients) with full ground-truth knowledge graphs. Used as "
          "the basis for the FirstTextWorld and TextWorld Challenge competitions."),
    claims=("Microsoft Research; ICML 2018; ground-truth KG for every generated game enables "
            "ablation studies on memory architectures"),
    modalities="text only (natural-language IF games)",
    created="2018-06 (Côté et al. arXiv 1806.11532)",
    license_="MIT",
    gh="1.3k★ Python",
    mindshare="Microsoft Research; standard benchmark for text-adventure agent research",
    citations_val="500+ cites — Côté et al. CGW@IJCAI 2018",
    founders="Marc-Alexandre Côté, Ákos Kádár, Xingdi Yuan, Ben Kybartas, Tavian Barnes, Emery Fine, James Moore, Matthew Hausknecht, Layla El Asri, Mahmoud Adada, Wendy Tay, Adam Trischler (Microsoft Research Montreal)",
    repro="Independently reproduced — FirstTextWorld Challenge winners",
    code_release="Code public",
    pros="Procedural generation gives unlimited variants; ground-truth KGs enable rigorous memory-architecture evaluation; lightweight (text-only).",
    cons="Pure text limits transfer to embodied agents; quest structures simpler than human-authored IF; less popular post-LLM-era (LLMs nearly solve handcrafted IF zero-shot).",
    links="github.com/microsoft/TextWorld arxiv 1806.11532",
))

# 7. Atari 100k (sample-efficient RL benchmark)
ROWS.append(bench_row(
    tier=3,
    name="Atari 100k",
    url="https://arxiv.org/abs/1903.00374",
    type_str="Sample-efficient RL benchmark — 100k env steps on Atari",
    primary_url="https://arxiv.org/abs/1903.00374",
    desc=("Sample-efficiency benchmark protocol on Arcade Learning Environment (ALE) — agents "
          "limited to 100k environment steps (~2 hours of game-play) before evaluation. Introduced "
          "by SimPLe (Kaiser et al. 2019) and adopted by EfficientZero, IRIS, BBF, DreamerV3, "
          "Storm. Tests world-model / model-based methods where memory-as-imagination matters more "
          "than huge replay buffers."),
    claims=("De-facto standard sample-efficient RL benchmark; canonical for world-model RL "
            "methods (DreamerV3 SOTA 2023; BBF surpasses human in 2023)"),
    modalities="visual (Atari pixel frames) — 26 game subset typical",
    created="2019-03 (Kaiser et al. SimPLe paper, ICLR 2020)",
    license_="GPL-2.0 (ALE)",
    gh="2.3k★ C++ (ALE / atari-py)",
    mindshare="Adopted by EfficientZero, DreamerV3, IRIS, BBF, Storm, SR-SPR — canonical for sample-efficient RL papers",
    citations_val="800+ cites — SimPLe paper (Kaiser et al.) introduced the 100k protocol",
    founders="Lukasz Kaiser, Mohammad Babaeizadeh, Piotr Milos, et al. (Google Brain / U Warsaw / DeepMind)",
    repro="Independently reproduced — multiple SOTA papers reference the protocol",
    code_release="Code public (ALE / atari-py)",
    pros="Tight sample budget (100k steps ≈ 2 hours) makes world-model methods competitive; long-established protocol with rich SOTA history.",
    cons="Atari games are short-horizon arcade tasks — not really 'memory' benchmarks; results often overfit the 26-game subset selection.",
    links="arxiv 1903.00374 ALE github",
))

# 8. PROCGEN
ROWS.append(bench_row(
    tier=3,
    name="PROCGEN benchmark suite",
    url="https://github.com/openai/procgen",
    type_str="Procedurally-generated RL game suite — generalisation eval",
    primary_url="https://github.com/openai/procgen",
    desc=("OpenAI's 16-game procedurally-generated benchmark for evaluating RL generalisation. "
          "Unlike Atari (fixed levels memorisable), every PROCGEN episode uses a different procedural "
          "seed → test-set generalisation is the headline metric. Released at ICML 2020. Standard "
          "benchmark for studying generalisation, exploration, transfer."),
    claims=("ICML 2020; 16 procedurally-generated games; standard for RL generalisation research; "
            "used by IMPALA, PPG, DAAC, IDAAC follow-ups"),
    modalities="visual (procedural 2D game frames, 64x64)",
    created="2019-12 (Cobbe et al. arXiv 1912.01588)",
    license_="MIT",
    gh="980★ Python/C",
    mindshare="Standard RL generalisation benchmark cited by hundreds of follow-up papers",
    citations_val="700+ cites — Cobbe et al. ICML 2020",
    founders="Karl Cobbe, Christopher Hesse, Jacob Hilton, John Schulman (OpenAI)",
    repro="Independently reproduced — multiple SOTA papers",
    code_release="Code public",
    pros="Procedural seed-train / seed-test split rigorously isolates generalisation from memorisation; lightweight (16 fast games).",
    cons="2D platformer style limits transfer to richer 3D / embodied; PROCGEN-shaped overfitting is a known critique.",
    links="github.com/openai/procgen arxiv 1912.01588",
))

# 9. Hanabi Learning Environment
ROWS.append(bench_row(
    tier=3,
    name="Hanabi Learning Environment",
    url="https://github.com/google-deepmind/hanabi-learning-environment",
    type_str="Cooperative multi-agent partial-observability card-game benchmark",
    primary_url="https://github.com/google-deepmind/hanabi-learning-environment",
    desc=("DeepMind's Hanabi Learning Environment — a benchmark for cooperative multi-agent agents "
          "under partial observability and theory-of-mind. Players see each other's cards but not "
          "their own; success requires modeling teammates' beliefs. Bard (Bowling et al. 2020) "
          "described Hanabi as 'a new frontier for AI research'. Used in OpenAI ad hoc team-play "
          "papers and DeepMind's Bayesian Action Decoder."),
    claims=("Bowling et al. 2020 — described Hanabi as 'new frontier for AI'; canonical "
            "cooperative-MARL benchmark; ad-hoc team-play benchmark used by Strouse et al. 2021"),
    modalities="discrete game state (card observability)",
    created="2019-02 (Bard et al. arXiv 1902.00506)",
    license_="Apache-2.0",
    gh="700★ C++/Python",
    mindshare="Canonical cooperative-MARL + theory-of-mind benchmark",
    citations_val="800+ cites — Bard et al. AIJ 2020",
    founders="Nolan Bard, Jakob Foerster, Sarath Chandar, Neil Burch, Marc Lanctot, H. Francis Song, Emilio Parisotto, et al. (DeepMind)",
    repro="Independently reproduced — multiple cooperative-MARL papers",
    code_release="Code public",
    pros="Tests cooperation + partial-observability + theory-of-mind simultaneously; cooperative-only (no zero-sum complication); strong DeepMind pedigree.",
    cons="Discrete card-game scope limits visual-perception relevance; performance ceilings against expert humans not yet reached.",
    links="github.com/google-deepmind/hanabi-learning-environment arxiv 1902.00506",
))

# 10. OpenAI Gym Retro (arcade game agents)
ROWS.append(bench_row(
    tier=3,
    name="OpenAI Gym Retro",
    url="https://github.com/openai/retro",
    type_str="Retro arcade RL benchmark — Sega / NES / SNES game integration",
    primary_url="https://github.com/openai/retro",
    desc=("OpenAI's Gym Retro — wraps thousands of classic arcade games (Sega Genesis, NES, SNES, "
          "Atari 2600, Game Boy) as Gym RL environments via libretro emulators. Released 2018; "
          "powered the OpenAI Retro Contest where agents had to generalise from train-set games "
          "to held-out levels of Sonic. Largely supplanted by Atari 100k / Procgen / etc. but still "
          "the most-popular path for adding arbitrary retro games to RL pipelines."),
    claims=("OpenAI 2018; powered Retro Contest 2018 (Sonic generalisation); 1000+ supported "
            "games; canonical entry-point for libretro-emulator RL"),
    modalities="visual (retro arcade frames)",
    created="2018-05 (Nichol et al. arXiv 1804.03720)",
    license_="MIT",
    gh="3.5k★ Python/C",
    mindshare="OpenAI Retro Contest was a high-profile community competition; deprecated in 2020 but still in use",
    citations_val="200+ cites — Nichol et al. arxiv",
    founders="Alex Nichol, Vicki Pfau, Christopher Hesse, Oleg Klimov, John Schulman (OpenAI)",
    repro="Independently reproduced — Retro Contest 2018 had public leaderboard",
    code_release="Code public + game ROMs require user-supply",
    pros="Largest catalog of retro games as RL environments (1000+); libretro-backed → broad emulator coverage; canonical for arcade-RL.",
    cons="No longer actively maintained by OpenAI (2020 deprecation); ROM legalities limit redistribution; outclassed by Atari 100k / Procgen for generalisation eval.",
    links="github.com/openai/retro Retro Contest 2018 arxiv 1804.03720",
))

# 11. Habitat 3.0 social agents
ROWS.append(bench_row(
    tier=3,
    name="Habitat 3.0 (social agents)",
    url="https://aihabitat.org/habitat3/",
    type_str="Embodied human-robot social interaction benchmark",
    primary_url="https://aihabitat.org/habitat3/",
    desc=("Meta AI's Habitat 3.0 — extends Habitat 2.0 with avatar humans, social tasks "
          "(navigate-while-following, rearrangement-while-not-blocking), and human-robot collaboration "
          "evaluation. Foundational for embodied social-agent research; supports both "
          "learned and scripted human avatars; SOTA realistic 3D scanned scenes (HM3D, Replica)."),
    claims=("ICLR 2024; first embodied social-agent benchmark at scale; supports human-avatars + "
            "robot agents in shared 3D scenes"),
    modalities="visual (3D rendered) + depth + collision + speech (avatar)",
    created="2023-10 (Puig et al. arXiv 2310.13724)",
    license_="MIT (Habitat-Lab); CC-BY-NC (3D scenes)",
    gh="2.6k★ Python/C++",
    mindshare="Meta AI flagship embodied-AI platform; cited by HomeRobot, OK-Robot, social-eval papers",
    citations_val="100+ cites — Habitat 3.0 ICLR 2024 paper",
    founders="Xavi Puig, Eric Undersander, Andrew Szot, Mikael Henaff, et al. (Meta AI FAIR)",
    repro="Independently reproduced — HomeRobot, OVMM follow-ups",
    code_release="Code public + datasets public",
    pros="Realistic 3D scanned environments; only major embodied-social-agent benchmark at scale; Meta AI active maintainer.",
    cons="Scene licensing complex (CC-BY-NC); GPU-heavy to run; social-task benchmarks still maturing.",
    links="aihabitat.org/habitat3 GitHub facebookresearch/habitat-lab arxiv 2310.13724",
))

# 12. AndroidEnv / AndroidWorld
ROWS.append(bench_row(
    tier=3,
    name="AndroidWorld",
    url="https://github.com/google-research/android_world",
    type_str="Mobile-OS agent benchmark — 116 real Android app tasks",
    primary_url="https://github.com/google-research/android_world",
    desc=("Google DeepMind's AndroidWorld — 116 hand-crafted tasks across 20 real Android apps "
          "(Calendar, Files, Markor, Tasks, etc.). Evaluates LLM agents controlling a real Android "
          "device via accessibility APIs. Distinct from AndroidEnv (RL-environment) — AndroidWorld "
          "is the benchmark suite. Released 2024; SOTA agent (M3A with GPT-4) at ~30% task success."),
    claims=("Google DeepMind 2024; 116 tasks across 20 real apps; SOTA ~30% success on multi-app "
            "compositional tasks; successor to AndroidEnv (RL environment)"),
    modalities="visual (Android screen) + accessibility tree + text",
    created="2024-05 (Rawles et al. arXiv 2405.14573)",
    license_="Apache-2.0",
    gh="1.2k★ Python",
    mindshare="Standard benchmark for mobile-agent / device-control research; cited by M3A, AppAgent, MobileAgent follow-ups",
    citations_val="50+ cites — AndroidWorld paper (2024)",
    founders="Christopher Rawles, Alice Li, Daniel Rodriguez, Oriana Riva, Timothy Lillicrap (Google DeepMind)",
    repro="Independently reproduced — M3A, AppAgent-v2 evaluations",
    code_release="Code public",
    pros="Real Android apps (not simulated) with reliable evaluation harness; broad app coverage; reproducible auto-grading.",
    cons="Android-only (no iOS); SOTA still ~30% — long way from human-comparable; setup heavier than synthetic benchmarks.",
    links="github.com/google-research/android_world arxiv 2405.14573",
))

# 13. WebArena
ROWS.append(bench_row(
    tier=3,
    name="WebArena",
    url="https://webarena.dev/",
    type_str="Web-agent benchmark — 812 tasks across 6 self-hosted sites",
    primary_url="https://webarena.dev/",
    desc=("CMU's WebArena — 812 hand-crafted web tasks across 6 self-hosted reproductions of real "
          "websites (Reddit-clone Postmill, GitLab, OneStopShop, CMS, Map, Wikipedia). Released ICLR 2024. "
          "Distinct from Mind2Web (real-website screenshots) — WebArena is fully reproducible with "
          "Docker-deployable backends. Spawned VisualWebArena, WorkArena, and dozens of agent benchmarks."),
    claims=("ICLR 2024; 812 reproducible web tasks; SOTA (Claude 3.5 Sonnet) ~36% success as of 2024; "
            "parent of VisualWebArena, WorkArena, etc."),
    modalities="visual (web page) + accessibility tree + DOM",
    created="2023-07 (Zhou et al. arXiv 2307.13854)",
    license_="Apache-2.0",
    gh="1.2k★ Python",
    mindshare="Most-cited reproducible web-agent benchmark; parent of VisualWebArena, WorkArena lineage",
    citations_val="300+ cites — Zhou et al. ICLR 2024",
    founders="Shuyan Zhou, Frank F. Xu, Hao Zhu, Xuhui Zhou, Robert Lo, Abishek Sridhar, Xianyi Cheng, Yonatan Bisk, Daniel Fried, Uri Alon, Graham Neubig (CMU)",
    repro="Independently reproduced — extensive SOTA-tracker leaderboard",
    code_release="Code public + Docker images for all 6 sites",
    pros="Fully reproducible (Docker self-hosted) — eliminates web-site-drift problem of real-site benchmarks; broad task coverage; active leaderboard.",
    cons="SOTA still ~36% — gap to human (~78%) remains large; self-hosted sites are simplified vs real production sites.",
    links="webarena.dev arxiv 2307.13854 github web-arena-x/webarena",
))

# 14. OSWorld
ROWS.append(bench_row(
    tier=3,
    name="OSWorld",
    url="https://os-world.github.io/",
    type_str="Desktop OS agent benchmark — 369 tasks across Ubuntu / Windows / macOS",
    primary_url="https://os-world.github.io/",
    desc=("HKU NLP + Salesforce's OSWorld — full-desktop agent benchmark with 369 tasks spanning "
          "real applications (LibreOffice, GIMP, Chrome, VS Code, Thunderbird, Files) across Ubuntu, "
          "Windows, and macOS. Tasks require multi-application workflows; evaluation via post-task "
          "state inspection (not just screenshot match). Released NeurIPS 2024."),
    claims=("NeurIPS 2024; 369 real-OS tasks across 3 operating systems; SOTA (Claude 3.5 Sonnet + Anthropic Computer Use) ~22% success"),
    modalities="visual (full desktop screenshot) + accessibility tree + multi-application state",
    created="2024-04 (Xie et al. arXiv 2404.07972)",
    license_="Apache-2.0",
    gh="1.7k★ Python",
    mindshare="Canonical computer-use benchmark; tracked by OpenAI Operator, Anthropic Computer Use, Google Project Mariner",
    citations_val="100+ cites — Xie et al. NeurIPS 2024",
    founders="Tianbao Xie, Danyang Zhang, Jixuan Chen, Xiaochuan Li, Siheng Zhao, Ruisheng Cao, Toh Jing Hua, Zhoujun Cheng, Dongchan Shin, Fangyu Liu, et al. (HKU + Salesforce Research)",
    repro="Independently reproduced — OpenAI Operator and Anthropic Computer Use both publish OSWorld scores",
    code_release="Code public + VM images public",
    pros="Multi-OS (Linux + Windows + macOS) coverage unique among OS benchmarks; real apps; state-based evaluation more robust than screenshot match.",
    cons="VM setup is heavyweight (gigabytes); SOTA still ~22% — long horizon to human parity; OSWorld game tasks (per spec) are not the focus — productivity apps dominate.",
    links="os-world.github.io arxiv 2404.07972 github xlang-ai/OSWorld",
))

# 15. SmartPlay
ROWS.append(bench_row(
    tier=3,
    name="SmartPlay",
    url="https://github.com/Microsoft/SmartPlay",
    type_str="LLM-agent benchmark across 6 games — Microsoft Research",
    primary_url="https://github.com/Microsoft/SmartPlay",
    desc=("Microsoft Research's SmartPlay — LLM-agent benchmark on 6 games (Bandits, Rock-Paper-Scissors, "
          "Tower of Hanoi, MessengerEnv, Crafter, Minecraft). Tests 9 distinct capability axes including "
          "object understanding, planning, generalisation, error-handling, theory-of-mind. ICLR 2024. "
          "Bridges narrow-task benchmarks (MMLU) and full-agent benchmarks (AgentBench)."),
    claims=("ICLR 2024; 9 capability axes evaluated across 6 games; GPT-4 SOTA at time of release"),
    modalities="text-converted game state (LLM-interfacing layer)",
    created="2023-10 (Wu et al. arXiv 2310.01557)",
    license_="MIT",
    gh="170★ Python",
    mindshare="Microsoft Research; one of the few systematic LLM-agent-vs-games benchmarks",
    citations_val="80+ cites — Wu et al. ICLR 2024",
    founders="Yue Wu, Xuan Tang, Tom M. Mitchell, Yuanzhi Li (Microsoft Research / CMU)",
    repro="Independently reproduced — multiple LLM-agent papers cite results",
    code_release="Code public",
    pros="9 capability axes give finer-grained agent capability picture than single-task benchmarks; lightweight (LLM-interface, not full RL).",
    cons="Text-only LLM interface bypasses perception; 6-game set is narrow; ICLR 2024 already feels dated vs newer agent benchmarks.",
    links="github.com/Microsoft/SmartPlay arxiv 2310.01557",
))

# 16. BALROG
ROWS.append(bench_row(
    tier=4,
    name="BALROG",
    url="https://balrogai.com/",
    type_str="LLM/VLM agent benchmark on 6 challenging game environments",
    primary_url="https://balrogai.com/",
    desc=("BALROG (Benchmarking Agentic LLM and VLM Reasoning on Games) — 2024 benchmark suite "
          "covering NetHack, BabyAI, Crafter, MiniHack, TextWorld, Baba Is AI. Specifically targets "
          "long-horizon, partial-observability, exploration-heavy games where memory and planning "
          "matter. SOTA GPT-4o and Claude 3.5 Sonnet both score <25% on aggregate. Released by "
          "AI Safety Institute UK + Cambridge collaborators."),
    claims=("2024 ICLR-track preprint; SOTA <25% — frontier models all struggle on long-horizon games; "
            "6 environments selected for memory / planning / partial-observability"),
    modalities="text + visual (varies by game)",
    created="2024-11 (Paglieri et al. arXiv 2411.13543)",
    license_="MIT",
    gh="200★ Python",
    mindshare="Active 2024-2025 benchmark; tracks frontier LLM progress on agentic-games",
    citations_val="20+ cites — Paglieri et al. preprint",
    founders="Davide Paglieri, Bartłomiej Cupiał, Samuel Coward, Ulyana Piterbarg, Maciej Wolczyk, Akbir Khan, et al. (AISI UK + Cambridge + collaborators)",
    repro="Independently reproduced — leaderboard active",
    code_release="Code public",
    pros="Specifically designed for memory + long-horizon + partial-observability evaluation; active leaderboard tracks frontier models monthly; six diverse environments.",
    cons="Recent (2024-11) — limited follow-up adoption yet; aggregate SOTA still very low → high noise in evaluation.",
    links="balrogai.com arxiv 2411.13543 github balrog-ai/BALROG",
))

# 17. Pokemon Red benchmark (academic + community)
ROWS.append(bench_row(
    tier=4,
    name="Pokemon Red benchmark (speedrun / completion)",
    url="https://github.com/PWhiddy/PokemonRedExperiments",
    type_str="Pokemon Red completion benchmark — long-horizon JRPG agent task",
    primary_url="https://github.com/PWhiddy/PokemonRedExperiments",
    desc=("Pokemon Red has emerged as a community + academic benchmark for long-horizon agentic AI. "
          "Notable instances: Peter Whiddy's PokemonRedExperiments (RL via PPO + curiosity, viral "
          "YouTube series 2023); Anthropic's ClaudePlaysPokemon Twitch stream (2025-02); Google's "
          "GeminiPlaysPokemon (2025); MorphLabs PokemonRedRL. The benchmark protocol varies: badge "
          "count, gym progression, full Elite-Four completion. Common across all: ~5k-20k+ step "
          "horizon, sparse rewards, deep partial-observability."),
    claims=("Anthropic ClaudePlaysPokemon: 2/8 badges over ~80hr (Claude 3.7 Sonnet, Feb 2025); "
            "Google Gemini 2.5 Pro reportedly completed full game; Whiddy's PPO+curiosity RL "
            "completed up to Pewter Gym; viral mindshare via Twitch livestreams"),
    modalities="visual (Game Boy emulator frames) + memory-state introspection",
    created="2023-09 (Whiddy YouTube + GitHub release)",
    license_="MIT (Whiddy repo)",
    gh="7.6k★ Python (PokemonRedExperiments)",
    mindshare="Anthropic ClaudePlaysPokemon Twitch viral 2025; ~7.6k stars on Whiddy repo; key public spectacle for long-horizon LLM-agent capability",
    citations_val="20+ cites — academic Pokemon-Red papers (Whiddy preprint, RL follow-ups)",
    founders="Peter Whiddy (independent); Anthropic team (ClaudePlaysPokemon); Google DeepMind (GeminiPlaysPokemon)",
    repro="Independently reproduced — multiple labs (Anthropic, Google, MorphLabs) running variants",
    code_release="Code public (Whiddy repo) + ROM user-supplied",
    pros="Most-watched public AI-agent benchmark via Twitch streams; ~hours-to-days horizon stresses long-horizon planning; deeply community-engaging; multiple frontier labs racing on it.",
    cons="No standardized scoring protocol (badge-count vs completion vs speed); Game Boy ROM legality issues; Twitch streams not always reproducible at the playthrough level.",
    links="github.com/PWhiddy/PokemonRedExperiments Anthropic ClaudePlaysPokemon Twitch GeminiPlaysPokemon",
))

# 18. ClaudePlaysPokemon (Anthropic agent product)
ROWS.append(agent_product_row(
    tier=2,
    name="Claude Plays Pokemon (Anthropic)",
    url="https://www.twitch.tv/claudeplayspokemon",
    type_str="Anthropic agent demo — Claude 3.7/4 Sonnet plays Pokemon Red on Twitch",
    primary_url="https://www.twitch.tv/claudeplayspokemon",
    desc=("Anthropic's public Twitch livestream of Claude (3.7 Sonnet → Claude 4 Opus) playing "
          "Pokemon Red. Agent uses screenshot vision + Game Boy controller actions + a scratchpad "
          "memory file the model can edit. Demonstrates long-horizon agentic capability publicly; "
          "ran continuously from Feb 2025; viewed by hundreds of thousands cumulatively; key data "
          "point for Anthropic's marketing around Claude as a long-horizon agent."),
    claims=("Anthropic-run Twitch stream Feb 2025 onwards; Claude 3.7 Sonnet reached Mt. Moon / "
            "2 badges over ~80hr; later runs with Claude 4 Opus reached deeper progress; one of "
            "the most-watched public LLM-agent demos of 2025"),
    modalities="visual (Game Boy emulator frames) + scratchpad text memory",
    created="2025-02 (Anthropic livestream launch)",
    latest_release="Twitch livestream ongoing; runs distinct per Claude model version",
    mindshare="Major Anthropic 2025 marketing moment; trended on HN, Twitter; viewed by 100k+ cumulatively on Twitch",
    founders="Anthropic — David Hershey is publicly credited as the engineer behind the demo",
    perf="Reached Lavender Town / ~3 badges over ~100+ hour Claude 4 Opus run (2025-05); Claude 3.7 Sonnet stalled around Mt. Moon",
    pros="Public, observable, real-time evidence of long-horizon LLM-agent capability; high mindshare; live discussion of failure modes (loops, forgetting, hallucinating items).",
    cons="Closed agent harness (Anthropic-internal); not reproducible by third parties; benchmark protocol informal — no standardized scoring.",
    hq="San Francisco, US",
    links="twitch.tv/claudeplayspokemon David Hershey threads",
))


# ============================================================================
# EMIT
# ============================================================================

def main():
    out = []
    # The subsection group-row
    out.append('  <tr class="group-row"><td colspan="92" style="padding-left: 28px; text-transform: none; letter-spacing: 0.04em; color: #b8b8b8;">— Game / interactive-environment benchmarks</td></tr>')
    out.append('')
    out.append('  <tr class="section-explainer"><td colspan="92"><div class="explainer-text">Game and interactive-environment benchmarks for agentic AI — distinct from the academic-benchmark cohort (LongMemEval / LoCoMo / GAIA / ALFWorld) by being play-shaped, long-horizon (hours to days of agent runtime), partial-observability, and often community-built. NetHack / Minecraft / Pokemon / Atari sit alongside web/mobile/desktop agent benchmarks (WebArena, OSWorld, AndroidWorld) — all share long-horizon, partial-observability, agentic-by-construction structure. Includes both OSS / community benchmarks AND known agent-plays-game products (Claude Plays Pokemon).</div></td></tr>')
    out.append('')
    for r in ROWS:
        out.append(r)
        out.append('')
    print('\n'.join(out))


if __name__ == "__main__":
    main()
