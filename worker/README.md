# Hosted MCP endpoint

This is a read-only remote MCP server for the catalog. It uses the stateless form of the Streamable HTTP transport and runs as a Cloudflare Worker. People can add it with one line, with nothing to clone or build:

```sh
claude mcp add --transport http landscape https://<your-worker>.workers.dev/mcp
```

In Cursor, Claude Desktop or any client that supports remote servers, use the URL `https://<your-worker>.workers.dev/mcp`.

**Tools (11):** `ask_catalog`, `plan_stack`, `context_pack`, `choose_memory_layer`, `choose_framework_or_store`, `check_stack`, `find_alternatives`, `check_compatibility`, `get_system`, `estimate_memory_cost`, `estimate_vector_store_cost`. They use the same logic as the website, the [local stdio server](../mcp) (25 tools) and the [CLI](../cli). Data is read from this repo's `main` branch and cached at the edge for an hour, so a merge reaches the endpoint without a redeploy.

**One silo:** `https://<your-worker>.workers.dev/mcp/<silo>` (for example `/mcp/memory` or `/mcp/coding`) lists `ask_catalog` and `get_system` plus that silo's tools from `taxonomy/silos.json`, and `ask_catalog` searches only the silo's sections. `GET /` lists every silo endpoint.

## Deploy

Cloudflare Workers Builds deploys this folder on every push to `main`. In the Cloudflare dashboard, the Worker `agent-infrastructure-landscape` → **Settings → Build** needs:
- Git repository: this repo. Production branch: `main`.
- Root directory: `worker`. Build command: none. Deploy command: `npx wrangler deploy`.
- Build watch paths, Include: `worker/*` and `mcp/src/*`. Data changes need no redeploy, so this saves build minutes.

The endpoint is `https://agent-infrastructure-landscape.<subdomain>.workers.dev/mcp`. `workers_dev = true` in `wrangler.toml` keeps that URL on.

The **Deploy MCP worker** workflow is an alternative for deploying from GitHub Actions. It needs the repo secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, and skips the deploy with a notice when they're missing. Locally, run `cd worker && npx wrangler deploy`.

Test locally with `npx tsx test/handler.test.ts`. It runs the handler against the repo's data files.
