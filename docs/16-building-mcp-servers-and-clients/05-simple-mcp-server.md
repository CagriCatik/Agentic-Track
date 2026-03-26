# 16.05 Connecting the Math and Weather Servers

Before we write the client itself, make sure both of the servers we built are currently running. Open two separate terminal windows and run:

**(Terminal 1) Math Server:**
```bash
uv run servers/math_server.py
```

**(Terminal 2) Weather Server:**
```bash
uv run servers/weather_server.py
```
*(You should see the weather server binding to local port 8000).*

---

## The Client Setup

Create a new file named `langchain_client.py` in the root of your project.

We are going to use a special abstraction provided by the LangChain team: The `MultiServerMCPClient`.

By default in the MCP specification, the connection between a client and a server is **1-to-1**. If you wanted an agent to access 5 different MCP servers, you would traditionally have to write 5 distinct client connection classes and manage a massive mess of async context managers to bind them all together. 

LangChain abstracts this completely.

### The Boilerplate

```python
import asyncio
import os
from dotenv import load_dotenv

# LangChain Imports
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

load_dotenv()

async def main():
    llm = ChatOpenAI(model="gpt-4o")
    print("Agent Initialized.")
    
    # We will instantiate the Multi-Client here...

if __name__ == "__main__":
    asyncio.run(main())
```

Run `uv run langchain_client.py` to ensure your boilerplate executes cleanly without throwing any dependency errors. In the next lesson, we will initialize the Multi-Client.