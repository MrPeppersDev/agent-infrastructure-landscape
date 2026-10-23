"""Letta — archival memory (passages) of a Letta agent, via `letta-client`.

Verified against letta-client v1.12.1 (GitHub main, Oct 2026):
  https://github.com/letta-ai/letta-python/blob/main/README.md
  https://github.com/letta-ai/letta-python/blob/main/api.md
  https://github.com/letta-ai/letta-python/blob/main/src/letta_client/_client.py
  https://github.com/letta-ai/letta-python/blob/main/src/letta_client/types/agent_create_params.py
  https://github.com/letta-ai/letta-python/blob/main/src/letta_client/types/agents/passage_create_params.py
  https://github.com/letta-ai/letta-python/blob/main/src/letta_client/types/agents/passage_create_response.py
  https://github.com/letta-ai/letta-python/blob/main/src/letta_client/types/agents/passage_search_params.py
  https://github.com/letta-ai/letta-python/blob/main/src/letta_client/types/agents/passage_search_response.py

Calls: `Letta(api_key=, base_url=)` (api_key may be None for an
unauthenticated self-hosted server); `agents.create(name=, model=
"provider/model", embedding="provider/model") -> AgentState(.id)`;
`agents.passages.create(agent_id, text=, created_at=, tags=)` (POST
/v1/agents/{id}/archival-memory; the server embeds before returning);
`agents.passages.search(agent_id, query=, top_k=) -> PassageSearchResponse(
results=[Result(id, content, timestamp, tags)])`; `agents.delete(agent_id)`.

This measures Letta's archival store as a retrieval layer (one passage per
turn), not the agent's self-editing core memory: no agent messages are sent,
so the agent's LLM is never called.
"""

from __future__ import annotations

import os

from ..datasets import Session
from ._util import get, iso_utc, parse_session_date, run_tag, safe_id
from .base import MemoryAdapter, require


class Letta(MemoryAdapter):
    name = "letta"
    requires = ("letta-client>=1.12.1",)
    env = ("LETTA_BASE_URL",)
    catalog_id = "letta-memgpt--letta-com"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._client = None
        self._run = run_tag()
        self._agent: dict[str, str] = {}

    def _letta(self):
        if self._client is None:
            lc = require("letta_client", "letta-client")
            self._client = lc.Letta(api_key=os.environ.get("LETTA_API_KEY") or None,
                                    base_url=os.environ["LETTA_BASE_URL"])
        return self._client

    def setup(self) -> None:
        self._letta()

    def reset(self, ns: str) -> None:
        c = self._letta()
        old = self._agent.pop(ns, None)
        if old:
            try:
                c.agents.delete(old)
            except Exception:
                pass
        agent = c.agents.create(
            name=safe_id(f"bench-{ns}-{self._run}", maxlen=200),
            model=f"openai/{self.extraction_model}",
            embedding=f"openai/{self.embed_model}",
            tags=["memory-bench"],
        )
        self._agent[ns] = agent.id

    def _aid(self, ns: str) -> str:
        if ns not in self._agent:
            self.reset(ns)
        return self._agent[ns]

    def ingest(self, ns: str, session: Session, speakers: tuple[str, str]) -> None:
        c, aid = self._letta(), self._aid(ns)
        when = iso_utc(parse_session_date(session.date))
        for t in session.turns:
            if not t.text:
                continue
            kw: dict = {"text": f"{t.speaker}: {t.text}", "tags": [f"session:{session.id}"[:100]]}
            if when:
                kw["created_at"] = when
            c.agents.passages.create(aid, **kw)

    def flush(self, ns: str) -> None:
        """passages.create returns after the passage is embedded and stored."""

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        res = self._letta().agents.passages.search(self._aid(ns), query=query, top_k=k)
        out = []
        for r in get(res, "results") or []:
            text = get(r, "content")
            if not text:
                continue
            ts = get(r, "timestamp")
            out.append(f"[{ts}] {text}" if ts else text)
        return out

    def teardown(self) -> None:
        if self._client is None:
            return
        for aid in list(self._agent.values()):
            try:
                self._client.agents.delete(aid)
            except Exception:
                pass
        self._agent.clear()

    def config(self) -> dict:
        return {**super().config(),
                "agent_model": f"openai/{self.extraction_model} (never called)",
                "embedding": f"openai/{self.embed_model}",
                "write": "agents.passages.create, one passage per turn, created_at=session date",
                "read": "agents.passages.search (semantic, server default ranking)",
                "teardown": "deletes the run's agents"}
