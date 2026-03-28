"""ChatOllama initialization — configured from config.yaml."""

from __future__ import annotations

from functools import lru_cache

from langchain_ollama import ChatOllama

from src.config import get_settings


def get_llm() -> ChatOllama:
    """Return a new ChatOllama instance reflecting current settings."""
    settings = get_settings()
    return ChatOllama(
        model=settings.llm.chat_model,
        base_url=settings.llm.base_url,
        temperature=settings.llm.temperature,
    )
