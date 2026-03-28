# Tutorial 10: Introduction to LangGraph

Standard LLM Chains are linear (A -> B -> C). `create_react_agent` is a massive black box loop. What if you want to build a deeply customized, branching AI flow with cycles and state management?
**LangGraph** treats the AI pipeline as a mathematical Graph (Nodes and Edges) running over a persistent state.

## The Goal
We will build a simple "State Machine" Agent. The graph has a `State` containing a message history. You will write custom python functions (nodes) and link them together (edges) to form a directed graph.

## Dependencies needed:
```bash
uv add langgraph langchain-openai langchain-core
```

## The Code

Create a file named `langgraph_intro.py`:

```python
import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage

load_dotenv()

# 1. Define the State Object
# This object is passed around to every Node.
# Annotated[list, operator.add] means "Every time a node returns a message, append it to the list, don't overwrite it."
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]

# 2. Define our actual LLM function (The Node)
def chatbot_node(state: AgentState):
    print("--- CHATBOT NODE TRIGGERED ---")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Run the LLM on the current state history
    response = llm.invoke(state["messages"])
    
    # Return a dictionary updating the state
    return {"messages": [response]}

def main():
    # 3. Initialize the Graph Builder
    graph_builder = StateGraph(AgentState)
    
    # 4. Add the Node to the graph
    graph_builder.add_node("chatbot", chatbot_node)
    
    # 5. Connect the Graph Logic (Edges)
    # The graph starts, goes directly precisely to the 'chatbot' node, and ends immediately.
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    
    # 6. Compile the graph
    app = graph_builder.compile()
    
    # 7. Execute!
    user_input = "Hello, what is LangGraph?"
    print(f"User: {user_input}\n")
    
    # We pass the initial state (dictionary) containing the human message
    final_state = app.invoke({"messages": [HumanMessage(content=user_input)]})
    
    # The graph processes all edges, then outputs the final state dictionary
    print("\n--- FINAL GRAPH OUTPUT ---")
    print(final_state["messages"][-1].content)

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run langgraph_intro.py
```

## Why all this boilerplate for a simple call?
Because later, you can add 10 different nodes (`database_lookup`, `approval_checker`, `email_sender`) and define highly complex, conditional edge routing (`if email_is_vulgar, route back to agent to rewrite`) entirely in pure Python logic while managing one centralized `state` dictionary!
