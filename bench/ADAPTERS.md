# Memory-layer adapters

How each third-party adapter in `memory_bench/adapters/` talks to its system.
Every API call was checked against the project's current source or docs on
2026-10-23. The shell here has no network, so none of these adapters has been
run against a live service. They were syntax-checked, and their control flow
was exercised against stub SDKs. Shared helpers live in
`memory_bench/adapters/_util.py`, which is stdlib only. It provides
best-effort session-date parsing, id sanitising, polling, and a
private-event-loop runner for async SDKs.

Common conventions:
- Every namespace gets a fresh id suffixed with a per-run random tag, so
  `reset(ns)` always starts empty. Where a delete call exists, `reset` also
  runs it.
- Turns are rendered as `speaker: text`. On LoCoMo, `speakers[0]` maps to the
  `user` role and `speakers[1]` maps to `assistant` wherever a system needs
  roles.
- Session dates are parsed into UTC datetimes. Values without a timezone are
  treated as UTC. A date that cannot be parsed gives None and is simply not
  sent.

| module | class | requires | status |
|---|---|---|---|
| `mem0_adapter.py` | `Mem0` | `mem0ai>=2.2.1` | verified (one UNVERIFIED branch, see below) |
| `graphiti_adapter.py` | `Graphiti` | `graphiti-core>=0.30.0` | verified |
| `cognee_adapter.py` | `Cognee` | `cognee>=1.5.3` | verified |
| `zep_adapter.py` | `Zep` | `zep-cloud>=3.25.0 (4.x API used when installed)` | verified (v4 on GitHub main); PyPI release status of 4.x not confirmed |
| `supermemory_adapter.py` | `Supermemory` | `supermemory>=3.62.0,<5` | verified |
| `letta_adapter.py` | `Letta` | `letta-client>=1.12.1` | verified |
| `honcho_adapter.py` | `Honcho` | `honcho-ai>=2.5.1` | verified |

---

## mem0 (`Mem0`, name `mem0`)

- **Package:** `mem0ai` 2.2.1 (latest release, Sep 2026; checked against GitHub main).
- **Sources:**
  - https://github.com/mem0ai/mem0/blob/main/mem0/memory/main.py
  - https://github.com/mem0ai/mem0/blob/main/mem0/memory/utils.py
  - https://github.com/mem0ai/mem0/blob/main/mem0/configs/base.py
  - https://docs.mem0.ai/open-source/configuration
  - https://github.com/mem0ai/mem0/releases
- **Env:** `OPENAI_API_KEY`.
- **Infra:** none. It uses the default local Qdrant on disk and SQLite history at `~/.mem0/history.db` (or `$MEM0_DIR`). The on-disk Qdrant is shared, so do not run two mem0 benchmark processes at once on one machine.
- **Write:** one `Memory.add(messages, user_id=, metadata=)` call per session, with `infer=True` (the default). `add` is synchronous, so `flush()` does nothing.
  - Roles come from the turns. mem0's `parse_messages` reads only `role` and `content`, so LoCoMo speaker names are written into the content.
- **Session date:** OSS `add(timestamp=)` and `search(reference_date=)` are platform-only and raise ValueError. Instead, the date goes in `metadata["created_at"]` (ISO), which mem0 keeps as the memory's `created_at`. The raw date also goes in `metadata["session_date"]`.
- **Read:** `search(query, top_k=k, filters={"user_id": uid})`. In v2, a top-level `user_id` is rejected.
- **retrieve() returns:** `"[<session date>] <memory text>"`.
- **Non-default settings:** LLM `openai/<extraction_model>` and embedder `openai/<embed_model>`, as requested. Everything else is default.
- **UNVERIFIED:** this only applies when `embed_model` is not 1536-dimensional (for example `text-embedding-3-large`). In that case the adapter adds `embedder.config.embedding_dims` and `vector_store={"provider": "qdrant", "config": {"embedding_model_dims": N}}`. I did not re-check those key names against the 2.2.1 source. The default `text-embedding-3-small` never uses this branch.

## graphiti (`Graphiti`, name `graphiti`)

- **Package:** `graphiti-core` 0.30.x (v0.30.1 tag, Sep 2026).
- **Sources:**
  - https://github.com/getzep/graphiti/blob/main/graphiti_core/graphiti.py
  - https://github.com/getzep/graphiti/blob/main/graphiti_core/edges.py
  - https://github.com/getzep/graphiti/blob/main/graphiti_core/helpers.py
  - https://github.com/getzep/graphiti/blob/main/graphiti_core/llm_client/config.py
  - https://github.com/getzep/graphiti/blob/main/graphiti_core/llm_client/openai_client.py
  - https://github.com/getzep/graphiti/blob/main/graphiti_core/embedder/openai.py
  - https://github.com/getzep/graphiti/blob/main/graphiti_core/utils/maintenance/graph_data_operations.py
  - https://github.com/getzep/graphiti/blob/main/examples/quickstart/quickstart_neo4j.py
  - https://github.com/getzep/graphiti/releases
- **Env:** `OPENAI_API_KEY`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`.
- **Infra:** a Neo4j 5.26+ service. Since v0.30.0, queries target the `neo4j` database. `build_indices_and_constraints()` runs once in `setup()`.
- **Write:** one `add_episode(..., source=EpisodeType.message, reference_time=<session date or now>, group_id=<ns>)` call per session. The episode body is `speaker: text` lines. The call awaits extraction, so `flush()` does nothing.
- **Isolation and reset:** the group id is `ns-<runtag>`, sanitised to `^[a-zA-Z0-9_-]+$`. `reset` runs `clear_data(driver, group_ids=[gid])`.
- **Read:** `search(query, group_ids=[gid], num_results=k)`. Its default recipe is `EDGE_HYBRID_SEARCH_RRF`, with no cross-encoder.
- **retrieve() returns:** edge facts, formatted `"[<valid_at> - <invalid_at|present>] <fact>"`.
- **Non-default settings:** `OpenAIClient(config=LLMConfig(model=<extraction_model>))` and `OpenAIEmbedder(config=OpenAIEmbedderConfig(embedding_model=<embed_model>))`. `small_model`, the cross-encoder, embedding dimension and `SEMAPHORE_LIMIT` stay at their defaults.
- **Async:** a private event loop on a daemon thread keeps the Neo4j async driver on one loop.

## cognee (`Cognee`, name `cognee`)

- **Package:** `cognee` 1.5.3 (Aug 2026).
- **Sources:**
  - https://github.com/topoteretes/cognee (README)
  - https://github.com/topoteretes/cognee/blob/main/cognee/api/v1/remember/remember.py
  - https://github.com/topoteretes/cognee/blob/main/cognee/api/v1/recall/recall.py
  - https://github.com/topoteretes/cognee/blob/main/cognee/api/v1/search/search.py
  - https://docs.cognee.ai/python-api/recall.md
  - https://docs.cognee.ai/python-api/remember.md
  - https://docs.cognee.ai/python-api/forget
  - https://docs.cognee.ai/setup-configuration/overview.md
  - https://docs.cognee.ai/setup-configuration/embedding-providers.md
  - https://github.com/topoteretes/cognee/releases
- **Env:** `OPENAI_API_KEY`, copied into `LLM_API_KEY` if that is unset. A local `.env` file overrides `os.environ` for cognee, so the adapter also calls `cognee.config.set("llm_api_key", ...)`.
- **Infra:** none. The defaults are LanceDB, the Ladybug (Kuzu-compatible) graph store and SQLite, all stored on local disk.
- **Departure from the brief:** cognee 1.x documents `remember` (add + cognify + improve) and `recall` as its API. Its README no longer presents `add`, `cognify` and `search`, so the adapter uses the documented pair.
- **Write:** `ingest()` buffers one text document per session, headed `Conversation session <id> — date: <date>`. cognee has no per-item timestamp argument; its default pipeline extracts dates from the text as Timestamp nodes. `flush()` calls `await cognee.remember(docs, dataset_name=ds)` and waits for it to finish (`run_in_background=False`, `self_improvement=True`, both defaults).
- **Isolation and reset:** the dataset is `ns_<runtag>`. `reset` calls `forget(dataset=ds)` and ignores DatasetNotFoundError.
- **Read:** `recall(query, datasets=[ds], top_k=k, only_context=True)`, with auto-routing left at its default.
- **retrieve() returns:** retrieved context, not cognee's generated answer. With `only_context=True` cognee makes no completion call, and each item's `.text` is the context. For completion search types, that context is the full prompt cognee would have sent its LLM, including the question. `source == "system"` warm-up markers are dropped.
- **Non-default settings:** `llm_model=openai/<extraction_model>` (the default is `openai/gpt-5.6-luna`), `embedding_model=openai/<embed_model>` (the default is `openai/text-embedding-3-large`), and `embedding_dimensions` from the model.

## zep (`Zep`, name `zep`)

- **Package:** `zep-cloud` 4.0.1.
  - The help.getzep.com docs now describe the v4 API, which is UUID-addressed, and keep the v3 docs under `/v3/`.
  - GitHub main's `pyproject.toml` is 4.0.1, but the GitHub releases list stops at v3.25.0 (Jul 2026), and PyPI could not be reached to confirm that 4.x is published.
  - The adapter therefore also contains a v3.25.0 code path. It picks the API by feature detection: the presence of `graph.search_edges`.
- **Sources (v4):**
  - https://github.com/getzep/zep-python/blob/main/pyproject.toml
  - https://github.com/getzep/zep-python/blob/main/src/zep_cloud/user/client.py
  - https://github.com/getzep/zep-python/blob/main/src/zep_cloud/thread/client.py
  - https://github.com/getzep/zep-python/blob/main/src/zep_cloud/graph/client.py
  - https://github.com/getzep/zep-python/blob/main/src/zep_cloud/task/client.py
  - types (`add_message`, `add_messages_result`, `task`, `user`, `thread`, `edge`) under https://github.com/getzep/zep-python/blob/main/src/zep_cloud/types/
  - https://github.com/getzep/zep-python/blob/main/src/zep_cloud/core/pagination.py
  - https://help.getzep.com/adding-messages
- **Sources (v3):**
  - https://github.com/getzep/zep-python/blob/v3.25.0/reference.md
  - `types/{message,add_thread_messages_response,graph_search_results,entity_edge}.py` at the v3.25.0 tag
  - https://help.getzep.com/v3/check-data-ingestion-status
- **Env:** `ZEP_API_KEY`.
- **Infra:** Zep Cloud account.
- **Write (v4):** `user.create(user_id=<ns-runtag>)`, then for each session `thread.create(user_uuid=)` and `thread.add_messages(thread_uuid, messages=[AddMessage(role, name, content, reference_time)])`. Messages go in batches of 30, the documented per-call limit. Messages longer than 4,096 characters, the documented default limit, are split rather than truncated.
- **Write (v3):** `user.add(user_id=)`, `thread.create(thread_id=, user_id=)`, and `Message(..., created_at=)`.
- **Session date:** `reference_time` (v4) or `created_at` (v3), as RFC 3339 UTC.
- **flush():** polls `task.get(task_uuid)` for each returned task until its status is `succeeded`, `partial` or `failed`. The timeout defaults to 3600 s and is set with `flush_timeout`.
- **Read (v4):** `graph.search_edges(<user graph uuid>, query=, page_size=k).items` (first page only).
- **Read (v3):** `graph.search(user_id=, query=, scope="edges", limit=min(k, 50)).edges`.
- **retrieve() returns:** edge facts, formatted `"[<valid_at> - <invalid_at|present>] <fact>"`.
- **Non-default settings:** none. Models are server-side. `teardown()` deletes the run's users.

## supermemory (`Supermemory`, name `supermemory`)

- **Package:** `supermemory` 3.62.0 (2026-09-14), the latest stable 3.x release.
  - 5.0.0rc1 (2026-10-04) is a release candidate that replaces container tags with namespaces (`client.add(namespace, ...)`), so the requirement pins `<5`.
  - When 5.0 ships, the adapter will need a namespace variant.
- **Sources:**
  - Under https://github.com/supermemoryai/python-sdk/blob/v3.62.0/src/supermemory/types/: `client_add_params.py`, `add_response.py`, `search_memories_params.py`, `search_memories_response.py`, `document_get_response.py`, `document_delete_bulk_params.py`
  - https://github.com/supermemoryai/python-sdk/blob/main/api.md
  - https://github.com/supermemoryai/python-sdk/blob/main/CHANGELOG.md
- **Env:** `SUPERMEMORY_API_KEY`.
- **Infra:** Supermemory account.
- **Write:** one `client.add(content=, container_tag=<ns-runtag>, metadata={session_id, session_date}, document_date=<ISO>)` call per session. `document_date` is the documented field for backfilled content: memory extraction resolves relative dates against it.
- **flush():** polls `documents.get(id)` until `status` is `done` or `failed`. It also waits for `dreaming_status == "done"`, because the default `dreaming="dynamic"` mode forms memories later. That wait can be turned off with `wait_for_dreaming=False`. The timeout is set with `flush_timeout`.
- **Reset:** `documents.delete_bulk(container_tags=[tag])`.
- **Read:** `search.memories(q=, container_tag=, limit=k)`, using the default `searchMode="memories"` with rerank and query rewrite off.
- **retrieve() returns:** `result.memory`, or `.chunk` when there is no memory, prefixed with `[session_date]` when that metadata comes back on the result.
- **Non-default settings:** none.

## letta (`Letta`, name `letta`)

- **Package:** `letta-client` 1.12.1 (GitHub main).
- **Sources:**
  - https://github.com/letta-ai/letta-python/blob/main/README.md
  - https://github.com/letta-ai/letta-python/blob/main/api.md
  - https://github.com/letta-ai/letta-python/blob/main/src/letta_client/_client.py
  - https://github.com/letta-ai/letta-python/blob/main/src/letta_client/types/agent_create_params.py
  - Under `src/letta_client/types/agents/`: `passage_create_params.py`, `passage_create_response.py`, `passage_search_params.py`, `passage_search_response.py`
- **Env:** `LETTA_BASE_URL` (required). `LETTA_API_KEY` is optional and can be omitted for an unauthenticated self-hosted server.
- **Infra:** a Letta server, for example at `http://localhost:8283`, configured with an OpenAI provider so that the `openai/<embed_model>` handle resolves.
- **Write:** one agent per namespace, from `agents.create(name=, model="openai/<extraction_model>", embedding="openai/<embed_model>", tags=["memory-bench"])`. Each turn becomes one archival passage via `agents.passages.create(agent_id, text="speaker: text", created_at=<ISO session date>, tags=["session:<id>"])`. The server embeds the passage before returning, so `flush()` does nothing.
- **Read:** `agents.passages.search(agent_id, query=, top_k=k).results`.
- **retrieve() returns:** `"[<timestamp>] speaker: text"`, where the timestamp comes from Letta in the agent's timezone.
- **Scope note:** this measures Letta's archival store as a retriever. No messages are sent to the agent, so its LLM and its self-editing core memory are never used.
- **Non-default settings:** none beyond the model handles. `teardown()` deletes the run's agents.

## honcho (`Honcho`, name `honcho`)

- **Package:** `honcho-ai` 2.5.1 (GitHub main).
- **Sources:**
  - Under https://github.com/plastic-labs/honcho/blob/main/sdks/python/: `README.md`, `pyproject.toml`
  - Under https://github.com/plastic-labs/honcho/blob/main/sdks/python/src/honcho/: `client.py`, `peer.py`, `session.py`, `api_types.py`
  - https://github.com/plastic-labs/honcho/blob/main/src/schemas/api.py
  - https://github.com/plastic-labs/honcho/blob/main/src/config.py
- **Env:** `HONCHO_API_KEY` (managed service) or `HONCHO_BASE_URL` (self-hosted). The adapter checks that one of them is set and passes it explicitly. The SDK's own variable for the URL is `HONCHO_URL`.
- **Infra:** Honcho managed service, or a self-hosted Honcho server with its deriver worker running.
- **Isolation:** one workspace per namespace, `ns-<runtag>`. Ids must match `^[a-zA-Z0-9_-]+$`.
- **Write:** one Honcho session per dataset session, with one peer per speaker. Messages are created with `peer.message(content, metadata={session_date}, created_at=<datetime>)` and sent with `session.add_messages` in batches of at most 100 (the server limit). Messages longer than 25,000 characters (the server's default `MAX_MESSAGE_SIZE`) are split.
- **flush():** polls `honcho.queue_status()` until `pending_work_units` and `in_progress_work_units` are both 0.
- **Read:** `peer.representation(search_query=query, search_top_k=k)` for every peer in the namespace. This is Honcho's derived, query-conditioned memory. Honcho's own LLM answer, `peer.chat`, is not used.
- **retrieve() returns:** the representation text split into lines, each prefixed with `[<peer>]`. `k` limits the conclusions searched per peer, not the number of lines returned.
- **Non-default settings:** none. Models are Honcho server config. `teardown()` deletes the run's workspaces.

## Blocked during verification

Two cognee docs URLs, `https://docs.cognee.ai/core-concepts/main-operations/recall` and an earlier attempt at `https://docs.cognee.ai/python-api/remember.md`, were refused by the fetch permission check. The same content was then read from the `.md` and Python API pages listed above. PyPI JSON pages are blocked by robots, so versions come from GitHub `pyproject.toml` files, tags and release pages.
