"""Unit tests for graph node routing logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.orchestration.nodes import route_after_security, route_after_route, route_after_grade


def test_security_routes_blocked():
    """DANGER state routes to blocked."""
    state = {"is_safe": "DANGER"}
    assert route_after_security(state) == "blocked"


def test_security_routes_safe():
    """SAFE state routes to route."""
    state = {"is_safe": "SAFE"}
    assert route_after_security(state) == "route"


def test_route_vectorstore():
    """Vectorstore datasource routes to retrieve."""
    state = {"datasource": "vectorstore"}
    assert route_after_route(state) == "retrieve"


def test_route_direct():
    """Direct LLM datasource routes to generate."""
    state = {"datasource": "direct_llm"}
    assert route_after_route(state) == "generate"


def test_grade_needs_websearch():
    """Web search needed routes to web_search."""
    state = {"web_search_needed": "yes"}
    assert route_after_grade(state) == "web_search"


def test_grade_all_relevant():
    """No web search needed routes to generate."""
    state = {"web_search_needed": "no"}
    assert route_after_grade(state) == "generate"
