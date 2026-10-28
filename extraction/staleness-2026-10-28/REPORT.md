# Issue triage 2026-10-28

## Staleness bot
`scripts/check_staleness.py` now also skips:
- **Papers:** records whose URL is a paper host (arXiv, OpenReview, ACL Anthology, NeurIPS) or whose id is an `--arxiv-` record. A finished paper's repo going quiet isn't a lifecycle event.
- **Recorded lifecycle:** rows whose `data/stack-index.json` status is already non-active (maintenance, stale, deprecated, archived, acquired, …). A closed issue on such a row would otherwise just be reopened next week.

An offline dry run clears 16 of the 19 open stale-row issues. The remaining 3 (and the repos only online mode flags) were checked on GitHub and their rows updated (`result-stale-rows.json`):

| Row | Repo status (GitHub, 2026-10-28) |
|---|---|
| Bolt.new (both rows) | stackblitz/bolt.new last pushed 2024-12, not archived; hosted product live |
| mcp-memory (Puliczek) | last pushed 2025-04 |
| Claude-CursorMemoryMCP | last commit 2025-05-27 |
| GWM (Gaussian World Models) | ICCV'25 research code, last pushed 2025-10 |
| UI-TARS | UI-TARS last pushed 2026-01; UI-TARS-desktop 2026-10 (active) |
| Second Me | last pushed 2025-09 |

## Release watch
- **GPT family row:** `latest-release` now lists GPT-6.1 Terra (2026-10-26) and GPT-6.1 Sol, from OpenAI's own news feed (openai.com pages return 403 to this environment; the RSS feed doesn't). Covers #266 and #267.
- **No catalog change:**
  - #268 (Greptile) and #287 (Anima) are customer stories.
  - #288 is a regional rollout of Meta Muse.
- **Out of scope:**
  - #221 (NVIDIA Minerva) is data-center observability.
  - #220 is a game-streaming launch.
  - #246 is a forum admin tool.

## Capability snapshots
`scripts/capability_rebaseline.py` now closes older open `phase-2-rebaseline` issues when it opens a new one, so only the latest weekly snapshot stays open.
# Re-verification 2026-10-28

- rows seen: 8
- rows verified: 8
- cells applied: 8
- cells skipped: 0
- decayed: 0
- renamed: 0
- url changed: 0
- taxonomy set: 0

## Lifecycle changes found

- **Claude-CursorMemoryMCP** — maintenance: Repo's latest commit is 2025-05-27; not archived; 4 stars. ([source](https://github.com/Angleito/Claude-CursorMemoryMCP/commits))
- **GWM (Gaussian World Models)** — maintenance: ICCV'25 research code; repo last pushed 2025-10-13; not archived. ([source](https://github.com/Gaussian-World-Model/gaussianwm))
- **Second Me (Mindverse)** — maintenance: Repo last pushed 2025-09-30; not archived. ([source](https://github.com/mindverse/Second-Me))
- **mcp-memory (Puliczek)** — maintenance: Repo last pushed 2025-04-24 (created the day before); not archived. ([source](https://github.com/Puliczek/mcp-memory))
