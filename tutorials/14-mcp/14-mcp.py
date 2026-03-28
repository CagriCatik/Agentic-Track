from __future__ import annotations

from pathlib import Path
from typing import List

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Local Dev Utilities", json_response=True)

BASE_DIR = Path.cwd()
NOTES_DIR = BASE_DIR / "notes"
NOTES_DIR.mkdir(exist_ok=True)


def safe_note_path(name: str) -> Path:
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_", ".")).strip()
    if not cleaned:
        raise ValueError("Invalid note name.")
    if not cleaned.endswith(".md"):
        cleaned += ".md"
    return NOTES_DIR / cleaned


@mcp.tool()
def add_note(name: str, content: str) -> str:
    """
    Create or overwrite a markdown note in the local notes directory.
    """
    path = safe_note_path(name)
    path.write_text(content, encoding="utf-8")
    return f"Saved note: {path.name}"


@mcp.tool()
def append_note(name: str, content: str) -> str:
    """
    Append content to an existing markdown note, or create it if missing.
    """
    path = safe_note_path(name)
    prefix = "\n" if path.exists() and path.read_text(encoding="utf-8").strip() else ""
    with path.open("a", encoding="utf-8") as f:
        f.write(prefix + content)
    return f"Updated note: {path.name}"


@mcp.tool()
def list_notes() -> List[str]:
    """
    List all markdown notes in the local notes directory.
    """
    return sorted(p.name for p in NOTES_DIR.glob("*.md"))


@mcp.tool()
def read_note(name: str) -> str:
    """
    Read a note from the local notes directory.
    """
    path = safe_note_path(name)
    if not path.exists():
        return f"Note not found: {path.name}"
    return path.read_text(encoding="utf-8")


@mcp.tool()
def search_project_todos(root: str = ".", max_results: int = 50) -> List[str]:
    """
    Search recursively for TODO/FIXME comments in text-like files.
    Returns lines in the format: relative/path.py:12: TODO message
    """
    root_path = (BASE_DIR / root).resolve()
    if not root_path.exists():
        return [f"Path does not exist: {root_path}"]

    allowed_suffixes = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt",
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cpp",
        ".c", ".h", ".hpp", ".java", ".rs", ".go"
    }

    results: List[str] = []

    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in allowed_suffixes:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, line in enumerate(text.splitlines(), start=1):
            upper = line.upper()
            if "TODO" in upper or "FIXME" in upper:
                rel = path.relative_to(BASE_DIR)
                results.append(f"{rel}:{i}: {line.strip()}")
                if len(results) >= max_results:
                    return results

    return results


@mcp.tool()
def summarize_text_file(path: str, max_chars: int = 1200) -> str:
    """
    Read a local text file and return a compact extractive summary.
    This is deterministic, not LLM-based.
    """
    file_path = (BASE_DIR / path).resolve()

    if not file_path.exists():
        return f"File not found: {file_path}"

    if not file_path.is_file():
        return f"Not a file: {file_path}"

    text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return "File is empty."

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    preview = "\n".join(lines[:12])

    if len(preview) > max_chars:
        preview = preview[:max_chars].rstrip() + "..."

    return preview


@mcp.resource("notes://all")
def notes_index() -> str:
    """
    Expose a resource listing all notes.
    """
    files = sorted(p.name for p in NOTES_DIR.glob("*.md"))
    if not files:
        return "No notes available."
    return "\n".join(files)


@mcp.resource("notes://{name}")
def note_resource(name: str) -> str:
    """
    Expose a single note as an MCP resource.
    """
    path = safe_note_path(name)
    if not path.exists():
        return f"Note not found: {path.name}"
    return path.read_text(encoding="utf-8")


@mcp.prompt()
def code_review_prompt(language: str, code: str) -> str:
    """
    Provide a reusable prompt template for reviewing code.
    """
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


if __name__ == "__main__":
    mcp.run()