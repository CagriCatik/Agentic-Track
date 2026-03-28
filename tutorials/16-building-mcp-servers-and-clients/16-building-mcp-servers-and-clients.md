# Tutorial 16: Building MCP Servers and Clients

In Tutorial 15 we used a pre-built MCP server. But what if you have a proprietary internal API (like a custom billing system) that you want your AI cursor to access? You must build your *own* MCP Server.

## The Goal
Build a minimal Python MCP server using the `@mcp` SDK that exposes a single Python function to the outside world as a standardized tool.

## Dependencies needed:
```bash
uv add mcp
```

## The Code (The Server)

Create a file named `my_mcp_server.py`:

```python
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

# 1. Initialize the Server object
server = Server("billing-mcp-server")

# 2. Register the Tool schema
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Tells any connected client what tools this server possesses."""
    return [
        Tool(
            name="get_customer_balance",
            description="Get the current billing balance for a customer ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "The UUID of the customer"}
                },
                "required": ["customer_id"]
            }
        )
    ]

# 3. Register the actual Function Logic
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Executes the tool when a client requests it."""
    if name != "get_customer_balance":
        raise ValueError(f"Tool {name} not found.")
        
    cust_id = arguments.get("customer_id")
    
    # Mocking a database lookup...
    if cust_id == "123":
        balance = "$450.00"
    else:
        balance = "$0.00"
        
    # Return the standardized result
    return [TextContent(type="text", text=f"The balance for {cust_id} is {balance}")]

# 4. Start the server on STDIO
async def main():
    print("Starting custom MCP Server...")
    # By running on STDIO, this script takes over the terminal's 
    # standard input/output streams to communicate via JSON-RPC.
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

## Running the Code
Because this server operates over standard input/output pipes (not HTTP), if you run it directly in your terminal, it will just sit there waiting for JSON-RPC messages to be typed in.

To use it, you configure your Host Client (like Claude Desktop) with a config file that literally says:
`"command": "uv", "args": ["run", "my_mcp_server.py"]`

The client will secretly spin up the script in the background, send the LLM's requests down the pipe, and your custom python script will execute!
