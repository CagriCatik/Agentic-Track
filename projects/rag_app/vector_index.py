"""Persistent indexing and hybrid retrieval for heterogeneous corpora."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chromadb import PersistentClient
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .catalog import (
    catalog_is_compatible,
    delete_chunk_ids as delete_catalog_chunk_ids,
    get_catalog_path,
    initialize_catalog,
    reset_catalog,
    upsert_documents,
)
from .loaders import discover_source_files, load_source_document, source_key
from .retrieval import HybridRetriever
from .reranker import build_reranker

MANIFEST_NAME = "index_manifest.json"
INDEX_SCHEMA_VERSION = 3
DEFAULT_COLLECTION = "agentic_rag_docs"
logger = logging.getLogger(__name__)


@dataclass
class IndexStats:
    scanned_files: int = 0
    indexed_files: int = 0
    skipped_files: int = 0
    removed_files: int = 0
    added_chunks: int = 0
    deleted_chunks: int = 0
    failed_files: int = 0
    total_chunks_in_index: int = 0


def _file_signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def _source_key(corpus_root: Path, source_path: Path) -> str:
    return source_key(corpus_root, source_path)


def _split_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    clean = " ".join(text.split())
    if not clean:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(clean)


def _chunk_source_document(
    source_document: Any,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[Document], list[str]]:
    documents: list[Document] = []
    ids: list[str] = []

    for segment_index, segment_text in enumerate(source_document.segments, start=1):
        chunks = _split_text(
            segment_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        for chunk_index, chunk in enumerate(chunks):
            chunk_id = hashlib.sha1(
                f"{source_document.source_key}|{segment_index}|{chunk_index}|{chunk}".encode("utf-8")
            ).hexdigest()
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "chunk_id": chunk_id,
                        "source_key": source_document.source_key,
                        "source_path": source_document.source_path,
                        "source_name": source_document.source_name,
                        "source_type": source_document.source_type,
                        "title": source_document.title,
                        "author": source_document.author,
                        "page": segment_index,
                        "chunk": chunk_index,
                    },
                )
            )
            ids.append(chunk_id)

    return documents, ids


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {"version": INDEX_SCHEMA_VERSION, "files": {}}
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": INDEX_SCHEMA_VERSION, "files": {}}

    files = raw.get("files")
    if raw.get("version") != INDEX_SCHEMA_VERSION or not isinstance(files, dict):
        return {"version": INDEX_SCHEMA_VERSION, "files": {}}
    return {"version": INDEX_SCHEMA_VERSION, "files": files}


def _save_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _batched(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _delete_ids(store: Chroma, catalog_path: Path, ids: list[str]) -> int:
    if not ids:
        return 0
    deleted = 0
    for batch in _batched(ids, 256):
        store.delete(ids=batch)
        delete_catalog_chunk_ids(catalog_path, batch)
        deleted += len(batch)
    return deleted


def _get_total_chunk_count(store: Chroma) -> int:
    data = store.get(include=[])
    return len(data.get("ids", []))


def _create_store(
    *,
    embedding_model: str,
    vector_db_dir: Path,
    collection_name: str,
    ollama_base_url: str | None,
) -> Chroma:
    embeddings = OllamaEmbeddings(
        model=embedding_model,
        base_url=ollama_base_url,
    )
    vector_db_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        persist_directory=str(vector_db_dir),
        embedding_function=embeddings,
    )


def _reset_store(vector_db_dir: Path, collection_name: str) -> None:
    vector_db_dir.mkdir(parents=True, exist_ok=True)
    client = PersistentClient(path=str(vector_db_dir))
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass


def index_requires_rebuild(vector_db_dir: str) -> bool:
    db_path = Path(vector_db_dir)
    manifest_path = db_path / MANIFEST_NAME
    catalog_path = get_catalog_path(db_path)

    if not manifest_path.exists():
        return True

    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True

    if raw.get("version") != INDEX_SCHEMA_VERSION:
        return True

    return not catalog_is_compatible(catalog_path)


def build_retriever(
    *,
    embedding_model: str,
    vector_db_dir: str,
    collection_name: str,
    ollama_base_url: str | None,
    top_k: int,
    retrieval_candidates: int | None = None,
    reranker_enabled: bool = True,
    reranker_mode: str = "auto",
    reranker_model: str | None = None,
    reranker_top_n: int = 8,
):
    logger.info(
        "Building retriever: collection=%s vector_db_dir=%s top_k=%d candidates=%s reranker_enabled=%s reranker_mode=%s reranker_model=%s",
        collection_name,
        vector_db_dir,
        top_k,
        retrieval_candidates or max(top_k * 4, 12),
        reranker_enabled,
        reranker_mode,
        reranker_model or "feature-only",
    )
    store = _create_store(
        embedding_model=embedding_model,
        vector_db_dir=Path(vector_db_dir),
        collection_name=collection_name,
        ollama_base_url=ollama_base_url,
    )
    candidate_limit = retrieval_candidates or max(top_k * 4, 12)
    return HybridRetriever(
        vector_store=store,
        vector_db_dir=vector_db_dir,
        top_k=top_k,
        reranker=build_reranker(
            enabled=reranker_enabled,
            mode=reranker_mode,
            candidate_limit=candidate_limit,
            ollama_base_url=ollama_base_url,
            llm_model=reranker_model,
            llm_top_n=reranker_top_n,
        ),
        semantic_k=candidate_limit,
        lexical_k=candidate_limit,
    )


def get_index_chunk_count(
    *,
    embedding_model: str,
    vector_db_dir: str,
    collection_name: str,
    ollama_base_url: str | None,
) -> int:
    store = _create_store(
        embedding_model=embedding_model,
        vector_db_dir=Path(vector_db_dir),
        collection_name=collection_name,
        ollama_base_url=ollama_base_url,
    )
    return _get_total_chunk_count(store)


def index_corpus(
    *,
    embedding_model: str,
    corpus_dir: str,
    vector_db_dir: str,
    collection_name: str = DEFAULT_COLLECTION,
    ollama_base_url: str | None = None,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
    force_reindex: bool = False,
) -> IndexStats:
    stats = IndexStats()
    logger.info(
        "Starting corpus indexing: corpus_dir=%s vector_db_dir=%s collection=%s force_reindex=%s chunk_size=%d chunk_overlap=%d",
        corpus_dir,
        vector_db_dir,
        collection_name,
        force_reindex,
        chunk_size,
        chunk_overlap,
    )

    corpus_root = Path(corpus_dir)
    if not corpus_root.exists():
        logger.warning("Corpus directory does not exist, skipping indexing: %s", corpus_dir)
        return stats

    db_path = Path(vector_db_dir)
    manifest_path = db_path / MANIFEST_NAME
    catalog_path = get_catalog_path(db_path)
    rebuild_required = force_reindex or index_requires_rebuild(vector_db_dir)

    if rebuild_required:
        logger.info(
            "Resetting persisted index and catalog: vector_db_dir=%s collection=%s rebuild_required=%s",
            vector_db_dir,
            collection_name,
            rebuild_required,
        )
        _reset_store(db_path, collection_name)
        reset_catalog(catalog_path)

    initialize_catalog(catalog_path)
    manifest = _load_manifest(manifest_path)
    files_state: dict[str, Any] = manifest["files"]

    store = _create_store(
        embedding_model=embedding_model,
        vector_db_dir=db_path,
        collection_name=collection_name,
        ollama_base_url=ollama_base_url,
    )

    source_paths = discover_source_files(corpus_root)
    stats.scanned_files = len(source_paths)
    logger.info("Discovered %d supported source files in corpus", stats.scanned_files)
    current_keys = {_source_key(corpus_root, path) for path in source_paths}
    known_keys = set(files_state.keys())

    for removed_key in sorted(known_keys - current_keys):
        entry = files_state.get(removed_key, {})
        ids = entry.get("ids", []) if isinstance(entry, dict) else []
        stats.deleted_chunks += _delete_ids(store, catalog_path, ids)
        stats.removed_files += 1
        files_state.pop(removed_key, None)
        logger.info(
            "Removed stale source from index: source=%s deleted_chunks=%d",
            removed_key,
            len(ids),
        )

    for source_path in source_paths:
        key = _source_key(corpus_root, source_path)
        signature = _file_signature(source_path)
        previous = files_state.get(key, {}) if isinstance(files_state.get(key), dict) else {}

        if not rebuild_required and previous.get("signature") == signature:
            stats.skipped_files += 1
            logger.debug("Skipping unchanged source: %s", key)
            continue

        stats.deleted_chunks += _delete_ids(
            store,
            catalog_path,
            previous.get("ids", []),
        )
        logger.info("Indexing source: %s", key)

        try:
            source_document = load_source_document(source_path, corpus_root=corpus_root)
            documents, ids = _chunk_source_document(
                source_document,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        except Exception as exc:
            stats.failed_files += 1
            files_state[key] = {
                "signature": signature,
                "ids": [],
                "error": str(exc),
            }
            logger.exception("Failed to index source: %s", key)
            continue

        if documents:
            for docs_batch, ids_batch in zip(
                _batched(documents, 64),
                _batched(ids, 64),
            ):
                store.add_documents(documents=docs_batch, ids=ids_batch)
                upsert_documents(catalog_path, ids_batch, docs_batch)
            stats.added_chunks += len(ids)
            logger.info(
                "Indexed source: source=%s source_type=%s chunks=%d",
                key,
                source_document.source_type,
                len(ids),
            )
        else:
            logger.info(
                "Indexed source with no chunks: source=%s source_type=%s",
                key,
                source_document.source_type,
            )

        files_state[key] = {
            "signature": signature,
            "ids": ids,
            "error": None,
            "source_type": source_document.source_type,
        }
        stats.indexed_files += 1

    _save_manifest(manifest_path, manifest)
    stats.total_chunks_in_index = _get_total_chunk_count(store)
    logger.info(
        "Corpus indexing complete: scanned=%d indexed=%d skipped=%d removed=%d added_chunks=%d deleted_chunks=%d failed=%d total_chunks=%d",
        stats.scanned_files,
        stats.indexed_files,
        stats.skipped_files,
        stats.removed_files,
        stats.added_chunks,
        stats.deleted_chunks,
        stats.failed_files,
        stats.total_chunks_in_index,
    )
    return stats


def index_pdf_corpus(**kwargs: Any) -> IndexStats:
    """Backward-compatible alias for the older entry point."""
    return index_corpus(**kwargs)
