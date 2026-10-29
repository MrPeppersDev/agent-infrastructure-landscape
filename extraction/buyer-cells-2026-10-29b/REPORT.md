# Buyer cells for the stack-layers intake (2026-10-29)

These cells cover the 57 rows added by the `2026-10-stack-layers` intake. One research agent followed `prompt.md` (the same rules as `../buyer-cells-2026-10-29/`) and used primary sources only: trust centres, docs SDK pages, official repos and registries. It filled **139 cells on 54 rows**. `apply_v1_1_research.py` applied all 139.

| Cell | Filled | Of which not-applicable |
|---|---|---|
| sdk-languages | 48 | |
| compliance-certifications | 46 | 20 (8 benchmarks, 12 open-source projects with no hosted service) |
| protocol-support | 28 | |
| maturity | 17 | |

**Not in GA**

- Official MCP Registry: preview.
- Docker MCP Catalog & Toolkit: beta.
- Golem Cloud: developer preview.
- NeMo Guardrails and Inspect AI: beta per PyPI classifiers (medium confidence).

**Left empty on purpose**

- **Okta Cross App Access:** the trust portal could not be loaded.
- **Falcon Guardian (ex-Pangea):** CrowdStrike's attestations cover the Falcon platform, and the page does not say whether the AIDR module is in scope.
- **SentinelOne Prompt Security:** no public SDK; the only compliance claim is platform-level.
- **Glama:** no trust page or SDK.
- **"SOC 2" with no type stated** (Bifrost, TrueFoundry, Stytch): left out, per the rules.
- **Cloudflare rows:** only the company-wide certificates are recorded. FedRAMP, PCI and HIPAA depend on which services are in scope.

**Judgment calls (medium confidence)**

- Gateways list their implementation language plus `rest`, matching how LiteLLM and vLLM are already recorded.
- MCP gateways that proxy servers are tagged `mcp-client,mcp-server`.
- A stable ≥1.0 release counts as `ga` only where nothing else states the release stage.
