# Jamba duplicate merge (2026-10-31)

Found while testing fit-first ranking (#359): AI21 Labs' Jamba model surfaced as the runner-up memory layer in the support-agent stack.

- `jamba-ai21-labs--ai21-com` (ai21.com/jamba, filed under "Dedicated memory layers") and `jamba-ai21--ai21-com` (the launch post, filed under "Recent method papers") describe the same model family.
- `rules.json` folds the second into the first with `scripts/merge_records.py`; the dropped id redirects to the kept one (`taxonomy/system-aliases.json`).
- The kept record's section is then set by hand to **Foundation models (substrate reference)**, where the other model families live. Its own description says what it is: "Israeli production model. Interleaves Mamba SSM layers with Transformer attention…" ([ai21.com/jamba](https://www.ai21.com/jamba/)).

No cell values changed beyond the merge.
