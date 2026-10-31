# AI stack check (GitHub Action)

Flags AI agent dependencies that are **archived, deprecated, in maintenance mode, acquired, renamed or stale**: frameworks, memory layers, vector databases and MCP servers. It suggests live replacements and links each finding to its evidence and cited migration notes. It reads `package.json`, `requirements*.txt`, `pyproject.toml` and MCP configs (`.mcp.json`, `mcp.json`, `claude_desktop_config.json`).

It uses the [AI Agent Infrastructure Landscape](https://mrpeppersdev.github.io/agent-infrastructure-landscape/) catalog, which covers 950+ systems with a citation behind every fact. You can also [check a stack in the browser](https://mrpeppersdev.github.io/agent-infrastructure-landscape/check).

```yaml
# .github/workflows/ai-stack-check.yml
name: AI stack check
on: [pull_request]
permissions:
  contents: read
  pull-requests: write   # for the PR comment
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: MrPeppersDev/agent-infrastructure-landscape@main
        with:
          fail-on: archived   # none | attention | archived | drift
```

On a PR it posts or updates one comment when something is flagged. It adds file annotations and a job summary, and sets the outputs `attention-count`, `matched-count` and `manifests`.

| Input | Default | |
|---|---|---|
| `manifests` | auto-detect | Comma- or newline-separated paths |
| `fail-on` | `none` | `attention` fails on any flagged dependency; `archived` fails only on archived, deprecated or shut-down ones; `drift` also fails on dependencies pinned behind the catalog's latest release |
| `comment` | `auto` | `auto` (only when something is flagged), `always`, `never` |
| `badge-path` | — | Writes a [shields.io endpoint](https://shields.io/badges/endpoint-badge) JSON you can commit or publish |
| `index-url` | live catalog index | Falls back to the copy bundled with the action version |

**Badge:** set `badge-path: .github/badges/ai-stack.json`, commit the file (for example with a scheduled workflow), then add:

```md
![AI stack](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/<owner>/<repo>/main/.github/badges/ai-stack.json)
```

Or use the static badge to show you check:
`[![AI stack checked](https://img.shields.io/badge/AI%20stack-checked-blue)](https://mrpeppersdev.github.io/agent-infrastructure-landscape/check)`

Something wrong? Every system page has a **Suggest a correction** link.
