# Section audit: AI sandbox & runtime environments (reverify) — 2026-10-22

**Section:** AI sandbox & runtime environments  
**Mode:** reverify  
**Date:** 2026-10-22

## Reverify summary

- Rows audited: **10**
- Proposed cell updates: **192** (each marked `needs-review` — un-checked deltas are NOT applied)
- Refresh-only date bumps: **84**

### Proposed cell updates (maintainer-gated)

| Approve | Row | Cell | Current | Proposed | Source |
|---------|-----|------|---------|----------|--------|
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `obs-langsmith` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `obs-weave` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `cost-batching` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `cost-token-budget` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `eval-langsmith-evals` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `obs-helicone` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `obs-langfuse` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `eval-production-traffic-replay` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `cost-observability-cost-attribution` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `cost-model-routing` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `obs-opentelemetry` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `cost-streaming-only` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `eval-weights-and-biases-agent` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `obs-datadog` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `desc` | Anchor Browser provides cloud-hosted Chromium instances opt… | Secure Infrastructure for Computer Using AI agents - Deploy… | https://anchorbrowser.io/ |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `cost-prompt-caching` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `eval-helicone-evals` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `eval-custom-test-harness` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `claims` | YC W24; $2.6M seed; cloud Chromium with anti-detect + persi… | Deploy millions of browser agents to automate any web task.… | https://anchorbrowser.io/ |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `cost-semantic-caching` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `obs-arize` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `eval-human-loop` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `eval-braintrust` |  | no | depth-floor: not detected |
| [ ] | `anchor-anchor-browser--anchorbrowser-io` (Anchor (Anchor Browser)) | `obs-custom` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `obs-langsmith` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `obs-weave` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `cost-batching` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `cost-token-budget` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `eval-langsmith-evals` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `obs-helicone` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `obs-langfuse` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `eval-production-traffic-replay` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `cost-observability-cost-attribution` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `cost-model-routing` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `obs-opentelemetry` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `cost-streaming-only` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `eval-weights-and-biases-agent` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `obs-datadog` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `desc` | Browserless is a headless-browser-as-a-service — managed Ch… | Give AI agents a cloud browser that won&#x27;t crash or get… | https://www.browserless.io/ |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `cost-prompt-caching` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `eval-helicone-evals` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `eval-custom-test-harness` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `claims` | Managed Chromium/Playwright/Puppeteer endpoints; founded 20… | Bring your own agent and library, or run ours. Stealth, CAP… | https://www.browserless.io/ |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `cost-semantic-caching` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `obs-arize` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `eval-human-loop` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `eval-braintrust` |  | no | depth-floor: not detected |
| [ ] | `browserless-io--browserless-io` (Browserless.io) | `obs-custom` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `obs-langsmith` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `obs-weave` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `cost-batching` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `cost-token-budget` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `eval-langsmith-evals` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `obs-helicone` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `obs-langfuse` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `eval-production-traffic-replay` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `cost-observability-cost-attribution` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `cost-model-routing` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `obs-opentelemetry` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `cost-streaming-only` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `eval-weights-and-biases-agent` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `obs-datadog` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `desc` | Coder.com (formerly Coder Technologies) provides enterprise… | Give developers a secure, governed environment to run AI co… | https://coder.com/ |
| [ ] | `coder-com--coder-com` (Coder.com) | `cost-prompt-caching` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `eval-helicone-evals` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `eval-custom-test-harness` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `claims` | $30M Series B 2021 (Redpoint + Founders Fund + Coatue); fou… | Coder powers secure, scalable development across key indust… | https://coder.com/ |
| [ ] | `coder-com--coder-com` (Coder.com) | `cost-semantic-caching` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `obs-arize` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `eval-human-loop` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `eval-braintrust` |  | no | depth-floor: not detected |
| [ ] | `coder-com--coder-com` (Coder.com) | `obs-custom` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `obs-langsmith` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `obs-weave` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `cost-batching` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `cost-token-budget` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `eval-langsmith-evals` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `obs-helicone` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `obs-langfuse` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `eval-production-traffic-replay` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `cost-observability-cost-attribution` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `cost-model-routing` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `obs-opentelemetry` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `cost-streaming-only` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `eval-weights-and-biases-agent` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `obs-datadog` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `desc` | Daytona is an open-source cloud development environment (CD… | Deploy Al code with confidence using Daytona | https://www.daytona.io/ |
| [ ] | `daytona--daytona-io` (Daytona) | `cost-prompt-caching` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `eval-helicone-evals` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `eval-custom-test-harness` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `claims` | Apache 2.0 OSS CDE; self-hostable; AI-sandbox tier for agen… | Lightning-Fast Infrastructure for AI Development | https://www.daytona.io/ |
| [ ] | `daytona--daytona-io` (Daytona) | `cost-semantic-caching` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `obs-arize` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `eval-human-loop` |  | yes | https://www.daytona.io/ |
| [ ] | `daytona--daytona-io` (Daytona) | `eval-braintrust` |  | no | depth-floor: not detected |
| [ ] | `daytona--daytona-io` (Daytona) | `obs-custom` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `obs-langsmith` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `obs-weave` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `cost-batching` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `cost-token-budget` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `eval-langsmith-evals` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `obs-helicone` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `obs-langfuse` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `eval-production-traffic-replay` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `cost-observability-cost-attribution` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `cost-model-routing` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `obs-opentelemetry` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `cost-streaming-only` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `eval-weights-and-biases-agent` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `obs-datadog` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `desc` | e2b provides secure, ephemeral sandboxes (Firecracker micro… | The AI Agent Cloud. An isolated machine for every AI agent:… | https://e2b.dev/ |
| [ ] | `e2b--e2b-dev` (e2b) | `cost-prompt-caching` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `eval-helicone-evals` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `eval-custom-test-harness` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `claims` | $13M+ raised (seed 2023 + Series A Sept-2024; Sunflower Cap… | E2B runs the isolated machine your agent works on. You ship… | https://e2b.dev/ |
| [ ] | `e2b--e2b-dev` (e2b) | `cost-semantic-caching` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `obs-arize` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `eval-human-loop` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `eval-braintrust` |  | no | depth-floor: not detected |
| [ ] | `e2b--e2b-dev` (e2b) | `obs-custom` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `obs-langsmith` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `obs-weave` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `cost-batching` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `cost-token-budget` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `eval-langsmith-evals` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `obs-helicone` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `obs-langfuse` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `eval-production-traffic-replay` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `cost-observability-cost-attribution` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `cost-model-routing` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `obs-opentelemetry` |  | yes | https://modal.com/docs/guide/sandbox |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `cost-streaming-only` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `eval-weights-and-biases-agent` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `obs-datadog` |  | yes | https://modal.com/docs/guide/sandbox |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `desc` | Modal Labs ships a serverless container platform with first… | This page is a high-level guide to Sandboxes, secure contai… | https://modal.com/docs/guide/sandbox |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `cost-prompt-caching` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `eval-helicone-evals` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `eval-custom-test-harness` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `claims` | $87M total raised (Series B Sept-2024 led by Lux Capital + … | This page is a high-level guide to Sandboxes, secure contai… | https://modal.com/docs/guide/sandbox |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `cost-semantic-caching` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `obs-arize` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `eval-human-loop` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `eval-braintrust` |  | no | depth-floor: not detected |
| [ ] | `modal-sandboxes--modal-com` (Modal Sandboxes) | `obs-custom` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `obs-langsmith` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `obs-weave` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `cost-batching` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `cost-token-budget` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `eval-langsmith-evals` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `obs-helicone` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `obs-langfuse` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `eval-production-traffic-replay` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `cost-observability-cost-attribution` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `cost-model-routing` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `obs-opentelemetry` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `cost-streaming-only` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `eval-weights-and-biases-agent` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `obs-datadog` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `desc` | StackBlitz's WebContainers technology — browser-native Node… | Build the future of web based coding experiences, from inte… | https://webcontainers.io/ |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `cost-prompt-caching` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `eval-helicone-evals` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `eval-custom-test-harness` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `claims` | $7M Series A 2022; founded 2017 by Eric Simons + Albert Pai… | From interactive tutorials to full-blown IDEs, build instan… | https://webcontainers.io/ |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `cost-semantic-caching` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `obs-arize` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `eval-human-loop` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `eval-braintrust` |  | no | depth-floor: not detected |
| [ ] | `stackblitz-webcontainers--webcontainers-io` (StackBlitz WebContainers) | `obs-custom` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `obs-langsmith` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `obs-weave` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `cost-batching` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `cost-token-budget` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `eval-langsmith-evals` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `obs-helicone` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `obs-langfuse` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `eval-production-traffic-replay` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `cost-observability-cost-attribution` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `cost-model-routing` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `obs-opentelemetry` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `cost-streaming-only` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `eval-weights-and-biases-agent` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `obs-datadog` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `desc` | Workato is the enterprise iPaaS (integration platform) lead… | Neutral control & execution platform for Enterprise AI | https://www.workato.com/ai |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `cost-prompt-caching` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `eval-helicone-evals` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `eval-custom-test-harness` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `claims` | $200M+ ARR; $5.7B valuation Nov-2021 Series E (Battery Vent… | Neutral control & execution platform for Enterprise AI | https://www.workato.com/ai |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `cost-semantic-caching` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `obs-arize` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `eval-human-loop` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `eval-braintrust` |  | no | depth-floor: not detected |
| [ ] | `workato-ai-workflow-bot-builder--workato-com` (Workato AI (Workflow Bot Buil…) | `obs-custom` |  | no | depth-floor: not detected |

---

**All delta proposals are marked `needs-review`. Approve each in this PR by checking the box, then make the corresponding edit in `landscape.html` (the HTML comments mark each location), and merge. Unchecked deltas are NOT applied.**

New-row candidates are inserted as stub `<tr>` blocks flagged with an HTML comment. If you accept a candidate, edit the row to fill in the cells (or close the PR and let the auto-intake workflow do the full research pass on a re-submission).
