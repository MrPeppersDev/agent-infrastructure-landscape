# Use-case taxonomy (companion to the 6-axis system-side schema)

**Date:** 2026-05-06
**Companion to:** `taxonomy/schema.md` (6-axis system-side), `landscape.html` (520 rows × 60 system-side columns)
**Purpose:** A controlled vocabulary of *use cases* (demand-side archetypes) against which
catalog systems can be scored for fit. The 6-axis schema captures *what a system is*; this
file captures *what a system is for*. Together they enable "best fit for X" matching.

---

## Rationale

The catalog is rich on the supply side — 60 system-side columns covering taxonomy,
deployment, compliance, latency, modalities, runtimes, MCP/A2A, governance,
multi-tenancy, conflict resolution, forgetting policy, etc. — but has no canonical
demand-side vocabulary. Without it, "which memory system is right for a clinical-voice
agent on HIPAA?" has no programmable answer; the catalog is queryable by capability but
not by fit.

This file defines **18 use-case archetypes**. Each archetype is:

- **Specific enough** that it actually distinguishes which systems are usable —
  HIPAA-required cuts the field from 520 to ~9; SOX + auditable cuts again.
- **General enough** that it covers a population of real deployments rather than a
  single product. "Coding agent for individual dev (IDE-integrated)" covers Cursor /
  Cline / Aider / Continue / Copilot / Claude Code / Cody / Windsurf / Zed AI users —
  not just one of them.

The taxonomy is deliberately user-and-deployment shaped, not feature shaped. That is
the axis on which the catalog is currently *under*-described, and the axis a buyer
or architect actually thinks along.

---

## Scoring schema

A system is scored against a use case in three sequential stages. Anti-requirements
are eliminative; required capabilities are gating; preferences are weighted-additive.
The hierarchy means a perfect preference score cannot save a system that fails an
anti-requirement, and a system that just barely meets all requirements outranks a
system that fails any of them.

### Stage 1 — Anti-requirement filter (hard eliminator)

For each anti-requirement on the use case, evaluate the corresponding system-side
column. If the system's value matches the anti-requirement, **score = 0, eliminated**.
No further evaluation. Examples:

- Use case `clinical-voice-scribe` has anti-requirement `compliance ∌ HIPAA`. Any
  system whose `Compliance` column does not list HIPAA → eliminated.
- Use case `enterprise-coding-team` has anti-requirement `data-handling: trains on
  customer data`. Any system whose `Data handling` column says "trains on prompts"
  → eliminated.
- Use case `pkm-lifelogger` has anti-requirement `deployment: SaaS-only`. Any system
  whose `Deployment` column lacks self-host → eliminated *for buyers in this UC who
  weight ownership*. (Soft variant: see "preference-only" anti-requirements below.)

### Stage 2 — Required-capability gate (hard requirements)

For each required capability, the system must declare a satisfying value in the
corresponding column. **Missing data ≠ pass.** A system whose `Compliance` column
is empty fails any compliance-required gate. This is intentional: an undeclared
capability cannot be relied on for high-stakes use cases.

If any required capability is unmet, the system passes through to Stage 3 with a
penalty (see weighting below) rather than being fully eliminated, because some
required capabilities are *strongly* preferred but not absolute. Each requirement
has a flag: `R-hard` (eliminate if missing) vs `R-soft` (penalty if missing). Most
compliance and deployment requirements are `R-hard`; most modality and persistence
requirements are `R-soft`.

### Stage 3 — Preference-weighted additive score

For each preference dimension `d_i` with weight `w_i ∈ [0, 5]`, compute a match
score `s_i ∈ [0, 1]` (1 = perfect match, 0 = absent / data missing). Total fit:

```
fit(system, use_case) =
    Σ_i (w_i × s_i)   for all preferences
  − Σ_j (penalty_j)   for unmet R-soft requirements
  × confidence_factor   based on how many system-side columns are populated
```

The `confidence_factor ∈ [0.3, 1.0]` discounts systems with sparse catalog data —
a system with 50/60 columns populated should outrank one with 20/60 even if both
appear to match, because the latter's apparent fit is partly hallucinated absence.

### Stage 4 — Tie-break heuristics

When two systems score within ±5% of each other, break ties by (in order):

1. Higher `Integration count` (Mem0 / LangChain / vector-DB hub effect)
2. More recent `Latest release` (active maintenance)
3. Lower `Pricing` for cost-sensitive UCs / higher `Compliance` count for regulated UCs
4. Higher `Mindshare` / `GitHub stars` (community sustainability)

---

## Use-case archetypes

Each archetype below has the same structure. Where a dimension references a specific
system-side column from `landscape.html`, that column name appears verbatim. Where the
catalog has no column for a dimension, that gap is flagged in the *Gap analysis*
section at the end.

Weight scale: `5` = critical preference, `3` = strong preference, `1` = nice-to-have.

---

### UC-01 — Personal AI assistant for individual user

**Description.** A long-running personal assistant that remembers preferences, prior
conversations, ongoing projects, and personal context across days and weeks. Single
user, single tenant, no organisational data. Examples include ChatGPT-with-memory,
Claude Projects, and Mem0-backed personal agents.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Persistence ⊇ {cross-session, long-term}` (R-hard); `Memory model ⊇ {profile, episode}` (R-hard); `API surface` declared (R-soft) |
| **Strong preferences** | `Governance ∈ {editable, inspectable, user-controllable}` (w=5); `Update ∈ {extraction, agent-controlled, consolidation}` (w=3); single-user pricing tier in `Pricing` (w=3); `Modalities ⊇ {text}` (w=5); `MCP support` (w=3) |
| **Anti-requirements** | `Governance = opaque` AND no edit path (eliminative); `Data handling: trains on customer data` (eliminative); `Pricing: enterprise contract only` (eliminative for individual UC) |
| **Modality** | Text required; voice nice-to-have |
| **Deployment** | SaaS or self-host both acceptable |
| **Persistence horizon** | `cross-session` minimum, `long-term` preferred, `lifelong` ideal |
| **Governance posture** | `editable` preferred so user can correct mistakes; `auditable` not required |
| **Throughput / latency** | Conversational latency (p99 < 3s); throughput trivial (single user) |
| **Scale envelope** | Single user, ≲ 10⁵ memories, ≲ 100 MB |
| **Budget profile** | Free or per-seat ≲ $20/mo |

---

### UC-02 — PKM / lifelogger

**Description.** Tools for capturing, organising, and retrieving the user's personal
knowledge — notes, web clippings, calendar events, emails, voice memos, sometimes
sensor data. Distinct from UC-01 by being substrate-first (the *user* curates and
queries) rather than agent-first. Examples: Reflect, mem.ai, Heyday, Recall, Apple
Notes-with-AI.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Persistence ∈ {long-term, lifelong}` (R-hard); user can read all stored content (R-hard); `Import / export` declared and bidirectional (R-soft) |
| **Strong preferences** | `Governance ∈ {editable, user-controllable}` (w=5); `Deployment ⊇ {self-host}` (w=3, ownership preference); markdown / file primitives in `Memory primitives` (w=3); `Versioning` non-trivial (w=3) |
| **Anti-requirements** | `Data handling: trains on customer data` (eliminative); no export path (eliminative); `Persistence < cross-session` |
| **Modality** | Text required; voice + image strong preference (w=3) |
| **Deployment** | Self-host strongly preferred; SaaS acceptable if export works |
| **Persistence horizon** | `lifelong` (years-scale) |
| **Governance posture** | `user-controllable` mandatory; `editable`; `auditable` nice-to-have |
| **Throughput / latency** | Interactive search latency (p99 < 1s); ingest can be batch |
| **Scale envelope** | Single user, 10⁵–10⁷ items, GB-scale |
| **Budget profile** | Free, one-time, or per-seat ≲ $15/mo |

---

### UC-03 — Coding agent for individual developer (IDE-integrated)

**Description.** Memory layer behind an IDE-integrated coding assistant for a single
developer. Remembers the working repo, recent edits, build errors, code conventions,
and developer preferences across sessions. Examples: Cursor + Mem0, Cline, Aider,
Claude Code with CLAUDE.md, Zed AI, Continue.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Persistence ∈ {session, cross-session}` (R-hard); `Memory model ⊇ {file, episode}` (R-hard); `Latency p50` ≲ 500ms (R-soft) |
| **Strong preferences** | `Programmatic control` declared (w=5); `Governance ∈ {editable, inspectable}` (w=5); `Memory primitives ⊇ {file}` (w=5, CLAUDE.md pattern); `Runtimes ⊇ {local}` (w=3); `MCP support` (w=3) |
| **Anti-requirements** | `Data handling: trains on customer data` (eliminative for proprietary code); `Latency p99 > 2s` (degrades editor UX) |
| **Modality** | Text + code; image nice-to-have for screenshots |
| **Deployment** | Local or self-host strongly preferred (proprietary code concerns) |
| **Persistence horizon** | `cross-session` minimum |
| **Governance posture** | `editable` (developer must be able to correct) |
| **Throughput / latency** | p50 < 200ms, p99 < 1s; throughput moderate |
| **Scale envelope** | 1 developer, 10⁴–10⁶ memories, repo-scale |
| **Budget profile** | Free or per-seat ≲ $20/mo |

---

### UC-04 — Coding agent for enterprise dev team

**Description.** Memory layer behind a coding assistant deployed across a 50–10,000
developer engineering org. Must respect repo permissions, integrate with code-review
workflows, and never leak between teams. Examples: GitHub Copilot Enterprise, Cursor
for Teams, Sourcegraph Cody Enterprise, Claude Code for organisations.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Multi-tenancy` declared with isolation guarantees (R-hard); `SSO / RBAC` (R-hard); `Compliance ⊇ {SOC 2}` (R-hard); `Audit log` / `auditable` governance (R-hard); `Deployment ⊇ {self-host or VPC}` (R-soft) |
| **Strong preferences** | `Encryption: at-rest + in-transit` (w=5); `Namespace primitives` per-team (w=5); `Programmatic control` for admin APIs (w=5); `Webhooks / events` (w=3); `OTel` (w=3); `Integration count` ≥ 5 (w=3) |
| **Anti-requirements** | `Data handling: trains on customer data` (eliminative); single-tenant only when 1000+ devs (eliminative); `Compliance` empty (eliminative — undeclared compliance fails procurement) |
| **Modality** | Text + code |
| **Deployment** | Self-host or dedicated VPC required |
| **Persistence horizon** | `long-term` |
| **Governance posture** | `auditable` mandatory; `deterministic` for permission boundaries |
| **Throughput / latency** | p99 < 1s; throughput 10²–10⁴ QPS |
| **Scale envelope** | Org-wide, 10⁶–10⁹ memories |
| **Budget profile** | Enterprise contract, $100k–$10M ARR |

---

### UC-05 — Customer support agent (SaaS multi-tenant)

**Description.** A vendor-hosted memory layer behind a customer-support copilot used
across many tenants (one tenant = one of the vendor's customers). Each tenant's
support history, KB, and product context must be strictly isolated. Examples: Intercom
Fin, Ada, Forethought, Zendesk AI, Salesforce Einstein Service.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Multi-tenancy` declared with strong isolation (R-hard); `Namespace primitives` per-tenant (R-hard); `SSO / RBAC` (R-hard); `Compliance ⊇ {SOC 2, GDPR}` (R-hard) |
| **Strong preferences** | `Governance ⊇ {auditable}` (w=5); `Forgetting policy` declared with TTL/eviction (w=5, GDPR right-to-be-forgotten); `Webhooks / events` (w=3); `API surface ⊇ {REST, streaming}` (w=3); `Conflict res ∈ {deterministic, structured}` (w=3) |
| **Anti-requirements** | `Multi-tenancy: shared` (eliminative); no per-tenant `Forgetting policy` (eliminative under GDPR); `Data handling: trains on customer data` (eliminative) |
| **Modality** | Text required; voice strong (w=3, phone support) |
| **Deployment** | SaaS acceptable; VPC option preferred for enterprise tenants |
| **Persistence horizon** | `long-term` |
| **Governance posture** | `auditable` mandatory |
| **Throughput / latency** | p99 < 1s; throughput 10³–10⁵ QPS aggregate |
| **Scale envelope** | 10²–10⁴ tenants, 10⁷–10⁹ memories aggregate |
| **Budget profile** | Per-seat or per-conversation, vendor-margin model |

---

### UC-06 — Contact-center memory (high-throughput)

**Description.** Memory behind an automated voice contact-center handling 10³–10⁶
concurrent calls. Distinguished from UC-05 by *throughput* and *real-time voice*
constraints — not just chat. Examples: Five9 AI, Cresta, Observe.AI, Genesys AI.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Modalities ⊇ {voice}` (R-hard); `Throughput ≥ 10³ QPS` (R-hard); `Latency p99 < 300ms` (R-hard for real-time turn); `Multi-tenancy` per agent / per call (R-hard); `Compliance ⊇ {PCI-DSS, SOC 2}` (R-hard, payment context) |
| **Strong preferences** | `Encryption: in-transit + at-rest` (w=5); `Forgetting policy: per-call eviction` (w=5); `Session handling` declared (w=5); `Auditable` (w=3) |
| **Anti-requirements** | Text-only system (eliminative — must handle voice latency budget); p99 ≥ 1s (eliminative); single-tenant (eliminative) |
| **Modality** | Voice + text |
| **Deployment** | Self-host or dedicated VPC |
| **Persistence horizon** | `session` to `cross-session` (call → caller history) |
| **Governance posture** | `auditable` for QA + dispute |
| **Throughput / latency** | p99 < 200ms; throughput 10³–10⁶ QPS |
| **Scale envelope** | 10⁵–10⁷ calls/day |
| **Budget profile** | Enterprise contract |

---

### UC-07 — Healthcare clinical-voice scribe (HIPAA + voice)

**Description.** Ambient AI scribe for clinicians — captures the patient encounter,
maintains patient longitudinal context, drafts notes for EHR. Examples: Abridge,
Suki, DeepScribe, Microsoft DAX, Nuance DAX.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Compliance ⊇ {HIPAA, BAA}` (R-hard); `Encryption: at-rest + in-transit` (R-hard); `Modalities ⊇ {voice, text}` (R-hard); `Audit log` per access (R-hard); `Data handling: no training, no third-party sharing` (R-hard) |
| **Strong preferences** | `Deployment ⊇ {VPC, self-host}` (w=5); `Governance: auditable` (w=5); `SSO / RBAC` per provider (w=5); `Forgetting policy` for state-mandated retention (w=5); `Integration count` with EHR vendors (Epic, Cerner) (w=5) |
| **Anti-requirements** | No HIPAA / BAA declared (eliminative); `Data handling: trains on customer data` (eliminative); SaaS without BAA (eliminative); `Compliance` empty (eliminative) |
| **Modality** | Voice + text required; image optional (wound photos) |
| **Deployment** | VPC / dedicated tenant; self-host preferred for large health systems |
| **Persistence horizon** | `long-term` (patient longitudinal record) |
| **Governance posture** | `auditable` mandatory; `deterministic` for retention policy |
| **Throughput / latency** | p99 < 2s for note generation; real-time voice transcription |
| **Scale envelope** | Per-provider ~10³ encounters / quarter; org ~10⁵ |
| **Budget profile** | Enterprise contract, per-provider per-month |

---

### UC-08 — Legal research assistant (privileged + citation accuracy)

**Description.** Memory behind a legal-research / drafting copilot. Must maintain
privileged client matter isolation, support precise citation, and never hallucinate
case law. Examples: Harvey, CoCounsel, Lexis+ AI, Spellbook.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Compliance ⊇ {SOC 2}` + privileged-context attestations (R-hard); `Multi-tenancy` per matter / client (R-hard); `Governance: auditable` with per-write provenance (R-hard); `Conflict res ∈ {deterministic, structured}` (R-hard, citation accuracy); `Memory model ⊇ {fact, document}` with citation (R-hard) |
| **Strong preferences** | `Versioning` (w=5, citation must be reproducible across time); `Tombstoning` (w=3, retraction handling); `Deployment ⊇ {VPC}` (w=5); `Encryption` at-rest + in-transit (w=5) |
| **Anti-requirements** | `Conflict res ∈ {LLM-arbitrate, last-write-wins}` (eliminative — cannot lose citation chains); `Data handling: trains on customer data` (eliminative); SaaS without legal-grade DPA (eliminative) |
| **Modality** | Text + document (PDF, DOCX); image for evidence; OCR strong |
| **Deployment** | VPC / dedicated tenant |
| **Persistence horizon** | `long-term` (matter lifecycle = years) |
| **Governance posture** | `auditable` mandatory with bi-temporal versioning |
| **Throughput / latency** | p99 < 3s; throughput moderate |
| **Scale envelope** | 10²–10⁴ attorneys, 10⁵–10⁷ documents per firm |
| **Budget profile** | Enterprise contract, per-seat $200–$500/mo |

---

### UC-09 — Financial analyst agent (SOX + audit trail)

**Description.** Memory behind an analyst / advisor agent inside a regulated FI.
Must support SOX-grade audit trail, segregation-of-duties on writes, and tie every
inference back to a sourced fact. Examples: Bloomberg GPT-style internal agents,
JPMorgan IndexGPT, BofA Erica behind-the-scenes.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Compliance ⊇ {SOC 2, SOX}` (R-hard); `Governance: auditable` with per-write log (R-hard); `Versioning` immutable (R-hard); `Encryption: at-rest + in-transit` (R-hard); `SSO / RBAC` segregation-of-duties (R-hard) |
| **Strong preferences** | `Conflict res: deterministic / bi-temporal` (w=5); `Tombstoning` (w=5); `Forgetting policy` with retention schedule (w=5); `Deployment ⊇ {self-host, VPC}` (w=5) |
| **Anti-requirements** | Append-only without provenance (eliminative — provenance is the SOX requirement); `Data handling: trains on customer data` (eliminative); SaaS without dedicated tenancy (eliminative for tier-1 FIs) |
| **Modality** | Text + tabular; image for charts |
| **Deployment** | Self-host or dedicated VPC |
| **Persistence horizon** | `long-term` (7-year minimum retention typical) |
| **Governance posture** | `auditable` + `deterministic` |
| **Throughput / latency** | p99 < 2s; throughput moderate |
| **Scale envelope** | 10³–10⁵ users per FI, 10⁷–10⁹ records |
| **Budget profile** | Enterprise contract, $1M–$50M ARR |

---

### UC-10 — Enterprise search assistant (entitlement-aware)

**Description.** "Glean / Microsoft Copilot for M365 / Google Duet" pattern — a
memory layer that federates over the org's heterogeneous knowledge sources, respects
each source's ACLs, and never returns content the asker isn't entitled to see.
Examples: Glean, Microsoft Copilot, Google Duet, Coveo, Sinequa.

| Dimension | Value |
|---|---|
| **Required capabilities** | `SSO / RBAC` with source-system entitlement passthrough (R-hard); `Multi-tenancy` per-org (R-hard); `Compliance ⊇ {SOC 2, GDPR}` (R-hard); `Integration count` ≥ 20 source connectors (R-hard); `Namespace primitives` per-user-permission (R-hard) |
| **Strong preferences** | `Forgetting policy: ACL-change propagation` (w=5); `Governance: auditable` (w=5); `Webhooks / events` for ACL sync (w=5); `API surface ⊇ {REST, GraphQL}` (w=3) |
| **Anti-requirements** | No entitlement passthrough (eliminative — biggest single failure mode of this UC); `Data handling: trains on customer data` (eliminative) |
| **Modality** | Text + document required; image / video search nice-to-have |
| **Deployment** | SaaS or VPC |
| **Persistence horizon** | `long-term` |
| **Governance posture** | `auditable` |
| **Throughput / latency** | p99 < 1s; throughput 10²–10⁴ QPS |
| **Scale envelope** | Org-wide, 10⁷–10¹⁰ documents |
| **Budget profile** | Per-seat $20–$50/mo, enterprise contract |

---

### UC-11 — Multi-agent coordination memory

**Description.** Shared memory substrate behind a multi-agent system where 2–N agents
coordinate, hand off tasks, and avoid duplicating work. Examples: AutoGen, CrewAI,
LangGraph multi-agent, Agno teams, OpenAI Swarm-style.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Memory model ⊇ {episode, trajectory, skill}` (R-hard); `Conflict res` declared and explicit (R-hard); `Programmatic control` for orchestration hooks (R-hard); `A2A support` or equivalent (R-soft) |
| **Strong preferences** | `Consistency: strong or sequential` (w=5, agents must agree on shared state); `Versioning` (w=3); `Webhooks / events` for agent triggers (w=5); `Governance: inspectable` for debugging (w=5); `MCP support` (w=3) |
| **Anti-requirements** | `Conflict res: last-write-wins` without ordering (eliminative — guarantees lost work); `Consistency: eventual` without explicit reconciliation (R-soft eliminative for coordination-critical UCs) |
| **Modality** | Text required; rest optional |
| **Deployment** | Self-host or SaaS |
| **Persistence horizon** | `session` to `cross-session` |
| **Governance posture** | `inspectable` mandatory (debugging multi-agent failures) |
| **Throughput / latency** | p99 < 500ms (agent-to-agent loops are tight); throughput agent-count × work-rate |
| **Scale envelope** | 2–100 agents, 10⁴–10⁷ memories |
| **Budget profile** | Free (OSS) or per-seat |

---

### UC-12 — Research / academic RAG (read-only, citation-grounded)

**Description.** RAG behind a literature-review or domain-knowledge research assistant
where the corpus is authoritative and read-only, and every answer must cite a
specific passage. Examples: Elicit, Consensus, Scite Assistant, Perplexity Pro,
You.com Research.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Memory model ⊇ {document, chunk}` (R-hard); `Update ∈ {read-only, append-only}` for the corpus (R-hard); `Conflict res: deterministic` (citation must be reproducible) (R-hard); `API surface` declared (R-soft) |
| **Strong preferences** | `Reproducibility` declared (w=5); `Versioning` of the corpus (w=5); `Governance: auditable` for citation provenance (w=5); `Embedding model` declared (w=3) |
| **Anti-requirements** | Mutable corpus with no version (eliminative for research integrity); `Conflict res: LLM-arbitrate` (eliminative — citation must be deterministic) |
| **Modality** | Text + document required |
| **Deployment** | SaaS acceptable; self-host preferred for research orgs |
| **Persistence horizon** | `lifelong` (corpus permanence) |
| **Governance posture** | `auditable` |
| **Throughput / latency** | p99 < 2s; throughput moderate |
| **Scale envelope** | 10⁶–10⁹ chunks |
| **Budget profile** | Free, freemium, or per-seat |

---

### UC-13 — Robotics / embodied (multimodal + real-time)

**Description.** Memory behind a robot or embodied agent — must fuse vision, depth,
proprioception, and language; persist scene graphs; meet real-time control loops.
Examples: PI Physical Intelligence, Figure 02, Tesla Optimus, Boston Dynamics
embodied AI, NAVER LABS robots.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Modalities ⊇ {vision, sensor}` (R-hard); `Memory model ⊇ {scene-graph, trajectory, episode}` (R-hard); `Latency p99 < 100ms` for control-loop slice (R-hard for closed-loop control); `Runtimes ⊇ {edge, on-device}` (R-hard) |
| **Strong preferences** | `Deployment ⊇ {self-host, edge}` (w=5); `Storage primitive ∈ {hybrid, kv-cache, parametric}` (w=3); `Memory primitives ⊇ {scene-graph}` (w=5); `Programmatic control` (w=5) |
| **Anti-requirements** | Cloud-only (eliminative — connectivity assumption fails); text-only (eliminative); p99 ≥ 500ms for control path (eliminative) |
| **Modality** | Vision + sensor + text required; voice nice-to-have |
| **Deployment** | Edge / on-device required |
| **Persistence horizon** | `session` (per-task) to `long-term` (skill library) |
| **Governance posture** | `inspectable` for safety review |
| **Throughput / latency** | p99 < 50ms for perception, < 200ms for episodic recall |
| **Scale envelope** | Per-robot 10⁵–10⁷ frames, fleet 10⁹+ |
| **Budget profile** | Mostly captive (vendor's own stack); or one-time license |

---

### UC-14 — Voice-first wearable assistant

**Description.** Always-on or push-to-talk voice assistant on a wearable
(pendant, ring, glasses, earbuds). Must capture, transcribe, summarise, and recall
ambient conversation; tight power, privacy, and latency budgets. Examples: Limitless,
Friend, Bee Computer, Humane Pin (legacy), Plaud, Rabbit R1, Meta Ray-Ban AI.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Modalities ⊇ {voice}` (R-hard); `Persistence ∈ {long-term, lifelong}` (R-hard); `Compliance ⊇ {GDPR}` and consent declarations (R-hard); `Encryption: at-rest + in-transit` (R-hard) |
| **Strong preferences** | `Governance ∈ {user-controllable, editable}` (w=5, sensitive ambient capture); `Forgetting policy` user-configurable (w=5); `Runtimes ⊇ {mobile, on-device}` (w=3); `Deployment ⊇ {self-host}` (w=3, ownership preference) |
| **Anti-requirements** | `Data handling: trains on customer data` (eliminative — consent failure mode); SaaS without explicit consent path (eliminative); `Persistence < cross-session` |
| **Modality** | Voice required; text downstream; vision optional (glasses) |
| **Deployment** | Vendor-hosted typical; self-host preferred by privacy-aware buyers |
| **Persistence horizon** | `lifelong` |
| **Governance posture** | `user-controllable` mandatory |
| **Throughput / latency** | p99 < 2s for query; capture is async |
| **Scale envelope** | 1 user, 10⁶–10⁸ minutes/year |
| **Budget profile** | Hardware + per-month subscription |

---

### UC-15 — Browser-agent memory

**Description.** Memory behind an autonomous browser agent — remembers prior page
visits, form data, task plans, and site-specific patterns across sessions. Tight
coupling to live web. Examples: Browser Use, Manus, Comet (Perplexity), ChatGPT
Atlas, Skyvern, Anthropic Computer Use.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Memory model ⊇ {trajectory, skill, episode}` (R-hard); `Persistence ⊇ {cross-session}` (R-hard); `API surface` programmatic (R-hard); `Modalities ⊇ {vision}` for screenshot recall (R-soft) |
| **Strong preferences** | `Storage primitive ∈ {hybrid, kv, file}` (w=3); `Update ∈ {agent-controlled, append-only}` (w=3); `Governance: inspectable` for replay / debugging (w=5); `Forgetting policy` for credentials and PII (w=5) |
| **Anti-requirements** | No vision modality (eliminative — most browser-agent memory is screenshot-grounded); session-only persistence (eliminative — defeats purpose) |
| **Modality** | Vision + text required |
| **Deployment** | SaaS dominant in this category (catalog: 100% SaaS-only) |
| **Persistence horizon** | `cross-session` |
| **Governance posture** | `inspectable` for replay |
| **Throughput / latency** | p99 < 2s; throughput moderate |
| **Scale envelope** | 1 user, 10⁴–10⁶ trajectories |
| **Budget profile** | Per-seat or per-task |

---

### UC-16 — Education / tutor memory

**Description.** Memory behind a personalised tutor or learning agent — tracks student
mastery, error patterns, learning trajectory, motivation. Examples: Khanmigo, Speak,
Synthesis Tutor, MagicSchool, ChatGPT Study Mode, Quizlet AI, Duolingo Max.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Memory model ⊇ {profile, episode}` (R-hard); `Compliance ⊇ {COPPA, FERPA}` for K-12 (R-hard); `Persistence ⊇ {long-term}` (R-hard); `Multi-tenancy` per-student (R-hard for institutional) |
| **Strong preferences** | `Modalities ⊇ {voice}` (w=5, language tutoring); `Governance: editable / inspectable` for parent / teacher review (w=5); `Forgetting policy` with FERPA retention (w=5); `Webhooks / events` for LMS integration (w=3) |
| **Anti-requirements** | `Compliance` empty for K-12 deployment (eliminative); `Data handling: trains on customer data` (eliminative for K-12 / under-18) |
| **Modality** | Text + voice; image for diagrams |
| **Deployment** | SaaS for K-12 (institutional); self-host for higher-ed where mandated |
| **Persistence horizon** | `long-term` (academic-year scale) |
| **Governance posture** | `inspectable` for educator oversight |
| **Throughput / latency** | p99 < 2s; throughput moderate |
| **Scale envelope** | 10³–10⁶ students per district |
| **Budget profile** | Per-seat $5–$30/mo, district-licensing |

---

### UC-17 — Sales / CRM-integrated agent

**Description.** Memory behind a sales-rep / CRM-augmenting agent — remembers each
prospect's history, prior conversations, deal stage, and rep preferences across
the rep's full book. Examples: Salesforce Einstein, HubSpot Breeze, Gong AI,
Clari Copilot, Outreach Kaia.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Memory model ⊇ {profile, episode}` (R-hard); `Multi-tenancy` per-org (R-hard); `Integration count` with CRM (Salesforce, HubSpot, Dynamics) (R-hard); `Compliance ⊇ {SOC 2, GDPR}` (R-hard) |
| **Strong preferences** | `Webhooks / events` for CRM sync (w=5); `Modalities ⊇ {voice}` for call recording (w=5); `Governance: auditable` for sales-process compliance (w=3); `Conflict res` declared (w=3, multiple reps may touch one account) |
| **Anti-requirements** | No CRM integration (eliminative for this UC); `Data handling: trains on customer data` (eliminative under GDPR for B2C contacts) |
| **Modality** | Text + voice; email + transcript |
| **Deployment** | SaaS with CRM-native integration |
| **Persistence horizon** | `long-term` |
| **Governance posture** | `auditable` for forecast / pipeline integrity |
| **Throughput / latency** | p99 < 2s; throughput moderate |
| **Scale envelope** | 10²–10⁵ reps per org, 10⁶–10⁹ interactions |
| **Budget profile** | Per-seat $50–$300/mo |

---

### UC-18 — HR / internal-knowledge agent

**Description.** Memory behind an HR-self-service or internal-policy agent — answers
questions about benefits, policies, payroll, time-off; remembers each employee's
prior tickets and entitlements. Examples: Moveworks, Leena AI, Workday AI, ServiceNow
Now Assist, Microsoft Copilot for HR.

| Dimension | Value |
|---|---|
| **Required capabilities** | `Multi-tenancy` per-org (R-hard); `SSO / RBAC` with HRIS integration (R-hard); `Compliance ⊇ {SOC 2, GDPR}` (R-hard); `Forgetting policy` for HRIS retention rules (R-hard) |
| **Strong preferences** | `Integration count` with HRIS (Workday, BambooHR, ADP) (w=5); `Governance: auditable` for sensitive HR conversations (w=5); `Encryption: at-rest + in-transit` (w=5); `Namespace primitives` per-employee (w=3) |
| **Anti-requirements** | No HRIS integration (eliminative); `Data handling: trains on customer data` (eliminative); shared multi-tenancy without isolation (eliminative) |
| **Modality** | Text required |
| **Deployment** | SaaS or VPC |
| **Persistence horizon** | `long-term` |
| **Governance posture** | `auditable` |
| **Throughput / latency** | p99 < 2s |
| **Scale envelope** | 10²–10⁵ employees per org |
| **Budget profile** | Per-employee $5–$20/mo |

---

## Mapping table — use-case dimension → system-side column(s)

The mapping below shows which of the 60 system-side columns in `landscape.html`
contribute to scoring each use-case dimension. Columns marked **★** are weak in the
current catalog (mostly empty / "no data") — see *Gap analysis* below.

| Use-case dimension | System-side column(s) (verbatim from `landscape.html`) |
|---|---|
| Required modality | `Modalities` |
| Persistence horizon | `Persistence` |
| Memory model / unit | `Memory model`, `Unit`, `Memory primitives` |
| Update / write semantics | `Update`, `Conflict res.`, `Versioning`, `Tombstoning`, `Forgetting policy` |
| Retrieval semantics | `Retrieval` |
| Storage primitive | `Storage`, `Backend storage` |
| Governance posture | `Governance`, `Contradiction handling`, `Conflict res.` |
| Compliance | `Compliance`, `Data handling` |
| Multi-tenancy / isolation | `Multi-tenancy`, `Namespace primitives` |
| Auth / RBAC | `SSO / RBAC` |
| Encryption | `Encryption` |
| Audit / provenance | `Governance` (auditable values), `Versioning`, `Tombstoning` |
| Latency profile | `Latency p50/p99` ★ |
| Throughput profile | `Throughput` ★ |
| Memory volume / scale | `Memory volume / scale` ★ |
| Modality breadth | `Modalities` |
| Deployment shape | `Deployment`, `Runtimes` |
| Programmatic surface | `API surface`, `Programmatic control`, `MCP support`, `A2A support`, `Webhooks / events` |
| Integration ecosystem | `Integration count`, `Orchestration` |
| Pricing / budget | `Pricing`, `Pricing specifics` |
| Maturity / sustainability | `Created`, `Latest release`, `License`, `GitHub`, `Mindshare`, `Citations`, `Funding`, `Customers / scale`, `Founders / pedigree` |
| Reproducibility / openness | `Reproducibility`, `Code/weights release`, `License` |
| LLM coupling | `LLM lock`, `Embedding model`, `Agent abstraction` |
| Schema / migration | `Schema evolution`, `Consistency` |
| Session semantics | `Session handling` |
| Vendor performance claims | `Performance`, `Vendor benchmarks` |

---

## Gap analysis — what the catalog currently lacks for high-quality fit-matching

Five categories of gap, ordered by how much they limit fit-matching today.

### Gap-1: Operational performance is mostly undeclared

`Latency p50/p99`, `Throughput`, and `Memory volume / scale` are populated for
< 25% of rows (estimated from row spot-checks). This breaks fit-matching for the
high-throughput / real-time UCs:

- **UC-06 (contact center)** — cannot reliably filter on `p99 < 300ms` because most
  contenders' p99 is "no data."
- **UC-13 (robotics)** — cannot reliably filter on `p99 < 100ms` for the same reason.
- **UC-04 (enterprise coding)** — at-scale throughput numbers are absent.

**Fix:** a focused operational-performance pass — vendor-published benchmarks +
GitHub-issue scrape for "latency" / "throughput" / "QPS" mentions on top 50 systems.

### Gap-2: "Validated verticals" / declared use-case fit is missing

The catalog records *what a system is built from*, not *what it has been validated
in*. There is no column for "deployments in healthcare," "named SOX-compliant
deployments," "K-12 referenceable customers," etc. `Customers / scale` partially
captures this when populated, but is free-form prose, not structured.

**Fix:** add a structured `Validated verticals` column with a controlled vocabulary
({healthcare, legal, finance, education-K12, education-HE, retail, manufacturing,
public-sector, …}). Tag every row that has a named, referenceable deployment in
that vertical.

### Gap-3: "Anti-fit" declarations are absent

No column captures "this system is **not** suitable for X." Vendor-disclosed
limitations live (sometimes) in `Cons` as free-form prose. For fit-matching, an
explicit *negative* signal is more valuable than absence — "Mem0 is not for
sub-100ms control loops" is a stronger filter than the absence of a latency claim.

**Fix:** add a structured `Anti-fit` column or extend `Cons` with a controlled
sub-vocabulary of disqualifying conditions. (Vendors will resist; community
tagging may be the realistic path.)

### Gap-4: "Decision criteria optimised for" is implicit, not declared

A coding-agent memory and a clinical-scribe memory both populate the same columns
but optimise for *radically* different criteria (latency vs auditability). There is
no column for *what the system was optimised for* — that signal lives in claim
prose.

**Fix:** add a `Primary optimisation target` column with a controlled vocabulary
({latency, throughput, governance, multi-tenancy, modality-breadth, ownership,
cost, accuracy, citation-fidelity, real-time-control, ambient-capture, …}). Each
row tags 1–3.

### Gap-5: Adjacent-infrastructure requirements are not catalogued

Many use cases require *adjacent* infrastructure beyond the memory layer itself —
EHR connectors (UC-07), CRM-native UI (UC-17), HRIS sync (UC-18), 20+ source
connectors (UC-10), MCP server registry presence (most). The catalog has
`Integration count` (often empty) and `Orchestration` (sparse) but no structured
list of *which* adjacent systems the memory layer connects to.

**Fix:** extend `Integration count` to a structured `Integrations` array with
named partners, or add a `Connector inventory` column. Mem0's 14 inbound edges
are visible in the synthesis pass; making them queryable per-row is the missing
piece.

### Secondary gaps (lower-impact)

- **`Compliance` column free-form** — should be a structured set
  ({HIPAA, BAA, SOC 2, GDPR, CCPA, FedRAMP, SOX, PCI-DSS, ISO 27001, FERPA, COPPA,
  HITRUST, …}) for clean filtering. Today, "HIPAA" vs "HIPAA-compatible" vs
  "BAA available" all appear as different strings.
- **`Forgetting policy` granularity unknown.** GDPR right-to-be-forgotten
  enforcement requires per-record TTL + user-initiated deletion + propagation
  semantics. Most rows say "TBD" or absent.
- **`Pricing` is prose**, not a structured tier (free / freemium / per-seat /
  per-call / enterprise). Budget-profile filtering is brittle.
- **No `Trust posture` column** — captures whether the vendor will accept liability
  for memory correctness (matters for UC-08 / UC-09 procurement). Always implicit
  in MSA terms, never in catalog.
- **No `Time-to-first-value` / `Friction-to-deploy` column.** Two systems with
  identical capability checklists can have a 100× difference in deployment effort.
  Would dramatically improve fit-matching for SMB use cases.

### Summary of catalog adequacy by use case

| Use case | Adequate today? | Most acute gap |
|---|---|---|
| UC-01 personal | **Yes** | Pricing-tier structure |
| UC-02 PKM | **Yes** | Validated-verticals (consumer market signals) |
| UC-03 dev IDE | **Mostly** | Latency p99 |
| UC-04 enterprise coding | Partial | Multi-tenancy isolation specifics |
| UC-05 SaaS support | Partial | Forgetting-policy granularity |
| UC-06 contact-center | **Weak** | Latency / throughput |
| UC-07 clinical scribe | Partial | Compliance specificity (BAA vs HIPAA-compatible) |
| UC-08 legal | Partial | Auditability + bi-temporal versioning declarations |
| UC-09 financial | Partial | Audit-trail granularity |
| UC-10 enterprise search | Partial | Connector inventory |
| UC-11 multi-agent | **Mostly** | Consistency model |
| UC-12 academic RAG | **Yes** | Reproducibility populated |
| UC-13 robotics | **Weak** | Latency, runtime/edge declarations |
| UC-14 voice wearable | Partial | Consent / data-handling specificity |
| UC-15 browser-agent | **Mostly** | Deployment uniformity (100% SaaS limits filter) |
| UC-16 education | Partial | COPPA/FERPA declarations |
| UC-17 sales/CRM | Partial | Integration inventory |
| UC-18 HR | Partial | HRIS integration declarations |

**Most adequate (top 5):** UC-01 personal, UC-02 PKM, UC-12 academic RAG, UC-11
multi-agent, UC-03 dev IDE.
**Most data-starved (top 5):** UC-06 contact center, UC-13 robotics, UC-09 financial,
UC-08 legal, UC-04 enterprise coding.

---

## Open questions for the next pass

1. Should use cases nest? (UC-04 enterprise coding is a stricter UC-03; UC-07 clinical
   scribe is a HIPAA-bound UC-05.) A hierarchy would let one system inherit fit
   scores. Trade-off: hierarchy complicates the scoring schema.
2. Should preference weights be use-case-author-set (current model) or user-set at
   query time? The latter makes the taxonomy interactive but dilutes its
   prescriptiveness.
3. Should there be a UC for **cross-vendor portability of memory state** — a buyer
   archetype optimised for "I never want to be locked in"? The synthesis flags this
   as a real white-space; making it a UC would surface which (if any) systems
   currently address it.
