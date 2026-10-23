"""The one interface every memory system implements.

A run calls, for each conversation:

    adapter.reset(ns)                    # fresh, isolated namespace (user / group / dataset)
    for session in conversation.sessions:
        adapter.ingest(ns, session, conversation.speakers)   # system's own write path
    adapter.flush(ns)                    # wait for async extraction / indexing to finish
    for question in its questions:
        adapter.retrieve(ns, question.text, k, question.date) -> list[str]   # system's own read path

The harness then answers from the returned strings with the shared answer
model. Adapters must not see questions before ingestion is complete, and
must not use gold answers.

Writing an adapter: subclass MemoryAdapter, set `name`, `requires`
(pip packages) and `env` (required environment variables), implement
ingest/retrieve (and reset/flush if the system needs them), and register
it in adapters/__init__.py. Keep the system's defaults — this benchmark
measures what a builder gets out of the box — and record any non-default
setting in `config()` so it lands in the results.
"""

from __future__ import annotations

import os
from typing import Any

from ..datasets import Session


class MissingDependency(RuntimeError):
    pass


class MemoryAdapter:
    #: short id used on the command line and in results
    name: str = "base"
    #: pip requirements, for the error message and the workflow matrix
    requires: tuple[str, ...] = ()
    #: environment variables that must be set
    env: tuple[str, ...] = ()
    #: link to the catalog record, for the leaderboard
    catalog_id: str | None = None

    def __init__(self, llm: Any = None, embed_model: str = "text-embedding-3-small",
                 extraction_model: str = "gpt-4o-mini", **options: Any):
        self.llm = llm
        self.embed_model = embed_model
        self.extraction_model = extraction_model
        self.options = options
        missing = [v for v in self.env if not os.environ.get(v)]
        if missing:
            raise MissingDependency(f"{self.name}: set {', '.join(missing)}")

    # -- lifecycle -----------------------------------------------------------
    def setup(self) -> None:
        """Called once per run before any namespace is used."""

    def reset(self, ns: str) -> None:
        """Start an empty, isolated memory for namespace `ns`."""

    def ingest(self, ns: str, session: Session, speakers: tuple[str, str]) -> None:
        raise NotImplementedError

    def flush(self, ns: str) -> None:
        """Block until everything ingested into `ns` is searchable."""

    def retrieve(self, ns: str, query: str, k: int, date: str = "") -> list[str]:
        raise NotImplementedError

    def teardown(self) -> None:
        """Called once at the end of the run."""

    # -- reporting -----------------------------------------------------------
    def config(self) -> dict:
        return {"name": self.name, "embed_model": self.embed_model,
                "extraction_model": self.extraction_model, **self.options}

    def version(self) -> str:
        """Installed package version(s), recorded with every result."""
        out = []
        for req in self.requires:
            pkg = req.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip()
            try:
                from importlib.metadata import version
                out.append(f"{pkg}=={version(pkg)}")
            except Exception:
                out.append(f"{pkg}==?")
        return ", ".join(out) or "builtin"


def session_text(session: Session, with_date: bool = True) -> list[str]:
    """One string per turn, prefixed with the session date — the shared
    rendering used by the baselines."""
    pre = f"[{session.date}] " if with_date and session.date else ""
    return [f"{pre}{t.speaker}: {t.text}" for t in session.turns]


def require(module: str, pip_name: str):
    try:
        return __import__(module, fromlist=["_"])
    except ImportError as e:
        raise MissingDependency(f"pip install {pip_name}  ({e})") from e
