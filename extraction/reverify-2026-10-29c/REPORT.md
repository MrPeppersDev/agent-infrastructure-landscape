# Leads from the gap-filling pass — 2026-10-29 (c)

Targets: 25 rows with leads found while filling locus and positioning cells (`extraction/gaps-2026-10-29/REPORT.md`). 24 are verified. There are 17 cell updates, 4 URL moves and 1 rename, plus one manual fix (below). Applied with `apply_reverify.py --date 2026-10-29`; the per-row output is in `apply-report.md`.

## Corrections
- **OpenMemory MCP is now hosted only.** Mem0's MCP docs say "Nothing runs on your machine: the server is hosted by Mem0", and the `openmemory/` folder is gone from mem0ai/mem0. Updated: desc, gh, and the `type` cell ("Local Postgres + Qdrant" → "Mem0-hosted MCP memory server"). `type` was set by hand, because `apply_reverify` only writes the six re-verify cells; its provenance points here. [Mem0 docs](https://docs.mem0.ai/platform/mem0-mcp)
- **Mem0 Security / OpenMemory:** self-hosting is now the Mem0 OSS server. The row URL moves to trust.mem0.ai, where mem0.ai/security now redirects.
- **OpenAI Operator → deprecated.** Its successor is ChatGPT agent, launched 2025-07-17 per OpenAI's news feed. operator.chatgpt.com now redirects to ChatGPT agent mode.
- **Enkrypt AI → acquired by Anaconda** (2026-08-04). [Anaconda](https://www.anaconda.com/blog/anaconda-acquires-enkrypt-ai)
- **Sweep AI → deprecated.** The successor is its JetBrains plugin (Marketplace id 26860, v1.29.3, 2026-02-05). sweep.dev no longer resolves.
- **Litera AI → renamed "Litera AI (now Lito)".** Litera brands its AI agent as Lito across its site. No page states a formal rename, so confidence is medium.
- **Desc and pricing updates:**
  - BenevolentAI now sells Qor.
  - FutureHouse spun out Edison Scientific (2025), and its platform now redirects there.
  - 01.AI's international API is suspended.
  - Cellon: memory.inc redirects to Pogl.
  - The Hyperproof AI Trust Center page is gone; trust features now sit under "Trust".
  - Continue Memory MCP is discontinued: hub.continue.dev is gone and billing is refunded.
- **OctoAI:** latest-release is now SDK 1.11.0 (2024-09-18). The acquisition evidence is only the redirect to nvidia.com, because NVIDIA never announced the deal.

## Confirmed, no change
Limitless (Meta), Bee (Amazon), TruEra (Snowflake), Robust Intelligence (Cisco), SnapAttack (Cisco), Protect AI (Palo Alto Networks), Continue.dev and its rules docs, Tana, Sajari / Search.io, Backboard (the URL moves to its API product page).

## Open
- **Adept:** adept.ai serves a bot challenge to scripts, so it was not verified.
- **Cellon (Memory.inc):** the row URL is a news article, and no primary page for a memory product remains. It is a removal candidate if nothing turns up.
