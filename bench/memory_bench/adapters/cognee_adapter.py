"""cognee — knowledge-graph memory, local default stack (LanceDB + Ladybug/Kuzu
graph + SQLite).

Verified against cognee v1.5.3 (GitHub main / docs, Aug–Oct 2026):
  https://github.com/topoteretes/cognee  (README: remember / recall / improve / forget)
  https://github.com/topoteretes/cognee/blob/main/cognee/api/v1/remember/remember.py
  https://github.com/topoteretes/cognee/blob/main/cognee/api/v1/recall/recall.py
  https://github.com/topoteretes/cognee/blob/main/cognee/api/v1/search/search.py
  https://docs.cognee.ai/python-api/recall.md
  https://docs.cognee.ai/python-api/remember.md
  https://docs.cognee.ai/python-api/forget
  https://docs.cognee.ai/setup-configuration/overview.md

cognee 1.x's documented entry points are `remember` (= add + cognify +
improve, awaited to completion by default) and `recall` (auto-routed
search). The older add / cognify / search functions still exist underneath,
but the README no longer presents them, so this adapter uses the current
recommended pair:

- `await cognee.remember(list_of_texts, dataset_name=ds)`; one text document
  per session, with the session date in a header line (cognee has no
  per-item timestamp argument; its default pipeline extracts dates from text
  as Timestamp nodes).
- `await cognee.recall(query, datasets=[ds], top_k=k, only_context=True)` ->
  list[RecallResponse]; with only_context=True cognee makes no completion
  call and each item's `.text` is the retrieved context (for completion
  search types, the full prompt cognee would have sent its LLM).
- `await cognee.forget(dataset=ds)`; raises DatasetNotFoundError if absent.
- `cognee.config.set("llm_model" | "embedding_model" | "embedding_dimensions"
  | "llm_api_key", value)`; model names use the "provider/model" form.
"""

from __future__ import annotations

import os
from collections import defaultdict

from ..datasets import Session
from ._util import EMBED_DIMS, AsyncRunner, get, run_tag, safe_id
from .base import MemoryAdapter, require


class Cognee(MemoryAdapter):
    name = "cognee"
    requires = ("cognee>=1.5.3",)
    env = ("OPENAI_API_KEY",)
    catalog_id = "cognee--cognee-ai"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._cg = None
        self._aio: AsyncRunner | None = None
        self._run = run_tag()
        self._ds: dict[str, str] = {}
        self._pending: dict[str, list[str]] = defaultdict(list)

    def _run_async(self, coro):
        if self._aio is None:
            self._aio = AsyncRunner()
        return self._aio.run(coro)

    def _cognee(self):
        if self._cg is None:
            # cognee reads LLM_API_KEY at import; values in a local .env take
            # precedence over os.environ, so also set it programmatically.
            os.environ.setdefault("LLM_API_KEY", os.environ["OPENAI_API_KEY"])
            cg = require("cognee", "cognee")
            cg.config.set("llm_api_key", os.environ["LLM_API_KEY"])
            cg.config.set("llm_model", f"openai/{self.extraction_model}")
            cg.config.set("embedding_model", f"openai/{self.embed_model}")
            dims = EMBED_DIMS.get(self.embed_model)
            if dims:
                cg.config.set("embedding_dimensions", dims)
            self._cg = cg
        return self._cg

    def setup(self) -> None:
        self._cognee()

    def _dataset(self, ns: str) -> str:
        if ns not in self._ds:
            self.reset(ns)
        return self._ds[ns]

    def reset(self, ns: str) -> None:
        cg = self._cognee()
        ds = safe_id(f"{ns}_{self._run}", maxlen=200, allowed=r"A-Za-z0-9_")
        self._ds[ns] = ds
        self._pending[ns] = []
        try:
            self._run_async(cg.forget(dataset=ds))
        except Exception:
            pass  # DatasetNotFoundError: a fresh name is already empty

    def ingest(self, ns: str, session: Session, speakers: tuple[str, str]) -> None:
        self._dataset(ns)
        lines = [f"{t.speaker}: {t.text}" for t in session.turns if t.text]
        if not lines:
            return
        header = f"Conversation session {session.id}"
        if session.date:
            header += f" — date: {session.date}"
        self._pending[ns].append(header + "\n" + "\n".join(lines))

    def flush(self, ns: str) -> None:
        """Runs remember() (add + cognify + improve) over every buffered
        session and waits for it to finish (run_in_background defaults to
        False)."""
        docs, self._pending[ns] = self._pending[ns], []
        if docs:
            self._run_async(self._cognee().remember(docs, dataset_name=self._dataset(ns)))

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        cg = self._cognee()
        try:
            results = self._run_async(cg.recall(query, datasets=[self._dataset(ns)], top_k=k, only_context=True))
        except Exception as e:  # empty / never-cognified dataset
            # Only DatasetNotFoundError is documented (forget/recall docs); the
            # other two names are tolerated defensively, anything else raises.
            if type(e).__name__ in ("DatasetNotFoundError", "NoDataError", "SearchOnEmptyGraphError"):
                return []
            raise
        out = []
        for r in results or []:
            if get(r, "source") == "system":  # warm-up / build-status marker
                continue
            text = get(r, "text") or get(r, "context") or get(r, "answer")
            if text:
                out.append(text if isinstance(text, str) else str(text))
        return out

    def teardown(self) -> None:
        if self._aio is not None:
            self._aio.close()
            self._aio = None

    def config(self) -> dict:
        return {**super().config(),
                "llm": f"openai/{self.extraction_model} (cognee default: openai/gpt-5.6-luna)",
                "embedder": f"openai/{self.embed_model} (cognee default: openai/text-embedding-3-large)",
                "write": "remember() per conversation (add+cognify+improve, self_improvement default on)",
                "read": "recall(auto_route default, only_context=True) — returns retrieved context, not cognee's answer",
                "session_date": "header line in each session document (no timestamp param)",
                "stores": "default (lancedb, ladybug graph, sqlite)"}
