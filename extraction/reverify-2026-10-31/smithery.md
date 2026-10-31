# Smithery after 2026-10-31

Source: Smithery's own announcement, [smithery.ai/future](https://smithery.ai/future), signed "Anirudh Kamath, Cofounder, Smithery (now part of Arcade)". Checked 2026-10-31.

- **Shut down 2026-10-31:** server URLs on run.tools and server.smithery.ai; the Smithery API, Connect and Toolbox; accounts and API keys. The CLI and SDKs are deprecated.
- **Continues:** smithery.ai as a public, non-proxied MCP registry powered by Arcade.dev; verified servers' pages list direct MCP URLs.

Applied with `scripts/apply_reverify.py` (`smithery.json`): `desc` and `claims` now say this, citing the announcement; the old `claims` cell was the site's banner scraped as text. The stack index keeps Smithery as **dead** (shut down), which is what matters to anyone depending on its packages or endpoints. The `funding` cell already recorded the Arcade acquisition (2026-08-05).

`lifecycle` in the input is `acquired`: with `dead`, apply_reverify sets `decay_cause: archived`, which the stack index reads as "repository archived", and that is wrong here.
