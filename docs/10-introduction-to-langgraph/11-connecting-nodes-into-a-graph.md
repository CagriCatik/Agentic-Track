# 10.11 Connecting Nodes into a Graph

We have built our nodes (`agent_node` and `tool_node`). Now we must draw the map that tells the LangGraph engine how to navigate between them. 

This happens in `graph.py`.

---

> [!NOTE]
> **Beginner Analogy: The Traffic Cop**
> Our graph needs a way to decide if the AI is finished thinking, or if it needs to use a tool. We will build a small Python function that acts as a **Traffic Cop**. It stands between the Reasoner and the Tools, looks at what the LLM generated, and points left or right.

---

## 1. Initializing the Graph

First, we create a blank canvas (the `StateGraph`) and tell it to use our `MessagesState` blueprint so it knows how to handle memory.

```python
# graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from nodes import agent_node, tool_node

# 1. Initialize the blank map
workflow = StateGraph(MessagesState)
```

## 2. Adding the Nodes & the Front Door

Next, we place our workers onto the map and assign them names. Then we define where the program should start.

```python
# We use strings as IDs so we don't accidentally make typos later
AGENT_REASON = "agent_reason"
ACT = "act"

# 2. Place the nodes on the map
workflow.add_node(AGENT_REASON, agent_node)
workflow.add_node(ACT, tool_node)

# 3. Define the Front Door
# When the user submits a message, always send it to the thinking node first!
workflow.add_edge(START, AGENT_REASON)
```

## 3. The Traffic Cop (Conditional Routing)

This is the most important function in the entire graph. After the `agent_reason` node finishes, the Graph calls this function to decide where to go next.

```python
# 4. Define the Traffic Cop function
def should_continue(state: MessagesState) -> str:
    """
    Evaluates the LLM's output to determine if we act or if we finish.
    """
    
    # Look at the very last message in the State memory
    last_message = state["messages"][-1]
    
    # Did the LLM output a structured JSON tool request?
    if last_message.tool_calls:
        # Yes! Point to the "act" node!
        return "act"
    
    # No tool request found. The LLM must have output standard narrative text.
    # Therefore, we are done! Point to the exit!
    return "end"
```

## 4. Drawing the Edges

Now we use our Traffic Cop to draw the conditional pathways out of the Reasoner Node.

```python
# 5. Add the conditional Edge AFTER the reasoner finishes
workflow.add_conditional_edges(
    AGENT_REASON,       # Node that just finished
    should_continue,    # The Traffic Cop function to run
    {
        "act": ACT,     # If traffic cop says 'act', go here
        "end": END      # If traffic cop says 'end', go to the back door
    }
)
```

Finally, we need to close the loop! Once the `act` node (the tools) finishes retrieving the web search or doing the math, we absolutely MUST send that data back to the LLM so it can read it. 

```python
# 6. Add the return Edge
# ALWAYS go from the tools back to the reasoner to complete the loop!
workflow.add_edge(ACT, AGENT_REASON)
```

## 5. Compiling the Graph

The map is drawn. The final step is to hit the "Compile" button. This locks the graph into an executable application that we can actually run.

```python
# 7. Compile the application
app = workflow.compile()
```

### Visualizing Our Masterpiece

If you print the compiled application to an image, it returns this exact topological map:

```mermaid
graph TD
    classDef sys fill:#eceff1,stroke:#607d8b,stroke-width:2px;
    classDef node fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;
    classDef router fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    
    Start((START)):::sys --> Reasoner[agent_reason]:::node
    
    Reasoner --> Condition{should_continue}:::router
    
    Condition -- "act" --> Tool[act (ToolNode)]:::node
    Condition -- "end" --> End((END)):::sys
    
    Tool -- Return Edge --> Reasoner
```

## Summary
You have officially built a ReAct Agent graph! Notice how clean this architecture is. There are no messy `while` loops, no complicated `try/except` blocks trying to parse prompt text. 

The loop is defined structurally in the graph. The LLM controls the flow by simply outputting JSON tool coordinates, and the Python graph strictly enforces those decisions.
