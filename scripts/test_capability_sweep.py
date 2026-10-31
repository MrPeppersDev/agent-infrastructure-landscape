#!/usr/bin/env python3
"""Offline tests for capability_sweep.py's stdlib paths (#128/#129): the
benchmark-mention parser, URL extraction and the benchmark-maxima refresh.
Run: python3 scripts/test_capability_sweep.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capability_sweep as cs  # noqa: E402

FAMILIES = {"swe-bench-verified": "code", "aider-polyglot": "code", "osworld": "agentic", "ruler": "longcontext"}

CELL = (
    "swe-bench-verified: 80.9% (Claude Opus 4.5, 2025-11-24) https://www.anthropic.com/news/claude-opus-4-5 · "
    "osworld 66.3% (Claude Opus 4.5, 2025-11-24) https://www.anthropic.com/news/claude-opus-4-5 · "
    "aider-polyglot: 89.0% (2025-11) https://aider.chat/docs/leaderboards/ · "
    "mmlu: 92.0% (excluded family) https://example.org/x"
)


def test_parse_scores_whole_numbers() -> None:
    got = [(o.id, o.score, o.family) for o in cs.parse_naive_observations(CELL, FAMILIES)]
    assert got == [
        ("swe-bench-verified", 80.9, "code"),
        ("osworld", 66.3, "agentic"),
        ("aider-polyglot", 89.0, "code"),
    ], got


def test_parse_variants() -> None:
    assert [(o.id, o.score) for o in cs.parse_naive_observations("SWE-bench Verified: 74.4%", FAMILIES)] == [("swe-bench-verified", 74.4)]
    assert [(o.id, o.score) for o in cs.parse_naive_observations("RULER ~ 95%", FAMILIES)] == [("ruler", 95.0)]
    assert cs.parse_naive_observations("general capability estimate — no specific benchmark", FAMILIES) == []


def test_extract_urls_and_placeholders() -> None:
    assert cs.extract_urls(CELL) == [
        "https://www.anthropic.com/news/claude-opus-4-5",
        "https://aider.chat/docs/leaderboards/",
        "https://example.org/x",
    ]
    assert cs.is_placeholder_text("not applicable — hardware maker")
    assert not cs.is_placeholder_text(CELL)


def test_maxima_from_catalog_cells() -> None:
    records = [
        {"id": "a", "cells": {"capability-benchmark-sources": {"value": CELL}}},
        {"id": "b", "cells": {"capability-benchmark-sources": {"value": "swe-bench-verified: 85.0% (x) https://e.org · osworld: 61.0% https://e.org"}}},
        {"id": "c", "cells": {"capability-benchmark-sources": {"value": "not applicable — robot maker"}}},
        {"id": "d", "cells": {}},
        # An estimate without a source URL must not move a ceiling.
        {"id": "e", "cells": {"capability-benchmark-sources": {"value": "SWE-bench Verified ~99% (2026), inherits frontier model"}}},
    ]
    got = cs.compute_benchmark_maxima(records, FAMILIES)
    assert list(got) == ["aider-polyglot", "osworld", "swe-bench-verified"], list(got)
    assert got["swe-bench-verified"] == {"max": 85.0, "min": 0.0, "rows": 2, "top_row": "b"}, got["swe-bench-verified"]
    assert got["osworld"] == {"max": 66.3, "min": 0.0, "rows": 2, "top_row": "a"}
    assert got["aider-polyglot"]["rows"] == 1


if __name__ == "__main__":
    test_parse_scores_whole_numbers()
    test_parse_variants()
    test_extract_urls_and_placeholders()
    test_maxima_from_catalog_cells()
    print("capability_sweep: parser, URL extraction and maxima refresh ok")
