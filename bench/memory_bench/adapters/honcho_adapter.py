"""Honcho — `honcho-ai` SDK: workspace / peers / sessions, with Honcho's
background deriver building per-peer representations (conclusions).

Verified against honcho-ai v2.5.1 (GitHub main, Oct 2026):
  https://github.com/plastic-labs/honcho/blob/main/sdks/python/README.md
  https://github.com/plastic-labs/honcho/blob/main/sdks/python/pyproject.toml
  https://github.com/plastic-labs/honcho/blob/main/sdks/python/src/honcho/client.py
  https://github.com/plastic-labs/honcho/blob/main/sdks/python/src/honcho/peer.py
  https://github.com/plastic-labs/honcho/blob/main/sdks/python/src/honcho/session.py
  https://github.com/plastic-labs/honcho/blob/main/sdks/python/src/honcho/api_types.py
  https://github.com/plastic-labs/honcho/blob/main/src/schemas/api.py   (<=100 msgs/batch, id pattern)
  https://github.com/plastic-labs/honcho/blob/main/src/config.py        (MAX_MESSAGE_SIZE 25,000)

Calls: `Honcho(api_key=, base_url=, workspace_id=)`; `honcho.peer(id)`;
`honcho.session(id)`; `session.add_peers([...])`; `session.add_messages(
[peer.message(content, metadata=, created_at=)])`; `honcho.queue_status()
-> QueueStatusResponse(pending_work_units, in_progress_work_units, ...)`;
`peer.representation(search_query=, search_top_k=) -> str`;
`honcho.delete_workspace(workspace_id)`.

Isolation: one workspace per namespace (fresh id per run). Retrieval: the
query-conditioned representation of every peer seen in the namespace
(Honcho's derived memory), split into lines. `peer.chat` (Honcho's own
LLM answer) is not used.
"""

from __future__ import annotations

import os

from ..datasets import Session
from ._util import chunks, parse_session_date, poll, run_tag, safe_id, split_text
from .base import MemoryAdapter, MissingDependency, require

_MAX_BATCH = 100
_MAX_CHARS = 25_000


class Honcho(MemoryAdapter):
    name = "honcho"
    requires = ("honcho-ai>=2.5.1",)
    env = ()  # HONCHO_API_KEY (managed) or HONCHO_BASE_URL (self-hosted); checked below
    catalog_id = "honcho-plastic-labs--honcho-dev"

    def __init__(self, *a, flush_timeout: float = 3600.0, **kw):
        super().__init__(*a, **kw)
        if not (os.environ.get("HONCHO_API_KEY") or os.environ.get("HONCHO_BASE_URL")):
            raise MissingDependency(f"{self.name}: set HONCHO_API_KEY or HONCHO_BASE_URL")
        self.flush_timeout = flush_timeout
        self._run = run_tag()
        self._ws: dict[str, str] = {}
        self._clients: dict[str, object] = {}
        self._peers: dict[str, dict[str, object]] = {}

    def _new_client(self, workspace_id: str):
        hc = require("honcho", "honcho-ai")
        kw: dict = {"workspace_id": workspace_id}
        if os.environ.get("HONCHO_API_KEY"):
            kw["api_key"] = os.environ["HONCHO_API_KEY"]
        if os.environ.get("HONCHO_BASE_URL"):
            kw["base_url"] = os.environ["HONCHO_BASE_URL"]
        return hc.Honcho(**kw)

    def reset(self, ns: str) -> None:
        old = self._ws.pop(ns, None)
        if old and ns in self._clients:
            try:
                self._clients[ns].delete_workspace(old)
            except Exception:
                pass
        ws = safe_id(f"{ns}-{self._run}", maxlen=512)
        self._ws[ns] = ws
        self._clients[ns] = self._new_client(ws)
        self._peers[ns] = {}

    def _h(self, ns: str):
        if ns not in self._clients:
            self.reset(ns)
        return self._clients[ns]

    def _peer(self, ns: str, speaker: str):
        peers = self._peers.setdefault(ns, {})
        if speaker not in peers:
            peers[speaker] = self._h(ns).peer(safe_id(speaker, maxlen=512))
        return peers[speaker]

    def ingest(self, ns: str, session: Session, speakers: tuple[str, str]) -> None:
        h = self._h(ns)
        turns = [t for t in session.turns if t.text]
        if not turns:
            return
        sess = h.session(safe_id(session.id, maxlen=512))
        names = list(dict.fromkeys([*speakers, *(t.speaker for t in turns)]))
        sess.add_peers([self._peer(ns, s) for s in names])
        when = parse_session_date(session.date)
        msgs = []
        for t in turns:
            for piece in split_text(t.text, _MAX_CHARS):
                kw: dict = {"metadata": {"session_date": session.date or ""}}
                if when is not None:
                    kw["created_at"] = when
                msgs.append(self._peer(ns, t.speaker).message(piece, **kw))
        for batch in chunks(msgs, _MAX_BATCH):
            sess.add_messages(batch)

    def flush(self, ns: str) -> None:
        h = self._h(ns)

        def done() -> bool:
            s = h.queue_status()
            return (s.pending_work_units or 0) == 0 and (s.in_progress_work_units or 0) == 0

        poll(done, self.flush_timeout, interval=3.0, what=f"honcho deriver queue for {ns}")

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        self._h(ns)
        out: list[str] = []
        for name, peer in self._peers.get(ns, {}).items():
            rep = peer.representation(search_query=query, search_top_k=min(max(k, 1), 100))
            for line in (rep or "").splitlines():
                line = line.strip()
                if line:
                    out.append(f"[{name}] {line}")
        return out

    def teardown(self) -> None:
        for ns, ws in list(self._ws.items()):
            try:
                self._clients[ns].delete_workspace(ws)
            except Exception:
                pass
        self._ws.clear()
        self._clients.clear()
        self._peers.clear()

    def config(self) -> dict:
        return {**super().config(),
                "llm": "honcho server config (not set by the adapter)",
                "embedder": "honcho server config (not set by the adapter)",
                "write": "one honcho session per dataset session; messages attributed to speaker peers; created_at=session date",
                "read": "peer.representation(search_query, search_top_k) for every peer, lines prefixed with peer name",
                "teardown": "deletes the run's workspaces"}
