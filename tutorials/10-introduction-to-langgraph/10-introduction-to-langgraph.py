import os
import operator
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


def get_llm() -> ChatOllama:
    return ChatOllama(
        model=os.environ["OLLAMA_MODEL"],
        base_url=os.environ["OLLAMA_BASE_URL"],
        temperature=0,
    )


def chatbot_node(state: AgentState) -> dict:
    print("\n--- CHATBOT NODE TRIGGERED ---")
    llm = get_llm()
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def build_app():
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    return graph_builder.compile()


def run_single_example(app) -> None:
    user_input = "Hello, what is LangGraph?"
    print(f"User: {user_input}")

    initial_state = {
        "messages": [HumanMessage(content=user_input)]
    }

    final_state = app.invoke(initial_state)

    print("\n--- FINAL GRAPH OUTPUT ---")
    print(final_state["messages"][-1].content)
    print()


def run_interactive_chat(app) -> None:
    print("Interactive mode started.")
    print("Type 'exit' or 'quit' to stop.\n")

    state: AgentState = {"messages": []}

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("Session ended.")
            break

        if not user_input:
            continue

        state["messages"].append(HumanMessage(content=user_input))
        state = app.invoke(state)

        print(f"\nAssistant: {state['messages'][-1].content}\n")


def main() -> None:
    try:
        app = build_app()
    except KeyError as exc:
        missing_key = str(exc).strip("'")
        print(f"Missing required environment variable: {missing_key}")
        print("Check your .env file.")
        return
    except Exception as exc:
        print(f"Failed to initialize LangGraph/Ollama: {exc}")
        return

    print("=== LangGraph Intro with Local Ollama ===\n")

    run_single_example(app)
    run_interactive_chat(app)


if __name__ == "__main__":
    main()