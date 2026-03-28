import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

load_dotenv()


class EssayState(TypedDict):
    topic: str
    draft: str
    critique: str
    revision_count: int


def get_writer_llm() -> ChatOllama:
    return ChatOllama(
        model=os.environ["OLLAMA_MODEL"],
        base_url=os.environ["OLLAMA_BASE_URL"],
        temperature=0.7,
    )


def get_critic_llm() -> ChatOllama:
    return ChatOllama(
        model=os.environ["OLLAMA_MODEL"],
        base_url=os.environ["OLLAMA_BASE_URL"],
        temperature=0,
    )


def generate_draft(state: EssayState) -> dict:
    print(f"--- GENERATOR (Revision {state['revision_count']}) ---")

    llm = get_writer_llm()

    if state.get("critique"):
        prompt = (
            f"Rewrite an essay about {state['topic']}. "
            f"Improve it using this critique: {state['critique']}"
        )
    else:
        prompt = f"Write a terrible, 2-sentence essay about {state['topic']}."

    response = llm.invoke(prompt)

    return {
        "draft": response.content,
        "revision_count": state["revision_count"] + 1,
    }


def critique_draft(state: EssayState) -> dict:
    print("--- CRITIC ---")

    llm = get_critic_llm()

    prompt = (
        f"Read this essay: '{state['draft']}'. "
        "Provide a 1-sentence harsh critique on how to make it better."
    )

    response = llm.invoke(prompt)
    print(f"Critique: {response.content}\n")

    return {"critique": response.content}


def route_critique(state: EssayState):
    if state["revision_count"] >= 2:
        return END
    return "critique"


def build_app():
    builder = StateGraph(EssayState)

    builder.add_node("generate", generate_draft)
    builder.add_node("critique", critique_draft)

    builder.add_edge(START, "generate")
    builder.add_conditional_edges("generate", route_critique)
    builder.add_edge("critique", "generate")

    return builder.compile()


def main() -> None:
    try:
        app = build_app()
    except KeyError as exc:
        missing_key = str(exc).strip("'")
        print(f"Missing required environment variable: {missing_key}")
        print("Check your .env file.")
        return
    except Exception as exc:
        print(f"Failed to initialize Reflection Agent: {exc}")
        return

    print("Starting Reflection Loop...\n")

    initial_state: EssayState = {
        "topic": "Why cats are great",
        "draft": "",
        "critique": "",
        "revision_count": 0,
    }

    final_state = app.invoke(initial_state)

    print("\n--- FINAL ESSAY ---")
    print(final_state["draft"])


if __name__ == "__main__":
    main()