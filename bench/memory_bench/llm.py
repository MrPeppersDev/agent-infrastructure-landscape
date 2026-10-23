"""Minimal OpenAI-compatible chat + embeddings client (stdlib only).

Works with any server exposing /v1/chat/completions and /v1/embeddings
(OpenAI, Azure-compatible gateways, OpenRouter, vLLM, LiteLLM, Ollama …).
Configure with env vars:

    BENCH_LLM_BASE_URL   default https://api.openai.com/v1
    BENCH_LLM_API_KEY    falls back to OPENAI_API_KEY

`FakeLLM` is a deterministic offline stand-in used by the smoke test: it
answers from whatever context it is given by keyword overlap, and judges
by normalised string containment.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass, field

# USD per million tokens (input, output). Used only for cost estimates in
# the run summary; edit or pass --price to override. Checked 2026-10.
PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
}


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    by_model: dict = field(default_factory=dict)

    def add(self, model: str, i: int, o: int) -> None:
        self.calls += 1
        self.input_tokens += i
        self.output_tokens += o
        m = self.by_model.setdefault(model, [0, 0])
        m[0] += i
        m[1] += o

    def cost(self) -> float:
        total = 0.0
        for model, (i, o) in self.by_model.items():
            pi, po = PRICES.get(model, (0.0, 0.0))
            total += i / 1e6 * pi + o / 1e6 * po
        return round(total, 4)


class LLM:
    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None,
                 usage: Usage | None = None, temperature: float = 0.0, timeout: int = 120):
        self.model = model
        self.base_url = (base_url or os.environ.get("BENCH_LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("BENCH_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise SystemExit("set BENCH_LLM_API_KEY or OPENAI_API_KEY (or use --fake for an offline run)")
        self.usage = usage or Usage()
        self.temperature = temperature
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode()
        for attempt in range(6):
            req = urllib.request.Request(f"{self.base_url}{path}", data=body, method="POST", headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                    time.sleep(min(60, 2 ** attempt * 2))
                    continue
                raise SystemExit(f"LLM request failed ({e.code}): {e.read()[:500]!r}")
            except urllib.error.URLError:
                if attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise RuntimeError("unreachable")

    def chat(self, system: str, user: str, max_tokens: int = 400) -> str:
        out = self._post("/chat/completions", {
            "model": self.model, "temperature": self.temperature, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        u = out.get("usage") or {}
        self.usage.add(self.model, u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
        return (out["choices"][0]["message"].get("content") or "").strip()

    def embed(self, texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
        vecs: list[list[float]] = []
        for i in range(0, len(texts), 256):
            batch = [t[:8000] for t in texts[i:i + 256]]
            out = self._post("/embeddings", {"model": model, "input": batch})
            self.usage.add(model, (out.get("usage") or {}).get("prompt_tokens", 0), 0)
            vecs.extend(d["embedding"] for d in sorted(out["data"], key=lambda d: d["index"]))
        return vecs


_WORD = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> list[str]:
    return _WORD.findall(s.lower())


class FakeLLM:
    """Deterministic offline LLM for tests. Not a model of anything."""

    def __init__(self, model: str = "fake", usage: Usage | None = None, **_):
        self.model = model
        self.usage = usage or Usage()

    def chat(self, system: str, user: str, max_tokens: int = 400) -> str:
        self.usage.add(self.model, len(user) // 4, 8)
        if "JUDGE" in system:
            gold = re.search(r"Correct answer:\s*(.*)", user)
            resp = re.search(r"Model response:\s*(.*)", user, re.S)
            g = " ".join(_tokens(gold.group(1))) if gold else ""
            r = " ".join(_tokens(resp.group(1))) if resp else ""
            if "not mentioned" in g:
                return "yes" if ("not" in r and "mention" in r) or "don t know" in r else "no"
            return "yes" if g and g in r else "no"
        # answer: return the memory line sharing the most words with the question
        q = re.search(r"Question:\s*(.*)", user)
        qtok = set(_tokens(q.group(1))) - {"what", "which", "the", "is", "of", "does", "did", "when", "user", "s"} if q else set()
        best, score = "", 0
        for line in user.split("\n"):
            if line.startswith("- "):
                sc = len(qtok & set(_tokens(line)))
                if sc > score:
                    best, score = line[2:], sc
        return best or "The information is not mentioned."

    def embed(self, texts: list[str], model: str = "fake-embed") -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * 64
            for w in _tokens(t):
                v[zlib.crc32(w.encode()) % 64] += 1.0  # stable across processes
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


def make_llm(model: str, fake: bool, usage: Usage) -> "LLM | FakeLLM":
    return FakeLLM(model, usage=usage) if fake else LLM(model, usage=usage)
