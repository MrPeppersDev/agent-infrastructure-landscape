// Unit tests for the leaderboard funding parser (issue #322).
// Run: npx tsx web/scripts/test-leaderboards.ts
import { extractFunding, formatUsd, companyKey, onePerCompany, type Ranked } from '../src/lib/leaderboards';

let failures = 0;
function eq(got: unknown, want: unknown, msg: string): void {
  if (got !== want) {
    failures++;
    console.error(`FAIL ${msg}: got ${got}, want ${want}`);
  }
}

// Public companies: market value, never funding.
eq(extractFunding('Microsoft public (MSFT); market cap ~$3T'), null, 'Microsoft market cap');
eq(extractFunding('NVIDIA parent — public company, $3T+ mkt cap'), null, 'NVIDIA mkt cap');
eq(extractFunding('Amazon (AMZN) public; ~$2T market cap; capex $100B+ 2025 (largest among hyperscalers)'), null, 'Amazon');
eq(extractFunding('Alphabet (GOOGL) public; ~$2T+ market cap; Google AI capex $75B+ 2025'), null, 'Alphabet');
eq(extractFunding('$183M total raised (CapitalG/NEA/General Atlantic); public company (DUOL)'), null, 'public after IPO');

// Private companies: the total when stated, else the largest round; never a valuation.
eq(extractFunding('LangChain Inc raised $25M Series A 2024-02 (Sequoia led; $200M valuation rumored); ~$110M total per later rounds 2024-2025.'), 110e6, 'LangChain total');
eq(extractFunding('$400M Series C at $13.3B valuation (2026-08-12), led by Menlo Ventures; prior $330M Series B at $6.6B (2025-12-18)'), 400e6, 'largest round, not valuation');
eq(extractFunding('OpenAI parent — ~$157B val 2024-10; $40B round Mar-2025 ($300B val)'), 40e9, 'round, skipping vals');
eq(extractFunding('Numerai: $30M Series C Nov-2025 ($500M val; led by university endowments)'), 30e6, 'val in parentheses');
eq(extractFunding('$57.9B+ total raised; $500B valuation (2025 secondary tender); Microsoft $13B+ strategic investment'), 57.9e9, 'total first');
eq(extractFunding('Acquired by Cognition (2025-07-14); prior Codeium $150M Series C (2024); ~$3B reported OpenAI offer'), 150e6, 'offer is not funding');

// No raise stated.
eq(extractFunding('Self-funded via High-Flyer; no external VC disclosed; estimated <$100M training cost'), null, 'training cost');
eq(extractFunding('Bootstrapped; no external VC funding; subscription-supported'), null, 'bootstrapped');
eq(extractFunding('£150K pre-seed (Feb 2021; Flamefinch Partners)'), null, 'non-dollar ignored');

eq(formatUsd(2.5e9), '$2.5B', 'billions');
eq(formatUsd(150e6), '$150M', 'millions');
eq(formatUsd(4.1e6), '$4.1M', 'small millions keep a decimal');
eq(formatUsd(500e3), '$500K', 'thousands');

// One row per company on the funding board.
eq(companyKey('claude-code-anthropic--anthropic-com'), 'anthropic', 'domain key');
eq(companyKey('anthropic-claude-memory--docs-anthropic-com'), 'anthropic', 'docs subdomain');
eq(companyKey('openai-codex-cli--gh-openai-codex'), 'openai', 'GitHub org');
eq(companyKey('chatgpt-study-mode--chatgpt-com'), 'openai', 'alias');
const row = (id: string, value: number, display = '') => ({ record: { id, name: id } as Ranked['record'], value, display });
const board = onePerCompany([
  row('a--anthropic-com', 65e9), row('b--docs-anthropic-com', 61.5e9), row('c--gh-mlflow-mlflow', 43e9, 'sponsored by Databricks'), row('d--x-ai', 20e9)
], 10);
eq(board.map((r) => r.record.id).join(','), 'a--anthropic-com,d--x-ai', 'company rows merged, sponsor cells dropped');
eq(board[0].also.join(','), 'b--docs-anthropic-com', 'merged products listed');

if (failures) {
  console.error(`${failures} leaderboard test(s) failed`);
  process.exit(1);
}
console.log('all leaderboard tests passed');
