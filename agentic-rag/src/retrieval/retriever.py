"""Retriever factory — configurable search strategies."""

from __future__ import annotations

from langchain_core.vectorstores import VectorStoreRetriever

from src.config import get_settings
from src.retrieval.vector_store import get_vector_store


def get_retriever() -> VectorStoreRetriever:
    """Create a retriever with parameters from config.yaml."""
    settings = get_settings()
    store = get_vector_store()

    if settings.retrieval.search_type == "mmr":
        return store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": settings.retrieval.top_k,
                "lambda_mult": settings.retrieval.mmr_diversity,
            },
        )
    else:
        return store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings.retrieval.top_k},
        )
