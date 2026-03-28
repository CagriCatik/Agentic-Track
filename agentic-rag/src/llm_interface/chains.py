"""LCEL chain definitions — 6 chains for the Agentic RAG pipeline."""

from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser

from src.llm_interface.model import get_llm
from src.llm_interface.prompts import (
    SECURITY_PROMPT,
    ROUTE_PROMPT,
    RETRIEVAL_GRADER_PROMPT,
    GENERATION_PROMPT,
    HALLUCINATION_GRADER_PROMPT,
    ANSWER_GRADER_PROMPT,
)


def _build_chain(prompt):
    """Build a simple prompt | llm | parser chain."""
    return prompt | get_llm() | StrOutputParser()


def get_security_chain():
    """Detect prompt injection attempts."""
    return _build_chain(SECURITY_PROMPT)


def get_route_chain():
    """Route queries to vectorstore or direct_llm."""
    return _build_chain(ROUTE_PROMPT)


def get_retrieval_grader():
    """Grade document relevance (yes/no)."""
    return _build_chain(RETRIEVAL_GRADER_PROMPT)


def get_generation_chain():
    """Generate RAG answer with citations."""
    return _build_chain(GENERATION_PROMPT)

def get_direct_chat_chain():
    """Answer simple queries directly, skipping RAG context."""
    from src.llm_interface.prompts import DIRECT_CHAT_PROMPT
    return _build_chain(DIRECT_CHAT_PROMPT)


def get_hallucination_grader():
    """Check if answer is grounded in documents (yes/no)."""
    return _build_chain(HALLUCINATION_GRADER_PROMPT)


def get_answer_grader():
    """Check if answer addresses the question (yes/no)."""
    return _build_chain(ANSWER_GRADER_PROMPT)
