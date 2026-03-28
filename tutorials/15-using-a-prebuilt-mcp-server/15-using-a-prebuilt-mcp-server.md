# Tutorial 15: Using a Prebuilt MCP Server

Instead of building our own server from scratch, we will integrate a pre-built open-source MCP server. For this tutorial, we will use the `sqlite` MCP server to allow our AI to inspect a local database.

## The Goal
Using the official `sqlite` MCP server via `npx`, we will connect a local client and execute an SQL query through the standardized protocol.

## Prerequisites
You must have Node.js and `npx` installed on your machine to pull the prebuilt server.
```bash
uv add mcp
```

## Part 1: Create a Dummy Database
Run this in your terminal to create a small test database:
```bash
sqlite3 test.db "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT); INSERT INTO users (name) VALUES ('Alice'), ('Bob');"
```

## Part 2: The MCP Client Code
We will use the Python MCP SDK to connect to the `npx` process over standard input/output (STDIO).

Create a file named `mcp_client.py`:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    # 1. Define the parameters to start the external server
    # We use npx to dynamically download and run the official sqlite MCP server
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sqlite", "test.db"],
    )

    print("Starting MCP Server connection...")

    # 2. Connect via STDIO
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 3. Initialize the handshake protocol
            await session.initialize()
            print("Handshake complete.\n")

            # 4. Ask the server what tools it exposes
            tools_response = await session.list_tools()
            print("Available Tools from the SQLite Server:")
            for tool in tools_response.tools:
                print(f" - {tool.name}: {tool.description}")

            print("\nExecuting 'read_query' tool...")
            
            # 5. Execute the specific tool remotely
            result = await session.call_tool("read_query", {"query": "SELECT * FROM users"})
            
            print("\nDatabase Output:")
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(run())
```

## Running the Code
```bash
uv run mcp_client.py
```

## What Happened?
Your python script started a Node.js process containing a fully functional Database API. Without writing any SQL connection logic yourself, your Python MCP client successfully requested the server's schematics, invoked an SQL query tool, and received the data over the local pipeline!
