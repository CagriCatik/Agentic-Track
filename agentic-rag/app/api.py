"""FastAPI server for Open WebUI (OpenAI compatible)."""

import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.orchestration.graph import app as graph_app
from src.config import get_settings

app = FastAPI(title="Agentic RAG — OpenAI Compatible API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Agentic RAG API is running! Connect Open WebUI to /v1"}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    stream: Optional[bool] = False

import json
import asyncio
from fastapi.responses import StreamingResponse

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """OpenAI-compatible endpoint for Open WebUI integration."""
    user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), None)
    if not user_msg:
        raise HTTPException(status_code=400, detail="No user message provided.")

    # Execute LangGraph backend
    initial_state = {
        "question": user_msg,
        "generation": "",
        "documents": [],
        "datasource": "",
        "is_safe": "",
        "web_search_needed": "no",
        "retry_count": 0,
    }

    result = graph_app.invoke(initial_state)
    answer = result.get("generation", "Keine Antwort generiert.")

    # Append citations into the Markdown response natively
    documents = result.get("documents", [])
    if documents:
        sources = []
        seen = set()
        for doc in documents:
            src = doc.metadata.get("source_file", "?")
            page = doc.metadata.get("page_start", "?")
            key = f"{src}::{page}"
            if key not in seen:
                seen.add(key)
                if str(page) == "0" or "http" in src:
                    sources.append(f"- {src}")
                else:
                    sources.append(f"- {src}, Seite {page}")

        if sources:
            answer += "\n\n---\n**📚 Quellen:**\n" + "\n".join(sources)

    if req.stream:
        async def event_stream():
            # Send initial role setup
            yield f"data: {json.dumps({'id': 'chat', 'object': 'chat.completion.chunk', 'model': req.model, 'choices': [{'delta': {'role': 'assistant'}, 'index': 0}]})}\n\n"
            
            # Stream the generated answer iteratively by character chunks to preserve all whitespace and newlines
            chunk_size = 15
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i+chunk_size]
                payload = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "model": req.model,
                    "choices": [{"delta": {"content": chunk}, "index": 0, "finish_reason": None}]
                }
                yield f"data: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.01)

            # End of stream
            yield f"data: {json.dumps({'id': 'chat', 'object': 'chat.completion.chunk', 'model': req.model, 'choices': [{'delta': {}, 'index': 0, 'finish_reason': 'stop'}]})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # Format return as an OpenAI HTTP format
    return {
        "id": f"chatcmpl-agentic-rag-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": answer
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(user_msg.split()),
            "completion_tokens": len(answer.split()),
            "total_tokens": len(user_msg.split()) + len(answer.split())
        }
    }

@app.get("/v1/models")
async def list_models():
    """Return dummy models to satisfy Open WebUI discovery."""
    return {
        "object": "list",
        "data": [
            {"id": "agentic-rag-backend", "object": "model", "owned_by": "ollama"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    # When run directly, default to 8000
    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)
