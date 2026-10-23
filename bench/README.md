# Memory benchmark

A neutral, reproducible benchmark for AI agent memory layers. In the [catalog](https://mrpeppersdev.github.io/agent-infrastructure-landscape/?product=memory), most memory products publish no comparable score, and almost every published number comes from the vendor. This harness runs every system the same way and publishes the code, the per-question outputs and the results.

## What's held constant

| Held constant | Default |
|---|---|
| Conversation history and questions | LongMemEval-S or LoCoMo, same deterministic sample (seed 7) |
| Answer model (turns retrieved memories into an answer) | `gpt-4o-mini` |
| Judge model (grades the answer) | `gpt-4o` |
| Memories retrieved per question | `k = 10` |
| Model each system uses internally for extraction | `gpt-4o-mini` |
| Embedding model where a system takes one | `text-embedding-3-small` |

**What varies:** only the memory layer. Each system ingests the history through its own write path and retrieves through its own read path, using its out-of-the-box defaults. Every non-default setting is recorded in the results.

## Datasets

- **[LongMemEval](https://github.com/xiaowu0162/LongMemEval)** (Wu et al., ICLR 2025). 500 questions, each with its own ~115k-token chat history of about 40 sessions.
  - **Question types:** single-session user / assistant / preference, multi-session, temporal reasoning, and **knowledge update**.
  - **Knowledge update** asks for the latest value after a fact changed. This is the "does memory handle contradictions" test.
  - **Abstention:** 30 questions (ids ending `_abs`) have no answer in the history, and the right response is "not mentioned".
- **[LoCoMo](https://github.com/snap-research/locomo)** (Maharana et al., ACL 2024). 10 very long two-speaker conversations with about 200 questions each. Category 5 (adversarial) is excluded by default.

The judge follows LongMemEval's design: an LLM decides whether the response contains the correct answer, with type-specific rules. Temporal answers can be off by one, and knowledge-update answers must give the latest value. The prompt wording is our own, so **scores are comparable within this harness**, not to numbers published elsewhere.

## Baselines

Every memory layer is shown next to these three:

- **`full-context`:** no memory system. The most recent turns that fit a 100k-token budget go straight into the prompt.
- **`bm25`:** lexical search over individual turns.
- **`embedding-rag`:** dense search over individual turns, using the same embedding model the memory layers get.

A memory layer that doesn't beat `embedding-rag` isn't adding anything on that question type.

## Systems

See [ADAPTERS.md](ADAPTERS.md) for each adapter's package version, API, required infrastructure and environment variables. `python -m memory_bench.requirements <systems>` prints the pip packages a run needs.

## Run it

```sh
cd bench
python -m tests.test_smoke                                   # offline, fake LLM, ~1 s

export OPENAI_API_KEY=...
python -m memory_bench.run --dataset longmemeval_s --per-type 10 --dry-run     # plan: questions, history size
pip install $(python -m memory_bench.requirements mem0)
python -m memory_bench.run --dataset longmemeval_s --per-type 10 \
    --systems full-context,bm25,embedding-rag,mem0
python -m memory_bench.report                                # → results/leaderboard.md
```

- **Output:** each run writes `results/runs/<run_id>/` containing `config.json`, `answers.jsonl` (one line per system × question, with the retrieved memories and the judge's verdict) and `summary.json`.
- **Resuming:** rerun with the same `--run-id` and questions already answered are skipped.
- **Other providers:** for any OpenAI-compatible endpoint, set `BENCH_LLM_BASE_URL` and `BENCH_LLM_API_KEY`.

**In GitHub Actions:** go to Actions → **Memory benchmark** → Run workflow, then choose dataset, systems and sample size. It needs the `OPENAI_API_KEY` repo secret, plus a key for each hosted system you include. Neo4j for Graphiti runs as a service container. Results are committed to a `bench/results-<run_id>` branch; open a PR from it to publish them.

**Cost:** a `--per-type 10` LongMemEval-S run (60 questions) costs a few dollars per system with the defaults. Ingestion dominates, because each system processes about 40 sessions per question. Run `--dry-run` first to see the plan.

## Reading the results

- **Macro accuracy:** the mean of the per-type accuracies, so the headline doesn't just reflect the biggest question type. This is the headline number.
- **Overall accuracy:** plain correct / answered.
- **Per-type columns:** read `knowledge-update` (does the system return the current fact rather than a stale one?) and `abstention` (does it avoid making things up?).
- **p50 retrieve:** median wall-clock time of the retrieval call only, not ingestion.
- **Errors:** an adapter error loses that conversation's questions for that system. They're counted in `errors`, never silently dropped.

## Adding a system

Subclass `MemoryAdapter` in `memory_bench/adapters/`, implementing `reset`, `ingest`, `flush` and `retrieve`. Register it in `adapters/__init__.py`, document it in `ADAPTERS.md`, and open a PR. Vendors are welcome to submit or correct their own adapter. The rule is that it uses the product's defaults and the same answer and judge models as everyone else.
