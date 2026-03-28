import pytest
from src.orchestration.graph import app
from src.config import get_settings

def test_rag_graph_execution_full():
    """
    Integration test for the LangGraph orchestrator.
    Requires local LLM (Ollama) to be running or mocked.
    Since we want a 'real' integration test, we'll assume Ollama is up.
    """
    # 1. Input state
    initial_state = {
        "question": "Was ist ASIL in Bezug auf funktionale Sicherheit?",
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "web_search_required": False
    }
    
    # 2. Invoke Graph
    # Use thread_id for state persistence if needed, but for a single shot it's fine
    config = {"configurable": {"thread_id": "test-123"}}
    
    result = app.invoke(initial_state, config=config)
    
    # 3. Assertions
    assert "generation" in result
    assert len(result["generation"]) > 5
    assert "asil" in result["generation"].lower()
    
    # Verify citations are present
    assert "[" in result["generation"]
    assert "Quelle" in result["generation"]
    
    # Verify documents were retrieved
    assert len(result["documents"]) > 0
    assert "page_content" in result["documents"][0].dict()
