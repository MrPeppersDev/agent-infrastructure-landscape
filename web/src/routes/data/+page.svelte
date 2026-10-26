<script lang="ts">
  // /data — how to consume the catalog from code: static JSON/CSV
  // endpoints, change feeds, the MCP server and CLI.
  import { base } from '$app/paths';
  import SeoHead from '$lib/components/SeoHead.svelte';

  let { data }: { data: { catalogs: { id: string; name: string; count: number }[]; total: number; sample: { id: string; name: string }; changes: number } } = $props();
  const REPO = 'https://github.com/MrPeppersDev/agent-infrastructure-landscape';
</script>

<SeoHead
  title="Data & API — AI agent infrastructure catalog as JSON, CSV and feeds"
  description="Download the AI agent infrastructure catalog as JSON or CSV, fetch one system's cited record as JSON, or subscribe to change feeds. Static, no auth, CC-BY-4.0."
  path="/data"
/>

<main class="page">
  <h1>Data &amp; API</h1>
  <p class="lede">
    Everything on this site is built from one open dataset of {data.total} systems. It's available as static JSON and
    CSV files: no key, no rate limit, licensed <a href="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</a>
    (credit "AI Agent Infrastructure Landscape" with a link).
  </p>

  <h2>Download a catalog</h2>
  <table>
    <thead><tr><th>Catalog</th><th>Systems</th><th>Download</th></tr></thead>
    <tbody>
      {#each data.catalogs as c (c.id)}
        <tr>
          <td><a href="{base}/?product={c.id}">{c.name}</a></td>
          <td class="num">{c.count}</td>
          <td><a href="{base}/api/catalogs/{c.id}.json">JSON</a> · <a href="{base}/api/catalogs/{c.id}.csv">CSV</a></td>
        </tr>
      {/each}
      <tr>
        <td><strong>Everything</strong></td>
        <td class="num">{data.total}</td>
        <td><a href="{base}/api/catalogs/all.json">JSON</a> · <a href="{base}/api/catalogs/all.csv">CSV</a></td>
      </tr>
    </tbody>
  </table>
  <p class="note">
    Catalog files are flattened to one row per system: name, section, tier, lifecycle status, licence, latest release,
    deployment, pricing, MCP/A2A support, the seven taxonomy axes and a link to the system page. For every cell with its
    citation and tier, use the per-system JSON below or the canonical
    <a href="{REPO}/blob/main/data/landscape.json">landscape.json</a>.
  </p>

  <h2>One system as JSON</h2>
  <pre><code>GET {base}/api/systems/&lt;id&gt;.json</code></pre>
  <p>
    The id is the last part of a system page's URL. Example: <a href="{base}/api/systems/{data.sample.id}.json">{data.sample.name}</a>.
    Each file has every cell (value, citation, status, tier), the taxonomy, incoming and outgoing edges, the change history and
    the lifecycle status the stack checker uses. <a href="{base}/api/index.json">api/index.json</a> lists every id.
  </p>
  <pre><code>curl -s https://mrpeppersdev.github.io/agent-infrastructure-landscape/api/systems/{data.sample.id}.json | jq '.cells.license'</code></pre>

  <h2 id="feeds">Change feeds</h2>
  <ul>
    <li><a href="{base}/changes.xml">All changes</a> (Atom): the latest 100 of {data.changes} recorded lifecycle, licence, release, pricing and hosting changes.</li>
    <li>One system: <code>{base}/feeds/&lt;id&gt;.xml</code>, also linked from each system page's "What changed" section.</li>
    <li>Your whole stack: run <a href="{base}/check">Check stack</a> and choose "Watch these systems" to download an OPML file of feeds for every catalogued dependency.</li>
    <li><a href="{base}/feed.xml">Recently verified</a> (Atom).</li>
  </ul>

  <h2>From an agent or a script</h2>
  <ul>
    <li><a href="{REPO}/tree/main/mcp">MCP server</a>: <code>choose_memory_layer</code>, <code>check_stack</code>, <code>find_alternatives</code>, <code>search_records</code>, <code>compare</code>, <code>recent_changes</code> and more, for Claude, Cursor or any MCP client.</li>
    <li><a href="{REPO}/tree/main/cli">CLI</a>: <code>landscape check package.json --fail-on-attention</code> for CI, plus <code>choose</code>, <code>alternatives</code> and search with <code>--json</code>/<code>--csv</code>.</li>
    <li><a href="{base}/llms.txt">llms.txt</a>: a map of the site and data for LLM crawlers.</li>
    <li><a href="{base}/api/stack-index.json">Stack-checker index</a>: npm, PyPI and Docker package names and GitHub repos mapped to systems and their lifecycle status.</li>
  </ul>

  <h2>Fixing the data</h2>
  <p>
    Every system page has a <strong>Suggest a correction</strong> link. It opens a pre-filled issue; a bot checks the source,
    patches the cell and opens a pull request for review. New systems go through <a href="{base}/submit">Submit</a>.
  </p>
</main>

<style>
  .page { max-width: 860px; margin: 0 auto; padding: 24px 16px 64px; color: #c9d1d9; line-height: 1.55; }
  h1 { margin: 0 0 8px; font-size: 28px; color: #f0f6fc; }
  h2 { font-size: 19px; color: #f0f6fc; margin: 28px 0 8px; }
  a { color: #58a6ff; }
  .lede, .note { color: #8b949e; }
  table { border-collapse: collapse; width: 100%; font-size: 14px; }
  th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #21262d; }
  th { color: #8b949e; font-weight: 500; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  pre { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 10px 12px; overflow-x: auto; font-size: 13px; }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.92em; }
</style>
