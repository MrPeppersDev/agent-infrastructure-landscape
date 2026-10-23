"""Run the benchmark.

    python -m memory_bench.run --dataset longmemeval_s --per-type 10 \\
        --systems full-context,bm25,embedding-rag,mem0 --k 10

    python -m memory_bench.run --dataset smoke --fake --systems full-context,bm25   # offline

Writes results/runs/<run_id>/{config.json, answers.jsonl, summary.json}.
Re-running with the same --run-id resumes (questions already answered for
a system are skipped). `python -m memory_bench.report` builds the
leaderboard from all runs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from pathlib import Path

from . import __version__
from .adapters import BASELINES, MissingDependency, get
from .datasets import Dataset, load, sample
from .judge import ANSWER_SYSTEM, JUDGE_SYSTEM, answer_prompt, judge_prompt, parse_verdict
from .llm import Usage, make_llm

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "runs"


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, cwd=ROOT).stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def plan(ds: Dataset) -> dict:
    sessions = sum(len(c.sessions) for c in ds.conversations.values())
    turns = sum(len(s.turns) for c in ds.conversations.values() for s in c.sessions)
    chars = sum(len(t.text) for c in ds.conversations.values() for s in c.sessions for t in s.turns)
    by = defaultdict(int)
    for q in ds.questions:
        by[q.qtype] += 1
    return {"conversations": len(ds.conversations), "sessions": sessions, "turns": turns,
            "history_tokens_est": chars // 4, "questions": len(ds.questions), "by_type": dict(by)}


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(p * len(xs)))], 1)


def summarise(rows: list[dict]) -> dict:
    out: dict = {}
    by_sys: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_sys[r["system"]].append(r)
    for sysname, rs in by_sys.items():
        ok = [r for r in rs if r.get("error") is None]
        types: dict[str, list[bool]] = defaultdict(list)
        for r in ok:
            types[r["qtype"]].append(r["correct"])
        acc = lambda xs: round(100 * sum(xs) / len(xs), 1) if xs else None  # noqa: E731
        lat = [r["retrieve_ms"] for r in ok]
        out[sysname] = {
            "questions": len(rs), "answered": len(ok), "errors": len(rs) - len(ok),
            "accuracy": acc([r["correct"] for r in ok]),
            # macro average over question types, so large types don't dominate
            "accuracy_macro": round(statistics.mean(acc(v) for v in types.values()), 1) if types else None,
            "by_type": {t: {"n": len(v), "accuracy": acc(v)} for t, v in sorted(types.items())},
            "abstention_accuracy": acc([r["correct"] for r in ok if r["abstention"]]),
            "retrieve_ms_p50": pct(lat, 0.5), "retrieve_ms_p95": pct(lat, 0.95),
            "context_chars_mean": round(statistics.mean(r["context_chars"] for r in ok)) if ok else 0,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Neutral benchmark for agent memory layers")
    ap.add_argument("--dataset", default="longmemeval_s", help="longmemeval_s | longmemeval_oracle | locomo | smoke")
    ap.add_argument("--data-path", default=None, help="local dataset file instead of downloading")
    ap.add_argument("--systems", default=",".join(BASELINES))
    ap.add_argument("--limit", type=int, default=None, help="random subset of N questions")
    ap.add_argument("--per-type", type=int, default=None, help="N questions per question type (stratified)")
    ap.add_argument("--types", default=None, help="comma-separated question types to keep")
    ap.add_argument("--k", type=int, default=10, help="memories retrieved per question")
    ap.add_argument("--answer-model", default="gpt-4o-mini")
    ap.add_argument("--judge-model", default="gpt-4o")
    ap.add_argument("--extraction-model", default="gpt-4o-mini", help="LLM the memory systems use internally")
    ap.add_argument("--embed-model", default="text-embedding-3-small")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--out", default=str(RUNS))
    ap.add_argument("--fake", action="store_true", help="offline: deterministic fake LLM (tests only)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    args = ap.parse_args(argv)

    ds = load(args.dataset, args.data_path)
    ds = sample(ds, args.limit, args.types.split(",") if args.types else None, args.seed, args.per_type)
    p = plan(ds)
    print(json.dumps({"dataset": ds.name, **p}, indent=1))
    if args.dry_run:
        return 0

    run_id = args.run_id or f"{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{ds.name}"
    out = Path(args.out) / run_id
    out.mkdir(parents=True, exist_ok=True)
    answers_path = out / "answers.jsonl"
    done = set()
    if answers_path.exists():
        for line in answers_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r["system"], r["question_id"]))

    harness_usage = Usage()
    answer_llm = make_llm(args.answer_model, args.fake, harness_usage)
    judge_llm = make_llm(args.judge_model, args.fake, harness_usage)
    embed_llm = make_llm(args.answer_model, args.fake, harness_usage)  # for embedding-rag

    systems = [s.strip() for s in args.systems.split(",") if s.strip()]
    versions, configs, skipped = {}, {}, {}
    qs_by_conv: dict[str, list] = defaultdict(list)
    for q in ds.questions:
        qs_by_conv[q.conversation_id].append(q)

    with open(answers_path, "a") as fout:
        for sysname in systems:
            try:
                adapter = get(sysname)(llm=embed_llm, embed_model=args.embed_model,
                                       extraction_model=args.extraction_model)
                adapter.setup()
            except MissingDependency as e:
                print(f"skip {sysname}: {e}", file=sys.stderr)
                skipped[sysname] = str(e)
                continue
            versions[sysname], configs[sysname] = adapter.version(), adapter.config()
            ingest_s = []
            for ci, (cid, conv) in enumerate(sorted(ds.conversations.items())):
                todo = [q for q in qs_by_conv[cid] if (sysname, q.id) not in done]
                if not todo:
                    continue
                ns = f"bench-{run_id}-{cid}"[:120]
                err = None
                try:
                    t0 = time.perf_counter()
                    adapter.reset(ns)
                    for s in conv.sessions:
                        adapter.ingest(ns, s, conv.speakers)
                    adapter.flush(ns)
                    ingest_s.append((time.perf_counter() - t0) / max(1, len(conv.sessions)))
                except Exception:  # an adapter failure costs that conversation, not the run
                    err = traceback.format_exc(limit=3)
                for q in todo:
                    row = {"system": sysname, "question_id": q.id, "conversation_id": cid, "qtype": q.qtype,
                           "abstention": q.abstention, "question": q.text, "gold": q.answer, "error": err}
                    if err is None:
                        try:
                            t1 = time.perf_counter()
                            mems = adapter.retrieve(ns, q.text, args.k, q.date)
                            row["retrieve_ms"] = round((time.perf_counter() - t1) * 1000, 1)
                            hyp = answer_llm.chat(ANSWER_SYSTEM, answer_prompt(q.text, q.date, mems))
                            verdict = judge_llm.chat(JUDGE_SYSTEM, judge_prompt(q.text, q.answer, hyp, q.qtype, q.abstention), max_tokens=5)
                            row.update(hypothesis=hyp, correct=parse_verdict(verdict),
                                       memories=len(mems), context_chars=sum(len(m) for m in mems),
                                       memories_sample=mems[:3])
                        except Exception:
                            row["error"] = traceback.format_exc(limit=3)
                    fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                    fout.flush()
                print(f"[{sysname}] {ci + 1}/{len(ds.conversations)} conversations", file=sys.stderr)
            configs[sysname]["ingest_s_per_session_mean"] = round(statistics.mean(ingest_s), 2) if ingest_s else None
            adapter.teardown()

    rows = [json.loads(l) for l in answers_path.read_text().splitlines()]
    summary = {
        "run_id": run_id, "dataset": ds.name, "plan": p, "k": args.k,
        "answer_model": args.answer_model, "judge_model": args.judge_model,
        "extraction_model": args.extraction_model, "embed_model": args.embed_model,
        "fake": args.fake, "harness_version": __version__, "git_sha": git_sha(),
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "harness_cost_usd": harness_usage.cost(), "versions": versions, "configs": configs,
        "skipped": skipped, "systems": summarise(rows),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    (out / "config.json").write_text(json.dumps({k: v for k, v in vars(args).items()}, indent=1) + "\n")
    for s, v in summary["systems"].items():
        print(f"{s:16} accuracy {v['accuracy']}%  macro {v['accuracy_macro']}%  "
              f"n={v['answered']}/{v['questions']}  p50 {v['retrieve_ms_p50']}ms")
    print(f"results: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
