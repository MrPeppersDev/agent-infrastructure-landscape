"""Supermemory — `supermemory` Python SDK (3.x line, container tags).

Verified against supermemory v3.62.0 (2026-09-14), the latest stable 3.x:
  https://github.com/supermemoryai/python-sdk/blob/v3.62.0/src/supermemory/types/client_add_params.py
  https://github.com/supermemoryai/python-sdk/blob/v3.62.0/src/supermemory/types/add_response.py
  https://github.com/supermemoryai/python-sdk/blob/v3.62.0/src/supermemory/types/search_memories_params.py
  https://github.com/supermemoryai/python-sdk/blob/v3.62.0/src/supermemory/types/search_memories_response.py
  https://github.com/supermemoryai/python-sdk/blob/v3.62.0/src/supermemory/types/document_get_response.py
  https://github.com/supermemoryai/python-sdk/blob/v3.62.0/src/supermemory/types/document_delete_bulk_params.py
  https://github.com/supermemoryai/python-sdk/blob/main/api.md
  https://github.com/supermemoryai/python-sdk/blob/main/CHANGELOG.md

The SDK's 5.0 line (5.0.0rc1, 2026-10-04) replaces container tags with
namespaces (`client.add(namespace, content=...)`, `client.search(namespace,
query=...)`); it is a release candidate, so this adapter pins `<5`.

Calls: `client.add(content=, container_tag=, metadata=, document_date=) ->
AddResponse(id, status)`; `client.documents.get(id).status` in unknown |
queued | extracting | chunking | embedding | indexing | done | failed, and
`.dreaming_status` in dreaming | done; `client.search.memories(q=,
container_tag=, limit=) -> results[].memory / .chunk / .metadata`;
`client.documents.delete_bulk(container_tags=[...])`.
"""

from __future__ import annotations

import os
from collections import defaultdict

from ..datasets import Session
from ._util import get, iso_utc, parse_session_date, poll, run_tag, safe_id
from .base import MemoryAdapter, require

_DOC_DONE = {"done", "failed"}


class Supermemory(MemoryAdapter):
    name = "supermemory"
    requires = ("supermemory>=3.62.0,<5",)
    env = ("SUPERMEMORY_API_KEY",)
    catalog_id = "supermemory--supermemory-ai"

    def __init__(self, *a, flush_timeout: float = 3600.0, wait_for_dreaming: bool = True, **kw):
        super().__init__(*a, **kw)
        self.flush_timeout = flush_timeout
        self.wait_for_dreaming = wait_for_dreaming
        self._client = None
        self._run = run_tag()
        self._tag: dict[str, str] = {}
        self._docs: dict[str, list[str]] = defaultdict(list)

    def _sm(self):
        if self._client is None:
            sm = require("supermemory", "supermemory")
            self._client = sm.Supermemory(api_key=os.environ["SUPERMEMORY_API_KEY"])
        return self._client

    def setup(self) -> None:
        self._sm()

    def _ctag(self, ns: str) -> str:
        if ns not in self._tag:
            self.reset(ns)
        return self._tag[ns]

    def reset(self, ns: str) -> None:
        # container tags: max 100 chars, alphanumerics, '-', '_' and '.'
        tag = safe_id(f"{ns}-{self._run}", maxlen=100, allowed=r"A-Za-z0-9_.-")
        self._tag[ns] = tag
        self._docs[ns] = []
        try:
            self._sm().documents.delete_bulk(container_tags=[tag])
        except Exception:
            pass  # nothing under a fresh tag

    def ingest(self, ns: str, session: Session, speakers: tuple[str, str]) -> None:
        lines = [f"{t.speaker}: {t.text}" for t in session.turns if t.text]
        if not lines:
            return
        kw: dict = {
            "content": "\n".join(lines),
            "container_tag": self._ctag(ns),
            "metadata": {"session_id": session.id, "session_date": session.date or ""},
        }
        when = iso_utc(parse_session_date(session.date))
        if when:
            kw["document_date"] = when
        res = self._sm().add(**kw)
        if get(res, "id"):
            self._docs[ns].append(res.id)

    def flush(self, ns: str) -> None:
        c = self._sm()
        pending = list(self._docs.get(ns, []))

        def done() -> bool:
            while pending:
                d = c.documents.get(pending[0])
                if get(d, "status") not in _DOC_DONE:
                    return False
                if self.wait_for_dreaming and get(d, "status") == "done" and get(d, "dreaming_status") not in (None, "done"):
                    return False
                pending.pop(0)
            return True

        poll(done, self.flush_timeout, interval=3.0, what=f"supermemory processing for {ns}")
        self._docs[ns] = []

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        res = self._sm().search.memories(q=query, container_tag=self._ctag(ns), limit=k)
        out = []
        for r in get(res, "results") or []:
            text = get(r, "memory") or get(r, "chunk")
            if not text:
                continue
            md = get(r, "metadata") or {}
            when = md.get("session_date") if isinstance(md, dict) else None
            out.append(f"[{when}] {text}" if when else text)
        return out

    def config(self) -> dict:
        return {**super().config(),
                "llm": "supermemory-managed (not configurable)",
                "embedder": "supermemory-managed (not configurable)",
                "write": "client.add per session (task_type default 'memory', dreaming default 'dynamic')",
                "session_date": "document_date",
                "read": "search.memories (search_mode default 'memories', rerank/rewrite off)",
                "flush_waits_for_dreaming": self.wait_for_dreaming}
