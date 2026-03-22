"""Configuration and CLI parsing for the local RAG app."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from .reranker import RERANKER_MODES

DEFAULT_SYSTEM_PROMPT = (
    "You are a retrieval-grounded assistant for an arbitrary indexed document corpus. "
    "Answer only with information supported by the retrieved context. "
    "If the evidence is incomplete, state what is supported and what is missing. "
    "Prefer concise answers for narrow questions and structured answers for broad questions. "
    "Cite source block numbers like [1] and [2] when you make a claim. "
    "Match the user's language unless the user explicitly asks for another one. "
    "Do not invent facts, metadata, or sources."
)

def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float, got: {value!r}") from exc


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got: {value!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean, got: {value!r}")


@dataclass(frozen=True)
class AppConfig:
    chat_model: str | None
    embedding_model: str | None
    temperature: float
    top_k: int
    retrieval_candidates: int
    reranker_enabled: bool
    reranker_mode: str
    reranker_model: str | None
    reranker_top_n: int
    system_prompt: str
    ollama_base_url: str | None
    corpus_dir: str
    vector_db_dir: str
    collection_name: str
    chunk_size: int
    chunk_overlap: int
    index_only: bool
    reindex: bool
    index_on_start: bool
    list_models_only: bool

    @classmethod
    def from_sources(cls, args: argparse.Namespace) -> "AppConfig":
        chat_model = args.chat_model or os.getenv("OLLAMA_CHAT_MODEL")
        embedding_model = args.embedding_model or os.getenv("OLLAMA_EMBED_MODEL")
        ollama_base_url = (
            args.ollama_base_url
            or os.getenv("OLLAMA_BASE_URL")
            or os.getenv("RAG_OLLAMA_BASE_URL")
        )

        temperature = (
            args.temperature
            if args.temperature is not None
            else _env_float("RAG_TEMPERATURE", 0.2)
        )
        top_k = args.top_k if args.top_k is not None else _env_int("RAG_TOP_K", 3)
        retrieval_candidates = (
            args.retrieval_candidates
            if args.retrieval_candidates is not None
            else _env_int("RAG_RETRIEVAL_CANDIDATES", max(top_k * 4, 12))
        )
        reranker_mode = (
            args.reranker_mode
            if args.reranker_mode is not None
            else os.getenv("RAG_RERANKER_MODE", "auto")
        ).strip().lower()
        reranker_model = (
            args.reranker_model
            if args.reranker_model is not None
            else os.getenv("RAG_RERANKER_MODEL")
        )
        reranker_top_n = (
            args.reranker_top_n
            if args.reranker_top_n is not None
            else _env_int("RAG_RERANKER_TOP_N", min(retrieval_candidates, 8))
        )
        chunk_size = (
            args.chunk_size
            if args.chunk_size is not None
            else _env_int("RAG_CHUNK_SIZE", 1200)
        )
        chunk_overlap = (
            args.chunk_overlap
            if args.chunk_overlap is not None
            else _env_int("RAG_CHUNK_OVERLAP", 200)
        )
        corpus_dir = args.corpus_dir or os.getenv("RAG_CORPUS_DIR", "corbus")
        vector_db_dir = args.vector_db_dir or os.getenv(
            "RAG_VECTOR_DB_DIR", "data/chroma"
        )
        collection_name = args.collection_name or os.getenv(
            "RAG_COLLECTION_NAME", "agentic_rag_docs"
        )
        index_on_start = (
            bool(args.index_on_start)
            if args.index_on_start
            else _env_bool("RAG_INDEX_ON_START", True)
        )
        reindex = bool(args.reindex) or _env_bool("RAG_REINDEX_ON_START", False)
        reranker_enabled = (
            not bool(args.disable_reranker)
            if args.disable_reranker
            else _env_bool("RAG_RERANKER_ENABLED", True)
        )
        system_prompt = os.getenv("RAG_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip()

        if temperature < 0:
            raise ValueError("temperature must be >= 0")
        if top_k < 1:
            raise ValueError("top-k must be >= 1")
        if retrieval_candidates < top_k:
            raise ValueError("retrieval-candidates must be >= top-k")
        if reranker_mode not in RERANKER_MODES:
            raise ValueError(
                f"reranker-mode must be one of {sorted(RERANKER_MODES)}, got: {reranker_mode!r}"
            )
        if reranker_top_n < 1:
            raise ValueError("reranker-top-n must be >= 1")
        if reranker_top_n > retrieval_candidates:
            raise ValueError("reranker-top-n must be <= retrieval-candidates")
        if chunk_size < 100:
            raise ValueError("chunk-size must be >= 100")
        if chunk_overlap < 0:
            raise ValueError("chunk-overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk-overlap must be smaller than chunk-size")
        if not system_prompt:
            raise ValueError("system prompt must not be empty")
        if not corpus_dir:
            raise ValueError("corpus-dir must not be empty")
        if not vector_db_dir:
            raise ValueError("vector-db-dir must not be empty")
        if not collection_name:
            raise ValueError("collection-name must not be empty")

        return cls(
            chat_model=chat_model,
            embedding_model=embedding_model,
            temperature=temperature,
            top_k=top_k,
            retrieval_candidates=retrieval_candidates,
            reranker_enabled=reranker_enabled,
            reranker_mode=reranker_mode,
            reranker_model=(reranker_model.strip() or None) if isinstance(reranker_model, str) else None,
            reranker_top_n=reranker_top_n,
            system_prompt=system_prompt,
            ollama_base_url=ollama_base_url,
            corpus_dir=corpus_dir,
            vector_db_dir=vector_db_dir,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            index_only=bool(args.index_only),
            reindex=reindex,
            index_on_start=index_on_start,
            list_models_only=bool(args.list_models),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local Ollama + LangChain corpus-driven RAG CLI",
    )
    parser.add_argument(
        "--chat-model",
        help="Force a specific chat model name",
    )
    parser.add_argument(
        "--embedding-model",
        help="Force a specific embedding model name",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature (default: env RAG_TEMPERATURE or 0.2)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Retrieved chunks count (default: env RAG_TOP_K or 3)",
    )
    parser.add_argument(
        "--retrieval-candidates",
        type=int,
        default=None,
        help="Candidate chunks retrieved before reranking (default: env RAG_RETRIEVAL_CANDIDATES or top-k*4)",
    )
    parser.add_argument(
        "--disable-reranker",
        action="store_true",
        help="Disable the retrieval reranker layer",
    )
    parser.add_argument(
        "--reranker-mode",
        choices=sorted(RERANKER_MODES),
        default=None,
        help="Reranker backend: feature, llm, or auto (default: env RAG_RERANKER_MODE or auto)",
    )
    parser.add_argument(
        "--reranker-model",
        default=None,
        help="Optional Ollama model for LLM reranking (default: env RAG_RERANKER_MODEL or chat model)",
    )
    parser.add_argument(
        "--reranker-top-n",
        type=int,
        default=None,
        help="How many candidates are passed into the LLM rerank stage (default: env RAG_RERANKER_TOP_N or 8)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List discovered Ollama models and exit",
    )
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="Build/update vector index and exit",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Force reindex all supported source documents",
    )
    parser.add_argument(
        "--index-on-start",
        action="store_true",
        help="Always run indexing before chat starts",
    )
    parser.add_argument(
        "--ollama-base-url",
        help="Override Ollama base URL (e.g. http://localhost:11434)",
    )
    parser.add_argument(
        "--corpus-dir",
        help="Directory containing source documents (default: corbus)",
    )
    parser.add_argument(
        "--vector-db-dir",
        help="Persistent vector DB directory (default: data/chroma)",
    )
    parser.add_argument(
        "--collection-name",
        help="Vector collection name (default: agentic_rag_docs)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Chunk size in characters for indexed source text (default: 1200)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="Chunk overlap in characters (default: 200)",
    )
    return parser

