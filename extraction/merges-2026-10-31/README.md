# Jamba duplicate merge (2026-10-31)

Found while testing fit-first ranking (#359): AI21 Labs' Jamba model surfaced as the runner-up memory layer in the support-agent stack.

- `jamba-ai21-labs--ai21-com` (ai21.com/jamba, filed under "Dedicated memory layers") and `jamba-ai21--ai21-com` (the launch post, filed under "Recent method papers") describe the same model family.
- `rules.json` folds the second into the first with `scripts/merge_records.py`; the dropped id redirects to the kept one (`taxonomy/system-aliases.json`).
- The kept record's section is then set by hand to **Foundation models (substrate reference)**, where the other model families live. Its own description says what it is: "Israeli production model. Interleaves Mamba SSM layers with Transformer attention…" ([ai21.com/jamba](https://www.ai21.com/jamba/)).

No cell values changed beyond the merge.

# Benchmark-pass duplicates (2026-11-01)

The benchmark-URL research pass (`extraction/benchmark-sources-2026-10-31/REPORT.md`, Follow-ups) found three duplicate pairs. `rules-benchmark-dups.json` merges them with `scripts/merge_records.py` (log: `log-benchmark-dups.json`). In each pair the record with more real-data cells is kept, and the old ids redirect.

| Kept | Dropped | Why |
|---|---|---|
| `anthropic-computer-use--docs-anthropic-com` | `anthropic-computer-use--anthropic-com` | Same tool: its docs page and its October 2024 launch post. The kept record moves to **Computer-use & desktop agents**, next to OpenAI Operator and Browser Use. |
| `openhands-all-hands-ai--all-hands-dev`, renamed **OpenHands** | `opendevin-openhands--gh-all-hands-ai-openhands` | Same project: OpenHands, formerly OpenDevin, maintained by All Hands AI. |
| `metagpt-harness--gh-foundationagents-metagpt`, renamed **MetaGPT** | `metagpt--gh-geekan-metagpt` | Same repository: github.com/geekan/MetaGPT serves FoundationAgents/MetaGPT. |

Inherited benchmark scores were removed in the same PR. Seven rows had a `capability-benchmark-sources` estimate copied from the model they run on, so a `--no-llm` sweep scored them as if they were models. The rows are Claude memory, Managed Agents memory, Bedrock AgentCore memory, Microsoft Copilot memory, ChatGPT memory, Mistral Agents API and the OpenAI Realtime API. Each cell now says it has no benchmark of its own and points to the model row (old and new text: `extraction/benchmark-sources-2026-10-31/inherited-neutralised-2026-11-01.json`). The `--no-llm` dry run now scores 35 rows, down from 42.
