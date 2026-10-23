"""Graphiti — `graphiti-core` temporal knowledge graph on Neo4j.

Verified against graphiti-core v0.30.x (GitHub main, Sep 2026):
  https://github.com/getzep/graphiti/blob/main/graphiti_core/graphiti.py
  https://github.com/getzep/graphiti/blob/main/graphiti_core/edges.py
  https://github.com/getzep/graphiti/blob/main/graphiti_core/helpers.py
  https://github.com/getzep/graphiti/blob/main/graphiti_core/llm_client/config.py
  https://github.com/getzep/graphiti/blob/main/graphiti_core/llm_client/openai_client.py
  https://github.com/getzep/graphiti/blob/main/graphiti_core/embedder/openai.py
  https://github.com/getzep/graphiti/blob/main/graphiti_core/utils/maintenance/graph_data_operations.py
  https://github.com/getzep/graphiti/blob/main/examples/quickstart/quickstart_neo4j.py

API facts this adapter depends on:
- `Graphiti(uri, user, password, llm_client=, embedder=)`; cross-encoder left
  at its default (`OpenAIRerankerClient()`).
- `OpenAIClient(config=LLMConfig(model=...))`, `OpenAIEmbedder(config=
  OpenAIEmbedderConfig(embedding_model=...))`.
- async `build_indices_and_constraints()`, `add_episode(name=, episode_body=,
  source_description=, reference_time=, source=EpisodeType.message,
  group_id=)` (awaits full extraction), `search(query, group_ids=,
  num_results=) -> list[EntityEdge]` with `.fact/.valid_at/.invalid_at`,
  `close()`.
- async `clear_data(driver, group_ids=[...])` deletes one group.
- group ids must match ^[a-zA-Z0-9_-]+$.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from ..datasets import Session
from ._util import AsyncRunner, parse_session_date, run_tag, safe_id
from .base import MemoryAdapter, require


class Graphiti(MemoryAdapter):
    name = "graphiti"
    requires = ("graphiti-core>=0.30.0",)
    env = ("OPENAI_API_KEY", "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD")
    catalog_id = "zep-graphiti--getzep-com"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._g = None
        self._aio: AsyncRunner | None = None
        self._run = run_tag()
        self._gid: dict[str, str] = {}

    def _run_async(self, coro):
        if self._aio is None:
            self._aio = AsyncRunner()
        return self._aio.run(coro)

    def _graph(self):
        if self._g is None:
            require("graphiti_core", "graphiti-core")
            from graphiti_core import Graphiti as _Graphiti
            from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
            from graphiti_core.llm_client.config import LLMConfig
            from graphiti_core.llm_client.openai_client import OpenAIClient

            self._g = _Graphiti(
                os.environ["NEO4J_URI"], os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"],
                llm_client=OpenAIClient(config=LLMConfig(model=self.extraction_model)),
                embedder=OpenAIEmbedder(config=OpenAIEmbedderConfig(embedding_model=self.embed_model)),
            )
            self._run_async(self._g.build_indices_and_constraints())
        return self._g

    def setup(self) -> None:
        self._graph()

    def _group(self, ns: str) -> str:
        if ns not in self._gid:
            self.reset(ns)
        return self._gid[ns]

    def reset(self, ns: str) -> None:
        g = self._graph()
        gid = safe_id(f"{ns}-{self._run}", maxlen=200)
        self._gid[ns] = gid
        from graphiti_core.utils.maintenance.graph_data_operations import clear_data
        self._run_async(clear_data(g.driver, group_ids=[gid]))

    def ingest(self, ns: str, session: Session, speakers: tuple[str, str]) -> None:
        from graphiti_core.nodes import EpisodeType

        body = "\n".join(f"{t.speaker}: {t.text}" for t in session.turns if t.text)
        if not body:
            return
        when = parse_session_date(session.date) or datetime.now(timezone.utc)
        self._run_async(self._graph().add_episode(
            name=f"session {session.id}",
            episode_body=body,
            source_description=f"chat session ({session.date})" if session.date else "chat session",
            reference_time=when,
            source=EpisodeType.message,
            group_id=self._group(ns),
        ))

    def flush(self, ns: str) -> None:
        """add_episode() awaits extraction and indexing; nothing is pending."""

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        edges = self._run_async(self._graph().search(query, group_ids=[self._group(ns)], num_results=k))
        out = []
        for e in edges or []:
            fact = getattr(e, "fact", None)
            if not fact:
                continue
            va, ia = getattr(e, "valid_at", None), getattr(e, "invalid_at", None)
            span = ""
            if va or ia:
                span = f"[{va.isoformat() if va else '?'} - {ia.isoformat() if ia else 'present'}] "
            out.append(span + fact)
        return out

    def teardown(self) -> None:
        if self._g is not None:
            try:
                self._run_async(self._g.close())
            finally:
                self._g = None
        if self._aio is not None:
            self._aio.close()
            self._aio = None

    def config(self) -> dict:
        return {**super().config(),
                "llm": f"openai/{self.extraction_model} (small_model left at default)",
                "embedder": f"openai/{self.embed_model}",
                "cross_encoder": "default",
                "graph_db": "neo4j",
                "search": "Graphiti.search (default hybrid edge search)",
                "ingest_unit": "one EpisodeType.message episode per session, reference_time=session date"}
