# Round 8 — Survivorship Unknown-bucket OSS enrichment

**Date:** 2026-05-12
**Scope:** the 79 records previously sitting in the survivorship view's
`Unknown — OSS but signal-too-weak` sub-bucket.
**Method:** reproduced `classify()` from `web/src/lib/analyses/survivorship.ts`
in Python to derive the exact 79; pulled `pushed_at`, `stargazers_count`,
`archived` from `gh api repos/{owner}/{repo}`; cached responses to
`extraction/gh-cache/`; rewrote each row's `<td class="code-release">` in
`landscape.html` to encode the new last-commit signal; re-extracted via
`scripts/extract.py` + `scripts/reconcile.py` + `scripts/validate.py`.

## 1. Totals

- **Rows enriched:** 79 (100% of the oss-weak-signal sub-bucket)
- **GitHub API calls:** 79 (cached; reproducible in seconds)
- **404 / repo-gone:** 0
- **Archived but recent (≤12mo):** 2 (`mem0ai/mem0-mcp`,
  `huggingface/text-generation-inference`)

For 36 of the 79 rows, the catalog did not carry an explicit `github.com`
URL in the `gh` or `code-release` cell — they fell into the OSS bucket via
the OSS-license heuristic in `hasGitHubPresence()`. For those we mapped
the row to its canonical upstream repo manually (mapping committed under
`/tmp/manual_gh_map.py`; e.g. LangChain → `langchain-ai/langchain`, Haystack
→ `deepset-ai/haystack`, Argilla → `argilla-io/argilla`, ZenML → `zenml-io/zenml`,
Sentence Transformers → `UKPLab/sentence-transformers`, …).

## 2. Bucket distribution (before → after)

| Bucket                  | Before | After | Δ     |
|-------------------------|-------:|------:|------:|
| Active                  |     80 |   156 |  +76  |
| Stale                   |      1 |     4 |   +3  |
| Abandoned               |      0 |     0 |    0  |
| Unknown                 |    321 |   242 |  -79  |
| Research                |    297 |   297 |    0  |
| **Total**               |    699 |   699 |    0  |

Unknown sub-buckets (after):

| Sub-bucket             | Before | After |
|------------------------|-------:|------:|
| closed-source          |    242 |   242 |
| oss-weak-signal        |     79 |     0 |
| newly-created          |      0 |     0 |
| na                     |      0 |     0 |

The Unknown floor is now `closed-source = 242` — proprietary products with
no public release cadence. That is a structural ceiling on
survivorship-view observability, not a catalog gap. Round 8 has fully
exhausted the catalog-fixable sub-bucket.

## 3. Newly-classified Stale or Abandoned rows

All three newly-Stale rows; zero newly-Abandoned. Cross-referenced with
the influence-vs-adoption view's score (inbound integrations × 3 + inbound
citations) is not meaningful here: none of the three carry an academic
citation count in the catalog and inbound integration counts for these
rows are low single digits. Listed below by raw star count + age:

| Row                       | Repo                                | Last commit | Age (mo) | Stars   |
|---------------------------|-------------------------------------|-------------|---------:|--------:|
| Bolt.new (StackBlitz)     | `stackblitz/bolt.new`               | 2024-12-17  |       17 |  16,368 |
| Jina AI Embeddings        | `jina-ai/jina`                      | 2025-03-24  |       14 |  21,872 |
| Nomic Embed               | `nomic-ai/contrastors`              | 2025-03-26  |       14 |     787 |

Bolt.new is the highest-mindshare "stale" row to surface in this round —
16.3k★ open-source product that has not received a push since
December 2024. Jina and Nomic are both embedding services that appear to
have shifted maintenance to closed surfaces (Jina API, Nomic Atlas) while
their public repos quietly stalled. None of the three crossed the 24-month
"Abandoned" boundary, so no entries for the "top 10 most-cited newly
Stale/Abandoned" call-out beyond the three above.

## 4. Top-5 most-influential newly-Abandoned (last-commit >24mo)

**None.** Round 8 surfaced 0 newly-Abandoned rows. Every one of the 79
previously-Unknown OSS rows now classifies as Active (76), Stale (3),
or Active-but-Archived (2 — see §5). This is itself a notable finding:
the "weak signal" was simply that the catalog had not captured the
last-commit date; the underlying projects are overwhelmingly still
maintained.

## 5. Archived repos (still recent)

Two repos report `archived=true` but their last push is recent (≤3mo).
Per the cell-text policy adopted in this round, these are tagged
`Archived — last commit YYYY-MM` so the human reader can see that the
upstream owner has explicitly closed maintenance, even though the
classifier currently still buckets them as Active (because the
classifier reads the date, not the Archived prefix).

- `mem0ai/mem0-mcp` — last commit 2026-03, archived (superseded by the
  official MCP server in `mem0ai/mem0` proper).
- `huggingface/text-generation-inference` — last commit 2026-03, archived
  (functionality migrated into other HF inference offerings).

A follow-up round could extend `classify()` to read the "Archived" prefix
and route these to `abandoned` regardless of recency; out of scope here.

## 6. 404 / repo-gone rows

**None.** All 79 canonical repos resolved with HTTP 200.

## 7. Files changed

- `landscape.html`: 79 `<td class="code-release">` cells rewritten.
- `web/landscape.json`: regenerated by `scripts/extract.py +
  scripts/reconcile.py`.
- `extraction/gh-cache/`: new directory, 79 JSON files committed for
  reproducibility (mirrors the `extraction/s2-cache/` pattern). Decision
  rationale logged in `docs/DECISIONS.md`.

## 8. Floor remaining

Sub-Unknown classification floor after Round 8: **`closed-source-opaque`
≈ 242 rows**. These are proprietary products (Salesforce Einstein, Notion
AI, Glean, Sierra, Decagon, Harvey, Abridge, et al.) where the catalog
cannot observe internal release cadence. Further enrichment of this
bucket requires non-API signal (press cadence, hiring posts, status-page
publication frequency) and is explicitly outside the
catalog-fixable scope.
