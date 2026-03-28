# Local Dev MCP Project

A robust MCP server for local development workflows, providing a standardized bridge between AI assistants and your local environment.

## Purpose

The **Local Dev MCP Project** is designed to give AI models (like Claude) direct, safe, and structured access to your local development environment via the **Model Context Protocol (MCP)**. 

By running this server, you empower your AI assistant to:
- **Understand Project Structure**: Quickly list and inspect files across your workspace.
- **Track Technical Debt**: Search for `TODO` and `FIXME` markers to identify pending tasks.
- **Maintain Contextual Notes**: Securely store and retrieve debugging notes or architectural decisions in local markdown files.
- **Perform Deep Code Search**: Locate specific logic or variables across the entire codebase.

This project serves as a "local-first" developer toolkit, enabling faster iteration and better AI-assisted development without requiring complex cloud integrations.

## Features

This server exposes a comprehensive local developer toolkit:

- **Notes Manager**: Create, append, list, and read markdown notes in a local directory.
- **Project Explorer**: List files recursively and search for TODO/FIXME comments.
- **Text Search**: Search for specific strings across all text files in the project.
- **File Utilities**: Read and summarize text files with safety checks.
- **MCP Resources**: Browse all notes via `notes://all` or specific notes via `notes://{name}`.
- **Developer Prompt**: Ready-to-use code review template.

## Installation

Using `uv` (recommended):

```bash
uv sync
```

## Running the Server

### For Development (with Inspector)

The MCP Inspector is the best way to test your server locally:

```bash
uv run mcp dev src/local_dev_mcp/server.py
```

### For Production / Scripts

You can run the server directly via the standardized entry point:

```bash
uv run local-dev-mcp
```

## Running Tests

Automated tests are included to ensure reliability:

```bash
uv run pytest
```

## Example Tool Calls

In the MCP Inspector, you can try:

- **`search_file_content`**: `{"query": "TODO", "root": "."}`
- **`add_note`**: `{"name": "readme-update", "content": "Updated readme with new features"}`
- **`list_project_files`**: `{"root": "src"}`

## Project Structure

- `pyproject.toml`: Standard build configuration and entry points.
- `src/local_dev_mcp/server.py`: Main MCP server implementation.
- `tests/test_server.py`: Unit tests for MCP tools.
- `notes/`: Directory where your notes are stored.
- `examples/sample_project/`: A sample directory structure for testing tools.

## Notes & Security

- The server is locked to the current working directory for file access.
- Only text-based file extensions are supported for reading and searching.
- Notes are stored in UTF-8 markdown format.
