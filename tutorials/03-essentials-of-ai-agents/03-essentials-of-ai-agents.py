import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain.agents import create_agent

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

load_dotenv()
console = Console()


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers together. Use this tool for multiplication."""
    return a * b


@tool
def get_current_time() -> str:
    """Return the current local date and time as an ISO string."""
    return datetime.now().isoformat(timespec="seconds")


@tool
def list_files(path: str = ".") -> list[str]:
    """List files and folders in a directory. Use this to inspect local project contents."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return [f"Path does not exist: {p}"]
    if not p.is_dir():
        return [f"Path is not a directory: {p}"]

    items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    return [f"{'[DIR]' if item.is_dir() else '[FILE]'} {item.name}" for item in items]


@tool
def read_text_file(path: str) -> str:
    """Read a UTF-8 text file from disk and return its contents."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"File does not exist: {p}"
    if not p.is_file():
        return f"Path is not a file: {p}"

    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"File is not valid UTF-8 text: {p}"
    except Exception as exc:
        return f"Failed to read file {p}: {exc}"


def main() -> None:
    console.print(Rule("[bold blue]Useful Local Agent"))

    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    console.print(f"[dim]Model:[/dim] {model_name}")
    console.print(f"[dim]Base URL:[/dim] {base_url}\n")

    llm = ChatOllama(
        model=model_name,
        base_url=base_url,
        temperature=0,
    )

    tools = [multiply, get_current_time, list_files, read_text_file]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=(
            "You are a practical local AI assistant. "
            "Use tools when they are needed for exact answers, file inspection, "
            "or current time. Be concise and factual."
        ),
    )

    question = (
        "List the files in the current folder, then tell me the current time, "
        "then multiply 14592 by 384."
    )

    console.print(Panel.fit(question, title="User", border_style="cyan"))

    response = agent.invoke(
        {"messages": [("user", question)]}
    )

    final_message = response["messages"][-1]
    console.print(Panel(str(final_message.content), title="Final Answer", border_style="green"))


if __name__ == "__main__":
    main()