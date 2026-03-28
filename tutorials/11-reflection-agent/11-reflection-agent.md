# Tutorial 11: Reflection Agent

In standard prompting, an LLM outputs its first guess and stops. A **Reflection Agent** uses LangGraph to feed the LLM's initial output *back* into itself, asking it to critique its own work and improve it. 

## The Goal
Create a 2-node graph. The first node generates an essay. The second node critiques the essay. The graph loops between them until the essay meets a certain quality standard.

## Dependencies needed:
```bash
uv add langgraph langchain-openai langchain-core
```

## The Code

Create a file named `reflection_agent.py`:

```python
import os
from dotenv import load_dotenv
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

class EssayState(TypedDict):
    topic: str
    draft: str
    critique: str
    revision_count: int

def generate_draft(state: EssayState):
    print(f"--- GENERATOR (Revision {state['revision_count']}) ---")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    # If there is a critique, use it to improve. Otherwise, write from scratch.
    if state.get("critique"):
        prompt = f"Rewrite an essay about {state['topic']}. Improve it using this critique: {state['critique']}"
    else:
        prompt = f"Write a terrible, 2-sentence essay about {state['topic']}."
        
    response = llm.invoke(prompt)
    return {"draft": response.content, "revision_count": state["revision_count"] + 1}

def critique_draft(state: EssayState):
    print("--- CRITIC ---")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = f"Read this essay: '{state['draft']}'. Provide a 1-sentence harsh critique on how to make it better."
    
    response = llm.invoke(prompt)
    print(f"Critique: {response.content}\n")
    return {"critique": response.content}

def route_critique(state: EssayState):
    # Stop looping after 2 revisions to save tokens
    if state["revision_count"] >= 2:
        return END
    return "critique"

def main():
    builder = StateGraph(EssayState)
    builder.add_node("generate", generate_draft)
    builder.add_node("critique", critique_draft)
    
    builder.add_edge(START, "generate")
    # Conditional edge: either go to critique, or end the graph
    builder.add_conditional_edges("generate", route_critique)
    builder.add_edge("critique", "generate")
    
    app = builder.compile()
    
    print("Starting Reflection Loop...\n")
    final_state = app.invoke({"topic": "Why cats are great", "draft": "", "critique": "", "revision_count": 0})
    
    print("\n--- FINAL ESSAY ---")
    print(final_state["draft"])

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run reflection_agent.py
```
You will see the console log the Generator writing a bad essay, the Critic tearing it apart, and the Generator rewriting it using the critique!
