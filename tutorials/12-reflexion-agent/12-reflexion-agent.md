# Tutorial 12: Reflexion Agent

While a *Reflection* agent simply critiques text, a **Reflexion** agent operates over *Tools and Environments*. If a Reflexion agent executes a Python execution tool and it crashes with a `SyntaxError`, the agent doesn't give up. It reads the stack trace, reflects on *why* the tool failed, rewrites the code, and tries again.

## The Goal
We will simulate a Reflexion loop where an Agent is forced to keep trying to use a completely broken tool until it realizes it needs to change its strategy.

## The Code

Create a file named `reflexion_agent.py`:

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

def flawed_database_tool(query: str) -> str:
    """A mock tool that intentionally crashes if the query isn't perfectly formatted."""
    if "SELECT" not in query:
        return "ERROR: Missing SELECT keyword."
    if "FROM users" not in query:
        return "ERROR: Missing FROM users clause."
    return "SUCCESS: [User: John, Age: 30]"

def main():
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # We maintain a memory of the agent's attempts and environment failures
    messages = [
        HumanMessage(content="Write a SQL query to get all users. Use the database_tool to test it. If the tool returns an ERROR, you must rewrite the query and try again.")
    ]
    
    print("--- Starting Reflexion Simulation ---")
    
    attempts = 0
    while attempts < 3:
        print(f"\nAttempt {attempts + 1}...")
        
        # 1. The Actor generates a query
        response = llm.invoke(messages)
        messages.append(response)
        
        # In a real LangGraph, we'd use function calling. Here we mock parsing the query out of the LLM text.
        query_guess = response.content
        print(f"Agent thought: {query_guess}")
        
        # 2. The Environment evaluates the action
        observation = flawed_database_tool(query_guess)
        print(f"Environment returned: {observation}")
        
        if "SUCCESS" in observation:
            print("\nTask Completed successfully!")
            break
            
        # 3. Reflexion: Append the failure to memory so the LLM learns what NOT to do
        messages.append(HumanMessage(content=f"Tool Execution Failed: {observation}. Reflect on the error and output a corrected query."))
        attempts += 1

if __name__ == "__main__":
    main()
```

## Running the Code
```bash
uv run reflexion_agent.py
```
Notice how the LLM actively learns from the explicit string errors returned by the tool, adjusting its strategy mathematically on the next loop!
