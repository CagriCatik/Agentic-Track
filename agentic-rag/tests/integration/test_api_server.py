import pytest
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_api_chat_completions_basic():
    """ Integration test for the OpenAI-compatible chat endpoint. """
    payload = {
        "model": "llama3:8b",
        "messages": [
            {"role": "user", "content": "Was ist ASIL?"}
        ],
        "stream": False
    }
    
    response = client.post("/v1/chat/completions", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "content" in data["choices"][0]["message"]
    # Verify the answer contains automotive context
    assert "asil" in data["choices"][0]["message"]["content"].lower()

def test_api_chat_completions_streaming():
    """ Integration test for streaming support. """
    payload = {
        "model": "llama3:8b",
        "messages": [
            {"role": "user", "content": "Kurz erklären: ASIL"}
        ],
        "stream": True
    }
    
    with client.stream("POST", "/v1/chat/completions", json=payload) as response:
        assert response.status_code == 200
        # Check for first chunk of SSE
        first_line = next(response.iter_lines())
        assert first_line.startswith("data: ")
