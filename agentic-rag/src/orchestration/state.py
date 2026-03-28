"""LangGraph AgentState — the shared memory bus for all nodes."""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict):
    """State that flows through every node in the Agentic RAG graph."""

    question: str
    generation: str
    documents: list  # list of LangChain Document objects
    datasource: str  # "vectorstore" or "direct_llm"
    is_safe: str  # "SAFE" or "DANGER"
    web_search_needed: str  # "yes" or "no"
    retry_count: int
