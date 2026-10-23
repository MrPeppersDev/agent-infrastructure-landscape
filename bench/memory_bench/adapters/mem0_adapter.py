"""mem0 (open source) — `mem0ai` `Memory`, local default stack.

Verified against mem0ai v2.2.1 (GitHub main, Sep 2026):
  https://github.com/mem0ai/mem0/blob/main/mem0/memory/main.py
  https://github.com/mem0ai/mem0/blob/main/mem0/configs/base.py
  https://docs.mem0.ai/open-source/configuration

API facts this adapter depends on:
- `Memory.from_config({"llm": {"provider": "openai", "config": {"model": ...}},
  "embedder": {"provider": "openai", "config": {"model": ...}}})`; everything
  else (Qdrant on local disk, SQLite history at ~/.mem0/history.db) stays default.
- `add(messages, *, user_id=, metadata=, infer=True)` is synchronous: the LLM
  extraction and the vector writes finish before it returns.
- `add(timestamp=...)` and `search(reference_date=...)` are platform-only and
  raise ValueError in OSS, so the session date goes in via `metadata`: a
  caller-supplied `metadata["created_at"]` is kept as the memory's created_at.
- `search(query, *, top_k=, filters={"user_id": ...})` (top-level user_id is
  rejected in v2) -> {"results": [{"memory", "created_at", "metadata", ...}]}.
- `delete_all(user_id=...)`.
"""

from __future__ import annotations

from ..datasets import Session
from ._util import EMBED_DIMS, parse_session_date, run_tag
from .base import MemoryAdapter, require


class Mem0(MemoryAdapter):
    name = "mem0"
    requires = ("mem0ai>=2.2.1",)
    env = ("OPENAI_API_KEY",)
    catalog_id = "mem0--mem0-ai"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._mem = None
        self._run = run_tag()
        self._uid: dict[str, str] = {}

    # -- lifecycle -----------------------------------------------------------
    def _memory(self):
        if self._mem is None:
            mem0 = require("mem0", "mem0ai")
            cfg: dict = {
                "llm": {"provider": "openai", "config": {"model": self.extraction_model}},
                "embedder": {"provider": "openai", "config": {"model": self.embed_model}},
            }
            dims = EMBED_DIMS.get(self.embed_model)
            if dims and dims != 1536:
                # The default local Qdrant collection is created for 1536-d
                # vectors; other models need the size declared.
                # UNVERIFIED: key names `embedding_dims` (embedder) and
                # `embedding_model_dims` (qdrant) were not re-checked against
                # v2.2.1 source; only used when embed_model is not 1536-d.
                cfg["embedder"]["config"]["embedding_dims"] = dims
                cfg["vector_store"] = {"provider": "qdrant", "config": {"embedding_model_dims": dims}}
            self._mem = mem0.Memory.from_config(cfg)
        return self._mem

    def setup(self) -> None:
        self._memory()

    def reset(self, ns: str) -> None:
        # A fresh user id per run guarantees an empty namespace even if an
        # earlier run left data in the shared on-disk store; delete_all also
        # clears anything under this id.
        uid = f"{ns}-{self._run}"
        self._uid[ns] = uid
        try:
            self._memory().delete_all(user_id=uid)
        except Exception:
            pass

    def _user(self, ns: str) -> str:
        if ns not in self._uid:
            self.reset(ns)
        return self._uid[ns]

    def ingest(self, ns: str, session: Session, speakers: tuple[str, str]) -> None:
        msgs = []
        for t in session.turns:
            if not t.text:
                continue
            if t.speaker in ("user", "assistant"):        # LongMemEval
                role, content = t.speaker, t.text
            else:                                          # LoCoMo: named speakers
                # mem0's parse_messages reads only role+content, so the name
                # goes into the content, as mem0's own LoCoMo eval does.
                role = "user" if t.speaker == speakers[0] else "assistant"
                content = f"{t.speaker}: {t.text}"
            msgs.append({"role": role, "content": content})
        if not msgs:
            return
        metadata = {"session_id": session.id, "session_date": session.date}
        dt = parse_session_date(session.date)
        if dt is not None:
            metadata["created_at"] = dt.isoformat()
        self._memory().add(msgs, user_id=self._user(ns), metadata=metadata)

    def flush(self, ns: str) -> None:
        """Memory.add() in OSS is synchronous; nothing is pending."""

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        res = self._memory().search(query, top_k=k, filters={"user_id": self._user(ns)})
        items = res.get("results", []) if isinstance(res, dict) else (res or [])
        out = []
        for it in items:
            text = it.get("memory") if isinstance(it, dict) else None
            if not text:
                continue
            md = it.get("metadata") or {}
            when = md.get("session_date") or it.get("created_at") or ""
            out.append(f"[{when}] {text}" if when else text)
        return out

    def config(self) -> dict:
        return {**super().config(),
                "llm": f"openai/{self.extraction_model}",
                "embedder": f"openai/{self.embed_model}",
                "vector_store": "default (local qdrant)",
                "infer": True,
                "session_date": "metadata.created_at (OSS has no timestamp param)",
                "ingest_unit": "one add() per session"}
