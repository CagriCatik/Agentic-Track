"""Application orchestration for the local RAG CLI."""

from __future__ import annotations

import logging

from .citations import normalize_inline_citations
from .cli import print_startup, run_chat_loop
from .config import AppConfig
from .graph import build_graph
from .logging_utils import configure_logging
from .models import discover_ollama_models, model_exists, select_models
from .vector_index import build_retriever, index_pdf_corpus, index_requires_rebuild

logger = logging.getLogger(__name__)


def _print_install_help() -> None:
    print("No Ollama models were discovered.")
    print("Install at least one chat model and one embedding model, for example:")
    print("  ollama pull qwen2.5:7b")
    print("  ollama pull nomic-embed-text")


def run(config: AppConfig) -> int:
    configure_logging()
    logger.info(
        "Starting CLI app: corpus_dir=%s vector_db_dir=%s collection=%s index_on_start=%s reindex=%s index_only=%s",
        config.corpus_dir,
        config.vector_db_dir,
        config.collection_name,
        config.index_on_start,
        config.reindex,
        config.index_only,
    )
    available_models = discover_ollama_models(base_url=config.ollama_base_url)
    if not available_models:
        _print_install_help()
        return 1

    if config.list_models_only:
        print("Discovered Ollama models:")
        for model in available_models:
            print(f" - {model}")
        return 0

    if config.chat_model and not model_exists(config.chat_model, available_models):
        print(
            f"Warning: --chat-model '{config.chat_model}' is not in `ollama list`; "
            "trying it anyway."
        )
    if config.embedding_model and not model_exists(
        config.embedding_model, available_models
    ):
        print(
            f"Warning: --embedding-model '{config.embedding_model}' is not in "
            "`ollama list`; trying it anyway."
        )

    chat_model, embedding_model = select_models(
        available_models,
        forced_chat=config.chat_model,
        forced_embedding=config.embedding_model,
    )
    if not chat_model:
        print("Could not infer a chat model from installed models.")
        print("Use --chat-model to set one explicitly.")
        return 1
    if not embedding_model:
        print("Could not infer an embedding model from installed models.")
        print("Use --embedding-model or install `nomic-embed-text`.")
        return 1

    effective_reranker_model = config.reranker_model or chat_model
    if (
        config.reranker_enabled
        and config.reranker_mode == "llm"
        and effective_reranker_model
        and not model_exists(effective_reranker_model, available_models)
    ):
        print(
            f"Configured reranker model '{effective_reranker_model}' was not discovered in `ollama list`."
        )
        return 1
    if (
        config.reranker_enabled
        and config.reranker_mode == "auto"
        and effective_reranker_model
        and not model_exists(effective_reranker_model, available_models)
    ):
        effective_reranker_model = None

    rebuild_required = index_requires_rebuild(config.vector_db_dir)
    logger.info("Index rebuild required=%s", rebuild_required)

    if config.index_on_start or config.reindex or config.index_only or rebuild_required:
        logger.info(
            "Running CLI indexing: force_reindex=%s",
            (config.reindex or rebuild_required),
        )
        stats = index_pdf_corpus(
            embedding_model=embedding_model,
            corpus_dir=config.corpus_dir,
            vector_db_dir=config.vector_db_dir,
            collection_name=config.collection_name,
            ollama_base_url=config.ollama_base_url,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            force_reindex=(config.reindex or rebuild_required),
        )
        print("\nIndex status:")
        print(f" scanned files   : {stats.scanned_files}")
        print(f" indexed files   : {stats.indexed_files}")
        print(f" skipped files   : {stats.skipped_files}")
        print(f" removed files   : {stats.removed_files}")
        print(f" added chunks    : {stats.added_chunks}")
        print(f" deleted chunks  : {stats.deleted_chunks}")
        print(f" failed files    : {stats.failed_files}")
        print(f" total chunks    : {stats.total_chunks_in_index}")
        logger.info(
            "CLI indexing complete: scanned=%d indexed=%d skipped=%d removed=%d added_chunks=%d deleted_chunks=%d failed=%d total_chunks=%d",
            stats.scanned_files,
            stats.indexed_files,
            stats.skipped_files,
            stats.removed_files,
            stats.added_chunks,
            stats.deleted_chunks,
            stats.failed_files,
            stats.total_chunks_in_index,
        )

    if config.index_only:
        logger.info("CLI exiting after index-only run")
        return 0

    retriever = build_retriever(
        embedding_model=embedding_model,
        vector_db_dir=config.vector_db_dir,
        collection_name=config.collection_name,
        ollama_base_url=config.ollama_base_url,
        top_k=config.top_k,
        retrieval_candidates=config.retrieval_candidates,
        reranker_enabled=config.reranker_enabled,
        reranker_mode=config.reranker_mode,
        reranker_model=effective_reranker_model,
        reranker_top_n=config.reranker_top_n,
    )
    logger.info(
        "CLI runtime ready: chat_model=%s embedding_model=%s reranker_enabled=%s reranker_mode=%s reranker_model=%s",
        chat_model,
        embedding_model,
        config.reranker_enabled,
        config.reranker_mode,
        effective_reranker_model or "feature-only",
    )

    graph = build_graph(
        chat_model=chat_model,
        temperature=config.temperature,
        system_prompt=config.system_prompt,
        retriever=retriever,
        ollama_base_url=config.ollama_base_url,
    )

    class _GraphChatAdapter:
        def invoke(self, question: str) -> str:
            logger.info("CLI question received: %r", question[:200])
            final_state = graph.invoke(
                {"question": question, "history": "", "revision_count": 0}
            )
            answer = final_state.get("generation", "")
            answer = answer if isinstance(answer, str) else str(answer)
            normalized_answer, _ = normalize_inline_citations(answer)
            logger.info(
                "CLI answer ready: support_status=%s support_confidence=%.2f docs=%d",
                final_state.get("support_status", "unknown"),
                float(final_state.get("support_confidence", 0.0)),
                len(final_state.get("docs", []) or []),
            )
            return normalized_answer

    print_startup(
        available_models=available_models,
        chat_model=chat_model,
        embedding_model=embedding_model,
        temperature=config.temperature,
        top_k=config.top_k,
        retrieval_candidates=config.retrieval_candidates,
        reranker_enabled=config.reranker_enabled,
        reranker_mode=config.reranker_mode,
        reranker_model=effective_reranker_model,
    )
    run_chat_loop(_GraphChatAdapter())
    return 0
