# Round 16 — game and interactive-environment benchmarks (2026-05-13)

**Issue**: #31 — *Ingestion: game and interactive-environment benchmarks
(OSRS, Pokemon, NetHack, etc.)*

**Goal**: Catalog the under-represented family of game and
interactive-environment benchmarks used to evaluate agentic capability.
Distinct from the academic-benchmark cohort (LongMemEval / LoCoMo /
GAIA / ALFWorld) — these are play-shaped, long-horizon, often
community-built.

## Section placement

NEW subsection **"— Game / interactive-environment benchmarks"** under
existing **"Memory benchmarks & evaluation"** section. *Not* a new
top-level section — game benchmarks share the static-read-only evaluation
shape with BABILong / HELMET / LongMemEval, so they nest under the same
parent.

This is the **first ever subsection** under "Memory benchmarks &
evaluation". Required updating `scripts/extract.py:SECTIONS_WITH_SUBS`
to permit it.

## Rows shipped: 18

| # | Name | Tier | Primary URL |
|---|------|------|-------------|
| 1 | OSRS Bench (Old School RuneScape agent benchmark) | 4 | https://github.com/grahamannett/osrs-bench |
| 2 | NetHack Learning Environment (NLE) | 2 | https://github.com/heiner/nle |
| 3 | MineRL Diamond Challenge | 2 | https://minerl.io/ |
| 4 | MineDojo | 3 | https://minedojo.org/ |
| 5 | Crafter | 3 | https://github.com/danijar/crafter |
| 6 | TextWorld | 3 | https://github.com/microsoft/TextWorld |
| 7 | Atari 100k | 3 | https://arxiv.org/abs/1903.00374 |
| 8 | PROCGEN benchmark suite | 3 | https://github.com/openai/procgen |
| 9 | Hanabi Learning Environment | 3 | https://github.com/google-deepmind/hanabi-learning-environment |
| 10 | OpenAI Gym Retro | 3 | https://github.com/openai/retro |
| 11 | Habitat 3.0 (social agents) | 3 | https://aihabitat.org/habitat3/ |
| 12 | AndroidWorld | 3 | https://github.com/google-research/android_world |
| 13 | WebArena | 3 | https://webarena.dev/ |
| 14 | OSWorld | 3 | https://os-world.github.io/ |
| 15 | SmartPlay | 3 | https://github.com/Microsoft/SmartPlay |
| 16 | BALROG | 4 | https://balrogai.com/ |
| 17 | Pokemon Red benchmark (speedrun/completion) | 4 | https://github.com/PWhiddy/PokemonRedExperiments |
| 18 | Claude Plays Pokemon (Anthropic) | 2 | https://www.twitch.tv/claudeplayspokemon |

## Coverage approach

The 18 rows cover ~16 of the ~19 seed-list items in the issue (re-grouping
near-duplicates):

- **Mapped 1:1**: OSRS, NetHack, Crafter, TextWorld, MineDojo,
  Habitat 3.0, AndroidEnv (→ AndroidWorld), Atari 100k, PROCGEN,
  Hanabi, Gym Retro, WebArena, OSWorld.
- **Mapped n:1 (consolidated)**: Pokemon Red speedrun benchmarks
  (academic + Whiddy + ClaudePlaysPokemon + GeminiPlaysPokemon) →
  one Pokemon Red row + one Claude Plays Pokemon product row.
- **Mapped to MineRL Diamond row**: Minecraft Diamonds (DreamerV3
  reference). MineDojo gets its own row separately.
- **Out of scope (no public benchmark spec)**:
  - **Generals.io agent bench** — community discord comps, no
    reproducible scoring protocol identified.
  - **Catanai / Dominion agent comps** — same; community contests
    without standardised release.
  - **Chess.com puzzle suites** — chess engine evaluation is its
    own field, not a memory-shaped benchmark.
  - **Slither.io / Agar.io community comps** — informal arena games,
    no standardised benchmark suite.
  - **AI Dungeon narrative agents** — narrative-game product, not a
    benchmark itself.

  These are flagged in `docs/DECISIONS.md` under "Out-of-scope items
  from the seed list" so future rounds can revisit if reproducible
  benchmark specs emerge.

- **Added beyond seed list**:
  - **SmartPlay** — Microsoft Research ICLR 2024 systematic
    LLM-vs-game benchmark covering 6 games × 9 capability axes.
  - **BALROG** — AISI UK + Cambridge 2024-11 benchmark explicitly
    targeting long-horizon / partial-observability / memory
    capabilities across 6 game envs.

## Editorial decisions

### Tier policy

- **T2** = battle-tested with significant adoption (NLE, MineRL,
  ClaudePlaysPokemon — all have multi-paper / multi-lab follow-up
  histories).
- **T3** = peer-reviewed ICLR/NeurIPS/ICML benchmark with code (most
  rows — MineDojo, Crafter, TextWorld, Atari 100k, PROCGEN, Hanabi,
  Gym Retro, Habitat 3.0, AndroidWorld, WebArena, OSWorld, SmartPlay).
- **T4** = preprint or niche community (OSRS Bench, BALROG, Pokemon
  Red community RL).

### Cell-fill policy

All 60 cells per row are terminal at commit per the standard policy:

- **real-data** with `<a class="cite">` link to a canonical citation
  URL (primarily the project / paper / repo home), for every fillable
  attribute.
- **not-applicable** with reason for benchmark-shaped columns (no
  `funding` / `customers` / `pricing` etc. on read-only static
  evaluation datasets).
- **depth-floor-reached** with `searched not found` and a search-trail
  citation for cells where I could not surface a defensible value
  within the round's time budget (`mindshare` on small / community
  repos; `pros` / `cons` on Pokemon Red speedrun where shape is
  community-evolving).

### Taxonomy policy

- All 17 benchmark rows use the established BABILong / NIAH taxonomy
  template: `update: read-only` is the only filled axis pill; the
  other 6 axes are `not applicable — eval dataset, not a system`.
- The one agent-product row (Claude Plays Pokemon) uses a session-only
  / agent-controlled / episode / opaque shape mirroring the existing
  IDE-agent rows.

## Surprises / notes

- **No NetHack Challenge 2021 winner row.** The competition's winners
  haven't matured into a named benchmark of their own; NLE itself is
  the canonical row.
- **Habitat 3.0 game tasks vs productivity tasks.** Habitat 3.0 is
  primarily an embodied-social-agents benchmark, not a "game"
  benchmark per the issue's framing. Included because the seed list
  named "Habitat 3.0 social agents" and the partial-observability /
  long-horizon / 3D-embodied shape clearly belongs in this cohort.
- **OSWorld's game tasks.** The seed list names "OSWorld game tasks"
  specifically — but OSWorld is dominated by productivity-app tasks
  (LibreOffice, GIMP, Files, Thunderbird). The row characterises the
  benchmark as a whole rather than fabricating a game-task carve-out.
- **The Pokemon Red row.** Folded multiple known Pokemon Red runs
  (Anthropic Claude Sonnet, Google Gemini 2.5 Pro, Whiddy PPO+curiosity)
  into one benchmark row to capture the "Pokemon Red is a community
  benchmark" framing without inflating row count with near-duplicates.
  Claude Plays Pokemon gets its own row because it's a *named
  Anthropic product / demo*, not just a benchmark variant.
- **fetch_citations.py edge surge.** Running offline mode after the
  insert surfaced 241 cited-by edges to the new arxiv-shaped rows
  (Atari 100k, Hanabi, Crafter, TextWorld, MineRL etc.) — these
  benchmarks were already cached as cites-targets by other catalog
  papers; adding the rows made the edges resolvable. landscape.edges.json
  grew from 75 → 316 edges as a result.

## Pipeline result

```
records           : 912   (was 894; +18)
total cells       : 54,720
gap rows in CSV   : 0      <- AUDIT GAPS REQUIREMENT MET
high-priority     : 0
  structurally-not-applicable    23,955
  terminal-real-data             19,194
  searched-not-found             11,571
```

All four `validate.py` gates pass:
- Gate 1 (JSON schema)            PASS — 912 records, 316 edges schema-conformant
- Gate 2 (determinism)            PASS — extract/reconcile/build_edges/fetch_citations byte-stable
- Gate 3 (cycle stability)        PASS — 0 lines of cycle drift
- Gate 4 (S2 cache integrity)     PASS — 228 cache files

## Files touched

- `landscape.html` — 18 new <tr> blocks + 1 group-row + 1 section-explainer
  inserted before "Memory observability & monitoring" group-row.
- `extraction/section-explainers.json` — one new entry for the new subsection.
- `scripts/extract.py` — added "Memory benchmarks & evaluation" to
  `SECTIONS_WITH_SUBS`.
- `scripts/round16_generate.py` — generator for the 18 rows (kept in
  scripts/ alongside round13/round15 generators for future reference).
- `web/landscape.json` — regenerated, 894 → 912 records.
- `web/landscape.edges.json` — regenerated, 75 → 316 edges (auto from
  fetch_citations cache).
- `docs/DECISIONS.md` — appended new "Round 16" entry.
- `extraction/round-16-game-benchmarks.md` — this file.

## Commit

`Round 16: game & interactive-environment benchmarks. 18 new rows. Final catalog: 912 records.`
