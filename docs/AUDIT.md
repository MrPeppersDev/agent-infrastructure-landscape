# Section audit — periodic catalog re-validation

This document describes the **section-audit pipeline** introduced in
issue #55 / T2.6-3. It builds on the freshness signal from
T2.6-2 (`last_verified_at`) and the research/PR plumbing from
T2.6-1 (`scripts/research_intake.py`).

The audit pipeline is the catalog's antibody system: without periodic
re-validation, freshness decays silently and gaps in coverage grow
unobserved. Every week, one section is audited automatically. The
maintainer reviews each proposal via a checkbox-driven PR — nothing
is auto-applied.

## End-to-end flow

```
        Tuesday 14:00 UTC cron tick
                  │
                  ▼
.github/workflows/audit-section.yml
                  │
                  ▼
scripts/audit_pick_section.py
  - reads audit/section-rotation.json
  - prints the section with the oldest last-audited date
                  │
                  ▼
scripts/audit_section.py "<section>" --mode full
  - reverify: re-fetch primary URL + GitHub API + README per row,
    diff every cell, stage drift as a proposed update
  - expand: search arxiv/HN/etc for candidates not yet in catalog,
    dedupe via MCP searchRecords, append up to 5 stubs
  - always bumps last_verified_at on touched rows
  - writes audit/staged-updates-<slug>-<date>.json
  - writes audit/new-rows-<slug>-<date>.json
                  │
                  ▼
scripts/apply_audit_pr.py --section "<section>" --mode full
  - applies refresh-last-verified actions in landscape.html
  - inserts <!-- audit proposal needs-review --> comments for diffs
  - inserts candidate stub <tr> rows
  - runs `make build` + `make validate` (aborts on failure)
  - writes intake-pr-bodies/audit-<slug>-<date>.md
  - commits to branch `audit/<slug>-<date>`
  - opens draft PR
                  │
                  ▼
        Maintainer reviews PR ─► merge (or close)
```

## Modes

| Mode      | Reverifies existing rows | Searches for new systems | Output files                                   |
|-----------|--------------------------|--------------------------|------------------------------------------------|
| reverify  | yes                      | no                       | `staged-updates-<slug>-<date>.json`            |
| expand    | no                       | yes                      | `new-rows-<slug>-<date>.json`                  |
| full      | yes                      | yes                      | both                                           |

### Reverify mode

For each row in the section, the audit script re-runs the same fetch +
parse pipeline as `scripts/research_intake.py`:

1. Fetch the primary URL HTML (`<meta description>`, first `<p>`).
2. Fetch GitHub repo facts (`/repos/{owner}/{repo}` + `/commits?per_page=1`
   + raw README).
3. Re-derive a focused set of cells:
   - `desc`, `claims` — re-extract from meta description / first paragraph.
   - `created`, `latest-release`, `license`, `gh`, `mindshare` — GitHub API.
   - 8 `obs-*` + 7 `cost-*` + 7 `eval-*` — keyword scan over HTML/README.

For each cell, the script compares the re-derived value to the current
catalog value:

- **Same value** → emit a `refresh-last-verified` action.
  - For volatile cells (per SCHEMA.md §3b): update the per-cell
    `data-last-verified` attribute.
  - For non-volatile cells: no-op (they inherit the row date).
- **Different value** → emit a `propose-update` action. The proposed
  value is stored in the staged-updates JSON, and a `<!-- audit
  proposal needs-review ... -->` HTML comment is added to the cell's
  `<td>` in `landscape.html`. The maintainer reads the comment,
  decides whether the proposed value is correct, and edits the cell
  inline in the PR.

The row-level `data-last-verified` is always refreshed when any cell
is touched.

### Expand mode

For each section, the audit script builds a small bag of search terms
(section name + first sentence of a couple of representative
descriptions) and queries:

- HN search (`https://hn.algolia.com/api/v1/search`)
- arxiv recent listings (`https://arxiv.org/list/cs.CL/recent`)

For each candidate name surfaced, it calls `mcp/dist/tools.js`
`searchRecords` to detect duplicates (similarity > 0.9 = skip). For
non-duplicates, it does a light-touch research pass (just the
description, primary URL) and appends to
`audit/new-rows-<slug>-<date>.json`. The cap is **5 candidates per
run** to keep the PR reviewable. Full 85-cell research happens at
intake time if the maintainer accepts the candidate.

### Full mode

Runs reverify, then expand. Both output files are produced; the PR
body covers both.

## Triggering an audit

### Manual via `gh` CLI

```bash
gh workflow run audit-section.yml \
    -F section="Memory benchmarks & evaluation" \
    -F mode="full"
```

If `section` is omitted, the picker chooses the oldest-audited section
automatically. If `mode` is omitted, defaults to `full`.

### Manual via local CLI

```bash
# 1. Run the audit script.
python3 scripts/audit_section.py "Memory benchmarks & evaluation" \
    --mode full

# 2. Apply the proposals (build + validate + PR body).
python3 scripts/apply_audit_pr.py \
    --section "Memory benchmarks & evaluation" --mode full \
    --no-push --no-commit
```

### Scheduled cron

The workflow runs every Tuesday at 14:00 UTC. With one section per
run and 34 sections total, a full rotation takes ~34 weeks (about 8
months).

## Reviewing an audit PR

The PR body contains a markdown table per mode with one row per
proposal and an unchecked checkbox per row. The review process:

### For reverify deltas

Each delta row in the PR body table looks like:

```
| Approve | Row | Cell | Current | Proposed | Source |
|---------|-----|------|---------|----------|--------|
| [ ] | `mem0--mem0-ai` (Mem0) | `gh` | 8.2k★ Python | 8.5k★ Python | https://github.com/mem0ai/mem0 |
```

For each delta you accept:

1. Check the box `[x]`.
2. Open `landscape.html`, find the `<!-- audit proposal needs-review proposed="..." source="..." -->` comment in the affected cell.
3. Replace the cell's current value with the proposed value (preserving the citation `<a>` tag).
4. Remove the `<!-- audit proposal -->` comment.
5. Commit on the PR branch.

For deltas you reject: just leave the box unchecked. Delete the
`<!-- audit proposal -->` comment when you commit. The original value
remains in place.

### For expand candidates

Each candidate row in the PR body table looks like:

```
| Include | Name | URL | Why surfaced |
|---------|------|-----|--------------|
| [ ] | NewMemSystem | https://github.com/x/newmemsystem | HN hit: Show HN: a memory layer for agents |
```

The candidate is inserted as a stub `<tr>` block in the section,
flagged with an HTML comment. For each candidate you accept:

1. Check the box `[x]`.
2. Either:
   - Fill in the cells inline on the PR branch (light-research → full
     research), OR
   - Close the PR's candidate stub and submit the system through the
     `/submit` form so the auto-intake workflow does the full 85-cell
     research pass.

For candidates you reject: delete the stub `<tr>` block on the PR
branch.

After processing all proposals, run `make build && make validate` once
more on the PR branch to confirm 5/5 gates pass, then merge.

## Failure modes

| Symptom | Cause | Remediation |
|---------|-------|-------------|
| Workflow exit code 1 | Section name not found in catalog | The `workflow_dispatch` input typo'd a section name. Run `python3 scripts/audit_pick_section.py` or check `audit/section-rotation.json` for canonical labels. |
| Workflow exit code 2 | No proposals generated | Reverify found no drift AND expand found no candidates. Not a failure — just a quiet section. The rotation tracker is still updated. |
| Workflow exit code 4 | `make build` failed | Check `audit/build-fail-<slug>-<date>.log`. Usually an `<tr>` insertion broke the renderer's expectations. Most common cause: the section name in `audit/new-rows-*.json` didn't match a `<tr class="group-row">` heading. |
| Workflow exit code 5 | `make validate` failed | Check `audit/validate-fail-<slug>-<date>.log`. Gate 3 (cycle stability) is the strict one; if HTML attribute round-tripping drifted, the patcher needs an update. Gate 5 (claim-tier provenance) might fire if the candidate stub's `tier` doesn't satisfy citation requirements. |
| Workflow exit code 6 | `git push` failed | Token permission issue. The default `GITHUB_TOKEN` should have `contents: write` per the workflow YAML; confirm in Repo Settings → Actions → General. |
| Workflow exit code 7 | `gh pr create` failed | Branch protection rule or repo-settings issue. Run `gh pr create --draft --base main --head audit/...` manually from the auto-created branch. |
| Per-cell research timeout | A primary URL or GitHub API is slow | Per-cell budget is 25s (matches `research_intake.py`). On miss, the cell receives a `refresh-last-verified` action instead of a `propose-update` — silent fallback. Re-running the audit may surface different proposals if the source recovers. |
| Duplicate candidate from expand | MCP `searchRecords` similarity > 0.9 | Skipped silently. If you see a known system surfaced anyway, check `mcp/dist/tools.js` is built (`cd mcp && npm run build`). |

Failure artifacts (build log, validate log, partial JSON) are uploaded
as `audit-failure-logs-<section>` on every failed run (retained 30
days).

## Section rotation policy

`audit/section-rotation.json` maps each primary section name to its
last-audited ISO date. `scripts/audit_pick_section.py` returns the
section with the lexicographically-smallest date; ties are broken
alphabetically.

After each audit run (manual or scheduled), the section's date is
bumped to today. With 34 sections and a weekly cron, a full rotation
completes in **~34 weeks**. Manual triggers via `workflow_dispatch`
let the maintainer audit specific sections on demand without breaking
the rotation; the picker still ignores the manually-triggered run
when choosing next week's section (the rotation tracker uses the
last-completed audit date regardless of trigger source).

To boost a section to the front of the queue, edit
`audit/section-rotation.json` directly and set its date to `1970-01-01`
(or any date older than every other entry). Commit the change. The
next scheduled run will pick it up.

## Configuration

`audit_section.py` reads these env vars:

- `GITHUB_TOKEN` / `GH_TOKEN` — lifts the GitHub API rate limit from
  60/hr → 5000/hr (matches `research_intake.py`).

`apply_audit_pr.py` does not need any env vars beyond standard `gh`
authentication.

The on-disk fetch cache (shared with `research_intake.py`) lives at
`extraction/intake-cache/0__<sha1>.html` (audit runs use issue number 0).
Re-runs on the same day hit the cache; the next day's run re-fetches.

## What's intentionally out of scope

- **Auto-merging audit PRs.** The maintainer-review gate is the whole
  point.
- **Cross-section dependency audits.** One section at a time; the
  rotation guarantees eventual coverage.
- **Slack / email notification on audit PR open.** Follow-up issue if
  desired; the GitHub Actions notification surface is sufficient
  today.
- **ML-driven proposal scoring.** The token-bigram similarity for
  duplicate detection (inherited from `research_intake.py`) is the
  limit of what fits in a per-run budget; richer scoring is
  curator-only.
- **Re-classifying claim tiers (T1/T2/T3) during audit.** Only cell
  values + `last_verified_at` change. Tier re-assignment is a
  maintainer-only operation outside the audit path.
- **More than 5 candidates per expand run.** PRs with 20+ unfamiliar
  candidates don't get reviewed; they get closed. Five is the
  reviewable budget.
