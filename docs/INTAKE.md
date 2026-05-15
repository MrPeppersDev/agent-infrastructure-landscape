# Intake — auto-research flow

This document describes the **auto-research intake pipeline** introduced
in issue #53 / T2.6-1. The pipeline decouples submission from data
quality: an intake-labelled Issue still gets logged (audit trail), but a
workflow runs against it to auto-fill all 85 columns from public
sources, then opens a draft PR for maintainer review.

## End-to-end flow

```
/submit form  ─┐
               ├──► GitHub Issue (labelled `intake`)
intake.yml ────┘            │
                            ▼
                .github/workflows/intake-research.yml
                            │
                            ▼
                scripts/research_intake.py
                  - parses the Issue body
                  - duplicate check (MCP searchRecords > 0.9)
                  - fetches: primary URL HTML, GitHub repo API + README,
                    arxiv abstract (if present)
                  - keyword scans: obs / cost / eval integrations
                  - emits a full 85-cell record dict
                            │
                            ▼
                scripts/apply_intake_pr.py
                  - inserts <tr> into landscape.html
                  - runs `make build` + `make validate`
                  - emits intake-pr-bodies/<N>.md (run trail)
                  - commits + opens draft PR + comments on Issue
                            │
                            ▼
                  Draft PR ──► Maintainer review ──► merge
```

## Per-cell tier strategy (per docs/SCHEMA.md §3a)

| Cell category | How it's filled | Tier |
|---------------|-----------------|------|
| GitHub stars, license, last-commit, created-at | GitHub API (`/repos/{owner}/{repo}`, `/commits?per_page=1`) | T1 |
| Description, claims | `<meta name="description">`, first `<p>`, arxiv abstract, README excerpt | T2 |
| obs-* / cost-* / eval-* integration columns | Keyword scan over fetched HTML/README — `"yes"` if matched, else `"no"` with depth-floor | T2 if matched, T2 (depth-floor) if not |
| Funding, customers | From submitter (if provided) — else depth-floor | T2 / T3 |
| Pricing, compliance, perf, latency, etc. | Depth-floor (`searched not found`) with the submitter URL as search trail | T2 |
| Taxonomy axes (storage, retrieval, …) | Left as `n/a` — curator fills post-merge | T3 |
| Trajectory cells (commit / citation / download) | Depth-floor — backfilled by `make refresh-*` | T2 |

The 30-second per-cell hard budget keeps the workflow bounded. If a
fetch times out the cell goes depth-floor with the URL we attempted as
its citation.

## Test the flow locally

Before pushing changes to either script, verify on a known
single-purpose system:

```bash
# 1. Run the research script against a synthetic Issue.
python3 scripts/research_intake.py \
    --name "Mem0" \
    --primary-url "https://mem0.ai" \
    --github-url "https://github.com/mem0ai/mem0" \
    --section "Dedicated memory layers" \
    --brief-description "Self-improving memory layer for LLM apps." \
    --type "framework" \
    --output /tmp/test-record.json

# 2. Inspect the record + source map.
jq '.cells | keys | length' /tmp/test-record.json   # → 85
cat /tmp/test-record.json.sources.json | head -30

# 3. Apply locally without pushing.
python3 scripts/apply_intake_pr.py \
    --record /tmp/test-record.json \
    --issue-number 9999 \
    --no-push --no-comment --no-commit

# 4. Confirm `make validate` passes.
make validate

# 5. Revert when done.
git checkout -- landscape.html data/landscape.json data/landscape.edges.json
```

## Override the auto-research

If the auto-research produces a row that's beyond fixable in PR review:

1. Close the draft PR with a comment explaining the gap.
2. Add the row manually to `landscape.html` following the catalog's
   existing patterns (see `docs/SCHEMA.md`).
3. Run `make build && make validate`.
4. Commit + push, then close the originating intake Issue.

## Failure modes

| Symptom | Cause | Remediation |
|---------|-------|-------------|
| Workflow exit code 2 | `research_intake.py` detected a duplicate (similarity > 0.9) | Either: (a) merge the submitter's notes into the existing row, or (b) edit the Issue title to disambiguate and re-add the `intake` label to retrigger. |
| Workflow exit code 3 | Section group-row missing in `landscape.html` | Section name doesn't match an existing `<tr class="group-row">` heading. Use one of the canonical labels in `docs/SCHEMA.md` (or the submit form dropdown). |
| Workflow exit code 4 | `make build` failed | Check `intake-failures/<issue-number>-build.log` (uploaded as workflow artifact). Most common cause: the inserted `<tr>` desynchronised with the renderer's expectations. |
| Workflow exit code 5 | `make validate` failed | Check `intake-failures/<issue-number>-validate.log`. Likely a tier mismatch — gate 5 expects T1 cells to cite GitHub URLs and T2 cells to have an http(s) citation. Adjust the script's cell-builder or fix the row by hand on the branch. |
| Workflow exit code 6 | `git push` failed | Usually a token permission issue. The default `GITHUB_TOKEN` should have `contents: write` per the workflow YAML; confirm in Repo Settings → Actions → General. |
| Workflow exit code 7 | `gh pr create` failed | Branch protection rule or repo-settings issue. Run `gh pr create --draft` manually from the auto-created branch. |

Failure artifacts (build log, validate log, partial record) are
uploaded as `intake-failure-logs-<issue-number>` on every failed run
(retained 30 days).

## Configuration

`research_intake.py` reads these env vars:

- `GITHUB_TOKEN` / `GH_TOKEN` — used for GitHub API calls (lifts the 60/hr
  unauthenticated limit to 5000/hr).

`apply_intake_pr.py` does not need any env vars beyond the standard `gh`
authentication.

The on-disk cache lives at `extraction/intake-cache/<issue-N>__<sha1>.html`.
It's small (~50KB per fetched URL) and not committed by default — add it
to the workflow's `actions/cache` step if you need cross-run caching.

## What's intentionally out of scope

- **Auto-merging the PR.** The maintainer review gate is the whole
  point of this design. PRs open in draft mode and require explicit
  maintainer approval.
- **Re-researching existing rows.** That's T2.6-3 section-audit
  territory. The duplicate check exits the workflow before any
  PR-opening side effects fire.
- **Per-section intake form variants.** One form serves all sections;
  the keyword scans are intentionally section-agnostic so a single
  research pass works across the catalog.
- **ML-based duplicate detection.** A token-normalised character-bigram
  Jaccard similarity > 0.9 is the cutoff. Subtler heuristics live with
  the maintainer's eye.
