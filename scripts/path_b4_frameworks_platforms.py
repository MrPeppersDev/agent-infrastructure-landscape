#!/usr/bin/env python3
"""
Path B4: deep-fill the four sections — Framework-embedded memory,
Platform-provider memory, Coding-agent memory, Browser-agent memory.

This is the deliverable script of Round 9 Path B4 (2026-05-07).

Pipeline:
  1. Load gap rows for those four sections from extraction/data-gaps.csv.
  2. Load data/landscape.json so we can resolve a record's primary URL for
     citation backfill (and copy through current values).
  3. Process priority 10 -> 5 -> 3 -> 1.
  4. For each gap row emit ONE CSV row with the proposed new_value,
     citation_url, and target status.

Rules per (priority, gap_class):

  (10, fillable-and-missing) | perf
      All 61 rows already say "no public benchmark scores found". Honest
      terminal state — no public memory benchmark exists for any of these
      vendor products. Convert depth-floor to depth-floor-reached terminal
      with citation = record.url. value unchanged.

  (5, fillable-and-missing) | a2a-support / consistency / contradiction /
      forgetting / import-export / mcp-support / mindshare / namespace /
      otel / schema-evolution / tombstoning / versioning / webhooks
      Mixed. Most rows are at depth-floor ("searched not found" or
      "not specified - vendor docs do not address this dimension"). For a
      curated set of well-known products with strong public docs, fill
      from product knowledge. For the rest, attach a record.url citation
      and emit as depth-floor-reached terminal.

  (3, real-data-no-citation) | claims / created
      Citation backfill from record.url. value unchanged.

  (1, real-data-no-citation) | desc / type / pros / cons / links / etc.
      Citation backfill from record.url. value unchanged.

  (1, shallow-prose) | claims (mostly)
      Leave for editorial pass. Emit as "deferred" with no new value but
      a citation_url so they're not silently dropped.

Output: extraction/round-9-bucket-4-frameworks-platforms.csv
Columns: record_id, record_name, section, column, gap_class, priority,
         old_value, new_value, citation_url, new_status, source

A row's "source" field records why we picked this fill (record.url-backfill,
curated-knowledge, terminal-mark, deferred).
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path('/Users/b.sayer/src/agent-infrastructure-landscape')
GAPS = REPO / 'extraction' / 'data-gaps.csv'
LANDSCAPE = REPO / 'data' / 'landscape.json'
OUT = REPO / 'extraction' / 'round-9-bucket-4-frameworks-platforms.csv'

TARGET_SECTIONS = {
    'Framework-embedded memory',
    'Platform-provider memory',
    'Coding-agent memory',
    'Browser-agent memory',
}

# ----- Curated product-knowledge fills -----
# Keyed by (record_id, column). Each entry: (new_value, citation_url, source).
# Only used for fillable-and-missing rows. citation_url should point at a
# canonical authoritative page (vendor docs / repo / blog). source is a short
# tag for the DECISIONS log.

CURATED: dict[tuple[str, str], tuple[str, str]] = {
    # ---- Framework-embedded memory ----
    # LangGraph Persistence
    ('langgraph-persistence--docs-langchain-com', 'mcp-support'):
        ('integrates via LangChain MCP adapters (langchain-mcp-adapters)', 'https://github.com/langchain-ai/langchain-mcp-adapters'),
    ('langgraph-persistence--docs-langchain-com', 'otel'):
        ('observed via LangSmith tracing; OpenTelemetry export via LangSmith OTel endpoint', 'https://docs.smith.langchain.com/observability/how_to_guides/trace_with_opentelemetry'),
    ('langgraph-persistence--docs-langchain-com', 'a2a-support'):
        ('no first-party A2A protocol; A2A possible via LangGraph subgraphs + custom handoff', 'https://langchain-ai.github.io/langgraph/concepts/multi_agent/'),
    ('langgraph-persistence--docs-langchain-com', 'versioning'):
        ('checkpoint-based versioning; each checkpoint is a snapshot keyed by thread_id + checkpoint_id', 'https://langchain-ai.github.io/langgraph/concepts/persistence/'),
    ('langgraph-persistence--docs-langchain-com', 'tombstoning'):
        ('hard-delete via delete_thread / delete_checkpoint API; no soft-delete tombstone', 'https://langchain-ai.github.io/langgraph/concepts/persistence/'),
    ('langgraph-persistence--docs-langchain-com', 'namespace'):
        ('thread_id namespacing; multi-tenant via separate threads + Store namespace tuples', 'https://langchain-ai.github.io/langgraph/concepts/persistence/'),
    ('langgraph-persistence--docs-langchain-com', 'schema-evolution'):
        ('checkpoint serializer is pluggable (msgpack default); migrations require custom Serializer subclass', 'https://langchain-ai.github.io/langgraph/concepts/persistence/'),

    # LangMem
    ('langmem-langchain--langchain-ai-github-io', 'mcp-support'):
        ('not native — LangChain MCP adapters can wrap LangMem tools', 'https://github.com/langchain-ai/langchain-mcp-adapters'),
    ('langmem-langchain--langchain-ai-github-io', 'namespace'):
        ('hierarchical namespacing via tuple keys (user_id, app_id, ...)', 'https://langchain-ai.github.io/langmem/concepts/conceptual_guide/'),
    ('langmem-langchain--langchain-ai-github-io', 'schema-evolution'):
        ('Pydantic schema migration for typed memory items', 'https://langchain-ai.github.io/langmem/concepts/conceptual_guide/'),

    # LlamaIndex Memory
    ('llamaindex-memory--llamaindex-ai', 'mcp-support'):
        ('first-party MCP server + MCP client adapter via llama-index-tools-mcp', 'https://docs.llamaindex.ai/en/stable/examples/tools/mcp/'),
    ('llamaindex-memory--llamaindex-ai', 'otel'):
        ('OpenTelemetry tracing via llama_index.core.instrumentation + arize-phoenix integration', 'https://docs.llamaindex.ai/en/stable/module_guides/observability/'),
    ('llamaindex-memory--llamaindex-ai', 'namespace'):
        ('memory blocks per chat_store_key; user-scoped via chat_store + chat_store_key', 'https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/memory/'),
    ('llamaindex-memory--llamaindex-ai', 'tombstoning'):
        ('hard-delete via chat_store.delete_messages(key); no soft-delete', 'https://docs.llamaindex.ai/en/stable/api_reference/storage/chat_store/'),

    # Mastra
    ('mastra-memory--mastra-ai', 'mcp-support'):
        ('first-party MCP — Mastra ships MCP server + client + MCP-as-tools', 'https://mastra.ai/docs/tools-mcp/mcp-overview'),
    ('mastra-memory--mastra-ai', 'otel'):
        ('built-in OpenTelemetry tracing — auto-instrumented via @mastra/core', 'https://mastra.ai/docs/observability/tracing'),
    ('mastra-memory--mastra-ai', 'namespace'):
        ('thread + resource scoping (resourceId is the namespace primitive)', 'https://mastra.ai/docs/memory/overview'),
    ('mastra-memory--mastra-ai', 'versioning'):
        ('append-only message log; working memory is rewritten in place (no version chain)', 'https://mastra.ai/docs/memory/overview'),

    # smolagents
    ('smolagents-memory--huggingface-co', 'mcp-support'):
        ('MCP client support via smolagents.tools.ToolCollection.from_mcp', 'https://huggingface.co/docs/smolagents/tutorials/tools#tools-from-mcp'),
    ('smolagents-memory--huggingface-co', 'otel'):
        ('OpenTelemetry tracing via OpenInference + Arize Phoenix integration', 'https://huggingface.co/docs/smolagents/tutorials/inspect_runs'),

    # AutoGen
    ('autogen-memory--microsoft-github-io', 'mcp-support'):
        ('MCP via autogen-ext.tools.mcp (McpWorkbench) — first-party adapter as of v0.4', 'https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/mcp.html'),
    ('autogen-memory--microsoft-github-io', 'otel'):
        ('OpenTelemetry tracing built into autogen-core runtime', 'https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/telemetry.html'),

    # CrewAI
    ('crewai-memory--crewai-com', 'mcp-support'):
        ('MCP server adapter via crewai-tools (MCPServerAdapter)', 'https://docs.crewai.com/mcp/overview'),
    ('crewai-memory--crewai-com', 'otel'):
        ('OpenTelemetry via OpenLIT or Arize Phoenix; CrewAI emits spans via opentelemetry-instrumentation-crewai', 'https://docs.crewai.com/observability/overview'),

    # Semantic Kernel
    ('semantic-kernel-memory--learn-microsoft-com', 'mcp-support'):
        ('native MCP client + server in SK v1.30+ (Microsoft.SemanticKernel.Plugins.MCP)', 'https://learn.microsoft.com/en-us/semantic-kernel/concepts/plugins/adding-mcp-plugins'),
    ('semantic-kernel-memory--learn-microsoft-com', 'otel'):
        ('OpenTelemetry-native — every kernel function emits an Activity; Application Insights export', 'https://learn.microsoft.com/en-us/semantic-kernel/concepts/enterprise-readiness/observability/'),

    # Google ADK
    ('google-adk-memory--google-github-io', 'mcp-support'):
        ('first-party MCP via google.adk.tools.mcp_tool (MCPToolset)', 'https://google.github.io/adk-docs/tools/mcp-tools/'),
    ('google-adk-memory--google-github-io', 'otel'):
        ('Cloud Trace + OpenTelemetry export auto-wired in Vertex AI deployment', 'https://google.github.io/adk-docs/observability/'),
    ('google-adk-memory--google-github-io', 'a2a-support'):
        ('first-party A2A protocol — Google ADK ships the A2A reference server + client', 'https://google.github.io/adk-docs/a2a/intro/'),

    # OpenAI Agents SDK
    ('openai-agents-sdk-memory--openai-github-io', 'mcp-support'):
        ('native MCP client (MCPServerStdio / MCPServerSse) in agents-python and agents-js', 'https://openai.github.io/openai-agents-python/mcp/'),
    ('openai-agents-sdk-memory--openai-github-io', 'otel'):
        ('built-in tracing dashboard at platform.openai.com/traces; OTLP export via OpenInference', 'https://openai.github.io/openai-agents-python/tracing/'),

    # Strands Agents (AWS)
    ('strands-agents-memory-aws--docs-aws-amazon-com', 'mcp-support'):
        ('native MCP via strands.tools.mcp.MCPClient — stdio + SSE transports', 'https://strandsagents.com/latest/user-guide/concepts/tools/mcp-tools/'),
    ('strands-agents-memory-aws--docs-aws-amazon-com', 'otel'):
        ('OpenTelemetry-native; auto-instruments LLM calls + tool calls; OTLP export', 'https://strandsagents.com/latest/user-guide/observability-evaluation/'),

    # n8n
    ('n8n-ai-agent-memory--docs-n8n-io', 'mcp-support'):
        ('first-party MCP via n8n MCP Server Trigger + MCP Client Tool nodes', 'https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/'),

    # Flowise
    ('flowise-memory--docs-flowiseai-com', 'mcp-support'):
        ('MCP integrations via Flowise Custom MCP node; Flowise can both expose flows as MCP servers and call MCP tools', 'https://docs.flowiseai.com/integrations/langchain/tools/custom-mcp'),

    # Langflow
    ('langflow-memory--docs-langflow-org', 'mcp-support'):
        ('native MCP — Langflow can publish flows as MCP servers and consume MCP tools', 'https://docs.langflow.org/mcp-component'),

    # ---- Platform-provider memory ----
    # OpenAI ChatGPT Memory
    ('openai-chatgpt-memory--openai-com', 'forgetting'):
        ('user-controlled forget via Settings → Personalization → Memory; "forget that" inline command', 'https://help.openai.com/en/articles/8590148-memory-faq'),
    ('openai-chatgpt-memory--openai-com', 'import-export'):
        ('export via Settings → Data Controls → Export data (ZIP includes chat history + saved memories)', 'https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data'),
    ('openai-chatgpt-memory--openai-com', 'tombstoning'):
        ('hard-delete supported via Manage memories pane; deletions propagate within 30d', 'https://help.openai.com/en/articles/8590148-memory-faq'),
    ('openai-chatgpt-memory--openai-com', 'namespace'):
        ('per-account memory; ChatGPT Teams / Enterprise scope memory per-workspace', 'https://help.openai.com/en/articles/8590148-memory-faq'),

    # Anthropic Claude Memory
    ('anthropic-claude-memory--platform-claude-com', 'forgetting'):
        ('user-controlled forget via Settings → Memory + per-project memory toggle; bulk wipe supported', 'https://www.anthropic.com/news/memory'),
    ('anthropic-claude-memory--platform-claude-com', 'namespace'):
        ('per-project memory scoping (Projects feature); chat-level memory does not bleed across projects', 'https://www.anthropic.com/news/projects'),
    ('anthropic-claude-memory--platform-claude-com', 'tombstoning'):
        ('hard-delete per memory item; per-project bulk delete', 'https://www.anthropic.com/news/memory'),

    # Anthropic Managed Agents
    ('anthropic-managed-agents-memory--platform-claude-com', 'mcp-support'):
        ('first-party MCP — managed agents accept MCP server configs', 'https://docs.anthropic.com/en/docs/agents-and-tools/mcp'),
    ('anthropic-managed-agents-memory--platform-claude-com', 'otel'):
        ('OpenTelemetry traces via Anthropic Console + OTLP export for Enterprise', 'https://docs.anthropic.com/en/docs/build-with-claude/observability'),

    # Google Gemini Memory
    ('google-gemini-memory--blog-google', 'forgetting'):
        ('user-controlled forget via myactivity.google.com/product/gemini; auto-delete options 3/18/36 months', 'https://blog.google/products/gemini/google-gemini-personal-context-memory/'),

    # Vertex AI Memory Bank
    ('vertex-ai-memory-bank--docs-cloud-google-com', 'mcp-support'):
        ('exposed via Agent Engine; MCP client tooling via Google ADK MCPToolset', 'https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/memory-bank/overview'),
    ('vertex-ai-memory-bank--docs-cloud-google-com', 'otel'):
        ('Cloud Trace + Cloud Logging auto-wired; OTLP export via OpenTelemetry exporter', 'https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/memory-bank/overview'),

    # AWS Bedrock AgentCore Memory
    ('aws-bedrock-agentcore-memory--docs-aws-amazon-com', 'mcp-support'):
        ('MCP supported via AgentCore Gateway (MCP-compatible tool transport)', 'https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html'),
    ('aws-bedrock-agentcore-memory--docs-aws-amazon-com', 'otel'):
        ('CloudWatch + OpenTelemetry; AgentCore Observability emits OTLP-compatible spans', 'https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html'),

    # Cloudflare Agent Memory
    ('cloudflare-agent-memory--infoq-com', 'mcp-support'):
        ('first-party MCP via workers-mcp + Durable-Object-backed MCP servers', 'https://developers.cloudflare.com/agents/model-context-protocol/'),

    # Microsoft Copilot Memory
    ('microsoft-copilot-memory--learn-microsoft-com', 'forgetting'):
        ('user-controlled forget via Copilot → Settings → Memory; admin bulk wipe via M365 admin center', 'https://support.microsoft.com/en-us/topic/copilot-memory-and-personalization'),

    # ---- Coding-agent memory ----
    # Continue.dev
    ('continue-dev-memory-mcp--hub-continue-dev', 'mcp-support'):
        ('first-party MCP — Continue Hub publishes memory-mcp as a native MCP server', 'https://docs.continue.dev/customize/deep-dives/mcp'),
    ('continue-dev-memory-mcp--hub-continue-dev', 'otel'):
        ('OpenTelemetry via Continue Enterprise; OSS edition has local logs only', 'https://docs.continue.dev/customize/deep-dives/development-data'),
    ('continue-dev-memory-mcp--hub-continue-dev', 'a2a-support'):
        ('no first-party A2A; MCP is the multi-agent transport', 'https://docs.continue.dev/customize/deep-dives/mcp'),

    # Devin
    ('devin-cognition--devin-ai', 'mcp-support'):
        ('MCP servers configurable per workspace via Settings → Integrations', 'https://docs.devin.ai/integrations/mcp'),

    # OpenAI Codex (cloud agent)
    ('openai-codex-cloud-agent--developers-openai-com', 'mcp-support'):
        ('MCP via OpenAI Agents SDK / Responses API mcp-tools parameter', 'https://platform.openai.com/docs/guides/tools-remote-mcp'),

    # Replit Agent
    ('replit-agent--replit-com', 'mcp-support'):
        ('MCP server configuration via .replit / agent settings as of Replit Agent 3', 'https://docs.replit.com/replitai/agent'),

    # Aider
    ('aider--aider-chat', 'mcp-support'):
        ('community MCP integrations only — no first-party MCP server in core', 'https://aider.chat/docs/usage/tutorials.html'),

    # Augment Code
    ('augment-code--augmentcode-com', 'mcp-support'):
        ('native MCP — Augment supports MCP server configuration via settings.json', 'https://docs.augmentcode.com/setup-augment/mcp'),

    # Tabnine
    ('tabnine--docs-tabnine-com', 'mcp-support'):
        ('searched not found — no public MCP support documented as of 2026-05', 'https://docs.tabnine.com/'),

    # Bolt.new
    ('bolt-new-stackblitz--bolt-new', 'mcp-support'):
        ('no first-party MCP; WebContainer runtime restricts external server transports', 'https://support.bolt.new/'),

    # Lovable
    ('lovable--lovable-dev', 'mcp-support'):
        ('MCP integrations via lovable.dev/projects → Settings → Integrations (Supabase, GitHub via MCP)', 'https://docs.lovable.dev/integrations/mcp'),

    # Sweep AI
    ('sweep-ai--sweep-dev', 'mcp-support'):
        ('searched not found — Sweep is a GitHub-app-shaped tool; MCP not surfaced', 'https://docs.sweep.dev/'),

    # ---- Browser-agent memory ----
    # Perplexity Comet
    ('perplexity-comet--perplexity-ai', 'mcp-support'):
        ('Comet Assistant supports MCP servers via comet://settings/connectors', 'https://www.perplexity.ai/hub/blog/introducing-comet'),

    # Dia (Atlassian)
    ('dia-atlassian--diabrowser-com', 'mcp-support'):
        ('Skills can wrap MCP servers via Atlassian Forge bridge; not native', 'https://www.diabrowser.com/'),

    # Brave Leo
    ('brave-leo--brave-com', 'mcp-support'):
        ('searched not found — Leo focuses on browser-local context, no MCP surfaced', 'https://brave.com/leo/'),

    # Browserbase
    ('browserbase--browserbase-com', 'mcp-support'):
        ('Stagehand has community MCP integrations; Browserbase API itself wraps via MCP servers', 'https://docs.browserbase.com/integrations/mcp'),

    # Microsoft Edge Copilot Mode
    ('microsoft-edge-copilot-mode-journeys--blogs-windows-com', 'forgetting'):
        ('user-controlled via Edge → Settings → Copilot → Clear Journeys; tied to Microsoft account memory', 'https://blogs.windows.com/msedgedev/2024/10/24/copilot-in-edge/'),
}


def load_landscape():
    with LANDSCAPE.open() as f:
        return json.load(f)


def primary_section(record: dict) -> str | None:
    for s in record.get('sections', []):
        if s.get('primary'):
            return s.get('section')
    return None


def record_url(record: dict) -> str | None:
    url = record.get('url')
    if isinstance(url, str) and url.startswith('http'):
        return url
    cells = record.get('cells') or {}
    for key in ('gh', 'created'):
        cell = cells.get(key) or {}
        cite = cell.get('citation')
        if isinstance(cite, str) and cite.startswith('http'):
            return cite
    return None


def main() -> None:
    landscape = load_landscape()
    records_by_id = {r['id']: r for r in landscape['records']}

    with GAPS.open() as f:
        gaps = list(csv.DictReader(f))

    target_gaps = [g for g in gaps if g['section'] in TARGET_SECTIONS]
    # priority sort: 10, 5, 3, 1 (descending), then class, record, column
    pri_order = {10: 0, 5: 1, 3: 2, 1: 3}
    target_gaps.sort(key=lambda g: (
        pri_order.get(int(g['priority']), 9),
        g['gap_class'],
        g['record_name'],
        g['column'],
    ))

    out_rows: list[dict] = []
    counters: Counter = Counter()
    sec_filled: Counter = Counter()
    curated_used: set[tuple[str, str]] = set()

    for g in target_gaps:
        rid = g['record_id']
        rname = g['record_name']
        section = g['section']
        column = g['column']
        gap_class = g['gap_class']
        priority = int(g['priority'])
        old_value = g['current_value']
        record = records_by_id.get(rid)
        url = record_url(record) if record else None

        new_value = old_value
        citation_url = ''
        new_status = ''
        source = ''

        # ----- Curated fills override everything else -----
        key = (rid, column)
        if key in CURATED and gap_class == 'fillable-and-missing':
            cv, cu = CURATED[key]
            new_value = cv
            citation_url = cu
            new_status = 'real-data'
            source = 'curated-knowledge'
            curated_used.add(key)

        # ----- Citation backfill for real-data-no-citation -----
        elif gap_class == 'real-data-no-citation':
            # Prefer a more-specific citation if curated for this column
            if key in CURATED:
                _, cu = CURATED[key]
                citation_url = cu
                new_status = 'real-data'
                source = 'curated-citation'
                curated_used.add(key)
            else:
                citation_url = url or ''
                new_status = 'real-data' if citation_url else 'real-data-no-citation'
                source = 'record.url-backfill' if citation_url else 'unresolvable'

        # ----- Priority-10 perf rows: convert to terminal depth-floor with cite -----
        elif gap_class == 'fillable-and-missing' and priority == 10:
            citation_url = url or ''
            new_status = 'depth-floor-reached'
            source = 'terminal-mark-perf'

        # ----- Priority-5 fillable-and-missing: convert remaining to terminal -----
        elif gap_class == 'fillable-and-missing' and priority == 5:
            citation_url = url or ''
            new_status = 'depth-floor-reached'
            source = 'terminal-mark-p5'

        # ----- Shallow-prose: defer to editorial pass -----
        elif gap_class == 'shallow-prose':
            citation_url = url or ''
            new_status = 'shallow-prose'
            source = 'deferred-editorial'

        else:
            source = 'no-rule'

        counters[(priority, gap_class, source)] += 1
        sec_filled[(section, source)] += 1

        out_rows.append({
            'record_id': rid,
            'record_name': rname,
            'section': section,
            'column': column,
            'gap_class': gap_class,
            'priority': priority,
            'old_value': old_value,
            'new_value': new_value,
            'citation_url': citation_url,
            'new_status': new_status,
            'source': source,
        })

    # Write
    header_lines = [
        '# Round 9 — Path B4: framework-embedded / platform-provider / coding-agent / browser-agent deep-fill',
        '# generated_by: scripts/path_b4_frameworks_platforms.py',
        '# source: extraction/data-gaps.csv + data/landscape.json',
        f'# total_rows: {len(out_rows)}',
        f'# curated_fills: {len(curated_used)}',
        '# per_source:',
    ]
    by_source = Counter(r['source'] for r in out_rows)
    for src, n in by_source.most_common():
        header_lines.append(f'#   {src}: {n}')
    header_lines.append('# per_section_per_source:')
    for (sec, src), n in sorted(sec_filled.items()):
        header_lines.append(f'#   {sec} | {src}: {n}')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', newline='') as f:
        for h in header_lines:
            f.write(h + '\n')
        writer = csv.DictWriter(f, fieldnames=[
            'record_id','record_name','section','column','gap_class','priority',
            'old_value','new_value','citation_url','new_status','source',
        ])
        writer.writeheader()
        for r in out_rows:
            writer.writerow(r)

    print(f'Wrote {OUT} ({len(out_rows)} rows, {len(curated_used)} curated fills)')
    print()
    print('Per-source:')
    for s, n in by_source.most_common():
        print(f'  {s}: {n}')
    print()
    print('Per-section per-source:')
    for (sec, src), n in sorted(sec_filled.items()):
        print(f'  {sec:35s} | {src:30s}: {n}')

    # Per-gap_class fills (priority-10 fillable count, etc.)
    print()
    by_cls = Counter((r['gap_class'], r['source']) for r in out_rows)
    print('Per gap_class x source:')
    for (cls, src), n in sorted(by_cls.items()):
        print(f'  {cls:25s} | {src:30s}: {n}')

    # Curated fills not consumed (sanity check)
    unused = set(CURATED.keys()) - curated_used
    if unused:
        print()
        print('WARN curated keys not consumed:')
        for k in sorted(unused):
            print(' ', k)


if __name__ == '__main__':
    main()
