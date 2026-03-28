# Tutorial 04: Agents Under the Hood (Manual ReAct Loop)

In Tutorial 03, we relied on `create_react_agent` to do all the heavy lifting. While easy, it hides the core architecture that makes Agentic AI work: The **Reason/Act (ReAct) Loop**. 

To truly understand agents, we must build the `while` loop manually.

## The Goal
We will build a loop that repeatedly prompts an LLM until it decides to stop using tools and answer the user directly. We will use the `bind_tools` method directly on the LLM.

## The Code

Create a file named `manual_react_loop.py`:

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
import json

load_dotenv()

# 1. Define our tool
@tool
def get_weather(city: str) -> str:
    """Get the current weather for a specific city."""
    weather_database = {
        "london": "rainy and 15C",
        "dubai": "sunny and 42C"
    }
    return weather_database.get(city.lower(), "weather unknown")

def main():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # 2. Bind the tool manually
    tools = [get_weather]
    tools_map = {t.name: t for t in tools}
    
    llm_with_tools = llm.bind_tools(tools)
    
    # 3. The Conversation Memory Array
    messages = [HumanMessage(content="What is the weather like in Dubai?")]
    
    print("--- Starting Manual ReAct Loop ---")
    
    # 4. The Agent Loop
    while True:
        # Step A: The LLM 'Reasons' based on context history
        print("Agent is thinking...")
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        
        # Step B: Check for Tool Calls
        if not response.tool_calls:
            # If there are no tool calls, the LLM has finished its logic.
            print("\nFinal Answer Reached!")
            print(f"Assistant: {response.content}")
            break
            
        print(f"Agent decided to make {len(response.tool_calls)} tool calls.")
        
        # Step C: 'Act' - Execute the requested tools
        for tool_call in response.tool_calls:
            print(f" > Executing tool: {tool_call['name']} with args {tool_call['args']}")
            
            # Fetch the actual python function by name
            selected_tool = tools_map[tool_call["name"]]
            
            # Run the tool
            observation = selected_tool.invoke(tool_call["args"])
            print(f" > Tool Returned: {observation}")
            
            # Step D: Append the observation back to memory as a ToolMessage
            tool_msg = ToolMessage(
                content=str(observation),
                tool_call_id=tool_call["id"]
            )
            messages.append(tool_msg)
            
        # The loop resets, the LLM will see the ToolMessage in its history and reason again based on the new data.

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run manual_react_loop.py
```
Watch the console output closely. You will see the agent thinking, deciding to execute the `get_weather` tool, observing that it is 42C in Dubai, looping back, and outputting the final English response without executing any more tools.
