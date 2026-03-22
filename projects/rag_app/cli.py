"""CLI display and interaction helpers."""

from __future__ import annotations


def print_startup(
    *,
    available_models: list[str],
    chat_model: str,
    embedding_model: str,
    temperature: float,
    top_k: int,
    retrieval_candidates: int,
    reranker_enabled: bool,
    reranker_mode: str,
    reranker_model: str | None,
) -> None:
    print("Discovered Ollama models:")
    for model in available_models:
        print(f" - {model}")

    print("\nSelected runtime configuration:")
    print(f" chat model      : {chat_model}")
    print(f" embedding model : {embedding_model}")
    print(f" temperature     : {temperature}")
    print(f" top-k           : {top_k}")
    print(f" candidates      : {retrieval_candidates}")
    print(f" reranker        : {reranker_enabled}")
    print(f" reranker mode   : {reranker_mode}")
    print(f" reranker model  : {reranker_model or 'feature-only'}")
    print("\nChat started. Commands: /quit, /exit, /help")


def run_chat_loop(chain) -> None:
    while True:
        try:
            question = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return

        if not question:
            continue
        if question in {"/quit", "/exit"}:
            return
        if question == "/help":
            print("Enter a question and press Enter. Use /quit or /exit to leave.")
            continue

        try:
            answer = chain.invoke(question)
        except Exception as exc:  # pragma: no cover - runtime/LLM path
            print(f"\nRequest failed: {exc}")
            continue

        print(f"\n{answer}")
