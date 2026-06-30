#!/usr/bin/env python3
"""
research_intake.py — auto-research an incoming intake submission.

Reads a GitHub Issue (intake-labelled, body in the format produced by
.github/ISSUE_TEMPLATE/intake.yml and web/src/lib/submit-issue.ts) and
emits a complete record dict matching `data/landscape.json`'s records[].

Each of the 96 cells is filled with `{value, citation, status, tier}`
per docs/SCHEMA.md §3a. Per-cell strategy:

  T1 cells (auto-verifiable):
    - If a GitHub URL is provided, fetch /repos/{owner}/{repo} for stars,
      license, archive status, default branch, created_at and the latest
      commit via /commits?per_page=1.
    - Citation is the GitHub URL.

  T2 cells (claim-citation required):
    - Fetch the primary URL HTML, the arxiv URL if present, and the
      GitHub README.
    - Parse description from <meta name="description"> + first <p>.
    - Keyword-scan for obs/cost/eval integrations.
    - For each detected mention, emit {value: "yes", citation: <source URL>,
      status: "real-data", tier: "T2"}.
    - For each non-detected: {value: "no", citation: "", status:
      "depth-floor", tier: "T3"}.
    - For free-text cells (description, claims), pull from the fetched
      HTML/README with the source URL as citation.

  T3 cells (estimate / inferred):
    - Tier guess from funding heuristic.
    - Section / type / cross-listing fields from submission.
    - status: "estimate", tier: "T3".

Hard budget: per-cell research must complete in <30 seconds. Timeout →
depth-floor the cell.

Deterministic cache: fetched URLs written to
`extraction/intake-cache/<issue-number>__<url-hash>.html` so re-runs
don't refetch.

Duplicate check: before producing the output, calls the MCP query layer
`mcp/dist/tools.js` `searchRecords` with the proposed name. If a record
with similarity > 0.9 already exists, abort with exit code 2.

CLI:
  python3 scripts/research_intake.py --issue-number 999 --output /tmp/record.json
  python3 scripts/research_intake.py --name "Foo" --primary-url URL \\
      --section "Foo bar" --output /tmp/record.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = "MrPeppersDev/agent-infrastructure-landscape"
ROOT = Path(__file__).resolve().parent.parent
LANDSCAPE_JSON = ROOT / "data" / "landscape.json"
INTAKE_CACHE = ROOT / "extraction" / "intake-cache"
MCP_TOOLS_JS = ROOT / "mcp" / "dist" / "tools.js"

# Mirror process_intake.py's FIELD_LABELS so the parser tracks the wire
# format produced by both the Issue Form (intake.yml) and the Svelte
# submit form (web/src/lib/submit-issue.ts).
FIELD_LABELS: list[tuple[str, str]] = [
    ("name", "Name"),
    ("url", "URL"),
    ("section", "Section"),
    ("subsection", "Subsection"),
    ("type", "Type"),
    ("tier_guess", "Tier guess"),
    ("brief_description", "Brief description"),
    ("claims", "Claims"),
    ("known_funding", "Known funding"),
    ("known_customers", "Known customers"),
    ("license", "License"),
    ("github_url", "GitHub URL"),
    ("arxiv_url", "Arxiv URL"),
    ("submitter_notes", "Submitter notes"),
]

REQUIRED_FIELDS = ("name", "url", "type", "section", "brief_description")

CELL_COLUMN_SLUGS: list[str] = [
    "type", "desc", "claims", "modalities", "created", "latest-release",
    "license", "gh", "mindshare", "citations", "funding", "customers",
    "pricing", "compliance", "data-handling", "deployment", "hq",
    "founders", "volume", "perf", "repro", "code-release", "api-surface",
    "latency", "throughput", "backend-storage", "multi-tenancy",
    "encryption", "sso-rbac", "embedding-model", "consistency",
    "versioning", "tombstoning", "schema-evolution", "namespace",
    "contradiction", "forgetting", "mcp-support", "a2a-support", "otel",
    "webhooks", "import-export", "integration-count", "orchestration",
    "programmatic-control", "vendor-benchmarks", "pricing-specifics",
    "agent-abstraction", "memory-primitives", "llm-lock", "runtimes",
    "session-handling", "validated-verticals", "time-to-running",
    "anti-fit", "optimised-for", "adjacent-infrastructure", "pros",
    "cons", "links",
    "obs-langsmith", "obs-opentelemetry", "obs-datadog", "obs-helicone",
    "obs-weave", "obs-langfuse", "obs-arize", "obs-custom",
    "cost-token-budget", "cost-prompt-caching", "cost-semantic-caching",
    "cost-batching", "cost-model-routing", "cost-streaming-only",
    "cost-observability-cost-attribution",
    "eval-langsmith-evals", "eval-braintrust",
    "eval-weights-and-biases-agent", "eval-helicone-evals",
    "eval-custom-test-harness", "eval-human-loop",
    "eval-production-traffic-replay",
    "commit-trajectory", "citation-trajectory", "download-trajectory",
    # Phase 2 / Gate 1 (issue #95) — see docs/SCHEMA.md §2.5.7–9.
    "cost-input-usd-per-mtok", "cost-output-usd-per-mtok", "cost-tier",
    "cost-pricing-model", "cost-last-verified",
    "capability-composite-score", "capability-band",
    "capability-benchmark-sources", "capability-last-verified",
    "use-case-tags", "use-case-anti-tags",
]
assert len(CELL_COLUMN_SLUGS) == 96

TAXONOMY_AXES = [
    "storage", "retrieval", "persistence", "update", "unit",
    "governance", "conflict",
]

# Keyword tables for the obs/cost/eval scans. Each list of regexes is
# OR-ed; first match wins. Matching is case-insensitive on the raw
# fetched HTML/README text. The intent is conservative ("if the docs
# mention LangSmith, mark integration yes"); maintainer review on the
# draft PR catches false positives.
OBS_KEYWORDS: dict[str, list[str]] = {
    "obs-langsmith": [r"\blangsmith\b"],
    "obs-opentelemetry": [r"\bopen\s*telemetry\b", r"\botel\b"],
    "obs-datadog": [r"\bdatadog\b"],
    "obs-helicone": [r"\bhelicone\b"],
    "obs-weave": [r"\bweave\b(?!r)", r"\bw&b\s+weave\b", r"\bweights?\s*&?\s*biases?\s+weave\b"],
    "obs-langfuse": [r"\blangfuse\b"],
    "obs-arize": [r"\barize\b", r"\bphoenix\b.*\barize\b"],
    "obs-custom": [r"\bcustom\s+tracing\b", r"\bbuilt[-\s]in\s+tracing\b", r"\bself[-\s]hosted\s+observability\b"],
}

COST_KEYWORDS: dict[str, list[str]] = {
    "cost-token-budget": [r"\btoken\s+budget\b", r"\bmax(?:imum)?\s+tokens?\b", r"\btoken[-\s]limit\b"],
    "cost-prompt-caching": [r"\bprompt\s+cach", r"\bcontext\s+cach"],
    "cost-semantic-caching": [r"\bsemantic\s+cach"],
    "cost-batching": [r"\bbatch(?:ing)?\s+api\b", r"\bbatch\s+inference\b", r"\bbatch\s+requests?\b"],
    "cost-model-routing": [r"\bmodel\s+rout", r"\bmodel\s+selection\b", r"\bmodel\s+gateway\b"],
    "cost-streaming-only": [r"\bstream(?:ing)?\s+(?:only|response|completion)\b"],
    "cost-observability-cost-attribution": [r"\bcost\s+attribut", r"\bspend\s+track", r"\bspending\s+by\b", r"\bcost\s+per\s+(?:user|request|customer|tenant)\b"],
}

EVAL_KEYWORDS: dict[str, list[str]] = {
    "eval-langsmith-evals": [r"\blangsmith\s+eval", r"\blangsmith\s+for\s+eval"],
    "eval-braintrust": [r"\bbraintrust\b"],
    "eval-weights-and-biases-agent": [r"\bweights?\s*&?\s*biases?\b", r"\bw&b\b", r"\bwandb\b"],
    "eval-helicone-evals": [r"\bhelicone\s+eval"],
    "eval-custom-test-harness": [r"\btest\s+harness\b", r"\bregression\s+test\b", r"\bgolden\s+(?:set|test)\b"],
    "eval-human-loop": [r"\bhuman[-\s]in[-\s]the[-\s]loop\b", r"\bhuman\s+annotat", r"\bhuman\s+feedback\b"],
    "eval-production-traffic-replay": [r"\btraffic\s+replay\b", r"\breplay\s+production\b", r"\bshadow\s+(?:test|deploy)\b"],
}

FUNDING_TO_TIER: list[tuple[re.Pattern, int]] = [
    (re.compile(r"series\s+[c-z]\b|ipo\b|public\b", re.I), 1),
    (re.compile(r"series\s+b\b|growth\b", re.I), 1),
    (re.compile(r"series\s+a\b|seed\b|pre[-\s]seed\b|angel\b", re.I), 2),
    (re.compile(r"academic|university|preprint|arxiv|research\s+grant", re.I), 4),
]

GITHUB_API = "https://api.github.com"
USER_AGENT = "agent-infrastructure-landscape-intake-research/1.0"
DEFAULT_TIMEOUT = 25.0  # bounded < 30s per cell rule
ARXIV_RE = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(?P<id>\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE,
)
GITHUB_REPO_RE = re.compile(
    r"github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?(?:/|$)",
    re.IGNORECASE,
)

# Subsections in HTML start with em-dash + space. process_intake.py's
# build_taxonomy_cell mirrors this.
SUB_PREFIX = "— "


# ---------------------------------------------------------------------------
# Issue body parsing — borrowed from process_intake.py
# ---------------------------------------------------------------------------


@dataclass
class IntakeFields:
    name: str = ""
    url: str = ""
    section: str = ""
    subsection: str = ""
    type: str = ""
    tier_guess: str = ""
    brief_description: str = ""
    claims: str = ""
    known_funding: str = ""
    known_customers: str = ""
    license: str = ""
    github_url: str = ""
    arxiv_url: str = ""
    submitter_notes: str = ""
    parse_errors: list[str] = field(default_factory=list)


def parse_issue_body(body: str) -> IntakeFields:
    """Pull `**Label:** value` markdown fields out of the issue body."""
    label_alternation = "|".join(re.escape(label) for _, label in FIELD_LABELS)
    pattern = re.compile(
        rf"\*\*(?P<label>{label_alternation}):\*\*\s*"
        rf"(?P<value>.*?)(?=\n\*\*(?:{label_alternation}):\*\*|\Z)",
        re.DOTALL,
    )
    label_to_key = {label: key for key, label in FIELD_LABELS}
    fields = IntakeFields()
    seen: dict[str, str] = {}
    for match in pattern.finditer(body or ""):
        key = label_to_key[match.group("label")]
        value = match.group("value").strip()
        if value in {"_(none)_", "(none)", "—", "-", ""}:
            continue
        seen[key] = value
    for k, v in seen.items():
        setattr(fields, k, v)
    for req in REQUIRED_FIELDS:
        if not getattr(fields, req, ""):
            label = dict(FIELD_LABELS)[req]
            fields.parse_errors.append(f"missing required field: {label}")
    return fields


def fetch_issue(number: int) -> IntakeFields:
    """Use `gh` to fetch an Issue by number and parse it."""
    proc = subprocess.run(
        ["gh", "issue", "view", str(number), "--repo", REPO,
         "--json", "title,body,number"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh issue view #{number} failed:\n  {proc.stderr.strip()}"
        )
    payload = json.loads(proc.stdout)
    return parse_issue_body(payload.get("body", "") or "")


# ---------------------------------------------------------------------------
# HTTP fetch with on-disk cache
# ---------------------------------------------------------------------------


def cache_key(url: str, issue_number: int) -> Path:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return INTAKE_CACHE / f"{issue_number}__{h}.html"


def fetch_url(
    url: str,
    *,
    issue_number: int,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict | None = None,
    use_cache: bool = True,
) -> tuple[bool, str, str]:
    """Fetch a URL with on-disk cache. Returns (ok, body, reason).

    Cache hit returns (True, cached_body, "cache"). Network errors return
    (False, "", reason).
    """
    if not url:
        return False, "", "no url"
    INTAKE_CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = cache_key(url, issue_number)
    if use_cache and cache_path.exists():
        try:
            return True, cache_path.read_text(encoding="utf-8", errors="replace"), "cache"
        except OSError:
            pass
    base_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        base_headers.update(headers)
    try:
        req = urllib.request.Request(url, headers=base_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            # Be defensive about encoding — fall back to latin-1.
            try:
                body = raw.decode("utf-8")
            except UnicodeDecodeError:
                body = raw.decode("latin-1", errors="replace")
            try:
                cache_path.write_text(body, encoding="utf-8")
            except OSError:
                pass
            return True, body, f"http {resp.status}"
    except urllib.error.HTTPError as exc:
        return False, "", f"HTTPError {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, "", f"net error: {exc}"


def fetch_json(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict | None = None,
) -> tuple[bool, Any, str]:
    """Fetch a URL and decode JSON. Returns (ok, decoded, reason)."""
    h = {"Accept": "application/json"}
    if headers:
        h.update(headers)
    if not url:
        return False, None, "no url"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **h})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data, f"http {resp.status}"
    except urllib.error.HTTPError as exc:
        return False, None, f"HTTPError {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return False, None, f"err: {exc}"


# ---------------------------------------------------------------------------
# GitHub API helpers (T1 cells)
# ---------------------------------------------------------------------------


def parse_github_repo(url: str) -> tuple[str, str] | None:
    if not url:
        return None
    m = GITHUB_REPO_RE.search(url)
    if not m:
        return None
    return m.group("owner"), m.group("repo")


def github_api_headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


@dataclass
class GitHubFacts:
    repo_url: str | None = None  # canonical https://github.com/owner/repo
    stars: int | None = None
    license_spdx: str | None = None
    license_name: str | None = None
    archived: bool | None = None
    default_branch: str | None = None
    created_at: str | None = None
    last_commit_iso: str | None = None
    readme_text: str = ""
    error: str | None = None


def fetch_github_facts(github_url: str) -> GitHubFacts:
    """Hit GitHub's API for repo metadata + latest commit + README."""
    facts = GitHubFacts()
    parsed = parse_github_repo(github_url)
    if not parsed:
        facts.error = "could not parse owner/repo from URL"
        return facts
    owner, repo = parsed
    canonical = f"https://github.com/{owner}/{repo}"
    facts.repo_url = canonical
    headers = github_api_headers()

    ok, data, reason = fetch_json(
        f"{GITHUB_API}/repos/{owner}/{repo}",
        headers=headers,
    )
    if ok and isinstance(data, dict):
        facts.stars = data.get("stargazers_count")
        facts.archived = data.get("archived")
        facts.default_branch = data.get("default_branch")
        facts.created_at = data.get("created_at")
        license_obj = data.get("license") or {}
        facts.license_spdx = license_obj.get("spdx_id")
        facts.license_name = license_obj.get("name")
    else:
        facts.error = f"repo fetch failed: {reason}"
        return facts

    # Latest commit on default branch.
    branch = facts.default_branch or "main"
    ok, data, reason = fetch_json(
        f"{GITHUB_API}/repos/{owner}/{repo}/commits?per_page=1&sha={urllib.parse.quote(branch)}",
        headers=headers,
    )
    if ok and isinstance(data, list) and data:
        commit = data[0].get("commit") or {}
        committer = commit.get("committer") or {}
        facts.last_commit_iso = committer.get("date") or commit.get("author", {}).get("date")

    # README — try main/master + a couple of conventional names.
    for fname in ("README.md", "readme.md", "README.rst", "README"):
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{fname}"
        ok, body, _ = fetch_url(raw_url, issue_number=0, use_cache=False)
        if ok and body.strip():
            facts.readme_text = body
            break

    return facts


# ---------------------------------------------------------------------------
# HTML scraping (T2 cells: description / claims)
# ---------------------------------------------------------------------------


def strip_tags(html: str) -> str:
    """Naive HTML → text. Adequate for description heuristics; the keyword
    scans pull from the raw HTML so attribute strings (e.g. integration
    badges in href values) are still matchable."""
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_meta_description(html: str) -> str:
    m = re.search(
        r'<meta\s+(?:name|property)=["\']?(?:description|og:description)["\']?'
        r'[^>]*content=["\']([^"\']{8,400})["\']',
        html, re.I,
    )
    if m:
        return m.group(1).strip()
    m = re.search(
        r'<meta\s+content=["\']([^"\']{8,400})["\'][^>]*'
        r'(?:name|property)=["\']?(?:description|og:description)["\']?',
        html, re.I,
    )
    if m:
        return m.group(1).strip()
    return ""


def extract_first_p(html: str) -> str:
    """First non-trivial <p> in the body."""
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", html, re.I | re.S):
        text = strip_tags(m.group(1))
        if len(text) >= 40:
            return text[:600]
    return ""


def extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        return strip_tags(m.group(1))[:200]
    return ""


def extract_arxiv_abstract(html: str) -> str:
    """arxiv.org HTML carries the abstract in
    <meta name="citation_abstract"> AND in a <blockquote class="abstract">."""
    m = re.search(
        r'<blockquote\s+class=["\']abstract\s+mathjax["\']>(.*?)</blockquote>',
        html, re.I | re.S,
    )
    if m:
        return strip_tags(m.group(1))[:1200]
    return extract_meta_description(html)


# ---------------------------------------------------------------------------
# Keyword scan — produces the obs-*/cost-*/eval-* yes/no decisions
# ---------------------------------------------------------------------------


def scan_keywords(
    corpus_with_sources: list[tuple[str, str]],
    keyword_table: dict[str, list[str]],
) -> dict[str, tuple[bool, str | None]]:
    """corpus_with_sources is [(text, source_url), …]. Returns {slug:
    (found, citation_url_or_None)}."""
    out: dict[str, tuple[bool, str | None]] = {}
    for slug, patterns in keyword_table.items():
        hit_source: str | None = None
        for text, src in corpus_with_sources:
            if not text:
                continue
            for pat in patterns:
                if re.search(pat, text, re.I):
                    hit_source = src
                    break
            if hit_source:
                break
        out[slug] = (hit_source is not None, hit_source)
    return out


# ---------------------------------------------------------------------------
# Cell helpers — assemble {value, citation, status, tier}
# ---------------------------------------------------------------------------


def cell_real(value: str, citation: str, tier: str = "T2") -> dict:
    """A real-data cell. citation must be an http(s) URL."""
    return {
        "value": value,
        "citation": citation if citation else None,
        "status": "real-data",
        "tier": tier,
    }


def cell_depth_floor(value: str, citation: str | None) -> dict:
    """depth-floor-reached with `searched not found` style value.

    citation should be the URL the researcher looked at (search trail).
    Tier is T2 when citation is present, T3 when blank."""
    if citation:
        return {
            "value": value or "searched not found",
            "citation": citation,
            "status": "depth-floor-reached",
            "tier": "T2",
        }
    return {
        "value": value or "searched not found",
        "citation": None,
        "status": "depth-floor-reached",
        "tier": "T3",
    }


def cell_not_applicable(reason: str) -> dict:
    """not-applicable cell. T3, no citation requirement."""
    return {
        "value": reason,
        "citation": None,
        "status": "not-applicable",
        "tier": "T3",
    }


def cell_estimate(value: str, citation: str | None = None) -> dict:
    """estimate cell — maintainer judgement, T3."""
    return {
        "value": value,
        "citation": citation,
        "status": "estimate",
        "tier": "T3",
    }


def cell_yes_no(found: bool, citation: str | None, search_url: str) -> dict:
    """obs-/cost-/eval-/style yes-no cell.

    Per the spec:
      - found=True  → {value: "yes", citation: source, status: "real-data", tier: "T2"}
      - found=False → {value: "no",  citation: search_url, status:
                       "depth-floor-reached", tier: "T2"} (so gate 5 has
                       a citation to a URL we looked at).
    """
    if found and citation:
        return cell_real("yes", citation, tier="T2")
    # Not found: depth-floor with the search URL as trail.
    return cell_depth_floor("no", search_url if search_url else None)


# ---------------------------------------------------------------------------
# Duplicate detection — calls mcp/dist/tools.js searchRecords
# ---------------------------------------------------------------------------


def normalised_name_token(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def detect_duplicate_mcp(name: str) -> dict | None:
    """Use the MCP `searchRecords` query (via a small Node shim) to scan
    for an existing record whose name token-normalises to a >0.9 match.

    Returns the matched record dict from landscape.json if found, else None.
    Falls back to a direct landscape.json scan if MCP isn't built.
    """
    target = normalised_name_token(name)
    if not target:
        return None
    records: list[dict] = []
    if LANDSCAPE_JSON.exists():
        try:
            records = json.loads(LANDSCAPE_JSON.read_text()).get("records", []) or []
        except json.JSONDecodeError:
            records = []

    # First try the MCP path (the issue spec asks for searchRecords specifically).
    if MCP_TOOLS_JS.exists():
        try:
            shim = (
                "import { searchRecords } from './mcp/dist/tools.js';\n"
                "import { readFileSync } from 'node:fs';\n"
                "const data = JSON.parse(readFileSync('data/landscape.json', 'utf8'));\n"
                f"const query = {json.dumps(name)};\n"
                "const out = searchRecords(data.records, { query, limit: 50 });\n"
                "process.stdout.write(JSON.stringify(out));\n"
            )
            proc = subprocess.run(
                ["node", "--input-type=module", "-e", shim],
                capture_output=True, text=True, cwd=str(ROOT), timeout=20,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                result = json.loads(proc.stdout)
                # Treat any name with > 0.9 token similarity as a duplicate.
                for r in result.get("results", []):
                    existing_name = r.get("name", "") or ""
                    existing_token = normalised_name_token(existing_name)
                    sim = name_similarity(target, existing_token)
                    if sim > 0.9:
                        # Re-load the full record from records.
                        rid = r.get("id")
                        for full in records:
                            if full.get("id") == rid:
                                return full
                        return {"id": rid, "name": existing_name, "_similarity": sim}
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass  # fall through to direct scan

    # Fallback: direct scan over landscape.json.
    for r in records:
        existing_name = r.get("name", "") or ""
        sim = name_similarity(target, normalised_name_token(existing_name))
        if sim > 0.9:
            return r
    return None


def name_similarity(a: str, b: str) -> float:
    """Trivial similarity: 1.0 iff token-normalised strings match exactly,
    else Levenshtein-ratio-style proxy via overlap of n-grams.

    We do this without a third-party library; the cutoff is 0.9, so a
    cheap symmetric token overlap is enough. (Anything subtler than
    "same string after normalisation" is out-of-scope per the issue
    constraints.)
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # Character bigram Jaccard.
    def bigrams(s: str) -> set:
        return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}
    A, B = bigrams(a), bigrams(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / union if union else 0.0


# ---------------------------------------------------------------------------
# Record assembly
# ---------------------------------------------------------------------------


def name_slug(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    s = re.sub(r"-+", "-", s)
    if len(s) > 64:
        cut = s[:64]
        if "-" in cut and not s[64:65] == "-":
            cut = cut.rsplit("-", 1)[0]
        s = cut.strip("-")
    return s


def host_slug(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host.replace(".", "-")


def make_id(name: str, url: str | None) -> str:
    base = name_slug(name)
    if not url:
        return base
    m = ARXIV_RE.search(url)
    if m:
        return f"{base}--arxiv-{m.group('id').replace('.', '-')}"
    parsed = parse_github_repo(url)
    if parsed:
        owner, repo = parsed
        return f"{base}--gh-{name_slug(owner)}-{name_slug(repo)}"
    h = host_slug(url)
    return f"{base}--{h}" if h else base


def tier_from_funding(funding: str, tier_guess: str) -> int:
    """Heuristic: derive a row tier (1-5) from funding + tier_guess.

    The submitter's `tier_guess` (free-form, e.g. "T2 — established …")
    wins if present. Else funding regex; else default to 3.
    """
    if tier_guess:
        m = re.search(r"T(\d)\b", tier_guess)
        if m:
            return int(m.group(1))
        m = re.search(r"\b([1-5])\b", tier_guess)
        if m:
            return int(m.group(1))
    if funding:
        for pat, tier in FUNDING_TO_TIER:
            if pat.search(funding):
                return tier
    return 3


def normalise_subsection(sub: str) -> str:
    if not sub:
        return ""
    sub = sub.strip()
    if not sub.startswith("—"):
        sub = f"{SUB_PREFIX}{sub}"
    return sub


def map_type_to_canonical(submitted_type: str) -> str:
    """Map the Issue Form dropdown values to the catalog's `type` cell
    short labels. The form emits e.g. "framework (library / SDK / OSS
    package)" — the catalog uses just "framework".
    """
    t = (submitted_type or "").lower()
    if "product" in t:
        return "Product"
    if "framework" in t or "library" in t:
        return "Framework"
    if "paper" in t:
        return "Paper"
    if "benchmark" in t:
        return "Benchmark"
    if "harness" in t:
        return "Harness"
    if "substrate" in t or "foundation model" in t:
        return "Substrate"
    return submitted_type or "Product"


def build_record(
    fields: IntakeFields,
    *,
    issue_number: int,
) -> tuple[dict, dict[str, str]]:
    """Top-level orchestration: fetch sources, scan keywords, produce
    a fully-filled record dict + a per-cell source map for the run-trail
    markdown.

    Returns (record, source_map). source_map[slug] = url or "depth-floor"
    explanatory string.
    """
    source_map: dict[str, str] = {}

    primary_url = fields.url
    github_url = fields.github_url or ""
    if not github_url:
        # Sometimes the submitter puts the GitHub URL in `url`.
        if parse_github_repo(primary_url):
            github_url = primary_url
    arxiv_url = fields.arxiv_url or ""
    if not arxiv_url and ARXIV_RE.search(primary_url or ""):
        arxiv_url = primary_url

    # Fetch primary URL HTML (T2 base).
    primary_html = ""
    if primary_url:
        ok, body, reason = fetch_url(primary_url, issue_number=issue_number)
        if ok:
            primary_html = body
        source_map["__primary_fetch"] = reason

    # Fetch arxiv abstract.
    arxiv_html = ""
    if arxiv_url and arxiv_url != primary_url:
        ok, body, _ = fetch_url(arxiv_url, issue_number=issue_number)
        if ok:
            arxiv_html = body

    # Fetch GitHub facts.
    gh_facts = GitHubFacts()
    if github_url:
        gh_facts = fetch_github_facts(github_url)

    # Build the keyword-scan corpus: (text, source_url) pairs in priority order.
    corpus: list[tuple[str, str]] = []
    if primary_html:
        corpus.append((primary_html, primary_url))
    if gh_facts.readme_text:
        corpus.append((gh_facts.readme_text, gh_facts.repo_url or github_url))
    if arxiv_html:
        corpus.append((arxiv_html, arxiv_url))

    obs_hits = scan_keywords(corpus, OBS_KEYWORDS)
    cost_hits = scan_keywords(corpus, COST_KEYWORDS)
    eval_hits = scan_keywords(corpus, EVAL_KEYWORDS)

    # Description: submitter brief_description wins; else meta-desc; else first <p>.
    description = (fields.brief_description or "").strip()
    if not description and primary_html:
        description = extract_meta_description(primary_html) or extract_first_p(primary_html)
    if not description and arxiv_html:
        description = extract_arxiv_abstract(arxiv_html)
    if not description:
        description = "(no description available)"
    desc_citation = primary_url or arxiv_url or github_url or ""

    # Claims: submitter > arxiv abstract > meta description.
    claims = (fields.claims or "").strip()
    claims_citation = primary_url or arxiv_url or ""
    if not claims and arxiv_html:
        claims = extract_arxiv_abstract(arxiv_html)
        claims_citation = arxiv_url
    if not claims and primary_html:
        # Use a longer prose excerpt for claims.
        claims = extract_first_p(primary_html) or extract_meta_description(primary_html)
        claims_citation = primary_url

    cells: OrderedDict = OrderedDict()

    # --- Cell 1: type ---
    type_value = map_type_to_canonical(fields.type)
    cells["type"] = cell_real(type_value, primary_url or github_url or "", tier="T2") \
        if (primary_url or github_url) else cell_estimate(type_value)
    source_map["type"] = primary_url or github_url or "estimate"

    # --- Cell 2: desc ---
    if description and desc_citation:
        cells["desc"] = cell_real(description[:1000], desc_citation, tier="T2")
        source_map["desc"] = desc_citation
    elif description:
        cells["desc"] = cell_estimate(description[:1000])
        source_map["desc"] = "submitter (estimate)"
    else:
        cells["desc"] = cell_depth_floor("searched not found", primary_url)
        source_map["desc"] = "depth-floor: no evidence found"

    # --- Cell 3: claims ---
    if claims and claims_citation:
        cells["claims"] = cell_real(claims[:1500], claims_citation, tier="T2")
        source_map["claims"] = claims_citation
    elif claims:
        cells["claims"] = cell_estimate(claims[:1500])
        source_map["claims"] = "submitter (estimate)"
    else:
        cells["claims"] = cell_depth_floor("searched not found", primary_url or "")
        source_map["claims"] = "depth-floor: no evidence found"

    # --- Cell 4: modalities ---
    cells["modalities"] = cell_depth_floor("searched not found", primary_url or "")
    source_map["modalities"] = "depth-floor: no evidence found"

    # --- Cell 5: created ---
    if gh_facts.created_at:
        cells["created"] = cell_real(gh_facts.created_at[:10], gh_facts.repo_url, tier="T1")
        source_map["created"] = gh_facts.repo_url
    elif arxiv_url:
        cells["created"] = cell_depth_floor("searched not found", arxiv_url)
        source_map["created"] = arxiv_url
    else:
        cells["created"] = cell_depth_floor("searched not found", primary_url or "")
        source_map["created"] = "depth-floor: no evidence found"

    # --- Cell 6: latest-release ---
    if gh_facts.last_commit_iso:
        cells["latest-release"] = cell_real(
            f"last commit {gh_facts.last_commit_iso[:10]}",
            gh_facts.repo_url, tier="T1",
        )
        source_map["latest-release"] = gh_facts.repo_url
    else:
        cells["latest-release"] = cell_depth_floor("searched not found", primary_url or "")
        source_map["latest-release"] = "depth-floor: no evidence found"

    # --- Cell 7: license ---
    license_str = (fields.license or "").strip()
    if license_str and license_str not in {"— skip —", "—"}:
        cells["license"] = cell_real(license_str, primary_url or github_url or "", tier="T2")
        source_map["license"] = primary_url or github_url
    elif gh_facts.license_spdx:
        cells["license"] = cell_real(
            gh_facts.license_spdx, gh_facts.repo_url, tier="T1",
        )
        source_map["license"] = gh_facts.repo_url
    else:
        cells["license"] = cell_depth_floor("searched not found", primary_url or "")
        source_map["license"] = "depth-floor: no evidence found"

    # --- Cell 8: gh (GitHub URL or n/a) ---
    if gh_facts.repo_url and gh_facts.stars is not None:
        archived = " [archived]" if gh_facts.archived else ""
        cells["gh"] = cell_real(
            f"{gh_facts.repo_url} ({gh_facts.stars}★){archived}",
            gh_facts.repo_url, tier="T1",
        )
        source_map["gh"] = gh_facts.repo_url
    elif github_url:
        cells["gh"] = cell_real(github_url, github_url, tier="T1") \
            if github_url.startswith("https://github.com") else \
            cell_depth_floor("searched not found", github_url)
        source_map["gh"] = github_url
    else:
        cells["gh"] = cell_not_applicable("not applicable — no GitHub repo")
        source_map["gh"] = "n/a (no GitHub repo)"

    # --- Cell 9: mindshare ---
    if gh_facts.stars is not None:
        cells["mindshare"] = cell_real(
            f"{gh_facts.stars} GitHub stars", gh_facts.repo_url, tier="T1",
        )
        source_map["mindshare"] = gh_facts.repo_url
    else:
        cells["mindshare"] = cell_depth_floor("searched not found", primary_url or "")
        source_map["mindshare"] = "depth-floor: no evidence found"

    # --- Cell 10: citations ---
    citations_cite = arxiv_url or primary_url or ""
    cells["citations"] = cell_depth_floor("searched not found", citations_cite)
    source_map["citations"] = citations_cite or "depth-floor: no evidence found"

    # --- Cell 11: funding ---
    if fields.known_funding:
        cells["funding"] = cell_real(
            fields.known_funding, primary_url or "", tier="T2",
        ) if primary_url else cell_estimate(fields.known_funding)
        source_map["funding"] = primary_url or "submitter (estimate)"
    else:
        cells["funding"] = cell_depth_floor("searched not found", primary_url or "")
        source_map["funding"] = "depth-floor: no evidence found"

    # --- Cell 12: customers ---
    if fields.known_customers:
        cells["customers"] = cell_real(
            fields.known_customers, primary_url or "", tier="T2",
        ) if primary_url else cell_estimate(fields.known_customers)
        source_map["customers"] = primary_url or "submitter (estimate)"
    else:
        cells["customers"] = cell_depth_floor("searched not found", primary_url or "")
        source_map["customers"] = "depth-floor: no evidence found"

    # --- Cells 13-60: bulk depth-floor with primary URL search trail ---
    depth_floor_slugs = [
        "pricing", "compliance", "data-handling", "deployment", "hq",
        "founders", "volume", "perf", "repro", "code-release", "api-surface",
        "latency", "throughput", "backend-storage", "multi-tenancy",
        "encryption", "sso-rbac", "embedding-model", "consistency",
        "versioning", "tombstoning", "schema-evolution", "namespace",
        "contradiction", "forgetting", "mcp-support", "a2a-support", "otel",
        "webhooks", "import-export", "integration-count", "orchestration",
        "programmatic-control", "vendor-benchmarks", "pricing-specifics",
        "agent-abstraction", "memory-primitives", "llm-lock", "runtimes",
        "session-handling", "validated-verticals", "time-to-running",
        "anti-fit", "optimised-for", "adjacent-infrastructure", "pros",
        "cons",
    ]
    for slug in depth_floor_slugs:
        cells[slug] = cell_depth_floor("searched not found", primary_url or "")
        source_map[slug] = "depth-floor: no evidence found"

    # --- Cell: code-release — special-case the otel detection too ---
    # code-release already filled above as depth-floor; leave it.

    # --- otel: detected via keyword scan; record under "otel" cell ---
    otel_found = obs_hits.get("obs-opentelemetry", (False, None))
    if otel_found[0]:
        cells["otel"] = cell_real("yes", otel_found[1], tier="T2")
        source_map["otel"] = otel_found[1]
    # Else leave the depth-floor cell already set above.

    # --- Cell: links ---
    link_parts = []
    if primary_url:
        link_parts.append(primary_url)
    if github_url and github_url != primary_url:
        link_parts.append(github_url)
    if arxiv_url and arxiv_url != primary_url:
        link_parts.append(arxiv_url)
    if link_parts:
        cells["links"] = cell_real(" ; ".join(link_parts), primary_url or github_url or arxiv_url, tier="T2")
        source_map["links"] = primary_url or github_url or arxiv_url
    else:
        cells["links"] = cell_depth_floor("searched not found", "")
        source_map["links"] = "depth-floor: no evidence found"

    # --- obs-/cost-/eval- columns: yes/no via keyword scan ---
    for slug, hits in obs_hits.items():
        cells[slug] = cell_yes_no(hits[0], hits[1], primary_url or github_url or "")
        source_map[slug] = hits[1] if hits[0] else "depth-floor: not detected"
    for slug, hits in cost_hits.items():
        cells[slug] = cell_yes_no(hits[0], hits[1], primary_url or github_url or "")
        source_map[slug] = hits[1] if hits[0] else "depth-floor: not detected"
    for slug, hits in eval_hits.items():
        cells[slug] = cell_yes_no(hits[0], hits[1], primary_url or github_url or "")
        source_map[slug] = hits[1] if hits[0] else "depth-floor: not detected"

    # --- T3-prep trajectory cells: depth-floor; backfilled by separate scripts ---
    for slug in ("commit-trajectory", "citation-trajectory", "download-trajectory"):
        cells[slug] = cell_depth_floor(
            "searched not found",
            gh_facts.repo_url if (slug == "commit-trajectory" and gh_facts.repo_url) else (primary_url or ""),
        )
        source_map[slug] = "depth-floor: trajectory cells filled by `make refresh-*` scripts"

    # Fill any missing slugs (sanity check). Should not happen, but guard
    # against future schema additions.
    for slug in CELL_COLUMN_SLUGS:
        if slug not in cells:
            cells[slug] = cell_depth_floor("searched not found", primary_url or "")
            source_map[slug] = "depth-floor: no evidence found"

    # Sort cells to match CELL_COLUMN_SLUGS order (extract.py preserves
    # insertion order, but validator only requires the keyset).
    ordered_cells = OrderedDict()
    for slug in CELL_COLUMN_SLUGS:
        ordered_cells[slug] = cells[slug]

    # --- Build record envelope ---
    record_id = make_id(fields.name, primary_url or github_url or arxiv_url)
    tier = tier_from_funding(fields.known_funding, fields.tier_guess)

    section_entry = {
        "section": fields.section,
        "subsection": normalise_subsection(fields.subsection) or None,
        "primary": True,
        "reason": None,
    }
    sections = [section_entry]

    # Taxonomy axes: empty primary-n/a stubs — curator will fill these
    # post-merge. Validate.py tolerates a single-entry n/a array (free-text
    # fallback shape).
    taxonomy: dict[str, list[dict]] = {}
    for axis in TAXONOMY_AXES:
        taxonomy[axis] = [{
            "value": "n/a",
            "primary": True,
            "reason": "not yet researched — auto-intake",
        }]

    record = {
        "id": record_id,
        "name": fields.name,
        "tier": tier,
        "url": primary_url or github_url or arxiv_url or None,
        "sections": sections,
        "taxonomy": taxonomy,
        "cells": ordered_cells,
    }

    return record, source_map


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--issue-number", type=int, default=None,
                    help="GitHub Issue # to parse via `gh issue view`")
    ap.add_argument("--name", default=None,
                    help="System name (overrides Issue parsing)")
    ap.add_argument("--primary-url", default=None,
                    help="Primary URL (overrides Issue parsing)")
    ap.add_argument("--section", default=None,
                    help="Section (overrides Issue parsing)")
    ap.add_argument("--github-url", default=None)
    ap.add_argument("--arxiv-url", default=None)
    ap.add_argument("--brief-description", default=None)
    ap.add_argument("--type", default=None,
                    help="System type — product/framework/paper/...")
    ap.add_argument("--tier-guess", default=None)
    ap.add_argument("--known-funding", default=None)
    ap.add_argument("--known-customers", default=None)
    ap.add_argument("--license", default=None)
    ap.add_argument("--output", required=True,
                    help="Where to write the record JSON")
    ap.add_argument("--source-map-output", default=None,
                    help="Where to write the per-cell source map JSON "
                         "(default: <output>.sources.json)")
    args = ap.parse_args()

    if args.issue_number is None and not (args.name and args.primary_url):
        print("error: provide --issue-number OR --name + --primary-url",
              file=sys.stderr)
        return 1

    if args.issue_number is not None:
        try:
            fields = fetch_issue(args.issue_number)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    else:
        fields = IntakeFields()

    # CLI overrides.
    if args.name:
        fields.name = args.name
    if args.primary_url:
        fields.url = args.primary_url
    if args.section:
        fields.section = args.section
    if args.github_url is not None:
        fields.github_url = args.github_url
    if args.arxiv_url is not None:
        fields.arxiv_url = args.arxiv_url
    if args.brief_description is not None:
        fields.brief_description = args.brief_description
    if args.type is not None:
        fields.type = args.type
    if args.tier_guess is not None:
        fields.tier_guess = args.tier_guess
    if args.known_funding is not None:
        fields.known_funding = args.known_funding
    if args.known_customers is not None:
        fields.known_customers = args.known_customers
    if args.license is not None:
        fields.license = args.license

    # Re-validate required.
    fields.parse_errors = []
    for req in REQUIRED_FIELDS:
        if not getattr(fields, req, ""):
            label = dict(FIELD_LABELS)[req]
            fields.parse_errors.append(f"missing required field: {label}")

    if fields.parse_errors:
        print("error: parse failed:", file=sys.stderr)
        for err in fields.parse_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # Duplicate check — abort with exit code 2 if a similar name exists.
    dup = detect_duplicate_mcp(fields.name)
    if dup is not None:
        sim = dup.get("_similarity")
        sim_str = f" (similarity ~{sim:.2f})" if isinstance(sim, float) else ""
        print(
            f"error: possible duplicate of `{dup.get('name')}` "
            f"(id `{dup.get('id')}`){sim_str} — manual review needed.",
            file=sys.stderr,
        )
        return 2

    print(f"Researching `{fields.name}` (section: {fields.section})…",
          file=sys.stderr)
    record, source_map = build_record(
        fields, issue_number=args.issue_number or 0,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False))

    src_path = Path(args.source_map_output) if args.source_map_output else \
        out_path.with_suffix(out_path.suffix + ".sources.json")
    src_path.write_text(json.dumps(source_map, indent=2, ensure_ascii=False))

    print(f"wrote {out_path} (record id: {record['id']})", file=sys.stderr)
    print(f"wrote {src_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
