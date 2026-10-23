"""Reference baselines every memory layer should be compared against.

- full-context: no memory system at all; the most recent turns that fit a
  token budget go straight into the prompt. Tells you whether a memory
  layer beats just using a long context window.
- bm25: lexical retrieval over individual turns (stdlib only).
- embedding-rag: dense retrieval over individual turns, same embedding
  model as the memory layers use by default.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from ..datasets import Session
from .base import MemoryAdapter, session_text

_WORD = re.compile(r"[a-z0-9]+")


def _tok(s: str) -> list[str]:
    return _WORD.findall(s.lower())


class FullContext(MemoryAdapter):
    name = "full-context"

    def __init__(self, *a, budget_tokens: int = 100_000, **kw):
        super().__init__(*a, budget_tokens=budget_tokens, **kw)
        self.budget = budget_tokens
        self.store: dict[str, list[str]] = defaultdict(list)

    def reset(self, ns: str) -> None:
        self.store[ns] = []

    def ingest(self, ns: str, session: Session, speakers) -> None:
        self.store[ns].extend(session_text(session))

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        out, used = [], 0
        for line in reversed(self.store[ns]):  # newest first until the budget is spent
            cost = len(line) // 4 + 1
            if used + cost > self.budget:
                break
            out.append(line)
            used += cost
        return list(reversed(out))


class BM25(MemoryAdapter):
    name = "bm25"

    def __init__(self, *a, k1: float = 1.5, b: float = 0.75, **kw):
        super().__init__(*a, **kw)
        self.k1, self.b = k1, b
        self.docs: dict[str, list[str]] = defaultdict(list)

    def reset(self, ns: str) -> None:
        self.docs[ns] = []

    def ingest(self, ns: str, session: Session, speakers) -> None:
        self.docs[ns].extend(session_text(session))

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        docs = self.docs[ns]
        toks = [_tok(d) for d in docs]
        if not docs:
            return []
        avg = sum(len(t) for t in toks) / len(toks)
        df = Counter(w for t in toks for w in set(t))
        n = len(docs)
        q = _tok(query)
        scores = []
        for i, t in enumerate(toks):
            tf = Counter(t)
            s = 0.0
            for w in q:
                if w not in tf:
                    continue
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * (self.k1 + 1) / (tf[w] + self.k1 * (1 - self.b + self.b * len(t) / avg))
            scores.append((s, i))
        top = sorted(scores, reverse=True)[:k]
        return [docs[i] for s, i in sorted(top, key=lambda x: x[1]) if s > 0]


class EmbeddingRAG(MemoryAdapter):
    name = "embedding-rag"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.docs: dict[str, list[str]] = defaultdict(list)
        self.vecs: dict[str, list[list[float]]] = defaultdict(list)

    def reset(self, ns: str) -> None:
        self.docs[ns], self.vecs[ns] = [], []

    def ingest(self, ns: str, session: Session, speakers) -> None:
        lines = session_text(session)
        if lines:
            self.docs[ns].extend(lines)
            self.vecs[ns].extend(self.llm.embed(lines, model=self.embed_model))

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        if not self.docs[ns]:
            return []
        qv = self.llm.embed([query], model=self.embed_model)[0]
        sims = [(sum(a * b for a, b in zip(qv, v)), i) for i, v in enumerate(self.vecs[ns])]
        top = sorted(sims, reverse=True)[:k]
        return [self.docs[ns][i] for _, i in sorted(top, key=lambda x: x[1])]
