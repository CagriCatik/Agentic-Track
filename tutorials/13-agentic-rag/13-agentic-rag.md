# Tutorial 13: Agentic RAG

Standard RAG pipelines break if the retrieval step fetches irrelevant chunks. **Agentic RAG** fixes this by inserting routing nodes: if the retrieved chunks are irrelevant, the agent throws them away, rewrites the user's search query, and searches the vector database again.

## The Goal
Build a theoretical conditional node architecture that evaluates RAG context quality.

## The Architecture (Conceptual)

Instead of a linear script, Agentic RAG is defined by conditionals. Create `agentic_rag.py`:

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict
import random

class RAGState(TypedDict):
    question: str
    context: str
    relevance_score: str
    answer: str

def retrieve_node(state: RAGState):
    print("-> Retrieving chunks from Vector DB...")
    # Mocking a bad retrieval 50% of the time
    if random.choice([True, False]):
        return {"context": "The company was founded in 1990."}
    else:
        return {"context": "Apples are delicious."}

def grade_node(state: RAGState):
    print("-> Grading Relevance of chunks...")
    # LLM decides if the chunk actually answers the question
    if "company" in state["context"]:
        return {"relevance_score": "yes"}
    else:
        return {"relevance_score": "no"}

def generate_node(state: RAGState):
    print("-> Generating final answer with LLM...")
    return {"answer": f"Based on '{state['context']}', here is the answer."}

def rewrite_query_node(state: RAGState):
    print("-> Context was useless. Rewriting query and trying again...")
    return {"question": state["question"] + " (rewritten)"}

def check_relevance(state: RAGState):
    # This is the routing logic
    if state["relevance_score"] == "yes":
        return "generate"
    else:
        return "rewrite"

def main():
    builder = StateGraph(RAGState)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("grade", grade_node)
    builder.add_node("generate", generate_node)
    builder.add_node("rewrite", rewrite_query_node)
    
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "grade")
    
    # Conditional branching!
    builder.add_conditional_edges("grade", check_relevance)
    
    # If we rewrite, loop back to retrieve
    builder.add_edge("rewrite", "retrieve")
    builder.add_edge("generate", END)
    
    app = builder.compile()
    print("Invoking Agentic RAG...\n")
    final = app.invoke({"question": "When was the company founded?", "context": "", "relevance_score": "", "answer": ""})
    
    print(f"\nFinal State Answer: {final['answer']}")

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run agentic_rag.py
```
If the mock retrieves "Apples", the grader will reject it, routing the flow to `rewrite`, forming a self-correcting RAG loop!
