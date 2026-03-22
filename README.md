# Agentic Track

KnowledgeBase-Hub for LangChain, Agents, RAG, LangGraph, and MCP workflows.

## What Starts Here

This repo starts a corpus-driven RAG app behind Open WebUI.

- `open-webui` is the browser UI
- `rag-api` is the OpenAI-compatible backend
- `agentic-rag` is the model id exposed to Open WebUI

Important:

- `agentic-rag` is not the actual Ollama model name
- the real runtime models are controlled through `.env.openwebui`
- the active runtime can always be checked at `http://localhost:8001/health`
- API documentation is available at `http://localhost:8001/docs`
- ReDoc is available at `http://localhost:8001/redoc`
- raw OpenAPI schema is available at `http://localhost:8001/openapi.json`

Main settings:

- `RAG_CHAT_MODEL`: underlying chat model
- `RAG_EMBED_MODEL`: embedding model
- `RAG_RERANKER_MODEL`: optional reranker LLM
- `RAG_API_MODEL_ID`: name shown in Open WebUI, default `agentic-rag`

If `RAG_CHAT_MODEL` and `RAG_EMBED_MODEL` are empty, the app auto-selects from installed Ollama models.

For the application internals and local CLI/API usage, see [projects/README.md](C:/Users/mccat/Desktop/Agentic-Track/projects/README.md).

## Open WebUI (Browser Chat)

This repo includes Open WebUI + a local RAG API bridge:

- `open-webui` provides the browser chat UI.
- `rag-api` exposes your LangChain RAG flow as an OpenAI-compatible API.
- `rag-api` calls local Ollama models.

### 1) First-time setup

1. Copy `.env.openwebui.example` to `.env.openwebui` (or run `openwebui.bat start` once and it auto-creates it).
2. Ensure Ollama is running on your machine (`http://localhost:11434` by default).
3. Put your source documents into the `corbus/` folder (mounted into the RAG API container). Supported formats include `pdf`, `txt`, `md`, `rst`, `html`, `json`, `csv`, `docx`, and `xlsx`.

### 2) Start Open WebUI

```bat
openwebui.bat start
```

Then open `http://localhost:3000`.
In the model picker, choose `agentic-rag` (default).

### Change The Actual Model

Edit [`.env.openwebui`](C:/Users/mccat/Desktop/Agentic-Track/.env.openwebui):

```env
RAG_CHAT_MODEL=gpt-oss:120b-cloud
RAG_EMBED_MODEL=nomic-embed-text:latest
RAG_RERANKER_MODEL=gpt-oss:120b-cloud
```

Then restart:

```bat
openwebui.bat restart
```

To verify what is active:

```bat
curl http://localhost:8001/health
```

### API Documentation

The RAG API exposes FastAPI Swagger / OpenAPI docs:

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`
- OpenAPI JSON: `http://localhost:8001/openapi.json`

Protected endpoints use Bearer auth. In Swagger UI, click `Authorize` and enter:

```text
agentic-track-local
```

or whatever you configured as `RAG_API_KEY` in `.env.openwebui`.

### 3) Useful commands

```bat
openwebui.bat status
openwebui.bat logs-api
openwebui.bat logs-webui
openwebui.bat stop
```

### Notes

- Docker + Docker Compose are required.
- Data is stored in Docker volume `open-webui-data`.
- Vector index is persisted under `data/chroma/` on the host.
- Open WebUI is wired to `rag-api` through `OPENAI_API_BASE_URL(S)` in `.env.openwebui`.
- LangSmith tracing can be enabled with `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT=...`, and `LANGSMITH_API_KEY=...` in `.env.openwebui`.
- `rag-api` model id is `agentic-rag` (configurable with `RAG_API_MODEL_ID`).
- Underlying Ollama chat/embed models auto-select by heuristic (or pin with `RAG_CHAT_MODEL` and `RAG_EMBED_MODEL`).
- Corpus path, reranking, and indexing behavior are controlled with `RAG_CORPUS_DIR`, `RAG_RETRIEVAL_CANDIDATES`, `RAG_RERANKER_ENABLED`, `RAG_RERANKER_MODE`, `RAG_RERANKER_MODEL`, `RAG_RERANKER_TOP_N`, `RAG_INDEX_ON_START`, and `RAG_REINDEX_ON_START`.
- Recommended for large corpora: keep `RAG_INDEX_ON_START=False` and run indexing explicitly.
- First startup can take 1-2 minutes (image/model initialization). The launcher now waits for readiness.
- If you see `Access is denied` from Docker, run terminal as Administrator or add your user to `docker-users`, then sign out/in.

## Local Indexing CLI

To rebuild the index locally without Docker:

```bat
python projects\main.py --index-only --reindex --corpus-dir corbus --vector-db-dir data/chroma
```

## Evaluation

Use the corpus-agnostic evaluation flow:

```bat
python evaluation\run_eval_pack.py --generate-pack --corpus-dir corbus --vector-db-dir data/chroma
python evaluation\score_eval_pack.py --pack evaluation\corpus_eval_pack.json --answers evaluation\eval_answers.jsonl --out evaluation\eval_scores.json
```

## CI

HTTP-level integration tests now run in CI through `.github/workflows/ci.yml`. The suite exercises `/v1/models` and `/v1/chat/completions` with a deterministic in-process runtime so the API surface is covered without requiring a live Ollama daemon during CI.
