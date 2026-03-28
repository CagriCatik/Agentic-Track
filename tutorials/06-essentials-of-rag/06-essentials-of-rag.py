import os
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

load_dotenv()
console = Console()


def main() -> None:
    console.print(Rule("[bold blue]Tutorial 06 - RAG Essentials"))

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text-v2-moe")

    console.print(f"[dim]Ollama URL:[/dim] {base_url}")
    console.print(f"[dim]Embedding Model:[/dim] {embedding_model}\n")

    # 1. Initialize the embedding model
    embeddings = OllamaEmbeddings(
        model=embedding_model,
        base_url=base_url,
    )

    console.print("[green]Embedding model loaded.[/green]\n")

    # 2. Prepare a tiny knowledge base
    documents = [
        "The company revenue in Q3 2023 was incredibly strong, up 24%.",
        "The company office is located in Seattle, Washington.",
        "The CEO's name is John Doe and he loves fishing.",
    ]

    console.print(
        Panel(
            "\n".join(f"- {doc}" for doc in documents),
            title="Knowledge Base",
            border_style="cyan",
        )
    )

    # 3. Create an in-memory Chroma vector store
    vector_store = Chroma.from_texts(
        texts=documents,
        embedding=embeddings,
        collection_name="tutorial_06_rag_essentials",
    )

    query = "Where is the headquarters?"
    console.print(f"\n[bold]User Query:[/bold] {query}")

    # 4. Perform semantic search
    # This returns tuples: (Document, score)
    results = vector_store.similarity_search_with_score(query, k=2)

    # 5. Display results
    if not results:
        console.print(
            Panel(
                "No match found.",
                title="Semantic Search Result",
                border_style="red",
            )
        )
        return

    formatted = []
    for i, (doc, score) in enumerate(results, start=1):
        formatted.append(
            f"{i}. score={score:.4f}\n{doc.page_content}"
        )

    console.print(
        Panel(
            "\n\n".join(formatted),
            title="Semantic Search Results",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()