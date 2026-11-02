# Golden stacks

Recorded picks for the twenty golden plan_stack questions (`mcp/src/golden-stacks.ts`). CI fails when a pick leaves its accepted set (the pick and its two runners-up). Review this table when re-recording.

## support-default

`{"product":"support-agent"}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | LiteLLM | OpenRouter, agentgateway |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| vectors | Milvus | Weaviate, Elasticsearch |
| embeddings | OpenAI Embeddings | Cohere Embed, Sentence Transformers |
| tools | Composio | Arcade.dev, IBM ContextForge MCP Gateway |
| observability | Arize Phoenix | OpenLLMetry (Traceloop), Braintrust |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Google Cloud Model Armor |

## support-ts-self-soc2

`{"product":"support-agent","language":"typescript","hosting":"self","compliance":["soc2-type2"]}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | LlamaIndex (framework), OpenAI Agents SDK |
| model | Mistral Large 2 / Mixtral family | Cohere Command R+ / Command A, Jamba (AI21 Labs) |
| gateway | LiteLLM | OpenRouter, agentgateway |
| memory | Hindsight (Vectorize) | Zep & Graphiti, Supermemory |
| vectors | Qdrant | Chroma, LanceDB |
| embeddings | Cohere Embed | Hugging Face Inference API (Embeddings), Mixedbread AI |
| tools | Arcade.dev | MCP Servers (Reference), Descope Agentic Identity Hub |
| observability | Braintrust | Langfuse, Laminar |
| guardrails | HiddenLayer AISec Platform 2.0 | Pillar Security, Lakera Guard / Lakera Red |
| serving | Baseten | vLLM, Fireworks AI |

## support-python-managed

`{"product":"support-agent","language":"python","hosting":"managed"}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | Portkey AI | OpenRouter, agentgateway |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| vectors | Milvus | Qdrant, Weaviate |
| embeddings | OpenAI Embeddings | Cohere Embed, Voyage AI (MongoDB) |
| tools | Composio | Arcade.dev, IBM ContextForge MCP Gateway |
| observability | LangSmith | Langfuse, Braintrust |
| guardrails | Lasso Security | Pillar Security, Promptfoo |

## support-hipaa

`{"product":"support-agent","compliance":["hipaa"]}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | TrueFoundry AI Gateway | Vercel AI Gateway, Portkey AI |
| memory | Mem0 | Zep & Graphiti, Supermemory |
| vectors | Weaviate | Elasticsearch, Qdrant |
| embeddings | Sentence Transformers | Voyage AI (MongoDB), Jina AI Embeddings |
| tools | Descope Agentic Identity Hub | Arcade.dev, IBM ContextForge MCP Gateway |
| observability | Braintrust | LangSmith, Confident AI / DeepEval |
| guardrails | Amazon Bedrock Guardrails | Pillar Security, Lakera Guard / Lakera Red |

## coding-default

`{"product":"coding-agent"}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | LiteLLM | OpenRouter, agentgateway |
| memory | claude-mem | codebase-memory-mcp (DeusData), mcp-memory-service (doobidoo) |
| sandbox | Daytona | e2b, Modal Sandboxes |
| tools | Composio | Arcade.dev, IBM ContextForge MCP Gateway |
| observability | Arize Phoenix | Braintrust, LangSmith |
| guardrails | Presidio | NVIDIA NeMo Guardrails, Google Cloud Model Armor |

## coding-ts-oss

`{"product":"coding-agent","language":"typescript","oss":true}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | LlamaIndex (framework), OpenAI Agents SDK |
| model | Mistral Large 2 / Mixtral family | Cohere Command R+ / Command A, DeepSeek R1 / V3 family |
| gateway | LiteLLM | agentgateway, Portkey AI |
| memory | claude-mem | Official MCP Memory server, Hindsight MCP |
| sandbox | e2b | Daytona, Modal Sandboxes |
| tools | Composio | Arcade.dev, MCP Servers (Reference) |
| observability | OpenInference | Langfuse, Laminar |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Arthur Engine |

## coding-self

`{"product":"coding-agent","hosting":"self"}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | Mistral Large 2 / Mixtral family | Cohere Command R+ / Command A, DeepSeek R1 / V3 family |
| gateway | LiteLLM | Portkey AI, Agent Router (formerly Envoy AI Gateway) |
| memory | claude-mem | codebase-memory-mcp (DeusData), mcp-memory-service (doobidoo) |
| sandbox | e2b | Modal Sandboxes, Coder.com |
| tools | Arcade.dev | IBM ContextForge MCP Gateway, MCP Servers (Reference) |
| observability | Braintrust | OpenLLMetry (Traceloop), OpenInference |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Guardrails AI |
| serving | vLLM | Baseten, SGLang |

## research-default

`{"product":"research-agent"}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | LiteLLM | OpenRouter, agentgateway |
| browser | Browser Use | Stagehand, Browserbase |
| sandbox | Daytona | e2b, Modal Sandboxes |
| vectors | Milvus | Weaviate, Elasticsearch |
| embeddings | OpenAI Embeddings | Cohere Embed, Sentence Transformers |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| observability | Arize Phoenix | OpenLLMetry (Traceloop), Braintrust |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Google Cloud Model Armor |

## research-python-oss

`{"product":"research-agent","language":"python","oss":true}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | Mistral Large 2 / Mixtral family | Cohere Command R+ / Command A, DeepSeek R1 / V3 family |
| gateway | LiteLLM | agentgateway, Portkey AI |
| browser | Stagehand | Browser Use, Skyvern |
| sandbox | e2b | Daytona, Modal Sandboxes |
| vectors | Milvus | Weaviate, Elasticsearch |
| embeddings | Sentence Transformers | Jina AI Embeddings, Nomic Embed |
| memory | Mem0 | Letta / MemGPT, Cognee |
| observability | OpenLLMetry (Traceloop) | OpenInference, Langfuse |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Guardrails AI |

## voice-default

`{"product":"voice-agent"}`

| Layer | Pick | Also accepted |
|---|---|---|
| voice | LiveKit Agents | Pipecat (Daily), Vapi |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| tools | Composio | Arcade.dev, IBM ContextForge MCP Gateway |
| observability | Braintrust | LangSmith, Arize Phoenix |
| guardrails | NVIDIA NeMo Guardrails | Presidio, PyRIT |

## voice-managed

`{"product":"voice-agent","hosting":"managed"}`

| Layer | Pick | Also accepted |
|---|---|---|
| voice | LiveKit Agents | Pipecat (Daily), Vapi |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| tools | Composio | Arcade.dev, IBM ContextForge MCP Gateway |
| observability | Braintrust | LangSmith, AgentOps |
| guardrails | HiddenLayer AISec Platform 2.0 | Lasso Security, Pillar Security |

## multi-default

`{"product":"multi-agent-workflow"}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | LiteLLM | OpenRouter, agentgateway |
| orchestration | n8n (AI agent flows) | CrewAI, LangGraph (orchestration) |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| tools | Composio | Arcade.dev, IBM ContextForge MCP Gateway |
| sandbox | Daytona | e2b, Modal Sandboxes |
| observability | Arize Phoenix | LangSmith, Braintrust |
| guardrails | Presidio | NVIDIA NeMo Guardrails, Google Cloud Model Armor |

## multi-ts

`{"product":"multi-agent-workflow","language":"typescript"}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | LlamaIndex (framework), OpenAI Agents SDK |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | LiteLLM | OpenRouter, agentgateway |
| orchestration | LangGraph (orchestration) | Inngest, Restate |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| tools | Composio | Arcade.dev, MCP Servers (Reference) |
| sandbox | Daytona | e2b, Modal Sandboxes |
| observability | Arize Phoenix | Braintrust, LangSmith |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Google Cloud Model Armor |

## multi-self-oss

`{"product":"multi-agent-workflow","hosting":"self","oss":true}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | Mistral Large 2 / Mixtral family | Cohere Command R+ / Command A, DeepSeek R1 / V3 family |
| gateway | LiteLLM | Portkey AI, Agent Router (formerly Envoy AI Gateway) |
| orchestration | CrewAI | LangGraph (orchestration), Restate |
| memory | Mem0 | Letta / MemGPT, Zep & Graphiti |
| tools | Arcade.dev | IBM ContextForge MCP Gateway, MCP Servers (Reference) |
| sandbox | e2b | Modal Sandboxes, Coder.com |
| observability | OpenLLMetry (Traceloop) | OpenInference, Langfuse |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Guardrails AI |
| serving | vLLM | SGLang, TensorRT-LLM |

## rag-default

`{"product":"rag-copilot"}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | LiteLLM | OpenRouter, agentgateway |
| vectors | Milvus | Weaviate, Elasticsearch |
| embeddings | OpenAI Embeddings | Cohere Embed, Sentence Transformers |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| observability | Arize Phoenix | OpenLLMetry (Traceloop), Braintrust |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Google Cloud Model Armor |

## rag-self

`{"product":"rag-copilot","hosting":"self"}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | Mistral Large 2 / Mixtral family | Cohere Command R+ / Command A, DeepSeek R1 / V3 family |
| gateway | LiteLLM | Portkey AI, Agent Router (formerly Envoy AI Gateway) |
| vectors | Milvus | Weaviate, Elasticsearch |
| embeddings | Cohere Embed | Sentence Transformers, Voyage AI (MongoDB) |
| memory | Mem0 | Letta / MemGPT, Cognee |
| observability | OpenLLMetry (Traceloop) | Langfuse, Braintrust |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Guardrails AI |
| serving | vLLM | Baseten, SGLang |

## rag-mcp

`{"product":"rag-copilot","mcp":true}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | LiteLLM | OpenRouter, agentgateway |
| vectors | Milvus | Weaviate, Elasticsearch |
| embeddings | OpenAI Embeddings | Cohere Embed, Sentence Transformers |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| observability | Arize Phoenix | OpenLLMetry (Traceloop), Braintrust |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Google Cloud Model Armor |

## rag-gdpr

`{"product":"rag-copilot","compliance":["gdpr"]}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Google Gemini 3 family, xAI Grok 4 |
| gateway | OpenRouter | TrueFoundry AI Gateway, Vercel AI Gateway |
| vectors | Qdrant | Supabase Vector, LanceDB |
| embeddings | OpenAI Embeddings | Hugging Face Inference API (Embeddings), Mixedbread AI |
| memory | Mem0 | n8n AI Agent Memory, Supermemory |
| observability | Braintrust | LangSmith, Pydantic Logfire |
| guardrails | Amazon Bedrock Guardrails | Lakera Guard / Lakera Red, HackerOne Hai |

## support-browser-sandbox

`{"product":"support-agent","add":["browser","sandbox"]}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | OpenAI GPT family (GPT-5 / GPT-4o / o3 / o4) | Anthropic Claude (foundation models), Google Gemini 3 family |
| gateway | LiteLLM | OpenRouter, agentgateway |
| memory | Mem0 | Zep & Graphiti, Letta / MemGPT |
| vectors | Milvus | Weaviate, Elasticsearch |
| embeddings | OpenAI Embeddings | Cohere Embed, Sentence Transformers |
| tools | Composio | Arcade.dev, IBM ContextForge MCP Gateway |
| observability | Arize Phoenix | OpenLLMetry (Traceloop), Braintrust |
| guardrails | NVIDIA NeMo Guardrails | Presidio, Google Cloud Model Armor |
| browser | Browser Use | Stagehand, Browserbase |
| sandbox | Daytona | e2b, Modal Sandboxes |

## coding-iso27001

`{"product":"coding-agent","compliance":["iso27001"]}`

| Layer | Pick | Also accepted |
|---|---|---|
| framework | LangChain (framework) | CrewAI, LlamaIndex (framework) |
| model | Anthropic Claude (foundation models) | Mistral Large 2 / Mixtral family, Jamba (AI21 Labs) |
| gateway | Portkey AI | Vercel AI Gateway, Cloudflare AI Gateway |
| memory | Lovable | Cursor Memories, claude-mem |
| sandbox | Anchor (Anchor Browser) | Workato AI (Workflow Bot Builder), Daytona |
| tools | Composio | Descope Agentic Identity Hub, Cloudflare MCP server portals |
| observability | LangSmith | Langfuse, Datadog Agent Observability (LLM Observability) |
| guardrails | Pillar Security | Promptfoo, Google Cloud Model Armor |
