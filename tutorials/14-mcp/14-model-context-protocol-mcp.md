# Tutorial 14: Model Context Protocol (MCP) Introduction

The **Model Context Protocol (MCP)** is an open standard introduced by Anthropic. It standardizes how AI applications (like Claude Desktop or Cursor) connect to external data sources and tools.

Instead of writing custom API integration code for Slack, GitHub, and Jira inside your LangChain application, you spin up standardized MCP Servers. Your LLM uses one single MCP Client to talk to all of them.

## The Architecture Layer

MCP operates on a strict Client-Server architecture:
1. **MCP Host:** The application you are using (e.g., Cursor IDE, Claude Desktop).
2. **MCP Client:** A protocol library embedded in the Host that initiates requests.
3. **MCP Server:** An external, lightweight server that exposes specific tools (e.g., a "GitHub Server" that exposes `read_repository` and `create_issue`).

## Exploring the Official MCP Registry

Before building anything, you should know that thousands of MCP servers already exist. 

You can find the official list of prebuilt, open-source servers maintained by Anthropic here:
[GitHub: modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)

### Common Prebuilt Servers Include:
* **SQLite / PostgreSQL:** Allows the LLM to run SELECT queries safely.
* **GitHub:** Allows the LLM to read PRs and commit code.
* **Slack:** Allows the LLM to read channels and post messages.
* **Brave Search:** Allows the LLM to browse the live internet.
* **Google Drive:** Allows the LLM to fetch internal corporate docs.

## Setup for the Next Chapter
In Tutorial 15, we will install and configure one of these prebuilt servers so that our local LLM client can interact with external dependencies without writing any API polling logic!
