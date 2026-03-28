"""LLM-as-a-Judge evaluator — uses local Ollama to score RAG outputs."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_interface.chains import get_hallucination_grader, get_answer_grader


def judge_faithfulness(documents_text: str, generation: str) -> str:
    """Judge if the generation is grounded in the documents.

    Returns: "yes" or "no"
    """
    result = get_hallucination_grader().invoke({
        "documents": documents_text,
        "generation": generation,
    })
    verdict = result.strip().lower()
    return "yes" if "yes" in verdict else "no"


def judge_relevance(question: str, generation: str) -> str:
    """Judge if the generation addresses the question.

    Returns: "yes" or "no"
    """
    result = get_answer_grader().invoke({
        "question": question,
        "generation": generation,
    })
    verdict = result.strip().lower()
    return "yes" if "yes" in verdict else "no"
