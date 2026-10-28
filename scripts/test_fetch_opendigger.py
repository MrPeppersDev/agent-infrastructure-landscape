#!/usr/bin/env python3
"""Offline regression test for fetch_opendigger.py (issue #150).

The fixtures in extraction/opendigger-fixtures/ are a frozen fetch of five
repos. Summarizing them must reproduce expected.json byte for byte, so a
change to the cell format shows up here rather than in the catalog.
Run: python3 scripts/test_fetch_opendigger.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_opendigger as f  # noqa: E402

FIX = Path(__file__).resolve().parent.parent / "extraction" / "opendigger-fixtures"


def test_fixtures_reproduce_expected() -> None:
    expected = json.loads((FIX / "expected.json").read_text())
    got = {p.stem: f.cell_value(f.summarize(json.loads(p.read_text())))
           for p in sorted(FIX.glob("*__*.json"))}
    assert got == expected, {k: (got.get(k), expected.get(k)) for k in expected if got.get(k) != expected[k]}
    for value in got.values():
        obj = json.loads(value)
        assert set(obj) == {"activity", "as_of", "openrank_12mo", "openrank_current", "participants"}


def test_missing_repo_has_no_summary() -> None:
    assert f.summarize({"repo": "a/b", "missing": True}) is None
    assert f.summarize({"repo": "a/b", "openrank": {}}) is None


def test_twelve_month_mean() -> None:
    raw = {"openrank": {f"2025-{m:02d}": 1.0 for m in range(1, 13)} | {"2026-01": 13.0},
           "activity": {"2026-01": 5}, "participants": {}}
    s = f.summarize(raw)
    assert s["as_of"] == "2026-01" and s["openrank_current"] == 13.0
    assert s["openrank_12mo"] == round((11 * 1.0 + 13.0) / 12, 2)
    assert s["activity"] == 5 and s["participants"] is None


def test_repo_for() -> None:
    rec = {"url": "https://github.com/mem0ai/mem0", "cells": {}}
    assert f.repo_for(rec) == "mem0ai/mem0"
    rec = {"url": "https://mem0.ai", "cells": {"gh": {"citation": "https://github.com/mem0ai/mem0/tree/main"}}}
    assert f.repo_for(rec) == "mem0ai/mem0"
    assert f.repo_for({"url": "https://github.com/orgs/foo/people", "cells": {}}) is None
    assert f.repo_for({"url": "https://example.com", "cells": {}}) is None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  PASS {t.__name__}")
    print(f"all {len(tests)} opendigger tests passed")
