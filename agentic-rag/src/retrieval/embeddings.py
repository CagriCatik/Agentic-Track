"""OllamaEmbeddings wrapper — configured from config.yaml."""

from __future__ import annotations

from functools import lru_cache

from langchain_ollama import OllamaEmbeddings

from src.config import get_settings


@lru_cache(maxsize=1)
def get_embeddings() -> OllamaEmbeddings:
    """Return a cached OllamaEmbeddings instance."""
    settings = get_settings()
    return OllamaEmbeddings(
        model=settings.llm.embed_model,
        base_url=settings.llm.base_url,
    )
