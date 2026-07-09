# The 2026 Tool-Use and Computer Agent Landscape

The way AI agents interact with the outside world has undergone a dramatic shift. In 2024, "tool use" meant a model emitting a JSON function call that your backend executed. Today we have full-blown autonomous agents that clone repos, run shell commands, control desktops via screenshots, and message you on WhatsApp, all orchestrated through standardized protocols like MCP. This chapter maps the landscape of these tools, their architectures, and the design decisions that differentiate them.

## Table of Contents

- [Ecosystem Overview](#ecosystem-overview)
- [Category Taxonomy](#category-taxonomy)
- [OpenClaw: The Viral Personal AI Agent](#openclaw)
- [OpenHands: Autonomous Developer Agent](#openhands)
- [Open Interpreter: Local Code Execution](#open-interpreter)
- [Claude Computer Use: Vision-Based Automation](#claude-computer-use)
- [Claude Code: The Terminal Agent](#claude-code)
- [IDE Agents: Cursor, Windsurf, Cline](#ide-agents)
- [Comparison Matrix](#comparison-matrix)
- [Market Trends and Adoption (2026)](#market-trends)
- [System Design Interview Angle](#interview-angle)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## Ecosystem Overview

The 2026 tool-use ecosystem has consolidated around four architectural patterns, each optimized for different levels of autonomy, safety, and integration depth:

```
+-----------------------------------------------------------------------+
|                     2026 Tool-Use Ecosystem                           |
+-----------------------------------------------------------------------+
|                                                                       |
|  +-------------------+  +-------------------+  +-------------------+  |
|  |  LOCAL AGENTS     |  |  CLOUD AGENTS     |  |  IDE AGENTS       |  |
|  |                   |  |                   |  |                   |  |
|  |  OpenClaw         |  |  Claude Code      |  |  Cursor           |  |
|  |  Open Interpreter |  |  OpenAI Codex     |  |  Windsurf         |  |
|  |  OpenHands (local)|  |  OpenHands Cloud  |  |  Cline            |  |
|  |  LM Studio Agent  |  |  Google Jules     |  |  GitHub Copilot   |  |
|  +-------------------+  +-------------------+  +-------------------+  |
|                                                                       |
|  +-------------------+  +-------------------+  +-------------------+  |
|  |  COMPUTER-USE     |  |  MCP SERVERS      |  |  MESSAGING AGENTS |  |
|  |                   |  |                   |  |                   |  |
|  |  Claude Computer  |  |  10,000+ servers  |  |  OpenClaw (multi) |  |
|  |  Use API          |  |  97M monthly SDK  |  |  Custom bots      |  |
|  |  Open Interpreter |  |  downloads        |  |  via MCP bridges  |  |
|  |  (Computer API)   |  |                   |  |                   |  |
|  +-------------------+  +-------------------+  +-------------------+  |
+-----------------------------------------------------------------------+
```

The key insight for 2026: these categories are converging. Claude Code is a cloud agent that runs locally. OpenClaw is a local agent that connects to cloud LLMs. Cursor is an IDE agent with cloud-side Background Agents. The lines are blurring, and what matters is the underlying **architecture pattern** (covered in the next chapter).

---

## Category Taxonomy

### 1. Local Agents (Self-Hosted, User-Controlled)

Agents that run on the user's own hardware. The LLM call may go to the cloud, but the agent process, memory, and tool execution are local.

**Key properties:**
- Full filesystem access on the user's machine
- Persistent memory stored locally (SQLite, JSON, Markdown)
- User owns all data; no vendor lock-in
- Security responsibility falls entirely on the operator

**Examples:** OpenClaw, Open Interpreter, local OpenHands deployments

### 2. Cloud Agents (Vendor-Hosted, API-Driven)

Agents that run in vendor-managed cloud environments. Code execution happens in sandboxed VMs or containers.

**Key properties:**
- Sandboxed execution (Docker, Firecracker VMs, E2B)
- No local filesystem access (works on cloned repos)
- Vendor handles scaling, security, and infrastructure
- Pay-per-use or subscription pricing

**Examples:** Claude Code (cloud mode), OpenAI Codex, Google Jules, OpenHands Cloud

### 3. IDE Agents (Editor-Integrated, Context-Aware)

Agents embedded directly in code editors. They have deep understanding of project structure, open files, and editor state.

**Key properties:**
- Tight integration with editor UI (inline diffs, tab completion)
- Codebase indexing via embeddings or AST parsing
- Background agents that work asynchronously on branches
- Optimized for developer workflow, not general automation

**Examples:** Cursor (Agent Mode + Background Agents), Windsurf (Cascade), Cline, GitHub Copilot, Google Antigravity (Gemini 3 agent-first workspace with a multi-agent manager view, successor to the Gemini CLI)

### 4. Computer-Use Agents (Vision-Based, GUI-Driven)

Agents that interact with software the way humans do -- by looking at screenshots and clicking.

**Key properties:**
- Model sees screenshots, decides mouse/keyboard actions
- Works with any application (no API needed)
- Higher latency (screenshot-action loop is 1-3 seconds per step)
- Requires sandboxed environments for safety (VM + VNC)

**Examples:** Claude Computer Use API, Open Interpreter Computer API

---

## OpenClaw: The Viral Personal AI Agent

### What It Is

OpenClaw is a self-hosted, open-source personal AI assistant created by Austrian developer Peter Steinberger. Originally published as "Clawdbot" in November 2025, it was renamed to OpenClaw in January 2026. It exploded from 0 to 346,000 GitHub stars in under five months, surpassing React as GitHub's most-starred software project on March 3, 2026.

**By the numbers (May 2026):**
- 346,000+ GitHub stars
- 3.2 million active users
- 500,000+ running instances
- 44,000+ community skills on ClawHub
- 38 million monthly visitors to the project site
- 24+ messaging platform integrations

### How It Works

OpenClaw's architecture has six core components:

```
+-------------------------------------------------------------------+
|                      OpenClaw Architecture                        |
+-------------------------------------------------------------------+
|                                                                   |
|  +-----------+     +-----------+     +----------+                 |
|  |  Gateway  |---->|  LLM      |---->| PI Agent |                 |
|  |           |     |  (Brain)  |     | (Exec)   |                 |
|  +-----------+     +-----------+     +----------+                 |
|       ^                  |                |                       |
|       |                  v                v                       |
|  +-----------+     +-----------+     +----------+                 |
|  | Channels  |     | SOUL.md   |     | Skills   |                 |
|  | (24+)     |     | (Identity)|     | (44K+)   |                 |
|  +-----------+     +-----------+     +----------+                 |
|                          |                                        |
|                          v                                        |
|                    +-----------+                                  |
|                    | Memories  |                                  |
|                    | (Persist) |                                  |
|                    +-----------+                                  |
+-------------------------------------------------------------------+
```

**1. Gateway**: The message ingress/egress layer. Connects to WhatsApp (via Baileys), Telegram, Discord, Slack, Signal, iMessage, Microsoft Teams, Matrix, and 16+ other platforms. Supports both DMs and group conversations with mention-based activation.

**2. LLM (The Brain)**: Model-agnostic by design. Supports GPT-4o, Claude, Gemini, DeepSeek, or local models via Ollama. The user picks the model; the architecture does not care.

**3. PI Agent (Process Interactor)**: A small runtime that allows the LLM to create, edit, run, and delete files on the host system. The LLM generates code, the PI Agent saves it, and then executes it. This is the "hands" of the agent.

**4. SOUL.md (Identity Layer)**: A plain Markdown file that defines the agent's personality, communication style, values, and behavioral guardrails. Loaded at session start and injected into the system prompt. Every agent instance reads SOUL.md first -- it "reads itself into being."

**5. Skills (Plugin System)**: Extensions that give the agent new capabilities. Over 44,000 community skills exist on ClawHub. Skills follow the AgentSkills spec and can be bundled, workspace-local, or installed globally.

**6. Memories (Persistent Context)**: Long-term memory stored locally. The agent builds up context about the user across conversations. Combined with SOUL.md, this gives each agent a consistent personality across all messaging platforms.

### Workspace Files

| File | Purpose |
|------|---------|
| `SOUL.md` | Agent personality, tone, values, guardrails |
| `AGENTS.md` | Operational instructions, tool configurations |
| `HEARTBEAT.md` | Scheduled autonomous actions (cron-like) |
| `Memories/` | Persistent context across conversations |

### Security Concerns

OpenClaw's rapid growth has outpaced security practices. As of May 2026, over 135,000 instances are exposed on the public internet, many with default configurations. The ClawHub skills marketplace has minimal security oversight: skills are Markdown with optional TypeScript, easy to create and install, and easy to abuse. This is a critical design consideration for anyone deploying OpenClaw in production.

---

## OpenHands: Autonomous Developer Agent

### What It Is

OpenHands (formerly OpenDevin) is an open-source autonomous AI software engineer. Licensed under MIT, it can modify code, execute commands, browse the web, and interact with APIs. Unlike tools that suggest code snippets, OpenHands clones repositories, runs terminal commands, executes tests, and debugs errors inside sandboxed Docker containers.

### Architecture: Event-Stream + Sandboxed Runtime

```
+-------------------------------------------------------------------+
|                     OpenHands Architecture                        |
+-------------------------------------------------------------------+
|                                                                   |
|  +------------------+                                             |
|  |   User / API     |                                             |
|  +--------+---------+                                             |
|           |                                                       |
|           v                                                       |
|  +--------+---------+     +------------------+                    |
|  |  Agent Controller |<--->|  Event Stream    |                   |
|  |  (CodeAct 1.0)   |     |  Hub             |                   |
|  +--------+---------+     +--------+---------+                    |
|           |                        |                              |
|           v                        v                              |
|  +--------+---------+     +--------+---------+                    |
|  |  Action Dispatch  |     |  Observation     |                   |
|  |                   |     |  Collector       |                   |
|  |  - CmdRunAction   |     |                  |                   |
|  |  - FileWriteAction|     |  - CmdOutput     |                   |
|  |  - BrowseURLAction|     |  - FileContent   |                   |
|  |  - CodeAction     |     |  - BrowserState  |                   |
|  +--------+---------+     +------------------+                    |
|           |                                                       |
|           v                                                       |
|  +--------+--------------------------------------------------+    |
|  |              Docker Sandbox (Per Session)                 |    |
|  |                                                           |    |
|  |  +----------+  +----------+  +----------+                |    |
|  |  | Terminal  |  |  Python  |  | Browser  |                |    |
|  |  | (bash)   |  | (stateful)|  | (BrowserGym)             |    |
|  |  +----------+  +----------+  +----------+                |    |
|  +-----------------------------------------------------------+    |
+-------------------------------------------------------------------+
```

**Key architectural decisions:**
- **Event-stream architecture**: All agent-environment interactions flow as typed events through a central hub. The Agent analyzes conversation state and produces Actions; the sandbox produces Observations.
- **Per-session Docker containers**: Each session gets its own isolated container with full OS capabilities. The container is insulated from the host.
- **CodeAct 1.0**: The default agent template. Embeds LLM reasoning into a unified coding control plane and maintains session-level project context.
- **BrowserGym integration**: Agents can conduct browser automation via declarative primitives (DOM manipulation, navigation).
- **SDK composability**: The OpenHands SDK is a Python library. You can define agents in code, run them locally, or scale to thousands in the cloud.

**Recent updates (v1.6.0, March 2026):**
- Kubernetes support for orchestrating agent sessions
- Planning Mode beta for multi-step task decomposition
- 2,100+ contributions from 188+ contributors

---

## Open Interpreter: Local Code Execution

### What It Is

Open Interpreter is a local code execution agent that provides a ChatGPT-like terminal interface. Instead of showing code and asking you to run it, Open Interpreter asks for permission and then executes it directly on your machine with full access to your local files.

### Architecture

```
+-------------------------------------------------------------------+
|                  Open Interpreter Architecture                    |
+-------------------------------------------------------------------+
|                                                                   |
|  +------------------+                                             |
|  |  Terminal UI      |                                            |
|  |  (ChatGPT-like)  |                                            |
|  +--------+---------+                                             |
|           |                                                       |
|           v                                                       |
|  +--------+---------+     +------------------+                    |
|  |  Core Engine      |<--->|  LLM Provider   |                   |
|  |                   |     |  (100+ models)  |                    |
|  |  - NL to Code     |     |  GPT, Claude,   |                   |
|  |  - Permission     |     |  Ollama, LM     |                   |
|  |    Gate            |     |  Studio, etc.   |                   |
|  +--------+---------+     +------------------+                    |
|           |                                                       |
|           v                                                       |
|  +--------+---------+                                             |
|  |  Code Executor    |                                            |
|  |                   |                                            |
|  |  - Python         |                                            |
|  |  - JavaScript     |                                            |
|  |  - Shell/Bash     |                                            |
|  |  - AppleScript    |                                            |
|  +--------+---------+                                             |
|           |                                                       |
|           v                                                       |
|  +--------+---------+                                             |
|  |  Computer API     |                                            |
|  |  (GUI Control)    |                                            |
|  |                   |                                            |
|  |  - Screen capture |                                            |
|  |  - Mouse/Keyboard |                                            |
|  |  - Icon detection |                                            |
|  +-------------------+                                            |
+-------------------------------------------------------------------+
```

**Key properties:**
- **Model flexibility**: Works with 100+ LLMs. Use GPT-4o or Claude for maximum capability, or run entirely offline with Ollama and LM Studio for privacy.
- **Permission gate**: Every code execution requires user approval (can be disabled for trusted workflows).
- **Computer API**: Beyond code execution, Open Interpreter can see your screen, identify UI elements, and control your mouse and keyboard -- elevating it from a code interpreter to a computer automation agent.
- **Unsandboxed by default**: Runs directly on the host machine. This is a deliberate design choice for maximum capability, but it means a bad LLM output can damage your system. Docker sandboxing is optional.

### When to Use Open Interpreter

Best for data analysis, file manipulation, and system administration tasks where you want a conversational interface to your local machine. Not ideal for production deployments or untrusted environments.

---

## Claude Computer Use: Vision-Based Automation

### What It Is

Claude Computer Use is an Anthropic API feature that allows Claude to control a desktop via screenshots, mouse movements, keyboard input, and application interaction. Introduced in October 2024 as a beta, it has evolved significantly. As of May 2026, Sonnet 4.6 reaches 72.5% on OSWorld-Verified, up from 14.9% at launch, with Opus 4.7 pushing further on agentic coding benchmarks (64.3% SWE-bench Pro).

### The Vision-Action Loop

```
+-------------------------------------------------------------------+
|              Claude Computer Use: Vision-Action Loop               |
+-------------------------------------------------------------------+
|                                                                   |
|  Step 1: OBSERVE          Step 2: REASON          Step 3: ACT    |
|  +----------------+       +----------------+      +------------+ |
|  |  Take          |       |  Analyze       |      |  Execute   | |
|  |  Screenshot    |------>|  Screenshot    |----->|  Action    | |
|  |  (base64 PNG)  |       |  + Task Goal   |      |  (click,   | |
|  |                |       |  + History      |      |  type,     | |
|  +----------------+       +----------------+      |  scroll)   | |
|                                                    +------+-----+ |
|                                                           |       |
|          +------------------------------------------------+       |
|          |                                                        |
|          v                                                        |
|  +-------+--------+                                               |
|  |  Wait + Take   |                                               |
|  |  New Screenshot|-------> (Loop back to Step 1)                 |
|  +----------------+                                               |
|                                                                   |
+-------------------------------------------------------------------+
```

### Available Tools

| Tool | Capability | Notes |
|------|------------|-------|
| `computer` | Mouse, keyboard, screenshot | Full desktop GUI control |
| `bash` | Run shell commands | Persistent session across turns |
| `text_editor` | Read/write/edit files | Supports view, create, str_replace |

### 2026 Enhancements

- **Zoom Action**: Inspects small UI elements at high resolution before clicking. Reduces misclick rates on dense interfaces.
- **Available in Claude Cowork and Claude Code**: Research preview for Pro and Max users, with human confirmation required before destructive actions.
- **Sandboxing best practice**: Always run in a sandboxed VM (Docker + VNC, or E2B cloud). Never give computer-use access to an unsandboxed host machine.

### Performance Trajectory

| Date | OSWorld Score | Key Milestone |
|------|---------------|---------------|
| Oct 2024 | 14.9% | Beta launch (Claude 3.5 Sonnet) |
| Mid 2025 | ~40% | Claude 3.7 improvements |
| Q1 2026 | 72.5% | Sonnet 4.6, Zoom Action |

---

## Claude Code: The Terminal Agent

### What It Is

Claude Code is Anthropic's agentic coding tool that lives in the terminal. It reads your codebase, edits files, runs commands, and integrates with development tools. It shipped publicly in May 2025 and crossed $2.5 billion ARR by February 2026.

### Architecture

Claude Code is a TypeScript terminal agent that loops through three phases:

```
+-------------------------------------------------------------------+
|                   Claude Code Agent Loop                          |
+-------------------------------------------------------------------+
|                                                                   |
|  +------------------+                                             |
|  |  1. GATHER       |  Read files, grep codebase, glob search,   |
|  |     CONTEXT      |  check git status, analyze structure        |
|  +--------+---------+                                             |
|           |                                                       |
|           v                                                       |
|  +--------+---------+                                             |
|  |  2. TAKE         |  Edit files, run bash, write new files,     |
|  |     ACTION       |  create commits, spawn subagents            |
|  +--------+---------+                                             |
|           |                                                       |
|           v                                                       |
|  +--------+---------+                                             |
|  |  3. VERIFY       |  Run tests, check build, review diffs,     |
|  |     RESULTS      |  validate output                            |
|  +--------+---------+                                             |
|           |                                                       |
|           +--------> (Loop back to Step 1 if not done)            |
|                                                                   |
+-------------------------------------------------------------------+

Built-in Tools: bash, read, write, edit, glob, grep, browser,
                subagent, notebook, web_search, web_fetch
```

**Key architectural properties:**
- One agent loop with a rich tool palette
- On-demand skill loading via slash commands and CLAUDE.md
- Context compression for long sessions (1M+ token context)
- Subagent spawning for parallel workstreams
- Worktree isolation for parallel branch execution
- Permission governance (allow/deny rules for tools)
- Task system with dependency graphs
- Hooks for custom automation (pre/post commit, file changes)

---

## IDE Agents: Cursor, Windsurf, Cline

### Cursor

Cursor is a VS Code fork with deep AI integration. Version 2.0 (early 2026) introduced:
- **Agent Mode**: Uses 20x scaled reinforcement learning for multi-file editing
- **Background Agents**: Clone your repo in cloud VMs, work autonomously, open PRs when done
- **Mission Control**: Dashboard for managing parallel agent workflows
- **Market**: $2B annualized revenue, 2M+ users, 1M+ paying customers, adopted by half the Fortune 500

### Windsurf

Windsurf (originally Codeium, acquired by Cognition for $250M in July 2025) features:
- **Cascade**: Multi-step AI agent that analyzes project structure, coordinates cross-file changes, and self-recovers from errors
- **Proprietary models**: SWE-1.5 (13x faster than Sonnet 4.5) and Fast Context
- **Codemaps**: AI-powered visual code navigation
- **Cross-IDE plugins**: Available for 40+ IDEs (JetBrains, Vim, NeoVim, XCode)

### Cline

Cline is a VS Code extension that operates as a full agent rather than an autocomplete tool. It takes a series of steps, evaluates results, fixes its own errors, and continues. More autonomous than Cursor or Windsurf but with less polish.

### IDE Agent Architecture Comparison

```
+-------------------------------------------------------------------+
|                 IDE Agent Architecture Patterns                   |
+-------------------------------------------------------------------+
|                                                                   |
|  Cursor:                                                          |
|  [Editor] --> [Agent Mode] --> [Multi-file RL] --> [Apply Diffs]  |
|                    |                                               |
|                    +--> [Background Agent] --> [Cloud VM] --> [PR] |
|                                                                   |
|  Windsurf:                                                        |
|  [Editor] --> [Cascade Agent] --> [RAG Codebase] --> [Apply Edits]|
|                    |                                               |
|                    +--> [SWE-1.5 Model] --> [Fast Context]        |
|                                                                   |
|  Cline:                                                           |
|  [Editor] --> [Agent Loop] --> [Evaluate] --> [Self-Fix] --> [Act]|
|                    |                                               |
|                    +--> [Any LLM Provider] --> [Tool Calls]       |
+-------------------------------------------------------------------+
```

---

## Comparison Matrix

| Feature | OpenClaw | OpenHands | Open Interpreter | Claude Computer Use | Claude Code | Cursor |
|---------|----------|-----------|-----------------|-------------------|-------------|--------|
| **Type** | Local agent | Dev agent | Local code exec | Vision automation | Terminal agent | IDE agent |
| **License** | AGPL-3.0 | MIT | AGPL-3.0 | Proprietary API | Proprietary | Proprietary |
| **GitHub Stars** | 346K | 51K+ | 58K+ | N/A (API) | 42K+ | N/A |
| **Sandboxed** | No (host) | Yes (Docker) | No (host) | Requires VM | Configurable | Yes (BG agents) |
| **LLM Support** | Any (model-agnostic) | Any | 100+ models | Claude only | Claude only | Multi-model |
| **GUI Control** | No | Yes (BrowserGym) | Yes (Computer API) | Yes (native) | Via computer-use | No |
| **Code Execution** | Yes (PI Agent) | Yes (container) | Yes (local) | Yes (bash tool) | Yes (bash) | Yes (terminal) |
| **Messaging** | 24+ platforms | Web UI / API | Terminal | API | Terminal / IDE | Editor |
| **Memory** | Persistent (local) | Session-based | Session-based | Per-conversation | Session + CLAUDE.md | Project-scoped |
| **MCP Support** | Community skills | Limited | No | Via Claude | Native | Growing |
| **Best For** | Personal assistant | Autonomous dev | Data analysis | GUI automation | Professional dev | IDE workflow |
| **Risk Level** | High (unsandboxed) | Low (sandboxed) | High (unsandboxed) | Medium (needs VM) | Medium | Low |

---

## Market Trends and Adoption (2026)

### The Numbers

- **MCP ecosystem**: 10,000+ active servers, 97 million monthly SDK downloads
- **Gartner projection**: 40% of enterprise applications will incorporate AI agents by end of 2026 (up from under 5% in early 2025)
- **OpenClaw**: Fastest project to 300K GitHub stars in history (under 5 months)
- **Claude Code**: $2.5B ARR by February 2026 -- fastest enterprise software product to $1B
- **Cursor**: $2B annualized revenue, half of Fortune 500

### Key Trends

**1. Convergence of Agent Types**: The boundaries between local, cloud, and IDE agents are dissolving. Claude Code runs locally but uses cloud models. Cursor's Background Agents run in the cloud. OpenClaw connects to any LLM. The pattern is moving toward a universal agent architecture that can operate in any environment.

**2. MCP as the Universal Tool Layer**: MCP has become the standard for tool integration, with adoption by Anthropic, OpenAI, Google, and hundreds of tool providers. The 2026 roadmap focuses on enterprise readiness: identity propagation, tool budgeting, structured error semantics, and audit trails.

**3. Sandboxing Becomes Non-Negotiable**: The OpenClaw security crisis (135,000 exposed instances) has pushed the industry toward sandboxed-by-default architectures. New agents are expected to provide isolation out of the box.

**4. Cost Optimization as First-Class Concern**: The Plan-and-Execute pattern (a capable model plans, cheaper models execute) reduces costs by 90%. This is the agentic equivalent of cloud cost optimization.

**5. Background and Asynchronous Agents**: Cursor's Background Agents and Claude Code's subagent spawning represent a shift from synchronous, interactive agents to autonomous, asynchronous workers that notify you when done.

---

## System Design Interview Angle

When asked about tool-use agents in system design interviews, focus on these dimensions:

**1. Security Model**: Is execution sandboxed? How are credentials managed? What happens if the LLM generates malicious code? (OpenClaw's AGPL license and unsandboxed execution vs. OpenHands' Docker isolation is a great comparison point.)

**2. State Management**: How does the agent maintain context across tool calls? Session-based (OpenHands) vs. persistent memory (OpenClaw) vs. file-based (Claude Code's CLAUDE.md)?

**3. Tool Discovery**: Static manifest (old approach) vs. dynamic discovery via MCP vs. skill marketplace (OpenClaw ClawHub)?

**4. Latency Budget**: Function calling (50-200ms per tool call) vs. vision-based automation (1-3 seconds per screenshot-action loop). How does this affect UX?

**5. Failure Handling**: What happens when a tool call fails? Retry? Fallback? Human-in-the-loop? How many retries before giving up?

---

## Interview Questions

### Q: Your team wants to build an internal AI assistant. Should you build on OpenClaw, OpenHands, or build custom with Claude Code + MCP?

**Strong answer:**
It depends on the use case and security requirements. OpenClaw is optimized for personal assistants with messaging integrations -- ideal if the goal is a Slack/Teams bot with persistent personality. But its unsandboxed execution and AGPL license create enterprise concerns. OpenHands is better for autonomous development tasks -- its Docker sandboxing and MIT license are enterprise-friendly. For a custom internal tool, Claude Code with MCP servers gives the most control: you define exactly which tools are available, run them in your own infrastructure, and benefit from MCP's standardized discovery and auth. The decision tree is: messaging-first? OpenClaw. Dev automation? OpenHands. Custom enterprise tool? MCP + your own agent loop.

### Q: How would you design a system that lets non-technical users automate desktop tasks using AI?

**Strong answer:**
I would use the vision-based computer-use pattern (Claude Computer Use or similar). The key design decisions: (1) Always run in a sandboxed VM so the agent cannot damage the user's actual machine. (2) Implement a Human-in-the-Loop confirmation step before any destructive action -- file deletion, form submission, purchases. (3) Use the Zoom Action pattern to reduce misclicks on dense UIs. (4) Set token/cost caps to prevent runaway loops. (5) Record all actions as an audit trail. The main tradeoff is latency -- each screenshot-action step takes 1-3 seconds -- but this approach works with any application without needing APIs. For higher-speed workflows, combine computer-use with function calling for applications that have APIs.

### Q: Why did OpenClaw grow faster than any open-source project in history? What does this tell you about the market?

**Strong answer:**
Three factors. (1) **Zero-friction onboarding**: OpenClaw connects to messaging platforms people already use (WhatsApp, Telegram). Users do not need to learn a new interface. (2) **SOUL.md personalization**: The ability to give your agent a custom personality creates emotional attachment and virality -- people share their agents. (3) **Model-agnostic architecture**: Users are not locked into one LLM provider, reducing cost and increasing flexibility. The market signal is that the agent "interface" matters more than the underlying model. People want agents that meet them where they are (messaging apps, not web UIs). The flip side: rapid growth without security investment leads to crises like the 135,000 exposed instances, which is a cautionary tale for any open-source agent project.

### Q: Compare sandboxed vs. unsandboxed execution for AI agents. When would you choose each?

**Strong answer:**
Sandboxed (Docker/VM): Use for untrusted code execution, multi-tenant systems, or any production deployment. OpenHands does this well -- each session gets its own Docker container. The trade-off is setup complexity and performance overhead. Unsandboxed (host access): Use only for single-user, trusted environments where the user is watching. Open Interpreter and OpenClaw take this approach for maximum capability. The risk is that a bad LLM output can damage the host system. The 2026 consensus is sandboxed-by-default with escape hatches for power users. In an interview, always mention that the sandbox boundary is a security decision, not just a convenience decision.

---

## References

- OpenClaw GitHub Repository and Documentation (2025-2026)
- OpenHands Documentation and SDK Reference (2025-2026)
- Open Interpreter GitHub Repository (2024-2026)
- Anthropic. "Computer Use Tool Documentation" (2024-2026)
- Anthropic. "Claude Code Overview" (2025-2026)
- MCP Specification 2025-11-25 and 2026 Roadmap
- Gartner. "AI Agent Adoption Projections" (2025-2026)
- Cursor, Windsurf, and Cline official documentation (2025-2026)

---

*Next: [Architecture Patterns for Tool-Use Agents](02-architecture-patterns.md)*
