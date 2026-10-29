# Star counts in prose (#326), 2026-10-29

A frozen star count in a `claims`, `desc` or `pros` cell contradicts the live `gh` cell on the same page. Mem0, for example, showed "~67.3k stars" in At a glance and "~51k★" under Claims. The new `stars-in-prose` check in `scripts/lint_contradictions.py` flags this. It found **173 cells on 163 records**, and it now reports 0.

**What changed** (`apply.py`, rerunnable on the pre-change data):

- **135 standalone clauses.** Examples are "Traction: ~2.3k GitHub stars", "; ~5k stars;" and "~7.7k★;". These were removed by rule in `strip.py`.
- **38 in-sentence cases.** These were edited by hand, one replacement each, listed in `manual.py`. Only the star figure and its connecting words were removed.

Two cells needed more than a removal:

- **Zep & Graphiti `claims`:** the cell opened with "Graphiti at 24.3k★.". It now reads "Graphiti is its open-source graph engine.", which restates the record's own name.
- **Mem0 `pros` and `claims`:** both said Mem0 is the *exclusive* memory provider for the AWS Agent SDK. Primary sources don't support exclusivity:
  - Mem0's [partnership announcement](https://mem0.ai/blog/aws-and-mem0-partner-to-bring-persistent-memory-to-next-gen-ai-agents-with-strands) (2025-05-19) describes a Strands integration.
  - AWS documents its own [AgentCore Memory integration for Strands](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/strands-sdk-memory.html).
  - So the `pros` clause was dropped, and the `claims` sentence now reads "Integrated memory provider for AWS's Strands Agents SDK (AWS partnership, 2025-05; not exclusive: AWS also offers AgentCore Memory for Strands)."

Some removed counts belonged to a related repository, not the row's own repo: a parent monorepo (Kong, PurpleLlama, modelcontextprotocol/servers) or a community implementation. They were removed as well, since the page's `gh` cell is the place for star counts.
