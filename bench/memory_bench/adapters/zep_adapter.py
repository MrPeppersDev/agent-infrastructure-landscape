"""Zep Cloud — `zep-cloud` SDK, user graph built from thread messages.

Written for the v4 SDK (zep-cloud 4.0.1 on GitHub main; help.getzep.com now
documents v4 and keeps v3 under /v3/). A v3 code path (zep-cloud 3.25.0) is
kept for installs that still resolve to 3.x; the adapter picks one by
feature detection.

v4 sources:
  https://github.com/getzep/zep-python/blob/main/pyproject.toml           (4.0.1)
  https://github.com/getzep/zep-python/blob/main/src/zep_cloud/user/client.py
  https://github.com/getzep/zep-python/blob/main/src/zep_cloud/thread/client.py
  https://github.com/getzep/zep-python/blob/main/src/zep_cloud/graph/client.py
  https://github.com/getzep/zep-python/blob/main/src/zep_cloud/task/client.py
  https://github.com/getzep/zep-python/blob/main/src/zep_cloud/types/{add_message,add_messages_result,task,user,thread,edge}.py
  https://github.com/getzep/zep-python/blob/main/src/zep_cloud/core/pagination.py
  https://help.getzep.com/adding-messages        (<=30 messages/call, 4,096 chars/message)
v3 sources:
  https://github.com/getzep/zep-python/blob/v3.25.0/reference.md
  https://github.com/getzep/zep-python/blob/v3.25.0/src/zep_cloud/types/{message,add_thread_messages_response,graph_search_results,entity_edge}.py
  https://help.getzep.com/v3/check-data-ingestion-status

v4 calls: `user.create(user_id=) -> User(.uuid_, .graph_uuid)`,
`thread.create(user_uuid=) -> Thread(.uuid_)`,
`thread.add_messages(thread_uuid, messages=[AddMessage(role, name, content,
reference_time)]) -> AddMessagesResult(.task: Task)`, `task.get(task_uuid) ->
Task(.status in pending|processing|succeeded|partial|failed)`,
`graph.search_edges(graph_uuid, query=, page_size=) -> SyncPager[Edge]`
(first page = `.items`), `user.delete(user_uuid)`.
"""

from __future__ import annotations

import os
from collections import defaultdict

from ..datasets import Session
from ._util import chunks, get, iso_utc, parse_session_date, poll, run_tag, split_text
from .base import MemoryAdapter, require

_MAX_MSGS_PER_CALL = 30
_MAX_CHARS = 4096
_TERMINAL = {"succeeded", "partial", "failed", "completed"}


class Zep(MemoryAdapter):
    name = "zep"
    requires = ("zep-cloud>=3.25.0",)
    env = ("ZEP_API_KEY",)
    catalog_id = "zep-graphiti--getzep-com"

    def __init__(self, *a, flush_timeout: float = 3600.0, **kw):
        super().__init__(*a, **kw)
        self.flush_timeout = flush_timeout
        self._client = None
        self._run = run_tag()
        self._user: dict[str, dict] = {}       # ns -> {"id": addressable id, "graph": graph uuid}
        self._tasks: dict[str, list[str]] = defaultdict(list)

    def _zep(self):
        if self._client is None:
            zc = require("zep_cloud", "zep-cloud")
            self._client = zc.Zep(api_key=os.environ["ZEP_API_KEY"])
            self._v4 = hasattr(self._client.graph, "search_edges")
        return self._client

    def setup(self) -> None:
        self._zep()

    # -- namespace -----------------------------------------------------------
    def reset(self, ns: str) -> None:
        c = self._zep()
        old = self._user.pop(ns, None)
        if old:
            try:
                c.user.delete(old["id"]) if self._v4 else c.user.delete(user_id=old["id"])
            except Exception:
                pass
        ext = f"{ns}-{self._run}"[:500]
        if self._v4:
            u = c.user.create(user_id=ext)
            self._user[ns] = {"id": u.uuid_, "graph": u.graph_uuid or u.uuid_}
        else:
            c.user.add(user_id=ext)
            self._user[ns] = {"id": ext, "graph": ext}
        self._tasks[ns] = []

    def _u(self, ns: str) -> dict:
        if ns not in self._user:
            self.reset(ns)
        return self._user[ns]

    # -- write ---------------------------------------------------------------
    def ingest(self, ns: str, session: Session, speakers: tuple[str, str]) -> None:
        zc = require("zep_cloud", "zep-cloud")
        c, u = self._zep(), self._u(ns)
        when = iso_utc(parse_session_date(session.date))
        msgs = []
        for t in session.turns:
            if not t.text:
                continue
            if t.speaker in ("user", "assistant"):
                role = t.speaker
            else:
                role = "user" if t.speaker == speakers[0] else "assistant"
            # Zep rejects messages over 4,096 chars by default: split, never drop.
            for piece in split_text(t.text, _MAX_CHARS):
                kw = {"role": role, "name": t.speaker, "content": piece}
                if self._v4:
                    if when:
                        kw["reference_time"] = when
                    msgs.append(zc.AddMessage(**kw))
                else:
                    if when:
                        kw["created_at"] = when
                    msgs.append(zc.Message(**kw))
        if not msgs:
            return
        if self._v4:
            thread = c.thread.create(user_uuid=u["id"])
            tid = thread.uuid_
        else:
            tid = f"{u['id']}-{session.id}"[:200]
            c.thread.create(thread_id=tid, user_id=u["id"])
        for batch in chunks(msgs, _MAX_MSGS_PER_CALL):
            res = c.thread.add_messages(tid, messages=batch)
            task_id = get(get(res, "task"), "uuid_") if self._v4 else get(res, "task_id")
            if task_id:
                self._tasks[ns].append(task_id)

    def flush(self, ns: str) -> None:
        c = self._zep()
        pending = list(self._tasks.get(ns, []))

        def done() -> bool:
            while pending:
                t = c.task.get(pending[0]) if self._v4 else c.task.get(task_id=pending[0])
                if (get(t, "status") or "").lower() not in _TERMINAL:
                    return False
                pending.pop(0)
            return True

        poll(done, self.flush_timeout, interval=3.0, what=f"zep graph ingestion for {ns}")
        self._tasks[ns] = []

    # -- read ----------------------------------------------------------------
    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        c, u = self._zep(), self._u(ns)
        if self._v4:
            edges = c.graph.search_edges(u["graph"], query=query, page_size=k).items or []
        else:
            res = c.graph.search(user_id=u["id"], query=query, scope="edges", limit=min(k, 50))
            edges = res.edges or []
        out = []
        for e in edges:
            fact = get(e, "fact")
            if not fact:
                continue
            va, ia = get(e, "valid_at"), get(e, "invalid_at")
            span = f"[{va or '?'} - {ia or 'present'}] " if (va or ia) else ""
            out.append(span + fact)
        return out[:k]

    def teardown(self) -> None:
        if self._client is None:
            return
        for ns in list(self._user):
            try:
                uid = self._user[ns]["id"]
                self._client.user.delete(uid) if self._v4 else self._client.user.delete(user_id=uid)
            except Exception:
                pass
        self._user.clear()

    def config(self) -> dict:
        return {**super().config(),
                "llm": "zep-managed (not configurable)",
                "embedder": "zep-managed (not configurable)",
                "sdk_api": "v4" if getattr(self, "_v4", True) else "v3",
                "write": "one thread per session; add_messages in batches of 30; messages >4096 chars split",
                "session_date": "AddMessage.reference_time (v4) / Message.created_at (v3)",
                "read": "graph edge search over the user graph, default reranker (rrf)",
                "teardown": "deletes the run's users"}
