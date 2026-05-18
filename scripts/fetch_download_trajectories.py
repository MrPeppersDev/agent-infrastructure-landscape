#!/usr/bin/env python3
"""
fetch_download_trajectories.py — pull monthly cumulative download counts
for every catalog row that publishes to NPM or PyPI.

Issue #52 (T3-prep-3). Feeds the S-curve maturity fit (T2-4 / issue #47)
the cleanest adoption signal we have for OSS libraries / SDKs — package
manager downloads are typically smooth monotonic curves with much less
burst noise than commit cadence or stargazer counts.

Outputs:
- Writes the `download-trajectory` cell into landscape.html for each
  row detected as an NPM or PyPI publisher.
- Caches every raw API response under
  ``extraction/download-cache/<source>__<sanitized-name>.json`` so
  subsequent ``make build`` runs are deterministic (and offline-safe).
- Persists in-progress state to
  ``extraction/download-trajectory-progress.json`` so a SIGINT or rate-limit
  abort resumes cleanly on the next run.

Cell shape on write (real-data):

    <td class="download-trajectory" ...>[{"ym":"2024-01","monthly":42000,"cum":42000},...]</td>

The cell value is the JSON-stringified compact array (no spaces). For
status=depth-floor-reached / not-applicable the cell uses the canonical
``<span class="no-data">`` patterns documented in SCHEMA.md §3 so the
existing parser in extract.py picks them up unchanged.

Detection priority:
  1. Cell value or citation contains `npmjs.com/package/<name>` → NPM.
  2. Cell value or citation contains `pypi.org/project/<name>/` → PyPI.
  3. Cell value or citation contains `pip install <name>` → PyPI.
  4. Cell value or citation contains `npm install <name>` → NPM.
  5. KNOWN_PACKAGES (record-id → (source, name)) — curated mapping for
     ambiguous / unstated cases. This is the largest source of coverage
     in practice since the catalog cells rarely spell out install paths.

For a row with BOTH NPM and PyPI publications, we keep the
higher-traffic of the two (compare cumulative final counts at the end
of the trajectory) and record the source in the citation. Cross-source
aggregation is intentionally out of scope per SCHEMA.md §2.5.6.

Auth:
  Neither NPM nor PyPI require auth for download counts. We add a
  ~200ms sleep between PyPI requests to be polite to pypistats.org.

Usage:
  python3 scripts/fetch_download_trajectories.py
  python3 scripts/fetch_download_trajectories.py --offline    # cache-only
  python3 scripts/fetch_download_trajectories.py --limit 50   # cap rows attempted
  python3 scripts/fetch_download_trajectories.py --force      # ignore progress
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LANDSCAPE = ROOT / "data" / "landscape.json"
DEFAULT_HTML = ROOT / "landscape.html"
CACHE_DIR = ROOT / "extraction" / "download-cache"
PROGRESS_FILE = ROOT / "extraction" / "download-trajectory-progress.json"

USER_AGENT = "agent-infrastructure-landscape-download-trajectories (https://github.com/MrPeppersDev/agent-infrastructure-landscape)"
PYPI_SLEEP_BETWEEN = 2.0  # politeness floor for pypistats.org (their rate limit is ~1 req/sec)
NPM_SLEEP_BETWEEN = 0.05  # NPM's range API is generous; small floor is fine
REQUEST_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

NPM_PKG_URL_RE = re.compile(
    r"npmjs\.com/package/(@?[A-Za-z0-9._/\-]+?)(?:/|\"|\s|$|[?#)])",
    re.IGNORECASE,
)
PYPI_PKG_URL_RE = re.compile(
    r"pypi\.org/project/([A-Za-z0-9._\-]+?)/?(?:\"|\s|$|[?#)])",
    re.IGNORECASE,
)
PIP_INSTALL_RE = re.compile(
    r"\bpip(?:3)?\s+install\s+(?:--upgrade\s+|-U\s+)?([A-Za-z0-9._\-]+)",
    re.IGNORECASE,
)
NPM_INSTALL_RE = re.compile(
    r"\bnpm(?:\s+i(?:nstall)?|\s+add)\s+(?:-g\s+|--global\s+)?(@?[A-Za-z0-9._/\-]+)",
    re.IGNORECASE,
)


# Curated record-id → (source, package-name) for rows where the catalog
# cells don't spell out an install command. Source is "npm" or "pypi".
# Names verified against the registry; ambiguous-name rows are omitted
# rather than guessed. The runtime detection falls back to this map
# only if URL-based / install-command detection fails for the row.
KNOWN_PACKAGES: dict[str, tuple[str, str]] = {
    # --- Dedicated memory layers ---
    "mem0--mem0-ai": ("pypi", "mem0ai"),
    "letta-memgpt--letta-com": ("pypi", "letta"),
    "cognee--cognee-ai": ("pypi", "cognee"),
    "memvid--gh-memvid-memvid": ("pypi", "memvid"),
    "memoripy--gh-caspianmoon-memoripy": ("pypi", "memoripy"),
    "memary--gh-kingjulio8238-memary": ("pypi", "memary"),
    "memobase--gh-memodb-io-memobase": ("pypi", "memobase"),
    "memori--gh-memorilabs-memori": ("pypi", "memori"),
    "memori-gibsonai--gh-gibsonai-memori": ("pypi", "memorisdk"),
    "zep-graphiti--getzep-com": ("pypi", "zep-python"),
    # --- Framework-embedded memory ---
    "langmem-langchain--langchain-ai-github-io": ("pypi", "langmem"),
    "llamaindex-memory--llamaindex-ai": ("pypi", "llama-index"),
    "agno-phidata-memory--docs-phidata-com": ("pypi", "agno"),
    "crewai-memory--crewai-com": ("pypi", "crewai"),
    "autogen-memory--microsoft-github-io": ("pypi", "pyautogen"),
    # --- Agent frameworks (no first-party memory layer) ---
    "autogen-ag2--gh-ag2ai-ag2": ("pypi", "ag2"),
    "autogpt--gh-significant-gravitas-autogpt": ("pypi", "autogpt"),
    "metagpt--gh-geekan-metagpt": ("pypi", "metagpt"),
    "babyagi--gh-yoheinakajima-babyagi": ("pypi", "babyagi"),
    "agency-swarm--gh-vrsen-agency-swarm": ("pypi", "agency-swarm"),
    "gpt-engineer--gh-antonosika-gpt-engineer": ("pypi", "gpt-engineer"),
    "burr-dagworks--gh-dagworks-inc-burr": ("pypi", "burr"),
    # --- Vector-database infrastructure ---
    "chroma--trychroma-com": ("pypi", "chromadb"),
    "lancedb--lancedb-com": ("pypi", "lancedb"),
    # --- Inference platforms & gateways ---
    "litellm--gh-berriai-litellm": ("pypi", "litellm"),
    # --- Coding-agent memory ---
    "aider--aider-chat": ("pypi", "aider-chat"),
    # --- Retrieval-as-memory hybrids ---
    "graphrag-microsoft--microsoft-com": ("pypi", "graphrag"),
    "lightrag--gh-hkuds-lightrag": ("pypi", "lightrag-hku"),
    "bge-m3--arxiv-2402-03216": ("pypi", "FlagEmbedding"),
    # --- Training infrastructure ---
    "accelerate-hugging-face--gh-huggingface-accelerate": ("pypi", "accelerate"),
    "axolotl--gh-axolotl-ai-cloud-axolotl": ("pypi", "axolotl"),
    "deepspeed--gh-microsoft-deepspeed": ("pypi", "deepspeed"),
    "composer-mosaicml--gh-mosaicml-composer": ("pypi", "mosaicml"),
    "llama-factory--gh-hiyouga-llama-factory": ("pypi", "llamafactory"),
    "distilabel--gh-argilla-io-distilabel": ("pypi", "distilabel"),
    "colossalai--gh-hpcaitech-colossalai": ("pypi", "colossalai"),
    # --- Knowledge-graph platforms ---
    "kuzu--kuzudb-github-io": ("pypi", "kuzu"),
    # --- Eliza / agent frameworks (NPM-published JS) ---
    "eliza-ai16z--gh-elizaos-eliza": ("npm", "@elizaos/core"),
    # --- LangChain core (broader than any single row but often referenced) ---
    "langchain-core--langchain-ai": ("pypi", "langchain"),
    # --- Additional vector / KG / memory libraries (round-2 enrichment) ---
    "milvus--milvus-io": ("pypi", "pymilvus"),
    "pgvector--gh-pgvector-pgvector": ("pypi", "pgvector"),
    "qdrant--qdrant-tech": ("pypi", "qdrant-client"),
    "neo4j--neo4j-com": ("pypi", "neo4j"),
    "supermemory--supermemory-ai": ("npm", "supermemory"),
    "cipher-byterover--gh-campfirein-cipher": ("npm", "@byterover/cipher"),
    "openmemory--gh-caviraoss-openmemory": ("pypi", "openmemory"),
    # --- Additional agent frameworks ---
    "openai-agents-sdk--gh-openai-openai-agents-python": ("pypi", "openai-agents"),
    "microsoft-semantic-kernel--gh-microsoft-semantic-kernel": ("pypi", "semantic-kernel"),
    "semantic-kernel-memory--learn-microsoft-com": ("pypi", "semantic-kernel"),
    "smolagents-hugging-face--gh-huggingface-smolagents": ("pypi", "smolagents"),
    "opendevin-openhands--gh-all-hands-ai-openhands": ("pypi", "openhands-ai"),
    # openai-swarm: deliberately omitted; not published to PyPI (install via git only).
    "praison-memory--gh-mervinpraison-praisonai": ("pypi", "praisonai"),
    "agixt-adaptive-memory--gh-josh-xt-agixt": ("pypi", "agixtsdk"),
    "pydantic-ai-hindsight--hindsight-vectorize-io": ("pypi", "pydantic-ai"),
    # --- Additional training-infra libraries ---
    "peft-hugging-face--gh-huggingface-peft": ("pypi", "peft"),
    "stable-baselines3--gh-dlr-rm-stable-baselines3": ("pypi", "stable-baselines3"),
    "tensorrt-llm--gh-nvidia-tensorrt-llm": ("pypi", "tensorrt-llm"),
    "text-generation-inference-tgi--gh-huggingface-text-generation-inference": ("pypi", "text-generation"),
    "sglang--gh-sgl-project-sglang": ("pypi", "sglang"),
    "openrlhf--gh-openrlhf-openrlhf": ("pypi", "openrlhf"),
    "rl4lms--gh-allenai-rl4lms": ("pypi", "rl4lms"),
    # --- Evaluation & observability platforms ---
    "ragas--gh-explodinggradients-ragas": ("pypi", "ragas"),
    "openllmetry-traceloop--gh-traceloop-openllmetry": ("pypi", "traceloop-sdk"),
    "openinference--gh-arize-ai-openinference": ("pypi", "openinference-instrumentation"),
    # --- Memory benchmarks (a handful publish actually-installable packages) ---
    "babilong--arxiv-2406-10149": ("pypi", "babilong"),
    "crafter--gh-danijar-crafter": ("pypi", "crafter"),
    "nethack-learning-environment-nle--gh-heiner-nle": ("pypi", "nle"),
    # --- Coding-agent memory (StackBlitz Bolt is the npm name) ---
    "bolt-new-stackblitz--bolt-new": ("npm", "bolt"),
    # --- Retrieval-as-memory ---
    "memorag--gh-qhjqhj00-memorag": ("pypi", "memorag"),
    # --- Sparse-attention / RAG papers with installable pkgs ---
    "raptor--gh-parthsarthi03-raptor": ("pypi", "raptor-tree"),
    "hipporag-hipporag2--gh-osu-nlp-group-hipporag": ("pypi", "hipporag"),
}


def _sanitize(name: str) -> str:
    """Cache filename sanitization — collapse / and other special chars."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", name)


def detect_package(
    record: dict[str, Any],
) -> tuple[str, str, str] | None:
    """Determine (source, package-name, display-url) for this row, or None.

    `source` is "npm" or "pypi". `display-url` is the canonical registry
    URL we'll use as the cell's citation when the trajectory is real.

    Detection priority:
      1. Direct package URL in any cell (npmjs.com/package/X or pypi.org/project/X)
      2. `pip install X` or `npm install X` in any cell value/citation
      3. KNOWN_PACKAGES map keyed on record id
    """
    cells = record.get("cells") or {}
    # Build a single big haystack of all cell values + citations + record url.
    parts: list[str] = []
    for cell in cells.values():
        v = cell.get("value") or ""
        c = cell.get("citation") or ""
        if v:
            parts.append(v)
        if c:
            parts.append(c)
    if record.get("url"):
        parts.append(record["url"])
    blob = " ".join(parts)

    # 1a. NPM URL.
    m = NPM_PKG_URL_RE.search(blob)
    if m:
        name = m.group(1).rstrip("/")
        return "npm", name, f"https://www.npmjs.com/package/{name}"
    # 1b. PyPI URL.
    m = PYPI_PKG_URL_RE.search(blob)
    if m:
        name = m.group(1)
        return "pypi", name, f"https://pypi.org/project/{name}/"

    # 2a. pip install.
    m = PIP_INSTALL_RE.search(blob)
    if m:
        name = m.group(1)
        # Reject common false-positives that aren't actually package names
        if name.lower() not in {"the", "this", "your", "with"}:
            return "pypi", name, f"https://pypi.org/project/{name}/"
    # 2b. npm install.
    m = NPM_INSTALL_RE.search(blob)
    if m:
        name = m.group(1)
        if name.lower() not in {"the", "this", "your", "with"}:
            return "npm", name, f"https://www.npmjs.com/package/{name}"

    # 3. KNOWN_PACKAGES fallback.
    rec_id = record.get("id") or ""
    if rec_id in KNOWN_PACKAGES:
        source, name = KNOWN_PACKAGES[rec_id]
        if source == "npm":
            return "npm", name, f"https://www.npmjs.com/package/{name}"
        else:
            return "pypi", name, f"https://pypi.org/project/{name}/"

    return None


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


class FetchError(Exception):
    """Per-package failure. Caller marks the row as depth-floor."""


class RateLimited(FetchError):
    """HTTP 429 — caller should retry after a backoff."""


def _request(url: str, timeout: float = REQUEST_TIMEOUT) -> bytes:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FetchError(f"not-found: {url}") from e
        if e.code == 429:
            raise RateLimited(f"rate-limited: {url}") from e
        raise FetchError(f"http-{e.code}: {url}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"network-error: {url}: {e.reason}") from e


def _request_with_retry(url: str, timeout: float = REQUEST_TIMEOUT) -> bytes:
    """Wrap _request with a single retry-after-backoff on rate-limit."""
    try:
        return _request(url, timeout)
    except RateLimited:
        # pypistats.org typical recovery window is ~30s; 60s gives margin.
        backoff = 60.0
        print(f"  rate-limited; sleeping {backoff:.0f}s then retrying {url}", file=sys.stderr)
        time.sleep(backoff)
        return _request(url, timeout)


# ---------------------------------------------------------------------------
# NPM
# ---------------------------------------------------------------------------


def fetch_npm_history(name: str) -> dict[str, Any]:
    """Pull monthly cumulative downloads for an NPM package.

    NPM's downloads API is `/downloads/range/<start>:<end>/<package>`,
    which returns daily counts for up to 18 months per request. To
    cover the package's whole life we walk backwards in 18-month
    windows from today until a window returns all zeros (or we hit
    2010, before NPM's stats start).

    Returns:
      {
        "source": "npm",
        "name": <package>,
        "trajectory": [{"ym": "YYYY-MM", "monthly": N, "cum": M}, ...],
        "total_downloads": int,
        "fetched_at": "<isoz>",
        "windows_fetched": int,
      }
    """
    today = dt.date.today()
    # Walk backwards from today in 18-month windows.
    window_days = 540  # ~18 months — NPM caps the range request at this.
    end = today
    earliest_allowed = dt.date(2010, 1, 1)

    monthly_totals: dict[str, int] = {}
    windows_fetched = 0
    quoted_name = urllib.parse.quote(name, safe="@/")
    last_error: str | None = None

    while end > earliest_allowed:
        start = end - dt.timedelta(days=window_days)
        if start < earliest_allowed:
            start = earliest_allowed
        url = (
            f"https://api.npmjs.org/downloads/range/"
            f"{start.isoformat()}:{end.isoformat()}/{quoted_name}"
        )
        try:
            body = _request_with_retry(url)
        except FetchError as e:
            last_error = str(e)
            if "not-found" in last_error and windows_fetched == 0:
                # Package doesn't exist on NPM.
                raise
            # Mid-walk error: bail out with whatever we have.
            break

        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise FetchError(f"bad-json: {url}: {e}") from e

        windows_fetched += 1
        downloads = data.get("downloads")
        if not isinstance(downloads, list) or not downloads:
            # No data for this window — stop walking back.
            break

        any_nonzero = False
        for entry in downloads:
            day = entry.get("day") or ""
            count = entry.get("downloads")
            if not isinstance(count, int) or count < 0:
                continue
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
                continue
            ym = day[:7]
            monthly_totals[ym] = monthly_totals.get(ym, 0) + count
            if count > 0:
                any_nonzero = True

        if not any_nonzero:
            break

        # Step the window backward.
        end = start - dt.timedelta(days=1)
        if NPM_SLEEP_BETWEEN > 0:
            time.sleep(NPM_SLEEP_BETWEEN)

    # Drop the current (partial) month — its monthly value isn't comparable
    # to past months yet. Keep only complete months.
    cur_ym = today.strftime("%Y-%m")
    if cur_ym in monthly_totals:
        del monthly_totals[cur_ym]

    if not monthly_totals:
        # Package exists but no historical downloads — treat as depth-floor.
        raise FetchError(f"no-downloads: npm/{name}{(' (' + last_error + ')') if last_error else ''}")

    trajectory: list[dict[str, Any]] = []
    cum = 0
    total = 0
    for ym in sorted(monthly_totals):
        monthly = monthly_totals[ym]
        cum += monthly
        total += monthly
        trajectory.append({"ym": ym, "monthly": monthly, "cum": cum})

    return {
        "source": "npm",
        "name": name,
        "trajectory": trajectory,
        "total_downloads": total,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "windows_fetched": windows_fetched,
    }


# ---------------------------------------------------------------------------
# PyPI (via pypistats.org)
# ---------------------------------------------------------------------------


def fetch_pypi_history(name: str) -> dict[str, Any]:
    """Pull monthly cumulative downloads for a PyPI package.

    pypistats.org's `/api/packages/<name>/overall` endpoint returns
    daily totals split by `with_mirrors` / `without_mirrors` for the
    package's full history (typically ~180 days but the JSON contains
    every observed day). We pick `without_mirrors` to mirror what NPM
    reports (real installs, not CDN mirror traffic).

    pypistats also returns a 404 for packages it has no record of;
    callers treat that as depth-floor.

    Returns the same shape as fetch_npm_history.
    """
    quoted = urllib.parse.quote(name, safe="")
    url = f"https://pypistats.org/api/packages/{quoted}/overall"
    body = _request_with_retry(url)

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise FetchError(f"bad-json: {url}: {e}") from e

    rows = data.get("data")
    if not isinstance(rows, list):
        raise FetchError(f"bad-shape: {url}")

    monthly_totals: dict[str, int] = {}
    for r in rows:
        category = r.get("category")
        if category != "without_mirrors":
            # The "with_mirrors" rows double-count CDN mirror downloads —
            # not what we want for adoption signal.
            continue
        date = r.get("date") or ""
        count = r.get("downloads")
        if not isinstance(count, int) or count < 0:
            continue
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            continue
        ym = date[:7]
        monthly_totals[ym] = monthly_totals.get(ym, 0) + count

    # Drop the current (partial) month.
    today_ym = dt.date.today().strftime("%Y-%m")
    if today_ym in monthly_totals:
        del monthly_totals[today_ym]

    if not monthly_totals:
        raise FetchError(f"no-downloads: pypi/{name}")

    trajectory: list[dict[str, Any]] = []
    cum = 0
    total = 0
    for ym in sorted(monthly_totals):
        monthly = monthly_totals[ym]
        cum += monthly
        total += monthly
        trajectory.append({"ym": ym, "monthly": monthly, "cum": cum})

    if PYPI_SLEEP_BETWEEN > 0:
        time.sleep(PYPI_SLEEP_BETWEEN)

    return {
        "source": "pypi",
        "name": name,
        "trajectory": trajectory,
        "total_downloads": total,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "windows_fetched": 1,
    }


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def cache_path(source: str, name: str) -> Path:
    """Cache filename — collapse source + sanitized name into one safe path."""
    return CACHE_DIR / f"{source}__{_sanitize(name)}.json"


def load_cache(source: str, name: str) -> dict[str, Any] | None:
    p = cache_path(source, name)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_cache(source: str, name: str, payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = cache_path(source, name)
    p.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# HTML rewrite — replace each row's download-trajectory <td>
# ---------------------------------------------------------------------------


# The empty scaffold placeholder we just wrote is:
#   <td class="download-trajectory"><span class="no-data">no data</span></td>
# Subsequent runs may have replaced this with real-data / depth-floor
# variants. The regex must catch all three.
CELL_RE = re.compile(
    r'<td class="download-trajectory">[^<]*'
    r'(?:<[^>]+>[^<]*</[^>]+>[^<]*'
    r'(?:<[^>]+>[^<]*</[^>]+>[^<]*)?)?'
    r'</td>',
    re.DOTALL,
)


def render_real_cell(trajectory: list[dict[str, Any]], display_url: str) -> str:
    """Real-data cell — JSON value + registry citation."""
    val = json.dumps(trajectory, separators=(",", ":"))
    return (
        f'<td class="download-trajectory">'
        f'<span class="trajectory-data">{val}</span> '
        f'<a class="cite" href="{display_url}" title="source">↗</a>'
        f'</td>'
    )


def render_depth_floor_cell(display_url: str) -> str:
    """Depth-floor cell — preserves the attempted URL in the citation."""
    return (
        f'<td class="download-trajectory">'
        f'<span class="no-data">searched not found</span> '
        f'<a class="cite" href="{display_url}" title="searched">↗</a>'
        f'</td>'
    )


def render_not_applicable_cell() -> str:
    """No package detected → not-applicable, no citation needed."""
    return (
        '<td class="download-trajectory">'
        '<span class="no-data" style="font-style:italic;color:#555;">'
        'not applicable — not published as a package</span>'
        '</td>'
    )


def patch_html_for_row(
    html: str,
    row_name: str,
    row_url: str | None,
    new_cell_html: str,
    occurrence: int = 0,
) -> tuple[str, bool]:
    """Patch the download-trajectory cell for the row whose name+url match.

    Mirrors patch_html_for_row in fetch_commit_trajectories.py. Returns
    (new_html, did_replace).
    """
    from html import escape

    name_escaped = escape(row_name)

    if row_url:
        url_escaped = escape(row_url, quote=True)
        anchor_pat = re.compile(
            re.escape(f'<td class="name"><a href="{url_escaped}">')
            + re.escape(name_escaped)
            + re.escape('</a></td>')
        )
    else:
        anchor_pat = re.compile(
            re.escape(f'<td class="name">{name_escaped}</td>')
        )

    matches = list(anchor_pat.finditer(html))
    if not matches or occurrence >= len(matches):
        return html, False
    m = matches[occurrence]

    end_tr = html.find('</tr>', m.end())
    if end_tr < 0:
        return html, False
    row_chunk = html[m.start():end_tr]
    cell_m = CELL_RE.search(row_chunk)
    if cell_m is None:
        return html, False
    abs_start = m.start() + cell_m.start()
    abs_end = m.start() + cell_m.end()
    new_html = html[:abs_start] + new_cell_html + html[abs_end:]
    return new_html, True


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


def load_progress() -> dict[str, Any]:
    if not PROGRESS_FILE.exists():
        return {"done": {}}
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"done": {}}


def save_progress(progress: dict[str, Any]) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(
        json.dumps(progress, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def fetch_one(source: str, name: str) -> dict[str, Any]:
    if source == "npm":
        return fetch_npm_history(name)
    elif source == "pypi":
        return fetch_pypi_history(name)
    else:
        raise FetchError(f"unknown-source: {source}")


def run(args: argparse.Namespace) -> int:
    landscape_path: Path = args.landscape
    html_path: Path = args.html

    if not landscape_path.exists():
        print(f"error: landscape not found: {landscape_path}", file=sys.stderr)
        return 1
    if not html_path.exists():
        print(f"error: landscape.html not found: {html_path}", file=sys.stderr)
        return 1

    data = json.loads(landscape_path.read_text(encoding="utf-8"))
    records = data.get("records") or []

    progress = {"done": {}} if args.force else load_progress()
    done: dict[str, Any] = progress.setdefault("done", {})

    print(
        f"fetch_download_trajectories: records={len(records)} "
        f"offline={args.offline} "
        f"resume-from-progress={'no' if args.force else 'yes'} "
        f"already-done={len(done)}",
        file=sys.stderr,
    )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    html = html_path.read_text(encoding="utf-8")

    counts = {
        "real-data": 0,
        "depth-floor": 0,
        "not-applicable": 0,
        "skipped-row-not-found": 0,
        "cache-hit": 0,
        "live-fetch": 0,
        "errors": 0,
        "npm-real": 0,
        "pypi-real": 0,
    }
    failed: list[dict[str, Any]] = []

    occurrence_counter: dict[tuple[str, str | None], int] = {}

    attempted = 0
    for rec in records:
        rec_id = rec.get("id") or "?"
        rec_name = rec.get("name") or ""
        rec_url = rec.get("url")
        key = (rec_name, rec_url)
        occ = occurrence_counter.get(key, 0)
        occurrence_counter[key] = occ + 1

        if args.limit and attempted >= args.limit:
            break

        detection = detect_package(rec)
        if detection is None:
            new_cell = render_not_applicable_cell()
            html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
            if ok:
                counts["not-applicable"] += 1
                done[rec_id] = {"status": "not-applicable"}
            else:
                counts["skipped-row-not-found"] += 1
            continue

        source, name, display_url = detection
        existing = done.get(rec_id)
        if existing and existing.get("status") in {"real-data", "depth-floor"}:
            # Re-render from cache (deterministic for `make build`).
            if existing["status"] == "real-data":
                cached = load_cache(source, name)
                if cached is not None:
                    new_cell = render_real_cell(cached.get("trajectory") or [], display_url)
                else:
                    new_cell = render_depth_floor_cell(display_url)
                html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
                if ok:
                    counts["real-data" if cached else "depth-floor"] += 1
                    counts["cache-hit"] += 1
                    if cached and source == "npm":
                        counts["npm-real"] += 1
                    if cached and source == "pypi":
                        counts["pypi-real"] += 1
                else:
                    counts["skipped-row-not-found"] += 1
            else:
                new_cell = render_depth_floor_cell(display_url)
                html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
                if ok:
                    counts["depth-floor"] += 1
                    counts["cache-hit"] += 1
                else:
                    counts["skipped-row-not-found"] += 1
            continue

        # New row: cache → network → cache miss.
        cached = load_cache(source, name)
        trajectory: list[dict[str, Any]] | None = None
        fetched = False

        if cached is not None and cached.get("trajectory") is not None:
            trajectory = cached["trajectory"]
            counts["cache-hit"] += 1
        elif args.offline:
            pass
        else:
            attempted += 1
            rate_limited_skip = False
            try:
                payload = fetch_one(source, name)
                save_cache(source, name, payload)
                trajectory = payload["trajectory"]
                counts["live-fetch"] += 1
                fetched = True
            except RateLimited as e:
                # Rate-limit after retry exhausted — DON'T mark this row as
                # depth-floor in progress. Leaving progress untouched lets
                # the next run retry the row from scratch.
                failed.append({"id": rec_id, "package": f"{source}/{name}", "error": str(e)})
                counts["errors"] += 1
                rate_limited_skip = True
            except FetchError as e:
                failed.append({"id": rec_id, "package": f"{source}/{name}", "error": str(e)})
                counts["errors"] += 1

            if rate_limited_skip:
                # Skip patching HTML for this row this run — the empty
                # scaffold placeholder stays in place until next retry.
                continue

        if trajectory:
            new_cell = render_real_cell(trajectory, display_url)
            html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
            if ok:
                counts["real-data"] += 1
                if source == "npm":
                    counts["npm-real"] += 1
                else:
                    counts["pypi-real"] += 1
                done[rec_id] = {
                    "status": "real-data",
                    "source": source,
                    "name": name,
                    "url": display_url,
                }
            else:
                counts["skipped-row-not-found"] += 1
        else:
            new_cell = render_depth_floor_cell(display_url)
            html, ok = patch_html_for_row(html, rec_name, rec_url, new_cell, occ)
            if ok:
                counts["depth-floor"] += 1
                done[rec_id] = {
                    "status": "depth-floor",
                    "source": source,
                    "name": name,
                    "url": display_url,
                }
            else:
                counts["skipped-row-not-found"] += 1

        # Checkpoint every 20 live fetches.
        if fetched and counts["live-fetch"] % 20 == 0:
            save_progress(progress)
            html_path.write_text(html, encoding="utf-8")
            print(
                f"  checkpoint: real-data={counts['real-data']} "
                f"depth-floor={counts['depth-floor']} "
                f"not-applicable={counts['not-applicable']} "
                f"live-fetch={counts['live-fetch']} "
                f"cache-hit={counts['cache-hit']}",
                file=sys.stderr,
            )

    save_progress(progress)
    html_path.write_text(html, encoding="utf-8")

    print(
        "\nfetch_download_trajectories: summary\n"
        f"  real-data:        {counts['real-data']} "
        f"(npm={counts['npm-real']} pypi={counts['pypi-real']})\n"
        f"  depth-floor:      {counts['depth-floor']}\n"
        f"  not-applicable:   {counts['not-applicable']}\n"
        f"  cache-hits:       {counts['cache-hit']}\n"
        f"  live-fetches:     {counts['live-fetch']}\n"
        f"  errors:           {counts['errors']}\n"
        f"  rows-not-found:   {counts['skipped-row-not-found']}",
        file=sys.stderr,
    )
    if failed:
        print("  sample errors (up to 10):", file=sys.stderr)
        for e in failed[:10]:
            print(f"    - {e['id']}  {e['package']}  {e['error']}", file=sys.stderr)

    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--landscape",
        type=Path,
        default=DEFAULT_LANDSCAPE,
        help="Path to landscape.json (default: data/landscape.json)",
    )
    p.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML,
        help="Path to landscape.html (default: landscape.html)",
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help="Don't hit the network. Cache-only fills, otherwise depth-floor.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Cap the number of NEW live fetches (0 = unlimited).",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Ignore extraction/download-trajectory-progress.json (restart fresh).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
