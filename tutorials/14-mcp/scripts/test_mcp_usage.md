# Manual MCP test sequence

1. Run `uv sync`
2. Run `uv run mcp dev src/local_dev_mcp/server.py`
3. In MCP Inspector, call `list_project_files` with root `examples/sample_project`
4. Call `search_project_todos` with the same root
5. Call `read_text_file` with `examples/sample_project/app.py`
6. Call `add_note` with any note name and content
7. Open resource `notes://all`
