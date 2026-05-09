# Memory Analysis Program

A landscape catalog of AI memory systems, frameworks, papers, products, and theoretical
proposals — built as the foundation for downstream comparative and trend analysis.

## What's in here

- **`landscape.html`** — the main artifact. ~510+ entries across 22+ sections /
  sub-groups, with tier badges (T1 battle-tested → T5 theoretical / informal),
  sortable by tier within each section, with section explainers and source links.
  Open in a browser.
- **`PLAN.md`** — current state, deferred work, and the data we need to pull in
  before doing real trend / adoption analysis.

## Sections currently in the landscape

Production / commercial:
- Dedicated memory layers
- Framework-embedded memory
- Platform-provider memory
- Coding-agent memory
- Browser-agent memory
- Personal AI / PKM / lifelogging memory
- Voice-first / wearable AI memory
- Vertical / domain-specific AI memory (sub-groups: scientific, healthcare, legal,
  customer-support / voice, gaming / NPC, robotics / autonomous-driving / embodied)

Research / academic:
- Research / specialised systems
- Recent method papers (sub-groups: factual / experiential / working memory /
  parametric & latent / world-model / continual learning / memory-augmented RL /
  cognitive-architecture-inspired)
- Retrieval-as-memory hybrids

Adjacent / infrastructure:
- File-backed / editor paradigms
- Claude Code memory mechanisms (incl. MCP servers)
- Knowledge-graph platforms
- Vector-database infrastructure
- Enterprise-search adjacencies
- Memory benchmarks & evaluation
- Memory observability & monitoring
- Memory governance, privacy & safety

Speculative:
- Theoretical / informal — ideas without a paper

## Why this exists

Three distinct uses, in priority order:

1. **Cross-system comparison** — given a problem, what tools / techniques exist?
2. **Adoption signal** — what's actually being used in production vs. just published?
3. **Trend signal** — what's growing, what's saturating, what's being abandoned?

The landscape catalog is the substrate for (1). Adoption and trend analysis are
downstream uses that need additional data we haven't gathered yet — see `PLAN.md`.

## Methodology / provenance

Every entry was sourced from one of:
- Curated lists (Agent-Memory-Paper-List, Awesome-GraphMemory)
- Survey papers (`arxiv.org/abs/2512.13564`, `arxiv.org/abs/2508.10824`)
- Benchmark leaderboards (LongMemEval, LoCoMo, ConvoMem)
- Vendor websites and academic venue pages
- Targeted research-agent sweeps (~25 agents over multiple sessions)

URLs verified at time of entry. Claims (the right-hand column for many rows) are
vendor-stated unless otherwise marked. Some 2026 arxiv IDs were independently
verified by a paper-verification pass.

## Status

The catalog is comprehensive enough for use as a reference. Honest confidence on
landscape coverage: ~88-92% as of 2026-05-06. The known gaps and the plan to close
them are in `PLAN.md`.

## Editing the catalog

Phase 1 (issues #1–#7) shipped a structured mirror of the catalog in
`web/landscape.json` and a relationship file in `web/landscape.edges.json`,
plus a render-from-JSON script in `scripts/render.py`. **Today's source of
authority is still `landscape.html`** — `render.py`'s output diffs from the
hand-edited HTML by ~50k lines (mostly tier-sort row reordering and dropped
inline markup like `<span class="signal-num">`, `<br>`, etc. that
`extract.py` collapses to plain text). Inverting that — making JSON the
authority and HTML a build artefact — is **deferred** until `extract.py`
preserves more of that markup. See the Path A vs Path B decision in
`docs/DECISIONS.md`.

Workflow today (Path B):

1. Edit `landscape.html` by hand as you have through Rounds 1–6.
2. Run `make build` to refresh `web/landscape.json` and
   `web/landscape.edges.json` from the new HTML.
3. Run `make validate` (described below). Fix any reported failures.
4. Commit `landscape.html` plus the regenerated JSON mirrors together.
   The CI workflow at `.github/workflows/validate.yml` re-runs the gates on
   push and PR.

`make refresh-citations` is a separate target that re-pulls Semantic Scholar
data — it takes ~15 min and is only needed when new research-paper rows have
been added or the catalog wants to refresh inbound-influence counts.

## Validation

`make validate` runs four cheap correctness gates in ~25 seconds. None of
them touch the network.

| # | Gate                    | Catches                                                                                          |
|---|-------------------------|--------------------------------------------------------------------------------------------------|
| 1 | JSON schema             | Records or edges that violate `docs/SCHEMA.md` §7 (bad enums, missing primary, dangling edges).  |
| 2 | Fast-step determinism   | Non-determinism in `extract.py` / `reconcile.py` / `build_edges.py` (random orders, clock-driven IDs). |
| 3 | Render-cycle stability  | Markup drift in `render.py` ↔ `extract.py` round-trips beyond the documented 16-line ceiling.    |
| 4 | S2 cache integrity      | Corrupted `extraction/s2-cache/*.json` files (so `fetch_citations.py` won't surprise-fail).      |

A pre-commit hook that runs `make validate` automatically before every commit
ships in `scripts/git-hooks/pre-commit`. Install it with `make install-hooks`
(idempotent). The hook short-circuits when no pipeline-relevant files are
staged, so commits to `PLAN.md` or `analysis.md` aren't slowed down. Bypass
the hook for a single commit with `git commit --no-verify`.

A CI workflow that runs the same `make validate` on push and PR is in the
issue tracker but not yet committed — the working OAuth token doesn't have
the `workflow` scope. To add it, refresh your `gh` token with
`gh auth refresh -s workflow` and commit a `.github/workflows/validate.yml`
that runs `make validate` on a Python 3.11 runner with `beautifulsoup4`
installed.
