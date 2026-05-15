# Memory Analysis Program — build & validation targets.
#
# Phase 1 deliverable (issue #7). The data pipeline is:
#
#   extract.py  →  reconcile.py  →  build_edges.py  →  fetch_citations.py  →  render.py
#                                                                              (Phase 2+)
#
# `make build` runs the cheap, deterministic, network-free steps.
# `make refresh-citations` runs the slow, network-dependent S2 fetch.
# `make validate` runs the four cheap correctness gates from scripts/validate.py.

PYTHON ?= python3
ROOT   := $(CURDIR)

.PHONY: all build validate refresh-citations refresh-commit-trajectories bucket-citations render install-hooks stale-check help

help:
	@echo "Targets:"
	@echo "  make build              — extract → reconcile → build_edges → fetch_citations --offline → bucket_s2_citations"
	@echo "  make validate           — schema + determinism + round-trip + cache gates (~25s)"
	@echo "  make all                — build then validate"
	@echo "  make refresh-citations  — re-run fetch_citations.py against live S2 (slow, ~15min, network)"
	@echo "  make refresh-commit-trajectories — fetch GitHub commit history (slow, network, requires GITHUB_TOKEN)"
	@echo "  make bucket-citations   — bucket S2 cache into citation-trajectory cells (offline, fast)"
	@echo "  make render             — re-render landscape.html from data/landscape.json"
	@echo "  make stale-check        — offline staleness scan against landscape.json (no network)"
	@echo "  make install-hooks      — install scripts/git-hooks/pre-commit into .git/hooks/"
	@echo
	@echo "Edit workflow (Path B — see docs/DECISIONS.md): edit landscape.html by hand"
	@echo "as the source of authority for now; treat data/landscape.json as the queryable"
	@echo "mirror. Run \`make build\` to refresh the JSON mirror after HTML edits, then"
	@echo "\`make validate\` before committing. Path A (JSON-as-source) activates when"
	@echo "extract.py loses less markup."

# `build` re-runs the full pipeline against the committed S2 cache.
#
# fetch_citations.py runs in --offline mode here: it reads from the committed
# extraction/s2-cache/ instead of hitting the Semantic Scholar API, so the
# cited-edges output is reproducible in seconds, not the ~15 minutes a cold
# fetch would take. When fresh S2 data IS wanted, run `make refresh-citations`
# explicitly — that one DOES hit the network.
#
# bucket_s2_citations.py runs after fetch_citations to refresh the
# citation-trajectory cell content in landscape.html from the committed
# S2 cache. After it runs, a second extract pass re-projects the patched
# HTML into landscape.json so the JSON mirror reflects the new cells.
build:
	$(PYTHON) scripts/extract.py        --output data/landscape.json
	$(PYTHON) scripts/reconcile.py      --input  data/landscape.json --output data/landscape.json
	$(PYTHON) scripts/build_edges.py
	$(PYTHON) scripts/fetch_citations.py --offline
	$(PYTHON) scripts/bucket_s2_citations.py --quiet
	$(PYTHON) scripts/extract.py        --output data/landscape.json
	$(PYTHON) scripts/reconcile.py      --input  data/landscape.json --output data/landscape.json
	@echo
	@echo "build: ran fetch_citations.py --offline (cache-only) and"
	@echo "       bucket_s2_citations.py (citation-trajectory backfill). For"
	@echo "       fresh S2 data, run \`make refresh-citations\` first."
	@echo

# Cheap round-trip validation gates. <30s.
validate:
	$(PYTHON) scripts/validate.py

# Convenience.
all: build validate

# Slow / network-dependent. NOT run as part of `build` or CI.
refresh-citations:
	@echo "Refreshing Semantic Scholar citation data — this can take ~15 minutes."
	@echo "Cached responses live in extraction/s2-cache/ and are committed to git."
	$(PYTHON) scripts/fetch_citations.py

# Offline / fast. Bucketed S2-cache → citation-trajectory cells.
# Reads extraction/s2-cache/*.json and inverts the references-out relation
# into within-catalog inbound-citation yearly trajectories. Idempotent;
# also runs as part of `make build` (after fetch_citations --offline).
# See docs/SCHEMA.md §2.5.5 and scripts/bucket_s2_citations.py.
bucket-citations:
	$(PYTHON) scripts/bucket_s2_citations.py

# Slow / network-dependent. NOT run as part of `build` or CI.
# Walks every row with a parseable GitHub repo URL (~230 rows) and writes a
# monthly cumulative-commit time series into the commit-trajectory cell.
# See docs/SCHEMA.md §2.5.4 and scripts/fetch_commit_trajectories.py.
refresh-commit-trajectories:
	@echo "Fetching GitHub commit history — this can take ~15-30 minutes."
	@echo "Cached responses live in extraction/commit-cache/ and are committed to git."
	@echo "Progress lives in extraction/commit-trajectory-progress.json; reruns resume."
	@echo "Set GITHUB_TOKEN env var to lift the unauthenticated 60/hr rate limit."
	$(PYTHON) scripts/fetch_commit_trajectories.py

# Re-render only — useful when iterating on render.py output without rebuilding
# the JSON. Writes to landscape.html (which is the existing template; render.py
# slices its head/tail so this is safe to repeat).
render:
	$(PYTHON) scripts/render.py --input data/landscape.json --output landscape.html

# Install the pre-commit hook that runs `make validate` before each commit.
# The hook lives under scripts/git-hooks/ (tracked); .git/hooks/ is not tracked.
install-hooks:
	cp scripts/git-hooks/pre-commit .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "pre-commit hook installed. Bypass with \`git commit --no-verify\` if needed."

# Local staleness scan. Runs the same script the weekly CI workflow runs,
# but in --offline mode so it parses dates from landscape.json cells
# instead of hitting the GitHub API. No token required. Writes the flagged
# list to extraction/staleness-report.json and a fuller summary to
# extraction/staleness-summary.json. See MAINTAINER.md §2 for the
# thresholds (active <12mo, stale 12-24mo, abandoned >24mo) and
# .github/workflows/staleness.yml for the CI wiring.
stale-check:
	$(PYTHON) scripts/check_staleness.py --offline \
	  --output extraction/staleness-report.json \
	  --reports-dir extraction
