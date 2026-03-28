"""StateGraph wiring — compile all nodes and edges into an executable app."""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from src.orchestration.state import AgentState
from src.orchestration.nodes import (
    security_node,
    route_node,
    retrieve_node,
    grade_documents_node,
    web_search_node,
    generate_node,
    hallucination_check_node,
    answer_relevance_node,
    route_after_security,
    route_after_route,
    route_after_grade,
    route_after_hallucination_check,
    route_after_answer_relevance,
)


def _blocked_node(state: AgentState) -> dict:
    """Terminal node for blocked (dangerous) inputs."""
    print("🚫  [blocked] Query rejected — potential prompt injection detected.")
    return {"generation": "⚠️ Anfrage blockiert: Potenzieller Prompt-Injection-Versuch erkannt."}


def build_graph() -> StateGraph:
    """Construct the Agentic RAG graph."""
    builder = StateGraph(AgentState)

    # ── Add Nodes ────────────────────────────────────────────
    builder.add_node("security", security_node)
    builder.add_node("route", route_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("grade_documents", grade_documents_node)
    builder.add_node("web_search", web_search_node)
    builder.add_node("generate", generate_node)
    builder.add_node("hallucination_check", hallucination_check_node)
    builder.add_node("answer_relevance", answer_relevance_node)
    builder.add_node("blocked", _blocked_node)

    # ── Entry Point ──────────────────────────────────────────
    builder.add_edge(START, "security")

    # ── Security → Route or Blocked ──────────────────────────
    builder.add_conditional_edges(
        "security",
        route_after_security,
        {"route": "route", "blocked": "blocked"},
    )
    builder.add_edge("blocked", END)

    # ── Route → Retrieve or Generate ─────────────────────────
    builder.add_conditional_edges(
        "route",
        route_after_route,
        {"retrieve": "retrieve", "generate": "generate"},
    )

    # ── Retrieve → Grade ─────────────────────────────────────
    builder.add_edge("retrieve", "grade_documents")

    # ── Grade → Generate or Web Search ───────────────────────
    builder.add_conditional_edges(
        "grade_documents",
        route_after_grade,
        {"generate": "generate", "web_search": "web_search"},
    )

    # ── Web Search → Generate ────────────────────────────────
    builder.add_edge("web_search", "generate")

    # ── Generate → Hallucination Check ───────────────────────
    builder.add_edge("generate", "hallucination_check")

    # ── Hallucination Check → Answer Relevance or Re-generate ─
    builder.add_conditional_edges(
        "hallucination_check",
        route_after_hallucination_check,
        {
            "answer_relevance": "answer_relevance",
            "regenerate": "generate",
        },
    )

    # ── Answer Relevance → END or Web Search ─────────────────
    builder.add_conditional_edges(
        "answer_relevance",
        route_after_answer_relevance,
        {"end": END, "web_search": "web_search"},
    )

    return builder


def compile_graph():
    """Build, compile, and return the executable graph."""
    builder = build_graph()
    return builder.compile()


# Singleton compiled graph
app = compile_graph()
