"""Offline end-to-end smoke test: fake LLM, built-in smoke dataset,
baselines only. Runs in CI on every PR that touches bench/.

    cd bench && python -m tests.test_smoke
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memory_bench import run  # noqa: E402
from memory_bench.datasets import Question, sample, smoke  # noqa: E402
from memory_bench.judge import parse_verdict  # noqa: E402


def main() -> int:
    failures = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal failures
        print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else f"  {detail}"))
        failures += 0 if cond else 1

    ds = smoke()
    check("smoke dataset has 4 questions", len(ds.questions) == 4)
    check("stratified sample keeps types", len(sample(ds, None, None, per_type=1).questions) == 3)
    check("verdict parse", parse_verdict("Yes.") and not parse_verdict("no"))

    with tempfile.TemporaryDirectory() as td:
        rc = run.main(["--dataset", "smoke", "--fake", "--systems", "full-context,bm25,embedding-rag",
                       "--run-id", "t", "--out", td, "--k", "3"])
        check("run exits 0", rc == 0)
        s = json.loads((Path(td) / "t" / "summary.json").read_text())
        systems = s["systems"]
        check("all three baselines reported", set(systems) == {"full-context", "bm25", "embedding-rag"}, str(systems.keys()))
        check("no errors", all(v["errors"] == 0 for v in systems.values()), json.dumps({k: v["errors"] for k, v in systems.items()}))
        fc = systems["full-context"]
        check("full-context answers the update question with the latest city",
              any(json.loads(l)["system"] == "full-context" and json.loads(l)["question_id"] == "smoke-1-q1" and json.loads(l)["correct"]
                  for l in (Path(td) / "t" / "answers.jsonl").read_text().splitlines()))
        check("full-context accuracy >= 50%", (fc["accuracy"] or 0) >= 50, str(fc["accuracy"]))
        check("by-type breakdown present", "knowledge-update" in fc["by_type"])
        # resume: a second call with the same run id adds nothing
        n1 = len((Path(td) / "t" / "answers.jsonl").read_text().splitlines())
        run.main(["--dataset", "smoke", "--fake", "--systems", "full-context", "--run-id", "t", "--out", td])
        n2 = len((Path(td) / "t" / "answers.jsonl").read_text().splitlines())
        check("resume skips answered questions", n1 == n2, f"{n1} -> {n2}")

    print(f"\n{failures} failure(s)" if failures else "\nsmoke test passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
