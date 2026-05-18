# Rendered-diff-preview action — design sketch

Status: **draft for review** (Stream C of #68 work).
Lives in branch `stream-68-review-surface`; promotes to a real
workflow once the contract is agreed.

## Problem

Under Path B (today), the auto-research and section-audit workflows
land their changes as edits to `landscape.html`. Reviewers see a
GitHub diff in the HTML — a cell's new prose appears in context, with
its row, its citation, and the surrounding cells visible. Reviewing
a 30-cell auto-PR takes a few minutes.

Under Path A (#68), those same writers will land JSON cell deltas in
`data/landscape.json`. A 30-cell change becomes a structured diff —
each cell appears as a `value/citation/status/last_verified_at`
object change with no row context, no rendered prose. Cognitive load
for reviewers goes up; the auto-research flywheel (#48 ecosystem)
loses its review-cycle latency advantage.

The rendered-diff-preview action restores the review experience: it
posts a comment on every PR that touches `data/landscape.json`,
rendering each changed cell the way it will appear in
`landscape.html`, with before/after framing.

## Contract

### Trigger

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - 'data/landscape.json'
      - 'data/landscape.edges.json'
```

`paths:` filter is the cheap no-op for unrelated PRs.

### Inputs

- `base.sha` and `head.sha` from the PR event payload.
- `data/landscape.json` at both shas (checked out side-by-side).
- `scripts/render.py` at the head sha (so renderer fixes propagate).

### Output

One comment on the PR (created if absent; updated in-place on
re-trigger via a marker `<!-- diff-preview-bot -->` in the body).

Comment structure:

```markdown
<!-- diff-preview-bot -->
## 🪞 Rendered cell preview

This PR changes **N records, M cells**. Rendered preview of each
cell change — what the cells will look like in `landscape.html`
after merge.

### `record-id-1` (Section Name)

**desc** — status `real-data` → `real-data`
- **before:** <td class="desc">… rendered HTML …</td>
- **after:**  <td class="desc">… rendered HTML …</td>

**latest-release** — status `no-data` → `real-data`
- **before:** <td class="latest-release no-data"></td>
- **after:**  <td class="latest-release">2025-11-04 <a class="cite" href="…">↗</a></td>

### `record-id-2` (Section Name)
…
```

Each rendered HTML snippet is shown both as the raw HTML (so
reviewers can spot escaping bugs) and as actual rendered HTML in a
GitHub-flavoured fenced block (so the prose reads naturally). Two-
pane layout.

### Truncation

- Hard cap: **40 cells across at most 20 records.** If exceeded,
  show the first 20 records and a footer line: `… and N more
  records / M more cells changed, see the JSON diff.`
- Per-cell value truncation: if rendered HTML is > 2000 chars, show
  first 500 + `…` + last 500. Most cells are well under this.
- Edge changes: separate section, summarised as a table (no
  per-edge rendering — edges don't have a `render_cell` equivalent).

### Edge cases

| Case | Behaviour |
|---|---|
| New record (whole row added) | Section "🆕 New records" with full row render |
| Removed record | Section "❌ Removed records" with id + last-known name |
| Cell flipped to `not-applicable` | Render with the `.no-data` italic-grey wrapper |
| Cell with `last_verified_at` change but no value/status change | Show as "refreshed" with just the date delta (no HTML render) |
| Taxonomy axis change (`tax-purpose` etc.) | Bullet list of added/removed taxonomy values |
| Section membership change | Special "Section move" section |
| Schema-only change (e.g., `schemaVersion` bump) | Skip; not a content change |

### Failure modes

- **render.py raises** on a cell: catch per-cell, fall back to
  `<error rendering cell: {exc}>`, continue. Do not fail the action.
- **JSON parse fails** on either sha: comment "❌ rendered preview
  failed: …" and exit 0 (don't block PR).
- **Comment too long for GitHub API (65k char limit):** truncate
  more aggressively and add `[preview truncated for length]`
  footer.

## Implementation

### New script: `scripts/diff_preview.py`

```
diff_preview.py --base PATH --head PATH [--edges-base PATH --edges-head PATH] --output FILE

Loads both JSON files, computes per-cell diff, renders each changed
cell via render.py's render_cell(), emits markdown to --output.
```

Pure Python. No GitHub-specific code. Locally runnable:

```bash
python3 scripts/diff_preview.py \
  --base data/landscape.json \
  --head /tmp/my-edit-landscape.json \
  --output /tmp/preview.md
```

Re-uses:

- `render.py`'s `render_cell()` (the just-fixed trajectory-span
  variant — Stream C is downstream of Stream B's step 1 in a
  no-functional way; the rebase is trivial).
- `render.py`'s `render_taxonomy_cell()` for taxonomy axes.
- A small new function for edge diffs (built fresh; no existing
  helper).

### New workflow: `.github/workflows/diff-preview.yml`

```yaml
name: Rendered diff preview
on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - 'data/landscape.json'
      - 'data/landscape.edges.json'
      - 'scripts/render.py'
      - 'scripts/diff_preview.py'

jobs:
  preview:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install beautifulsoup4
      - name: Extract base + head JSON
        run: |
          mkdir -p /tmp/preview
          git show ${{ github.event.pull_request.base.sha }}:data/landscape.json \
            > /tmp/preview/base.json
          git show ${{ github.event.pull_request.head.sha }}:data/landscape.json \
            > /tmp/preview/head.json
      - name: Render preview
        run: |
          python3 scripts/diff_preview.py \
            --base /tmp/preview/base.json \
            --head /tmp/preview/head.json \
            --output /tmp/preview/comment.md
      - name: Post comment
        uses: peter-evans/create-or-update-comment@v4
        with:
          issue-number: ${{ github.event.pull_request.number }}
          body-file: /tmp/preview/comment.md
          edit-mode: replace
          # idempotency via marker in body header
          body-includes: '<!-- diff-preview-bot -->'
```

### Wiring into existing workflows

- `intake-research.yml` — no change. The bot opens a PR that
  touches `data/landscape.json` (post-flip). `diff-preview.yml`
  triggers automatically via `pull_request: opened`.
- `audit-section.yml` — same. The audit-apply step in the bot PR
  triggers the preview.
- `staleness.yml` — doesn't change cells, just opens issues. Not
  affected.

## Open questions

1. ~~Should the preview render the full row context~~ **DECIDED
   2026-05-18:** Always render the full row for every touched
   record (all 85 cells). Reviewer sees the same context they get
   today from the HTML diff. Comment length is managed via the
   truncation rules above (hard cap at 20 records; rest listed by
   id with a "see JSON diff" footer). Changed cells within each
   rendered row get a visual highlight (e.g. `🔸` prefix or
   `<mark>` wrap on the cell label) so the reviewer's eye lands on
   the delta without losing surrounding context. Implementation
   implication: `diff_preview.py` calls `render.py`'s `render_row()`
   per touched record, not `render_cell()` per changed cell.
2. **Should edge diffs render the records on each end** of the
   edge? Useful but adds two cell renders per edge. Default: just
   show id → id with edge type and metadata, no record render.
3. **PR title parsing for bot identification** — do we want the
   preview to behave differently for bot-opened PRs vs human PRs?
   Likely no (the renderer doesn't care who opened the PR), but
   worth a checkbox.

## Dependencies

- **Stream B step 1** (the trajectory-span render fix in `c9b55d2`)
  is already in main. No code dep — but the diff-preview must use
  the same render.py to avoid drift.
- **Stream B step 2** (trajectory writers flipped to JSON) — not a
  code dep; the diff-preview will render JSON-cell changes regardless
  of who wrote them. But Stream C's writer scripts are the ones that
  most need this preview action working, so coordinate the merge so
  the writers don't ship before the preview is live.

## Not in scope

- Diff *summarisation* (e.g., "12 latest-release dates refreshed").
  Useful but a separate enhancement.
- Auto-approval based on the preview. We're surfacing, not deciding.
- Cross-PR conflict detection.

## Done when

- `scripts/diff_preview.py` exists, has tests, renders both
  cell-value and taxonomy changes correctly.
- `.github/workflows/diff-preview.yml` triggers and comments on a
  real PR that touches `data/landscape.json`.
- The intake-research and section-audit auto-PRs (post-Stream-C
  writer flip) get a preview comment on open.
- README "Editing the catalog" mentions the preview as part of
  the Path A review workflow.
