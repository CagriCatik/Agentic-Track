# Tutorial 03: The Essentials of AI Agents

Standard LLM chains (like the one we built in Tutorial 02) are entirely deterministic and linear: Prompt goes in, Text comes out.
**Agents** are fundamentally different. An Agent is an LLM equipped with a `scratchpad` and `tools`. It decides autonomously *if* it needs to use a tool, *which* tool to use, and when to stop.

## The Goal
We are going to give an LLM the ability to multiply numbers exactly, overriding its notoriously bad internal math skills by providing it with a Python calculator tool. We will use the `langgraph.prebuilt.create_react_agent` for simplicity.

## Dependencies needed:
```bash
uv add langgraph langchain-openai
```

## The Code

Create a file named `simple_agent.py`:

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

load_dotenv()

# 1. Define a powerful Custom Tool
@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers together. Always use this tool for multiplication."""
    return a * b

def main():
    # 2. Initialize the LLM
    # Note: The LLM must support function calling!
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # 3. Create the tools array
    tools = [multiply]
    
    # 4. Compile the Agent
    # create_react_agent generates a cyclic graph under the hood
    agent_executor = create_react_agent(llm, tools)
    
    # 5. Invoke the Agent
    question = "What is 14592 multiplied by 384?"
    print(f"User: {question}\n")
    
    # We pass the input wrapped as a human message
    response = agent_executor.invoke(
        {"messages": [("human", question)]}
    )
    
    # 6. Print the final answer
    final_message = response["messages"][-1]
    print(f"Agent Final Answer: {final_message.content}")

if __name__ == "__main__":
    main()
```

## What Happens Under the Hood?
1. The Agent kicks off and reads your prompt.
2. It realizes that `14592` and `384` are numbers that need to be multiplied, and sees it has a `multiply` tool.
3. It pauses text generation, outputs a JSON blob requesting to call `multiply(a=14592, b=384)`.
4. Our Python code executes the physical math function and returns `5603328`.
5. The Agent ingests that result as a `tool_message` and generates the final English sentence.

## Running the Code
```bash
uv run simple_agent.py
```
