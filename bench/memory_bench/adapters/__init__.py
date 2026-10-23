"""Adapter registry. Entries are "module:Class" so optional SDKs are only
imported when that system is actually requested."""

from __future__ import annotations

import importlib

from .base import MemoryAdapter, MissingDependency

REGISTRY: dict[str, str] = {
    # baselines (no extra dependencies)
    "full-context": "baselines:FullContext",
    "bm25": "baselines:BM25",
    "embedding-rag": "baselines:EmbeddingRAG",
}

BASELINES = ("full-context", "bm25", "embedding-rag")


def get(name: str) -> type[MemoryAdapter]:
    if name not in REGISTRY:
        raise SystemExit(f"unknown system {name!r}; known: {', '.join(sorted(REGISTRY))}")
    mod, cls = REGISTRY[name].split(":")
    return getattr(importlib.import_module(f".{mod}", __name__), cls)


__all__ = ["REGISTRY", "BASELINES", "get", "MemoryAdapter", "MissingDependency"]
