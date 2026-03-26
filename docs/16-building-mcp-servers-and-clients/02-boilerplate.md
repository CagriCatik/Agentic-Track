# 16.02 Boilerplate Setup

Before writing MCP servers or clients, we must set up our project scaffolding and environment using `uv`.

---

## 1. Initializing the Project

Start with a clean slate by initializing a new Python project:

```bash
uv init
```
This generates your boilerplate files: `README.md`, `main.py`, and `pyproject.toml`.

## 2. Virtual Environment Setup

Create and activate a virtual environment:

```bash
uv venv
source .venv/bin/activate  # Or equivalent for your OS
```

## 3. Installing Dependencies

We need the LangChain MCP Adapters and tracing modules.

```bash
uv add langchain-mcp-adapters langgraph langchain-openai python-dotenv
```

> [!NOTE]
> Notice that we did **not** explicitly install the `mcp` package. The `langchain-mcp-adapters` package automatically installs the core MCP SDK as a dependency.

## 4. Environment Variables

Create a `.env` file at the root of your project:

```env
OPENAI_API_KEY=your_openai_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langchain_key
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=mcp_test
```

> [!WARNING]
> Always create a `.gitignore` file and add `.env` to prevent accidentally committing your API keys to GitHub.

## 5. Main Script Sanity Check

Update your `main.py` with asynchronous boilerplate and load your environment variables to ensure everything is wired correctly.

```python
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    print("Welcome to MCP Adapters")
    print(f"OpenAI Key Loaded: {os.getenv('OPENAI_API_KEY') is not None}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run the file to verify:
```bash
uv run main.py
```