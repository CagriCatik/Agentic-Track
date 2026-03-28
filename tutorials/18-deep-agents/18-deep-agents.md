# Tutorial 18: Deep Agents (Sub-Agents & Hierarchies)

When an agent becomes too complex—given 50 tools and a massive system prompt—it inevitably becomes confused, forgets instructions, and hallucinates parameters.
The solution is a **Hierarchical Agent Graph**. A main "Supervisor" agent has no tools except the ability to delegate tasks to highly specialized "Worker" Sub-Agents.

## The Goal
Build a LangGraph node structure where a Supervisor Agent receives a user prompt and delegates it to either a "Math Worker" or a "Research Worker".

## The Conceptual Architecture

We cannot fit a massive multi-agent system into 50 lines easily, but here is the exact LangGraph routing architecture you would build in `deep_agents.py`:

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class MultiAgentState(TypedDict):
    task: str
    delegation: str
    final_answer: str

# --- The Supervisor ---
def supervisor_node(state: MultiAgentState):
    print("SUPERVISOR: Analyzing task...")
    # In reality, this is an LLM call deciding who to route to
    if "multiply" in state["task"].lower():
        routing = "math_worker"
    else:
        routing = "research_worker"
        
    return {"delegation": routing}

# --- The Workers ---
def math_worker_node(state: MultiAgentState):
    print("MATH WORKER: Executing math tools...")
    return {"final_answer": "I calculated the math."}

def research_worker_node(state: MultiAgentState):
    print("RESEARCH WORKER: Scraping wikipedia tools...")
    return {"final_answer": "I researched the topic."}

# --- The Router Function ---
def route_to_worker(state: MultiAgentState):
    return state["delegation"]

def main():
    builder = StateGraph(MultiAgentState)
    
    # Add all 3 agents as nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("math_worker", math_worker_node)
    builder.add_node("research_worker", research_worker_node)
    
    builder.add_edge(START, "supervisor")
    
    # The supervisor dictates which edge activates
    builder.add_conditional_edges("supervisor", route_to_worker)
    
    # They both return to the user
    builder.add_edge("math_worker", END)
    builder.add_edge("research_worker", END)
    
    app = builder.compile()
    
    print("\n--- Test 1 ---")
    app.invoke({"task": "Please multiply 50 by 2", "delegation": "", "final_answer": ""})
    
    print("\n--- Test 2 ---")
    app.invoke({"task": "Who was Abraham Lincoln?", "delegation": "", "final_answer": ""})

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run deep_agents.py
```
Notice how the Supervisor completely shields the Math Worker from unrelated tasks. This allows you to give the Math Worker a hyper-strict prompt and tools without confusing the Research Worker!
