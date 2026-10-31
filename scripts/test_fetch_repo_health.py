#!/usr/bin/env python3
"""Offline regression test for fetch_repo_health.py (#365): summarizing the
frozen API payloads in extraction/repo-health-fixtures/ must reproduce
expected.json. Run: python3 scripts/test_fetch_repo_health.py"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_repo_health as f  # noqa: E402

FIX = Path(__file__).resolve().parent.parent / "extraction" / "repo-health-fixtures"


def test_fixtures_reproduce_expected() -> None:
    expected = json.loads((FIX / "expected.json").read_text())
    today = dt.date(2026, 10, 31)
    got = {}
    for p in sorted(FIX.glob("*__*.json")):
        d = json.loads(p.read_text())
        got[p.stem] = f.summarize(d["repo"], d["issues"], d["releases"], d["contributors"], today)
    assert got == expected, {k: (got.get(k), expected.get(k)) for k in expected if got.get(k) != expected[k]}


if __name__ == "__main__":
    test_fixtures_reproduce_expected()
    print("fetch_repo_health: fixtures reproduce expected.json")
