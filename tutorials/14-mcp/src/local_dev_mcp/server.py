from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("local-dev-mcp")

mcp = FastMCP("Local Dev Utilities", json_response=True)

# Use absolute path for BASE_DIR to ensure consistency
BASE_DIR = Path.cwd().resolve()
NOTES_DIR = BASE_DIR / "notes"
NOTES_DIR.mkdir(exist_ok=True)

TEXT_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cpp",
    ".c", ".h", ".hpp", ".java", ".rs", ".go", ".log",
}


def safe_note_path(name: str) -> Path:
    """Ensure the note path is safe and within the notes directory."""
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_", ".")).strip()
    if not cleaned:
        raise ValueError("Invalid note name.")
    if not cleaned.endswith(".md"):
        cleaned += ".md"
    return (NOTES_DIR / cleaned).resolve()


def safe_path(path_str: str) -> Path:
    """Ensure the path is within the BASE_DIR."""
    try:
        candidate = (BASE_DIR / path_str).resolve()
        # Check if candidate is within BASE_DIR
        candidate.relative_to(BASE_DIR)
        return candidate
    except (ValueError, RuntimeError) as exc:
        logger.warning(f"Access denied to path: {path_str}")
        raise ValueError(f"Path '{path_str}' must stay inside the project directory: {BASE_DIR}") from exc


@mcp.tool()
def add_note(name: str, content: str) -> str:
    """Create or overwrite a markdown note in the local notes directory."""
    try:
        path = safe_note_path(name)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Note added: {path.name}")
        return f"Saved note: {path.name}"
    except Exception as e:
        return f"Error adding note: {str(e)}"


@mcp.tool()
def append_note(name: str, content: str) -> str:
    """Append content to an existing markdown note, or create it if missing."""
    try:
        path = safe_note_path(name)
        prefix = "\n" if path.exists() and path.read_text(encoding="utf-8").strip() else ""
        with path.open("a", encoding="utf-8") as f:
            f.write(prefix + content)
        logger.info(f"Note updated: {path.name}")
        return f"Updated note: {path.name}"
    except Exception as e:
        return f"Error appending note: {str(e)}"


@mcp.tool()
def list_notes() -> List[str]:
    """List all markdown notes in the local notes directory."""
    return sorted(p.name for p in NOTES_DIR.glob("*.md"))


@mcp.tool()
def read_note(name: str) -> str:
    """Read a note from the local notes directory."""
    try:
        path = safe_note_path(name)
        if not path.exists():
            return f"Note not found: {path.name}"
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading note: {str(e)}"


@mcp.tool()
def list_project_files(root: str = ".", max_results: int = 100) -> List[str]:
    """List project files recursively under a root path."""
    try:
        root_path = safe_path(root)
        if not root_path.exists():
            return [f"Error: Path does not exist: {root}"]
        if not root_path.is_dir():
            return [f"Error: Not a directory: {root}"]

        files: List[str] = []
        for path in sorted(root_path.rglob("*")):
            if path.is_file():
                files.append(str(path.relative_to(BASE_DIR)))
                if len(files) >= max_results:
                    break
        return files
    except Exception as e:
        return [f"Error listing files: {str(e)}"]


@mcp.tool()
def search_project_todos(root: str = ".", max_results: int = 50) -> List[str]:
    """Search recursively for TODO/FIXME comments in text-like files."""
    try:
        root_path = safe_path(root)
        results: List[str] = []

        for path in root_path.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.splitlines(), start=1):
                    upper = line.upper()
                    if "TODO" in upper or "FIXME" in upper:
                        rel = path.relative_to(BASE_DIR)
                        results.append(f"{rel}:{i}: {line.strip()}")
                        if len(results) >= max_results:
                            return results
            except Exception:
                continue

        return results
    except Exception as e:
        return [f"Error searching todos: {str(e)}"]


@mcp.tool()
def search_file_content(query: str, root: str = ".", max_results: int = 50) -> List[str]:
    """Search for a specific string within all text files in the project."""
    try:
        root_path = safe_path(root)
        results: List[str] = []

        for path in root_path.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.splitlines(), start=1):
                    if query in line:
                        rel = path.relative_to(BASE_DIR)
                        results.append(f"{rel}:{i}: {line.strip()}")
                        if len(results) >= max_results:
                            return results
            except Exception:
                continue

        return results
    except Exception as e:
        return [f"Error searching content: {str(e)}"]


@mcp.tool()
def read_text_file(path: str, max_chars: int = 10000) -> str:
    """Read a local text file safely and return its content."""
    try:
        file_path = safe_path(path)
        if not file_path.exists():
            return f"Error: File not found: {path}"
        if not file_path.is_file():
            return f"Error: Not a file: {path}"
        if file_path.suffix.lower() not in TEXT_SUFFIXES:
            return f"Error: Unsupported file type: {file_path.suffix}"

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if len(text) > max_chars:
            return text[:max_chars].rstrip() + "\n... [truncated]"
        return text
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.resource("notes://all")
def notes_index() -> str:
    """Expose a resource listing all notes."""
    files = sorted(p.name for p in NOTES_DIR.glob("*.md"))
    if not files:
        return "No notes available."
    return "\n".join(files)


@mcp.resource("notes://{name}")
def note_resource(name: str) -> str:
    """Expose a single note as an MCP resource."""
    try:
        path = safe_note_path(name)
        if not path.exists():
            return f"Note not found: {path.name}"
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error accessing resource: {str(e)}"


@mcp.prompt()
def code_review_prompt(language: str, code: str) -> str:
    """Provide a reusable prompt template for reviewing code."""
    return (
        f"Review the following {language} code.\n\n"
        "Focus on:\n"
        "1. correctness\n"
        "2. readability\n"
        "3. edge cases\n"
        "4. performance issues\n"
        "5. security concerns\n\n"
        f"Code:\n{code}"
    )


def main() -> None:
    """Entry point for the local-dev-mcp server."""
    logger.info("Starting Local Dev Utilities MCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
