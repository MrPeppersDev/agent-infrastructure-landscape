// Web re-export of the shared compatibility logic (mcp/src/compat.ts) with
// the curated aliases loaded.
import aliasesRaw from '../../../taxonomy/system-aliases.json';
import { setAliases } from '../../../mcp/src/compat';

setAliases((aliasesRaw as { aliases: Record<string, string[]> }).aliases);

export * from '../../../mcp/src/compat';
