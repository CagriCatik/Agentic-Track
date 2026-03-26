# 16.01 Introduction to Building MCP Servers & Clients

Previously, we integrated pre-built MCP servers with pre-built MCP clients (like Claude Desktop or Cursor). Now, we are diving a layer deeper into the architecture.

In the upcoming lessons, we will:
1. **Implement custom MCP Servers:** We will build servers that expose custom tools over both STDIO and SSE transports.
2. **Implement a Custom MCP Client:** We will build our own client that can connect to these servers using the official `langchain-mcp-adapters` package.
3. **Integrate the System:** We will connect our custom servers to our custom client, dynamically converting MCP tools into native LangChain tools.