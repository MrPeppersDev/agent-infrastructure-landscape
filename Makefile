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

.PHONY: all build build-path-a validate refresh-citations refresh-commit-trajectories refresh-download-trajectories bucket-citations render install-hooks stale-check help

help:
	@echo "Targets:"
	@echo "  make build              — extract → reconcile → build_edges → fetch_citations --offline → bucket_s2_citations"
	@echo "  make build-path-a       — assert render.py(landscape.json) is byte-identical to committed landscape.html (Path A gate, refs #68)"
	@echo "  make validate           — schema + determinism + round-trip + cache gates (~25s)"
	@echo "  make all                — build then validate"
	@echo "  make refresh-citations  — re-run fetch_citations.py against live S2 (slow, ~15min, network)"
	@echo "  make refresh-commit-trajectories — fetch GitHub commit history (slow, network, requires GITHUB_TOKEN)"
	@echo "  make refresh-download-trajectories — fetch NPM + PyPI download history (slow, network)"
	@echo "  make bucket-citations   — bucket S2 cache into citation-trajectory cells (offline, fast)"
	@echo "  make render             — re-render landscape.html from data/landscape.json"
	@echo "  make stale-check        — offline staleness scan against landscape.json (no network)"
	@echo "  make install-hooks      — install scripts/git-hooks/pre-commit into .git/hooks/"
	@echo
	@echo "Edit workflow (Path B, transitional — see docs/DECISIONS.md 2026-05-18 Path A entry):"
	@echo "edit landscape.html by hand; treat data/landscape.json as the queryable mirror."
	@echo "Run \`make build\` to refresh the JSON mirror after HTML edits, then"
	@echo "\`make validate\` before committing. Path A (JSON-as-source) target was declared"
	@echo "in c9b55d2; pipeline flip is tracked in #68. \`make build-path-a\` is the"
	@echo "byte-identity gate that proves the inversion is safe."

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

# Path A byte-identity gate (refs #68 Stream B step 1). Renders
# data/landscape.json through scripts/render.py and asserts the output
# is byte-identical to the committed landscape.html. This is the
# acceptance test for Path A inversion: once this passes reliably, the
# remaining writer-script flips in #68 are safe because we've proven
# that the JSON round-trips cleanly to the HTML surface.
#
# Distinct from `validate.py` gate 3 (which tests render → extract →
# render cycle stability). gate 3 catches renderer/extractor drift in
# isolation; build-path-a catches drift between the committed JSON and
# the committed HTML, which is the property Path A actually depends on.
#
# Trajectory-span fix in c9b55d2 made this pass at 0 diff lines. If
# this target ever fails, it means either (a) a hand edit to
# landscape.html bypassed the JSON, or (b) render.py drifted from the
# HTML surface. Both are Path A bugs that need fixing before #68 step 2.
build-path-a:
	@tmp_html=$$(mktemp -t landscape-path-a.XXXXXX.html); \
	$(PYTHON) scripts/render.py --input data/landscape.json --template landscape.html --output $$tmp_html; \
	diff_lines=$$(diff landscape.html $$tmp_html | wc -l | tr -d ' '); \
	rm -f $$tmp_html; \
	if [ "$$diff_lines" -ne 0 ]; then \
	  echo "✗ build-path-a FAILED: render.py(landscape.json) differs from landscape.html by $$diff_lines diff lines"; \
	  echo "  Run 'diff landscape.html <(python3 scripts/render.py --input data/landscape.json --template landscape.html --output /dev/stdout)' to inspect."; \
	  exit 1; \
	fi; \
	echo "✓ build-path-a PASS: render.py(landscape.json) is byte-identical to landscape.html"

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

# Slow / network-dependent. NOT run as part of `build` or CI.
# Walks every row detected as an NPM or PyPI package publisher (~80 rows)
# and writes a monthly cumulative-download time series into the
# download-trajectory cell. Both registries are no-auth. PyPI's
# pypistats.org has soft throttling; the script adds a politeness sleep
# and retries on 429 with backoff.
# See docs/SCHEMA.md §2.5.6 and scripts/fetch_download_trajectories.py.
refresh-download-trajectories:
	@echo "Fetching NPM + PyPI download history — this can take ~5-10 min."
	@echo "Cached responses live in extraction/download-cache/ and are committed to git."
	@echo "Progress lives in extraction/download-trajectory-progress.json; reruns resume."
	$(PYTHON) scripts/fetch_download_trajectories.py

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
