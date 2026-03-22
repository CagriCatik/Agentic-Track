# Projects

This folder contains the actual corpus-driven RAG application used by this repository.

## What Is Here

- [main.py](C:/Users/mccat/Desktop/Agentic-Track/projects/main.py): local CLI entrypoint
- `rag_app/`: application package
  - [app.py](C:/Users/mccat/Desktop/Agentic-Track/projects/rag_app/app.py): CLI orchestration
  - [openai_compatible_api.py](C:/Users/mccat/Desktop/Agentic-Track/projects/rag_app/openai_compatible_api.py): OpenAI-compatible HTTP API
  - [vector_index.py](C:/Users/mccat/Desktop/Agentic-Track/projects/rag_app/vector_index.py): indexing and retriever construction
  - [retrieval.py](C:/Users/mccat/Desktop/Agentic-Track/projects/rag_app/retrieval.py): hybrid retrieval
  - [reranker.py](C:/Users/mccat/Desktop/Agentic-Track/projects/rag_app/reranker.py): feature + LLM reranking
  - [graph.py](C:/Users/mccat/Desktop/Agentic-Track/projects/rag_app/graph.py): grounded LangGraph answer flow
  - [loaders.py](C:/Users/mccat/Desktop/Agentic-Track/projects/rag_app/loaders.py): corpus loaders

## What The App Does

The app indexes a document corpus and serves grounded question answering over that corpus.

Current supported source types:

- `pdf`
- `txt`
- `md`
- `rst`
- `html`
- `json`
- `csv`
- `docx`
- `xlsx`

Core behavior:

- corpus-driven ingestion
- Chroma vector store
- SQLite FTS lexical catalog
- hybrid retrieval
- reranking
- support gating before answer generation
- OpenAI-compatible API for Open WebUI

## Prerequisites

From the repo root:

1. Install Python dependencies:

```bat
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. Ensure Ollama is running.

3. Ensure at least:

- one chat model is available
- one embedding model is available

Example:

```bat
ollama pull gpt-oss:20b
ollama pull nomic-embed-text
```

4. Put your corpus files into `corbus/`.

## Start Locally

Run from repo root.

### 1) Build or rebuild the index

```bat
.\.venv\Scripts\python.exe projects\main.py --index-only --reindex --corpus-dir corbus --vector-db-dir data/chroma
```

### 2) Start the local CLI chat

```bat
.\.venv\Scripts\python.exe projects\main.py --corpus-dir corbus --vector-db-dir data/chroma
```

Useful flags:

- `--top-k 3`
- `--retrieval-candidates 12`
- `--reranker-mode auto`
- `--reranker-mode feature`
- `--reranker-mode llm`
- `--reranker-model gpt-oss:120b-cloud`
- `--reranker-top-n 8`
- `--disable-reranker`
- `--index-on-start`
- `--reindex`

## Start The API Only

This exposes the app as an OpenAI-compatible API.

```bat
.\.venv\Scripts\python.exe -m uvicorn projects.rag_app.openai_compatible_api:app --host 0.0.0.0 --port 8001
```

Important endpoints:

- `GET http://localhost:8001/health`
- `GET http://localhost:8001/v1/models`
- `POST http://localhost:8001/v1/chat/completions`
- `GET http://localhost:8001/docs`
- `GET http://localhost:8001/redoc`
- `GET http://localhost:8001/openapi.json`

Default API key:

- `agentic-track-local`

Swagger / OpenAPI:

- Swagger UI is available at `http://localhost:8001/docs`
- ReDoc is available at `http://localhost:8001/redoc`
- OpenAPI JSON is available at `http://localhost:8001/openapi.json`
- For protected endpoints, click `Authorize` in Swagger UI and provide the Bearer token from `RAG_API_KEY`

Example request:

```powershell
$body = @{
  model = "agentic-rag"
  messages = @(
    @{ role = "user"; content = "What is ODX?" }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8001/v1/chat/completions" `
  -Headers @{ Authorization = "Bearer agentic-track-local" } `
  -ContentType "application/json" `
  -Body $body
```

## Start With Docker And Open WebUI

From repo root:

```bat
openwebui.bat start
```

This starts:

- `rag-api` on `http://localhost:8001`
- `open-webui` on `http://localhost:3000`

Useful commands:

```bat
openwebui.bat status
openwebui.bat logs-api
openwebui.bat logs-webui
openwebui.bat stop
```

## Important Configuration

### API / Docker env vars

- `RAG_API_MODEL_ID`
- `RAG_API_KEY`
- `RAG_CHAT_MODEL`
- `RAG_EMBED_MODEL`
- `RAG_CORPUS_DIR`
- `RAG_VECTOR_DB_DIR`
- `RAG_COLLECTION_NAME`
- `RAG_TOP_K`
- `RAG_RETRIEVAL_CANDIDATES`
- `RAG_RERANKER_ENABLED`
- `RAG_RERANKER_MODE`
- `RAG_RERANKER_MODEL`
- `RAG_RERANKER_TOP_N`
- `RAG_CHUNK_SIZE`
- `RAG_CHUNK_OVERLAP`
- `RAG_INDEX_ON_START`
- `RAG_REINDEX_ON_START`

### CLI env vars

The CLI resolves models from:

- `OLLAMA_CHAT_MODEL`
- `OLLAMA_EMBED_MODEL`
- `OLLAMA_BASE_URL`

And also reads the shared `RAG_*` indexing/retrieval settings.

## Reranker Modes

- `feature`: fast heuristic reranking only
- `llm`: feature reranking plus LLM rerank stage
- `auto`: use LLM reranking when a reranker model is available, otherwise fall back to feature-only

Operational guidance:

- use `feature` if you want lower latency
- use `llm` if you want stronger semantic disambiguation
- use `auto` as the default production mode

## Typical Workflow

1. Add or update files in `corbus/`
2. Reindex
3. Check `GET /health`
4. Test a few grounded queries
5. Run evaluation:

```bat
.\.venv\Scripts\python.exe evaluation\run_eval_pack.py --generate-pack --corpus-dir corbus --vector-db-dir data/chroma
.\.venv\Scripts\python.exe evaluation\score_eval_pack.py --pack evaluation\corpus_eval_pack.json --answers evaluation\eval_answers.jsonl --out evaluation\eval_scores.json
```

## Tests

Run all tests:

```bat
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The test suite includes:

- loader tests
- retrieval tests
- reranker tests
- graph support-gate tests
- API-level E2E tests

## Notes

- The app is corpus-driven, not domain hard-coded.
- The main production path is the API in [openai_compatible_api.py](C:/Users/mccat/Desktop/Agentic-Track/projects/rag_app/openai_compatible_api.py).
- `projects/main.py` is the fastest way to debug locally without Docker.
