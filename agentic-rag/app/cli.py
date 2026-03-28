"""Interactive CLI entry point for the Agentic RAG system."""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_settings


def run_ingest(force: bool = False) -> None:
    """Execute the ingestion pipeline."""
    from src.knowledge.ingestion import run_ingestion
    run_ingestion(force=force)


def run_chat() -> None:
    """Start the interactive Q&A loop."""
    from src.orchestration.graph import app

    print("\n" + "=" * 60)
    print("Agentic RAG — Automotive Engineering Knowledge Base")
    print("=" * 60)
    print("Type your question (or 'quit' to exit).\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print()

        # Invoke the graph
        initial_state = {
            "question": question,
            "generation": "",
            "documents": [],
            "datasource": "",
            "is_safe": "",
            "web_search_needed": "no",
            "retry_count": 0,
        }

        result = app.invoke(initial_state)

        # Print the answer
        print("\n" + "─" * 60)
        print("Answer:")
        print(result.get("generation", "No answer generated."))
        print("─" * 60)

        # Print sources
        documents = result.get("documents", [])
        if documents:
            print("\nSources:")
            seen = set()
            for doc in documents:
                src = doc.metadata.get("source_file", "?")
                page = doc.metadata.get("page_start", "?")
                key = f"{src}::{page}"
                if key not in seen:
                    seen.add(key)
                    print(f"   • {src}, Seite {page}")
        print()


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Agentic RAG — Automotive Engineering Knowledge Base"
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Run the ingestion pipeline (Bronze → Silver → Gold)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion of all PDFs (ignore manifest)",
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Print the Mermaid graph diagram and exit",
    )

    args = parser.parse_args()

    if args.graph:
        from src.orchestration.graph import app
        print(app.get_graph().draw_mermaid())
        return

    if args.ingest:
        run_ingest(force=args.force)
        return

    run_chat()


if __name__ == "__main__":
    main()
