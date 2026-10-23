<script lang="ts">
  // /check — "Is anything in my stack archived, acquired or stale?"
  //
  // Paste a package.json, requirements.txt, pyproject.toml or MCP client
  // config. The same parser + matcher as the MCP `check_stack` tool and
  // the `landscape check` CLI (mcp/src/stack-check.ts) runs in the
  // browser against data/stack-index.json, so pasted manifests never
  // leave the page.

  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';
  import {
    checkManifest,
    STATUS_LABEL,
    type StackIndex,
    type StackReport,
    type ManifestFormat
  } from '../../../../mcp/src/stack-check';
  import indexRaw from '../../../../data/stack-index.json';

  const index = indexRaw as unknown as StackIndex;

  const SAMPLES: Record<string, { label: string; filename: string; text: string }> = {
    pkg: {
      label: 'package.json',
      filename: 'package.json',
      text: JSON.stringify(
        {
          name: 'my-agent',
          dependencies: {
            flowise: '^3.1.0',
            '@mastra/core': '^1.0.0',
            mem0ai: '^2.2.0',
            ai: '^5.0.0',
            chromadb: '^3.0.0'
          },
          devDependencies: { '@modelcontextprotocol/server-memory': 'latest' }
        },
        null,
        2
      )
    },
    req: {
      label: 'requirements.txt',
      filename: 'requirements.txt',
      text: 'autogen-agentchat==0.7.5\nlangchain>=0.3\nlangmem\ngraphiti-core\nsemantic-kernel\nqdrant-client\n'
    },
    mcp: {
      label: 'MCP config',
      filename: '.mcp.json',
      text: JSON.stringify(
        {
          mcpServers: {
            memory: { command: 'npx', args: ['-y', '@modelcontextprotocol/server-memory'] },
            mem0: { command: 'uvx', args: ['mem0-mcp'] },
            graphiti: { command: 'docker', args: ['run', '-i', '--rm', 'zepai/knowledge-graph-mcp'] }
          }
        },
        null,
        2
      )
    }
  };

  let text = $state('');
  let filename = $state('');
  let format = $state<'' | ManifestFormat>('');
  let showAll = $state(false);
  let report = $state<StackReport | null>(null);

  function run() {
    report = text.trim()
      ? checkManifest(text, index, { filename: filename || undefined, format: format || undefined })
      : null;
  }

  function loadSample(key: string) {
    const s = SAMPLES[key];
    text = s.text;
    filename = s.filename;
    format = '';
    run();
  }

  async function onFile(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    const f = input.files?.[0];
    if (!f) return;
    filename = f.name;
    text = await f.text();
    run();
  }

  async function onDrop(e: DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer?.files?.[0];
    if (!f) return;
    filename = f.name;
    text = await f.text();
    run();
  }

  const TONE: Record<string, string> = {
    dead: 'bad',
    archived: 'bad',
    deprecated: 'bad',
    maintenance: 'warn',
    inactive: 'warn',
    stale: 'warn',
    acquired: 'warn',
    renamed: 'info',
    'research-code': 'info',
    active: 'ok'
  };

  const shown = $derived(report ? (showAll ? report.matched : report.attention) : []);
</script>

<SeoHead
  title="Check your AI stack — archived, acquired or stale dependencies"
  description="Paste a package.json, requirements.txt, pyproject.toml or MCP config to see which AI agent dependencies are archived, deprecated, acquired, renamed or stale."
  path="/check"
/>

<main class="page">
  <header>
    <h1>Check your stack</h1>
    <p class="lede">
      Paste a <code>package.json</code>, <code>requirements.txt</code>, <code>pyproject.toml</code> or an MCP
      client config. You'll see which agent frameworks, memory layers, vector stores and MCP servers in it are
      <strong>archived, deprecated, in maintenance mode, acquired, renamed or stale</strong>, with the evidence
      for each. It runs entirely in your browser; nothing you paste is sent anywhere.
    </p>
  </header>

  <section class="input">
    <div class="samples">
      Try a sample:
      {#each Object.entries(SAMPLES) as [key, s] (key)}
        <button type="button" onclick={() => loadSample(key)}>{s.label}</button>
      {/each}
      <label class="file">
        or open a file <input type="file" onchange={onFile} />
      </label>
    </div>
    <textarea
      bind:value={text}
      ondragover={(e) => e.preventDefault()}
      ondrop={onDrop}
      oninput={() => (report = null)}
      rows="12"
      spellcheck="false"
      placeholder={'{\n  "dependencies": { "flowise": "^3.1.0", "mem0ai": "^2.2.0" }\n}\n\n…or requirements.txt lines, pyproject.toml, an MCP config, or one package per line (npm:/pypi: optional)'}
      aria-label="Manifest contents"
    ></textarea>
    <div class="controls">
      <label>
        Format
        <select bind:value={format}>
          <option value="">Auto-detect</option>
          <option value="package.json">package.json</option>
          <option value="requirements.txt">requirements.txt</option>
          <option value="pyproject.toml">pyproject.toml</option>
          <option value="mcp-config">MCP config</option>
          <option value="list">One package per line</option>
        </select>
      </label>
      <button type="button" class="primary" onclick={run} disabled={!text.trim()}>Check stack</button>
    </div>
  </section>

  {#if report}
    <section class="results" aria-live="polite">
      <p class="summary">
        <strong>{report.dependencyCount}</strong> dependencies ({report.format}) ·
        <strong>{report.matched.length}</strong> in the catalog ·
        <strong class:alert={report.attention.length > 0}>{report.attention.length}</strong> need attention
      </p>

      {#if report.attention.length === 0}
        <p class="clean">
          Nothing archived, deprecated, acquired or stale among the dependencies the catalog knows about.
        </p>
      {/if}

      <label class="toggle">
        <input type="checkbox" bind:checked={showAll} /> Also show catalogued dependencies that are fine ({report.matched.length - report.attention.length})
      </label>

      {#if shown.length}
        <ul class="findings">
          {#each shown as f (f.dependency.ecosystem + f.dependency.name)}
            {@const r = f.record}
            <li class="finding tone-{TONE[r.status]}">
              <div class="head">
                <span class="badge">{STATUS_LABEL[r.status]}</span>
                <code class="dep">{f.dependency.name}</code>
                <span class="arrow">→</span>
                <a href="{base}/systems/{f.recordId}">{r.name}</a>
              </div>
              {#if r.note}<p class="note">{r.note}</p>{/if}
              {#if r.context}<p class="ctx">{r.context}</p>{/if}
              <p class="meta">
                {#if r.last_commit}<span>last commit {r.last_commit}</span>{/if}
                {#if r.license}<span>licence: {r.license}</span>{/if}
                {#if r.llm_lock}<span>model lock-in: {r.llm_lock}</span>{/if}
                {#if r.evidence}<a href={r.evidence} target="_blank" rel="noopener noreferrer">evidence ↗</a>{/if}
              </p>
            </li>
          {/each}
        </ul>
      {/if}

      {#if report.unmatched.length}
        <details class="unmatched">
          <summary>{report.unmatched.length} dependencies not in the catalog</summary>
          <p>
            {#each report.unmatched as d, i (d.ecosystem + d.name)}<code>{d.name}</code>{i < report.unmatched.length - 1 ? ', ' : ''}{/each}
          </p>
          <p class="hint">
            Missing an AI agent system that should be here? <a href="{base}/submit">Submit it</a>.
          </p>
        </details>
      {/if}

      <p class="footnote">
        Status comes from the catalog's verified lifecycle data (index built {report.indexGeneratedAt}). "Stale"
        means no commits in 12+ months on the repo the catalog tracks. Also available as the MCP tool
        <code>check_stack</code> and <code>landscape check &lt;file&gt;</code> on the CLI, for CI.
      </p>
    </section>
  {/if}
</main>

<style>
  .page {
    max-width: 920px;
    margin: 0 auto;
    padding: 24px 16px 64px;
    color: #c9d1d9;
  }
  h1 {
    margin: 0 0 8px;
    font-size: 28px;
    color: #f0f6fc;
  }
  .lede {
    color: #8b949e;
    line-height: 1.55;
    margin: 0 0 20px;
  }
  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.92em;
  }
  .samples {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    font-size: 13px;
    color: #8b949e;
    margin-bottom: 8px;
  }
  .samples button,
  .file {
    border: 1px solid #30363d;
    background: #161b22;
    color: #c9d1d9;
    border-radius: 999px;
    padding: 4px 12px;
    font: inherit;
    font-size: 13px;
    cursor: pointer;
  }
  .file input {
    display: none;
  }
  textarea {
    width: 100%;
    box-sizing: border-box;
    background: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 13px;
    line-height: 1.5;
    resize: vertical;
  }
  .controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-top: 10px;
    flex-wrap: wrap;
  }
  .controls label {
    font-size: 13px;
    color: #8b949e;
  }
  select {
    margin-left: 6px;
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px 6px;
  }
  .primary {
    background: #1f6feb;
    border: 1px solid #1f6feb;
    color: #fff;
    border-radius: 6px;
    padding: 8px 16px;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  .primary:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .results {
    margin-top: 28px;
  }
  .summary {
    font-size: 15px;
  }
  .alert {
    color: #f85149;
  }
  .clean {
    color: #3fb950;
  }
  .toggle {
    display: block;
    font-size: 13px;
    color: #8b949e;
    margin: 8px 0 16px;
  }
  .findings {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 10px;
  }
  .finding {
    border: 1px solid #30363d;
    border-left-width: 4px;
    border-radius: 8px;
    padding: 10px 14px;
    background: #0d1117;
  }
  .tone-bad {
    border-left-color: #f85149;
  }
  .tone-warn {
    border-left-color: #d29922;
  }
  .tone-info {
    border-left-color: #58a6ff;
  }
  .tone-ok {
    border-left-color: #3fb950;
  }
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px;
  }
  .badge {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 2px 8px;
    border-radius: 999px;
    background: #21262d;
  }
  .tone-bad .badge {
    color: #f85149;
  }
  .tone-warn .badge {
    color: #d29922;
  }
  .tone-info .badge {
    color: #58a6ff;
  }
  .tone-ok .badge {
    color: #3fb950;
  }
  .dep {
    color: #f0f6fc;
  }
  .arrow {
    color: #6e7681;
  }
  .head a {
    color: #58a6ff;
  }
  .note,
  .ctx {
    margin: 6px 0 0;
    font-size: 14px;
  }
  .ctx {
    color: #8b949e;
  }
  .meta {
    margin: 6px 0 0;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 12px;
    color: #6e7681;
  }
  .meta a {
    color: #58a6ff;
  }
  .unmatched {
    margin-top: 20px;
    font-size: 13px;
    color: #8b949e;
  }
  .unmatched code {
    color: #c9d1d9;
  }
  .hint a {
    color: #58a6ff;
  }
  .footnote {
    margin-top: 24px;
    font-size: 12px;
    color: #6e7681;
    line-height: 1.5;
  }
</style>
