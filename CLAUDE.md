# CLAUDE.md — working on the AI Agent Infrastructure Landscape

A citation-backed catalog of ~964 AI agent systems, published as a SvelteKit site on GitHub Pages and also served as an MCP server, a CLI, a hosted MCP worker and a GitHub Action. **Open work is in [`docs/HANDOFF.md`](docs/HANDOFF.md). Read it first.**

## Ground rules

- **Merge your own PRs once CI is green.** The maintainer wants that done automatically: open the PR, wait for checks, merge, and don't ask first. Never push to `main` directly and never force-push.
- **Every published fact needs a primary-source citation.** That means a vendor page, the official repo or registry, or a paper. Secondary sources are confidence `medium` at best. Never write a value you couldn't verify; leave the cell alone instead.
- **Reports go inline.** The maintainer reads results in chat, not in separate report files, and wants links for everything.
- Commit messages end with a `Co-Authored-By:` line. PR bodies end with the generated-with footer.

## The pipeline (Path A)

`data/landscape.json` is the source of truth. Everything else is derived from it.

```sh
make build      # reconcile → edges → citations → render landscape.html → data/stack-index.json
make validate   # 7 gates (~25 s). Gate 2 requires JSON == render→extract→reconcile round-trip, byte for byte
make lint       # contradiction lint (oss-conflict, acquired-year, truncated, bare-citation, blank-taxonomy); keep at 0
make history    # data/history.json from git (needs full history: git fetch --unshallow)
make action     # regenerate action/dist/stack-check.mjs from mcp/src/stack-check.ts (CI checks it's current)
```

**After any JSON edit, canonicalize.** Run render → extract → reconcile (`python3 -c "import sys; sys.path.insert(0,'scripts'); import apply_reverify; apply_reverify.canonicalize()"`), then `make build && make validate`. `apply_reverify.py`, `apply_intake_pr.py`, `apply_audit_pr.py` and `apply_correction.py` already do this.

**Rules that trip people up:**
- A per-cell `last_verified_at` is only allowed on `extract.VOLATILE_CELL_SLUGS`.
- Taxonomy reasons on single-value axes must start with the value and contain no colons.
- Renames keep the id. `render.py` emits `data-id` when the id isn't `make_id(name, url)`.
- Commit `landscape.json`, `landscape.edges.json`, `landscape.html` and `stack-index.json` together.

## Applying research results

Re-verification agents write JSON lists in this shape:

```json
{ "id": "...", "verified": true,
  "lifecycle": "active|maintenance|archived|deprecated|acquired|renamed|dead",
  "lifecycle_note": "...", "lifecycle_citation": "https://...",
  "updates": [ { "cell": "license", "old": "...", "new": "...",
                 "citation": "https://...", "confidence": "high|medium" } ] }
```

Apply them with `python3 scripts/apply_reverify.py --date YYYY-MM-DD <files> --report out.md`. Rows with `verified != true` are skipped. Keep inputs, results and a REPORT.md under `extraction/reverify-<date>/`. To add new systems, push a branch `intake-batch/<name>` containing a candidates file in `extraction/intake-batches/`. The **Batch intake** workflow researches and commits each one; then open a PR from the branch. See `scripts/batch_intake.py` for the format.

**Fan-out lesson.** The web-search budget is shared by all subagents in one turn: 200 searches. Five parallel re-verify agents exhausted it after about 25% of rows. Run 1–2 agents per turn, or have them use WebFetch on known URLs (repo pages, vendor pricing and docs) instead of searching.

## Code map

| Path | What |
|---|---|
| `mcp/src/stack-check.ts`, `chooser.ts`, `chooser-infra.ts`, `compat.ts`, `search.ts`, `costs.ts` | Pure, dependency-free logic shared by the web, the MCP server, the CLI, the worker and the Action. Import siblings with a `.js` suffix. |
| `mcp/src/server.ts` | stdio MCP server (23 tools). Tests: `cd mcp && npm test`, or run `tsx src/test-*.ts` directly |
| `cli/src/landscape.ts` | CLI (`check`, `choose`, `choose-stack`, `compat`, `alternatives`, …) |
| `worker/` | Hosted MCP: stateless Streamable HTTP, Cloudflare Worker. `npx tsx worker/test/handler.test.ts` |
| `action.yml`, `action/` | "AI stack check" GitHub Action; self-test in `.github/workflows/action-test.yml` |
| `web/` | SvelteKit (Svelte 5). The postbuild script `web/scripts/generate-exports.mjs` writes `/api/*`, `/feeds/*`, `/changes.xml` and `llms.txt`. `web/scripts/smoke.mjs` is the Playwright smoke test that runs in PR checks |
| `scripts/` | Python pipeline and bots: `build_stack_index.py` (lifecycle detection), `build_history.py`, `apply_*.py`, `lint_contradictions.py` |
| `data/` | `landscape.json`, edges, `stack-index.json`, `history.json`, `migrations.json` (curated, official sources only), `pricing/memory.json` (published list prices + date checked) |
| `taxonomy/` | `families.json` (section → 5 product families), `package-aliases.json`, `system-aliases.json` |
| `bench/` | Memory benchmark harness (LongMemEval, LoCoMo). Never run against live services yet |

`docs/` holds a **stale committed copy** of the built site. The Pages workflow rebuilds it in CI. After a local `npm run build`, run `git checkout docs/` and don't commit it.

## Environment quirks (cloud sessions)

- GitHub REST works through `gh api`; GraphQL doesn't. Create PRs with `gh api repos/{owner}/{repo}/pulls --input body.json`, and merge with `gh api -X PUT .../pulls/N/merge -f merge_method=merge`.
- The Actions logs, artifacts, secrets and dispatch APIs are blocked. Read failures from check-run annotations: `gh api repos/.../check-runs/<id>/annotations`. Workflows surface errors as `::error` annotations for this reason.
- The npm and PyPI registries and `*.github.io` may be unreachable from the shell. Global `tsc` (6.0.3) and `tsx` are available, and CI does the full web build. Local clones can be shallow, so run `git fetch --unshallow` before `make history`.
- Don't run `git stash -u` while background agents are writing untracked files.
