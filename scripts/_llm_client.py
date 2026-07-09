"""
_llm_client.py — Anthropic LLM plumbing for the capability sweep.

Two responsibilities (docs/composite-methodology.md, issue #127):

  1. Haiku-per-URL extraction: given the fetched text of a linked
     benchmark source, extract structured {benchmark_id, score,
     run_date} triples restricted to the classified benchmark set
     from docs/benchmark-families.yml.
  2. Sonnet QA pass: sanity-check a computed composite (observations
     + sub-scores + band) before it is eligible for the verified bit.
     Returns 'approved' or 'flagged'.

Cost design
-----------
Sequential `messages.create` calls with prompt caching: the system
prompt (instructions + full benchmark-id list) carries a
`cache_control: ephemeral` breakpoint, so every per-URL call after the
first hits the cache. Batch API (24h SLA, 50% discount) is a
documented follow-up, not half-built here — sequential calls keep the
sweep debuggable while row counts are small.

Dependency convention
---------------------
scripts/*.py are stdlib-only (see e.g. research_intake.py, which uses
urllib rather than requests). The `anthropic` SDK is therefore
lazy-imported with a clear install message; the --no-llm and --dry-run
sweep paths never import this module's client, so CI without the SDK
or an API key stays green.

API key: `ANTHROPIC_API_KEY` env var; falls back to a `.env` file at
the repo root for local runs (KEY=value lines, stdlib parse).
"""

from __future__ import annotations

import html as _html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent

# Model pinning: Haiku is date-pinned for extraction reproducibility;
# the Sonnet QA alias tracks the current 4-6 snapshot (matches the
# model_id already recorded by capability_sweep.py's merge step).
EXTRACTION_MODEL = "claude-haiku-4-5-20251001"
QA_MODEL = "claude-sonnet-4-6"

USER_AGENT = "memory-landscape-capability-sweep/1.0"
FETCH_TIMEOUT = 20
PAGE_TEXT_MAX_CHARS = 40_000  # keep per-URL Haiku input bounded

_TAG_STRIP_RE = re.compile(
    r"<(script|style|noscript|svg)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)
_TAGS_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\f\v]+")


def _load_dotenv_key(name: str) -> Optional[str]:
    """Minimal .env reader (stdlib) — local-run convenience only."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == name:
            return v.strip().strip("'\"") or None
    return None


def get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY") or _load_dotenv_key("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set (env var or .env at repo root). "
            "Use --no-llm to run the sweep without LLM extraction."
        )
    return key


def fetch_url_text(url: str) -> tuple[bool, str]:
    """Fetch a URL and return (ok, plain-ish text). HTML is crudely
    de-tagged — Haiku tolerates residual markup fine; we only strip
    the bulk (scripts/styles/tags) to keep token counts down."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read(2_000_000)
        text = raw.decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            OSError, ValueError) as exc:
        return False, f"fetch failed: {exc}"
    text = _TAG_STRIP_RE.sub(" ", text)
    text = _TAGS_RE.sub(" ", text)
    text = _html.unescape(text)
    text = _WS_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return True, text.strip()[:PAGE_TEXT_MAX_CHARS]


def _extract_json_block(text: str) -> Any:
    """Parse the first JSON array/object out of a model reply,
    tolerating markdown fences and prose framing."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = min(
        (i for i in (text.find("["), text.find("{")) if i != -1),
        default=-1,
    )
    if start == -1:
        raise ValueError("no JSON found in model reply")
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(text[start:])
    return obj


class LLMClient:
    """Thin wrapper over the Anthropic SDK for the sweep's two calls."""

    def __init__(
        self,
        extraction_model: str = EXTRACTION_MODEL,
        qa_model: str = QA_MODEL,
    ) -> None:
        try:
            import anthropic  # lazy: scripts stay stdlib-clean without it
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The `anthropic` package is required for the LLM sweep path "
                "(pip install anthropic). Use --no-llm to skip it."
            ) from exc
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=get_api_key())
        self.extraction_model = extraction_model
        self.qa_model = qa_model
        self._extraction_system: Optional[list[dict]] = None

    # -- Haiku extraction ---------------------------------------------------

    def _extraction_system_blocks(self, benchmark_ids: list[str]) -> list[dict]:
        """System prompt with cache_control so sequential per-URL calls
        share a prompt-cache prefix (built once per client)."""
        if self._extraction_system is None:
            self._extraction_system = [
                {
                    "type": "text",
                    "text": (
                        "You extract benchmark results from web page text for an "
                        "AI-capability catalog.\n\n"
                        "Return ONLY a JSON array. Each element:\n"
                        '  {"benchmark_id": "<id>", "score": <number>, '
                        '"run_date": "<YYYY-MM-DD or null>"}\n\n'
                        "Rules:\n"
                        "- benchmark_id MUST be one of the known ids listed below. "
                        "Map page names onto them (e.g. 'SWE-Bench Verified' -> "
                        "'swe-bench-verified'). Skip results for any benchmark not "
                        "in the list.\n"
                        "- score is the reported number as-is (percent -> the "
                        "number, e.g. 74.5). Skip scores you cannot read "
                        "unambiguously from the text.\n"
                        "- run_date only when the page states it; otherwise null.\n"
                        "- One entry per benchmark: if the page reports several "
                        "scores for the same benchmark, keep the most recent (or "
                        "the highest if recency is unclear).\n"
                        "- No commentary, no markdown fences: bare JSON array. "
                        "Empty array if nothing matches.\n\n"
                        "Known benchmark ids:\n"
                        + "\n".join(f"- {b}" for b in sorted(benchmark_ids))
                    ),
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        return self._extraction_system

    def extract_benchmarks(
        self, url: str, page_text: str, benchmark_ids: list[str]
    ) -> list[dict]:
        """Haiku over one fetched URL → [{benchmark_id, score, run_date}]."""
        resp = self.client.messages.create(
            model=self.extraction_model,
            max_tokens=1500,
            system=self._extraction_system_blocks(benchmark_ids),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Source URL: {url}\n\nPage text:\n{page_text}"
                    ),
                }
            ],
        )
        reply = "".join(b.text for b in resp.content if b.type == "text")
        try:
            data = _extract_json_block(reply)
        except (ValueError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        out: list[dict] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            bid = item.get("benchmark_id")
            score = item.get("score")
            if not isinstance(bid, str) or not isinstance(score, (int, float)):
                continue
            out.append(
                {
                    "benchmark_id": bid.strip().lower(),
                    "score": float(score),
                    "run_date": item.get("run_date")
                    if isinstance(item.get("run_date"), str)
                    else None,
                }
            )
        return out

    # -- Sonnet QA ----------------------------------------------------------

    QA_SYSTEM = (
        "You are a QA reviewer for computed capability composites in an "
        "AI-catalog pipeline. Given a row's extracted benchmark "
        "observations and the composite computed from them, decide whether "
        "the result is sane.\n\n"
        "Flag when: a score is implausible for its benchmark (e.g. >100 on "
        "a percentage benchmark), a benchmark is assigned a family that "
        "contradicts what it measures, the observation set is internally "
        "contradictory, or the composite/band is inconsistent with the "
        "sub-scores shown.\n"
        "Approve when the numbers are plausible and internally consistent. "
        "You are NOT judging whether the model deserves its score — only "
        "whether the extraction and arithmetic look trustworthy.\n\n"
        'Return ONLY JSON: {"verdict": "approved" | "flagged", '
        '"reason": "<one sentence>"}'
    )

    def qa_review(
        self,
        row_id: str,
        observations: list[dict],
        composite: Optional[float],
        band: Optional[str],
        by_family: dict[str, Optional[float]],
    ) -> tuple[str, str]:
        """Sonnet sanity check → ('approved'|'flagged', reason)."""
        payload = json.dumps(
            {
                "row_id": row_id,
                "observations": observations,
                "by_family": by_family,
                "composite": composite,
                "band": band,
            },
            indent=2,
            ensure_ascii=False,
        )
        resp = self.client.messages.create(
            model=self.qa_model,
            max_tokens=300,
            system=[
                {
                    "type": "text",
                    "text": self.QA_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": payload}],
        )
        reply = "".join(b.text for b in resp.content if b.type == "text")
        try:
            data = _extract_json_block(reply)
            verdict = data.get("verdict") if isinstance(data, dict) else None
            reason = data.get("reason", "") if isinstance(data, dict) else ""
        except (ValueError, json.JSONDecodeError):
            verdict, reason = None, ""
        if verdict not in ("approved", "flagged"):
            # Unparseable QA reply = no approval. Fail safe: flagged.
            return "flagged", "QA reply unparseable — defaulting to flagged"
        return verdict, str(reason)


if __name__ == "__main__":
    # Tiny smoke entry point: `python3 scripts/_llm_client.py <url>`
    # fetches a URL and prints extracted triples (needs API key).
    if len(sys.argv) != 2:
        print("usage: python3 scripts/_llm_client.py <url>", file=sys.stderr)
        sys.exit(2)
    ok, text = fetch_url_text(sys.argv[1])
    if not ok:
        print(text, file=sys.stderr)
        sys.exit(1)
    client = LLMClient()
    print(json.dumps(
        client.extract_benchmarks(sys.argv[1], text, ["swe-bench-verified"]),
        indent=2,
    ))
