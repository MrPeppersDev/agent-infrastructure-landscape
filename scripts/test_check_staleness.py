"""
test_check_staleness.py — unit tests for scripts/check_staleness.py.

Focus: the reserved-namespace guard in extract_repo (#168), which stops
github.com product/docs routes (features/, copilot/, …) from being parsed
as `owner/repo` and 404-flagged as abandoned.

Run:  python3 scripts/test_check_staleness.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_staleness import extract_repo  # noqa: E402


def _rec(citation=None, url=None, value=None):
    return {"cells": {"gh": {"citation": citation, "value": value}}, "url": url}


def test_real_repo_from_citation():
    got = extract_repo(_rec(citation="https://github.com/openai/retro"))
    assert got == ("openai", "retro", "https://github.com/openai/retro"), got


def test_real_repo_strips_trailing_path_and_git():
    assert extract_repo(_rec(citation="https://github.com/danijar/crafter/tree/main"))[:2] == ("danijar", "crafter")
    assert extract_repo(_rec(citation="https://github.com/allenai/RL4LMs.git"))[:2] == ("allenai", "RL4LMs")


def test_reserved_features_copilot_is_not_a_repo():
    # github-copilot-agent-mode: url is github.com/features/copilot (#168 false positive)
    assert extract_repo(_rec(url="https://github.com/features/copilot")) is None


def test_reserved_copilot_route_is_not_a_repo():
    # github-copilot-custom-instructions: gh citation github.com/copilot/customizing-copilot
    assert extract_repo(_rec(citation="https://github.com/copilot/customizing-copilot")) is None


def test_reserved_is_skipped_but_real_candidate_still_wins():
    # If a reserved URL and a real repo are both present, the real repo is returned.
    rec = _rec(citation="https://github.com/features/copilot",
               url="https://github.com/octocat/Hello-World")
    assert extract_repo(rec) == ("octocat", "Hello-World", "https://github.com/octocat/Hello-World")


def test_reserved_matching_is_case_insensitive():
    assert extract_repo(_rec(citation="https://github.com/Features/Copilot")) is None


def test_no_github_url_returns_none():
    assert extract_repo(_rec(url="https://magnitude.run/")) is None


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
