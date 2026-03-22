"""OpenAI-compatible HTTP API backed by the local LangChain RAG flow."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .citations import build_cited_reference_lines, normalize_inline_citations
from .config import DEFAULT_SYSTEM_PROMPT
from .logging_utils import configure_logging
from .models import discover_ollama_models, model_exists, select_models
from .reranker import RERANKER_MODES
from .graph import build_graph
from .vector_index import (
    DEFAULT_COLLECTION,
    build_retriever,
    get_index_chunk_count,
    index_pdf_corpus,
    index_requires_rebuild,
)

configure_logging()
logger = logging.getLogger(__name__)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass
class RuntimeState:
    model_id: str
    chat_model: str | None
    embedding_model: str | None
    temperature: float
    top_k: int
    retrieval_candidates: int
    reranker_enabled: bool
    reranker_mode: str
    reranker_model: str | None
    reranker_top_n: int
    ollama_base_url: str | None
    retriever: Any | None
    chain: Any | None
    available_models: list[str]
    corpus_dir: str
    vector_db_dir: str
    collection_name: str
    index_stats: dict[str, int]
    last_request_trace: dict[str, Any] | None
    startup_error: str | None


class ChatMessage(BaseModel):
    role: str
    content: Any = ""


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    stream: bool = False


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    parts.append(text)
                continue
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type", "")).lower()
            if item_type == "text" and isinstance(item.get("text"), str):
                text = item["text"].strip()
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()

    return ""


def _messages_to_question(messages: list[ChatMessage]) -> str:
    if not messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    history_lines: list[str] = []
    last_user = ""
    for message in messages[-10:]:
        content = _extract_text(message.content)
        if not content:
            continue
        role = message.role.lower().strip()
        if role == "user":
            prefix = "User"
            last_user = content
        elif role == "assistant":
            prefix = "Assistant"
        elif role == "system":
            prefix = "System"
        else:
            prefix = role.title() if role else "Unknown"
        history_lines.append(f"{prefix}: {content}")

    if not history_lines:
        raise HTTPException(status_code=400, detail="no textual content in messages")

    if not last_user:
        # Fallback: use the last textual message regardless of role.
        last_user = history_lines[-1].split(":", 1)[-1].strip()

    history = "\n".join(history_lines[:-1]) if len(history_lines) > 1 else ""
    return history, last_user


def _chunk_text(text: str, chunk_size: int = 120) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    auth = authorization.strip()
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    return token or None


def _require_api_key(authorization: str | None) -> None:
    expected = os.getenv("RAG_API_KEY", "agentic-track-local").strip()
    if not expected:
        return
    token = _get_bearer_token(authorization)
    if token != expected:
        raise HTTPException(status_code=401, detail="invalid API key")


def _empty_runtime_state(
    *,
    model_id: str,
    temperature: float,
    top_k: int,
    retrieval_candidates: int,
    reranker_enabled: bool,
    reranker_mode: str,
    reranker_model: str | None,
    reranker_top_n: int,
    ollama_base_url: str | None,
    corpus_dir: str,
    vector_db_dir: str,
    collection_name: str,
    available_models: list[str],
    startup_error: str,
) -> RuntimeState:
    return RuntimeState(
        model_id=model_id,
        chat_model=None,
        embedding_model=None,
        temperature=temperature,
        top_k=top_k,
        retrieval_candidates=retrieval_candidates,
        reranker_enabled=reranker_enabled,
        reranker_mode=reranker_mode,
        reranker_model=reranker_model,
        reranker_top_n=reranker_top_n,
        ollama_base_url=ollama_base_url,
        retriever=None,
        chain=None,
        available_models=available_models,
        corpus_dir=corpus_dir,
        vector_db_dir=vector_db_dir,
        collection_name=collection_name,
        index_stats={},
        last_request_trace=None,
        startup_error=startup_error,
    )


def _build_runtime_state() -> RuntimeState:
    model_id = os.getenv("RAG_API_MODEL_ID", "agentic-rag").strip() or "agentic-rag"
    forced_chat = os.getenv("RAG_CHAT_MODEL")
    forced_embedding = os.getenv("RAG_EMBED_MODEL")
    temperature = _env_float("RAG_TEMPERATURE", 0.2)
    top_k = _env_int("RAG_TOP_K", 5)
    retrieval_candidates = max(top_k, _env_int("RAG_RETRIEVAL_CANDIDATES", max(top_k * 4, 12)))
    reranker_enabled = _env_bool("RAG_RERANKER_ENABLED", True)
    reranker_mode = (os.getenv("RAG_RERANKER_MODE", "auto").strip().lower() or "auto")
    forced_reranker_model = os.getenv("RAG_RERANKER_MODEL")
    reranker_top_n = min(
        retrieval_candidates,
        max(1, _env_int("RAG_RERANKER_TOP_N", min(retrieval_candidates, 8))),
    )
    chunk_size = _env_int("RAG_CHUNK_SIZE", 1200)
    chunk_overlap = _env_int("RAG_CHUNK_OVERLAP", 200)
    ollama_base_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("RAG_OLLAMA_BASE_URL")
    corpus_dir = os.getenv("RAG_CORPUS_DIR", "corbus")
    vector_db_dir = os.getenv("RAG_VECTOR_DB_DIR", "data/chroma")
    collection_name = os.getenv("RAG_COLLECTION_NAME", DEFAULT_COLLECTION)
    index_on_start = _env_bool("RAG_INDEX_ON_START", True)
    force_reindex = _env_bool("RAG_REINDEX_ON_START", False)
    rebuild_required = index_requires_rebuild(vector_db_dir)
    system_prompt = (
        os.getenv("RAG_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip()
        or DEFAULT_SYSTEM_PROMPT
    )
    logger.info(
        "Building API runtime: model_id=%s corpus_dir=%s vector_db_dir=%s collection=%s index_on_start=%s force_reindex=%s rebuild_required=%s",
        model_id,
        corpus_dir,
        vector_db_dir,
        collection_name,
        index_on_start,
        force_reindex,
        rebuild_required,
    )
    if reranker_mode not in RERANKER_MODES:
        logger.error("Unsupported reranker mode configured: %s", reranker_mode)
        return _empty_runtime_state(
            model_id=model_id,
            temperature=temperature,
            top_k=top_k,
            retrieval_candidates=retrieval_candidates,
            reranker_enabled=reranker_enabled,
            reranker_mode=reranker_mode,
            reranker_model=(forced_reranker_model.strip() or None) if isinstance(forced_reranker_model, str) else None,
            reranker_top_n=reranker_top_n,
            ollama_base_url=ollama_base_url,
            corpus_dir=corpus_dir,
            vector_db_dir=vector_db_dir,
            collection_name=collection_name,
            available_models=[],
            startup_error=f"Unsupported reranker mode: {reranker_mode!r}",
        )

    available_models = discover_ollama_models(base_url=ollama_base_url)
    if not available_models:
        logger.error("No Ollama models discovered while building API runtime")
        return _empty_runtime_state(
            model_id=model_id,
            temperature=temperature,
            top_k=top_k,
            retrieval_candidates=retrieval_candidates,
            reranker_enabled=reranker_enabled,
            reranker_mode=reranker_mode,
            reranker_model=(forced_reranker_model.strip() or None) if isinstance(forced_reranker_model, str) else None,
            reranker_top_n=reranker_top_n,
            ollama_base_url=ollama_base_url,
            corpus_dir=corpus_dir,
            vector_db_dir=vector_db_dir,
            collection_name=collection_name,
            available_models=[],
            startup_error=(
                "No Ollama models discovered. Ensure Ollama is running and reachable."
            ),
        )

    chat_model, embedding_model = select_models(
        available_models,
        forced_chat=forced_chat,
        forced_embedding=forced_embedding,
    )
    resolved_reranker_model = (
        forced_reranker_model.strip()
        if isinstance(forced_reranker_model, str) and forced_reranker_model.strip()
        else chat_model
    )
    if not chat_model:
        logger.error("Could not infer chat model from discovered models")
        return _empty_runtime_state(
            model_id=model_id,
            temperature=temperature,
            top_k=top_k,
            retrieval_candidates=retrieval_candidates,
            reranker_enabled=reranker_enabled,
            reranker_mode=reranker_mode,
            reranker_model=resolved_reranker_model,
            reranker_top_n=reranker_top_n,
            ollama_base_url=ollama_base_url,
            available_models=available_models,
            corpus_dir=corpus_dir,
            vector_db_dir=vector_db_dir,
            collection_name=collection_name,
            startup_error="Could not infer a chat model from discovered models.",
        )
    if not embedding_model:
        logger.error("Could not infer embedding model from discovered models")
        return _empty_runtime_state(
            model_id=model_id,
            temperature=temperature,
            top_k=top_k,
            retrieval_candidates=retrieval_candidates,
            reranker_enabled=reranker_enabled,
            reranker_mode=reranker_mode,
            reranker_model=resolved_reranker_model,
            reranker_top_n=reranker_top_n,
            ollama_base_url=ollama_base_url,
            available_models=available_models,
            corpus_dir=corpus_dir,
            vector_db_dir=vector_db_dir,
            collection_name=collection_name,
            startup_error="Could not infer an embedding model from discovered models.",
        )
    if (
        reranker_enabled
        and reranker_mode == "llm"
        and resolved_reranker_model
        and not model_exists(resolved_reranker_model, available_models)
    ):
        logger.error(
            "Configured reranker model was not discovered: %s",
            resolved_reranker_model,
        )
        return RuntimeState(
            model_id=model_id,
            chat_model=chat_model,
            embedding_model=embedding_model,
            temperature=temperature,
            top_k=top_k,
            retrieval_candidates=retrieval_candidates,
            reranker_enabled=reranker_enabled,
            reranker_mode=reranker_mode,
            reranker_model=resolved_reranker_model,
            reranker_top_n=reranker_top_n,
            ollama_base_url=ollama_base_url,
            retriever=None,
            chain=None,
            available_models=available_models,
            corpus_dir=corpus_dir,
            vector_db_dir=vector_db_dir,
            collection_name=collection_name,
            index_stats={},
            last_request_trace=None,
            startup_error=f"Configured reranker model '{resolved_reranker_model}' was not discovered.",
        )
    if (
        reranker_enabled
        and reranker_mode == "auto"
        and resolved_reranker_model
        and not model_exists(resolved_reranker_model, available_models)
    ):
        logger.warning(
            "Auto reranker model not discovered, falling back to feature-only reranking: %s",
            resolved_reranker_model,
        )
        resolved_reranker_model = None

    index_stats: dict[str, int] = {}
    if index_on_start or force_reindex or rebuild_required:
        logger.info(
            "Running startup indexing: corpus_dir=%s force_reindex=%s",
            corpus_dir,
            (force_reindex or rebuild_required),
        )
        stats = index_pdf_corpus(
            embedding_model=embedding_model,
            corpus_dir=corpus_dir,
            vector_db_dir=vector_db_dir,
            collection_name=collection_name,
            ollama_base_url=ollama_base_url,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            force_reindex=(force_reindex or rebuild_required),
        )
        index_stats = {
            "scanned_files": stats.scanned_files,
            "indexed_files": stats.indexed_files,
            "skipped_files": stats.skipped_files,
            "removed_files": stats.removed_files,
            "added_chunks": stats.added_chunks,
            "deleted_chunks": stats.deleted_chunks,
            "failed_files": stats.failed_files,
            "total_chunks_in_index": stats.total_chunks_in_index,
            "rebuild_required": int(rebuild_required),
        }
        logger.info(
            "Startup indexing complete: scanned=%d indexed=%d skipped=%d removed=%d added_chunks=%d deleted_chunks=%d failed=%d total_chunks=%d",
            stats.scanned_files,
            stats.indexed_files,
            stats.skipped_files,
            stats.removed_files,
            stats.added_chunks,
            stats.deleted_chunks,
            stats.failed_files,
            stats.total_chunks_in_index,
        )

    if not index_stats:
        index_stats = {
            "total_chunks_in_index": get_index_chunk_count(
                embedding_model=embedding_model,
                vector_db_dir=vector_db_dir,
                collection_name=collection_name,
                ollama_base_url=ollama_base_url,
            )
        }
        logger.info(
            "Startup indexing skipped, existing chunk count=%d",
            index_stats["total_chunks_in_index"],
        )

    retriever = build_retriever(
        embedding_model=embedding_model,
        vector_db_dir=vector_db_dir,
        collection_name=collection_name,
        ollama_base_url=ollama_base_url,
        top_k=top_k,
        retrieval_candidates=retrieval_candidates,
        reranker_enabled=reranker_enabled,
        reranker_mode=reranker_mode,
        reranker_model=resolved_reranker_model,
        reranker_top_n=reranker_top_n,
    )

    chain = build_graph(
        chat_model=chat_model,
        temperature=temperature,
        system_prompt=system_prompt,
        retriever=retriever,
        ollama_base_url=ollama_base_url,
    )

    logger.info(
        "API runtime ready: chat_model=%s embedding_model=%s reranker_enabled=%s reranker_mode=%s reranker_model=%s top_k=%d retrieval_candidates=%d",
        chat_model,
        embedding_model,
        reranker_enabled,
        reranker_mode,
        resolved_reranker_model or "feature-only",
        top_k,
        retrieval_candidates,
    )

    return RuntimeState(
        model_id=model_id,
        chat_model=chat_model,
        embedding_model=embedding_model,
        temperature=temperature,
        top_k=top_k,
        retrieval_candidates=retrieval_candidates,
        reranker_enabled=reranker_enabled,
        reranker_mode=reranker_mode,
        reranker_model=resolved_reranker_model,
        reranker_top_n=reranker_top_n,
        ollama_base_url=ollama_base_url,
        retriever=retriever,
        chain=chain,
        available_models=available_models,
        corpus_dir=corpus_dir,
        vector_db_dir=vector_db_dir,
        collection_name=collection_name,
        index_stats=index_stats,
        last_request_trace=None,
        startup_error=None,
    )

APP_STATE = (
    _empty_runtime_state(
        model_id=os.getenv("RAG_API_MODEL_ID", "agentic-rag").strip() or "agentic-rag",
        temperature=_env_float("RAG_TEMPERATURE", 0.2),
        top_k=_env_int("RAG_TOP_K", 5),
        retrieval_candidates=max(
            _env_int("RAG_TOP_K", 5),
            _env_int("RAG_RETRIEVAL_CANDIDATES", max(_env_int("RAG_TOP_K", 5) * 4, 12)),
        ),
        reranker_enabled=_env_bool("RAG_RERANKER_ENABLED", True),
        reranker_mode=(os.getenv("RAG_RERANKER_MODE", "auto").strip().lower() or "auto"),
        reranker_model=(os.getenv("RAG_RERANKER_MODEL", "").strip() or None),
        reranker_top_n=max(1, _env_int("RAG_RERANKER_TOP_N", 8)),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL") or os.getenv("RAG_OLLAMA_BASE_URL"),
        corpus_dir=os.getenv("RAG_CORPUS_DIR", "corbus"),
        vector_db_dir=os.getenv("RAG_VECTOR_DB_DIR", "data/chroma"),
        collection_name=os.getenv("RAG_COLLECTION_NAME", DEFAULT_COLLECTION),
        available_models=[],
        startup_error="startup build skipped",
    )
    if _env_bool("RAG_SKIP_STARTUP_BUILD", False)
    else _build_runtime_state()
)
APP_TITLE = "Agentic Track RAG OpenAI Bridge"
APP_DESCRIPTION = (
    "OpenAI-compatible RAG API over the local corpus. "
    "Use Bearer auth with the configured `RAG_API_KEY` for `/v1/models` and `/v1/chat/completions`."
)
app = FastAPI(
    title=APP_TITLE,
    version="0.1.0",
    description=APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


def _custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=APP_TITLE,
        version="0.1.0",
        description=APP_DESCRIPTION,
        routes=app.routes,
    )
    components = schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "API key",
        "description": "Use the RAG API key, for example `agentic-track-local` in local development.",
    }

    protected_paths = ("/v1/models", "/models", "/v1/chat/completions", "/chat/completions")
    for path, methods in schema.get("paths", {}).items():
        if path not in protected_paths:
            continue
        for operation in methods.values():
            operation.setdefault("security", []).append({"BearerAuth": []})

    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi


def _ensure_runtime_ready() -> RuntimeState:
    global APP_STATE
    if APP_STATE.startup_error:
        logger.warning("Runtime not ready, attempting rebuild: error=%s", APP_STATE.startup_error)
        refreshed = _build_runtime_state()
        if refreshed.startup_error is None:
            APP_STATE = refreshed
            logger.info("Runtime rebuild succeeded")

    if APP_STATE.startup_error or APP_STATE.chain is None:
        detail = APP_STATE.startup_error or "RAG runtime is unavailable"
        logger.error("Runtime unavailable: %s", detail)
        raise HTTPException(status_code=503, detail=detail)
    return APP_STATE


def _build_model_response() -> dict[str, Any]:
    created = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": APP_STATE.model_id,
                "object": "model",
                "created": created,
                "owned_by": "agentic-track",
            }
        ],
    }


def _summarize_retrieval(docs: Any) -> dict[str, Any]:
    if not isinstance(docs, list):
        if docs is None:
            docs = []
        else:
            docs = list(docs)

    sources: list[str] = []
    total_chars = 0
    for doc in docs:
        content = getattr(doc, "page_content", "")
        if isinstance(content, str):
            total_chars += len(content)
        metadata = getattr(doc, "metadata", None)
        if not isinstance(metadata, dict):
            continue
        source = (
            metadata.get("source_name")
            or metadata.get("source_path")
            or metadata.get("source")
        )
        if isinstance(source, str) and source and source not in sources:
            sources.append(source)

    return {
        "retrieved_docs": len(docs),
        "retrieved_chars": total_chars,
        "retrieved_sources": sources[:8],
    }


async def _invoke_chain(vector_query: str, *, history: str, request_id: str) -> str:
    state = _ensure_runtime_ready()
    
    tags = ["agentic-track", "rag", "openai-compatible"]
    if state.chat_model:
        tags.append(f"chat:{state.chat_model}")
    if state.embedding_model:
        tags.append(f"embed:{state.embedding_model}")

    trace_metadata: dict[str, Any] = {
        "request_id": request_id,
        "api_model_id": state.model_id,
        "chat_model": state.chat_model or "",
        "embedding_model": state.embedding_model or "",
        "collection_name": state.collection_name,
        "top_k": state.top_k,
        "retrieval_candidates": state.retrieval_candidates,
        "reranker_enabled": state.reranker_enabled,
        "reranker_mode": state.reranker_mode,
        "reranker_model": state.reranker_model or "",
        "reranker_top_n": state.reranker_top_n,
        "temperature": state.temperature,
        "retriever_type": "hybrid",
    }
    logger.info(
        "Invoking RAG chain: request_id=%s query=%r history_chars=%d",
        request_id,
        vector_query[:200],
        len(history),
    )

    try:
        final_state = await asyncio.to_thread(
            state.chain.invoke,
            {"question": vector_query, "history": history, "revision_count": 0},
            {
                "run_name": "rag_chat_completion",
                "tags": tags,
                "metadata": trace_metadata,
            },
        )
        answer = final_state.get("generation", "")
        if not isinstance(answer, str):
            answer = str(answer)
        answer, cited_indices = normalize_inline_citations(answer)

        docs = final_state.get("docs", [])
        support_status = str(final_state.get("support_status", "unknown"))
        support_confidence = float(final_state.get("support_confidence", 0.0))
        retrieval_stats = _summarize_retrieval(docs)
        trace_metadata.update(retrieval_stats)
        trace_metadata["support_status"] = support_status
        trace_metadata["support_confidence"] = support_confidence
        trace_metadata["cited_indices"] = cited_indices
        cited_references = build_cited_reference_lines(docs, cited_indices)
        if support_status != "unsupported" and cited_references:
            answer = answer.rstrip()
            answer += "\n\nSources:\n"
            for line in cited_references:
                answer += f"- {line}\n"
        logger.info(
            "RAG chain completed: request_id=%s support_status=%s support_confidence=%.2f retrieved_docs=%s retrieved_sources=%s cited_indices=%s",
            request_id,
            support_status,
            support_confidence,
            retrieval_stats.get("retrieved_docs", 0),
            retrieval_stats.get("retrieved_sources", []),
            cited_indices,
        )
    except Exception as exc:  # pragma: no cover
        answer = f"Error generating answer: {exc}"
        retrieval_stats = {}
        logger.exception("RAG chain failed: request_id=%s", request_id)

    state.last_request_trace = {
        "request_id": request_id,
        "timestamp": int(time.time()),
        **trace_metadata,
        "tags": tags,
    }
    return answer


@app.get("/health")
def health() -> Any:
    langsmith_tracing = os.getenv("LANGSMITH_TRACING", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    payload = {
        "status": "ok" if APP_STATE.startup_error is None else "error",
        "model_id": APP_STATE.model_id,
        "chat_model": APP_STATE.chat_model,
        "embedding_model": APP_STATE.embedding_model,
        "temperature": APP_STATE.temperature,
        "top_k": APP_STATE.top_k,
        "retrieval_candidates": APP_STATE.retrieval_candidates,
        "reranker_enabled": APP_STATE.reranker_enabled,
        "reranker_mode": APP_STATE.reranker_mode,
        "reranker_model": APP_STATE.reranker_model,
        "reranker_top_n": APP_STATE.reranker_top_n,
        "startup_error": APP_STATE.startup_error,
        "available_models": APP_STATE.available_models,
        "corpus_dir": APP_STATE.corpus_dir,
        "vector_db_dir": APP_STATE.vector_db_dir,
        "collection_name": APP_STATE.collection_name,
        "index_stats": APP_STATE.index_stats,
        "last_request_trace": APP_STATE.last_request_trace,
        "langsmith_tracing": langsmith_tracing,
        "langsmith_project": os.getenv("LANGSMITH_PROJECT", "").strip(),
    }
    if APP_STATE.startup_error:
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.get("/v1/models")
@app.get("/models")
def list_models(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_api_key(authorization)
    return _build_model_response()


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
):
    _require_api_key(authorization)
    _ensure_runtime_ready()

    if request.model and request.model != APP_STATE.model_id:
        raise HTTPException(
            status_code=400,
            detail=f"unknown model '{request.model}', expected '{APP_STATE.model_id}'",
        )

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    model = APP_STATE.model_id
    history, vector_query = _messages_to_question(request.messages)
    logger.info(
        "Received chat completion request: request_id=%s model=%s stream=%s messages=%d",
        completion_id,
        model,
        request.stream,
        len(request.messages),
    )
    
    answer = await _invoke_chain(vector_query, history=history, request_id=completion_id)

    if request.stream:
        async def gen():
            yield _sse(
                {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant"},
                            "finish_reason": None,
                        }
                    ],
                }
            )

            for chunk in _chunk_text(answer):
                yield _sse(
                    {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": chunk},
                                "finish_reason": None,
                            }
                        ],
                    }
                )
                await asyncio.sleep(0)

            yield _sse(
                {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
            )
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    payload = {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
    return JSONResponse(payload)
