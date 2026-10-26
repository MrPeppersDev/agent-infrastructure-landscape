# Hosted MCP endpoint

This is a read-only remote MCP server for the catalog. It uses the stateless form of the Streamable HTTP transport and runs as a Cloudflare Worker. People can add it with one line, with nothing to clone or build:

```sh
claude mcp add --transport http landscape https://<your-worker>.workers.dev/mcp
```

In Cursor, Claude Desktop or any client that supports remote servers, use the URL `https://<your-worker>.workers.dev/mcp`.

**Tools (8):** `ask_catalog`, `choose_memory_layer`, `choose_framework_or_store`, `check_stack`, `find_alternatives`, `check_compatibility`, `get_system`, `estimate_memory_cost`. They use the same logic as the website, the [local stdio server](../mcp) (22 tools) and the [CLI](../cli). Data is read from this repo's `main` branch and cached at the edge for an hour, so a merge reaches the endpoint without a redeploy.

## Deploy

1. Create a free Cloudflare account and an API token from the *Edit Cloudflare Workers* template.
2. Add the token as the repo secret `CLOUDFLARE_API_TOKEN`, and your account id as `CLOUDFLARE_ACCOUNT_ID`.
3. Run the **Deploy MCP worker** workflow (Actions tab). Locally, run `cd worker && npx wrangler deploy` instead.

Test locally with `npx tsx test/handler.test.ts`. It runs the handler against the repo's data files.
