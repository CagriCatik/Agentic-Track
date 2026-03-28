"""Evaluation metrics — retrieval quality, generation quality, and system performance."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class QueryMetrics:
    """Metrics for a single query evaluation."""

    question: str = ""
    expected_source: str = ""
    expected_keywords: list[str] = field(default_factory=list)

    # Retrieval metrics
    retrieved_sources: list[str] = field(default_factory=list)
    precision_at_k: float = 0.0
    source_hit: bool = False

    # Generation metrics
    generation: str = ""
    faithfulness: str = ""  # "yes" or "no"
    answer_relevance: str = ""  # "yes" or "no"
    citation_found: bool = False

    # Latency
    retrieval_latency_s: float = 0.0
    e2e_latency_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "expected_source": self.expected_source,
            "precision_at_k": self.precision_at_k,
            "source_hit": self.source_hit,
            "faithfulness": self.faithfulness,
            "answer_relevance": self.answer_relevance,
            "citation_found": self.citation_found,
            "retrieval_latency_s": round(self.retrieval_latency_s, 3),
            "e2e_latency_s": round(self.e2e_latency_s, 3),
        }


@dataclass
class EvalReport:
    """Aggregated evaluation report across all queries."""

    query_results: list[QueryMetrics] = field(default_factory=list)

    @property
    def total_queries(self) -> int:
        return len(self.query_results)

    @property
    def avg_precision_at_k(self) -> float:
        if not self.query_results:
            return 0.0
        return sum(q.precision_at_k for q in self.query_results) / len(self.query_results)

    @property
    def source_accuracy(self) -> float:
        if not self.query_results:
            return 0.0
        return sum(1 for q in self.query_results if q.source_hit) / len(self.query_results)

    @property
    def faithfulness_rate(self) -> float:
        if not self.query_results:
            return 0.0
        return sum(1 for q in self.query_results if q.faithfulness == "yes") / len(self.query_results)

    @property
    def relevance_rate(self) -> float:
        if not self.query_results:
            return 0.0
        return sum(1 for q in self.query_results if q.answer_relevance == "yes") / len(self.query_results)

    @property
    def avg_e2e_latency(self) -> float:
        if not self.query_results:
            return 0.0
        return sum(q.e2e_latency_s for q in self.query_results) / len(self.query_results)

    @property
    def avg_retrieval_latency(self) -> float:
        if not self.query_results:
            return 0.0
        return sum(q.retrieval_latency_s for q in self.query_results) / len(self.query_results)

    def summary(self) -> dict:
        return {
            "total_queries": self.total_queries,
            "avg_precision_at_k": round(self.avg_precision_at_k, 3),
            "source_accuracy": round(self.source_accuracy, 3),
            "faithfulness_rate": round(self.faithfulness_rate, 3),
            "relevance_rate": round(self.relevance_rate, 3),
            "avg_e2e_latency_s": round(self.avg_e2e_latency, 3),
            "avg_retrieval_latency_s": round(self.avg_retrieval_latency, 3),
        }
