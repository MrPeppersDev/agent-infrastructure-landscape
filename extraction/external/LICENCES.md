# External-landscape sources — licence audit

Audit output for issue #118 (Phase 0 of the external-landscape ingestion
workstream). Each source below lists its upstream licence, the re-use
verdict for a CC-BY-4.0 downstream aggregation, the attribution string
we must carry when we cite it, the fetch date, and the upstream commit
SHA the vendored snapshot was pinned to. The vendored files live under
`extraction/external/<source-id>/<YYYYMMDD>/`.

Verdict vocabulary:

- `compatible` — no attribution required; re-use unrestricted.
- `attribution-required` — re-use permitted with attribution per the
  upstream licence; must carry the attribution string below.
- `incompatible` — bare re-use of the *compilation* is not safe. Facts
  (names, URLs) can still be extracted and independently verified;
  the upstream's curated selection/arrangement cannot be republished
  wholesale.

---

## `agentic-community`

- **Repo:** [agentic-community/agentic-landscape](https://github.com/agentic-community/agentic-landscape)
- **Vendored file:** `extraction/external/agentic-community/20260701/data.yml`
- **Upstream path:** `agentic-landscape/data.yml`
- **Upstream commit SHA:** `45ee78b33a3864659fb5f77161afa9b15f751d4c`
- **Fetch date:** 2026-07-01
- **SHA-256 of snapshot:** `fdd7911dc0c83d6fe12deed753e832fada1ed49fc404ed923abeadb563761c4e`
- **Upstream licence:** Apache-2.0 (SPDX-detected; `LICENSE` file present at repo root)
- **Re-use verdict:** `attribution-required`
- **Attribution string:**
  > Data from the Agentic Community landscape
  > (github.com/agentic-community/agentic-landscape), licensed under
  > Apache-2.0.

## `antgroup`

- **Repo:** [antgroup/agentic-ai-landscape](https://github.com/antgroup/agentic-ai-landscape)
- **Vendored file:** `extraction/external/antgroup/20260701/agentic-ai-projects.csv`
- **Upstream path:** `data/agentic-ai-projects.csv`
- **Upstream commit SHA:** `6467938c0d8c759db183e1653b31aa682c5c6935`
- **Fetch date:** 2026-07-01
- **SHA-256 of snapshot:** `261addbeafbfbd6620343ffdf62e676ca2d8af86cb57026b1d29dd019204eeb1`
- **Upstream licence:** **None declared.** No `LICENSE` / `LICENCE` /
  `COPYING` file at repo root; no licence statement in `README.md`.
  Under default copyright rules the compilation is all-rights-reserved.
- **Re-use verdict:** `incompatible`
- **Impact on downstream phases:**
  - Phase 1 (**diff**) — permitted. Set-difference against our catalog is
    fact-checking, not republication.
  - Phase 3 (**intake**) — permitted only if each candidate row we open
    is independently verified against primary sources; do not cite the
    antgroup CSV as the primary source URL.
  - Phase 4 (**cross-listing corroboration**) — do **not** import the
    antgroup category assignment as a T1/T2 cited claim on catalog
    rows. Their curation is the copyrightable slice.
  - Phase 5 (**standing-source polling**) — hold. Re-evaluate if the
    upstream adds a licence.
- **Recommended follow-up:** open a courtesy issue on the upstream repo
  asking for an explicit licence grant (Apache-2.0 or CC-BY-4.0 would
  both unblock everything). Do not import their compilation until then.
- **Attribution string** (only if their licence stance changes):
  > Data from the InclusionAI Agentic AI Landscape
  > (github.com/antgroup/agentic-ai-landscape), used with permission.

## `yc-sylph`

- **Repo:** [SylphAI-Inc/yc-agent-landscape](https://github.com/SylphAI-Inc/yc-agent-landscape)
- **Vendored file:** `extraction/external/yc-sylph/20260701/yc_agent_companies_ai.csv`
- **Upstream path:** `data/yc_agent_companies_ai.csv`
- **Upstream commit SHA:** `f3f9cb44477e66bc40aadfd7f9de47fb06f38a64`
- **Fetch date:** 2026-07-01
- **SHA-256 of snapshot:** `0dea850b29255f2efa1f1931627821bef9165dfd13641d8d44e6b46a27a6088c`
- **Upstream licence:** MIT (declared in `README.md` under `## 📄
  License`; no `LICENSE` file at repo root, but the README declaration
  is a valid licence grant under standard interpretation).
- **Re-use verdict:** `attribution-required`
- **Recommended follow-up:** open a courtesy issue on the upstream
  asking them to add a `LICENSE` file at the repo root so the grant is
  machine-detectable. Non-blocking.
- **Attribution string:**
  > Company classifications derived from the SylphAI YC Agent
  > Landscape (github.com/SylphAI-Inc/yc-agent-landscape), licensed
  > under MIT.

## `ombharatiya`

- **Repo:** [ombharatiya/ai-system-design-guide](https://github.com/ombharatiya/ai-system-design-guide)
- **Vendored file:** `extraction/external/ombharatiya/20260701/01-tool-use-landscape.md`
- **Upstream path:** `17-tool-use-and-computer-agents/01-tool-use-landscape.md`
- **Upstream commit SHA:** `42cb011ff752f153e4c5003a93539765578769fe`
- **Fetch date:** 2026-07-01
- **SHA-256 of snapshot:** `4ba5e94e6743ad32d04ab311b96bad7c360ab548e192268338142c7a6d053bca`
- **Upstream licence:** MIT (SPDX-detected; `LICENSE` file present at
  repo root).
- **Re-use verdict:** `attribution-required`
- **Attribution string:**
  > Benchmarks and adoption figures cited from the AI System Design
  > Guide chapter "The 2026 Tool-Use and Computer Agent Landscape"
  > (github.com/ombharatiya/ai-system-design-guide), licensed under MIT.

---

## Summary table

| Source | Licence | Verdict | Blocks any downstream phase? |
|---|---|---|---|
| `agentic-community` | Apache-2.0 | `attribution-required` | No |
| `antgroup` | None declared | `incompatible` | **Yes — blocks Phases 4 & 5; Phases 1 & 3 fact-only** |
| `yc-sylph` | MIT (README-declared) | `attribution-required` | No |
| `ombharatiya` | MIT | `attribution-required` | No |
