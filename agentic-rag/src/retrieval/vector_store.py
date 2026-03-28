"""ChromaDB Index Layer — built FROM Gold, can be rebuilt anytime.

ChromaDB is NOT Gold. It is an ephemeral serving layer.
"""

from __future__ import annotations

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import get_settings, resolve_path
from src.knowledge.schemas import GoldRecord
from src.retrieval.embeddings import get_embeddings


def get_vector_store() -> Chroma:
    """Return a handle to the persisted ChromaDB vector store."""
    settings = get_settings()
    persist_dir = str(resolve_path(settings.data.gold_dir))
    return Chroma(
        collection_name=settings.retrieval.collection_name,
        embedding_function=get_embeddings(),
        persist_directory=persist_dir,
    )


def _gold_records_to_langchain_docs(gold_records: list[GoldRecord]) -> list[Document]:
    """Convert Gold records to LangChain Documents with full Chroma metadata."""
    docs: list[Document] = []
    for g in gold_records:
        meta = g.to_chroma_metadata()
        # Legacy aliases so existing retriever / node code doesn't break
        meta["page_start"] = g.pdf_page_start
        meta["page_end"] = g.pdf_page_end
        meta["section_header"] = g.section_path
        docs.append(Document(page_content=g.retrieval_text, metadata=meta))
    return docs


def index_gold_into_chromadb(gold_records: list[GoldRecord]) -> Chroma:
    """Wipe the existing index and rebuild it from a set of Gold records.

    Implements idempotent upsert behaviour: same Gold hash → same vector ID.
    """
    settings = get_settings()
    persist_dir = resolve_path(settings.data.gold_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    print(f"  📦 Building index at {persist_dir}")
    print(f"  📊 {len(gold_records)} Gold records to embed")

    docs = _gold_records_to_langchain_docs(gold_records)

    store = Chroma.from_documents(
        documents=docs,
        embedding=get_embeddings(),
        collection_name=settings.retrieval.collection_name,
        persist_directory=str(persist_dir),
    )
    print(f"  ✅ Index built with {store._collection.count()} vectors")
    return store


def query_chromadb(query_text: str, top_k: int = 5, filters: dict | None = None) -> list[Document]:
    """Search the ChromaDB index with optional metadata filters."""
    store = get_vector_store()
    retriever = store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": top_k, **({"filter": filters} if filters else {})},
    )
    return retriever.invoke(query_text)


# ── Legacy shim: old code calls rebuild_index(documents: list[Document]) ────
def rebuild_index(documents: list[Document]) -> Chroma:
    """Legacy compatibility: accept pre-built LangChain Documents and index them."""
    settings = get_settings()
    persist_dir = resolve_path(settings.data.gold_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    print(f"  📦 Building index at {persist_dir}")
    print(f"  📊 {len(documents)} chunks to embed")

    store = Chroma.from_documents(
        documents=documents,
        embedding=get_embeddings(),
        collection_name=settings.retrieval.collection_name,
        persist_directory=str(persist_dir),
    )
    print(f"  ✅ Index built with {store._collection.count()} vectors")
    return store
