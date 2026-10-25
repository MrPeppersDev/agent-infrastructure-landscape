// The chooser / alternatives logic lives in mcp/src/chooser.ts so the MCP
// server, CLI and web app share one implementation (same pattern as
// stack-check). Re-exported here for $lib imports.
export * from '../../../mcp/src/chooser';
